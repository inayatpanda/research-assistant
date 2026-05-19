import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeAll, beforeEach, describe, expect, it, vi } from 'vitest'

// Polyfills for Radix UI inside jsdom.
beforeAll(() => {
  if (!Element.prototype.scrollIntoView) {
    Element.prototype.scrollIntoView = vi.fn()
  }
  if (!('hasPointerCapture' in Element.prototype)) {
    Element.prototype.hasPointerCapture = vi.fn(() => false)
    Element.prototype.releasePointerCapture = vi.fn()
  }
})

const { psmRunMock } = vi.hoisted(() => ({ psmRunMock: vi.fn() }))

vi.mock('@/lib/api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/lib/api')>()
  return {
    ...actual,
    psmApi: { run: psmRunMock },
  }
})

import type { Dataset } from '@/lib/api'
import { PSMWizard } from '../PSMWizard'

const DATASET: Dataset = {
  id: 'ds-1',
  project_id: 'p-1',
  filename: 'cohort.csv',
  file_type: 'csv',
  n_rows: 200,
  n_columns: 4,
  created_at: '2026-05-18T00:00:00Z',
  variables: [
    {
      id: 'v-1',
      dataset_id: 'ds-1',
      name: 'treatment',
      position: 0,
      inferred_type: 'nominal',
      user_type: null,
      n_missing: 0,
      sample_values: ['0', '1'],
    },
    {
      id: 'v-2',
      dataset_id: 'ds-1',
      name: 'age',
      position: 1,
      inferred_type: 'numeric',
      user_type: null,
      n_missing: 0,
      sample_values: ['65', '72', '58'],
    },
    {
      id: 'v-3',
      dataset_id: 'ds-1',
      name: 'bmi',
      position: 2,
      inferred_type: 'numeric',
      user_type: null,
      n_missing: 0,
      sample_values: ['25.1', '28.4', '22.0'],
    },
  ],
}

function wrap(node: React.ReactNode) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  return render(
    <MemoryRouter>
      <QueryClientProvider client={client}>{node}</QueryClientProvider>
    </MemoryRouter>,
  )
}

afterEach(() => {
  cleanup()
  psmRunMock.mockReset()
})

describe('PSMWizard — happy path', () => {
  beforeEach(() => {
    psmRunMock.mockResolvedValue({
      matched_dataset_id: 'ds-2',
      n_treated_total: 50,
      n_control_total: 150,
      n_treated_matched: 48,
      n_control_matched: 48,
      caliper_sd: 0.2,
      balance_before: [
        { covariate: 'age', smd: 0.45, mean_treated: 70, mean_control: 65 },
        { covariate: 'bmi', smd: 0.31, mean_treated: 27, mean_control: 25 },
      ],
      balance_after: [
        { covariate: 'age', smd: 0.03, mean_treated: 68, mean_control: 68 },
        { covariate: 'bmi', smd: 0.05, mean_treated: 26, mean_control: 26 },
      ],
      max_smd_before: 0.45,
      max_smd_after: 0.05,
    })
  })

  it('renders the balance table after a successful run', async () => {
    wrap(
      <PSMWizard
        open
        onOpenChange={() => {}}
        projectId="p-1"
        dataset={DATASET}
      />,
    )

    // Pick the only binary nominal column.
    const treatmentTrigger = screen.getByTestId('psm-treatment')
    fireEvent.click(treatmentTrigger)
    fireEvent.click(await screen.findByRole('option', { name: 'treatment' }))

    // Tick at least one covariate.
    const ageCheckbox = await screen.findByTestId('psm-cov-age')
    fireEvent.click(ageCheckbox)

    // Run.
    fireEvent.click(screen.getByRole('button', { name: /run matching/i }))
    await waitFor(() => expect(psmRunMock).toHaveBeenCalledTimes(1))
    expect(psmRunMock.mock.calls[0][2]).toMatchObject({
      treatment_col: 'treatment',
      covariate_cols: ['age'],
      caliper_sd: 0.2,
    })

    const table = await screen.findByTestId('psm-balance-table')
    expect(table).toBeTruthy()
    // The balance table has rows for both covariates (full result rendered).
    expect(table.textContent).toContain('age')
    expect(table.textContent).toContain('bmi')
    expect(table.textContent).toContain('0.450')
    expect(table.textContent).toContain('0.030')
  })
})

describe('PSMWizard — validation', () => {
  it('does not call the API when no covariates are picked', async () => {
    wrap(
      <PSMWizard
        open
        onOpenChange={() => {}}
        projectId="p-1"
        dataset={DATASET}
      />,
    )
    const trigger = screen.getByTestId('psm-treatment')
    fireEvent.click(trigger)
    fireEvent.click(await screen.findByRole('option', { name: 'treatment' }))
    fireEvent.click(screen.getByRole('button', { name: /run matching/i }))
    await new Promise((r) => setTimeout(r, 30))
    expect(psmRunMock).not.toHaveBeenCalled()
  })
})
