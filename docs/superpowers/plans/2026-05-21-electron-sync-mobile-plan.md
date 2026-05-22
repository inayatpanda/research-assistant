# Electron + Sync + Mobile Implementation Plan

**Status:** draft — for iterative review.
**Author/date:** 2026-05-21.
**Supersedes:** `2026-05-21-mobile-pwa-plan.md` (the mobile bit re-slots into Phase M, after E and S).

---

## Locked decisions

| Decision | Value |
|---|---|
| Sync architecture | **A: Laptop is server + Tailscale.** Single canonical SQLite on the user's primary machine. Other devices reach it over a Tailscale tailnet. No cloud sync server, no recurring cost. |
| Build order | **E1 (Electron) → S1 (multi-user auth + sharing) → M0–M5 (mobile PWA as thin client over tailnet).** Mobile depends on a stable backend URL + real auth, so it comes last. |
| Multi-user | Real auth (email + password), per-project sharing with role (owner/editor/viewer), invitation flow. The schema is already user_id-aware — this phase swaps the static `local_user_id` for a real session-derived ID and adds a `project_members` join table. |
| Desktop installer | **Mac `.dmg` + Windows `.exe` (NSIS) in E1. Linux AppImage deferred.** **No Apple Developer code signing** (user constraint: do not pay). Gatekeeper / SmartScreen warning documented in onboarding. |
| App icon | **Placeholder "RA" tile in E1**, refresh with a designed icon later. |
| Tailnet transport | **HTTP over tailnet for v1.** Cookies use `SameSite=Lax` (works with HTTP). HTTPS upgrade via Tailscale Serve is a later polish. |
| Auto-update | Deferred to a later phase. Upgrade path = reinstall. |
| PWA backend URL | Configurable. Desktop app shows a QR code + URL the user scans/types into the PWA on first launch. |
| Mobile breakpoint | `<900px` (unchanged from prior plan). |
| Bottom tabs | 5 fixed: Library, Manuscripts, Stats, Learn, More (unchanged). |
| PWA offline | Full offline reading via IndexedDB cache. Writes require connectivity to the laptop (which means tailnet up + laptop awake). |

---

## Architecture overview

```
       ┌─────────────────────────────────────────────┐
       │  TAILSCALE TAILNET (your private VPN)       │
       │                                             │
       │  Your laptop (the "home server"):           │
       │    Electron app                             │
       │    ├── packaged FastAPI backend (port N)    │
       │    └── packaged React frontend (served      │
       │        from same backend or file://)        │
       │      ▲                                      │
       │      │ HTTPS over tailnet                   │
       │      │                                      │
       │  iPad / iPhone / second laptop:             │
       │    Mobile PWA (or desktop UI in browser)    │
       │    pointed at https://your-mac.tail-xxx.ts.net:N │
       │    Reads cached in IndexedDB for offline    │
       │                                             │
       │  Invited collaborator's laptop:             │
       │    Their browser hits your tailnet URL      │
       │    Logs in with their own credentials       │
       │    Sees only projects you've shared with them │
       └─────────────────────────────────────────────┘
```

**Key idea:** There is exactly **one database**, on the home laptop. There is no sync engine, no CRDT, no replication. "Cross-device" means other devices remote-access the laptop's backend. Tailscale handles the networking + identity; we handle auth + RBAC inside the backend.

Trade-off: when the laptop is closed/asleep/away from internet, remote devices lose connectivity. The PWA's IndexedDB cache keeps the most recent read snapshot available offline. Writes from remote devices fail until the laptop is reachable again.

**Why this works for medical research:**
- Data never leaves your hardware → privacy + compliance easy
- No subscription cost
- Tailscale is free for personal/small-team use (≤100 devices, ≤3 users)
- Upgrade path to a cloud sync server later (Phase S2) without changing the data model
- Collaborators join your tailnet via Tailscale's invitation flow (free tier covers small co-author teams)

---

## Phase E1 — Electron desktop packaging (~3 days)

Goal: produce installable `.dmg` / `.exe` / `.AppImage` of the current app, with the FastAPI backend frozen via PyInstaller and shipped alongside.

### E1.1 — Backend freezing (~1 day)

- Add a `apps/desktop/` directory for the Electron shell.
- Use **PyInstaller** to freeze the FastAPI app:
  - Entry point: `apps/api/src/research_api/main.py`
  - Hidden imports: aiosqlite, alembic, scipy, pingouin, lifelines, statsmodels, matplotlib backends, etc. (build out incrementally — PyInstaller will whine until it's right)
  - One-folder mode (faster startup than `--onefile`)
  - Produces `dist/research_api/research_api` (executable) + library files
- Bundle the alembic migrations directory next to the executable so the frozen backend can still run them.
- Bundle the Learn hub markdown content (`apps/api/src/research_api/learn/`) — it's loaded from disk at runtime.
- Test: run the frozen binary directly, confirm `/api/health` responds, confirm a project can be created and an article uploaded.

### E1.2 — Electron shell (~1 day)

- Stack: `electron-builder` for packaging, no Electron Forge.
- Files:
  - `apps/desktop/package.json` — Electron entry + electron-builder config
  - `apps/desktop/src/main.ts` — main process: launch backend subprocess on free port, then create BrowserWindow pointing to it
  - `apps/desktop/src/preload.ts` — preload script (minimal, just exposes app version + tailnet URL helper to the renderer)
- Main-process behaviour:
  - On launch: spawn the bundled `research_api` binary on `0.0.0.0:<random-free-port>`, wait for `/api/health` to return 200.
  - Configure CORS env vars on the spawned process to allow `app://research-assistant` (electron's local origin) + tailnet hosts.
  - Pass the port to the renderer via preload.
  - On quit: SIGTERM the backend subprocess, wait up to 5s, SIGKILL.
  - Menu bar: native menu with File / Edit / View / Window / Help. Add a "Show tailnet URL" item that opens a dialog with the user's `your-mac.tail-xxx.ts.net:<port>` URL + a copy-to-clipboard button.
- Renderer: loads the pre-built React frontend from disk (no dev server). The React app's API base URL is `http://127.0.0.1:<port>` (resolved at load time via preload).

### E1.3 — Installer + branding (~half day)

- electron-builder config:
  - Mac: `target: ["dmg"]`, custom DMG background image, app icon `.icns`
  - Windows: `target: ["nsis"]`, NSIS installer wizard, app icon `.ico`
  - Linux AppImage: **deferred** (add later if needed)
- App icon: **placeholder "RA" tile** generated programmatically (solid `#0F1117` background + white "RA" text, multiple sizes: 16/32/64/128/256/512). One Python script in `apps/desktop/scripts/make_placeholder_icons.py` produces all sizes + `.icns` + `.ico`. Design refresh later.
- DMG background: simple "drag-to-Applications" template.
- **No code signing.** Add a doc page explaining:
  - Mac: right-click → Open → "Open anyway" on first launch
  - Win: SmartScreen "More info → Run anyway"
- `npm run dist` produces installers in `apps/desktop/release/`.

### E1.4 — First-run experience (~half day)

- On first launch, show a welcome screen explaining:
  - The app stores all data locally (path shown).
  - To access from other devices, install Tailscale + show the tailnet URL.
  - Migration: import an existing browser-session's bundle export.
- Detect Tailscale presence (check for `tailscale` CLI binary or `100.x.x.x` IP on a network interface). If present, derive the tailnet URL automatically and display it.

### E1.5 — Tests + verification (~half day)

- Backend tests: unchanged, run via `pytest` against the source (not the frozen binary).
- New: `apps/desktop/tests/test_electron_smoke.spec.ts` (Playwright Electron) — launches the packaged app, waits for the splash, hits a basic API endpoint, confirms a project can be created. One end-to-end smoke test, kept minimal.
- Manual QA on Mac (your primary): full install/uninstall cycle, verify backend subprocess cleanup on quit.

### E1 deliverable
- A clickable `.dmg` for Mac. You drag it to Applications, double-click, get the existing app running locally with the SQLite DB at `~/Library/Application Support/Research Assistant/`. The "Show tailnet URL" menu item gives you the URL to put on your phone. Existing data migrates via Settings → Import.

---

## Phase S1 — Multi-user auth + sharing (~4 days)

Goal: replace the static `local_user_id` with real authentication, add user accounts, and enable per-project sharing with collaborators across the tailnet.

### S1.1 — Auth backend (~1 day)

- New tables (migration 0027_users_auth.py):
  - `users` — id, email (unique), password_hash, display_name, created_at, updated_at, is_admin
  - `sessions` — id, user_id, token_hash, created_at, expires_at, last_seen_at
  - `invitations` — id, email, project_id, role, token, created_at, expires_at, accepted_at
- Password hashing: **argon2id** via `argon2-cffi` (add to backend deps). Strong default params.
- Session model: server-side sessions, not JWT. Token is a random 32-byte URL-safe string stored httpOnly + Secure cookie. Sessions table tracks last_seen_at for "active devices" UI.
- New auth routes in `routes/auth.py`:
  - `POST /api/auth/signup` — email + password + display_name → creates user + session cookie
  - `POST /api/auth/login` — email + password → session cookie
  - `POST /api/auth/logout` — invalidates current session
  - `GET /api/auth/me` — returns current user (or 401)
  - `POST /api/auth/change-password` — old + new password
- Replace `_user_id()` dependency in **every route** with `get_current_user()` that reads the session cookie. Static `local_user_id` becomes a fallback for non-auth mode (controlled by `RMA_DISABLE_AUTH=1` env var for local dev).

### S1.2 — Project sharing + RBAC (~1.5 days)

- New table (migration 0028_project_members.py):
  - `project_members` — id, project_id, user_id, role (`owner` | `editor` | `viewer`), invited_by, created_at
  - Index on (project_id, user_id) unique.
  - Owner role inserted automatically on project creation (the creator).
- New routes in `routes/project_members.py`:
  - `GET /api/projects/{pid}/members` — list members + roles
  - `POST /api/projects/{pid}/invitations` — body `{email, role}` → creates pending invitation, returns invitation URL (`<base>/invite/<token>`)
  - `POST /api/auth/accept-invitation/{token}` — accepts invitation, adds project_member row
  - `PATCH /api/projects/{pid}/members/{uid}` — change role
  - `DELETE /api/projects/{pid}/members/{uid}` — remove
- Repository refactor: every `*_for_project()` / `*_for_user()` method now checks via `project_members` instead of strict user_id ownership. Owner has full rights, editor can edit, viewer is read-only.
- 403 vs 404: viewers see editor/owner-only routes as 403. Non-members see the project as 404 (don't leak existence).
- Migration: existing projects get a `project_members` row for the legacy `local_user_id` user as owner.

### S1.3 — Frontend auth UI (~1 day)

- New pages:
  - `/login` — email + password + "create account" link
  - `/signup` — email + password + display name
  - `/invite/:token` — accept invitation, sign in or sign up
  - `/account` — show profile, change password, list active sessions, log out everywhere
- Wrap existing routes in `<RequireAuth>` — redirects to /login if not authenticated.
- Settings: new "Account" card showing user email + logout button.
- Project settings: new "Members" tab in project Settings showing collaborators + invite UI (owner/editor only).

### S1.4 — Tests (~half day)

- Backend: ~30 new tests covering signup/login/logout, password rules, session expiry, project membership grants, role-based 403s, invitation flow end-to-end, RBAC cross-user isolation across **every** route.
- Frontend: ~8 vitest covering login form, signup form, invite-accept flow, members panel.

### S1 deliverable
- You log into your Mac's Electron app with your email + password. You invite a collaborator by email; they get an invitation URL, accept it, and now they can join your tailnet, hit your tailnet URL in their browser, log in, and see the project you shared with them. Their role determines what they can do.

---

## Phase M0 — Mobile foundations (~half day)

Same as prior plan, with one addition: the mobile PWA's backend URL is configurable (set on first launch by scanning/typing the tailnet URL shown in the desktop app).

- `vite-plugin-pwa` + `idb` (new npm deps)
- Manifest, service worker, placeholder icons
- DeviceRouter, useViewport, useForceDesktop store
- MobileShell with 5 bottom tabs + placeholder pages
- ForceDesktopCard in Settings
- **New for this revision**: `apps/web/src/mobile/lib/backendUrl.ts` — a zustand store + localStorage persistence for the tailnet API URL. First-launch screen prompts the user to enter or scan the URL.

## Phase M1–M5 — Mobile pages (~5 days)

Unchanged from the prior plan. Each phase ships independently. See the previous plan doc for detail.

---

## Cross-cutting concerns

### Migration of existing data
- Existing single-user DB has rows with `user_id = "local"` (or whatever the static value is). The auth migration creates one default user with email `local@research-assistant.local` and re-points all those rows to it.
- Document a "first-run claim" flow: on the first signup after auth is enabled, prompt the user "Do you want to claim the existing local data?" — yes → re-assign all `user_id="local"` rows to the new user.

### CORS + cookies over tailnet
- Backend CORS allow-list configurable via env. For Tailscale: allow `*.tail-xxx.ts.net` plus `app://` (Electron origin) plus `localhost`.
- **v1 transport is HTTP** (decision locked). Cookies use `SameSite=Lax` + `HttpOnly` (no `Secure` flag since HTTP). Works for same-tailnet origins which the browser treats as same-site under Lax.
- HTTPS upgrade path (later polish): turn on Tailscale Serve, get free certs via MagicDNS, switch cookies to `SameSite=None; Secure`.

### Security
- argon2id password hashing
- Session tokens stored hashed in DB
- Rate-limit login/signup (slowapi or simple in-memory)
- HTTPS-only cookies once HTTPS is set up (Tailscale provides certs via MagicDNS)
- Audit log table (`audit_log`): record auth events + project sharing changes
- Threat model documented in `docs/security.md` (deferred polish)

### Backwards compatibility
- The `RMA_DISABLE_AUTH=1` env var keeps the legacy single-user mode for dev/test runs. CI uses it. Production (Electron) does not.

### Updating the app
- v1: reinstall the `.dmg` to update.
- v2: investigate `electron-updater` with a GitHub Releases feed (free).

### Telemetry / crash reporting
- None in v1. You explicitly value privacy + zero recurring cost.

---

## Estimates

| Phase | Effort | Cumulative |
|---|---|---|
| E1 Electron packaging | 3 days | 3 |
| S1 Multi-user auth + sharing | 4 days | 7 |
| M0 Mobile foundations | 0.5 day | 7.5 |
| M1 Read-only mobile | 1 day | 8.5 |
| M2 Library + Reader | 1.5 days | 10 |
| M3 Manuscript reader | 1 day | 11 |
| M4 Stats wizard | 1 day | 12 |
| M5 Mini-apps | 0.5 day | 12.5 |

**~12.5 days total.** Each phase ships independently; you can stop after any phase.

---

## Open items

- **App icon design** — placeholder "RA" tile in E1 (LOCKED). Refresh once you have brand direction.
- **Code signing for Mac + Windows** — costs $99/yr Apple, ~$300/yr OV cert for Windows. Skipped. Document Gatekeeper + SmartScreen workarounds in onboarding.
- **Linux AppImage** — deferred from E1 (LOCKED). Add later if needed.
- **HTTPS over tailnet** — HTTP for v1 (LOCKED). Upgrade via Tailscale Serve as later polish.
- **Tailscale setup docs** — write a short markdown guide for the user explaining how to install Tailscale on Mac + Windows + iPhone + how the tailnet URL works.
- **Migration of legacy `local_user_id` data** — needs a one-time prompt UI when auth is enabled for the first time.
- **Cloud sync upgrade path (S2)** — deferred. If laptop-as-server becomes too limiting, add an optional cloud Postgres + sync layer. Architecture A → B/C is a future migration.

---

## Approval gate

Before any code lands, you sign off on:

- [ ] This plan, or with edits.
- [ ] Two new backend deps: `argon2-cffi` (for password hashing) and `pyinstaller` (build-time only, not a runtime dep).
- [ ] Two new frontend deps: `vite-plugin-pwa`, `idb` (M0).
- [ ] Skipping Mac code signing (Gatekeeper warning documented).
- [ ] Starting with **E1 first**, S1 next, then M phases.

---

## What changes about the M0–M5 prior plan

- **Mobile PWA backend URL** is now configurable (was implicitly localhost). Adds ~30 LOC + a first-launch onboarding screen.
- **Auth flow** is required before any mobile page works. Mobile gets the same login screen as desktop, adapted to small-screen layout.
- **Force-desktop toggle** still works — it just toggles which UI shell the user sees; auth and backend URL are shell-independent.

---

*Edits welcome — strike through what you don't like, comment in the margin, replace whole sections. Iterate freely on this doc before we open any new files.*
