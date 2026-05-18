import { Download } from 'lucide-react'
import { useState } from 'react'

import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'

export type ChartImageProps = {
  chart: { format: 'png'; data_uri: string; byte_size: number } | null
  alt: string
  downloadName?: string
}

export function ChartImage({ chart, alt, downloadName }: ChartImageProps) {
  const [open, setOpen] = useState(false)
  if (!chart) return null
  const fileName = `${downloadName ?? 'chart'}.png`
  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="block w-full group rounded-md overflow-hidden border border-border bg-white"
        aria-label={`View ${alt} full size`}
      >
        <img
          src={chart.data_uri}
          alt={alt}
          className="w-full h-auto group-hover:opacity-95 transition-opacity"
          loading="lazy"
        />
      </button>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="max-w-4xl">
          <DialogHeader>
            <DialogTitle>{alt}</DialogTitle>
          </DialogHeader>
          <img src={chart.data_uri} alt={alt} className="w-full h-auto" />
          <DialogFooter>
            <a
              href={chart.data_uri}
              download={fileName}
              className="inline-flex items-center gap-2 text-[13px] underline-offset-2 hover:underline"
            >
              <Download className="h-3.5 w-3.5" /> Download PNG
            </a>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  )
}
