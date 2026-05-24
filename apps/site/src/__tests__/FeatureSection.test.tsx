/**
 * Phase D3 — FeatureSection test.
 *
 * Asserts that the reusable feature block renders the eyebrow, title,
 * bullets, screenshot, and respects the `side` prop ordering at lg+.
 */
import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, it, expect } from 'vitest'

import { FeatureSection } from '@/components/FeatureSection'

afterEach(() => cleanup())

const baseProps = {
  id: 'demo',
  eyebrow: 'Library',
  title: 'A test feature title.',
  body: 'A test body sentence.',
  bullets: ['First bullet point.', 'Second bullet point.'],
  screenshots: [
    {
      src: '/screenshots/library.png',
      alt: 'Library screenshot',
    },
  ],
} as const

describe('FeatureSection', () => {
  it('renders the eyebrow, title, body, bullets and screenshot', () => {
    render(<FeatureSection {...baseProps} side="right" />)
    expect(screen.getByTestId('feature-section-demo')).toBeInTheDocument()
    expect(screen.getByTestId('feature-eyebrow')).toHaveTextContent('Library')
    expect(screen.getByRole('heading', { level: 2 })).toHaveTextContent(
      /a test feature title/i,
    )
    const bullets = screen.getByTestId('feature-bullets')
    expect(bullets).toHaveTextContent(/first bullet point/i)
    expect(bullets).toHaveTextContent(/second bullet point/i)
    const img = screen.getByRole('img', { name: /library screenshot/i }) as HTMLImageElement
    expect(img.getAttribute('src')).toBe('/screenshots/library.png')
  })

  it('places the visual column on the left when side="left"', () => {
    render(<FeatureSection {...baseProps} side="left" />)
    const section = screen.getByTestId('feature-section-demo')
    // We assert by inspecting the order class so the snapshot stays
    // visual-only and doesn't depend on rendered widths.
    const visualCol = section.querySelector('.lg\\:order-1')
    const copyCol = section.querySelector('.lg\\:order-2')
    expect(visualCol).not.toBeNull()
    expect(copyCol).not.toBeNull()
    expect(copyCol).toHaveTextContent(/a test feature title/i)
  })
})
