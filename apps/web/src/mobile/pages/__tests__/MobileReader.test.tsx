/**
 * Phase M2.3 — MobileReader smoke tests.
 *
 *   1. The reader renders the article text as paragraphs of words.
 *   2. A long-press (simulated via the test-only imperative handle)
 *      enters selection mode and shows the colour-swatch bar.
 *   3. Tapping a colour pill calls ``highlightsApi.create`` and clears
 *      the selection on success.
 *   4. Tapping an existing highlight opens the edit BottomSheet.
 */
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { createRef } from 'react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

const hoisted = vi.hoisted(() => ({
  article: {
    id: 'a-1',
    user_id: 'u-1',
    project_id: 'p-1',
    title: 'Outcomes of hip replacement',
    authors: ['Smith J'],
    journal: 'BMJ',
    year: 2024,
    volume: null,
    issue: null,
    pages: null,
    doi: null,
    pmid: null,
    file_ref: null,
    file_type: null,
    abstract:
      'Hip replacement surgery remains effective.\n\nResults showed durable outcomes over five years.',
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
  highlights: [
    {
      id: 'h-1',
      user_id: 'u-1',
      article_id: 'a-1',
      page_number: 1,
      selected_text: 'durable outcomes',
      colour: 'results' as const,
      section: 'Results' as const,
      bounding_coords: { rects: [{ x0: 0, y0: 0, x1: 1, y1: 0.05 }] },
      user_note: 'Important durability finding.',
      ai_summary: null,
      sort_order: 0,
      created_at: '2026-01-03T00:00:00Z',
    },
  ],
  createMock: vi.fn(),
  listMock: vi.fn(),
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
      list: hoisted.listMock,
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
  hoisted.createMock.mockReset()
  hoisted.createMock.mockResolvedValue({
    ...hoisted.highlights[0],
    id: 'h-new',
    selected_text: 'Hip replacement',
    colour: 'intro',
    section: 'Introduction',
  })
  hoisted.listMock.mockReset()
  hoisted.listMock.mockResolvedValue(hoisted.highlights)
})

afterEach(() => {
  cleanup()
  vi.clearAllMocks()
})

describe('MobileReader', () => {
  it('renders the article body as individual word spans', async () => {
    renderAt()
    await waitFor(() =>
      expect(screen.getByTestId('mreader-word-0').textContent).toBe('Hip'),
    )
    expect(screen.getByTestId('mreader-word-1').textContent).toBe(
      'replacement',
    )
    expect(screen.getByTestId('mreader-title').textContent).toContain(
      'Outcomes of hip replacement',
    )
  })

  it('shows the colour swatch bar when a selection is active', async () => {
    const ref = createRef<MobileReaderTestHandle>()
    renderAt(ref)
    await waitFor(() => screen.getByTestId('mreader-word-0'))
    // Force a selection covering words 0..1 ("Hip replacement").
    ref.current!.__forceSelection(0, 1)
    await waitFor(() => screen.getByTestId('mreader-swatch-bar'))
    expect(screen.getByTestId('mreader-pill-intro')).toBeTruthy()
    expect(screen.getByTestId('mreader-pill-method')).toBeTruthy()
    expect(screen.getByTestId('mreader-pill-results')).toBeTruthy()
    expect(screen.getByTestId('mreader-pill-discussion')).toBeTruthy()
  })

  it('tapping a colour pill calls highlightsApi.create with the selected text', async () => {
    const ref = createRef<MobileReaderTestHandle>()
    renderAt(ref)
    await waitFor(() => screen.getByTestId('mreader-word-0'))
    ref.current!.__forceSelection(0, 1)
    await waitFor(() => screen.getByTestId('mreader-pill-intro'))
    fireEvent.click(screen.getByTestId('mreader-pill-intro'))
    await waitFor(() => expect(hoisted.createMock).toHaveBeenCalled())
    const [articleId, body] = hoisted.createMock.mock.calls[0]
    expect(articleId).toBe('a-1')
    expect(body.colour).toBe('intro')
    expect(body.section).toBe('Introduction')
    expect(body.selected_text).toBe('Hip replacement')
  })

  it('tapping an existing highlight opens the edit bottom sheet', async () => {
    renderAt()
    // The fixture highlight is "durable outcomes" — find the first
    // word and click it.
    await waitFor(() => screen.getByTestId('mreader-word-0'))
    // Walk the rendered words to find the one that says "durable".
    const allWords = screen.getAllByTestId(/^mreader-word-/)
    const durable = allWords.find((el) => el.textContent === 'durable')
    expect(durable).toBeTruthy()
    fireEvent.click(durable!)
    await waitFor(() => screen.getByTestId('mreader-edit-sheet'))
    expect(
      screen
        .getByTestId('mreader-edit-sheet')
        .textContent?.includes('durable outcomes'),
    ).toBeTruthy()
  })
})
