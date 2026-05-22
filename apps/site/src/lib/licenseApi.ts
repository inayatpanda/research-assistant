/**
 * Phase L1c — Landing-site client for the L1a Cloudflare Worker licence
 * server.
 *
 * This mirrors apps/web/src/lib/licenseApi.ts but is standalone — the
 * marketing site is its own Vite bundle and must not import from the
 * Electron-targeted apps/web tree. The session token is persisted to
 * localStorage under ``rma.licenseSession.token`` so the /account page
 * can survive a page reload without re-prompting for credentials.
 */

export const LICENSE_BASE_URL =
  'https://research-assistant-license.workers.dev'

export const TOKEN_STORAGE_KEY = 'rma.licenseSession.token'
export const TRIAL_TOKEN_STORAGE_KEY = 'rma.licenseSession.trialToken'
const DEVICE_ID_KEY = 'rma.site.deviceId'

// ---------------------------------------------------------------------------
// Types — mirror the worker's `publicAccount` / `publicSession` shapes.
// ---------------------------------------------------------------------------

export type LicenseType = 'trial' | 'lifetime' | 'revoked'

export interface LicenseAccount {
  id: string
  email: string
  display_name: string
  type: LicenseType
  trial_expires_at: number | null
  lifetime_purchased_at: number | null
  email_verified_at: number | null
  created_at?: number
}

export interface LicenseSession {
  id: string
  device_id: string
  device_label: string | null
  user_agent: string | null
  ip: string | null
  last_seen_at: number
  created_at: number
  expires_at: number
}

export interface LicenseAuthResponse {
  token: string
  account: LicenseAccount
  session: LicenseSession
  devices?: LicenseSession[]
}

export interface LicenseAccountResponse {
  valid: true
  account: LicenseAccount
  session: LicenseSession
  devices: LicenseSession[]
}

export interface LicenseVerifyResponse {
  valid: true
  account: LicenseAccount
  session: LicenseSession
}

export class LicenseError extends Error {
  code: string
  status: number
  raw: unknown
  devices?: LicenseSession[]
  constructor(code: string, message: string, status: number, raw?: unknown) {
    super(message)
    this.code = code
    this.status = status
    this.raw = raw
    if (
      raw &&
      typeof raw === 'object' &&
      'devices' in raw &&
      Array.isArray((raw as { devices: unknown }).devices)
    ) {
      this.devices = (raw as { devices: LicenseSession[] }).devices
    }
  }
}

// ---------------------------------------------------------------------------
// Local storage helpers.
// ---------------------------------------------------------------------------

function safeLocalStorage(): Storage | null {
  if (typeof window === 'undefined') return null
  try {
    return window.localStorage
  } catch {
    return null
  }
}

export function saveSessionToken(token: string): void {
  const ls = safeLocalStorage()
  if (ls) ls.setItem(TOKEN_STORAGE_KEY, token)
}

export function loadSessionToken(): string | null {
  const ls = safeLocalStorage()
  if (!ls) return null
  return ls.getItem(TOKEN_STORAGE_KEY)
}

export function clearSessionToken(): void {
  const ls = safeLocalStorage()
  if (ls) ls.removeItem(TOKEN_STORAGE_KEY)
}

export function saveTrialToken(token: string): void {
  const ls = safeLocalStorage()
  if (ls) ls.setItem(TRIAL_TOKEN_STORAGE_KEY, token)
}

// ---------------------------------------------------------------------------
// Device fingerprint helpers.
// ---------------------------------------------------------------------------

function randomHex(bytes: number): string {
  const buf = new Uint8Array(bytes)
  if (typeof crypto !== 'undefined' && crypto.getRandomValues) {
    crypto.getRandomValues(buf)
  } else {
    for (let i = 0; i < bytes; i++) buf[i] = Math.floor(Math.random() * 256)
  }
  return Array.from(buf, (b) => b.toString(16).padStart(2, '0')).join('')
}

export function getOrCreateDeviceId(): string {
  const ls = safeLocalStorage()
  if (!ls) return 'ssr-fallback-device'
  let id = ls.getItem(DEVICE_ID_KEY)
  if (!id) {
    id = randomHex(16)
    ls.setItem(DEVICE_ID_KEY, id)
  }
  return id
}

export function getDeviceLabel(): string {
  if (typeof navigator === 'undefined') return 'Web browser'
  const ua = navigator.userAgent
  let platform = 'Web'
  if (/iPhone|iPod/.test(ua)) platform = 'iPhone'
  else if (/iPad/.test(ua)) platform = 'iPad'
  else if (/Android/.test(ua)) platform = 'Android'
  else if (/Mac/.test(ua)) platform = 'Mac'
  else if (/Windows/.test(ua)) platform = 'Windows'
  else if (/Linux/.test(ua)) platform = 'Linux'
  return `${platform} (web)`
}

// ---------------------------------------------------------------------------
// HTTP helper.
// ---------------------------------------------------------------------------

interface FetchOptions {
  method?: 'GET' | 'POST' | 'DELETE' | 'PATCH'
  body?: unknown
  token?: string | null
}

async function call<T>(path: string, opts: FetchOptions = {}): Promise<T> {
  const url = `${LICENSE_BASE_URL}${path}`
  const headers: Record<string, string> = {}
  if (opts.body !== undefined) headers['Content-Type'] = 'application/json'
  if (opts.token) headers.Authorization = `Bearer ${opts.token}`

  let res: Response
  try {
    res = await fetch(url, {
      method: opts.method ?? 'GET',
      headers,
      body: opts.body !== undefined ? JSON.stringify(opts.body) : undefined,
    })
  } catch (err) {
    throw new LicenseError(
      'network_error',
      err instanceof Error ? err.message : 'Network error',
      0,
      err,
    )
  }

  let raw: unknown
  try {
    raw = await res.json()
  } catch {
    raw = null
  }

  if (!res.ok) {
    const code =
      (raw && typeof raw === 'object' && 'error' in raw
        ? String((raw as { error: unknown }).error)
        : null) ?? `http_${res.status}`
    throw new LicenseError(code, code, res.status, raw)
  }

  return raw as T
}

// ---------------------------------------------------------------------------
// Public API surface.
// ---------------------------------------------------------------------------

export interface SignupArgs {
  email: string
  password: string
  display_name: string
}

export interface LoginArgs {
  email: string
  password: string
}

export const licenseApi = {
  async signup(args: SignupArgs): Promise<LicenseAuthResponse> {
    return call<LicenseAuthResponse>('/api/signup', {
      method: 'POST',
      body: {
        ...args,
        device_id: getOrCreateDeviceId(),
        device_label: getDeviceLabel(),
      },
    })
  },

  async login(args: LoginArgs): Promise<LicenseAuthResponse> {
    return call<LicenseAuthResponse>('/api/login', {
      method: 'POST',
      body: {
        ...args,
        device_id: getOrCreateDeviceId(),
        device_label: getDeviceLabel(),
      },
    })
  },

  async verify(token: string): Promise<LicenseVerifyResponse> {
    return call<LicenseVerifyResponse>('/api/verify', { token })
  },

  async account(token: string): Promise<LicenseAccountResponse> {
    return call<LicenseAccountResponse>('/api/account', { token })
  },

  async logout(token: string): Promise<{ ok: true }> {
    return call<{ ok: true }>('/api/logout', { method: 'POST', token })
  },

  async forgotPassword(email: string): Promise<{ ok: true }> {
    return call<{ ok: true }>('/api/forgot-password', {
      method: 'POST',
      body: { email },
    })
  },

  async resetPassword(args: {
    token: string
    new_password: string
  }): Promise<{ ok: true }> {
    return call<{ ok: true }>('/api/reset-password', {
      method: 'POST',
      body: args,
    })
  },
}

// ---------------------------------------------------------------------------
// Human-readable error mapping.
// ---------------------------------------------------------------------------

export const ERROR_MESSAGES: Record<string, string> = {
  email_in_use:
    "An account with that email already exists. Try signing in instead.",
  validation_failed:
    'Please double-check the form fields and try again.',
  invalid_credentials:
    "We couldn't sign you in with those details. Check your email and password and try again.",
  account_revoked:
    'This account has been revoked. Contact support@research-assistant.dev if you think this is a mistake.',
  rate_limited:
    "You've made too many attempts. Please wait a few minutes and try again.",
  device_limit_exceeded:
    "You're already signed in on 5 devices. Sign in on one of your existing devices and revoke a slot in Settings → License.",
  network_error:
    "Can't reach the licence server. Check your internet connection and try again.",
  invalid_token:
    'This reset link is invalid or has already been used. Request a new one.',
  token_expired: 'This reset link has expired. Request a new one.',
}

export function humaniseError(err: unknown): string {
  if (err instanceof LicenseError) {
    return ERROR_MESSAGES[err.code] ?? `Something went wrong (${err.code}).`
  }
  if (err instanceof Error) return err.message
  return 'Something went wrong. Please try again.'
}

// ---------------------------------------------------------------------------
// Pricing constants — kept here so PricingPage / HomePage / SignupPage all
// reference the same single source of truth.
// ---------------------------------------------------------------------------

export const LIFETIME_PRICE_USD = 29
export const TRIAL_DAYS = 30
export const DEVICE_LIMIT = 5
export const LEMON_SQUEEZY_CHECKOUT_URL =
  'https://research-assistant.lemonsqueezy.com/buy/REPLACE-AFTER-LS-PRODUCT-CREATED'
