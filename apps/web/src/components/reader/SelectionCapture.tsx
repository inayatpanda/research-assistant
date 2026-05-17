import { useCallback, useEffect, useState } from 'react'
import { toast } from 'sonner'

import { useCreateHighlight } from '@/hooks/useHighlights'
import type { Highlight, HighlightColour } from '@/lib/api'
import { pixelRectToPct, rectsFromSelectionInPage } from '@/lib/pdfCoords'
import { SECTION_FOR_COLOUR, useReader } from '@/lib/readerStore'

import { SelectionToolbar } from './SelectionToolbar'

/**
 * Owns text-selection-to-highlight flows. Three creation paths converge on
 * `createHighlight(colour)`:
 *
 * 1. **Pre-pick mode**: user picks a colour first, then selects text → on mouseup,
 *    create highlight immediately.
 * 2. **Floating toolbar**: user selects text WITHOUT a pre-picked colour → a small
 *    4-colour toolbar floats near the selection; click a colour → highlight.
 * 3. **Keyboard**: Cmd/Ctrl+1..4 highlights the current selection in that colour.
 */
export function SelectionCapture({
  articleId,
  onCreated,
}: {
  articleId: string
  onCreated?: (highlight: Highlight, anchorRect: DOMRect) => void
}) {
  const create = useCreateHighlight(articleId)
  const activeColour = useReader((s) => s.activeColour)
  const [toolbarRect, setToolbarRect] = useState<DOMRect | null>(null)

  /** Read the live selection and create a highlight. Used by all three paths. */
  const createHighlight = useCallback(
    (colour: HighlightColour) => {
      const sel = window.getSelection()
      if (!sel || sel.isCollapsed || sel.rangeCount === 0) return

      const range = sel.getRangeAt(0)
      const text = range.toString().trim()
      if (!text) return

      const node =
        range.commonAncestorContainer.nodeType === Node.ELEMENT_NODE
          ? (range.commonAncestorContainer as Element)
          : range.commonAncestorContainer.parentElement
      const pageEl = node?.closest('[data-page-number]') as HTMLElement | null
      if (!pageEl) return

      const pageNumber = Number(pageEl.getAttribute('data-page-number') ?? '0')
      if (!pageNumber) return

      const pageBox = pageEl.getBoundingClientRect()
      if (pageBox.width === 0 || pageBox.height === 0) return

      const pixelRects = rectsFromSelectionInPage(range, pageEl)
      if (pixelRects.length === 0) return

      const firstViewportRect = range.getClientRects()[0]
      const rects = pixelRects.map((r) => pixelRectToPct(r, pageBox.width, pageBox.height))

      create.mutate(
        {
          page_number: pageNumber,
          selected_text: text,
          colour,
          section: SECTION_FOR_COLOUR[colour],
          bounding_coords: { rects },
        },
        {
          onSuccess: (highlight) => {
            sel.removeAllRanges()
            setToolbarRect(null)
            if (firstViewportRect && onCreated) onCreated(highlight, firstViewportRect)
          },
          onError: (e: Error) => toast.error(e.message),
        },
      )
    },
    [create, onCreated],
  )

  // PATH 1 & 2: mouseup commits the selection.
  const handleMouseUp = useCallback(() => {
    const sel = window.getSelection()
    if (!sel || sel.isCollapsed || sel.rangeCount === 0) {
      setToolbarRect(null)
      return
    }
    const range = sel.getRangeAt(0)
    const text = range.toString().trim()
    if (!text) {
      setToolbarRect(null)
      return
    }

    const node =
      range.commonAncestorContainer.nodeType === Node.ELEMENT_NODE
        ? (range.commonAncestorContainer as Element)
        : range.commonAncestorContainer.parentElement
    const pageEl = node?.closest('[data-page-number]') as HTMLElement | null
    if (!pageEl) {
      setToolbarRect(null)
      return
    }

    if (activeColour) {
      createHighlight(activeColour)
      return
    }

    // No pre-picked colour — show the floating toolbar near the end of the selection
    const rects = Array.from(range.getClientRects())
    const last = rects[rects.length - 1]
    if (!last) return
    setToolbarRect(last)
  }, [activeColour, createHighlight])

  useEffect(() => {
    document.addEventListener('mouseup', handleMouseUp)
    return () => document.removeEventListener('mouseup', handleMouseUp)
  }, [handleMouseUp])

  // PATH 3: Cmd/Ctrl + 1..4 highlights the current selection
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (!(e.metaKey || e.ctrlKey)) return
      const map: Record<string, HighlightColour> = {
        '1': 'intro',
        '2': 'method',
        '3': 'results',
        '4': 'discussion',
      }
      const c = map[e.key]
      if (!c) return
      const sel = window.getSelection()
      if (!sel || sel.isCollapsed) return
      e.preventDefault()
      createHighlight(c)
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [createHighlight])

  // Dismiss floating toolbar on Escape or when selection collapses
  useEffect(() => {
    function onSelChange() {
      const sel = window.getSelection()
      if (!sel || sel.isCollapsed) setToolbarRect(null)
    }
    function onKey(e: KeyboardEvent) {
      if (e.key === 'Escape') setToolbarRect(null)
    }
    document.addEventListener('selectionchange', onSelChange)
    window.addEventListener('keydown', onKey)
    return () => {
      document.removeEventListener('selectionchange', onSelChange)
      window.removeEventListener('keydown', onKey)
    }
  }, [])

  if (!toolbarRect || activeColour) return null
  return (
    <SelectionToolbar
      anchorRect={toolbarRect}
      onPick={(c) => createHighlight(c)}
      onDismiss={() => setToolbarRect(null)}
    />
  )
}
