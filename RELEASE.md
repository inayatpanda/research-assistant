# Release procedure

Research Assistant ships unsigned `.dmg` (macOS), NSIS `.exe` (Windows),
and `.AppImage` (Linux) installers via GitHub Releases. Auto-update is
handled by `electron-updater` against the same release feed.

## One-time setup

Before publishing the first release you need:

1. **A public GitHub repo** with this code pushed to it.
   `electron-updater` reads `releases/latest` over plain HTTPS, no
   token — that only works on a public repo.
2. **Fill in `apps/desktop/package.json` → `build.publish`:**
   ```json
   "publish": {
     "provider": "github",
     "owner": "<your-github-username>",
     "repo":  "<your-repo-name>",
     "releaseType": "release"
   }
   ```
   The placeholder is `"TBD"`/`"TBD"` — auto-update is silently
   disabled until you replace both. The change goes into a commit; the
   installer baked into each release reads its own copy of
   `package.json`, so rolling out a new value requires shipping a
   release.
3. **GitHub Actions → Settings → Workflow permissions:**
   *Read and write permissions* — the workflow needs to attach
   artifacts to the release it creates. The workflow asks for
   `contents: write` via its `permissions:` block, but the repo-level
   toggle must allow it.
4. *(Optional)* Document the Gatekeeper / SmartScreen workaround on
   your landing page since the binaries are unsigned. The text is
   already in [`apps/desktop/README.md`](apps/desktop/README.md) →
   "Code signing".

## Cutting a release

```bash
# 1. Bump the version. electron-builder uses this for the dmg/exe filename,
#    and electron-updater compares against it on next launch.
$EDITOR apps/desktop/package.json   # bump "version"

# 2. Commit the bump.
git add apps/desktop/package.json
git commit -m "chore: release v0.1.0"

# 3. Tag and push. Pushing the tag triggers .github/workflows/release.yml.
git tag v0.1.0
git push                # commits
git push --tags         # the tag (this is what triggers CI)
```

## What the workflow does

`.github/workflows/release.yml` runs three parallel jobs (`mac`, `win`,
`linux`) on their native runners. Each job:

1. Checks out the code at the tagged commit.
2. Installs Python 3.12 + Node 20.
3. `pip install -e .` in `apps/api/` + `pip install pyinstaller`.
4. Freezes the FastAPI backend via
   `apps/desktop/scripts/build_backend.py`.
5. `npm ci && npm run build` in `apps/web/` — produces the static
   React bundle electron-builder picks up via `extraResources`.
6. `npm ci` in `apps/desktop/`, generates placeholder icons, runs
   `npm run dist:<platform>` — produces the installer.
7. Uploads the installer to the GitHub Release via
   `softprops/action-gh-release@v2`. The first job creates the
   release; the rest just append.

Build time is roughly:
* macOS — ~12 minutes (PyInstaller + matplotlib font cache + dmg).
* Windows — ~10 minutes.
* Linux — ~9 minutes.

## Verifying the release

Once the workflow finishes:

1. Go to `https://github.com/<owner>/<repo>/releases/tag/v0.1.0`.
2. Confirm three assets are present: `.dmg`, `.exe`, `.AppImage` plus
   the auto-generated `latest-mac.yml`, `latest.yml`, `latest-linux.yml`
   (electron-builder publishes these as part of the dist step — they're
   what electron-updater reads to decide whether a newer version is
   available).
3. Download the binary on each platform and confirm the app boots.

## Post-release: existing installs auto-upgrade

The next time a previously-installed app starts, `electron-updater`:

1. Fetches `latest-<platform>.yml` from your release tag.
2. Compares the version against the installed version.
3. If newer, downloads the binary in the background and shows a toast.
4. On window close (or "Restart now" from the Help menu), applies the
   update and restarts.

If the user is offline, the check silently fails and the app continues
to run with the installed version. There's no retry loop — the next
launch will try again.

## Yanking a bad release

```bash
gh release delete v0.1.0 --yes
git push --delete origin v0.1.0
```

Cut a new patch release with the fix.
