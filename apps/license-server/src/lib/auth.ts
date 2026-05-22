// Phase L1a — Bearer-token / session helpers shared across routes.

import type { Context } from "hono";
import { Db, type AccountRow, type SessionRow } from "./db";
import { sha256Hex, generateToken, uuidv4 } from "./crypto";
import type { AppEnv } from "./env";

export const SESSION_TTL_MS = 90 * 24 * 60 * 60 * 1000; // 90 days
export const DEVICE_LIMIT = 5;
export const RESET_TOKEN_TTL_MS = 15 * 60 * 1000; // 15 minutes

export function publicAccount(a: AccountRow) {
  return {
    id: a.id,
    email: a.email,
    display_name: a.display_name,
    type: a.type,
    trial_expires_at: a.trial_expires_at,
    lifetime_purchased_at: a.lifetime_purchased_at,
    email_verified_at: a.email_verified_at,
  };
}

export function publicSession(s: SessionRow) {
  return {
    id: s.id,
    device_id: s.device_id,
    device_label: s.device_label,
    user_agent: s.user_agent,
    ip: s.ip,
    last_seen_at: s.last_seen_at,
    created_at: s.created_at,
    expires_at: s.expires_at,
  };
}

export interface AuthContext {
  account: AccountRow;
  session: SessionRow;
}

export async function authenticate(
  c: Context<AppEnv>,
): Promise<AuthContext | { error: string; status: 401 }> {
  const header = c.req.header("Authorization") ?? "";
  const m = header.match(/^Bearer\s+(.+)$/i);
  if (!m) return { error: "missing_bearer_token", status: 401 };
  const token = m[1].trim();
  if (!token) return { error: "missing_bearer_token", status: 401 };
  const jwtId = await sha256Hex(token);
  const db = new Db(c.env.DB);
  const session = await db.getSessionByJwtId(jwtId);
  if (!session) return { error: "invalid_token", status: 401 };
  if (session.expires_at < Date.now()) return { error: "expired_token", status: 401 };
  const account = await db.getAccountById(session.account_id);
  if (!account) return { error: "account_missing", status: 401 };
  if (account.type === "revoked") return { error: "account_revoked", status: 401 };
  return { account, session };
}

export async function createSessionForAccount(
  db: Db,
  account: AccountRow,
  opts: {
    device_id?: string;
    device_label?: string;
    user_agent?: string;
    ip?: string;
  },
): Promise<{ token: string; session: SessionRow }> {
  const now = Date.now();
  const token = generateToken(32);
  const jwtId = await sha256Hex(token);
  const session: SessionRow = {
    id: uuidv4(),
    account_id: account.id,
    jwt_id: jwtId,
    device_id: opts.device_id ?? uuidv4(),
    device_label: opts.device_label ?? null,
    user_agent: opts.user_agent ?? null,
    ip: opts.ip ?? null,
    last_seen_at: now,
    created_at: now,
    expires_at: now + SESSION_TTL_MS,
  };
  await db.insertSession(session);
  return { token, session };
}

export function clientIp(c: Context<AppEnv>): string {
  return (
    c.req.header("cf-connecting-ip") ??
    c.req.header("x-forwarded-for")?.split(",")[0]?.trim() ??
    "unknown"
  );
}
