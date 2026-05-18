import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import {
  cleanup,
  render,
  waitFor,
  fireEvent,
} from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { StructuredAbstract } from '../StructuredAbstract'

// Hoisted mock state so the vi.mock factory below can reference these.
const mocks = vi.hoisted(() => {
  const baseFm = {
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
  }
  const getMock = vi.fn(async () => baseFm)
  const patchMock = vi.fn(async (_pid: string, body: unknown) => ({
    ...baseFm,
    ...(body as object),
  }))
  return { getMock, patchMock }
})

vi.mock('@/lib/api', async (orig) => {
  const real = (await orig()) as Record<string, unknown>
  return {
    ...real,
    frontmatterApi: {
      frontmatter: {
        get: mocks.getMock,
        patch: mocks.patchMock,
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

describe('StructuredAbstract', () => {
  afterEach(() => {
    cleanup()
    mocks.getMock.mockClear()
    mocks.patchMock.mockClear()
  })

  it('hides the 4 sub-fields when toggle is OFF', async () => {
    const { findByTestId, queryByTestId } = wrap(
      <StructuredAbstract projectId="p1" />,
    )
    await findByTestId('sa-enable')
    expect(queryByTestId('sa-fields')).toBeNull()
  })

  it('renders the 4 sub-fields after enabling and patches the server', async () => {
    const { findByTestId, getByTestId } = wrap(
      <StructuredAbstract projectId="p1" />,
    )
    const toggle = await findByTestId('sa-enable')
    fireEvent.click(toggle)
    await waitFor(() => {
      expect(mocks.patchMock).toHaveBeenCalledWith('p1', {
        structured_abstract_enabled: true,
      })
    })
    expect(getByTestId('sa-fields')).toBeTruthy()
    expect(getByTestId('sa-background')).toBeTruthy()
    expect(getByTestId('sa-methods')).toBeTruthy()
    expect(getByTestId('sa-results')).toBeTruthy()
    expect(getByTestId('sa-conclusions')).toBeTruthy()
  })
})
