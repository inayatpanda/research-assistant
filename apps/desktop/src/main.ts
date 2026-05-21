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
  shell,
} from "electron";
import getPort, { portNumbers } from "get-port";

import { detectTailnetUrl } from "./tailscale";

type BackendState = {
  port: number;
  process: ChildProcess;
  baseUrl: string;
};

let backend: BackendState | null = null;
let mainWindow: BrowserWindow | null = null;
let tailnetUrl: string | null = null;

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
      ],
    },
  ];
  Menu.setApplicationMenu(Menu.buildFromTemplate(template));
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
