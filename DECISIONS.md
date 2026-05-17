# Decisions Log

Non-obvious architectural / library / design choices made during the build.
Lightweight Architecture Decision Records: what was picked, what was rejected,
why. So future-me (or future-you) understands why the codebase looks the way
it does without git-blaming every line.

Format:

```
## YYYY-MM-DD — Decision title
**Context:** What was being decided and why it mattered.
**Choice:** What I picked.
**Rejected:** Alternatives considered.
**Reason:** Why this won.
```

---

## 2026-05-17 — Local SQLite over Supabase cloud (v1)

**Context:** User chose "Local-only Supabase via Docker" initially, but Docker isn't installed and user prefers their SSD as the backend with cloud migration later.
**Choice:** SQLite via SQLAlchemy 2.0 async + aiosqlite, with repository/storage adapters for future cloud move.
**Rejected:** (a) install Docker for Supabase local stack — adds 4GB RAM + slow on Intel Mac; (b) Postgres via Homebrew — needs daemon management; (c) Supabase cloud free tier — would work but user prefers local-first.
**Reason:** Zero-install. Single file. SQLAlchemy code runs against Postgres later with one URL change. Multi-user-ready schema (every table has `user_id`) means migration is wiring, not rewriting.

## 2026-05-17 — Two-process monorepo (FastAPI + Vite)

**Context:** Backend needs scipy/lifelines/pingouin (Python-only). Frontend is React. Where to draw the line.
**Choice:** Separate apps/api (FastAPI on :8787) and apps/web (Vite on :5173) in a monorepo. Boot both with `concurrently`.
**Rejected:** (a) Supabase Edge Functions in Deno/TS — scientific libs don't exist there, hybrid gets messy; (b) Electron with embedded Python — defers web value, harder to dev.
**Reason:** Python in its native habitat. Clear separation. Web runs as a real web app today, Electron wraps it later.

## 2026-05-17 — Model-resolution chain over hardcoded Gemini model

**Context:** User reported Gemini Flash sometimes "doesn't work" — deprecated model names, 429s, 503s, safety-filter false-positives.
**Choice:** `GEMINI_MODEL_CHAIN` ordered list, filtered at startup against `list_models()`. Persistent 404 demotes the active model and promotes the next chain member. 3× exponential backoff on transient errors.
**Rejected:** Single pinned model string in env.
**Reason:** Pinned model = brittle. Chain self-heals across deprecations. Same shape applied to Claude + OpenAI adapters.

## 2026-05-17 — Defer Tremor install to Phase 6 (React 19 peer conflict)

**Context:** `@tremor/react@3.18.7` pins peer `react@^18.0.0`. Vite scaffolded React 19.2.6. npm refuses install.
**Choice:** Skip Tremor install in Phase 1. Revisit at Phase 6 (stats module) — install with `--legacy-peer-deps` (it works fine with React 19 in practice) or switch to a React-19-native chart lib (e.g. raw Recharts + custom table primitives).
**Rejected:** (a) Downgrade React to 18 — drops React 19 features the rest of the stack benefits from; (b) install Tremor now with --legacy-peer-deps — unused dep risk, easier to defer.
**Reason:** Tremor is unused until Phase 6. Delay = no immediate cost; gives Tremor team time to ship React 19 support; preserves option to swap lib.

## 2026-05-17 — Percentage coords for PDF highlights

**Context:** React-PDF pixel coordinates change with zoom and page reflow. Need highlights that re-render in the same logical place across sessions.
**Choice:** Store `{page, rects: [{x0_pct, y0_pct, x1_pct, y1_pct}]}` relative to PDF page dimensions. Recompute pixel rects on render.
**Rejected:** Absolute pixels at the zoom level at which the highlight was drawn.
**Reason:** Zoom invariance. Survives PDF reflow. Multi-line selections store an array of rects naturally.

---
