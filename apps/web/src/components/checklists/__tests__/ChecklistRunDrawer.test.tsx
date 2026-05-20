/**
 * MP20 — ChecklistRunDrawer smoke tests.
 *
 * Verifies (1) the title + auto-check button render given a hook-mocked
 * run payload, and (2) clicking a status pill calls the patch mutation
 * with the right payload.
 */
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { ChecklistRunRead } from '@/lib/api'

const RUN: ChecklistRunRead = {
  id: 'run-1',
  project_id: 'p-1',
  checklist_key: 'CONSORT_2010',
  title: 'v1 to JBJS',
  overall_compliance_pct: 0,
  created_at: '2026-05-20T00:00:00Z',
  updated_at: '2026-05-20T00:00:00Z',
  items: [
    {
      item_id: '1',
      item_text: 'Title and abstract',
      status: 'unclear',
      comment: '',
      mapped_section: null,
      mapped_text_excerpt: null,
    },
    {
      item_id: '2',
      item_text: 'Background and objectives',
      status: 'pass',
      comment: 'Already verified',
      mapped_section: 'Introduction',
      mapped_text_excerpt: 'This study aims to …',
    },
  ],
}

const patchMutate = vi.fn()
const autoCheckMutate = vi.fn()

vi.mock('@/hooks/useChecklists', () => ({
  useChecklistRun: () => ({ data: RUN, isLoading: false }),
  usePatchChecklistItem: () => ({ mutate: patchMutate, isPending: false }),
  useAutoCheckRun: () => ({ mutate: autoCheckMutate, isPending: false }),
}))

// react-resizable-panels needs ResizeObserver under jsdom — not used here,
// but the drawer uses ScrollArea which (via radix) can require it.
class ResizeObserverStub {
  observe() {}
  unobserve() {}
  disconnect() {}
}
;(globalThis as unknown as {
  ResizeObserver?: typeof ResizeObserverStub
}).ResizeObserver = ResizeObserverStub

import { ChecklistRunDrawer } from '../ChecklistRunDrawer'

function wrap() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  return render(
    <QueryClientProvider client={client}>
      <ChecklistRunDrawer projectId="p-1" runId="run-1" />
    </QueryClientProvider>,
  )
}

afterEach(() => {
  cleanup()
  patchMutate.mockClear()
  autoCheckMutate.mockClear()
})

describe('ChecklistRunDrawer', () => {
  it('renders the run title + the auto-check + export controls', () => {
    wrap()
    expect(screen.getByText('v1 to JBJS')).toBeDefined()
    expect(screen.getByTestId('checklist-auto-check-btn')).toBeDefined()
    expect(screen.getByTestId('checklist-export-button')).toBeDefined()
    // Both items present.
    expect(screen.getByTestId('checklist-item-row-1')).toBeDefined()
    expect(screen.getByTestId('checklist-item-row-2')).toBeDefined()
  })

  it('clicking the "Pass" pill for item 1 patches with status=pass', () => {
    wrap()
    const passBtn = screen.getByTestId('status-1-pass')
    fireEvent.click(passBtn)
    expect(patchMutate).toHaveBeenCalledTimes(1)
    expect(patchMutate).toHaveBeenCalledWith({
      itemId: '1',
      patch: { status: 'pass' },
    })
  })
})
