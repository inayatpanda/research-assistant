/**
 * F2.4 — Bulk-upload UI: progress, failure handling, 50-file cap.
 *
 * The dropzone accepts multiple files at once, shows a per-file status,
 * and emits a summary card when the batch completes.
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

const { uploadMock } = vi.hoisted(() => ({
  uploadMock: vi.fn(),
}))

vi.mock('@/lib/api', async (orig) => {
  const real = (await orig()) as Record<string, unknown>
  return {
    ...real,
    articlesApi: {
      upload: uploadMock,
      list: vi.fn(),
      get: vi.fn(),
      update: vi.fn(),
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

import { UploadZone } from '../UploadZone'

function wrap(node: React.ReactNode) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return render(<QueryClientProvider client={client}>{node}</QueryClientProvider>)
}

function makeFile(name: string) {
  return new File(['%PDF-1.4 fake'], name, { type: 'application/pdf' })
}

function makeResponse(name: string, extra: Partial<Record<string, unknown>> = {}) {
  return {
    article: {
      id: `id-${name}`,
      user_id: 'u',
      project_id: 'p',
      title: name,
      authors: [],
      journal: null,
      year: null,
      volume: null,
      issue: null,
      pages: null,
      doi: null,
      pmid: null,
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
      created_at: new Date().toISOString(),
      file_url: null,
    },
    duplicate_of: null,
    extraction_source: 'crossref',
    extraction_error: null,
    autofill_status: 'doi_match',
    autofilled_by: { title: 'doi' },
    ...extra,
  }
}

async function dropFiles(files: File[]) {
  const input = document.querySelector('input[type="file"]') as HTMLInputElement
  expect(input).toBeTruthy()
  // react-dropzone reads `event.target.files`; the easiest way to simulate
  // a drag-drop in jsdom is to fire `change` with a FileList-shaped object.
  Object.defineProperty(input, 'files', { value: files, configurable: true })
  await act(async () => {
    fireEvent.change(input)
  })
}

afterEach(() => {
  cleanup()
  uploadMock.mockReset()
})

describe('UploadZone — F2 bulk upload', () => {
  it('shows a row per dropped file and uploads them all', async () => {
    uploadMock.mockImplementation(async (_pid: string, file: File) => makeResponse(file.name))
    wrap(<UploadZone projectId="proj-1" />)

    await dropFiles([makeFile('a.pdf'), makeFile('b.pdf'), makeFile('c.pdf')])

    expect(screen.getByText('3 files ready')).toBeTruthy()

    const startBtn = screen.getByTestId('library-upload-start')
    await act(async () => {
      fireEvent.click(startBtn)
    })

    await waitFor(() => {
      expect(uploadMock).toHaveBeenCalledTimes(3)
    })
    expect(screen.getAllByTestId('library-upload-row')).toHaveLength(3)
    await waitFor(() => {
      expect(
        screen.getByTestId('library-upload-summary').textContent,
      ).toContain('3 uploaded')
    })
  })

  it('reports a failure summary when one of the uploads errors', async () => {
    uploadMock.mockImplementation(async (_pid: string, file: File) => {
      if (file.name === 'broken.pdf') throw new Error('boom')
      return makeResponse(file.name)
    })
    wrap(<UploadZone projectId="proj-1" />)

    await dropFiles([
      makeFile('ok-1.pdf'),
      makeFile('broken.pdf'),
      makeFile('ok-2.pdf'),
    ])
    await act(async () => {
      fireEvent.click(screen.getByTestId('library-upload-start'))
    })

    await waitFor(() => {
      expect(
        screen.getByTestId('library-upload-summary').textContent,
      ).toContain('2 uploaded')
    })
    expect(
      screen.getByTestId('library-upload-summary').textContent,
    ).toContain('1 failed')
    expect(screen.getByText('boom')).toBeTruthy()
  })

  it('caps the batch at 50 files when the user drops more', async () => {
    uploadMock.mockImplementation(async (_pid: string, file: File) => makeResponse(file.name))
    wrap(<UploadZone projectId="proj-1" />)

    const files = Array.from({ length: 60 }, (_, i) => makeFile(`f-${i}.pdf`))
    await dropFiles(files)

    expect(screen.getByText('50 files ready')).toBeTruthy()
  })

  it('lets the user remove a staged file before clicking Upload', async () => {
    uploadMock.mockImplementation(async (_pid: string, file: File) => makeResponse(file.name))
    wrap(<UploadZone projectId="proj-1" />)
    await dropFiles([makeFile('keep.pdf'), makeFile('drop.pdf')])
    expect(screen.getByText('2 files ready')).toBeTruthy()

    const removeButtons = screen.getAllByTestId('library-upload-remove')
    await act(async () => {
      fireEvent.click(removeButtons[1]!) // remove drop.pdf
    })
    expect(screen.getByText('1 file ready')).toBeTruthy()
    expect(screen.queryByText('drop.pdf')).toBeNull()
  })

  it('caps concurrency so no more than 4 uploads are in-flight at once', async () => {
    let active = 0
    let peak = 0
    uploadMock.mockImplementation(async (_pid: string, file: File) => {
      active++
      peak = Math.max(peak, active)
      // Yield once so the queue actually has time to schedule overlapping
      // workers; otherwise the synchronous resolve hides the contention.
      await new Promise((r) => setTimeout(r, 5))
      active--
      return makeResponse(file.name)
    })
    wrap(<UploadZone projectId="proj-1" />)
    await dropFiles(Array.from({ length: 10 }, (_, i) => makeFile(`f-${i}.pdf`)))
    await act(async () => {
      fireEvent.click(screen.getByTestId('library-upload-start'))
    })
    await waitFor(() => {
      expect(uploadMock).toHaveBeenCalledTimes(10)
    })
    expect(peak).toBeLessThanOrEqual(4)
    expect(peak).toBeGreaterThan(1) // sanity: workers actually overlapped
  })
})
