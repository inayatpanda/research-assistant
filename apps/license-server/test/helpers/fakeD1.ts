// Phase L1a — Hand-rolled in-memory D1 fake.
//
// Why not the official @cloudflare/vitest-pool-workers harness? It works
// but adds ~30s per cold run + Workerd dependency surface. The Worker
// code here only touches `prepare().bind().run() / first() / all()`, so a
// minimal table-backed shim covers our test surface with zero install
// cost. The shim implements just enough SQL to support the queries our
// repository layer emits.
//
// If we ever stray into joins or aggregates beyond `COUNT(*)`, swap this
// for the official pool.

interface RowMap {
  [key: string]: any;
}

type Table = RowMap[];

interface Tables {
  [name: string]: Table;
}

const SCHEMA: Record<string, string[]> = {
  accounts: [
    "id", "email", "password_hash", "display_name", "type",
    "trial_expires_at", "lifetime_purchased_at", "email_verified_at",
    "created_at", "updated_at",
  ],
  sessions: [
    "id", "account_id", "jwt_id", "device_id", "device_label",
    "user_agent", "ip", "last_seen_at", "created_at", "expires_at",
  ],
  purchase_events: [
    "id", "account_id", "ls_order_id", "amount_cents", "currency",
    "raw_payload", "created_at",
  ],
  email_events: [
    "id", "account_id", "email", "kind", "sent_at", "resend_id",
  ],
  password_resets: [
    "id", "account_id", "token_hash", "expires_at", "used_at", "created_at",
  ],
  rate_limits: ["id", "bucket", "hit_at"],
};

class FakeStatement {
  private bindings: any[] = [];
  constructor(private readonly db: FakeD1, private readonly sql: string) {}

  bind(...args: any[]): FakeStatement {
    this.bindings = args;
    return this;
  }

  async first<T = any>(): Promise<T | null> {
    const rows = await this.execAndGetRows();
    return (rows[0] ?? null) as T | null;
  }

  async all<T = any>(): Promise<{ results: T[] }> {
    const rows = await this.execAndGetRows();
    return { results: rows as T[] };
  }

  async run(): Promise<{ success: boolean }> {
    await this.execAndGetRows();
    return { success: true };
  }

  private async execAndGetRows(): Promise<RowMap[]> {
    return this.db.execute(this.sql, this.bindings);
  }
}

export class FakeD1 {
  private tables: Tables = {
    accounts: [],
    sessions: [],
    purchase_events: [],
    email_events: [],
    password_resets: [],
    rate_limits: [],
  };

  prepare(sql: string): FakeStatement {
    return new FakeStatement(this, sql);
  }

  /** Test-only direct row access. */
  rows(table: keyof typeof SCHEMA): RowMap[] {
    return this.tables[table];
  }

  /** Clear all tables (used between tests). */
  reset(): void {
    for (const k of Object.keys(this.tables)) this.tables[k] = [];
  }

  execute(sql: string, args: any[]): RowMap[] {
    const trimmed = sql.trim().replace(/\s+/g, " ");
    if (trimmed.startsWith("INSERT INTO ")) {
      return this.handleInsert(trimmed, args);
    }
    if (trimmed.startsWith("UPDATE ")) {
      return this.handleUpdate(trimmed, args);
    }
    if (trimmed.startsWith("DELETE FROM ")) {
      return this.handleDelete(trimmed, args);
    }
    if (trimmed.startsWith("SELECT ")) {
      return this.handleSelect(trimmed, args);
    }
    throw new Error(`FakeD1: unsupported SQL: ${trimmed}`);
  }

  // ---------------------------------------------------------- mutations

  private handleInsert(sql: string, args: any[]): RowMap[] {
    // INSERT INTO <table> (col1, col2, ...) VALUES (?, ?, ...)
    const m = sql.match(/^INSERT INTO (\w+) \(([^)]+)\) VALUES \(([^)]+)\)$/i);
    if (!m) throw new Error(`FakeD1 insert parse fail: ${sql}`);
    const table = m[1];
    const cols = m[2].split(",").map((s) => s.trim());
    if (args.length !== cols.length) {
      throw new Error(
        `FakeD1 insert: arg count ${args.length} != col count ${cols.length} in ${sql}`,
      );
    }
    const row: RowMap = {};
    for (let i = 0; i < cols.length; i++) row[cols[i]] = args[i];
    // Enforce UNIQUE on a per-table basis.
    const uniques: Record<string, string[]> = {
      accounts: ["id", "email"],
      sessions: ["id", "jwt_id"],
      purchase_events: ["id", "ls_order_id"],
      password_resets: ["id", "token_hash"],
      email_events: ["id"],
      rate_limits: ["id"],
    };
    for (const col of uniques[table] ?? []) {
      if (row[col] == null) continue;
      if (this.tables[table].some((r) => r[col] === row[col])) {
        throw new Error(`UNIQUE constraint failed: ${table}.${col}`);
      }
    }
    // Defaults
    if (table === "purchase_events" && row.ls_order_id === undefined) row.ls_order_id = null;
    if (!this.tables[table]) this.tables[table] = [];
    this.tables[table].push(row);
    return [];
  }

  private handleUpdate(sql: string, args: any[]): RowMap[] {
    // Match all the specific UPDATE statements we use.
    if (sql.startsWith("UPDATE accounts SET type = ?,")) {
      const [type, lifetime_purchased_at, trial_expires_at, updated_at, id] = args;
      const row = this.tables.accounts.find((r) => r.id === id);
      if (!row) return [];
      row.type = type;
      if (lifetime_purchased_at != null) row.lifetime_purchased_at = lifetime_purchased_at;
      row.trial_expires_at = trial_expires_at;
      row.updated_at = updated_at;
      return [];
    }
    if (sql.startsWith("UPDATE accounts SET password_hash = ?,")) {
      const [hash, updated_at, id] = args;
      const row = this.tables.accounts.find((r) => r.id === id);
      if (row) {
        row.password_hash = hash;
        row.updated_at = updated_at;
      }
      return [];
    }
    if (sql.startsWith("UPDATE sessions SET last_seen_at = ?")) {
      const [last_seen_at, id] = args;
      const row = this.tables.sessions.find((r) => r.id === id);
      if (row) row.last_seen_at = last_seen_at;
      return [];
    }
    if (sql.startsWith("UPDATE password_resets SET used_at = ?")) {
      const [used_at, id] = args;
      const row = this.tables.password_resets.find((r) => r.id === id);
      if (row) row.used_at = used_at;
      return [];
    }
    throw new Error(`FakeD1: unsupported UPDATE: ${sql}`);
  }

  private handleDelete(sql: string, args: any[]): RowMap[] {
    if (sql.startsWith("DELETE FROM sessions WHERE id = ?")) {
      const [id] = args;
      this.tables.sessions = this.tables.sessions.filter((r) => r.id !== id);
      return [];
    }
    if (sql.startsWith("DELETE FROM sessions WHERE account_id = ?")) {
      const [account_id] = args;
      this.tables.sessions = this.tables.sessions.filter(
        (r) => r.account_id !== account_id,
      );
      return [];
    }
    if (sql.startsWith("DELETE FROM rate_limits WHERE hit_at < ?")) {
      const [cutoff] = args;
      this.tables.rate_limits = this.tables.rate_limits.filter(
        (r) => r.hit_at >= cutoff,
      );
      return [];
    }
    throw new Error(`FakeD1: unsupported DELETE: ${sql}`);
  }

  private handleSelect(sql: string, args: any[]): RowMap[] {
    if (sql.startsWith("SELECT * FROM accounts WHERE email = ?")) {
      const [email] = args;
      return this.tables.accounts.filter((r) => r.email === email).slice(0, 1);
    }
    if (sql.startsWith("SELECT * FROM accounts WHERE id = ?")) {
      const [id] = args;
      return this.tables.accounts.filter((r) => r.id === id).slice(0, 1);
    }
    if (sql.startsWith("SELECT * FROM sessions WHERE jwt_id = ?")) {
      const [jwt_id] = args;
      return this.tables.sessions.filter((r) => r.jwt_id === jwt_id).slice(0, 1);
    }
    if (sql.startsWith("SELECT * FROM sessions WHERE id = ?")) {
      const [id] = args;
      return this.tables.sessions.filter((r) => r.id === id).slice(0, 1);
    }
    if (sql.startsWith("SELECT * FROM sessions WHERE account_id = ? AND expires_at > ?")) {
      const [account_id, now] = args;
      return this.tables.sessions
        .filter((r) => r.account_id === account_id && r.expires_at > now)
        .sort((a, b) => b.last_seen_at - a.last_seen_at);
    }
    if (sql.startsWith("SELECT * FROM purchase_events WHERE ls_order_id = ?")) {
      const [order_id] = args;
      return this.tables.purchase_events
        .filter((r) => r.ls_order_id === order_id)
        .slice(0, 1);
    }
    if (sql.startsWith("SELECT * FROM password_resets WHERE token_hash = ?")) {
      const [h] = args;
      return this.tables.password_resets
        .filter((r) => r.token_hash === h)
        .slice(0, 1);
    }
    if (sql.startsWith("SELECT COUNT(*) AS c FROM rate_limits WHERE bucket = ? AND hit_at >= ?")) {
      const [bucket, since] = args;
      const c = this.tables.rate_limits.filter(
        (r) => r.bucket === bucket && r.hit_at >= since,
      ).length;
      return [{ c }];
    }
    throw new Error(`FakeD1: unsupported SELECT: ${sql}`);
  }
}
