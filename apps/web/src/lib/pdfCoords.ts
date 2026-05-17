/**
 * PDF highlight coordinate transforms.
 *
 * Highlights are stored as page-relative percentages so they survive any zoom or
 * page reflow. At render time we recompute pixel rects from the page's current
 * display size.
 *
 * Coordinate origin: top-left of the page element. y increases downward.
 * Percentages are in [0, 1] of the page's natural width/height.
 */

export type PctRect = { x0: number; y0: number; x1: number; y1: number }
export type PixelRect = { x: number; y: number; width: number; height: number }

const clamp01 = (n: number): number => Math.max(0, Math.min(1, n))

export function pixelRectToPct(
  rect: PixelRect,
  pageWidth: number,
  pageHeight: number,
): PctRect {
  return {
    x0: clamp01(rect.x / pageWidth),
    y0: clamp01(rect.y / pageHeight),
    x1: clamp01((rect.x + rect.width) / pageWidth),
    y1: clamp01((rect.y + rect.height) / pageHeight),
  }
}

export function pctRectToPixel(
  pct: PctRect,
  displayWidth: number,
  displayHeight: number,
): PixelRect {
  return {
    x: pct.x0 * displayWidth,
    y: pct.y0 * displayHeight,
    width: (pct.x1 - pct.x0) * displayWidth,
    height: (pct.y1 - pct.y0) * displayHeight,
  }
}

/**
 * Walk a selection Range's client rects, expressed relative to the page element.
 * Filters out sub-pixel artifacts that browsers sometimes emit at line breaks.
 */
export function rectsFromSelectionInPage(range: Range, pageEl: HTMLElement): PixelRect[] {
  const page = pageEl.getBoundingClientRect()
  const out: PixelRect[] = []
  for (const r of Array.from(range.getClientRects())) {
    if (r.width < 1 || r.height < 1) continue
    out.push({
      x: r.left - page.left,
      y: r.top - page.top,
      width: r.width,
      height: r.height,
    })
  }
  return out
}
