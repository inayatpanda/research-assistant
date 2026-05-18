# Phase 8.6 — Ingestion (PubMed / Crossref / RIS / BibTeX / dedup) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` or `superpowers:executing-plans`. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Researchers populate a project Library by metadata rather than only by PDF upload. The phase ships four ingestion surfaces and a duplicate-resolution workflow:

- **DOI lookup** — paste a DOI, Crossref resolves full metadata, "Add to project" creates an `Article` row with no `file_ref` (PDF can be uploaded later via the existing pipeline).
- **PubMed search** — query the NCBI E-utilities (esearch → efetch), preview results, multi-select and bulk-add.
- **RIS / BibTeX import** — drag-drop a `.ris` or `.bib` file, parse, preview detected records, user picks which to add (mirror of the Phase 8 RIS/BibTeX *export*).
- **Dedup workflow** — after every bulk import (and on demand), flag duplicate groups (DOI exact + fuzzy title + year proximity); user reviews side-by-side; merges drop-IDs into a keep-ID with full FK rewiring (highlights, screening_records, rob_assessments, extraction_records, meta_inputs).

**Architecture:**

- New service tree `services/ingest/` with four parser/lookup modules + one dedup module:
  - `crossref.py` — thin wrapper around the existing `services/crossref.py` that maps `CitationMetadata → ArticleMetadata` (the new uniform schema used by all ingest surfaces).
  - `pubmed.py` — `esearch` + `efetch` with NCBI E-utilities, XML parsing.
  - `ris.py` — pure RIS parser (no third-party dep — 25 line tag→field map).
  - `bibtex.py` — uses **`bibtexparser>=1.4,<2`** (NEW DEP, pinned to the v1 API).
  - `dedup.py` — extends/wraps the existing `services/dedupe.py` with a *group-finder* (`find_duplicates(articles) -> list[DuplicateGroup]`) using DOI exact-match first, then rapidfuzz `token_set_ratio ≥ 0.92` *plus* same year ± 1.
- New uniform schema `schemas/ingest.py::ArticleMetadata` (super-set of `CitationMetadata` — adds `abstract`, `pmid`, `source` provenance).
- New routes module `routes/ingest.py` — five surfaces (DOI lookup, PubMed search, import-from-metadata, RIS upload, BibTeX upload) + two dedup routes (`/duplicates`, `/merge-duplicates`).
- One alembic migration `0009_ingest.py` (chains from `0008_meta_analysis` from Phase 7.5) — adds:
  - `Article.pmid String(16) NULL INDEX` (queryable; cheap; future-proof for PubMed re-sync).
  - `Article.source String(16) NULL` — `'upload' | 'doi' | 'pubmed' | 'ris' | 'bibtex' | 'manual'` provenance for the audit trail. Defaults to `'upload'` for existing rows in the same `upgrade()` data-migration step.
- New repository method `SqliteArticleRepository.merge(*, keep_id, drop_ids, user_id) -> Article` — single SQLAlchemy transaction that rewrites every FK to `drop_ids` to `keep_id`, deletes the dropped rows, returns the merged keep row. The model count is fixed (highlights, article_notes, screening_records, rob_assessments, extraction_records, **meta_inputs** if 7.5 is in) — the migration won't add new tables, so the merge code lists them explicitly.
- Frontend: extends `LibraryPage.tsx` with three new action buttons + matching dialogs. New `DuplicatesPanel` rendered in-page when any duplicate group is flagged for the project. No new npm deps — we use the existing react-dropzone for RIS/BibTeX upload.

**Tech Stack additions:**

- API: **one new pip dep — `bibtexparser>=1.4,<2`** (pinned to the v1 API; v2 introduces a breaking parser rewrite). `rapidfuzz` and `httpx` are already present (Phase 2 / Phase 1). NCBI E-utilities is a public API — no key required, but accepts an optional `api_key` query param that raises the rate limit from 3 req/s to 10; we read this from `settings.ncbi_api_key: str | None = None` and an optional `entrez_email` for compliance.
- Web: no new deps.

---

## Citation-safety + provenance contract

Every ingested row carries a `source` value so future audit/export flows can distinguish a researcher-uploaded PDF from a Crossref-derived metadata-only stub. Provenance is server-set; the FE never picks it. AI extraction is **not** invoked for DOI/PMID/RIS/BibTeX imports — these sources are authoritative; we trust them verbatim. The PDF-upload pipeline (existing) still routes through `ai.extract_citation` → Crossref enrichment → merge.

---

## File Structure

```
apps/api/
├── alembic/versions/0009_ingest.py                          (NEW)
├── pyproject.toml                                            (modify: add bibtexparser)
├── src/research_api/
│   ├── db/models.py                                          (modify: Article.pmid, Article.source)
│   ├── settings.py                                           (modify: ncbi_api_key, entrez_email)
│   ├── schemas/
│   │   ├── ingest.py                                         (NEW — ArticleMetadata, DuplicateGroup, MergeRequest)
│   │   └── __init__.py                                       (modify: export)
│   ├── repositories/articles.py                              (modify: merge() method)
│   ├── services/
│   │   ├── ingest/
│   │   │   ├── __init__.py                                   (NEW)
│   │   │   ├── crossref.py                                   (NEW — wrap services/crossref.py)
│   │   │   ├── pubmed.py                                     (NEW)
│   │   │   ├── ris.py                                        (NEW)
│   │   │   ├── bibtex.py                                     (NEW)
│   │   │   └── dedup.py                                      (NEW — group-finder)
│   │   └── dedupe.py                                         (existing, untouched)
│   ├── routes/
│   │   ├── ingest.py                                         (NEW — sub-router included by main.py)
│   │   └── (main.py)                                         (modify: include ingest_router)
└── tests/
    ├── fixtures/
    │   ├── crossref_sample.json                              (NEW — captured Crossref response)
    │   ├── pubmed_esearch_sample.xml                         (NEW)
    │   ├── pubmed_efetch_sample.xml                          (NEW)
    │   ├── ris_zotero_sample.ris                             (NEW)
    │   ├── ris_pubmed_export_sample.ris                      (NEW)
    │   └── bibtex_zotero_sample.bib                          (NEW)
    ├── test_ingest_crossref.py                               (NEW)
    ├── test_ingest_pubmed.py                                 (NEW)
    ├── test_ingest_ris.py                                    (NEW)
    ├── test_ingest_bibtex.py                                 (NEW)
    ├── test_ingest_dedup.py                                  (NEW — group finder)
    ├── test_ingest_route_doi.py                              (NEW)
    ├── test_ingest_route_pubmed.py                           (NEW)
    ├── test_ingest_route_import_metadata.py                  (NEW)
    ├── test_ingest_route_ris.py                              (NEW)
    ├── test_ingest_route_bibtex.py                           (NEW)
    ├── test_ingest_route_duplicates.py                       (NEW — GET + merge)
    ├── test_articles_merge.py                                (NEW — repo-level merge with FK rewiring)
    └── test_security_ingest_isolation.py                     (NEW — cross-user / cross-project)

apps/web/
├── src/
│   ├── lib/api.ts                                            (modify: ingestApi + zod schemas)
│   ├── components/library/
│   │   ├── AddByDoiInline.tsx                                (NEW)
│   │   ├── PubMedSearchDialog.tsx                            (NEW)
│   │   ├── RisBibtexDropzone.tsx                             (NEW)
│   │   ├── ImportPreviewDialog.tsx                           (NEW — shared by RIS / BibTeX / PubMed-bulk)
│   │   └── DuplicatesPanel.tsx                               (NEW)
│   ├── hooks/useIngest.ts                                    (NEW)
│   └── routes/LibraryPage.tsx                                (modify: ingest action row + DuplicatesPanel)
└── (no new deps)

docs/phase-8p6-screenshots/                                   (NEW)
```

---

## Pre-flight

- [ ] **Step 1: Verify Phase 7.5 + 8.5 tags are current**: `git tag --list | grep -E "phase-(7p5|8p5)"` → both should show.
- [ ] **Step 2: Branch (optional)**: `git checkout -b phase-8p6`.
- [ ] **Step 3: Backend baseline**: `cd apps/api && python -m pytest -q` → ≥ 656 + (Phase 7.5 ~90) + (Phase 8.5 ~50) green. Record the count for BUILD_LOG.
- [ ] **Step 4: Frontend baseline**: `cd apps/web && npm run typecheck && npm test -- --run && npm run build` → clean.
- [ ] **Step 5: Verify the assumed migration head**: `cd apps/api && alembic current` → should show `0008_meta_analysis` (head from Phase 7.5). This plan's `0009_ingest.py` sets `down_revision = "0008"`.
- [ ] **Step 6: Confirm `rapidfuzz` + `httpx` are importable** (existing): `python -c "import rapidfuzz, httpx; print('ok')"`.

---

## Task 1: Add `bibtexparser` dep + schema additions for Article (TDD-supportive)

**Files:**
- Modify: `apps/api/pyproject.toml`
- Modify: `apps/api/src/research_api/db/models.py`
- Modify: `apps/api/src/research_api/settings.py`
- Create: `apps/api/alembic/versions/0009_ingest.py`
- Create: `apps/api/tests/test_ingest_schema.py`

### Dep + settings additions

`pyproject.toml` — under `[project] dependencies`, add `"bibtexparser>=1.4,<2"`. v1 ships the stable `bibtexparser.loads(text)` → `BibDatabase` API we use here; v2 introduces a breaking rewrite, so cap it.

`settings.py` — add:

```python
ncbi_api_key: str | None = None
entrez_email: str = "noreply@research-assistant.local"
```

### Article additions

- `Article.pmid Mapped[str | None] = mapped_column(String(16), nullable=True)` + `Index("ix_articles_pmid", "pmid")`.
- `Article.source Mapped[str] = mapped_column(String(16), default="upload", nullable=False)` — `'upload' | 'doi' | 'pubmed' | 'ris' | 'bibtex' | 'manual'`.

### Migration `0009_ingest.py`

```python
revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None

def upgrade() -> None:
    with op.batch_alter_table("articles", schema=None) as batch_op:
        batch_op.add_column(sa.Column("pmid", sa.String(length=16), nullable=True))
        batch_op.add_column(
            sa.Column(
                "source",
                sa.String(length=16),
                nullable=False,
                server_default=sa.text("'upload'"),
            )
        )
        batch_op.create_index("ix_articles_pmid", ["pmid"])

    # One-time strip of the server_default so future inserts must set the column
    # via the ORM (we set it server-side at every ingest call site).
    with op.batch_alter_table("articles", schema=None) as batch_op:
        batch_op.alter_column("source", server_default=None)


def downgrade() -> None:
    with op.batch_alter_table("articles", schema=None) as batch_op:
        batch_op.drop_index("ix_articles_pmid")
        batch_op.drop_column("source")
        batch_op.drop_column("pmid")
```

### Tests (`test_ingest_schema.py`)

- `test_article_pmid_persists_and_is_indexed`.
- `test_article_source_required_and_defaults_to_upload_on_upgrade` (insert without `source` via raw SQL during the upgraded state → row exists with `source='upload'`).
- `test_article_source_must_be_in_enum_via_pydantic_validator` (validator on the read schema — defence-in-depth, since SQLite doesn't enforce CHECK by default).

- [ ] **Step 1:** Tests. **Step 2:** Add dep + settings + model fields + migration. **Step 3:** `alembic upgrade head` → green. **Step 4:** `pip install -e ".[dev]"` from `apps/api`. **Step 5:** Commit: `git commit -am "feat(phase8p6): article.pmid + article.source + bibtexparser dep"`.

---

## Task 2: Uniform `ArticleMetadata` + `DuplicateGroup` + `MergeRequest` schemas

**Files:** `apps/api/src/research_api/schemas/ingest.py`, modify `schemas/__init__.py`.

```python
ArticleSource = Literal["upload", "doi", "pubmed", "ris", "bibtex", "manual"]


class ArticleMetadata(BaseModel):
    """Uniform shape returned by every ingest surface (DOI/PubMed/RIS/BibTeX)
    BEFORE the row is persisted. Maps 1:1 to ArticleCreate plus pmid/abstract/source."""
    title: str
    authors: list[str] = []
    journal: str | None = None
    year: int | None = None
    volume: str | None = None
    issue: str | None = None
    pages: str | None = None
    doi: str | None = None
    pmid: str | None = None
    abstract: str | None = None
    source: ArticleSource


class ImportFromMetadataRequest(BaseModel):
    items: list[ArticleMetadata] = Field(min_length=1)


class ImportFromMetadataResponse(BaseModel):
    created: list[ArticleRead]
    skipped_duplicates: list[ArticleRead]   # rows that already existed by DOI/PMID
    duplicate_groups: list["DuplicateGroup"]  # *fuzzy* candidates flagged for review


class DuplicateGroup(BaseModel):
    keep_candidate_id: str                  # the oldest row (deterministic)
    candidate_ids: list[str]                # includes the keep candidate
    reason: Literal["doi_exact", "pmid_exact", "title_fuzzy"]
    score: float                            # 1.0 for exact; rapidfuzz/100 for fuzzy


class MergeRequest(BaseModel):
    keep_id: str
    drop_ids: list[str] = Field(min_length=1)


class DoiLookupRequest(BaseModel):
    doi: str


class PubMedSearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=500)
    retmax: int = Field(default=20, ge=1, le=100)
```

Note: `DuplicateGroup.score = 1.0` for `doi_exact`/`pmid_exact`; fuzzy hits use `rapidfuzz.fuzz.token_set_ratio(...) / 100`. **Reason precedence:** if both DOIs match AND titles fuzz-match, the group is `"doi_exact"`.

- [ ] **Step 1:** Implement. **Step 2:** Export from `schemas/__init__.py`. **Step 3:** Commit.

---

## Task 3: `services/ingest/crossref.py` — DOI → `ArticleMetadata` (TDD)

**Files:**
- Create: `apps/api/src/research_api/services/ingest/__init__.py` (empty for now — modules import directly)
- Create: `apps/api/src/research_api/services/ingest/crossref.py`
- Create: `apps/api/tests/test_ingest_crossref.py`
- Create: `apps/api/tests/fixtures/crossref_sample.json` (capture from `curl https://api.crossref.org/works/10.1056/NEJMoa2110345` — strip to ≤ 5 KiB)

### Public API

```python
async def lookup_doi_metadata(
    doi: str, *, http_client: httpx.AsyncClient | None = None,
) -> ArticleMetadata | None:
    """Resolve a DOI via Crossref → uniform ArticleMetadata.
    Returns None on 404 / parse failure / network error."""
```

Reuses the existing `services.crossref.lookup_doi` → `CitationMetadata` and maps the result to `ArticleMetadata(source="doi", abstract=msg.get("abstract"), pmid=None)`. Crossref's `abstract` field is JATS-XML — strip tags via `re.sub(r"<[^>]+>", " ", raw)` then collapse whitespace.

The Crossref `User-Agent` already includes a mailto in the existing module; carry it through. If `settings.entrez_email` is set we *additionally* append a `+{email}` to the User-Agent (Crossref's polite pool prefers a real contact).

### Tests (`test_ingest_crossref.py`)

Mirror the existing `tests/test_crossref.py` pattern (`httpx.MockTransport`):

- `test_lookup_doi_metadata_happy_path` — load `crossref_sample.json`, mount a `MockTransport`, assert `meta.title`, `authors[0]`, `journal`, `year`, `doi`, `source == "doi"`.
- `test_lookup_doi_metadata_extracts_abstract_strips_jats`.
- `test_lookup_doi_metadata_returns_none_on_404`.
- `test_lookup_doi_metadata_returns_none_on_network_error` (`MockTransport` that raises `httpx.NetworkError`).
- `test_lookup_doi_metadata_normalises_doi_prefix` (input `https://doi.org/10.x/y` → calls Crossref with the bare DOI).
- `test_lookup_doi_metadata_handles_missing_authors_list_gracefully`.

- [ ] **Step 1:** Capture fixture (`scripts/capture_crossref.sh` is a one-liner curl). **Step 2:** Tests. **Step 3:** Implement. **Step 4:** Commit.

---

## Task 4: `services/ingest/pubmed.py` — esearch + efetch (TDD)

**Files:**
- Create: `apps/api/src/research_api/services/ingest/pubmed.py`
- Create: `apps/api/tests/test_ingest_pubmed.py`
- Create: `apps/api/tests/fixtures/pubmed_esearch_sample.xml` (`https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term=...&retmode=xml`)
- Create: `apps/api/tests/fixtures/pubmed_efetch_sample.xml` (`efetch.fcgi?db=pubmed&id=...&retmode=xml`)

### Public API

```python
ESEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
EFETCH_URL  = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"

async def search_pubmed(
    query: str, *, retmax: int = 20,
    api_key: str | None = None, email: str = "noreply@research-assistant.local",
    http_client: httpx.AsyncClient | None = None,
) -> list[ArticleMetadata]:
    """esearch → list of PMIDs → efetch → parse XML → list[ArticleMetadata].
    Empty list on any failure; never raises."""

async def fetch_pmid_metadata(
    pmids: list[str], *, api_key: str | None = None,
    email: str = "noreply@research-assistant.local",
    http_client: httpx.AsyncClient | None = None,
) -> list[ArticleMetadata]:
    """Direct efetch path. Used by the DOI-lookup PMID fall-through."""
```

### XML parsing

Use **`xml.etree.ElementTree`** from the stdlib (no new dep). Defuse with `defusedxml.ElementTree` if `defusedxml` is already in deps — check `pyproject.toml`; if not, use stdlib `ElementTree` with `forbid_dtd=True` (not directly available; **mitigate by reading only at the test boundary**: `ET.fromstring(text)` where `text` is the bytes Crossref returned; we already trust the wire). Track adding `defusedxml` in DEFERRED for defence-in-depth.

Tags read per `<PubmedArticle>`:
- `MedlineCitation/PMID` → `pmid`
- `MedlineCitation/Article/ArticleTitle` → `title`
- `MedlineCitation/Article/Abstract/AbstractText` (join with `" "` when multiple `Label`/`NlmCategory` segments) → `abstract`
- `MedlineCitation/Article/AuthorList/Author` → `f"{ForeName} {LastName}".strip()` for each; skip CollectiveName-only authors.
- `MedlineCitation/Article/Journal/Title` → `journal`
- `MedlineCitation/Article/Journal/JournalIssue/PubDate/Year` (fall back to `MedlineDate[:4]`) → `year`
- `MedlineCitation/Article/Journal/JournalIssue/Volume` / `Issue` → `volume` / `issue`
- `MedlineCitation/Article/Pagination/MedlinePgn` → `pages`
- `PubmedData/ArticleIdList/ArticleId[@IdType="doi"]` → `doi`

`source = "pubmed"`.

### Robustness

- Timeout 15 s (PubMed is sometimes slow; longer than Crossref's 10).
- 429 → wait 1 s, retry once with `tenacity.AsyncRetrying`. After second 429 → return `[]`.
- 5xx / 4xx → log WARNING, return `[]`.

### Tests

- `test_search_pubmed_happy_path` — `MockTransport` returns esearch.xml then efetch.xml; assert ≥ 1 result, fields populated, `source="pubmed"`.
- `test_search_pubmed_empty_query_returns_empty`.
- `test_search_pubmed_zero_results_returns_empty`.
- `test_search_pubmed_includes_api_key_when_provided` — inspect the URL params in the captured request.
- `test_search_pubmed_appends_email_to_request`.
- `test_search_pubmed_handles_5xx_returns_empty`.
- `test_search_pubmed_handles_429_with_one_retry`.
- `test_search_pubmed_strips_multi_segment_abstract`.
- `test_fetch_pmid_metadata_batches_ids_into_one_efetch`.
- `test_fetch_pmid_metadata_skips_collective_only_authors`.
- `test_fetch_pmid_metadata_extracts_doi_from_article_id_list`.

- [ ] **Step 1:** Capture two XML fixtures. **Step 2:** Tests. **Step 3:** Implement. **Step 4:** Commit.

---

## Task 5: `services/ingest/ris.py` — RIS parser (TDD)

**Files:**
- Create: `apps/api/src/research_api/services/ingest/ris.py`
- Create: `apps/api/tests/test_ingest_ris.py`
- Create: `apps/api/tests/fixtures/ris_zotero_sample.ris`
- Create: `apps/api/tests/fixtures/ris_pubmed_export_sample.ris`

### Public API

```python
def parse_ris(text: str) -> list[ArticleMetadata]:
    """Parse RIS text into ArticleMetadata. Skips records lacking a title.
    source='ris'. Never raises — malformed records are silently dropped."""
```

### Format

RIS is line-based: `TAG  - VALUE`. Tags used:

| Tag | Field |
|-----|-------|
| `TY` | record type (we accept any; filter only on `title` presence) |
| `TI` / `T1` | title (concatenate if multiple) |
| `AU` / `A1` | author (repeatable; append to list, normalise "Last, First" → "First Last") |
| `JO` / `JF` / `T2` | journal |
| `PY` / `Y1` | year (parse first 4 digits) |
| `VL` | volume |
| `IS` | issue |
| `SP` / `EP` | start/end page → `f"{SP}-{EP}"` |
| `DO` | doi |
| `AB` / `N2` | abstract (concatenate with `" "`) |
| `ER` | end-of-record marker |

Records are delimited by `ER  -`. The parser must tolerate Windows / Unix / mixed line endings (use `splitlines()`).

### Tests

- `test_parse_ris_zotero_export_round_trip` — load the fixture (≥ 3 records); assert title/authors/journal/year/doi for each.
- `test_parse_ris_pubmed_export_round_trip`.
- `test_parse_ris_normalises_author_last_first_to_first_last`.
- `test_parse_ris_concatenates_multi_line_abstract`.
- `test_parse_ris_handles_missing_pages_gracefully`.
- `test_parse_ris_drops_record_without_title`.
- `test_parse_ris_handles_crlf_lf_mixed_newlines`.
- `test_parse_ris_empty_input_returns_empty_list`.
- `test_parse_ris_source_is_ris_on_every_record`.

- [ ] **Step 1:** Capture two fixtures. **Step 2:** Tests. **Step 3:** Implement. **Step 4:** Commit.

---

## Task 6: `services/ingest/bibtex.py` — BibTeX parser (TDD)

**Files:**
- Create: `apps/api/src/research_api/services/ingest/bibtex.py`
- Create: `apps/api/tests/test_ingest_bibtex.py`
- Create: `apps/api/tests/fixtures/bibtex_zotero_sample.bib`
- Create: `apps/api/tests/fixtures/bibtex_mendeley_sample.bib`
- Create: `apps/api/tests/fixtures/bibtex_googlescholar_sample.bib`

### Public API

```python
def parse_bibtex(text: str) -> list[ArticleMetadata]:
    """Parse BibTeX text via bibtexparser v1. Only @article entries are returned;
    @inproceedings/@book/etc are skipped (orthopaedics literature is journals).
    source='bibtex'. Never raises — bibtexparser errors are caught + logged."""
```

### Mapping

Using `bibtexparser.loads(text).entries`:

| BibTeX field | ArticleMetadata field |
|-------------|----------------------|
| `title` | title (strip outer `{}` braces via `bibtexparser.customization.homogenize_latex_encoding`-aware pass) |
| `author` | authors (split on ` and `, normalise "Last, First" → "First Last") |
| `journal` / `journaltitle` | journal |
| `year` | year (parse first 4 digits) |
| `volume` | volume |
| `number` / `issue` | issue |
| `pages` | pages (canonicalise `--` to `-`) |
| `doi` | doi |
| `abstract` | abstract |

### Tests

- `test_parse_bibtex_zotero_round_trip`.
- `test_parse_bibtex_mendeley_round_trip`.
- `test_parse_bibtex_googlescholar_round_trip` (Google Scholar quotes authors differently — `{Last, First}` braced).
- `test_parse_bibtex_strips_brace_armor_on_titles` (`{Total Hip {Arthroplasty}}` → `Total Hip Arthroplasty`).
- `test_parse_bibtex_handles_multiple_authors_split_on_and`.
- `test_parse_bibtex_skips_non_article_entries`.
- `test_parse_bibtex_handles_inproceedings_entry_silently_skipped`.
- `test_parse_bibtex_corrupted_input_returns_empty_list_logs_warning` (`caplog.at_level("WARNING")`).
- `test_parse_bibtex_source_is_bibtex_on_every_record`.

- [ ] **Step 1:** Capture three fixtures. **Step 2:** Tests. **Step 3:** Implement. **Step 4:** Commit.

---

## Task 7: `services/ingest/dedup.py` — group finder (TDD)

**Files:**
- Create: `apps/api/src/research_api/services/ingest/dedup.py`
- Create: `apps/api/tests/test_ingest_dedup.py`

### Public API

```python
@dataclass(frozen=True)
class DuplicateCandidate:
    article_id: str
    title: str
    year: int | None
    doi: str | None
    pmid: str | None


def find_duplicates(
    candidates: list[DuplicateCandidate],
    *,
    fuzzy_threshold: float = 0.92,
    year_tolerance: int = 1,
) -> list[DuplicateGroup]:
    """Return groups of likely duplicates.

    Algorithm:
    1. Bucket by lowercase DOI; any bucket with len >= 2 → group with reason='doi_exact'.
    2. Among rows NOT yet grouped, bucket by PMID; any bucket with len >= 2 → 'pmid_exact'.
    3. Among rows STILL not grouped, run rapidfuzz token_set_ratio over normalised
       titles in O(n^2). Any pair with ratio >= fuzzy_threshold AND |year_a - year_b| <= year_tolerance
       → group with reason='title_fuzzy'.
       Build connected components via union-find so transitive matches stay together.
    Return groups sorted by len(candidate_ids) DESC, then keep_candidate_id ASC."""
```

`keep_candidate_id` is the oldest row in the group (deterministic; the route layer will pass `created_at` in the candidate so the dedup module doesn't need DB access). For v1 we sort the input list by `created_at ASC` outside the function and pass it in — internally the first row in a group wins.

### Tests

- `test_find_duplicates_doi_exact` — two rows with same DOI → one group, reason `'doi_exact'`, score 1.0.
- `test_find_duplicates_pmid_exact_when_no_doi`.
- `test_find_duplicates_title_fuzzy_above_threshold` — `"Anterior vs Posterior Approach in THA"` vs `"Anterior vs. posterior approach in total hip arthroplasty"` → grouped, reason `'title_fuzzy'`, score ≥ 0.92.
- `test_find_duplicates_year_outside_tolerance_does_not_match` — same titles but years 2018 / 2024 → not grouped.
- `test_find_duplicates_doi_takes_precedence_over_fuzzy` — same DOI + same titles → one group, reason `'doi_exact'`.
- `test_find_duplicates_transitive_fuzzy_via_union_find` — A~B and B~C → one group of three.
- `test_find_duplicates_no_duplicates_returns_empty`.
- `test_find_duplicates_handles_missing_title_falls_through_to_doi`.
- `test_find_duplicates_deterministic_ordering`.

- [ ] **Step 1:** Tests. **Step 2:** Implement (use `from rapidfuzz import fuzz`). **Step 3:** Commit.

---

## Task 8: Repository — `SqliteArticleRepository.merge(...)` (TDD)

**Files:**
- Modify: `apps/api/src/research_api/repositories/articles.py`
- Create: `apps/api/tests/test_articles_merge.py`

### Public API

```python
async def merge(self, *, keep_id: str, drop_ids: list[str], user_id: str) -> Article:
    """Merge drop_ids into keep_id. All FKs that currently point at any drop_id
    are rewritten to keep_id. The drop rows are then deleted. Single transaction.

    Refuses if:
    - keep_id not owned by user_id → ValueError("keep article not found")
    - any drop_id not owned by user_id → ValueError("drop article not found")
    - any drop_id == keep_id → ValueError("cannot merge an article into itself")
    - keep + drop don't share the same project_id → ValueError("cross-project merge")"""
```

### Tables to rewrite

The merge code lists explicit table targets so a schema drift fails the unit test loudly:

```python
_FK_TABLES_BY_COLUMN = [
    ("highlights", "article_id"),
    ("article_notes", "article_id"),
    ("screening_records", "article_id"),
    ("rob_assessments", "article_id"),
    ("extraction_records", "article_id"),
    # Phase 7.5 add — guard with try/except importerror so 8.6 still runs
    # cleanly if it's somehow shipped before 7.5 is in the database.
    ("meta_inputs", "article_id"),
]
```

For tables with composite UNIQUE (e.g. `screening_records (review_id, article_id, stage)`, `rob_assessments (review_id, article_id, tool)`, `extraction_records (review_id, article_id)`), a naive UPDATE can hit the constraint. Resolution strategy: **prefer the keep row's record**; for each drop row whose `(review_id, *)` already exists on `keep_id`, **delete the drop row** instead of updating. Implement via a per-table `select(..., where=...)` that finds collisions first, deletes those, then updates the rest.

### Tests

- `test_merge_rewrites_highlight_fks`.
- `test_merge_rewrites_article_note_fk_when_no_collision`.
- `test_merge_deletes_drop_article_note_when_keep_already_has_one` (UNIQUE collision path).
- `test_merge_rewrites_screening_records_when_distinct_stages`.
- `test_merge_deletes_screening_record_when_keep_already_has_same_stage`.
- `test_merge_rewrites_rob_assessments_with_distinct_tools`.
- `test_merge_rewrites_extraction_records_when_keep_has_none`.
- `test_merge_deletes_drop_extraction_when_keep_already_has_one`.
- `test_merge_rewrites_meta_inputs_when_present` (only run if Phase 7.5 tables exist; skip via `pytest.importorskip` style guard).
- `test_merge_handles_drop_with_file_ref_does_not_delete_file` (storage delete is out of scope — file lives on; future polish).
- `test_merge_refuses_same_id`.
- `test_merge_refuses_cross_project`.
- `test_merge_refuses_cross_user`.
- `test_merge_returns_keep_row`.
- `test_merge_transaction_atomic_on_failure` (monkeypatch the second UPDATE to raise; assert nothing committed).

- [ ] **Step 1:** Tests. **Step 2:** Implement. **Step 3:** Commit.

---

## Task 9: Route — `POST /lookup-doi` (TDD)

**Files:**
- Create: `apps/api/src/research_api/routes/ingest.py`
- Modify: `apps/api/src/research_api/main.py` (`include_router(ingest_router, prefix="/api")`)
- Create: `apps/api/tests/test_ingest_route_doi.py`

```
POST /projects/{pid}/articles/lookup-doi  body: {doi}  → ArticleMetadata
```

Flow: resolve project for user (404 if missing). Call `lookup_doi_metadata(doi)`. None → 404 with `"DOI not found in Crossref"`. Otherwise return the metadata (NOT persisted yet — UI confirms and then calls import-from-metadata).

### Tests

- `test_lookup_doi_route_returns_metadata` (Crossref MockTransport via FastAPI dependency override of the http client).
- `test_lookup_doi_route_404_on_missing_doi`.
- `test_lookup_doi_route_404_on_wrong_user_project`.
- `test_lookup_doi_route_normalises_https_prefixed_doi`.
- `test_lookup_doi_route_422_on_empty_body`.

- [ ] **Step 1:** Tests. **Step 2:** Implement. **Step 3:** Commit.

---

## Task 10: Route — `POST /search-pubmed` (TDD)

**Files:**
- Extend: `apps/api/src/research_api/routes/ingest.py`
- Create: `apps/api/tests/test_ingest_route_pubmed.py`

```
POST /projects/{pid}/articles/search-pubmed  body: PubMedSearchRequest  → list[ArticleMetadata]
```

Flow: resolve project (404). Call `search_pubmed(query, retmax, api_key=settings.ncbi_api_key, email=settings.entrez_email)`. Returns whatever the service returned (possibly empty).

### Tests

- `test_search_pubmed_route_returns_results` (esearch + efetch MockTransport).
- `test_search_pubmed_route_passes_settings_api_key_to_service`.
- `test_search_pubmed_route_empty_query_returns_422_via_pydantic`.
- `test_search_pubmed_route_retmax_capped_at_100`.
- `test_search_pubmed_route_404_on_wrong_user_project`.

- [ ] **Step 1:** Tests. **Step 2:** Implement. **Step 3:** Commit.

---

## Task 11: Route — `POST /import-from-metadata` (TDD)

**Files:**
- Extend: `apps/api/src/research_api/routes/ingest.py`
- Create: `apps/api/tests/test_ingest_route_import_metadata.py`

```
POST /projects/{pid}/articles/import-from-metadata  body: ImportFromMetadataRequest  → ImportFromMetadataResponse
```

Flow:

1. Resolve project (404).
2. For each `item` in body.items:
   - **Server-side dedup-against-existing**: query existing articles in the project; if any has `doi == item.doi (case-insensitive)` OR `pmid == item.pmid`, append the *existing row* to `skipped_duplicates` and skip.
   - Otherwise create an Article row with `file_ref=None`, `file_type=None`, `source=item.source`, all other metadata fields from the item. Append to `created`.
3. After all rows are processed, run `find_duplicates` over the union of (newly created + existing in project) to flag any fuzzy duplicates. Build `duplicate_groups` and return.
4. Return `ImportFromMetadataResponse(created, skipped_duplicates, duplicate_groups)`.

### Tests

- `test_import_from_metadata_creates_rows_with_correct_source`.
- `test_import_from_metadata_skips_existing_doi`.
- `test_import_from_metadata_skips_existing_pmid`.
- `test_import_from_metadata_returns_fuzzy_duplicate_groups`.
- `test_import_from_metadata_404_on_other_user_project`.
- `test_import_from_metadata_empty_items_returns_422`.
- `test_import_from_metadata_persists_abstract_and_pmid`.

- [ ] **Step 1:** Tests. **Step 2:** Implement. **Step 3:** Commit.

---

## Task 12: Route — `POST /import-ris` (multipart) (TDD)

**Files:**
- Extend: `apps/api/src/research_api/routes/ingest.py`
- Create: `apps/api/tests/test_ingest_route_ris.py`

```
POST /projects/{pid}/articles/import-ris  multipart file=upload.ris  → list[ArticleMetadata]
```

Flow:

1. Resolve project (404).
2. Read file bytes; cap at 2 MiB (RIS files for a typical export are < 500 KiB — generous cap).
3. Decode as UTF-8 with `errors="replace"`. (RIS spec is ASCII but exports often carry Latin-1 — replacement is acceptable for parser robustness.)
4. Call `parse_ris(text)` → `list[ArticleMetadata]`. Empty list → 422 with `"No RIS records detected"`.
5. **Do NOT persist.** Return the parsed metadata as a *preview*; the FE then calls `/import-from-metadata` with the user-selected subset.

### Tests

- `test_import_ris_returns_preview_list`.
- `test_import_ris_404_on_other_user_project`.
- `test_import_ris_413_when_oversize`.
- `test_import_ris_422_when_zero_records`.
- `test_import_ris_handles_zotero_export_fixture`.

- [ ] **Step 1:** Tests. **Step 2:** Implement. **Step 3:** Commit.

---

## Task 13: Route — `POST /import-bibtex` (multipart) (TDD)

**Files:**
- Extend: `apps/api/src/research_api/routes/ingest.py`
- Create: `apps/api/tests/test_ingest_route_bibtex.py`

```
POST /projects/{pid}/articles/import-bibtex  multipart file=upload.bib  → list[ArticleMetadata]
```

Same flow as RIS (decode → parse_bibtex → preview list, no persist).

### Tests

- `test_import_bibtex_returns_preview_list`.
- `test_import_bibtex_404_on_other_user_project`.
- `test_import_bibtex_413_when_oversize`.
- `test_import_bibtex_422_when_zero_records`.
- `test_import_bibtex_handles_zotero_mendeley_googlescholar_fixtures`.

- [ ] **Step 1:** Tests. **Step 2:** Implement. **Step 3:** Commit.

---

## Task 14: Routes — `GET /duplicates` + `POST /merge-duplicates` (TDD)

**Files:**
- Extend: `apps/api/src/research_api/routes/ingest.py`
- Create: `apps/api/tests/test_ingest_route_duplicates.py`

```
GET  /projects/{pid}/articles/duplicates                      → list[DuplicateGroup]
POST /projects/{pid}/articles/merge-duplicates  body: MergeRequest  → ArticleRead   (the kept row)
```

### GET flow

1. Resolve project (404).
2. Load all articles in the project for the user.
3. Build `DuplicateCandidate` list sorted by `created_at ASC` (so the oldest wins).
4. Call `find_duplicates`. Return the groups (may be empty).

### POST flow

1. Resolve project (404).
2. Call `repo.merge(keep_id=..., drop_ids=..., user_id=...)`.
3. Catch `ValueError` → 422 with the message.
4. Return the merged row via `_hydrated(article, container)` (re-uses existing helper from `routes/articles.py` — refactor to a shared `routes/_articles_hydrate.py` or copy the helper; pick copy-and-paste for v1 to minimise churn).

### Tests

- `test_get_duplicates_returns_groups_for_doi_exact`.
- `test_get_duplicates_returns_groups_for_title_fuzzy`.
- `test_get_duplicates_returns_empty_when_no_duplicates`.
- `test_get_duplicates_404_on_other_user_project`.
- `test_merge_duplicates_returns_kept_row`.
- `test_merge_duplicates_422_on_cross_project`.
- `test_merge_duplicates_422_on_self_merge`.
- `test_merge_duplicates_rewires_highlights` (end-to-end: seed a highlight on a drop row; merge; assert the highlight now belongs to keep).
- `test_merge_duplicates_404_on_other_user`.

- [ ] **Step 1:** Tests. **Step 2:** Implement. **Step 3:** Commit.

---

## Task 15: Security regression — cross-user / cross-project isolation

**File:** `apps/api/tests/test_security_ingest_isolation.py`.

Tests (every endpoint):

- `test_lookup_doi_404_for_other_users_project`.
- `test_search_pubmed_404_for_other_users_project`.
- `test_import_from_metadata_404_for_other_users_project`.
- `test_import_from_metadata_rejects_when_pid_belongs_to_another_user`.
- `test_import_ris_404_for_other_users_project`.
- `test_import_bibtex_404_for_other_users_project`.
- `test_get_duplicates_only_groups_within_owning_user`.
- `test_merge_duplicates_rejects_when_keep_owned_by_another_user`.
- `test_merge_duplicates_rejects_when_drop_owned_by_another_user`.
- `test_merge_duplicates_rejects_when_articles_in_different_projects`.

- [ ] **Step 1:** Tests. **Step 2:** Fix any leaks. **Step 3:** Commit.

---

## Task 16: Frontend API client (`ingestApi`) — TDD

**File:** modify `apps/web/src/lib/api.ts`; create `apps/web/src/lib/__tests__/ingestApi.test.ts`.

Add zod schemas + endpoint helpers mirroring `articlesApi`:

```ts
export const ArticleSourceSchema = z.enum(['upload','doi','pubmed','ris','bibtex','manual'])

export const ArticleMetadataSchema = z.object({
  title: z.string(),
  authors: z.array(z.string()).default([]),
  journal: z.string().nullable().optional(),
  year: z.number().int().nullable().optional(),
  volume: z.string().nullable().optional(),
  issue: z.string().nullable().optional(),
  pages: z.string().nullable().optional(),
  doi: z.string().nullable().optional(),
  pmid: z.string().nullable().optional(),
  abstract: z.string().nullable().optional(),
  source: ArticleSourceSchema,
})

export const DuplicateGroupSchema = z.object({
  keep_candidate_id: z.string(),
  candidate_ids: z.array(z.string()).min(2),
  reason: z.enum(['doi_exact','pmid_exact','title_fuzzy']),
  score: z.number().min(0).max(1),
})

export const ImportFromMetadataResponseSchema = z.object({
  created: z.array(ArticleSchema),
  skipped_duplicates: z.array(ArticleSchema),
  duplicate_groups: z.array(DuplicateGroupSchema),
})

export const ingestApi = {
  lookupDoi: (pid, doi) => api.post(`/api/projects/${pid}/articles/lookup-doi`, { doi })
    .then(r => ArticleMetadataSchema.parse(r.data)),
  searchPubMed: (pid, query, retmax = 20) => api.post(`/api/projects/${pid}/articles/search-pubmed`, { query, retmax })
    .then(r => z.array(ArticleMetadataSchema).parse(r.data)),
  importFromMetadata: (pid, items) => api.post(`/api/projects/${pid}/articles/import-from-metadata`, { items })
    .then(r => ImportFromMetadataResponseSchema.parse(r.data)),
  importRis: (pid, file) => { const fd = new FormData(); fd.append('file', file); return api.post(`/api/projects/${pid}/articles/import-ris`, fd).then(r => z.array(ArticleMetadataSchema).parse(r.data)) },
  importBibtex: (pid, file) => { const fd = new FormData(); fd.append('file', file); return api.post(`/api/projects/${pid}/articles/import-bibtex`, fd).then(r => z.array(ArticleMetadataSchema).parse(r.data)) },
  duplicates: (pid) => api.get(`/api/projects/${pid}/articles/duplicates`).then(r => z.array(DuplicateGroupSchema).parse(r.data)),
  merge: (pid, keep_id, drop_ids) => api.post(`/api/projects/${pid}/articles/merge-duplicates`, { keep_id, drop_ids }).then(r => ArticleSchema.parse(r.data)),
}
```

Also extend `ArticleSchema` to include `pmid: z.string().nullable().optional()` + `source: ArticleSourceSchema.default('upload')`.

**Vitest:** parse one mocked payload of each new schema; assert one helper round-trips via msw or via mocked axios.

- [ ] **Step 1:** Add schemas + endpoints + types. **Step 2:** `npm run typecheck`. **Step 3:** Vitest. **Step 4:** Commit.

---

## Task 17: Frontend hook — `useIngest.ts`

**File:** `apps/web/src/hooks/useIngest.ts` (NEW).

TanStack Query hooks:

- `useLookupDoi(projectId)` — mutation (DOI strings are user-typed; we don't cache them as queries).
- `useSearchPubMed(projectId)` — mutation (search is action-driven).
- `useImportFromMetadata(projectId)` — mutation; on success invalidates `['articles', projectId]` and `['duplicates', projectId]`.
- `useImportRis(projectId)` / `useImportBibtex(projectId)` — mutations returning the preview list.
- `useDuplicates(projectId)` — query; `queryKey: ['duplicates', projectId]`.
- `useMergeDuplicates(projectId)` — mutation; on success invalidates `['articles', projectId]` and `['duplicates', projectId]`.

- [ ] **Step 1:** Implement. **Step 2:** Commit.

---

## Task 18: Frontend components — Library ingest UI

**Files (all NEW)** under `apps/web/src/components/library/`.

### `AddByDoiInline.tsx`
- Inline form on the Library page header (above `UploadZone`): text input + "Look up DOI" button.
- On success: opens `ImportPreviewDialog` with a single-row preview.

### `PubMedSearchDialog.tsx`
- Modal: query textarea + retmax slider (5/10/20/50). "Search" → renders a checklist (title, authors, year, journal, DOI/PMID badges, expandable abstract). "Add selected" → calls `useImportFromMetadata` then closes.

### `RisBibtexDropzone.tsx`
- Existing `react-dropzone` pattern. Accepts `.ris` and `.bib` (also `.bibtex`). On drop, infers from extension whether to call `useImportRis` or `useImportBibtex`. On success: opens `ImportPreviewDialog` with the preview list.

### `ImportPreviewDialog.tsx`
- Shared component used by DOI / PubMed / RIS / BibTeX flows. Props: `items: ArticleMetadata[]`, `onConfirm(selected)`.
- Checkbox per row (all checked by default). "Import {N} articles" button → calls `useImportFromMetadata` with the selected rows. On success: toast `"Added {n} · skipped {k} duplicates"` and re-route to a duplicates flow if the response includes any `duplicate_groups`.

### `DuplicatesPanel.tsx`
- Rendered on `LibraryPage` when `useDuplicates(projectId)` returns ≥ 1 group.
- For each group: side-by-side card list of candidate rows with title/year/journal/authors/DOI/PMID. The keep candidate is pre-selected; user can pick a different row as the "keep". "Merge {N} → 1" button → calls `useMergeDuplicates`. On success: toast + invalidate.

- [ ] **Step 1:** Implement five components. **Step 2:** Manual smoke: zero `console.error`. **Step 3:** Commit.

---

## Task 19: Wire ingest UI into `LibraryPage.tsx`

**File:** modify `apps/web/src/routes/LibraryPage.tsx`.

- Above the existing `<UploadZone>`, add a single row of three actions: `<AddByDoiInline/>`, `<PubMedSearchDialog/>` trigger button, and `<RisBibtexDropzone/>`.
- Below the article list, conditionally render `<DuplicatesPanel projectId={projectId}/>` when `useDuplicates(projectId).data.length > 0`.
- Pipe `onConfirm` from `ImportPreviewDialog` through to `useImportFromMetadata`, then invalidate the article list.

- [ ] **Step 1:** Modify. **Step 2:** `npm run typecheck && npm test -- --run && npm run build`. **Step 3:** Commit.

---

## Task 20: E2E browser smoke (chrome-devtools-mcp)

- [ ] **Step 1:** Boot servers (`apps/api`: `uvicorn research_api.main:app --port 8787`; `apps/web`: `npm run dev`).
- [ ] **Step 2:** Drive Chrome via MCP:
  1. Open `/library` against a fresh project.
  2. Paste a known DOI (`10.1056/NEJMoa2110345`) into `AddByDoiInline` → assert preview dialog opens with title populated → confirm → assert one article appears.
  3. Open PubMed search → query `"anterior approach total hip arthroplasty"` → retmax 10 → run → assert ≥ 1 result → tick 3 → confirm → assert 3 new articles.
  4. Drag a fixture `.ris` file onto the dropzone → assert preview opens → confirm → assert N new articles.
  5. Drag a fixture `.bib` file → same.
  6. Now seed a duplicate of one earlier title (re-import the same RIS) → confirm import → assert `DuplicatesPanel` appears with a group → click "Merge" → assert only one row remains.
  7. Open the kept row's reader → assert any pre-existing highlight/note is still attached.
- [ ] **Step 3:** Screenshot each step under `docs/phase-8p6-screenshots/`.
- [ ] **Step 4:** Accessibility audit (`chrome-devtools-mcp:a11y-debugging`) on `/library`. Confirm dropzone has an aria-label, dialogs trap focus, every form input has a `<Label>`.

---

## Task 21: `/security-review`

Targets:

- `services/ingest/pubmed.py` — XML parsing uses stdlib `ElementTree`; PubMed's wire format is bounded by NCBI. Track `defusedxml` add in `DEFERRED.md`. No user-supplied input reaches `ElementTree.fromstring` *except* via the request body's `query` param which is URL-encoded into the esearch call — that's HTTP, not XML, so no XXE surface here.
- `services/ingest/ris.py` — pure string parser, no eval/exec, no filesystem access.
- `services/ingest/bibtex.py` — `bibtexparser.loads(text)` is a pure parser; no execution. Track that bibtexparser v1 imports `pyparsing` at module load.
- `services/ingest/crossref.py` — uses existing percent-encoded DOI path; abstract JATS stripping uses a non-greedy `<[^>]+>` regex — no risk of executing tags.
- `routes/ingest.py` — every route resolves project via `proj_repo.get(pid, user_id)`; 404 on cross-user.
- `repositories/articles.merge` — explicit cross-user + cross-project refusal; UPDATE statements scoped on `user_id`; single transaction (`session.begin_nested()` if a sub-savepoint is needed; otherwise rely on the request-scoped session's outer transaction).
- File upload surfaces (`/import-ris`, `/import-bibtex`) — size cap 2 MiB; UTF-8 decode with replacement; never invoke any external process.
- Frontend `ImportPreviewDialog` — renders metadata text via React; no `dangerouslySetInnerHTML`.

- [ ] **Step 1:** Run `/security-review` on the diff.
- [ ] **Step 2:** Fix HIGH + MED inline. Log LOW to `POLISH.md`.
- [ ] **Step 3:** Commit.

---

## Task 22: BUILD_LOG entry + tag

Append `## 2026-05-18 · Phase 8.6 — Ingestion ✅ COMPLETE` to `BUILD_LOG.md`. Cover: backend (one new dep `bibtexparser`, migration `0009`, `services/ingest/` subtree, repo `merge`, routes), frontend (5 new components, `ingestApi`, hook, Library page wiring), test deltas (~+80 backend tests, ~+5 vitest), acceptance bar (DOI lookup, PubMed search, RIS, BibTeX, fuzzy dedup, merge with full FK rewiring), decisions (no AI extraction on metadata-only sources; ImportPreviewDialog two-step gate; `find_duplicates` uses union-find for transitive groups).

- [ ] **Step 1:** Compose entry.
- [ ] **Step 2:** `git tag phase-8p6`.

---

## Out of scope (deferred)

- **EMBASE, Scopus, Web of Science search** — Crossref + PubMed only in v1.
- **OAuth login to NCBI** for personalised query history — anonymous public API only.
- **Author disambiguation via ORCID** — names are taken verbatim from Crossref/PubMed.
- **AI-assisted dedup** ("are these the same paper?") — algorithmic only in v1.
- **Auto-attach PDFs from unpaywall / OA sources** on DOI lookup — manual upload remains the path.
- **`defusedxml`** — add as a hardening pass; the current XML surface is PubMed-only and trusted-ish.
- **Bulk re-dedup over the entire library** as a background job — runs synchronously on every import in v1.

---

## Self-Review

**Spec coverage:**
- DOI lookup ✅ Tasks 3, 9
- PubMed search ✅ Tasks 4, 10
- Bulk-add from metadata ✅ Task 11
- RIS upload ✅ Tasks 5, 12
- BibTeX upload ✅ Tasks 6, 13
- Dedup (DOI exact + fuzzy title + year proximity) ✅ Task 7
- Duplicates panel + merge ✅ Tasks 8, 14, 18
- Cross-user / cross-project isolation ✅ Task 15

**Multi-user readiness:** every new row carries `user_id` (Article already does). Every read scopes to `user_id`. Merge refuses cross-user and cross-project explicitly.

**Provenance:** `Article.source` carries the ingest path for every row. Existing rows default to `'upload'` via the migration's `server_default`.

**TDD ordering:** every service module has tests written before implementation. Route handlers likewise. Cross-cutting security regression is Task 15.

**Bite-sized tasks:** 22 tasks. Each ~5-minute step inside.

**Type consistency:** every enum (`ArticleSource`, `DuplicateGroup.reason`) is identical Python ↔ TS via `Literal` / `z.enum` pairs.

**Self-check ok. Proceeding to execution.**
````

---

# File 2 — paste into `docs/superpowers/plans/2026-05-18-phase-8p7-figures-consort-tables-journals.md`

````markdown
