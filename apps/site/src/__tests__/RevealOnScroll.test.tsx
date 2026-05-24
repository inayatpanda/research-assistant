/**
 * Phase v0.3 — RevealOnScroll passthrough test.
 *
 * jsdom's IntersectionObserver shim never fires "intersect", so the
 * wrapper's children should still be rendered into the DOM (with
 * `opacity: 0` styling) — that's enough to keep structure-level
 * assertions on `<FeatureSection>` etc. working.
 */
import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, it, expect } from 'vitest'

import { RevealOnScroll } from '@/components/RevealOnScroll'

afterEach(() => cleanup())

describe('RevealOnScroll', () => {
  it('renders children in the DOM even before they enter the viewport', () => {
    render(
      <RevealOnScroll>
        <p data-testid="reveal-child">Hello world</p>
      </RevealOnScroll>,
    )
    expect(screen.getByTestId('reveal-child')).toBeInTheDocument()
  })
})
