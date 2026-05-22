/**
 * Phase L1c.8 — SignupPage tests.
 *
 * Mocks the global fetch and asserts the happy-path success screen plus
 * the inline-error rendering on a 409 email_in_use response.
 */
import { cleanup, render, screen, fireEvent, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, it, expect, vi } from 'vitest'
import { MemoryRouter } from 'react-router-dom'

import SignupPage from '@/pages/SignupPage'

const NOW = 1_716_500_000_000
const TRIAL_EXPIRES = NOW + 30 * 24 * 60 * 60 * 1000

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
  fireEvent.change(screen.getByLabelText(/display name/i), {
    target: { value: 'Dr Jane Doe' },
  })
  fireEvent.change(screen.getByLabelText(/email/i), {
    target: { value: 'jane@example.com' },
  })
  fireEvent.change(screen.getByLabelText(/password/i), {
    target: { value: 'supersecret123' },
  })
  fireEvent.click(screen.getByTestId('signup-terms'))
  fireEvent.click(screen.getByTestId('signup-submit'))
}

describe('SignupPage', () => {
  it('shows the success screen with the user email after a 200 response', async () => {
    mockFetchOnce(200, {
      token: 'tok-abc',
      account: {
        id: 'acct-1',
        email: 'jane@example.com',
        display_name: 'Dr Jane Doe',
        type: 'trial',
        trial_expires_at: TRIAL_EXPIRES,
        lifetime_purchased_at: null,
        email_verified_at: null,
      },
      session: {
        id: 'sess-1',
        device_id: 'dev-1',
        device_label: 'Web (web)',
        user_agent: null,
        ip: null,
        last_seen_at: NOW,
        created_at: NOW,
        expires_at: NOW + 31536000000,
      },
    })

    render(
      <MemoryRouter>
        <SignupPage />
      </MemoryRouter>,
    )

    fillAndSubmit()

    await waitFor(() =>
      expect(screen.getByTestId('signup-success')).toBeInTheDocument(),
    )
    expect(screen.getByTestId('signup-success-email').textContent).toBe(
      'jane@example.com',
    )
    expect(window.localStorage.getItem('rma.licenseSession.token')).toBe('tok-abc')
  })

  it('renders an inline error when the server returns 409 email_in_use', async () => {
    mockFetchOnce(409, { error: 'email_in_use' })

    render(
      <MemoryRouter>
        <SignupPage />
      </MemoryRouter>,
    )

    fillAndSubmit()

    await waitFor(() =>
      expect(screen.getByTestId('signup-error')).toBeInTheDocument(),
    )
    expect(screen.getByTestId('signup-error').textContent ?? '').toMatch(
      /account with that email already exists/i,
    )
  })
})
