import { AlertTriangle, CheckCircle2 } from 'lucide-react'

import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip'
import { cn } from '@/lib/utils'

type AssumptionEntry = {
  statistic?: number | null
  p_value?: number | null
  ok?: boolean
}

const ASSUMPTION_LABELS: Record<string, string> = {
  shapiro: 'Shapiro–Wilk',
  levene: 'Levene',
  prop_hazards: 'Proportional hazards',
}

export function AssumptionPills({
  assumptions,
}: {
  assumptions: Record<string, unknown> | null | undefined
}) {
  if (!assumptions) return null
  const entries = Object.entries(assumptions).filter(
    ([, v]) => v && typeof v === 'object',
  ) as Array<[string, AssumptionEntry]>

  if (entries.length === 0) return null

  return (
    <TooltipProvider delayDuration={150}>
      <div className="flex flex-wrap gap-1.5">
        {entries.map(([key, val]) => {
          const ok = val.ok ?? true
          const label = ASSUMPTION_LABELS[key] ?? key
          const p = typeof val.p_value === 'number' ? val.p_value : null
          return (
            <Tooltip key={key}>
              <TooltipTrigger asChild>
                <span
                  className={cn(
                    'inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[11px] font-medium',
                    ok
                      ? 'border-emerald-200 bg-emerald-50 text-emerald-700'
                      : 'border-amber-200 bg-amber-50 text-amber-700',
                  )}
                >
                  {ok ? (
                    <CheckCircle2 className="h-3 w-3" />
                  ) : (
                    <AlertTriangle className="h-3 w-3" />
                  )}
                  {label}
                </span>
              </TooltipTrigger>
              <TooltipContent side="top">
                <div className="text-[12px]">
                  <div className="font-medium">{label}</div>
                  <div className="text-muted-foreground">
                    {ok ? 'Passed' : 'Violated'}
                    {p !== null ? ` · p = ${formatP(p)}` : ''}
                  </div>
                </div>
              </TooltipContent>
            </Tooltip>
          )
        })}
      </div>
    </TooltipProvider>
  )
}

function formatP(p: number): string {
  if (p < 0.001) return '<0.001'
  return p.toFixed(3)
}
