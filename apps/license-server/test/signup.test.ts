// Phase L1a — signup endpoint tests.

import { describe, it, expect } from "vitest";
import { makeHarness } from "./helpers/setup";

describe("POST /api/signup", () => {
  it("creates a trial account and returns a session token", async () => {
    const h = makeHarness();
    const resp = await h.fetch("/api/signup", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        email: "alice@example.com",
        password: "correct-horse-7",
        display_name: "Alice",
      }),
    });
    expect(resp.status).toBe(200);
    const body = (await resp.json()) as any;
    expect(typeof body.token).toBe("string");
    expect(body.token.length).toBeGreaterThan(20);
    expect(body.account.email).toBe("alice@example.com");
    expect(body.account.type).toBe("trial");
    expect(typeof body.account.trial_expires_at).toBe("number");
    expect(h.db.rows("accounts")).toHaveLength(1);
    expect(h.db.rows("sessions")).toHaveLength(1);
    // Welcome email queued.
    expect(h.mailer.sent).toHaveLength(1);
    expect(h.mailer.sent[0].to).toBe("alice@example.com");
    expect(h.mailer.sent[0].subject).toMatch(/trial/i);
  });

  it("rejects weak passwords with 400", async () => {
    const h = makeHarness();
    const resp = await h.fetch("/api/signup", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        email: "bob@example.com",
        password: "short",
        display_name: "Bob",
      }),
    });
    expect(resp.status).toBe(400);
    const body = (await resp.json()) as any;
    expect(body.error).toBe("validation_failed");
    expect(body.details.some((d: any) => d.field === "password")).toBe(true);
    expect(h.db.rows("accounts")).toHaveLength(0);
  });

  it("rejects duplicate email with 409", async () => {
    const h = makeHarness();
    const payload = {
      email: "carol@example.com",
      password: "correct-horse-7",
      display_name: "Carol",
    };
    const first = await h.fetch("/api/signup", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    expect(first.status).toBe(200);
    const dup = await h.fetch("/api/signup", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    expect(dup.status).toBe(409);
    const body = (await dup.json()) as any;
    expect(body.error).toBe("email_in_use");
  });
});
