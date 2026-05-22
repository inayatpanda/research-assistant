// Phase L1a — Worker bindings & DI container.
//
// Hono receives an `Env` generic for `c.env`; tests inject a fake env that
// substitutes a NullEmailSender + a fresh in-memory D1 (via the
// vitest-pool-workers harness).

import type { D1Database } from "@cloudflare/workers-types";
import { Db } from "./db";
import { ResendEmailSender, NullEmailSender, type EmailSender } from "./email";

export interface Bindings {
  DB: D1Database;
  ADMIN_TOKEN?: string;
  RESEND_API_KEY?: string;
  RESEND_FROM?: string;
  LEMONSQUEEZY_WEBHOOK_SECRET?: string;
  APP_DOWNLOAD_URL?: string;
  APP_BASE_URL?: string;
  ENV?: string;
  // Optional test-only override; the route layer uses getEmailSender(env).
  __EMAIL_SENDER?: EmailSender;
}

export type AppEnv = { Bindings: Bindings };

export function getEmailSender(env: Bindings): EmailSender {
  if (env.__EMAIL_SENDER) return env.__EMAIL_SENDER;
  if (env.RESEND_API_KEY) {
    return new ResendEmailSender(
      env.RESEND_API_KEY,
      env.RESEND_FROM ?? "licenses@research-assistant.dev",
    );
  }
  return new NullEmailSender();
}

export function getDb(env: Bindings): Db {
  return new Db(env.DB);
}
