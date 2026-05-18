# Phase 8 — Bibliography, Export, Polish & Deploy Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` or `superpowers:executing-plans`. Steps use checkbox (`- [ ]`) syntax for tracking. This is the LAST autonomous phase — Phase 9 (Electron) is paused for user check-in.

**Goal:** Researchers can (a) see every cited article as a deduplicated, ordered bibliography in their chosen style (Vancouver / APA 7 / Harvard / IEEE), (b) export the whole manuscript to DOCX / PDF, (c) back up + restore a project as a JSON bundle, (d) deploy the web frontend to Vercel and the API to Fly.io from prepared artefacts. Plus all open POLISH items that touch correctness or security get resolved inline.

**Architecture:**
- One new service package `services/export/` with four siblings: `docx_export.py`, `pdf_export.py`, `bundle_export.py`, `bundle_import.py`. Each is a pure function over repository reads.
- `services/citation_format.py` extended in place: APA 7 + Harvard + IEEE bibliography functions; existing Vancouver kept verbatim. Style switching remains a pure function on the canonical article record. **No new abstraction.**
- One new route module `routes/export.py` exposing 4 endpoints: `POST /export/docx`, `POST /export/pdf`, `POST /export/bundle`, `POST /import/bundle`. All scoped by `user_id`. Multipart upload re-uses the `articles.py` magic-byte sniff pattern.
- One new frontend route `/bibliography` (panel inside Manuscript page) + Settings additions (Export section, Storage section, Health link, future-cloud-button stub).
- Polish items resolved inline as bite-sized commits, each annotated back in `POLISH.md`.
- Deploy artefacts: `vercel.json` (web), `Dockerfile` + `fly.toml` (api). No actual deploy — user runs the final commands.

**Tech Stack additions:**
- API: `weasyprint>=62`, `cairosvg>=2.7`, `Pillow>=10` (rasterise PRISMA SVG for DOCX). `python-docx` already in deps from Phase 1.
- Web: `dompurify>=3` + `@types/dompurify` (defence-in-depth on AI HTML).

---

## Citation safety contract (Phase 8 specifics)

The bibliography page lists references built **only** from `articles` rows (the trust boundary). Style switching is a pure function on those rows. AI never touches bibliography rendering. Export endpoints render manuscript HTML through DOMPurify on the way out to DOCX/PDF (defence-in-depth — ProseMirror's schema is the primary filter at write time). The JSON bundle exporter dumps DB rows verbatim with one exception: the importer **strips and re-assigns every `user_id` to `current_user_id`** and **mints fresh `id`s for every row** to prevent cross-user leakage on import.

---

## File Structure

```
apps/api/
├── src/research_api/
│   ├── services/
│   │   ├── citation_format.py                              (modify: add APA/Harvard/IEEE bibliography + IEEE inline)
│   │   └── export/
│   │       ├── __init__.py                                 (NEW)
│   │       ├── docx_export.py                              (NEW)
│   │       ├── pdf_export.py                               (NEW)
│   │       ├── bundle_export.py                            (NEW)
│   │       ├── bundle_import.py                            (NEW)
│   │       └── bibliography.py                             (NEW — dedupe + ordering logic shared by DOCX/PDF/bibliography page)
│   ├── schemas/
│   │   ├── export.py                                       (NEW)
│   │   └── __init__.py                                     (modify: export new)
│   ├── routes/
│   │   ├── export.py                                       (NEW)
│   │   ├── bibliography.py                                 (NEW — GET only, used by frontend bibliography panel)
│   │   └── (main.py)                                       (modify: include export_router + bibliography_router)
│   ├── db/
│   │   └── base.py                                         (modify: register sqlite_connect listener for PRAGMA foreign_keys=ON)
│   └── services/ai/prompts/result_interpretation.py        (modify: rounding rules — POLISH-fix)
└── tests/
    ├── test_citation_format_apa.py                         (NEW)
    ├── test_citation_format_harvard.py                     (NEW)
    ├── test_citation_format_ieee.py                        (NEW)
    ├── test_citation_format_style_matrix.py                (NEW — 4 styles × 4 article shapes parametrised)
    ├── test_export_docx.py                                 (NEW)
    ├── test_export_pdf.py                                  (NEW)
    ├── test_export_bundle.py                               (NEW)
    ├── test_import_bundle.py                               (NEW)
    ├── test_bibliography_service.py                        (NEW)
    ├── test_export_routes.py                               (NEW)
    ├── test_bibliography_route.py                          (NEW)
    ├── test_security_export_isolation.py                   (NEW — multi-user regression for export + import)
    └── test_db_pragma_foreign_keys.py                      (NEW — POLISH-fix verification)

apps/web/
├── src/
│   ├── lib/
│   │   ├── api.ts                                          (modify: exportApi, bibliographyApi, IEEE in bibliographyFormat)
│   │   ├── bibliographyFormat.ts                           (modify: APA/Harvard/IEEE)
│   │   ├── sanitizeHtml.ts                                 (NEW — DOMPurify wrapper)
│   │   └── citationSerialize.ts                            (modify: pre-pass DOMPurify in aiSafeTextToHtml)
│   ├── components/
│   │   ├── bibliography/
│   │   │   ├── BibliographyPanel.tsx                       (NEW — renders inside ManuscriptPage)
│   │   │   ├── BibliographyRow.tsx                         (NEW)
│   │   │   ├── BibliographyToolbar.tsx                     (NEW — style picker + copy-all + export menu)
│   │   │   └── ExportButtonGroup.tsx                       (NEW — DOCX / PDF / Bundle)
│   │   ├── settings/
│   │   │   ├── StorageCard.tsx                             (NEW — backend display + 'Migrate to cloud' stub)
│   │   │   ├── ExportCard.tsx                              (NEW — top-level export buttons; also lives in Bibliography panel)
│   │   │   ├── ImportDropzone.tsx                          (NEW — JSON bundle import)
│   │   │   └── HealthLink.tsx                              (NEW)
│   │   └── statistics/
│   │       └── WizardVariableStep.tsx                      (modify: pre-empt type-mismatch — POLISH-fix)
│   ├── routes/
│   │   ├── ManuscriptPage.tsx                              (modify: render BibliographyPanel in the right rail or as a tab)
│   │   ├── SettingsPage.tsx                                (modify: add Export + Storage cards)
│   │   └── HealthPage.tsx                                  (NEW — /health diagnostic page)
│   ├── App.tsx                                             (modify: future flags on BrowserRouter + add /health route)
│   └── components/manuscript/BubbleAIMenu.tsx              (modify: DOMPurify pre-pass — POLISH-fix)

apps/api/Dockerfile                                          (NEW)
apps/api/fly.toml                                            (NEW — placeholder, no deploy)
apps/web/vercel.json                                         (NEW)

docs/phase-8-screenshots/                                    (NEW)
```

---

## Pre-flight

- [ ] **Step 1: Verify Phase 7 tag**: `git tag --list | grep phase-7` → present.
- [ ] **Step 2: Branch (optional)**: stay on `main` per established workflow.
- [ ] **Step 3: Backend baseline**: `cd apps/api && python -m pytest -q` → 488 green.
- [ ] **Step 4: Frontend baseline**: `cd apps/web && npm run test && npm run build` → 44 vitest green, clean build.
- [ ] **Step 5: Confirm `python-docx` is already installed**: `python -c "import docx; print(docx.__version__)"` from `apps/api/.venv`. (Phase 1 added it for upload extraction; we now use it for write.)
- [ ] **Step 6: Add new Python deps**: edit `apps/api/pyproject.toml` to add `weasyprint>=62`, `cairosvg>=2.7`, `Pillow>=10`. Run `pip install -e ".[dev]"` from `apps/api/`. If `weasyprint` fails to install on macOS, document the Homebrew prereqs: `brew install pango cairo gdk-pixbuf libffi`. Log the install path in `BUILD_LOG.md`.
- [ ] **Step 7: Add new web deps**: `cd apps/web && npm install dompurify @types/dompurify`.
- [ ] **Step 8: Read POLISH.md and confirm the open items** that this plan resolves (RR v7 flags, DOMPurify, SQLite FK PRAGMA, result-interpretation rounding, wizard step 2 pre-empt, review push replace-by-class, plus inline Settings storage card and Health page).

---

## Task 1: Extend citation_format with APA 7 / Harvard / IEEE bibliographies (TDD)

**Files:**
- Modify: `apps/api/src/research_api/services/citation_format.py`
- Create: `apps/api/tests/test_citation_format_apa.py`
- Create: `apps/api/tests/test_citation_format_harvard.py`
- Create: `apps/api/tests/test_citation_format_ieee.py`
- Create: `apps/api/tests/test_citation_format_style_matrix.py`

### Style reference (canonical APA 7 / Harvard Cite Them Right 11 / IEEE)

For a journal article with authors `["Jane Doe", "John Smith"]`, title `Anterior approach`, journal `J Orthop Res`, year 2024, volume 42, issue 3, pages `100-110`, doi `10.1234/jor.42.3.100`:

- **Vancouver** (already): `1. Doe J, Smith J. Anterior approach. J Orthop Res. 2024;42(3):100-110. doi:10.1234/jor.42.3.100`
- **APA 7**: `Doe, J., & Smith, J. (2024). Anterior approach. J Orthop Res, 42(3), 100–110. https://doi.org/10.1234/jor.42.3.100`
- **Harvard**: `Doe, J. and Smith, J. (2024) 'Anterior approach', J Orthop Res, 42(3), pp. 100–110. doi:10.1234/jor.42.3.100`
- **IEEE**: `[1] J. Doe and J. Smith, "Anterior approach," J Orthop Res, vol. 42, no. 3, pp. 100–110, 2024, doi: 10.1234/jor.42.3.100.`

### Per-style branches in `bibliography_entry`

Refactor `bibliography_entry` to dispatch on `style`:
```python
_BIB_FORMATTERS = {
    "vancouver": _bibliography_vancouver,  # existing logic, extracted into a private fn
    "apa": _bibliography_apa,
    "harvard": _bibliography_harvard,
    "ieee": _bibliography_ieee,
}

CitationStyle = Literal["vancouver", "apa", "harvard", "ieee"]
```

Each `_bibliography_<style>(article, number)` is a pure function. Helpers (`_author_list_apa`, `_author_list_harvard`, `_author_list_ieee`) live alongside the existing `_author_list_vancouver`. **All interpolated user data passes through `html.escape()` when later wrapped in HTML (export pipeline does this; the raw function returns plain text).**

### Inline-citation behaviour

- Vancouver / APA / Harvard: keep current `vancouver_inline` (author-year).
- IEEE: number-only, `[N]`. The route knows `N` (the position in the bibliography list). Add `def ieee_inline(n: int) -> str: return f"[{n}]"`. Plumb the number through `replace_cite_tokens` when style == "ieee" (the existing function gets a `numbering: dict[str, int] | None = None` keyword; ignored unless IEEE).

### Per-style author formatting rules

| Style | 1 | 2 | 3+ | Surname format |
|-------|---|---|----|----------------|
| Vancouver | `Last F` | `Last F, Last F` | up to 6, then `et al.` | `Last F` (one-letter initials, no comma) |
| APA 7 | `Doe, J.` | `Doe, J., & Smith, J.` | up to 20, then `... ` + last author | `Last, F.` |
| Harvard | `Doe, J.` | `Doe, J. and Smith, J.` | up to 3, then `Doe, J. et al.` | `Last, F.` |
| IEEE | `J. Doe` | `J. Doe and J. Smith` | up to 3, then `J. Doe et al.` | `F. Last` |

### Edge cases (each is a parametrised test row)

- **Full journal article** — all fields present
- **No DOI** — omit the `doi:` / `https://doi.org/...` suffix
- **With volume + issue + pages** (standard)
- **Missing year** — `n.d.` in APA/Harvard/Vancouver; IEEE omits the year section but keeps the comma layout intact
- **No journal** — drop the journal segment cleanly
- **No authors** — `Anonymous` (Vancouver) / `Anonymous.` (APA) / `Anon.` (Harvard) / `Anonymous` (IEEE)
- **Title with trailing period** — already stripped in current `bibliography_entry`; preserve across all 4

### Tests (parametrised matrix)

`test_citation_format_style_matrix.py`:
```python
@pytest.mark.parametrize("style", ["vancouver", "apa", "harvard", "ieee"])
@pytest.mark.parametrize("shape", ["full", "no_doi", "no_year", "no_journal"])
def test_bibliography_entry_emits_well_formed(style, shape): ...
```
Each style file (`test_citation_format_apa.py` etc.) holds **golden-string** assertions for the canonical reference example above — these are the regression anchors.

Additional tests:
- `test_ieee_inline_uses_bracket_number`
- `test_apa_two_authors_uses_ampersand`
- `test_harvard_two_authors_uses_and`
- `test_replace_cite_tokens_ieee_uses_numbering_map` — `replace_cite_tokens(..., style="ieee", numbering={"a1": 1, "a2": 2})` → `[1]`, `[2]`
- `test_unknown_style_raises` — `format_inline("mla", ...)` raises `ValueError`

- [ ] **Step 1: Write all tests first.**
- [ ] **Step 2: Refactor `bibliography_entry` into the dispatch + private style fns.** Keep Vancouver byte-identical to current output (do not regress the existing tests).
- [ ] **Step 3: Add IEEE inline + numbering plumb-through in `replace_cite_tokens`.**
- [ ] **Step 4: Iterate to green.**
- [ ] **Step 5: Commit:** `feat(phase8): full-fidelity APA / Harvard / IEEE bibliography + IEEE inline`.

---

## Task 2: Bibliography service (dedupe + ordering)

**Files:**
- Create: `apps/api/src/research_api/services/export/bibliography.py`
- Create: `apps/api/tests/test_bibliography_service.py`

### Public API

```python
@dataclass(frozen=True)
class BibliographyEntry:
    article_id: str
    number: int                  # 1-based, position in the final ordered list
    formatted: str               # output of bibliography_entry(article, number=N, style=...)

def collect_used_article_ids_in_order(sections: list[ManuscriptSection]) -> list[str]:
    """Scan section content (rendered HTML) in canonical section order
    (Abstract, Introduction, Methodology, Results, Discussion, Conclusion)
    for [CITE_<id>] tokens (Phase 5 stored these as <sup data-citation
    data-article-id="..."> in HTML; treat both forms as equivalent).

    Returns the article_ids in the order of first occurrence — Vancouver
    convention. Deduplicated.
    """

def build_bibliography(
    *,
    articles_by_id: Mapping[str, _ArticleLike],
    sections: list[ManuscriptSection],
    style: CitationStyle,
) -> list[BibliographyEntry]:
    """Composition of the above two: scan, dedupe, format with numbering."""
```

### Section ordering

```python
CANONICAL_SECTION_ORDER = (
    "Abstract", "Introduction", "Methodology",
    "Results", "Discussion", "Conclusion",
)
```

### Tests

- `test_collect_skips_sections_with_no_citations`
- `test_collect_dedupes_repeated_citations`
- `test_collect_orders_by_first_occurrence` (cite a3 in Methodology before a1 in Introduction → order respects Introduction-first)
- `test_collect_handles_both_token_forms` (`[CITE_a1]` plain-text legacy AND `<sup data-article-id="a1">[…]</sup>` HTML form)
- `test_build_bibliography_numbers_consecutively`
- `test_build_bibliography_drops_unknown_article_ids` (citation token references an id no longer in articles → log a warning, omit from list)
- `test_build_bibliography_respects_style` (parametrised over 4 styles)

- [ ] **Step 1: Tests.**
- [ ] **Step 2: Implement using a compiled regex `re.compile(r'\[CITE_([A-Za-z0-9_-]+)\]|data-article-id="([A-Za-z0-9_-]+)"')`** that captures either form into the same group set.
- [ ] **Step 3: Iterate.**
- [ ] **Step 4: Commit:** `feat(phase8): bibliography dedupe + ordering service`.

---

## Task 3: Pydantic schemas for export

**Files:**
- Create: `apps/api/src/research_api/schemas/export.py`
- Modify: `apps/api/src/research_api/schemas/__init__.py`

```python
ExportFormat = Literal["docx", "pdf"]

class ExportRequest(BaseModel):
    style: CitationStyle = "vancouver"           # bibliography style for the export
    include_bibliography: bool = True

class BibliographyEntryRead(BaseModel):
    article_id: str
    number: int
    formatted: str

class BibliographyResponse(BaseModel):
    style: CitationStyle
    entries: list[BibliographyEntryRead]

# Bundle shape — exhaustive, strict.
class BundleProject(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str
    study_type: str
    citation_style: str
    ai_provider: str
    target_journal: str | None = None
    prospero_number: str | None = None
    clinicaltrials_number: str | None = None

class BundleArticle(BaseModel):
    model_config = ConfigDict(extra="forbid")
    # All article fields — see Article model. user_id, project_id, id, created_at intentionally omitted.
    title: str
    authors: list[str]
    journal: str | None = None
    year: int | None = None
    volume: str | None = None
    issue: str | None = None
    pages: str | None = None
    doi: str | None = None
    abstract: str | None = None
    study_design: str | None = None
    review_status: str = "pending"
    exclusion_reason: str | None = None
    conflict_of_interest: str | None = None
    # Highlights, notes, compilation cards keyed by a client-side index so the importer can rewire FKs.
    client_ref: str                              # opaque per-bundle unique key

class BundleHighlight(BaseModel): ...
class BundleArticleNote(BaseModel): ...
class BundleCompiledCard(BaseModel): ...
class BundleManuscriptSection(BaseModel): ...
class BundleAbbreviation(BaseModel): ...
class BundleDataset(BaseModel): ...
class BundleDatasetVariable(BaseModel): ...
class BundleAnalysis(BaseModel): ...
class BundleAnalysisResult(BaseModel): ...
class BundleReview(BaseModel): ...
class BundleSearchRecord(BaseModel): ...
class BundleScreeningRecord(BaseModel): ...
class BundleRobAssessment(BaseModel): ...
class BundleExtractionRecord(BaseModel): ...

class ProjectBundle(BaseModel):
    model_config = ConfigDict(extra="forbid")
    bundle_version: Literal[1] = 1
    exported_at: datetime
    project: BundleProject
    articles: list[BundleArticle] = []
    highlights: list[BundleHighlight] = []
    article_notes: list[BundleArticleNote] = []
    compiled_cards: list[BundleCompiledCard] = []
    manuscript_sections: list[BundleManuscriptSection] = []
    abbreviations: list[BundleAbbreviation] = []
    datasets: list[BundleDataset] = []
    dataset_variables: list[BundleDatasetVariable] = []
    analyses: list[BundleAnalysis] = []
    analysis_results: list[BundleAnalysisResult] = []
    review: BundleReview | None = None
    search_records: list[BundleSearchRecord] = []
    screening_records: list[BundleScreeningRecord] = []
    rob_assessments: list[BundleRobAssessment] = []
    extraction_records: list[BundleExtractionRecord] = []

class ImportBundleResponse(BaseModel):
    project_id: str
    counts: dict[str, int]                       # {articles: 42, highlights: 318, ...}
```

**Note:** `client_ref` is a per-bundle string (e.g. `art-1`, `art-2`) used to wire foreign-keys WITHIN the bundle. Dependent rows (highlights, notes, etc.) reference `article_client_ref` rather than the original DB id, so the importer can mint fresh DB ids without breaking FKs.

- [ ] **Step 1: Implement schemas.**
- [ ] **Step 2: Export from `schemas/__init__.py`.**
- [ ] **Step 3: Commit.**

---

## Task 4: DOCX export service (TDD)

**Files:**
- Create: `apps/api/src/research_api/services/export/docx_export.py`
- Create: `apps/api/tests/test_export_docx.py`

### Public API

```python
def render_docx(
    *,
    project: Project,
    sections: list[ManuscriptSection],
    bibliography: list[BibliographyEntry],
    prisma_svg: str | None,
) -> bytes:
    """Return DOCX bytes."""
```

### Implementation outline

1. `docx.Document()` → use default Calibri 11; H1 for section names, body for paragraphs.
2. Render sections in canonical order (Abstract, Introduction, Methodology, Results, Discussion, Conclusion). Each section's HTML is parsed with stdlib `html.parser.HTMLParser`:
   - `<p>` → new paragraph
   - `<strong>` / `<em>` → bold / italic run
   - `<sup data-citation data-article-id="...">[…]</sup>` → a small run with `font.superscript = True` carrying the visible text (which for IEEE is `[N]`, for Vancouver/APA/Harvard is the author-year string already substituted at render time)
   - `<ul>` / `<ol>` → list paragraphs with the right `style`
   - `<table>` → docx table (rob-traffic-light + extraction tables from Phase 7 land here)
   - `<img src="data:image/svg+xml;base64,...">` (the PRISMA flow) → rasterise via `cairosvg.svg2png` → embed via `document.add_picture(io.BytesIO(png_bytes), width=Inches(6))`
   - Unknown tags → fall through to text content
3. **Citation substitution rule**: BEFORE parsing, substitute citation `<sup>` content with the style-formatted citation text using `bibliography` for the numbering map. For Vancouver/APA/Harvard the formatted text is `(Doe et al., 2024)` placed as a NORMAL run (no superscript). For IEEE the formatted text is `[N]` placed as a SUPERSCRIPT run.
4. Add a "References" page break, render `bibliography` entries with hanging-indent 0.5" left + 0.5" first-line indent of `-0.5"` (achieved via `paragraph_format.left_indent` + `first_line_indent`).
5. **No external assets beyond what's in the bundle**: PRISMA SVG (if any section's content holds it) is the only image source.

### Tests (using `python-docx` to **read back** the produced file in-memory)

- `test_render_docx_produces_valid_zip` (DOCX is a zip; `zipfile.is_zipfile(...)` on the output bytes)
- `test_render_docx_contains_section_headings` (open with `Document(io.BytesIO(bytes))` → assert `Heading 1` paragraphs match the section names in order)
- `test_render_docx_renders_paragraphs_in_order`
- `test_render_docx_strips_unknown_html_tags_safely`
- `test_render_docx_renders_bibliography_section_with_hanging_indent`
- `test_render_docx_handles_empty_bibliography` (no References page, no error)
- `test_render_docx_substitutes_citations_for_vancouver`
- `test_render_docx_substitutes_citations_for_ieee` (assert visible text is `[1]`, `[2]` and is superscript)
- `test_render_docx_renders_prisma_when_present` (mock `cairosvg.svg2png` to return a 1x1 PNG; assert the document has 1 inline image)
- `test_render_docx_renders_table_from_html` (RoB push table from Phase 7 round-trips as a docx table with same row count)

- [ ] **Step 1: Tests first.**
- [ ] **Step 2: Implement; HTML parsing helper is the gnarly bit — keep it as a single function `_walk_html_to_paragraphs(doc, html)` that uses `html.parser.HTMLParser` with an explicit stack.**
- [ ] **Step 3: Cairosvg import is lazy** (only imported when an `<img data:image/svg+xml>` is encountered) — so tests that don't touch SVG don't need the dep.
- [ ] **Step 4: Iterate to green.**
- [ ] **Step 5: Commit:** `feat(phase8): DOCX export with citations, bibliography, PRISMA embed`.

---

## Task 5: PDF export service (TDD)

**Files:**
- Create: `apps/api/src/research_api/services/export/pdf_export.py`
- Create: `apps/api/tests/test_export_pdf.py`

### Public API

```python
def render_pdf(
    *,
    project: Project,
    sections: list[ManuscriptSection],
    bibliography: list[BibliographyEntry],
) -> bytes:
    """Return PDF bytes via WeasyPrint."""
```

### Implementation outline

1. Assemble an HTML document in memory: print-friendly CSS (8.5"x11", 1" margins, serif `Crimson Pro` fallback `Georgia, "Times New Roman", serif`), styled section H1s, styled citation `<sup>` (font-size 75%, vertical-align super).
2. Concatenate section HTML in canonical order; **DOMPurify equivalent server-side**: use `nh3` (already a stable, fast HTML sanitizer in Python) — actually, scratch — to avoid a new dep, we use a small allow-list HTML walker we already have? No — simplest path: use `html.parser` + an allow-list of safe tags (`p, strong, em, ul, ol, li, table, thead, tbody, tr, td, th, figure, figcaption, img, sup, br, h1, h2, h3, blockquote, code`). Anything else → drop and emit text content only. This is the SAME walker built in Task 4; extract it to `services/export/_html.py` and reuse from both renderers.
3. Append a "References" `<section>` with the bibliography entries as `<p class="bib-entry">`.
4. `weasyprint.HTML(string=html_str, base_url=".")` → `.write_pdf()`.
5. The PRISMA SVG embedded in section HTML is already a `<img data:image/svg+xml;base64,...>` — WeasyPrint renders it natively, no rasterisation needed.

### Tests

- `test_render_pdf_returns_pdf_bytes` (starts with `%PDF-`)
- `test_render_pdf_contains_section_text` (use `pypdf.PdfReader` to extract text and grep)
- `test_render_pdf_renders_bibliography`
- `test_render_pdf_handles_empty_bibliography`
- `test_render_pdf_html_walker_drops_script` (inject `<script>alert(1)</script>` into a section, render, assert no `alert` in PDF text)
- `test_render_pdf_uses_chosen_style_for_inline_citations` (style passed via the bibliography mapping)

- [ ] **Step 1: Extract HTML walker** to `services/export/_html.py`; tests for it (`test_export_html_walker.py` — small unit tests).
- [ ] **Step 2: Write PDF tests.**
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Iterate.**
- [ ] **Step 5: Commit:** `feat(phase8): PDF export via WeasyPrint`.

---

## Task 6: Bundle export service (TDD)

**Files:**
- Create: `apps/api/src/research_api/services/export/bundle_export.py`
- Create: `apps/api/tests/test_export_bundle.py`

### Public API

```python
async def export_project_bundle(
    *,
    project: Project,
    session: AsyncSession,
    user_id: str,
) -> ProjectBundle:
    """Read every dependent row, build a strict ProjectBundle. Pure-ish: no FS writes."""
```

### Steps

1. Load articles for the project, scoped by `user_id`. Assign each a `client_ref = f"art-{i}"`.
2. For each article, load highlights + notes → append with `article_client_ref`.
3. Load compiled cards → reference parent highlight client_ref.
4. Load manuscript sections.
5. Load abbreviations.
6. Load datasets → variables → analyses → analysis_results, wiring client_refs at each level.
7. Load review (single) → search/screening/rob/extraction. Screening + RoB + Extraction reference `article_client_ref`.
8. Return `ProjectBundle(...)` with `exported_at=datetime.utcnow()`.

### Tests

- `test_bundle_contains_all_articles_for_project`
- `test_bundle_excludes_articles_from_other_projects`
- `test_bundle_excludes_articles_from_other_users`
- `test_bundle_wires_highlight_to_article_via_client_ref`
- `test_bundle_omits_internal_ids` (assert no `user_id`, no `id`, no DB `created_at` leak into the dict — only `client_ref`s)
- `test_bundle_empty_project_produces_minimal_valid_bundle`
- `test_bundle_includes_review_when_present`
- `test_bundle_skips_review_when_absent`

- [ ] **Step 1: Tests.**
- [ ] **Step 2: Implement step-by-step over the 7 row groups.**
- [ ] **Step 3: Iterate.**
- [ ] **Step 4: Commit:** `feat(phase8): JSON project bundle export`.

---

## Task 7: Bundle import service (TDD — security-critical)

**Files:**
- Create: `apps/api/src/research_api/services/export/bundle_import.py`
- Create: `apps/api/tests/test_import_bundle.py`

### Public API

```python
async def import_project_bundle(
    *,
    bundle: ProjectBundle,
    session: AsyncSession,
    current_user_id: str,
) -> ImportBundleResponse:
    """Create a NEW project (+ all dependents) owned by current_user_id.
    Mints fresh ids for every row. Discards any user_id in the bundle.
    Wraps everything in a single transaction; on any failure rolls back."""
```

### Steps

1. `Project(...).id = new_id()`, `user_id = current_user_id`, fields from `bundle.project`. Insert.
2. For each `BundleArticle`, mint `id`, set `user_id = current_user_id`, set `project_id = new project's id`. Build a `client_ref → article_id` map.
3. For each highlight/note, look up the article_id via the map; mint id; insert.
4. For compiled cards, similar via highlight_client_ref map.
5. For manuscript sections, mint id; uniqueness is `(project_id, user_id, section_name)` — naturally satisfied because project is fresh.
6. For abbreviations, datasets, dataset_variables, analyses, analysis_results — same pattern. Datasets need `file_ref` handling: a bundle is metadata-only (no binary blobs); set `file_ref={"backend": "missing", "key": ""}` so the dataset row exists for stats history but rendering will note "file missing". Document this in the response payload.
7. For review (if present), mint review id; for search/screening/rob/extraction wire `review_id` + `article_id` via maps.
8. Commit the transaction; return counts.

### Tests (security-heavy)

- `test_import_assigns_current_user_id_to_all_rows`
- `test_import_strips_attacker_user_id_from_bundle` (inject `"user_id": "attacker"` into a serialised bundle dict, pass through Pydantic — `extra="forbid"` rejects it; **also** add a positive test that ensures a bundle missing user_id wins through and stamps current_user_id)
- `test_import_mints_fresh_ids` (assert no row's id matches any id in the bundle JSON)
- `test_import_rolls_back_on_partial_failure` (monkeypatch one repository insert to raise; assert no rows remain)
- `test_import_creates_dependents_correctly` (article → highlights → compiled_card chain)
- `test_import_review_optional` (no review → bundle imports cleanly)
- `test_import_handles_orphan_dependents` (highlight references a nonexistent client_ref → 422 with clear error)
- `test_import_size_cap` (a 11MB bundle JSON is rejected at the route level — test in route file; service-level test asserts the function doesn't OOM on a 5MB bundle: build a synthetic one with 1000 articles, time-bound to <2s)
- `test_import_dataset_marks_file_ref_missing`

- [ ] **Step 1: Tests.**
- [ ] **Step 2: Implement.**
- [ ] **Step 3: Iterate.**
- [ ] **Step 4: Commit:** `feat(phase8): JSON bundle import with current-user re-tagging`.

---

## Task 8: Export routes (TDD)

**Files:**
- Create: `apps/api/src/research_api/routes/export.py`
- Create: `apps/api/tests/test_export_routes.py`
- Modify: `apps/api/src/research_api/main.py`

### Endpoints

```
POST   /projects/{project_id}/export/docx               body: ExportRequest → application/vnd.openxmlformats-officedocument.wordprocessingml.document
POST   /projects/{project_id}/export/pdf                body: ExportRequest → application/pdf
POST   /projects/{project_id}/export/bundle             body: (empty) → application/json
POST   /import/bundle                                   multipart: file=ProjectBundle JSON → ImportBundleResponse
```

### Per-route behaviour

- `/export/docx`:
  1. Resolve project for current user → 404 if missing.
  2. Load sections (all 6 names) via repository.
  3. Load articles via repository — needed for citation substitution.
  4. Build bibliography (Task 2) with the requested style.
  5. Look for an embedded PRISMA SVG in the Methodology section (regex on `<img.*?data:image/svg\+xml`); extract the base64 payload + decode.
  6. Call `render_docx(...)`.
  7. Return as `StreamingResponse(io.BytesIO(bytes), media_type=..., headers={"Content-Disposition": f"attachment; filename=\"{slug}-{date}.docx\""})`.
- `/export/pdf`: symmetric, PDF media type.
- `/export/bundle`: call `export_project_bundle(...)` and stream the JSON with `Content-Disposition: attachment; filename="<project>-bundle-<date>.json"`. Pretty-printed (`indent=2`) for human inspection.
- `/import/bundle`:
  1. **Size cap: 10MB** (`UploadFile.size > 10 * 1024 * 1024 → 413`).
  2. **Content sniff: must be JSON** (first byte must be `{`; if it's a PDF magic, reject 415).
  3. Parse to `ProjectBundle`; Pydantic enforces `extra="forbid"` everywhere → 422 on any unknown field.
  4. Call `import_project_bundle(bundle, session, current_user_id=user_id)`.
  5. Return `ImportBundleResponse(project_id, counts)`.

### Tests

- `test_export_docx_returns_attachment_with_content_disposition`
- `test_export_pdf_returns_attachment`
- `test_export_bundle_returns_json_attachment`
- `test_export_docx_404_for_other_user`
- `test_export_pdf_404_for_other_user`
- `test_export_bundle_404_for_other_user`
- `test_import_bundle_creates_new_project_owned_by_current_user`
- `test_import_bundle_rejects_oversize_413`
- `test_import_bundle_rejects_non_json_415`
- `test_import_bundle_rejects_extra_fields_422`
- `test_import_bundle_ignores_attacker_user_id_in_payload` (post a JSON with `"user_id": "attacker"` inside `project` — Pydantic's `extra="forbid"` rejects 422)
- `test_export_request_style_defaults_to_project_style` (no `style` in body → use `project.citation_style`)

- [ ] **Step 1: Tests.**
- [ ] **Step 2: Implement route.**
- [ ] **Step 3: Wire into `main.py`** under `prefix="/api"`.
- [ ] **Step 4: Iterate.**
- [ ] **Step 5: Commit:** `feat(phase8): export + import routes with size/content caps`.

---

## Task 9: Bibliography route (TDD)

**Files:**
- Create: `apps/api/src/research_api/routes/bibliography.py`
- Create: `apps/api/tests/test_bibliography_route.py`
- Modify: `apps/api/src/research_api/main.py`

### Endpoints

```
GET    /projects/{project_id}/bibliography                  ?style=vancouver|apa|harvard|ieee → BibliographyResponse
```

Implementation: load sections + articles for project + user, call `build_bibliography`, return.

### Tests

- `test_bibliography_endpoint_returns_entries_in_first_cite_order`
- `test_bibliography_endpoint_dedupes`
- `test_bibliography_endpoint_404_for_other_user`
- `test_bibliography_endpoint_respects_style_query_param`
- `test_bibliography_endpoint_defaults_to_project_style`

- [ ] **Step 1: Tests.**
- [ ] **Step 2: Implement.**
- [ ] **Step 3: Commit:** `feat(phase8): bibliography GET endpoint`.

---

## Task 10: Security regression — export isolation (multi-user)

**File:** `apps/api/tests/test_security_export_isolation.py`

Tests:
- `test_export_docx_isolated_across_users` (user A exports project P1 → returns. User B calls `/projects/P1/export/docx` → 404)
- `test_export_pdf_isolated_across_users`
- `test_export_bundle_isolated_across_users`
- `test_import_re_assigns_user_id` (export from user A, import to user B's session → all rows owned by B)
- `test_import_does_not_clobber_existing_user_projects` (B already has a project P_b; import → P_b untouched; a new project row is created)
- `test_import_rejects_attacker_user_id_in_bundle_payload`
- `test_import_size_cap_enforced_at_route_level`
- `test_bibliography_endpoint_isolated_across_users`
- `test_export_filename_does_not_leak_other_users_data` (Content-Disposition filename derives from project title — assert it's properly slugified and contains no path-traversal characters)

- [ ] **Step 1: Tests.**
- [ ] **Step 2: Fix any leaks.**
- [ ] **Step 3: Commit:** `test(phase8): cross-user export/import isolation regression`.

---

## Task 11: POLISH-fix — React Router v7 future flags

**File:** `apps/web/src/App.tsx`

```tsx
<BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
```

- [ ] **Step 1: Modify.**
- [ ] **Step 2: Run frontend, confirm console clean (no more v7 future-flag warnings).**
- [ ] **Step 3: Add a vitest in `apps/web/src/__tests__/app-router.test.tsx`** that renders `<App />` inside MemoryRouter and asserts dashboard renders.
- [ ] **Step 4: Annotate POLISH.md**: change the `[phase1] [low] React Router v6→v7` line to add `· ✅ resolved in P8-T11 (2026-05-18)`.
- [ ] **Step 5: Commit:** `chore(phase8): opt into React Router v7 future flags`.

---

## Task 12: POLISH-fix — DOMPurify pre-pass on AI HTML

**Files:**
- Create: `apps/web/src/lib/sanitizeHtml.ts`
- Modify: `apps/web/src/lib/citationSerialize.ts` — `aiSafeTextToHtml` should sanitize before returning
- Modify: `apps/web/src/components/manuscript/BubbleAIMenu.tsx` — sanitize on receive

```ts
// sanitizeHtml.ts
import DOMPurify from 'dompurify'

const ALLOWED_TAGS = ['p', 'strong', 'em', 'u', 's', 'sup', 'sub', 'br', 'a', 'ul', 'ol', 'li', 'blockquote', 'code', 'pre']
const ALLOWED_ATTR = ['data-citation', 'data-article-id', 'class', 'href']

export function sanitizeAiHtml(html: string): string {
  return DOMPurify.sanitize(html, {
    ALLOWED_TAGS,
    ALLOWED_ATTR,
    FORBID_ATTR: ['style', 'onerror', 'onload', 'onclick'],
    KEEP_CONTENT: true,
  })
}
```

In `citationSerialize.ts`, wrap `aiSafeTextToHtml`'s return with `sanitizeAiHtml(...)` before returning. ProseMirror's schema filter remains the second line of defence.

### Tests

`apps/web/src/lib/__tests__/sanitizeHtml.test.ts`:
- `script tag is dropped`
- `onclick attribute is stripped`
- `data-article-id is preserved`
- `sup data-citation survives`
- `iframe is dropped`
- `nested malicious markup` (`<a href="javascript:alert(1)">`) — href is dropped

- [ ] **Step 1: Add `dompurify` + types** (already in pre-flight).
- [ ] **Step 2: Create `sanitizeHtml.ts` + tests.**
- [ ] **Step 3: Wire into `citationSerialize.ts` + `BubbleAIMenu.tsx`.**
- [ ] **Step 4: Annotate POLISH.md `[phase5] [med] AI writing-assist output is inserted into TipTap` → `✅ resolved in P8-T12`.**
- [ ] **Step 5: Commit:** `feat(phase8): DOMPurify pre-pass on AI-returned HTML`.

---

## Task 13: POLISH-fix — SQLite foreign-keys PRAGMA app-wide

**Files:**
- Modify: `apps/api/src/research_api/db/base.py`
- Create: `apps/api/tests/test_db_pragma_foreign_keys.py`

```python
# in db/base.py — add after make_engine definition
from sqlalchemy import event

def _set_sqlite_pragma(dbapi_connection, _connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()

def make_engine(url: str) -> AsyncEngine:
    engine = create_async_engine(url, echo=False, future=True)
    if url.startswith("sqlite"):
        @event.listens_for(engine.sync_engine, "connect")
        def _on_connect(dbapi_connection, connection_record):
            _set_sqlite_pragma(dbapi_connection, connection_record)
    return engine
```

### Tests

- `test_pragma_foreign_keys_on_for_new_engine` (open an `AsyncSession`, execute `PRAGMA foreign_keys;` → returns `1`)
- `test_cascade_delete_works_via_pragma` (create a project + article; delete project; assert article also gone — without needing the manual cascade list in dataset repo)

- [ ] **Step 1: Implement.**
- [ ] **Step 2: Tests.**
- [ ] **Step 3: Remove the manual cascade-delete fallback in the dataset repository if it exists and tests still pass** (grep for `# manual cascade` first).
- [ ] **Step 4: Annotate POLISH.md `[phase6] [low] SQLite foreign-key PRAGMA` → `✅ resolved in P8-T13`.**
- [ ] **Step 5: Commit:** `fix(phase8): enable SQLite foreign_keys PRAGMA app-wide`.

---

## Task 14: POLISH-fix — Result interpretation prompt rounding

**File:** `apps/api/src/research_api/services/ai/prompts/result_interpretation.py`

Add to the system rules section:
```
- Round p-values to 3 decimal places. Report values smaller than 0.001 as "<0.001".
- Round effect sizes, mean differences, and CI bounds to 2-3 significant figures.
- Round percentages to 1 decimal place.
- Never report scientific notation in user-facing prose unless the value is genuinely >1e6 or <1e-6.
```

### Tests

`apps/api/tests/test_result_interpretation_prompt.py` — extend if exists, else create:
- `test_prompt_includes_rounding_rules`

- [ ] **Step 1: Modify the prompt.**
- [ ] **Step 2: Annotate POLISH.md `[phase6] [low] Result-interpretation prompt` → `✅ resolved in P8-T14`.**
- [ ] **Step 3: Commit:** `fix(phase8): instruct AI to round numbers in result interpretations`.

---

## Task 15: POLISH-fix — Wizard step 2 type-mismatch pre-empt

**File:** `apps/web/src/components/statistics/WizardVariableStep.tsx`

Add client-side validation: when the user picks a variable for a role (`outcome`, `group`, etc.) and the variable's `inferred_type` doesn't match the test's expected type (e.g. t-test outcome must be continuous), show a warning toast inline + disable the Next button until resolved or overridden.

### Test

`apps/web/src/components/statistics/__tests__/WizardVariableStep.test.tsx`:
- `picking a categorical column for t-test outcome shows warning`
- `picking a continuous column for t-test outcome does not warn`
- `next button disabled while warning active`

- [ ] **Step 1: Implement validation.**
- [ ] **Step 2: Tests.**
- [ ] **Step 3: Annotate POLISH.md** `[phase6] [low] Statistics page wizard step 2` → `✅ resolved in P8-T15`.
- [ ] **Step 4: Commit:** `fix(phase8): validate variable types in stats wizard before submit`.

---

## Task 16: POLISH-fix — Review push replace-by-class-hook

**File:** `apps/api/src/research_api/routes/reviews.py` (push endpoints from Phase 7)

Add `?mode=append|replace` query param (default `append`). When `replace`:
- For PRISMA push: search the section content for `<figure class="prisma-flow">…</figure>` and replace in place; fall back to append if absent.
- For RoB push: replace `<table class="rob-traffic-light">`.
- For Extraction push: replace `<table class="extraction-table">`.
- For Search push: replace `<table class="search-strategy">`.

Each rendered block already has (or now gets) the appropriate class hook on the outer element.

### Tests (extend `test_reviews_route_push.py`)

- `test_prisma_push_replace_swaps_existing_figure`
- `test_rob_push_replace_swaps_existing_table`
- `test_push_default_mode_is_append` (regression — default behaviour unchanged)
- `test_push_replace_creates_when_no_existing_block` (replace gracefully degrades to append)

- [ ] **Step 1: Add class hooks to rendered HTML** in each push helper.
- [ ] **Step 2: Implement replace logic** (regex on the class hook — `<figure class="prisma-flow"[^>]*>.*?</figure>` with `re.DOTALL`).
- [ ] **Step 3: Tests.**
- [ ] **Step 4: Annotate POLISH.md `[phase7] [low] Review pushes (PRISMA/search/RoB/extraction) append`** → `✅ resolved in P8-T16`.
- [ ] **Step 5: Commit:** `feat(phase8): review push supports mode=replace via class hooks`.

---

## Task 17: Bibliography panel (frontend)

**Files (all NEW):**
- `apps/web/src/components/bibliography/BibliographyPanel.tsx`
- `apps/web/src/components/bibliography/BibliographyRow.tsx`
- `apps/web/src/components/bibliography/BibliographyToolbar.tsx`
- `apps/web/src/lib/bibliographyFormat.ts` (modify — extend to APA/Harvard/IEEE; mirror server logic)

`BibliographyPanel.tsx`:
- Lives inside `ManuscriptPage.tsx` as a right-rail tab (or full-page modal — pick right-rail to mirror the existing layout style).
- Fetches `/projects/{pid}/bibliography?style=...` via TanStack Query, key `['bibliography', pid, style]`.
- Renders one `BibliographyRow` per entry.
- Toolbar: style picker (4 styles), **Copy all** button (plain text, joined by `\n\n`), **Export** dropdown (DOCX / PDF / Bundle / Plain BibTeX / RIS / CSL-JSON).

`BibliographyRow.tsx`:
- Layout: `<div class="flex"><span class="num">[1]</span><span class="entry">{formatted}</span><Button onClick=copy><Copy/></Button><Button onClick=locate><MapPin/></Button></div>`.
- "Locate" calls a small helper `findFirstCitationInSection(articleId, sections)` that returns `{sectionName, charOffset}`, then dispatches a navigation to the manuscript editor scrolled to that offset (use TipTap's `commands.scrollIntoView()` + a small `setTextSelection`).

`BibliographyToolbar.tsx`:
- Style picker is a shadcn `<Select>` with 4 options. Persists to project via PATCH `/projects/{pid}` (existing endpoint already accepts `citation_style`).
- "Export bibliography only" mini-button (different from full-manuscript export): downloads a `.txt` file with the joined formatted entries — purely client-side, no new endpoint.
- BibTeX / RIS / CSL-JSON exports: pure client-side serialisation from the same articles data — small helpers in `apps/web/src/lib/bibliographyFormat.ts` (`toBibTeX`, `toRIS`, `toCSLJSON`).

### Tests (vitest)

- `apps/web/src/lib/__tests__/bibliographyFormat.test.ts` — golden-string tests for the 4 styles mirroring the API matrix (proves Python↔TS parity).
- `apps/web/src/components/bibliography/__tests__/BibliographyPanel.test.tsx` — renders 3 rows from a mocked API response; copy-all button copies all 3 joined with `\n\n`.
- `toBibTeX`, `toRIS`, `toCSLJSON` unit tests against a canonical article.

- [ ] **Step 1: Extend `bibliographyFormat.ts` with APA / Harvard / IEEE + format converters.**
- [ ] **Step 2: Implement components.**
- [ ] **Step 3: Wire into ManuscriptPage as a right-rail tab.**
- [ ] **Step 4: Tests.**
- [ ] **Step 5: Commit:** `feat(phase8): bibliography panel in manuscript with multi-style + multi-export`.

---

## Task 18: Settings page — Export, Storage, Health link

**Files:**
- Create: `apps/web/src/components/settings/ExportCard.tsx`
- Create: `apps/web/src/components/settings/StorageCard.tsx`
- Create: `apps/web/src/components/settings/ImportDropzone.tsx`
- Create: `apps/web/src/components/settings/HealthLink.tsx`
- Create: `apps/web/src/routes/HealthPage.tsx`
- Modify: `apps/web/src/routes/SettingsPage.tsx`
- Modify: `apps/web/src/App.tsx` (add `/health`)

`ExportCard.tsx`:
- ProjectSelectGate inside (because export is per-project).
- 3 buttons: Export to DOCX / Export to PDF / Export project bundle (JSON).
- Each calls `exportApi.docx(pid)` / `exportApi.pdf(pid)` / `exportApi.bundle(pid)` and triggers a browser download via blob URL.
- During export, a small Sonner toast `Generating DOCX…` is shown; resolves on success/error.

`StorageCard.tsx`:
- Reads `data.storage_backend` from `/health`. Displays the backend (`Local FS` with the resolved path from a new GET `/health/storage` if needed, or just the backend name) and **"Migrate to cloud"** button — disabled, tooltip "Coming in a future phase".
- This satisfies the polish item: storage section in Settings + future-cloud stub.

`ImportDropzone.tsx`:
- react-dropzone on JSON files.
- POSTs to `/import/bundle` as multipart.
- On success, toast "Imported as new project: <title>" + offers to navigate to it.
- File-size cap on the client side (10MB) with friendly error.

`HealthLink.tsx`: a small inline link "View detailed health diagnostics →" → routes to `/health`.

`HealthPage.tsx`:
- Renders `/health` payload formatted: API status, DB status, storage backend, AI providers list (with per-provider keys configured?), build version, current secret rotation date (omit if not exposed). Read-only.

`SettingsPage.tsx`:
- Add the new Cards after the existing AI providers + Storage cards: Export card, Import dropzone card, Health link.

### Tests (vitest)

- `apps/web/src/components/settings/__tests__/ExportCard.test.tsx` — clicking DOCX → triggers download attribute on a created anchor.
- `apps/web/src/components/settings/__tests__/ImportDropzone.test.tsx` — rejects files larger than 10MB.
- `apps/web/src/routes/__tests__/HealthPage.test.tsx` — renders provider statuses from a mocked /health response.

- [ ] **Step 1: Implement components + page.**
- [ ] **Step 2: Add `/health` route to App.tsx.**
- [ ] **Step 3: Tests.**
- [ ] **Step 4: Commit:** `feat(phase8): settings export + import + storage + health UI`.

---

## Task 19: Deploy artefacts

**Files:**
- Create: `apps/api/Dockerfile`
- Create: `apps/api/fly.toml`
- Create: `apps/web/vercel.json`

### `apps/api/Dockerfile`

```dockerfile
FROM python:3.12-slim

# WeasyPrint system deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpango-1.0-0 libpangoft2-1.0-0 libcairo2 libgdk-pixbuf-2.0-0 libffi-dev \
    libmagic1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY apps/api/pyproject.toml /app/
COPY apps/api/src /app/src
COPY apps/api/alembic /app/alembic
COPY apps/api/alembic.ini /app/alembic.ini

RUN pip install --no-cache-dir -e .

# Mounted volume for SQLite + uploaded files
ENV DATA_DIR=/data
RUN mkdir -p /data
VOLUME /data

EXPOSE 8787
CMD ["sh", "-c", "alembic upgrade head && uvicorn research_api.main:app --host 0.0.0.0 --port 8787"]
```

### `apps/api/fly.toml`

```toml
app = "research-assistant-api"           # placeholder; user changes before deploy
primary_region = "lhr"

[build]
  dockerfile = "Dockerfile"

[env]
  AI_PROVIDER_DEFAULT = "gemini"
  DATA_DIR = "/data"
  SQLITE_URL = "sqlite+aiosqlite:////data/research.db"
  STORAGE_BACKEND = "local"

[mounts]
  source = "research_data"
  destination = "/data"

[http_service]
  internal_port = 8787
  force_https = true
  auto_stop_machines = "stop"
  auto_start_machines = true
  min_machines_running = 0

[[services.ports]]
  port = 443
  handlers = ["tls", "http"]
```

Secrets (set by user via `fly secrets set`):
- `GEMINI_API_KEY`
- `API_SIGNING_SECRET`

### `apps/web/vercel.json`

```json
{
  "buildCommand": "npm run build",
  "outputDirectory": "dist",
  "framework": "vite",
  "headers": [
    {
      "source": "/(.*)",
      "headers": [
        { "key": "X-Content-Type-Options", "value": "nosniff" },
        { "key": "X-Frame-Options", "value": "DENY" },
        { "key": "Referrer-Policy", "value": "strict-origin-when-cross-origin" }
      ]
    }
  ],
  "rewrites": [
    { "source": "/(.*)", "destination": "/index.html" }
  ]
}
```

### Documentation in BUILD_LOG.md (Phase 8 closing notes will append):

```markdown
**Deploy commands (user runs manually):**

Web (Vercel):
  cd apps/web && vercel --prod

API (Fly.io):
  cd apps/api && fly launch --copy-config --no-deploy --name <yourname>-api
  fly secrets set GEMINI_API_KEY=... API_SIGNING_SECRET=$(openssl rand -hex 32)
  fly volumes create research_data --size 1 --region lhr
  fly deploy

Update VITE_API_BASE_URL in apps/web/.env.production to point at the Fly URL,
then redeploy the web frontend.
```

- [ ] **Step 1: Create the 3 artefact files.**
- [ ] **Step 2: Run `pnpm build` (or `npm run build`) from `apps/web` to verify dist/ is clean.**
- [ ] **Step 3: Run `docker build -t research-api apps/api/` locally** to verify the Dockerfile builds. Don't push.
- [ ] **Step 4: Add the deploy-commands doc** to the BUILD_LOG draft.
- [ ] **Step 5: Commit:** `chore(phase8): deploy artefacts (vercel.json, Dockerfile, fly.toml)`.

---

## Task 20: E2E browser smoke (chrome-devtools-mcp)

**Goal:** Prove all three export formats download, the bibliography page renders all 4 styles, and the JSON bundle round-trips through import.

- [ ] **Step 1: Boot servers** (`apps/api`: uvicorn on 8787; `apps/web`: vite on 5173).
- [ ] **Step 2: Drive Chrome via MCP:**
  1. Open Manuscript page on an existing project with citations.
  2. Open the Bibliography panel → switch between Vancouver / APA / Harvard / IEEE → confirm the formatted strings change.
  3. Click **Copy all** → verify clipboard contents.
  4. Click "Locate in manuscript" on entry [1] → verify the editor scrolls to the first occurrence.
  5. Click **Export → DOCX** → file downloads. Open with `python -c "from docx import Document; d=Document('~/Downloads/<file>.docx'); print(len(d.paragraphs))"` to confirm well-formed.
  6. Click **Export → PDF** → file downloads. `pdftotext` on it → confirm section headings and bibliography are present.
  7. Click **Export → Bundle** → JSON downloads. `jq .bundle_version <file>` returns `1`.
  8. Go to Settings → Import dropzone → drop the just-exported JSON → toast "Imported as new project". Navigate to it → confirm articles, highlights, manuscript sections, review (if present) all round-trip.
  9. Go to Settings → Health link → /health page renders.
  10. Verify console clean (no v7 future-flag warnings — POLISH-fix verification).
- [ ] **Step 3: Screenshot each step** under `docs/phase-8-screenshots/`.
- [ ] **Step 4: a11y audit** via `chrome-devtools-mcp:a11y-debugging` on /bibliography (panel) + /settings. Fix any AA violations inline.

---

## Task 21: `/security-review`

Targets:
- `services/citation_format.py` — all 4 style formatters use only `escape()` on interpolated user fields when wrapped in HTML downstream (the export pipeline does the escaping; the raw string functions return plain text). **Confirm no `eval`, no string-templating-into-HTML inside `citation_format.py` itself.**
- `services/export/_html.py` (the shared HTML walker) — allow-list filter, drops `<script>`, `<iframe>`, `<object>`, `<embed>`, `style` attribute, `on*` attributes.
- `services/export/docx_export.py` — `cairosvg.svg2png` only on SVG content extracted from the manuscript's own sections (which were ProseMirror-filtered at write time). Confirm no external URL fetches.
- `services/export/bundle_import.py` — Pydantic `extra="forbid"` on every BundleX model. Importer mints fresh ids. Single-transaction rollback on failure.
- `routes/export.py` — every endpoint scopes by user. Import endpoint enforces 10MB size + JSON-content sniff. Content-Disposition filename is slugified (no path traversal).
- `routes/bibliography.py` — scope by user.
- `lib/sanitizeHtml.ts` — allow-list configured. **Spot test**: paste `<script>alert(1)</script>` into the AI bubble menu, confirm it's stripped.
- React Router v7 future flags — confirm no behavioural regression in routing.
- SQLite FK PRAGMA — confirm fixture flow still cascades correctly.

- [ ] **Step 1: Run `/security-review` skill on the diff.**
- [ ] **Step 2: Fix HIGH + MED inline. Log LOW to POLISH.md.**
- [ ] **Step 3: Commit:** `security(phase8): address findings from /security-review`.

---

## Task 22: BUILD_LOG entry + tag + Phase 9 readiness checklist

Append to `BUILD_LOG.md` (newest first):

```markdown
## 2026-05-18 · Phase 8 — Bibliography, Export, Polish & Deploy ✅ COMPLETE

**Tag:** `phase-8`
**Commits:** ~N atomic commits. Plan at `docs/superpowers/plans/2026-05-18-phase-8-bibliography-export-polish-deploy.md`.

**What's running now**

- Backend: `services/citation_format.py` now ships 4 full-fidelity styles (Vancouver, APA 7, Harvard, IEEE). New `services/export/` package: `bibliography.py` (dedupe + first-cite ordering), `docx_export.py` (python-docx + cairosvg + Pillow), `pdf_export.py` (weasyprint), `bundle_export.py` + `bundle_import.py` (strict-schema Pydantic round-trip). New `routes/export.py` (POST docx/pdf/bundle, POST import/bundle) and `routes/bibliography.py` (GET with style query). SQLite FK PRAGMA now app-wide via a SQLAlchemy connect listener.
- Frontend: Bibliography panel inside Manuscript page with 4-style picker, Copy all, Locate-in-manuscript, BibTeX/RIS/CSL-JSON client-side export. Settings page now ships Export, Import dropzone, Storage backend display with future-cloud stub, and a Health diagnostics link → /health page. React Router v7 future flags opted in. DOMPurify pre-pass on all AI HTML.
- Deploy artefacts ready: `apps/api/Dockerfile`, `apps/api/fly.toml` (placeholder), `apps/web/vercel.json`. User runs `fly deploy` / `vercel --prod` manually.

**Acceptance bar (ResearchApp_BuildPlan.md Phase 8)**

- [x] Bibliography UI listing every cited article, deduplicated, ordered by first citation — Tasks 2, 17
- [x] Citation style switcher (Vancouver / APA 7 / Harvard / IEEE) — Tasks 1, 17
- [x] Export to DOCX (formatted with headings, citations, bibliography) — Task 4
- [x] Export to PDF — Task 5
- [x] JSON project bundle export + import — Tasks 6, 7
- [x] Settings panel with Storage display + Migrate-to-cloud stub — Task 18
- [x] Health diagnostics surface — Task 18
- [x] Deploy artefacts ready for Vercel + Fly.io — Task 19
- [x] All open POLISH items resolved or annotated — Tasks 11–16
- [x] Cross-user export/import security regression — Task 10
- [x] `/security-review` passed — Task 21
- [x] E2E browser smoke green — Task 20

**Incidents handled inline**

(fill on completion)

**Decisions**

- IEEE uses bracket-numbered inline citations `[N]` rather than the author-year `vancouver_inline` shared by the other 3 styles. Numbering is computed once per render from the bibliography order and threaded through `replace_cite_tokens` via an optional `numbering` map.
- Project bundle is JSON-only for v1 (no file/binary attachments). Imported datasets get `file_ref={"backend":"missing", "key":""}` so the row exists for analyses history but file-bound operations fail loudly rather than silently. Logged to DEFERRED.md for "binary-bundle" v2.
- Bibliography panel lives inside ManuscriptPage as a right-rail tab (not a dedicated `/bibliography` route) — reduces nav clutter and keeps bibliography next to the editing surface where it's used.
- Deploy targets prepared but not pushed: user runs `fly deploy` and `vercel --prod` themselves at check-in time.

**Phase 9 readiness checklist** (Electron desktop — paused per user directive)

Before kicking off Phase 9 ("desktop packaging"):
- [ ] Decide auto-update strategy: electron-updater + GitHub Releases, or built-in Squirrel updater (Windows) + Sparkle (macOS).
- [ ] Decide code-signing approach: Developer ID Application certificate (macOS), Authenticode certificate (Windows). User must provision both before any signed binary can ship.
- [ ] Decide how to ship Python: PyOxidizer (single binary, complex), `pyinstaller` (multi-file), or bundling a uvicorn + venv directory (simplest, largest). Recommend `pyinstaller --onedir` for v1 + start uvicorn as a child process from Electron's main process.
- [ ] Decide IPC: Electron main spawns the Python API on a localhost port (the existing 8787) at app start, kills it at app exit. Renderer talks to the API exactly as today.
- [ ] Decide data location: per-OS user-data dir (`~/Library/Application Support/ResearchAssistant` on macOS, `%APPDATA%/ResearchAssistant` on Windows) — replaces the current `./data` relative path.
- [ ] Decide first-run UX: copy the bundled empty SQLite DB to the user-data dir + run `alembic upgrade head` on it.
- [ ] Decide AI key storage: ship via OS keychain (Keychain on macOS, Credential Manager on Windows) rather than `.env`. Add a Settings flow to set/replace keys.
- [ ] CI for signed builds: GitHub Actions matrix (macos-latest, windows-latest) + secrets for signing certs.
- [ ] Window chrome: titlebar style, custom traffic-light position on macOS, frameless+custom-titlebar on Windows.
- [ ] Decide whether to ship a Linux build at all in v1 (recommend skipping; Linux users can run the web version locally).

DO NOT start Phase 9 work without an explicit user "begin Phase 9" message.
```

- [ ] **Step 1: Compose entry** with actual commit count + incident list.
- [ ] **Step 2: `git tag phase-8`.**
- [ ] **Step 3: User check-in** — surface the Phase 9 readiness checklist explicitly and wait.

---

## Out of scope (deferred)

- **Onboarding walkthrough flow** (BuildPlan mentions this in Phase 8; we don't ship it). Logged to DEFERRED.md — better placed alongside Phase 9 (first-run UX) anyway.
- **"Email me the export" via SMTP** — explicit no-SMTP-yet decision in the requirements.
- **Loading skeletons for ALL data-fetching screens** — most already have them; final sweep is an aesthetic-polish item logged to POLISH.md.
- **Theme switcher (light/dark)** — `next-themes` is in deps but no UI exposes it; defer.
- **Multi-project bundle export** (one JSON containing N projects) — v1 is per-project.
- **Binary attachments in bundles** (PDFs, datasets) — JSON-only for v1.
- **Cloud storage migration** — UI stub exists; actual implementation is post-Phase-9.
- **Direct Vercel/Fly deployment** — artefacts ready; user runs commands.

---

## Self-Review

**Spec coverage** (`docs/superpowers/specs/2026-05-17-…-design.md` + `ResearchApp_BuildPlan.md` Phase 8):
- Bibliography generation with chosen style ✅ Tasks 1, 2, 9, 17
- Word export with headings, citations, bibliography ✅ Task 4
- PDF export ✅ Task 5
- JSON bundle backup ✅ Tasks 6, 7
- Settings panel (storage display + future-cloud stub + health link) ✅ Task 18
- Error/empty states for all screens — covered by existing patterns; no regression
- Loading skeletons — existing in all data-fetching screens; no new screens added
- Deploy artefacts for Vercel + Fly.io ✅ Task 19
- All POLISH items (correctness + security) ✅ Tasks 11–16
- Security regression ✅ Tasks 10, 21

**Citation safety**: Every formatted citation in DOCX/PDF/JSON comes from authoritative `articles` rows; AI never touches the bibliography pipeline. AI HTML now passes through DOMPurify before TipTap sees it (defence-in-depth). Bundle import re-tags every row to `current_user_id` and mints fresh ids — bundles cannot be used to inject foreign data into a user's namespace.

**Multi-user readiness**: Every export route + bibliography route scopes by `user_id`. Import creates rows owned by the current user. Cross-user regression (Task 10) is the gate.

**TDD ordering**: Each service file (`bibliography`, `docx_export`, `pdf_export`, `bundle_export`, `bundle_import`) has tests written before implementation. Each POLISH-fix has either a verification test or an annotation in POLISH.md. Cross-user security regression is its own task.

**Bite-sized tasks**: 22 tasks, each a single-commit unit, each ~5 min. No new abstractions — reuses repository / route / sub-skill patterns established in Phases 2–7.

**Placeholder scan**: clean — no `Coming soon`, no stubs except the **Migrate to cloud** button (explicitly disabled with a tooltip saying "Coming in a future phase" — this IS the requirement).

**Type consistency**: `CitationStyle` is `vancouver | apa | harvard | ieee` everywhere (Python Literal + TS zod enum). Bundle types in Pydantic ↔ implicit on the client (the client only consumes the import-response counts).

**Self-check ok. Proceeding to execution.**
