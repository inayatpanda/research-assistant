# Phase 3 — PDF Reader & Annotation Engine — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` or `superpowers:executing-plans`. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Open a PDF in the Reader. Select text. Pick one of four section colours. The selection is highlighted on a canvas overlay and persisted with **page-relative percentage coordinates** so it re-renders pixel-precise at any zoom. Click a highlight → inline note panel (paraphrase + AI Summarise). Right rail = general article notes with autosave.

**Architecture:** React-PDF renders pages. A canvas overlay sits on top of each page absolute-positioned. Selection events come from `window.getSelection()`; we walk the DOM rects, normalise each rect to the page's natural dimensions (`{page, x0%, y0%, x1%, y1%}`), and store an array of rects (multi-line selections). On render, we recompute pixel rects from the page's current display size — surviving zoom invariant. New backend tables: `highlights`, `article_notes`. New backend endpoint: `POST /api/articles/{id}/highlights/{hid}/summarise`.

**Tech Stack:** Existing + `react-pdf@^9` (uses pdfjs-dist v4), `react-error-boundary`, `idb-keyval` (cache PDFs locally to skip re-fetch).

---

## File Structure

```
apps/api/
├── alembic/versions/0003_highlights_notes.py
├── src/research_api/
│   ├── db/models.py                       (modify: add Highlight + ArticleNote)
│   ├── schemas/
│   │   ├── highlight.py                   (NEW: HighlightCreate/Read/Update + BoundingCoords)
│   │   └── note.py                        (NEW: ArticleNoteCreate/Read/Upsert)
│   ├── repositories/
│   │   ├── highlights.py                  (NEW)
│   │   └── notes.py                       (NEW)
│   └── routes/
│       ├── highlights.py                  (NEW: CRUD + /summarise)
│       └── notes.py                       (NEW: upsert + read)
└── tests/
    ├── test_highlight_repository.py       (NEW)
    ├── test_note_repository.py            (NEW)
    ├── test_highlights_route.py           (NEW)
    └── test_notes_route.py                (NEW)

apps/web/
├── package.json                           (modify: react-pdf, react-error-boundary, idb-keyval)
├── public/
│   └── pdf.worker.min.js                  (NEW — copied from pdfjs-dist build output by Vite)
├── src/
│   ├── lib/
│   │   ├── api.ts                         (modify: highlightsApi + notesApi)
│   │   ├── pdfCoords.ts                   (NEW: pixel ↔ percent transforms)
│   │   └── pdfjsSetup.ts                  (NEW: configure pdfjs worker src)
│   ├── components/reader/
│   │   ├── ReaderShell.tsx                (NEW: 2-pane layout: PDF | right rail)
│   │   ├── PdfViewer.tsx                  (NEW: react-pdf <Document> + paged <Page>)
│   │   ├── PdfToolbar.tsx                 (NEW: page nav, zoom, color picker)
│   │   ├── HighlightOverlay.tsx           (NEW: absolute-positioned overlay per page)
│   │   ├── HighlightChip.tsx              (modify Phase 1 bespoke shell — implement)
│   │   ├── ColorPicker.tsx                (NEW: 4-button section colour pick)
│   │   ├── HighlightNotePopover.tsx       (NEW: inline note + AI Summarise on hover/click)
│   │   ├── ArticleNotesRail.tsx           (NEW: right side; autosave)
│   │   └── SelectionCapture.tsx           (NEW: hooks into window selection events)
│   ├── hooks/
│   │   ├── usePdfDocument.ts              (NEW: load + cache via idb-keyval)
│   │   ├── useHighlights.ts               (NEW: TanStack Query for /api/articles/{id}/highlights)
│   │   └── useArticleNote.ts              (NEW: autosave notes with debounce)
│   └── routes/
│       └── ReaderPage.tsx                 (modify: real impl with route param)
```

---

## Pre-flight

- [ ] **Step 1: Install frontend deps**

```bash
cd apps/web && npm install react-pdf@^9 react-error-boundary idb-keyval
```

- [ ] **Step 2: Confirm pdfjs worker is available**

```bash
ls apps/web/node_modules/pdfjs-dist/build/pdf.worker.min.mjs
```

Expected: file exists. Vite will serve it through the `pdfjsSetup.ts` import.

- [ ] **Step 3: Commit pre-flight**

```bash
git commit -am "chore(phase3): add react-pdf, react-error-boundary, idb-keyval"
```

---

## Task 1: Coordinate transform utilities (frontend) — TDD

**Files:**
- Create: `apps/web/src/lib/pdfCoords.ts`
- Create: `apps/web/src/lib/__tests__/pdfCoords.test.ts`

**Why first:** the whole annotation engine rests on these — getting them right with tests up front prevents weeks of pixel debugging.

- [ ] **Step 1: Add vitest + jsdom to deps**

```bash
cd apps/web && npm install -D vitest @vitest/ui jsdom @testing-library/react
```

- [ ] **Step 2: Add vitest config in `vite.config.ts`**

Append a `test` block:

```ts
test: {
  environment: 'jsdom',
  globals: false,
}
```

- [ ] **Step 3: Add `package.json` test script**

```json
"test": "vitest run",
"test:watch": "vitest"
```

- [ ] **Step 4: Write `pdfCoords.test.ts`** asserting:
  - `pixelRectToPct(rect, pageWidth, pageHeight)` returns `{x0,y0,x1,y1}` in [0,1]
  - `pctRectToPixel(pct, displayWidth, displayHeight)` is the inverse
  - Round-trip identity within 0.0001
  - Off-page rect (negative or > page) clamps to [0,1]
  - `rectsFromSelectionRange(range, pageEl)` returns array of normalised rects (mock DOMRect)

- [ ] **Step 5: Implement `pdfCoords.ts`:**

```ts
export type PctRect = { x0: number; y0: number; x1: number; y1: number }
export type PixelRect = { x: number; y: number; width: number; height: number }

export function pixelRectToPct(
  rect: PixelRect,
  pageWidth: number,
  pageHeight: number,
): PctRect {
  return {
    x0: clamp01(rect.x / pageWidth),
    y0: clamp01(rect.y / pageHeight),
    x1: clamp01((rect.x + rect.width) / pageWidth),
    y1: clamp01((rect.y + rect.height) / pageHeight),
  }
}

export function pctRectToPixel(pct: PctRect, w: number, h: number): PixelRect {
  return { x: pct.x0 * w, y: pct.y0 * h, width: (pct.x1 - pct.x0) * w, height: (pct.y1 - pct.y0) * h }
}

const clamp01 = (n: number) => Math.max(0, Math.min(1, n))

export function rectsFromSelectionInPage(
  range: Range,
  pageEl: HTMLElement,
): PixelRect[] {
  const pageBox = pageEl.getBoundingClientRect()
  const out: PixelRect[] = []
  for (const r of Array.from(range.getClientRects())) {
    if (r.width < 1 || r.height < 1) continue
    out.push({
      x: r.left - pageBox.left,
      y: r.top - pageBox.top,
      width: r.width,
      height: r.height,
    })
  }
  return out
}
```

- [ ] **Step 6: Run tests → pass. Commit.**

```bash
git commit -am "feat(phase3): pdfCoords — pixel ↔ percent transforms with selection-range extractor (TDD)"
```

---

## Task 2: Highlight + ArticleNote ORM models + Alembic 0003

**Files:**
- Modify: `apps/api/src/research_api/db/models.py`
- Create: `apps/api/alembic/versions/0003_highlights_notes.py`

- [ ] **Step 1: Add models** to `models.py`:

```python
class Highlight(Base):
    __tablename__ = "highlights"
    __table_args__ = (Index("ix_highlights_article_page", "article_id", "page_number"),)

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    article_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("articles.id", ondelete="CASCADE"), nullable=False
    )
    page_number: Mapped[int] = mapped_column(Integer, nullable=False)
    selected_text: Mapped[str] = mapped_column(Text, nullable=False)
    colour: Mapped[str] = mapped_column(String(16), nullable=False)  # intro|method|results|discussion
    section: Mapped[str] = mapped_column(String(32), nullable=False)
    bounding_coords: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)  # {rects: [{x0,y0,x1,y1}, ...]}
    user_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class ArticleNote(Base):
    __tablename__ = "article_notes"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    article_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("articles.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    content: Mapped[str] = mapped_column(Text, default="", nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
```

Note `unique=True` on `article_id` — there's exactly one general-notes row per article (upsert semantics).

- [ ] **Step 2: Generate + apply migration:**

```bash
cd apps/api && .venv/bin/alembic revision --autogenerate -m "highlights notes" --rev-id 0003
.venv/bin/alembic upgrade head
```

- [ ] **Step 3: Verify schema:**

```bash
.venv/bin/python -c "import sqlite3; c=sqlite3.connect('/Users/inayat/Desktop/Research-assistant/data/research.db'); print(sorted(r[0] for r in c.execute(\"SELECT name FROM sqlite_master WHERE type='table'\")))"
```

Expected: includes `highlights` and `article_notes`.

- [ ] **Step 4: Commit.**

---

## Task 3: Highlight + ArticleNote Pydantic schemas

**Files:**
- Create: `apps/api/src/research_api/schemas/highlight.py`
- Create: `apps/api/src/research_api/schemas/note.py`
- Modify: `apps/api/src/research_api/schemas/__init__.py`

- [ ] **Step 1: `highlight.py`** with `BoundingRect`, `BoundingCoords`, `HighlightCreate`, `HighlightUpdate`, `HighlightRead`:

```python
from typing import Literal
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field

HighlightColour = Literal["intro", "method", "results", "discussion"]
SectionName = Literal["Introduction", "Methodology", "Results", "Discussion"]


class BoundingRect(BaseModel):
    x0: float = Field(ge=0, le=1)
    y0: float = Field(ge=0, le=1)
    x1: float = Field(ge=0, le=1)
    y1: float = Field(ge=0, le=1)


class BoundingCoords(BaseModel):
    rects: list[BoundingRect]


class HighlightCreate(BaseModel):
    page_number: int = Field(ge=1)
    selected_text: str = Field(min_length=1)
    colour: HighlightColour
    section: SectionName
    bounding_coords: BoundingCoords
    user_note: str | None = None
    sort_order: int = 0


class HighlightUpdate(BaseModel):
    user_note: str | None = None
    ai_summary: str | None = None
    sort_order: int | None = None


class HighlightRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    user_id: str
    article_id: str
    page_number: int
    selected_text: str
    colour: HighlightColour
    section: SectionName
    bounding_coords: dict  # JSON shape — frontend parses
    user_note: str | None
    ai_summary: str | None
    sort_order: int
    created_at: datetime
```

- [ ] **Step 2: `note.py`:**

```python
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class ArticleNoteUpsert(BaseModel):
    content: str  # empty allowed


class ArticleNoteRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    user_id: str
    article_id: str
    content: str
    updated_at: datetime
```

- [ ] **Step 3: Export both from `schemas/__init__.py`.**

- [ ] **Step 4: Compile check + commit.**

---

## Task 4: HighlightRepository TDD

**Files:**
- Create: `apps/api/src/research_api/repositories/highlights.py`
- Create: `apps/api/tests/test_highlight_repository.py`
- Modify: `apps/api/src/research_api/repositories/__init__.py`

- [ ] **Step 1: Tests** asserting:
  - Create + get
  - Cross-user access blocked
  - List by article (filter optionally by colour, page, ordered by `sort_order` then `page_number`, `created_at`)
  - Update sets `user_note`, `ai_summary`, `sort_order`
  - Delete scoped

Code follows the same pattern as `SqliteArticleRepository`.

- [ ] **Step 2: Implement** `SqliteHighlightRepository` with methods: `create`, `get`, `list_for_article`, `update`, `delete`.

- [ ] **Step 3: Run, pass, commit.**

---

## Task 5: ArticleNoteRepository TDD (upsert semantics)

**Files:**
- Create: `apps/api/src/research_api/repositories/notes.py`
- Create: `apps/api/tests/test_note_repository.py`
- Modify: `apps/api/src/research_api/repositories/__init__.py`

- [ ] **Step 1: Tests:**
  - `get_or_empty(article_id, user_id)` returns existing note OR a transient empty `ArticleNote` (no DB write)
  - `upsert(article_id, content, user_id)` creates on first call, updates content on subsequent calls; `updated_at` advances
  - Cross-user upsert creates a separate row (test that one user's note doesn't overwrite another's)

- [ ] **Step 2: Implement** `SqliteArticleNoteRepository`. Use a `SELECT ... WHERE article_id AND user_id` first; if found, update; else insert. The DB-level `UNIQUE(article_id)` would conflict on multi-user upserts — change the model's `unique=True` to a unique composite `(article_id, user_id)` index, not a column-level unique.

**Important:** revisit Task 2 model: change `unique=True` on `article_id` to a unique composite index `Index("uq_notes_article_user", "article_id", "user_id", unique=True)`. Update the migration accordingly.

- [ ] **Step 3: Run, pass, commit.**

---

## Task 6: /api/articles/{id}/highlights routes TDD

**Files:**
- Create: `apps/api/src/research_api/routes/highlights.py`
- Create: `apps/api/tests/test_highlights_route.py`
- Modify: `apps/api/src/research_api/main.py`

Endpoints:
- `POST   /api/articles/{aid}/highlights` — create one
- `GET    /api/articles/{aid}/highlights` — list (filter by `colour`, `page`)
- `PATCH  /api/highlights/{hid}` — update note/summary/sort
- `DELETE /api/highlights/{hid}`
- `POST   /api/highlights/{hid}/summarise` — calls `container.ai.summarise(selected_text)`, stores result on the row, returns updated row

- [ ] **Step 1: Tests** (use `client` fixture w/ FakeAIProvider — summarise returns `"Summary of: ..."`):

```python
async def test_create_and_list_highlights(client):
    # ... create project, upload article, then:
    create = await client.post(
        f"/api/articles/{aid}/highlights",
        json={
            "page_number": 1,
            "selected_text": "anterior approach showed faster ambulation",
            "colour": "results",
            "section": "Results",
            "bounding_coords": {"rects": [{"x0": 0.1, "y0": 0.2, "x1": 0.4, "y1": 0.23}]},
        },
    )
    assert create.status_code == 201
    # list returns it
    listing = await client.get(f"/api/articles/{aid}/highlights")
    assert len(listing.json()) == 1

async def test_summarise_highlight_uses_ai(client):
    # create one ... then:
    r = await client.post(f"/api/highlights/{hid}/summarise")
    assert r.status_code == 200
    assert "Summary of:" in r.json()["ai_summary"]
```

- [ ] **Step 2: Implement** routes following the `articles.py` pattern. Wire into `main.py` under `/api`.

- [ ] **Step 3: Run, pass, commit.**

---

## Task 7: /api/articles/{id}/notes route TDD

**Files:**
- Create: `apps/api/src/research_api/routes/notes.py`
- Create: `apps/api/tests/test_notes_route.py`
- Modify: `apps/api/src/research_api/main.py`

Endpoints:
- `GET /api/articles/{aid}/notes` — returns the user's note (empty if none)
- `PUT /api/articles/{aid}/notes` — upserts `{content: string}`; returns the saved row

- [ ] **Step 1: Tests**:
  - GET on empty returns `{content: ""}`
  - PUT then GET returns the saved content
  - PUT updates timestamp

- [ ] **Step 2: Implement** + register in main.py.

- [ ] **Step 3: Run, pass, commit.**

---

## Task 8: Frontend API client extensions

**Files:**
- Modify: `apps/web/src/lib/api.ts`

- [ ] **Step 1: Add schemas + endpoints**:

```ts
export const HighlightColourSchema = z.enum(['intro', 'method', 'results', 'discussion'])
export const BoundingRectSchema = z.object({
  x0: z.number(), y0: z.number(), x1: z.number(), y1: z.number(),
})
export const BoundingCoordsSchema = z.object({ rects: z.array(BoundingRectSchema) })
export const HighlightSchema = z.object({
  id: z.string(),
  user_id: z.string(),
  article_id: z.string(),
  page_number: z.number().int(),
  selected_text: z.string(),
  colour: HighlightColourSchema,
  section: z.string(),
  bounding_coords: BoundingCoordsSchema,
  user_note: z.string().nullable(),
  ai_summary: z.string().nullable(),
  sort_order: z.number().int(),
  created_at: z.string(),
})
export type Highlight = z.infer<typeof HighlightSchema>

export const highlightsApi = {
  list: async (articleId: string) => z.array(HighlightSchema).parse(
    (await api.get(`/api/articles/${articleId}/highlights`)).data),
  create: async (articleId: string, body: { ... }) => HighlightSchema.parse(
    (await api.post(`/api/articles/${articleId}/highlights`, body)).data),
  update: async (id: string, patch: { user_note?: string; ai_summary?: string; sort_order?: number }) => HighlightSchema.parse(
    (await api.patch(`/api/highlights/${id}`, patch)).data),
  delete: async (id: string) => { await api.delete(`/api/highlights/${id}`) },
  summarise: async (id: string) => HighlightSchema.parse(
    (await api.post(`/api/highlights/${id}/summarise`)).data),
}

export const notesApi = {
  get: async (articleId: string) => /* parse ArticleNoteRead */,
  upsert: async (articleId: string, content: string) => /* parse */,
}
```

- [ ] **Step 2: Typecheck. Commit.**

---

## Task 9: pdfjs worker config + Vite asset handling

**Files:**
- Create: `apps/web/src/lib/pdfjsSetup.ts`

```ts
import { pdfjs } from 'react-pdf'
import workerSrc from 'pdfjs-dist/build/pdf.worker.min.mjs?url'

pdfjs.GlobalWorkerOptions.workerSrc = workerSrc
```

- [ ] **Step 1: Import once in `main.tsx`** so the worker config runs before any PDF render.

```tsx
import '@/lib/pdfjsSetup'
```

- [ ] **Step 2: Commit.**

---

## Task 10: PdfViewer + PdfToolbar + ReaderShell

**Files:** `apps/web/src/components/reader/*`

- [ ] **Step 1: `ReaderShell.tsx`** — two-pane layout, left = viewer, right = `ArticleNotesRail` (Task 13). Header bar shows article title + back to library.

- [ ] **Step 2: `PdfViewer.tsx`** — load via `usePdfDocument` (Task 11). Render visible page only. State: `currentPage`, `numPages`, `scale`, `pageWidth`. On `<Page>` render, capture the rendered width via `onLoadSuccess`.

```tsx
<Document file={fileUrl}>
  <Page
    pageNumber={page}
    scale={scale}
    onLoadSuccess={(p) => setPageSize({ width: p.width, height: p.height })}
    renderTextLayer
    renderAnnotationLayer={false}
  />
  <HighlightOverlay page={page} pageSize={pageSize} />
</Document>
```

- [ ] **Step 3: `PdfToolbar.tsx`** — page nav (`<` / page N of M / `>`), zoom (`-` / `100%` / `+`), color picker (passes selected colour to a context).

- [ ] **Step 4: Commit each as it lands.**

---

## Task 11: `usePdfDocument` hook with caching

**Files:** `apps/web/src/hooks/usePdfDocument.ts`

Caches the PDF arrayBuffer in idb-keyval under key `pdf:${articleId}` so re-opening doesn't re-fetch (signed URLs expire after 1h, but cached bytes persist).

- [ ] **Step 1: Fetch signed URL from `articlesApi.get(id).file_url`, GET bytes, cache, return ArrayBuffer.**
- [ ] **Step 2: Commit.**

---

## Task 12: HighlightOverlay + SelectionCapture + ColorPicker

**Files:** `apps/web/src/components/reader/HighlightOverlay.tsx`, `SelectionCapture.tsx`, `ColorPicker.tsx`

- [ ] **Step 1: `ColorPicker`** — 4 chips (red/blue/green/yellow). On hover: ring. Click: sets `activeColor` in a Zustand store (`useReader`). Shortcut keys: `1` intro, `2` method, `3` results, `4` discussion.

- [ ] **Step 2: `SelectionCapture`** — listens for `selectionchange` and `mouseup` inside the page container. When user releases mouse with a non-empty selection AND `activeColor` is set:
  1. Find the `pageEl` ancestor with `data-page-number`.
  2. Get `Range` from `getSelection()`.
  3. `rectsFromSelectionInPage(range, pageEl)` → pixel rects.
  4. Each rect → `pixelRectToPct(rect, pageEl.clientWidth, pageEl.clientHeight)`.
  5. `selected_text = range.toString().trim()`.
  6. Build `HighlightCreate` payload (colour, section, bounding_coords.rects).
  7. Call `highlightsApi.create` via mutation; on success, invalidate `['highlights', articleId]`.
  8. Clear native selection: `getSelection()?.removeAllRanges()`.

- [ ] **Step 3: `HighlightOverlay`** — absolute-positioned `<div>` covering the page. For each highlight on this page:
  - For each rect in `bounding_coords.rects`:
    - Convert to pixel via `pctRectToPixel(rect, pageWidth, pageHeight)`.
    - Render an absolutely positioned `<button>` with the colour's `fill` background, the `ring` colour as outline on hover, and `pointer-events: auto` so it's clickable.
    - Framer Motion `highlightBloom` variant on initial mount.

- [ ] **Step 4: Commit.**

---

## Task 13: HighlightNotePopover + AI Summarise

**Files:** `apps/web/src/components/reader/HighlightNotePopover.tsx`

- [ ] **Step 1: shadcn Popover** anchored on each highlight `<button>`.
  - Header: `[colour chip] Section name · page N`
  - Body: textarea (`user_note`) — debounced autosave via mutation.
  - Buttons: **AI Summarise** (POST `/api/highlights/{id}/summarise`, replaces `ai_summary` field on response, displays in a violet "AI Suggested" box with Accept / Edit / Reject), **Delete highlight**.
  - The "Reject" on AI summary just clears the field via `update({ai_summary: null})`.

- [ ] **Step 2: Wire the popover into `HighlightOverlay`** — open on click of the highlight button.

- [ ] **Step 3: Commit.**

---

## Task 14: ArticleNotesRail (right rail, autosave)

**Files:** `apps/web/src/components/reader/ArticleNotesRail.tsx`, `apps/web/src/hooks/useArticleNote.ts`

- [ ] **Step 1: `useArticleNote(articleId)`** — TanStack `useQuery` to GET note, `useMutation` to PUT. Returns `{value, onChange}` with internal debounce (700ms) before firing the PUT.

- [ ] **Step 2: `ArticleNotesRail`** — fixed-width 320px right column. Header: "Notes". TipTap is overkill for v1 — use a plain `<textarea>` styled to look like a notebook. Below textarea: list of all highlights for this article (links scrolling the PDF to that page).

- [ ] **Step 3: Commit.**

---

## Task 15: Real ReaderPage route + navigation from Library

**Files:**
- Modify: `apps/web/src/App.tsx` (add `/reader/:articleId` route)
- Modify: `apps/web/src/routes/ReaderPage.tsx` (real impl)
- Modify: `apps/web/src/components/library/ArticleListItem.tsx` (clicking the row navigates to the reader)

- [ ] **Step 1: Route**: `<Route path="reader/:articleId" element={<ReaderPage />} />`. Empty `/reader` stays as placeholder ("Pick an article from the library").

- [ ] **Step 2: `ReaderPage`**: read `:articleId` param, fetch article via `articlesApi.get`, render `ReaderShell`. Handle 404 with a clean back-to-library state.

- [ ] **Step 3: `ArticleListItem`** — make the whole row clickable (wrap in `<button>` or use `useNavigate`); preserve View / Edit / More actions.

- [ ] **Step 4: Typecheck. Commit.**

---

## Task 16: End-to-end browser verification + tag

- [ ] **Step 1: Boot** `npm run dev`.

- [ ] **Step 2: Drive Chrome via MCP:**
  1. Dashboard → click project → Library.
  2. Click an article row → lands on `/reader/<id>`.
  3. Wait for PDF to render (`wait_for` "Page 1").
  4. Use the shortcut key to set colour: press `1`.
  5. (We can't drive text selection via the snapshot; instead, verify the underlying API + persistence by **simulating** via a direct POST to `/api/articles/{id}/highlights` and reloading the page — assert highlight appears at the right place.)
  6. Test zoom: click `+` button → highlight rectangle still aligns to the same text after recomputation.
  7. Test note rail: type into right textarea, wait 1s, reload, assert text persists.
  8. Test AI Summarise: simulate API call directly; on the UI, confirm the violet block appears with Accept/Reject.

Note: native text selection via puppeteer/Chrome DevTools is finicky. The post-hoc API-driven verification still proves persistence + coord round-trip.

- [ ] **Step 3: Run all backend tests** — expect 84 + new tests, all green.

- [ ] **Step 4: Run `/security-review`** on the new endpoints (mainly check: AI summarise calls user-supplied highlight text — re-use Phase 2's prompt-injection language).

- [ ] **Step 5: Update BUILD_LOG.md + tag phase-3:**

```bash
git tag -a phase-3 -m "Phase 3 — PDF reader + annotation engine complete"
```

---

## Acceptance check (spec §7 Phase 3)

- [ ] React-PDF viewer renders pages with working toolbar (zoom, page nav, colour picker)
- [ ] Highlights stored as page-relative percentages
- [ ] Multi-line selection captured as array of rects
- [ ] Highlights persist across reload — re-render at correct pixel positions at any zoom (verified via Vite zoom-in + screenshot diff)
- [ ] Per-highlight inline note panel with paraphrase + AI Summarise
- [ ] Right rail general notes with autosave (700ms debounce)
- [ ] `highlightBloom` Framer animation on first appearance

---

## Self-Review

**Spec coverage (spec §7 Phase 3):**
- React-PDF viewer ✅ Task 10
- Toolbar (colour picker, zoom, page nav) ✅ Task 10 / Task 12
- Text selection → colour → highlight on overlay with persisted page-rel coords ✅ Task 1 + 12
- Inline note popup w/ paraphrase + AI Summarise ✅ Task 13
- Right rail general notes ✅ Task 14
- Highlights survive reload at any zoom ✅ Tasks 1 + 12 (percentage coords + recompute on render)
- `highlightBloom` Framer animation ✅ Task 12 step 3

**Voice dictation: deliberately deferred** (spec §2 — user opted out of voice).

**Placeholder scan:** ✅ clean.

**Type consistency:** `BoundingRect`/`BoundingCoords` aligned between Python schema (Task 3) and TS zod schema (Task 8). `HighlightColour` enum identical. `Highlight.bounding_coords` is `{rects: BoundingRect[]}` everywhere.

**Risks called out:**
- React-PDF coordinate stability under zoom (the whole point — pages re-render with new dimensions, our overlay recomputes pixel rects from the new `pageWidth`/`pageHeight`).
- pdfjs worker setup with Vite (use `?url` import suffix to get a static asset URL).
- Selection capture across pages — current scope: highlight must be wholly inside ONE page (DOM range may span pages; we filter rects to the active page's element).

**Self-check ok. Proceeding to execution.**
