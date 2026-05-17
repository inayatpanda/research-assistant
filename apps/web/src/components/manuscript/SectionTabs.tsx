import { motion } from 'framer-motion'
import { useSearchParams } from 'react-router-dom'

import type { ManuscriptSectionName } from '@/lib/api'
import { cn } from '@/lib/utils'

const TABS: { id: ManuscriptSectionName | 'final'; label: string }[] = [
  { id: 'Abstract', label: 'Abstract' },
  { id: 'Introduction', label: 'Introduction' },
  { id: 'Methodology', label: 'Methodology' },
  { id: 'Results', label: 'Results' },
  { id: 'Discussion', label: 'Discussion' },
  { id: 'Conclusion', label: 'Conclusion' },
  { id: 'final', label: 'Final' },
]

export type ManuscriptTab = ManuscriptSectionName | 'final'

export function useManuscriptTab(): [ManuscriptTab, (t: ManuscriptTab) => void] {
  const [params, setParams] = useSearchParams()
  const raw = params.get('section') as ManuscriptTab | null
  const active: ManuscriptTab = TABS.find((t) => t.id === raw)?.id ?? 'Introduction'
  const set = (t: ManuscriptTab) => {
    const next = new URLSearchParams(params)
    next.set('section', t)
    setParams(next, { replace: true })
  }
  return [active, set]
}

export function SectionTabs({
  active,
  onChange,
  wordCounts,
}: {
  active: ManuscriptTab
  onChange: (t: ManuscriptTab) => void
  wordCounts?: Partial<Record<ManuscriptTab, number>>
}) {
  return (
    <div className="border-b border-border">
      <div className="flex gap-1 overflow-x-auto">
        {TABS.map((t) => {
          const isActive = active === t.id
          const n = wordCounts?.[t.id] ?? 0
          return (
            <button
              key={t.id}
              onClick={() => onChange(t.id)}
              className={cn(
                'relative px-3.5 py-3 text-[13px] font-medium transition-colors flex items-center gap-2 whitespace-nowrap',
                isActive ? 'text-foreground' : 'text-muted-foreground hover:text-foreground',
              )}
            >
              {t.label}
              {t.id !== 'final' && (
                <span
                  className={cn(
                    'inline-flex items-center justify-center min-w-[24px] h-[16px] px-1 rounded text-[10px] tabular-nums',
                    isActive ? 'bg-foreground text-background' : 'bg-muted text-muted-foreground',
                  )}
                >
                  {n}
                </span>
              )}
              {isActive && (
                <motion.div
                  layoutId="manuscript-tab"
                  className="absolute left-2 right-2 -bottom-[1px] h-[2px] rounded-full bg-accent"
                />
              )}
            </button>
          )
        })}
      </div>
    </div>
  )
}
