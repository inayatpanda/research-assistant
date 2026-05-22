-- Phase L1a — D1 schema for the Research Assistant license server.
-- Apply with `wrangler d1 execute research-license --file=src/db/schema.sql`.
-- Re-running is safe: every statement uses IF NOT EXISTS.

CREATE TABLE IF NOT EXISTS accounts (
  id TEXT PRIMARY KEY,
  email TEXT NOT NULL UNIQUE,
  password_hash TEXT NOT NULL,
  display_name TEXT NOT NULL,
  type TEXT NOT NULL CHECK(type IN ('trial', 'lifetime', 'revoked')),
  trial_expires_at INTEGER,
  lifetime_purchased_at INTEGER,
  email_verified_at INTEGER,
  created_at INTEGER NOT NULL,
  updated_at INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_accounts_email ON accounts(email);

CREATE TABLE IF NOT EXISTS sessions (
  id TEXT PRIMARY KEY,
  account_id TEXT NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
  jwt_id TEXT NOT NULL UNIQUE,
  device_id TEXT NOT NULL,
  device_label TEXT,
  user_agent TEXT,
  ip TEXT,
  last_seen_at INTEGER NOT NULL,
  created_at INTEGER NOT NULL,
  expires_at INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_sessions_account ON sessions(account_id);
CREATE INDEX IF NOT EXISTS idx_sessions_jwt ON sessions(jwt_id);

CREATE TABLE IF NOT EXISTS purchase_events (
  id TEXT PRIMARY KEY,
  account_id TEXT NOT NULL REFERENCES accounts(id),
  ls_order_id TEXT UNIQUE,
  amount_cents INTEGER,
  currency TEXT,
  raw_payload TEXT,
  created_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS email_events (
  id TEXT PRIMARY KEY,
  account_id TEXT REFERENCES accounts(id),
  email TEXT NOT NULL,
  kind TEXT NOT NULL,
  sent_at INTEGER NOT NULL,
  resend_id TEXT
);

CREATE TABLE IF NOT EXISTS password_resets (
  id TEXT PRIMARY KEY,
  account_id TEXT NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
  token_hash TEXT NOT NULL UNIQUE,
  expires_at INTEGER NOT NULL,
  used_at INTEGER,
  created_at INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_password_resets_token ON password_resets(token_hash);

-- Rate-limit hits, GC'd on read by a sliding window query.
CREATE TABLE IF NOT EXISTS rate_limits (
  id TEXT PRIMARY KEY,
  bucket TEXT NOT NULL,        -- e.g. `signup:1.2.3.4`
  hit_at INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_rate_limits_bucket ON rate_limits(bucket, hit_at);
