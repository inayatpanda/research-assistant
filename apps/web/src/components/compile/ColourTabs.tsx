import { motion } from 'framer-motion'
import { useSearchParams } from 'react-router-dom'

import type { HighlightColour } from '@/lib/api'
import { highlightColors, sectionLabels } from '@/lib/tokens'
import { cn } from '@/lib/utils'

const ORDER: HighlightColour[] = ['intro', 'method', 'results', 'discussion']

export function useActiveColour(): [HighlightColour, (c: HighlightColour) => void] {
  const [params, setParams] = useSearchParams()
  const raw = params.get('tab') as HighlightColour | null
  const active: HighlightColour = ORDER.includes(raw as HighlightColour) ? (raw as HighlightColour) : 'intro'
  const setActive = (c: HighlightColour) => {
    const next = new URLSearchParams(params)
    next.set('tab', c)
    setParams(next, { replace: true })
  }
  return [active, setActive]
}

export function ColourTabs({
  active,
  onChange,
  counts,
}: {
  active: HighlightColour
  onChange: (c: HighlightColour) => void
  counts?: Partial<Record<HighlightColour, number>>
}) {
  return (
    <div className="border-b border-border">
      <div className="flex gap-1">
        {ORDER.map((c) => {
          const palette = highlightColors[c]
          const isActive = active === c
          const n = counts?.[c] ?? 0
          return (
            <button
              key={c}
              onClick={() => onChange(c)}
              className={cn(
                'relative px-4 py-3 text-[13px] font-medium transition-colors flex items-center gap-2',
                isActive ? 'text-foreground' : 'text-muted-foreground hover:text-foreground',
              )}
            >
              <span
                className="inline-block h-2.5 w-2.5 rounded-full"
                style={{ background: palette.solid }}
                aria-hidden
              />
              {sectionLabels[c]}
              <span
                className={cn(
                  'inline-flex items-center justify-center min-w-[18px] h-[18px] px-1.5 rounded-full text-[10px] tabular-nums',
                  isActive ? 'bg-foreground text-background' : 'bg-muted text-muted-foreground',
                )}
              >
                {n}
              </span>
              {isActive && (
                <motion.div
                  layoutId="compile-tab"
                  className="absolute left-2 right-2 -bottom-[1px] h-[2px] rounded-full"
                  style={{ background: palette.solid }}
                />
              )}
            </button>
          )
        })}
      </div>
    </div>
  )
}
