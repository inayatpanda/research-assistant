/**
 * Phase L1b — Persistent client-side state for the licence layer.
 *
 * Stores the bearer token + cached account + last-verified timestamp in
 * localStorage so the app survives reloads without re-prompting for
 * credentials. The ``isLicenseFresh`` helper enforces a 7-day offline
 * grace: if we verified within the last 7 days and now have no
 * connectivity, the app still launches.
 */
import { create } from 'zustand'
import { createJSONStorage, persist, type StateStorage } from 'zustand/middleware'

import type {
  LicenseAccount,
  LicenseDevice,
  LicenseSession,
} from './licenseApi'

/**
 * jsdom and SSR environments don't expose ``window.localStorage``;
 * persist would throw on first use. Fall back to an in-memory Map so
 * tests can exercise the store without monkey-patching globals.
 *
 * Fix-13/11 — wraps every ``getItem`` in a try/catch so a corrupt JSON
 * payload (or a localStorage quota error) returns ``null`` instead of
 * killing the boot. ``createJSONStorage`` will then treat the slot as
 * empty and the store rehydrates to ``EMPTY``.
 */
function getStableStorage(): StateStorage {
  const inner: StateStorage =
    typeof window !== 'undefined' && window.localStorage
      ? window.localStorage
      : (() => {
          const memory = new Map<string, string>()
          return {
            getItem: (k) => memory.get(k) ?? null,
            setItem: (k, v) => {
              memory.set(k, v)
            },
            removeItem: (k) => {
              memory.delete(k)
            },
          } satisfies StateStorage
        })()
  return {
    getItem: (k) => {
      try {
        return inner.getItem(k)
      } catch (err) {
        // eslint-disable-next-line no-console
        console.warn('[licenseStore] storage.getItem failed:', err)
        return null
      }
    },
    setItem: (k, v) => {
      try {
        inner.setItem(k, v)
      } catch (err) {
        // Quota-exceeded etc — not fatal; the session is still usable
        // in-memory, just not persisted across reloads.
        // eslint-disable-next-line no-console
        console.warn('[licenseStore] storage.setItem failed:', err)
      }
    },
    removeItem: (k) => {
      try {
        inner.removeItem(k)
      } catch {
        /* ignore */
      }
    },
  }
}

const SEVEN_DAYS_MS = 7 * 24 * 60 * 60 * 1000

export interface LicenseSessionState {
  token: string | null
  account: LicenseAccount | null
  session: LicenseSession | null
  devices: LicenseDevice[] | null
  lastVerifiedAt: number | null
}

interface LicenseStoreActions {
  setSession(
    token: string,
    account: LicenseAccount,
    session?: LicenseSession,
    devices?: LicenseDevice[],
  ): void
  setLastVerified(timestamp: number): void
  setAccount(account: LicenseAccount): void
  setDevices(devices: LicenseDevice[]): void
  clear(): void
}

/**
 * Surface the in-flight scope-wipe so tests (and callers that need to
 * wait for the cache to drain before re-rendering) can await it.
 */
export let pendingScopeClear: Promise<void> | null = null

const EMPTY: LicenseSessionState = {
  token: null,
  account: null,
  session: null,
  devices: null,
  lastVerifiedAt: null,
}

export const useLicenseStore = create<LicenseSessionState & LicenseStoreActions>()(
  persist(
    (set) => ({
      ...EMPTY,
      setSession(token, account, session, devices) {
        set({
          token,
          account,
          session: session ?? null,
          devices: devices ?? null,
          lastVerifiedAt: Date.now(),
        })
      },
      setLastVerified(timestamp) {
        set({ lastVerifiedAt: timestamp })
      },
      setAccount(account) {
        set({ account })
      },
      setDevices(devices) {
        set({ devices })
      },
      clear() {
        // Capture the outgoing account id BEFORE we wipe the state so
        // the offline-cache scope wipe targets the right slot
        // (Fix-13/6). Best-effort: a stuck IndexedDB shouldn't block
        // a logout. Surfaced as the module-level
        // ``pendingScopeClear`` promise so tests can await it.
        const outgoing = useLicenseStore.getState().account?.id ?? null
        set({ ...EMPTY })
        if (outgoing) {
          pendingScopeClear = import('@/mobile/lib/offlineLearn')
            .then(({ clearScope }) => clearScope(outgoing))
            .catch(() => {
              /* ignore — clearing offline cache is best-effort */
            })
        }
      },
    }),
    {
      name: 'rma.licenseSession',
      storage: createJSONStorage(getStableStorage),
      // Only persist the relevant fields; not the actions.
      partialize: (state) => ({
        token: state.token,
        account: state.account,
        session: state.session,
        devices: state.devices,
        lastVerifiedAt: state.lastVerifiedAt,
      }),
      // Fix-13/11: if the stored payload is corrupt JSON / from an
      // older schema, zustand's persist middleware logs an error but
      // silently leaves the in-memory state at its initial value. We
      // make that recovery explicit: if the hydrate emits an error,
      // discard whatever it tried to set and fall back to EMPTY.
      onRehydrateStorage: () => (_state, error) => {
        if (error) {
          // eslint-disable-next-line no-console
          console.warn(
            '[licenseStore] rehydration failed, falling back to empty:',
            error,
          )
          try {
            useLicenseStore.setState({ ...EMPTY })
          } catch {
            /* ignore */
          }
        }
      },
    },
  ),
)

/**
 * Returns ``true`` if the cached verify response is younger than 7 days,
 * regardless of whether the app currently has network connectivity.
 */
export function isLicenseFresh(state?: LicenseSessionState): boolean {
  const s = state ?? useLicenseStore.getState()
  if (!s.lastVerifiedAt) return false
  return Date.now() - s.lastVerifiedAt < SEVEN_DAYS_MS
}

/**
 * Returns ``true`` if the account exists and is currently usable
 * (not revoked, and either lifetime OR a trial that has not expired).
 */
export function isAccountUsable(account: LicenseAccount | null): boolean {
  if (!account) return false
  if (account.type === 'revoked') return false
  if (account.type === 'lifetime') return true
  if (account.type === 'trial') {
    return (account.trial_expires_at ?? 0) > Date.now()
  }
  return false
}

export function trialDaysRemaining(account: LicenseAccount | null): number | null {
  if (!account || account.type !== 'trial' || !account.trial_expires_at) return null
  const ms = account.trial_expires_at - Date.now()
  if (ms <= 0) return 0
  return Math.ceil(ms / (24 * 60 * 60 * 1000))
}

// Convenience selectors.
export const useLicenseAccount = () =>
  useLicenseStore((s) => s.account)
export const useLicenseToken = () => useLicenseStore((s) => s.token)
export const useLicenseDevices = () => useLicenseStore((s) => s.devices)
export const useLastVerifiedAt = () =>
  useLicenseStore((s) => s.lastVerifiedAt)
