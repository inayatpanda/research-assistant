/**
 * Phase M0.3 — configurable backend URL for the mobile PWA.
 *
 * On iPhone/iPad the PWA has to know which tailnet URL to talk to.
 * The user enters the URL once on first launch (or pastes it from the
 * desktop app's "Show tailnet URL" menu item), we ping `/api/health`
 * to validate, and stash the value in localStorage.
 *
 * The store is the *first* link in `resolveApiUrl()`'s precedence
 * chain — it overrides the Electron preload's `window.electron.apiUrl`
 * because the only time both can be set is "Electron renderer on a
 * dev machine", and the user-typed value wins.
 */
import { create } from 'zustand'
import { createJSONStorage, persist, type StateStorage } from 'zustand/middleware'

type ElectronBridge = {
  apiUrl?: string | null
  tailnetUrl?: string | null
  platform?: string
}

const STORAGE_KEY = 'rma.backendUrl'

/**
 * jsdom 29 (vitest's default environment) does not expose
 * `window.localStorage`. Mirror the in-memory fallback used by
 * `projectContext.ts` so tests never crash on `setItem`.
 */
function getStableStorage(): StateStorage {
  if (typeof window !== 'undefined' && window.localStorage) {
    return window.localStorage
  }
  const memory = new Map<string, string>()
  return {
    getItem: (k) => memory.get(k) ?? null,
    setItem: (k, v) => {
      memory.set(k, v)
    },
    removeItem: (k) => {
      memory.delete(k)
    },
  }
}

type BackendUrlState = {
  url: string | null
  setUrl: (url: string) => void
  clear: () => void
}

export const useBackendUrlStore = create<BackendUrlState>()(
  persist(
    (set) => ({
      url: null,
      setUrl: (url) => set({ url: url.trim() || null }),
      clear: () => set({ url: null }),
    }),
    { name: STORAGE_KEY, storage: createJSONStorage(getStableStorage) },
  ),
)

/**
 * Returns the resolved backend URL using the full precedence chain.
 *
 *   1. User-typed value in the zustand store (rma.backendUrl).
 *   2. Electron preload (`window.electron.apiUrl`).
 *   3. Vite build-time env var (VITE_API_URL).
 *   4. ``null`` — caller's responsibility to show the setup screen.
 *
 * Implemented as a plain function (not a hook) so it can be called
 * from non-React code paths too. Components that want reactivity
 * should subscribe to `useBackendUrlStore` directly.
 */
export function resolveBackendUrl(): string | null {
  const stored = useBackendUrlStore.getState().url
  if (stored) return stored
  if (typeof window !== 'undefined') {
    const bridge = (window as unknown as { electron?: ElectronBridge }).electron
    const fromElectron = bridge?.apiUrl
    if (typeof fromElectron === 'string' && fromElectron.length > 0) {
      return fromElectron
    }
  }
  const fromEnv = (import.meta as { env?: Record<string, string | undefined> })
    .env?.VITE_API_URL
  if (typeof fromEnv === 'string' && fromEnv.length > 0) return fromEnv
  return null
}

/**
 * Reactive variant — re-renders when the user updates the stored URL.
 * Returns ``null`` when no URL is configured (caller should route to
 * the `/m/setup` screen).
 */
export function useResolvedBackendUrl(): string | null {
  const stored = useBackendUrlStore((s) => s.url)
  if (stored) return stored
  if (typeof window !== 'undefined') {
    const bridge = (window as unknown as { electron?: ElectronBridge }).electron
    const fromElectron = bridge?.apiUrl
    if (typeof fromElectron === 'string' && fromElectron.length > 0) {
      return fromElectron
    }
  }
  const fromEnv = (import.meta as { env?: Record<string, string | undefined> })
    .env?.VITE_API_URL
  if (typeof fromEnv === 'string' && fromEnv.length > 0) return fromEnv
  return null
}
