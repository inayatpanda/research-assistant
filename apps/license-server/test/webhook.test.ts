// Phase L1a — Lemon Squeezy webhook tests.

import { describe, it, expect } from "vitest";
import { makeHarness } from "./helpers/setup";

async function hmacHex(secret: string, body: string): Promise<string> {
  const enc = new TextEncoder();
  const key = await crypto.subtle.importKey(
    "raw",
    enc.encode(secret),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"],
  );
  const mac = await crypto.subtle.sign("HMAC", key, enc.encode(body));
  return [...new Uint8Array(mac)]
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
}

function lsOrderPayload(overrides: Partial<{ id: string; email: string; name: string }> = {}) {
  return {
    meta: { event_name: "order_created" },
    data: {
      id: overrides.id ?? "order-123",
      attributes: {
        status: "paid",
        user_email: overrides.email ?? "buyer@example.com",
        user_name: overrides.name ?? "Bought Person",
        total: 2900,
        currency: "USD",
      },
    },
  };
}

describe("POST /api/webhook/lemonsqueezy", () => {
  it("upgrades an existing trial account to lifetime", async () => {
    const h = makeHarness({ webhookSecret: "hook-secret" });
    // Signup a trial account first.
    await h.fetch("/api/signup", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        email: "buyer@example.com",
        password: "correct-horse-7",
        display_name: "Buyer",
      }),
    });
    expect(h.db.rows("accounts")[0].type).toBe("trial");

    const payload = lsOrderPayload();
    const body = JSON.stringify(payload);
    const sig = await hmacHex("hook-secret", body);
    const resp = await h.fetch("/api/webhook/lemonsqueezy", {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-Signature": sig },
      body,
    });
    expect(resp.status).toBe(200);
    const account = h.db.rows("accounts")[0];
    expect(account.type).toBe("lifetime");
    expect(typeof account.lifetime_purchased_at).toBe("number");
    expect(h.db.rows("purchase_events")).toHaveLength(1);
    // Confirmation email sent.
    expect(h.mailer.sent.some((m) => m.subject.toLowerCase().includes("purchas"))).toBe(true);
  });

  it("rejects requests with an invalid signature", async () => {
    const h = makeHarness({ webhookSecret: "hook-secret" });
    const payload = lsOrderPayload();
    const body = JSON.stringify(payload);
    const resp = await h.fetch("/api/webhook/lemonsqueezy", {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-Signature": "0".repeat(64) },
      body,
    });
    expect(resp.status).toBe(401);
    expect(h.db.rows("accounts")).toHaveLength(0);
  });

  it("Fix-13/5: concurrent deliveries of the same order produce at most one purchase + one lifetime conversion", async () => {
    // Two simultaneous webhook calls for the same order can race past
    // the dup-check. The UNIQUE(ls_order_id) constraint + catch in the
    // route mean we still end up with exactly one purchase_event row
    // and exactly one lifetime upgrade.
    const h = makeHarness({ webhookSecret: "hook-secret" });
    const payload = lsOrderPayload({ id: "order-race" });
    const body = JSON.stringify(payload);
    const sig = await hmacHex("hook-secret", body);
    const [r1, r2] = await Promise.all([
      h.fetch("/api/webhook/lemonsqueezy", {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-Signature": sig },
        body,
      }),
      h.fetch("/api/webhook/lemonsqueezy", {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-Signature": sig },
        body,
      }),
    ]);
    expect(r1.status).toBe(200);
    expect(r2.status).toBe(200);
    expect(h.db.rows("purchase_events")).toHaveLength(1);
    expect(h.db.rows("accounts")).toHaveLength(1);
    expect(h.db.rows("accounts")[0].type).toBe("lifetime");
  });

  it("is idempotent on repeated deliveries of the same order id", async () => {
    const h = makeHarness({ webhookSecret: "hook-secret" });
    const payload = lsOrderPayload({ id: "order-dup" });
    const body = JSON.stringify(payload);
    const sig = await hmacHex("hook-secret", body);

    const r1 = await h.fetch("/api/webhook/lemonsqueezy", {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-Signature": sig },
      body,
    });
    expect(r1.status).toBe(200);
    const r2 = await h.fetch("/api/webhook/lemonsqueezy", {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-Signature": sig },
      body,
    });
    expect(r2.status).toBe(200);
    const b2 = (await r2.json()) as any;
    expect(b2.idempotent).toBe(true);
    // Only one purchase event recorded.
    expect(h.db.rows("purchase_events")).toHaveLength(1);
    // And we created exactly one account.
    expect(h.db.rows("accounts")).toHaveLength(1);
  });
});
