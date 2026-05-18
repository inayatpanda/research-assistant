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
- [phase1] [low] React Router v6→v7 future-flag warnings in console (`v7_startTransition`, `v7_relativeSplatPath`). Opt in to silence: pass `future={{...}}` to `BrowserRouter`. · `apps/web/src/App.tsx`
- ~~[phase1] [low] Dashboard project card has no click target / no detail page yet. Cursor changes but nothing happens. Resolve when project detail view ships in Phase 2. · `apps/web/src/components/projects/ProjectCard.tsx`~~ ✅ resolved in P2 — card navigates to Library with active-project set
- ~~[phase2] [med] react-dropzone hidden input doesn't fire `change` when the **same file** is re-selected via click~~ ✅ resolved in P2-T21 (onClick reset of input.value)
- [phase2] [low] Upload validation 413/415 responses leak server cap and full allowed_upload_mime list. Fine for local-first, harden if ever exposed publicly. · `apps/api/src/research_api/routes/articles.py`

- [phase5] [med] AI writing-assist output is inserted into TipTap via insertContent — ProseMirror's schema-based parser drops unknown attrs (no script/onerror execution), but defense-in-depth would add DOMPurify pre-pass on the AI output before `aiSafeTextToHtml` returns it. · `apps/web/src/lib/citationSerialize.ts` + `apps/web/src/components/manuscript/BubbleAIMenu.tsx`
- [phase5] [low] Citation NodeView in-editor DOM omits `data-article-id` (only `data-citation`). Serialized HTML (`editor.getHTML()`) has the attribute, so storage/round-trip works, but any selector relying on in-editor DOM articleId will miss. · `apps/web/src/lib/tiptap/extensions/CitationNodeView.tsx`
- [phase5] [low] BubbleAIMenu position can be stale after window resize — uses cached coordinates from last selectionUpdate. Add a window 'resize' listener if used in serious resize flows. · `apps/web/src/components/manuscript/BubbleAIMenu.tsx`
- [phase6] [low] Result-interpretation prompt does not instruct the model to round numbers — output uses full float precision (e.g. `p=5.535274203885035e-07`, `effect size = 3.3763886032268267`). Add a "round p-values to 3 decimal places (or report `<0.001`), effect sizes / CI to 2-3 sig figs" line in `result_interpretation.py`. · `apps/api/src/research_api/services/ai/prompts/result_interpretation.py`
- [phase6] [low] SQLite foreign-key PRAGMA is not enabled app-wide; cascades work in code via manual delete in the dataset repository, and in tests via a per-connection PRAGMA. Add a connect-event listener that sets `PRAGMA foreign_keys=ON` for every aiosqlite connection so we don't have to maintain the manual cascade list. · `apps/api/src/research_api/db/engine.py`
- [phase6] [low] Statistics page wizard step 2 has no validation that the chosen columns match the chosen test's variable-type expectations (e.g. nothing stops you from picking a nominal column as the outcome of a t-test). Backend rejects, but the UX could pre-empt. · `apps/web/src/components/statistics/WizardVariableStep.tsx`
- [phase7] [low] Review pushes (PRISMA/search/RoB/extraction) append to the manuscript section. Pushing twice stacks duplicate tables. Consider a `mode=replace|append` query param, or detect the existing block by class hook (`.rob-traffic-light-table`, `.prisma-flow`) and replace in-place. · `apps/api/src/research_api/routes/reviews.py`
- [phase7] [low] RoB 2 catalogue uses UK spelling (`randomisation`) but the AMSTAR-2 inversion vocabulary uses `yes_no/partial_yes/no` rather than the unified low/some_concerns/high — confusing for an international user pool. Either pick one spelling app-wide, or surface tooltips in the form. · `apps/api/src/research_api/services/review/rob_rules.py`
- [phase7] [med] Extraction schema validation rejects flat fields like `notes: "some text"` because the validator expects every group value to be an object. Document the required shape on the GET /extraction/schema response (currently the shape is implicit). · `apps/api/src/research_api/services/review/extraction_schema.py`
