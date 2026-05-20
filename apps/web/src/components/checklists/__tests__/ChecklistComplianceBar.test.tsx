import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'

import { ChecklistComplianceBar } from '../ChecklistComplianceBar'

afterEach(cleanup)

describe('ChecklistComplianceBar', () => {
  it('renders the compliance percentage + raw counts', () => {
    render(
      <ChecklistComplianceBar
        pct={75.0}
        passCount={9}
        failCount={1}
        unclearCount={2}
        naCount={0}
        totalCount={12}
      />,
    )
    expect(screen.getByText('75.0% compliance')).toBeDefined()
    expect(screen.getByText(/9 pass.+1 fail.+2 unclear.+0 N\/A/)).toBeDefined()
  })

  it('exposes a progressbar with aria-valuenow set to the compliance pct', () => {
    render(
      <ChecklistComplianceBar
        pct={42.5}
        passCount={3}
        failCount={2}
        unclearCount={3}
        naCount={0}
        totalCount={8}
      />,
    )
    const bar = screen.getByRole('progressbar')
    expect(bar.getAttribute('aria-valuenow')).toBe('42.5')
    expect(bar.getAttribute('aria-valuemin')).toBe('0')
    expect(bar.getAttribute('aria-valuemax')).toBe('100')
  })
})
