# Research Assistant — Desktop (Phase E1 + D1)

Electron shell that bundles the FastAPI backend + the React frontend into a
single installable app. Targets all three desktop platforms:

* macOS — `.dmg` (unsigned; see *Code signing* below)
* Windows — NSIS `.exe` (unsigned)
* Linux — `.AppImage`

Builds run per-platform — cross-compiling Linux/Windows binaries from macOS
is fiddly enough that we run each target on its native runner via the
`release.yml` GitHub Actions workflow (see `RELEASE.md`).

## Layout

```
apps/desktop/
  package.json              # Electron + electron-builder config
  tsconfig.json             # Main-process TypeScript
  research_api.spec         # PyInstaller spec (freezes the backend)
  src/
    main.ts                 # Electron main process
    preload.ts              # Renderer bridge (window.electron.*)
    tailscale.ts            # Best-effort tailnet URL detection
  scripts/
    build_backend.py        # Wrapper around PyInstaller
    make_placeholder_icons.py
  tests/
    test_frozen_smoke.py    # Manual smoke for the frozen backend
  build/                    # Compiled main + preload land here
  build/icons/              # Placeholder "RA" icons (PNG/ICO/ICNS)
  dist/backend/             # PyInstaller output (`research_api/...`)
  release/                  # electron-builder output (`*.dmg`, `*.exe`)
```

## Build pipeline (Mac, end-to-end)

```bash
# from repo root
cd apps/desktop

# 1. Freeze the FastAPI backend (~600 MB onedir bundle, takes ~3 minutes
#    on a cold cache).
python scripts/build_backend.py

# 2. Generate placeholder icons (PNG/ICO/ICNS — uses iconutil on macOS).
python scripts/make_placeholder_icons.py

# 3. Build the prebuilt React frontend so electron-builder can pick it up
#    from extraResources.
npm --prefix ../web run build

# 4. Compile the Electron main + preload TS.
npm install     # first time only
npm run build

# 5. Produce the installable. Outputs land in apps/desktop/release/.
npm run dist:mac     # macOS    → release/*.dmg
# or, on the matching native runner:
npm run dist:win     # Windows  → release/*.exe (NSIS installer)
npm run dist:linux   # Linux    → release/*.AppImage
```

All three `dist:*` scripts pass `--publish never` so a local build never
attempts to upload to GitHub. The CI release workflow (`release.yml`) is
the only place that publishes — it sets `GH_TOKEN` and invokes
electron-builder with the GitHub provider implicitly.

For day-to-day dev with the frozen backend (no need to rebuild the installer):

```bash
npm install
npm run build
npx electron .
```

## What ships inside the bundle

`extraResources` (from `package.json`) copies these into the packaged app:

| Source                        | Target inside the app | Why                                                |
| ----------------------------- | --------------------- | -------------------------------------------------- |
| `dist/backend/research_api/`  | `Resources/backend/`  | Frozen FastAPI executable + libs + alembic + learn |
| `../web/dist/`                | `Resources/web/`      | Prebuilt React bundle (loaded via `file://`)       |

The Electron main process spawns `Resources/backend/research_api` on a free
port in the `18000–18999` range, waits for `/health`, then opens a window
pointed at `Resources/web/index.html`.

## Manual verification

After running the build pipeline, you can sanity-check the frozen backend
without launching Electron:

```bash
# Spawn directly
./dist/backend/research_api/research_api --port 18787 &
PID=$!
sleep 15           # matplotlib font cache on first boot
curl http://127.0.0.1:18787/health   # → {"status":"degraded", ...}
curl -X POST http://127.0.0.1:18787/api/projects \
  -H 'Content-Type: application/json' \
  -d '{"title":"smoke","study_type":"observational"}'
kill -TERM $PID
```

The included smoke script wraps this in `tests/test_frozen_smoke.py`. It is
intentionally **not** run in CI — booting the bundle once costs ~30 seconds
and a few hundred MB of disk activity.

## Code signing

Skipped on purpose — the user opted not to pay $99/year for Apple Developer
or ~$300/year for an OV cert. To open the unsigned `.dmg` / `.exe`:

* **macOS Gatekeeper:** right-click the app → *Open* → *Open anyway* in
  System Settings → Privacy & Security.
* **Windows SmartScreen:** click *More info* → *Run anyway*.

`electron-builder` will print warnings about the missing identity. Those
are expected.

## What's wired up in E1

* PyInstaller freezes the FastAPI backend in one-folder mode with all
  scientific deps (scipy / statsmodels / pingouin / lifelines /
  matplotlib backend_agg / reportlab / python-docx / openpyxl).
* Electron spawns the binary on a dynamic port and waits for `/health`.
* `window.electron.apiUrl` is bridged into the renderer; the frontend's
  `lib/api.ts` already honours that source first.
* `window.electron.tailnetUrl` is populated when the `tailscale` CLI is
  installed and reports a 100.x.x.x address — otherwise it's `null`.
* `File → Show tailnet URL…` opens a dialog with copy-to-clipboard
  buttons.
* `/welcome` route in the React app explains the local-storage model +
  Tailscale setup.

## What's NOT in E1 (intentional)

* DMG custom background, branded icon, signed installer.
* HTTPS over tailnet by default — HTTP only for v1. The optional
  upgrade path via `tailscale serve --https=443` is documented at
  [`docs/setup/https-over-tailnet.md`](../../docs/setup/https-over-tailnet.md).

## Auto-update (Phase D1.4)

Auto-update is wired through `electron-updater` and reads release metadata
from the public GitHub repo identified in `package.json` →
`build.publish`. **You must fill in `owner` and `repo`** in that block
(both are placeholder `"TBD"` strings right now) before the first
release goes out, otherwise the updater will silently no-op and log a
warning at startup.

The CI workflow in `.github/workflows/release.yml` builds + publishes
artifacts to GitHub Releases when you push a `vX.Y.Z` tag. See
[`RELEASE.md`](../../RELEASE.md) for the full release procedure.

## Auth model (Phase S1)

The packaged Electron app boots the FastAPI backend with
`RMA_DISABLE_AUTH=0` — real argon2id auth + per-project membership /
RBAC. On first launch the renderer's `<RequireAuth>` wrapper redirects
to `/signup`; subsequent launches land on `/login`.

For local development (running `npx electron .` against the source tree)
set `RMA_DEV=1` to revive the static-`local-user` flow. CI / `pytest`
also rely on this escape hatch via `RMA_DISABLE_AUTH=1` in
`tests/conftest.py`.

```bash
# production-like launch (real auth)
npx electron .

# legacy single-user mode for fast iteration
RMA_DEV=1 npx electron .
```

Existing data from pre-S1 installations: the migration 0028 step seeds
an owner row for the legacy `local-user` so projects keep working.
After the first signup, the renderer's `/welcome` route can offer to
"Adopt local data" — the backend exposes `GET /api/auth/legacy-data-
status` and `POST /api/auth/claim-legacy-data` for this.

## Common pitfalls

* **`/api/health` returns 404**: the route is mounted at `/health`, not
  `/api/health`. The Electron polling code uses `/health`.
* **Backend takes ~20 s on first boot**: matplotlib has to build its font
  cache the first time it runs in the unpacked bundle. Subsequent boots
  are ~3 s.
* **`python` shadowed**: scripts always invoke
  `apps/api/.venv/bin/python` so PyInstaller sees the project deps.
* **Untracked `dist/backend/` / `release/`**: large outputs, leave them
  out of git (add to `.gitignore` if needed).
* **`dmgbuild` fails with `libintl.8.dylib` missing**: electron-builder's
  bundled dmgbuild needs Homebrew's gettext on macOS. Install with
  `brew install gettext` then re-run `npm run dist:mac`. The `.app`
  itself still builds correctly into `release/mac/` even when the DMG
  step fails — you can zip and ship it manually as a fallback.
