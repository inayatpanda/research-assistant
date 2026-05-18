import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, render, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { FrontMatterPanel } from '../FrontMatterPanel'

vi.mock('@/lib/api', async (orig) => {
  const real = (await orig()) as Record<string, unknown>
  return {
    ...real,
    frontmatterApi: {
      authors: { list: vi.fn(async () => []) },
      affiliations: { list: vi.fn(async () => []) },
      contributions: { list: vi.fn(async () => []) },
      link: { add: vi.fn(), remove: vi.fn() },
      frontmatter: {
        get: vi.fn(async () => ({
          id: 'fm1',
          project_id: 'p1',
          funding_statement: null,
          funders: [],
          ethics_irb: null,
          ethics_approval_number: null,
          ethics_consent: null,
          conflicts_statement: null,
          structured_abstract_enabled: false,
          structured_abstract: {
            background: '',
            methods: '',
            results: '',
            conclusions: '',
          },
          updated_at: '2026-05-18T00:00:00Z',
        })),
        patch: vi.fn(),
      },
    },
  }
})

function wrap(node: React.ReactNode) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return render(<QueryClientProvider client={client}>{node}</QueryClientProvider>)
}

describe('FrontMatterPanel', () => {
  afterEach(cleanup)

  it('renders all five section tabs', () => {
    const { getByTestId } = wrap(<FrontMatterPanel projectId="p1" />)
    expect(getByTestId('fm-section-authors')).toBeTruthy()
    expect(getByTestId('fm-section-affiliations')).toBeTruthy()
    expect(getByTestId('fm-section-contributions')).toBeTruthy()
    expect(getByTestId('fm-section-ethics')).toBeTruthy()
    expect(getByTestId('fm-section-abstract')).toBeTruthy()
  })

  it('starts on the Authors section', async () => {
    const { getByTestId } = wrap(<FrontMatterPanel projectId="p1" />)
    await waitFor(() => expect(getByTestId('author-new-name')).toBeTruthy())
  })
})
