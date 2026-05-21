/**
 * Phase D3.5 — MobileReader PDF-mode highlight tests.
 *
 *   1. An existing highlight stored with ``bounding_coords.type ===
 *      'pdf'`` renders as an SVG ``<rect>`` overlay on the matching
 *      page (we verify the test-id surfaced by the overlay).
 *   2. A new highlight forced via the test handle round-trips
 *      ``highlightsApi.create`` with the PDF anchor shape: ``page``,
 *      ``rects[]``, and a ``bounding_coords.type === 'pdf'`` payload.
 *
 * We do not run real pdf.js in jsdom — the page-level smoke is in
 * ``MobileReader.pdf.test.tsx``. Here we only need the PDF reader to
 * mount so we can exercise the parent's mutation wiring.
 */
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, render, screen, waitFor, fireEvent } from '@testing-library/react'
import { createRef } from 'react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

const hoisted = vi.hoisted(() => ({
  article: {
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
    abstract: 'Fallback extracted text.',
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
  pdfHighlight: {
    id: 'h-pdf-1',
    user_id: 'u-1',
    article_id: 'a-pdf',
    page_number: 1,
    selected_text: 'durable five-year outcomes',
    colour: 'results' as const,
    section: 'Results' as const,
    bounding_coords: {
      type: 'pdf' as const,
      page: 1,
      text: 'durable five-year outcomes',
      rects: [{ x0: 0.12, y0: 0.21, x1: 0.48, y1: 0.24 }],
    },
    user_note: null,
    ai_summary: null,
    sort_order: 0,
    created_at: '2026-01-03T00:00:00Z',
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
      list: vi.fn(async () => [hoisted.pdfHighlight]),
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

function buildFakePdf() {
  const page = {
    pageNumber: 1,
    getViewport: () => ({ width: 400, height: 600, transform: [1, 0, 0, -1, 0, 600] }),
    render: () => ({ promise: Promise.resolve(), cancel: () => undefined }),
    getTextContent: async () => ({ items: [] }),
    cleanup: () => undefined,
  }
  return {
    numPages: 2,
    getPage: async () => page,
    destroy: async () => undefined,
  }
}

const fakeGetDocument = (_url: string) => ({
  promise: Promise.resolve(buildFakePdf()) as Promise<unknown>,
})

beforeEach(() => {
  Object.defineProperty(HTMLCanvasElement.prototype, 'getContext', {
    value: vi.fn(() => ({} as unknown)),
    configurable: true,
  })
  hoisted.createMock.mockReset()
  hoisted.createMock.mockResolvedValue({
    ...hoisted.pdfHighlight,
    id: 'h-new',
  })
})

afterEach(() => {
  cleanup()
  vi.clearAllMocks()
})

function renderAt(ref?: React.Ref<MobileReaderTestHandle>) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={['/m/reader/a-pdf']}>
        <Routes>
          <Route
            path="/m/reader/:articleId"
            element={
              <MobileReader ref={ref} pdfjsGetDocument={fakeGetDocument} />
            }
          />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('MobileReader — PDF highlights', () => {
  it('renders an existing PDF-anchored highlight as an SVG rect', async () => {
    renderAt()
    await waitFor(() => screen.getByTestId('mpdf-overlay-1'))
    // The overlay rect's test id is mpdf-h-<hl-id>-<rect-idx>.
    await waitFor(() =>
      expect(screen.getByTestId('mpdf-h-h-pdf-1-0')).toBeTruthy(),
    )
  })

  it('forces a new PDF highlight and posts a pdf-typed anchor', async () => {
    const ref = createRef<MobileReaderTestHandle>()
    renderAt(ref)
    await waitFor(() => screen.getByTestId('mpdf-root'))
    // Drive a fake selection through the imperative test hook.
    ref.current!.__forcePdfHighlight!({
      page: 2,
      text: 'novel finding A',
      rects: [{ x0: 0.1, y0: 0.2, x1: 0.5, y1: 0.23 }],
    })
    // The pending draft surfaces a PDF colour-swatch bar.
    await waitFor(() => screen.getByTestId('mreader-pdf-swatch-bar'))
    fireEvent.click(screen.getByTestId('mreader-pdf-pill-results'))
    await waitFor(() => expect(hoisted.createMock).toHaveBeenCalled())
    const [articleId, body] = hoisted.createMock.mock.calls[0]
    expect(articleId).toBe('a-pdf')
    expect(body.page_number).toBe(2)
    expect(body.colour).toBe('results')
    expect(body.bounding_coords.type).toBe('pdf')
    expect(body.bounding_coords.page).toBe(2)
    expect(body.bounding_coords.text).toBe('novel finding A')
    expect(body.bounding_coords.rects[0].x0).toBe(0.1)
  })
})
