import { useMutation, useQueryClient } from '@tanstack/react-query'
import { AnimatePresence, motion } from 'framer-motion'
import { CheckCircle2, FileText, Loader2, UploadCloud, XCircle } from 'lucide-react'
import { useCallback, useState } from 'react'
import { useDropzone } from 'react-dropzone'
import { toast } from 'sonner'

import { articlesApi, type UploadResponse } from '@/lib/api'
import { cn } from '@/lib/utils'

type RowState =
  | { kind: 'uploading'; file: File }
  | { kind: 'success'; file: File; response: UploadResponse }
  | { kind: 'error'; file: File; message: string }

type Row = { id: string; state: RowState }

export function UploadZone({
  projectId,
  onUploaded,
}: {
  projectId: string
  onUploaded?: (response: UploadResponse) => void
}) {
  const [rows, setRows] = useState<Row[]>([])
  const qc = useQueryClient()

  const upload = useMutation({
    mutationFn: ({ file }: { rowId: string; file: File }) =>
      articlesApi.upload(projectId, file),
  })

  const onDrop = useCallback(
    async (accepted: File[]) => {
      // Process sequentially to avoid hitting AI rate limits with parallel uploads
      for (const file of accepted) {
        const rowId = crypto.randomUUID()
        setRows((r) => [...r, { id: rowId, state: { kind: 'uploading', file } }])
        try {
          const resp = await upload.mutateAsync({ rowId, file })
          setRows((r) =>
            r.map((row) =>
              row.id === rowId
                ? { id: rowId, state: { kind: 'success', file, response: resp } }
                : row,
            ),
          )
          qc.invalidateQueries({ queryKey: ['articles', projectId] })
          onUploaded?.(resp)
        } catch (e) {
          const msg = e instanceof Error ? e.message : 'Upload failed'
          setRows((r) =>
            r.map((row) =>
              row.id === rowId
                ? { id: rowId, state: { kind: 'error', file, message: msg } }
                : row,
            ),
          )
          toast.error(msg)
        }
      }
    },
    [upload, qc, projectId, onUploaded],
  )

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
    },
    multiple: true,
    disabled: !projectId,
  })

  return (
    <div className="space-y-3">
      <motion.div
        {...getRootProps()}
        whileHover={{ scale: 1.005 }}
        className={cn(
          'relative rounded-lg border-2 border-dashed p-10 text-center cursor-pointer transition-colors',
          isDragActive
            ? 'border-accent bg-accent/5'
            : 'border-border bg-white/40 hover:border-accent/40',
        )}
      >
        <input {...getInputProps()} />
        <motion.div
          animate={isDragActive ? { scale: 1.05 } : { scale: 1 }}
          className="flex flex-col items-center gap-3 text-muted-foreground"
        >
          <UploadCloud className="h-7 w-7" />
          <div className="text-[14px]">
            <span className="font-medium text-foreground">
              {isDragActive ? 'Drop to upload' : 'Drop PDFs or Word docs here'}
            </span>
            <span className="text-muted-foreground">, or click to choose</span>
          </div>
          <div className="text-[12px] text-muted-foreground">
            Max 50 MB · PDF (.pdf) and Word (.docx)
          </div>
        </motion.div>
      </motion.div>

      <AnimatePresence initial={false}>
        {rows.map((row) => (
          <motion.div
            key={row.id}
            initial={{ opacity: 0, y: 4 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            className="flex items-center gap-3 rounded-md border border-border bg-white px-4 py-3 text-[13px]"
          >
            <FileText className="h-4 w-4 text-muted-foreground shrink-0" />
            <div className="flex-1 min-w-0">
              <div className="truncate font-medium">{row.state.file.name}</div>
              {row.state.kind === 'success' && row.state.response.duplicate_of && (
                <div className="text-amber-600 text-[12px] mt-0.5">
                  Possible duplicate of:{' '}
                  <span className="font-medium">{row.state.response.duplicate_of.title}</span>
                </div>
              )}
              {row.state.kind === 'success' && row.state.response.extraction_error && (
                <div className="text-rose-600 text-[12px] mt-0.5">
                  AI extraction warning: {row.state.response.extraction_error}
                </div>
              )}
              {row.state.kind === 'error' && (
                <div className="text-rose-600 text-[12px] mt-0.5">{row.state.message}</div>
              )}
            </div>
            {row.state.kind === 'uploading' && (
              <Loader2 className="h-4 w-4 text-muted-foreground animate-spin shrink-0" />
            )}
            {row.state.kind === 'success' && (
              <CheckCircle2 className="h-4 w-4 text-emerald-600 shrink-0" />
            )}
            {row.state.kind === 'error' && (
              <XCircle className="h-4 w-4 text-rose-600 shrink-0" />
            )}
          </motion.div>
        ))}
      </AnimatePresence>
    </div>
  )
}
