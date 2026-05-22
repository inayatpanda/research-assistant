/**
 * Fix-13/13 — single source of truth for the password policy used by
 * the landing-site bundle.
 *
 * Kept in lock-step with ``apps/web/src/lib/passwordRules.ts`` and the
 * server-side validator at
 * ``apps/license-server/src/lib/validation.ts``. The server is the
 * real source of truth; we mirror its rule on the client so the user
 * sees an inline error instead of round-tripping a 400.
 */

export const PASSWORD_MIN_LENGTH = 10

export const PASSWORD_PATTERN = '^(?=.*\\d).{10,256}$'

export const PASSWORD_HINT =
  'At least 10 characters with at least one digit.'

export function isStrongPassword(pw: string): boolean {
  if (typeof pw !== 'string') return false
  if (pw.length < PASSWORD_MIN_LENGTH || pw.length > 256) return false
  if (!/\d/.test(pw)) return false
  return true
}
