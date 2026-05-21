/**
 * Phase 5c — LearnTooltip component tests.
 *
 * Verifies:
 *   1. The inline icon-only variant renders an info icon + link.
 *   2. The default variant renders the children wrapped in a link.
 *   3. Unknown concepts gracefully fall back to plain text.
 */
import { cleanup, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, describe, expect, it } from 'vitest'

import { LearnTooltip } from '../LearnTooltip'

function wrap(node: React.ReactNode) {
  return render(<MemoryRouter>{node}</MemoryRouter>)
}

afterEach(cleanup)

describe('LearnTooltip', () => {
  it('renders an icon-only trigger when iconOnly is set', () => {
    wrap(
      <LearnTooltip concept="anova" iconOnly>
        One-way ANOVA
      </LearnTooltip>,
    )
    // Children are rendered verbatim, plus an info link beside.
    expect(screen.getByText('One-way ANOVA')).toBeDefined()
    const trigger = screen.getByTestId('learn-tooltip-trigger')
    expect(trigger).toBeDefined()
    // The link should resolve the alias "anova" to the canonical slug
    // "one-way-anova" so the Learn page deep-links the right entry.
    expect(trigger.getAttribute('href')).toContain('slug=one-way-anova')
    expect(trigger.getAttribute('data-concept')).toBe('anova')
  })

  it('renders the default (wrapped) variant with a dotted underline link', () => {
    wrap(<LearnTooltip concept="prisma">PRISMA flow</LearnTooltip>)
    const trigger = screen.getByTestId('learn-tooltip-trigger')
    expect(trigger).toBeDefined()
    expect(trigger.textContent).toContain('PRISMA flow')
    expect(trigger.getAttribute('href')).toContain('slug=prisma')
  })

  it('renders children as plain text for unknown concepts', () => {
    wrap(<LearnTooltip concept="not-a-real-concept">Some label</LearnTooltip>)
    // No link — just the children text node.
    expect(screen.getByText('Some label')).toBeDefined()
    expect(screen.queryByTestId('learn-tooltip-trigger')).toBeNull()
  })
})
