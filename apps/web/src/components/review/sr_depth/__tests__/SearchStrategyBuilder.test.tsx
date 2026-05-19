/**
 * MP19 — SearchStrategyBuilder vitest.
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

const { listMock, createMock, updateMock, removeMock } = vi.hoisted(() => ({
  listMock: vi.fn(),
  createMock: vi.fn(),
  updateMock: vi.fn(),
  removeMock: vi.fn(),
}))

vi.mock('@/lib/api', async (orig) => {
  const real = (await orig()) as Record<string, unknown>
  return {
    ...real,
    searchStrategiesApi: {
      list: listMock,
      create: createMock,
      update: updateMock,
      remove: removeMock,
      translate: vi.fn(),
    },
  }
})

import { SearchStrategyBuilder } from '../SearchStrategyBuilder'

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
})

describe('SearchStrategyBuilder', () => {
  it('inserting an operator appends it to the query textarea', () => {
    listMock.mockResolvedValue([])
    wrap(<SearchStrategyBuilder projectId="p1" />)
    const ta = screen.getByTestId('ss-query') as HTMLTextAreaElement
    fireEvent.change(ta, { target: { value: 'diabetes' } })
    fireEvent.click(screen.getByTestId('op-AND'))
    expect(ta.value).toBe('diabetes AND')
    fireEvent.click(screen.getByTestId('op-OR'))
    expect(ta.value).toBe('diabetes AND OR')
  })

  it('posts the query when the user clicks save', async () => {
    listMock.mockResolvedValue([])
    createMock.mockResolvedValue({
      id: 's1',
      project_id: 'p1',
      review_id: 'r1',
      name: 'Untitled strategy',
      database: 'PubMed',
      query_text: 'diabetes',
      mesh_term_ids: [],
      translated_from_id: null,
      is_locked: false,
      warnings: null,
      created_at: '2026-05-19T00:00:00Z',
      updated_at: '2026-05-19T00:00:00Z',
    })
    wrap(<SearchStrategyBuilder projectId="p1" />)
    fireEvent.change(screen.getByTestId('ss-query'), {
      target: { value: 'diabetes' },
    })
    fireEvent.click(screen.getByRole('button', { name: /save strategy/i }))
    await waitFor(() => {
      expect(createMock).toHaveBeenCalledWith(
        'p1',
        expect.objectContaining({ query_text: 'diabetes', database: 'PubMed' }),
      )
    })
  })
})
