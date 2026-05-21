/**
 * Phase M0.7 — `useBackendUrlStore` + `resolveBackendUrl` tests.
 */
import { afterEach, beforeEach, describe, expect, it } from 'vitest'

import { resolveBackendUrl, useBackendUrlStore } from '../backendUrl'

const STORAGE_KEY = 'rma.backendUrl'

function resetStore() {
  useBackendUrlStore.setState({ url: null })
  if (typeof window !== 'undefined' && window.localStorage) {
    try {
      window.localStorage.removeItem(STORAGE_KEY)
    } catch {
      // jsdom 29 may not expose localStorage; ignore.
    }
  }
  delete (window as unknown as { electron?: unknown }).electron
}

describe('useBackendUrlStore', () => {
  beforeEach(resetStore)
  afterEach(resetStore)

  it('defaults to null', () => {
    expect(useBackendUrlStore.getState().url).toBeNull()
    expect(resolveBackendUrl()).toBeNull()
  })

  it('setUrl trims input, persists, and is reflected in resolveBackendUrl()', () => {
    useBackendUrlStore
      .getState()
      .setUrl('  http://my-mac.tail-xyz.ts.net:18000  ')
    expect(useBackendUrlStore.getState().url).toBe(
      'http://my-mac.tail-xyz.ts.net:18000',
    )
    expect(resolveBackendUrl()).toBe('http://my-mac.tail-xyz.ts.net:18000')
  })

  it('clear() resets to null', () => {
    useBackendUrlStore.getState().setUrl('http://x.example')
    useBackendUrlStore.getState().clear()
    expect(useBackendUrlStore.getState().url).toBeNull()
    expect(resolveBackendUrl()).toBeNull()
  })
})
