/**
 * Phase 4.5 — InsertArticlesTableDialog vitest.
 *
 * Covers the dialog's three-step state machine without booting a real
 * TipTap editor: we pass ``editor=null`` (the only path that uses it is
 * the final Insert click which we exercise indirectly).
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

const { listMock, buildTableMock } = vi.hoisted(() => ({
  listMock: vi.fn(),
  buildTableMock: vi.fn(),
}))

vi.mock('@/lib/api', async (orig) => {
  const real = (await orig()) as Record<string, unknown>
  return {
    ...real,
    articlesApi: { ...(real.articlesApi as object), list: listMock },
    manuscriptApi: {
      ...(real.manuscriptApi as object),
      buildArticlesTable: buildTableMock,
    },
  }
})

import { InsertArticlesTableDialog } from '../InsertArticlesTableDialog'

const ART = (id: string, title: string, year = 2024) => ({
  id,
  user_id: 'u',
  project_id: 'p1',
  title,
  authors: ['Smith J'],
  journal: 'Lancet',
  year,
  volume: null,
  issue: null,
  pages: null,
  doi: null,
  file_ref: null,
  file_type: null,
  abstract: null,
  study_design: null,
  review_status: 'included' as const,
  exclusion_reason: null,
  conflict_of_interest: null,
  source: 'upload' as const,
  reference_type: 'journal_article' as const,
  url: null,
  created_at: '2024-01-01T00:00:00Z',
  file_url: null,
})

function renderDialog() {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  })
  return render(
    <QueryClientProvider client={qc}>
      <InsertArticlesTableDialog
        open
        onOpenChange={vi.fn()}
        projectId="p1"
        editor={null}
      />
    </QueryClientProvider>,
  )
}

describe('InsertArticlesTableDialog', () => {
  afterEach(() => {
    cleanup()
    listMock.mockReset()
    buildTableMock.mockReset()
  })

  it('lists project articles and allows selecting them', async () => {
    listMock.mockResolvedValue([
      ART('a1', 'Effect of X on Y'),
      ART('a2', 'A cohort study'),
    ])
    renderDialog()

    await waitFor(() =>
      expect(screen.getByText('Effect of X on Y')).toBeTruthy(),
    )
    expect(screen.getByText('A cohort study')).toBeTruthy()

    // Tick the first article — the "Next" button should enable.
    const next = screen.getByRole('button', { name: /next: columns/i })
    expect((next as HTMLButtonElement).disabled).toBe(true)
    fireEvent.click(screen.getByLabelText('Select Effect of X on Y'))
    expect((next as HTMLButtonElement).disabled).toBe(false)
  })

  it('toggles column presets in the columns step', async () => {
    listMock.mockResolvedValue([ART('a1', 'Effect of X on Y')])
    renderDialog()
    await waitFor(() => screen.getByText('Effect of X on Y'))
    fireEvent.click(screen.getByLabelText('Select Effect of X on Y'))
    fireEvent.click(screen.getByRole('button', { name: /next: columns/i }))

    // The locked first column is rendered.
    expect(screen.getByText(/locked/i)).toBeTruthy()
    // Adding a preset (Title) flips it on.
    const titleBtn = screen.getByRole('button', { name: /^\+ Title$/i })
    expect(titleBtn.getAttribute('aria-pressed')).toBe('false')
    fireEvent.click(titleBtn)
    const titleBtnOn = screen.getByRole('button', { name: /^✓ Title$/i })
    expect(titleBtnOn.getAttribute('aria-pressed')).toBe('true')
  })

  it('renders the backend-returned HTML in the preview step', async () => {
    listMock.mockResolvedValue([ART('a1', 'Effect of X on Y')])
    buildTableMock.mockResolvedValue(
      '<table class="rma-articles-table"><thead><tr><th><p>Study</p></th></tr></thead><tbody><tr><td><p>Smith (2024)</p></td></tr></tbody></table>',
    )
    renderDialog()
    await waitFor(() => screen.getByText('Effect of X on Y'))
    fireEvent.click(screen.getByLabelText('Select Effect of X on Y'))
    fireEvent.click(screen.getByRole('button', { name: /next: columns/i }))
    fireEvent.click(screen.getByRole('button', { name: /next: preview/i }))

    await waitFor(() => expect(buildTableMock).toHaveBeenCalled())
    const preview = await screen.findByTestId('articles-table-preview')
    expect(preview.querySelector('table')).toBeTruthy()
    expect(preview.textContent).toContain('Smith (2024)')
  })
})
