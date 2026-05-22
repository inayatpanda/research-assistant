// Phase L1a — POST /api/logout, POST /api/logout-all, DELETE /api/devices/:id

import { Hono } from "hono";
import type { AppEnv } from "../lib/env";
import { getDb } from "../lib/env";
import { authenticate } from "../lib/auth";

export const logoutRoute = new Hono<AppEnv>().post("/", async (c) => {
  const auth = await authenticate(c);
  if ("error" in auth) return c.json({ error: auth.error }, auth.status);
  const db = getDb(c.env);
  await db.deleteSession(auth.session.id);
  return c.json({ ok: true });
});

export const logoutAllRoute = new Hono<AppEnv>().post("/", async (c) => {
  const auth = await authenticate(c);
  if ("error" in auth) return c.json({ error: auth.error }, auth.status);
  const db = getDb(c.env);
  await db.deleteSessionsForAccount(auth.account.id);
  return c.json({ ok: true });
});

export const devicesRoute = new Hono<AppEnv>().delete("/:session_id", async (c) => {
  const auth = await authenticate(c);
  if ("error" in auth) return c.json({ error: auth.error }, auth.status);
  const targetId = c.req.param("session_id");
  const db = getDb(c.env);
  const target = await db.getSessionById(targetId);
  if (!target) return c.json({ error: "session_not_found" }, 404);
  if (target.account_id !== auth.account.id) return c.json({ error: "forbidden" }, 403);
  await db.deleteSession(targetId);
  return c.json({ ok: true });
});
