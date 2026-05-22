import { afterEach, describe, expect, it } from 'vitest'

import {
  isAccountUsable,
  isLicenseFresh,
  trialDaysRemaining,
  useLicenseStore,
} from '@/lib/licenseStore'
import type { LicenseAccount } from '@/lib/licenseApi'

function fakeAccount(over: Partial<LicenseAccount> = {}): LicenseAccount {
  return {
    id: 'acc_1',
    email: 'a@b.test',
    display_name: 'A',
    type: 'trial',
    trial_expires_at: Date.now() + 24 * 60 * 60 * 1000,
    lifetime_purchased_at: null,
    email_verified_at: null,
    ...over,
  }
}

afterEach(() => {
  useLicenseStore.getState().clear()
})

describe('licenseStore', () => {
  it('setSession persists token + account and stamps lastVerifiedAt', () => {
    useLicenseStore.getState().setSession('tok', fakeAccount())
    const s = useLicenseStore.getState()
    expect(s.token).toBe('tok')
    expect(s.account?.email).toBe('a@b.test')
    expect(typeof s.lastVerifiedAt).toBe('number')
  })

  it('isLicenseFresh returns true within 7 days and false beyond', () => {
    useLicenseStore.getState().setSession('tok', fakeAccount())
    expect(isLicenseFresh()).toBe(true)
    // Backdate to 8 days ago.
    useLicenseStore
      .getState()
      .setLastVerified(Date.now() - 8 * 24 * 60 * 60 * 1000)
    expect(isLicenseFresh()).toBe(false)
  })

  it('isAccountUsable distinguishes lifetime / trial / expired / revoked', () => {
    expect(isAccountUsable(fakeAccount({ type: 'lifetime' }))).toBe(true)
    expect(isAccountUsable(fakeAccount({ type: 'trial' }))).toBe(true)
    expect(
      isAccountUsable(
        fakeAccount({ type: 'trial', trial_expires_at: Date.now() - 1000 }),
      ),
    ).toBe(false)
    expect(isAccountUsable(fakeAccount({ type: 'revoked' }))).toBe(false)
    expect(isAccountUsable(null)).toBe(false)
  })

  it('trialDaysRemaining counts up correctly', () => {
    const future = Date.now() + 5 * 24 * 60 * 60 * 1000 + 30_000
    expect(trialDaysRemaining(fakeAccount({ trial_expires_at: future }))).toBe(6)
    expect(trialDaysRemaining(fakeAccount({ type: 'lifetime' }))).toBeNull()
  })

  it('clear wipes the session', () => {
    useLicenseStore.getState().setSession('tok', fakeAccount())
    useLicenseStore.getState().clear()
    expect(useLicenseStore.getState().token).toBeNull()
    expect(useLicenseStore.getState().account).toBeNull()
  })

  it('Fix-13/11: tolerates a corrupt JSON payload in localStorage', () => {
    // We can't easily re-mount the persist middleware, so directly call
    // ``persist().rehydrate()`` on the live store with a localStorage
    // slot pre-populated with garbage. The store must end up at EMPTY
    // and must not throw.
    if (typeof window !== 'undefined' && window.localStorage) {
      window.localStorage.setItem('rma.licenseSession', '{not valid json')
    }
    // Drive the persist API to attempt rehydration.
    const storeWithPersist = useLicenseStore as unknown as {
      persist?: { rehydrate?: () => Promise<void> | void }
    }
    expect(() => storeWithPersist.persist?.rehydrate?.()).not.toThrow()
    // State is whatever rehydrate fell back to — must NOT have a token.
    expect(useLicenseStore.getState().token).toBeNull()
    expect(useLicenseStore.getState().account).toBeNull()
    // Clean up — leave nothing in localStorage for subsequent tests.
    if (typeof window !== 'undefined' && window.localStorage) {
      window.localStorage.removeItem('rma.licenseSession')
    }
  })
})
