/**
 * Phase M0.3 — first-launch tailnet URL configuration.
 *
 * The user lands here when the PWA has no backend URL configured (or
 * when they tap "Change backend URL" from the More tab). They paste
 * the URL their desktop app displayed in its "Show tailnet URL" menu,
 * we ping `/api/health`, and stash the value in localStorage.
 *
 * This screen has NO bottom tabs and NO RequireAuth — the API call
 * for `/me` would fail without a valid backend URL, so we can't
 * gate on auth here.
 */
import { useState } from 'react'
import { Loader2 } from 'lucide-react'
import { useLocation, useNavigate } from 'react-router-dom'

import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'

import { MobileHeader } from '../components/MobileHeader'
import { useBackendUrlStore } from '../lib/backendUrl'

/**
 * Best-effort URL sanitiser:
 *   - trim trailing slash
 *   - reject empty / whitespace-only strings
 *   - allow `http://` and `https://` schemes only
 *
 * We do NOT enforce a TLD here — `http://my-mac.tail-xyz.ts.net:18000`
 * is a Tailscale MagicDNS name with a perfectly valid (if unusual)
 * suffix.
 */
function normaliseUrl(input: string): string | null {
  const trimmed = input.trim().replace(/\/+$/, '')
  if (!trimmed) return null
  if (!/^https?:\/\//i.test(trimmed)) return null
  try {
    // URL parse for an extra layer of validation. If the user typed
    // "http:// " (with a space), this throws.
    new URL(trimmed)
    return trimmed
  } catch {
    return null
  }
}

export default function MobileSetupPage() {
  const navigate = useNavigate()
  const location = useLocation()
  const current = useBackendUrlStore((s) => s.url)
  const setUrl = useBackendUrlStore((s) => s.setUrl)
  const [value, setValue] = useState<string>(current ?? '')
  const [status, setStatus] = useState<'idle' | 'checking' | 'error'>('idle')
  const [error, setError] = useState<string | null>(null)

  // Allow the caller to specify `?next=/m/library` to bounce back to
  // wherever the user was trying to reach.
  const nextPath = new URLSearchParams(location.search).get('next') ?? '/m/library'

  async function onSave(event: React.FormEvent) {
    event.preventDefault()
    setError(null)
    const cleaned = normaliseUrl(value)
    if (!cleaned) {
      setError('Enter a URL beginning with http:// or https://')
      return
    }
    setStatus('checking')
    try {
      // Ping /api/health directly using fetch so we don't accidentally
      // pin the current axios baseURL — the new value must work in
      // isolation.
      const res = await fetch(`${cleaned}/api/health`, {
        method: 'GET',
        credentials: 'include',
      })
      if (!res.ok) {
        throw new Error(`Backend responded ${res.status}`)
      }
      setUrl(cleaned)
      setStatus('idle')
      navigate(nextPath, { replace: true })
    } catch (e: unknown) {
      setStatus('error')
      const msg = e instanceof Error ? e.message : String(e)
      setError(`Couldn't reach ${cleaned}: ${msg}`)
    }
  }

  return (
    <div className="flex min-h-[100dvh] flex-col bg-background">
      <MobileHeader title="Backend URL" />
      <main className="flex-1 overflow-y-auto px-4 py-6">
        <Card>
          <CardHeader>
            <CardTitle className="text-[15px]">Connect to your laptop</CardTitle>
          </CardHeader>
          <CardContent>
            <form onSubmit={onSave} className="space-y-4">
              <div className="space-y-1.5">
                <Label htmlFor="backend-url">Tailnet URL</Label>
                <Input
                  id="backend-url"
                  inputMode="url"
                  autoComplete="url"
                  autoCorrect="off"
                  autoCapitalize="none"
                  spellCheck={false}
                  placeholder="http://your-mac.tail-xxx.ts.net:18000"
                  value={value}
                  onChange={(e) => setValue(e.target.value)}
                  disabled={status === 'checking'}
                />
                <p className="text-[12px] text-muted-foreground">
                  Paste your laptop&apos;s tailnet URL — e.g.,{' '}
                  <code className="rounded bg-muted px-1 py-0.5 font-mono text-[11px]">
                    http://your-mac.tail-xxx.ts.net:18000
                  </code>
                  . Open the desktop app&apos;s &ldquo;Show tailnet URL&rdquo;
                  menu to find it.
                </p>
              </div>
              {error ? (
                <div
                  role="alert"
                  className="rounded-md border border-destructive/30 bg-destructive/10 px-3 py-2 text-[12px] text-destructive"
                >
                  {error}
                </div>
              ) : null}
              <Button
                type="submit"
                disabled={status === 'checking' || value.trim().length === 0}
                className="w-full"
              >
                {status === 'checking' ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Checking…
                  </>
                ) : (
                  'Connect'
                )}
              </Button>
            </form>
          </CardContent>
        </Card>
      </main>
    </div>
  )
}
