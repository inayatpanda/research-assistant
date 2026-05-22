import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'

const loginMock = vi.fn()
const signupMock = vi.fn()

vi.mock('@/lib/licenseApi', async () => {
  const actual =
    await vi.importActual<typeof import('@/lib/licenseApi')>('@/lib/licenseApi')
  return {
    ...actual,
    licenseApi: {
      ...actual.licenseApi,
      login: (...args: unknown[]) => loginMock(...args),
      signup: (...args: unknown[]) => signupMock(...args),
    },
  }
})

import LicensePage from '@/routes/LicensePage'
import { LicenseError } from '@/lib/licenseApi'
import { useLicenseStore } from '@/lib/licenseStore'

function fakeAccount() {
  return {
    id: 'acc_1',
    email: 'a@b.test',
    display_name: 'A',
    type: 'lifetime' as const,
    trial_expires_at: null,
    lifetime_purchased_at: Date.now(),
    email_verified_at: null,
  }
}

function renderPage() {
  return render(
    <MemoryRouter>
      <LicensePage />
    </MemoryRouter>,
  )
}

beforeEach(() => {
  loginMock.mockReset()
  signupMock.mockReset()
  useLicenseStore.getState().clear()
})
afterEach(() => cleanup())

describe('LicensePage', () => {
  it('submits the login form and persists the session', async () => {
    loginMock.mockResolvedValueOnce({
      token: 'tok',
      account: fakeAccount(),
      session: null,
      devices: [],
    })
    renderPage()
    fireEvent.change(screen.getByTestId('license-input-email'), {
      target: { value: 'a@b.test' },
    })
    fireEvent.change(screen.getByTestId('license-input-password'), {
      target: { value: 'longpass1234' },
    })
    fireEvent.click(screen.getByTestId('license-submit'))
    await waitFor(() => {
      expect(useLicenseStore.getState().token).toBe('tok')
    })
    expect(loginMock).toHaveBeenCalled()
  })

  it('submits the signup form once terms are accepted', async () => {
    signupMock.mockResolvedValueOnce({
      token: 'tok',
      account: fakeAccount(),
      session: null,
      devices: [],
    })
    renderPage()
    fireEvent.click(screen.getByTestId('license-tab-signup'))
    fireEvent.change(screen.getByTestId('license-input-name'), {
      target: { value: 'Smith' },
    })
    fireEvent.change(screen.getByTestId('license-input-email'), {
      target: { value: 'a@b.test' },
    })
    fireEvent.change(screen.getByTestId('license-input-password'), {
      target: { value: 'longpass1234' },
    })
    fireEvent.click(screen.getByTestId('license-accept-terms'))
    fireEvent.click(screen.getByTestId('license-submit'))
    await waitFor(() => {
      expect(signupMock).toHaveBeenCalled()
    })
  })

  it('shows an error on 401 invalid credentials', async () => {
    loginMock.mockRejectedValueOnce(
      new LicenseError('invalid_credentials', 'bad', 401, {
        error: 'invalid_credentials',
      }),
    )
    renderPage()
    fireEvent.change(screen.getByTestId('license-input-email'), {
      target: { value: 'a@b.test' },
    })
    fireEvent.change(screen.getByTestId('license-input-password'), {
      target: { value: 'longpass1234' },
    })
    fireEvent.click(screen.getByTestId('license-submit'))
    await waitFor(() => {
      expect(screen.getByTestId('license-error').textContent).toMatch(
        /wrong email or password/i,
      )
    })
  })

  it('opens the device manager on 409 device_limit_exceeded', async () => {
    loginMock.mockRejectedValueOnce(
      new LicenseError('device_limit_exceeded', 'full', 409, {
        error: 'device_limit_exceeded',
        devices: [
          {
            id: 's1',
            device_id: 'd1',
            device_label: 'Mac Safari',
            user_agent: 'UA',
            ip: '1.2.3.4',
            last_seen_at: Date.now(),
            created_at: Date.now(),
            expires_at: Date.now() + 1000,
          },
        ],
      }),
    )
    renderPage()
    fireEvent.change(screen.getByTestId('license-input-email'), {
      target: { value: 'a@b.test' },
    })
    fireEvent.change(screen.getByTestId('license-input-password'), {
      target: { value: 'longpass1234' },
    })
    fireEvent.click(screen.getByTestId('license-submit'))
    await waitFor(() => {
      expect(screen.getByTestId('device-manager-dialog')).toBeTruthy()
    })
    expect(screen.getByTestId('device-row-s1')).toBeTruthy()
  })
})
