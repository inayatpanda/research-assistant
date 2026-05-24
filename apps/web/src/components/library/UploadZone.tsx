import { useMutation, useQueryClient } from '@tanstack/react-query'
import { AnimatePresence, motion } from 'framer-motion'
import {
  CheckCircle2,
  FileText,
  Loader2,
  Trash2,
  UploadCloud,
  XCircle,
} from 'lucide-react'
import { useCallback, useMemo, useRef, useState } from 'react'
import { useDropzone } from 'react-dropzone'
import { toast } from 'sonner'

import { Button } from '@/components/ui/button'
import { articlesApi, type UploadResponse } from '@/lib/api'
import { cn } from '@/lib/utils'

// F2 — Bulk upload constraints. Browsers handle ~4 concurrent multipart
// uploads well; more than that and we either saturate the uplink or
// hammer the API. 50 files per batch matches the task spec — beyond that
// the user is probably better served by a folder-watch workflow we don't
// yet ship.
const MAX_BATCH = 50
const CONCURRENCY = 4

type RowStatus = 'pending' | 'uploading' | 'done' | 'failed'

type Row = {
  id: string
  file: File
  status: RowStatus
  response?: UploadResponse
  error?: string
}

export function UploadZone({
  projectId,
  onUploaded,
}: {
  projectId: string
  onUploaded?: (response: UploadResponse) => void
}) {
  // Two slots: ``staged`` is the user's cart of files awaiting "Upload".
  // ``log`` is the past run history (so users see "5 uploaded, 2 failed"
  // even after they click Upload again). Keeping them separate prevents
  // the UploadZone from looking like it's spawning ghost rows mid-run.
  const [staged, setStaged] = useState<Row[]>([])
  const [log, setLog] = useState<Row[]>([])
  const [busy, setBusy] = useState(false)
  const qc = useQueryClient()
  // Stable ref into log so the concurrency loop can mutate the most
  // recent state without re-deriving the closure on every keystroke.
  const logRef = useRef<Row[]>(log)
  logRef.current = log

  const upload = useMutation({
    mutationFn: ({ file }: { rowId: string; file: File }) =>
      articlesApi.upload(projectId, file),
  })

  const onDrop = useCallback((accepted: File[]) => {
    // Enforce the 50-file cap up-front so the user sees it before they
    // click "Upload". Drop excess files with a clear toast — never
    // silently discard.
    if (accepted.length > MAX_BATCH) {
      toast.message(
        `Selected ${accepted.length} — only the first ${MAX_BATCH} will be uploaded.`,
      )
      accepted = accepted.slice(0, MAX_BATCH)
    }
    const newRows: Row[] = accepted.map((file) => ({
      id: crypto.randomUUID(),
      file,
      status: 'pending',
    }))
    setStaged((rows) => {
      const combined = [...rows, ...newRows]
      if (combined.length > MAX_BATCH) {
        toast.message(`Batch capped at ${MAX_BATCH} files.`)
        return combined.slice(0, MAX_BATCH)
      }
      return combined
    })
  }, [])

  const removeStaged = useCallback((id: string) => {
    setStaged((rows) => rows.filter((r) => r.id !== id))
  }, [])

  const clearLog = useCallback(() => setLog([]), [])

  const startUpload = useCallback(async () => {
    if (busy || staged.length === 0) return
    setBusy(true)
    const queue = staged
    // Hand the staged rows straight into the log so progress is visible
    // immediately. ``staged`` clears so the user can start picking the
    // next batch while this one finishes.
    setLog((prev) => [...prev, ...queue.map((r) => ({ ...r }))])
    setStaged([])

    const updateRow = (id: string, patch: Partial<Row>) => {
      setLog((rows) => rows.map((r) => (r.id === id ? { ...r, ...patch } : r)))
    }

    // Concurrency-N promise pool. Each worker drains the queue.
    let cursor = 0
    const workers = Array.from({ length: Math.min(CONCURRENCY, queue.length) }, async () => {
      while (cursor < queue.length) {
        const row = queue[cursor++]
        if (!row) break
        updateRow(row.id, { status: 'uploading' })
        try {
          const resp = await upload.mutateAsync({ rowId: row.id, file: row.file })
          updateRow(row.id, { status: 'done', response: resp })
          onUploaded?.(resp)
        } catch (e) {
          const msg = e instanceof Error ? e.message : 'Upload failed'
          updateRow(row.id, { status: 'failed', error: msg })
        }
      }
    })

    await Promise.all(workers)
    qc.invalidateQueries({ queryKey: ['articles', projectId] })
    setBusy(false)
  }, [busy, staged, upload, qc, projectId, onUploaded])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
    },
    multiple: true,
    disabled: !projectId || busy,
  })

  const stats = useMemo(() => {
    const total = log.length
    const done = log.filter((r) => r.status === 'done').length
    const failed = log.filter((r) => r.status === 'failed').length
    const inflight = log.filter((r) => r.status === 'uploading').length
    return { total, done, failed, inflight }
  }, [log])

  const showSummary = !busy && log.length > 0 && stats.inflight === 0

  return (
    <div className="space-y-3" data-testid="library-upload-zone">
      <motion.div
        {...getRootProps()}
        whileHover={{ scale: 1.005 }}
        className={cn(
          'relative rounded-lg border-2 border-dashed p-10 text-center cursor-pointer transition-colors',
          isDragActive
            ? 'border-accent bg-accent/5'
            : 'border-border bg-white/40 hover:border-accent/40',
          busy && 'opacity-60 cursor-wait',
        )}
      >
        <input
          {...getInputProps({
            onClick: (e) => {
              ;(e.target as HTMLInputElement).value = ''
            },
          })}
        />
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
            Max 50 MB per file · up to {MAX_BATCH} files per batch
          </div>
        </motion.div>
      </motion.div>

      {/* Staged queue — user can prune before kicking off the batch. */}
      {staged.length > 0 && (
        <div
          className="rounded-md border border-border bg-white p-3 space-y-2"
          data-testid="library-upload-staged"
        >
          <div className="flex items-center justify-between text-[12px]">
            <span className="font-medium">
              {staged.length} file{staged.length === 1 ? '' : 's'} ready
            </span>
            <Button
              size="sm"
              onClick={startUpload}
              disabled={busy}
              data-testid="library-upload-start"
            >
              {busy ? 'Uploading…' : `Upload ${staged.length}`}
            </Button>
          </div>
          <ul className="divide-y divide-border">
            {staged.map((row) => (
              <li key={row.id} className="flex items-center gap-2 py-1.5 text-[13px]">
                <FileText className="h-4 w-4 text-muted-foreground shrink-0" />
                <span className="flex-1 truncate">{row.file.name}</span>
                <button
                  type="button"
                  className="text-muted-foreground hover:text-rose-600"
                  onClick={() => removeStaged(row.id)}
                  aria-label={`Remove ${row.file.name}`}
                  data-testid="library-upload-remove"
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Progress + per-file log */}
      {log.length > 0 && (
        <div className="space-y-2">
          <div
            className="flex items-center justify-between text-[12px] text-muted-foreground"
            data-testid="library-upload-progress"
          >
            <span>
              Uploaded {stats.done} of {stats.total}
              {stats.failed > 0 && ` · ${stats.failed} failed`}
            </span>
            {showSummary && (
              <button
                type="button"
                className="hover:text-foreground underline-offset-2 hover:underline"
                onClick={clearLog}
              >
                Clear
              </button>
            )}
          </div>
          <AnimatePresence initial={false}>
            {log.map((row) => (
              <motion.div
                key={row.id}
                initial={{ opacity: 0, y: 4 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0 }}
                className="flex items-center gap-3 rounded-md border border-border bg-white px-4 py-3 text-[13px]"
                data-testid="library-upload-row"
                data-status={row.status}
              >
                <FileText className="h-4 w-4 text-muted-foreground shrink-0" />
                <div className="flex-1 min-w-0">
                  <div className="truncate font-medium">{row.file.name}</div>
                  {row.status === 'done' && row.response?.autofill_status === 'doi_match' && (
                    <div
                      className="mt-0.5 inline-flex items-center gap-1 text-[11px] text-emerald-700 bg-emerald-50 rounded px-1.5 py-0.5"
                      data-testid="library-upload-badge-doi"
                    >
                      DOI autofilled
                    </div>
                  )}
                  {row.status === 'done' &&
                    row.response?.autofill_status === 'heuristic_only' && (
                      <div
                        className="mt-0.5 inline-flex items-center gap-1 text-[11px] text-amber-700 bg-amber-50 rounded px-1.5 py-0.5"
                        data-testid="library-upload-badge-heuristic"
                      >
                        Heuristic guess
                      </div>
                    )}
                  {row.status === 'done' && row.response?.duplicate_of && (
                    <div className="text-amber-600 text-[12px] mt-0.5">
                      Possible duplicate of:{' '}
                      <span className="font-medium">
                        {row.response.duplicate_of.title}
                      </span>
                    </div>
                  )}
                  {row.status === 'done' && row.response?.extraction_error && (
                    <div className="text-rose-600 text-[12px] mt-0.5">
                      AI extraction warning: {row.response.extraction_error}
                    </div>
                  )}
                  {row.status === 'failed' && (
                    <div className="text-rose-600 text-[12px] mt-0.5">{row.error}</div>
                  )}
                </div>
                {row.status === 'pending' && (
                  <span className="text-[11px] text-muted-foreground">Pending</span>
                )}
                {row.status === 'uploading' && (
                  <Loader2 className="h-4 w-4 text-muted-foreground animate-spin shrink-0" />
                )}
                {row.status === 'done' && (
                  <CheckCircle2 className="h-4 w-4 text-emerald-600 shrink-0" />
                )}
                {row.status === 'failed' && (
                  <XCircle className="h-4 w-4 text-rose-600 shrink-0" />
                )}
              </motion.div>
            ))}
          </AnimatePresence>
          {showSummary && (
            <div
              className="rounded-md border border-border bg-muted/30 px-4 py-2 text-[12px]"
              data-testid="library-upload-summary"
            >
              <span className="font-medium">{stats.done} uploaded</span>
              {stats.failed > 0 && (
                <span className="text-rose-700">, {stats.failed} failed</span>
              )}
              .
            </div>
          )}
        </div>
      )}
    </div>
  )
}
