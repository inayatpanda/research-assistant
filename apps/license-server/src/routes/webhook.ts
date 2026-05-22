// Phase L1a — POST /api/webhook/lemonsqueezy
//
// Verifies the HMAC-SHA256 signature, idempotently records the order, and
// upgrades / creates the buyer's account to a lifetime licence.

import { Hono } from "hono";
import type { AppEnv } from "../lib/env";
import { getDb, getEmailSender } from "../lib/env";
import { verifyHmacSha256, hashPassword, generateRandomPassword, uuidv4 } from "../lib/crypto";
import { purchaseConfirmationEmail, welcomeLifetimeEmail } from "../lib/email";

interface LsAttributes {
  status?: string;
  user_email?: string;
  user_name?: string;
  total?: number;
  currency?: string;
  identifier?: string;
}
interface LsData {
  id?: string;
  attributes?: LsAttributes;
}
interface LsPayload {
  meta?: { event_name?: string };
  data?: LsData;
}

export const webhookRoute = new Hono<AppEnv>().post("/", async (c) => {
  const secret = c.env.LEMONSQUEEZY_WEBHOOK_SECRET;
  if (!secret) return c.json({ error: "webhook_not_configured" }, 500);

  const raw = await c.req.text();
  const sig = c.req.header("x-signature") ?? "";
  if (!(await verifyHmacSha256(secret, raw, sig))) {
    return c.json({ error: "invalid_signature" }, 401);
  }

  let payload: LsPayload;
  try {
    payload = JSON.parse(raw) as LsPayload;
  } catch {
    return c.json({ error: "invalid_json" }, 400);
  }

  const event = payload.meta?.event_name ?? "";
  if (event !== "order_created") {
    // Acknowledge other events but do nothing.
    return c.json({ ok: true, ignored: event || "unknown" });
  }
  const attrs = payload.data?.attributes ?? {};
  if (attrs.status && attrs.status !== "paid") {
    return c.json({ ok: true, skipped: "not_paid" });
  }
  const email = (attrs.user_email ?? "").trim().toLowerCase();
  const name = (attrs.user_name ?? "").trim() || "there";
  const orderId = payload.data?.id ?? attrs.identifier ?? null;
  if (!email) return c.json({ error: "no_email" }, 400);

  const db = getDb(c.env);

  if (orderId) {
    const dup = await db.getPurchaseByOrderId(orderId);
    if (dup) return c.json({ ok: true, idempotent: true });
  }

  let account = await db.getAccountByEmail(email);
  const sender = getEmailSender(c.env);
  let tempPassword: string | null = null;
  const now = Date.now();
  if (!account) {
    tempPassword = generateRandomPassword(12);
    account = {
      id: uuidv4(),
      email,
      password_hash: await hashPassword(tempPassword),
      display_name: name,
      type: "lifetime",
      trial_expires_at: null,
      lifetime_purchased_at: now,
      email_verified_at: null,
      created_at: now,
      updated_at: now,
    };
    try {
      await db.insertAccount(account);
    } catch (err) {
      // Fix-13/5: race-safe path. A concurrent webhook delivery for
      // the same buyer may have just inserted the row; re-fetch and
      // continue with the existing account.
      const msg = err instanceof Error ? err.message : String(err);
      if (/UNIQUE/i.test(msg) && /email/i.test(msg)) {
        const refreshed = await db.getAccountByEmail(email);
        if (refreshed) {
          account = refreshed;
          tempPassword = null;
        } else {
          throw err;
        }
      } else {
        throw err;
      }
    }
  } else {
    await db.updateAccountType(account.id, "lifetime", {
      lifetime_purchased_at: now,
      trial_expires_at: null,
    });
  }

  // Fix-13/5: the schema declares ls_order_id UNIQUE, but two
  // concurrent retries of the same webhook can still race past the
  // earlier dup-check. Catch the UNIQUE-constraint failure here and
  // treat it as idempotent success — by the time the constraint
  // fires, the first call has already upgraded the account.
  try {
    await db.insertPurchase({
      id: uuidv4(),
      account_id: account.id,
      ls_order_id: orderId,
      amount_cents: typeof attrs.total === "number" ? attrs.total : null,
      currency: attrs.currency ?? null,
      raw_payload: raw,
      created_at: now,
    });
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err);
    if (orderId && /UNIQUE/i.test(msg) && /ls_order_id/i.test(msg)) {
      return c.json({ ok: true, idempotent: true });
    }
    throw err;
  }

  const baseUrl = c.env.APP_BASE_URL ?? "https://research-assistant.dev";
  if (tempPassword) {
    const tpl = welcomeLifetimeEmail({
      display_name: account.display_name,
      temp_password: tempPassword,
      login_url: `${baseUrl}/account`,
    });
    const r = await sender.send({ to: account.email, ...tpl });
    await db.insertEmailEvent({
      id: uuidv4(),
      account_id: account.id,
      email: account.email,
      kind: "welcome_lifetime",
      sent_at: Date.now(),
      resend_id: r.id ?? null,
    });
  } else {
    const tpl = purchaseConfirmationEmail({
      display_name: account.display_name,
      login_url: `${baseUrl}/account`,
    });
    const r = await sender.send({ to: account.email, ...tpl });
    await db.insertEmailEvent({
      id: uuidv4(),
      account_id: account.id,
      email: account.email,
      kind: "purchase_confirmation",
      sent_at: Date.now(),
      resend_id: r.id ?? null,
    });
  }

  return c.json({ ok: true, account_id: account.id });
});
