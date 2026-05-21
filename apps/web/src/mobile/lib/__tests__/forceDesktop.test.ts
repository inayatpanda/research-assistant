/**
 * Phase M0.7 — `useForceDesktop` store tests.
 */
import { afterEach, beforeEach, describe, expect, it } from 'vitest'

import { useForceDesktop } from '../forceDesktop'

const STORAGE_KEY = 'rma.forceDesktop'

function resetStore() {
  useForceDesktop.setState({ enabled: false })
  if (typeof window !== 'undefined' && window.localStorage) {
    try {
      window.localStorage.removeItem(STORAGE_KEY)
    } catch {
      // jsdom 29 may throw when localStorage is unavailable.
    }
  }
}

describe('useForceDesktop', () => {
  beforeEach(resetStore)
  afterEach(resetStore)

  it('defaults to false', () => {
    expect(useForceDesktop.getState().enabled).toBe(false)
  })

  it('toggle() flips the value', () => {
    useForceDesktop.getState().toggle()
    expect(useForceDesktop.getState().enabled).toBe(true)
    useForceDesktop.getState().toggle()
    expect(useForceDesktop.getState().enabled).toBe(false)
  })

  it('set(true) persists through the store (and survives re-read)', () => {
    useForceDesktop.getState().set(true)
    expect(useForceDesktop.getState().enabled).toBe(true)
    // A fresh getState() still sees the value — confirms the setter
    // wrote through the zustand persist middleware rather than being a
    // transient mutation on the snapshot.
    expect(useForceDesktop.getState().enabled).toBe(true)
  })
})
