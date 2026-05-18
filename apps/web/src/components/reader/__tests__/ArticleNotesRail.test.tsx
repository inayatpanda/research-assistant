import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import {
  cleanup,
  fireEvent,
  render,
  screen,
} from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

const { listMock } = vi.hoisted(() => ({
  listMock: vi.fn(),
}))

vi.mock('@/hooks/useArticleNote', () => ({
  useArticleNote: () => ({
    value: '',
    setValue: vi.fn(),
    saving: false,
    savedAt: null,
  }),
}))

vi.mock('@/hooks/useHighlights', () => ({
  useHighlights: () => ({ data: listMock(), isLoading: false }),
}))

vi.mock('@/lib/readerStore', () => ({
  useReader: (sel: (s: { setCurrentPage: (n: number) => void }) => unknown) =>
    sel({ setCurrentPage: vi.fn() }),
}))

import { ArticleNotesRail } from '../ArticleNotesRail'

function wrap(node: React.ReactNode) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return render(
    <QueryClientProvider client={client}>{node}</QueryClientProvider>,
  )
}

const SAMPLE_HIGHLIGHTS = [
  {
    id: 'h1',
    user_id: 'u1',
    article_id: 'a1',
    page_number: 3,
    selected_text: 'Anterior approach reduced opioid use.',
    colour: 'results' as const,
    section: 'Results' as const,
    bounding_coords: { rects: [{ x0: 0, y0: 0, x1: 0.5, y1: 0.05 }] },
    user_note: 'My paraphrase',
    ai_summary: null,
    sort_order: 0,
    created_at: '2024-01-01T00:00:00Z',
  },
]

describe('ArticleNotesRail — MP12.6 click-to-popover', () => {
  afterEach(() => {
    cleanup()
    listMock.mockReset()
  })

  it('fires onOpenHighlight with the row rect when a highlight row is clicked', () => {
    listMock.mockReturnValue(SAMPLE_HIGHLIGHTS)
    const onOpen = vi.fn()
    wrap(
      <ArticleNotesRail articleId="a1" onOpenHighlight={onOpen} />,
    )
    const row = document.querySelector(
      '[data-highlight-row="h1"]',
    ) as HTMLElement
    expect(row).toBeTruthy()
    fireEvent.click(row)
    expect(onOpen).toHaveBeenCalledTimes(1)
    const [highlight, rect] = onOpen.mock.calls[0]
    expect(highlight.id).toBe('h1')
    // jsdom returns a DOMRect-like object
    expect(rect).toBeTruthy()
    expect(typeof rect.top).toBe('number')
  })

  it('does not throw when onOpenHighlight is not provided', () => {
    listMock.mockReturnValue(SAMPLE_HIGHLIGHTS)
    wrap(<ArticleNotesRail articleId="a1" />)
    const row = document.querySelector(
      '[data-highlight-row="h1"]',
    ) as HTMLElement
    expect(() => fireEvent.click(row)).not.toThrow()
  })

  it('renders the empty state when no highlights', () => {
    listMock.mockReturnValue([])
    wrap(<ArticleNotesRail articleId="a1" />)
    expect(screen.getByText(/No highlights yet/i)).toBeTruthy()
  })
})
