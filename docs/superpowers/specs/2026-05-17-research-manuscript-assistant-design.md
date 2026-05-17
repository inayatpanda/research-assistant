# Research Manuscript Assistant — Design Spec

**Author:** inayatc2002@gmail.com (orthopaedic researcher) + Claude
**Date:** 2026-05-17
**Status:** Draft for user review

---

## 1. Purpose

A web + desktop application for medical researchers (initially orthopaedics) to streamline writing research articles. Combines library management, colour-coded PDF annotation, AI-assisted drafting grounded in user annotations, statistical analysis, and systematic review tooling around a single manuscript workflow.

**Core philosophy:** AI assists, never replaces. Every AI output is grounded in source material the user has already read and annotated, and every AI block is clearly labelled with Accept / Edit / Reject controls. The AI never invents citations — citations always come from the library database.

---

## 2. Operating constraints (decided in brainstorming)

| Decision | Choice | Rationale |
|---|---|---|
| Storage backend | Local SSD (`./data/`) with adapter for future Supabase migration | User wants local-first now, cloud later |
| Database | SQLite via SQLAlchemy 2.0 async + aiosqlite | Zero-install; same code runs against Postgres later |
| Auth | Single-user with hardcoded `user_id = "local-user"` | Multi-user schema-ready (every table has `user_id`), real auth deferred |
| AI provider | Gemini 1.5 Flash by default (user has key); Claude / GPT-4o adapters built but untested live | Free tier covers dev; provider-agnostic adapter |
| Voice-to-text | Dropped from v1 | User opted out |
| Build pacing | Autonomous Phase 1 → 8; pause before Electron (Phase 9) | User choice |
| Scope | All 9 phases kept | User choice |
| Backend deploy | Deferred — runs locally for now | User choice |
| Git | Local-only repo initially, GitHub push allowed later | User choice |
| Responsive | Mobile-responsive shell from day 1, with explicit module-by-module support tiers | See §10 |

---

## 3. Architecture

### 3.1 Topology

Monorepo, two long-running processes during development, one combined production target later.

```
~/Desktop/Research-assistant/
├── apps/
│   ├── web/                React + TypeScript + Vite + Tailwind + shadcn
│   │   └── dev: http://127.0.0.1:5173
│   └── api/                FastAPI (Python 3.12)
│       └── dev: http://127.0.0.1:8787
├── packages/
│   └── shared-types/       TS types generated from Pydantic schemas (codegen)
├── data/                   LOCAL SSD STORE (gitignored)
│   ├── research.db         SQLite database
│   ├── files/              Uploaded source documents
│   │   └── {user_id}/{namespace}/{uuid}/{filename}
│   └── exports/            Generated .docx, charts, diagrams
├── docs/superpowers/specs/ Design specs (committed)
├── scripts/                start-dev.sh, init-db.sh, gen-types.sh
└── .env                    Secrets (gitignored). .env.example committed.
```

### 3.2 Data flow (canonical example: upload PDF)

1. User drops PDF onto web upload zone.
2. Frontend `POST /api/articles/upload` (multipart).
3. FastAPI validates (MIME, size cap, no path traversal), then calls `storage.save(...)` → `LocalFsStorage` writes to `./data/files/local-user/articles/{uuid}/paper.pdf` and returns a `StorageRef`.
4. FastAPI calls `ai.extract_citation(pdf_bytes)` → `GeminiProvider` returns structured metadata.
5. If extraction confidence is low or DOI is present, fall back to CrossRef DOI lookup.
6. FastAPI calls `repo.articles.create(...)` → `SqliteArticleRepository` inserts row.
7. Returns full article object to frontend; UI shows metadata confirmation card (user can edit before final save).

### 3.3 Why two processes

Python owns: PDF parsing, statistical libraries (`scipy`, `lifelines`, `pingouin`, `plotly`), AI provider SDKs, Word export (`python-docx`). Browser-side cannot run these credibly.

Web owns: rendering, interaction, animation, TipTap, React-PDF view layer.

Single `npm run dev` script (`concurrently`) boots both. `npm run build` produces a Vite production bundle. The FastAPI server runs locally only in v1; containerisation and deploy are deferred per §2.

---

## 4. Adapter layer (the seams that make migration painless)

Every business path crosses one of three protocols. Implementations are swapped via DI based on `.env`. **Business logic never imports a vendor SDK directly.**

### 4.1 `AIProvider`

```python
class AIProvider(Protocol):
    async def extract_citation(self, pdf_bytes: bytes) -> CitationMetadata: ...
    async def summarise(self, text: str, max_sentences: int = 2) -> str: ...
    async def generate_draft(self, ctx: DraftContext) -> str: ...
    async def interpret_result(self, test: str, output: dict) -> str: ...
    async def assist_writing(self, text: str, action: WritingAction) -> str: ...
```

Implementations: `GeminiProvider` (default), `ClaudeProvider`, `OpenAIProvider`.
Per-project selection stored in `projects.ai_provider`. API keys live in `.env`, never in DB. **Anti-hallucination:** every text-generating method receives the user's highlighted source text + paraphrase as required input; prompt templates explicitly forbid invented citations.

### 4.2 `FileStorage`

```python
class FileStorage(Protocol):
    async def save(self, user_id: str, namespace: str, filename: str,
                   data: bytes) -> StorageRef: ...
    async def read(self, ref: StorageRef) -> bytes: ...
    async def delete(self, ref: StorageRef) -> None: ...
    async def signed_url(self, ref: StorageRef, expires_in: int = 3600) -> str: ...

@dataclass(frozen=True)
class StorageRef:
    backend: str   # "local" | "supabase"
    key: str
```

`LocalFsStorage` (v1) writes under `./data/files/`. `signed_url()` returns a HMAC-signed short-lived URL served by `GET /files/{token}` — frontend never reads disk directly.
`SupabaseStorage` (future) — same interface, calls `supabase.storage.from_('research-files')`.

### 4.3 `Repository`

One protocol per aggregate (`ArticleRepository`, `ProjectRepository`, `HighlightRepository`, `NoteRepository`, `SectionRepository`, `CitationRepository`, `RiskOfBiasRepository`, `StatAnalysisRepository`, `PrismaFlowRepository`, `PicoRepository`, `ScreeningRepository`, `AbbreviationRepository`).

Every method takes `user_id` and includes it in the WHERE clause. **No row is ever returned without proven ownership.** This contract is enforced now even with one user, so multi-tenancy later is wiring not refactoring.

Implementations: `Sqlite*Repository` (v1) uses SQLAlchemy 2.0 async. `Postgres*Repository` / `Supabase*Repository` reuse most code (Alembic migrations target both; JSONB replaces JSON1 functions in a thin shim).

### 4.4 Dependency injection

```python
def build_container() -> Container:
    settings = Settings()
    return Container(
        ai=provider_factory(settings.ai_provider_default),
        storage=storage_factory(settings.storage_backend),
        repos=repo_factory(settings.sqlite_url),
    )
```

Routes depend on the container via FastAPI `Depends()`. Tests substitute fakes for all three layers — no live Gemini, disk, or DB in unit tests.

### 4.5 Cloud migration playbook (frozen contract)

When moving to Supabase later:

1. Add `SupabaseStorage` (implements `FileStorage`).
2. Add Supabase or Postgres repository implementations (or keep SQLAlchemy and just change the URL).
3. Flip `.env`: `STORAGE_BACKEND=supabase`, `SQLITE_URL → DATABASE_URL=postgres://...`.
4. Run `scripts/migrate_to_supabase.py` (delivered in v1, unused) — copies SQLite rows + storage files to Supabase.
5. **Zero UI changes. Zero business-logic changes.**

---

## 5. Data model

### 5.1 Conventions

- IDs: `TEXT` UUIDv4 hex (SQLite has no native UUID; same string format works on Postgres).
- Timestamps: `TEXT` ISO-8601 with `Z` suffix (SQLite has no native `TIMESTAMPTZ`).
- JSON columns: SQLite JSON1 (`bounding_coords`, `content`, `scores`, `result`, `chart_data`, `variables`, `excluded_reasons`). On Postgres these become JSONB.
- Arrays (e.g. `authors`): `JSON` arrays in SQLite, `TEXT[]` on Postgres.
- Foreign keys: every FK declared with `ON DELETE CASCADE`. Connections execute `PRAGMA foreign_keys = ON`.
- `user_id TEXT NOT NULL` on every table. Default value in v1: `"local-user"`.

### 5.2 Tables

**Core (matching the user-provided Supabase schema):**

- `projects` — title, study_type, citation_style, ai_provider, target_journal, prospero_number, clinicaltrials_number, user_id, created_at, updated_at
- `articles` — bibliographic metadata (title, authors JSON array, journal, year, volume, issue, pages, doi), file_ref (JSON `{backend, key}`), file_type, study_design, review_status, exclusion_reason, conflict_of_interest, project_id, user_id, created_at
- `highlights` — article_id, page_number, selected_text, colour, section, bounding_coords (JSON array of page-relative rects), user_note, ai_summary, sort_order, user_id, created_at
- `article_notes` — article_id, content, user_id, created_at, updated_at
- `manuscript_sections` — project_id, section_name, content (JSON, TipTap document), word_count, user_id, updated_at
- `citations` — project_id, article_id, citation_number, user_id, created_at — `UNIQUE(project_id, citation_number)`
- `risk_of_bias` — article_id, tool, scores (JSON), total_score, overall_risk, user_id, created_at
- `statistical_analyses` — project_id, test_name, variables (JSON), result (JSON), chart_data (JSON), ai_interpretation, user_id, created_at

**Additions needed for Phases 5 & 7 that were not in the original schema:**

- `prisma_flow` — project_id, identified_n, screened_n, eligible_n, included_n, excluded_reasons (JSON), user_id, updated_at
- `pico` — project_id, population, intervention, comparison, outcome, user_id, updated_at
- `screening_decisions` — article_id, decision (`include` | `exclude` | `unsure`), reason, decided_at, user_id
- `abbreviations` — project_id, short_form, long_form, user_id, created_at

### 5.3 Indexes

- `(user_id, project_id)` on every per-project table.
- `(article_id, page_number)` on `highlights`.
- `(doi)` on `articles` for duplicate lookup.
- `(project_id, citation_number)` unique on `citations`.

### 5.4 Migrations

Alembic in `apps/api/migrations/`. First migration generates the full schema. `scripts/init_db.sh` runs `alembic upgrade head` against the SQLite file — idempotent. Same migrations are designed to run against Postgres for the future cloud move.

### 5.5 Identity invariant

Every query is scoped by `user_id`. Even though only `local-user` exists in v1, all repository methods enforce this filter. Repository tests assert that a row created by user A is invisible to user B. This protects against accidental data leaks the day multi-user is enabled.

---

## 6. AI integration & anti-hallucination

### 6.1 Adapter rules

- Every AI call goes through `AIProvider` — no direct SDK access from routes or services.
- All prompt templates live in `apps/api/services/ai/prompts/` as named, versioned files.
- **Source-grounding rule:** every generation method requires the user's actual highlighted text + paraphrase as input. Prompts include the instruction: *"Use only the provided source text. Do not invent facts, citations, or numerical values. If the source is insufficient, respond with 'INSUFFICIENT_SOURCE'."*
- AI outputs are wrapped in an `<AISuggestionBlock state="pending|accepted|edited|rejected" />` with Accept / Edit / Reject controls. Until accepted, the content is visually marked (violet ring, "AI Suggested" badge) and cannot be exported.
- Per-call telemetry (provider, tokens, latency, success/error) logged to `apps/api/logs/ai_calls.jsonl` (append-only file, gitignored).
- API keys: stored in `.env` only, never in DB, never echoed in UI. Settings page can read from `.env` (via API) and write back. Keys never leave the machine except to the chosen provider.

### 6.2 Robustness — handling Gemini (and any provider) flakiness

Gemini specifically has a track record of: model-name deprecations (`gemini-1.5-flash` → `-002` → `-latest`), free-tier rate limits (15 RPM / 1500 RPD), 503 overloads, and safety-filter false-positives on medical content. The adapter handles all four cases.

**Model resolution chain.** No hardcoded single model. The provider holds an ordered list:

```python
GEMINI_MODEL_CHAIN = [
    "gemini-2.5-flash",          # newest, fastest, free tier
    "gemini-2.0-flash",          # stable fallback
    "gemini-1.5-flash-latest",   # legacy alias
    "gemini-1.5-flash-002",      # legacy pinned
]
```

On startup, `genai.list_models()` filters this to models the current API key can actually call. The first survivor becomes `active_model`; the rest stay as a queue.

**Per-call retry policy.** For 429 / 503 / transient network errors: 3× exponential backoff with jitter (≈1s, 2s, 4s). For persistent 404 on `active_model`: demote it, promote the next chain member, retry once. If the chain is exhausted, return a structured `AIProviderUnavailable` error.

**UI behaviour on exhaustion.** A clean toast: *"Gemini is temporarily unavailable. Retry in a few minutes, or switch provider in Settings."* The retry button on every AI block lets the user try again without losing context.

**Safety filters tuned for medical content.** Default Gemini safety thresholds frequently block medical text (drug names, anatomy, symptoms). The adapter sets `safety_settings = BLOCK_NONE` for all four categories on summarisation/drafting calls. Citation extraction stays at default thresholds.

**Optional cross-provider failover.** A Settings toggle, off by default: when Gemini's chain is exhausted, auto-failover to Claude (if key present) or OpenAI (if key present). Off by default because users care about cost surprise.

**Startup health check.** `GET /health` returns per-provider status:

```json
{
  "ai_providers": {
    "gemini": { "ok": true, "active_model": "gemini-2.5-flash" },
    "claude": { "ok": false, "reason": "no key" },
    "openai": { "ok": false, "reason": "no key" }
  }
}
```

The topbar shows a red dot if the active provider is down — the user knows before wasting time annotating.

### 6.3 Same robustness shape for other providers

The Claude and OpenAI adapters get the same treatment in miniature: model chain + retry + failure surface. Pinned defaults:

- Claude: `claude-opus-4-7` → `claude-sonnet-4-6` → `claude-haiku-4-5`
- OpenAI: `gpt-4o` → `gpt-4o-mini`

This means **a model deprecation never breaks the app** — the chain just demotes the broken entry.

---

## 7. Module breakdown & phase plan

Each phase has a **deliverable**, an **acceptance bar**, **skills invoked**, and **risks + mitigation**.

### Phase 1 — Foundation & scaffold

**Deliverable**
- Monorepo bootstrapped with `apps/web` and `apps/api`.
- `npm run dev` starts both servers.
- Tailwind + shadcn primitives installed (see §9.3).
- Sidebar shell with all 6 nav routes, dark `#0F1117` background, Framer Motion slide on mount.
- Dashboard route: project list + create-project modal (title + study type selector).
- Settings route: AI provider selector, key fields, citation-style selector.
- SQLite + Alembic baseline migration. `scripts/init_db.sh` works.

**Acceptance**
- Create a project → persists → reload → still there.
- All routes navigable, no console errors.
- Backend `/health` returns 200, returns `{ai_provider, storage_backend, db_ok}`.

**Skills:** `ui-ux-pro-max`, `frontend-design`, `chrome-devtools-mcp`, `/review`.

**Risks**
- Python 3.14 default — install 3.12 via Homebrew, pin in `apps/api/.venv`.
- Async SQLAlchemy + aiosqlite quirks — smoke test on first migration.

---

### Phase 2 — Library module

**Deliverable**
- Drag-and-drop + file picker upload (PDF, .docx).
- Gemini citation extraction on upload (title, authors, journal, year, volume, issue, pages, DOI).
- CrossRef fallback when DOI present or extraction confidence low.
- Metadata confirmation modal (user edits before final save).
- Library list: sortable (author/year/title), text search, filter by review_status, study_design.
- Duplicate detection: DOI exact match or title similarity ≥ 90% (`rapidfuzz`).
- Per-article fields: study design tag, review status, exclusion reason, COI notes.

**Acceptance**
- Real PDF: upload → extraction within ~10s → user confirms → list updates.
- Same PDF re-uploaded → duplicate warning.
- Search by author works.

**Skills:** `ui-ux-pro-max`, `frontend-design`, `/security-review` (file upload), `/review`.

**Risks**
- Gemini extraction quality on scanned PDFs (no OCR in v1). Mitigation: surface CrossRef DOI lookup prominently; allow manual paste; OCR is a v2 feature.

---

### Phase 3 — PDF reader & annotation engine

**Deliverable**
- React-PDF full-page viewer with toolbar (4-colour picker, hand tool, zoom, page nav).
- Text selection → colour click → highlight drawn on canvas overlay AND saved to DB with **page-relative percentage coords** (survives zoom + reflow): `{page, rects: [{x0_pct, y0_pct, x1_pct, y1_pct}]}`.
- Inline note panel slides in on highlight click (`paraphrase` field + `AI Summarise` button).
- Right rail: general article notes with autosave (debounced 800ms).
- Reopen PDF → all highlights re-render exactly where they were.
- `highlightBloom` Framer Motion animation on new highlight.

**Acceptance**
- Highlight a sentence → close → reopen → highlight is in identical place at any zoom level.
- AI Summarise returns 1–2 sentences grounded in selected text.
- Multi-line selection persists correctly.

**Skills:** `ui-ux-pro-max`, `frontend-design`, `chrome-devtools-mcp` (pixel-perfect verification), `/review`.

**Risks**
- React-PDF text-layer coordinate stability — solved by storing percentages relative to PDF page dimensions, recomputing pixel rects from current page size on render.
- This is the technically hardest phase; ship a vertical slice (one-line single-rect highlight) first, then multi-line.

---

### Phase 4 — Compilation module

**Deliverable**
- Four colour-tabbed views (Introduction / Methodology / Results / Discussion).
- Each pulls highlights of that colour from all articles in the project.
- Cards: highlighted text | user paraphrase | citation `(Author et al., Year)`.
- Drag-and-drop reorder (`dnd-kit`) persists `sort_order`.
- Per-card "Generate" → AI drafts a sentence from highlight + paraphrase + section context.
- Section "Generate Draft" → AI drafts a full paragraph from all cards.
- Every AI output: `<AISuggestionBlock>` with Accept / Edit / Reject. Accept pushes content into `manuscript_sections`.
- Free-text note insertion between cards.

**Acceptance**
- Highlight 3 things across 2 PDFs (all red) → Compile/Intro shows 3 cards with citations.
- Reorder → reload → order persists.
- Generate Section Draft → paragraph appears with violet AI badge → Accept → visible in Manuscript Editor.

**Skills:** `ui-ux-pro-max`, `frontend-design`, `/review`.

**Risks**
- Prompt quality — iterate in `apps/api/services/ai/prompts/`. Add a test that asserts generated text contains tokens from the source highlights (anti-hallucination probe).

---

### Phase 5 — Manuscript editor

**Deliverable**
- TipTap editor with 6 section tabs (Intro / Method / Results / Discussion / Abstract / Conclusion) + Final Manuscript tab (read-only concatenation).
- Floating bubble toolbar on selection: Improve / Shorten / Formalise / Add Transition (each → `AIProvider.assist_writing`).
- `@` opens citation popup — search project articles → insert numbered inline citation (Vancouver, default).
- Citation numbers auto-renumber as citations are added/removed/reordered.
- Word count per section + total.
- Abbreviation tracker: scans text on save, populates `abbreviations` table.
- Reference integrity panel: unused articles, unmatched in-text numbers, year mismatches.

**Acceptance**
- Type → select → Improve → diff modal → Accept replaces text.
- `@` → search → pick article → `[1]` appears. Add a citation before → `[1]` becomes `[2]`.
- Delete citation → bibliography count drops by one.
- Final Manuscript tab shows correct concatenation.

**Skills:** `ui-ux-pro-max`, `frontend-design`, `/review`.

**Risks**
- TipTap custom citation mark + node — ship minimum mark with `articleId` attr first, then add features.

---

### Phase 6 — Data & statistics module

**Deliverable**
- Excel upload (`.xlsx`) → pandas parse → editable Tremor data table.
- Auto-descriptive stats panel on upload (mean, SD, median, IQR, n, %).
- Study-type-aware Suggested Tests panel with plain-English explanations.
- Full test suite — all live, not stubbed:
  - Normality: Shapiro-Wilk, Kolmogorov-Smirnov
  - Comparisons: paired/independent t-test, Mann-Whitney, Wilcoxon, χ², ANOVA, Kruskal-Wallis
  - Regression: linear, logistic, Cox PH (`lifelines`)
  - Survival: Kaplan-Meier, log-rank
  - Correlation: Pearson, Spearman
  - Effect sizes: Cohen's d, OR, RR, HR with 95% CI
- Per-test variable selector → run → result (Tremor table + Plotly chart) → AI plain-English interpretation.
- Export: Word table (`python-docx`) + PNG/SVG chart.

**Acceptance**
- Upload real `.xlsx` → descriptives appear → run Independent t-test → p-value, CI, mean difference, box plot.
- Interpretation cites the actual p-value.
- Export PNG opens cleanly.

**Skills:** `ui-ux-pro-max`, `frontend-design`, `/security-review` (Excel parsing — disable formula execution, MIME check, size cap), `/review`.

**Risks**
- Heavy Python deps: scipy / lifelines / pingouin / plotly. Pin versions in `pyproject.toml`. Unit-test each statistical function against a known-answer fixture.

---

### Phase 7 — Systematic review module

**Activation:** when `study_type = 'Systematic Review'`. Sidebar gains an extra route.

**Deliverable**
1. **Search strategy** — per-database (PubMed/Embase/Cochrane/CINAHL/Web of Science) timestamped strings, exportable.
2. **PICO form** — Population / Intervention / Comparison / Outcome (rich text).
3. **PRISMA flow** — numeric inputs per stage → live SVG diagram → PNG/SVG export.
4. **Abstract screening queue** — paged list of `review_status = 'pending'` → show abstract → Include / Exclude / Unsure + reason → updates `screening_decisions` and `articles.review_status` and rolls up to PRISMA "Screened".
5. **Risk of bias** — auto-selects tool from `articles.study_design`:
   - MINORS (12 items, 0–2) for non-randomised studies
   - RoB 2 (5 domains) for RCTs
   - Newcastle-Ottawa for cohort/case-control
6. Summary risk-of-bias table — articles × domains, colour-coded low / moderate / high.
7. Data extraction form builder — fields defined once per project, filled per article.

**Acceptance**
- Switch project to Systematic Review → tab appears.
- Fill PRISMA → diagram updates live.
- Screen articles → PRISMA "Screened" count auto-updates.
- Score MINORS on one article → summary table populates the row.

**Skills:** `ui-ux-pro-max`, `frontend-design`, `/review`.

**Risks**
- Large surface area. Mitigation: vertical slice per tool first, polish iteratively.

---

### Phase 8 — Bibliography, export, polish (deploy deferred)

**Deliverable**
- Bibliography auto-built from cited articles via `citeproc-py` — Vancouver / APA / Harvard switchable.
- Full-manuscript Word export (`python-docx`): cover, headings, page numbers, inline citation numbers, bibliography, abbreviations list.
- Onboarding tour for first-time users.
- Empty states for every module (illustrations from Lucide compositions).
- Skeleton loaders on every async fetch.
- Final `/security-review`.
- **Deploy: deferred** (user kept everything local). Hook in `package.json` script for Vercel later.

**Acceptance**
- Export a real manuscript → opens in Word, correct numbering, complete bibliography matching citations, no broken refs.
- `/security-review` passes.

**Skills:** `ui-ux-pro-max`, `frontend-design`, `/review`, `/security-review`.

---

### Phase 9 — Electron desktop (paused; not in autonomous run)

**Deliverable**
- Electron shell wrapping Vite production build.
- Local filesystem access for PDF cache (replaces FastAPI signed-URL for local files).
- Context isolation, `nodeIntegration: false`, preload script with narrow IPC surface.
- App icon, splash screen.
- macOS `.dmg`, Windows `.exe` packaged.

**Skills:** `frontend-design` (Electron security patterns), `/review`, `/security-review`.

I will stop and check in with the user before starting Phase 9.

---

## 8. Per-phase rhythm

For every phase:

1. **Announce** the phase and concrete deliverables.
2. **Design**: invoke `ui-ux-pro-max` + `frontend-design` for new UI surfaces.
3. **Build**: TDD where it pays off (stats tests, citation renumbering, duplicate detection, anti-hallucination probe). UI changes verified in `chrome-devtools-mcp` before claiming done.
4. **Review**: `/review`. Phases 2, 6, 8 also `/security-review`.
5. **Verify**: invoke `superpowers:verification-before-completion` — run the actual command, paste actual output, no claiming green without evidence.
6. **Commit**: git commit with `phase-N` tag.
7. **Responsive check**: open dev server in three viewports (390×844, 820×1180, 1440×900) and verify intended behaviour at each.

---

## 9. UI shell, tokens, motion

### 9.1 App shell

Fixed dark sidebar 240px wide (`#0F1117`), 56px topbar, workspace fills the rest. Sidebar collapses to icon-rail < 1100px and to bottom-nav drawer < 768px (see §10). Topbar holds project switcher, command palette trigger (⌘K), settings cog.

### 9.2 Design tokens

Single source of truth: `apps/web/src/lib/tokens.ts`, exposed as Tailwind theme + CSS vars. No component picks colours or spacing from anywhere else.

**Highlight colours** — the visual centrepiece:

| Section | `solid` | `fill` (PDF paint) | `ring` (focus/hover) |
|---|---|---|---|
| Introduction | `#EF4444` | `rgba(239,68,68,0.22)` | `rgba(239,68,68,0.55)` |
| Methodology | `#3B82F6` | `rgba(59,130,246,0.22)` | `rgba(59,130,246,0.55)` |
| Results | `#22C55E` | `rgba(34,197,94,0.22)` | `rgba(34,197,94,0.55)` |
| Discussion | `#EAB308` | `rgba(234,179,8,0.22)` | `rgba(234,179,8,0.55)` |

**Accent / interactive:** `#2563EB`. Hover `#1D4ED8`. Tint `#EFF6FF`.

**AI suggestions:** violet `#7C3AED` family — never blue, so users always distinguish "this came from the model" from "primary action".

**Type:**
- UI: Inter Variable
- Manuscript editor (TipTap only): Source Serif 4 — the document being written should feel like a document
- Numerical output: JetBrains Mono — numbers align

**Spacing:** 4px base scale (`1=4, 2=8, 3=12, 4=16, 5=20, 6=24, 8=32, 10=40, 12=48, 16=64`).

**Radii:** `sm=6, md=8, lg=12, xl=16, pill=999`.

**Shadows:** `xs / sm / md / pop` — soft, near-black, 4–32px reach.

### 9.3 Component primitives (installed Phase 1, no custom forks)

shadcn/ui: `ScrollArea, Separator, Tabs, Sheet, Resizable, Button, Input, Textarea, Select, Checkbox, RadioGroup, Switch, Slider, Form, Dialog, AlertDialog, Popover, Tooltip, HoverCard, Command, DropdownMenu, ContextMenu, Toast, Card, Badge, Avatar, Progress, Skeleton`.

Bespoke components built on top:

- `<HighlightChip color="intro|method|results|discussion" />`
- `<AISuggestionBlock state="pending|accepted|edited|rejected" />`
- `<CitationInline articleId number />`
- `<StudyTypeBadge />`
- `<PRISMACell stage n />`
- `<StatTestCard />` (Tremor underneath)
- `<EmptyState illustration />`

### 9.4 Motion vocabulary

Single file `apps/web/src/lib/motion.ts`. Six named transitions; every animation calls one by name (no inline `duration: 0.3` anywhere).

| Name | Purpose | Spec |
|---|---|---|
| `pageEnter` | Route change | `opacity 0→1, y +4→0, 240ms, standard` |
| `cardEnter` | List/grid items | `stagger 30ms · opacity 0→1, y +6→0, 200ms` |
| `modalIn / modalOut` | Dialog / Sheet | `scale 0.96→1, opacity 0→1, 200ms expressive` |
| `highlightBloom` | New highlight on PDF | `fill 0→target, ring pulse 1×, 320ms expressive` |
| `aiSuggestionEnter` | AI block reveal | `opacity 0→1, y +8→0, soft violet ring fade, 320ms` |
| `skeletonShimmer` | Loading | `linear-gradient sweep 1400ms infinite linear` |

`prefers-reduced-motion`: durations collapse to 0; only opacity remains.

### 9.5 Density rules

- Sidebar nav: 14/20, weight 500
- Card title: 15/22, weight 600
- Body: 14/22, weight 400
- Manuscript text: 16/28, **serif**, weight 400
- Stat output: 13/20, **mono**
- Min tap target: 32px desktop, 44px touch

### 9.6 Accessibility floor

- 2px accent focus ring with 2px offset on every focusable; never removed.
- Contrast: AAA over all highlight `fill`s.
- Keyboard: ⌘K palette, ⌘N new project, arrow nav in sidebar, `/` focuses search.
- ARIA labels on every icon-only button. Live regions for streaming AI output.
- `chrome-devtools-mcp:a11y-debugging` pass per phase.

---

## 10. Responsive support tiers

Mobile-responsive shell from Phase 1, but explicit per-module reality — selecting precise PDF text on a 5-inch screen is bad UX whether we ship it or not.

| Module | Phone < 768 | Tablet 768–1280 | Desktop ≥ 1280 |
|---|---|---|---|
| Dashboard / project list | Full | Full | Full |
| Library list & search | Full | Full | Full |
| Abstract screening | Full (nice for triage) | Full | Full |
| PDF reader & highlighting | **Read-only** (view existing highlights) | Full (Apple Pencil supported) | Optimal |
| Compilation tabs | Read-only review | Full | Optimal |
| Manuscript editor | Quick edits + AI Improve only | Full | Optimal |
| Statistics | **Charts viewable only** | Partial | Optimal |
| Risk of bias / data extraction | View only | Full | Full |

**Implementation rules**

- Tailwind breakpoints: `sm 640 / md 768 / lg 1024 / xl 1280 / 2xl 1536`. Every module ships `md` + `lg` variants Phase 1.
- Sidebar: bottom-nav drawer < 768; icon-rail < 1100; full < 1280.
- Color picker becomes a Sheet (bottom drawer) on `<md`; Popover on `≥md`.
- PDF reader on tablet: pointer events distinguish stylus from finger (`pointer.pointerType === 'pen'`) — only pen-input drives highlighting on touch; finger pan/zoom only.
- Capability gates: modules not viable below their tier render a clean `<EmptyState>` with a "Best on tablet/desktop — open Library instead" CTA, not a broken UI.
- Per-phase verification at three viewports: 390×844, 820×1180, 1440×900.

**Explicitly NOT building**

- React Native app — Electron + responsive web covers desktop.
- PWA install prompts in v1 — easy to add later.
- Phone-optimised stats UI — desktop-tier feature.

---

## 11. Testing strategy

- **Python unit tests (`pytest`)**: every statistical function vs. a known-answer fixture; every repository method (fake user_id leak test); every prompt template (anti-hallucination probe — generated text must contain tokens from source highlights).
- **TypeScript unit tests (`vitest`)**: citation renumbering, coordinate transforms (page-rel ↔ pixel), duplicate detection scorer.
- **Component tests (`@testing-library/react`)**: `<AISuggestionBlock>` state machine, `<HighlightChip>` color contracts, citation popup search behaviour.
- **Integration tests (`pytest` + httpx `AsyncClient`)**: upload → extract → list → delete; highlight → reload → re-render rect equivalence.
- **Browser verification per phase** via `chrome-devtools-mcp`: load the page, run a real interaction, assert no console errors, screenshot.
- **Accessibility verification per phase** via `chrome-devtools-mcp:a11y-debugging`.
- **Playwright (as needed)** for flows that need scripted interaction (drag-drop reorder, multi-step compilation).

---

## 12. Security baseline

- API keys: `.env` only, never DB, never echoed. `.gitignore` covers `.env*`.
- File upload: MIME sniff (`python-magic`), size cap (50 MB default, configurable), filename normalised (no path traversal).
- Excel parsing: openpyxl with `data_only=True` (no formula evaluation).
- Signed-URL endpoint: HMAC, short TTL (1h default), single-use option.
- CORS: dev allows `localhost:5173`; production locked to specific origin.
- Electron (Phase 9): context isolation, `nodeIntegration: false`, narrow preload IPC.
- `/security-review` runs before Phase 2 ships, before Phase 6 ships, and before Phase 8 closes.

---

## 13. Out of scope (v1)

- Real authentication / multi-user (schema-ready, UI deferred).
- Cloud storage (adapter ready, implementation deferred).
- PubMed direct search import (v2 idea).
- OCR for scanned PDFs (v2 idea).
- Journal-specific submission checker (v2 idea).
- Collaboration mode / co-author annotations (v2 idea).
- Version history / snapshots (v2 idea).
- Mobile PDF highlighting on phones (deliberately not supported).
- Vercel deployment (deferred per user choice).
- Voice-to-text (user opted out).

---

## 14. Open risks & mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| React-PDF coordinate stability across zooms | High | High | Store percentage-based coords; vertical-slice single-line first |
| Python 3.14 lib incompat | Confirmed | Medium | Install Python 3.12 via Homebrew, pin in venv |
| Gemini extraction quality on scans | Medium | Medium | CrossRef fallback; manual paste fallback; OCR deferred |
| Stats library install size / cold start | Low | Medium | Pin versions; defer Vercel deploy entirely |
| TipTap custom citation extension scope | Medium | Medium | Ship minimum mark first, iterate |
| Prompt drift across providers (Gemini ↔ Claude ↔ GPT) | Medium | Medium | Per-provider prompt overrides; output normalisation in adapter |

---

## 15. Definition of done (v1)

The app is "done" when:

1. All 8 phases ship with their acceptance bars met.
2. Phase 9 ships separately after user check-in.
3. A real user can: create a Systematic Review project, upload 10 PDFs, annotate them across all 4 colours, see compiled cards, generate AI drafts, accept into manuscript, run a stats analysis on an uploaded Excel, complete PRISMA + RoB, export a Word manuscript with bibliography — without crashes, with all data persisted locally.
4. `/security-review` passes on the last phase before any future deploy.
5. The codebase is internally consistent: no inline magic numbers, no direct SDK calls outside adapters, no rows fetched without `user_id`.

---
