// Phase L1a — Worker entry. Mounts Hono routers under /api/* and applies
// permissive CORS for the desktop / web / mobile clients.

import { Hono } from "hono";
import { cors } from "hono/cors";
import type { AppEnv } from "./lib/env";

import { signupRoute } from "./routes/signup";
import { loginRoute } from "./routes/login";
import { verifyRoute, accountRoute } from "./routes/verify";
import { logoutRoute, logoutAllRoute, devicesRoute } from "./routes/logout";
import { adminMintRoute, adminRevokeRoute } from "./routes/admin";
import { webhookRoute } from "./routes/webhook";
import { forgotPasswordRoute, resetPasswordRoute } from "./routes/password_reset";

const ALLOWED_ORIGIN_PATTERNS: RegExp[] = [
  // Local dev (Vite, Electron renderer, etc.)
  /^http:\/\/localhost(:\d+)?$/,
  /^http:\/\/127\.0\.0\.1(:\d+)?$/,
  // Cloudflare *.workers.dev
  /^https:\/\/[a-z0-9-]+\.workers\.dev$/,
  // Electron renderer
  /^app:\/\//,
  // Landing site placeholder; replace once the production domain is set up.
  // TODO(L1c): swap this for the user's chosen landing domain.
  /^https:\/\/research-assistant\.dev$/,
  /^https:\/\/.+\.research-assistant\.dev$/,
];

function isAllowedOrigin(origin: string): boolean {
  if (!origin) return false;
  return ALLOWED_ORIGIN_PATTERNS.some((re) => re.test(origin));
}

const app = new Hono<AppEnv>();

app.use("*", async (c, next) => {
  const origin = c.req.header("Origin") ?? "";
  const allowed = isAllowedOrigin(origin) ? origin : "";
  return cors({
    origin: allowed,
    allowMethods: ["GET", "POST", "DELETE", "OPTIONS"],
    allowHeaders: ["Content-Type", "Authorization", "X-Admin-Token", "X-Signature"],
    maxAge: 600,
    credentials: false,
  })(c, next);
});

app.get("/", (c) =>
  c.json({
    name: "research-assistant-license",
    version: "0.0.1",
    env: c.env.ENV ?? "production",
  }),
);

app.get("/api/health", (c) =>
  c.json({ ok: true, ts: Date.now() }),
);

app.route("/api/signup", signupRoute);
app.route("/api/login", loginRoute);
app.route("/api/verify", verifyRoute);
app.route("/api/account", accountRoute);
app.route("/api/logout", logoutRoute);
app.route("/api/logout-all", logoutAllRoute);
app.route("/api/devices", devicesRoute);
app.route("/api/admin/mint", adminMintRoute);
app.route("/api/admin/revoke", adminRevokeRoute);
app.route("/api/webhook/lemonsqueezy", webhookRoute);
app.route("/api/forgot-password", forgotPasswordRoute);
app.route("/api/reset-password", resetPasswordRoute);

app.notFound((c) => c.json({ error: "not_found" }, 404));
app.onError((err, c) => {
  console.error("[license-server]", err);
  return c.json({ error: "internal_error", message: err.message }, 500);
});

export default app;
