import { useNavigate } from 'react-router-dom'
import { Sparkles } from 'lucide-react'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import {
  useInterpretMeta,
  usePushMeta,
  useRunMeta,
} from '@/hooks/useMeta'
import type { MetaAnalysisRead } from '@/lib/api'

const _LOG_METRICS = new Set(['or', 'rr', 'hr'])

function backTransform(metric: string, x: number | null): number | null {
  if (x == null) return null
  if (_LOG_METRICS.has(metric)) return Math.exp(x)
  if (metric === 'r') return Math.tanh(x)
  return x
}

function fmt(x: number | null | undefined, digits = 2): string {
  if (x == null || Number.isNaN(x)) return '—'
  if (Math.abs(x) >= 100) return x.toFixed(0)
  return x.toFixed(digits)
}

function fmtP(p: number | null | undefined): string {
  if (p == null) return '—'
  if (p < 0.001) return '<0.001'
  return p.toFixed(3)
}

function statusBadge(status: string) {
  switch (status) {
    case 'completed':
      return <Badge className="bg-emerald-100 text-emerald-700 border-emerald-200">Completed</Badge>
    case 'running':
      return <Badge className="bg-amber-100 text-amber-700 border-amber-200">Running</Badge>
    case 'failed':
      return <Badge variant="destructive">Failed</Badge>
    default:
      return <Badge variant="outline">Draft</Badge>
  }
}

export function MetaResultCard({
  projectId,
  meta,
}: {
  projectId: string
  meta: MetaAnalysisRead
}) {
  const navigate = useNavigate()
  const { mutateAsync: runMeta, isPending: isRunning } = useRunMeta(projectId)
  const { mutateAsync: interpret, isPending: isInterpreting } = useInterpretMeta(projectId)
  const { mutateAsync: pushMeta, isPending: isPushing } = usePushMeta(projectId)

  const showLog = _LOG_METRICS.has(meta.effect_metric)
  const est = meta.pooled_estimate
  const lo = meta.ci_low
  const hi = meta.ci_high
  const estBt = backTransform(meta.effect_metric, est)
  const loBt = backTransform(meta.effect_metric, lo)
  const hiBt = backTransform(meta.effect_metric, hi)

  return (
    <Card>
      <CardHeader className="flex flex-row items-start justify-between gap-2">
        <div>
          <CardTitle className="text-[16px]">
            {meta.title || `${meta.effect_metric.toUpperCase()} (${meta.model})`}
          </CardTitle>
          <div className="mt-1 text-[12px] text-muted-foreground">
            {meta.effect_metric.toUpperCase()} · {meta.model}-effects · k={meta.inputs.length}
          </div>
        </div>
        {statusBadge(meta.status)}
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid grid-cols-2 gap-4">
          <div>
            <div className="text-[11px] uppercase tracking-wider text-muted-foreground">
              Pooled estimate
            </div>
            <div className="text-[18px] font-semibold">
              {showLog
                ? `${fmt(estBt)} [${fmt(loBt)}, ${fmt(hiBt)}]`
                : `${fmt(est)} [${fmt(lo)}, ${fmt(hi)}]`}
            </div>
            {showLog && (
              <div className="text-[11px] text-muted-foreground mt-0.5">
                log-scale: {fmt(est, 3)} [{fmt(lo, 3)}, {fmt(hi, 3)}]
              </div>
            )}
            <div className="text-[11px] text-muted-foreground">
              z = {fmt(meta.z_value, 2)} · p = {fmtP(meta.p_value)}
            </div>
          </div>
          <div>
            <div className="text-[11px] uppercase tracking-wider text-muted-foreground">
              Heterogeneity
            </div>
            <table className="text-[12px]">
              <tbody>
                <tr><td className="pr-2 text-muted-foreground">Q</td><td>{fmt(meta.q_value)}</td></tr>
                <tr><td className="pr-2 text-muted-foreground">df</td><td>{meta.q_df ?? '—'}</td></tr>
                <tr><td className="pr-2 text-muted-foreground">p</td><td>{fmtP(meta.q_p)}</td></tr>
                <tr><td className="pr-2 text-muted-foreground">I²</td><td>{meta.i2 != null ? `${fmt(meta.i2, 1)}%` : '—'}</td></tr>
                <tr><td className="pr-2 text-muted-foreground">τ²</td><td>{fmt(meta.tau2, 4)}</td></tr>
              </tbody>
            </table>
          </div>
        </div>

        {meta.subgroup_summary && (
          <div>
            <div className="text-[11px] uppercase tracking-wider text-muted-foreground mb-1">
              Subgroup summary
            </div>
            <table className="w-full text-[12px] border border-border rounded-md">
              <thead className="bg-muted/30">
                <tr>
                  <th className="px-2 py-1 text-left">Subgroup</th>
                  <th className="px-2 py-1 text-left">k</th>
                  <th className="px-2 py-1 text-left">Pooled</th>
                  <th className="px-2 py-1 text-left">95% CI</th>
                  <th className="px-2 py-1 text-left">I²</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(meta.subgroup_summary).map(([name, payload]) => {
                  const p = payload as Record<string, number | null>
                  return (
                    <tr key={name} className="border-t border-border">
                      <td className="px-2 py-1 font-medium">{name}</td>
                      <td className="px-2 py-1">{p.k ?? '—'}</td>
                      <td className="px-2 py-1">{fmt(p.estimate ?? null)}</td>
                      <td className="px-2 py-1">
                        {p.ci_low != null && p.ci_high != null
                          ? `[${fmt(p.ci_low)}, ${fmt(p.ci_high)}]`
                          : '—'}
                      </td>
                      <td className="px-2 py-1">{p.i2 != null ? `${fmt(p.i2, 1)}%` : '—'}</td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}

        {meta.ai_interpretation && (
          <div className="rounded-md border border-border bg-muted/20 p-3 text-[13px] leading-relaxed">
            {meta.ai_interpretation}
          </div>
        )}

        <div className="flex items-center gap-2 pt-2">
          <Button
            size="sm"
            onClick={() => runMeta(meta.id)}
            disabled={isRunning}
          >
            {isRunning ? 'Running…' : meta.status === 'completed' ? 'Re-run' : 'Run'}
          </Button>
          <Button
            size="sm"
            variant="outline"
            onClick={() => interpret(meta.id)}
            disabled={meta.status !== 'completed' || isInterpreting}
          >
            <Sparkles className="h-3.5 w-3.5 mr-1" />
            {isInterpreting ? 'Interpreting…' : 'Interpret with AI'}
          </Button>
          <Button
            size="sm"
            variant="outline"
            onClick={async () => {
              await pushMeta(meta.id)
              navigate(`/projects/${projectId}/manuscript?section=Results`)
            }}
            disabled={meta.status !== 'completed' || isPushing}
          >
            {isPushing ? 'Pushing…' : 'Push to Manuscript'}
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}
