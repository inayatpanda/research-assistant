# Research Assistant — Licence system

Phase L1a documentation. The licence system is a small Cloudflare Worker
+ D1 SQLite database living in `apps/license-server/`. The desktop and
web apps verify on every launch (with a 7-day offline-grace cache); the
landing site funnels signups, payments, and account management.

## Architecture

```
+-------------------+         +---------------------+        +-------------------+
| Electron / web    | <-----> | Cloudflare Worker   | <----> | Cloudflare D1     |
| Research Assistant|         | research-license    |        | research-license  |
+-------------------+         +---------------------+        +-------------------+
                                       |                            |
                                       v                            v
                              +-----------------+        +------------------------+
                              | Resend (email)  |        | Lemon Squeezy (webhook |
                              +-----------------+        | inbound only)          |
                                                         +------------------------+
```

**Why a central account?** A self-hosted licence file would be trivial
to share, and a hardware fingerprint would lock users out of their own
machines. A bearer token + 5-device cap + offline cache strikes the
right balance: lightweight, revocable, and never blocks people who lose
internet for a week.

## Lifecycle

### Signup (`POST /api/signup`)

```
client -> /api/signup {email, password, display_name}
            -> validate (10+ chars w/ digit, etc.)
            -> rate-limit by IP (5/hour)
            -> hash password (PBKDF2 SHA-256, 600k iterations)
            -> insert accounts row (type=trial, trial_expires_at=now+30d)
            -> insert sessions row, return token + account
            -> async: send welcome email via Resend
```

### Login (`POST /api/login`)

```
client -> /api/login {email, password, device_id, device_label}
            -> verify password
            -> count active sessions for the account
              -> if >= 5: return 409 device_limit_exceeded + device list
              -> else: insert sessions row, return token + device list
```

### Verify (every launch) (`GET /api/verify`)

```
client -> /api/verify (Authorization: Bearer <token>)
          -> SHA-256(token) -> sessions.jwt_id lookup
          -> assert session.expires_at > now
          -> assert account.type != 'revoked'
          -> bump sessions.last_seen_at
          -> return {valid:true, account, session}
```

**Offline grace**: the client keeps the last successful verify response
in local storage for 7 days. If `verify` fails to reach the network
within that window, the app continues to run. After 7 days offline, the
app refuses to start until it can reach the licence server again. (See
`L1b: App-side license flow` for the client cache implementation.)

### Purchase (`POST /api/webhook/lemonsqueezy`)

```
Lemon Squeezy -> /api/webhook/lemonsqueezy (X-Signature: hex(hmac-sha256))
                  -> verify HMAC
                  -> parse {meta.event_name, data.attributes.{status,user_email,total,...}}
                  -> if event != 'order_created' or status != 'paid': ack + skip
                  -> dedup on data.id (purchase_events.ls_order_id)
                  -> find or create account
                       -> existing: set type='lifetime', clear trial expiry
                       -> new: create with random temp password, send welcome_lifetime email
                  -> insert purchase_events row
```

### Reset (`POST /api/forgot-password`, `POST /api/reset-password`)

```
client -> /api/forgot-password {email}
            -> always returns 200 (don't leak existence)
            -> if account exists: store SHA-256(token) + 15-minute TTL
            -> send reset email with /reset?token=<plain>

client -> /api/reset-password {token, new_password}
            -> SHA-256(token) -> password_resets lookup
            -> assert unused, not expired
            -> update password hash, mark reset used
            -> invalidate every session for this account
```

## Privacy

Every launch sends:

- Bearer session token (already known to the server)
- User-Agent string
- IP address (logged on the session row)

Stored at rest:

- Email, display name, hashed password, account type + timestamps
- Active sessions (token hash, device id/label, user-agent, IP, timestamps)
- Purchase events (Lemon Squeezy order id + raw payload, retained for accounting)
- Email send history (kind + Resend message id)

We do **not** send manuscript content, file contents, telemetry events,
or any analytics. The app's project data stays local-first.

Retention: sessions are auto-expired after 90 days. Accounts can be
deleted by emailing support; their sessions + reset tokens cascade.

## Failure modes

- **D1 down**: all routes 5xx. Apps fall back to the 7-day offline cache.
- **Resend down**: account creation still succeeds; the welcome email
  retries on the next event. We log the failure in `email_events` with a
  `null` resend_id.
- **Lemon Squeezy delays delivery**: webhook is idempotent on `ls_order_id`,
  so re-delivery is safe.
- **Lost device**: the user revokes the device from /account or via
  /api/logout-all. The 5-device cap means slot freed up immediately.

## Operations

- Mint a comp licence: `python scripts/mint_license.py --email ... --type lifetime`.
- Revoke: `curl -X POST .../api/admin/revoke -H "X-Admin-Token: $RMA_ADMIN_TOKEN" -d '{"email":"..."}'`.
- See the deployment README at `apps/license-server/README.md`.
