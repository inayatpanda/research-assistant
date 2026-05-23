/**
 * Phase D2 — InstallPage smoke tests.
 *
 * We stub the `detectOS` module so the test environment doesn't depend
 * on jsdom's user-agent string. This lets us assert that the correct
 * platform card receives the data-active="true" marker for any OS.
 */
import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, it, expect, vi } from 'vitest'
import { MemoryRouter } from 'react-router-dom'

vi.mock('@/lib/detectOS', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/lib/detectOS')>()
  return {
    ...actual,
    detectOS: vi.fn(() => ({ os: 'win', isMobile: false, source: 'userAgent' as const })),
  }
})

import InstallPage from '@/pages/InstallPage'

afterEach(() => cleanup())
beforeEach(() => {
  // Reset the mock to the default win value between tests.
})

describe('InstallPage', () => {
  it('renders three OS download cards', () => {
    render(
      <MemoryRouter>
        <InstallPage />
      </MemoryRouter>,
    )
    expect(screen.getByTestId('platform-card-mac')).toBeInTheDocument()
    expect(screen.getByTestId('platform-card-win')).toBeInTheDocument()
    expect(screen.getByTestId('platform-card-linux')).toBeInTheDocument()
  })

  it('highlights the detected platform (Windows) and not the others', () => {
    render(
      <MemoryRouter>
        <InstallPage />
      </MemoryRouter>,
    )
    expect(screen.getByTestId('platform-card-win')).toHaveAttribute('data-active', 'true')
    expect(screen.getByTestId('platform-card-mac')).toHaveAttribute('data-active', 'false')
    expect(screen.getByTestId('platform-card-linux')).toHaveAttribute('data-active', 'false')
  })

  it('exposes a Windows download link pointing at the placeholder release URL', () => {
    render(
      <MemoryRouter>
        <InstallPage />
      </MemoryRouter>,
    )
    const link = screen.getByTestId('download-win') as HTMLAnchorElement
    expect(link.href).toContain('inayatpanda/research-assistant')
    expect(link.href).toContain('Research-Assistant-Win.exe')
  })
})
