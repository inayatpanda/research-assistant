# Post-E2E Roadmap — Research Manuscript Assistant

Total scope: 16 items grouped into 7 mini-phases (~1 day each).

This roadmap covers all work remaining after mini-phases 7.5 / 8.5 / 8.6 / 8.7 and the comprehensive E2E test have landed. Phase 9 (Electron desktop packaging) remains paused.

Items are tagged BUG (regression of shipped behaviour — must fix) or NEW (new feature). The roadmap front-loads BUGs, then sequences NEW features by user-value per day.

| # | Item | Type | Mini-phase |
|---|------|------|------------|
| 14 | Bibliography alphabetical ordering (APA/Harvard) | BUG | 9 |
| 15 | Citation cluster consolidation | BUG | 9 |
| 13 | Cmd-F across all manuscript sections | NEW (UX) | 9 |
| 16 | Search inside manuscript + Cmd-G next | NEW (UX) | 9 |
| 1  | ICMJE structured front-matter | NEW | 10 |
| 2  | Manuscript version history + diff | NEW | 11 |
| 3  | Comments / margin notes (single-user) | NEW | 11 |
| 4  | Cover letter generator (AI) | NEW | 12 |
| 5  | Response-to-reviewers helper (AI) | NEW | 12 |
| 6  | Submission package (zip) | NEW | 12 |
| 7  | Sample-size + power calculator | NEW | 13 |
| 8  | Propensity-score matching | NEW | 13 |
| 9  | OLS residual / leverage / influence plots | NEW | 13 |
| 10 | GRADE certainty-of-evidence | NEW | 14 |
| 11 | PROSPERO registration helper | NEW | 14 |
| 12 | Living systematic-review auto-rerun | NEW (infra) | 15 |

---

## Sequence + Rationale

- **Mini-phase 9 — Citation/search correctness fixes:** Real bugs first. Bibliography wrong-ordering for APA/Harvard and missing citation clustering ship today; researchers will spot both during their first APA submission. Cmd-F across sections is a UX paper-cut bundled here because all four items touch the same surfaces (`citation_format.py`, `bibliography.py`, `ManuscriptEditor.tsx`).
- **Mini-phase 10 — ICMJE structured front-matter:** High-impact for journal submissions; almost every target journal requires structured authors+affiliations, conflict, funding, ethics. Largest schema-design lift in the roadmap, so it lands while context is fresh and before subsequent phases (cover letter, submission package) depend on it.
- **Mini-phase 11 — Version history + comments:** Unlocks the revision workflow (v1 → v2 → v3) plus marginalia during drafting. Sequenced after 10 because version snapshots must capture the new ICMJE fields.
- **Mini-phase 12 — Cover letter + response-to-reviewers + submission package:** Three AI-assisted helpers that complete the submission loop. Depends on 10 (ICMJE for cover letter author/affiliations) and 11 (version pinning per submission).
- **Mini-phase 13 — Statistics expansion:** Pre-study power calc, PSM, OLS diagnostic plots. Independent of the submission workflow track, so any agent could parallelise this if dispatched separately.
- **Mini-phase 14 — Systematic review polish:** GRADE + PROSPERO. Builds on existing Phase 7/7.5 review module.
- **Mini-phase 15 — Living review automation:** Last because it introduces a new infrastructure surface (scheduler/cron) and depends on the Phase 8.6 ingestion module being stable post-E2E.

Parallelisation opportunity: mini-phases 13 (stats), 14 (review polish), and the second half of 12 (submission package) have no shared files; if multiple agents are available they can run concurrently once 11 is in.

---

## Mini-phase 9 — Citation correctness + manuscript search

**Scope:** Two real bugs in the bibliography/citation pipeline plus the corresponding UX gap in the editor's Find. APA 7 + Harvard switch to alphabetical-by-first-author bibliography ordering (Vancouver/IEEE keep first-citation-of-appearance — this is a per-style numbering policy, not a sort everywhere). Citation tokens consolidate when they appear consecutively: `[1][2][3]` → `[1-3]` for Vancouver/IEEE numeric, `(Smith 2024; Patel 2022)` (single parens, semicolon-separated) for APA/Harvard author-year. Editor-side: Cmd-F opens a cross-section search panel that lists hits across all six manuscript sections (Abstract → Conclusion) with click-to-jump; Cmd-G moves to the next hit; Esc closes.

**Dependencies:** Phase 8.7 landed (figures/tables/journal templates) so `_html_walker` is stable. No new dependencies on 7.5 / 8.5 / 8.6.

**Items addressed:** #13 #14 #15 #16

**Files:** `apps/api/src/research_api/services/export/bibliography.py` (add `style`-aware ordering branch — alphabetical for APA/Harvard, first-occurrence for Vancouver/IEEE), `apps/api/src/research_api/services/citation_format.py` (new `consolidate_inline_clusters(html, style)` post-pass walking adjacent `<sup data-citation>` or token spans), `apps/api/tests/test_bibliography_ordering.py` (NEW), `apps/api/tests/test_citation_cluster.py` (NEW), `apps/web/src/components/manuscript/ManuscriptSearchPanel.tsx` (NEW), `apps/web/src/components/manuscript/ManuscriptEditor.tsx` (register Cmd-F handler, expose section→editor instance map up to a parent), `apps/web/src/routes/ManuscriptPage.tsx`.

**Tasks (rough count):** ~12.

**Tests delta:** +~14 backend, +~3 vitest.

**Security review:** light — string-rendering only, no new surfaces. Confirm cluster consolidator handles adversarial author-year strings (escaped parentheses) without breaking out of the citation span.

**Decisions needed:** Per-style numbering policy — confirm that APA/Harvard renumbering after alphabetical sort does NOT renumber inline citations (they stay author-year). Also: cluster grouping window — adjacent tokens with only whitespace between them, or also across short connectors like `, `?

---

## Mini-phase 10 — ICMJE structured front-matter

**Scope:** Promote the loose "authors string" surface to a structured first-class data model: authors with affiliations (many-to-many), ORCID per author, CRediT contribution matrix (14-role checklist per author), conflict-of-interest declarations (per author, free-text plus boolean "none-to-declare"), funding statement (free-text + structured funder list with grant IDs), ethics statement (IRB name + approval number + consent statement), and structured abstract sections (Background / Methods / Results / Conclusions) replacing the freeform Abstract. All persisted on the project, included in DOCX/PDF export front-matter, and surfaced to downstream cover-letter / submission-package generators.

**Dependencies:** None hard — but cover letter (#4) and submission package (#6) consume this output, so 10 must precede 12.

**Items addressed:** #1

**Files:** `apps/api/alembic/versions/0011_icmje_frontmatter.py` (NEW — 4 new tables: `authors`, `author_affiliations`, `affiliations`, `contributions`; plus `project_frontmatter` column or sibling table for funding/ethics/structured-abstract JSON), `apps/api/src/research_api/db/models.py`, `apps/api/src/research_api/schemas/frontmatter.py` (NEW), `apps/api/src/research_api/repositories/frontmatter.py` (NEW), `apps/api/src/research_api/routes/frontmatter.py` (NEW: 8 endpoints — authors CRUD + reorder, affiliations CRUD, frontmatter PATCH), `apps/api/src/research_api/services/export/docx_export.py` (modify — emit ICMJE title page), `apps/api/src/research_api/services/export/pdf_export.py`, `apps/web/src/components/frontmatter/AuthorsEditor.tsx` (NEW), `apps/web/src/components/frontmatter/AffiliationsEditor.tsx` (NEW), `apps/web/src/components/frontmatter/ContributionsMatrix.tsx` (NEW), `apps/web/src/components/frontmatter/EthicsFundingForm.tsx` (NEW), `apps/web/src/components/frontmatter/StructuredAbstract.tsx` (NEW — replaces existing freeform Abstract section when project opts in), `apps/web/src/routes/ManuscriptPage.tsx`.

**Tasks (rough count):** ~22 (largest mini-phase in the roadmap).

**Tests delta:** +~30 backend, +~5 vitest.

**Security review:** medium. New free-text fields (affiliation strings, funding statements) are user-supplied but rendered into DOCX/PDF — `html.escape` and DOMPurify treatment must be confirmed. Ensure `author_id` always scoped to `user_id` + `project_id` in repository queries.

**Decisions needed (significant design):**
- Author-affiliation cardinality: many-to-many (one author can have 2+ affiliations) — confirmed by ICMJE.
- CRediT role list: do we ship all 14 roles or a curated subset? Recommend all 14.
- Backwards compat: existing projects have a freeform Abstract section. New schema makes "structured abstract" opt-in per project so existing E2E projects don't break.
- ORCID validation: pattern match + checksum, but no API call to orcid.org for v1.

---

## Mini-phase 11 — Version snapshots + margin comments

**Scope:** Two related collaboration-adjacent features. (a) Manuscript version history: a `manuscript_snapshots` table captures a full point-in-time copy of every section's HTML plus ICMJE front-matter; user creates named snapshots ("v1 – initial submission", "v2 – post-review"); diff viewer renders side-by-side HTML diff (via a JS diff lib like `diff-match-patch`) with additions/removals highlighted. (b) Margin comments: TipTap mark or decoration anchoring an authored note to a text range, rendered in a right-rail with "Resolved" toggle. Single-user only — no permissions, no notifications. Multi-user collaboration is explicitly deferred.

**Dependencies:** Mini-phase 10 (snapshots must capture ICMJE rows).

**Items addressed:** #2 #3

**Files:** `apps/api/alembic/versions/0012_snapshots_comments.py` (NEW — `manuscript_snapshots` table with JSON blob of all sections + frontmatter; `manuscript_comments` table with section_name + anchor_start + anchor_end + body + resolved + user_id), `apps/api/src/research_api/db/models.py`, `apps/api/src/research_api/repositories/snapshots.py` (NEW), `apps/api/src/research_api/repositories/comments.py` (NEW), `apps/api/src/research_api/routes/snapshots.py` (NEW: list/create/get/delete/diff), `apps/api/src/research_api/routes/comments.py` (NEW: list/create/patch/delete/resolve), `apps/web/src/components/manuscript/VersionPanel.tsx` (NEW), `apps/web/src/components/manuscript/VersionDiffView.tsx` (NEW), `apps/web/src/components/manuscript/CommentsRail.tsx` (NEW), `apps/web/src/lib/tiptap/extensions/CommentMark.tsx` (NEW — TipTap mark with `commentId` attr), `apps/web/src/components/manuscript/ManuscriptEditor.tsx`.

**Tasks (rough count):** ~16.

**Tests delta:** +~20 backend, +~4 vitest.

**Security review:** medium. Diff endpoint must scope both snapshots to `user_id`. Comment bodies are user-supplied text — render through DOMPurify on display.

**Decisions needed:**
- NEW dep: `diff-match-patch` (npm, ~30KB, MIT). Acceptable.
- Snapshot storage: full JSON blob per snapshot (simpler) vs. delta-only (smaller). Recommend full JSON for v1 — manuscripts are tiny.
- Comment anchoring: TipTap mark vs. ProseMirror decoration. Recommend Mark so anchors survive editing (decorations don't).
- Snapshot retention: unlimited for v1 (manual delete only).

---

## Mini-phase 12 — Cover letter + reviewer response + submission zip

**Scope:** Three AI-assisted helpers that close the submission loop. (a) Cover letter generator: user picks target journal (from Phase 8.7 catalogue) + enters 2-3 novelty bullet points; AI drafts a 250-word cover letter referencing title, corresponding author, conflict statement (pulled from ICMJE), suggested reviewers field. Saved as a project-scoped document, exportable as separate DOCX. (b) Response-to-reviewers helper: user pastes reviewer comments (block of free text); AI segments into individual comments and drafts initial responses with "we have revised X to Y" scaffolding; user edits inline; exports as a separate DOCX. (c) Submission package zip: one button assembles `manuscript.docx` + each figure as a separate `Figure_N.png/jpg/svg` + each table extracted to its own `Table_N.docx` + `cover_letter.docx` + (when present) `response_to_reviewers.docx` into a zip, named `{project_slug}_v{snapshot}.zip`.

**Dependencies:** Mini-phase 10 (ICMJE for cover-letter fields), mini-phase 11 (snapshot to pin a "submission package"). Phase 8.7 (figures table + journal catalogue). Phase 8 (existing DOCX export).

**Items addressed:** #4 #5 #6

**Files:** `apps/api/alembic/versions/0013_cover_letters_responses.py` (NEW — `cover_letters` + `reviewer_responses` tables), `apps/api/src/research_api/services/ai/prompts/cover_letter.py` (NEW), `apps/api/src/research_api/services/ai/prompts/reviewer_response.py` (NEW), `apps/api/src/research_api/services/ai/base.py` (modify — `draft_cover_letter` + `draft_reviewer_response` Protocol methods), `apps/api/src/research_api/services/ai/gemini.py`, `apps/api/src/research_api/services/export/submission_package.py` (NEW — zipfile assembly using stdlib `zipfile`), `apps/api/src/research_api/services/export/docx_export.py` (modify — extract `<table>` walks into a standalone `tables_to_docx` function that emits one DOCX per table), `apps/api/src/research_api/routes/cover_letter.py` (NEW), `apps/api/src/research_api/routes/reviewer_response.py` (NEW), `apps/api/src/research_api/routes/export.py` (modify — `POST /export/submission-package`), `apps/web/src/components/submission/CoverLetterEditor.tsx` (NEW), `apps/web/src/components/submission/ReviewerResponseEditor.tsx` (NEW), `apps/web/src/components/submission/SubmissionPackageDialog.tsx` (NEW).

**Tasks (rough count):** ~18.

**Tests delta:** +~24 backend, +~3 vitest.

**Security review:** medium. AI prompts must use the existing untrusted-data warning pattern from `result_interpretation.py`. The submission package zip writer must reject path-traversal in figure filenames (already sanitised at upload but defence-in-depth here).

**Decisions needed:**
- AI prompt design for reviewer-response segmentation — split on blank lines + numeric prefixes; let user re-segment if AI gets it wrong.
- Filename convention: `Figure_1.png` (1-indexed) confirmed per researcher convention.
- Table extraction: each TipTap `<table>` becomes its own DOCX named `Table_1.docx` etc., preserving the manuscript's table numbering.

---

## Mini-phase 13 — Statistics: power, PSM, OLS diagnostics

**Scope:** Three additions to the statistics module. (a) Pre-study sample size + power calculator: a wizard accepts test type (currently scoped to t-test independent / paired, ANOVA, chi-square, correlation, OLS — five families covering the 18 tests), alpha (default 0.05), power (default 0.80), effect size (small/medium/large presets per Cohen plus a custom field), and solves for required n via `statsmodels.stats.power`. (b) Propensity-score matching: dataset + outcome variable + treatment variable + covariate list → fit logistic regression with sklearn, compute propensity scores, perform 1:1 nearest-neighbour matching with caliper (0.2 SD default), output a matched dataset (saved back as a new dataset row), plus a covariate-balance table (standardised mean differences before/after). (c) OLS residuals/leverage/influence plots: extend the existing OLS test result to also save residuals-vs-fitted, QQ, scale-location, and residuals-vs-leverage PNGs (statsmodels `plot_regress_exog` + `plot_leverage_resid2`).

**Dependencies:** Phase 6 (stats module) + Phase 8.5 (charts pipeline) — both confirmed shipped.

**Items addressed:** #7 #8 #9

**Files:** `apps/api/src/research_api/services/stats/power.py` (NEW — pure-function wrappers around `statsmodels.stats.power.TTestIndPower`, `FTestAnovaPower`, `NormalIndPower`, etc.), `apps/api/src/research_api/services/stats/psm.py` (NEW — sklearn `LogisticRegression` + numpy nearest-neighbour matching), `apps/api/src/research_api/services/stats/diagnostics/ols_plots.py` (NEW), `apps/api/src/research_api/services/stats/runner.py` (modify — OLS path emits diagnostics PNGs), `apps/api/src/research_api/routes/power.py` (NEW: `POST /api/power` returning required n + sensitivity curve PNG), `apps/api/src/research_api/routes/psm.py` (NEW: `POST /api/datasets/{id}/psm` creating a matched dataset), `apps/web/src/components/statistics/PowerCalculator.tsx` (NEW), `apps/web/src/components/statistics/PSMWizard.tsx` (NEW), `apps/web/src/components/statistics/OLSDiagnosticsPanel.tsx` (NEW).

**Tasks (rough count):** ~16.

**Tests delta:** +~22 backend, +~3 vitest.

**Security review:** low. PSM accepts column names from user-uploaded CSV — confirm column names are validated against the dataset schema (already done in 8.5's wizard).

**Decisions needed:**
- `statsmodels` already installed via pingouin chain — confirm `statsmodels.stats.power` ships with it. `scikit-learn` already pulled by pingouin transitively. NO new deps expected; double-check during preflight.
- PSM matching algorithm: nearest-neighbour with caliper is the simplest defensible choice. Optimal matching (network-flow) deferred.
- Caliper default: 0.2 × SD(propensity-score-logit) per Austin 2011.

---

## Mini-phase 14 — Systematic review: GRADE + PROSPERO

**Scope:** Two systematic-review polish features. (a) GRADE certainty-of-evidence: per outcome (one row per outcome × meta-analysis), the user assesses 5 downgrade domains (risk of bias / inconsistency / indirectness / imprecision / publication bias) each `not serious / serious / very serious`, and 3 upgrade domains (large effect / dose-response / all-plausible-confounders-against), each `none / present / large`. Starting certainty defaults to "High" for RCTs and "Low" for observational (read from extraction `basic.design`). Result: certainty rating per outcome (4 levels) plus a printable Summary of Findings table. (b) PROSPERO registration helper: a structured form with the 22 PROSPERO required fields (title, anticipated start/finish dates, named contact, search strategy text, inclusion/exclusion criteria, primary/secondary outcomes, etc.) pre-filled from the review's existing fields; output is a copy-friendly text block the user pastes into the PROSPERO web form. No API call to prospero.

**Dependencies:** Phase 7 (systematic review + RoB), Phase 7.5 (meta-analysis — GRADE attaches to a meta outcome).

**Items addressed:** #10 #11

**Files:** `apps/api/alembic/versions/0014_grade_prospero.py` (NEW — `grade_assessments` table with `review_id`, `meta_id` nullable, `outcome_label`, the 8 domain fields, computed `certainty`, plus `prospero_drafts` table with one JSON row per review), `apps/api/src/research_api/services/review/grade.py` (NEW — pure-function `compute_certainty(starting, downgrades, upgrades) -> "high"|"moderate"|"low"|"very_low"`), `apps/api/src/research_api/services/review/sof_table.py` (NEW — renders Summary-of-Findings as HTML for push-to-Results), `apps/api/src/research_api/routes/grade.py` (NEW), `apps/api/src/research_api/routes/prospero.py` (NEW), `apps/web/src/components/review/grade/GRADEAssessmentForm.tsx` (NEW), `apps/web/src/components/review/grade/SoFTable.tsx` (NEW), `apps/web/src/components/review/PROSPEROForm.tsx` (NEW).

**Tasks (rough count):** ~14.

**Tests delta:** +~18 backend, +~3 vitest.

**Security review:** low. Free-text PROSPERO fields are user-supplied — render through DOMPurify on display.

**Decisions needed:**
- GRADE starting-certainty default: tied to study design extracted in Phase 7. If `basic.design` is missing for any included study, default to "High" and let the user downgrade.
- Whether GRADE attaches per meta-analysis or per outcome. Recommend per outcome (one meta-analysis can produce 2+ outcomes — primary + secondary).

---

## Mini-phase 15 — Living systematic review (scheduled reruns)

**Scope:** Save the PubMed query that produced the systematic review's hits (from Phase 8.6) and schedule a monthly automated re-run. New hits compared to the saved baseline; novel articles are surfaced in a "New since last run" panel in the review's Screening tab. Researcher can mark each as include / exclude (which then enters the standard screening flow). Single-tenant scheduler: in dev, an APScheduler `BackgroundScheduler` inside the FastAPI process; in production (Fly.io), a tiny separate worker process driven by `apscheduler` cron triggers reading the same SQLite DB.

**Dependencies:** Phase 8.6 (ingestion — PubMed query and result hashing already shipped).

**Items addressed:** #12

**Files:** `apps/api/alembic/versions/0015_living_review.py` (NEW — `living_review_jobs` table: `review_id`, `pubmed_query`, `cron_expr`, `last_run_at`, `last_hit_count`, `enabled`; `living_review_hits` table: per-run delta), `apps/api/pyproject.toml` (modify — add `apscheduler>=3.10`), `apps/api/src/research_api/services/review/living.py` (NEW — pure-function `diff_new_hits(prior_ids, fresh_ids) -> list[str]`), `apps/api/src/research_api/services/scheduler/runner.py` (NEW — APScheduler init + cron-driven job that calls existing PubMed ingest service), `apps/api/src/research_api/main.py` (modify — start scheduler on app lifespan in dev; document worker process for prod), `apps/api/src/research_api/routes/living.py` (NEW — enable/disable, list runs, list new hits, dismiss/accept), `apps/web/src/components/review/LivingReviewPanel.tsx` (NEW).

**Tasks (rough count):** ~12.

**Tests delta:** +~14 backend (scheduler under fake clock), +~2 vitest.

**Security review:** medium. Scheduler runs background tasks → must scope each job to its `user_id` when calling the ingest service. Confirm no information leaks across users via the shared DB. Rate-limit PubMed calls to respect NCBI's 3 req/sec (existing client should already enforce this — verify).

**Decisions needed (significant):**
- **NEW dep:** `apscheduler` (BSD, well-maintained). Alternative: `croniter` + manual asyncio loop. APScheduler simpler.
- **EXTERNAL surface:** scheduler is the first long-running background process in the codebase. In Fly.io, decide between (a) running scheduler inside the API container (simple, fine at this scale), or (b) a separate Fly process group (cleaner). Recommend (a) for v1 with a feature flag.
- Cron expression UX: expose only `monthly`, `weekly`, `daily` presets — not raw cron strings — to keep researchers safe.
- Notification surface: in-app badge in `LivingReviewPanel`. Email notifications deferred (depends on multi-user / auth).

---

## Out of scope (acknowledged, deferred — not in this roadmap)

- Multi-user with auth, permissions, invitations, comments-by-other-user — requires real authentication infrastructure.
- Plagiarism / similarity check (Turnitin / iThenticate) — external paid service.
- Phase 9 — Electron desktop packaging — paused per user direction.
- REML / Paule-Mandel τ² estimators (already deferred from Phase 7.5).
- Network meta-analysis (already deferred from Phase 7.5).
- Egger's regression for publication bias (already deferred from Phase 7.5).

---

## Risk register

| Risk | Likelihood | Phase | Mitigation |
|------|------------|-------|------------|
| ICMJE schema design churn requires migration 0011 + 0011b | medium | 10 | Spend extra design time up-front; tag `phase-icmje` after schema lands separately from UI |
| `apscheduler` + Fly.io single-instance constraint (only one scheduler must run) | medium | 15 | Lock via SQLite advisory row in `living_review_jobs.lease_holder`; alt: scale Fly to 1 instance with a feature flag |
| AI cover-letter quality variable | low | 12 | Same untrusted-data + token-set discipline as Phase 7.5 prompts; user always edits |
| Diff viewer performance on long manuscripts | low | 11 | `diff-match-patch` is fast on <100KB inputs (manuscripts are smaller); chunk per section |
| Cmd-F cross-section search clashes with browser Cmd-F | low | 9 | Catch keydown only when the editor has focus; release back to browser otherwise |

---

## Test-count delta estimate (across all 7 mini-phases)

Backend: ~+142 tests
Frontend (vitest): ~+23 tests
E2E (chrome-devtools-mcp): one new run per mini-phase = +7 E2E screenshot sets

---

## Execution checkpoints

After each mini-phase: `BUILD_LOG.md` entry, `git tag phase-{N}`, `/security-review` on the diff, E2E smoke via chrome-devtools-mcp.
