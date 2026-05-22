// Phase L1a — logout / logout-all tests.

import { describe, it, expect } from "vitest";
import { makeHarness } from "./helpers/setup";

async function signupToken(h: ReturnType<typeof makeHarness>, email: string) {
  const r = await h.fetch("/api/signup", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      email,
      password: "correct-horse-7",
      display_name: "Test",
    }),
  });
  const body = (await r.json()) as any;
  return body.token as string;
}

describe("logout endpoints", () => {
  it("POST /api/logout invalidates only the current session", async () => {
    const h = makeHarness();
    const t1 = await signupToken(h, "alice@example.com");
    // Login again to open a second session.
    const r2 = await h.fetch("/api/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        email: "alice@example.com",
        password: "correct-horse-7",
      }),
    });
    const b2 = (await r2.json()) as any;
    expect(h.db.rows("sessions")).toHaveLength(2);

    const resp = await h.fetch("/api/logout", {
      method: "POST",
      headers: { Authorization: `Bearer ${t1}` },
    });
    expect(resp.status).toBe(200);
    expect(h.db.rows("sessions")).toHaveLength(1);

    // The other token still works.
    const v = await h.fetch("/api/verify", {
      headers: { Authorization: `Bearer ${b2.token}` },
    });
    expect(v.status).toBe(200);
  });

  it("POST /api/logout-all invalidates every session", async () => {
    const h = makeHarness();
    const t1 = await signupToken(h, "bob@example.com");
    await h.fetch("/api/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        email: "bob@example.com",
        password: "correct-horse-7",
      }),
    });
    expect(h.db.rows("sessions")).toHaveLength(2);
    const resp = await h.fetch("/api/logout-all", {
      method: "POST",
      headers: { Authorization: `Bearer ${t1}` },
    });
    expect(resp.status).toBe(200);
    expect(h.db.rows("sessions")).toHaveLength(0);
  });
});
