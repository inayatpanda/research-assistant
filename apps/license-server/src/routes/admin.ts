// Phase L1a — admin endpoints (mint / revoke).
//
// Gated by `X-Admin-Token` (Wrangler secret ADMIN_TOKEN). Used by the CLI
// in scripts/mint_license.py for granting comp licences and demo access.

import { Hono } from "hono";
import type { AppEnv } from "../lib/env";
import { getDb } from "../lib/env";
import {
  hashPassword,
  uuidv4,
  generateRandomPassword,
  timingSafeEqualString,
} from "../lib/crypto";
import { publicAccount } from "../lib/auth";
import { isDisplayName, isEmail, normaliseEmail } from "../lib/validation";

function adminAuth(token: string | undefined, env: AppEnv["Bindings"]): boolean {
  if (!env.ADMIN_TOKEN || !token) return false;
  // Constant-time compare to avoid leaking the secret's prefix length
  // via response timing (Fix-13/2).
  return timingSafeEqualString(token, env.ADMIN_TOKEN);
}

export const adminMintRoute = new Hono<AppEnv>().post("/", async (c) => {
  if (!adminAuth(c.req.header("x-admin-token"), c.env)) {
    return c.json({ error: "forbidden" }, 403);
  }
  const body = await c.req.json().catch(() => ({}));
  const b = (body && typeof body === "object" ? body : {}) as Record<string, unknown>;
  if (!isEmail(b.email)) return c.json({ error: "invalid_email" }, 400);
  if (!isDisplayName(b.display_name))
    return c.json({ error: "invalid_display_name" }, 400);
  const type = b.type;
  if (type !== "trial" && type !== "lifetime") {
    return c.json({ error: "invalid_type" }, 400);
  }
  const email = normaliseEmail(b.email as string);
  const db = getDb(c.env);
  const existing = await db.getAccountByEmail(email);
  if (existing) return c.json({ error: "email_in_use" }, 409);

  let tempPassword: string | null = null;
  let pw: string;
  if (typeof b.password === "string" && b.password.length >= 10) {
    pw = b.password as string;
  } else {
    pw = generateRandomPassword(12);
    tempPassword = pw;
  }
  const now = Date.now();
  const account = {
    id: uuidv4(),
    email,
    password_hash: await hashPassword(pw),
    display_name: (b.display_name as string).trim(),
    type: type as "trial" | "lifetime",
    trial_expires_at: type === "trial" ? now + 30 * 24 * 60 * 60 * 1000 : null,
    lifetime_purchased_at: type === "lifetime" ? now : null,
    email_verified_at: null,
    created_at: now,
    updated_at: now,
  };
  await db.insertAccount(account);
  return c.json({ account: publicAccount(account), temp_password: tempPassword });
});

export const adminRevokeRoute = new Hono<AppEnv>().post("/", async (c) => {
  if (!adminAuth(c.req.header("x-admin-token"), c.env)) {
    return c.json({ error: "forbidden" }, 403);
  }
  const body = await c.req.json().catch(() => ({}));
  const b = (body && typeof body === "object" ? body : {}) as Record<string, unknown>;
  if (!isEmail(b.email)) return c.json({ error: "invalid_email" }, 400);
  const db = getDb(c.env);
  const email = normaliseEmail(b.email as string);
  const account = await db.getAccountByEmail(email);
  if (!account) return c.json({ error: "not_found" }, 404);
  await db.updateAccountType(account.id, "revoked", { trial_expires_at: null });
  await db.deleteSessionsForAccount(account.id);
  return c.json({ ok: true });
});
