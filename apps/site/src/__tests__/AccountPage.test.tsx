/**
 * Phase L1c.8 — AccountPage test.
 *
 * Asserts the page renders the trial status when a token is present in
 * localStorage and the /api/account response is OK.
 */
import { cleanup, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, it, expect, vi } from 'vitest'
import { MemoryRouter } from 'react-router-dom'

import AccountPage from '@/pages/AccountPage'

function mockFetchOnce(status: number, body: unknown) {
  // @ts-expect-error vitest mock typing
  global.fetch = vi.fn(async () =>
    Promise.resolve({
      ok: status >= 200 && status < 300,
      status,
      json: async () => body,
    }),
  )
}

afterEach(() => {
  cleanup()
  vi.restoreAllMocks()
  window.localStorage.clear()
})

beforeEach(() => {
  window.localStorage.clear()
})

describe('AccountPage', () => {
  it('does not crash when no token is present in localStorage', () => {
    // No token in localStorage — page should render its loading shell
    // and the router-driven redirect to /login will fire on mount.
    render(
      <MemoryRouter>
        <AccountPage />
      </MemoryRouter>,
    )
    expect(screen.getByText(/loading your account/i)).toBeInTheDocument()
  })

  it('renders the trial status banner when account is loaded', async () => {
    window.localStorage.setItem('rma.licenseSession.token', 'tok-account-1')
    const now = Date.now()
    mockFetchOnce(200, {
      valid: true,
      account: {
        id: 'acct-1',
        email: 'jane@example.com',
        display_name: 'Dr Jane Doe',
        type: 'trial',
        trial_expires_at: now + 15 * 24 * 60 * 60 * 1000,
        lifetime_purchased_at: null,
        email_verified_at: null,
        created_at: now - 24 * 60 * 60 * 1000,
      },
      session: {
        id: 'sess-1',
        device_id: 'd-1',
        device_label: 'Web (web)',
        user_agent: null,
        ip: null,
        last_seen_at: now,
        created_at: now,
        expires_at: now + 31536000000,
      },
      devices: [
        {
          id: 'sess-1',
          device_id: 'd-1',
          device_label: 'Web (web)',
          user_agent: null,
          ip: null,
          last_seen_at: now,
          created_at: now,
          expires_at: now + 31536000000,
        },
      ],
    })

    render(
      <MemoryRouter>
        <AccountPage />
      </MemoryRouter>,
    )

    await waitFor(() =>
      expect(screen.getByTestId('account-status')).toBeInTheDocument(),
    )
    expect(screen.getByRole('heading', { level: 1, name: /hi, dr jane doe/i })).toBeInTheDocument()
    expect(screen.getByTestId('account-upgrade-cta')).toBeInTheDocument()
  })
})
