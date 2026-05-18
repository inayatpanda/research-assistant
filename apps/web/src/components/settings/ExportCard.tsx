import { useQuery } from '@tanstack/react-query'
import { Download, FileJson, FileText, Loader2 } from 'lucide-react'
import { useState } from 'react'
import { toast } from 'sonner'

import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { exportApi, projectsApi } from '@/lib/api'

type Format = 'docx' | 'pdf' | 'bundle'

const FORMATS: Array<{ id: Format; label: string; icon: typeof Download; description: string }> = [
  { id: 'docx', label: 'DOCX', icon: FileText, description: 'Word document with formatted sections + bibliography.' },
  { id: 'pdf', label: 'PDF', icon: FileText, description: 'Print-ready PDF rendered server-side.' },
  { id: 'bundle', label: 'JSON Bundle', icon: FileJson, description: 'Complete project snapshot for backup or import.' },
]

export function ExportCard({ projectId }: { projectId: string }) {
  const [busy, setBusy] = useState<Format | null>(null)
  const { data: project } = useQuery({
    queryKey: ['project', projectId],
    queryFn: () => projectsApi.get(projectId),
  })

  const slug =
    (project?.title ?? 'manuscript')
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, '-')
      .replace(/(^-|-$)+/g, '')
      .slice(0, 40) || 'manuscript'

  const trigger = async (kind: Format) => {
    setBusy(kind)
    try {
      const filename =
        kind === 'docx'
          ? await exportApi.downloadDocx(projectId, slug)
          : kind === 'pdf'
            ? await exportApi.downloadPdf(projectId, slug)
            : await exportApi.downloadBundle(projectId, slug)
      toast.success(`Downloaded ${filename}`)
    } catch (e) {
      const msg = e instanceof Error ? e.message : 'Export failed'
      toast.error(msg)
    } finally {
      setBusy(null)
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-[15px]">Export project</CardTitle>
      </CardHeader>
      <CardContent className="space-y-2">
        {FORMATS.map((f) => {
          const Icon = f.icon
          const isBusy = busy === f.id
          return (
            <div
              key={f.id}
              className="flex items-center justify-between gap-3 border-b last:border-b-0 border-border py-3"
            >
              <div className="flex items-start gap-3 min-w-0">
                <Icon className="h-4 w-4 mt-[2px] text-muted-foreground shrink-0" />
                <div className="min-w-0">
                  <div className="text-[13px] font-medium">{f.label}</div>
                  <div className="text-[12px] text-muted-foreground">{f.description}</div>
                </div>
              </div>
              <Button
                size="sm"
                variant="outline"
                onClick={() => trigger(f.id)}
                disabled={busy != null}
                className="h-8 text-[12px] min-w-[88px] justify-center"
              >
                {isBusy ? (
                  <>
                    <Loader2 className="h-3 w-3 mr-1 animate-spin" />
                    Working…
                  </>
                ) : (
                  <>
                    <Download className="h-3 w-3 mr-1" />
                    Download
                  </>
                )}
              </Button>
            </div>
          )
        })}
      </CardContent>
    </Card>
  )
}
