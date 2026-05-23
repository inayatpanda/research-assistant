/**
 * Phase D2 — userAgent → OS mapping unit tests.
 */
import { describe, it, expect } from 'vitest'

import { detectOS, downloadUrlFor } from '@/lib/detectOS'

describe('detectOS', () => {
  it('maps modern Mac Safari to mac', () => {
    expect(
      detectOS(
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15',
      ),
    ).toEqual({ os: 'mac', isMobile: false, source: 'userAgent' })
  })

  it('maps Windows Chrome to win', () => {
    expect(
      detectOS(
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
      ),
    ).toEqual({ os: 'win', isMobile: false, source: 'userAgent' })
  })

  it('maps Ubuntu Firefox to linux', () => {
    expect(detectOS('Mozilla/5.0 (X11; Linux x86_64; rv:120.0) Gecko/20100101 Firefox/120.0')).toEqual({
      os: 'linux',
      isMobile: false,
      source: 'userAgent',
    })
  })

  it('maps iPad Safari to mac+mobile', () => {
    const d = detectOS(
      'Mozilla/5.0 (iPad; CPU OS 17_0 like Mac OS X) AppleWebKit/605.1.15 Version/17.0 Mobile/15E148 Safari/604.1',
    )
    expect(d.os).toBe('mac')
    expect(d.isMobile).toBe(true)
  })

  it('maps Android Chrome to linux+mobile', () => {
    const d = detectOS(
      'Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 Chrome/120.0.0.0 Mobile Safari/537.36',
    )
    expect(d.os).toBe('linux')
    expect(d.isMobile).toBe(true)
  })

  it('falls back to mac for an unknown agent', () => {
    expect(detectOS('Unknown/1.0')).toEqual({ os: 'mac', isMobile: false, source: 'fallback' })
  })

  it('downloadUrlFor produces the placeholder release URL', () => {
    expect(downloadUrlFor('mac')).toBe(
      'https://github.com/inayatpanda/research-assistant/releases/latest/download/Research-Assistant-Mac.dmg',
    )
    expect(downloadUrlFor('win')).toContain('Research-Assistant-Win.exe')
    expect(downloadUrlFor('linux')).toContain('Research-Assistant-Linux.AppImage')
  })
})
