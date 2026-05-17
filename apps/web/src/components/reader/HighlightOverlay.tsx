import { motion } from 'framer-motion'

import type { Highlight } from '@/lib/api'
import { highlightBloom } from '@/lib/motion'
import { pctRectToPixel } from '@/lib/pdfCoords'
import { highlightColors } from '@/lib/tokens'

/**
 * Renders all highlights for a given page as absolute-positioned divs over the
 * react-pdf page element. Pixel positions are recomputed from percentage coords
 * on every render — so any zoom or page-size change just works.
 */
export function HighlightOverlay({
  highlights,
  pageWidth,
  pageHeight,
  onClickHighlight,
}: {
  highlights: Highlight[]
  pageWidth: number
  pageHeight: number
  onClickHighlight: (h: Highlight) => void
}) {
  if (pageWidth === 0 || pageHeight === 0) return null
  return (
    <div
      className="absolute inset-0 pointer-events-none"
      style={{ width: pageWidth, height: pageHeight }}
    >
      {highlights.map((h) => (
        <HighlightRects key={h.id} highlight={h} pageWidth={pageWidth} pageHeight={pageHeight} onClick={onClickHighlight} />
      ))}
    </div>
  )
}

function HighlightRects({
  highlight,
  pageWidth,
  pageHeight,
  onClick,
}: {
  highlight: Highlight
  pageWidth: number
  pageHeight: number
  onClick: (h: Highlight) => void
}) {
  const palette = highlightColors[highlight.colour]
  return (
    <>
      {highlight.bounding_coords.rects.map((rect, i) => {
        const px = pctRectToPixel(rect, pageWidth, pageHeight)
        return (
          <motion.button
            key={`${highlight.id}-${i}`}
            variants={highlightBloom}
            initial="initial"
            animate="animate"
            onClick={(e) => {
              e.stopPropagation()
              onClick(highlight)
            }}
            className="absolute rounded-[2px] cursor-pointer pointer-events-auto transition-shadow hover:shadow-[0_0_0_2px_var(--hl-ring)]"
            style={
              {
                left: px.x,
                top: px.y,
                width: px.width,
                height: px.height,
                background: palette.fill,
                // CSS var for the hover ring colour
                ['--hl-ring' as string]: palette.ring,
                border: 'none',
                padding: 0,
              } as React.CSSProperties
            }
            aria-label={`Highlight: ${highlight.section} — ${highlight.selected_text.slice(0, 80)}`}
          />
        )
      })}
    </>
  )
}
