import { Plus, Scale, UploadCloud } from 'lucide-react'

import { Button } from '@/components/ui/button'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { type Dataset } from '@/lib/api'
import { cn } from '@/lib/utils'

/**
 * Horizontal data-row toolbar for the Statistics page. Sits directly under the
 * page header and surfaces the dataset selector + the dataset-scoped actions
 * (PSM, New analysis) and Upload as a single primary row. Replaces the old
 * left-rail dataset list when the page moved to a full-width layout.
 *
 * Selector heuristic: ≤3 datasets render as pills (fast switch + always
 * visible). >3 render as a `Select` dropdown so the toolbar doesn't wrap.
 */
const PILL_THRESHOLD = 3

export function DatasetToolbar({
  datasets,
  activeDatasetId,
  onSelect,
  onUpload,
  onNewAnalysis,
  onPsm,
}: {
  datasets: Dataset[]
  activeDatasetId: string | null
  onSelect: (id: string) => void
  onUpload: () => void
  onNewAnalysis: () => void
  onPsm: () => void
}) {
  const hasActive = !!activeDatasetId && datasets.some((d) => d.id === activeDatasetId)
  const usePills = datasets.length > 0 && datasets.length <= PILL_THRESHOLD

  return (
    <div
      className="flex flex-wrap items-center gap-2"
      data-testid="dataset-toolbar"
    >
      <Button
        variant="outline"
        size="sm"
        onClick={onUpload}
        data-testid="dataset-toolbar-upload"
      >
        <UploadCloud className="h-4 w-4 mr-1.5" />
        Upload
      </Button>

      {datasets.length === 0 ? (
        <span className="text-[12px] text-muted-foreground italic">
          No datasets yet — upload a masterchart to begin.
        </span>
      ) : usePills ? (
        <div
          className="flex flex-wrap items-center gap-1.5"
          role="tablist"
          aria-label="Datasets"
          data-testid="dataset-toolbar-pills"
        >
          {datasets.map((d) => (
            <button
              type="button"
              key={d.id}
              role="tab"
              aria-selected={d.id === activeDatasetId}
              onClick={() => onSelect(d.id)}
              data-testid={`dataset-pill-${d.id}`}
              title={`${d.filename} · ${d.n_rows} rows × ${d.n_columns} cols`}
              className={cn(
                'inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-[12px] transition-colors',
                d.id === activeDatasetId
                  ? 'border-accent bg-accent/10 text-accent font-medium'
                  : 'border-border bg-white text-muted-foreground hover:border-accent/40 hover:text-foreground',
              )}
            >
              <span className="truncate max-w-[160px] font-medium">
                {d.filename}
              </span>
              <span className="text-[11px] text-muted-foreground tabular-nums">
                {d.n_rows}×{d.n_columns}
              </span>
            </button>
          ))}
        </div>
      ) : (
        <div className="min-w-[260px]" data-testid="dataset-toolbar-select">
          <Select
            value={activeDatasetId ?? undefined}
            onValueChange={onSelect}
          >
            <SelectTrigger className="h-9 text-[13px]">
              <SelectValue placeholder="Select dataset" />
            </SelectTrigger>
            <SelectContent>
              {datasets.map((d) => (
                <SelectItem
                  key={d.id}
                  value={d.id}
                  data-testid={`dataset-option-${d.id}`}
                >
                  <span className="font-medium">{d.filename}</span>
                  <span className="ml-2 text-muted-foreground text-[12px]">
                    · {d.n_rows} rows × {d.n_columns} cols
                  </span>
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      )}

      <div className="flex items-center gap-2 ml-auto">
        <Button
          variant="outline"
          size="sm"
          onClick={onPsm}
          disabled={!hasActive}
          data-testid="dataset-toolbar-psm"
        >
          <Scale className="h-4 w-4 mr-1.5" />
          PSM
        </Button>
        <Button
          size="sm"
          onClick={onNewAnalysis}
          disabled={!hasActive}
          className="bg-accent hover:bg-accent-hover text-white"
          data-testid="dataset-toolbar-new-analysis"
        >
          <Plus className="h-4 w-4 mr-1.5" />
          New analysis
        </Button>
      </div>
    </div>
  )
}
