/**
 * Phase M2.2 — Mobile article reader with touch-native highlights.
 *
 * The desktop reader (``ReaderShell``) is PDF-pixel based: it overlays
 * highlight rectangles on a pdf.js canvas. That model doesn't fit a
 * phone — PDFs reflow poorly at 390px and pinch-zoom interferes with
 * selection. Instead, this reader renders the article's extracted
 * text (the ``abstract`` field, which is populated by the upload /
 * DOI / PubMed ingestion pipelines for every article) as a stack of
 * paragraphs, split at word boundaries.
 *
 * Word indices are dense: every word in the article body gets a
 * unique integer, monotonically increasing from 0. Each ``<span>``
 * carries ``data-word-idx`` so the touch handlers can resolve a
 * pointer hit back to an index in ~O(1) via DOM lookup.
 *
 * Selection lifecycle:
 *
 *   1. ``touchstart`` on a word span fires a 500ms timer. If the user
 *      lifts or moves > 10px within that window, the timer is cleared
 *      and we treat it as a normal tap.
 *   2. After 500ms with the finger still down, we enter "selection
 *      mode": the word is highlighted, two ``<SelectionHandles>``
 *      anchor/focus pills appear, and a colour-swatch toolbar slides
 *      in from the bottom.
 *   3. Dragging a handle fires ``onMove(side, x, y)``; we look up the
 *      element at that point with ``elementFromPoint`` to find the
 *      word index under the finger, then update the local range.
 *   4. Tapping outside the selection cancels selection mode.
 *   5. Tapping a colour pill calls ``highlightsApi.create`` with the
 *      selected text + colour. ``bounding_coords`` is filled with a
 *      placeholder full-page box because we don't have PDF pixel
 *      coordinates on mobile — the backend stores it verbatim and the
 *      desktop reader simply won't be able to re-locate the highlight
 *      on the PDF until the user resaves it from desktop.
 *   6. Tapping an existing highlighted span opens a BottomSheet with
 *      summarise / re-colour / note / delete actions. The "popup on
 *      highlighting" pattern the desktop uses is explicitly avoided
 *      here per the M2 spec.
 *
 * Offline: the article + existing highlights are read through
 * ``cacheable()`` so the page renders even when the laptop is asleep.
 * Highlight mutations need connectivity and surface a clear toast on
 * failure.
 */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ArrowLeft, Loader2, MoreVertical } from 'lucide-react'
import {
  useCallback,
  useEffect,
  useImperativeHandle,
  useMemo,
  useRef,
  useState,
  forwardRef,
} from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { toast } from 'sonner'

import { Button } from '@/components/ui/button'
import {
  absoluteFileUrl,
  articlesApi,
  highlightsApi,
  type Article,
  type Highlight,
  type HighlightColour,
} from '@/lib/api'
import { cn } from '@/lib/utils'

import { BottomSheet } from '../components/BottomSheet'
import { ConfirmSheet } from '../components/ConfirmSheet'
import {
  MobilePdfReader,
  type MobilePdfReaderTestHandle,
  type PdfHighlightDraft,
} from '../components/MobilePdfReader'
import { SelectionHandles, type HandleSide } from '../components/SelectionHandles'
import { cacheable } from '../lib/offlineLearn'

const LONG_PRESS_MS = 500
const LONG_PRESS_TOLERANCE_PX = 10

// Tailwind ``highlight.intro|method|results|discussion`` palette
// duplicated as inline colours so the reader works even if the
// runtime CSS bundle is stripped. Keep in sync with
// ``apps/web/tailwind.config.ts``.
const HIGHLIGHT_COLOURS: { id: HighlightColour; bg: string; label: string }[] = [
  { id: 'intro', bg: '#EF4444', label: 'Intro' },
  { id: 'method', bg: '#3B82F6', label: 'Method' },
  { id: 'results', bg: '#22C55E', label: 'Results' },
  { id: 'discussion', bg: '#EAB308', label: 'Discussion' },
]

const SECTION_FOR_COLOUR: Record<HighlightColour, 'Introduction' | 'Methodology' | 'Results' | 'Discussion'> = {
  intro: 'Introduction',
  method: 'Methodology',
  results: 'Results',
  discussion: 'Discussion',
}

type Range = { start: number; end: number } | null

// ---------------------------------------------------------------------------
// Word + paragraph segmentation
// ---------------------------------------------------------------------------

type WordToken = {
  idx: number
  text: string
  paragraphIdx: number
}

type Paragraph = {
  idx: number
  /** Word indices in this paragraph, in order. */
  wordIndices: number[]
}

function segmentText(raw: string): { words: WordToken[]; paragraphs: Paragraph[] } {
  const paragraphs: Paragraph[] = []
  const words: WordToken[] = []
  const trimmed = (raw || '').trim()
  if (!trimmed) return { words, paragraphs }
  const paraTexts = trimmed.split(/\n{2,}|\r\n{2,}/g)
  paraTexts.forEach((pt, pIdx) => {
    const wordTexts = pt.split(/\s+/).filter((s) => s.length > 0)
    const indices: number[] = []
    for (const w of wordTexts) {
      const idx = words.length
      words.push({ idx, text: w, paragraphIdx: pIdx })
      indices.push(idx)
    }
    paragraphs.push({ idx: pIdx, wordIndices: indices })
  })
  return { words, paragraphs }
}

// ---------------------------------------------------------------------------
// Imperative handle exposed only for tests so we can drive selection
// without simulating a 500ms pointer-down.
// ---------------------------------------------------------------------------

export type MobileReaderTestHandle = {
  __forceSelection: (start: number, end: number) => void
  /** Phase D3 — drive a pdf-mode highlight creation without touching pdfjs. */
  __forcePdfHighlight?: (draft: PdfHighlightDraft) => void
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

type MobileReaderProps = {
  /**
   * Phase D3 — injectable pdfjs ``getDocument`` for tests. Production
   * callers leave this undefined and the PDF reader dynamically imports
   * ``pdfjs-dist`` + boots its worker via ``@/lib/pdfjsSetup``. Wiring
   * it through the page lets the MobileReader test suite stub pdf.js
   * end-to-end without bringing a canvas to jsdom.
   */
  pdfjsGetDocument?: (url: string) => { promise: Promise<unknown> }
}

const MobileReader = forwardRef<MobileReaderTestHandle, MobileReaderProps>(
  function MobileReader(props, ref) {
    const { pdfjsGetDocument } = props
    const params = useParams<{ articleId: string }>()
    const articleId = params.articleId
    const navigate = useNavigate()
    const qc = useQueryClient()

    // ------ Data
    const articleQ = useQuery({
      queryKey: ['mreader', 'article', articleId],
      queryFn: async () => {
        if (!articleId) throw new Error('missing articleId')
        return cacheable<Article>(
          `mreader:article:${articleId}`,
          () => articlesApi.get(articleId),
        )
      },
      enabled: !!articleId,
    })

    const highlightsQ = useQuery({
      queryKey: ['mreader', 'highlights', articleId],
      queryFn: async () => {
        if (!articleId) throw new Error('missing articleId')
        return cacheable<Highlight[]>(
          `mreader:highlights:${articleId}`,
          () => highlightsApi.list(articleId),
        )
      },
      enabled: !!articleId,
    })

    const article = articleQ.data?.data
    const highlights = highlightsQ.data?.data ?? []
    const offline =
      (articleQ.data?.offline ?? false) || (highlightsQ.data?.offline ?? false)

    // ------ Segment text + build word→highlight index
    const text = article?.abstract ?? ''
    const { words, paragraphs } = useMemo(() => segmentText(text), [text])

    // Map each highlight to the contiguous slice of words that contains
    // its selected_text. We do a naive subsequence search — good enough
    // for the abstract-length bodies we render here. If the highlight
    // text isn't found (e.g. the article body was reflowed), we skip it.
    const wordHighlight = useMemo(() => {
      const map = new Map<number, Highlight>() // wordIdx → owning highlight
      const ranges = new Map<string, { start: number; end: number }>() // id → range
      for (const h of highlights) {
        const needle = h.selected_text.trim().split(/\s+/).filter(Boolean)
        if (needle.length === 0) continue
        let found: { start: number; end: number } | null = null
        for (let i = 0; i + needle.length <= words.length; i++) {
          let ok = true
          for (let j = 0; j < needle.length; j++) {
            // Loose comparison — strip surrounding punctuation so we
            // forgive trailing commas / periods.
            const w = words[i + j].text.replace(/^[^A-Za-z0-9]+|[^A-Za-z0-9]+$/g, '')
            const n = needle[j].replace(/^[^A-Za-z0-9]+|[^A-Za-z0-9]+$/g, '')
            if (w.toLowerCase() !== n.toLowerCase()) {
              ok = false
              break
            }
          }
          if (ok) {
            found = { start: i, end: i + needle.length - 1 }
            break
          }
        }
        if (found) {
          ranges.set(h.id, found)
          for (let i = found.start; i <= found.end; i++) {
            // First highlight wins on overlap (rare).
            if (!map.has(i)) map.set(i, h)
          }
        }
      }
      return { wordToHighlight: map, idToRange: ranges }
    }, [words, highlights])

    // ------ Selection state
    const [range, setRange] = useState<Range>(null)
    const [editingHighlight, setEditingHighlight] = useState<Highlight | null>(null)

    // Phase D3 — render mode (PDF vs extracted text). Switches automatically
    // when the article carries a PDF file ref, but the user can flip back
    // to text from the overflow menu (slow connection, prefers reflowed
    // reading, etc.).
    const hasPdf = !!(
      article && article.file_url && (article.file_type === 'application/pdf')
    )
    const [readingMode, setReadingMode] = useState<'pdf' | 'text'>(
      hasPdf ? 'pdf' : 'text',
    )
    useEffect(() => {
      setReadingMode(hasPdf ? 'pdf' : 'text')
    }, [hasPdf])
    const [performanceMode, setPerformanceMode] = useState(false)
    const [overflowOpen, setOverflowOpen] = useState(false)

    const pdfRef = useRef<MobilePdfReaderTestHandle | null>(null)

    // Imperative test hook.
    useImperativeHandle(
      ref,
      () => ({
        __forceSelection: (start: number, end: number) => {
          setRange({ start: Math.min(start, end), end: Math.max(start, end) })
        },
        __forcePdfHighlight: (draft: PdfHighlightDraft) => {
          pdfRef.current?.__forceNewHighlight(draft)
        },
      }),
      [],
    )

    // Long-press tracking
    const pressTimer = useRef<number | null>(null)
    const pressOrigin = useRef<{ x: number; y: number; wordIdx: number } | null>(null)

    const containerRef = useRef<HTMLDivElement | null>(null)

    function clearPressTimer() {
      if (pressTimer.current != null) {
        window.clearTimeout(pressTimer.current)
        pressTimer.current = null
      }
    }

    // Resolve a pointer position (clientX/Y) to a word-idx by querying
    // ``document.elementFromPoint`` and walking up to the nearest
    // ``data-word-idx`` ancestor.
    const wordIdxAtPoint = useCallback(
      (clientX: number, clientY: number): number | null => {
        const el = document.elementFromPoint(clientX, clientY)
        if (!el) return null
        const walker = el.closest('[data-word-idx]') as HTMLElement | null
        if (!walker) return null
        const idx = Number(walker.getAttribute('data-word-idx'))
        return Number.isFinite(idx) ? idx : null
      },
      [],
    )

    // ------ Text long-press handlers (touch events, not pointer, per spec).
    function onTouchStart(e: React.TouchEvent<HTMLDivElement>) {
      // Ignore multi-touch (pinch-zoom). Fix-13/7: if a second finger
      // lands *after* a single-touch press has already started, we
      // also need to cancel — otherwise the 500ms timer would still
      // fire mid-pinch and pop up the selection toolbar over a
      // zooming user.
      if (e.touches.length > 1) {
        clearPressTimer()
        pressOrigin.current = null
        return
      }
      if (e.touches.length !== 1) {
        clearPressTimer()
        return
      }
      const t = e.touches[0]
      const idx = wordIdxAtPoint(t.clientX, t.clientY)
      if (idx == null) return
      pressOrigin.current = { x: t.clientX, y: t.clientY, wordIdx: idx }
      clearPressTimer()
      pressTimer.current = window.setTimeout(() => {
        // Long-press fired. Start selection on this word.
        setRange({ start: idx, end: idx })
        pressTimer.current = null
      }, LONG_PRESS_MS)
    }

    function onTouchMove(e: React.TouchEvent<HTMLDivElement>) {
      // Fix-13/7: a second finger arrived during move (pinch-zoom).
      // Bail out of the long-press machinery entirely.
      if (e.touches.length > 1) {
        clearPressTimer()
        pressOrigin.current = null
        return
      }
      const origin = pressOrigin.current
      if (!origin || pressTimer.current == null) return
      const t = e.touches[0]
      const dx = Math.abs(t.clientX - origin.x)
      const dy = Math.abs(t.clientY - origin.y)
      if (dx > LONG_PRESS_TOLERANCE_PX || dy > LONG_PRESS_TOLERANCE_PX) {
        // The user is scrolling, not long-pressing. Cancel.
        clearPressTimer()
        pressOrigin.current = null
      }
    }

    function onTouchEnd() {
      clearPressTimer()
      pressOrigin.current = null
    }

    // ------ Selection drag handles
    const onHandleMove = useCallback(
      (side: HandleSide, clientX: number, clientY: number) => {
        if (!range) return
        const idx = wordIdxAtPoint(clientX, clientY)
        if (idx == null) return
        setRange((r) => {
          if (!r) return r
          if (side === 'anchor') {
            const start = Math.min(idx, r.end)
            const end = Math.max(idx, r.end)
            return { start, end }
          } else {
            const start = Math.min(r.start, idx)
            const end = Math.max(r.start, idx)
            return { start, end }
          }
        })
      },
      [range, wordIdxAtPoint],
    )

    // ------ Tap-outside handling
    const onContainerTap = useCallback(
      (e: React.MouseEvent<HTMLDivElement>) => {
        if (!range) return
        // If the tap target is inside a selected word or a handle,
        // let it bubble; otherwise dismiss.
        const target = e.target as HTMLElement
        const inHandle = target.closest('[data-side]')
        if (inHandle) return
        const wordEl = target.closest('[data-word-idx]') as HTMLElement | null
        if (wordEl) {
          const idx = Number(wordEl.getAttribute('data-word-idx'))
          if (idx >= range.start && idx <= range.end) return
        }
        setRange(null)
      },
      [range],
    )

    // ------ Highlight create / update / delete
    const selectedText = useMemo(() => {
      if (!range) return ''
      return words.slice(range.start, range.end + 1).map((w) => w.text).join(' ')
    }, [range, words])

    const createMutation = useMutation({
      mutationFn: async ({ colour, note }: { colour: HighlightColour; note?: string }) => {
        if (!articleId) throw new Error('missing article')
        if (!range) throw new Error('no selection')
        return highlightsApi.create(articleId, {
          page_number: 1,
          selected_text: selectedText,
          colour,
          section: SECTION_FOR_COLOUR[colour],
          // The full-page placeholder rect — mobile doesn't have PDF
          // pixel coordinates available. The backend stores it
          // verbatim; the desktop reader treats it as off-screen.
          bounding_coords: { rects: [{ x0: 0, y0: 0, x1: 1, y1: 0.05 }] },
          user_note: note ?? null,
        })
      },
      onSuccess: () => {
        qc.invalidateQueries({ queryKey: ['mreader', 'highlights', articleId] })
        setRange(null)
        setNoteSheet(false)
        setNoteDraft('')
        toast.success('Highlight saved')
      },
      onError: (err) => {
        const msg = err instanceof Error ? err.message : 'Failed to save'
        if (!navigator.onLine) {
          toast.error('Offline — connect to laptop to save')
        } else {
          toast.error(msg)
        }
      },
    })

    // Phase D3 — separate PDF-mode create mutation. The shape of the
    // request body differs from text-mode (no word-derived
    // selected_text, real page_number, pdf-typed bounding_coords) so a
    // dedicated mutation is cleaner than overloading createMutation.
    const createPdfMutation = useMutation({
      mutationFn: async ({
        draft,
        colour,
      }: {
        draft: PdfHighlightDraft
        colour: HighlightColour
      }) => {
        if (!articleId) throw new Error('missing article')
        return highlightsApi.create(articleId, {
          page_number: draft.page,
          selected_text: draft.text,
          colour,
          section: SECTION_FOR_COLOUR[colour],
          bounding_coords: {
            rects: draft.rects,
            type: 'pdf',
            page: draft.page,
            text: draft.text,
          },
        })
      },
      onSuccess: () => {
        qc.invalidateQueries({ queryKey: ['mreader', 'highlights', articleId] })
        setPdfDraft(null)
        toast.success('Highlight saved')
      },
      onError: (err) => {
        const msg = err instanceof Error ? err.message : 'Failed to save'
        if (!navigator.onLine) {
          toast.error('Offline — connect to laptop to save')
        } else {
          toast.error(msg)
        }
      },
    })

    // Holds the pending PDF selection while the user picks a colour.
    const [pdfDraft, setPdfDraft] = useState<PdfHighlightDraft | null>(null)

    const updateMutation = useMutation({
      mutationFn: async ({ id, note }: { id: string; note: string }) => {
        return highlightsApi.update(id, { user_note: note })
      },
      onSuccess: () => {
        qc.invalidateQueries({ queryKey: ['mreader', 'highlights', articleId] })
      },
      onError: (err) => {
        toast.error(err instanceof Error ? err.message : 'Save failed')
      },
    })

    // D1.1 — separate mutation so the colour PATCH updates the open
    // bottom-sheet's local state in addition to invalidating the list.
    const recolourMutation = useMutation({
      mutationFn: async ({ id, colour }: { id: string; colour: HighlightColour }) => {
        return highlightsApi.update(id, { colour })
      },
      onSuccess: (h) => {
        qc.invalidateQueries({ queryKey: ['mreader', 'highlights', articleId] })
        setEditingHighlight(h)
      },
      onError: (err) => {
        toast.error(err instanceof Error ? err.message : 'Could not change colour')
      },
    })

    const deleteMutation = useMutation({
      mutationFn: async (id: string) => highlightsApi.delete(id),
      onSuccess: () => {
        qc.invalidateQueries({ queryKey: ['mreader', 'highlights', articleId] })
        setEditingHighlight(null)
      },
      onError: (err) => {
        toast.error(err instanceof Error ? err.message : 'Delete failed')
      },
    })

    const summariseMutation = useMutation({
      mutationFn: async (id: string) => highlightsApi.summarise(id),
      onSuccess: (h) => {
        qc.invalidateQueries({ queryKey: ['mreader', 'highlights', articleId] })
        setEditingHighlight(h)
      },
      onError: (err) => {
        toast.error(err instanceof Error ? err.message : 'Paraphrase failed')
      },
    })

    // ------ "Add note" sheet bookkeeping
    const [noteSheet, setNoteSheet] = useState(false)
    const [noteDraft, setNoteDraft] = useState('')
    const [chosenColour, setChosenColour] = useState<HighlightColour>('intro')

    function onPickColour(colour: HighlightColour) {
      setChosenColour(colour)
      createMutation.mutate({ colour })
    }

    function onOpenNote() {
      setNoteSheet(true)
    }

    function onSaveNote() {
      createMutation.mutate({ colour: chosenColour, note: noteDraft.trim() || undefined })
    }

    // ------ Note auto-save (when editing an existing highlight)
    const editNoteRef = useRef<number | null>(null)
    const [editNoteDraft, setEditNoteDraft] = useState('')
    // Fix-13/9: replace window.confirm() with an in-app sheet. iOS PWAs
    // can swallow confirm() entirely when the page isn't the foreground
    // tab, leaving the user stuck.
    const [deleteConfirmOpen, setDeleteConfirmOpen] = useState(false)
    useEffect(() => {
      setEditNoteDraft(editingHighlight?.user_note ?? '')
    }, [editingHighlight?.id, editingHighlight?.user_note])

    function onEditNoteChange(v: string) {
      setEditNoteDraft(v)
      if (editNoteRef.current) window.clearTimeout(editNoteRef.current)
      if (!editingHighlight) return
      editNoteRef.current = window.setTimeout(() => {
        updateMutation.mutate({ id: editingHighlight.id, note: v })
      }, 800)
    }

    function onEditColour(colour: HighlightColour) {
      if (!editingHighlight) return
      if (editingHighlight.colour === colour) return
      recolourMutation.mutate({ id: editingHighlight.id, colour })
    }

    // ------ Render
    if (!articleId) {
      return (
        <div className="p-6 text-center text-[14px] text-muted-foreground">
          No article selected.
        </div>
      )
    }
    if (articleQ.isLoading || highlightsQ.isLoading) {
      return (
        <div className="flex items-center justify-center py-16">
          <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
        </div>
      )
    }
    if (articleQ.isError || !article) {
      return (
        <div className="p-6 text-center text-[14px] text-rose-700">
          Could not load article.
        </div>
      )
    }

    return (
      <div className="flex min-h-full flex-col bg-background" data-testid="mreader-root">
        {/* Custom header */}
        <header className="sticky top-0 z-30 flex h-12 items-center gap-2 border-b border-border bg-background/95 px-2 backdrop-blur">
          <button
            type="button"
            aria-label="Back"
            onClick={() => navigate('/m/library')}
            className="inline-flex h-10 w-10 items-center justify-center rounded-md hover:bg-muted"
            data-testid="mreader-back"
          >
            <ArrowLeft className="h-5 w-5" />
          </button>
          <h1
            className="flex-1 truncate text-[14px] font-semibold tracking-tight"
            data-testid="mreader-title"
          >
            {article.title}
          </h1>
          {offline && (
            <span
              data-testid="mreader-offline-badge"
              className="rounded-md bg-amber-500/15 px-2 py-0.5 text-[10px] font-medium uppercase tracking-wider text-amber-700"
            >
              Offline
            </span>
          )}
          <button
            type="button"
            aria-label="More options"
            data-testid="mreader-overflow"
            onClick={() => setOverflowOpen(true)}
            className="inline-flex h-10 w-10 items-center justify-center rounded-md hover:bg-muted"
          >
            <MoreVertical className="h-5 w-5" />
          </button>
        </header>

        {/* Article body — Phase D3: branch on render mode */}
        {readingMode === 'pdf' && article.file_url && (
          <MobilePdfReader
            ref={pdfRef}
            fileUrl={absoluteFileUrl(article.file_url) ?? article.file_url}
            highlights={highlights}
            onHighlightTap={(h) => setEditingHighlight(h)}
            onCreateHighlight={(draft) => setPdfDraft(draft)}
            performanceMode={performanceMode}
            pdfjsGetDocument={
              pdfjsGetDocument as
                | ((url: string) => { promise: Promise<never> })
                | undefined
            }
          />
        )}

        {/* PDF colour picker — appears once a draft is staged */}
        {readingMode === 'pdf' && pdfDraft && (
          <div
            data-testid="mreader-pdf-swatch-bar"
            className="fixed left-0 right-0 z-30 border-t border-border bg-background/95 px-3 py-3 pb-[calc(12px+env(safe-area-inset-bottom))] shadow-[0_-4px_12px_rgba(0,0,0,0.08)] backdrop-blur"
            style={{ bottom: 64 }}
          >
            <div className="mb-2 line-clamp-2 text-[12px] italic text-muted-foreground">
              {pdfDraft.text}
            </div>
            <div className="flex items-center justify-between gap-2">
              <div className="flex gap-2">
                {HIGHLIGHT_COLOURS.map((c) => (
                  <button
                    key={c.id}
                    type="button"
                    data-testid={`mreader-pdf-pill-${c.id}`}
                    aria-label={`Highlight ${c.label}`}
                    onClick={() =>
                      createPdfMutation.mutate({ draft: pdfDraft, colour: c.id })
                    }
                    className="h-9 w-9 rounded-full ring-2 ring-background"
                    style={{ backgroundColor: c.bg }}
                  />
                ))}
              </div>
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={() => setPdfDraft(null)}
                data-testid="mreader-pdf-cancel"
              >
                Cancel
              </Button>
            </div>
          </div>
        )}

        {readingMode === 'text' && (
        <div
          ref={containerRef}
          data-testid="mreader-body"
          onClick={onContainerTap}
          onTouchStart={onTouchStart}
          onTouchMove={onTouchMove}
          onTouchEnd={onTouchEnd}
          onTouchCancel={onTouchEnd}
          className="relative flex-1 px-4 py-4 pb-44 text-[15px] leading-7 text-foreground"
          style={{ touchAction: 'pan-y' }}
        >
          {text.trim().length === 0 && (
            <div
              data-testid="mreader-empty"
              className="py-12 text-center text-[13px] text-muted-foreground"
            >
              No extracted text is available for this article on mobile.
              Open it on the desktop reader to read the PDF.
            </div>
          )}

          {paragraphs.map((p) => (
            <p key={p.idx} className="mb-4">
              {p.wordIndices.map((wIdx, j) => {
                const word = words[wIdx]
                const inSelection =
                  range != null && wIdx >= range.start && wIdx <= range.end
                const owningHighlight = wordHighlight.wordToHighlight.get(wIdx)
                const bg = owningHighlight
                  ? HIGHLIGHT_COLOURS.find((c) => c.id === owningHighlight.colour)?.bg
                  : null
                return (
                  <span key={wIdx}>
                    <span
                      data-word-idx={wIdx}
                      data-testid={`mreader-word-${wIdx}`}
                      onClick={(e) => {
                        if (owningHighlight && !inSelection) {
                          e.stopPropagation()
                          setEditingHighlight(owningHighlight)
                        }
                      }}
                      className={cn(
                        'rounded-sm transition-colors',
                        inSelection && 'outline-2 outline-dashed outline-sky-500',
                      )}
                      style={
                        bg
                          ? {
                              backgroundColor: `${bg}4D`, // 30% alpha
                              boxShadow: `inset 0 -2px 0 ${bg}`,
                            }
                          : inSelection
                          ? {
                              backgroundColor: 'rgba(56,189,248,0.25)',
                            }
                          : undefined
                      }
                    >
                      {word.text}
                    </span>
                    {j < p.wordIndices.length - 1 ? ' ' : ''}
                  </span>
                )
              })}
            </p>
          ))}

          {/* Selection handles overlay */}
          <SelectionHandlesAnchored range={range} words={words} containerRef={containerRef} onMove={onHandleMove} />
        </div>
        )}

        {/* Colour-swatch toolbar (visible only when a selection is live) */}
        {readingMode === 'text' && range && (
          <div
            data-testid="mreader-swatch-bar"
            className="fixed left-0 right-0 z-30 border-t border-border bg-background/95 px-3 py-3 pb-[calc(12px+env(safe-area-inset-bottom))] shadow-[0_-4px_12px_rgba(0,0,0,0.08)] backdrop-blur"
            style={{ bottom: 64 }}
          >
            <div className="flex items-center justify-between gap-2">
              <div className="flex gap-2">
                {HIGHLIGHT_COLOURS.map((c) => (
                  <button
                    key={c.id}
                    type="button"
                    data-testid={`mreader-pill-${c.id}`}
                    aria-label={`Highlight ${c.label}`}
                    onClick={() => onPickColour(c.id)}
                    className="h-9 w-9 rounded-full ring-2 ring-background"
                    style={{ backgroundColor: c.bg }}
                  />
                ))}
              </div>
              <div className="flex gap-2">
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={onOpenNote}
                  data-testid="mreader-add-note"
                >
                  Add note
                </Button>
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={() => setRange(null)}
                  data-testid="mreader-cancel"
                >
                  Cancel
                </Button>
              </div>
            </div>
          </div>
        )}

        {/* "Add note" sheet — for new highlights */}
        <BottomSheet
          open={noteSheet}
          onClose={() => setNoteSheet(false)}
          title="Add a note"
          snapPoints={['60%']}
        >
          <div className="flex flex-col gap-3 pb-2" data-testid="mreader-note-sheet">
            <blockquote className="rounded-lg border border-border bg-muted/40 px-3 py-2 text-[13px] italic text-muted-foreground">
              {selectedText}
            </blockquote>
            <div className="flex flex-wrap gap-2">
              {HIGHLIGHT_COLOURS.map((c) => (
                <button
                  key={c.id}
                  type="button"
                  onClick={() => setChosenColour(c.id)}
                  className={cn(
                    'h-8 w-8 rounded-full ring-2',
                    chosenColour === c.id ? 'ring-foreground' : 'ring-background',
                  )}
                  style={{ backgroundColor: c.bg }}
                  aria-label={c.label}
                  data-testid={`mreader-note-pill-${c.id}`}
                />
              ))}
            </div>
            <textarea
              value={noteDraft}
              onChange={(e) => setNoteDraft(e.target.value)}
              placeholder="Why does this passage matter?"
              data-testid="mreader-note-textarea"
              className="min-h-[120px] rounded-lg border border-border bg-card px-3 py-2 text-[14px] focus:outline-none focus:ring-2 focus:ring-primary/40"
            />
            <Button
              type="button"
              onClick={onSaveNote}
              disabled={createMutation.isPending}
              data-testid="mreader-note-save"
            >
              {createMutation.isPending ? 'Saving…' : 'Save highlight'}
            </Button>
          </div>
        </BottomSheet>

        {/* Existing-highlight sheet */}
        <BottomSheet
          open={editingHighlight !== null}
          onClose={() => setEditingHighlight(null)}
          title="Highlight"
          snapPoints={['70%']}
        >
          {editingHighlight && (
            <div
              className="flex flex-col gap-3 pb-2"
              data-testid="mreader-edit-sheet"
            >
              <blockquote
                className="max-h-32 overflow-y-auto rounded-lg border border-border bg-muted/40 px-3 py-2 text-[13px] italic"
                style={{
                  boxShadow: `inset 4px 0 0 ${
                    HIGHLIGHT_COLOURS.find((c) => c.id === editingHighlight.colour)?.bg
                  }`,
                }}
              >
                {editingHighlight.selected_text}
              </blockquote>

              <div className="flex flex-wrap items-center gap-2 text-[12px]">
                {HIGHLIGHT_COLOURS.map((c) => (
                  <button
                    key={c.id}
                    type="button"
                    onClick={() => onEditColour(c.id)}
                    className={cn(
                      'h-7 w-7 rounded-full ring-2',
                      editingHighlight.colour === c.id
                        ? 'ring-foreground'
                        : 'ring-background',
                    )}
                    style={{ backgroundColor: c.bg }}
                    aria-label={`Change colour to ${c.label}`}
                    data-testid={`mreader-edit-pill-${c.id}`}
                  />
                ))}
              </div>

              <Button
                type="button"
                variant="outline"
                size="sm"
                disabled={summariseMutation.isPending}
                onClick={() => summariseMutation.mutate(editingHighlight.id)}
                data-testid="mreader-edit-paraphrase"
              >
                {summariseMutation.isPending ? 'Paraphrasing…' : 'Paraphrase with AI'}
              </Button>

              {editingHighlight.ai_summary && (
                <div className="rounded-lg border border-border bg-card px-3 py-2 text-[13px]">
                  <div className="mb-1 text-[11px] uppercase tracking-wider text-muted-foreground">
                    AI paraphrase
                  </div>
                  {editingHighlight.ai_summary}
                </div>
              )}

              <textarea
                value={editNoteDraft}
                onChange={(e) => onEditNoteChange(e.target.value)}
                placeholder="Your note"
                data-testid="mreader-edit-note-textarea"
                className="min-h-[120px] rounded-lg border border-border bg-card px-3 py-2 text-[14px] focus:outline-none focus:ring-2 focus:ring-primary/40"
              />

              <Button
                type="button"
                variant="ghost"
                size="sm"
                disabled={deleteMutation.isPending}
                onClick={() => setDeleteConfirmOpen(true)}
                data-testid="mreader-edit-delete"
                className="text-rose-700"
              >
                {deleteMutation.isPending ? 'Deleting…' : 'Delete highlight'}
              </Button>
            </div>
          )}
        </BottomSheet>

        <ConfirmSheet
          open={deleteConfirmOpen && !!editingHighlight}
          title="Delete highlight"
          message="This will remove the highlight, its note and any AI paraphrase. You can't undo this."
          confirmLabel="Delete"
          destructive
          onConfirm={() => {
            if (editingHighlight) deleteMutation.mutate(editingHighlight.id)
            setDeleteConfirmOpen(false)
          }}
          onCancel={() => setDeleteConfirmOpen(false)}
        />

        {/* D3.6 — Overflow menu */}
        <BottomSheet
          open={overflowOpen}
          onClose={() => setOverflowOpen(false)}
          title="Reader options"
          snapPoints={['45%']}
        >
          <div
            data-testid="mreader-overflow-sheet"
            className="flex flex-col gap-2 pb-2"
          >
            {hasPdf && (
              <button
                type="button"
                data-testid="mreader-toggle-mode"
                onClick={() => {
                  setReadingMode((m) => (m === 'pdf' ? 'text' : 'pdf'))
                  setOverflowOpen(false)
                }}
                className="rounded-lg border border-border bg-card px-3 py-3 text-left text-[14px] hover:bg-muted"
              >
                {readingMode === 'pdf'
                  ? 'Switch to reading mode (extracted text)'
                  : 'Switch to PDF mode'}
              </button>
            )}
            {hasPdf && readingMode === 'pdf' && (
              <button
                type="button"
                data-testid="mreader-toggle-perf"
                onClick={() => {
                  setPerformanceMode((v) => !v)
                  setOverflowOpen(false)
                }}
                className="rounded-lg border border-border bg-card px-3 py-3 text-left text-[14px] hover:bg-muted"
              >
                Performance mode: {performanceMode ? 'on' : 'off'}
              </button>
            )}
            {article.file_url && (
              <a
                data-testid="mreader-open-original"
                href={absoluteFileUrl(article.file_url) ?? article.file_url}
                target="_blank"
                rel="noopener noreferrer"
                onClick={() => setOverflowOpen(false)}
                className="rounded-lg border border-border bg-card px-3 py-3 text-[14px] hover:bg-muted"
              >
                View original PDF
              </a>
            )}
          </div>
        </BottomSheet>
      </div>
    )
  },
)

export default MobileReader

// ---------------------------------------------------------------------------
// Anchored handles helper — keeps the maths out of the main component.
// ---------------------------------------------------------------------------

function SelectionHandlesAnchored({
  range,
  words,
  containerRef,
  onMove,
}: {
  range: Range
  words: WordToken[]
  containerRef: React.RefObject<HTMLDivElement | null>
  onMove: (side: HandleSide, x: number, y: number) => void
}) {
  const [positions, setPositions] = useState<{
    anchor: { x: number; y: number; lineHeight: number } | null
    focus: { x: number; y: number; lineHeight: number } | null
  }>({ anchor: null, focus: null })

  useEffect(() => {
    if (!range || !containerRef.current) {
      setPositions({ anchor: null, focus: null })
      return
    }
    const container = containerRef.current
    const startEl = container.querySelector<HTMLElement>(
      `[data-word-idx="${range.start}"]`,
    )
    const endEl = container.querySelector<HTMLElement>(
      `[data-word-idx="${range.end}"]`,
    )
    if (!startEl || !endEl) return
    const cRect = container.getBoundingClientRect()
    const sRect = startEl.getBoundingClientRect()
    const eRect = endEl.getBoundingClientRect()
    setPositions({
      anchor: {
        x: sRect.left - cRect.left + container.scrollLeft,
        y: sRect.top - cRect.top + container.scrollTop,
        lineHeight: sRect.height,
      },
      focus: {
        x: eRect.right - cRect.left + container.scrollLeft,
        y: eRect.top - cRect.top + container.scrollTop,
        lineHeight: eRect.height,
      },
    })
  }, [range, words, containerRef])

  return <SelectionHandles anchor={positions.anchor} focus={positions.focus} onMove={onMove} />
}
