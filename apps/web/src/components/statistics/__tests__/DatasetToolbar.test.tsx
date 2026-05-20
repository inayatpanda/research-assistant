/**
 * Statistics layout refactor — Vitest for DatasetToolbar.
 *
 * Verifies:
 *   1. With ≤3 datasets, the selector renders as pills (one per dataset).
 *   2. With >3 datasets, the selector renders as a shadcn Select dropdown.
 *   3. With no active dataset, PSM and New analysis buttons are disabled.
 *   4. Clicking a pill fires onSelect with the pill's dataset id.
 */
import { cleanup, fireEvent, render } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { Dataset } from '@/lib/api'

import { DatasetToolbar } from '../DatasetToolbar'

function ds(id: string, filename: string): Dataset {
  return {
    id,
    project_id: 'p-1',
    filename,
    file_type: 'text/csv',
    n_rows: 60,
    n_columns: 13,
    created_at: '2026-05-18T00:00:00Z',
    variables: [],
    header_sanitisation_report: [],
  }
}

afterEach(cleanup)

describe('DatasetToolbar', () => {
  it('renders datasets as pills when there are 3 or fewer', () => {
    const datasets = [ds('a', 'one.csv'), ds('b', 'two.csv'), ds('c', 'three.csv')]
    const { getByTestId, queryByTestId } = render(
      <DatasetToolbar
        datasets={datasets}
        activeDatasetId="b"
        onSelect={() => {}}
        onUpload={() => {}}
        onNewAnalysis={() => {}}
        onPsm={() => {}}
      />,
    )
    expect(getByTestId('dataset-toolbar-pills')).toBeDefined()
    expect(getByTestId('dataset-pill-a')).toBeDefined()
    expect(getByTestId('dataset-pill-b')).toBeDefined()
    expect(getByTestId('dataset-pill-c')).toBeDefined()
    // The Select dropdown branch is not used at this count.
    expect(queryByTestId('dataset-toolbar-select')).toBeNull()
  })

  it('renders a Select dropdown when there are more than 3 datasets', () => {
    const datasets = [
      ds('a', 'one.csv'),
      ds('b', 'two.csv'),
      ds('c', 'three.csv'),
      ds('d', 'four.csv'),
    ]
    const { getByTestId, queryByTestId } = render(
      <DatasetToolbar
        datasets={datasets}
        activeDatasetId="a"
        onSelect={() => {}}
        onUpload={() => {}}
        onNewAnalysis={() => {}}
        onPsm={() => {}}
      />,
    )
    expect(getByTestId('dataset-toolbar-select')).toBeDefined()
    expect(queryByTestId('dataset-toolbar-pills')).toBeNull()
  })

  it('disables PSM and New analysis when there is no active dataset', () => {
    const { getByTestId } = render(
      <DatasetToolbar
        datasets={[]}
        activeDatasetId={null}
        onSelect={() => {}}
        onUpload={() => {}}
        onNewAnalysis={() => {}}
        onPsm={() => {}}
      />,
    )
    expect(
      (getByTestId('dataset-toolbar-psm') as HTMLButtonElement).disabled,
    ).toBe(true)
    expect(
      (getByTestId('dataset-toolbar-new-analysis') as HTMLButtonElement)
        .disabled,
    ).toBe(true)
  })

  it('fires onSelect with the dataset id when a pill is clicked', () => {
    const onSelect = vi.fn()
    const datasets = [ds('a', 'one.csv'), ds('b', 'two.csv')]
    const { getByTestId } = render(
      <DatasetToolbar
        datasets={datasets}
        activeDatasetId="a"
        onSelect={onSelect}
        onUpload={() => {}}
        onNewAnalysis={() => {}}
        onPsm={() => {}}
      />,
    )
    fireEvent.click(getByTestId('dataset-pill-b'))
    expect(onSelect).toHaveBeenCalledWith('b')
  })
})
