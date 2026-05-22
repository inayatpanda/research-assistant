// Phase L1a — POST /api/login
//
// Verifies the password, enforces the 5-device cap, opens a session.

import { Hono } from "hono";
import type { AppEnv } from "../lib/env";
import { getDb } from "../lib/env";
import { validateLogin } from "../lib/validation";
import { verifyPassword } from "../lib/crypto";
import {
  createSessionForAccount,
  publicAccount,
  publicSession,
  clientIp,
  DEVICE_LIMIT,
} from "../lib/auth";

export const LOGIN_RATE_LIMIT = 10;
export const LOGIN_WINDOW_MS = 60 * 60 * 1000;

export const loginRoute = new Hono<AppEnv>().post("/", async (c) => {
  const db = getDb(c.env);
  const ip = clientIp(c);
  const hits = await db.hitRateLimit(`login:${ip}`, LOGIN_WINDOW_MS);
  if (hits > LOGIN_RATE_LIMIT) {
    return c.json({ error: "rate_limited" }, 429);
  }

  const body = await c.req.json().catch(() => ({}));
  const v = validateLogin(body);
  if (!v.ok) return c.json({ error: "validation_failed", details: v.errors }, 400);

  const account = await db.getAccountByEmail(v.value.email);
  if (!account) return c.json({ error: "invalid_credentials" }, 401);
  if (account.type === "revoked") return c.json({ error: "account_revoked" }, 403);
  const ok = await verifyPassword(v.value.password, account.password_hash);
  if (!ok) return c.json({ error: "invalid_credentials" }, 401);

  const active = await db.listActiveSessions(account.id);
  if (active.length >= DEVICE_LIMIT) {
    return c.json(
      {
        error: "device_limit_exceeded",
        devices: active.map(publicSession),
      },
      409,
    );
  }

  const { token, session } = await createSessionForAccount(db, account, {
    device_id: v.value.device_id,
    device_label: v.value.device_label,
    user_agent: c.req.header("user-agent"),
    ip,
  });

  // Return existing devices alongside the new one so clients can show the
  // device-manager UI immediately.
  const devices = [...active, session].map(publicSession);
  return c.json({
    token,
    account: publicAccount(account),
    session: publicSession(session),
    devices,
  });
});
