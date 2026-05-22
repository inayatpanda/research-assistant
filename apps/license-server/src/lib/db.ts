// Phase L1a — Tiny D1 repository layer. All time fields are integers
// (milliseconds since epoch) so the storage format stays portable.

import type { D1Database } from "@cloudflare/workers-types";

export type AccountType = "trial" | "lifetime" | "revoked";

export interface AccountRow {
  id: string;
  email: string;
  password_hash: string;
  display_name: string;
  type: AccountType;
  trial_expires_at: number | null;
  lifetime_purchased_at: number | null;
  email_verified_at: number | null;
  created_at: number;
  updated_at: number;
}

export interface SessionRow {
  id: string;
  account_id: string;
  jwt_id: string;
  device_id: string;
  device_label: string | null;
  user_agent: string | null;
  ip: string | null;
  last_seen_at: number;
  created_at: number;
  expires_at: number;
}

export interface PasswordResetRow {
  id: string;
  account_id: string;
  token_hash: string;
  expires_at: number;
  used_at: number | null;
  created_at: number;
}

export interface PurchaseEventRow {
  id: string;
  account_id: string;
  ls_order_id: string | null;
  amount_cents: number | null;
  currency: string | null;
  raw_payload: string | null;
  created_at: number;
}

export class Db {
  constructor(private readonly d1: D1Database) {}

  // ----------------------------------------------------------- accounts

  async insertAccount(row: AccountRow): Promise<void> {
    await this.d1
      .prepare(
        `INSERT INTO accounts (id, email, password_hash, display_name, type,
           trial_expires_at, lifetime_purchased_at, email_verified_at,
           created_at, updated_at)
         VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
      )
      .bind(
        row.id,
        row.email,
        row.password_hash,
        row.display_name,
        row.type,
        row.trial_expires_at,
        row.lifetime_purchased_at,
        row.email_verified_at,
        row.created_at,
        row.updated_at,
      )
      .run();
  }

  async getAccountByEmail(email: string): Promise<AccountRow | null> {
    const row = await this.d1
      .prepare(`SELECT * FROM accounts WHERE email = ? LIMIT 1`)
      .bind(email)
      .first<AccountRow>();
    return row ?? null;
  }

  async getAccountById(id: string): Promise<AccountRow | null> {
    const row = await this.d1
      .prepare(`SELECT * FROM accounts WHERE id = ? LIMIT 1`)
      .bind(id)
      .first<AccountRow>();
    return row ?? null;
  }

  async updateAccountType(
    id: string,
    type: AccountType,
    extra: { lifetime_purchased_at?: number | null; trial_expires_at?: number | null } = {},
  ): Promise<void> {
    await this.d1
      .prepare(
        `UPDATE accounts SET type = ?,
           lifetime_purchased_at = COALESCE(?, lifetime_purchased_at),
           trial_expires_at = ?,
           updated_at = ?
         WHERE id = ?`,
      )
      .bind(
        type,
        extra.lifetime_purchased_at ?? null,
        extra.trial_expires_at === undefined ? null : extra.trial_expires_at,
        Date.now(),
        id,
      )
      .run();
  }

  async updateAccountPasswordHash(id: string, hash: string): Promise<void> {
    await this.d1
      .prepare(
        `UPDATE accounts SET password_hash = ?, updated_at = ? WHERE id = ?`,
      )
      .bind(hash, Date.now(), id)
      .run();
  }

  // ----------------------------------------------------------- sessions

  async insertSession(row: SessionRow): Promise<void> {
    await this.d1
      .prepare(
        `INSERT INTO sessions (id, account_id, jwt_id, device_id, device_label,
           user_agent, ip, last_seen_at, created_at, expires_at)
         VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
      )
      .bind(
        row.id,
        row.account_id,
        row.jwt_id,
        row.device_id,
        row.device_label,
        row.user_agent,
        row.ip,
        row.last_seen_at,
        row.created_at,
        row.expires_at,
      )
      .run();
  }

  async getSessionByJwtId(jwt_id: string): Promise<SessionRow | null> {
    const row = await this.d1
      .prepare(`SELECT * FROM sessions WHERE jwt_id = ? LIMIT 1`)
      .bind(jwt_id)
      .first<SessionRow>();
    return row ?? null;
  }

  async getSessionById(id: string): Promise<SessionRow | null> {
    const row = await this.d1
      .prepare(`SELECT * FROM sessions WHERE id = ? LIMIT 1`)
      .bind(id)
      .first<SessionRow>();
    return row ?? null;
  }

  async listActiveSessions(account_id: string): Promise<SessionRow[]> {
    const now = Date.now();
    const res = await this.d1
      .prepare(
        `SELECT * FROM sessions
         WHERE account_id = ? AND expires_at > ?
         ORDER BY last_seen_at DESC`,
      )
      .bind(account_id, now)
      .all<SessionRow>();
    return res.results ?? [];
  }

  async bumpSessionSeen(id: string, now: number): Promise<void> {
    await this.d1
      .prepare(`UPDATE sessions SET last_seen_at = ? WHERE id = ?`)
      .bind(now, id)
      .run();
  }

  async deleteSession(id: string): Promise<void> {
    await this.d1.prepare(`DELETE FROM sessions WHERE id = ?`).bind(id).run();
  }

  async deleteSessionsForAccount(account_id: string): Promise<void> {
    await this.d1
      .prepare(`DELETE FROM sessions WHERE account_id = ?`)
      .bind(account_id)
      .run();
  }

  // ----------------------------------------------------------- purchase

  async getPurchaseByOrderId(ls_order_id: string): Promise<PurchaseEventRow | null> {
    const row = await this.d1
      .prepare(`SELECT * FROM purchase_events WHERE ls_order_id = ? LIMIT 1`)
      .bind(ls_order_id)
      .first<PurchaseEventRow>();
    return row ?? null;
  }

  async insertPurchase(row: PurchaseEventRow): Promise<void> {
    await this.d1
      .prepare(
        `INSERT INTO purchase_events (id, account_id, ls_order_id, amount_cents,
           currency, raw_payload, created_at)
         VALUES (?, ?, ?, ?, ?, ?, ?)`,
      )
      .bind(
        row.id,
        row.account_id,
        row.ls_order_id,
        row.amount_cents,
        row.currency,
        row.raw_payload,
        row.created_at,
      )
      .run();
  }

  // ------------------------------------------------------ password reset

  async insertPasswordReset(row: PasswordResetRow): Promise<void> {
    await this.d1
      .prepare(
        `INSERT INTO password_resets (id, account_id, token_hash, expires_at,
           used_at, created_at)
         VALUES (?, ?, ?, ?, ?, ?)`,
      )
      .bind(
        row.id,
        row.account_id,
        row.token_hash,
        row.expires_at,
        row.used_at,
        row.created_at,
      )
      .run();
  }

  async getPasswordResetByTokenHash(token_hash: string): Promise<PasswordResetRow | null> {
    const row = await this.d1
      .prepare(`SELECT * FROM password_resets WHERE token_hash = ? LIMIT 1`)
      .bind(token_hash)
      .first<PasswordResetRow>();
    return row ?? null;
  }

  async markPasswordResetUsed(id: string): Promise<void> {
    await this.d1
      .prepare(`UPDATE password_resets SET used_at = ? WHERE id = ?`)
      .bind(Date.now(), id)
      .run();
  }

  // ----------------------------------------------------------- email log

  async insertEmailEvent(row: {
    id: string;
    account_id: string | null;
    email: string;
    kind: string;
    sent_at: number;
    resend_id: string | null;
  }): Promise<void> {
    await this.d1
      .prepare(
        `INSERT INTO email_events (id, account_id, email, kind, sent_at, resend_id)
         VALUES (?, ?, ?, ?, ?, ?)`,
      )
      .bind(
        row.id,
        row.account_id,
        row.email,
        row.kind,
        row.sent_at,
        row.resend_id,
      )
      .run();
  }

  // ----------------------------------------------------------- rate-limit

  /**
   * Returns the number of hits in `bucket` within the last `windowMs` ms.
   * Inserts a hit row as a side effect. Old rows are GC'd opportunistically.
   */
  async hitRateLimit(bucket: string, windowMs: number): Promise<number> {
    const now = Date.now();
    const since = now - windowMs;
    await this.d1
      .prepare(`INSERT INTO rate_limits (id, bucket, hit_at) VALUES (?, ?, ?)`)
      .bind(crypto.randomUUID(), bucket, now)
      .run();
    // Sweep ancient entries (best-effort, keeps the table bounded).
    await this.d1
      .prepare(`DELETE FROM rate_limits WHERE hit_at < ?`)
      .bind(now - windowMs * 4)
      .run();
    const row = await this.d1
      .prepare(
        `SELECT COUNT(*) AS c FROM rate_limits WHERE bucket = ? AND hit_at >= ?`,
      )
      .bind(bucket, since)
      .first<{ c: number }>();
    return row?.c ?? 0;
  }
}
