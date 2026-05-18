# Phase 8.7 — Figures + CONSORT + Tables + Journal Templates Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` or `superpowers:executing-plans`. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship the three remaining authoring layers a researcher needs to produce a submittable manuscript:

1. **Figures** — researchers upload PNG/JPEG/SVG image files; the system numbers them automatically, lets the user reorder via drag-and-drop, and inserts them into the manuscript via a TipTap atomic node that renders inline. Captions and alt-text travel with the figure across DOCX/PDF export.
2. **CONSORT 2010 diagram** — for RCT-typed projects, a structured flow chart (Enrollment → Allocation → Follow-up → Analysis), server-rendered SVG (same pure-function shape as `services/review/prisma.py`), push-to-Methodology with idempotent replace-by-class.
3. **Tables (TipTap)** — drop the official `@tiptap/extension-table*` packages into the editor + toolbar buttons. Export already supports `<table>` (Phase 8's `_html_walker.py` emits `table_start`/`table_end` events) — verify and extend where needed.
4. **Journal templates** — a declarative catalogue of major orthopaedics journals with word/figure/table caps; `Project.template_journal` is the persisted choice; the `WordCountBar` turns amber/red against the cap.

**Architecture:**

- New tables: `figures` (one row per figure, FK to project + user, FileStorage ref, ordinal, caption, alt_text) and `consort_data` (one row per project; nullable until first edited; rich enrollment/allocation/follow-up/analysis counters). All carry `user_id`. UNIQUE `(project_id, user_id)` on consort_data.
- Migration `0010_figures_consort_templates.py` (chains from `0009_ingest` from Phase 8.6). Adds the two tables and `Project.template_journal String(64) NULL`.
- New service trees:
  - `services/figures/{repository,storage}.py` — multipart upload (PNG/JPEG/SVG magic-byte sniff, 10 MiB cap), ordinal management, reorder + delete.
  - `services/consort/{counter,svg_renderer}.py` — pure functions: counter validates + sums (computes derived totals where appropriate); `svg_renderer` mirrors `services/review/prisma.py` shape (Cochrane-aligned CONSORT 2010 boxes).
  - `services/journal_templates/catalogue.py` — declarative `JOURNALS: dict[str, JournalTemplate]` with required-sections list, max-words-per-section dict, total max words, reference style, ICMJE structured-abstract required, max figures, max tables.
- New routes:
  - `routes/figures.py` — multipart upload, list, get-binary (signed-URL pattern via FileStorage), update-caption, reorder, delete.
  - `routes/consort.py` — get, update (PATCH), push.
  - `routes/journal_templates.py` — `GET /api/journal-templates` (catalogue).
- One new TipTap extension `Figure.tsx` (atomic node, `figureId` attribute, NodeView renders `<img src=...>` from the binary URL).
- Three new npm deps for tables: `@tiptap/extension-table`, `@tiptap/extension-table-row`, `@tiptap/extension-table-header`, `@tiptap/extension-table-cell` (pinned to the existing TipTap 3.23.4 stream).

**Tech Stack additions:**

- API: **no new pip deps.** Pillow is already pinned (`Pillow>=10.0` — used for image dimension probing during upload). SVG is handled as bytes + magic-prefix sniff. Pillow has no native SVG support so SVG bytes get a regex sniff (`<svg`) + a `python-magic` MIME re-check.
- Web: **four new TipTap extension packages** (table, table-row, table-header, table-cell — all at `^3.23.4` to match the installed StarterKit).

---

## File Structure

```
apps/api/
├── alembic/versions/0010_figures_consort_templates.py        (NEW)
├── src/research_api/
│   ├── db/models.py                                          (modify: Figure, ConsortData; Project.template_journal)
│   ├── schemas/
│   │   ├── figure.py                                         (NEW)
│   │   ├── consort.py                                        (NEW)
│   │   ├── journal_template.py                               (NEW)
│   │   ├── project.py                                        (modify: template_journal)
│   │   └── __init__.py                                       (modify: exports)
│   ├── repositories/
│   │   ├── figures.py                                        (NEW)
│   │   ├── consort.py                                        (NEW)
│   │   └── __init__.py                                       (modify: exports)
│   ├── services/
│   │   ├── figures/
│   │   │   ├── __init__.py                                   (NEW)
│   │   │   └── validation.py                                 (NEW — magic-byte sniff + dimension probe)
│   │   ├── consort/
│   │   │   ├── __init__.py                                   (NEW)
│   │   │   ├── counter.py                                    (NEW)
│   │   │   └── svg_renderer.py                               (NEW)
│   │   ├── journal_templates/
│   │   │   ├── __init__.py                                   (NEW)
│   │   │   └── catalogue.py                                  (NEW)
│   │   └── export/_html_walker.py                            (modify: ensure figure node emitted as <img>; verify table walk)
│   └── routes/
│       ├── figures.py                                        (NEW)
│       ├── consort.py                                        (NEW)
│       ├── journal_templates.py                              (NEW)
│       ├── projects.py                                       (modify: PATCH template_journal accepted)
│       ├── reviews.py                                        (modify: add 'consort-flow' to _BLOCK_TAG_BY_CLASS)
│       └── (main.py)                                         (modify: include the three new routers)
└── tests/
    ├── fixtures/
    │   ├── tiny.png                                          (NEW — 12-byte PNG header + minimal body)
    │   ├── tiny.jpg                                          (NEW)
    │   ├── tiny.svg                                          (NEW)
    │   └── totally_not_a_png.bin                             (NEW — bytes that look like PDF)
    ├── test_figure_model.py                                  (NEW)
    ├── test_figure_validation.py                             (NEW — magic-byte sniff)
    ├── test_figure_repository.py                             (NEW)
    ├── test_figures_route_upload.py                          (NEW)
    ├── test_figures_route_list_reorder_delete.py             (NEW)
    ├── test_figures_route_caption_alt.py                     (NEW)
    ├── test_consort_counter.py                               (NEW)
    ├── test_consort_svg_renderer.py                          (NEW)
    ├── test_consort_repository.py                            (NEW)
    ├── test_consort_route.py                                 (NEW)
    ├── test_consort_route_push.py                            (NEW)
    ├── test_journal_templates_catalogue.py                   (NEW)
    ├── test_journal_templates_route.py                       (NEW)
    ├── test_projects_route_template_journal.py               (NEW)
    ├── test_export_tables_round_trip.py                      (NEW — DOCX + PDF carry <table>)
    └── test_security_figures_consort_isolation.py            (NEW — cross-user / cross-project)

apps/web/
├── package.json                                              (modify: 4 new TipTap table deps)
├── src/
│   ├── lib/api.ts                                            (modify: figuresApi, consortApi, journalTemplatesApi)
│   ├── lib/tiptap/extensions/Figure.tsx                      (NEW — atomic node + NodeView)
│   ├── components/manuscript/
│   │   ├── ManuscriptEditor.tsx                              (modify: register Figure + Table extensions)
│   │   ├── EditorToolbar.tsx                                 (modify: table buttons)
│   │   └── WordCountBar.tsx                                  (modify: reads journal cap)
│   ├── components/figures/
│   │   ├── FiguresPanel.tsx                                  (NEW — right rail in ManuscriptPage)
│   │   ├── FigureUploadDialog.tsx                            (NEW)
│   │   ├── FigureCard.tsx                                    (NEW)
│   │   └── FigureReorderHandle.tsx                           (NEW — dnd-kit drag handle)
│   ├── components/consort/
│   │   ├── CONSORTPage.tsx                                   (NEW — or tab in Statistics; we go with /consort top-level route)
│   │   └── CONSORTFlowChart.tsx                              (NEW)
│   ├── components/manuscript/JournalChip.tsx                 (NEW — header chip "Targeting: JBJS · max 4000 words")
│   ├── routes/
│   │   ├── ManuscriptPage.tsx                                (modify: FiguresPanel in right rail; JournalChip in header)
│   │   ├── ConsortPage.tsx                                   (NEW)
│   │   ├── SettingsPage.tsx                                  (modify: journal template selector)
│   │   └── AppRoutes.tsx                                     (modify: /consort route)
│   └── hooks/
│       ├── useFigures.ts                                     (NEW)
│       ├── useConsort.ts                                     (NEW)
│       └── useJournalTemplates.ts                            (NEW)
└── docs/phase-8p7-screenshots/                               (NEW)
```

---

## Pre-flight

- [ ] **Step 1: Verify Phase 8.6 tag is current**: `git tag --list | grep phase-8p6` → should show.
- [ ] **Step 2: Branch (optional)**: `git checkout -b phase-8p7`.
- [ ] **Step 3: Backend baseline**: `cd apps/api && python -m pytest -q` → all green. Record count.
- [ ] **Step 4: Frontend baseline**: `cd apps/web && npm run typecheck && npm test -- --run && npm run build` → clean.
- [ ] **Step 5: Verify migration head**: `cd apps/api && alembic current` → should show `0009_ingest`. This plan's `0010_figures_consort_templates.py` sets `down_revision = "0009"`.
- [ ] **Step 6: Confirm Pillow imports**: `python -c "from PIL import Image; print(Image.__version__)"`.
- [ ] **Step 7: Confirm `Project.study_type` enum**: `grep StudyType apps/api/src/research_api/schemas/project.py` — note there is **no `'Randomised Controlled Trial'` value today** (Phase 1's `StudyType` list omitted it). This plan adds it as Task 0 below. Existing values are: Before/After Intervention, Outcome Study, Risk Factor Analysis, Group Comparison, Prospective Cohort, Retrospective Case Series, Systematic Review.

---

## Task 0: Add `'Randomised Controlled Trial'` to `StudyType` (TDD-supportive)

**Files:**
- Modify: `apps/api/src/research_api/schemas/project.py` (extend `StudyType` Literal)
- Modify: `apps/web/src/lib/api.ts` (extend the matching `z.enum(['Before/After Intervention', ..., 'Randomised Controlled Trial'])`)
- Modify: `apps/web/src/components/projects/CreateProjectDialog.tsx` (add the option to the select)
- Create: `apps/api/tests/test_study_type_rct.py` — assert a Project can be created with `study_type='Randomised Controlled Trial'` and that updates accept it.

No DB migration needed — `Project.study_type` is `String(64)` and SQLite doesn't enforce a CHECK; the constraint lives in the Pydantic schema.

- [ ] **Step 1:** Tests. **Step 2:** Update enums. **Step 3:** Commit: `git commit -am "feat(phase8p7): RCT study type for CONSORT-eligible projects"`.

---

## Task 1: Schema additions — `figures` + `consort_data` + `Project.template_journal` (TDD-supportive)

**Files:**
- Modify: `apps/api/src/research_api/db/models.py`
- Create: `apps/api/alembic/versions/0010_figures_consort_templates.py`
- Create: `apps/api/tests/test_figure_model.py`
- Create: `apps/api/tests/test_consort_repository.py` (scaffold for Task 6 — model assertions here)

### `figures`

- `id String(32) PK`
- `user_id String(64) NOT NULL INDEX`
- `project_id String(32) FK projects(id) ON DELETE CASCADE NOT NULL`
- `file_ref JSON NOT NULL` (FileStorage `{backend, key}`)
- `file_type String(64) NOT NULL` (`'image/png' | 'image/jpeg' | 'image/svg+xml'`)
- `figure_number Integer NOT NULL` (1-based ordinal within project; the repo maintains contiguity on reorder/delete)
- `caption Text NOT NULL DEFAULT ''`
- `alt_text String(500) NOT NULL DEFAULT ''`
- `width_px Integer NULL` / `height_px Integer NULL` (Pillow-probed at upload; NULL for SVG)
- `byte_size Integer NOT NULL`
- `created_at` / `updated_at` (server_default / onupdate)
- Composite UNIQUE `(project_id, user_id, figure_number)`
- Index `ix_figures_project (project_id)`

### `consort_data`

One row per project (UNIQUE `(project_id, user_id)`). All numeric columns nullable until the user enters data; the SVG renderer treats NULL as "—" or skips the line.

Columns:
- `enrollment_assessed Integer NULL`
- `enrollment_excluded Integer NULL`
- `enrollment_excluded_reasons JSON NULL` — `{"reason": count, ...}`
- `randomised Integer NULL`
- `allocated_intervention Integer NULL`
- `allocated_control Integer NULL`
- `intervention_received Integer NULL`
- `control_received Integer NULL`
- `intervention_lost_followup Integer NULL`
- `control_lost_followup Integer NULL`
- `intervention_discontinued Integer NULL`
- `control_discontinued Integer NULL`
- `intervention_analysed Integer NULL`
- `control_analysed Integer NULL`
- `created_at` / `updated_at`

### `projects.template_journal`

- `Project.template_journal Mapped[str | None] = mapped_column(String(64), nullable=True)` — a key into the journal catalogue. Default `None` (no template).

### Migration `0010_figures_consort_templates.py`

```python
revision = "0010"
down_revision = "0009"

def upgrade() -> None:
    op.create_table("figures", ...)  # all columns above
    with op.batch_alter_table("figures", schema=None) as batch_op:
        batch_op.create_index("ix_figures_user_id", ["user_id"])
        batch_op.create_index("ix_figures_project", ["project_id"])
        batch_op.create_unique_constraint(
            "uq_figures_project_user_number",
            ["project_id", "user_id", "figure_number"],
        )

    op.create_table("consort_data", ...)
    with op.batch_alter_table("consort_data", schema=None) as batch_op:
        batch_op.create_index("ix_consort_user_id", ["user_id"])
        batch_op.create_unique_constraint(
            "uq_consort_project_user",
            ["project_id", "user_id"],
        )

    with op.batch_alter_table("projects", schema=None) as batch_op:
        batch_op.add_column(sa.Column("template_journal", sa.String(length=64), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("projects", schema=None) as batch_op:
        batch_op.drop_column("template_journal")
    op.drop_table("consort_data")
    op.drop_table("figures")
```

### Tests

- `test_figure_uniqueness_per_project_user_number_violation_fires`.
- `test_figure_cascades_when_project_deleted`.
- `test_consort_unique_per_project_user`.
- `test_project_template_journal_nullable_and_persists`.

- [ ] **Step 1:** Tests. **Step 2:** Implement models + migration. **Step 3:** `alembic upgrade head`. **Step 4:** Commit.

---

## Task 2: Pydantic schemas

**Files:** `apps/api/src/research_api/schemas/figure.py`, `schemas/consort.py`, `schemas/journal_template.py`, modify `schemas/project.py` and `schemas/__init__.py`.

```python
# figure.py
ImageMime = Literal["image/png", "image/jpeg", "image/svg+xml"]

class FigureRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    project_id: str
    figure_number: int
    caption: str
    alt_text: str
    file_type: ImageMime
    width_px: int | None
    height_px: int | None
    byte_size: int
    file_url: str | None = None   # populated by route via signed_url
    created_at: datetime
    updated_at: datetime

class FigureUpdate(BaseModel):
    caption: str | None = None
    alt_text: str | None = Field(default=None, max_length=500)

class FigureReorderRequest(BaseModel):
    ordered_figure_ids: list[str] = Field(min_length=1)
```

```python
# consort.py
class ConsortData(BaseModel):
    enrollment_assessed: int | None = Field(default=None, ge=0)
    enrollment_excluded: int | None = Field(default=None, ge=0)
    enrollment_excluded_reasons: dict[str, int] | None = None
    randomised: int | None = Field(default=None, ge=0)
    allocated_intervention: int | None = Field(default=None, ge=0)
    allocated_control: int | None = Field(default=None, ge=0)
    intervention_received: int | None = Field(default=None, ge=0)
    control_received: int | None = Field(default=None, ge=0)
    intervention_lost_followup: int | None = Field(default=None, ge=0)
    control_lost_followup: int | None = Field(default=None, ge=0)
    intervention_discontinued: int | None = Field(default=None, ge=0)
    control_discontinued: int | None = Field(default=None, ge=0)
    intervention_analysed: int | None = Field(default=None, ge=0)
    control_analysed: int | None = Field(default=None, ge=0)

class ConsortRead(ConsortData):
    model_config = ConfigDict(from_attributes=True)
    id: str
    project_id: str
    created_at: datetime
    updated_at: datetime
```

```python
# journal_template.py
class JournalTemplate(BaseModel):
    key: str
    label: str
    max_total_words: int
    max_words_by_section: dict[str, int]  # "Abstract": 300, "Introduction": 600, ...
    required_sections: list[str]
    structured_abstract: bool
    reference_style: Literal["vancouver","apa","harvard"]
    max_figures: int | None = None
    max_tables: int | None = None
```

Extend `ProjectUpdate` + `ProjectRead` with `template_journal: str | None`.

- [ ] **Step 1:** Implement. **Step 2:** Export. **Step 3:** Commit.

---

## Task 3: `services/figures/validation.py` — magic-byte sniff + dimension probe (TDD)

**Files:**
- Create: `apps/api/src/research_api/services/figures/validation.py`
- Create: `apps/api/src/research_api/services/figures/__init__.py`
- Create: `apps/api/tests/test_figure_validation.py`
- Create binary fixtures: `tiny.png`, `tiny.jpg`, `tiny.svg`, `totally_not_a_png.bin`.

### Public API

```python
@dataclass(frozen=True)
class ValidatedImage:
    mime: Literal["image/png","image/jpeg","image/svg+xml"]
    width_px: int | None
    height_px: int | None
    byte_size: int

ALLOWED_FIGURE_MIME = {"image/png","image/jpeg","image/svg+xml"}
FIGURE_SIZE_CAP_MB = 10

class FigureValidationError(ValueError): ...

def validate_image_bytes(data: bytes) -> ValidatedImage:
    """Magic-byte sniff via python-magic (already in deps). SVG additionally
    verified by checking the first 1 KiB for a literal '<svg' token.
    Raises FigureValidationError on any failure or unsupported MIME.

    For PNG/JPEG: open via Pillow and read width/height.
    For SVG: width/height stay None (we don't parse the viewBox in v1)."""
```

### Tests

- `test_validate_png_returns_dimensions`.
- `test_validate_jpeg_returns_dimensions`.
- `test_validate_svg_accepts_with_no_dimensions`.
- `test_validate_pdf_disguised_as_png_rejects` (load `totally_not_a_png.bin` — bytes start with `%PDF`).
- `test_validate_empty_bytes_rejects`.
- `test_validate_oversize_bytes_rejects` (bytes longer than 10 MiB).
- `test_validate_truncated_png_rejects` (PNG header but Pillow fails on body).
- `test_validate_svg_without_open_tag_rejects` (`.txt` file masquerading as svg).

- [ ] **Step 1:** Tests + fixtures. **Step 2:** Implement. **Step 3:** Commit.

---

## Task 4: `repositories/figures.py` — `SqliteFigureRepository` (TDD)

**Files:**
- Create: `apps/api/src/research_api/repositories/figures.py`
- Create: `apps/api/tests/test_figure_repository.py`

### Public API

```python
class SqliteFigureRepository:
    async def list(self, *, project_id: str, user_id: str) -> list[Figure]:
        """Ordered by figure_number ASC."""
    async def get(self, figure_id: str, user_id: str) -> Figure | None: ...
    async def create(
        self, *, project_id: str, user_id: str,
        file_ref: dict, file_type: str, width_px: int | None,
        height_px: int | None, byte_size: int,
        caption: str = "", alt_text: str = "",
    ) -> Figure:
        """Assigns figure_number = MAX(figure_number) + 1 within project+user."""
    async def update(
        self, figure_id: str, user_id: str, *,
        caption: str | None = None, alt_text: str | None = None,
    ) -> Figure | None: ...
    async def reorder(
        self, *, project_id: str, user_id: str, ordered_ids: list[str],
    ) -> list[Figure]:
        """Rewrites figure_number across the entire project to match the
        provided order. Validates the id set matches exactly; raises ValueError
        on mismatch."""
    async def delete(self, figure_id: str, user_id: str) -> Figure | None:
        """Deletes the row; recompacts remaining figure_numbers to stay contiguous.
        Returns the deleted row (caller will delete the file from storage)."""
```

### UNIQUE constraint workaround on reorder/delete

SQLite (and Postgres) enforce `UNIQUE(project_id, user_id, figure_number)` per-row, so naive UPDATEs that swap numbers can transiently violate the constraint. Resolution: inside `reorder` and `delete`'s recompact step, **first** offset all rows in the project by `+1000` (a safe magnitude beyond reasonable figure counts), **then** write the final numbers. Two UPDATE statements in one transaction.

### Tests

- `test_create_assigns_first_figure_number_1`.
- `test_create_assigns_next_figure_number_after_existing`.
- `test_create_isolates_numbering_per_project`.
- `test_list_returns_sorted_by_figure_number`.
- `test_update_caption_and_alt_text`.
- `test_reorder_rewrites_figure_numbers_coherently`.
- `test_reorder_rejects_when_ids_do_not_match_project_set`.
- `test_delete_recompacts_remaining_numbers`.
- `test_delete_returns_deleted_row_for_storage_cleanup`.
- `test_get_404_for_other_user`.

- [ ] **Step 1:** Tests. **Step 2:** Implement. **Step 3:** Commit.

---

## Task 5: Routes — Figures CRUD + reorder + binary serve (TDD)

**Files:**
- Create: `apps/api/src/research_api/routes/figures.py`
- Modify: `apps/api/src/research_api/main.py` (include router)
- Create: `apps/api/tests/test_figures_route_upload.py`
- Create: `apps/api/tests/test_figures_route_list_reorder_delete.py`
- Create: `apps/api/tests/test_figures_route_caption_alt.py`

### Endpoints

```
POST   /projects/{pid}/figures              multipart file=… → FigureRead  (201)
GET    /projects/{pid}/figures              → list[FigureRead]
PATCH  /figures/{fid}                       body: FigureUpdate → FigureRead
POST   /projects/{pid}/figures/reorder      body: FigureReorderRequest → list[FigureRead]
DELETE /figures/{fid}                       → 204
```

### Upload flow

1. Resolve project (404).
2. Read bytes; cap at 10 MiB → 413 if exceeded.
3. `validate_image_bytes(data)` → 415 on `FigureValidationError`.
4. `container.storage.save(user_id, "figures", file.filename or "figure", data)` → `StorageRef`.
5. `repo.create(...)` with all fields.
6. Hydrate via `signed_url`. Return 201.

### Binary serve

The existing `routes/files.py` handles signed-URL token routing — figures piggyback on the same path. No new endpoint needed; `FigureRead.file_url` carries the signed URL.

### Tests

- `test_upload_png_returns_201_with_figure_number_1`.
- `test_upload_jpeg_returns_201`.
- `test_upload_svg_returns_201_with_null_dimensions`.
- `test_upload_pdf_rejects_415`.
- `test_upload_oversize_rejects_413`.
- `test_upload_404_on_wrong_user_project`.
- `test_list_figures_ordered_by_number`.
- `test_patch_caption`.
- `test_patch_alt_text_max_500_chars`.
- `test_reorder_rewrites_numbers`.
- `test_reorder_422_when_ids_mismatch`.
- `test_delete_removes_file_from_storage` (assert FileStorage.delete was called).
- `test_delete_recompacts_numbers`.

- [ ] **Step 1:** Tests. **Step 2:** Implement. **Step 3:** Commit.

---

## Task 6: `services/consort/counter.py` + `repositories/consort.py` (TDD)

**Files:**
- Create: `apps/api/src/research_api/services/consort/__init__.py`
- Create: `apps/api/src/research_api/services/consort/counter.py`
- Create: `apps/api/src/research_api/repositories/consort.py`
- Create: `apps/api/tests/test_consort_counter.py`
- Create: `apps/api/tests/test_consort_repository.py` (extends scaffold from Task 1)

### Counter — public API

```python
@dataclass(frozen=True)
class ConsortFlow:
    assessed: int | None
    excluded: int | None
    excluded_reasons: dict[str, int] | None
    randomised: int | None
    allocated: dict[str, int | None]      # {'intervention': X, 'control': Y}
    received: dict[str, int | None]
    lost_followup: dict[str, int | None]
    discontinued: dict[str, int | None]
    analysed: dict[str, int | None]
    warnings: list[str]                    # arithmetic inconsistencies surfaced to UI

def derive_flow(data: ConsortData) -> ConsortFlow:
    """Compute warnings:
    - sum(excluded_reasons.values()) != enrollment_excluded
    - assessed - excluded != randomised
    - allocated_intervention + allocated_control != randomised
    - allocated_intervention < received_intervention etc.
    Warnings are advisory; the SVG renderer still draws whatever numbers it gets."""
```

### Repository — public API

```python
class SqliteConsortRepository:
    async def get_or_create(self, *, project_id: str, user_id: str) -> ConsortDataRow: ...
    async def update(self, *, project_id: str, user_id: str, patch: ConsortData) -> ConsortDataRow: ...
```

### Tests

- `test_derive_flow_warns_when_excluded_reasons_dont_sum`.
- `test_derive_flow_warns_when_assessed_minus_excluded_neq_randomised`.
- `test_derive_flow_warns_when_arms_dont_sum_to_randomised`.
- `test_derive_flow_handles_all_nulls`.
- `test_consort_repo_get_or_create_idempotent_per_project_user`.
- `test_consort_repo_update_persists_all_fields`.
- `test_consort_repo_isolated_per_user`.

- [ ] **Step 1:** Tests. **Step 2:** Implement. **Step 3:** Commit.

---

## Task 7: `services/consort/svg_renderer.py` — CONSORT 2010 SVG (TDD)

**Files:**
- Create: `apps/api/src/research_api/services/consort/svg_renderer.py`
- Create: `apps/api/tests/test_consort_svg_renderer.py`

### Public API

```python
def render_consort_svg(flow: ConsortFlow) -> str:
    """Pure function. Returns SVG markup mirroring CONSORT 2010 (5 levels:
    Enrollment, Allocation, Follow-up, Analysis, plus a Reasons-for-exclusion
    side box).

    Same construction style as services/review/prisma.py — we hand-build the
    SVG via f-strings into a fixed grid of <rect> + <text> nodes. NO external
    libraries; the output must be valid SVG 1.1 and parseable by ElementTree."""
```

Layout (vertical):
1. **Enrollment** — "Assessed for eligibility (n=X)" → "Excluded (n=Y)" side-arrow with reasons sub-list.
2. **Randomised (n=Z)** — single centred box.
3. **Allocation** — two-arm side-by-side: Intervention (n=A1, received=R1) | Control (n=A2, received=R2).
4. **Follow-up** — Lost-to-follow-up + Discontinued per arm.
5. **Analysis** — analysed per arm.

Numbers default to "—" when the corresponding `Optional[int]` is None.

### Tests

- `test_render_consort_svg_returns_well_formed_xml` (parse via `xml.etree.ElementTree.fromstring`).
- `test_render_consort_svg_contains_all_numbers_when_populated`.
- `test_render_consort_svg_shows_em_dash_for_missing_numbers`.
- `test_render_consort_svg_includes_reasons_when_present`.
- `test_render_consort_svg_omits_reasons_block_when_empty`.
- `test_render_consort_svg_html_escapes_reason_labels` (untrusted user-entered reason strings).
- `test_render_consort_svg_root_element_has_xmlns`.

- [ ] **Step 1:** Tests. **Step 2:** Implement. **Step 3:** Commit.

---

## Task 8: Routes — CONSORT get / update / push (TDD)

**Files:**
- Create: `apps/api/src/research_api/routes/consort.py`
- Modify: `apps/api/src/research_api/main.py` (include router)
- Modify: `apps/api/src/research_api/routes/reviews.py` — add `"consort-flow": "figure"` to `_BLOCK_TAG_BY_CLASS`.
- Create: `apps/api/tests/test_consort_route.py`
- Create: `apps/api/tests/test_consort_route_push.py`

### Endpoints

```
GET    /projects/{pid}/consort           → ConsortRead + ConsortFlow + svg (base64) + warnings
PATCH  /projects/{pid}/consort           body: ConsortData → ConsortRead + …
POST   /projects/{pid}/consort/push      → ManuscriptSectionRead   (Methodology)
```

### Project-type gate

`POST /push` (and optionally `GET` — but be permissive on GET so the user can preview the editor UX) refuses with 422 when `Project.study_type != "Randomised Controlled Trial"`. Frontend uses the same gate to hide the CONSORT navigation entry for non-RCT projects.

### Push flow

Mirror `routes/reviews.py::push_prisma`:

```python
svg = render_consort_svg(flow)
encoded = base64.b64encode(svg.encode("utf-8")).decode("ascii")
html = (
    f'<figure class="consort-flow">'
    f'<img src="data:image/svg+xml;base64,{encoded}" '
    f'alt="CONSORT 2010 flow diagram"/>'
    f'<figcaption>CONSORT 2010 flow diagram.</figcaption>'
    f'</figure>'
)
return await _push_to_section(
    session, project_id=pid, section_name="Methodology",
    html=html, class_hook="consort-flow", user_id=user_id,
)
```

Reuse `_push_to_section` from `routes/reviews.py` — **import** it from the reviews module (it's the same plumbing PRISMA uses). Add `'consort-flow'` to the existing `_BLOCK_TAG_BY_CLASS` table.

### Tests

- `test_get_consort_returns_data_and_svg`.
- `test_get_consort_creates_blank_row_when_missing`.
- `test_patch_consort_persists_partial_update`.
- `test_patch_consort_returns_warnings_when_arithmetic_inconsistent`.
- `test_consort_404_when_project_missing`.
- `test_consort_route_404_for_other_user`.
- `test_push_consort_appends_figure_to_methodology`.
- `test_push_consort_idempotent_replaces_previous` (push twice → one figure).
- `test_push_consort_422_when_not_rct`.
- `test_push_consort_404_for_other_user`.

- [ ] **Step 1:** Tests. **Step 2:** Implement. **Step 3:** Commit.

---

## Task 9: `services/journal_templates/catalogue.py` (TDD)

**Files:**
- Create: `apps/api/src/research_api/services/journal_templates/__init__.py`
- Create: `apps/api/src/research_api/services/journal_templates/catalogue.py`
- Create: `apps/api/tests/test_journal_templates_catalogue.py`

### Catalogue

Declarative; eight major orthopaedics journals. Verbatim publisher data are author guidelines that drift quarterly — encode our best snapshot and ship the catalogue as data, easy to update:

```python
JOURNALS: dict[str, JournalTemplate] = {
    "jbjs": JournalTemplate(
        key="jbjs", label="JBJS (Journal of Bone & Joint Surgery)",
        max_total_words=4000,
        max_words_by_section={"Abstract": 300, "Introduction": 600, "Methodology": 1200,
                              "Results": 1000, "Discussion": 900, "Conclusion": 200},
        required_sections=["Abstract","Introduction","Methodology","Results","Discussion","Conclusion"],
        structured_abstract=True, reference_style="vancouver",
        max_figures=8, max_tables=4,
    ),
    "bjj": JournalTemplate(key="bjj", label="Bone & Joint Journal", max_total_words=3500, ...),
    "bjsm": JournalTemplate(key="bjsm", label="British Journal of Sports Medicine", ...),
    "jaaos": JournalTemplate(key="jaaos", label="JAAOS", ...),
    "jor": JournalTemplate(key="jor", label="Journal of Orthopaedic Research", ...),
    "ota-int": JournalTemplate(key="ota-int", label="OTA International", ...),
    "arthroscopy": JournalTemplate(key="arthroscopy", label="Arthroscopy", ...),
    "ajsm": JournalTemplate(key="ajsm", label="American Journal of Sports Medicine", ...),
}

def list_templates() -> list[JournalTemplate]: ...
def get_template(key: str) -> JournalTemplate | None: ...
```

### Tests

- `test_catalogue_has_eight_journals`.
- `test_catalogue_keys_match_pattern` (lowercase + hyphen only).
- `test_every_template_has_required_sections_nonempty`.
- `test_every_template_max_words_sum_le_total_or_warns` (sum of section caps should be ≥ `max_total_words` so the FE chip math is sensible).
- `test_get_template_returns_none_on_unknown_key`.

- [ ] **Step 1:** Tests. **Step 2:** Implement catalogue. **Step 3:** Commit.

---

## Task 10: Routes — journal templates + `Project.template_journal` (TDD)

**Files:**
- Create: `apps/api/src/research_api/routes/journal_templates.py`
- Modify: `apps/api/src/research_api/routes/projects.py` (extend `ProjectUpdate` validator to accept `template_journal: str | None` where the key, if non-null, must exist in the catalogue → 422 if not)
- Modify: `apps/api/src/research_api/main.py` (include router)
- Create: `apps/api/tests/test_journal_templates_route.py`
- Create: `apps/api/tests/test_projects_route_template_journal.py`

### Endpoints

```
GET   /api/journal-templates                  → list[JournalTemplate]
PATCH /api/projects/{pid}  body: {template_journal: "jbjs"}  → ProjectRead
```

### Tests

- `test_list_journal_templates_returns_catalogue`.
- `test_patch_project_template_journal_persists`.
- `test_patch_project_template_journal_unknown_key_422`.
- `test_patch_project_template_journal_null_clears`.
- `test_404_for_other_user_project`.

- [ ] **Step 1:** Tests. **Step 2:** Implement. **Step 3:** Commit.

---

## Task 11: TipTap tables — install + wire into editor + DOCX/PDF export verification (TDD)

**Files:**
- Modify: `apps/web/package.json` (add `@tiptap/extension-table`, `-table-row`, `-table-header`, `-table-cell` at `^3.23.4`)
- Modify: `apps/web/src/components/manuscript/ManuscriptEditor.tsx` (register the four extensions)
- Modify: `apps/web/src/components/manuscript/EditorToolbar.tsx` (or create one if it doesn't yet exist; add Insert Table / Add Row / Delete Row / Add Column / Delete Column buttons + a Toggle Header Row button)
- Create: `apps/web/src/components/manuscript/__tests__/Tables.test.tsx` (vitest)
- Create: `apps/api/tests/test_export_tables_round_trip.py`

### Editor wiring

```tsx
import { Table } from '@tiptap/extension-table'
import { TableRow } from '@tiptap/extension-table-row'
import { TableHeader } from '@tiptap/extension-table-header'
import { TableCell } from '@tiptap/extension-table-cell'

// In useEditor extensions:
Table.configure({ resizable: true, HTMLAttributes: { class: 'rma-table' } }),
TableRow,
TableHeader,
TableCell,
```

Add a `EditorToolbar` row (icon buttons via lucide-react): `TableIcon` → `editor.chain().focus().insertTable({ rows: 3, cols: 3, withHeaderRow: true }).run()`; `Rows3` → addRow; `Trash2` over a row → deleteRow; etc. The toolbar only shows table-specific buttons when the cursor is inside a table.

### Export verification

The existing `_html_walker.py` already emits `("table_start",)`, `("row_start",)`, `("th",)`, `("td",)`, `("row_end",)`, `("table_end",)` — confirm by reading `_html_walker.py` end-to-end. The DOCX exporter (`docx_export.py`) and PDF exporter (`pdf_export.py`) consume those events. We **verify** rather than rewrite:

- `tests/test_export_tables_round_trip.py`:
  - Seed a manuscript section with `<table><tr><th>A</th><th>B</th></tr><tr><td>1</td><td>2</td></tr></table>` content. Run DOCX export. Open the resulting `.docx` via `python-docx` and assert: `len(doc.tables) >= 1`, `doc.tables[0].rows[0].cells[0].text == "A"`, etc.
  - Same for PDF export — assert the output bytes contain the cell strings (`b"A"`, `b"B"`, `b"1"`, `b"2"`). Reportlab Tables are flowables; their text survives as PDF content streams (decode via `pypdf` for assertion).
  - If either exporter is missing event coverage: extend `_html_walker.py` and the exporter handler, then re-test.

### Frontend test

- `tests/Tables.test.tsx`: render the editor with content containing a table → assert the rendered HTML in the `EditorContent` includes `<table class="rma-table">` and the toolbar buttons exist.

- [ ] **Step 1:** Install deps. **Step 2:** Tests (both fe + be). **Step 3:** Implement editor wire + toolbar. **Step 4:** `npm run typecheck && npm test -- --run`. **Step 5:** Commit.

---

## Task 12: TipTap `Figure` extension + atomic NodeView (TDD)

**Files:**
- Create: `apps/web/src/lib/tiptap/extensions/Figure.tsx`
- Modify: `apps/web/src/components/manuscript/ManuscriptEditor.tsx` (register Figure)
- Create: `apps/web/src/lib/tiptap/__tests__/Figure.test.tsx`

### Public API

```tsx
import { Node, mergeAttributes } from '@tiptap/core'
import { NodeViewWrapper, ReactNodeViewRenderer } from '@tiptap/react'

export interface FigureAttributes {
  figureId: string
  caption: string
  altText: string
}

export const Figure = Node.create<{}>({
  name: 'figure',
  group: 'block',
  atom: true,
  draggable: true,
  selectable: true,

  addAttributes() {
    return {
      figureId: { default: null, parseHTML: el => el.getAttribute('data-figure-id') },
      caption:  { default: '',   parseHTML: el => el.querySelector('figcaption')?.textContent ?? '' },
      altText:  { default: '',   parseHTML: el => el.querySelector('img')?.getAttribute('alt') ?? '' },
    }
  },

  parseHTML() { return [{ tag: 'figure[data-figure-id]' }] },

  renderHTML({ HTMLAttributes }) {
    return ['figure',
      mergeAttributes(HTMLAttributes, { 'data-figure-id': HTMLAttributes.figureId, class: 'rma-figure' }),
      ['img', { src: figureBinaryUrl(HTMLAttributes.figureId), alt: HTMLAttributes.altText ?? '' }],
      ['figcaption', {}, HTMLAttributes.caption ?? ''],
    ]
  },

  addNodeView() { return ReactNodeViewRenderer(FigureNodeView) }
})

function FigureNodeView({ node }: NodeViewProps) {
  const { figureId, caption, altText } = node.attrs
  const { data: fig } = useFigure(figureId)  // hook from useFigures.ts
  return (
    <NodeViewWrapper as="figure" className="rma-figure" data-figure-id={figureId}>
      {fig?.file_url ? <img src={fig.file_url} alt={altText} /> : <div className="…skeleton…"/>}
      <figcaption>{caption}</figcaption>
    </NodeViewWrapper>
  )
}
```

### Tests

- `test_figure_node_parses_existing_html`.
- `test_figure_node_renders_with_data_figure_id_attribute`.
- `test_figure_node_atom_is_not_editable_inline`.
- `test_figure_node_caption_is_serialised_in_renderHTML`.

- [ ] **Step 1:** Tests. **Step 2:** Implement. **Step 3:** Commit.

---

## Task 13: Frontend API client + hooks for figures/consort/templates (TDD)

**Files:**
- Modify: `apps/web/src/lib/api.ts`
- Create: `apps/web/src/hooks/useFigures.ts`
- Create: `apps/web/src/hooks/useConsort.ts`
- Create: `apps/web/src/hooks/useJournalTemplates.ts`
- Create: `apps/web/src/lib/__tests__/figuresApi.test.ts`
- Create: `apps/web/src/lib/__tests__/consortApi.test.ts`

```ts
export const FigureSchema = z.object({
  id: z.string(), project_id: z.string(),
  figure_number: z.number().int(),
  caption: z.string(), alt_text: z.string(),
  file_type: z.enum(['image/png','image/jpeg','image/svg+xml']),
  width_px: z.number().int().nullable(),
  height_px: z.number().int().nullable(),
  byte_size: z.number().int(),
  file_url: z.string().nullable().optional(),
  created_at: z.string(), updated_at: z.string(),
})

export const figuresApi = {
  list:    (pid) => api.get(`/api/projects/${pid}/figures`).then(r => z.array(FigureSchema).parse(r.data)),
  upload:  (pid, file) => { const fd = new FormData(); fd.append('file', file); return api.post(`/api/projects/${pid}/figures`, fd).then(r => FigureSchema.parse(r.data)) },
  patch:   (fid, body) => api.patch(`/api/figures/${fid}`, body).then(r => FigureSchema.parse(r.data)),
  reorder: (pid, ids)  => api.post(`/api/projects/${pid}/figures/reorder`, { ordered_figure_ids: ids }).then(r => z.array(FigureSchema).parse(r.data)),
  remove:  (fid) => api.delete(`/api/figures/${fid}`),
}

export const ConsortDataSchema = z.object({ /* all 14 numeric fields + reasons dict */ })
export const ConsortReadSchema = ConsortDataSchema.extend({ id, project_id, created_at, updated_at })

export const consortApi = {
  get:    (pid) => api.get(`/api/projects/${pid}/consort`).then(r => r.data),    // {data, flow, svg_base64, warnings}
  patch:  (pid, body) => api.patch(`/api/projects/${pid}/consort`, body).then(r => r.data),
  push:   (pid) => api.post(`/api/projects/${pid}/consort/push`).then(r => ManuscriptSectionSchema.parse(r.data)),
}

export const journalTemplatesApi = {
  list: () => api.get('/api/journal-templates').then(r => r.data),
}
```

Hooks: `useFigures(projectId)`, `useFigure(figureId)`, `useUploadFigure`, `useReorderFigures`, `useUpdateFigure`, `useDeleteFigure`, `useConsort(projectId)`, `useUpdateConsort`, `usePushConsort`, `useJournalTemplates()`.

### Vitest

- Parse one mocked payload of each schema.
- Assert `figuresApi.upload` puts the file under the `'file'` key.

- [ ] **Step 1:** Schemas + endpoints + hooks. **Step 2:** Vitest. **Step 3:** Commit.

---

## Task 14: `FiguresPanel` + supporting components (TDD-supportive)

**Files (all NEW)** under `apps/web/src/components/figures/`.

### `FiguresPanel.tsx`
- Right-rail in `ManuscriptPage` above `BibliographyPanel`. Lists figures in `figure_number` order with thumbnail (`<img src={f.file_url}>`), caption, alt text, and three buttons: **Insert into manuscript** (chains `editor.commands.insertContent({ type: 'figure', attrs: {figureId: f.id, caption: f.caption, altText: f.alt_text} })`); **Edit metadata**; **Delete**.
- Drag-to-reorder via `@dnd-kit/sortable` (already in deps from Phase 8).
- "+ Add figure" button → opens `FigureUploadDialog`.

### `FigureUploadDialog.tsx`
- `react-dropzone` accepting PNG/JPEG/SVG. On drop: call `useUploadFigure`. Then prompt for caption + alt text in a follow-up step. Close.

### `FigureCard.tsx`
- Reusable card for a figure in the panel. Click thumbnail → open zoom modal (reuse the shadcn Dialog pattern from `ChartImage.tsx` if Phase 8.5 is in).

### `FigureReorderHandle.tsx`
- The `useSortable` drag handle component.

### Tests

- vitest `FiguresPanel.test.tsx`: render with seeded list → assert 2 figure cards, "+ Add figure" button visible.
- vitest `Figure insertion`: mock editor; click "Insert into manuscript"; assert `editor.commands.insertContent` was called with a `figure` node.

- [ ] **Step 1:** Implement. **Step 2:** Vitests. **Step 3:** Commit.

---

## Task 15: CONSORT page + flow chart UI (TDD-supportive)

**Files (all NEW)** under `apps/web/src/components/consort/` + `apps/web/src/routes/ConsortPage.tsx`.

### `ConsortPage.tsx`
- Route: `/projects/:pid/consort` (add to `AppRoutes.tsx`).
- Two columns: left = form (numeric inputs per CONSORT cell, dynamic `reasons` list with add/remove rows); right = rendered SVG flow chart (decoded from base64 returned by `consortApi.get`). Warnings render under the form as an amber callout list.
- Header: "Push to Methodology" button (disabled when `project.study_type !== 'Randomised Controlled Trial'`).

### `CONSORTFlowChart.tsx`
- Renders the SVG via `<img src={'data:image/svg+xml;base64,' + svg_base64}/>` (or inline `dangerouslySetInnerHTML` *only if* we trust the renderer; for v1 base64 image is safer).

### Tests

- vitest `ConsortPage.test.tsx`: render with seeded data → assert form fields populate; assert warnings render when service returns them; assert "Push" disabled for non-RCT projects.

- [ ] **Step 1:** Implement. **Step 2:** Vitest. **Step 3:** Commit.

---

## Task 16: Journal template UX — `JournalChip` + `WordCountBar` integration

**Files:**
- Create: `apps/web/src/components/manuscript/JournalChip.tsx`
- Modify: `apps/web/src/components/manuscript/WordCountBar.tsx` (read journal cap)
- Modify: `apps/web/src/routes/ManuscriptPage.tsx` (render chip in header)
- Modify: `apps/web/src/routes/SettingsPage.tsx` (selector to set `template_journal`)

### `JournalChip.tsx`
- Reads `project.template_journal` + the catalogue (via `useJournalTemplates`). Renders a small pill: "Targeting: JBJS · max 4000 words" with a dropdown (or link to Settings) to change. When `template_journal` is null: pill says "No template — pick one" linking to Settings.

### `WordCountBar.tsx`
- Already shows the total word count. Extended: when a template is active, look up the per-section + total caps. Bar turns amber at 90% of the cap, red at 100%, and renders the cap number alongside the current count.
- Per-section cap derived from the active section's name; total cap from the same template.

### Tests

- vitest `WordCountBar.test.tsx` extended: cap = 1000, words = 800 → bar shows amber class; words = 1100 → red class.
- vitest `JournalChip.test.tsx`: chip renders label + max-words when template set; chip links to Settings when null.

- [ ] **Step 1:** Implement. **Step 2:** Vitests. **Step 3:** Commit.

---

## Task 17: Security regression — cross-user / cross-project isolation

**File:** `apps/api/tests/test_security_figures_consort_isolation.py`.

- `test_figures_list_isolated_per_user`.
- `test_get_figure_404_for_other_user`.
- `test_upload_figure_404_when_project_owned_by_other_user`.
- `test_reorder_figures_rejects_when_ids_include_other_users_figure`.
- `test_delete_figure_404_for_other_user`.
- `test_consort_get_404_for_other_user`.
- `test_consort_patch_404_for_other_user`.
- `test_consort_push_404_for_other_user`.
- `test_consort_push_422_when_project_not_rct`.
- `test_patch_project_template_journal_404_for_other_user`.
- `test_journal_templates_list_is_public_per_user_isolation_not_applicable` (catalogue is public; doc it as such).

- [ ] **Step 1:** Tests. **Step 2:** Fix any leaks. **Step 3:** Commit.

---

## Task 18: E2E browser smoke (chrome-devtools-mcp)

- [ ] **Step 1:** Boot servers.
- [ ] **Step 2:** Drive Chrome via MCP:
  1. Create an RCT project ("Randomised Controlled Trial").
  2. Open `/manuscript` → assert `FiguresPanel` visible in right rail.
  3. Open `FigureUploadDialog` → drop a PNG → enter caption "Knee imaging" → close → assert Figure 1 appears in the panel.
  4. Upload a JPEG → assert Figure 2 appears.
  5. Drag Figure 2 above Figure 1 → assert their numbers swap.
  6. Click "Insert into manuscript" on Figure 1 → switch to Results → assert the `<figure>` node rendered with the image and caption.
  7. Export the manuscript to DOCX → open the file → assert the figure appears.
  8. Open `/consort` → fill in: Assessed=200, Excluded=50 (reasons: "Declined"=30, "Ineligible"=20), Randomised=150, Allocated I=75, C=75, …, Analysed I=72, C=70 → assert the SVG re-renders → assert any warnings list is empty.
  9. Click "Push to Methodology" → switch to /manuscript → Methodology → assert the CONSORT figure inline.
  10. Open Settings → set Journal Template to "JBJS" → return to Manuscript → assert the chip reads "Targeting: JBJS · max 4000 words" and the bar turns amber when typing past 3600 words.
  11. Insert a TipTap table → fill cells → export DOCX → assert the table cells round-trip.
- [ ] **Step 3:** Screenshot every step under `docs/phase-8p7-screenshots/`.
- [ ] **Step 4:** Accessibility audit on `/manuscript` and `/consort`: every figure has non-empty `alt`; CONSORT SVG has an `<title>` element; toolbar buttons have aria-labels.

---

## Task 19: `/security-review`

Targets:

- `services/figures/validation.py` — magic-byte sniff at the entry; SVG additionally checked via literal `<svg` token; Pillow opens PNG/JPEG only (SVG never reaches Pillow → no XML-bomb surface).
- `services/consort/svg_renderer.py` — every user-entered exclusion reason is `html.escape`d before being interpolated into the SVG.
- `routes/figures.py` — every upload routes through `validate_image_bytes` BEFORE saving to storage; storage key includes `user_id` + `figures` namespace; signed URLs from existing `signed_urls.py`.
- `routes/consort.py` — every read/write scopes to `user_id`; push reuses `_push_to_section` which already guards on the manuscript section repo's `user_id`.
- `routes/journal_templates.py` — GET only; no auth-sensitive data.
- Frontend `Figure` extension — `<img src>` is always a server-signed URL (no `data:` URIs from user input); `figcaption` content is React-rendered text (no `dangerouslySetInnerHTML`).
- Frontend `CONSORTFlowChart` — renders the server-rendered SVG via base64 `<img>` (no inline injection).
- TipTap Table extension — accepts user input by design; XSS surface mitigated because `editor.getHTML()` produces a fixed allowed schema; the server's `_html_walker.py` whitelist is the actual defence.

- [ ] **Step 1:** Run `/security-review`.
- [ ] **Step 2:** Fix HIGH + MED inline. Log LOW to `POLISH.md`.
- [ ] **Step 3:** Commit.

---

## Task 20: BUILD_LOG entry + tag

Append `## 2026-05-18 · Phase 8.7 — Figures + CONSORT + Tables + Journal templates ✅ COMPLETE` to `BUILD_LOG.md`. Cover: backend (two new tables, migration `0010`, three new service trees, three new route modules, `Project.template_journal`), frontend (four new TipTap packages, Figure atomic node, FiguresPanel, CONSORTPage, JournalChip, WordCountBar cap-aware), test deltas (~+95 backend tests, ~+15 vitest), acceptance bar maps to spec, decisions (Pillow probes PNG/JPEG only — SVG dimensions deferred; CONSORT pushes a single replace-by-class figure; journal templates are a server-side data file rather than a separate table to keep them easy to update without migration).

- [ ] **Step 1:** Compose entry.
- [ ] **Step 2:** `git tag phase-8p7`.

---

## Out of scope (deferred)

- **In-text Figure {N} cross-references** that auto-renumber on reorder — v1 inserts the figure inline via the panel; the editor doesn't track inline `Figure 1` text references. Logged in `DEFERRED.md`.
- **PRISMA-style auto-derivation of CONSORT** from screening_records — v1 is manual entry.
- **SVG dimension parsing** (viewBox) for figures — Pillow doesn't read SVG; `width_px`/`height_px` stay None.
- **Per-journal section ordering enforcement** in the editor — chip is advisory only in v1.
- **Word-count cap enforcement on save** — bar turns red but never blocks.
- **Image cropping / annotation in-browser** — out of scope.
- **Resizable table columns** in TipTap — enabled in `Table.configure({ resizable: true })` but no cell-merge / split-cell UI in v1.
- **More than 8 journals** in the catalogue — easy to extend; defer until product feedback.

---

## Self-Review

**Spec coverage:**
- Figures table + migration + service + routes ✅ Tasks 1, 3, 4, 5
- TipTap Figure node + FiguresPanel + inserts ✅ Tasks 12, 14
- CONSORT data + counter + SVG + push ✅ Tasks 6, 7, 8, 15
- Tables (TipTap + DOCX/PDF round-trip) ✅ Task 11
- Journal templates catalogue + project field + WordCountBar cap + chip ✅ Tasks 9, 10, 16
- StudyType RCT added ✅ Task 0
- Cross-user / cross-project isolation ✅ Task 17

**Multi-user readiness:** every new row carries `user_id`. Every read scopes to `user_id`. Storage keys include user_id; UNIQUE constraints include user_id where contention is possible.

**TDD ordering:** every model/service/repo has tests written before implementation. Route handlers likewise. Cross-cutting security regression is Task 17.

**Bite-sized tasks:** 21 tasks (0–20). Each ~5-minute step.

**Type consistency:** `ImageMime`, `ConsortData`, `JournalTemplate` are identical Python ↔ TS via `Literal` / `z.enum` / `z.object` pairs.

**Self-check ok. Proceeding to execution.**
````

---
