/**
 * Phase M0.7 — MobileShell renders the 5-tab bottom nav and highlights
 * the active tab. The shell is wrapped in <RequireAuth>; we mock
 * `useCurrentUser` so the auth gate resolves synchronously.
 */
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'

vi.mock('@/hooks/useAuth', () => ({
  useCurrentUser: () => ({
    data: { id: 'u1', email: 'a@b.com', display_name: 'A' },
    isLoading: false,
  }),
}))

import { MobileShell } from '@/mobile/MobileShell'
import { MOBILE_TABS } from '@/mobile/lib/tabs'

function renderAt(path: string) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[path]}>
        <Routes>
          <Route element={<MobileShell />}>
            <Route path="/m/library" element={<div>Library page</div>} />
            <Route path="/m/manuscripts" element={<div>Manuscripts page</div>} />
            <Route path="/m/stats" element={<div>Stats page</div>} />
            <Route path="/m/learn" element={<div>Learn page</div>} />
            <Route path="/m/more" element={<div>More page</div>} />
          </Route>
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

afterEach(cleanup)

describe('MobileShell', () => {
  it('renders all five bottom tabs with aria labels', () => {
    renderAt('/m/library')
    expect(screen.queryByTestId('mobile-bottom-tabs')).toBeTruthy()
    for (const tab of MOBILE_TABS) {
      expect(screen.getByLabelText(tab.ariaLabel)).toBeTruthy()
    }
  })

  it('highlights the active tab with an indicator', () => {
    renderAt('/m/stats')
    const indicator = screen.queryByTestId('tab-indicator-stats')
    expect(indicator).toBeTruthy()
    // Sibling tabs should not have an indicator.
    expect(screen.queryByTestId('tab-indicator-library')).toBeFalsy()
    expect(screen.queryByTestId('tab-indicator-learn')).toBeFalsy()
  })

  it('applies safe-area padding on the bottom tab bar', () => {
    renderAt('/m/library')
    const tabs = screen.getByTestId('mobile-bottom-tabs') as HTMLElement
    expect(tabs.className).toMatch(/safe-area-inset-bottom/)
  })
})
