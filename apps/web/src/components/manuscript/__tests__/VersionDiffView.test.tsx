import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'

import { VersionDiffView } from '../VersionDiffView'

describe('VersionDiffView', () => {
  afterEach(cleanup)

  it('renders empty-state when sections record is empty', () => {
    render(
      <VersionDiffView
        diff={{
          base_snapshot_id: 's1',
          target_snapshot_id: 's2',
          sections: {},
        }}
      />,
    )
    expect(screen.getByTestId('diff-empty')).toBeTruthy()
  })

  it('renders <ins> for additions and <del> for deletions', () => {
    render(
      <VersionDiffView
        diff={{
          base_snapshot_id: 's1',
          target_snapshot_id: null,
          sections: {
            Introduction: [
              { type: '-', line: '<p>Original</p>' },
              { type: '+', line: '<p>Revised</p>' },
            ],
          },
        }}
      />,
    )
    const adds = document.querySelectorAll('ins[data-diff-type="add"]')
    const dels = document.querySelectorAll('del[data-diff-type="del"]')
    expect(adds.length).toBe(1)
    expect(dels.length).toBe(1)
    expect(adds[0].textContent).toContain('Revised')
    expect(dels[0].textContent).toContain('Original')
  })

  it('renders the loading state', () => {
    render(<VersionDiffView diff={undefined} loading />)
    expect(screen.getByText(/Computing diff/i)).toBeTruthy()
  })
})
