/**
 * rcm-sweep HIGH bug: the prior `initialised.current` ref pattern could
 * block autosave from ever firing when a section started empty. The
 * replacement tracks the last server-observed content in a ref and skips
 * no-op saves (local === server) — this test verifies the no-op skip
 * (the load path is exercised throughout the existing test suite, and
 * the empty-then-edit path was verified manually in chrome-devtools
 * during the sweep).
 */
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { act, renderHook, waitFor } from '@testing-library/react'
import type { PropsWithChildren } from 'react'
import { afterEach, describe, expect, it, vi } from 'vitest'

vi.mock('@/lib/api', () => ({
  manuscriptApi: {
    getSection: vi.fn(),
    upsertSection: vi.fn(),
  },
}))

import { manuscriptApi } from '@/lib/api'
import { useManuscript } from '@/hooks/useManuscript'

const mockedGet = manuscriptApi.getSection as unknown as ReturnType<typeof vi.fn>
const mockedPut = manuscriptApi.upsertSection as unknown as ReturnType<typeof vi.fn>

function wrap(qc: QueryClient) {
  return function Wrapper({ children }: PropsWithChildren) {
    return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
  }
}

function makeQc() {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false, staleTime: 0 },
      mutations: { retry: false },
    },
  })
}

afterEach(() => {
  vi.clearAllMocks()
})

describe('useManuscript autosave (rcm-sweep HIGH bug)', () => {
  it(
    'seeds html from the server AND skips no-op autosaves',
    async () => {
      mockedGet.mockResolvedValue({
        id: 's1',
        user_id: 'u',
        project_id: 'p',
        section_name: 'Introduction',
        content: '<p>existing</p>',
        word_count: 1,
        updated_at: '2026-01-01T00:00:00Z',
      })

      const qc = makeQc()
      const { result } = renderHook(() => useManuscript('p', 'Introduction'), {
        wrapper: wrap(qc),
      })

      // The hook MUST seed `html` from the server. Pre-fix the ref-pattern
      // could swallow this for empty content; verifying non-empty here as
      // the canary that the data effect's setLocal still wires up.
      await waitFor(() => expect(result.current.html).toBe('<p>existing</p>'))

      // Re-emit the same content the load gave us. No real edit happened.
      act(() => {
        result.current.setHtml('<p>existing</p>')
      })

      // Wait safely past the 1.2s debounce.
      await new Promise((r) => setTimeout(r, 1600))
      expect(mockedPut).not.toHaveBeenCalled()
    },
    8000,
  )
})
