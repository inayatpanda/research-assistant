# MP12.5 → MP15 Consolidated Execution Plan

This plan covers the seven remaining mini-phases as a single coherent execution roadmap. Each section is dense — executor agents fill in details by reading existing patterns (Phase 1-12 references are in this repo).

**Entering state**: 1278 backend + 153 vitest, all green. Migration head: `0013_cover_letters_responses`. Tags: phase-1 → phase-12 (with phase-7p5/8p5/8p6/8p7 between).

---

## MP12.5 — URL-scoped project routing  (~½ day)

**Goal**: Open multiple projects in parallel tabs. Project ID becomes part of the URL path; the global "active project" Zustand store becomes a "last-viewed default for new tabs" only.

**Route refactor**:

| Today | Tomorrow |
|---|---|
| `/` | Dashboard (project picker) — unchanged |
| `/library` | `/projects/:projectId/library` |
| `/reader`, `/reader/:articleId` | `/projects/:projectId/reader`, `/projects/:projectId/reader/:articleId` |
| `/compile` | `/projects/:projectId/compile` |
| `/manuscript` | `/projects/:projectId/manuscript` |
| `/statistics` | `/projects/:projectId/statistics` |
| `/review` | `/projects/:projectId/review` |
| `/consort` | `/projects/:projectId/consort` |
| `/submission` | `/projects/:projectId/submission` |
| `/settings` | `/settings` (global) |
| `/health` | `/health` (global) |

New route: `/projects/:projectId` (project home — quick-link grid to its modules + small dashboard of counts).

**Tasks**:
1. `App.tsx`: nested route tree `Route path="projects/:projectId/*"` with child routes for each module.
2. Every page that does `useActiveProject(s => s.projectId)` → switch to `useParams<{projectId: string}>().projectId`. Add a `useEnsureProjectExists(projectId)` guard hook that 404s if the project doesn't belong to the user.
3. Sidebar nav becomes contextual: links use `useParams().projectId` to build hrefs. Show "Pick a project" state when no projectId in URL.
4. Header gets a project switcher: dropdown listing recent projects + "Open new project in new tab" affordance.
5. Old URLs (`/library`, `/manuscript`, etc.) → redirect to `/projects/<lastActive>/library` if a last-active exists; else to `/`.
6. Zustand store: keep but rename to `lastViewedProjectId`; written on every project route mount.
7. Update every existing nav link, in-page link, and toast-action that previously did `navigate('/manuscript')` to `navigate(\`/projects/\${projectId}/manuscript\`)`.

**Tests**: ~+6 vitest covering route guards, redirects, switcher dropdown.

**Tag**: `phase-12p5`.

---

## MP12.6 — Polish round  (~½ day)

**Goal**: Three user-reported issues + resizable dividers across all multi-pane pages.

**Tasks**:

1. **PubMed search v2**:
   - `services/ingest/pubmed.py`: pass `sort=relevance`, raise default `retmax` from 20 to 50.
   - `routes/ingest.py POST /search-pubmed`: return abstract + MeSH terms + author affiliations (already in efetch XML — currently dropped at parse time).
   - Frontend `PubMedSearchDialog`: each result row now has a "Preview" expand-button → side panel shows full abstract + MeSH + a "View on PubMed →" external link (`https://pubmed.ncbi.nlm.nih.gov/<pmid>/`).
   - Optional filters: date range, article type (Clinical Trial / Review / Meta-analysis), English-only.

2. **Paraphrase + notes persistence fix**:
   - Investigate `routes/compilations.py` and the Compile UI's "Accept" vs "Push to Manuscript" flow. Likely the buttons are mis-labelled or "Accept" doesn't trigger the manuscript-section update.
   - Same investigation for highlight notes — verify the Compile card pulls notes through when pushing.
   - Either fix the buttons or relabel them so the user understands which one persists where. Add tests.

3. **Click highlight in Reader rail to open popover**:
   - `apps/web/src/components/reader/HighlightsRail.tsx` (or whatever file): the right-rail highlight rows should fire the same `HighlightNotePopover` that on-page highlights do. Forward the click target's bounding rect or anchor to a known position.

4. **Resizable dividers**:
   - Install `react-resizable-panels` (already a peer of shadcn's `resizable` component) or use shadcn's `<ResizablePanelGroup>`.
   - Apply to: Reader (PDF / Highlights rail), Compile (Cards / Section draft), Manuscript (Editor / Right rail), Statistics (Dataset list / Detail), Review (Tabs / future second pane).
   - Persist widths per-page in localStorage.

**Tests**: ~+8 backend (PubMed parsing + paraphrase persistence + abstract field round-trip), ~+5 vitest.

**Tag**: `phase-12p6`.

---

## MP13 — Stats workbench  (~3 days)

**Goal**: Make Statistics a real workbench. Data transformation, cross-dataset ops, extended test catalogue, power calculator, PSM, OLS diagnostics, editable data view, syntax view.

### Data transformation workspace
- New table `dataset_transformations`: id, user_id, dataset_id (FK CASCADE), position (int), op_type (Literal: `filter` | `mutate` | `select` | `recode` | `group_summarise` | `log_transform` | `z_score` | `drop_na`), op_args (JSON), label (str), created_at.
- Service `services/stats/transform.py`: pure functions applying an op to a pandas DataFrame. Functions return a new DataFrame; original untouched.
- Route `/api/projects/{pid}/datasets/{did}/transformations`: CRUD on the operation stack.
- The runner applies the dataset's transformation stack BEFORE running any test (transformations are a property of the dataset, not the analysis).

### Cross-dataset ops
- Route `/api/projects/{pid}/datasets/cross-op`: body `{op: "merge"|"append"|"join", source_dataset_ids, args}`. Creates a new Dataset row with `derived_from_dataset_ids: list[str]` (extend the Dataset schema; needs migration alongside `derived_from_dataset_id` from MP13's PSM).
- Service `services/stats/cross_dataset.py`.

### Extended test catalogue
- Add to `TestKey` Literal: `mixed_effects_lm`, `glm_poisson`, `glm_binomial`, `glm_gamma`, `gee`, `bootstrap_mean_diff`, `permutation_test`, `tost_equivalence`, `tost_noninferiority`.
- Implement each in `services/stats/runner.py`:
  - **Mixed-effects**: `statsmodels.MixedLM.from_formula(...)`. Recommender suggests this when the dataset has a repeated-measures structure (long format with same patient_id across multiple rows + a time variable).
  - **GLM** (Poisson / Binomial / Gamma): `statsmodels.GLM.from_formula(..., family=sm.families.Poisson())`.
  - **GEE**: `statsmodels.GEE.from_formula(..., cov_struct=Exchangeable())`.
  - **Bootstrap**: `scipy.stats.bootstrap` for confidence intervals on any statistic.
  - **Permutation**: `scipy.stats.permutation_test`.
  - **TOST** (Two One-Sided Tests for equivalence/non-inferiority): `statsmodels.stats.weightstats.ttost_ind` + `ttost_paired`. Requires user-specified equivalence margin.
- Each gets a chart renderer in `services/stats/charts/`:
  - Mixed-effects: random-effects caterpillar plot
  - GLM: deviance residuals
  - GEE: same as GLM
  - Bootstrap: histogram of bootstrap distribution with CI bands
  - Permutation: null-distribution histogram with observed-statistic line
  - TOST: equivalence-bounds plot with point estimate + 90% CI

### Power calculator (#7 from roadmap)
- `services/stats/power.py`: wrappers around `statsmodels.stats.power` for 5 families (ttest_ind, ttest_paired, anova, chi_square, correlation). Each function returns required_n + sensitivity-curve PNG.
- Route `POST /api/power`.
- Frontend `PowerCalculator.tsx`: standalone tool, NOT tied to a dataset.

### PSM (#8)
- `services/stats/psm.py`: sklearn `LogisticRegression` → propensity scores → 1:1 nearest-neighbour matching with 0.2 SD caliper → SMD balance table (pre vs post).
- Route `POST /api/projects/{pid}/datasets/{did}/psm`: creates a new derived Dataset row.

### OLS diagnostics (#9)
- `services/stats/diagnostics/ols_plots.py`: 4-panel residuals/leverage/influence plots. Extends `AnalysisResult.chart` JSON for OLS results with `{panels: {residuals_vs_fitted, qq, scale_location, residuals_vs_leverage}}`.

### Editable Data View
- Frontend `components/statistics/DataView.tsx`: tabular grid (use a lightweight grid like `@tanstack/react-table` — already in deps? if not, add it). Pagination 50 rows/page. Sortable / filterable. Click a cell to edit. Edit emits a new `mutate` op into the operation stack (non-destructive — original CSV untouched).

### Syntax view
- For every analysis + transformation, render a pseudo-code trace in a togglable panel:
```
data <- import("hip_outcomes.csv")
data <- filter(data, !is.na(hhs_6w))
data <- mutate(data, log_blood_loss = log(blood_loss_ml))
result <- ttest(data, formula = hhs_6w ~ approach, var.equal = FALSE)
```
- Build a tiny `lib/syntaxRenderer.ts` that takes a Dataset's transformation stack + an Analysis row and emits the text.

**Tests**: ~+90 backend, ~+12 vitest.

**Tag**: `phase-13`.

---

## MP13.5 — Plots + plans + reports + output viewer  (~2 days)

### Plot workspace (grammar-of-graphics style)
- Route `POST /api/projects/{pid}/datasets/{did}/plot`: body `{geom: "point"|"bar"|"line"|"box"|"violin"|"heatmap"|"histogram"|"density", x: col_name, y?: col_name, color?: col_name, facet?: col_name, ...}`. Renders matplotlib chart, returns base64 PNG.
- New table `dataset_plots`: id, user_id, dataset_id (FK), spec (JSON), title, created_at — so saved plots persist.
- Frontend `components/statistics/PlotWorkspace.tsx`: form-driven plot builder. Live preview.

### Analysis plans
- New table `analysis_plans`: id, user_id, project_id (FK CASCADE), name, description (NULL), steps (JSON list of `{type: "transform"|"test"|"plot", ...args}`), created_at, updated_at.
- New table `analysis_plan_runs`: id, plan_id, dataset_id, executed_at, result_blob (JSON). Versioned.
- Routes `/api/projects/{pid}/analysis-plans/*`: CRUD + `POST /{id}/run`.
- Frontend: save current analysis as a plan; re-run; clone-to-edit; compare across plans.

### Statistical report PDF
- Service `services/export/stats_report.py`: walks all analyses on a dataset + their charts + assumption checks + AI interpretations → multi-page PDF via reportlab.
- Route `POST /api/projects/{pid}/datasets/{did}/report`.
- Frontend: "Export full statistical report" button on the Statistics page.

### Output Viewer
- Frontend `components/statistics/OutputViewer.tsx`: scrollable document showing every analysis run on the active dataset, in chronological order. Each card expandable/collapsible/pinnable. Reorder by drag.

**Tests**: ~+30 backend, ~+8 vitest.

**Tag**: `phase-13p5`.

---

## MP13.6 — Bayesian (conditional)  (~1 day)

**Preflight**: attempt `.venv/bin/pip install bambi pymc` on the dev machine. If it fails (most likely cause: missing Xcode CLT or pytensor C build error), DEFER cleanly and add to DEFERRED.md.

**If preflight succeeds**:
- `services/stats/bayesian.py`: wrappers around bambi for Bayesian t-test, ANOVA, regression. Returns posterior means + 95% credible intervals + posterior plot PNG.
- Routes hooked into the existing `analyses` flow with `test_key = bayesian_ttest`, etc.
- Frontend: enrich AnalysisResultCard to render credible intervals and posterior distribution plots.

**Tag**: `phase-13p6` (or skip-tag if deferred).

---

## MP14 — GRADE + PROSPERO  (~1 day)

Per the original post-E2E roadmap. No changes.

- New table `grade_assessments`: id, user_id, review_id, meta_id (nullable), outcome_label, 5 downgrade-domain fields + 3 upgrade-domain fields, computed `certainty` (Literal high/moderate/low/very_low).
- New table `prospero_drafts`: one JSON row per review with the 22 PROSPERO required fields pre-filled from existing review data.
- Service `services/review/grade.py`: pure `compute_certainty(starting, downgrades, upgrades)`.
- Service `services/review/sof_table.py`: Summary-of-Findings HTML for push-to-Results.
- Frontend GRADEAssessmentForm, SoFTable, PROSPEROForm.

**Tests**: ~+18 backend, ~+3 vitest.

**Tag**: `phase-14`.

---

## MP15 — Living systematic review  (~1 day)

Per the original roadmap.

- New dep: `apscheduler>=3.10`.
- New tables `living_review_jobs` (cron schedule per review) + `living_review_hits` (per-run delta).
- Service `services/review/living.py`: `diff_new_hits(prior_ids, fresh_ids)`.
- Service `services/scheduler/runner.py`: APScheduler init on app lifespan in dev; document worker process for prod.
- Routes `/api/projects/{pid}/reviews/living/*`.
- Frontend `LivingReviewPanel.tsx`.

**Tests**: ~+14 backend (under fake clock), ~+2 vitest.

**Tag**: `phase-15`.

---

## Final E2E sweep

After MP15: re-run the comprehensive E2E with the same mock data, screenshot every page, log any regressions, hot-fix.

---

## Test-count target on completion

- Backend: 1278 → ~1500 (~+220 across all 7 mini-phases)
- Vitest: 153 → ~210 (~+57)
- Tags: phase-12p5, phase-12p6, phase-13, phase-13p5, phase-13p6 (or skipped), phase-14, phase-15.

## Risk register

| Risk | Phase | Mitigation |
|---|---|---|
| URL refactor breaks deep-linked bookmarks | 12.5 | Backwards-compat redirect from `/library` etc. to last-active project; deprecate after a release. |
| Compile Accept-vs-Push flow may have deeper schema issue | 12.6 | Time-box investigation; if it's a schema problem, lift to its own mini-phase. |
| pymc install fails on macOS | 13.6 | Deferred clean — no hold-up of MP14/MP15. |
| APScheduler + Fly.io single-instance constraint | 15 | Use SQLite advisory row as lease holder; document. |
| Subagent quota hits during dispatch | every phase | Re-attempt after reset, or work inline for the final touches. |

## Out of scope (still)

- Multi-user auth + permissions + invitations
- Plagiarism / similarity check
- Phase 9 — Electron desktop packaging
- Full lme4 parity (only limited statsmodels GLMM in v1)
- Notebook-style cells (rejected — too big a UI lift; the Output Viewer fakes it)
- Arbitrary user code execution (rejected — security)
