// Phase L1a — Shared test setup: builds a fresh app + env with a clean
// FakeD1 + NullEmailSender for every test.

import app from "../../src/index";
import { FakeD1 } from "./fakeD1";
import { NullEmailSender } from "../../src/lib/email";
import type { Bindings } from "../../src/lib/env";

export interface TestHarness {
  env: Bindings;
  db: FakeD1;
  mailer: NullEmailSender;
  fetch: (input: string, init?: RequestInit) => Promise<Response>;
}

export interface HarnessOpts {
  adminToken?: string;
  webhookSecret?: string;
}

export function makeHarness(opts: HarnessOpts = {}): TestHarness {
  const db = new FakeD1();
  const mailer = new NullEmailSender();
  const env: Bindings = {
    DB: db as unknown as Bindings["DB"],
    ADMIN_TOKEN: opts.adminToken ?? "test-admin-token",
    LEMONSQUEEZY_WEBHOOK_SECRET: opts.webhookSecret ?? "test-webhook-secret",
    APP_DOWNLOAD_URL: "https://example.test/install",
    APP_BASE_URL: "https://example.test",
    RESEND_FROM: "licenses@example.test",
    ENV: "test",
    __EMAIL_SENDER: mailer,
  };
  const fetch: TestHarness["fetch"] = async (input, init) => {
    const url = input.startsWith("http") ? input : `http://test.local${input}`;
    return await app.fetch(new Request(url, init), env);
  };
  return { env, db, mailer, fetch };
}
