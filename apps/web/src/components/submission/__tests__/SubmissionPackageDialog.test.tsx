import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

const { downloadMock } = vi.hoisted(() => ({
  downloadMock: vi.fn(async () => 'demo_vdraft.zip'),
}))

vi.mock('@/lib/api', async (orig) => {
  const real = (await orig()) as Record<string, unknown>
  return {
    ...real,
    exportApi: {
      downloadSubmissionPackage: downloadMock,
    },
    snapshotsApi: {
      list: vi.fn(async () => [
        {
          id: 's1',
          project_id: 'p1',
          label: 'v1',
          description: null,
          created_at: 'x',
        },
      ]),
      create: vi.fn(),
      get: vi.fn(),
      diff: vi.fn(),
      delete: vi.fn(),
    },
  }
})

import { SubmissionPackageDialog } from '../SubmissionPackageDialog'

function wrap(node: React.ReactNode) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return render(
    <QueryClientProvider client={client}>{node}</QueryClientProvider>,
  )
}

describe('SubmissionPackageDialog', () => {
  afterEach(() => {
    cleanup()
    downloadMock.mockClear()
  })

  it('renders the trigger button', () => {
    wrap(<SubmissionPackageDialog projectId="p1" />)
    expect(screen.getByTestId('submission-package-button')).toBeTruthy()
  })

  it('downloads when the user clicks the download button', async () => {
    wrap(<SubmissionPackageDialog projectId="p1" />)
    fireEvent.click(screen.getByTestId('submission-package-button'))
    await waitFor(() =>
      expect(screen.getByTestId('submission-package-dialog')).toBeTruthy(),
    )
    fireEvent.click(screen.getByTestId('submission-download-button'))
    await waitFor(() => expect(downloadMock).toHaveBeenCalled())
    // No snapshot picked → second arg is undefined.
    expect(downloadMock.mock.calls[0]?.[1]).toBeUndefined()
  })
})
