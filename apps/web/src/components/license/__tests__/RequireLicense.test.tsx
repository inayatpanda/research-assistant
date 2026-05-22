import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { cleanup, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'

const verifyMock = vi.fn()

vi.mock('@/lib/licenseApi', async () => {
  const actual =
    await vi.importActual<typeof import('@/lib/licenseApi')>('@/lib/licenseApi')
  return {
    ...actual,
    licenseApi: {
      ...actual.licenseApi,
      verify: (...args: unknown[]) => verifyMock(...args),
    },
  }
})

import { RequireLicense } from '@/components/license/RequireLicense'
import { LicenseError } from '@/lib/licenseApi'
import { useLicenseStore } from '@/lib/licenseStore'

function fakeAccount(over: Partial<{ type: 'trial' | 'lifetime' | 'revoked'; trial_expires_at: number | null }> = {}) {
  return {
    id: 'acc_1',
    email: 'a@b.test',
    display_name: 'A',
    type: over.type ?? ('lifetime' as const),
    trial_expires_at: over.trial_expires_at ?? null,
    lifetime_purchased_at: Date.now() - 100,
    email_verified_at: null,
  }
}

function renderApp() {
  return render(
    <MemoryRouter initialEntries={['/private']}>
      <Routes>
        <Route
          path="/private"
          element={
            <RequireLicense>
              <div>private-content</div>
            </RequireLicense>
          }
        />
        <Route path="/license" element={<div>license-page</div>} />
        <Route path="/upgrade" element={<div>upgrade-page</div>} />
      </Routes>
    </MemoryRouter>,
  )
}

beforeEach(() => {
  verifyMock.mockReset()
  useLicenseStore.getState().clear()
})
afterEach(() => cleanup())

describe('RequireLicense', () => {
  it('redirects to /license when no token is stored', async () => {
    renderApp()
    await waitFor(() => {
      expect(screen.getByText('license-page')).toBeTruthy()
    })
  })

  it('allows fresh sessions through without re-verifying', async () => {
    useLicenseStore.getState().setSession('tok', fakeAccount())
    renderApp()
    expect(screen.getByText('private-content')).toBeTruthy()
    expect(verifyMock).not.toHaveBeenCalled()
  })

  it('redirects to /upgrade when the trial has expired', async () => {
    useLicenseStore
      .getState()
      .setSession(
        'tok',
        fakeAccount({ type: 'trial', trial_expires_at: Date.now() - 1000 }),
      )
    renderApp()
    await waitFor(() => {
      expect(screen.getByText('upgrade-page')).toBeTruthy()
    })
  })

  it('clears state and bounces to /license on a 401 from verify', async () => {
    useLicenseStore.getState().setSession('tok', fakeAccount())
    // Backdate so RequireLicense decides to re-verify.
    useLicenseStore
      .getState()
      .setLastVerified(Date.now() - 8 * 24 * 60 * 60 * 1000)
    verifyMock.mockRejectedValueOnce(
      new LicenseError('invalid_token', 'invalid_token', 401, {
        error: 'invalid_token',
      }),
    )
    renderApp()
    await waitFor(() => {
      expect(screen.getByText('license-page')).toBeTruthy()
    })
    expect(useLicenseStore.getState().token).toBeNull()
  })

  it('grants offline grace if network fails within the 7-day window', async () => {
    useLicenseStore.getState().setSession('tok', fakeAccount())
    // Just inside the freshness window (6 days old).
    useLicenseStore
      .getState()
      .setLastVerified(Date.now() - 6 * 24 * 60 * 60 * 1000)
    verifyMock.mockRejectedValueOnce(
      new LicenseError('network_error', 'offline', 0, null),
    )
    renderApp()
    await waitFor(() => {
      expect(screen.getByText('private-content')).toBeTruthy()
    })
  })
})
