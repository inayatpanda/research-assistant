import type { Highlight } from '@/lib/api'

// Real implementation lands in P3-T13. This stub keeps PdfViewer typechecking
// while the overlay + selection capture land.
export function HighlightNotePopover({
  articleId,
  highlight,
  onClose,
}: {
  articleId: string
  highlight: Highlight | null
  onClose: () => void
}) {
  void articleId
  void highlight
  void onClose
  return null
}
