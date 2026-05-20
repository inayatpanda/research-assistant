import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

const { searchMock, importMock } = vi.hoisted(() => ({
  searchMock: vi.fn(),
  importMock: vi.fn(),
}))

vi.mock('@/lib/api', async (orig) => {
  const real = (await orig()) as Record<string, unknown>
  return {
    ...real,
    ingestApi: {
      searchPubMed: searchMock,
      importFromMetadata: importMock,
      lookupDoi: vi.fn(),
      importRis: vi.fn(),
      importBibtex: vi.fn(),
      duplicates: vi.fn(),
      merge: vi.fn(),
    },
  }
})

import { PubMedSearchDialog } from '../PubMedSearchDialog'

function wrap(node: React.ReactNode) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return render(
    <QueryClientProvider client={client}>{node}</QueryClientProvider>,
  )
}

const SAMPLE_RESULT = {
  title: 'Anterior approach in THA',
  authors: ['Wei Chen', 'Linh Nguyen'],
  journal: 'JAMA',
  year: 2023,
  volume: '329',
  issue: '21',
  pages: '1843-1852',
  doi: '10.1001/jama.2023.7770',
  pmid: '37251234',
  abstract: 'BACKGROUND: Surgical approach impacts recovery. METHODS: 600 patients.',
  source: 'pubmed' as const,
  mesh_terms: ['Arthroplasty, Replacement, Hip', 'Humans'],
  affiliations: [
    'Department of Orthopaedic Surgery, Stanford University, USA.',
  ],
  article_types: ['Journal Article', 'Randomized Controlled Trial'],
}

describe('PubMedSearchDialog (MP12.6 v2)', () => {
  afterEach(() => {
    cleanup()
    searchMock.mockReset()
    importMock.mockReset()
  })

  it('runs a search and shows results in the list pane', async () => {
    searchMock.mockResolvedValueOnce([SAMPLE_RESULT])
    wrap(<PubMedSearchDialog projectId="p1" />)
    fireEvent.click(screen.getByRole('button', { name: /Search PubMed/i }))

    const input = await screen.findByLabelText('Query')
    fireEvent.change(input, { target: { value: 'hip arthroplasty' } })
    const buttons = screen.getAllByRole('button', { name: 'Search' })
    fireEvent.click(buttons[buttons.length - 1])

    await waitFor(() => expect(searchMock).toHaveBeenCalled())
    await waitFor(() => {
      expect(screen.getByTestId('pubmed-results-pane')).toBeTruthy()
    })
    expect(screen.getByText('Anterior approach in THA')).toBeTruthy()
  })

  it('opens the preview pane with MeSH + affiliations + PubMed link when a row is previewed', async () => {
    searchMock.mockResolvedValueOnce([SAMPLE_RESULT])
    wrap(<PubMedSearchDialog projectId="p1" />)
    fireEvent.click(screen.getByRole('button', { name: /Search PubMed/i }))

    const input = await screen.findByLabelText('Query')
    fireEvent.change(input, { target: { value: 'hip' } })
    const buttons = screen.getAllByRole('button', { name: 'Search' })
    fireEvent.click(buttons[buttons.length - 1])

    // Wait for results, then click the Preview (Eye) button on the first row
    await waitFor(() => screen.getByTestId('pubmed-results-pane'))
    fireEvent.click(screen.getByRole('button', { name: 'Preview' }))

    const preview = screen.getByTestId('pubmed-preview-pane')
    expect(preview.textContent).toContain('Anterior approach in THA')
    expect(preview.textContent).toContain('Stanford')
    expect(preview.textContent).toContain('Arthroplasty, Replacement, Hip')
    expect(preview.textContent).toContain('Randomized Controlled Trial')

    const link = screen.getByRole('link', { name: /View on PubMed/i })
    expect(link.getAttribute('href')).toBe(
      'https://pubmed.ncbi.nlm.nih.gov/37251234/',
    )
  })

  it('shows empty-state and clears stale results when a follow-up search returns zero hits (#L-PM-empty)', async () => {
    // First search returns 1 result, second returns []
    searchMock.mockResolvedValueOnce([SAMPLE_RESULT])
    searchMock.mockResolvedValueOnce([])
    wrap(<PubMedSearchDialog projectId="p1" />)
    fireEvent.click(screen.getByRole('button', { name: /Search PubMed/i }))

    const input = await screen.findByLabelText('Query')
    fireEvent.change(input, { target: { value: 'hip arthroplasty' } })
    const searchBtns = screen.getAllByRole('button', { name: 'Search' })
    fireEvent.click(searchBtns[searchBtns.length - 1])

    await waitFor(() => screen.getByTestId('pubmed-results-pane'))
    expect(screen.getByText('Anterior approach in THA')).toBeTruthy()
    // Import button visible when results present
    expect(
      screen.queryByRole('button', { name: /Import \d+ articles?/ }),
    ).toBeTruthy()

    // Second query → zero results
    fireEvent.change(input, { target: { value: 'xyzzyqwerty' } })
    const btns2 = screen.getAllByRole('button', { name: 'Search' })
    fireEvent.click(btns2[btns2.length - 1])

    await waitFor(() =>
      expect(screen.queryByTestId('pubmed-results-pane')).toBeNull(),
    )
    // Empty-state pane is visible, with the helper copy
    expect(screen.getByTestId('pubmed-empty-state').textContent).toMatch(
      /No PubMed results/i,
    )
    // Import button gone — stale "Import N articles" must not linger
    expect(
      screen.queryByRole('button', { name: /Import \d+ articles?/ }),
    ).toBeNull()
    // Stale row from previous query gone
    expect(screen.queryByText('Anterior approach in THA')).toBeNull()
  })

  it('placeholder is shown when no result has been previewed', async () => {
    searchMock.mockResolvedValueOnce([SAMPLE_RESULT])
    wrap(<PubMedSearchDialog projectId="p1" />)
    fireEvent.click(screen.getByRole('button', { name: /Search PubMed/i }))

    const input = await screen.findByLabelText('Query')
    fireEvent.change(input, { target: { value: 'hip' } })
    const buttons = screen.getAllByRole('button', { name: 'Search' })
    fireEvent.click(buttons[buttons.length - 1])

    await waitFor(() => screen.getByTestId('pubmed-results-pane'))
    const preview = screen.getByTestId('pubmed-preview-pane')
    expect(preview.textContent).toMatch(/preview/i)
  })
})
