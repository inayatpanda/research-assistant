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
  })),
}))

import {
  _resetOfflineLearnForTests,
  cacheable,
  readOfflineEntry,
  writeOfflineEntry,
} from '@/mobile/lib/offlineLearn'

beforeEach(() => {
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
})
