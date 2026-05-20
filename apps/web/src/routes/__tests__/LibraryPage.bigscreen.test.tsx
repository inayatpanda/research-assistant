/**
 * Big-screen layout — Vitest for the LibraryPage article list.
 *
 * The article list used to be a single `space-y-2` stack which left the
 * right ~1300px of a 27" Mac display as empty whitespace. After the layout
 * refactor it is a responsive grid:
 *   - default: 1 column
 *   - 2xl  (1536px+): 2 columns
 *   - 4xl  (1920px+): 3 columns
 *
 * JSDOM does not actually apply media queries, so we assert the responsive
 * class names are present on the grid container; that's all that's needed
 * for the production Tailwind runtime to switch column counts. We also
 * verify the page container itself uses `max-w-screen-2xl` so it scales.
 */
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, render } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { ProjectContext } from '@/lib/projectContext'
import type { Article } from '@/lib/api'

const ARTICLES: Article[] = Array.from({ length: 6 }).map((_, i) => ({
  id: `a-${i}`,
  user_id: 'u-1',
  project_id: 'p-1',
  title: `Article ${i}`,
  authors: ['Smith J'],
  journal: null,
  year: null,
  volume: null,
  issue: null,
  pages: null,
  doi: null,
  file_ref: null,
  file_type: null,
  abstract: null,
  study_design: null,
  review_status: 'pending',
  exclusion_reason: null,
  conflict_of_interest: null,
  source: 'upload',
  reference_type: 'journal_article',
  url: null,
  created_at: '2026-05-18T00:00:00Z',
  file_url: null,
}))

vi.mock('@/lib/api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/lib/api')>()
  return {
    ...actual,
    projectsApi: {
      ...actual.projectsApi,
      get: vi.fn(async () => ({
        id: 'p-1',
        title: 'Big-screen project',
        study_type: 'Cohort',
        template_journal: null,
      })),
    },
    articlesApi: {
      ...actual.articlesApi,
      list: vi.fn(async () => ARTICLES),
      delete: vi.fn(async () => undefined),
    },
  }
})

vi.mock('@/hooks/useIngest', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/hooks/useIngest')>()
  return {
    ...actual,
    useDuplicates: () => ({ data: [], isLoading: false }),
    useMergeDuplicates: () => ({ mutate: vi.fn(), isPending: false }),
    useLookupDoi: () => ({ mutateAsync: vi.fn(), isPending: false }),
    useImportRis: () => ({ mutateAsync: vi.fn(), isPending: false }),
    useImportBibtex: () => ({ mutateAsync: vi.fn(), isPending: false }),
  }
})

// jsdom doesn't ship ResizeObserver
class ResizeObserverStub {
  observe() {}
  unobserve() {}
  disconnect() {}
}
;(globalThis as unknown as {
  ResizeObserver?: typeof ResizeObserverStub
}).ResizeObserver = ResizeObserverStub

import LibraryPage from '../LibraryPage'

function wrap() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  // Pretend we're on a 2560-wide display for any code that introspects
  // window.innerWidth (Tailwind itself works on CSS media-queries which
  // JSDOM doesn't evaluate, hence we assert via class names).
  Object.defineProperty(window, 'innerWidth', {
    configurable: true,
    value: 2560,
  })
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={['/projects/p-1/library']}>
        <ProjectContext.Provider value={{ projectId: 'p-1', project: null }}>
          <Routes>
            <Route
              path="/projects/:projectId/library"
              element={<LibraryPage />}
            />
          </Routes>
        </ProjectContext.Provider>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

afterEach(cleanup)

describe('LibraryPage — big-screen layout', () => {
  it('uses a wide max-width container so it scales on ultra-wide displays', () => {
    const { container } = wrap()
    // The outer motion.div is the page container.
    const root = container.querySelector('.max-w-screen-2xl')
    expect(root).not.toBeNull()
  })

  it('renders the article list as a responsive grid with 2xl/4xl breakpoints', async () => {
    const { findByTestId } = wrap()
    const grid = await findByTestId('library-article-grid')
    expect(grid.className).toContain('grid')
    expect(grid.className).toContain('grid-cols-1')
    expect(grid.className).toContain('2xl:grid-cols-2')
    expect(grid.className).toContain('4xl:grid-cols-3')
  })
})
