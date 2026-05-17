import { motion } from 'framer-motion'
import { useEffect, useRef } from 'react'

import type { HighlightColour } from '@/lib/api'
import { highlightColors, sectionLabels } from '@/lib/tokens'

const ORDER: HighlightColour[] = ['intro', 'method', 'results', 'discussion']

/**
 * Floating mini-toolbar that appears just below a text selection, offering
 * the four section colours. Click a colour to highlight the current selection.
 *
 * Self-dismisses on outside mousedown.
 */
export function SelectionToolbar({
  anchorRect,
  onPick,
  onDismiss,
}: {
  anchorRect: DOMRect
  onPick: (colour: HighlightColour) => void
  onDismiss: () => void
}) {
  const ref = useRef<HTMLDivElement>(null)

  // Outside mousedown dismisses (deferred so the mousedown that may have
  // selected the text doesn't immediately collapse us).
  useEffect(() => {
    function onDown(e: MouseEvent) {
      if (ref.current && ref.current.contains(e.target as Node)) return
      onDismiss()
    }
    const t = setTimeout(() => document.addEventListener('mousedown', onDown), 0)
    return () => {
      clearTimeout(t)
      document.removeEventListener('mousedown', onDown)
    }
  }, [onDismiss])

  // Position: centred horizontally on the end of the selection, 6px below.
  // Clamp to viewport so the toolbar never clips offscreen.
  const TOOLBAR_W = 196
  const margin = 8
  const left = Math.max(
    margin,
    Math.min(window.innerWidth - TOOLBAR_W - margin, anchorRect.right - TOOLBAR_W / 2),
  )
  const top = Math.min(window.innerHeight - 48, anchorRect.bottom + 6)

  return (
    <motion.div
      ref={ref}
      data-selection-toolbar
      initial={{ opacity: 0, y: -4, scale: 0.96 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      transition={{ duration: 0.14, ease: [0.16, 1, 0.3, 1] }}
      onMouseDown={(e) => e.preventDefault()}  // don't steal focus / collapse the selection
      className="fixed z-50 flex items-center gap-1 rounded-full bg-white border border-border px-2 py-1.5"
      style={{
        left,
        top,
        width: TOOLBAR_W,
        boxShadow: '0 8px 24px rgba(15,17,23,0.16)',
      }}
      role="toolbar"
      aria-label="Highlight current selection"
    >
      {ORDER.map((c) => {
        const palette = highlightColors[c]
        return (
          <motion.button
            key={c}
            whileHover={{ scale: 1.12 }}
            whileTap={{ scale: 0.92 }}
            onClick={(e) => {
              e.stopPropagation()
              onPick(c)
            }}
            aria-label={`Highlight ${sectionLabels[c]}`}
            title={`${sectionLabels[c]} (Cmd+${ORDER.indexOf(c) + 1})`}
            className="h-7 w-7 rounded-full border-2 transition-shadow hover:shadow-md"
            style={{ background: palette.fill, borderColor: palette.solid }}
          />
        )
      })}
      <div className="mx-1 h-5 w-px bg-border" />
      <button
        onClick={(e) => {
          e.stopPropagation()
          onDismiss()
        }}
        className="text-[11px] text-muted-foreground hover:text-foreground px-1"
        aria-label="Dismiss"
        title="Esc"
      >
        ✕
      </button>
    </motion.div>
  )
}
