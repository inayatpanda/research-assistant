import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { cleanup, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'

const accountMock = vi.fn()
const logoutMock = vi.fn()

vi.mock('@/lib/licenseApi', async () => {
  const actual =
    await vi.importActual<typeof import('@/lib/licenseApi')>('@/lib/licenseApi')
  return {
    ...actual,
    licenseApi: {
      ...actual.licenseApi,
      account: (...args: unknown[]) => accountMock(...args),
      logout: (...args: unknown[]) => logoutMock(...args),
      logoutAll: (...args: unknown[]) => logoutMock(...args),
      revokeDevice: vi.fn(),
    },
  }
})

import { LicenseStatusCard } from '@/components/settings/LicenseStatusCard'
import { useLicenseStore } from '@/lib/licenseStore'

beforeEach(() => {
  accountMock.mockReset()
  logoutMock.mockReset()
  useLicenseStore.getState().clear()
})
afterEach(() => cleanup())

describe('LicenseStatusCard', () => {
  it('renders trial status with days remaining', async () => {
    useLicenseStore.getState().setSession('tok', {
      id: 'acc_1',
      email: 'a@b.test',
      display_name: 'Dr Smith',
      type: 'trial',
      trial_expires_at: Date.now() + 5 * 24 * 60 * 60 * 1000 + 30_000,
      lifetime_purchased_at: null,
      email_verified_at: null,
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
    expect(screen.getByText('Dr Smith')).toBeTruthy()
    expect(screen.getByText('a@b.test')).toBeTruthy()
    // Days-left badge is "Trial · 6d left" (5 days remaining + change → ceil = 6)
    await waitFor(() => {
      expect(screen.getByText(/trial · 6d left/i)).toBeTruthy()
    })
    expect(screen.getByTestId('license-upgrade')).toBeTruthy()
  })
})
