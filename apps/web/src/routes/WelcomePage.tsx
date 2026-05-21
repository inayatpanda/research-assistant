/**
 * Phase E1.4 — First-run welcome screen.
 *
 * Displayed when the renderer is running inside Electron and the user
 * navigates to `/welcome`. The page is intentionally informational only;
 * everything it explains (local storage path, tailnet access, bundle
 * import) maps to functionality that already exists elsewhere in the app.
 *
 * Bridge contract: the Electron preload exposes
 *   window.electron = { apiUrl, tailnetUrl, platform }
 * so the renderer doesn't need to know how the backend was spawned.
 */
import { Link } from 'react-router-dom'

type ElectronBridge = {
  apiUrl?: string | null
  tailnetUrl?: string | null
  platform?: string
}

function getElectron(): ElectronBridge | null {
  if (typeof window === 'undefined') return null
  return (window as unknown as { electron?: ElectronBridge }).electron ?? null
}

function dataPathHint(platform?: string): string {
  if (platform === 'darwin') {
    return '~/Library/Application Support/Research Assistant/'
  }
  if (platform === 'win32') {
    return '%APPDATA%\\Research Assistant\\'
  }
  return '~/.config/research-assistant/'
}

export default function WelcomePage() {
  const electron = getElectron()
  const tailnet = electron?.tailnetUrl ?? null
  const localUrl = electron?.apiUrl ?? null
  const platform = electron?.platform

  return (
    <div className="mx-auto max-w-3xl space-y-8 px-6 py-10">
      <header className="space-y-2">
        <h1 className="text-3xl font-bold">Welcome to Research Assistant</h1>
        <p className="text-muted-foreground">
          Everything lives on your laptop. No cloud, no subscription, no
          telemetry.
        </p>
      </header>

      <section className="rounded-lg border bg-card p-6">
        <h2 className="mb-2 text-xl font-semibold">Where your data is stored</h2>
        <p className="text-sm text-muted-foreground">
          Projects, articles, datasets, manuscripts and stats outputs sit in
          a single SQLite file plus a few folders under:
        </p>
        <pre className="mt-3 rounded bg-muted px-3 py-2 text-sm">
          {dataPathHint(platform)}
        </pre>
      </section>

      <section className="grid gap-4 md:grid-cols-2">
        <Link
          to="/"
          className="rounded-lg border bg-card p-6 transition hover:border-primary"
        >
          <h3 className="text-lg font-semibold">Start fresh</h3>
          <p className="mt-2 text-sm text-muted-foreground">
            Open the dashboard and create your first project.
          </p>
        </Link>
        <Link
          to="/settings"
          className="rounded-lg border bg-card p-6 transition hover:border-primary"
        >
          <h3 className="text-lg font-semibold">Import existing bundle</h3>
          <p className="mt-2 text-sm text-muted-foreground">
            Restore a project bundle exported from a browser-only session via
            Settings → Import.
          </p>
        </Link>
      </section>

      <section className="rounded-lg border bg-card p-6">
        <h2 className="mb-2 text-xl font-semibold">Access from your phone</h2>
        <p className="text-sm text-muted-foreground">
          To open this app from a second laptop or your phone, install
          Tailscale (free for personal use) on both devices. Once they share a
          tailnet, the URL below works inside your browser on any of them.
        </p>
        {tailnet ? (
          <div className="mt-3 rounded bg-muted px-3 py-2 font-mono text-sm">
            {tailnet}
          </div>
        ) : (
          <p className="mt-3 text-sm">
            Tailscale wasn&apos;t detected on this machine.{' '}
            <a
              href="https://tailscale.com/download"
              target="_blank"
              rel="noreferrer"
              className="text-primary underline"
            >
              Install Tailscale
            </a>{' '}
            to enable cross-device access.
          </p>
        )}
        {localUrl && (
          <p className="mt-3 text-xs text-muted-foreground">
            This-machine-only URL: <code>{localUrl}</code>
          </p>
        )}
      </section>
    </div>
  )
}
