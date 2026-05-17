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
- [phase1] [low] Dashboard project card has no click target / no detail page yet. Cursor changes but nothing happens. Resolve when project detail view ships in Phase 2. · `apps/web/src/components/projects/ProjectCard.tsx`
