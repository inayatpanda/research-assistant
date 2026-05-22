# Research Assistant — Licence Server

Phase L1a — Cloudflare Worker + D1 + Resend. Free-tier-only. Mints,
verifies, and revokes lifetime/trial licences for the Research Assistant
desktop and web apps.

## Architecture

- **Worker**: `apps/license-server/src/` — Hono router with PBKDF2 password
  hashing, opaque session tokens, Lemon Squeezy webhook ingestion.
- **D1**: schema in `src/db/schema.sql`. Five tables — accounts, sessions,
  purchase events, email events, password resets — plus a rate-limit
  table swept opportunistically on each hit.
- **Email**: Resend REST API (free tier — 3,000 emails/mo) with a
  drop-in `NullEmailSender` for tests.

## Bring-up checklist

You only need to do this once per environment.

### 1. Log in to Cloudflare

```sh
cd apps/license-server
npx wrangler login
```

### 2. Create the D1 database

```sh
npx wrangler d1 create research-license
```

Wrangler will print something like:

```
[[d1_databases]]
binding = "DB"
database_name = "research-license"
database_id = "abcd1234-...-..."
```

Copy the `database_id` and paste it into `wrangler.toml` (replace the
`TBD-AFTER-WRANGLER-D1-CREATE` placeholder).

### 3. Apply the schema

Local (Miniflare):

```sh
npx wrangler d1 execute research-license --local --file=src/db/schema.sql
```

Remote (production):

```sh
npx wrangler d1 execute research-license --remote --file=src/db/schema.sql
```

### 4. Set the three secrets

```sh
npx wrangler secret put ADMIN_TOKEN
# paste a long random string. Use this whenever you run scripts/mint_license.py.

npx wrangler secret put RESEND_API_KEY
# from https://resend.com/api-keys

npx wrangler secret put LEMONSQUEEZY_WEBHOOK_SECRET
# from Lemon Squeezy → Settings → Webhooks (after step 6 below).
```

### 5. Deploy

```sh
npx wrangler deploy
```

The first deploy publishes to `research-assistant-license.workers.dev`.
(You can attach a custom domain later via the Cloudflare dashboard;
nothing in the codebase hardcodes the URL.)

### 6. Set up Lemon Squeezy

1. Create a product **Research Assistant Lifetime** at $29 USD.
2. Add a webhook pointing at
   `https://<your-worker-url>/api/webhook/lemonsqueezy`.
3. Copy the webhook secret and feed it to `wrangler secret put` (step 4).

### 7. Smoke-test

```sh
# Healthcheck
curl https://<your-worker-url>/api/health

# Mint a comp licence
RMA_ADMIN_TOKEN=... python ../../scripts/mint_license.py \
  --email test@example.com --name "Test" --type lifetime \
  --server-url https://<your-worker-url>
```

## Local development

```sh
npm install
npm run dev   # starts wrangler dev on a local port
npm test      # runs vitest against the in-memory D1 fake
```

The `vitest` harness in `test/helpers/fakeD1.ts` is a minimal in-memory
D1 fake — enough to cover the queries the repository layer emits. For
deeper integration tests, swap it for `@cloudflare/vitest-pool-workers`.

## File map

| Path | Purpose |
| ---- | ------- |
| `src/index.ts` | Hono entry + CORS + route mounts |
| `src/routes/` | One file per endpoint group |
| `src/lib/crypto.ts` | PBKDF2, HMAC, token + UUID helpers |
| `src/lib/db.ts` | D1 repository — typed CRUD |
| `src/lib/email.ts` | Resend wrapper + templates |
| `src/lib/auth.ts` | Bearer-token validation + session helpers |
| `src/db/schema.sql` | Canonical D1 schema |

## Endpoints

| Method | Path | Notes |
| ------ | ---- | ----- |
| POST   | /api/signup | trial sign-up, sends welcome email |
| POST   | /api/login | password login, enforces 5-device cap |
| GET    | /api/verify | bearer-token check, 7-day client cache |
| GET    | /api/account | verify + full device list |
| POST   | /api/logout | invalidate current session |
| POST   | /api/logout-all | invalidate every session |
| DELETE | /api/devices/:id | revoke a specific session |
| POST   | /api/admin/mint | comp/demo licences (X-Admin-Token) |
| POST   | /api/admin/revoke | revoke a licence (X-Admin-Token) |
| POST   | /api/webhook/lemonsqueezy | order webhook (X-Signature HMAC-SHA256) |
| POST   | /api/forgot-password | request reset link |
| POST   | /api/reset-password | redeem reset link |

## Privacy

See `docs/license-system.md` for the full disclosure of what gets sent
on every launch and how long it's retained.
