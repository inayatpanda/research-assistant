/**
 * Phase L1b — Client for the L1a Cloudflare Worker licence server.
 *
 * The licence layer sits ABOVE S1's per-install auth: a user signs into
 * their licence first, then into their per-install Research Assistant
 * account. The token is a 32-byte random string returned by the worker;
 * we send it as ``Authorization: Bearer <token>`` and persist it via
 * ``licenseStore`` in localStorage.
 *
 * API base URL precedence:
 *   1. ``import.meta.env.VITE_LICENSE_SERVER_URL`` (set at build time)
 *   2. ``https://research-assistant-license.workers.dev`` (placeholder
 *      until the user picks a custom domain)
 *
 * The verify call is cached client-side for up to 7 days — see
 * ``licenseStore.isLicenseFresh``.
 */

const FALLBACK_BASE_URL = 'https://research-assistant-license.workers.dev'

function envBase(): string | undefined {
  // Vite injects import.meta.env at build time. Guarded for test envs
  // that may not provide the meta object.
  try {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const env = (import.meta as any).env
    if (env?.VITE_LICENSE_SERVER_URL) return String(env.VITE_LICENSE_SERVER_URL)
  } catch {
    /* not in a Vite context */
  }
  return undefined
}

export function getLicenseBaseUrl(): string {
  return envBase() ?? FALLBACK_BASE_URL
}

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

export interface LicenseDevice extends LicenseSession {}

export interface LicenseVerifyResponse {
  valid: true
  account: LicenseAccount
  session: LicenseSession
}

export interface LicenseAccountResponse extends LicenseVerifyResponse {
  devices: LicenseDevice[]
}

export interface LicenseAuthResponse {
  token: string
  account: LicenseAccount
  session: LicenseSession
  devices?: LicenseDevice[]
}

export interface DeviceLimitError {
  error: 'device_limit_exceeded'
  devices: LicenseDevice[]
}

export class LicenseError extends Error {
  code: string
  status: number
  raw: unknown
  devices?: LicenseDevice[]
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
      this.devices = (raw as { devices: LicenseDevice[] }).devices
    }
  }
}

// ---------------------------------------------------------------------------
// Device fingerprint helpers.
// ---------------------------------------------------------------------------

const DEVICE_ID_KEY = 'rma.deviceId'

export function getOrCreateDeviceId(): string {
  if (typeof window === 'undefined' || !window.localStorage) {
    // SSR / test environments — return a stable per-process default.
    return 'ssr-fallback-device'
  }
  let id = window.localStorage.getItem(DEVICE_ID_KEY)
  if (!id) {
    id = randomHex(16)
    window.localStorage.setItem(DEVICE_ID_KEY, id)
  }
  return id
}

export function getDeviceLabel(): string {
  if (typeof navigator === 'undefined') return 'Unknown device'
  const ua = navigator.userAgent
  let platform = 'Device'
  if (/iPhone|iPod/.test(ua)) platform = 'iPhone'
  else if (/iPad/.test(ua)) platform = 'iPad'
  else if (/Android/.test(ua)) platform = 'Android'
  else if (/Mac/.test(ua)) platform = 'Mac'
  else if (/Windows/.test(ua)) platform = 'Windows'
  else if (/Linux/.test(ua)) platform = 'Linux'
  let browser = 'Browser'
  if (/Chrome/.test(ua) && !/Edg|OPR/.test(ua)) browser = 'Chrome'
  else if (/Firefox/.test(ua)) browser = 'Firefox'
  else if (/Safari/.test(ua) && !/Chrome/.test(ua)) browser = 'Safari'
  else if (/Edg/.test(ua)) browser = 'Edge'
  return `${platform} ${browser}`
}

function randomHex(bytes: number): string {
  const buf = new Uint8Array(bytes)
  if (typeof crypto !== 'undefined' && crypto.getRandomValues) {
    crypto.getRandomValues(buf)
  } else {
    for (let i = 0; i < bytes; i++) buf[i] = Math.floor(Math.random() * 256)
  }
  return Array.from(buf, (b) => b.toString(16).padStart(2, '0')).join('')
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
  const url = `${getLicenseBaseUrl()}${path}`
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

  async logoutAll(token: string): Promise<{ ok: true }> {
    return call<{ ok: true }>('/api/logout-all', { method: 'POST', token })
  },

  async revokeDevice(token: string, sessionId: string): Promise<{ ok: true }> {
    return call<{ ok: true }>(`/api/devices/${encodeURIComponent(sessionId)}`, {
      method: 'DELETE',
      token,
    })
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
