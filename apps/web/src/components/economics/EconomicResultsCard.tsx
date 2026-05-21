import { LearnTooltip } from '@/components/learn/LearnTooltip'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { ChartImage } from '@/components/statistics/ChartImage'
import type { EconomicAnalysis } from '@/lib/api'

export interface EconomicResultsCardProps {
  analysis: EconomicAnalysis
}

function _formatCurrency(value: number, currency: string): string {
  try {
    return new Intl.NumberFormat(undefined, {
      style: 'currency',
      currency: currency === 'Other' ? 'USD' : currency,
      maximumFractionDigits: 0,
    }).format(value)
  } catch {
    return `${currency} ${value.toFixed(0)}`
  }
}

function _dominanceBadgeVariant(
  status: string,
): 'default' | 'destructive' | 'secondary' | 'outline' {
  if (status === 'dominant') return 'default'
  if (status === 'dominated') return 'destructive'
  if (status === 'northeast') return 'secondary'
  if (status === 'southwest') return 'outline'
  return 'secondary'
}

/**
 * MP18 — Renders ICER + NMB + mean diffs + plane / CEAC PNGs for a single
 * EconomicAnalysis. Click each PNG to open the existing ChartImage zoom
 * modal.
 */
export function EconomicResultsCard({ analysis }: EconomicResultsCardProps) {
  const result = analysis.result
  if (!result) {
    return (
      <Card data-testid="economic-results-card">
        <CardHeader>
          <CardTitle>Results</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            The analysis has not been run yet.
          </p>
        </CardContent>
      </Card>
    )
  }
  const currency = analysis.currency
  return (
    <Card data-testid="economic-results-card">
      <CardHeader className="flex items-center justify-between gap-2 flex-row">
        <CardTitle>Results — {analysis.name}</CardTitle>
        <Badge variant={_dominanceBadgeVariant(result.dominance_status)}>
          {result.dominance_status}
        </Badge>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-sm">
          <div>
            <div className="text-muted-foreground">Mean cost diff</div>
            <div className="font-semibold">
              {_formatCurrency(result.mean_cost_diff, currency)}
            </div>
          </div>
          <div>
            <div className="text-muted-foreground">
              <LearnTooltip
                concept="qaly"
                iconOnly
                description="QALY — quality-adjusted life year, combines length and quality of life into a single outcome."
              >
                Mean QALY diff
              </LearnTooltip>
            </div>
            <div className="font-semibold">{result.mean_qaly_diff.toFixed(4)}</div>
          </div>
          <div>
            <div className="text-muted-foreground">
              <LearnTooltip
                concept="icer"
                iconOnly
                description="ICER — incremental cost-effectiveness ratio, additional cost per additional QALY gained vs comparator."
              >
                ICER
              </LearnTooltip>
            </div>
            <div className="font-semibold">
              {result.icer === null
                ? 'n/a'
                : `${_formatCurrency(result.icer, currency)} / QALY`}
            </div>
          </div>
          <div>
            <div className="text-muted-foreground">Bootstrap reps</div>
            <div className="font-semibold">{result.plane_bootstrap.length}</div>
          </div>
        </div>
        {Object.keys(result.nmb_at_thresholds ?? {}).length > 0 && (
          <div className="rounded-md border border-border p-3 text-sm">
            <div className="text-muted-foreground mb-1">
              <LearnTooltip
                concept="nmb"
                iconOnly
                description="Net Monetary Benefit — NMB = λ·ΔQALY − ΔCost, where λ is the willingness-to-pay threshold."
              >
                Net Monetary Benefit at each WTP
              </LearnTooltip>
            </div>
            <ul className="grid grid-cols-2 md:grid-cols-3 gap-1">
              {Object.entries(result.nmb_at_thresholds)
                .sort((a, b) => Number(a[0]) - Number(b[0]))
                .map(([wtp, nmb]) => (
                  <li key={wtp}>
                    <span className="text-muted-foreground">
                      @ {_formatCurrency(Number(wtp), currency)}:
                    </span>{' '}
                    <span className="font-medium">
                      {_formatCurrency(Number(nmb), currency)}
                    </span>
                  </li>
                ))}
            </ul>
          </div>
        )}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <div className="text-sm font-medium mb-1">CE plane</div>
            <ChartImage
              chart={{
                format: 'png',
                data_uri: result.plane_png_uri,
                byte_size: 0,
              }}
              alt="Cost-effectiveness plane"
              downloadName={`${analysis.name}-plane`}
            />
          </div>
          <div>
            <div className="text-sm font-medium mb-1">CEAC</div>
            <ChartImage
              chart={{
                format: 'png',
                data_uri: result.ceac_png_uri,
                byte_size: 0,
              }}
              alt="Cost-effectiveness acceptability curve"
              downloadName={`${analysis.name}-ceac`}
            />
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
