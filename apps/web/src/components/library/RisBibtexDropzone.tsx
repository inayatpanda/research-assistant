import { FileText } from 'lucide-react'
import { useCallback, useState } from 'react'
import { useDropzone } from 'react-dropzone'
import { toast } from 'sonner'

import { useImportBibtex, useImportRis } from '@/hooks/useIngest'
import { cn } from '@/lib/utils'
import { type ArticleMetadata } from '@/lib/api'

import { ImportPreviewDialog } from './ImportPreviewDialog'

export function RisBibtexDropzone({ projectId }: { projectId: string }) {
  const [items, setItems] = useState<ArticleMetadata[] | null>(null)
  const [open, setOpen] = useState(false)
  const ris = useImportRis(projectId)
  const bib = useImportBibtex(projectId)

  const busy = ris.isPending || bib.isPending

  const onDrop = useCallback(
    async (accepted: File[]) => {
      const file = accepted[0]
      if (!file) return
      const name = file.name.toLowerCase()
      const isRis = name.endsWith('.ris')
      const isBib = name.endsWith('.bib') || name.endsWith('.bibtex')
      if (!isRis && !isBib) {
        toast.error('Drop a .ris or .bib file')
        return
      }
      try {
        const parsed = isRis
          ? await ris.mutateAsync(file)
          : await bib.mutateAsync(file)
        setItems(parsed)
        setOpen(true)
      } catch (e) {
        toast.error(e instanceof Error ? e.message : 'Import failed')
      }
    },
    [ris, bib],
  )

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/x-research-info-systems': ['.ris'],
      'application/x-bibtex': ['.bib', '.bibtex'],
      'text/plain': ['.ris', '.bib', '.bibtex'],
    },
    multiple: false,
    disabled: busy,
  })

  return (
    <>
      <div
        {...getRootProps()}
        role="button"
        tabIndex={0}
        aria-label="Import RIS or BibTeX file"
        className={cn(
          'rounded-lg border-2 border-dashed p-4 text-center cursor-pointer transition-colors',
          isDragActive
            ? 'border-accent bg-accent/5'
            : 'border-border bg-white/40 hover:border-accent/40',
        )}
      >
        <input {...getInputProps()} />
        <div className="flex flex-col items-center gap-1 text-muted-foreground">
          <FileText className="h-5 w-5" />
          <div className="text-[13px]">
            <span className="font-medium text-foreground">
              Drop a .ris or .bib export
            </span>
            <span className="text-muted-foreground">, or click to choose</span>
          </div>
          <div className="text-[11px]">2 MiB cap</div>
        </div>
      </div>

      {items !== null && (
        <ImportPreviewDialog
          projectId={projectId}
          open={open}
          items={items}
          onOpenChange={(o) => {
            setOpen(o)
            if (!o) setItems(null)
          }}
        />
      )}
    </>
  )
}
