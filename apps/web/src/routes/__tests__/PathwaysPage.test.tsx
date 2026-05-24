/**
 * F3 — vitest for the PathwaysPage cards + wizard navigation.
 */
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, beforeAll, describe, expect, it, vi } from 'vitest'

beforeAll(() => {
  const proto = Element.prototype as unknown as Record<string, unknown>
  if (!proto.scrollIntoView) proto.scrollIntoView = vi.fn()
  if (!('hasPointerCapture' in proto)) {
    proto.hasPointerCapture = vi.fn(() => false)
    proto.releasePointerCapture = vi.fn()
  }
})

const { listMock } = vi.hoisted(() => ({ listMock: vi.fn() }))

vi.mock('@/lib/api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/lib/api')>()
  return {
    ...actual,
    datasetsApi: {
      ...actual.datasetsApi,
      list: listMock,
    },
  }
})

import PathwaysPage from '../PathwaysPage'

function wrap(node: React.ReactNode) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={['/projects/p-1/pathways']}>
        <Routes>
          <Route path="/projects/:projectId/pathways" element={node} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

afterEach(() => {
  cleanup()
  listMock.mockReset()
})

describe('PathwaysPage', () => {
  it('renders all 5 pathway cards', async () => {
    listMock.mockResolvedValue([])
    wrap(<PathwaysPage />)
    expect(screen.getByText('Pick a pathway')).toBeTruthy()
    expect(screen.getByTestId('pathway-card-two-group')).toBeTruthy()
    expect(screen.getByTestId('pathway-card-risk-factors')).toBeTruthy()
    expect(screen.getByTestId('pathway-card-survival')).toBeTruthy()
    expect(screen.getByTestId('pathway-card-diagnostic')).toBeTruthy()
    expect(screen.getByTestId('pathway-card-agreement')).toBeTruthy()
  })

  it('navigates into the two-group wizard on card click', async () => {
    listMock.mockResolvedValue([])
    wrap(<PathwaysPage />)
    fireEvent.click(screen.getByTestId('pathway-card-two-group'))
    await waitFor(() => {
      expect(screen.getByTestId('pathway-wizard-two-group')).toBeTruthy()
    })
    expect(screen.getByText('Two-group comparison')).toBeTruthy()
  })

  it('warns when no datasets exist', async () => {
    listMock.mockResolvedValue([])
    wrap(<PathwaysPage />)
    fireEvent.click(screen.getByTestId('pathway-card-survival'))
    await waitFor(() => {
      expect(screen.getByText(/No datasets in this project/)).toBeTruthy()
    })
  })

  it('learn-more link uses correct slug per pathway', async () => {
    listMock.mockResolvedValue([])
    wrap(<PathwaysPage />)
    const learnLinks = screen.getAllByText('Learn more')
    expect(learnLinks.length).toBe(5)
  })
})
