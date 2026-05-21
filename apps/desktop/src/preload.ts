/**
 * Phase E1 — Electron preload script.
 *
 * The renderer is sandboxed (contextIsolation: true, nodeIntegration: false),
 * so the only path the React app has to the host is `window.electron`. We
 * keep that surface intentionally tiny:
 *
 * * `apiUrl`     — the local FastAPI URL the renderer should hit.
 * * `tailnetUrl` — the tailnet URL other devices can use (or null when
 *                  Tailscale isn't installed).
 * * `platform`   — process platform string, handy for OS-specific copy.
 *
 * S1 will add session helpers (login / logout / share invitation URL) and
 * M0 will add the cross-device URL configuration helpers for the PWA.
 */
import { contextBridge } from "electron";

const apiUrl = process.env.RMA_API_URL ?? "";
const tailnetUrl = process.env.RMA_TAILNET_URL ?? "";

contextBridge.exposeInMainWorld("electron", {
  apiUrl,
  tailnetUrl: tailnetUrl.length > 0 ? tailnetUrl : null,
  platform: process.platform,
});
