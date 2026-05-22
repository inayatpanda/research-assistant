/**
 * Phase L1c.8 — LoginPage tests.
 *
 * Mocks fetch and asserts both the happy path (token saved) and the
 * device_limit_exceeded path (amber banner rendered).
 */
import { cleanup, render, screen, fireEvent, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, it, expect, vi } from 'vitest'
import { MemoryRouter } from 'react-router-dom'

import LoginPage from '@/pages/LoginPage'

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

function fillAndSubmit() {
  fireEvent.change(screen.getByLabelText(/email/i), {
    target: { value: 'jane@example.com' },
  })
  fireEvent.change(screen.getByLabelText(/password/i), {
    target: { value: 'supersecret123' },
  })
  fireEvent.click(screen.getByTestId('login-submit'))
}

describe('LoginPage', () => {
  it('persists the token on a successful login', async () => {
    mockFetchOnce(200, {
      token: 'tok-login-1',
      account: {
        id: 'acct-1',
        email: 'jane@example.com',
        display_name: 'Jane',
        type: 'trial',
        trial_expires_at: Date.now() + 100000,
        lifetime_purchased_at: null,
        email_verified_at: null,
      },
      session: {
        id: 'sess-1',
        device_id: 'd-1',
        device_label: 'Web',
        user_agent: null,
        ip: null,
        last_seen_at: Date.now(),
        created_at: Date.now(),
        expires_at: Date.now() + 100000,
      },
    })

    render(
      <MemoryRouter>
        <LoginPage />
      </MemoryRouter>,
    )

    fillAndSubmit()

    await waitFor(() =>
      expect(window.localStorage.getItem('rma.licenseSession.token')).toBe(
        'tok-login-1',
      ),
    )
  })

  it('shows the device-limit banner on a 409 device_limit_exceeded', async () => {
    mockFetchOnce(409, {
      error: 'device_limit_exceeded',
      devices: [],
    })

    render(
      <MemoryRouter>
        <LoginPage />
      </MemoryRouter>,
    )

    fillAndSubmit()

    await waitFor(() =>
      expect(screen.getByTestId('login-device-limit')).toBeInTheDocument(),
    )
    expect(screen.getByTestId('login-device-limit').textContent ?? '').toMatch(
      /signed in on 5 devices/i,
    )
  })
})
