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

## 2026-05-17 · Phase 2 — Library Module ✅ COMPLETE

**Tag:** `phase-2`
**Commits:** ~14 atomic commits. Plan at `docs/superpowers/plans/2026-05-17-phase-2-library.md`.

**What's running now**

- **Adapters fully wired this phase**: `FileStorage` (LocalFs + signed-URL serving), `AIProvider` (Gemini with the §6.2 model resolution chain + retry/demote), CrossRef DOI lookup, rapidfuzz dedupe, PDF + DOCX text extraction.
- **Backend**: `Article` ORM + alembic 0002, ArticleRepository with filter/search/sort/dedupe, `/api/projects/{id}/articles/upload` orchestration (validate → save → extract → AI → CrossRef → dedup → DB), full CRUD, `/files/{token}` HMAC-served file route.
- **Frontend**: real `LibraryPage` (replaces Phase 1 stub) with project gate, `UploadZone` (react-dropzone), `MetadataConfirmDialog` (RHF + zod), `ArticleFilters` with debounced search, `ArticleListItem` with status-colored badges. Active-project Zustand store (localStorage-persisted). `ProjectCard` navigates to Library and sets active project.
- **POLISH carry-over resolved**: mobile nav drawer (P2-T1) — shadcn Sheet hamburger replaces hidden sidebar on `<md`.

**Acceptance bar (spec §7 Phase 2)**

- [x] Drag-and-drop PDF → ~7s Gemini extraction → confirm dialog with all 9 fields pre-filled correctly → save → article in list (verified live via chrome-devtools-mcp with a real generated research PDF; every field came back accurate including DOI)
- [x] Same PDF re-uploaded → amber "Possible duplicate of: …" warning rendered on upload row (verified in browser; backend regression test for multi-duplicate case)
- [x] Search "posterior" → article matches; search "no-such-term" → empty state
- [x] All 14 Phase 1 tests still pass + **70 new Phase 2 tests** = 84/84 backend pass
- [x] Frontend clean typecheck
- [x] `/health` reports live `active_model: "gemini-2.5-flash"` (chain resolved against Google's real `list_models()` at first call)
- [x] `/security-review` passed after fixes (all HIGH + MED resolved, see below)

**Live verification highlights**

The model returned for the real PDF:

```json
{
  "title": "Anterior vs Posterior Approach in Total Hip Arthroplasty: A Prospective Cohort Study",
  "authors": ["Inayat Choudhary", "Sarah Johnson"],
  "journal": "Journal of Bone and Joint Surgery",
  "year": 2024, "volume": "106", "issue": "11", "pages": "1245-1253",
  "doi": "10.2106/JBJS.24.00123"
}
```

Every field accurate.

**Security review (`/security-review` pass on file upload + AI integration)**

Found 2 HIGH + 6 MED + 3 LOW. All HIGH and MED fixed inline in this phase:

- **HIGH**: `api_signing_secret` placeholder default — now auto-generates a 48-byte url-safe random secret on first boot, persists to `data/.signing_secret` with `chmod 0600`.
- **HIGH**: Path-traversal guard switched from `str.startswith` to `Path.is_relative_to` (defends macOS case-insensitive FS + prefix siblings).
- **MED**: `/files/{token}` no longer echoes exception messages (generic responses, full detail in server logs).
- **MED**: `verify_token` catches missing payload keys explicitly → TokenInvalid (regression test added).
- **MED**: DOCX parser enforces 200 MB uncompressed cap (zip-bomb guard via `ZipInfo.file_size` sum).
- **MED**: Extraction prompt explicitly marks article text as untrusted data, tells the model to ignore embedded instructions.
- **MED**: CORS narrowed from `*` methods/headers to the actual surface.
- **MED**: Upload route returns extraction error CLASS only; full detail in server logs.
- **LOW**: CrossRef DOI percent-encoded to prevent URL injection. 413/415 message disclosure logged as accepted local-first risk in POLISH.

**Incidents handled inline**

1. shadcn CLI created `@/components/ui/sheet.tsx` and `@/components/ui/dropdown-menu.tsx` as literal directories instead of resolving the alias — wrote files manually, fixed by restoring `paths` to root `tsconfig.json` with `ignoreDeprecations`.
2. libmagic reports `application/octet-stream` for DOCX on this libmagic version → switched detection to magic-byte sniffing (`%PDF-` and `PK\x03\x04` + `[Content_Types].xml` check).
3. `find_duplicate` used `scalar_one_or_none()` and crashed `MultipleResultsFound` when 2+ rows shared a DOI — switched to `.limit(1)`. The bug surfaced because the dedupe-still-creates-the-row policy left duplicates in DB across upload cycles. Regression test added.
4. react-dropzone hidden input didn't fire `change` on re-selection of the same file — fixed by resetting `e.target.value` in the input's onClick.
5. `LocalFsStorage`'s `signing_secret` ≠ `Settings.api_signing_secret` in tests after the random-secret feature was added — fixed by only auto-replacing the placeholder, not arbitrary user-provided secrets.

**Test counts**

- Backend: 84 pass (was 14 after Phase 1, +70 in Phase 2)
- New test files: test_local_fs_storage, test_signed_urls, test_model_chain, test_gemini_provider, test_crossref, test_dedupe, test_article_repository, test_pdf_text, test_files_route, test_articles_route

**Open items captured**

- `POLISH.md`: 1 new low (413/415 cap disclosure)
- `DECISIONS.md`: unchanged this phase
- `QUESTIONS.md`: still empty
- `DEFERRED.md`: `google-generativeai` → `google.genai` migration

**Next:** Phase 3 — PDF reader & annotation engine. The hardest phase technically (React-PDF + canvas overlay + percentage-based coordinates).

---
