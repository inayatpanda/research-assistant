/**
 * Fix-13/13 — single source of truth for the password policy used by
 * the desktop / mobile bundle.
 *
 * The Cloudflare Worker (``apps/license-server/src/lib/validation.ts``)
 * is the *real* source of truth — the server rejects anything that
 * doesn't satisfy these constraints. We mirror it client-side so we
 * can surface inline errors before the user makes a doomed round-trip.
 *
 * The site bundle (``apps/site``) keeps its own copy at
 * ``apps/site/src/lib/passwordRules.ts``; the two files are kept in
 * lock-step manually because the bundles ship to different surfaces
 * (Electron / Cloudflare Pages) and we don't want a runtime cross-bundle
 * import.
 */

/** Minimum number of characters in a valid password. */
export const PASSWORD_MIN_LENGTH = 10

/** HTML ``pattern`` attribute matching the server's ``isStrongPassword``. */
export const PASSWORD_PATTERN = '^(?=.*\\d).{10,256}$'

/** Human-readable hint shown beneath the password input. */
export const PASSWORD_HINT =
  'At least 10 characters with at least one digit.'

/** Returns ``true`` when the input would survive the server validator. */
export function isStrongPassword(pw: string): boolean {
  if (typeof pw !== 'string') return false
  if (pw.length < PASSWORD_MIN_LENGTH || pw.length > 256) return false
  if (!/\d/.test(pw)) return false
  return true
}
