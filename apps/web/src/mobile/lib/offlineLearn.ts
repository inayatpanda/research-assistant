/**
 * Phase M1.2 — IndexedDB-backed offline cache for Learn entries.
 *
 * Pattern: the React Query queryFn wraps a network call in
 * ``cacheable(key, fetcher)``. On a successful network response the
 * value is mirrored to IndexedDB; on a failed network call (offline,
 * server down, etc.) we try to return whatever's cached.
 *
 * Why IndexedDB and not localStorage:
 *   - Learn entries can be ~10KB of markdown each. localStorage has a
 *     5MB cap that we'd burn through quickly.
 *   - idb (already in deps) gives us a tiny promise-based wrapper over
 *     the native API — no extra runtime cost.
 *
 * The store is intentionally schema-light: a single object store keyed
 * by ``<category>:<slug>`` (e.g. ``stat-tests:wilcoxon``). List
 * summaries are keyed by ``__list:<category>``. That keeps the
 * read-path trivially fast and lets us nuke the cache by bumping the
 * DB version without touching consumers.
 */
import { openDB, type IDBPDatabase } from 'idb'

const DB_NAME = 'rma-learn'
const DB_VERSION = 1
const STORE = 'entries'

type EntryRecord = {
  key: string
  data: unknown
  cachedAt: number
}

let dbPromise: Promise<IDBPDatabase> | null = null

function getDb(): Promise<IDBPDatabase> {
  if (!dbPromise) {
    dbPromise = openDB(DB_NAME, DB_VERSION, {
      upgrade(db) {
        if (!db.objectStoreNames.contains(STORE)) {
          db.createObjectStore(STORE, { keyPath: 'key' })
        }
      },
    })
  }
  return dbPromise
}

/** Reset the cached DB handle. Exposed for tests. */
export function _resetOfflineLearnForTests() {
  dbPromise = null
}

/**
 * Read a value from the offline store. Returns ``null`` if nothing is
 * cached for that key, or if IndexedDB isn't available (jsdom in
 * vitest sometimes fakes a partial API).
 */
export async function readOfflineEntry<T>(key: string): Promise<T | null> {
  try {
    const db = await getDb()
    const row = (await db.get(STORE, key)) as EntryRecord | undefined
    if (!row) return null
    return row.data as T
  } catch {
    return null
  }
}

/**
 * Persist a value to the offline store. Fire-and-forget — errors are
 * swallowed because a missing cache entry is never worse than a stale
 * one (the network fetch already succeeded by the time we get here).
 */
export async function writeOfflineEntry<T>(key: string, data: T): Promise<void> {
  try {
    const db = await getDb()
    await db.put(STORE, { key, data, cachedAt: Date.now() })
  } catch {
    // ignore — offline caching is best-effort
  }
}

/**
 * Outcome of a `cacheable()` resolution. The `offline` flag tells the
 * UI to surface a small "Offline" badge in the page header.
 */
export type CacheableResult<T> = {
  data: T
  offline: boolean
}

/**
 * Wrap a fetcher with the offline strategy:
 *
 *   1. Try the network. On success, persist + return ``{ data, offline: false }``.
 *   2. On failure, check IndexedDB. If found, return ``{ data, offline: true }``.
 *   3. Otherwise re-throw the original network error so React Query
 *      can surface it.
 */
export async function cacheable<T>(
  key: string,
  fetcher: () => Promise<T>,
): Promise<CacheableResult<T>> {
  try {
    const data = await fetcher()
    await writeOfflineEntry(key, data)
    return { data, offline: false }
  } catch (err) {
    const cached = await readOfflineEntry<T>(key)
    if (cached != null) {
      return { data: cached, offline: true }
    }
    throw err
  }
}

/** Compose a deterministic key from a category + slug. */
export function entryKey(category: string, slug: string): string {
  return `${category}:${slug}`
}

/** List-summary key namespace (kept distinct from per-entry keys). */
export function listKey(category: string): string {
  return `__list:${category}`
}
