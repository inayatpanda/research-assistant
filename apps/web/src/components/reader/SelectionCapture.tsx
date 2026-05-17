import { useCallback, useEffect } from 'react'
import { toast } from 'sonner'

import { useCreateHighlight } from '@/hooks/useHighlights'
import type { HighlightCreate } from '@/lib/api'
import { pixelRectToPct, rectsFromSelectionInPage } from '@/lib/pdfCoords'
import { SECTION_FOR_COLOUR, useReader } from '@/lib/readerStore'

/**
 * Listens for text selections inside a PDF page container.
 * When the user releases the mouse with a non-empty selection AND an active colour is set,
 * convert the selection into a Highlight payload and persist.
 */
export function SelectionCapture({
  articleId,
  currentPage,
}: {
  articleId: string
  currentPage: number
}) {
  const create = useCreateHighlight(articleId)
  const activeColour = useReader((s) => s.activeColour)

  const handleMouseUp = useCallback(() => {
    if (!activeColour) return  // no colour selected — let normal text selection live

    const sel = window.getSelection()
    if (!sel || sel.isCollapsed || sel.rangeCount === 0) return

    const range = sel.getRangeAt(0)
    const text = range.toString().trim()
    if (text.length === 0) return

    // Find the page DOM element via the data attribute react-pdf injects
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

    const rects = pixelRects.map((r) => pixelRectToPct(r, pageBox.width, pageBox.height))

    const payload: HighlightCreate = {
      page_number: pageNumber,
      selected_text: text,
      colour: activeColour,
      section: SECTION_FOR_COLOUR[activeColour],
      bounding_coords: { rects },
    }

    create.mutate(payload, {
      onSuccess: () => {
        sel.removeAllRanges()
      },
      onError: (e: Error) => toast.error(e.message),
    })
  }, [activeColour, create])

  useEffect(() => {
    document.addEventListener('mouseup', handleMouseUp)
    return () => document.removeEventListener('mouseup', handleMouseUp)
  }, [handleMouseUp])

  // unused but kept in signature in case we add page-level scoping later
  void currentPage
  return null
}
