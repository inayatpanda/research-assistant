import { describe, expect, it } from 'vitest'

import {
  pctRectToPixel,
  pixelRectToPct,
  rectsFromSelectionInPage,
  type PctRect,
  type PixelRect,
} from '../pdfCoords'

describe('pixelRectToPct', () => {
  it('returns values in [0,1] for an in-page rect', () => {
    const pct = pixelRectToPct({ x: 50, y: 100, width: 200, height: 30 }, 500, 700)
    expect(pct.x0).toBeCloseTo(0.1)
    expect(pct.y0).toBeCloseTo(100 / 700)
    expect(pct.x1).toBeCloseTo(0.5)
    expect(pct.y1).toBeCloseTo(130 / 700)
  })

  it('clamps off-page rects to [0,1]', () => {
    const pct = pixelRectToPct({ x: -10, y: -10, width: 600, height: 800 }, 500, 700)
    expect(pct.x0).toBe(0)
    expect(pct.y0).toBe(0)
    expect(pct.x1).toBe(1)
    expect(pct.y1).toBe(1)
  })
})

describe('pctRectToPixel', () => {
  it('is the inverse of pixelRectToPct for in-bounds rects', () => {
    const original: PixelRect = { x: 50, y: 100, width: 200, height: 30 }
    const pct = pixelRectToPct(original, 500, 700)
    const back = pctRectToPixel(pct, 500, 700)
    expect(back.x).toBeCloseTo(original.x)
    expect(back.y).toBeCloseTo(original.y)
    expect(back.width).toBeCloseTo(original.width)
    expect(back.height).toBeCloseTo(original.height)
  })

  it('scales correctly when display size changes (zoom invariance)', () => {
    const original: PixelRect = { x: 50, y: 100, width: 200, height: 30 }
    const pct = pixelRectToPct(original, 500, 700)
    // Now render at 2x zoom — page is 1000x1400
    const zoomed = pctRectToPixel(pct, 1000, 1400)
    expect(zoomed.x).toBeCloseTo(100)
    expect(zoomed.y).toBeCloseTo(200)
    expect(zoomed.width).toBeCloseTo(400)
    expect(zoomed.height).toBeCloseTo(60)
  })
})

describe('rectsFromSelectionInPage', () => {
  it('returns rects relative to the page element', () => {
    const pageEl = makeMockPage({ x: 100, y: 200, width: 500, height: 700 })
    const range = makeMockRange([
      // Selection rect at viewport (150, 250) → relative to page = (50, 50)
      { x: 150, y: 250, width: 200, height: 20 },
    ])
    const rects = rectsFromSelectionInPage(range, pageEl)
    expect(rects).toEqual([{ x: 50, y: 50, width: 200, height: 20 }])
  })

  it('filters out zero-size rects (selection artifacts)', () => {
    const pageEl = makeMockPage({ x: 0, y: 0, width: 500, height: 700 })
    const range = makeMockRange([
      { x: 10, y: 20, width: 0, height: 0 },
      { x: 10, y: 20, width: 100, height: 15 },
      { x: 10, y: 40, width: 0.5, height: 15 },
    ])
    const rects = rectsFromSelectionInPage(range, pageEl)
    expect(rects).toHaveLength(1)
    expect(rects[0]).toEqual({ x: 10, y: 20, width: 100, height: 15 })
  })

  it('handles multi-line selections (multiple rects)', () => {
    const pageEl = makeMockPage({ x: 0, y: 0, width: 500, height: 700 })
    const range = makeMockRange([
      { x: 10, y: 20, width: 480, height: 16 },
      { x: 10, y: 40, width: 480, height: 16 },
      { x: 10, y: 60, width: 200, height: 16 },
    ])
    const rects = rectsFromSelectionInPage(range, pageEl)
    expect(rects).toHaveLength(3)
  })
})

// --- mocks ---

function makeMockPage(box: { x: number; y: number; width: number; height: number }): HTMLElement {
  const el = document.createElement('div')
  el.getBoundingClientRect = () =>
    ({
      left: box.x,
      top: box.y,
      right: box.x + box.width,
      bottom: box.y + box.height,
      width: box.width,
      height: box.height,
      x: box.x,
      y: box.y,
      toJSON() {
        return {}
      },
    }) as DOMRect
  return el
}

function makeMockRange(rects: Array<{ x: number; y: number; width: number; height: number }>): Range {
  const domRects = rects.map(
    (r) =>
      ({
        left: r.x,
        top: r.y,
        right: r.x + r.width,
        bottom: r.y + r.height,
        width: r.width,
        height: r.height,
        x: r.x,
        y: r.y,
        toJSON() {
          return {}
        },
      }) as DOMRect,
  )
  const list = Object.assign(domRects, {
    item(i: number) {
      return domRects[i] ?? null
    },
  })
  return {
    getClientRects: () => list as unknown as DOMRectList,
  } as Range
}
