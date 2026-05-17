import { useMemo, useState } from 'react'
import { Document, Page } from 'react-pdf'
import 'react-pdf/dist/Page/AnnotationLayer.css'
import 'react-pdf/dist/Page/TextLayer.css'

import { useHighlights } from '@/hooks/useHighlights'
import { usePdfDocument } from '@/hooks/usePdfDocument'
import type { Highlight } from '@/lib/api'
import { useReader } from '@/lib/readerStore'

import { HighlightNotePopover } from './HighlightNotePopover'
import { HighlightOverlay } from './HighlightOverlay'
import { SelectionCapture } from './SelectionCapture'

type PageSize = { width: number; height: number }

export function PdfViewer({
  articleId,
  onNumPages,
}: {
  articleId: string
  onNumPages: (n: number) => void
}) {
  const { data: pdfData, isLoading, isError, error } = usePdfDocument(articleId)
  const { data: highlights = [] } = useHighlights(articleId)
  const currentPage = useReader((s) => s.currentPage)
  const scale = useReader((s) => s.scale)
  const [pageSize, setPageSize] = useState<PageSize>({ width: 0, height: 0 })
  const [openHighlight, setOpenHighlight] = useState<Highlight | null>(null)

  const pageHighlights = useMemo(
    () => highlights.filter((h) => h.page_number === currentPage),
    [highlights, currentPage],
  )

  // Memoise the file option so react-pdf doesn't re-load on every render
  const file = useMemo(
    () => (pdfData ? { data: pdfData.data } : undefined),
    [pdfData],
  )

  if (isLoading) {
    return (
      <div className="flex-1 flex items-center justify-center text-[13px] text-muted-foreground">
        Loading PDF…
      </div>
    )
  }
  if (isError || !pdfData) {
    return (
      <div className="flex-1 flex items-center justify-center px-8 text-center">
        <div className="text-[13px] text-rose-700 max-w-md">
          Couldn't load the PDF: {error instanceof Error ? error.message : 'unknown error'}
        </div>
      </div>
    )
  }

  return (
    <div className="flex-1 overflow-auto bg-zinc-100">
      <div className="py-8 flex justify-center">
        <Document
          file={file}
          onLoadSuccess={(doc) => onNumPages(doc.numPages)}
          loading={<div className="text-[13px] text-muted-foreground">Loading document…</div>}
          error={<div className="text-[13px] text-rose-600">Error loading document</div>}
        >
          <div className="relative inline-block shadow-md">
            <Page
              pageNumber={currentPage}
              scale={scale}
              renderTextLayer
              renderAnnotationLayer={false}
              onLoadSuccess={(p) => setPageSize({ width: p.width, height: p.height })}
            />
            <HighlightOverlay
              highlights={pageHighlights}
              pageWidth={pageSize.width}
              pageHeight={pageSize.height}
              onClickHighlight={setOpenHighlight}
            />
          </div>
        </Document>
      </div>
      <SelectionCapture articleId={articleId} currentPage={currentPage} />
      <HighlightNotePopover
        articleId={articleId}
        highlight={openHighlight}
        onClose={() => setOpenHighlight(null)}
      />
    </div>
  )
}
