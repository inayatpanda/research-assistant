import { useMutation, useQueryClient } from '@tanstack/react-query'
import { FileUp, Loader2 } from 'lucide-react'
import { useCallback } from 'react'
import { useDropzone, type FileRejection } from 'react-dropzone'
import { useNavigate } from 'react-router-dom'
import { toast } from 'sonner'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { exportApi, IMPORT_SIZE_CAP_BYTES } from '@/lib/api'
import { useLastViewedProject } from '@/lib/projectContext'
import { cn } from '@/lib/utils'

const MAX_MB = Math.round(IMPORT_SIZE_CAP_BYTES / (1024 * 1024))

function summariseCounts(counts: Record<string, number>): string {
  const pieces: string[] = []
  if (counts.articles) pieces.push(`${counts.articles} articles`)
  if (counts.highlights) pieces.push(`${counts.highlights} highlights`)
  if (counts.manuscript_sections) pieces.push(`${counts.manuscript_sections} sections`)
  if (counts.datasets) pieces.push(`${counts.datasets} datasets`)
  if (counts.analyses) pieces.push(`${counts.analyses} analyses`)
  return pieces.join(' · ')
}

export function ImportDropzone() {
  const navigate = useNavigate()
  const qc = useQueryClient()
  const setLastViewed = useLastViewedProject((s) => s.set)

  const mutation = useMutation({
    mutationFn: (file: File) => exportApi.importBundle(file),
    onSuccess: (data) => {
      qc.invalidateQueries({ queryKey: ['projects'] })
      // MP12.5: keep the import-then-default behaviour by stashing the
      // new project as the user's "last viewed", and navigate using the
      // URL-scoped route.
      setLastViewed(data.project_id)
      const summary = summariseCounts(data.counts)
      toast.success(`Imported project · ${summary || 'no items'}`, {
        action: {
          label: 'Open',
          onClick: () =>
            navigate(`/projects/${data.project_id}/manuscript`),
        },
      })
    },
    onError: (e: Error) => toast.error(e.message),
  })

  const onDrop = useCallback(
    (accepted: File[], rejected: FileRejection[]) => {
      if (rejected.length > 0) {
        const first = rejected[0]
        const msg = first.errors[0]?.message ?? 'File rejected'
        toast.error(msg)
        return
      }
      const file = accepted[0]
      if (!file) return
      if (file.size > IMPORT_SIZE_CAP_BYTES) {
        toast.error(`File exceeds ${MAX_MB} MiB limit`)
        return
      }
      mutation.mutate(file)
    },
    [mutation],
  )

  const { getRootProps, getInputProps, isDragActive, isDragReject } = useDropzone({
    onDrop,
    multiple: false,
    accept: { 'application/json': ['.json'] },
    maxSize: IMPORT_SIZE_CAP_BYTES,
    disabled: mutation.isPending,
  })

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-[15px]">Import project bundle</CardTitle>
      </CardHeader>
      <CardContent>
        <div
          {...getRootProps()}
          className={cn(
            'flex flex-col items-center justify-center gap-2 rounded-md border-2 border-dashed p-8 text-center cursor-pointer transition-colors',
            isDragActive
              ? 'border-accent bg-accent/5'
              : 'border-border bg-zinc-50 hover:border-accent/40',
            isDragReject && 'border-rose-500 bg-rose-50',
            mutation.isPending && 'cursor-not-allowed opacity-60',
          )}
        >
          <input {...getInputProps()} />
          {mutation.isPending ? (
            <>
              <Loader2 className="h-6 w-6 text-muted-foreground animate-spin" />
              <div className="text-[13px] font-medium">Importing…</div>
            </>
          ) : (
            <>
              <FileUp className="h-6 w-6 text-muted-foreground" />
              <div className="text-[13px] font-medium">
                {isDragActive ? 'Drop the JSON bundle' : 'Drag a JSON bundle here or click to browse'}
              </div>
              <div className="text-[11px] text-muted-foreground">
                Up to {MAX_MB} MiB · creates a new project on import
              </div>
            </>
          )}
        </div>
      </CardContent>
    </Card>
  )
}
