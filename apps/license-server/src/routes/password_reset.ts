// Phase L1a — POST /api/forgot-password, POST /api/reset-password

import { Hono } from "hono";
import type { AppEnv } from "../lib/env";
import { getDb, getEmailSender } from "../lib/env";
import { isEmail, normaliseEmail, isStrongPassword } from "../lib/validation";
import {
  generateToken,
  sha256Hex,
  hashPassword,
  uuidv4,
} from "../lib/crypto";
import { passwordResetEmail } from "../lib/email";
import { RESET_TOKEN_TTL_MS } from "../lib/auth";

export const forgotPasswordRoute = new Hono<AppEnv>().post("/", async (c) => {
  const body = await c.req.json().catch(() => ({}));
  const b = (body && typeof body === "object" ? body : {}) as Record<string, unknown>;
  if (!isEmail(b.email)) return c.json({ ok: true }); // don't leak
  const email = normaliseEmail(b.email as string);
  const db = getDb(c.env);
  const account = await db.getAccountByEmail(email);
  if (account && account.type !== "revoked") {
    // Fix-13/4: nuke any previously-issued, unused reset tokens for
    // this account so only the freshest one is valid. Without this,
    // a user who clicks "Forgot password" twice would leave two live
    // tokens; an attacker who only intercepts the first email could
    // still use it for 15 minutes.
    await db.invalidateUnusedPasswordResets(account.id);
    const token = generateToken(32);
    const token_hash = await sha256Hex(token);
    const now = Date.now();
    await db.insertPasswordReset({
      id: uuidv4(),
      account_id: account.id,
      token_hash,
      expires_at: now + RESET_TOKEN_TTL_MS,
      used_at: null,
      created_at: now,
    });
    const baseUrl = c.env.APP_BASE_URL ?? "https://research-assistant.dev";
    const tpl = passwordResetEmail({
      display_name: account.display_name,
      reset_url: `${baseUrl}/reset?token=${encodeURIComponent(token)}`,
      ttl_minutes: Math.round(RESET_TOKEN_TTL_MS / 60_000),
    });
    const sender = getEmailSender(c.env);
    const r = await sender.send({ to: account.email, ...tpl });
    await db.insertEmailEvent({
      id: uuidv4(),
      account_id: account.id,
      email: account.email,
      kind: "password_reset",
      sent_at: now,
      resend_id: r.id ?? null,
    });
  }
  return c.json({ ok: true });
});

export const resetPasswordRoute = new Hono<AppEnv>().post("/", async (c) => {
  const body = await c.req.json().catch(() => ({}));
  const b = (body && typeof body === "object" ? body : {}) as Record<string, unknown>;
  const token = typeof b.token === "string" ? b.token : "";
  const new_password = b.new_password;
  if (!token) return c.json({ error: "invalid_token" }, 400);
  if (!isStrongPassword(new_password))
    return c.json({ error: "weak_password" }, 400);

  const db = getDb(c.env);
  const token_hash = await sha256Hex(token);
  const reset = await db.getPasswordResetByTokenHash(token_hash);
  if (!reset) return c.json({ error: "invalid_token" }, 400);
  if (reset.used_at) return c.json({ error: "token_used" }, 400);
  if (reset.expires_at < Date.now()) return c.json({ error: "token_expired" }, 400);

  const hash = await hashPassword(new_password as string);
  await db.updateAccountPasswordHash(reset.account_id, hash);
  await db.markPasswordResetUsed(reset.id);
  // Invalidate existing sessions so attackers with stolen tokens are kicked.
  await db.deleteSessionsForAccount(reset.account_id);
  return c.json({ ok: true });
});
