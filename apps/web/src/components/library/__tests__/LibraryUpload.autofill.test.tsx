/**
 * F1.4 — Autofill badge surfaces on the upload row + dims when the user
 * edits the autofilled field inside the MetadataConfirmDialog.
 */
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import {
  act,
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

const { uploadMock, updateMock } = vi.hoisted(() => ({
  uploadMock: vi.fn(),
  updateMock: vi.fn(),
}))

vi.mock('@/lib/api', async (orig) => {
  const real = (await orig()) as Record<string, unknown>
  return {
    ...real,
    articlesApi: {
      upload: uploadMock,
      list: vi.fn(),
      get: vi.fn(),
      update: updateMock,
      delete: vi.fn(),
    },
  }
})

vi.mock('sonner', () => ({
  toast: {
    message: vi.fn(),
    error: vi.fn(),
    success: vi.fn(),
  },
}))

import { MetadataConfirmDialog } from '../MetadataConfirmDialog'
import { UploadZone } from '../UploadZone'

function wrap(node: React.ReactNode) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return render(<QueryClientProvider client={client}>{node}</QueryClientProvider>)
}

function articleStub() {
  return {
    id: 'a-1',
    user_id: 'u',
    project_id: 'p',
    title: 'Crossref Title',
    authors: ['Jane Doe'],
    journal: 'J Foo',
    year: 2023,
    volume: null,
    issue: null,
    pages: null,
    doi: '10.1234/abc',
    pmid: null,
    file_ref: null,
    file_type: null,
    abstract: null,
    study_design: null,
    review_status: 'pending' as const,
    exclusion_reason: null,
    conflict_of_interest: null,
    source: 'upload',
    reference_type: 'journal_article' as const,
    url: null,
    created_at: new Date().toISOString(),
    file_url: null,
  }
}

async function dropFile(file: File) {
  const input = document.querySelector('input[type="file"]') as HTMLInputElement
  Object.defineProperty(input, 'files', { value: [file], configurable: true })
  await act(async () => {
    fireEvent.change(input)
  })
}

afterEach(() => {
  cleanup()
  uploadMock.mockReset()
  updateMock.mockReset()
})

describe('UploadZone — F1 autofill badge on the row', () => {
  it('shows a "DOI autofilled" pill after a successful Crossref hit', async () => {
    uploadMock.mockResolvedValue({
      article: articleStub(),
      duplicate_of: null,
      extraction_source: 'crossref',
      extraction_error: null,
      autofill_status: 'doi_match',
      autofilled_by: { title: 'doi', doi: 'doi' },
    })
    wrap(<UploadZone projectId="p" />)
    await dropFile(new File(['%PDF-1.4'], 'paper.pdf', { type: 'application/pdf' }))
    await act(async () => {
      fireEvent.click(screen.getByTestId('library-upload-start'))
    })

    await waitFor(() => {
      expect(screen.getByTestId('library-upload-badge-doi')).toBeTruthy()
    })
    expect(
      screen.getByTestId('library-upload-badge-doi').textContent,
    ).toContain('DOI autofilled')
  })

  it('shows a "Heuristic guess" pill when only the heuristic path ran', async () => {
    uploadMock.mockResolvedValue({
      article: articleStub(),
      duplicate_of: null,
      extraction_source: 'none',
      extraction_error: null,
      autofill_status: 'heuristic_only',
      autofilled_by: { title: 'heuristic' },
    })
    wrap(<UploadZone projectId="p" />)
    await dropFile(new File(['%PDF-1.4'], 'paper.pdf', { type: 'application/pdf' }))
    await act(async () => {
      fireEvent.click(screen.getByTestId('library-upload-start'))
    })
    await waitFor(() => {
      expect(screen.getByTestId('library-upload-badge-heuristic')).toBeTruthy()
    })
  })
})

describe('MetadataConfirmDialog — F1 per-field badge dims when overridden', () => {
  it('renders pills next to autofilled fields and dims after edit', async () => {
    wrap(
      <MetadataConfirmDialog
        article={articleStub()}
        autofilledBy={{ title: 'doi', doi: 'doi', year: 'heuristic' }}
        open={true}
        onOpenChange={() => {}}
      />,
    )

    const doiBadges = screen.getAllByTestId('autofill-badge-doi')
    expect(doiBadges).toHaveLength(2) // title + doi
    const heuristicBadges = screen.getAllByTestId('autofill-badge-heuristic')
    expect(heuristicBadges).toHaveLength(1) // year

    for (const badge of [...doiBadges, ...heuristicBadges]) {
      expect(badge.className).not.toMatch(/opacity-50/)
    }

    const titleInput = screen.getByDisplayValue('Crossref Title')
    fireEvent.change(titleInput, { target: { value: 'My Override' } })

    await waitFor(() => {
      const titleBadge = screen.getAllByTestId('autofill-badge-doi')[0]
      expect(titleBadge.className).toMatch(/opacity-50/)
    })
    const doiBadgeStill = screen.getAllByTestId('autofill-badge-doi')[1]
    expect(doiBadgeStill.className).not.toMatch(/opacity-50/)
  })
})
