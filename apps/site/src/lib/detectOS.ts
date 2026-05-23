/**
 * Phase D2 — OS detection for download CTAs.
 *
 * We feature-detect from `navigator.userAgent` because that is the only
 * cross-browser signal that is widely available. The hierarchy matters:
 *
 *   1. iPadOS 13+ reports "Macintosh" with touch points > 0. We treat
 *      iPad/iPhone as "mac" for download-CTA purposes since the user
 *      will install on their *laptop*, not their tablet, but we expose
 *      `isMobile` so the page can show a "install on laptop first" hint.
 *   2. Apple desktop UAs contain "Macintosh" or "Mac OS X".
 *   3. Windows UAs contain "Windows NT" (covers Win 10/11).
 *   4. Anything else with "Linux" → linux. (Android contains "Linux"
 *      but also "Android" — we strip mobile first.)
 *   5. Fallback → "mac" because the project is built on macOS and the
 *      author's primary audience is Mac-first orthopaedic researchers.
 */
export type DetectedOS = 'mac' | 'win' | 'linux'

export interface OSDetection {
  os: DetectedOS
  isMobile: boolean
  source: 'userAgent' | 'fallback'
}

export function detectOS(userAgent?: string): OSDetection {
  const ua = (userAgent ?? (typeof navigator !== 'undefined' ? navigator.userAgent : '') ?? '').toLowerCase()
  if (!ua) {
    return { os: 'mac', isMobile: false, source: 'fallback' }
  }

  // Mobile detection first — iPadOS 13+ masquerades as Mac, but the touch
  // platform string keeps Android distinguishable from desktop Linux.
  const isAndroid = ua.includes('android')
  const isIosLike = /iphone|ipad|ipod/.test(ua)

  if (isAndroid) {
    return { os: 'linux', isMobile: true, source: 'userAgent' }
  }
  if (isIosLike) {
    return { os: 'mac', isMobile: true, source: 'userAgent' }
  }
  if (ua.includes('windows nt')) {
    return { os: 'win', isMobile: false, source: 'userAgent' }
  }
  if (ua.includes('mac os x') || ua.includes('macintosh')) {
    return { os: 'mac', isMobile: false, source: 'userAgent' }
  }
  if (ua.includes('linux') || ua.includes('x11')) {
    return { os: 'linux', isMobile: false, source: 'userAgent' }
  }
  return { os: 'mac', isMobile: false, source: 'fallback' }
}

export const OS_LABEL: Record<DetectedOS, string> = {
  mac: 'macOS',
  win: 'Windows',
  linux: 'Linux',
}

export const OS_DOWNLOAD_FILE: Record<DetectedOS, string> = {
  mac: 'Research-Assistant-Mac.dmg',
  win: 'Research-Assistant-Win.exe',
  linux: 'Research-Assistant-Linux.AppImage',
}

/**
 * Placeholder release URL. The user replaces `inayatpanda/research-assistant` with
 * their real GitHub slug after creating the repo. The URL structure is
 * still valid — once filled in, GitHub Releases serves the artifact
 * directly.
 */
export const RELEASES_BASE =
  'https://github.com/inayatpanda/research-assistant/releases/latest/download'

export function downloadUrlFor(os: DetectedOS): string {
  return `${RELEASES_BASE}/${OS_DOWNLOAD_FILE[os]}`
}
