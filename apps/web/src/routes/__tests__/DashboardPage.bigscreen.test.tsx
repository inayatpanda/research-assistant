/**
 * Big-screen layout — Vitest for the DashboardPage project grid.
 *
 * Before the layout fix the dashboard was clipped to `max-w-6xl` (~1152px),
 * leaving most of a 27" Mac viewport empty. It now scales to
 * `max-w-screen-2xl` (1536px) and the project grid bumps to 4 columns at
 * the `4xl` breakpoint (1920px+).
 */
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, render } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { Project } from '@/lib/api'

const PROJECTS: Project[] = Array.from({ length: 4 }).map((_, i) => ({
  id: `p-${i}`,
  user_id: 'u-1',
  title: `Project ${i}`,
  study_type: 'Cohort',
  citation_style: 'vancouver_numeric',
  ai_provider: 'claude',
  target_journal: null,
  prospero_number: null,
  clinicaltrials_number: null,
  template_journal: null,
  inline_citation_mode: 'bracket_numeric',
  created_at: '2026-05-18T00:00:00Z',
  updated_at: '2026-05-18T00:00:00Z',
}))

vi.mock('@/lib/api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/lib/api')>()
  return {
    ...actual,
    projectsApi: {
      ...actual.projectsApi,
      list: vi.fn(async () => PROJECTS),
    },
  }
})

// jsdom doesn't ship ResizeObserver
class ResizeObserverStub {
  observe() {}
  unobserve() {}
  disconnect() {}
}
;(globalThis as unknown as {
  ResizeObserver?: typeof ResizeObserverStub
}).ResizeObserver = ResizeObserverStub

import DashboardPage from '../DashboardPage'

function wrap() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  Object.defineProperty(window, 'innerWidth', {
    configurable: true,
    value: 2560,
  })
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter>
        <DashboardPage />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

afterEach(cleanup)

describe('DashboardPage — big-screen layout', () => {
  it('uses max-w-screen-2xl so the page scales on ultra-wide displays', () => {
    const { container } = wrap()
    expect(container.querySelector('.max-w-screen-2xl')).not.toBeNull()
  })

  it('declares a 4-column grid at the 4xl breakpoint', async () => {
    const { container, findByText } = wrap()
    // Wait for the project list to land
    await findByText('Project 0')
    // Find the grid wrapper containing the cards
    const grids = container.querySelectorAll('div.grid')
    const cardGrid = Array.from(grids).find((g) =>
      g.className.includes('4xl:grid-cols-4'),
    )
    expect(cardGrid).toBeDefined()
    expect(cardGrid?.className).toContain('xl:grid-cols-3')
  })
})
