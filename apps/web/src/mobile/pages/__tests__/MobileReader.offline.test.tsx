/**
 * Phase M2.3 — MobileReader offline-write smoke test.
 *
 * When ``navigator.onLine === false`` and a highlight create fails
 * with a network error, the reader surfaces a toast that mentions
 * "Offline" and keeps the selection unchanged so the user can retry
 * after reconnecting.
 */
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { createRef } from 'react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

const toastHoisted = vi.hoisted(() => ({
  error: vi.fn(),
  success: vi.fn(),
  info: vi.fn(),
  message: vi.fn(),
}))

vi.mock('sonner', async () => {
  const actual = await vi.importActual<Record<string, unknown>>('sonner')
  return {
    ...actual,
    toast: toastHoisted,
  }
})

const hoisted = vi.hoisted(() => ({
  article: {
    id: 'a-1',
    user_id: 'u-1',
    project_id: 'p-1',
    title: 'Offline test article',
    authors: ['Doe J'],
    journal: null,
    year: null,
    volume: null,
    issue: null,
    pages: null,
    doi: null,
    pmid: null,
    file_ref: null,
    file_type: null,
    abstract: 'Some short abstract.\n\nA second paragraph here.',
    study_design: null,
    review_status: 'pending' as const,
    exclusion_reason: null,
    conflict_of_interest: null,
    source: 'doi' as const,
    reference_type: 'journal_article' as const,
    url: null,
    created_at: '2026-01-02T00:00:00Z',
    file_url: null,
  },
  createMock: vi.fn(),
}))

vi.mock('@/lib/api', async () => {
  const actual = await vi.importActual<Record<string, unknown>>('@/lib/api')
  return {
    ...actual,
    articlesApi: {
      list: vi.fn(),
      upload: vi.fn(),
      get: vi.fn(async () => hoisted.article),
      update: vi.fn(),
      delete: vi.fn(),
    },
    highlightsApi: {
      list: vi.fn(async () => []),
      create: hoisted.createMock,
      update: vi.fn(),
      delete: vi.fn(),
      summarise: vi.fn(),
    },
  }
})

vi.mock('@/mobile/lib/offlineLearn', async () => ({
  cacheable: async (_key: string, fetcher: () => Promise<unknown>) => ({
    data: await fetcher(),
    offline: false,
  }),
  entryKey: (c: string, s: string) => `${c}:${s}`,
  listKey: (c: string) => `__list:${c}`,
}))

import MobileReader, {
  type MobileReaderTestHandle,
} from '@/mobile/pages/MobileReader'

function renderAt(ref?: React.Ref<MobileReaderTestHandle>) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={['/m/reader/a-1']}>
        <Routes>
          <Route
            path="/m/reader/:articleId"
            element={<MobileReader ref={ref} />}
          />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

beforeEach(() => {
  toastHoisted.error.mockReset()
  hoisted.createMock.mockReset()
  hoisted.createMock.mockRejectedValue(new Error('Network error'))
  Object.defineProperty(window.navigator, 'onLine', {
    configurable: true,
    value: false,
  })
})

afterEach(() => {
  cleanup()
  vi.clearAllMocks()
  Object.defineProperty(window.navigator, 'onLine', {
    configurable: true,
    value: true,
  })
})

describe('MobileReader (offline)', () => {
  it('shows an Offline toast on highlight write failure and keeps selection', async () => {
    const ref = createRef<MobileReaderTestHandle>()
    renderAt(ref)
    await waitFor(() => screen.getByTestId('mreader-word-0'))
    ref.current!.__forceSelection(0, 1)
    await waitFor(() => screen.getByTestId('mreader-pill-intro'))
    fireEvent.click(screen.getByTestId('mreader-pill-intro'))
    await waitFor(() => expect(toastHoisted.error).toHaveBeenCalled())
    expect(toastHoisted.error.mock.calls[0][0]).toMatch(/offline/i)
    // Selection should still be live (we didn't clear it on failure).
    expect(screen.getByTestId('mreader-swatch-bar')).toBeTruthy()
  })
})
