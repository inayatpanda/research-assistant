import { ChevronLeft, ChevronRight, ZoomIn, ZoomOut } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { useReader } from '@/lib/readerStore'

import { ColorPicker } from './ColorPicker'

export function PdfToolbar({ numPages }: { numPages: number }) {
  const page = useReader((s) => s.currentPage)
  const setPage = useReader((s) => s.setCurrentPage)
  const scale = useReader((s) => s.scale)
  const setScale = useReader((s) => s.setScale)

  return (
    <div className="h-12 px-4 border-b border-border bg-white flex items-center gap-4">
      <div className="flex items-center gap-1">
        <Button
          variant="ghost"
          size="icon"
          className="h-8 w-8"
          onClick={() => setPage(Math.max(1, page - 1))}
          disabled={page <= 1}
          aria-label="Previous page"
        >
          <ChevronLeft className="h-4 w-4" />
        </Button>
        <span className="text-[12px] text-muted-foreground tabular-nums min-w-[80px] text-center">
          {numPages > 0 ? `${page} / ${numPages}` : '— / —'}
        </span>
        <Button
          variant="ghost"
          size="icon"
          className="h-8 w-8"
          onClick={() => setPage(Math.min(numPages, page + 1))}
          disabled={numPages > 0 && page >= numPages}
          aria-label="Next page"
        >
          <ChevronRight className="h-4 w-4" />
        </Button>
      </div>

      <div className="h-5 w-px bg-border" />

      <div className="flex items-center gap-1">
        <Button
          variant="ghost"
          size="icon"
          className="h-8 w-8"
          onClick={() => setScale(scale - 0.1)}
          aria-label="Zoom out"
        >
          <ZoomOut className="h-4 w-4" />
        </Button>
        <span className="text-[12px] text-muted-foreground tabular-nums min-w-[44px] text-center">
          {Math.round(scale * 100)}%
        </span>
        <Button
          variant="ghost"
          size="icon"
          className="h-8 w-8"
          onClick={() => setScale(scale + 0.1)}
          aria-label="Zoom in"
        >
          <ZoomIn className="h-4 w-4" />
        </Button>
      </div>

      <div className="h-5 w-px bg-border" />

      <ColorPicker />
    </div>
  )
}
