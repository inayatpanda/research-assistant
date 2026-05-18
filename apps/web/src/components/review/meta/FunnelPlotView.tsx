import { useState } from 'react'

import { Dialog, DialogContent, DialogTrigger } from '@/components/ui/dialog'
import { metaAnalysisApi, type MetaAnalysisRead } from '@/lib/api'

export function FunnelPlotView({
  projectId,
  meta,
}: {
  projectId: string
  meta: MetaAnalysisRead
}) {
  const [open, setOpen] = useState(false)
  const src = `${metaAnalysisApi.funnelUrl(projectId, meta.id)}?t=${encodeURIComponent(meta.updated_at)}`

  if (meta.status !== 'completed') {
    return (
      <div className="rounded-md border border-dashed border-border bg-white p-6 text-center text-[12px] text-muted-foreground">
        Run the analysis to render the funnel plot.
      </div>
    )
  }

  return (
    <div className="space-y-2">
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogTrigger asChild>
          <button
            className="rounded-md border border-border bg-white p-2 hover:border-accent transition-colors"
            aria-label="Zoom funnel plot"
          >
            <img src={src} alt="Funnel plot" className="max-w-full" />
          </button>
        </DialogTrigger>
        <DialogContent className="max-w-3xl">
          <img src={src} alt="Funnel plot (enlarged)" className="w-full" />
        </DialogContent>
      </Dialog>
      <div className="flex justify-end">
        <a
          href={src}
          download={`funnel-${meta.id}.png`}
          className="text-[11px] underline text-muted-foreground hover:text-foreground"
        >
          Download PNG
        </a>
      </div>
    </div>
  )
}
