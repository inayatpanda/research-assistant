// Phase L1a — POST /api/signup
//
// Creates a trial account, opens a session, sends a welcome email.

import { Hono } from "hono";
import type { AppEnv } from "../lib/env";
import { getDb, getEmailSender } from "../lib/env";
import { validateSignup } from "../lib/validation";
import { hashPassword, uuidv4 } from "../lib/crypto";
import { createSessionForAccount, publicAccount, clientIp } from "../lib/auth";
import { welcomeTrialEmail } from "../lib/email";

export const TRIAL_DAYS = 30;
export const SIGNUP_RATE_LIMIT = 5;
export const SIGNUP_WINDOW_MS = 60 * 60 * 1000; // 1 hour

export const signupRoute = new Hono<AppEnv>().post("/", async (c) => {
  const db = getDb(c.env);
  const ip = clientIp(c);
  const hits = await db.hitRateLimit(`signup:${ip}`, SIGNUP_WINDOW_MS);
  if (hits > SIGNUP_RATE_LIMIT) {
    return c.json({ error: "rate_limited" }, 429);
  }

  const body = await c.req.json().catch(() => ({}));
  const v = validateSignup(body);
  if (!v.ok) return c.json({ error: "validation_failed", details: v.errors }, 400);

  const existing = await db.getAccountByEmail(v.value.email);
  if (existing) return c.json({ error: "email_in_use" }, 409);

  const now = Date.now();
  const id = uuidv4();
  const password_hash = await hashPassword(v.value.password);
  const account = {
    id,
    email: v.value.email,
    password_hash,
    display_name: v.value.display_name,
    type: "trial" as const,
    trial_expires_at: now + TRIAL_DAYS * 24 * 60 * 60 * 1000,
    lifetime_purchased_at: null,
    email_verified_at: null,
    created_at: now,
    updated_at: now,
  };
  await db.insertAccount(account);

  const { token, session } = await createSessionForAccount(db, account, {
    device_id: v.value.device_id,
    device_label: v.value.device_label,
    user_agent: c.req.header("user-agent"),
    ip,
  });

  // Fire-and-forget email.
  const sender = getEmailSender(c.env);
  const tpl = welcomeTrialEmail({
    display_name: account.display_name,
    trial_days: TRIAL_DAYS,
    download_url: c.env.APP_DOWNLOAD_URL ?? "https://research-assistant.dev/install",
  });
  const result = await sender.send({ to: account.email, ...tpl });
  await db.insertEmailEvent({
    id: uuidv4(),
    account_id: account.id,
    email: account.email,
    kind: "welcome_trial",
    sent_at: Date.now(),
    resend_id: result.id ?? null,
  });

  return c.json({
    token,
    account: publicAccount(account),
    session: { id: session.id, device_id: session.device_id, expires_at: session.expires_at },
  });
});
