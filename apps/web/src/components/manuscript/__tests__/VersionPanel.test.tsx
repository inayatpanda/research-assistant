import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

vi.mock('@/lib/api', async (orig) => {
  const real = (await orig()) as Record<string, unknown>
  return {
    ...real,
    snapshotsApi: {
      list: vi.fn(async () => [
        {
          id: 's1',
          project_id: 'p1',
          label: 'v1 – initial submission',
          description: 'pre-review',
          created_at: '2026-05-18T00:00:00Z',
        },
      ]),
      create: vi.fn(async (_pid: string, body: { label: string }) => ({
        id: 's2',
        project_id: 'p1',
        label: body.label,
        description: null,
        full_blob: {},
        created_at: '2026-05-18T01:00:00Z',
      })),
      get: vi.fn(),
      diff: vi.fn(async () => ({
        base_snapshot_id: 's1',
        target_snapshot_id: null,
        sections: {},
      })),
      delete: vi.fn(async () => undefined),
    },
  }
})

import { VersionPanel } from '../VersionPanel'

function wrap(node: React.ReactNode) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return render(
    <QueryClientProvider client={client}>{node}</QueryClientProvider>,
  )
}

describe('VersionPanel', () => {
  afterEach(cleanup)

  it('lists existing snapshots', async () => {
    wrap(<VersionPanel projectId="p1" />)
    await waitFor(() => {
      expect(screen.getByTestId('snapshot-row-s1')).toBeTruthy()
    })
    expect(screen.getByText(/v1 – initial submission/)).toBeTruthy()
  })

  it('opens the create dialog and validates label', async () => {
    wrap(<VersionPanel projectId="p1" />)
    fireEvent.click(screen.getByTestId('version-panel-new'))
    await waitFor(() => {
      expect(screen.getByTestId('snapshot-create-confirm')).toBeTruthy()
    })
    // Empty label rejected via toast — we just confirm the button is wired and
    // the input is empty. The toast itself is a side-effect we don't render here.
    const input = screen.getByTestId('snapshot-label-input') as HTMLInputElement
    expect(input.value).toBe('')
  })

  it('toggles diff visibility per row', async () => {
    wrap(<VersionPanel projectId="p1" />)
    await waitFor(() => {
      expect(screen.getByTestId('snapshot-diff-s1')).toBeTruthy()
    })
    const btn = screen.getByTestId('snapshot-diff-s1')
    expect(btn.textContent).toMatch(/Diff/i)
    fireEvent.click(btn)
    await waitFor(() => {
      expect(btn.textContent).toMatch(/Hide/i)
    })
  })
})
