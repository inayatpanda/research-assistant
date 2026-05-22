/**
 * Fix-E2E/5 — LicenseStatusCard offline-UX regression.
 *
 * When the licence-server hostname can't be resolved (DNS failure, dev
 * without the worker running, ad-blocker), the card must surface a
 * friendly "showing cached info" banner instead of silently failing while
 * the console prints ERR_NAME_NOT_RESOLVED.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { cleanup, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'

const accountMock = vi.fn()

vi.mock('@/lib/licenseApi', async () => {
  const actual =
    await vi.importActual<typeof import('@/lib/licenseApi')>('@/lib/licenseApi')
  return {
    ...actual,
    licenseApi: {
      ...actual.licenseApi,
      account: (...args: unknown[]) => accountMock(...args),
      logout: vi.fn(),
      logoutAll: vi.fn(),
      revokeDevice: vi.fn(),
    },
  }
})

import { LicenseStatusCard } from '@/components/settings/LicenseStatusCard'
import { LicenseError } from '@/lib/licenseApi'
import { useLicenseStore } from '@/lib/licenseStore'

beforeEach(() => {
  accountMock.mockReset()
  useLicenseStore.getState().clear()
})
afterEach(() => cleanup())

describe('LicenseStatusCard — DNS-failure UX (Fix-E2E/5)', () => {
  it('shows the cached-info hint when the licence server is unreachable', async () => {
    useLicenseStore.getState().setSession('tok-x', {
      id: 'acc_offline',
      email: 'offline@example.test',
      display_name: 'Offline User',
      type: 'lifetime',
      trial_expires_at: null,
      lifetime_purchased_at: Date.now(),
      email_verified_at: Date.now(),
    })
    // Simulate the network layer rejecting with the LicenseError code we
    // emit from licenseApi.call() when fetch() itself throws.
    accountMock.mockRejectedValueOnce(
      new LicenseError('network_error', 'DNS failure', 0, null),
    )
    render(
      <MemoryRouter>
        <LicenseStatusCard />
      </MemoryRouter>,
    )
    // The cached display_name + email still render (the audit's "cached
    // info" requirement).
    expect(screen.getByText('Offline User')).toBeTruthy()
    expect(screen.getByText('offline@example.test')).toBeTruthy()
    // The offline hint becomes visible after the rejected effect resolves.
    await waitFor(() => {
      expect(screen.getByTestId('license-offline-hint')).toBeTruthy()
    })
    expect(screen.getByTestId('license-offline-hint').textContent ?? '').toMatch(
      /Could not reach the license server/i,
    )
  })

  it('does not show the offline hint on a successful account fetch', async () => {
    useLicenseStore.getState().setSession('tok-y', {
      id: 'acc_online',
      email: 'ok@example.test',
      display_name: 'Online User',
      type: 'lifetime',
      trial_expires_at: null,
      lifetime_purchased_at: Date.now(),
      email_verified_at: Date.now(),
    })
    accountMock.mockResolvedValueOnce({
      valid: true,
      account: useLicenseStore.getState().account,
      session: null,
      devices: [],
    })
    render(
      <MemoryRouter>
        <LicenseStatusCard />
      </MemoryRouter>,
    )
    await waitFor(() => {
      expect(screen.getByText('Online User')).toBeTruthy()
    })
    expect(screen.queryByTestId('license-offline-hint')).toBeNull()
  })
})
