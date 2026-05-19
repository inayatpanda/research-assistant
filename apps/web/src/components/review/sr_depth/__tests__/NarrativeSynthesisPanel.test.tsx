/**
 * MP19 — NarrativeSynthesisPanel vitest.
 */
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

const { listMock, createMock, updateMock, removeMock, pushMock } = vi.hoisted(() => ({
  listMock: vi.fn(),
  createMock: vi.fn(),
  updateMock: vi.fn(),
  removeMock: vi.fn(),
  pushMock: vi.fn(),
}))

vi.mock('@/lib/api', async (orig) => {
  const real = (await orig()) as Record<string, unknown>
  return {
    ...real,
    narrativeSynthesisApi: {
      list: listMock,
      create: createMock,
      update: updateMock,
      remove: removeMock,
      push: pushMock,
    },
  }
})

import { NarrativeSynthesisPanel } from '../NarrativeSynthesisPanel'

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
  removeMock.mockReset()
  pushMock.mockReset()
})

describe('NarrativeSynthesisPanel', () => {
  it('renders the existing entries from the API', async () => {
    listMock.mockResolvedValue([
      {
        id: 'e1',
        review_id: 'r1',
        outcome_label: 'Pain',
        instrument: 'VAS',
        range_text: '0-10',
        direction: 'lower_better',
        narrative_html: '<p>Reduced over time.</p>',
        study_citations: [],
        created_at: '2026-05-19T00:00:00Z',
        updated_at: '2026-05-19T00:00:00Z',
      },
    ])
    wrap(<NarrativeSynthesisPanel projectId="p1" />)
    expect(await screen.findByText('Pain')).toBeTruthy()
    expect(screen.getByText('VAS')).toBeTruthy()
  })

  it('creates a new entry when the user clicks Add', async () => {
    listMock.mockResolvedValue([])
    createMock.mockResolvedValue({
      id: 'e1',
      review_id: 'r1',
      outcome_label: 'Function',
      instrument: 'OKS',
      range_text: '0-48',
      direction: 'higher_better',
      narrative_html: '',
      study_citations: [],
      created_at: '2026-05-19T00:00:00Z',
      updated_at: '2026-05-19T00:00:00Z',
    })
    wrap(<NarrativeSynthesisPanel projectId="p1" />)
    fireEvent.change(screen.getByLabelText('Outcome'), {
      target: { value: 'Function' },
    })
    fireEvent.change(screen.getByLabelText('Instrument'), {
      target: { value: 'OKS' },
    })
    fireEvent.click(screen.getByRole('button', { name: /^add$/i }))
    await waitFor(() => {
      expect(createMock).toHaveBeenCalledWith(
        'p1',
        expect.objectContaining({
          outcome_label: 'Function',
          instrument: 'OKS',
        }),
      )
    })
  })
})
