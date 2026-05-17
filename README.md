# Research Manuscript Assistant

Local-first web app for medical researchers (initially orthopaedics) to write manuscripts. Combines library management, colour-coded PDF annotation, AI-assisted drafting grounded in source material, statistical analysis, and systematic review tooling.

## Quick start

```bash
npm install                           # one-time, root
cd apps/web && npm install && cd ../..  # one-time, frontend deps
bash scripts/init-db.sh               # one-time, run DB migrations
npm run dev                           # boots web (:5173) + api (:8787)
```

Then open <http://127.0.0.1:5173>.

## Structure

- `apps/web` — React + Vite + TS + Tailwind + shadcn
- `apps/api` — FastAPI + SQLAlchemy + SQLite
- `data/` — local SQLite DB and uploaded files (gitignored)
- `docs/superpowers/specs/` — design specs
- `docs/superpowers/plans/` — phased implementation plans

## Tracking files

- `BUILD_LOG.md` — narrative of each phase
- `POLISH.md` — UX/visual nits to revisit
- `DEFERRED.md` — features punted past v1
- `DECISIONS.md` — lightweight ADRs
- `QUESTIONS.md` — open questions with chosen defaults

## Environment

Copy `.env.example` → `.env` and fill in your API keys. Only Gemini is needed by default.
