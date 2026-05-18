import { motion } from 'framer-motion'
import { useSearchParams } from 'react-router-dom'

import { type ReviewStage } from '@/lib/api'
import { cn } from '@/lib/utils'

const STAGES: { id: ReviewStage; label: string }[] = [
  { id: 'title_abstract', label: 'Title / Abstract' },
  { id: 'full_text', label: 'Full text' },
]

export function useScreeningStage(): [ReviewStage, (s: ReviewStage) => void] {
  const [params, setParams] = useSearchParams()
  const raw = params.get('stage') as ReviewStage | null
  const active: ReviewStage = STAGES.find((s) => s.id === raw)?.id ?? 'title_abstract'
  const set = (s: ReviewStage) => {
    const next = new URLSearchParams(params)
    next.set('stage', s)
    setParams(next, { replace: true })
  }
  return [active, set]
}

export function ScreeningStageTabs({
  active,
  onChange,
  counts,
}: {
  active: ReviewStage
  onChange: (s: ReviewStage) => void
  counts?: Partial<Record<ReviewStage, number>>
}) {
  return (
    <div className="flex gap-1 border-b border-border">
      {STAGES.map((s) => {
        const isActive = active === s.id
        const n = counts?.[s.id] ?? 0
        return (
          <button
            key={s.id}
            onClick={() => onChange(s.id)}
            className={cn(
              'relative px-3.5 py-2.5 text-[13px] font-medium transition-colors flex items-center gap-2',
              isActive ? 'text-foreground' : 'text-muted-foreground hover:text-foreground',
            )}
          >
            {s.label}
            <span
              className={cn(
                'inline-flex items-center justify-center min-w-[22px] h-[16px] px-1 rounded text-[10px] tabular-nums',
                isActive ? 'bg-foreground text-background' : 'bg-muted text-muted-foreground',
              )}
            >
              {n}
            </span>
            {isActive && (
              <motion.div
                layoutId="screening-tab"
                className="absolute left-2 right-2 -bottom-[1px] h-[2px] rounded-full bg-accent"
              />
            )}
          </button>
        )
      })}
    </div>
  )
}
