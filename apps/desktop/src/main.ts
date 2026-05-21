/**
 * Phase E1 — Electron main process.
 *
 * Boot sequence:
 *   1. Pick a free TCP port for the backend.
 *   2. Spawn the frozen `research_api` executable, passing the port via env.
 *   3. Poll `/health` until 200 or a 30-second timeout.
 *   4. Detect Tailscale (best-effort) and stash the tailnet URL.
 *   5. Open a single BrowserWindow loading the bundled React frontend
 *      (file:// URL into apps/web/dist or, in packaged builds, the
 *      extraResources `web/` folder).
 *   6. Bridge `apiUrl` + `tailnetUrl` to the renderer via the preload.
 *
 * Shutdown: SIGTERM the backend, wait 5 s, SIGKILL on timeout.
 *
 * Code signing is intentionally skipped (free-tier constraint). The README
 * documents how users open the unsigned `.dmg` and `.exe`.
 */
import { spawn, ChildProcess } from "node:child_process";
import { existsSync } from "node:fs";
import * as path from "node:path";
import { setTimeout as wait } from "node:timers/promises";

import {
  app,
  BrowserWindow,
  clipboard,
  dialog,
  Menu,
  Notification,
  shell,
} from "electron";
import getPort, { portNumbers } from "get-port";
// Lazy require — electron-updater pulls in some Node-only deps that
// don't tree-shake well, and we want a hard error on import to be
// caught (we log + continue rather than crashing the app).
// eslint-disable-next-line @typescript-eslint/no-require-imports
import { autoUpdater } from "electron-updater";

import { detectTailnetUrl } from "./tailscale";

type BackendState = {
  port: number;
  process: ChildProcess;
  baseUrl: string;
};

let backend: BackendState | null = null;
let mainWindow: BrowserWindow | null = null;
let tailnetUrl: string | null = null;
// D1.4 — flipped to true on ``update-available``; surfaces in the Help menu
// as a hint that something to download is sitting on GitHub.
let updateAvailable = false;
let updateDownloaded = false;
let pendingUpdateVersion: string | null = null;

const isPackaged = app.isPackaged;

/**
 * Resolve a path inside the packaged extraResources folder (`backend/`,
 * `web/`) or fall back to the dev-time location in the source tree.
 */
function resolveResource(...segments: string[]): string {
  if (isPackaged) {
    return path.join(process.resourcesPath, ...segments);
  }
  // Dev mode — read from the on-disk dist paths.
  const desktopDir = path.resolve(__dirname, "..");
  if (segments[0] === "backend") {
    return path.join(desktopDir, "dist", "backend", "research_api", ...segments.slice(1));
  }
  if (segments[0] === "web") {
    return path.join(desktopDir, "..", "web", "dist", ...segments.slice(1));
  }
  return path.join(desktopDir, ...segments);
}

function backendExecutable(): string {
  const exeName = process.platform === "win32" ? "research_api.exe" : "research_api";
  return resolveResource("backend", exeName);
}

function frontendIndex(): string {
  return resolveResource("web", "index.html");
}

async function startBackend(): Promise<BackendState> {
  const exe = backendExecutable();
  if (!existsSync(exe)) {
    throw new Error(
      `backend executable not found at ${exe} — did you run ` +
        `"python scripts/build_backend.py" first?`,
    );
  }
  const port = await getPort({ port: portNumbers(18000, 18999) });
  const baseUrl = `http://127.0.0.1:${port}`;

  // Phase S1 — production-mode Electron runs against the real multi-user
  // auth subsystem. Set RMA_DEV=1 (e.g. ``RMA_DEV=1 npx electron .``)
  // to revive the legacy static-user-id mode for local development.
  const devMode = process.env.RMA_DEV === "1";
  const child = spawn(exe, ["--host", "127.0.0.1", "--port", String(port)], {
    env: {
      ...process.env,
      RMA_HOST: "127.0.0.1",
      RMA_PORT: String(port),
      // Real auth in prod; static-user-id mode only when RMA_DEV=1.
      ...(devMode ? { RMA_DISABLE_AUTH: "1" } : { RMA_DISABLE_AUTH: "0" }),
    },
    stdio: ["ignore", "pipe", "pipe"],
  });

  child.stdout?.on("data", (b) =>
    process.stdout.write(`[backend] ${b.toString()}`),
  );
  child.stderr?.on("data", (b) =>
    process.stderr.write(`[backend] ${b.toString()}`),
  );
  child.on("exit", (code, signal) => {
    console.log(`[backend] exited code=${code} signal=${signal}`);
    if (backend && backend.process === child) {
      backend = null;
    }
  });

  // Poll /health with a 30s budget.
  const deadline = Date.now() + 30_000;
  while (Date.now() < deadline) {
    try {
      const resp = await fetch(`${baseUrl}/health`);
      if (resp.ok) {
        console.log(`[main] backend healthy at ${baseUrl}`);
        return { port, process: child, baseUrl };
      }
    } catch {
      // not yet listening
    }
    await wait(500);
  }
  child.kill("SIGTERM");
  throw new Error(`backend failed to respond on ${baseUrl}/health within 30 s`);
}

async function stopBackend(): Promise<void> {
  if (!backend) return;
  const child = backend.process;
  backend = null;
  try {
    child.kill("SIGTERM");
  } catch {
    /* already dead */
  }
  const stopped = await Promise.race([
    new Promise<boolean>((resolve) => child.once("exit", () => resolve(true))),
    wait(5_000).then(() => false),
  ]);
  if (!stopped) {
    try {
      child.kill("SIGKILL");
    } catch {
      /* */
    }
  }
}

function showTailnetDialog() {
  const localUrl = backend?.baseUrl ?? "(backend not running)";
  if (tailnetUrl) {
    const choice = dialog.showMessageBoxSync({
      type: "info",
      title: "Tailnet URL",
      message: "Cross-device access",
      detail:
        `Other devices on your tailnet can reach this app at:\n\n` +
        `  ${tailnetUrl}\n\n` +
        `Local URL (this machine only): ${localUrl}`,
      buttons: ["Copy tailnet URL", "Copy local URL", "Close"],
      defaultId: 0,
      cancelId: 2,
    });
    if (choice === 0) clipboard.writeText(tailnetUrl);
    if (choice === 1) clipboard.writeText(localUrl);
  } else {
    const choice = dialog.showMessageBoxSync({
      type: "info",
      title: "Tailnet URL",
      message: "Tailscale not detected",
      detail:
        "Install Tailscale from tailscale.com to enable cross-device access " +
        "from your phone or other laptops.\n\n" +
        `Local URL (this machine only): ${localUrl}`,
      buttons: ["Open tailscale.com", "Copy local URL", "Close"],
      defaultId: 0,
      cancelId: 2,
    });
    if (choice === 0) shell.openExternal("https://tailscale.com/download");
    if (choice === 1) clipboard.writeText(localUrl);
  }
}

function buildMenu() {
  const isMac = process.platform === "darwin";
  const template: Electron.MenuItemConstructorOptions[] = [
    ...(isMac
      ? [
          {
            label: app.name,
            submenu: [
              { role: "about" as const },
              { type: "separator" as const },
              { role: "services" as const },
              { type: "separator" as const },
              { role: "hide" as const },
              { role: "hideOthers" as const },
              { role: "unhide" as const },
              { type: "separator" as const },
              { role: "quit" as const },
            ],
          },
        ]
      : []),
    {
      label: "File",
      submenu: [
        {
          label: "Show tailnet URL…",
          accelerator: "CmdOrCtrl+Shift+T",
          click: showTailnetDialog,
        },
        { type: "separator" },
        isMac ? { role: "close" } : { role: "quit" },
      ],
    },
    {
      label: "Edit",
      submenu: [
        { role: "undo" },
        { role: "redo" },
        { type: "separator" },
        { role: "cut" },
        { role: "copy" },
        { role: "paste" },
        { role: "selectAll" },
      ],
    },
    {
      label: "View",
      submenu: [
        { role: "reload" },
        { role: "forceReload" },
        { role: "toggleDevTools" },
        { type: "separator" },
        { role: "resetZoom" },
        { role: "zoomIn" },
        { role: "zoomOut" },
        { type: "separator" },
        { role: "togglefullscreen" },
      ],
    },
    {
      label: "Window",
      submenu: [{ role: "minimize" }, { role: "zoom" }, { role: "close" }],
    },
    {
      role: "help",
      submenu: [
        {
          label: "Documentation",
          click: () =>
            shell.openExternal(
              "https://github.com/anthropic-claude/research-assistant",
            ),
        },
        {
          label: "Tailscale setup",
          click: () => shell.openExternal("https://tailscale.com/download"),
        },
        // D1.4 — update-status badge. When an update is sitting on
        // GitHub, the user sees a one-click way to either restart now
        // (if it's already downloaded) or be reminded what version is
        // coming. We rebuild the menu on each state transition.
        ...(updateDownloaded
          ? [
              { type: "separator" as const },
              {
                label: `Restart to install v${pendingUpdateVersion ?? "?"}`,
                click: () => {
                  try {
                    autoUpdater.quitAndInstall();
                  } catch (err) {
                    console.warn("[updater] quitAndInstall failed:", err);
                  }
                },
              },
            ]
          : updateAvailable
            ? [
                { type: "separator" as const },
                {
                  label: `Downloading update v${pendingUpdateVersion ?? "?"}…`,
                  enabled: false,
                },
              ]
            : []),
      ],
    },
  ];
  Menu.setApplicationMenu(Menu.buildFromTemplate(template));
}

/**
 * D1.4 — wire ``electron-updater`` against the public GitHub repo
 * declared in ``package.json``→``build.publish``.
 *
 * Update lifecycle:
 *   1. After the window is shown, call ``checkForUpdatesAndNotify()``.
 *   2. ``update-available`` → set the menu badge + fire an OS toast.
 *   3. ``update-downloaded`` → ask the user whether to relaunch now.
 *   4. ``error`` → log + carry on (the most common cause is the user
 *      still having the placeholder ``owner: 'TBD'`` in package.json
 *      because they haven't published a release yet).
 *
 * Disabled when:
 *   * The app isn't packaged (running ``npx electron .`` from source).
 *     The dev backend doesn't have a version to compare against.
 *   * The GitHub owner/repo are still the placeholder ``TBD``. We log a
 *     one-time warning so the user knows to fill them in.
 */
function setupAutoUpdater() {
  if (!isPackaged) {
    console.log("[updater] skipped — running from source");
    return;
  }
  // Read the publish block — electron-builder injects it into the
  // bundled ``app-update.yml``. ``autoUpdater.getFeedURL()`` doesn't
  // help before we call check, so we crack open package.json directly.
  type PkgPublish = { owner?: string; repo?: string };
  let publish: PkgPublish = {};
  try {
    // eslint-disable-next-line @typescript-eslint/no-require-imports, @typescript-eslint/no-var-requires
    const pkg = require(path.join(app.getAppPath(), "package.json"));
    publish = (pkg?.build?.publish ?? {}) as PkgPublish;
  } catch {
    /* fall through — guarded below */
  }
  if (publish.owner === "TBD" || publish.repo === "TBD") {
    console.warn(
      "[updater] disabled — package.json build.publish.{owner,repo} " +
        "are still the placeholder 'TBD'. Fill them in once your GitHub " +
        "repo is public, then rebuild. See apps/desktop/README.md.",
    );
    return;
  }

  autoUpdater.logger = {
    info: (m: unknown) => console.log("[updater]", m),
    warn: (m: unknown) => console.warn("[updater]", m),
    error: (m: unknown) => console.error("[updater]", m),
    // electron-log expects a debug method too; no-op here is fine.
    debug: () => {},
  } as unknown as typeof autoUpdater.logger;

  autoUpdater.autoDownload = true;
  autoUpdater.autoInstallOnAppQuit = true;

  autoUpdater.on("update-available", (info) => {
    updateAvailable = true;
    pendingUpdateVersion = info?.version ?? null;
    rebuildMenuWithUpdateBadge();
    try {
      new Notification({
        title: "Research Assistant",
        body: `Update available — v${pendingUpdateVersion ?? "?"} is downloading…`,
      }).show();
    } catch {
      /* notifications may be disabled by user — ignore */
    }
  });

  autoUpdater.on("update-not-available", () => {
    console.log("[updater] up to date");
  });

  autoUpdater.on("update-downloaded", (info) => {
    updateDownloaded = true;
    pendingUpdateVersion = info?.version ?? pendingUpdateVersion;
    rebuildMenuWithUpdateBadge();
    const choice = dialog.showMessageBoxSync({
      type: "info",
      title: "Update ready to install",
      message: `Research Assistant v${pendingUpdateVersion ?? "?"} is ready.`,
      detail:
        "Click Restart to relaunch the app and finish installing. " +
        "Otherwise the update will be applied next time you quit.",
      buttons: ["Restart now", "Later"],
      defaultId: 0,
      cancelId: 1,
    });
    if (choice === 0) {
      autoUpdater.quitAndInstall();
    }
  });

  autoUpdater.on("error", (err) => {
    // The most common error is a 404 on the GitHub Releases API while
    // no release has been published yet. We don't want this to surface
    // to the user as a dialog — log and move on.
    console.warn("[updater] error:", err?.message ?? err);
  });

  // Fire and forget. Returning the promise would block bootstrap.
  void autoUpdater.checkForUpdatesAndNotify().catch((err) => {
    console.warn("[updater] check failed:", err?.message ?? err);
  });
}

/**
 * Rebuild the application menu so the Help submenu picks up the
 * "Update available" / "Update downloaded — restart" badge. Cheap
 * enough to rebuild on every state change.
 */
function rebuildMenuWithUpdateBadge() {
  buildMenu();
}

async function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    backgroundColor: "#0F1117",
    title: "Research Assistant",
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      nodeIntegration: false,
      contextIsolation: true,
      webSecurity: true,
      sandbox: false, // preload uses ipcRenderer
    },
  });
  mainWindow.on("closed", () => {
    mainWindow = null;
  });
  const indexPath = frontendIndex();
  if (!existsSync(indexPath)) {
    await mainWindow.loadURL(
      "data:text/html;charset=utf-8," +
        encodeURIComponent(
          `<h1>Frontend missing</h1>` +
            `<p>Expected <code>${indexPath}</code>. Run ` +
            `<code>npm run build:frontend</code> in <code>apps/web</code>.</p>`,
        ),
    );
    return;
  }
  await mainWindow.loadFile(indexPath);
}

async function bootstrap() {
  buildMenu();
  try {
    backend = await startBackend();
  } catch (err) {
    dialog.showErrorBox(
      "Research Assistant — backend failed to start",
      (err as Error).message,
    );
    app.quit();
    return;
  }
  tailnetUrl = await detectTailnetUrl(backend.port).catch(() => null);
  // Expose to renderer via a process-level env var that the preload reads.
  process.env.RMA_API_URL = backend.baseUrl;
  process.env.RMA_TAILNET_URL = tailnetUrl ?? "";
  await createWindow();
  // D1.4 — check for updates *after* the main window is up so the
  // user sees the app first; a 1.5 s nudge lets initial frame paint
  // settle before we fire the network request.
  setTimeout(() => {
    try {
      setupAutoUpdater();
    } catch (err) {
      console.warn("[updater] setup failed:", err);
    }
  }, 1500);
}

app.whenReady().then(bootstrap);

app.on("window-all-closed", async () => {
  await stopBackend();
  if (process.platform !== "darwin") {
    app.quit();
  }
});

app.on("activate", () => {
  if (BrowserWindow.getAllWindows().length === 0) {
    void createWindow();
  }
});

app.on("before-quit", async (event) => {
  if (backend) {
    event.preventDefault();
    await stopBackend();
    app.exit(0);
  }
});
