/**
 * Phase M0.4 — "Force desktop layout" toggle.
 *
 * iPad users in particular sometimes want the full desktop UI on a
 * small viewport (more dense, more keyboard shortcuts). This store
 * lets them flip a switch in Settings → Layout.
 *
 * The setting is persisted to localStorage under ``rma.forceDesktop``
 * so it survives reloads and "Add to Home Screen" relaunches.
 */
import { create } from 'zustand'
import { createJSONStorage, persist, type StateStorage } from 'zustand/middleware'

const STORAGE_KEY = 'rma.forceDesktop'

/**
 * Same jsdom fallback as ``backendUrl.ts`` — vitest's environment does
 * not expose ``window.localStorage`` by default.
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

type ForceDesktopState = {
  enabled: boolean
  toggle: () => void
  set: (value: boolean) => void
}

export const useForceDesktop = create<ForceDesktopState>()(
  persist(
    (set, get) => ({
      enabled: false,
      toggle: () => set({ enabled: !get().enabled }),
      set: (value) => set({ enabled: value }),
    }),
    { name: STORAGE_KEY, storage: createJSONStorage(getStableStorage) },
  ),
)
