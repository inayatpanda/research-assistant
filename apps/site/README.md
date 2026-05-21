# Research Assistant — landing site

Marketing + install site for [Research Assistant](../README.md). Static React +
TypeScript + Tailwind, built with Vite, deployable to Cloudflare Pages free tier.

## Pages

| Path         | Purpose                                                       |
|--------------|---------------------------------------------------------------|
| `/`          | Hero + 8-feature grid + trust strip + download CTA            |
| `/install`   | Mac / Win / Linux download cards with OS auto-detect          |
| `/sync`      | Tailscale setup guide + troubleshooting accordion             |
| `/docs`      | What/Who/Cost + FAQ accordion                                 |
| `/changelog` | Reverse-chrono release notes (sourced from `src/data/changelog.ts`) |

## Local development

```bash
cd apps/site
npm install
npm run dev          # http://127.0.0.1:5174
```

## Build

```bash
npm run build        # outputs static bundle to ./dist
npm run preview      # serves the built bundle for smoke-testing
```

## Tests

```bash
npm run test         # vitest run
npm run typecheck    # tsc --noEmit
```

## Deploy to Cloudflare Pages

The site is configured for Cloudflare Pages via `wrangler.toml`:

```bash
# 1. Install wrangler (once, globally or per-user)
npm install -g wrangler

# 2. Authenticate (opens browser; one-time)
wrangler login

# 3. Build and deploy
cd apps/site
npm run build
wrangler pages deploy dist --project-name research-assistant
```

Subsequent deploys re-run the same command — Cloudflare keeps the project
history and you get an automatic preview URL per deploy.

## TODO for the user before first deploy

1. **Create the GitHub repo** that hosts the desktop app releases, then
   search-and-replace `TBD-OWNER/TBD-REPO` across `apps/site/src/**` and
   `apps/site/index.html`. The download CTAs target
   `https://github.com/<OWNER>/<REPO>/releases/latest/download/...`.
2. **Sign up for Cloudflare** (free tier) and create a Pages project named
   `research-assistant`. The first `wrangler pages deploy` will offer to create
   it for you.
3. **Connect a custom domain** in the Cloudflare dashboard:
   `Pages → research-assistant → Custom domains → Set up a custom domain`. If
   the domain is already on Cloudflare DNS it activates in seconds; otherwise
   add the CNAME they show you at your registrar.
4. **(Optional) Hook to GitHub for auto-deploys**: connect the repo in the
   Pages project settings and set the build command to `npm run build` and the
   build output directory to `apps/site/dist`. Pull requests then get a
   preview deployment automatically.

## Why standalone?

The site has no shared code with `apps/web` so it ships independently with a
minimal dependency footprint (React, Router, Tailwind, framer-motion,
lucide-react). No backend calls, no PWA, no auth — every page is a static
HTML/JS bundle.
