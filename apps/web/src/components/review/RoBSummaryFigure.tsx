import { Loader2, Send } from 'lucide-react'
import { useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { toast } from 'sonner'

import { Button } from '@/components/ui/button'
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip'
import {
  ROB_JUDGEMENT_LABELS,
  type Article,
  type RoBAssessment,
  type RoBJudgement,
  type RoBToolDef,
} from '@/lib/api'
import { usePushRoB } from '@/hooks/useReviews'

const COLOURS: Record<RoBJudgement | 'no_assessment', string> = {
  low: '#10b981', // emerald-500
  some_concerns: '#f59e0b', // amber-500
  high: '#ef4444', // red-500
  critical: '#7f1d1d', // red-900
  unclear: '#9ca3af', // gray-400
  no_assessment: '#e5e7eb', // gray-200
}

function normaliseToJudgement(ans: string): RoBJudgement {
  // For ROBINS-I or NOS, raw answers don't map directly to judgements.
  // For RoB 2 / AMSTAR-2 / ROBINS-I we coerce here for display purposes.
  if (ans === 'low' || ans === 'yes') return 'low'
  if (ans === 'some_concerns' || ans === 'moderate' || ans === 'partial_yes')
    return 'some_concerns'
  if (ans === 'high' || ans === 'serious' || ans === 'no') return 'high'
  if (ans === 'critical') return 'critical'
  return 'unclear'
}

export function RoBSummaryFigure({
  projectId,
  toolDefs,
  assessments,
  articles,
}: {
  projectId: string
  toolDefs: RoBToolDef[]
  assessments: RoBAssessment[]
  articles: Article[]
}) {
  const push = usePushRoB(projectId)
  const navigate = useNavigate()

  // Choose the dominant tool (most common across assessments) to drive
  // column layout. Falls back to rob2.
  const dominantToolKey = useMemo(() => {
    const counts = new Map<string, number>()
    for (const a of assessments) {
      counts.set(a.tool, (counts.get(a.tool) ?? 0) + 1)
    }
    let best: string | undefined
    let bestN = -1
    for (const [k, n] of counts) {
      if (n > bestN) {
        best = k
        bestN = n
      }
    }
    return best ?? 'rob2'
  }, [assessments])

  const dominantTool = toolDefs.find((t) => t.key === dominantToolKey)

  const articleById = useMemo(() => {
    const m = new Map<string, Article>()
    for (const a of articles) m.set(a.id, a)
    return m
  }, [articles])

  if (!dominantTool) {
    return (
      <div className="rounded-md border border-dashed border-border p-6 text-center text-[13px] text-muted-foreground">
        Loading tools…
      </div>
    )
  }

  if (assessments.length === 0) {
    return (
      <div className="rounded-md border border-dashed border-border p-6 text-center text-[13px] text-muted-foreground">
        No risk of bias assessments yet.
      </div>
    )
  }

  const domains = dominantTool.domains

  return (
    <div className="space-y-3">
      <header className="flex items-center justify-between">
        <div>
          <div className="text-[15px] font-semibold tracking-tight">
            Summary (traffic-light)
          </div>
          <div className="text-[12px] text-muted-foreground">
            Showing assessments using <span className="font-medium">{dominantTool.label}</span>. Others are
            included with overall judgement only.
          </div>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={() =>
            push.mutate(undefined, {
              onSuccess: () => {
                toast.success('Pushed to Results')
                navigate(`/projects/${projectId}/manuscript?section=Results`)
              },
              onError: (e: Error) => toast.error(e.message),
            })
          }
          disabled={push.isPending}
        >
          {push.isPending ? (
            <Loader2 className="h-3.5 w-3.5 mr-1.5 animate-spin" />
          ) : (
            <Send className="h-3.5 w-3.5 mr-1.5" />
          )}
          Push to Results
        </Button>
      </header>

      <div className="rounded-lg border border-border bg-white overflow-auto">
        <table className="text-[12px]">
          <thead>
            <tr className="text-[10px] uppercase tracking-wider text-muted-foreground">
              <th className="text-left px-3 py-2 font-medium min-w-[220px]">Study</th>
              <th className="text-left px-3 py-2 font-medium">Tool</th>
              {domains.map((d) => (
                <th
                  key={d.key}
                  className="px-2 py-2 font-medium text-center"
                  title={d.label}
                >
                  <div className="-rotate-45 origin-bottom-left translate-y-3 whitespace-nowrap inline-block">
                    {d.label}
                  </div>
                </th>
              ))}
              <th className="px-2 py-2 font-medium text-center">Overall</th>
            </tr>
          </thead>
          <tbody>
            <TooltipProvider delayDuration={120}>
              {assessments.map((a) => {
                const art = articleById.get(a.article_id)
                const overall = (a.overall_override ?? a.overall_auto) as RoBJudgement
                return (
                  <tr key={a.id} className="border-t border-border">
                    <td className="px-3 py-2 max-w-[260px] truncate" title={art?.title ?? a.article_id}>
                      {art?.title ?? a.article_id}
                    </td>
                    <td className="px-3 py-2 text-muted-foreground">{a.tool}</td>
                    {domains.map((d) => {
                      const raw = a.domain_answers[d.key]
                      if (!raw) {
                        return (
                          <td key={d.key} className="px-1 py-1 text-center">
                            <Dot judge="unclear" raw="—" label={d.label} />
                          </td>
                        )
                      }
                      return (
                        <td key={d.key} className="px-1 py-1 text-center">
                          <Dot
                            judge={normaliseToJudgement(raw)}
                            raw={raw}
                            label={d.label}
                          />
                        </td>
                      )
                    })}
                    <td className="px-1 py-1 text-center">
                      <Dot
                        judge={overall}
                        raw={overall}
                        label="Overall"
                        diamond
                      />
                    </td>
                  </tr>
                )
              })}
            </TooltipProvider>
          </tbody>
        </table>
      </div>

      <Legend />
    </div>
  )
}

function Dot({
  judge,
  raw,
  label,
  diamond = false,
}: {
  judge: RoBJudgement
  raw: string
  label: string
  diamond?: boolean
}) {
  const colour = COLOURS[judge] ?? COLOURS.no_assessment
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <span
          aria-label={`${label}: ${ROB_JUDGEMENT_LABELS[judge]} (${raw})`}
          className="inline-block"
        >
          <svg width={20} height={20} viewBox="0 0 20 20" role="img">
            {diamond ? (
              <polygon
                points="10,2 18,10 10,18 2,10"
                fill={colour}
                stroke="rgba(0,0,0,0.15)"
              />
            ) : (
              <circle cx={10} cy={10} r={7} fill={colour} stroke="rgba(0,0,0,0.15)" />
            )}
          </svg>
        </span>
      </TooltipTrigger>
      <TooltipContent side="top" className="text-[11px]">
        <div className="font-medium">{label}</div>
        <div className="text-muted-foreground">
          {ROB_JUDGEMENT_LABELS[judge]} ({raw})
        </div>
      </TooltipContent>
    </Tooltip>
  )
}

function Legend() {
  const items: { j: RoBJudgement; label: string }[] = [
    { j: 'low', label: 'Low' },
    { j: 'some_concerns', label: 'Some concerns' },
    { j: 'high', label: 'High' },
    { j: 'critical', label: 'Critical' },
    { j: 'unclear', label: 'Unclear' },
  ]
  return (
    <div className="flex items-center gap-3 flex-wrap text-[11px] text-muted-foreground">
      {items.map((it) => (
        <div key={it.j} className="flex items-center gap-1.5">
          <span
            className="inline-block h-3 w-3 rounded-full"
            style={{ background: COLOURS[it.j] }}
          />
          {it.label}
        </div>
      ))}
    </div>
  )
}
