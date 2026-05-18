import { Loader2, Send } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { toast } from 'sonner'

import { Button } from '@/components/ui/button'
import { EXCLUSION_CATEGORY_LABELS, type ExclusionCategory } from '@/lib/api'
import { usePrisma, usePushPrisma } from '@/hooks/useReviews'

export function PRISMAFlowChart({ projectId }: { projectId: string }) {
  const { data, isLoading } = usePrisma(projectId)
  const push = usePushPrisma(projectId)
  const navigate = useNavigate()

  if (isLoading || !data) {
    return <div className="text-[13px] text-muted-foreground">Loading…</div>
  }

  const counts = data.counts
  const excluded = counts.excluded_full as Record<ExclusionCategory, number>
  const excludedTotal = Object.values(excluded).reduce(
    (s, n) => s + (n ?? 0),
    0,
  )

  return (
    <div className="space-y-4">
      <header className="flex items-center justify-between">
        <div>
          <h3 className="text-[15px] font-semibold tracking-tight">PRISMA 2020 flow</h3>
          <div className="text-[12px] text-muted-foreground">
            Auto-generated from your search log and screening decisions.
          </div>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={() =>
            push.mutate(undefined, {
              onSuccess: () => {
                toast.success('Pushed to Methodology')
                navigate('/manuscript?section=Methodology')
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
          Push to Methodology
        </Button>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-5 gap-3">
        <div className="lg:col-span-3 space-y-3">
          <FlowBox label="Records identified" n={counts.identified} tone="indigo" />
          <FlowBox label="After deduplication" n={counts.after_dedupe} tone="indigo" />
          <div className="grid grid-cols-2 gap-3">
            <FlowBox label="Title / Abstract screened" n={counts.screened} tone="indigo" />
            <FlowBox label="Excluded at title/abstract" n={counts.excluded_title} tone="rose" />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <FlowBox label="Full-text assessed" n={counts.full_text_assessed} tone="indigo" />
            <FlowBox label="Excluded at full-text" n={excludedTotal} tone="rose" />
          </div>
          <FlowBox label="Studies included" n={counts.included} tone="emerald" prominent />
        </div>

        <aside className="lg:col-span-2 rounded-md border border-border bg-white p-4">
          <div className="text-[11px] uppercase tracking-wider text-muted-foreground font-medium">
            Full-text exclusion reasons
          </div>
          <dl className="mt-2 space-y-1.5">
            {(Object.keys(excluded) as ExclusionCategory[]).map((k) => (
              <div key={k} className="flex items-center justify-between text-[12px]">
                <dt className="text-muted-foreground">
                  {EXCLUSION_CATEGORY_LABELS[k]}
                </dt>
                <dd className="tabular-nums font-medium">{excluded[k] ?? 0}</dd>
              </div>
            ))}
          </dl>
        </aside>
      </div>

      <details className="rounded-md border border-border bg-white">
        <summary className="cursor-pointer px-4 py-2 text-[12px] font-medium">
          Preview rendered SVG
        </summary>
        <div className="p-4 overflow-auto" dangerouslySetInnerHTML={{ __html: data.svg }} />
      </details>
    </div>
  )
}

function FlowBox({
  label,
  n,
  tone,
  prominent = false,
}: {
  label: string
  n: number
  tone: 'indigo' | 'rose' | 'emerald'
  prominent?: boolean
}) {
  const tones: Record<typeof tone, string> = {
    indigo: 'bg-indigo-50 border-indigo-200 text-indigo-900',
    rose: 'bg-rose-50 border-rose-200 text-rose-900',
    emerald: 'bg-emerald-50 border-emerald-200 text-emerald-900',
  }
  return (
    <div
      className={
        'rounded-md border px-4 py-3 flex items-center justify-between ' +
        tones[tone] +
        (prominent ? ' ring-1 ring-emerald-300' : '')
      }
    >
      <span className="text-[12px] font-medium">{label}</span>
      <span className="tabular-nums text-[18px] font-semibold">{n}</span>
    </div>
  )
}
