/**
 * Phase M0.7 — DeviceRouter renders the correct shell based on viewport.
 *
 * We mount a tiny dual-route tree (`/desktop-marker`, `/m/library`) and
 * flip the JSDOM viewport between desktop + mobile widths. The router
 * either renders the desktop marker, redirects narrow viewports to
 * `/m/library`, or honours the "force desktop" override.
 */
import { cleanup, render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it } from 'vitest'

import { DeviceRouter } from '@/mobile/DeviceRouter'
import { useForceDesktop } from '@/mobile/lib/forceDesktop'

function setViewportWidth(width: number) {
  Object.defineProperty(window, 'innerWidth', {
    configurable: true,
    writable: true,
    value: width,
  })
  Object.defineProperty(window, 'innerHeight', {
    configurable: true,
    writable: true,
    value: 800,
  })
}

function Desktop() {
  return (
    <Routes>
      <Route path="/desktop-marker" element={<div data-testid="desktop">desk</div>} />
      <Route path="/" element={<div data-testid="desktop-home">desk-home</div>} />
    </Routes>
  )
}

function Mobile() {
  return (
    <Routes>
      <Route path="/m/library" element={<div data-testid="mobile">mobile</div>} />
    </Routes>
  )
}

function renderAt(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <DeviceRouter desktop={<Desktop />} mobile={<Mobile />} />
    </MemoryRouter>,
  )
}

beforeEach(() => {
  setViewportWidth(1280)
  useForceDesktop.setState({ enabled: false })
})

afterEach(() => {
  cleanup()
  useForceDesktop.setState({ enabled: false })
  setViewportWidth(1280)
})

describe('DeviceRouter', () => {
  it('renders the desktop shell at 1280px', () => {
    setViewportWidth(1280)
    renderAt('/desktop-marker')
    expect(screen.queryByTestId('desktop')).toBeTruthy()
    expect(screen.queryByTestId('mobile')).toBeFalsy()
  })

  it('redirects narrow viewports to the mobile shell', () => {
    setViewportWidth(600)
    renderAt('/desktop-marker')
    expect(screen.queryByTestId('mobile')).toBeTruthy()
    expect(screen.queryByTestId('desktop')).toBeFalsy()
  })

  it('forceDesktop overrides a narrow viewport', () => {
    setViewportWidth(600)
    useForceDesktop.setState({ enabled: true })
    renderAt('/desktop-marker')
    expect(screen.queryByTestId('desktop')).toBeTruthy()
    expect(screen.queryByTestId('mobile')).toBeFalsy()
  })

  it('explicit /m/* path renders mobile shell even on wide viewport', () => {
    setViewportWidth(1280)
    renderAt('/m/library')
    expect(screen.queryByTestId('mobile')).toBeTruthy()
    expect(screen.queryByTestId('desktop')).toBeFalsy()
  })
})
