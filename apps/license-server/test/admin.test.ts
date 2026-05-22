// Phase L1a — admin mint / revoke tests.

import { describe, it, expect } from "vitest";
import { makeHarness } from "./helpers/setup";

describe("admin endpoints", () => {
  it("/api/admin/mint creates a trial account and returns temp password", async () => {
    const h = makeHarness();
    const resp = await h.fetch("/api/admin/mint", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Admin-Token": "test-admin-token",
      },
      body: JSON.stringify({
        email: "trial@example.com",
        display_name: "Trial",
        type: "trial",
      }),
    });
    expect(resp.status).toBe(200);
    const body = (await resp.json()) as any;
    expect(body.account.type).toBe("trial");
    expect(typeof body.account.trial_expires_at).toBe("number");
    expect(typeof body.temp_password).toBe("string");
    expect(body.temp_password.length).toBeGreaterThanOrEqual(10);
  });

  it("/api/admin/mint can create a lifetime account directly", async () => {
    const h = makeHarness();
    const resp = await h.fetch("/api/admin/mint", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Admin-Token": "test-admin-token",
      },
      body: JSON.stringify({
        email: "life@example.com",
        display_name: "Lifer",
        type: "lifetime",
      }),
    });
    expect(resp.status).toBe(200);
    const body = (await resp.json()) as any;
    expect(body.account.type).toBe("lifetime");
    expect(body.account.lifetime_purchased_at).toBeTypeOf("number");
    expect(body.account.trial_expires_at).toBeNull();
  });

  it("/api/admin/mint rejects calls without the admin token", async () => {
    const h = makeHarness();
    const resp = await h.fetch("/api/admin/mint", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        email: "x@example.com",
        display_name: "X",
        type: "trial",
      }),
    });
    expect(resp.status).toBe(403);
  });

  it("/api/admin/revoke sets type=revoked and clears sessions", async () => {
    const h = makeHarness();
    // Create + login an account first.
    const sup = await h.fetch("/api/signup", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        email: "bad@example.com",
        password: "correct-horse-7",
        display_name: "Bad",
      }),
    });
    const supBody = (await sup.json()) as any;
    expect(h.db.rows("sessions")).toHaveLength(1);

    const resp = await h.fetch("/api/admin/revoke", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Admin-Token": "test-admin-token",
      },
      body: JSON.stringify({ email: "bad@example.com" }),
    });
    expect(resp.status).toBe(200);
    expect(h.db.rows("accounts")[0].type).toBe("revoked");
    expect(h.db.rows("sessions")).toHaveLength(0);

    // The old token is now invalid.
    const v = await h.fetch("/api/verify", {
      headers: { Authorization: `Bearer ${supBody.token}` },
    });
    expect(v.status).toBe(401);
  });
});
