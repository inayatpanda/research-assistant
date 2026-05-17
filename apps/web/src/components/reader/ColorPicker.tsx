import { motion } from 'framer-motion'
import { useEffect } from 'react'

import type { HighlightColour } from '@/lib/api'
import { useReader } from '@/lib/readerStore'
import { highlightColors, sectionLabels } from '@/lib/tokens'
import { cn } from '@/lib/utils'

const ORDER: HighlightColour[] = ['intro', 'method', 'results', 'discussion']

export function ColorPicker() {
  const active = useReader((s) => s.activeColour)
  const setActive = useReader((s) => s.setActiveColour)

  // Keyboard shortcuts: 1/2/3/4 select a colour; Escape clears.
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      // Don't hijack typing in inputs/textareas
      const t = e.target as HTMLElement | null
      if (t && (t.tagName === 'INPUT' || t.tagName === 'TEXTAREA' || t.isContentEditable)) return
      if (e.key === '1') setActive('intro')
      else if (e.key === '2') setActive('method')
      else if (e.key === '3') setActive('results')
      else if (e.key === '4') setActive('discussion')
      else if (e.key === 'Escape') setActive(null)
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [setActive])

  return (
    <div className="flex items-center gap-1.5" role="radiogroup" aria-label="Highlight colour">
      {ORDER.map((c) => {
        const isActive = active === c
        const palette = highlightColors[c]
        return (
          <motion.button
            key={c}
            role="radio"
            aria-checked={isActive}
            aria-label={`Highlight ${sectionLabels[c]} (key ${ORDER.indexOf(c) + 1} or Cmd+${ORDER.indexOf(c) + 1} for current selection)`}
            title={`${sectionLabels[c]}\n${ORDER.indexOf(c) + 1} — pick first, then select\nCmd+${ORDER.indexOf(c) + 1} — highlight current selection`}
            whileHover={{ scale: 1.08 }}
            whileTap={{ scale: 0.94 }}
            onClick={() => setActive(isActive ? null : c)}
            className={cn(
              'relative h-7 w-7 rounded-full border-2 transition-shadow',
              isActive ? 'shadow-md' : 'shadow-none',
            )}
            style={{
              background: palette.fill,
              borderColor: isActive ? palette.solid : 'transparent',
            }}
          >
            {isActive && (
              <motion.span
                layoutId="picker-ring"
                className="absolute inset-[-3px] rounded-full border-2"
                style={{ borderColor: palette.solid }}
              />
            )}
          </motion.button>
        )
      })}
      <div className="ml-2 text-[11px] text-muted-foreground min-w-[180px]">
        {active ? (
          `Selecting → ${sectionLabels[active]}`
        ) : (
          <>Select text, then pick a colour · or <kbd className="px-1 py-px text-[10px] rounded bg-muted">⌘ 1–4</kbd></>
        )}
      </div>
    </div>
  )
}
