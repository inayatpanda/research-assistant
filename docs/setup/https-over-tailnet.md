# HTTPS over Tailnet (optional)

> **Status:** optional. For a personal install (one researcher, one laptop,
> two devices) you can skip this entire page — the v1 build is happy on
> plain HTTP over your tailnet.

## Why the default is plain HTTP

Research Assistant ships with `Secure=false` on the session cookie and
serves the API on `http://<tailnet-ip>:<port>`. This is intentional:

* Tailscale already encrypts every packet on the wire with WireGuard.
  Adding TLS on top is belt-and-braces, not load-bearing security.
* It avoids the operational headache of provisioning, rotating, and
  trusting a self-signed certificate on every device.
* Browsers don't downgrade-block HTTP traffic to `100.64.0.0/10`
  addresses — it just works.

If your threat model includes a compromised tailnet relay, or you want
to share the install with someone outside your tailnet, you should
turn on HTTPS via Tailscale Serve. Steps below.

## Upgrading to HTTPS via Tailscale Serve

Tailscale Serve provisions a publicly-trusted Let's Encrypt certificate
for your tailnet domain (`<hostname>.<tailnet>.ts.net`) and proxies it
to a local port — no port forwarding, no DNS setup.

### 1. Enable MagicDNS + HTTPS in your tailnet admin

In the Tailscale admin console:

* **DNS → MagicDNS** — enable.
* **DNS → HTTPS Certificates** — enable.

### 2. Start the backend as usual

```bash
# Production-like (frozen Electron build):
open "Research Assistant.app"

# Or for development:
cd apps/desktop && RMA_DEV=1 npx electron .
```

Note the port that the Electron app picks (visible in
`File → Show tailnet URL…`). Call it `${PORT}`.

### 3. Proxy port 443 to the backend

```bash
tailscale serve --bg --https=443 http://localhost:${PORT}
```

That command:

* Provisions a Let's Encrypt certificate for
  `<hostname>.<tailnet>.ts.net` (cached at
  `/var/lib/tailscale/certs/` on Linux,
  `~/Library/Containers/io.tailscale.ipn.macos/Data/Library/...` on
  macOS).
* Listens on `:443` and forwards plaintext to `localhost:${PORT}`.
* Survives reboots because of `--bg`. Run `tailscale serve status` to
  inspect, `tailscale serve --https=443 off` to remove.

### 4. Flip the cookie to `Secure=true; SameSite=None`

Once the front door is HTTPS-only, the session cookie needs to opt in to
the secure attribute. Edit `apps/api/src/research_api/routes/auth.py`:

```python
COOKIE_SAMESITE = "none"   # was "lax"

def _set_session_cookie(response: Response, cookie_value: str) -> None:
    response.set_cookie(
        key=COOKIE_NAME,
        value=cookie_value,
        max_age=COOKIE_MAX_AGE,
        httponly=True,
        secure=True,       # was False
        samesite=COOKIE_SAMESITE,
        path=COOKIE_PATH,
    )
```

Rebuild the frozen backend (`cd apps/desktop && python
scripts/build_backend.py`) and re-package the Electron installer
(`npm run dist:mac` / `dist:win` / `dist:linux`).

> Why both? `SameSite=None` requires `Secure=true` per the modern
> browser spec — without it, Chromium silently drops the cookie. The
> reason to switch from `Lax` is so a browser tab opened against the
> tailnet HTTPS URL can still send the cookie when the renderer process
> is on a different origin (Electron `file://` → tailnet `https://`).

### 5. Tell the renderer to use the HTTPS URL

The Electron main process detects a tailnet IP via the `tailscale` CLI
and exposes it as `window.electron.tailnetUrl`. The renderer's
`apps/web/src/lib/api.ts` prefers the API URL in this order:

1. `window.electron.apiUrl` (the local backend)
2. `import.meta.env.VITE_API_URL`
3. The window's `location.origin` (PWA fallback)

For your other devices to talk to the HTTPS endpoint, just open
`https://<hostname>.<tailnet>.ts.net/` in a browser — the bundled
service worker + the PWA fallback will take over from there.

## Rolling back

```bash
tailscale serve --https=443 off
```

Revert the auth.py cookie config to `secure=False; samesite="lax"` and
re-build the backend. Plain HTTP resumes immediately.

## Caveats

* Tailscale Serve only works if you're on Tailscale's free or
  paid plan with MagicDNS — it doesn't work on a self-hosted
  Headscale install unless Headscale has cert provisioning enabled
  (it doesn't, as of writing).
* The certificate is for the tailnet hostname only — you can't use
  it to expose the app to the public internet. For that, use
  `tailscale funnel` (different command, different
  considerations — out of scope for this guide).
* `Secure=true` cookies in development mode (`http://localhost:5173`)
  will not work. Keep two builds: one with `secure=False` for dev,
  one with `secure=True` for tailnet deployment.
