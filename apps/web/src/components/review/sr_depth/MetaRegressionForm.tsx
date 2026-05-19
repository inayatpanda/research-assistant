/**
 * MetaRegressionForm (MP19) — pick a continuous moderator (one value per
 * input), run weighted OLS, show coefficient table + bubble plot.
 */
import { Loader2 } from 'lucide-react'
import { useState } from 'react'
import { toast } from 'sonner'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { useMetaRegression } from '@/hooks/useMetaExtensions'

type Props = {
  projectId: string
  metaId: string
  defaultK?: number
}

export function MetaRegressionForm({
  projectId,
  metaId,
  defaultK = 4,
}: Props) {
  const reg = useMetaRegression(projectId)
  const [label, setLabel] = useState('Mean age')
  const [csv, setCsv] = useState(
    Array.from({ length: defaultK }, (_, i) => String(50 + i * 5)).join(', '),
  )

  const run = async () => {
    const values = csv
      .split(/[,\s]+/)
      .map((v) => v.trim())
      .filter(Boolean)
      .map((v) => Number(v))
    if (values.some(Number.isNaN)) {
      toast.error('Moderator must be a list of numbers.')
      return
    }
    try {
      await reg.mutateAsync({
        metaId,
        moderator: values,
        moderator_label: label,
      })
    } catch (e) {
      toast.error(e instanceof Error ? e.message : 'Regression failed.')
    }
  }

  return (
    <section data-testid="meta-regression-form" className="space-y-3">
      <h3 className="text-sm font-medium">Meta-regression</h3>
      <div className="grid grid-cols-2 gap-3">
        <div>
          <Label htmlFor="mr-label">Moderator label</Label>
          <Input
            id="mr-label"
            value={label}
            onChange={(e) => setLabel(e.target.value)}
          />
        </div>
        <div className="col-span-2">
          <Label htmlFor="mr-values">
            Values per input (comma-separated, in input order)
          </Label>
          <Input
            id="mr-values"
            value={csv}
            onChange={(e) => setCsv(e.target.value)}
            data-testid="mr-values"
          />
        </div>
      </div>
      <Button onClick={run} disabled={reg.isPending} data-testid="mr-run">
        {reg.isPending ? (
          <Loader2 className="h-4 w-4 animate-spin mr-1" />
        ) : null}
        Run regression
      </Button>

      {reg.data && (
        <div className="grid grid-cols-2 gap-4 mt-3" data-testid="mr-result">
          <table className="text-sm">
            <tbody>
              <tr>
                <td className="text-muted-foreground pr-3">Coefficient</td>
                <td>{reg.data.coef.toFixed(4)}</td>
              </tr>
              <tr>
                <td className="text-muted-foreground pr-3">SE</td>
                <td>{reg.data.se.toFixed(4)}</td>
              </tr>
              <tr>
                <td className="text-muted-foreground pr-3">p</td>
                <td>{reg.data.p.toFixed(4)}</td>
              </tr>
              <tr>
                <td className="text-muted-foreground pr-3">Intercept</td>
                <td>{reg.data.intercept.toFixed(4)}</td>
              </tr>
              <tr>
                <td className="text-muted-foreground pr-3">R²</td>
                <td>{reg.data.r2.toFixed(3)}</td>
              </tr>
              <tr>
                <td className="text-muted-foreground pr-3">n</td>
                <td>{reg.data.n}</td>
              </tr>
            </tbody>
          </table>
          <img
            src={`data:image/png;base64,${reg.data.bubble_plot_png_base64}`}
            alt="Bubble plot"
            className="w-full rounded border border-border"
            data-testid="mr-plot"
          />
        </div>
      )}
    </section>
  )
}
