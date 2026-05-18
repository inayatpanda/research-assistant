import { motion } from 'framer-motion'
import { FileSpreadsheet, Trash2 } from 'lucide-react'
import { toast } from 'sonner'

import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { type Dataset } from '@/lib/api'
import { cn } from '@/lib/utils'
import { useDatasets, useDeleteDataset } from '@/hooks/useDatasets'

export function DatasetList({
  projectId,
  activeId,
  onSelect,
}: {
  projectId: string
  activeId: string | null
  onSelect: (id: string) => void
}) {
  const { data: datasets = [], isLoading } = useDatasets(projectId)
  const del = useDeleteDataset(projectId)

  if (isLoading) {
    return (
      <div className="space-y-2">
        {[0, 1].map((i) => (
          <Skeleton key={i} className="h-[68px] rounded-lg" />
        ))}
      </div>
    )
  }

  if (datasets.length === 0) {
    return (
      <div className="rounded-md border border-dashed border-border bg-white/40 p-6 text-center">
        <FileSpreadsheet className="h-6 w-6 mx-auto text-muted-foreground" />
        <div className="mt-2 text-[13px] font-medium">No datasets yet</div>
        <div className="mt-1 text-[12px] text-muted-foreground">
          Upload a masterchart to begin.
        </div>
      </div>
    )
  }

  return (
    <ul className="space-y-2">
      {datasets.map((d, i) => (
        <DatasetRow
          key={d.id}
          dataset={d}
          isActive={d.id === activeId}
          index={i}
          onSelect={() => onSelect(d.id)}
          onDelete={() => {
            if (
              confirm(
                `Delete "${d.filename}"? Linked analyses will be removed too.`,
              )
            ) {
              del.mutate(d.id, {
                onSuccess: () => toast.success('Dataset deleted'),
                onError: (e: Error) => toast.error(e.message),
              })
            }
          }}
        />
      ))}
    </ul>
  )
}

function DatasetRow({
  dataset,
  isActive,
  index,
  onSelect,
  onDelete,
}: {
  dataset: Dataset
  isActive: boolean
  index: number
  onSelect: () => void
  onDelete: () => void
}) {
  return (
    <motion.li
      initial={{ opacity: 0, y: 4 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.03 }}
      className={cn(
        'group flex items-center gap-3 rounded-md border bg-white px-3 py-2.5 cursor-pointer transition-all',
        isActive
          ? 'border-accent shadow-sm ring-1 ring-accent/20'
          : 'border-border hover:border-accent/40',
      )}
      onClick={onSelect}
    >
      <FileSpreadsheet
        className={cn(
          'h-5 w-5 shrink-0',
          isActive ? 'text-accent' : 'text-muted-foreground',
        )}
      />
      <div className="flex-1 min-w-0">
        <div className="truncate text-[13px] font-medium">{dataset.filename}</div>
        <div className="text-[11px] text-muted-foreground">
          {dataset.n_rows} rows · {dataset.n_columns} cols ·{' '}
          {dataset.variables.length} variable
          {dataset.variables.length === 1 ? '' : 's'}
        </div>
      </div>
      <Button
        size="icon"
        variant="ghost"
        className="opacity-0 group-hover:opacity-100 h-7 w-7"
        onClick={(e) => {
          e.stopPropagation()
          onDelete()
        }}
        aria-label="Delete dataset"
      >
        <Trash2 className="h-4 w-4 text-muted-foreground" />
      </Button>
    </motion.li>
  )
}
