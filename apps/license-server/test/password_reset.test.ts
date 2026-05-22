// Phase L1a — password reset tests.

import { describe, it, expect } from "vitest";
import { makeHarness } from "./helpers/setup";

describe("password reset", () => {
  it("forgot-password sends an email + creates a reset row", async () => {
    const h = makeHarness();
    await h.fetch("/api/signup", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        email: "alice@example.com",
        password: "correct-horse-7",
        display_name: "Alice",
      }),
    });
    h.mailer.sent.length = 0; // clear welcome email

    const resp = await h.fetch("/api/forgot-password", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email: "alice@example.com" }),
    });
    expect(resp.status).toBe(200);
    expect((await resp.json() as any).ok).toBe(true);
    expect(h.db.rows("password_resets")).toHaveLength(1);
    expect(h.mailer.sent).toHaveLength(1);
    expect(h.mailer.sent[0].subject.toLowerCase()).toContain("reset");

    // Forgot-password for an unknown email still returns 200 + no row.
    h.mailer.sent.length = 0;
    const r2 = await h.fetch("/api/forgot-password", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email: "nobody@example.com" }),
    });
    expect(r2.status).toBe(200);
    expect(h.db.rows("password_resets")).toHaveLength(1);
    expect(h.mailer.sent).toHaveLength(0);
  });

  it("reset-password rotates the password + kills sessions", async () => {
    const h = makeHarness();
    const sup = await h.fetch("/api/signup", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        email: "bob@example.com",
        password: "correct-horse-7",
        display_name: "Bob",
      }),
    });
    const oldBody = (await sup.json()) as any;

    await h.fetch("/api/forgot-password", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email: "bob@example.com" }),
    });
    // Grab the reset link out of the email body.
    const last = h.mailer.sent[h.mailer.sent.length - 1];
    const m = last.text.match(/token=([^\s)]+)/);
    expect(m).toBeTruthy();
    const token = decodeURIComponent(m![1]);

    const resp = await h.fetch("/api/reset-password", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ token, new_password: "newer-horse-99" }),
    });
    expect(resp.status).toBe(200);

    // Old session invalidated.
    const v = await h.fetch("/api/verify", {
      headers: { Authorization: `Bearer ${oldBody.token}` },
    });
    expect(v.status).toBe(401);

    // New password works.
    const login = await h.fetch("/api/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        email: "bob@example.com",
        password: "newer-horse-99",
      }),
    });
    expect(login.status).toBe(200);

    // Reset token can't be reused.
    const again = await h.fetch("/api/reset-password", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ token, new_password: "even-newer-77" }),
    });
    expect(again.status).toBe(400);
  });
});
