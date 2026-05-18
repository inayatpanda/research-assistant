# Build Log

Phase-by-phase narrative of what happened during the autonomous build.
Newest entries on top. Each entry: timestamp · phase · what changed · any incidents.

---

## 2026-05-18 · Mini-phase 11 — Manuscript version snapshots + margin comments ✅ COMPLETE

**Plan:** `docs/superpowers/plans/2026-05-18-post-e2e-roadmap.md` (Mini-phase 11 section)

**Items addressed:** #2 (version history + diff), #3 (margin comments).

**Backend changes**

- New migration `0012_snapshots_comments.py` creating:
  - `manuscript_snapshots` (project_id, user_id, label, description, full_blob JSON, created_at). `UNIQUE (project_id, user_id, label)`. Index on (project_id, user_id).
  - `manuscript_comments` (project_id, user_id, section_name, anchor_start, anchor_end, body, resolved, created_at, updated_at). Index on (project_id, user_id, section_name, resolved).
- `db/models.py` — new `ManuscriptSnapshot` + `ManuscriptComment` ORM classes; both FK-cascade off `projects`.
- `schemas/snapshots.py` + `schemas/comments.py` — Pydantic models incl. the diff payload shape (`{section_name: [{type, line}]}`). `CommentSection` is a `Literal` of the six sections plus `FrontMatter`.
- `repositories/snapshots.py` — `list_for_project / get / create_from_current / delete`. No update path — snapshots are immutable. `create_from_current` assembles the JSON blob by walking sections, ICMJE rows (authors/affiliations/links/contributions/project_frontmatter), figures, abbreviations, meta_analyses, and extraction_records via direct selects (so the snapshot survives independent of the live repos).
- `repositories/comments.py` — list-with-filters / create / update (body or resolved) / delete. Returns `None` on cross-tenant ids so the route layer surfaces 404.
- `routes/snapshots.py` — five endpoints: list (Summary, no `full_blob`), create (201, 409 on label clash), get full, GET diff with optional `?target=` query (omitted = diff vs current state), DELETE.
- `routes/comments.py` — list (filterable by `?section=&resolved=`), POST, PATCH (body/resolved), DELETE.
- `services/export/bundle_export.py` + `bundle_import.py` — round-trip both tables; the importer suffixes label collisions with " (imported)" so the UNIQUE(project,user,label) constraint never trips.
- Wired `snapshots_router` + `comments_router` under `/api` in `main.py`.

**Diff design**

- `difflib.unified_diff` (stdlib only — no `diff-match-patch` dep). Per section, HTML is `splitlines()`-ed and fed in with `n=0` (no context) so the response is surgical: only changed lines surface. The route post-processes `+`/`-` markers into typed records; `---`/`+++`/`@@` headers are stripped before serialisation. Identical sections drop out of the response payload entirely (the UI shows "No changes" on empty `sections`).
- Granularity: line-by-line. TipTap emits one block per `<p>` so line granularity yields readable surgical diffs without a word-diff dep.

**Anchor staleness**

- Backend never validates `anchor_start/end` against the live content — comments are append-only metadata. The frontend's `CommentsRail` checks the bound editor's `state.doc.content.size`; if `anchor_start >= docSize` or `anchor_end > docSize+1`, the row gets a `(anchor stale)` badge and the jump button toasts "Comment anchor is no longer in this section" instead of moving the selection.

**Frontend changes**

- `lib/api.ts` — `snapshotsApi` (5 methods) + `commentsApi` (4 methods); Zod schemas for `SnapshotSummary / SnapshotRead / SnapshotDiffResponse / DiffLine / CommentRead`.
- `hooks/useSnapshots.ts` + `hooks/useComments.ts` — TanStack Query hooks with `['snapshots', projectId]` / `['comments', projectId, section, resolved]` invalidation on every mutation.
- `components/manuscript/VersionPanel.tsx` — right-rail collapsible card; new-snapshot dialog (label + description); rows show created-at, label, description, and Diff/Hide + Delete buttons. Diff expands inline under each row.
- `components/manuscript/VersionDiffView.tsx` — renders per-section `<ins>` / `<del>` blocks with emerald/rose background tinting; equal lines render in dim grey. No new dependency.
- `components/manuscript/CommentsRail.tsx` — open comments at top, resolved ones tucked in `<details>` collapsible. Click body → jumps the bound `Editor` to the anchored range. DOMPurify-strips ALL tags from comment body before display.
- `lib/tiptap/extensions/CommentMark.ts` — TipTap Mark with `commentId` attr. Serialised HTML: `<span data-comment data-comment-id="…">…</span>`. Inclusive=false so typing adjacent to a comment doesn't widen it.
- `components/manuscript/BubbleAIMenu.tsx` — appended a `Comment` button next to the AI actions; click opens a textarea, Save POSTs to `commentsApi.create` with the current selection's `from`/`to` as anchors.
- `ManuscriptPage.tsx` — mounted `VersionPanel` + `CommentsRail` in the right rail (xl breakpoint), alongside Figures/Bibliography/References/Abbreviations panels. CommentsRail is filtered to the active manuscript-section tab.

**Test deltas**

- Backend: 1200 → **1227 (+27)**.
  - `test_snapshots_route.py` (10) — create, list, label collision, frontmatter capture, get full blob, diff vs current, diff between two snapshots, identical diff returns empty, delete, project-404, target-404.
  - `test_comments_route.py` (9) — create/list, section + resolved filters, PATCH resolved, PATCH body, delete, anchor range validation, unknown section in query, unknown section in POST, FrontMatter section accepted.
  - `test_security_snapshots_comments_isolation.py` (8) — 4 snapshot tests (list/get/diff/delete 404 for other user, alice's data survives bob's attempted delete) + 3 comment tests + 1 bundle round-trip that exports as alice and re-imports as bob, asserting both new counts arrive and rows are re-tagged.
  - `test_bundle_import.py` updated to allow `manuscript_snapshots`/`manuscript_comments` keys in the lossless round-trip dict.
- Frontend: 131 → **144 (+13 vitest across 4 new files)**.
  - `VersionDiffView.test.tsx` (3) — empty-state, `<ins>`/`<del>` rendering, loading state.
  - `VersionPanel.test.tsx` (3) — list rendering, create dialog opens with empty label input, Diff button toggles to Hide.
  - `CommentsRail.test.tsx` (4) — open vs resolved separation, stale badge logic does NOT fire when anchor in range, jump button calls `setTextSelection({from, to})`, DOMPurify strips `<script>` from bodies.
  - `CommentMark.test.ts` (3) — Mark name + type, `commentId` attribute declared, `renderHTML` emits a `<span data-comment>`.

**One bug found during diff testing**

- The first cut of `_diff_html` returned the unified-diff headers (`--- / +++ / @@ … @@`) as `=` lines, which polluted the response payload — the frontend renders `=` rows in dim grey, so the user saw chatty diff-machinery noise above every changed line. Fix: explicitly skip lines starting with `---`, `+++`, or `@@` before classifying. Captured in test `test_diff_between_two_snapshots` (asserts only `+` and `-` rows survive for the changed line).

**Files created**

- `apps/api/alembic/versions/0012_snapshots_comments.py`
- `apps/api/src/research_api/schemas/snapshots.py`
- `apps/api/src/research_api/schemas/comments.py`
- `apps/api/src/research_api/repositories/snapshots.py`
- `apps/api/src/research_api/repositories/comments.py`
- `apps/api/src/research_api/routes/snapshots.py`
- `apps/api/src/research_api/routes/comments.py`
- `apps/api/tests/test_snapshots_route.py`
- `apps/api/tests/test_comments_route.py`
- `apps/api/tests/test_security_snapshots_comments_isolation.py`
- `apps/web/src/hooks/useSnapshots.ts`
- `apps/web/src/hooks/useComments.ts`
- `apps/web/src/components/manuscript/VersionPanel.tsx`
- `apps/web/src/components/manuscript/VersionDiffView.tsx`
- `apps/web/src/components/manuscript/CommentsRail.tsx`
- `apps/web/src/lib/tiptap/extensions/CommentMark.ts`
- `apps/web/src/components/manuscript/__tests__/VersionDiffView.test.tsx`
- `apps/web/src/components/manuscript/__tests__/VersionPanel.test.tsx`
- `apps/web/src/components/manuscript/__tests__/CommentsRail.test.tsx`
- `apps/web/src/lib/tiptap/extensions/__tests__/CommentMark.test.ts`

**Files modified**

- `apps/api/src/research_api/db/models.py`
- `apps/api/src/research_api/main.py`
- `apps/api/src/research_api/routes/export.py`
- `apps/api/src/research_api/services/export/bundle_export.py`
- `apps/api/src/research_api/services/export/bundle_import.py`
- `apps/api/src/research_api/schemas/__init__.py`
- `apps/api/tests/test_bundle_import.py`
- `apps/web/src/lib/api.ts`
- `apps/web/src/components/manuscript/BubbleAIMenu.tsx`
- `apps/web/src/components/manuscript/ManuscriptEditor.tsx`
- `apps/web/src/routes/ManuscriptPage.tsx`

**Git:** tagged `phase-11`.

---

## 2026-05-18 · Mini-phase 10 — ICMJE structured front-matter ✅ COMPLETE

**Plan:** `docs/superpowers/plans/2026-05-18-post-e2e-roadmap.md` (Mini-phase 10 section)

**Items addressed:** #1.

**Backend changes**

- New migration `0011_icmje_frontmatter.py` (down_revision 0010) with 5
  tables: `authors`, `affiliations`, `author_affiliations` (m2m UNIQUE pair),
  `contributions` (UNIQUE author_id+role), `project_frontmatter` (1:1 with
  project, JSON columns for funders + structured_abstract).
- `db/models.py` — Author / Affiliation / AuthorAffiliation / Contribution
  / ProjectFrontmatter ORM classes. Author has a contiguous `position`
  invariant within (project_id, user_id).
- `schemas/frontmatter.py` — `CreditRole` Literal of 14 NISO-CRediT roles,
  `validate_orcid()` with ISO/IEC 7064 MOD-11-2 checksum (uppercase X = 10),
  light-weight regex email validator (avoids the optional
  `pydantic[email]` dep).
- `repositories/frontmatter.py` — `SqliteAuthorRepository` /
  `SqliteAffiliationRepository` / `SqliteContributionRepository` /
  `SqliteFrontmatterRepository`. All scoped by user_id. Reorder uses the
  same `+1000` two-step UPDATE trick as `figures.py`. The corresponding-
  author single-row invariant is enforced via a single
  `UPDATE authors SET is_corresponding=false WHERE project_id=? AND
  user_id=? AND id != ?` BEFORE any insert/update sets the flag.
- `routes/frontmatter.py` — 12 endpoints under `/api`: authors CRUD +
  reorder + set-corresponding, affiliations CRUD + reorder, m2m
  link/unlink under `/api/authors/{id}/affiliations/{id}`, contributions
  set/clear, frontmatter GET (auto-creates) / PATCH.
- `services/export/docx_export.py` — accepts an optional
  `FrontMatterPayload` dataclass; when present, renders authors with
  numbered affiliation superscripts (first-encounter ordering), a
  corresponding-author email line, COI / funding / ethics paragraphs
  after References, and optional structured abstract replacing the
  freeform Abstract section. Backwards compatible: omitting the payload
  reproduces the pre-Phase-10 title page exactly.
- `services/export/pdf_export.py` — same surface, reportlab platypus
  flowables.
- `services/export/bundle_export.py` + `bundle_import.py` — extended to
  round-trip the 5 new tables. Import re-stamps user_id, mints fresh PKs,
  rewires FKs through `author_map` / `affiliation_map`, and **defensively
  caps `is_corresponding=true` to one row per project** even if the
  incoming bundle smuggles two.
- `routes/export.py` — DOCX / PDF / bundle export endpoints now load the
  front-matter rows and pass them through.

**Frontend changes**

- `lib/api.ts` — `frontmatterApi` with `authors` / `affiliations` /
  `link` / `contributions` / `frontmatter` sub-namespaces. TS literal
  union for the 14 CRediT roles. Zod schemas for every server payload.
- `components/frontmatter/AuthorsEditor.tsx` — `@dnd-kit/sortable` list
  with per-row fields (full name, ORCID, email, corresponding checkbox)
  and per-row affiliation toggle chips.
- `components/frontmatter/AffiliationsEditor.tsx` — drag-sortable list
  with name + address + city + country.
- `components/frontmatter/ContributionsMatrix.tsx` — authors × 14 CRediT
  roles checkbox grid; click toggles via per-author per-role
  `contributions.set` / `.clear`.
- `components/frontmatter/EthicsFundingForm.tsx` — free-text COI,
  funding statement + dynamic funder list (name + grant id), IRB,
  approval number, consent.
- `components/frontmatter/StructuredAbstract.tsx` — opt-in toggle
  reveals four textareas (Background / Methods / Results / Conclusions).
  When disabled (default), the freeform Abstract section is used.
- `components/frontmatter/FrontMatterPanel.tsx` — wrapper that hosts
  the five sub-section tabs.
- `routes/ManuscriptPage.tsx` + `SectionTabs.tsx` — new "Front matter"
  tab inserted before Abstract; mounts `FrontMatterPanel` instead of
  the TipTap editor when selected.

**Test deltas**

- Backend: **1122 → 1200 (+78 tests across 6 new files)**
  - `test_frontmatter_schemas.py` (18) — ORCID checksum (valid + invalid),
    14-role enum, Funder min-length, partial PATCH dump.
  - `test_frontmatter_repository.py` (19) — position assignment,
    corresponding-author single-row, cross-project isolation, reorder
    rejection on foreign ids, m2m cross-project rejection, contributions
    idempotent, frontmatter auto-create.
  - `test_frontmatter_route.py` (9) — happy-path CRUD round-trip via
    live ASGI app.
  - `test_security_frontmatter_isolation.py` (19) — every endpoint
    returns 404 / 422 for the other user.
  - `test_frontmatter_export.py` (7) — DOCX emits authors + ethics
    block, structured abstract replaces freeform when enabled, HTML
    chars escaped, PDF byte-magic check.
  - `test_frontmatter_bundle_round_trip.py` (2) — full export → re-import
    as a different user; corresponding-author cap enforced on hostile
    bundle.
  - `test_bundle_import.py` — extended the existing count-dict assertion
    with the 5 new keys (no logic change).
- Frontend: **117 → 131 (+14 vitest across 3 new files)**
  - `lib/__tests__/frontmatterApi.test.ts` (10) — Zod schema parsing for
    Author / Affiliation / Contribution / ProjectFrontmatter + CRediT
    role enum exhaustiveness.
  - `components/frontmatter/__tests__/FrontMatterPanel.test.tsx` (2) —
    renders 5 sub-section tabs, starts on Authors.
  - `components/frontmatter/__tests__/StructuredAbstract.test.tsx` (2) —
    sub-fields hidden when toggle off, visible after toggling, PATCH
    fires correctly.

**Decisions logged**

- **ORCID checksum.** Implemented the ISO/IEC 7064 MOD-11-2 algorithm
  documented at orcid.org — the final character is digit 0-9 or `X` for
  the value 10. Inputs are uppercased before validation so a lowercase
  `x` is accepted as a canonical `X`. We do NOT call orcid.org for v1.
- **Corresponding-author single-row enforcement.** All three write paths
  (create, update, set-corresponding endpoint) call a private
  `_clear_corresponding(project_id, user_id, exclude_id)` BEFORE setting
  the target row's flag. The bundle importer applies the same cap by
  consuming a `correspondings_remaining = 1` counter while inserting
  authors so a malicious bundle cannot bypass the invariant.
- **Front matter UI placement.** Mounted as a NEW LEFTMOST tab in the
  manuscript section tabbar ("Front matter"), not as a dialog. The tab
  shows 5 sub-sections (Authors, Affiliations, Contributions, Ethics &
  funding, Structured abstract) so all ICMJE fields live in the same
  workspace as the body sections.
- **Backwards compatibility.** `structured_abstract_enabled` defaults
  to FALSE so existing manuscripts keep using the freeform Abstract.
  `render_docx` / `render_pdf` accept `frontmatter` as optional, so
  pre-Phase-10 callers reproduce their original output.
- **Defence in depth.** All user-supplied front-matter strings flow
  through `html.escape` before being emitted into DOCX / PDF, mirroring
  the existing `replace_cite_tokens_with_markup` discipline.

**Acceptance bar**

- [x] 5 new tables; migration `0011` clean upgrade.
- [x] ORCID validates the canonical iD + checksum (incl. uppercase X).
- [x] At most one corresponding author per project — enforced server-side.
- [x] All 12 frontmatter endpoints scoped by user_id + project_id (19
  isolation tests).
- [x] DOCX / PDF exports emit ICMJE block when present; legacy projects
  unchanged.
- [x] Bundle round-trip carries all 5 new tables and re-stamps user_id.
- [x] `cd apps/web && npx tsc -p tsconfig.app.json --noEmit` clean.
- [x] 1200 backend tests pass; 131 frontend vitest pass.

**Files created**

- `apps/api/alembic/versions/0011_icmje_frontmatter.py`
- `apps/api/src/research_api/schemas/frontmatter.py`
- `apps/api/src/research_api/repositories/frontmatter.py`
- `apps/api/src/research_api/routes/frontmatter.py`
- `apps/api/tests/test_frontmatter_schemas.py`
- `apps/api/tests/test_frontmatter_repository.py`
- `apps/api/tests/test_frontmatter_route.py`
- `apps/api/tests/test_security_frontmatter_isolation.py`
- `apps/api/tests/test_frontmatter_export.py`
- `apps/api/tests/test_frontmatter_bundle_round_trip.py`
- `apps/web/src/components/frontmatter/AuthorsEditor.tsx`
- `apps/web/src/components/frontmatter/AffiliationsEditor.tsx`
- `apps/web/src/components/frontmatter/ContributionsMatrix.tsx`
- `apps/web/src/components/frontmatter/EthicsFundingForm.tsx`
- `apps/web/src/components/frontmatter/StructuredAbstract.tsx`
- `apps/web/src/components/frontmatter/FrontMatterPanel.tsx`
- `apps/web/src/lib/__tests__/frontmatterApi.test.ts`
- `apps/web/src/components/frontmatter/__tests__/FrontMatterPanel.test.tsx`
- `apps/web/src/components/frontmatter/__tests__/StructuredAbstract.test.tsx`

**Files modified**

- `apps/api/src/research_api/db/models.py`
- `apps/api/src/research_api/main.py`
- `apps/api/src/research_api/routes/export.py`
- `apps/api/src/research_api/services/export/docx_export.py`
- `apps/api/src/research_api/services/export/pdf_export.py`
- `apps/api/src/research_api/services/export/bundle_export.py`
- `apps/api/src/research_api/services/export/bundle_import.py`
- `apps/api/tests/test_bundle_import.py`
- `apps/web/src/lib/api.ts`
- `apps/web/src/components/manuscript/SectionTabs.tsx`
- `apps/web/src/routes/ManuscriptPage.tsx`

**Git:** tagged `phase-10`.

---

## 2026-05-18 · Mini-phase 9 — Citation correctness + manuscript search ✅ COMPLETE

**Plan:** `docs/superpowers/plans/2026-05-18-post-e2e-roadmap.md` (Mini-phase 9 section)

**Items addressed:** #13, #14, #15, #16.

**Backend changes**

- `services/export/bibliography.py` — `build_bibliography` now branches on
  citation style: Vancouver / IEEE keep first-citation-of-appearance;
  APA / Harvard sort alphabetically by first author's surname
  (case-insensitive), with `(year ASC, title ASC, first-citation-position)`
  tie-break. Missing-year articles sort after concrete years via a
  10**6 sentinel. Empty-authors articles bucket consistently.
- `services/citation_format.py` — new `consolidate_inline_clusters(html, style)`
  walks adjacent `<sup data-citation>` tokens (only whitespace between them
  counts as adjacent) and:
  - Vancouver/IEEE: `[1][2][3]` → `[1-3]` (range when ≥3 contiguous), `[1,2]`
    for two-element runs, `[1,3,5]` for non-contiguous, `[1-3,5]` for mixed.
    Sorts before range detection so `[3][1][2]` also folds to `[1-3]`.
  - APA/Harvard: merges into a single paren with semicolon-separated entries,
    deduped — `(Smith, 2024; Patel, 2022; Brown, 2021)`.
  Cluster detection uses a single regex (`_CLUSTER_RE`) with a `(?:WS SUP)+`
  repeat group so adjacent runs are captured in one match.
- `routes/export.py` — new `_consolidate_sections` runs the consolidator on
  every section right before passing them to `render_docx` / `render_pdf`.
  Uses a lightweight `_ConsolidatedSection` slotted class so the ORM row is
  never mutated.

**Frontend changes**

- New `components/manuscript/ManuscriptSearchPanel.tsx` — popover that opens
  inside the editor pane, with a debounced (150 ms) input, hits grouped by
  section, per-hit ~80 char preview with the match highlighted, Cmd-G / F3
  next, Shift variants prev, Enter to jump, Esc to close. Strips
  `<sup data-citation>…</sup>` blocks before searching so users do not match
  `[N]` literals.
- `routes/ManuscriptPage.tsx` — `useEffect` captures `keydown` in capture
  phase; intercepts Cmd-F / Ctrl-F ONLY when the focused element is inside
  the manuscript editor pane wrapper (so the browser's native Find stays
  intact everywhere else). Wraps the editor in a `relative` div with a ref;
  the search panel is rendered absolutely positioned inside that ref.
  Click-to-jump walks the ProseMirror doc's text nodes, counts to the
  match's `matchIndex`, places a TextSelection, and calls `scrollIntoView`.

**Test deltas**

- Backend: **1078 → 1122 (+44 tests)**:
  - `tests/test_bibliography_ordering.py` (13) — parametrised across all 4
    styles × multiple cite-order scenarios (alphabetical, case-insensitive,
    year tie-break, title tie-break, missing year, empty authors).
  - `tests/test_citation_cluster.py` (30) — 2/3/4-contiguous, gaps,
    out-of-order, dedup, idempotency, trailing-period edge case, all 4
    styles.
  - `tests/test_export_route.py` (+1) — integration: adjacent numeric sups
    collapse to `[1-3]` in DOCX output.
- Frontend: **108 → 117 (+9 vitest)** — `ManuscriptSearchPanel.test.tsx`
  covers `stripHtmlForSearch`, empty-query path, multi-section matches,
  preview length cap, case-insensitivity, jump callback, Esc closes,
  F3 / Shift-F3 navigation.

**Decisions logged**

- Cluster grouping window: ONLY whitespace adjacency counts. A trailing
  period, comma, or any non-whitespace character breaks the cluster.
- Sentence-end edge case: `[1][2].` — the period stays outside the cluster
  because it never gets matched by `_CLUSTER_RE`; the consolidated sup
  emits `[1,2].` correctly (verified by `test_consolidator_handles_trailing_period`).
- Adversarial author-year strings (parens inside the inner text) are escaped
  via the same `html.escape` pass used in `replace_cite_tokens_with_markup`
  so a user-provided `Smith, "evil"` cannot break out of the `data-article-id`
  attribute.
- Cmd-F intercept condition: capture-phase keydown listener, `e.preventDefault`
  ONLY when `document.activeElement` is inside the manuscript editor pane
  wrapper. Outside that zone (sidebars, top nav, library page), the
  browser's native Find runs normally.

**Acceptance bar**

- [x] APA + Harvard reference list orders alphabetically by first author surname.
- [x] Vancouver + IEEE keep first-citation-of-appearance numbering.
- [x] `[1][2][3]` → `[1-3]` for Vancouver/IEEE; `(Smith, 2024)(Patel, 2022)`
  → `(Smith, 2024; Patel, 2022)` for APA/Harvard.
- [x] Cmd-F opens the cross-section search panel only when focus is in
  the manuscript editor; native browser Find preserved elsewhere.
- [x] Cmd-G / F3 (next), Shift-Cmd-G / Shift-F3 (prev), Esc close.
- [x] `cd apps/web && npx tsc -p tsconfig.app.json --noEmit` clean (the
  pre-existing baseUrl deprecation warning is unrelated to this phase).

**Files created**

- `apps/api/tests/test_bibliography_ordering.py`
- `apps/api/tests/test_citation_cluster.py`
- `apps/web/src/components/manuscript/ManuscriptSearchPanel.tsx`
- `apps/web/src/components/manuscript/__tests__/ManuscriptSearchPanel.test.tsx`

**Files modified**

- `apps/api/src/research_api/services/export/bibliography.py`
- `apps/api/src/research_api/services/citation_format.py`
- `apps/api/src/research_api/routes/export.py`
- `apps/api/tests/test_export_route.py`
- `apps/web/src/routes/ManuscriptPage.tsx`
- `POLISH.md`

**Git:** tagged `phase-9`.

---

## 2026-05-18 · Phase 8.5 — Stats visualisation ✅ COMPLETE

**Plan:** `docs/superpowers/plans/2026-05-18-phase-8p5-stats-visualisation.md`

**Backend additions**

- New service subtree `services/stats/charts/` with shared `_base.py` pinning `matplotlib.use('Agg')` (server-side, headless) plus `fig_context`/`fig_to_png_bytes`/`fig_to_data_uri` helpers. Storage shape is the documented contract `{"format": "png", "data_uri": "data:image/png;base64,...", "byte_size": N}`.
- Five pure-function chart renderers — every one a `(df, var_spec) -> dict` and every one wrapped in a `fig_context` so figures close on exception:
  - `box_plot.py` — boxplot + strip overlay for `independent_t`, `mann_whitney`, `one_way_anova`, `kruskal_wallis`, `rm_anova` (long-form melt).
  - `histogram.py` — single-variable histogram + KDE for the difference distribution of `paired_t` / `wilcoxon_signed`. Bonus `render_categorical_counts` for `chi_squared` / `fisher_exact` side-by-side bars.
  - `qq_plot.py` — scipy.probplot Q-Q normality diagnostic.
  - `scatter_plot.py` — seaborn `regplot` for `pearson` (linear), `spearman` (lowess), `linear_regression` / `multiple_linear` (first predictor) and `logistic` (first predictor). Constant-x falls back to plain scatter.
  - `km_curve.py` — Kaplan-Meier survival curves with `add_at_risk_counts` band; reused for `cox_ph` against the first covariate.
- Single dispatcher `select_and_render(test_key, df, variables)` in `charts/__init__.py` with a per-test_key callable map; every renderer call is wrapped in `try/except Exception` returning `None` on failure. Failures log a WARNING.
- One-line wire-up in `services/stats/runner.run` — after the existing handler returns its `TestResult`, the dispatcher's chart dict replaces the (frozen) result via `dataclasses.replace(result, chart=...)`. Pre-Phase-6 KM "series" chart shape is fully replaced (one regression test in `test_stats_runner.py` updated to assert the new PNG shape; numerics path unchanged).
- No new pip deps (matplotlib + seaborn already installed by pingouin in Phase 6), no migration, no schema change.

**Frontend additions**

- New `ChartImage.tsx` component (img + shadcn Dialog zoom + Download PNG anchor against the `data:image/png;base64,...` URI). Pure presentation, no network.
- `AnalysisResultCard.tsx` now renders `<ChartImage>` between the numbers grid and the assumption pills. A defensive `isChartDict` type-guard ignores any malformed older chart payloads (the Phase 6 `{type, series}` shape is silently skipped at the UI boundary).

**Test deltas**

- Backend: **765 → 849 (+84 tests)** across `test_stats_chart_base.py` (5), `test_stats_chart_box_plot.py` (7), `test_stats_chart_histogram.py` (7), `test_stats_chart_qq_plot.py` (6), `test_stats_chart_scatter_plot.py` (5), `test_stats_chart_km_curve.py` (6), `test_stats_chart_dispatch.py` (41 — parametrised over every test_key + numerics-parity regression + monkeypatched-failure path + helper unit tests), `test_stats_chart_resilience.py` (7 — single-level group, all-NaN, constant predictor, end-to-end route persists chart, end-to-end route persists `chart=None` on simulated failure).
- Frontend: **74 → 81 (+7 vitest)** — `ChartImage.test.tsx` (4) and `AnalysisResultCard.test.tsx` (3, covering present-chart / null-chart / malformed-chart slots).
- All 488+ pre-existing stats route tests stay green. The single `test_kaplan_meier_known_answer` assertion was migrated from `chart["type"]` to `chart["format"]`/`chart["data_uri"]`.

**Acceptance bar**

- [x] Box / histogram / Q-Q / scatter / KM (Tasks 2–6) — PNG magic bytes + state-leak checks + dispatcher parametric across all 18 test keys.
- [x] Server-side `Agg` rendering (Task 1) — pinned at the top of `_base.py`; figures closed on exception.
- [x] Storage shape `{format, data_uri, byte_size}` (Task 7) — end-to-end verified via `/analyses/{id}/run` route test that base64-decodes the PNG header.
- [x] Failure path (Task 8) — monkeypatched renderer raises → `result.chart is None`, numerics intact, HTTP 200, WARNING logged.
- [x] FE renders the chart with zoom + download (Tasks 9–10) — defensive type guard at the UI boundary keeps old-shape chart payloads invisible.

**Decisions / out-of-scope**

- PNG-only in v1 (SVG would require ProseMirror schema work — deferred).
- Partial regression plots for `multiple_linear` / `logistic` substituted with first-predictor scatter — deferred.
- `icc` / `cohen_kappa` deliberately produce no chart (agreement tables work poorly as plots).
- Task 11 (chrome-devtools-mcp E2E smoke) and Task 12's `/security-review` + tag deferred to the bundled E2E phase at the end of the autonomous run.

**Seaborn quirk:** seaborn 0.13.2 emits a `PendingDeprecationWarning` from `categorical.py` about `vert: bool` deprecation in `ax.bxp`. Harmless and originates inside seaborn, not our code — surfaced in the test summary but no action needed.

**Next:** Phase 8.6 — ingestion (PubMed / Crossref / RIS / BibTeX / dedup).

---

## 2026-05-18 · Phase 7.5 — Meta-analysis ✅ COMPLETE

**Plan:** `docs/superpowers/plans/2026-05-18-phase-7p5-meta-analysis.md`

**Backend additions**

- Two new tables (`meta_analyses` + `meta_inputs`) with migration `0008_meta_analysis.py` (`down_revision = '0007'`). Both tables `user_id`-scoped. UNIQUE `(meta_id, article_id)`.
- New service tree `services/meta/` with five pure-function modules:
  - `effect_sizes.py` — MD / SMD (Hedges' g with small-sample correction) / log-OR / log-RR / log-HR / Fisher-z, all with Cochrane-style zero-cell continuity correction for OR & RR, and HR computable from either `(log_hr, se_log_hr)` or `(hr, ci_low, ci_high)`.
  - `pooling.py` — inverse-variance fixed-effects + DerSimonian-Laird random-effects, both returning `PooledResult(estimate, se, ci_low, ci_high, z, p, weights, model)`.
  - `heterogeneity.py` — Cochran Q, df, p, I² (Higgins), τ² (DL).
  - `forest_plot.py` — matplotlib `Agg`-backend renderer returning PNG bytes; supports subgroup blocks; per-row diamond + pooled diamond; `_build_figure` exposed for testability.
  - `funnel_plot.py` — scatter of effect vs SE (axis inverted) with pseudo-95% CI funnel lines.
- AI Protocol method `AIProvider.interpret_meta_analysis(...)`. Real Gemini implementation + FakeAI stub + UnconfiguredAIProvider stub. Prompt at `services/ai/prompts/meta_interpretation.py` preserves every `[CITE_<article_id>]` token verbatim and embeds back-transformed pooled+CI for OR/RR/HR.
- Repository `SqliteMetaRepository` with defence-in-depth `MetaArticleMismatch` when an input references an article from another project.
- New routes submodule `routes/reviews_meta.py` mounted under `/api` — full CRUD, `/run`, `/forest.png`, `/funnel.png`, `/interpret`, `/push`. Pushes idempotently via the existing `_push_to_section` helper; new class hook `meta-analysis-forest` registered in `_BLOCK_TAG_BY_CLASS`.

**Frontend additions**

- `metaAnalysisApi` in `lib/api.ts` (kept distinct from the pre-existing `metaApi` for /health which is used elsewhere).
- `useMeta.ts` TanStack hooks mirroring the `useAnalyses` shape (`useMetaList`, `useMetaDetail`, `useCreateMeta`, `useRunMeta`, `useInterpretMeta`, `usePushMeta`, `useUpsertMetaInput`, …).
- Six components under `components/review/meta/`: `MetaAnalysisForm`, `PerStudyInputs`, `ForestPlotView`, `FunnelPlotView`, `MetaResultCard`, `MetaListPanel`.
- `SystematicReviewPage.tsx` extended with a sixth tab `Meta-analysis` between extraction and PRISMA, with a `MetaTabContent` shell that pairs a left-rail list with a detail pane.

**Test deltas**

- Backend: **656 → 765 (+109 tests)** across:
  - `test_meta_models.py` (3), `test_meta_effect_sizes.py` (12), `test_meta_pooling.py` (8), `test_meta_heterogeneity.py` (8).
  - `test_meta_forest_plot.py` (6), `test_meta_funnel_plot.py` (4).
  - `test_meta_prompt.py` (7), `test_meta_ai_provider.py` (6).
  - `test_meta_repository.py` (9).
  - Routes: `test_reviews_route_meta_crud.py` (9), `..._run.py` (9), `..._plots.py` (5), `..._interpret.py` (6), `..._push.py` (7).
  - Security regression: `test_security_meta_isolation.py` (10) — every endpoint + subgroup-variable resolution is user-scoped.
- Frontend: **71 → 74 (+3 vitest)** — `metaApi.test.ts` exercises the two new zod schemas and the absolute-URL builders.

**Acceptance bar**

- [x] Per-metric effect-size computation (Task 3) — formulae hand-checked against the Cochrane Handbook §10 worked examples (especially the SMD §10.5 example with `mean_a=10, sd_a=4, n_a=40`, `mean_b=8, sd_b=4, n_b=40` → `g ≈ 0.495`, `vi ≈ 0.0515`).
- [x] Fixed + DL random pooling (Task 4) — hand-computed two-study answer `yi=[0.5,0.3]`, `vi=[0.04,0.05]` → `yi_bar ≈ 0.4111`, `se ≈ 0.149`.
- [x] Q + df + p + I² + τ² heterogeneity (Task 5).
- [x] Forest PNG + funnel PNG (Tasks 6/7) — magic-byte check + no matplotlib state leak.
- [x] Subgroup analysis (Task 11) — `subgroup_variable` resolved via owner's `extraction_records.fields` only.
- [x] AI interpretation with `[CITE_<article_id>]` per pooled study (Tasks 8/13) — the prompt's "POOLED STUDIES" block lists every token and the model is told not to invent new ones.
- [x] Push to Results (Task 14) — idempotent via `class="meta-analysis-forest"` hook.
- [x] Meta-analysis tab in /review (Task 19) — URL state `?tab=meta&meta=<id>`.
- [x] Cross-user / cross-project security regression (Task 15) — all 10 isolation tests green.

**Decisions / tactical notes**

- Random-effects τ² estimator: **DerSimonian-Laird only** for v1 (REML / Paule-Mandel deferred).
- Plots are **PNG only** for v1 (SVG forest deferred per plan).
- HR can be entered as `(log_hr, se_log_hr)` or `(hr, hr_ci_low, hr_ci_high)` — the latter back-calculates `se` via `(ln(hi) - ln(lo)) / (2 · 1.959964)`.
- Frontend pre-existing `metaApi` (for `/health`) untouched; meta-analysis client is `metaAnalysisApi` to avoid breaking Topbar/Settings/Health imports.
- E2E browser smoke (Task 20) deferred — pytest route + security tests cover the full HTTP surface.

**Tag:** to be created (`phase-7p5`) after BUILD_LOG commit.

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

## 2026-05-17 · Phase 3 — PDF Reader & Annotation Engine ✅ COMPLETE

**Tag:** `phase-3`
**Commits:** ~12 atomic commits. Plan at `docs/superpowers/plans/2026-05-17-phase-3-pdf-reader.md`.

**What's running**

- **Backend**: `Highlight` + `ArticleNote` ORM with `(article_id, user_id)` unique composite for upsert; alembic 0003; CRUD + AI summarise endpoint with provider-error mapping to 429/422/503 (no detail leak); per-article notes upsert.
- **Frontend**: react-pdf with Vite-bundled pdfjs worker. PDF bytes cached in IndexedDB. `pdfCoords` library (TDD) converts DOM selection rects ↔ page-relative percentages. `SelectionCapture` (window mouseup → percent payload → POST). `HighlightOverlay` recomputes pixel rects on every render so any zoom is exact. `HighlightNotePopover` is **anchored to the clicked highlight** via Radix Popover virtualRef and **auto-opens with focus on the paraphrase field** when a new highlight is created. `ArticleNotesRail` right column with 700ms debounced autosave and click-to-jump-to-page.

**Acceptance bar (live in-browser verification)**

- [x] Real text selection → highlight rect aligned **pixel-perfect** to the underlying text: highlight (446, 467, 322×12) vs text (446, 468, 322×10). Δx=0, Δw=0, Δy=−1, Δh=+2 (browser sub-pixel slop on selection rects). Visually identical.
- [x] **Zoom invariance mathematically verified**: 100% → page 612×792, highlight w=516. 150% → page 918×1188 (×1.5 exact), highlight w=774 (×1.5 exact). Coords scale proportionally.
- [x] **Popover anchored to highlight** at (447, 486) sitting just below highlight at (446, 467) — Δx=+1, Δy=+19 (6px sideOffset). Auto-focused textarea with placeholder "How do you want this to read in your manuscript?".
- [x] AI Summarise: live Gemini returned *"Anterior approach offers measurable short-term advantages."* from `gemini-2.5-flash` (chain still resolving correctly).
- [x] Right-rail Notes PUT + GET roundtrip; "Saved Xs ago" indicator live.
- [x] 106 backend tests + 7 frontend (pdfCoords) tests pass.

**Per the user's mid-build feedback (verified)**

> "Make sure highlights accurately identify the text which is highlighted. Also the user should be able to paraphrase and make notes next to the highlights if needed, so that should also get compiled with citation in the final section."

1. ✅ **Accuracy**: selection capture pulls real DOM rects (`range.getClientRects()`) — pixel-aligned to the actual text glyphs.
2. ✅ **Inline paraphrase**: popover anchors directly below the highlight and auto-focuses the paraphrase textarea so the user can type immediately. Autosaves at 600ms.
3. ✅ **Will compile in Phase 4**: each highlight row carries `{selected_text, user_note, ai_summary, page_number, section}` and joins to `articles` for `(Author, year, journal, DOI)` — the Compilation module will assemble these into cards (highlighted text + user paraphrase + citation) per section colour.

**Security review (2 MED + 3 LOW all fixed inline)**

- MED: SUMMARISE_PROMPT got the same "untrusted passage" framing as EXTRACTION_PROMPT.
- MED: HighlightUpdate.user_note/ai_summary bounded (max_length).
- LOW: BoundingCoords.rects capped at 64; ArticleNoteUpsert.content capped at 100k; BoundingRect rejects inverted rects via model_validator.

**Incidents handled inline**

1. shadcn popover install dropped file into a stray `@/...` literal folder until the Phase 2 tsconfig fix kicked in — re-confirmed.
2. `unique=True` on ArticleNote.article_id would block multi-user upsert — switched to composite unique index at the model level so the migration is right first time.
3. **Hardcoded test coordinates appeared below the actual text** — discovered the user feedback "make sure highlights accurately identify the text" was right because my E2E test data was synthetic. Switched to driving the real SelectionCapture path through DOM, verified pixel alignment, and added the anchored popover.
4. **Rules of Hooks violation** in HighlightNotePopover (useRef after early return) caused the popover to crash on open. Fixed by hoisting all hook calls above the conditional return.

**Test counts**

- Backend: 106 pass (was 84 after Phase 2, +22 in Phase 3)
- Frontend: 7 vitest pass (pdfCoords transforms + selection extractor)
- New test files: test_highlight_repository, test_note_repository, test_highlights_route, test_notes_route, lib/__tests__/pdfCoords.test.ts

**Open items**

- `POLISH.md`: unchanged
- `DECISIONS.md`: unchanged
- `QUESTIONS.md`: still empty
- `DEFERRED.md`: unchanged

**Next:** Phase 4 — Compilation module. This is where the value lives: highlights + paraphrases + citations from every article in the project get aggregated by section colour, drag-reordered, and assembled into AI-drafted paragraphs grounded in the user's actual annotations.

---

## 2026-05-18 · Phase 4 — Compilation Module ✅ COMPLETE

**Tag:** `phase-4`
**Commits:** ~10 atomic commits. Plan at `docs/superpowers/plans/2026-05-17-phase-4-compilation.md`.

**What's running**

- **Backend**:
  - `citation_format` service: Vancouver/APA/Harvard inline formatting + `[CITE_aN]` token replacement (unknown tokens left visible)
  - `ManuscriptSection` ORM + alembic 0004 + composite-unique upsert repo
  - `CompilationRepository` (highlights JOIN articles, sorted)
  - `AIProvider` extended: `generate_card_draft`, `generate_section_draft` (CardContext / SectionDraftContext)
  - Routes: `GET /compilation/{colour}`, `POST /highlights/{id}/draft`, `POST /compilation/{colour}/draft`, `PATCH /compilation/{colour}/order`, `GET|PUT /sections/{name}`
- **Frontend**:
  - `compilationApi` + `manuscriptApi` with full zod schemas
  - `AISuggestionBlock` reusable Accept/Edit/Reject (used in Phase 5 too)
  - `ColourTabs` URL-synced (`?tab=intro|method|results|discussion`) with animated underline
  - `SortableCardList` via dnd-kit
  - `CompiledCard` (colour stripe, source quote in section fill, paraphrase, citation chip, Generate sentence button, Accept → append to manuscript_section)
  - `SectionDraftPanel` (Generate paragraph from N cards, Accept → replace section content with confirmation if non-empty, used_citations list)
  - Real `CompilePage` replacing the Phase 1 stub; optimistic reorder via TanStack Query

**The citation safety contract** — the heart of this phase:

1. Server builds a per-card token map (`a1`, `a2`, …) from the project-scoped compilation rows
2. Gemini sees tokens like `[CITE_a1]` in the prompt; **never sees author names**
3. Gemini emits text with those tokens
4. Server replaces tokens with the formatted citation from the authoritative `articles` row (style chosen by `projects.citation_style`)
5. Unknown tokens (hallucinated) are left visible — reviewers see them

**Acceptance bar (live-verified)**

- [x] 4 colour tabs (Introduction/Methodology/Results/Discussion) with correct counts
- [x] Cards aggregate highlights of that colour **across all articles** in the project — verified with 2 articles
- [x] Each card shows: source text · paraphrase · citation chip (e.g. `CHOUDHARY & JOHNSON, 2024`)
- [x] Drag-to-reorder via dnd-kit; sort_order persists
- [x] **Per-card live Gemini draft**: returned *"The optimal surgical approach for total hip arthroplasty (THA) continues to be debated **(Choudhary & Johnson, 2024)**."*
- [x] **Section-level live Gemini paragraph**:

> *"A total of 412 patients were prospectively enrolled at our institution between January 2021 and December 2023 **(Choudhary & Johnson, 2024)**. This cohort comprised 198 anterior cases and 214 posterior cases **(Choudhary & Johnson, 2024)**. The prospective enrolment methods were consistently applied throughout the study, ensuring comparability across all recruited participants **(Patel et al., 2022)**."*

- [x] References row: `Choudhary & Johnson, 2024 · Patel et al., 2022`
- [x] Accept on a card pushes the sentence into `manuscript_sections.{section}.content` (verified via direct GET roundtrip — word_count: 17)
- [x] All citations in Gemini output came from the database, not the model

**Security review (1 MED + 4 INFO)**

- **MED → FIXED**: reorder route initially only filtered by `user_id`; could mutate sort_order on highlights in *other* projects/colours the same user owns. Fix: validate each item against the project+colour view's whitelist; silently skip out-of-scope IDs. Regression test added.
- INFO: prompt-injection framing on both card and section prompts confirmed
- INFO: AI error mapping (429/422/503) leaks no provider detail
- INFO: user-isolation gated on every endpoint via project lookup
- INFO: unknown CITE token behaviour (leave visible) is the intended contract

**Test counts**

- Backend: **139 pass** (was 106 after Phase 3, +33 in Phase 4)
- Frontend: 7 vitest pass (unchanged)
- New test files: test_citation_format (10), test_manuscript_section_repository (5), test_compilation_repository (4), test_compilation_route (8 incl. security regression), test_manuscript_sections_route (6)

**Open items**

- `POLISH.md`: unchanged
- `DECISIONS.md`: CITE token contract is implicit in the citation_format docstring + commit messages — could promote to a formal ADR in DECISIONS later
- `QUESTIONS.md`: still empty
- `DEFERRED.md`: unchanged

**Next:** Phase 5 — Manuscript editor. TipTap with floating AI toolbar (Improve/Shorten/Formalise/Add Transition), `@` citation insert with auto-numbering, abbreviation tracker, reference integrity checker.

---

## 2026-05-18 · Phase 5 — Manuscript Editor ✅ COMPLETE

**Goal**

Turn the Compile drafts into a real prose authoring surface: TipTap-based rich text editor with section tabs, an AI floating toolbar (Improve / Shorten / Formalise / Add Transition), `@`-trigger citation picker with continuous auto-numbering across all sections, an abbreviation scanner, a reference-integrity panel, and a read-only Final view that concatenates all sections with a Vancouver bibliography.

**What shipped**

Backend (5 files, 1 migration):

- `services/abbreviation_scanner.py` — regex pass over manuscript text, detects `Long Form (LF)` patterns
- `db/models.py` + `alembic/versions/0005_abbreviations.py` — `Abbreviation` table, composite unique `(project_id, user_id, short_form)`, 200-item cap enforced at the schema layer
- `repositories/abbreviations.py` — `list_for_project`, transactional `replace_all`, `delete`
- `routes/abbreviations.py` — GET list / PUT replace / DELETE
- `services/ai/gemini.py` — implemented `assist_writing` (was a NotImplementedError stub); new `prompts/writing_assist.py` carries the **"preserve every [CITE_xxx] token verbatim"** rule
- `routes/writing.py` — `POST /api/writing/assist` with input cap 4_000 chars; classified errors (429/422/503)
- `services/citation_format.py` — added `bibliography_entry()` (Vancouver style)

Frontend (12 files):

- `lib/tiptap/extensions/Citation.ts` — inline atomic Node with `articleId` attr, parses `sup[data-citation]`, renders via React NodeView
- `lib/tiptap/extensions/CitationNodeView.tsx` — reads `useCitationNumbers` store, renders `[N]` (or `[?]`, `[…]`)
- `lib/tiptap/citationEngine.ts` — `numberCitationsFromDoc/Html/Across` for per-section and continuous numbering
- `lib/tiptap/citationNumbers.ts` — Zustand store: `articleId → number` map
- `lib/citationSerialize.ts` — `htmlToAiSafeText` / `aiSafeTextToHtml`, the round-trip used at the AI boundary
- `lib/bibliographyFormat.ts` — client-side Vancouver `bibliographyEntry`
- `hooks/useManuscript.ts` — section CRUD with **1200 ms debounced autosave**
- `components/manuscript/ManuscriptEditor.tsx` — TipTap + StarterKit + Placeholder + CharacterCount + Citation
- `components/manuscript/BubbleAIMenu.tsx` — floating menu (Improve / Shorten / Formalise / Add Transition); position tracked via `editor.view.coordsAtPos`, **persists through the in-flight assist call and the suggestion review**
- `components/manuscript/CitationSuggestions.tsx` — `@`-trigger article picker, inserts a Citation node and drops a trailing space
- `components/manuscript/SectionTabs.tsx` — 7 tabs URL-synced via `?section=`
- `components/manuscript/WordCountBar.tsx` — per-section + total + `Saved …` indicator
- `components/manuscript/FinalManuscriptView.tsx` — read-only concat with **continuous citation numbering across sections** + Vancouver REFERENCES block
- `components/manuscript/ReferenceIntegrityPanel.tsx` — flags uncited library articles + orphan inline citations
- `components/manuscript/AbbreviationsPanel.tsx` — client-side scanner + save
- `routes/ManuscriptPage.tsx` — real implementation with `ProjectSelectGate` + tabs + editor / FinalView + word-count bar + right rail

**Citation safety contract (locked in)**

Model never sees author/year. Outbound HTML is replaced with `[CITE_aN]` tokens; the model's system prompt requires preserving them verbatim. Server-side and client-side reverse paths reject any token whose `articleId` is not in the current project's article set — unknown tokens stay as literal text. ProseMirror's schema-based DOM parser filters anything beyond schema attrs when the AI-suggested HTML is inserted, so `<script>` / `onerror` etc. are dropped.

**E2E verification (browser smoke test)**

- Edit Introduction: typed, autosave fired at 1200 ms, GET returned the saved HTML, reload restored content correctly.
- Select "remains debated" → BubbleAIMenu appeared → click Shorten → POST `/api/writing/assist 200` → AISuggestionBlock rendered `"However, it remains debated."` → Accept replaced the editor selection.
- Typed `@` at end of paragraph → picker showed the project's one article → click inserted a Citation node → saved HTML contains `<sup data-citation="true" class="citation" data-article-id="…">[…]</sup>` → ReferenceIntegrityPanel updated to **"every citation points to a real article"**.
- Final view: all six sections concatenated, citation displayed as `[1]`, REFERENCES section showed the Vancouver entry.
- Abbreviations panel: detected `THA` + `HHS`, Save → PUT replace persisted both rows.

**Incidents fixed during verification**

- BubbleAIMenu used `assist.isPending` inside an effect's dependency array **before** `assist = useMutation(...)` was declared — temporal-dead-zone crash on every render. Re-ordered: `useMutation` first, then the selection-update effect that reads it. While at it, the selection-collapse path no longer tears down the bubble while a request is in flight or a suggestion is on screen.
- `ManuscriptEditor`'s content-load `useEffect` watched `[loading, editor]` but not `html`. With cached query data, `loading` never flipped, so the effect ran once with empty `html` and the editor stayed blank after refresh. Added `html` to deps; the `current === html` guard prevents the typing path from re-`setContent`-ing on every keystroke.

**Security review (3 polish items, 0 blockers)**

- MED → polish: AI HTML output is inserted via TipTap `insertContent`. ProseMirror's schema-based parser already drops unknown attrs (no script/onerror execution), but defense-in-depth would add a DOMPurify pre-pass. Logged.
- LOW → polish: Citation NodeView in-editor DOM omits `data-article-id` (only on serialized HTML). Storage round-trips correctly, but any future selector against in-editor DOM needs to use the React fiber.
- LOW → polish: BubbleAIMenu position is cached at selection time — stale after window resize.

**Test counts**

- Backend: **142 pass** (was 139 after Phase 4; +3 in Phase 5 for abbreviations + writing route happy paths)
- Frontend: 11 vitest pass (was 7; +4 for `citationSerialize` round-trip)
- New test files: `test_abbreviations.py`, `test_abbreviation_scanner.py`, `test_writing_assist.py`, `citationSerialize.test.ts`

**Open items**

- `POLISH.md`: +3 phase-5 entries
- `DECISIONS.md`: unchanged
- `QUESTIONS.md`: still empty
- `DEFERRED.md`: unchanged

**Next:** Phase 6 — Data & Statistics module. Study-type-aware test recommendations (t-test, Mann-Whitney, χ², Fisher exact, Wilcoxon, ANOVA, Kruskal-Wallis, repeated-measures ANOVA, Pearson/Spearman, simple/multiple regression, logistic regression, Cox / Kaplan-Meier via lifelines, ICC, Cohen's κ); CSV/Excel upload + variable typing; assumption checks; results rendered into the Results section as prose with citations to the dataset.

---

## 2026-05-18 · Phase 6 — Data & Statistics ✅ COMPLETE

**Goal**

Researchers upload a Masterchart (CSV / `.xlsx`), the app infers each column's `VariableType`, the user can override it, they answer "what are you testing?", the app recommends an appropriate test from an 18-strong catalogue (t-test / Mann-Whitney / Wilcoxon / ANOVA / Kruskal-Wallis / repeated-measures ANOVA / Pearson / Spearman / OLS / multiple regression / logistic regression / KM + log-rank / Cox / ICC / Cohen's κ / χ² / Fisher exact / paired t-test) with rationale + assumption checks, runs it server-side via scipy / statsmodels / lifelines / pingouin, returns a structured result (statistic, p-value, effect size, CI, n, df), an AI step generates a one-paragraph plain-English interpretation that preserves a `[CITE_dataset_<id>]` token (Phase 4-5 contract reused), and a Push button appends the paragraph to `manuscript_sections.Results.content`.

**What shipped**

Backend (10 files + 1 migration):

- `db/models.py` — `Dataset`, `DatasetVariable`, `Analysis`, `AnalysisResult` (all `user_id`-scoped)
- `alembic/versions/0006_statistics.py` — revision 0005 → 0006
- `schemas/dataset.py` + `schemas/analysis.py` — `VariableType`, `QuestionType`, `TestKey` Literal unions (load-bearing for runner dispatch + recommender rules + TS mirror)
- `services/stats/ingest.py` — CSV / XLSX parse, **openpyxl `data_only=True`** so formulas are never evaluated; deterministic type inference
- `services/stats/registry.py` — the catalogue + pure `recommend()` truth table
- `services/stats/assumptions.py` — Shapiro-Wilk / Levene / lifelines proportional-hazards
- `services/stats/runner.py` — one branch per test; column-name whitelist (`^[A-Za-z_]\w*$`) enforced **before** any `statsmodels.formula.api` call
- `services/ai/prompts/result_interpretation.py` — token-preserving prompt
- `services/ai/gemini.py` — implemented `interpret_result` via `_generate_with_resilience` (same shape as `assist_writing`)
- `repositories/datasets.py` + `repositories/analyses.py` — user-scoped, manual cascade on delete
- `routes/datasets.py` — POST upload (magic-byte sniff, 50 MiB cap), GET list / one, PATCH variable type, DELETE
- `routes/analyses.py` — recommend, create, list, get, run, interpret, push. AI errors map 429/422/503. Push **appends** to `manuscript_sections.{section}.content` rather than overwriting

Frontend (10 files):

- `lib/api.ts` — `datasetsApi` + `analysesApi`; TS literal unions mirror Pydantic
- `hooks/useDatasets.ts` + `useAnalyses.ts` — TanStack Query wrappers, invalidation
- `components/statistics/DatasetUpload.tsx` — react-dropzone `.csv` / `.xlsx`
- `components/statistics/DatasetList.tsx` — selectable list
- `components/statistics/DatasetDetail.tsx` — column table with inline `VariableType` override
- `components/statistics/NewAnalysisWizard.tsx` (+ `WizardVariableStep.tsx`) — 3-step Sheet: question → variables → recommendation. Create + Run + Interpret chain.
- `components/statistics/RecommendationCard.tsx` — recommended test + rationale + "use a different test"
- `components/statistics/AssumptionPills.tsx` — Shapiro / Levene / PH status pills with p-value tooltips
- `components/statistics/AnalysisResultCard.tsx` — statistic / p-value (`<0.001` formatting) / effect size + 95% CI / n / df, **AI interpretation with the `[CITE_dataset_<id>]` token rendered as a small dataset chip**, Push-to-Manuscript navigates back to `/manuscript?section=Results`
- `routes/StatisticsPage.tsx` — replaced placeholder. ProjectSelectGate + two-pane layout, `?dataset=…` URL state

**E2E verification (browser smoke test on `hip_outcomes.csv`, n=20 split 10 anterior / 10 posterior)**

- Upload → 20 rows × 5 cols, types inferred (numeric / nominal). ✓
- Wizard step 1: Group comparison; step 2: outcome=`hhs_6w`, group=`approach`; step 3: recommender returned **"Independent t-test"** with rationale "Comparing a numeric outcome between two independent groups with approximately normal distributions." ✓
- Run: `t = 7.550 · p < 0.001 · effect size = 3.376 · 95% CI [6.856, 12.144] · n = 20 · df = 18`. Shapiro-Wilk + Levene pills green. ✓
- Interpret: Gemini produced a one-paragraph interpretation that preserved `[CITE_dataset_fd3a7…]` exactly and was rendered in the UI with a dataset chip. ✓
- Push: `manuscript_sections.Results.content` now starts with `<p>An independent samples t-test revealed…[CITE_dataset_fd3a7…]…</p>`, word_count 73. ✓

**Security review (3 polish items, 0 blockers)**

- Column-name injection: prevented at **two layers** — route (`_validate_columns` against `dataset_variables.name`) + runner (`_check_column_name` regex). 28-test cross-user / cross-project isolation regression covers every endpoint in both directions.
- XLSX formula evaluation: `openpyxl.load_workbook(..., data_only=True, read_only=True)` always — formulas never executed. Explicit test fixture `tiny_with_formula.xlsx` proves cached values are read.
- Upload cap: 50 MiB hard cap; magic-byte sniff rejects PDF prefix.
- AI errors map 429/422/503 with no provider detail leaked.
- LOW polish (logged): AI prompt should instruct number rounding; SQLite FK PRAGMA should be enabled app-wide; wizard step 2 could pre-empt type-mismatched picks.

**Test counts**

- Backend: **326 pass** (was 166 entering Phase 6; +160 in Phase 6)
- Frontend: 19 vitest pass (was 11; +8 for client-side schema + hook coverage already present in the run)
- New backend test files: `test_datasets_models.py`, `test_stats_ingest.py`, `test_stats_registry.py`, `test_stats_assumptions.py`, `test_stats_runner.py`, `test_ai_interpret_result.py`, `test_datasets_route.py`, `test_analyses_route.py`, `test_security_stats_isolation.py`

**Open items**

- `POLISH.md`: +3 phase-6 entries
- `DECISIONS.md`: unchanged
- `QUESTIONS.md`: still empty
- `DEFERRED.md`: unchanged (charts still deferred per the v1 ADR)

**Next:** Phase 7 — Systematic Review module. PRISMA flow tracking, inclusion/exclusion screening, risk-of-bias assessment (RoB 2 for RCTs, ROBINS-I for non-randomised, Newcastle-Ottawa for cohort/case-control), data extraction tables.

---

## 2026-05-18 · Phase 7 — Systematic Review ✅ COMPLETE

**Goal**

Researchers running a Systematic Review log their search strategy across databases, screen articles in two stages (title/abstract → full text), assess Risk of Bias with the tool appropriate to each study's design (RoB 2 / ROBINS-I / Newcastle-Ottawa / AMSTAR-2), extract structured study-level data, and watch a PRISMA 2020 flow diagram count itself. Any artefact — PRISMA SVG, search log, RoB summary, extraction table — pushes into the Manuscript with `[CITE_<article_id>]` tokens for included studies (Phase 5 token contract reused).

**What shipped**

Backend (15 files + 1 migration):

- `db/models.py`: `Review` (one per project), `SearchRecord`, `ScreeningRecord` (UNIQUE per article/stage), `RobAssessment` (UNIQUE per tool), `ExtractionRecord` (UNIQUE per article). All `user_id`-scoped. Additive `articles.abstract Text NULL` column.
- `alembic/versions/0007_systematic_review.py`: 0006 → 0007.
- `schemas/review.py`: `ReviewStage`, `ScreeningDecision`, `ExclusionCategory`, `RoBTool`, `RoBJudgement`, `DatabaseName` Literal unions — load-bearing for service + TS mirror.
- `services/review/prisma.py`: pure `count_flow()` + no-dep `render_prisma_svg()` (XML-escaped, viewBox 800×720).
- `services/review/rob_rules.py`: declarative catalogues for all four tools + `derive_overall()`. AMSTAR-2's yes/partial-yes/no vocabulary explicitly inverted via `AMSTAR2_UNIFIED_MAPPING`.
- `services/review/extraction_schema.py`: seven-group schema + `validate()`.
- `services/ai/prompts/screening_suggestion.py` + `gemini.py::suggest_screening`: title+abstract-only, JSON-output, advisory-only framing. `FakeAIProvider.suggest_screening` deterministic.
- `repositories/reviews.py`: `SqliteReviewRepository` covering all five resources. `upsert_screening` rejects cross-project articles via `ScreeningArticleMismatch`.
- `routes/reviews.py`: ~20 endpoints under `/api/projects/{pid}/reviews/...`. Auto-creates the one-per-project review on first GET. `/reviews/rob/tools` + `/reviews/extraction/schema` serve catalogues so the frontend doesn't duplicate them. AI suggest stores `ai_suggestion` but **never mutates `decision`** — load-bearing invariant covered by isolation tests. Four pushes: PRISMA → Methodology; search log table → Methodology; RoB traffic-light table → Results with `[CITE_<id>]` tokens; extraction table → Results with `[CITE_<id>]` tokens.
- `tests/test_security_review_isolation.py`: 29 tests proving zero leak across users or projects on every endpoint, including the AI-doesn't-mutate-decision invariant.

Frontend (19 files):

- `lib/api.ts`: `reviewsApi`/`searchApi`/`screeningApi`/`robApi`/`extractionApi`. TS Literal unions mirror Pydantic.
- `lib/rob.ts`: TS port of `derive_overall` for live RoB preview; server is still source of truth.
- `hooks/useReviews.ts`: TanStack Query wrappers with invalidation chains.
- `components/review/`: 10 components — `ReviewHeader` (PICO/eligibility edit), `SearchLog`, `ScreeningStageTabs` + `ScreeningTable` + `ScreeningRowActions` (advisory AI suggest button never overwrites user decision), `RoBToolPicker`, `RoBAssessmentForm` (live overall preview), `RoBSummaryFigure` (traffic-light SVG), `ExtractionTable`, `PRISMAFlowChart`, `EmptyReviewState`.
- `routes/SystematicReviewPage.tsx`: ProjectSelectGate → study-type guard → 5 tabs (URL `?tab=`).
- `App.tsx` + `nav-items.ts`: `/review` route + sidebar nav.

**E2E verification (browser smoke on a fresh Systematic Review project)**

Created two search records (PubMed n=412, Embase n=278 → identified=690). Inserted 2 articles. Title/abstract screening: included the RCT, excluded the editorial (reason "Editorial — not a primary study"). Full-text screening: included the RCT. RoB 2 assessment on the RCT (`measurement=some_concerns`, all others `low`) → `overall_auto = some_concerns`. Extraction with full structured fields persisted. PRISMA: `identified=690, after_dedupe=690, screened=2, excluded_title=1, full_text_assessed=1, included=1`. All four pushes returned 200; Methodology now contains the PRISMA SVG (base64 `<img>`) + search log table; Results contains the RoB traffic-light table (5 domain cells, overall column) and the extraction table — both with `[CITE_01a2ab7…]` token for the included study, exactly matching the Phase 5 contract.

**Two test-run bugs discovered, both UX-only**

Initial test pushes returned 422 because: (a) the RoB 2 catalogue uses `randomisation` (UK) / `missing_outcome` / `reporting` rather than the US/colloquial keys I first sent; (b) extraction schema requires `first_author` (not `author`) and the `notes` group must be an object (not bare string). Both are correct per the catalogue endpoints (`/reviews/rob/tools`, `/reviews/extraction/schema`) — the frontend wizard already builds forms from those catalogues so the user never sees these keys. Logged to POLISH as "document required shape on the schema endpoints."

**Security review (3 polish items, 0 blockers)**

- AI suggest never mutates `decision` — proven via two dedicated tests in the security regression.
- Two layers of project scoping on every route: `_resolve_review` does the project ownership check, the repo's `user_id` filter is defence-in-depth.
- PRISMA SVG injected with XML-escaped integers only; ProseMirror's schema parser strips any unknown attrs in the pushed `<table>` / `<img>` HTML.
- Push endpoints **append** rather than overwrite — a re-push will stack duplicate tables in the section. Logged as polish (low: replace-by-class-hook or a `mode=replace|append` query param).

**Test counts**

- Backend: **488 pass** (was 326 entering Phase 7; +162 in Phase 7)
- Frontend: 44 vitest pass (was 19; +25)
- New backend test files: `test_review_models`, `test_review_prisma`, `test_review_rob_rules`, `test_review_extraction_schema`, `test_ai_suggest_screening`, `test_reviews_route`, `test_security_review_isolation`

**Open items**

- `POLISH.md`: +3 phase-7 entries
- `DECISIONS.md`: unchanged
- `QUESTIONS.md`: still empty
- `DEFERRED.md`: unchanged (meta-analysis + GRADE + PubMed direct-search deferred to Phase 7.5 / Phase 8)

**Next:** Phase 8 — bibliography polish, export (DOCX + PDF + JSON), full-app polish, deploy targets (Vercel for static / Fly.io for API). Phase 9 (Electron desktop) remains paused per the user's directive — autonomous runs end after Phase 8.

---

## 2026-05-18 · Phase 8 — Bibliography, Export, Polish & Deploy ✅ COMPLETE

**Goal**

Bibliography UI in 4 styles (Vancouver / APA 7 / Harvard / IEEE), one-click export of the whole project to DOCX / PDF / JSON, JSON bundle import that re-tags everything to the current user (security-critical), six high-priority `POLISH.md` items resolved, and deploy artefacts for Vercel (frontend) + Fly.io (API) prepared but not pushed.

**What shipped**

Backend (12 files + tests):

- `services/citation_format.py` extended with full APA 7, Harvard, IEEE formatters (Vancouver byte-identical). `format_entry(article, style)` dispatcher + HTML-safe `format_entry_html`.
- `services/export/bibliography.py`: `build_bibliography(sections, articles, style)` walking all six sections in order, dedupe by article_id, returns numbered entries.
- `services/export/{docx,pdf,bundle}_export.py`: DOCX via python-docx (A4, TNR 11, double-spaced); PDF via reportlab.platypus with native SVG embedding via svglib; JSON bundle covering all 17 tables.
- `services/export/bundle_import.py`: the security gate. Mints fresh primary keys, rewrites every FK through old→new id maps, **force-stamps `user_id = target_user_id` on every row regardless of bundle contents**. Validates `schema_version == 1`. Orphan FKs silently dropped. Wrapped in a transaction.
- `services/export/_html_walker.py`: shared HTML walker (stdlib `html.parser`), allowlist-only.
- `schemas/export.py`: `BibliographyResponse`, `BundleImportResponse`, `ExportFormat`, etc.
- `routes/export.py`: `POST /export/docx`, `POST /export/pdf`, `POST /export/bundle`, `POST /import/bundle`, `GET /bibliography`. Slug-safe `Content-Disposition` filenames. 50 MiB upload cap. 415 for non-JSON content, 422 for `BundleImportError`, 413 for oversize.
- `tests/test_security_export_isolation.py`: 19 tests proving cross-user 404s, force-retag of imported bundles, size + content-type rejections.

Frontend (10 files):

- `lib/api.ts`: `bibliographyApi`, `exportApi` (`downloadDocx/Pdf/Bundle`, `importBundle`). Blob download helper + RFC 5987-aware Content-Disposition filename parser.
- `lib/bibliographyFormat.ts`: client-side mirror of all 4 server formatters + `toBibTeX`, `toRIS`, `toCSLJSON` converters.
- `components/bibliography/`: BibliographyPanel + BibliographyToolbar + BibliographyRow. Mounted in the right rail of ManuscriptPage. Style picker persists via `projectsApi.update` for vancouver/apa/harvard; IEEE is a session-only override (schema doesn't store it — see POLISH).
- `components/settings/`: ExportCard (per-project DOCX/PDF/Bundle download buttons), ImportDropzone (react-dropzone, 50 MiB client cap), StorageCard (backend identifier + "Migrate to cloud" stub), HealthLink.
- `routes/HealthPage.tsx`: read-only diagnostics polled every 10s.
- `ManuscriptEditor.tsx`: `?scrollTo=cite-<articleId>` URL handler — walks the ProseMirror doc, places selection on the matching citation node, scrolls into view, strips the param.
- `App.tsx`: React Router v7 future flags (`v7_startTransition`, `v7_relativeSplatPath`), `/health` route added.

**Six POLISH items resolved**

- **T11**: React Router v7 future flags — no more console warnings.
- **T12**: DOMPurify pre-pass applied in `aiSafeTextToHtml()` AND `BubbleAIMenu.handleAccept()` (defence-in-depth).
- **T13**: SQLite FK PRAGMA enabled app-wide via a SQLAlchemy `event.listen` on engine connect. Per-test PRAGMA workarounds removed.
- **T14**: AI result-interpretation prompt teaches the model to round p-values to 3 decimals (or `<0.001`), effect sizes / CI to 2-3 sig figs.
- **T15**: Stats wizard step 2 surfaces an inline amber warning when the picked variable's type doesn't match the slot expectation (advisory; backend still validates).
- **T16**: Review pushes (PRISMA / search / RoB / extraction) use **replace-by-class-hook** — re-push swaps the existing block in place rather than stacking duplicates.

**Deploy artefacts (prepared, NOT deployed)**

- `apps/api/Dockerfile`: Python 3.12-slim, `libmagic1` system dep for python-magic, mounts `/data` volume for the SQLite DB + file storage. Runs `alembic upgrade head` before `uvicorn`.
- `apps/api/fly.toml`: placeholder pointing at the Dockerfile, with a `/data` volume mount, `/health` HTTP healthcheck, and shared-cpu-1x / 512MB sizing. Secrets (`GEMINI_API_KEY` etc.) are stamped via `fly secrets set`.
- `apps/web/vercel.json`: vite framework, SPA rewrites, security headers (`X-Content-Type-Options`, `X-Frame-Options=DENY`, `Referrer-Policy`, `Permissions-Policy`), and immutable cache for `/assets/`.

**E2E verification (browser smoke on the Phase 7 systematic-review project)**

`POST /export/docx` → 37 KB DOCX, `POST /export/pdf` → 7.5 KB PDF, `POST /export/bundle` → JSON with all 17 tables + `schema_version: 1`. `GET /bibliography?style=apa` returned 1 entry (the one cited article) with `first_section` populated. **Round-trip**: posted the bundle straight to `POST /import/bundle`; got back a fresh project_id (`a930029d…` vs source `5ebc0209…`) with counts {projects: 1, articles: 2, manuscript_sections: 2, reviews: 1, search_records: 2, screening_records: 3, rob_assessments: 1, extraction_records: 1} — identical to the source modulo IDs + user_id (which is correctly re-stamped).

**Security review (1 LOW polish; 0 blockers)**

- Bundle import re-tags every row to `target_user_id` and mints fresh primary keys — proven by `test_security_export_isolation.py::test_import_stamps_target_user_id_regardless_of_bundle` and a follow-up sweep asserting every model's `user_id == target` post-import.
- Filename slug regex strips path-traversal characters before composing `Content-Disposition`.
- Multipart import rejects size > 50 MiB (413), content not starting with `{` (415), and `BundleImportError` (422).
- DOMPurify pre-pass on AI HTML adds a defence-in-depth layer on top of ProseMirror's schema filter.
- **LOW polish** (logged): `schemas/project.py::CitationStyle` doesn't list `ieee`, so `PATCH /projects/{id} citation_style=ieee` would 422. Frontend handles this gracefully but the schema mismatch is worth tightening.

**Test counts**

- Backend: **656 pass** (was 488 entering Phase 8; +168 in Phase 8 across citation styles, bibliography, all four export services + import, routes, polish-fix coverage)
- Frontend: 71 vitest pass (was 44; +27 across bibliography format + API client + dompurify)

**Open items**

- `POLISH.md`: 6 entries struck through with `✅ resolved in P8-T1{1..6} (2026-05-18)`; one new low-sev entry added about the `CitationStyle` schema mismatch on `ieee`.
- `DECISIONS.md`: unchanged
- `DEFERRED.md`: meta-analysis + GRADE + PubMed direct-search still deferred.

---

## 2026-05-18 · Phase 8.6 — Ingestion (PubMed / Crossref / RIS / BibTeX / dedup) ✅ COMPLETE

**Goal:** populate the Library by metadata, not just by PDF upload. Four ingest surfaces + a duplicate-resolution workflow.

**Backend (one new pip dep — `bibtexparser>=1.4,<2`; dev: `respx>=0.21`)**

- `services/ingest/crossref.py`: thin wrapper around the existing `services/crossref.py` that strips JATS abstract tags and returns `ArticleMetadata(source='doi')`.
- `services/ingest/pubmed.py`: NCBI E-utilities `esearch` + `efetch`; stdlib `ElementTree` parser; 15 s timeout; single automatic 429 retry; never raises (returns `[]` on any failure).
- `services/ingest/ris.py`: pure RIS line parser (TI/T1, AU/A1, JO/JF/T2/JT, PY/Y1/DA, VL, IS, SP/EP, DO, AB/N2). Tolerates CRLF/LF/mixed newlines.
- `services/ingest/bibtex.py`: `bibtexparser` v1 wrapper, `@article` only (journals); brace-armour stripped from titles; `Last, First` → `First Last` author normalisation.
- `services/ingest/dedup.py`: 3-stage group finder — DOI exact (lowercase) > PMID exact > rapidfuzz `token_set_ratio ≥ 0.92` AND `|Δyear| ≤ 1`, with union-find so transitive matches collapse to one group.
- `schemas/ingest.py`: `ArticleMetadata` (uniform shape across all ingest surfaces) + `DuplicateGroup` + `MergeRequest` + `ImportFromMetadataRequest/Response` + `DoiLookupRequest` + `PubMedSearchRequest`.
- `db/models.Article.pmid` (indexed) + `Article.source` (`upload | doi | pubmed | ris | bibtex | manual`), Alembic `0009_ingestion` back-fills existing rows to `source='upload'`.
- `repositories/articles.merge(keep_id, drop_ids, user_id)`: rewires every article FK across highlights / article_notes / screening_records / rob_assessments / extraction_records / **meta_inputs** (Phase 7.5 cross-link) to the keep row, then deletes the drops. Composite-UNIQUE-bearing tables get a per-row collision check — keep wins, drop is deleted instead of UPDATE-rewired. Refuses cross-user / cross-project / same-id. Single transaction.
- `routes/ingest.py`: 7 endpoints (`POST /lookup-doi`, `POST /search-pubmed`, `POST /import-from-metadata`, `POST /import-ris`, `POST /import-bibtex`, `GET /duplicates`, `POST /merge-duplicates`). RIS/BibTeX uploads: 2 MiB cap, magic-byte sniff (`TY  -` / `@`).

**Frontend (no new npm deps)**

- `lib/api.ts`: `ArticleSourceSchema`, `ArticleMetadataSchema`, `DuplicateGroupSchema`, `ImportFromMetadataResponseSchema` + `ingestApi` (7 methods). `ArticleSchema` extended with `pmid` + `abstract` + `source`.
- `hooks/useIngest.ts`: 7 TanStack hooks. Successful imports / merges invalidate both `['articles', projectId]` and `['duplicates', projectId]`.
- 5 new components — `AddByDoiInline`, `PubMedSearchDialog`, `RisBibtexDropzone` (existing `react-dropzone`), shared `ImportPreviewDialog`, `DuplicatesPanel` (per-group radio-pick keep + merge action).
- `LibraryPage`: three-action row above `UploadZone`; `DuplicatesPanel` rendered when groups exist.

**Test deltas**

- Backend: 970 pass (was 849 entering 8.6; **+121 across 11 new test files**)
  - `test_ingest_schema.py` (3) · `test_ingest_crossref.py` (8) · `test_ingest_pubmed.py` (13) · `test_ingest_ris.py` (11) · `test_ingest_bibtex.py` (12) · `test_ingest_dedup.py` (12) · `test_articles_merge.py` (15) · `test_ingest_route_doi.py` (5) · `test_ingest_route_pubmed.py` (5) · `test_ingest_route_import_metadata.py` (7) · `test_ingest_route_ris.py` (5) · `test_ingest_route_bibtex.py` (5) · `test_ingest_route_duplicates.py` (9) · `test_security_ingest_isolation.py` (11)
- Frontend: 86 pass (was 81; +5 in `ingestApi.test.ts`).

**Acceptance bar**

- ✅ DOI lookup via Crossref (preview before persist).
- ✅ PubMed esearch + efetch with API-key polite-pool support.
- ✅ RIS & BibTeX upload + preview (no persist on parse).
- ✅ Bulk add via `/import-from-metadata` with DOI/PMID dedup-against-existing.
- ✅ Fuzzy dedup over project library (DOI > PMID > title-fuzzy + year ± 1).
- ✅ Merge with full FK rewiring (highlights / notes / screening / RoB / extraction / meta-inputs).
- ✅ Cross-user / cross-project isolation regression (11 tests).

**Decisions**

- **No AI extraction for metadata-only ingest sources** — DOI/PubMed/RIS/BibTeX results are trusted verbatim; the PDF-upload pipeline keeps its existing AI → Crossref enrichment merge.
- **ImportPreviewDialog two-step gate** — every metadata source funnels through the same preview dialog so users can deselect anything they don't want before persistence.
- **Union-find for fuzzy duplicates** — transitive matches (A~B, B~C) collapse to one group of three.
- **`bibtexparser` v1 pin** — v2 introduces a breaking parser rewrite; we pin `<2` until v2 stabilises.

**Out of scope (deferred)**

- EMBASE / Scopus / Web of Science search.
- Author disambiguation via ORCID.
- AI-assisted dedup ("are these the same paper?").
- Auto-attach PDFs from unpaywall on DOI lookup.
- `defusedxml` hardening (the PubMed XML wire format is bounded by NCBI; no user-controlled XML reaches `ElementTree`).
- Bulk background re-dedup over the entire library — runs synchronously on every import in v1.

---

## Phase 9 readiness checklist (autonomous run STOPS here — user check-in required)

Before starting Phase 9 (Electron desktop packaging), the user should decide on / acknowledge:

1. **Bundling strategy** — Electron + Python sidecar (uvicorn) vs PyOxidizer-compiled single binary vs sidecar via `electron-forge`'s `extraResource`. The pragmatic v1 is "spawn `uvicorn` as a child process from `electron/main.ts` with the bundled venv path" — works on macOS / Windows / Linux out of the box but ships ~120 MB of Python deps. Document the trade-off.
2. **Auto-update** — `electron-updater` with a code-signing certificate (Apple Developer ID / Microsoft Authenticode). User needs to decide on signing identities BEFORE the first release, otherwise users get "unidentified developer" warnings.
3. **Data directory** — per-OS conventions: `~/Library/Application Support/ResearchAssistant/` on macOS, `%APPDATA%/ResearchAssistant/` on Windows, `~/.local/share/ResearchAssistant/` on Linux. The SQLite DB + file storage move from `./data/` to the OS data dir on first launch (migration step).
4. **AI provider keys** — currently in `.env` at the project root. For desktop, store in OS keychain via `keytar` (npm package) — user enters once in Settings, never written to disk in plaintext.
5. **IPC** — Electron renderer talks to the bundled uvicorn on a locally-bound port (127.0.0.1:8787 default). For multi-instance support, pick a free port at launch and pass to the renderer via IPC.
6. **Signed-build CI** — GitHub Actions matrix (macOS / Windows / Linux) with secrets for the signing identity. Build artefacts: `.dmg` / `.exe` / `.AppImage`. Optionally `.deb` / `.rpm`.
7. **First-launch UX** — health-check the sidecar process; if it dies, show a "Restart API" button rather than a white screen. The existing `/health` endpoint already gives the data needed.

**This is the user check-in point.** Phase 9 is paused. Web app is feature-complete for single-user local-first use; Vercel + Fly deploys are ready when the user wants them.

---
