/**
 * MP19 — MeSHBrowser vitest.
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

const { searchMock, cacheMock, upsertMock, deleteMock } = vi.hoisted(() => ({
  searchMock: vi.fn(),
  cacheMock: vi.fn(),
  upsertMock: vi.fn(),
  deleteMock: vi.fn(),
}))

vi.mock('@/lib/api', async (orig) => {
  const real = (await orig()) as Record<string, unknown>
  return {
    ...real,
    meshApi: {
      search: searchMock,
      suggest: vi.fn(),
      listCache: cacheMock,
      upsertCache: upsertMock,
      deleteCache: deleteMock,
    },
  }
})

import { MeSHBrowser } from '../MeSHBrowser'

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
  searchMock.mockReset()
  cacheMock.mockReset()
  upsertMock.mockReset()
  deleteMock.mockReset()
})

describe('MeSHBrowser', () => {
  it('renders search results when the user submits a query', async () => {
    cacheMock.mockResolvedValue([])
    searchMock.mockResolvedValue({
      query: 'diabetes',
      hits: [
        {
          descriptor_ui: 'D003920',
          descriptor_name: 'Diabetes Mellitus',
          scope_note: 'A condition...',
          tree_numbers: ['C19.246'],
          entry_terms: ['Diabetes'],
        },
      ],
    })

    wrap(<MeSHBrowser projectId="p1" />)
    fireEvent.change(screen.getByTestId('mesh-search-input'), {
      target: { value: 'diabetes' },
    })
    fireEvent.click(screen.getByRole('button', { name: /search/i }))

    await waitFor(() => {
      expect(searchMock).toHaveBeenCalledWith('p1', 'diabetes')
    })
    expect(await screen.findByText('Diabetes Mellitus')).toBeTruthy()
    expect(screen.getByTestId('mesh-hit-D003920')).toBeTruthy()
  })

  it('renders zero-results message when the API returns an empty list', async () => {
    cacheMock.mockResolvedValue([])
    searchMock.mockResolvedValue({ query: 'asdfghjkl', hits: [] })
    wrap(<MeSHBrowser projectId="p1" />)
    fireEvent.change(screen.getByTestId('mesh-search-input'), {
      target: { value: 'asdfghjkl' },
    })
    fireEvent.click(screen.getByRole('button', { name: /search/i }))
    expect(await screen.findByText(/no descriptors found/i)).toBeTruthy()
  })
})
