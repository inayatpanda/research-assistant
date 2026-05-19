/**
 * Phase 13.5 (MP13.5) — vitest for AnalysisPlanBuilder.
 */
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

const { listMock, createMock, updateMock, deleteMock } = vi.hoisted(() => ({
  listMock: vi.fn(),
  createMock: vi.fn(),
  updateMock: vi.fn(),
  deleteMock: vi.fn(),
}))

vi.mock('@/lib/api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/lib/api')>()
  return {
    ...actual,
    analysisPlansApi: {
      ...actual.analysisPlansApi,
      list: listMock,
      create: createMock,
      update: updateMock,
      delete: deleteMock,
    },
  }
})

import { AnalysisPlanBuilder } from '../AnalysisPlanBuilder'

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
  listMock.mockReset()
  createMock.mockReset()
  updateMock.mockReset()
  deleteMock.mockReset()
})

describe('AnalysisPlanBuilder', () => {
  beforeEach(() => {
    listMock.mockResolvedValue([])
  })

  it('shows empty state and create input', async () => {
    wrap(<AnalysisPlanBuilder projectId="p-1" />)
    expect(screen.getByTestId('analysis-plan-builder')).toBeTruthy()
    await waitFor(() =>
      expect(screen.getByText(/No plans yet/i)).toBeTruthy(),
    )
  })

  it('creates a new plan via the form', async () => {
    createMock.mockResolvedValue({
      id: 'plan-1',
      project_id: 'p-1',
      name: 'My plan',
      description: null,
      steps: [],
      created_at: '2026-05-18T00:00:00Z',
      updated_at: '2026-05-18T00:00:00Z',
    })
    wrap(<AnalysisPlanBuilder projectId="p-1" />)
    await waitFor(() => expect(listMock).toHaveBeenCalled())
    fireEvent.change(screen.getByTestId('plan-new-name'), {
      target: { value: 'My plan' },
    })
    fireEvent.click(screen.getByTestId('plan-create'))
    await waitFor(() => expect(createMock).toHaveBeenCalled())
    expect(createMock.mock.calls[0][1]).toMatchObject({ name: 'My plan' })
  })

  it('lists existing plans in the side rail', async () => {
    listMock.mockResolvedValue([
      {
        id: 'plan-a',
        project_id: 'p-1',
        name: 'Plan A',
        description: null,
        steps: [],
        created_at: '2026-05-18T00:00:00Z',
        updated_at: '2026-05-18T00:00:00Z',
      },
    ])
    wrap(<AnalysisPlanBuilder projectId="p-1" />)
    await waitFor(() =>
      expect(screen.getByTestId('plan-tab-plan-a')).toBeTruthy(),
    )
  })
})
