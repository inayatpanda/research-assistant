/**
 * MP19 — PublicationBiasPanel vitest.
 */
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

const { biasMock } = vi.hoisted(() => ({
  biasMock: vi.fn(),
}))

vi.mock('@/lib/api', async (orig) => {
  const real = (await orig()) as Record<string, unknown>
  return {
    ...real,
    metaExtensionsApi: {
      publicationBias: biasMock,
      leaveOneOut: vi.fn(),
      leaveOneOutPngUrl: vi.fn(),
      subgroupInteraction: vi.fn(),
      metaRegression: vi.fn(),
    },
  }
})

import { PublicationBiasPanel } from '../PublicationBiasPanel'

function wrap(node: React.ReactNode) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  return render(
    <QueryClientProvider client={client}>{node}</QueryClientProvider>,
  )
}

afterEach(() => {
  cleanup()
  biasMock.mockReset()
})

describe('PublicationBiasPanel', () => {
  it('renders the test rows with pass/fail badges', async () => {
    biasMock.mockResolvedValue({
      metric: 'md',
      k: 5,
      recommended: 'egger',
      tests: [
        { method: 'egger', statistic: 0.42, p: 0.04, note: null },
        { method: 'begg', statistic: 0.31, p: 0.21, note: null },
      ],
    })
    wrap(<PublicationBiasPanel projectId="p1" metaId="m1" />)
    expect(await screen.findByTestId('pb-row-egger')).toBeTruthy()
    expect(await screen.findByTestId('pb-verdict-egger')).toBeTruthy()
    expect(screen.getByTestId('pb-verdict-egger').textContent).toMatch(
      /possible bias/i,
    )
    expect(screen.getByTestId('pb-verdict-begg').textContent).toMatch(
      /no asymmetry/i,
    )
  })
})
