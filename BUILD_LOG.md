# Build Log

Phase-by-phase narrative of what happened during the autonomous build.
Newest entries on top. Each entry: timestamp · phase · what changed · any incidents.

---

## 2026-05-17 · Phase 0 — Brainstorm & Spec

- Read user's hand-drawn workflow sketch + original `ResearchApp_BuildPlan.md`.
- Locked operating constraints: local SSD storage, SQLite, single-user with multi-user-ready schema, Gemini default AI, voice-to-text dropped, autonomous Phase 1→8, pause before 9.
- Wrote design spec → `docs/superpowers/specs/2026-05-17-research-manuscript-assistant-design.md`.
- Added §6.2 robustness layer: Gemini model resolution chain + retry + safety-filter tuning + optional cross-provider failover.
- Initialised git repo, committed spec + source material.
- Smoke-tested Chrome DevTools MCP — works, no permission prompts needed.
- Created tracking files: BUILD_LOG, POLISH, DEFERRED, DECISIONS, QUESTIONS.

Next: write Phase 1 implementation plan via `superpowers:writing-plans`, then execute.

---

## 2026-05-17 · Phase 1 — Foundation & Scaffold ✅ COMPLETE

**Tag:** `phase-1`
**Commits:** ~17 atomic commits, plan in `docs/superpowers/plans/2026-05-17-phase-1-foundation.md`

**What's running**

- `apps/web` — React 19 + TS + Vite + Tailwind 3 + shadcn (13 primitives) + Framer Motion + React Router 6 + TanStack Query + RHF + zod + Lucide. Bound to `127.0.0.1:5173`.
- `apps/api` — FastAPI + SQLAlchemy 2.0 async + aiosqlite + Alembic + Pydantic Settings. Bound to `127.0.0.1:8787`. Python 3.12 in `apps/api/.venv`.
- SQLite DB at `data/research.db`. Alembic baseline migration `0001_initial_projects` applied.
- `.env` at repo root with Gemini key, absolute SQLITE_URL. CORS allows :5173.

**Acceptance bar**

- [x] `/health` returns `{status:"ok", db_ok:true, gemini:{ok:true}}`
- [x] All 7 routes navigable, no console errors (only React Router v7 future-flag warnings — POLISH'd)
- [x] Backend test sweep: 14/14 pass (settings 2, projects repo 5, health 1, projects routes 6)
- [x] Frontend typecheck clean
- [x] Create project in UI → SQLite write → reload → project persists ✅ verified via chrome-devtools-mcp
- [x] Settings page reads live `/health` and renders provider statuses

**Incidents handled inline**

1. `npm install` at root accidentally polluted root package.json — uninstalled, moved to `apps/web`.
2. `shadcn init` had an interactive prompt that couldn't be bypassed by flags — wrote `components.json` manually and ran `shadcn add` (which works without re-init).
3. Tremor 3 pins React 18; React 19 in our stack. Deferred Tremor install to Phase 6 (logged in `DECISIONS.md`).
4. Alembic relative DB path resolved to `apps/data/` instead of repo root. Fixed `env.py` to compute absolute path from `parents[3]`.
5. Production SQLITE_URL used relative path; uvicorn from `apps/api/` resolved it wrong. Switched `.env` to absolute path.
6. `class-variance-authority` missing — shadcn Button required it but it wasn't auto-installed. Added manually.

**Open items captured**

- `POLISH.md`: mobile hamburger nav (high — fix before Phase 2 closes), RR v7 flag warnings (low), card click target (low).
- `DECISIONS.md`: 5 ADRs total — SQLite local-first, two-process monorepo, model resolution chain, percentage coords for highlights, Tremor deferred.
- `QUESTIONS.md`: empty (no judgment calls needed yet).
- `DEFERRED.md`: spec-decided deferrals only.

**Next:** Phase 2 — Library module (file upload, Gemini citation extraction, CrossRef fallback, metadata confirmation, list/search/filter/dedup).

---
