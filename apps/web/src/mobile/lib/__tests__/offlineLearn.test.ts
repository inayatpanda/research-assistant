/**
 * Phase M1.5 — offlineLearn smoke tests.
 *
 * Uses `fake-indexeddb/auto` (already in node_modules thanks to `idb`'s
 * deps) when available, but we deliberately stub `openDB` so we don't
 * need any test-only deps. The store-shape we test is the public
 * helpers that callers actually use:
 *
 *   1. `cacheable()` persists the value on success and exposes it
 *      under the key supplied.
 *   2. When the fetcher throws, `cacheable()` falls back to the cached
 *      copy and flips `offline: true`.
 *   3. With no cache + a failing fetcher, the original error propagates.
 */
import { beforeEach, describe, expect, it, vi } from 'vitest'

// In-memory IDB stand-in. We mock the `idb` module so the offline lib
// never touches the real IndexedDB API (jsdom only ships a partial
// implementation that throws on `openDB(..., {upgrade: ...})`).
const memory: Map<string, { key: string; data: unknown; cachedAt: number }> = new Map()

vi.mock('idb', () => ({
  openDB: vi.fn(async () => ({
    get: async (_store: string, key: string) => memory.get(key),
    put: async (_store: string, value: { key: string; data: unknown; cachedAt: number }) => {
      memory.set(value.key, value)
      return value.key
    },
    getAllKeys: async (_store: string) => Array.from(memory.keys()),
    delete: async (_store: string, key: string) => {
      memory.delete(key)
    },
  })),
}))

import {
  _resetOfflineLearnForTests,
  cacheable,
  clearScope,
  PUBLIC_SCOPE,
  readOfflineEntry,
  writeOfflineEntry,
} from '@/mobile/lib/offlineLearn'
import { useLicenseStore } from '@/lib/licenseStore'

beforeEach(async () => {
  useLicenseStore.getState().clear()
  // Wait for the async scope-wipe kicked off by clear() to settle
  // before the test populates fresh data — otherwise its delete()
  // calls would race the test writes and silently nuke them.
  const { pendingScopeClear } = await import('@/lib/licenseStore')
  if (pendingScopeClear) await pendingScopeClear
  memory.clear()
  _resetOfflineLearnForTests()
})

describe('offlineLearn', () => {
  it('persists data on a successful network fetch', async () => {
    const fetcher = vi.fn(async () => ({ hello: 'world' }))
    const result = await cacheable('foo:bar', fetcher)
    expect(result.offline).toBe(false)
    expect(result.data).toEqual({ hello: 'world' })
    expect(await readOfflineEntry('foo:bar')).toEqual({ hello: 'world' })
  })

  it('falls back to the cached copy when the fetcher fails', async () => {
    await writeOfflineEntry('foo:bar', { hello: 'cached' })
    const fetcher = vi.fn(async () => {
      throw new Error('network down')
    })
    const result = await cacheable<{ hello: string }>('foo:bar', fetcher)
    expect(result.offline).toBe(true)
    expect(result.data).toEqual({ hello: 'cached' })
  })

  it('re-throws when fetcher fails AND there is nothing cached', async () => {
    const err = new Error('still down')
    const fetcher = vi.fn(async () => {
      throw err
    })
    await expect(cacheable('cold:key', fetcher)).rejects.toBe(err)
  })

  describe('Fix-13/6: user-scoping', () => {
    function fakeAccount(id: string) {
      return {
        id,
        email: `${id}@b.test`,
        display_name: id,
        type: 'lifetime' as const,
        trial_expires_at: null,
        lifetime_purchased_at: Date.now(),
        email_verified_at: null,
      }
    }

    it('writes under different keys for different licence accounts', async () => {
      useLicenseStore.getState().setSession('tok-a', fakeAccount('acc-a'))
      await writeOfflineEntry('article:42', { user: 'A' })
      useLicenseStore.getState().setSession('tok-b', fakeAccount('acc-b'))
      // User B reads the same logical key and must NOT see user A's data.
      expect(await readOfflineEntry('article:42')).toBeNull()
      await writeOfflineEntry('article:42', { user: 'B' })
      // User A's data is still there under their own scope.
      expect(await readOfflineEntry('article:42', 'acc-a')).toEqual({
        user: 'A',
      })
      expect(await readOfflineEntry('article:42', 'acc-b')).toEqual({
        user: 'B',
      })
    })

    it('clearScope removes only the targeted scope', async () => {
      await writeOfflineEntry('k', { x: 1 }, 'acc-a')
      await writeOfflineEntry('k', { y: 2 }, 'acc-b')
      await clearScope('acc-a')
      expect(await readOfflineEntry('k', 'acc-a')).toBeNull()
      expect(await readOfflineEntry('k', 'acc-b')).toEqual({ y: 2 })
    })

    it('falls back to the public scope when there is no signed-in account', async () => {
      // No useLicenseStore.setSession() above — readScope() returns PUBLIC_SCOPE.
      await writeOfflineEntry('k', { z: 3 })
      expect(await readOfflineEntry('k', PUBLIC_SCOPE)).toEqual({ z: 3 })
    })
  })
})
