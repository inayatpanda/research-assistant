# MP16 → MP20 Consolidated Execution Plan

Five mini-phases addressing gaps identified from analysis of 5 real research papers (1 RCT, 2 retrospective comparative, 2 systematic reviews). Total scope ~10 agent-days. Executed in this order: **MP19 → MP17 → MP18 → MP20 → MP16**.

**Entering state**: 1545 backend + 212 vitest, all green. Migration head: `0019_living_review`. Tags: phase-1 through phase-15.

**User-confirmed decisions**:
- MeSH translator = best-effort cross-database (mark "review before running")
- Outcome instrument library = curated 30-item declarative list
- Reporting checklists = interactive (tick each item with comment + status badge, export as completed PDF)

---

## MP19 — SR depth + MeSH (~2.5d)

Largest of the five. Sits inside the Systematic Review module.

### Schema
- Migration `0020_sr_depth_mesh.py` (down_revision `0019`):
  - `mesh_terms` table: id, project_id, descriptor_ui (e.g. "D013313" for THA), descriptor_name, scope_note, tree_numbers (JSON list), entry_terms (JSON list), source ("user_added" | "ncbi_lookup"), created_at.
  - `search_strategies` table: id, user_id, project_id, review_id (FK), name, database (Literal PubMed / Embase / Cochrane / Web of Science / Scopus / Other), query_text, mesh_term_ids (JSON list), translated_from_id (FK self, nullable — tracks source query for cross-DB translation), is_locked (bool), created_at, updated_at.
  - `narrative_synthesis_entries` table: id, user_id, review_id (FK), outcome_label, instrument, range_text, direction (Literal "higher_better"|"lower_better"|"neutral"), narrative_html, study_citations (JSON list of article_ids), created_at, updated_at.
  - `outcome_instruments` table: id, user_id, review_id (FK CASCADE), outcome_label, instrument_name, score_range_low, score_range_high, MID (nullable), study_values (JSON: list of {article_id, group_label, value, sd_or_ci, n}), created_at.
  - `rob_assessments` (existing): add `tool_per_study` flag — when false (default), review uses one tool; when true, each study row has its own `tool` field.
  - `articles` (existing): formalise `study_design` Literal: `rct | cohort | case_control | case_series | case_report | cross_sectional | quasi_experimental | systematic_review | diagnostic_accuracy | prevalence | qualitative | other`.

### Services
- `services/review/jbi_rules.py`: declarative catalogue of 7 JBI Critical Appraisal Tools (Case Series 10 items, Case Reports 8, Cohort 11, Cross-sectional 8, Quasi-experimental 9, Diagnostic Test Accuracy 10, Prevalence 9). Each item has prompt + answer set ("Yes" | "No" | "Unclear" | "Not Applicable"). Pure `derive_overall_jbi(tool, answers) → "low"|"moderate"|"high"|"unclear"` mirroring `rob_rules`. Add to `TOOL_CATALOGUE` so existing RoB endpoints support them.
- `services/review/narrative_synthesis.py`: pure `build_narrative_table_html(entries) → str` renders a multi-instrument comparison table (rows = studies, columns = instruments). One row per included study, NA cells where unmeasured.
- `services/review/publication_bias.py`: `egger_test(effects, ses) → {intercept, p}`, `harbord_test(events_t, n_t, events_c, n_c) → {z, p}`, `begg_test(effects, ses) → {tau, p}`, `peters_test(events, total) → {intercept, p}`. Pure scipy/numpy. Picked by metric type (continuous → Egger; binary → Harbord, Peters; rank-based → Begg).
- `services/meta/leave_one_out.py`: extends MP7.5's pooler. For each input, rerun pool with that study excluded → returns `[{excluded_study_id, pooled_effect, ci_low, ci_high, i2}]`. Add chart.
- `services/meta/subgroup_interaction.py`: Q-between = Q-total − Σ Q-within. Returns `{q_between, df, p_interaction}`.
- `services/meta/meta_regression.py`: weighted OLS on effect ~ moderator_variable. statsmodels WLS. Returns coefficient + p + R² + bubble plot. Single-moderator v1; multi-moderator deferred.
- `services/ingest/mesh.py`: thin wrapper over NCBI `esearch.fcgi?db=mesh&term=…` and `efetch.fcgi?db=mesh&id=…&retmode=xml`. Parses MeSH XML for: descriptor UI, name, scope note, tree numbers, entry terms. Cached locally in `mesh_terms` table after first lookup.
- `services/ingest/search_translator.py`: best-effort PubMed → Embase / Cochrane / Web of Science. Map MeSH `[MeSH Major Topic]` / `[MeSH Terms]` → Embase `/exp` / `/de`, Cochrane `MeSH descriptor: [...]`, WoS `TS=(…)`. Operator translation (`AND` / `OR` / `NOT` consistent; `NEAR/n` syntax differs). Returns translated query + warnings list (terms that couldn't be mapped cleanly).
- `services/review/grade.py` (existing): tighten linkage so when a meta-analysis publishes a result, GRADE assessment auto-prefills the effect estimate + n studies columns.

### Routes
- `/api/projects/{pid}/review/mesh/search?q=…` — MeSH lookup
- `/api/projects/{pid}/review/mesh/suggest` — given the review's PICO, suggest top MeSH terms
- `/api/projects/{pid}/review/search-strategies` (CRUD)
- `/api/projects/{pid}/review/search-strategies/{id}/translate?to=embase|cochrane|wos` — best-effort translation
- `/api/projects/{pid}/review/narrative-synthesis` (CRUD)
- `/api/projects/{pid}/review/narrative-synthesis/push` — push table to Results
- `/api/projects/{pid}/review/outcome-instruments` (CRUD)
- `/api/projects/{pid}/review/outcome-instruments/push` — push comparison table to Results
- `/api/projects/{pid}/review/meta/{id}/publication-bias` — runs Egger/Harbord/Begg/Peters
- `/api/projects/{pid}/review/meta/{id}/leave-one-out`
- `/api/projects/{pid}/review/meta/{id}/subgroup-interaction`
- `/api/projects/{pid}/review/meta/{id}/meta-regression`
- Article PATCH gains `study_design` field validation
- RoB POST gains `tool_per_study` flag handling

### Frontend
- `MeSHBrowser.tsx` — search MeSH, drag terms into search builder
- `SearchStrategyBuilder.tsx` — query composer with boolean operator buttons, MeSH-term chips, free-text input, live PubMed count preview
- `CrossDatabaseTranslator.tsx` — pick source query → pick target DB → see translated query + warnings
- `NarrativeSynthesisPanel.tsx` — per-outcome rows with instrument + range + narrative editor
- `OutcomeInstrumentsTable.tsx` — many-to-many studies × instruments
- `PublicationBiasPanel.tsx` — shows Egger / Harbord / Begg / Peters results + funnel
- `LeaveOneOutTable.tsx` — sensitivity table
- `MetaRegressionForm.tsx`
- `JBIAssessmentForm.tsx` — JBI tool selector + per-item form
- `RoBToolPicker` extension: when `tool_per_study` enabled, allow per-study tool dropdown

### Tests
~+90 backend, ~+10 vitest. Cross-user isolation regression `test_security_sr_depth_isolation.py`.

### Tag
`phase-19`.

---

## MP17 — Stats depth (~2.5d)

### Schema
- Migration `0021_stats_depth.py`:
  - `analyses` (existing): add `population` Literal field (`itt | pp | safety | as_treated | economic | complete_case | imputed`), nullable. NULL = whole dataset. Add `is_locked` boolean + `locked_at` + `integrity_hash` for pre-registration.
  - `analysis_plans` (existing): same lock fields.
  - `analysis_populations` table: id, user_id, dataset_id (FK), name, definition (JSON: pandas filter expression as Literal AST), study_assignment_field (str — column holding allocation), treatment_received_field (str, nullable — for ITT vs as-treated logic).
  - `outcome_instruments_catalogue` (static; loaded from a JSON file at startup, not a migration): curated 30-item list.
  - `imputation_runs` table: id, user_id, dataset_id, method (Literal "mice" | "knn" | "mean" | "median" | "last_observation"), n_imputations (int, default 5), seed, created_at. Each run stores pooled effect summaries.
  - `analysis_results` (existing): allow multiple results per analysis when populations differ (or add `analysis_population_id` FK).

### Services
- `services/stats/post_hoc.py`: Tukey HSD (statsmodels), Bonferroni (scipy), Dunn's (manual implementation), Games-Howell (manual). Auto-invoked when ANOVA / Kruskal-Wallis p<0.05.
- `services/stats/mixed_effects.py` (extend MP13's MixedLM): nested random effects via grouping syntax `groups=cluster1 | cluster2`, REML default, unstructured covariance, treatment × time interaction expansion. Use statsmodels' `formula` parameter with `(1 | centre) + (1 | centre:patient)`.
- `services/stats/populations.py`: pure `apply_population(df, population_def) → df` filters/transforms the dataset for the chosen analysis population. Defines macros: ITT = "all randomised", PP = "completed treatment as assigned", safety = "received any treatment", etc.
- `services/stats/imputation.py`: statsmodels MICE wrapper. Returns m=5 imputed datasets, pools effects via Rubin's rules.
- `services/stats/cace.py`: 2SLS approach for compliance-adjusted causal effect. statsmodels IV2SLS.
- `services/stats/sensitivity.py`: worst-case (assign worst possible value to missing), best-case, tipping point (find imputation value where significance flips).
- `services/stats/irr.py` (extend MP13): Fleiss κ (statsmodels), Krippendorff α (manual implementation), weighted κ (linear + quadratic weights via scipy).
- `services/stats/power.py` (extend MP13): survival/log-rank (lifelines), MixedLM (Liu & Liang 1997 formula), non-inferiority (TOST framework), cluster RCT (Donner & Klar).
- `services/instruments/catalogue.py`: 30-item curated declarative list. See appendix at end of this plan.
- `services/export/sap.py`: build_sap_document(project, analysis_plan) → bytes (PDF/DOCX). Walks the plan, lists per-analysis: test, variables, population, hypotheses, multiplicity adjustment.

### Routes
- `/api/projects/{pid}/datasets/{did}/populations` (CRUD)
- `/api/projects/{pid}/analyses/{aid}/post-hoc` — auto-runs when omnibus significant; can be manually triggered
- `/api/projects/{pid}/analyses/{aid}/mixed-effects` — full UI for nested clusters + interaction
- `/api/projects/{pid}/datasets/{did}/impute` — run MICE
- `/api/projects/{pid}/analyses/{aid}/cace`
- `/api/projects/{pid}/analyses/{aid}/sensitivity?type=worst|best|tipping`
- `/api/projects/{pid}/datasets/{did}/irr?method=fleiss|krippendorff|weighted_kappa`
- `/api/projects/{pid}/power/extended` (extends MP13's `/api/power` with new families)
- `/api/instruments/catalogue` — static list
- `/api/projects/{pid}/datasets/{did}/variables/{vid}/instrument-binding` — link a column to an instrument
- `/api/projects/{pid}/analysis-plans/{id}/lock` — pre-register: compute integrity hash, set locked_at
- `/api/projects/{pid}/analysis-plans/{id}/sap` — generate SAP document

### Frontend
- `PopulationManager.tsx` on Dataset detail — define + label populations
- `PostHocComparisonsCard.tsx` rendered below ANOVA/KW results
- `MixedEffectsWizard.tsx` — random-effect picker (single or nested), interaction toggle, REML/ML selector
- `ImputationCard.tsx` — pick method + n_imputations + seed, see pooled Rubin's
- `CACEPanel.tsx`
- `SensitivityAnalysisPanel.tsx` — worst/best/tipping with threshold slider
- `InstrumentLibraryBrowser.tsx` — searchable list of 30 instruments, click to bind to a dataset column
- `AnalysisPlanLockButton.tsx` — confirmation dialog + integrity hash display
- `SAPExportButton.tsx`

### Tests
~+80 backend, ~+10 vitest. Cross-user isolation extended.

### Tag
`phase-17`.

### Outcome instrument library (curated 30)

Hip/Knee: Harris Hip Score (HHS, 0-100, higher better, MID=8), Oxford Hip Score (OHS, 0-48, higher better, MID=5), Oxford Knee Score (OKS, 0-48, higher better, MID=5), Knee Society Score (KSS, 0-200, higher better), Knee Injury and Osteoarthritis Outcome Score (KOOS, 0-100), WOMAC (0-96, lower better, MID=12%), Forgotten Joint Score (FJS-12, 0-100), UCLA Activity Score (1-10).

Spine: Oswestry Disability Index (ODI, 0-100, lower better, MID=10), Neck Disability Index (NDI, 0-50), Roland-Morris (RMDQ, 0-24), Japanese Orthopaedic Association Score (JOA-back, 0-29).

Shoulder/Elbow: Constant-Murley (0-100), DASH (0-100, lower better, MID=10), Quick-DASH (0-100), Oxford Shoulder Score (OSS), ASES, PROMIS UE.

Foot/Ankle: AOFAS, FAOS, MOXFQ.

Generic: VAS Pain (0-10, lower better, MID=2), Numerical Rating Scale (NRS, 0-10), Short Form-36 (SF-36, 8 domains), SF-12 (PCS+MCS), EQ-5D-3L/5L/Y (utility 0-1), PROMIS Global Health, PROMIS Physical Function CAT, Patient Specific Functional Scale (PSFS).

Cardio: NYHA class.

Each entry: name, abbreviation, scale range, MID (when known), direction (higher_better|lower_better), category, default citation.

---

## MP18 — Health economics (~2d)

### Schema
- Migration `0022_health_economics.py`:
  - `economic_analyses` table: id, user_id, project_id (FK), dataset_id (FK), name, currency (Literal "GBP"|"USD"|"EUR"|"AUD"|"CAD"|"Other"), time_horizon_months (int), perspective (Literal "patient"|"healthcare_system"|"societal"), discount_rate_costs (float, default 0.035), discount_rate_qalys (float, default 0.035), wtp_thresholds (JSON list of int — e.g. [20000, 30000]), utility_value_set (Literal "EQ5D_3L_UK"|"EQ5D_5L_UK"|"EQ5D_Y_DUTCH"|"SF6D"), bootstrap_n (int, default 1000), seed (int), created_at, updated_at.
  - `cost_columns_binding`: links dataset variables to economic role (`unit_cost` | `quantity` | `cost_total` | `utility_score` | `qaly_weight` | `time_to_event`).
  - `economic_results` table: id, user_id, economic_analysis_id, mean_cost_diff, mean_qaly_diff, icer, nmb_at_thresholds (JSON), ceac_data (JSON list of {wtp, prob_costeffective}), plane_bootstrap (JSON list of {dCost, dQALY}), sensitivity (JSON), interpretation_html, created_at.

### Services
- `services/economics/qaly.py`: `compute_qaly(df, utility_col, time_col, group_col) → df` — area-under-the-curve per patient, baseline-adjusted.
- `services/economics/cost_qaly_regression.py`: bivariate regression with bootstrap. statsmodels OLS + scipy bootstrap. Returns full distribution.
- `services/economics/ceac.py`: probability of cost-effectiveness across WTP threshold range. Pure scipy.
- `services/economics/icer.py`: incremental cost-effectiveness ratio + dominance + NMB.
- `services/economics/utility_value_sets.py`: declarative catalogue — EQ-5D-3L UK (Dolan 1997), EQ-5D-5L UK, EQ-5D-Y Dutch, SF-6D Brazier. Each value set is a function from response profile → utility.
- `services/economics/charts.py`: cost-effectiveness plane (scatter of bootstrap dCost/dQALY with WTP threshold lines), CEAC (probability curve), tornado plot (one-way DSA).
- `services/economics/sensitivity.py`: deterministic sensitivity analysis (one-way DSA across parameter ranges), probabilistic sensitivity analysis (resample parameter distributions), scenario analysis (named scenarios with overrides).
- `services/export/economic_report.py`: CHEERS-style economic evaluation report.

### Routes
- `/api/projects/{pid}/economic-analyses` (CRUD)
- `/api/projects/{pid}/economic-analyses/{id}/run` — runs everything (QALYs, ICER, bootstrap, CEAC, plane)
- `/api/projects/{pid}/economic-analyses/{id}/sensitivity?type=psa|dsa|scenario`
- `/api/projects/{pid}/economic-analyses/{id}/push` — pushes summary + plane + CEAC to Results section via existing `_push_to_section`
- `/api/projects/{pid}/economic-analyses/{id}/cheers` — generates CHEERS-compliant report (linked into MP20)
- `/api/utility-value-sets` — static list

### Frontend
- `EconomicAnalysisSetup.tsx` — currency, time horizon, perspective, discount rates, WTP thresholds, utility value set
- `CostColumnBinder.tsx` — drag dataset variables onto economic roles
- `EconomicResultsCard.tsx` — ICER, NMB, mean diffs, "Plane" and "CEAC" panels with click-to-zoom
- `EconomicSensitivityPanel.tsx` — toggles between PSA / DSA / scenario
- `EconomicAnalysisWizard.tsx` — multi-step setup
- `UtilityValueSetSelector.tsx`

### Tests
~+60 backend, ~+8 vitest. Known-answer tests for QALY (worked example: utilities {0.8, 0.7, 0.6} over 12 months → QALY = 0.708), ICER, EQ-5D-3L value set.

### Tag
`phase-18`.

---

## MP20 — Reporting checklists (~1d)

### Schema
- Migration `0023_reporting_checklists.py`:
  - `checklists_catalogue` (static, loaded from JSON at startup, not a DB table — though a runtime DB cache could speed lookups).
  - `checklist_runs` table: id, user_id, project_id (FK), checklist_key (e.g. "CONSORT_2010"), title (e.g. "v1 submission to JBJS"), items (JSON list of `{item_id, item_text, status: "pass"|"fail"|"unclear"|"na", comment, mapped_section: ManuscriptSectionName | null, mapped_text_excerpt: str | null}`), overall_compliance_pct (float, derived), created_at, updated_at.
  - One run per (project, checklist_key) — UNIQUE.

### Catalogue (declarative, one JSON per checklist)

10 new + 2 retrofits:
- **CONSORT 2010** (25 items) — retrofit existing CONSORT to use the new runs table
- **PRISMA 2020** (27 items) — retrofit existing PRISMA
- **CHEERS 2022** (28 items)
- **STROBE** (22 items, 4 design-specific sub-checklists: cohort, case-control, cross-sectional)
- **TRIPOD-AI** (27 items for prediction models)
- **SPIRIT 2013** (33 items for trial protocols)
- **SQUIRE 2.0** (18 items for quality improvement)
- **CARE** (13 items for case reports)
- **AGREE II** (23 items for clinical practice guidelines)
- **SAMPL** (~30 items for statistical reporting)
- **PRISMA-S** (16 items for search strategy reporting)
- **PRISMA-ScR** (22 items for scoping reviews)

Each item: `{id, title, description, section_hint (manuscript_section_name), prompt, default_status}`.

### Services
- `services/checklists/catalogue.py`: loads JSON catalogues at startup. Cached.
- `services/checklists/auto_check.py`: pure best-effort auto-check. Given a manuscript + a checklist item, search the relevant section for keywords from the item's prompt and pre-fill `status: "pass"` (low confidence) when found. User reviews/edits.
- `services/checklists/export.py`: completed checklist as PDF, journal-submission-ready.

### Routes
- `/api/checklists/catalogue` — static list of available checklists + per-checklist item count
- `/api/projects/{pid}/checklists` (CRUD on runs)
- `/api/projects/{pid}/checklists/{run_id}/auto-check` — best-effort fill
- `/api/projects/{pid}/checklists/{run_id}/export` — PDF
- `/api/projects/{pid}/checklists/{run_id}/items/{item_id}` — PATCH single item status / comment / mapping

### Frontend
- `ChecklistsPage.tsx` — list of available checklists, per-run progress bars, "Start checklist" / "Resume" actions
- `ChecklistRunDrawer.tsx` — slide-in panel with per-item row: prompt + status radio (pass/fail/unclear/na) + comment textarea + "Link to section" button + "Mark from selection" button (drag from manuscript)
- `ChecklistAutoCheckButton.tsx` — runs the best-effort prefill
- `ChecklistExportButton.tsx`
- Mount under each project: new tab "Reporting checklists" — sits alongside Manuscript / Statistics / Review tabs in `ProjectHomePage` quick-links

### Retrofit existing CONSORT + PRISMA flows
Both already have flow-diagram generators (MP7 + MP8.7). Add a checklist run for each that captures the items beyond the flow chart.

### Tests
~+25 backend, ~+5 vitest.

### Tag
`phase-20`.

---

## MP16 — Citation depth (~1.5d)

### Schema
- Migration `0024_citation_depth.py`:
  - `articles` (existing): add `reference_type` Literal (`journal_article` | `book` | `book_chapter` | `conference_abstract` | `thesis` | `preprint` | `registry_record` | `report` | `web_resource` | `other`) — default `journal_article`. Add `url` (Text, nullable — for grey-literature URL-only refs).
  - `projects` (existing): add `inline_citation_mode` Literal (`bracket_numeric` | `superscript_numeric` | `author_year_parens`) — default `bracket_numeric` (current behaviour).

### Catalogue (extend `services/citation_format.py`)
Add ~6 new journal-specific style variants on top of the 4 canonical (vancouver / apa / harvard / ieee):
- `lancet` (Vancouver variant with superscript inline + specific reference-list format)
- `nejm` (numeric with specific reference layout)
- `bjj` (Bone & Joint Journal — Vancouver variant)
- `jbjs_am` (JBJS American — Vancouver variant)
- `bjsm` (BJSM — Vancouver variant)
- `jama` (numeric with specific format)

Each is a Python function `format_entry_<style>(article) → str` mirroring the existing Vancouver/APA/Harvard/IEEE entries.

### Services
- `services/citation_format.py` (extend): new style functions + dispatch.
- `services/ingest/citation_text_parser.py`: parse a block of pasted references. Handles common formats:
  - Numbered Vancouver: "1. Smith J, Jones K. Title. Journal. 2020;15(3):234-45."
  - Author-year: "Smith J, Jones K (2020). Title. Journal 15: 234-245."
  - Bare DOI per line.
  Splits on numbered prefixes / blank lines / `[N]` markers. For each fragment, extracts DOI/PMID via regex; if found, resolves via Crossref/PubMed; if not, attempts title-match in Crossref's search API.
- `services/figures/numbering.py`: pure `assign_figure_numbers(figures, references_in_manuscript) → dict[figure_id, int]`. Numbers figures in order of first in-text reference. Mirror for tables. Re-runs on push and on figure reorder.

### Routes
- `/api/projects/{pid}/articles/import-from-text` — body `{text}` → parses, resolves DOIs via Crossref, returns preview list (like MP8.6's import-from-metadata pattern)
- `/api/projects/{pid}/citations/styles` — static list with sample renders
- `/api/projects/{pid}/figures/renumber` — auto-renumber based on in-text references
- Add `?style=<key>` to existing bibliography endpoint; accept new style keys
- PATCH `/api/projects/{pid}` accepts `inline_citation_mode`

### Frontend
- `CitationStylePicker.tsx` — extend BibliographyToolbar with the 6 new styles
- `InlineCitationModeSelector.tsx` — radio: brackets / superscript / author-year
- `CitationTextImportDialog.tsx` — paste-references textarea + Parse button → preview + per-row Add/Skip
- `GreyLiteratureEntryForm.tsx` — manual entry for URL-only / registry / thesis refs
- `FigureNumberingPanel.tsx` — shows current numbering, "Auto-renumber" button, drag-to-reorder

### Folded-in bonus polish
- **B3 + B6** Figure auto-numbering with reorder + continuous figure & table numbering — handled by `services/figures/numbering.py` + frontend renumber panel
- **B4** Advanced comparison-matrix tables — folded into MP19's narrative-synthesis multi-instrument table

### Tests
~+45 backend, ~+8 vitest.

### Tag
`phase-16`.

---

## Risk register

| Risk | Phase | Mitigation |
|---|---|---|
| NCBI E-utilities rate limit on MeSH lookups | 19 | Local cache via `mesh_terms` table; expose API-key setting (NCBI's polite 10/sec tier) |
| Cross-DB search translation accuracy | 19 | User-confirmed best-effort; emit warnings list on every translation |
| MICE imputation slow on large datasets | 17 | Cap m=10; document expected runtime; expose seed for reproducibility |
| Multi-population analysis complicates result-rendering | 17 | Add `population_label` field on result card; tab-switch between populations |
| EQ-5D value sets are jurisdiction-specific | 18 | Catalogue 5 common ones; allow user-extensible later (deferred) |
| Checklist auto-check generates false positives | 20 | Default status = `unclear` after auto-check (not `pass`); user always reviews |
| Subagent quota mid-phase | every | Re-attempt after reset, work inline for terminal touches |

## Test count target on completion

- Backend: 1545 → ~1845 (~+300)
- Vitest: 212 → ~250 (~+38)
- Tags: phase-16, phase-17, phase-18, phase-19, phase-20

## Out of scope (still)

- Bayesian (pymc/llvmlite blocker — DEFERRED)
- Full lme4 GLMM parity (R bridge — DEFERRED)
- Network meta-analysis (NetMeta — DEFERRED)
- Multi-user collaboration
- DICOM imaging measurement
- Electron desktop packaging (Phase 9 — paused per user)
