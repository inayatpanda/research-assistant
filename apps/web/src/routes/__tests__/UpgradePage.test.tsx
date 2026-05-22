import { afterEach, describe, expect, it, vi } from 'vitest'
import { cleanup, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'

vi.mock('@/lib/licenseApi', async () => {
  const actual =
    await vi.importActual<typeof import('@/lib/licenseApi')>('@/lib/licenseApi')
  return {
    ...actual,
    licenseApi: { ...actual.licenseApi, verify: vi.fn() },
  }
})

import UpgradePage from '@/routes/UpgradePage'

afterEach(() => cleanup())

describe('UpgradePage', () => {
  it('renders Lemon Squeezy checkout link with placeholder URL', () => {
    render(
      <MemoryRouter>
        <UpgradePage />
      </MemoryRouter>,
    )
    const link = screen.getByTestId('upgrade-checkout-link') as HTMLAnchorElement
    expect(link.href).toMatch(/lemonsqueezy\.com\/buy/i)
    expect(screen.getByTestId('upgrade-refresh')).toBeTruthy()
  })
})
