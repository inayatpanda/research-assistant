import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

const { renumberMock } = vi.hoisted(() => ({ renumberMock: vi.fn() }))

vi.mock('@/lib/api', async (orig) => {
  const real = (await orig()) as Record<string, unknown>
  return {
    ...real,
    figuresApi: {
      list: vi.fn(),
      upload: vi.fn(),
      get: vi.fn(),
      patch: vi.fn(),
      reorder: vi.fn(),
      renumber: renumberMock,
      remove: vi.fn(),
    },
  }
})

import { FigureNumberingPanel } from '../FigureNumberingPanel'

const FIG = (id: string, n: number, caption: string) => ({
  id,
  project_id: 'p1',
  figure_number: n,
  caption,
  alt_text: '',
  file_type: 'image/png' as const,
  width_px: 800,
  height_px: 600,
  byte_size: 12345,
  file_url: null,
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
})

describe('FigureNumberingPanel', () => {
  afterEach(() => {
    cleanup()
    renumberMock.mockReset()
  })

  it('shows current numbering and calls renumber on click', async () => {
    const figs = [FIG('fA', 1, 'CONSORT flow'), FIG('fB', 2, 'Forest plot')]
    renumberMock.mockResolvedValue([
      { ...FIG('fB', 1, 'Forest plot') },
      { ...FIG('fA', 2, 'CONSORT flow') },
    ])
    render(<FigureNumberingPanel projectId="p1" figures={figs} />)
    expect(screen.getByText('CONSORT flow')).toBeTruthy()
    expect(screen.getByText('Forest plot')).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: /auto-renumber/i }))
    await waitFor(() => {
      expect(renumberMock).toHaveBeenCalledWith('p1')
    })
  })

  it('renders an empty-state when there are no figures', () => {
    render(<FigureNumberingPanel projectId="p1" figures={[]} />)
    expect(screen.getByText(/Upload figures/i)).toBeTruthy()
  })
})
