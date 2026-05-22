// Phase L1a — POST /api/login
//
// Verifies the password, enforces the 5-device cap, opens a session.

import { Hono } from "hono";
import type { AppEnv } from "../lib/env";
import { getDb } from "../lib/env";
import { validateLogin } from "../lib/validation";
import { verifyPassword } from "../lib/crypto";
import {
  createSessionUnderLimit,
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

  // Atomic insert: the SQL itself checks the device-count, so two
  // concurrent /login calls can't both observe < limit and slip past.
  // On failure we re-read the list and return 409 with the devices.
  const created = await createSessionUnderLimit(db, account, DEVICE_LIMIT, {
    device_id: v.value.device_id,
    device_label: v.value.device_label,
    user_agent: c.req.header("user-agent"),
    ip,
  });
  if (!created) {
    const active = await db.listActiveSessions(account.id);
    return c.json(
      {
        error: "device_limit_exceeded",
        devices: active.map(publicSession),
      },
      409,
    );
  }

  // Return existing devices alongside the new one so clients can show the
  // device-manager UI immediately.
  const after = await db.listActiveSessions(account.id);
  return c.json({
    token: created.token,
    account: publicAccount(account),
    session: publicSession(created.session),
    devices: after.map(publicSession),
  });
});
