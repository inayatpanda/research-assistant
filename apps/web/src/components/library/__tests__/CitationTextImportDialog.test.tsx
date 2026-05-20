import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

const { importTextMock, importMetadataMock } = vi.hoisted(() => ({
  importTextMock: vi.fn(),
  importMetadataMock: vi.fn(),
}))

vi.mock('@/lib/api', async (orig) => {
  const real = (await orig()) as Record<string, unknown>
  return {
    ...real,
    citationImportApi: { importFromText: importTextMock },
    ingestApi: {
      importFromMetadata: importMetadataMock,
      lookupDoi: vi.fn(),
      searchPubMed: vi.fn(),
      importRis: vi.fn(),
      importBibtex: vi.fn(),
      duplicates: vi.fn(),
      merge: vi.fn(),
    },
  }
})

import { CitationTextImportDialog } from '../CitationTextImportDialog'

function wrap(node: React.ReactNode) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return render(
    <QueryClientProvider client={client}>{node}</QueryClientProvider>,
  )
}

const SAMPLE_PREVIEW = {
  items: [
    {
      raw: '1. Doe J. Title. doi:10.1234/abc',
      doi: '10.1234/abc',
      pmid: null,
      status: 'ok' as const,
      parsed_metadata: {
        title: 'Resolved title',
        authors: ['Jane Doe'],
        journal: 'J Foo',
        year: 2024,
        doi: '10.1234/abc',
        pmid: null,
        source: 'doi' as const,
        mesh_terms: [],
        affiliations: [],
        article_types: [],
      },
      notes: [],
    },
    {
      raw: '2. Smith K. Untraceable.',
      doi: null,
      pmid: null,
      status: 'unresolved' as const,
      parsed_metadata: null,
      notes: ['No high-confidence Crossref title match'],
    },
  ],
}

describe('CitationTextImportDialog', () => {
  afterEach(() => {
    cleanup()
    importTextMock.mockReset()
    importMetadataMock.mockReset()
  })

  it('parses input text and renders resolved + unresolved entries', async () => {
    importTextMock.mockResolvedValue(SAMPLE_PREVIEW)
    wrap(
      <CitationTextImportDialog
        projectId="p1"
        open
        onOpenChange={() => {}}
      />,
    )
    const textarea = screen.getByTestId('citation-text-input') as HTMLTextAreaElement
    fireEvent.change(textarea, { target: { value: 'pasted text' } })
    fireEvent.click(screen.getByRole('button', { name: /parse/i }))
    await waitFor(() => {
      expect(importTextMock).toHaveBeenCalled()
    })
    const [pid, text] = importTextMock.mock.calls[0]
    expect(pid).toBe('p1')
    expect(text).toBe('pasted text')
    expect(await screen.findByText('Resolved title')).toBeTruthy()
    expect(
      screen.getByText(/No high-confidence Crossref title match/i),
    ).toBeTruthy()
  })

  it('disables the checkbox for unresolved entries', async () => {
    importTextMock.mockResolvedValue(SAMPLE_PREVIEW)
    wrap(
      <CitationTextImportDialog
        projectId="p1"
        open
        onOpenChange={() => {}}
      />,
    )
    const textarea = screen.getByTestId('citation-text-input') as HTMLTextAreaElement
    fireEvent.change(textarea, { target: { value: 'x' } })
    fireEvent.click(screen.getByRole('button', { name: /parse/i }))
    const okBox = (await screen.findByLabelText(
      /Include reference 1/i,
    )) as HTMLInputElement
    const badBox = (await screen.findByLabelText(
      /Include reference 2/i,
    )) as HTMLInputElement
    expect(okBox.disabled).toBe(false)
    expect(badBox.disabled).toBe(true)
  })
})
