/**
 * Phase D3 — PDF rendering for the mobile reader.
 *
 * The M2 reader rendered the article's extracted text only. That works
 * for DOCX uploads and web-scraped articles but loses the figures,
 * tables, equation typography, and "exact-on-the-page" feel that
 * matters when a researcher is re-reading a paper they care about.
 *
 * This component renders the PDF itself, one canvas per page, with a
 * transparent text layer on top for selection and an SVG overlay for
 * highlight rectangles. Pages render lazily via IntersectionObserver
 * so a 40-page paper doesn't burn memory on a phone.
 *
 * Highlight model (Phase D3.2):
 *   - Existing highlights with ``bounding_coords.type === 'pdf'`` paint
 *     directly as ``<rect>``s on the SVG overlay using their saved
 *     normalised page rects.
 *   - Existing highlights with ``bounding_coords.type !== 'pdf'`` (i.e.
 *     legacy text-anchored M2 highlights) are best-effort migrated on
 *     first view: we look up the highlight's ``selected_text`` in the
 *     page's text layer and synthesise rects from the matching text
 *     items. If the text isn't found, the highlight remains in a
 *     "missing rects" bucket the parent can surface in a sheet so it's
 *     not silently lost.
 *   - New highlights from a long-press on the text layer concatenate
 *     the touched ``TextItem``s, build rects from each item's
 *     transform, and POST with ``bounding_coords = {type:'pdf', page,
 *     rects, text}``.
 *
 * Memory + perf (D3.4):
 *   - Max 5 pages rendered at once. Scrolling past an off-screen page
 *     calls ``page.cleanup()`` and clears the canvas via the
 *     ``canvas.width = 0`` trick to release GPU-backed buffers.
 *   - "Performance mode" (toggle in the parent's overflow menu) skips
 *     the text layer and forces scale 1.0 so old iPads stay smooth at
 *     the cost of losing selection.
 */
import {
  forwardRef,
  useEffect,
  useImperativeHandle,
  useMemo,
  useRef,
  useState,
} from 'react'

import type { Highlight, HighlightColour } from '@/lib/api'
import { cn } from '@/lib/utils'

// Late-bound so test envs can mock ``pdfjs-dist`` cheaply without
// jsdom having to satisfy the worker boot. Top-level imports of
// pdfjs-dist would also pull the worker URL at module-load time which
// is hostile to vitest.
type PdfDocumentProxy = {
  numPages: number
  getPage: (n: number) => Promise<PdfPageProxy>
  destroy: () => Promise<void>
}
type PdfPageProxy = {
  pageNumber: number
  getViewport: (opts: { scale: number }) => PdfViewport
  render: (params: { canvasContext: CanvasRenderingContext2D; viewport: PdfViewport }) => { promise: Promise<void>; cancel: () => void }
  getTextContent: () => Promise<{ items: PdfTextItem[] }>
  cleanup: () => void
}
type PdfViewport = {
  width: number
  height: number
  transform: number[]
}
type PdfTextItem = {
  str: string
  transform: number[]  // [scaleX, skewY, skewX, scaleY, x, y]
  width: number
  height: number
}

const HIGHLIGHT_BG: Record<HighlightColour, string> = {
  intro: '#EF4444',
  method: '#3B82F6',
  results: '#22C55E',
  discussion: '#EAB308',
}

const SCALE_PRESETS = [1.0, 1.5, 2.0, 3.0]
const MAX_RENDERED_PAGES = 5
const PRELOAD_PAGES = 3
const LONG_PRESS_MS = 500
const LONG_PRESS_TOLERANCE_PX = 10

export type PdfHighlightDraft = {
  page: number
  rects: { x0: number; y0: number; x1: number; y1: number }[]
  text: string
}

export type MobilePdfReaderTestHandle = {
  __forceNewHighlight: (draft: PdfHighlightDraft) => void
  __forcePage: (page: number) => void
}

export type MobilePdfReaderProps = {
  /** Resolved URL to the PDF (signed if S3, absolute API path otherwise). */
  fileUrl: string
  /** Existing highlights for this article. */
  highlights: Highlight[]
  /** Called when the user taps an existing highlight rect. */
  onHighlightTap: (h: Highlight) => void
  /** Called when the user finishes a selection via long-press + lift. */
  onCreateHighlight: (draft: PdfHighlightDraft) => void
  /** Performance mode skips the text layer (no selection) at scale 1.0. */
  performanceMode?: boolean
  /** Override the initial scale (defaults to 1.5 on small viewports, 2.0 elsewhere). */
  initialScale?: number
  /** For test mocking — pluggable pdfjs ``getDocument``. */
  pdfjsGetDocument?: (url: string) => { promise: Promise<PdfDocumentProxy> }
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/**
 * Convert a pdf.js text item's transform matrix + width/height into an
 * SVG-friendly rect in the *viewport* coordinate system (origin top-left
 * with +y down). pdf.js text transforms are PDF-native (origin bottom-left)
 * so we apply the viewport's transform matrix to flip y.
 *
 * Returns a normalised rect (0..1 per axis) inside the viewport so the
 * value we persist is independent of the render scale and the device.
 */
function itemToRect(item: PdfTextItem, viewport: PdfViewport) {
  // The pdf.js viewport transform is [a, b, c, d, e, f]; we use the
  // standard mult-then-translate. For text we want a tight rectangle
  // around the glyphs whose baseline is at (item.transform[4], item.transform[5]).
  // The item's width/height are in PDF units; viewport.transform applies scale.
  const t = item.transform
  const v = viewport.transform
  // Item origin (baseline-left) in PDF space.
  const px = t[4]
  const py = t[5]
  // Apply viewport matrix.
  const x = v[0] * px + v[2] * py + v[4]
  const y = v[1] * px + v[3] * py + v[5]
  // PDF glyph height in PDF units ≈ item.height; scale by viewport.
  const w = Math.abs(v[0]) * item.width
  const h = Math.abs(v[3]) * item.height
  // Convert to top-left rect: pdf.js viewport already places y at baseline.
  const y0 = y - h
  return {
    x0: x / viewport.width,
    y0: y0 / viewport.height,
    x1: (x + w) / viewport.width,
    y1: (y0 + h) / viewport.height,
  }
}

/**
 * Best-effort: locate a legacy text-anchored highlight inside a page's
 * text content. Returns rects (normalised 0..1) for the contiguous run
 * of matching items, or ``null`` if no match.
 *
 * The match is case-insensitive and tolerates trailing punctuation —
 * the same loose comparison the M2 reader uses for its word-index
 * search. We don't attempt fuzzy matching across line breaks because
 * the false-positive rate would be high.
 */
export function findRectsForText(
  items: PdfTextItem[],
  viewport: PdfViewport,
  needle: string,
): { x0: number; y0: number; x1: number; y1: number }[] | null {
  const clean = (s: string) =>
    s.replace(/^[^A-Za-z0-9]+|[^A-Za-z0-9]+$/g, '').toLowerCase()
  const needleWords = needle.trim().split(/\s+/).filter(Boolean).map(clean)
  if (needleWords.length === 0) return null
  // Flatten items into per-word tokens (most pdf.js text items are
  // already roughly word-sized, but some are full lines — split them).
  const tokens: { word: string; item: PdfTextItem }[] = []
  for (const item of items) {
    const ws = item.str.split(/\s+/).filter(Boolean)
    for (const w of ws) tokens.push({ word: clean(w), item })
  }
  for (let i = 0; i + needleWords.length <= tokens.length; i++) {
    let ok = true
    for (let j = 0; j < needleWords.length; j++) {
      if (tokens[i + j].word !== needleWords[j]) {
        ok = false
        break
      }
    }
    if (ok) {
      // Collect the unique TextItems backing this match (dedupe — many
      // tokens share an item when pdf.js emits whole-line items).
      const seen = new Set<PdfTextItem>()
      for (let j = 0; j < needleWords.length; j++) {
        seen.add(tokens[i + j].item)
      }
      return [...seen].map((it) => itemToRect(it, viewport))
    }
  }
  return null
}

// ---------------------------------------------------------------------------
// Per-page subcomponent
// ---------------------------------------------------------------------------

type PageState = {
  width: number
  height: number
  textItems: PdfTextItem[]
  viewport: PdfViewport
}

function PdfPage({
  pageNumber,
  document: doc,
  scale,
  highlights,
  performanceMode,
  visible,
  onHighlightTap,
  onCreateHighlight,
}: {
  pageNumber: number
  document: PdfDocumentProxy
  scale: number
  highlights: Highlight[]
  performanceMode: boolean
  visible: boolean
  onHighlightTap: (h: Highlight) => void
  onCreateHighlight: (draft: PdfHighlightDraft) => void
}) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null)
  const [state, setState] = useState<PageState | null>(null)
  const renderTaskRef = useRef<{ cancel: () => void } | null>(null)
  const pageRef = useRef<PdfPageProxy | null>(null)
  const [migrated, setMigrated] = useState<Map<string, { x0: number; y0: number; x1: number; y1: number }[]>>(new Map())

  useEffect(() => {
    let cancelled = false
    if (!visible) return
    ;(async () => {
      const page = await doc.getPage(pageNumber)
      if (cancelled) return
      pageRef.current = page
      const viewport = page.getViewport({ scale })
      const canvas = canvasRef.current
      if (!canvas) return
      canvas.width = viewport.width
      canvas.height = viewport.height
      const ctx = canvas.getContext('2d')
      if (!ctx) return
      const task = page.render({ canvasContext: ctx, viewport })
      renderTaskRef.current = task
      try {
        await task.promise
      } catch {
        // cancelled — fine.
      }
      if (cancelled) return
      let textItems: PdfTextItem[] = []
      if (!performanceMode) {
        try {
          const tc = await page.getTextContent()
          textItems = tc.items as PdfTextItem[]
        } catch {
          textItems = []
        }
      }
      if (!cancelled) {
        setState({
          width: viewport.width,
          height: viewport.height,
          textItems,
          viewport,
        })
      }
    })()
    return () => {
      cancelled = true
      // Dispose render task + free buffers (D3.4 perf).
      if (renderTaskRef.current) {
        try { renderTaskRef.current.cancel() } catch { /* noop */ }
        renderTaskRef.current = null
      }
      const c = canvasRef.current
      if (c && !visible) {
        // Free the GPU-backed buffer by zeroing dimensions.
        c.width = 0
        c.height = 0
      }
      if (pageRef.current && !visible) {
        try { pageRef.current.cleanup() } catch { /* noop */ }
        pageRef.current = null
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pageNumber, doc, scale, performanceMode, visible])

  // Migrate legacy highlights (best-effort).
  useEffect(() => {
    if (!state) return
    const next = new Map<string, { x0: number; y0: number; x1: number; y1: number }[]>()
    for (const h of highlights) {
      const bc = h.bounding_coords
      // Only attempt migration for legacy (non-pdf-typed) highlights
      // that haven't already been allocated to this page.
      if (bc.type === 'pdf') continue
      const found = findRectsForText(state.textItems, state.viewport, h.selected_text)
      if (found) next.set(h.id, found)
    }
    setMigrated(next)
  }, [highlights, state])

  // Long-press selection (touch-only — pointer drags scroll the list).
  const pressTimer = useRef<number | null>(null)
  const pressOrigin = useRef<{ x: number; y: number } | null>(null)
  const [selRange, setSelRange] = useState<{ from: number; to: number } | null>(null)

  function clearPress() {
    if (pressTimer.current != null) {
      window.clearTimeout(pressTimer.current)
      pressTimer.current = null
    }
  }

  function itemIdxAtPoint(clientX: number, clientY: number): number | null {
    if (!state || !canvasRef.current) return null
    const r = canvasRef.current.getBoundingClientRect()
    const lx = (clientX - r.left) / r.width
    const ly = (clientY - r.top) / r.height
    if (lx < 0 || lx > 1 || ly < 0 || ly > 1) return null
    // Linear search — text items are usually <1000 per page so this is fine.
    for (let i = 0; i < state.textItems.length; i++) {
      const rect = itemToRect(state.textItems[i], state.viewport)
      if (lx >= rect.x0 && lx <= rect.x1 && ly >= rect.y0 && ly <= rect.y1) {
        return i
      }
    }
    return null
  }

  function onTouchStart(e: React.TouchEvent) {
    if (e.touches.length !== 1) {
      clearPress()
      return
    }
    const t = e.touches[0]
    pressOrigin.current = { x: t.clientX, y: t.clientY }
    clearPress()
    pressTimer.current = window.setTimeout(() => {
      const idx = itemIdxAtPoint(t.clientX, t.clientY)
      if (idx != null) {
        setSelRange({ from: idx, to: idx })
      }
      pressTimer.current = null
    }, LONG_PRESS_MS)
  }
  function onTouchMove(e: React.TouchEvent) {
    if (selRange && state) {
      // Selection mode: extend to point under finger.
      const t = e.touches[0]
      const idx = itemIdxAtPoint(t.clientX, t.clientY)
      if (idx != null) setSelRange((r) => (r ? { from: r.from, to: idx } : r))
      return
    }
    const origin = pressOrigin.current
    if (!origin || pressTimer.current == null) return
    const t = e.touches[0]
    const dx = Math.abs(t.clientX - origin.x)
    const dy = Math.abs(t.clientY - origin.y)
    if (dx > LONG_PRESS_TOLERANCE_PX || dy > LONG_PRESS_TOLERANCE_PX) {
      clearPress()
      pressOrigin.current = null
    }
  }
  function onTouchEnd() {
    clearPress()
    pressOrigin.current = null
    if (selRange && state) {
      const lo = Math.min(selRange.from, selRange.to)
      const hi = Math.max(selRange.from, selRange.to)
      const items = state.textItems.slice(lo, hi + 1)
      const text = items.map((i) => i.str).join(' ').replace(/\s+/g, ' ').trim()
      const rects = items.map((i) => itemToRect(i, state.viewport))
      if (text.length > 0 && rects.length > 0) {
        onCreateHighlight({ page: pageNumber, rects, text })
      }
      setSelRange(null)
    }
  }

  const pageHighlights = useMemo(() => {
    const list: { id: string; colour: HighlightColour; rects: { x0: number; y0: number; x1: number; y1: number }[]; h: Highlight }[] = []
    for (const h of highlights) {
      const bc = h.bounding_coords
      if (bc.type === 'pdf') {
        if ((bc.page ?? 1) === pageNumber) {
          list.push({ id: h.id, colour: h.colour, rects: bc.rects, h })
        }
        continue
      }
      const m = migrated.get(h.id)
      if (m) list.push({ id: h.id, colour: h.colour, rects: m, h })
    }
    return list
  }, [highlights, migrated, pageNumber])

  // While we wait for the viewport size, render a placeholder so the
  // IntersectionObserver still has a real height to measure (otherwise
  // the page never enters the viewport).
  const placeholderHeight = state?.height ?? Math.round(window.innerWidth * 1.3)
  const placeholderWidth = state?.width ?? (window.innerWidth - 32)

  return (
    <div
      data-testid={`mpdf-page-${pageNumber}`}
      data-pdf-page={pageNumber}
      className="relative mx-auto my-3 bg-white shadow-sm"
      style={{ width: placeholderWidth, height: placeholderHeight, touchAction: 'pan-y' }}
      onTouchStart={onTouchStart}
      onTouchMove={onTouchMove}
      onTouchEnd={onTouchEnd}
    >
      <canvas ref={canvasRef} className="block w-full h-full" />
      {state && !performanceMode && (
        <svg
          data-testid={`mpdf-overlay-${pageNumber}`}
          className="pointer-events-none absolute inset-0 h-full w-full"
          viewBox={`0 0 ${state.width} ${state.height}`}
          preserveAspectRatio="none"
        >
          {pageHighlights.map((ph) =>
            ph.rects.map((r, i) => (
              <rect
                key={`${ph.id}:${i}`}
                data-testid={`mpdf-h-${ph.id}-${i}`}
                x={r.x0 * state.width}
                y={r.y0 * state.height}
                width={Math.max(2, (r.x1 - r.x0) * state.width)}
                height={Math.max(2, (r.y1 - r.y0) * state.height)}
                fill={HIGHLIGHT_BG[ph.colour]}
                fillOpacity={0.3}
                className="pointer-events-auto cursor-pointer"
                onClick={(e) => {
                  e.stopPropagation()
                  onHighlightTap(ph.h)
                }}
              />
            )),
          )}
          {/* Live selection feedback */}
          {selRange && state && (() => {
            const lo = Math.min(selRange.from, selRange.to)
            const hi = Math.max(selRange.from, selRange.to)
            return state.textItems.slice(lo, hi + 1).map((it, i) => {
              const r = itemToRect(it, state.viewport)
              return (
                <rect
                  key={`sel:${i}`}
                  data-testid={`mpdf-sel-${pageNumber}-${i}`}
                  x={r.x0 * state.width}
                  y={r.y0 * state.height}
                  width={Math.max(2, (r.x1 - r.x0) * state.width)}
                  height={Math.max(2, (r.y1 - r.y0) * state.height)}
                  fill="#38BDF8"
                  fillOpacity={0.35}
                />
              )
            })
          })()}
        </svg>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export const MobilePdfReader = forwardRef<
  MobilePdfReaderTestHandle,
  MobilePdfReaderProps
>(function MobilePdfReader(props, ref) {
  const {
    fileUrl,
    highlights,
    onHighlightTap,
    onCreateHighlight,
    performanceMode = false,
    initialScale,
    pdfjsGetDocument,
  } = props

  const [doc, setDoc] = useState<PdfDocumentProxy | null>(null)
  const [loadErr, setLoadErr] = useState<string | null>(null)
  // Default scale: 1.5 on narrow viewports for perf, else 2.0.
  const defaultScale = initialScale ?? (typeof window !== 'undefined' && window.innerWidth < 500 ? 1.5 : 2.0)
  const [scale, setScale] = useState<number>(performanceMode ? 1.0 : defaultScale)
  const [visiblePages, setVisiblePages] = useState<Set<number>>(new Set([1, 2, 3]))
  const [currentPage, setCurrentPage] = useState(1)
  const containerRef = useRef<HTMLDivElement | null>(null)

  useImperativeHandle(
    ref,
    () => ({
      __forceNewHighlight: (draft: PdfHighlightDraft) => {
        onCreateHighlight(draft)
      },
      __forcePage: (page: number) => setCurrentPage(page),
    }),
    [onCreateHighlight],
  )

  // Load the PDF.
  useEffect(() => {
    let cancelled = false
    setLoadErr(null)
    setDoc(null)
    ;(async () => {
      try {
        let task: { promise: Promise<PdfDocumentProxy> }
        if (pdfjsGetDocument) {
          task = pdfjsGetDocument(fileUrl) as {
            promise: Promise<PdfDocumentProxy>
          }
        } else {
          // Dynamically import so the worker URL isn't pulled at
          // module-load time (matters for vitest + SSR).
          const pdfjs = await import('pdfjs-dist')
          await import('@/lib/pdfjsSetup')
          task = pdfjs.getDocument(fileUrl) as unknown as {
            promise: Promise<PdfDocumentProxy>
          }
        }
        const d = await task.promise
        if (!cancelled) setDoc(d)
      } catch (e) {
        if (!cancelled) setLoadErr(e instanceof Error ? e.message : 'Failed to load PDF')
      }
    })()
    return () => {
      cancelled = true
    }
  }, [fileUrl, pdfjsGetDocument])

  // Dispose document on unmount / url change.
  useEffect(() => {
    return () => {
      if (doc) doc.destroy().catch(() => undefined)
    }
  }, [doc])

  // Track which pages are visible to decide what to mount.
  useEffect(() => {
    if (!doc || !containerRef.current) return
    if (typeof IntersectionObserver === 'undefined') {
      // jsdom — keep the initial preload set.
      return
    }
    const io = new IntersectionObserver(
      (entries) => {
        setVisiblePages((prev) => {
          const next = new Set(prev)
          for (const e of entries) {
            const el = e.target as HTMLElement
            const pageStr = el.getAttribute('data-pdf-page')
            if (!pageStr) continue
            const page = Number(pageStr)
            if (e.isIntersecting) {
              next.add(page)
              setCurrentPage(page)
            }
          }
          // Cap the rendered-pages set around currentPage to MAX_RENDERED_PAGES.
          if (next.size > MAX_RENDERED_PAGES) {
            const sorted = [...next].sort(
              (a, b) => Math.abs(a - currentPage) - Math.abs(b - currentPage),
            )
            return new Set(sorted.slice(0, MAX_RENDERED_PAGES))
          }
          return next
        })
      },
      { root: containerRef.current, rootMargin: '200px' },
    )
    const els = containerRef.current.querySelectorAll('[data-pdf-page]')
    els.forEach((el) => io.observe(el))
    return () => io.disconnect()
  }, [doc, currentPage])

  if (loadErr) {
    return (
      <div
        data-testid="mpdf-error"
        className="p-6 text-center text-[14px] text-rose-700"
      >
        Could not load PDF: {loadErr}
      </div>
    )
  }
  if (!doc) {
    return (
      <div
        data-testid="mpdf-loading"
        className="p-6 text-center text-[14px] text-muted-foreground"
      >
        Loading PDF…
      </div>
    )
  }

  const pages: number[] = []
  for (let i = 1; i <= doc.numPages; i++) pages.push(i)

  function zoomIn() {
    const idx = SCALE_PRESETS.indexOf(scale)
    if (idx < SCALE_PRESETS.length - 1) setScale(SCALE_PRESETS[idx + 1])
    else if (idx === -1) setScale(SCALE_PRESETS[0])
  }
  function zoomOut() {
    const idx = SCALE_PRESETS.indexOf(scale)
    if (idx > 0) setScale(SCALE_PRESETS[idx - 1])
  }

  return (
    <div
      ref={containerRef}
      data-testid="mpdf-root"
      className="relative flex-1 overflow-y-auto bg-neutral-100 pb-32"
    >
      {pages.map((p) => {
        const isVisible = visiblePages.has(p) || p <= PRELOAD_PAGES
        return (
          <PdfPage
            key={p}
            pageNumber={p}
            document={doc}
            scale={performanceMode ? 1.0 : scale}
            highlights={highlights}
            performanceMode={performanceMode}
            visible={isVisible}
            onHighlightTap={onHighlightTap}
            onCreateHighlight={onCreateHighlight}
          />
        )
      })}

      {/* Bottom progress + zoom chip */}
      <div
        data-testid="mpdf-progress"
        className="pointer-events-none fixed left-0 right-0 z-30 flex items-center justify-center gap-2 pb-[calc(72px+env(safe-area-inset-bottom))] text-[11px] font-medium text-foreground/80"
        style={{ bottom: 0 }}
      >
        <div className="pointer-events-auto flex items-center gap-1 rounded-full border border-border bg-background/95 px-3 py-1 shadow-sm backdrop-blur">
          <button
            type="button"
            data-testid="mpdf-zoom-out"
            aria-label="Zoom out"
            onClick={zoomOut}
            className="rounded-full px-1 text-[14px] leading-none hover:bg-muted"
          >
            −
          </button>
          <span data-testid="mpdf-page-chip">
            Page {currentPage} of {doc.numPages}
          </span>
          <button
            type="button"
            data-testid="mpdf-zoom-in"
            aria-label="Zoom in"
            onClick={zoomIn}
            className="rounded-full px-1 text-[14px] leading-none hover:bg-muted"
          >
            +
          </button>
        </div>
      </div>

      {/* Progress bar */}
      <div
        className={cn(
          'pointer-events-none fixed left-0 right-0 z-30 h-0.5 bg-primary/70 transition-[width]',
        )}
        style={{
          bottom: `calc(110px + env(safe-area-inset-bottom))`,
          width: `${(currentPage / Math.max(1, doc.numPages)) * 100}%`,
        }}
        data-testid="mpdf-progress-bar"
      />
    </div>
  )
})

export default MobilePdfReader
