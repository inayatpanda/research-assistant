// Phase L1a — GET /api/verify, GET /api/account
//
// `verify` is the lightweight call made on every app launch (with a 7-day
// client-side cache); `account` adds the full device list for the
// in-product account page.

import { Hono } from "hono";
import type { AppEnv } from "../lib/env";
import { getDb } from "../lib/env";
import { authenticate, publicAccount, publicSession } from "../lib/auth";

export const verifyRoute = new Hono<AppEnv>().get("/", async (c) => {
  const auth = await authenticate(c);
  if ("error" in auth) return c.json({ error: auth.error, valid: false }, auth.status);
  const db = getDb(c.env);
  await db.bumpSessionSeen(auth.session.id, Date.now());
  return c.json({
    valid: true,
    account: publicAccount(auth.account),
    session: publicSession(auth.session),
  });
});

export const accountRoute = new Hono<AppEnv>().get("/", async (c) => {
  const auth = await authenticate(c);
  if ("error" in auth) return c.json({ error: auth.error, valid: false }, auth.status);
  const db = getDb(c.env);
  await db.bumpSessionSeen(auth.session.id, Date.now());
  const devices = await db.listActiveSessions(auth.account.id);
  return c.json({
    valid: true,
    account: publicAccount(auth.account),
    session: publicSession(auth.session),
    devices: devices.map(publicSession),
  });
});
