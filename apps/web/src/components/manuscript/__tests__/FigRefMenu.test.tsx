/**
 * Phase 4.5 — Figure-ref dropdown menu on the editor toolbar.
 *
 * Verifies that the menu lists the project's figures and that clicking
 * one invokes the editor's ``insertFigRef`` command with the right id.
 * We stub ``useFigures`` directly so we don't have to spin up react-query.
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

const { useFiguresMock } = vi.hoisted(() => ({ useFiguresMock: vi.fn() }))

vi.mock('@/hooks/useFigures', () => ({
  useFigures: useFiguresMock,
}))

import { EditorToolbar } from '../EditorToolbar'

function renderToolbar(editor: unknown) {
  // The toolbar mounts InsertArticlesTableDialog (which uses react-query
  // internally). Provide a throwaway client so the hook is happy even
  // when the dialog itself is closed.
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  })
  return render(
    <QueryClientProvider client={qc}>
      <EditorToolbar projectId="p1" editor={editor as never} />
    </QueryClientProvider>,
  )
}

const FIG = (id: string, n: number, caption: string) => ({
  id,
  project_id: 'p1',
  figure_number: n,
  caption,
  alt_text: '',
  file_type: 'image/png' as const,
  width_px: 800,
  height_px: 600,
  byte_size: 123,
  file_url: null,
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
})

function makeFakeEditor() {
  // Minimal chain interface that records the insertFigRef payload.
  const calls: Array<{ command: string; payload?: unknown }> = []
  const chain: any = {
    focus: () => chain,
    insertFigRef: (attrs: unknown) => {
      calls.push({ command: 'insertFigRef', payload: attrs })
      return chain
    },
    insertTable: (attrs: unknown) => {
      calls.push({ command: 'insertTable', payload: attrs })
      return chain
    },
    addRowAfter: () => chain,
    deleteRow: () => chain,
    addColumnAfter: () => chain,
    deleteColumn: () => chain,
    deleteTable: () => chain,
    run: () => true,
  }
  const can = () => ({ addRowAfter: () => true })
  return { chain: () => chain, can, _calls: calls } as any
}

describe('EditorToolbar — Figure ref menu', () => {
  afterEach(() => {
    cleanup()
    useFiguresMock.mockReset()
  })

  it('lists the project figures in the dropdown', async () => {
    useFiguresMock.mockReturnValue({
      data: [FIG('fA', 1, 'CONSORT flow'), FIG('fB', 2, 'Forest plot')],
      isLoading: false,
    })
    const editor = makeFakeEditor()
    renderToolbar(editor)
    fireEvent.click(screen.getByRole('button', { name: /reference a figure/i }))
    await waitFor(() => screen.getByText(/CONSORT flow/))
    expect(screen.getByText('Figure 1')).toBeTruthy()
    expect(screen.getByText('Figure 2')).toBeTruthy()
  })

  it('clicking a figure inserts a FigRef with the right id', async () => {
    useFiguresMock.mockReturnValue({
      data: [FIG('fA', 1, 'CONSORT flow')],
      isLoading: false,
    })
    const editor = makeFakeEditor()
    renderToolbar(editor)
    fireEvent.click(screen.getByRole('button', { name: /reference a figure/i }))
    const item = await screen.findByTestId('figref-item-fA')
    fireEvent.click(item)
    expect(editor._calls).toContainEqual({
      command: 'insertFigRef',
      payload: { figureId: 'fA' },
    })
  })
})
