/**
 * Phase M0.7 — ForceDesktopCard renders + updates the store.
 */
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it } from 'vitest'

import { ForceDesktopCard } from '@/components/settings/ForceDesktopCard'
import { useForceDesktop } from '@/mobile/lib/forceDesktop'

beforeEach(() => {
  useForceDesktop.setState({ enabled: false })
})
afterEach(() => {
  cleanup()
  useForceDesktop.setState({ enabled: false })
})

describe('ForceDesktopCard', () => {
  it('renders the labelled toggle', () => {
    render(<ForceDesktopCard />)
    expect(screen.getByText('Layout')).toBeTruthy()
    const toggle = screen.getByRole('switch', { name: /force desktop layout/i })
    expect(toggle).toBeTruthy()
    expect((toggle as HTMLInputElement).checked).toBe(false)
  })

  it('toggling the switch updates the force-desktop store', () => {
    render(<ForceDesktopCard />)
    const toggle = screen.getByRole('switch', { name: /force desktop layout/i })
    fireEvent.click(toggle)
    expect(useForceDesktop.getState().enabled).toBe(true)
    expect((toggle as HTMLInputElement).checked).toBe(true)
  })
})
