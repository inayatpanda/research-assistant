/**
 * Phase M1.5 — MobileMore smoke tests.
 *
 *   1. All four sections render with their expected entries.
 *   2. Tapping "Log out" triggers `authApi.logout`.
 */
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'

const hoisted = vi.hoisted(() => ({
  logout: vi.fn(async () => undefined),
}))

vi.mock('@/lib/api', async () => {
  const actual = await vi.importActual<Record<string, unknown>>('@/lib/api')
  return {
    ...actual,
    authApi: {
      ...((actual.authApi as Record<string, unknown>) ?? {}),
      logout: hoisted.logout,
    },
  }
})

vi.mock('@/hooks/useAuth', () => ({
  useCurrentUser: () => ({
    data: {
      id: 'u1',
      email: 'me@example.com',
      display_name: 'Me',
    },
    isLoading: false,
  }),
}))

import MobileMore from '@/mobile/pages/MobileMore'

function renderAt(path: string) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[path]}>
        <Routes>
          <Route path="/m/more" element={<MobileMore />} />
          <Route path="/login" element={<div data-testid="login-route">login</div>} />
          <Route
            path="/m/economics"
            element={<div data-testid="m-economics-route">economics</div>}
          />
          <Route
            path="/m/checklists"
            element={<div data-testid="m-checklists-route">checklists</div>}
          />
          <Route
            path="/m/submission"
            element={<div data-testid="m-submission-route">submission</div>}
          />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

afterEach(() => {
  cleanup()
  vi.clearAllMocks()
})

describe('MobileMore', () => {
  it('renders the four sections with their key rows', () => {
    renderAt('/m/more')
    // Account section: shows the user's email.
    expect(screen.getByTestId('mmore-account-email').textContent).toContain('Me')
    // Tools section: live Peer review + the M5 placeholders.
    expect(screen.getByTestId('mmore-peer-review')).toBeTruthy()
    expect(screen.getByTestId('mmore-economics')).toBeTruthy()
    expect(screen.getByTestId('mmore-checklists')).toBeTruthy()
    expect(screen.getByTestId('mmore-submission')).toBeTruthy()
    // Settings + About.
    expect(screen.getByTestId('mmore-settings')).toBeTruthy()
    expect(screen.getByTestId('mmore-force-desktop')).toBeTruthy()
    expect(screen.getByTestId('mmore-about')).toBeTruthy()
    expect(screen.getByTestId('mmore-tailscale-help')).toBeTruthy()
  })

  it('calls authApi.logout when the Log out row is tapped', async () => {
    renderAt('/m/more')
    fireEvent.click(screen.getByTestId('mmore-logout'))
    await waitFor(() => expect(hoisted.logout).toHaveBeenCalled())
  })

  it('navigates to the three M5 mini-app routes on tap', async () => {
    renderAt('/m/more')
    fireEvent.click(screen.getByTestId('mmore-economics'))
    await waitFor(() =>
      expect(screen.getByTestId('m-economics-route')).toBeTruthy(),
    )
  })

  it('routes to checklists when the Checklists row is tapped', async () => {
    renderAt('/m/more')
    fireEvent.click(screen.getByTestId('mmore-checklists'))
    await waitFor(() =>
      expect(screen.getByTestId('m-checklists-route')).toBeTruthy(),
    )
  })

  it('routes to submission when the Submission row is tapped', async () => {
    renderAt('/m/more')
    fireEvent.click(screen.getByTestId('mmore-submission'))
    await waitFor(() =>
      expect(screen.getByTestId('m-submission-route')).toBeTruthy(),
    )
  })
})
