import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { CostColumnBinder } from '../CostColumnBinder'
import type { CostColumnBinding } from '@/lib/api'

describe('CostColumnBinder', () => {
  afterEach(cleanup)

  it('renders the empty-state hint when no bindings present', () => {
    render(
      <CostColumnBinder
        availableColumns={['cost_total', 'utility', 'time_months']}
        bindings={[]}
        onChange={vi.fn()}
      />,
    )
    expect(screen.getByTestId('cost-column-binder')).toBeTruthy()
    // The empty-state hint is wrapped across <strong> tags, so match the
    // leading prose only.
    expect(screen.getByText(/No bindings yet/i)).toBeTruthy()
  })

  it('emits onChange when adding a binding via the Add button', () => {
    const onChange = vi.fn()
    const bindings: CostColumnBinding[] = []
    render(
      <CostColumnBinder
        availableColumns={['cost_total', 'utility']}
        bindings={bindings}
        onChange={onChange}
      />,
    )
    fireEvent.click(screen.getByRole('button', { name: /Add binding/i }))
    // First column from availableColumns + default role cost_total
    expect(onChange).toHaveBeenCalledWith([
      { col: 'cost_total', role: 'cost_total' },
    ])
  })

  it('removes a binding by index when the trash button is clicked', () => {
    const onChange = vi.fn()
    const bindings: CostColumnBinding[] = [
      { col: 'cost_total', role: 'cost_total' },
      { col: 'utility', role: 'utility_score' },
    ]
    render(
      <CostColumnBinder
        availableColumns={['cost_total', 'utility']}
        bindings={bindings}
        onChange={onChange}
      />,
    )
    // Remove the first row.
    fireEvent.click(
      screen.getByRole('button', { name: /Remove binding cost_total/ }),
    )
    expect(onChange).toHaveBeenCalledWith([
      { col: 'utility', role: 'utility_score' },
    ])
  })
})
