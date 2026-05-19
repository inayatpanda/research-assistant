/**
 * MP19 — CrossDatabaseTranslator vitest.
 */
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

const { listMock, translateMock } = vi.hoisted(() => ({
  listMock: vi.fn(),
  translateMock: vi.fn(),
}))

vi.mock('@/lib/api', async (orig) => {
  const real = (await orig()) as Record<string, unknown>
  return {
    ...real,
    searchStrategiesApi: {
      list: listMock,
      create: vi.fn(),
      update: vi.fn(),
      remove: vi.fn(),
      translate: translateMock,
    },
  }
})

import { CrossDatabaseTranslator } from '../CrossDatabaseTranslator'

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
  listMock.mockReset()
  translateMock.mockReset()
})

describe('CrossDatabaseTranslator', () => {
  it('renders the translated query and warnings panel when present', async () => {
    listMock.mockResolvedValue([
      {
        id: 's1',
        project_id: 'p1',
        review_id: 'r1',
        name: 'PubMed base',
        database: 'PubMed',
        query_text: 'diabetes[MeSH Terms]',
        mesh_term_ids: [],
        translated_from_id: null,
        is_locked: false,
        warnings: null,
        created_at: '2026-05-19T00:00:00Z',
        updated_at: '2026-05-19T00:00:00Z',
      },
    ])
    translateMock.mockResolvedValue({
      translated_query: "'diabetes'/de",
      warnings: ['Tag [lang] dropped — no equivalent in embase.'],
      target: 'embase',
    })

    wrap(<CrossDatabaseTranslator projectId="p1" />)

    // Wait for the strategies list to load and option 's1' to render.
    await waitFor(() => {
      const opts = (screen.getByTestId('tr-source') as HTMLSelectElement)
        .options
      const optVals = Array.from(opts).map((o) => o.value)
      expect(optVals).toContain('s1')
    })
    fireEvent.change(screen.getByTestId('tr-source'), { target: { value: 's1' } })
    fireEvent.click(screen.getByRole('button', { name: /^translate$/i }))

    await waitFor(() => {
      expect(translateMock).toHaveBeenCalledWith('p1', 's1', 'embase', false)
    })
    expect(await screen.findByTestId('tr-output')).toBeTruthy()
    expect(screen.getByText(/'diabetes'\/de/)).toBeTruthy()
    expect(screen.getByTestId('tr-warnings')).toBeTruthy()
    expect(screen.getByText(/dropped/i)).toBeTruthy()
  })
})
