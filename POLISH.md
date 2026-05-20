# Polish Backlog

Visual, UX, and micro-interaction nits noticed while building. **Not blockers** —
the build proceeds; these get revisited before each phase ships and again
in Phase 8 (final polish).

Format: `[phase] [severity: low|med|high] description · where`

Severity meaning:
- **low** — would only notice on close inspection
- **med** — noticeably wrong feel; worth fixing before user demo
- **high** — actively bad UX; fix before phase closes

---

- ~~[phase1] [high] No mobile navigation at <768px — sidebar correctly hides but nothing replaces it. Add hamburger Sheet drawer with same nav items before Phase 2 ships. · `apps/web/src/components/layout/Topbar.tsx` + new `MobileNav.tsx`~~ ✅ resolved in P2-T1 (2026-05-17)
- ~~[phase1] [low] React Router v6→v7 future-flag warnings in console (`v7_startTransition`, `v7_relativeSplatPath`). Opt in to silence: pass `future={{...}}` to `BrowserRouter`. · `apps/web/src/App.tsx`~~ ✅ resolved in P8-T11 (2026-05-18)
- ~~[phase1] [low] Dashboard project card has no click target / no detail page yet. Cursor changes but nothing happens. Resolve when project detail view ships in Phase 2. · `apps/web/src/components/projects/ProjectCard.tsx`~~ ✅ resolved in P2 — card navigates to Library with active-project set
- ~~[phase2] [med] react-dropzone hidden input doesn't fire `change` when the **same file** is re-selected via click~~ ✅ resolved in P2-T21 (onClick reset of input.value)
- [phase2] [low] Upload validation 413/415 responses leak server cap and full allowed_upload_mime list. Fine for local-first, harden if ever exposed publicly. · `apps/api/src/research_api/routes/articles.py`

- ~~[phase5] [med] AI writing-assist output is inserted into TipTap via insertContent — ProseMirror's schema-based parser drops unknown attrs (no script/onerror execution), but defense-in-depth would add DOMPurify pre-pass on the AI output before `aiSafeTextToHtml` returns it. · `apps/web/src/lib/citationSerialize.ts` + `apps/web/src/components/manuscript/BubbleAIMenu.tsx`~~ ✅ resolved in P8-T12 (2026-05-18)
- [phase5] [low] Citation NodeView in-editor DOM omits `data-article-id` (only `data-citation`). Serialized HTML (`editor.getHTML()`) has the attribute, so storage/round-trip works, but any selector relying on in-editor DOM articleId will miss. · `apps/web/src/lib/tiptap/extensions/CitationNodeView.tsx`
- [phase5] [low] BubbleAIMenu position can be stale after window resize — uses cached coordinates from last selectionUpdate. Add a window 'resize' listener if used in serious resize flows. · `apps/web/src/components/manuscript/BubbleAIMenu.tsx`
- ~~[phase6] [low] Result-interpretation prompt does not instruct the model to round numbers — output uses full float precision (e.g. `p=5.535274203885035e-07`, `effect size = 3.3763886032268267`). Add a "round p-values to 3 decimal places (or report `<0.001`), effect sizes / CI to 2-3 sig figs" line in `result_interpretation.py`. · `apps/api/src/research_api/services/ai/prompts/result_interpretation.py`~~ ✅ resolved in P8-T14 (2026-05-18)
- ~~[phase6] [low] SQLite foreign-key PRAGMA is not enabled app-wide; cascades work in code via manual delete in the dataset repository, and in tests via a per-connection PRAGMA. Add a connect-event listener that sets `PRAGMA foreign_keys=ON` for every aiosqlite connection so we don't have to maintain the manual cascade list. · `apps/api/src/research_api/db/engine.py`~~ ✅ resolved in P8-T13 (2026-05-18)
- ~~[phase6] [low] Statistics page wizard step 2 has no validation that the chosen columns match the chosen test's variable-type expectations (e.g. nothing stops you from picking a nominal column as the outcome of a t-test). Backend rejects, but the UX could pre-empt. · `apps/web/src/components/statistics/WizardVariableStep.tsx`~~ ✅ resolved in P8-T15 (2026-05-18)
- ~~[phase7] [low] Review pushes (PRISMA/search/RoB/extraction) append to the manuscript section. Pushing twice stacks duplicate tables. Consider a `mode=replace|append` query param, or detect the existing block by class hook (`.rob-traffic-light-table`, `.prisma-flow`) and replace in-place. · `apps/api/src/research_api/routes/reviews.py`~~ ✅ resolved in P8-T16 (2026-05-18)
- [phase7] [low] RoB 2 catalogue uses UK spelling (`randomisation`) but the AMSTAR-2 inversion vocabulary uses `yes_no/partial_yes/no` rather than the unified low/some_concerns/high — confusing for an international user pool. Either pick one spelling app-wide, or surface tooltips in the form. · `apps/api/src/research_api/services/review/rob_rules.py`
- [phase7] [med] Extraction schema validation rejects flat fields like `notes: "some text"` because the validator expects every group value to be an object. Document the required shape on the GET /extraction/schema response (currently the shape is implicit). · `apps/api/src/research_api/services/review/extraction_schema.py`
- [phase8] [low] `schemas/project.py::CitationStyle` Literal still only lists `vancouver|apa|harvard` even though `citation_format.py` and the bibliography route now accept `ieee`. `PATCH /projects/{id} citation_style=ieee` would 422; the frontend skips the PATCH for IEEE and keeps it as a session-only override. Tighten the schema (and the DB column comment) when IEEE persistence is wanted. · `apps/api/src/research_api/schemas/project.py`
- ~~[roadmap-#14] [high] Bibliography uses first-citation-of-appearance for all 4 styles. APA + Harvard expect alphabetical-by-first-author. Fix per-style ordering policy. · `apps/api/src/research_api/services/export/bibliography.py`~~ ✅ resolved in P9 (2026-05-18)
- ~~[roadmap-#15] [high] Sequential citations don't consolidate. `[1][2][3]` should render as `[1-3]` in Vancouver/IEEE; `(Smith 2024; Patel 2022; Brown 2021)` (single parens, semicolon-separated) for APA/Harvard. · `apps/api/src/research_api/services/citation_format.py`~~ ✅ resolved in P9 (2026-05-18)

### Stats-refine residual (2026-05-19)

- [stats-refine] [low] AnalysisResultCard "Re-interpret" replaces the AI paragraph wholesale; no diff highlighting of what changed. · `apps/web/src/components/statistics/AnalysisResultCard.tsx`
- [stats-refine] [low] PowerCalculator family switch keeps stale family-specific extras in state (e.g. switching to mixed_effects retains a previously-typed event_rate). Sent payload is still correct because only relevant fields are passed, but disabled inputs are confusing. Reset on family change. · `apps/web/src/components/statistics/PowerCalculator.tsx`
- [stats-refine] [low] `detect_long_format` heuristic recognises only patient/subject/id/pid/case as subject-id names. Custom names (record_no, study_id, mrn) won't trigger the mixed-effects banner. Extend the regex if false-positive risk is acceptable. · `apps/api/src/research_api/services/stats/ingest.py`
- [stats-refine] [low] PlotWorkspace renders a single live preview; no side-by-side facet preview. Saved plots accumulate below the form. · `apps/web/src/components/statistics/PlotWorkspace.tsx`
- [stats-refine] [low] Push to Manuscript Results is one-shot — no "undo push" affordance. Researchers can manually delete the appended paragraph in the editor. · `apps/web/src/components/statistics/AnalysisResultCard.tsx`
- [stats-refine] [low] shadcn `Select` is hard to drive from `fireEvent.change` in vitest; the PowerCalculator's per-family input panels are covered by family-label test rather than full integration. Look into `@testing-library/user-event` keyboard navigation. · `apps/web/src/components/statistics/__tests__/PowerCalculator.test.tsx`
- [demo] [resolved] Bibliography panel includes cited datasets as a "Dataset" reference type with project-investigator authorship and upload-year. Fixed 2026-05-20.
- [demo] [resolved] AI result-interpretation prompt no longer emits (Dataset, YYYY) wrapper text — citation engine handles inline marker formatting per style. Fixed 2026-05-20.

### Meta-sweep residual (2026-05-20)

Surfaced by the 8-study anterior-vs-posterior THA meta-analysis E2E sweep.
8 BLOCKER/HIGH bugs were fixed in the same session (commit `fix(meta-sweep): ...`).
The items below are MEDIUM/LOW deferrals:

- [meta-sweep] [med] **M1 PRISMA no auto-dedupe** — PRISMA flow stages do not auto-dedupe across imported sources. Implement record-level dedup pass before populating "Records after duplicates removed" stage. · `apps/api/src/research_api/routes/reviews.py` (prisma fields)
- [meta-sweep] [low] **M2 Publication-bias test catalogue clarification** — Egger + Begg is intentional for MD/SMD outcomes (Harbord is OR-specific, Peters is event-specific). Document why the other tests are gated on metric type so reviewers don't think they're missing. · `apps/api/src/research_api/services/meta/publication_bias.py`
- [meta-sweep] [med] **M3 Meta-regression needs raw values** — current schema requires pre-computed effect sizes; for direct meta-regression we need raw arm-level inputs surfaced as covariates. Plumb the `MetaInput.subgroup` column + extraction-table fields into the meta-regression service.
- [meta-sweep] [low] **M4 I²=0% sanity** — input data issue, not code. When all studies have identical effect sizes I²=0 is correct, just visually surprising. Add a tooltip explaining the interpretation in the forest plot panel. · `apps/web/src/components/review/meta/MetaAnalysisRunner.tsx`
- [meta-sweep] [med] **M5 PROSPERO field coverage** — 13/22 fields populated by autofill; the rest need ICMJE author lookups + manual fill. Surface a "fields missing for submission" banner. · `apps/api/src/research_api/services/review/prospero.py`
- [meta-sweep] [low] **M6 Checklist key case-sensitive** — checklist item lookups are case-sensitive; CONSORT/PRISMA bundle import that capitalises a key silently drops items. Normalise to `lower_snake_case` on read.
- [meta-sweep] [low] **M7 Orphan citation panel** — the OrphanCitationPanel doesn't refresh after deleting a referenced article; stale "orphans" sit in the panel until the user navigates away. Invalidate the orphans query on article-delete. · `apps/web/src/components/manuscript/OrphanCitationPanel.tsx`
- [meta-sweep] [low] **L1-L3** — assorted minor lint/typography nits captured during the meta-sweep; not material to the build.

## Library sweep (2026-05-20) MEDIUM / LOW deferrals

- [lib-sweep] [med] **L-DLG-authors** — `ImportPreviewDialog` renders the full author list for Crossref records inline. Lancet CRAFFT trial drops a ~10kB author string (215 authors) into the dialog as a single line. Trim to first-3 + `+N more` with a hover tooltip for the rest. · `apps/web/src/components/library/ImportPreviewDialog.tsx`
- [lib-sweep] [low] **L-DOI-toast-ttl** — `toast.error` from a DOI lookup auto-dismisses within ~3s; users who tab away come back to no feedback. Bump the duration or keep the error inline in the AddByDoiInline card. · `apps/web/src/components/library/AddByDoiInline.tsx`
- [lib-sweep] [low] **L-PM-all-selected** — PubMed v2 results dialog defaults to "all 50 checked → Import 50 articles". Easy to fat-finger and import the entire result set. Consider defaulting to no selection or capping at 10. · `apps/web/src/components/library/PubMedSearchDialog.tsx`
- [lib-sweep] [low] **L-Cross-404-copy** — DOI 404 toast just says "DOI not found in Crossref". Some 404s are NEJM/BJJ blocking Crossref-public retrieval — the DOI is real but the publisher gates the metadata. Phrase the error to suggest "verify on doi.org or try PubMed search" rather than implying the DOI is invalid. · `apps/api/src/research_api/services/ingest/crossref.py`

<!-- rcm-sweep (Phase 3 — 2026-05-20) -->
- ~~[rcm-sweep] [HIGH] **R-Autosave-stuck-empty** — `useManuscript` blocks autosave when the section starts empty because the `initialised.current` ref pattern races with StrictMode double-mount. Reproduction: open a brand-new project → Manuscript → Discussion → type a paragraph; nothing PUTs to the server. Fix: replaced the boolean ref with a `serverContent` ref that tracks the last server-observed string and skips no-op saves instead. · `apps/web/src/hooks/useManuscript.ts`~~ ✅ resolved
- ~~[rcm-sweep] [HIGH] **R-Legacy-CITE-tokens** — Section content persisted before Phase 1's CITE-token resolver was wired could contain raw `[CITE_xxx]` strings inside meta-analysis figcaptions. Bibliography panel never picked these up. Fix: lazy resolve `[CITE_<aid>]` (and combined `[CITE_a, CITE_b]` clusters) on GET in `routes/manuscript_sections.py` so legacy data heals itself without a forced rewrite. · `apps/api/src/research_api/routes/manuscript_sections.py`~~ ✅ resolved
- [rcm-sweep] [MED] **R-Paraphrase-Note-combined** — `HighlightNotePopover` exposes a single "Your paraphrase / note" textarea but the spec / sidebar tooltips talk about paraphrase AND note as separate concepts. Either rename the field to one or split into two (paraphrase = AI/manual reword for Compile, note = personal thoughts that stay in the Reader). · `apps/web/src/components/reader/HighlightNotePopover.tsx`
- [rcm-sweep] [MED] **R-Overlap-highlights** — Selecting the same span and applying a second colour creates a stacked highlight. There is no UI affordance to merge or surface "already highlighted in another colour" — fine as a design choice but worth a tooltip warning. · `apps/web/src/components/reader/SelectionCapture.tsx`
- [rcm-sweep] [LOW] **R-Citation-numbering-on-empty-section** — When typing the first @ citation in a brand-new section, the inline marker shows `[1]` momentarily even though the global bibliography numbering would put it at a higher position. Resolves correctly once autosave fires + bibliography refetches. · `apps/web/src/components/manuscript/CitationSuggestions.tsx`
- [rcm-sweep] [LOW] **R-Cite-token-clusters-on-save** — Backend write path stores the HTML the editor sent (including unresolved CITE tokens if the section had them from earlier flows). The on-read resolver patches this on display, but the database row stays in the legacy form forever. Optional background migration could rewrite the rows after read so re-runs are O(1). · `apps/api/src/research_api/routes/manuscript_sections.py`
- [sub-export-sweep] [LOW] **SE-Page-section-count** — `SubmissionPage` description says "Cover Letter, Reviewer Responses, and Submission Package" but the package is a top-bar dialog button, not a third stacked card. Either restructure to three explicit cards or rephrase the lead paragraph. · `apps/web/src/routes/SubmissionPage.tsx`
- [sub-export-sweep] [LOW] **SE-Bundle-version-error-msg** — Import of a bundle with mismatched `schema_version` returns "Unsupported schema_version: 999 (expected 1)". Helpful but lacks an explicit upgrade-path hint (e.g. "open the bundle in version X first"). Cosmetic — researchers can deduce it. · `apps/api/src/research_api/services/export/bundle_import.py`
