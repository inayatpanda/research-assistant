// Phase L1a — verify endpoint tests.

import { describe, it, expect } from "vitest";
import { makeHarness } from "./helpers/setup";

async function signupAndToken(h: ReturnType<typeof makeHarness>, email: string) {
  const r = await h.fetch("/api/signup", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      email,
      password: "correct-horse-7",
      display_name: "Test User",
    }),
  });
  if (r.status !== 200) throw new Error(`signup failed ${r.status}`);
  const body = (await r.json()) as any;
  return body.token as string;
}

describe("GET /api/verify", () => {
  it("returns valid:true for a fresh token", async () => {
    const h = makeHarness();
    const token = await signupAndToken(h, "alice@example.com");
    const resp = await h.fetch("/api/verify", {
      headers: { Authorization: `Bearer ${token}` },
    });
    expect(resp.status).toBe(200);
    const body = (await resp.json()) as any;
    expect(body.valid).toBe(true);
    expect(body.account.email).toBe("alice@example.com");
  });

  it("returns 401 for a missing bearer token", async () => {
    const h = makeHarness();
    const resp = await h.fetch("/api/verify");
    expect(resp.status).toBe(401);
    const body = (await resp.json()) as any;
    expect(body.error).toBe("missing_bearer_token");
    expect(body.valid).toBe(false);
  });

  it("returns 401 for an expired token", async () => {
    const h = makeHarness();
    await signupAndToken(h, "bob@example.com");
    // Force-expire the session.
    const sess = h.db.rows("sessions")[0];
    sess.expires_at = Date.now() - 1000;

    // Look up the original token via the jwt_id is impossible (it's
    // hashed), so we just send a bogus bearer to assert the negative path
    // and rely on the session-expiry branch in a second sub-step.
    const bogus = await h.fetch("/api/verify", {
      headers: { Authorization: "Bearer not-a-real-token" },
    });
    expect(bogus.status).toBe(401);

    // The harness exposes the most recent signup token; reissue via
    // login to test expired-session branch directly.
    const login = await h.fetch("/api/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        email: "bob@example.com",
        password: "correct-horse-7",
      }),
    });
    const loginBody = (await login.json()) as any;
    // Expire this new session too.
    h.db.rows("sessions").forEach((s) => (s.expires_at = Date.now() - 1000));
    const resp = await h.fetch("/api/verify", {
      headers: { Authorization: `Bearer ${loginBody.token}` },
    });
    expect(resp.status).toBe(401);
    const body = (await resp.json()) as any;
    expect(body.error).toBe("expired_token");
  });
});
