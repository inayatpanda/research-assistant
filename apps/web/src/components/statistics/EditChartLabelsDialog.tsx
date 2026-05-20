/**
 * DEMO-FIX-C — Per-chart label override form.
 *
 * Lets the user override the x-axis, y-axis and title for a single
 * AnalysisResult.chart. Overrides are stored on the chart blob and re-applied
 * on re-render; they take precedence over the dataset-level display labels.
 *
 * Empty submissions are allowed — sending an empty string clears that
 * particular override (defaults back to the display-label / canonical name).
 */
import { Loader2 } from 'lucide-react'
import { useEffect, useState } from 'react'
import { toast } from 'sonner'

import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { useUpdateChartLabels } from '@/hooks/useAnalyses'

export type ChartLabelOverrides = {
  x_label_override?: string | null
  y_label_override?: string | null
  title_override?: string | null
}

export function EditChartLabelsDialog({
  open,
  onOpenChange,
  projectId,
  datasetId,
  analysisId,
  initial,
}: {
  open: boolean
  onOpenChange: (next: boolean) => void
  projectId: string
  datasetId: string
  analysisId: string
  initial: ChartLabelOverrides
}) {
  const [x, setX] = useState(initial.x_label_override ?? '')
  const [y, setY] = useState(initial.y_label_override ?? '')
  const [title, setTitle] = useState(initial.title_override ?? '')
  const updateLabels = useUpdateChartLabels(projectId, datasetId)

  // Re-sync when the dialog reopens against a different analysis.
  useEffect(() => {
    if (open) {
      setX(initial.x_label_override ?? '')
      setY(initial.y_label_override ?? '')
      setTitle(initial.title_override ?? '')
    }
  }, [open, initial.x_label_override, initial.y_label_override, initial.title_override])

  const handleSave = () => {
    updateLabels.mutate(
      {
        analysisId,
        // Empty string clears the override.
        x_label_override: x,
        y_label_override: y,
        title_override: title,
      },
      {
        onSuccess: () => {
          toast.success('Chart labels updated')
          onOpenChange(false)
        },
        onError: (e: Error) => toast.error(e.message),
      },
    )
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md" data-testid="edit-chart-labels-dialog">
        <DialogHeader>
          <DialogTitle>Edit chart labels</DialogTitle>
          <DialogDescription>
            Override the x-axis, y-axis and title for this chart only. Leave a
            field empty to fall back to the variable's display label.
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-3 pt-1">
          <div className="space-y-1.5">
            <Label htmlFor="x-label" className="text-[12px]">
              X-axis label
            </Label>
            <Input
              id="x-label"
              value={x}
              onChange={(e) => setX(e.target.value)}
              placeholder="e.g. BMI group"
              data-testid="x-label-input"
            />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="y-label" className="text-[12px]">
              Y-axis label
            </Label>
            <Input
              id="y-label"
              value={y}
              onChange={(e) => setY(e.target.value)}
              placeholder="e.g. VAS pain at 6 months (post-op)"
              data-testid="y-label-input"
            />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="title" className="text-[12px]">
              Chart title
            </Label>
            <Input
              id="title"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="e.g. Pain by BMI group"
              data-testid="title-input"
            />
          </div>
        </div>
        <DialogFooter>
          <Button
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={updateLabels.isPending}
          >
            Cancel
          </Button>
          <Button
            onClick={handleSave}
            disabled={updateLabels.isPending}
            data-testid="save-chart-labels"
          >
            {updateLabels.isPending && (
              <Loader2 className="h-4 w-4 mr-1.5 animate-spin" />
            )}
            Save
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
