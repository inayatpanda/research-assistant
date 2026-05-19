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
