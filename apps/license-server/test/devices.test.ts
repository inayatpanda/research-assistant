// Phase L1a — device list + revoke tests.

import { describe, it, expect } from "vitest";
import { makeHarness } from "./helpers/setup";

describe("device management", () => {
  it("GET /api/account lists every active device", async () => {
    const h = makeHarness();
    const r = await h.fetch("/api/signup", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        email: "alice@example.com",
        password: "correct-horse-7",
        display_name: "Alice",
        device_label: "Mac",
      }),
    });
    const b = (await r.json()) as any;
    await h.fetch("/api/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        email: "alice@example.com",
        password: "correct-horse-7",
        device_label: "iPad",
      }),
    });

    const resp = await h.fetch("/api/account", {
      headers: { Authorization: `Bearer ${b.token}` },
    });
    expect(resp.status).toBe(200);
    const body = (await resp.json()) as any;
    expect(body.devices).toHaveLength(2);
  });

  it("DELETE /api/devices/:id revokes a specific session", async () => {
    const h = makeHarness();
    const r = await h.fetch("/api/signup", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        email: "bob@example.com",
        password: "correct-horse-7",
        display_name: "Bob",
      }),
    });
    const b = (await r.json()) as any;
    const r2 = await h.fetch("/api/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        email: "bob@example.com",
        password: "correct-horse-7",
        device_label: "Other",
      }),
    });
    const b2 = (await r2.json()) as any;

    const other = b2.session.id;
    const resp = await h.fetch(`/api/devices/${other}`, {
      method: "DELETE",
      headers: { Authorization: `Bearer ${b.token}` },
    });
    expect(resp.status).toBe(200);
    expect(h.db.rows("sessions")).toHaveLength(1);
    // The other token now 401s.
    const v = await h.fetch("/api/verify", {
      headers: { Authorization: `Bearer ${b2.token}` },
    });
    expect(v.status).toBe(401);
  });
});
