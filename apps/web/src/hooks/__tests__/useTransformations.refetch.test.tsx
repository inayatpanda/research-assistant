/**
 * DEMO-FIX-D MEDIUM-1 — verify the useTransformations query is configured
 * with the polling + on-focus refetch policy so external mutations (e.g.
 * the runner saving a derived column) surface in the panel without a hard
 * reload. We don't drive timers here — we just read the resolved query
 * options off the QueryClient cache to assert intent.
 */
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { renderHook, waitFor } from '@testing-library/react'
import type { PropsWithChildren } from 'react'
import { afterEach, describe, expect, it, vi } from 'vitest'

vi.mock('@/lib/api', () => ({
  transformationsApi: {
    list: vi.fn(async () => [] as unknown[]),
  },
}))

import { useTransformations } from '@/hooks/useTransformations'

function wrap(qc: QueryClient) {
  return function Wrapper({ children }: PropsWithChildren) {
    return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
  }
}

afterEach(() => {
  vi.clearAllMocks()
})

describe('useTransformations refetch policy (DEMO-FIX-D MEDIUM-1)', () => {
  it('configures refetchOnWindowFocus="always" + 30s interval', async () => {
    const qc = new QueryClient()
    const { result } = renderHook(() => useTransformations('p-1', 'ds-1'), {
      wrapper: wrap(qc),
    })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))

    const observer = qc
      .getQueryCache()
      .find({ queryKey: ['transformations', 'p-1', 'ds-1'] })
    expect(observer).toBeDefined()
    const options = observer!.observers[0]?.options as
      | { refetchOnWindowFocus?: unknown; refetchInterval?: unknown }
      | undefined
    expect(options).toBeDefined()
    expect(options!.refetchOnWindowFocus).toBe('always')
    expect(options!.refetchInterval).toBe(30000)
  })
})
