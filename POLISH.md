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
