/**
 * DEMO-FIX-C — Vitest for EditChartLabelsDialog.
 *
 * Mocks the analyses API so the form's three inputs flow into the
 * updateChartLabels call, and verifies the prefilled state mirrors the
 * incoming `initial` overrides.
 */
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import {
  cleanup,
  fireEvent,
  render,
  waitFor,
} from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

const { updateChartLabelsMock } = vi.hoisted(() => ({
  updateChartLabelsMock: vi.fn(),
}))

vi.mock('@/lib/api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/lib/api')>()
  return {
    ...actual,
    analysesApi: {
      ...actual.analysesApi,
      updateChartLabels: updateChartLabelsMock,
    },
  }
})

import { EditChartLabelsDialog } from '../EditChartLabelsDialog'

function wrap(node: React.ReactNode) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  return render(
    <QueryClientProvider client={client}>{node}</QueryClientProvider>,
  )
}

afterEach(() => {
  cleanup()
  updateChartLabelsMock.mockReset()
})

describe('EditChartLabelsDialog', () => {
  beforeEach(() => {
    updateChartLabelsMock.mockResolvedValue({
      id: 'a-1',
      project_id: 'p-1',
      dataset_id: 'ds-1',
      question_type: 'group_comparison',
      chosen_test: 'independent_t',
      recommendation_rationale: 'r',
      variables: {},
      status: 'completed',
      created_at: '2026-05-18T00:00:00Z',
      result: {
        summary: {},
        assumptions: {},
        chart: { x_label_override: 'X' },
        ai_interpretation: null,
      },
    })
  })

  it('prefills inputs from the initial overrides', () => {
    const { getByTestId } = wrap(
      <EditChartLabelsDialog
        open
        onOpenChange={() => {}}
        projectId="p-1"
        datasetId="ds-1"
        analysisId="a-1"
        initial={{
          x_label_override: 'BMI group',
          y_label_override: 'VAS pain',
          title_override: 'Pain by BMI',
        }}
      />,
    )
    expect((getByTestId('x-label-input') as HTMLInputElement).value).toBe('BMI group')
    expect((getByTestId('y-label-input') as HTMLInputElement).value).toBe('VAS pain')
    expect((getByTestId('title-input') as HTMLInputElement).value).toBe('Pain by BMI')
  })

  it('Save submits the form via the API', async () => {
    const { getByTestId } = wrap(
      <EditChartLabelsDialog
        open
        onOpenChange={() => {}}
        projectId="p-1"
        datasetId="ds-1"
        analysisId="a-1"
        initial={{}}
      />,
    )
    fireEvent.change(getByTestId('x-label-input'), {
      target: { value: 'Treatment arm' },
    })
    fireEvent.change(getByTestId('y-label-input'), {
      target: { value: 'Pain (VAS, 0-10)' },
    })
    fireEvent.change(getByTestId('title-input'), {
      target: { value: 'My title' },
    })
    fireEvent.click(getByTestId('save-chart-labels'))
    await waitFor(() => {
      expect(updateChartLabelsMock).toHaveBeenCalledWith('p-1', 'a-1', {
        x_label_override: 'Treatment arm',
        y_label_override: 'Pain (VAS, 0-10)',
        title_override: 'My title',
      })
    })
  })

  it('renders the description prompting the user about the override behaviour', () => {
    const { getByText } = wrap(
      <EditChartLabelsDialog
        open
        onOpenChange={() => {}}
        projectId="p-1"
        datasetId="ds-1"
        analysisId="a-1"
        initial={{}}
      />,
    )
    // The description explains the override-vs-display-label precedence.
    expect(getByText(/Override the x-axis/i)).toBeDefined()
  })
})
