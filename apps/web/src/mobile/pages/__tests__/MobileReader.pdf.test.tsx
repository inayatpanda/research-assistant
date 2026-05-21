/**
 * Phase D3.5 — MobileReader PDF-mode smoke tests.
 *
 *   1. When the article carries a ``file_url`` + ``application/pdf``
 *      file_type, the reader mounts the PDF reader and renders a
 *      canvas-bearing page element. We do not exercise real pdf.js
 *      under jsdom — instead we inject a stubbed ``getDocument`` via
 *      the ``pdfjsGetDocument`` prop so the page count + chip work
 *      deterministically.
 *   2. When no file_url is present, the reader falls back to the M2
 *      text-mode rendering (the existing word-span path).
 *   3. The page chip + zoom buttons exist and the chip reflects the
 *      current "current page" state.
 */
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

const hoisted = vi.hoisted(() => ({
  articlePdf: {
    id: 'a-pdf',
    user_id: 'u-1',
    project_id: 'p-1',
    title: 'PDF paper',
    authors: ['Smith J'],
    journal: 'BMJ',
    year: 2024,
    volume: null,
    issue: null,
    pages: null,
    doi: null,
    pmid: null,
    file_ref: { backend: 'local', key: 'k' },
    file_type: 'application/pdf',
    abstract: 'Fallback extracted text body for offline mode.',
    study_design: null,
    review_status: 'pending' as const,
    exclusion_reason: null,
    conflict_of_interest: null,
    source: 'upload' as const,
    reference_type: 'journal_article' as const,
    url: null,
    created_at: '2026-01-02T00:00:00Z',
    file_url: 'http://api.test/files/k',
  },
  articleText: {
    id: 'a-txt',
    user_id: 'u-1',
    project_id: 'p-1',
    title: 'Text-only paper',
    authors: ['Doe J'],
    journal: 'JAMA',
    year: 2023,
    volume: null,
    issue: null,
    pages: null,
    doi: null,
    pmid: null,
    file_ref: null,
    file_type: null,
    abstract: 'Only extracted text available here on the device.',
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
  highlights: [] as unknown[],
  getMock: vi.fn(),
}))

vi.mock('@/lib/api', async () => {
  const actual = await vi.importActual<Record<string, unknown>>('@/lib/api')
  return {
    ...actual,
    articlesApi: {
      list: vi.fn(),
      upload: vi.fn(),
      get: hoisted.getMock,
      update: vi.fn(),
      delete: vi.fn(),
    },
    highlightsApi: {
      list: vi.fn(async () => hoisted.highlights),
      create: vi.fn(),
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

import MobileReader from '@/mobile/pages/MobileReader'

// Minimal pdf.js stub. The MobilePdfReader only touches numPages,
// getPage().getViewport(), .render() (returns a {promise, cancel}),
// and getTextContent(). We can satisfy all of these with a hand-rolled
// object — no canvas needed because we never call canvas getContext in
// jsdom-friendly tests if we keep state.viewport undefined. For the
// happy-path render we need to give it a fake CanvasRenderingContext.
function buildFakePdf(numPages: number) {
  const page = {
    pageNumber: 1,
    getViewport: () => ({ width: 400, height: 600, transform: [1, 0, 0, -1, 0, 600] }),
    render: () => ({ promise: Promise.resolve(), cancel: () => undefined }),
    getTextContent: async () => ({
      items: [
        { str: 'hello', transform: [1, 0, 0, 1, 10, 580], width: 40, height: 12 },
        { str: 'world', transform: [1, 0, 0, 1, 60, 580], width: 40, height: 12 },
      ],
    }),
    cleanup: () => undefined,
  }
  return {
    numPages,
    getPage: async () => page,
    destroy: async () => undefined,
  }
}

const fakeGetDocument = (_url: string) => ({
  promise: Promise.resolve(buildFakePdf(5)) as Promise<unknown>,
})

// jsdom doesn't ship a real CanvasRenderingContext; the only call our
// component makes is canvas.getContext('2d') which returns null and
// then the fake render task resolves immediately. Stub minimally so
// `ctx` is truthy and `.render` receives a valid CanvasRenderingContext.
beforeEach(() => {
  Object.defineProperty(HTMLCanvasElement.prototype, 'getContext', {
    value: vi.fn(() => ({} as unknown)),
    configurable: true,
  })
  hoisted.getMock.mockReset()
})

afterEach(() => {
  cleanup()
  vi.clearAllMocks()
})

function renderAt(article: typeof hoisted.articlePdf | typeof hoisted.articleText) {
  hoisted.getMock.mockResolvedValue(article)
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[`/m/reader/${article.id}`]}>
        <Routes>
          <Route
            path="/m/reader/:articleId"
            element={<MobileReader pdfjsGetDocument={fakeGetDocument} />}
          />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('MobileReader — PDF mode', () => {
  it('mounts the PDF reader when the article has a file_url + pdf file_type', async () => {
    renderAt(hoisted.articlePdf)
    await waitFor(() => screen.getByTestId('mpdf-root'))
    expect(screen.getByTestId('mpdf-page-1')).toBeTruthy()
    expect(screen.getByTestId('mpdf-page-chip').textContent).toContain('Page')
    expect(screen.getByTestId('mpdf-page-chip').textContent).toContain('5')
  })

  it('falls back to text mode when no PDF file_url is present', async () => {
    renderAt(hoisted.articleText)
    await waitFor(() => screen.getByTestId('mreader-body'))
    expect(screen.queryByTestId('mpdf-root')).toBeNull()
    // Word spans from the abstract should render.
    expect(screen.getByTestId('mreader-word-0').textContent).toBe('Only')
  })

  it('overflow menu can flip PDF mode back to extracted-text reading mode', async () => {
    renderAt(hoisted.articlePdf)
    await waitFor(() => screen.getByTestId('mpdf-root'))
    fireEvent.click(screen.getByTestId('mreader-overflow'))
    await waitFor(() => screen.getByTestId('mreader-overflow-sheet'))
    fireEvent.click(screen.getByTestId('mreader-toggle-mode'))
    await waitFor(() => screen.getByTestId('mreader-body'))
    expect(screen.queryByTestId('mpdf-root')).toBeNull()
  })
})
