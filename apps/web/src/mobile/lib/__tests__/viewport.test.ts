/**
 * Phase M0.7 — `useViewport` + `useIsMobile` tests.
 */
import { act, renderHook } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it } from 'vitest'

import { useForceDesktop } from '../forceDesktop'
import { useIsMobile, useViewport, VIEWPORT_THROTTLE_MS } from '../viewport'

function setViewportWidth(width: number, height = 800) {
  Object.defineProperty(window, 'innerWidth', {
    configurable: true,
    writable: true,
    value: width,
  })
  Object.defineProperty(window, 'innerHeight', {
    configurable: true,
    writable: true,
    value: height,
  })
}

beforeEach(() => {
  // Reset to a "desktop" baseline before each test so hooks initialise
  // deterministically.
  setViewportWidth(1280, 800)
  useForceDesktop.setState({ enabled: false })
})

afterEach(() => {
  setViewportWidth(1280, 800)
  useForceDesktop.setState({ enabled: false })
})

describe('useViewport', () => {
  it('returns the current window dimensions', () => {
    setViewportWidth(1024, 768)
    const { result } = renderHook(() => useViewport())
    expect(result.current.width).toBe(1024)
    expect(result.current.height).toBe(768)
  })

  it('emits the leading edge of a resize immediately', () => {
    const { result } = renderHook(() => useViewport())
    expect(result.current.width).toBe(1280)
    act(() => {
      setViewportWidth(600)
      window.dispatchEvent(new Event('resize'))
    })
    expect(result.current.width).toBe(600)
  })

  it('throttles rapid bursts but emits a trailing-edge update', async () => {
    const { result } = renderHook(() => useViewport())
    // First resize — leading edge fires immediately.
    act(() => {
      setViewportWidth(900)
      window.dispatchEvent(new Event('resize'))
    })
    expect(result.current.width).toBe(900)
    // Second + third within the throttle window — only the trailing
    // value (the most recent dispatch) should win.
    act(() => {
      setViewportWidth(800)
      window.dispatchEvent(new Event('resize'))
      setViewportWidth(720)
      window.dispatchEvent(new Event('resize'))
    })
    // Until the throttle timer fires, we still see 900.
    expect(result.current.width).toBe(900)
    await act(async () => {
      await new Promise((r) => setTimeout(r, VIEWPORT_THROTTLE_MS + 25))
    })
    expect(result.current.width).toBe(720)
  })
})

describe('useIsMobile', () => {
  it('returns true below 900px', () => {
    setViewportWidth(600)
    const { result } = renderHook(() => useIsMobile())
    expect(result.current).toBe(true)
  })

  it('returns false at exactly 900px (breakpoint is < 900)', () => {
    setViewportWidth(900)
    const { result } = renderHook(() => useIsMobile())
    expect(result.current).toBe(false)
  })

  it('returns false above 900px', () => {
    setViewportWidth(1200)
    const { result } = renderHook(() => useIsMobile())
    expect(result.current).toBe(false)
  })

  it('forceDesktop overrides a narrow viewport', () => {
    setViewportWidth(500)
    useForceDesktop.setState({ enabled: true })
    const { result } = renderHook(() => useIsMobile())
    expect(result.current).toBe(false)
  })
})
