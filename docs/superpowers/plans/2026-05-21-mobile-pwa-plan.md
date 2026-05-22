# Mobile (PWA) Implementation Plan

**Status:** draft — for iterative review before any code lands.
**Author/date:** 2026-05-21.

## Locked decisions

| Decision | Value |
|---|---|
| Architecture | Single repo, parallel mobile shell at `apps/web/src/mobile/`. Shared lib/hooks/API/types/content with desktop. |
| Breakpoint | Mobile shell shown when `window.innerWidth < 900px`. Above that = desktop UI (unchanged). |
| Bottom tabs | 5 slots: Library, Manuscripts, Stats, Learn, More. |
| PWA scope | Installable + full offline reading. Articles + Learn entries + manuscript snapshots cached in IndexedDB. |
| Override | "Force desktop layout" toggle as a Settings card. Persisted in localStorage. |

## Architecture

```
apps/web/src/
├── App.tsx                  # top-level <DeviceRouter>
├── routes/                  # desktop pages (unchanged)
├── mobile/                  # NEW
│   ├── MobileShell.tsx      # bottom-tab nav + safe-area handling
│   ├── pages/
│   │   ├── MobileLibrary.tsx
│   │   ├── MobileManuscripts.tsx
│   │   ├── MobileStats.tsx
│   │   ├── MobileLearn.tsx
│   │   ├── MobileMore.tsx
│   │   ├── MobileReader.tsx        # opened from Library, no tab
│   │   ├── MobilePeerReview.tsx
│   │   ├── MobileSettings.tsx
│   │   ├── MobileEconomics.tsx
│   │   ├── MobileChecklist.tsx
│   │   └── MobileSubmission.tsx
│   ├── components/
│   │   ├── BottomTabs.tsx
│   │   ├── BottomSheet.tsx
│   │   ├── MobileHeader.tsx
│   │   ├── TouchHighlight.tsx
│   │   └── ...
│   └── lib/
│       ├── viewport.ts             # useViewport hook
│       └── forceDesktop.ts         # zustand store + localStorage
├── lib/                     # SHARED (api, schemas, utils)
├── hooks/                   # SHARED
└── components/              # SHARED (shadcn primitives)
```

**DeviceRouter** (~30 lines, top of `App.tsx`):
- Reads `useViewport()` + `useForceDesktop()`.
- Below 900 AND not forced → `<MobileShell><MobileRoutes/></MobileShell>`.
- Otherwise → existing `<AppShell><DesktopRoutes/></AppShell>`.
- The shared `lib/` means both routers hit the same TanStack Query cache, so switching between desktop and mobile during a session is instant.

**PWA stack**:
- `vite-plugin-pwa` (single new npm dep) — handles manifest, service worker registration, asset precaching.
- Service worker strategy: app shell (HTML/CSS/JS) → `CacheFirst`. API GETs → `NetworkFirst` with cache fallback. Mutations → online-only with a "queued for later" hint (no offline writes in v1).
- IndexedDB via `idb` (small, well-maintained — second new npm dep) for offline content: articles (text + highlights), Learn entries, last-opened manuscript HTML.
- Icons: placeholder 192/512 PNGs in `apps/web/public/icons/` initially; can refresh with a designed icon later.

## Phase M0 — Foundations (~half day)

Pre-work that everything else depends on.

- **Add deps**: `vite-plugin-pwa`, `idb`. ~2 new lines in `package.json`.
- **Vite config**: register `VitePWA({ registerType: 'autoUpdate', manifest: {...}, workbox: {...} })`.
- **Manifest**: `name: "Research Assistant"`, `short_name: "Research"`, `theme_color`, `display: standalone`, `start_url: "/"`.
- **DeviceRouter + viewport hook + force-desktop store**: ~120 LOC total.
- **MobileShell**: bottom-tab nav, safe-area padding, top-header slot, page transition wrapper.
- **Settings card**: "Force desktop layout" toggle, persists in localStorage.
- **Placeholder PWA icons**.
- **Tests**: DeviceRouter switches at 900px, force-desktop overrides correctly, MobileShell renders all 5 tabs.

**Deliverable**: install the PWA on iPhone, open it, see the bottom tabs, all tabs say "coming soon" placeholders. Force-desktop toggle in Settings works.

## Phase M1 — Read-only mobile (~1 day)

Easy wins to validate the shell.

- **MobileSettings** — list of Settings cards (AI providers, Storage, Journal template, Export, Import, Learn link, Health, **+ Force desktop toggle**). Single-column scroll. Reuses the same backend.
- **MobileLearn** — single-column list with a sticky category selector chip-row at top. Tap entry → full-screen reader. Search via a top-sheet that drops down. All 64 curated entries available offline (cached on first visit via IndexedDB).
- **MobilePeerReview** — two big buttons: "Review my manuscript" or "Upload an article". Critique renders as full-screen scrollable cards (Overall / Strengths / Issues / Recommendation). History tab via top swipe.
- **MobileMore** — list of less-frequent actions: Settings, Peer Review, Economics, Checklists, Submission, Sign out, About.

**Tests**: 5 vitest files, ~10 tests. Each page renders, navigation works, offline-mode for Learn returns cached content.

## Phase M2 — Library + Reader with touch highlights (~1.5 days)

The biggest UX win.

### MobileLibrary
- Card list with thumbnail (first-page render from PDF), title, authors, year. Search at top.
- Tap card → opens MobileReader.
- Upload button (floating action button bottom-right): picks files via native picker, or "Take photo of article" (uses camera → OCR via tesseract.js — but only if we want to add that; otherwise just file upload).
- Add by DOI / PubMed ID modal (existing endpoints).

### MobileReader
- Full-screen reading view of extracted article text.
- **Touch highlight model** (your explicit ask, no popup):
  - Long-press a word → enter highlight mode with handles at both ends to extend the selection.
  - Tap one of 4 colour swatches in the bottom bar to apply.
  - To act on an existing highlight: **tap it**. A bottom sheet slides up with:
    - The highlighted text quoted at top.
    - **Paraphrase** button (calls existing AI endpoint, shows result inline).
    - **Note** textarea (saves to existing notes table).
    - **Change colour** chip row.
    - **Delete** at the bottom.
  - No floating popup ever. Bottom sheet is the only interaction surface.
- Highlights sync to backend via existing `highlights` endpoints.
- Offline cache: article text + highlights cached on first open. Reads work offline. New highlights queue until reconnect.

**Tests**: ~8 vitest. Long-press selection, colour application, bottom sheet open/close, paraphrase action, note save, delete.

## Phase M3 — Manuscript read + per-paragraph edit (~1 day)

- **MobileManuscripts** — list of projects with last-edited timestamp.
- Tap project → **MobileManuscriptReader**:
  - Read-only render of all 6 sections + frontmatter, scroll vertically.
  - Same highlight model as MobileReader.
  - **Tap a paragraph** → bottom sheet with:
    - Paragraph text in an editable textarea.
    - "Rewrite with AI" button (calls existing AI rewrite endpoint).
    - Save / Cancel.
  - Saved edits replace that paragraph in the section.
- Citation chips render inline; tap → opens article in MobileReader.
- No live cursor editing, no @-mentions, no toolbar — those stay desktop-only.

**Tests**: ~5 vitest. Read render, paragraph edit sheet, AI rewrite mock, save persists, citation chip navigation.

## Phase M4 — Statistics wizard (~1 day)

A linear page-per-step flow, mirroring your description.

- **Page 1 — Upload masterchart**: drag-drop or file picker. Existing endpoint.
- **Page 2 — Preview + column types**: dataset table (horizontally scrollable, sticky header), tap a column header to set its type (numeric / categorical / date / outcome). AI auto-suggestion enabled by default.
- **Page 3 — Analysis picker**: chip grid of common analyses (t-test, chi-square, regression, ANOVA, Kaplan-Meier, etc.). Tap → analysis-specific page.
- **Page 4 — Analysis-specific config**: minimal form, pick variables from the dataset's columns. "Run" button.
- **Page 5 — Results**: full-screen results card with statistic + p-value + interpretation. "Save to project", "Push to manuscript" buttons.

No live data grid editing, no multi-panel workbench. Heavy stats (mixed-effects, PSM, sensitivity analyses, transformations) stay desktop-only — surfaced via a "Open in desktop" prompt.

**Tests**: ~6 vitest. Upload → preview → analysis → results round-trip with a mock dataset.

## Phase M5 — Mini-apps (~half day)

Each is a one-task screen. Mostly bindings to existing endpoints.

- **MobileEconomics** — ICER / QALY / NMB calculators, single form per analysis type.
- **MobileChecklists** — interactive CONSORT / STROBE / PRISMA / etc. checklists. Tap items to tick. Progress bar. Save to project.
- **MobileSubmission** — cover letter editor (textarea + AI generate) + reviewer response editor (paired textareas). No PDF preview on mobile, defer to "Export from desktop".

**Tests**: ~3 vitest per mini-app.

## Cross-cutting concerns

### Typography & spacing
- Body 16px (avoids iOS auto-zoom on input focus).
- Tap targets ≥ 44×44pt (Apple HIG).
- Headers slightly smaller than desktop (24px vs 28px) — phones are close to your face.

### Motion
- Page transitions: framer-motion slide-from-right on push, slide-back on pop.
- Bottom sheets: spring slide-up with backdrop fade.
- Highlight handles: subtle pulse on first show.

### Safe areas
- Use `env(safe-area-inset-*)` for iPhone notch + home-indicator padding.

### Touch idioms
- Long-press = ~500ms.
- Swipe-down on a bottom sheet dismisses.
- Pull-to-refresh on list pages (Library, Manuscripts).

### Offline behaviour
- Reads work fully offline once cached.
- Writes require network in v1; show a banner "Offline — changes queued" if user tries.
- Service worker auto-updates on each release, with a "Tap to update" toast when a new version is available.

### Testing strategy
- Each phase adds ~5-10 vitest files using `testing-library` with viewport mocked to 390×844 (iPhone 14).
- Integration smoke test: install PWA in headless browser via Puppeteer (optional, can defer).
- Manual QA pass on physical iPhone + iPad portrait + Chrome mobile emulator.

### Accessibility
- All interactive elements have proper roles + aria-labels.
- Highlights have a contrast-aware foreground colour.
- Focus management: bottom-sheet trap, restore on close.

## Open items (decide as we go)

- **App icon design** — placeholder for now, refresh once we have brand direction.
- **Splash screen** — generated from icon + theme colour by `vite-plugin-pwa`.
- **Push notifications** — DEFERRED past v1. No use case yet.
- **Camera-OCR for upload** — defer past M2. Tesseract.js is ~2MB and adds complexity.
- **Compile / Systematic Review on mobile** — DEFERRED indefinitely (you confirmed).

## Estimates

| Phase | Effort | Cumulative |
|---|---|---|
| M0 Foundations | 0.5 day | 0.5 |
| M1 Read-only shells | 1 day | 1.5 |
| M2 Library + Reader | 1.5 days | 3.0 |
| M3 Manuscript | 1 day | 4.0 |
| M4 Stats wizard | 1 day | 5.0 |
| M5 Mini-apps | 0.5 day | 5.5 |

**Total: ~5.5 days.** Each phase produces a shippable slice — you can stop after any of them and the mobile app still works for the features built so far.

## Risks

1. **TipTap on mobile**: avoided entirely — mobile uses a custom non-TipTap renderer. Risk = zero, but means feature parity diverges (a feature you write on desktop won't auto-appear on mobile).
2. **Service worker caching bugs**: PWA caching can leave users stuck on old builds. Mitigation: aggressive auto-update + version banner.
3. **iOS PWA quirks**: Safari has spotty PWA support (no push notifications, limited storage). Doesn't block v1 since we're read+light-write.
4. **Manuscript paragraph edits diverging from desktop's section-as-HTML model**: need to keep paragraph identity stable across edits. Mitigation: assign stable IDs to paragraphs on first render, then patch by ID.

## Approval gate

Before any code lands, you sign off on:

- [ ] This plan, or with edits below.
- [ ] Two new npm deps: `vite-plugin-pwa`, `idb`.
- [ ] Starting with **M0 + M1** as the first batch (delivers an installable PWA with Settings + Learn + Peer Review working).

---

*Edits welcome — strike through what you don't like, comment in the margin, replace whole sections. We'll iterate this doc before opening a single file in `apps/web/src/mobile/`.*
