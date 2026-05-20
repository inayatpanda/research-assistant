import { AnimatePresence, motion } from 'framer-motion'
import { FileSpreadsheet, Loader2, UploadCloud } from 'lucide-react'
import { useCallback, useState } from 'react'
import { useDropzone } from 'react-dropzone'
import { toast } from 'sonner'

import { type Dataset } from '@/lib/api'
import { cn } from '@/lib/utils'
import { useUploadDataset } from '@/hooks/useDatasets'

export function DatasetUpload({
  projectId,
  onUploaded,
  compact = false,
}: {
  projectId: string
  onUploaded?: (dataset: Dataset) => void
  compact?: boolean
}) {
  const [activeFile, setActiveFile] = useState<File | null>(null)
  const upload = useUploadDataset(projectId)

  const onDrop = useCallback(
    async (accepted: File[]) => {
      if (!accepted.length) return
      const file = accepted[0]
      setActiveFile(file)
      try {
        const dataset = await upload.mutateAsync(file)
        const meta = (dataset.dataset_metadata ?? null) as
          | { sheet_name?: string; long_format_hint?: unknown }
          | null
        if (meta?.sheet_name) {
          // Multi-sheet XLSX path: filename already includes the sheet
          // segment, but flag to the user so they understand the split.
          toast.success(
            `Imported workbook "${file.name}". Each sheet has been added as its own dataset.`,
          )
        } else {
          toast.success(`Uploaded ${dataset.filename} · ${dataset.n_rows} rows`)
        }
        // DEMO-FIX-C — Inform the user when column headers were sanitised so
        // they know to review the new "Display label" column. The dataset
        // detail page also surfaces a banner with the full mapping.
        const report = dataset.header_sanitisation_report ?? []
        if (report.length > 0) {
          toast.info(
            `Renamed ${report.length} column header${
              report.length === 1 ? '' : 's'
            } to identifier-safe names. Original labels preserved as display labels.`,
            { duration: 6000 },
          )
        }
        onUploaded?.(dataset)
      } catch (e) {
        const msg = e instanceof Error ? e.message : 'Upload failed'
        toast.error(msg)
      } finally {
        setActiveFile(null)
      }
    },
    [upload, onUploaded],
  )

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'text/csv': ['.csv'],
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
    },
    multiple: false,
    disabled: !projectId || upload.isPending,
  })

  const isUploading = upload.isPending

  return (
    <div className="space-y-2">
      <motion.div
        {...getRootProps()}
        whileHover={{ scale: 1.005 }}
        className={cn(
          'relative rounded-lg border-2 border-dashed cursor-pointer transition-colors',
          compact ? 'p-5 text-left' : 'p-8 text-center',
          isDragActive
            ? 'border-accent bg-accent/5'
            : 'border-border bg-white/40 hover:border-accent/40',
          (isUploading || !projectId) && 'pointer-events-none opacity-70',
        )}
      >
        <input
          {...getInputProps({
            onClick: (e) => {
              ;(e.target as HTMLInputElement).value = ''
            },
          })}
        />
        {compact ? (
          <div className="flex items-center gap-3 text-[13px] text-muted-foreground">
            <UploadCloud className="h-5 w-5" />
            <div className="flex-1 min-w-0">
              <div className="font-medium text-foreground truncate">
                {isUploading
                  ? `Uploading ${activeFile?.name ?? 'file'}…`
                  : isDragActive
                    ? 'Drop to upload'
                    : 'Upload masterchart'}
              </div>
              <div className="text-[12px] text-muted-foreground">CSV or XLSX</div>
            </div>
            {isUploading && (
              <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
            )}
          </div>
        ) : (
          <motion.div
            animate={isDragActive ? { scale: 1.05 } : { scale: 1 }}
            className="flex flex-col items-center gap-3 text-muted-foreground"
          >
            <UploadCloud className="h-7 w-7" />
            <div className="text-[14px]">
              <span className="font-medium text-foreground">
                {isUploading
                  ? `Uploading ${activeFile?.name ?? 'file'}…`
                  : isDragActive
                    ? 'Drop to upload'
                    : 'Drop a CSV or XLSX here'}
              </span>
              {!isUploading && (
                <span className="text-muted-foreground">, or click to choose</span>
              )}
            </div>
            <div className="text-[12px] text-muted-foreground">
              .csv · .xlsx (Excel formulas not evaluated)
            </div>
          </motion.div>
        )}
      </motion.div>

      <AnimatePresence>
        {isUploading && activeFile && !compact && (
          <motion.div
            initial={{ opacity: 0, y: 4 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            className="flex items-center gap-3 rounded-md border border-border bg-white px-3 py-2 text-[13px]"
          >
            <FileSpreadsheet className="h-4 w-4 text-muted-foreground" />
            <div className="flex-1 truncate font-medium">{activeFile.name}</div>
            <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
