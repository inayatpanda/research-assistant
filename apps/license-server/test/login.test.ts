// Phase L1a — login endpoint tests.

import { describe, it, expect } from "vitest";
import { makeHarness } from "./helpers/setup";

async function signup(h: ReturnType<typeof makeHarness>, email: string) {
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
}

describe("POST /api/login", () => {
  it("returns a token on correct credentials", async () => {
    const h = makeHarness();
    await signup(h, "alice@example.com");
    const resp = await h.fetch("/api/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        email: "alice@example.com",
        password: "correct-horse-7",
        device_label: "Test Device",
      }),
    });
    expect(resp.status).toBe(200);
    const body = (await resp.json()) as any;
    expect(typeof body.token).toBe("string");
    expect(body.account.email).toBe("alice@example.com");
    expect(Array.isArray(body.devices)).toBe(true);
    expect(body.devices.length).toBeGreaterThanOrEqual(1);
  });

  it("rejects wrong password with 401", async () => {
    const h = makeHarness();
    await signup(h, "bob@example.com");
    const resp = await h.fetch("/api/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        email: "bob@example.com",
        password: "wrong-password-9",
      }),
    });
    expect(resp.status).toBe(401);
    const body = (await resp.json()) as any;
    expect(body.error).toBe("invalid_credentials");
  });

  it("rejects concurrent logins that would breach the 5-device cap", async () => {
    // Fix-13/1 regression: two concurrent POST /api/login calls both
    // observed active.length < 5 in the old read-then-insert code and
    // both inserted, yielding 6 active devices. The atomic
    // INSERT ... WHERE (SELECT COUNT < limit) means at most 5 sessions
    // ever exist regardless of how many concurrent calls fire.
    const h = makeHarness();
    await signup(h, "race@example.com");
    // Bring the account up to 4 active sessions (signup created #1, the
    // loop adds 3 more = 4). The next *two* concurrent logins must
    // produce exactly one success and one 409, never two successes.
    for (let i = 0; i < 3; i++) {
      const r = await h.fetch("/api/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email: "race@example.com",
          password: "correct-horse-7",
          device_label: `Device ${i + 2}`,
        }),
      });
      expect(r.status).toBe(200);
    }
    // Two concurrent slot-grabbers.
    const [a, b] = await Promise.all([
      h.fetch("/api/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email: "race@example.com",
          password: "correct-horse-7",
          device_label: "Racer A",
        }),
      }),
      h.fetch("/api/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email: "race@example.com",
          password: "correct-horse-7",
          device_label: "Racer B",
        }),
      }),
    ]);
    const statuses = [a.status, b.status].sort();
    expect(statuses).toEqual([200, 409]);
    // Confirm the DB never went above 5.
    expect(h.db.rows("sessions").length).toBeLessThanOrEqual(5);
  });

  it("returns 409 device_limit_exceeded after 5 active sessions", async () => {
    const h = makeHarness();
    await signup(h, "carol@example.com");
    // The signup already created session #1. Add four more logins (=5
    // active sessions). The sixth login must be blocked.
    for (let i = 0; i < 4; i++) {
      const r = await h.fetch("/api/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email: "carol@example.com",
          password: "correct-horse-7",
          device_label: `Device ${i + 2}`,
        }),
      });
      expect(r.status).toBe(200);
    }
    const blocked = await h.fetch("/api/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        email: "carol@example.com",
        password: "correct-horse-7",
        device_label: "Sixth",
      }),
    });
    expect(blocked.status).toBe(409);
    const body = (await blocked.json()) as any;
    expect(body.error).toBe("device_limit_exceeded");
    expect(body.devices.length).toBe(5);
  });
});
