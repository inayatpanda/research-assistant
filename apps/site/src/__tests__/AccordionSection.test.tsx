/**
 * Phase v0.3 — AccordionSection behaviour tests.
 *
 * Asserts:
 *   - All items render closed by default.
 *   - Click toggles aria-expanded on the trigger.
 *   - Single mode closes other items when a new one opens.
 */
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, it, expect } from 'vitest'
import { MemoryRouter } from 'react-router-dom'

import { AccordionSection, HomeFaqAccordion, type AccordionItem } from '@/components/AccordionSection'

afterEach(() => cleanup())

const ITEMS: readonly AccordionItem[] = [
  { id: 'a', question: 'First question?', answer: 'First answer.' },
  { id: 'b', question: 'Second question?', answer: 'Second answer.' },
]

describe('AccordionSection', () => {
  it('renders all items closed by default', () => {
    render(<AccordionSection items={ITEMS} />)
    expect(screen.getByTestId('acc-trigger-a')).toHaveAttribute('aria-expanded', 'false')
    expect(screen.getByTestId('acc-trigger-b')).toHaveAttribute('aria-expanded', 'false')
  })

  it('toggles aria-expanded when a trigger is clicked', () => {
    render(<AccordionSection items={ITEMS} />)
    const trigger = screen.getByTestId('acc-trigger-a')
    fireEvent.click(trigger)
    expect(trigger).toHaveAttribute('aria-expanded', 'true')
    fireEvent.click(trigger)
    expect(trigger).toHaveAttribute('aria-expanded', 'false')
  })

  it('closes the previously-open item when single mode is on', () => {
    render(<AccordionSection items={ITEMS} mode="single" />)
    fireEvent.click(screen.getByTestId('acc-trigger-a'))
    fireEvent.click(screen.getByTestId('acc-trigger-b'))
    expect(screen.getByTestId('acc-trigger-a')).toHaveAttribute('aria-expanded', 'false')
    expect(screen.getByTestId('acc-trigger-b')).toHaveAttribute('aria-expanded', 'true')
  })

  it('keeps multiple items open in multi mode', () => {
    render(<AccordionSection items={ITEMS} mode="multi" />)
    fireEvent.click(screen.getByTestId('acc-trigger-a'))
    fireEvent.click(screen.getByTestId('acc-trigger-b'))
    expect(screen.getByTestId('acc-trigger-a')).toHaveAttribute('aria-expanded', 'true')
    expect(screen.getByTestId('acc-trigger-b')).toHaveAttribute('aria-expanded', 'true')
  })
})

describe('HomeFaqAccordion', () => {
  it('renders the six pre-baked FAQ items', () => {
    render(
      <MemoryRouter>
        <HomeFaqAccordion />
      </MemoryRouter>,
    )
    expect(screen.getByTestId('acc-trigger-local-first')).toBeInTheDocument()
    expect(screen.getByTestId('acc-trigger-sync')).toBeInTheDocument()
    expect(screen.getByTestId('acc-trigger-stats')).toBeInTheDocument()
    expect(screen.getByTestId('acc-trigger-import')).toBeInTheDocument()
    expect(screen.getByTestId('acc-trigger-offline')).toBeInTheDocument()
    expect(screen.getByTestId('acc-trigger-open-source')).toBeInTheDocument()
  })
})
