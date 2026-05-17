# Phase 2 — Library Module — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` or `superpowers:executing-plans`. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upload PDFs/Word docs → Gemini extracts citation metadata → user confirms → article persists. Library page shows a sortable, searchable, filterable list with duplicate detection. Files live on the local SSD via the `FileStorage` adapter (LocalFsStorage now, Supabase-swappable later).

**Architecture:** Backend grows three new adapters fully wired this phase: `FileStorage` (LocalFs impl + signed-URL endpoint), `AIProvider` (Gemini impl with the §6.2 robustness layer — model chain, retry, demotion), and `CrossRef` client (DOI fallback). New `Article` aggregate with repository + migration + routes. Frontend gets a real `LibraryPage`, drag-and-drop upload zone, metadata confirmation modal, mobile nav drawer (POLISH carry-over).

**Tech Stack:** New backend deps: `google-generativeai`, `pypdf`, `python-docx`, `python-magic`, `rapidfuzz`, `tenacity`. New frontend deps: `react-dropzone`. Existing stack from Phase 1.

---

## File Structure (created or modified in this plan)

```
apps/api/
├── pyproject.toml                                  (modify: add deps)
├── alembic/versions/0002_articles.py               (NEW)
├── src/research_api/
│   ├── db/models.py                                (modify: add Article)
│   ├── schemas/
│   │   ├── __init__.py                             (modify: export new)
│   │   ├── article.py                              (NEW)
│   │   └── upload.py                               (NEW)
│   ├── services/
│   │   ├── storage/
│   │   │   ├── __init__.py                         (NEW)
│   │   │   ├── base.py                             (NEW — Protocol + StorageRef)
│   │   │   ├── local_fs.py                         (NEW)
│   │   │   └── signed_urls.py                      (NEW — HMAC tokens)
│   │   ├── ai/
│   │   │   ├── __init__.py                         (NEW)
│   │   │   ├── base.py                             (NEW — AIProvider Protocol)
│   │   │   ├── errors.py                           (NEW)
│   │   │   ├── model_chain.py                      (NEW — generic retry/demote)
│   │   │   ├── gemini.py                           (NEW)
│   │   │   ├── prompts/
│   │   │   │   ├── __init__.py                     (NEW)
│   │   │   │   └── citation_extraction.py          (NEW)
│   │   │   └── schemas.py                          (NEW — CitationMetadata)
│   │   ├── crossref.py                             (NEW)
│   │   ├── dedupe.py                               (NEW — rapidfuzz title match)
│   │   └── pdf_text.py                             (NEW — extract first N pages text)
│   ├── repositories/
│   │   ├── __init__.py                             (modify: export ArticleRepository)
│   │   └── articles.py                             (NEW)
│   ├── routes/
│   │   ├── __init__.py                             (modify: include new routers)
│   │   ├── articles.py                             (NEW)
│   │   ├── files.py                                (NEW — signed-URL serving)
│   │   └── health.py                               (modify: real provider check via AI chain)
│   ├── container.py                                (modify: add storage + ai_provider)
│   └── settings.py                                 (modify: AI_TIMEOUT, FILE_SIZE_CAP_MB)
└── tests/
    ├── test_local_fs_storage.py                    (NEW)
    ├── test_signed_urls.py                         (NEW)
    ├── test_model_chain.py                         (NEW)
    ├── test_gemini_provider.py                     (NEW — uses fake)
    ├── test_crossref.py                            (NEW — mocked HTTPX)
    ├── test_dedupe.py                              (NEW)
    ├── test_article_repository.py                  (NEW)
    ├── test_articles_route.py                      (NEW)
    └── conftest.py                                 (modify: add fake AI + tmp storage)

apps/web/
├── package.json                                    (modify: react-dropzone)
├── src/
│   ├── components/
│   │   ├── layout/
│   │   │   ├── MobileNav.tsx                       (NEW — POLISH item)
│   │   │   └── Topbar.tsx                          (modify: hamburger trigger)
│   │   ├── library/
│   │   │   ├── UploadZone.tsx                      (NEW)
│   │   │   ├── MetadataConfirmDialog.tsx           (NEW)
│   │   │   ├── ArticleListItem.tsx                 (NEW)
│   │   │   ├── ArticleFilters.tsx                  (NEW)
│   │   │   └── ProjectSelectGate.tsx               (NEW — pick project before library)
│   │   └── projects/
│   │       └── ProjectCard.tsx                     (modify: NavLink to /library?project=...)
│   ├── lib/
│   │   ├── api.ts                                  (modify: ArticleSchema + articlesApi)
│   │   └── projectContext.ts                       (NEW — active project store)
│   └── routes/
│       └── LibraryPage.tsx                         (modify: real impl, replace stub)
```

**Why these splits:** every adapter (Storage, AI, CrossRef) gets its own file with a Protocol + concrete impl. Routes are thin glue. The model chain is generic enough to be shared by Claude/OpenAI providers in later phases — so it lives in its own file, not inside `gemini.py`.

---

## Pre-flight

- [ ] **Step 1: Add Python deps to `apps/api/pyproject.toml`**

Update the `dependencies` array to include:

```toml
  "google-generativeai>=0.8",
  "pypdf>=4.0",
  "python-docx>=1.1",
  "python-magic>=0.4",
  "rapidfuzz>=3.0",
  "tenacity>=8.2",
```

Then install:

```bash
cd apps/api && .venv/bin/pip install -e ".[dev]"
```

Expected: install succeeds. `python-magic` on macOS needs `libmagic` — install via Homebrew if first run errors:

```bash
brew install libmagic
```

- [ ] **Step 2: Add frontend dep**

```bash
cd apps/web && npm install react-dropzone
```

- [ ] **Step 3: Commit pre-flight**

```bash
git commit -am "chore(phase2): add deps — google-generativeai, pypdf, python-docx, python-magic, rapidfuzz, tenacity, react-dropzone"
```

---

## Task 1: POLISH carry-over — Mobile nav drawer

**Files:**
- Create: `apps/web/src/components/layout/MobileNav.tsx`
- Modify: `apps/web/src/components/layout/Topbar.tsx`

- [ ] **Step 1: Create `MobileNav.tsx`** using shadcn `Sheet`, same `navItems` list as Sidebar. Trigger renders a `Menu` icon button. Visible only `<md`. Body lists nav items styled like Sidebar.

- [ ] **Step 2: Modify Topbar** to render `<MobileNav />` on the left side at `<md`, hidden `≥md`.

- [ ] **Step 3: Browser verify at 390×844** via `chrome-devtools-mcp`: hamburger appears, opens drawer, navigates to Settings, drawer closes.

- [ ] **Step 4: Commit**

```bash
git commit -am "fix(polish): mobile nav drawer for <md viewports"
```

POLISH.md entry resolved — strike through it.

---

## Task 2: `FileStorage` Protocol + StorageRef + LocalFsStorage — TDD

**Files:**
- Create: `apps/api/src/research_api/services/storage/base.py`
- Create: `apps/api/src/research_api/services/storage/local_fs.py`
- Create: `apps/api/src/research_api/services/storage/__init__.py`
- Create: `apps/api/tests/test_local_fs_storage.py`

- [ ] **Step 1: Write `tests/test_local_fs_storage.py`** asserting:
  - `save()` returns `StorageRef(backend="local", key="user-a/articles/<uuid>/paper.pdf")`
  - File lands at `<data_dir>/files/<key>`
  - `read()` returns same bytes
  - `delete()` removes the file
  - `save()` is **scoped by user_id** — different user, different prefix
  - Filenames are normalised (no path traversal): `save(filename="../../etc/passwd", ...)` strips traversal

- [ ] **Step 2: Run, expect collection failure.**

- [ ] **Step 3: Implement `base.py`** — `StorageRef` (frozen dataclass) + `FileStorage` Protocol with `save`, `read`, `delete`, `signed_url`.

- [ ] **Step 4: Implement `local_fs.py`** — `LocalFsStorage(root: Path)`. `save()` writes to `root/files/{user_id}/{namespace}/{uuid}/{safe_filename}`. `signed_url()` defers to `signed_urls.create_token(ref)`; constructs `/files/{token}`. Reject filenames containing `..` or `/` after `pathlib.Path(filename).name`.

- [ ] **Step 5: Tests pass.**

- [ ] **Step 6: Commit**

```bash
git commit -am "feat(phase2): FileStorage Protocol + LocalFsStorage with user-scoped paths and traversal protection"
```

---

## Task 3: Signed-URL HMAC tokens — TDD

**Files:**
- Create: `apps/api/src/research_api/services/storage/signed_urls.py`
- Create: `apps/api/tests/test_signed_urls.py`

- [ ] **Step 1: Write tests** for `create_token(ref, secret, ttl)` and `verify_token(token, secret)`:
  - Round-trip works
  - Expired token rejected
  - Tampered token rejected
  - Different secret rejected

- [ ] **Step 2: Implement** using HMAC-SHA256: `payload = base64url(json({backend, key, exp}))`, `sig = hmac(secret, payload)`, `token = payload + "." + sig`. Use `hmac.compare_digest`.

- [ ] **Step 3: Tests pass. Commit:**

```bash
git commit -am "feat(phase2): HMAC-signed short-TTL URL tokens for file access"
```

---

## Task 4: `AIProvider` Protocol + errors + CitationMetadata schema

**Files:**
- Create: `apps/api/src/research_api/services/ai/base.py`
- Create: `apps/api/src/research_api/services/ai/errors.py`
- Create: `apps/api/src/research_api/services/ai/schemas.py`
- Create: `apps/api/src/research_api/services/ai/__init__.py`

- [ ] **Step 1: `errors.py`** — `AIProviderUnavailable`, `AIRateLimited`, `AISafetyBlocked`, `AISourceInsufficient`. Each carries `provider` + `reason`.

- [ ] **Step 2: `schemas.py`** — `CitationMetadata` (Pydantic): title, authors (list[str]), journal, year, volume, issue, pages, doi, confidence (0.0–1.0). All fields optional except title.

- [ ] **Step 3: `base.py`** — `AIProvider(Protocol)` with the spec §4.1 methods. For Phase 2, only `extract_citation` and `summarise` are needed end-to-end; others land in later phases. Keep them in the Protocol so adapter shape is locked.

- [ ] **Step 4: `__init__.py`** exports.

- [ ] **Step 5: Compile check.** Commit:

```bash
git commit -am "feat(phase2): AIProvider Protocol + CitationMetadata schema + error taxonomy"
```

---

## Task 5: Generic model-resolution chain — TDD

**Files:**
- Create: `apps/api/src/research_api/services/ai/model_chain.py`
- Create: `apps/api/tests/test_model_chain.py`

- [ ] **Step 1: Tests** for `ModelChain`:
  - `resolve(available_models, chain)` returns first chain entry present in available
  - All chain entries missing → raises `AIProviderUnavailable("no model available")`
  - `with_active_demoted(reason)` returns new chain with current head dropped
  - When all demoted → next call raises `AIProviderUnavailable`

- [ ] **Step 2: Implement** as a small dataclass:

```python
@dataclass(frozen=True)
class ModelChain:
    chain: tuple[str, ...]
    active: str

    @classmethod
    def resolve(cls, available: set[str], chain: Sequence[str]) -> "ModelChain":
        for m in chain:
            if m in available:
                return cls(chain=tuple(chain), active=m)
        raise AIProviderUnavailable("no model available", provider="?")

    def demote(self) -> "ModelChain":
        remaining = tuple(m for m in self.chain if m != self.active)
        if not remaining:
            raise AIProviderUnavailable("chain exhausted", provider="?")
        return ModelChain(chain=remaining, active=remaining[0])
```

- [ ] **Step 3: Tests pass. Commit:**

```bash
git commit -am "feat(phase2): ModelChain — startup resolution + 404 demotion"
```

---

## Task 6: GeminiProvider implementation — TDD with fake SDK

**Files:**
- Create: `apps/api/src/research_api/services/ai/prompts/citation_extraction.py`
- Create: `apps/api/src/research_api/services/ai/prompts/__init__.py`
- Create: `apps/api/src/research_api/services/ai/gemini.py`
- Create: `apps/api/tests/test_gemini_provider.py`

- [ ] **Step 1: Prompt template** in `citation_extraction.py`:

```python
EXTRACTION_PROMPT = """You are extracting bibliographic metadata from a research article.

Return STRICT JSON with these fields (use null when unknown):
{
  "title": string,
  "authors": [string, ...],   // 'First Last' format
  "journal": string | null,
  "year": integer | null,
  "volume": string | null,
  "issue": string | null,
  "pages": string | null,
  "doi": string | null,
  "confidence": number          // 0.0-1.0 — your confidence that the title is correct
}

Rules:
- Use only the provided text. Do not invent.
- If the document is not a research article, return {"title": "UNKNOWN", "confidence": 0.0}.
- DOI format: '10.xxxx/...' — strip 'doi:' or 'https://doi.org/' prefixes.
- 'authors' MUST be a list, even if one.

ARTICLE TEXT (truncated to first ~6000 chars):
\"\"\"
{text}
\"\"\"

JSON:"""
```

- [ ] **Step 2: Tests** in `test_gemini_provider.py` — use a `FakeGeminiClient` injected into `GeminiProvider`:
  - Returns valid JSON → parsed `CitationMetadata`
  - Returns invalid JSON → `AIProviderUnavailable("parse failed")`
  - Returns 429 → retries 3× then raises `AIRateLimited`
  - Returns 503 → retries → succeeds on 2nd try
  - Returns 404 model not found → chain demotes, retries on next model, returns result
  - All models exhausted → raises `AIProviderUnavailable("chain exhausted")`

- [ ] **Step 3: Implement `GeminiProvider`** with:
  - `__init__(api_key, http_client=None)` — accepts optional injected client for tests
  - On boot, calls `list_models()` and resolves `GEMINI_MODEL_CHAIN = ("gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash-latest", "gemini-1.5-flash-002")` against availability via `ModelChain.resolve`
  - `extract_citation(pdf_bytes)`: uses `pdf_text.extract_first_pages_text(pdf_bytes, n=2)`, formats prompt, calls model with `safety_settings={cat: BLOCK_NONE}`, parses JSON, returns `CitationMetadata`
  - Tenacity `@retry` decorator: 3 attempts, exponential backoff 1s/2s/4s with jitter, retry only on `(429, 503, ConnectionError)`
  - On 404 → demote chain → retry once
  - `summarise(text, max_sentences=2)`: separate prompt template (defined inline in this method; can move later)

- [ ] **Step 4: Tests pass. Commit:**

```bash
git commit -am "feat(phase2): GeminiProvider with model chain, retry/demote, safety BLOCK_NONE for medical content"
```

---

## Task 7: PDF/Word text extraction service — TDD

**Files:**
- Create: `apps/api/src/research_api/services/pdf_text.py`
- Create: `apps/api/tests/test_pdf_text.py`
- Create: `apps/api/tests/fixtures/sample.pdf` (small real PDF)

- [ ] **Step 1: Generate a tiny sample PDF** for tests using pypdf or reportlab. Better: commit a 1-page real research PDF (any open-access paper, ~50KB).

If no PDF handy, write a script that uses pypdf to build one with known text. For Phase 2 testing, a 5-line PDF with `"Test Title", "John Doe", "Journal of Tests"` suffices.

- [ ] **Step 2: Tests** assert:
  - `extract_first_pages_text(pdf_bytes, n=2)` returns a string containing known fixture text
  - `extract_first_pages_text(docx_bytes, n=...)` for Word docs (use python-docx)
  - Auto-detect via `python-magic`: PDF → pypdf path, DOCX → python-docx path
  - Empty/corrupt input → returns "" (don't raise)

- [ ] **Step 3: Implement** `pdf_text.py`:

```python
def extract_first_pages_text(data: bytes, n: int = 2) -> str:
    mime = magic.from_buffer(data[:2048], mime=True)
    if mime == "application/pdf":
        return _from_pdf(data, n)
    if mime in ("application/vnd.openxmlformats-officedocument.wordprocessingml.document",):
        return _from_docx(data)
    return ""
```

- [ ] **Step 4: Tests pass. Commit:**

```bash
git commit -am "feat(phase2): pdf_text — extract first N pages from PDF or DOCX (MIME-sniffed)"
```

---

## Task 8: CrossRef DOI lookup service — TDD with httpx mock

**Files:**
- Create: `apps/api/src/research_api/services/crossref.py`
- Create: `apps/api/tests/test_crossref.py`

- [ ] **Step 1: Tests** with `httpx.MockTransport`:
  - Valid DOI → returns populated `CitationMetadata`
  - 404 → returns `None`
  - 5xx → returns `None` (degrades gracefully)
  - Malformed DOI → returns `None` without HTTP call

- [ ] **Step 2: Implement** `crossref.py` — `async def lookup_doi(doi: str, http_client=None) -> CitationMetadata | None`. Hits `https://api.crossref.org/works/{doi}`. Maps `message.author[].given + family`, `container-title[0]`, `published-print.date-parts[0][0]`, `volume`, `issue`, `page`, `DOI`. Sets `confidence=1.0` (authoritative source).

- [ ] **Step 3: Tests pass. Commit:**

```bash
git commit -am "feat(phase2): CrossRef DOI lookup as fallback for AI extraction"
```

---

## Task 9: Duplicate detection — TDD

**Files:**
- Create: `apps/api/src/research_api/services/dedupe.py`
- Create: `apps/api/tests/test_dedupe.py`

- [ ] **Step 1: Tests** asserting `score_match(candidate, existing)` returns 1.0 when DOIs match exactly, ≥0.9 when titles are 90% similar (normalised: lowercase, punctuation stripped), <0.5 for unrelated.

- [ ] **Step 2: Implement** using `rapidfuzz.fuzz.token_sort_ratio` (returns 0–100):

```python
def score_match(a: ArticleLike, b: ArticleLike) -> float:
    if a.doi and b.doi and a.doi.lower() == b.doi.lower():
        return 1.0
    if not a.title or not b.title:
        return 0.0
    return rapidfuzz.fuzz.token_sort_ratio(a.title.lower(), b.title.lower()) / 100.0
```

- [ ] **Step 3: Tests pass. Commit:**

```bash
git commit -am "feat(phase2): dedupe — DOI exact match or title fuzzy ratio >= 0.9"
```

---

## Task 10: Article model + Alembic migration

**Files:**
- Modify: `apps/api/src/research_api/db/models.py`
- Create: `apps/api/alembic/versions/0002_articles.py`

- [ ] **Step 1: Add `Article` ORM** to `models.py`. Fields per spec §5.2:
  - id (PK, uuid hex), user_id, project_id (FK, CASCADE)
  - title, authors (JSON list[str]), journal, year, volume, issue, pages, doi
  - file_ref (JSON `{backend, key}`), file_type
  - study_design, review_status (default 'pending'), exclusion_reason, conflict_of_interest
  - created_at

Index `(user_id, project_id)` and `doi`.

- [ ] **Step 2: Generate migration**

```bash
cd apps/api && .venv/bin/alembic revision --autogenerate -m "articles" --rev-id 0002
```

Inspect the generated file to ensure JSON columns + indexes look right.

- [ ] **Step 3: Apply**

```bash
.venv/bin/alembic upgrade head
```

Verify with `sqlite3 data/research.db ".tables"` — should include `articles`.

- [ ] **Step 4: Commit**

```bash
git commit -am "feat(phase2): Article model + alembic 0002 migration"
```

---

## Task 11: Article schemas (Pydantic)

**Files:**
- Create: `apps/api/src/research_api/schemas/article.py`
- Create: `apps/api/src/research_api/schemas/upload.py`
- Modify: `apps/api/src/research_api/schemas/__init__.py`

- [ ] **Step 1: `article.py`** — `ArticleCreate`, `ArticleUpdate`, `ArticleRead`. `file_ref` is `StorageRef`-shaped dict (`{backend: str, key: str}`). Authors is `list[str]`.

- [ ] **Step 2: `upload.py`** — `UploadResponse(article: ArticleRead, duplicate_of: ArticleRead | None, source: Literal["ai", "crossref", "both"])`.

- [ ] **Step 3: Compile check + commit:**

```bash
git commit -am "feat(phase2): pydantic schemas for Article + UploadResponse"
```

---

## Task 12: ArticleRepository — TDD

**Files:**
- Create: `apps/api/src/research_api/repositories/articles.py`
- Modify: `apps/api/src/research_api/repositories/__init__.py`
- Create: `apps/api/tests/test_article_repository.py`

- [ ] **Step 1: Tests** asserting:
  - `create(project_id, article_create, user_id)` persists with all fields
  - `get(article_id, user_id)` honours user scope (cross-user returns None)
  - `list_for_project(project_id, user_id, filters)` filters by `review_status`, `study_design`, free-text title search
  - `find_duplicate(doi, title, user_id)` returns existing article via DOI exact OR title ≥ 0.9 fuzz; returns None otherwise
  - `update`, `delete` scoped by user_id

- [ ] **Step 2: Implement** following the Phase 1 `SqliteProjectRepository` pattern. `find_duplicate` queries by DOI first (fast index), then falls back to a Python-side fuzz scan over user's articles in same project (acceptable for v1 scale).

- [ ] **Step 3: Tests pass. Commit:**

```bash
git commit -am "feat(phase2): ArticleRepository TDD — list filters + duplicate detection + user isolation"
```

---

## Task 13: Container wiring for storage + AI + settings additions

**Files:**
- Modify: `apps/api/src/research_api/settings.py`
- Modify: `apps/api/src/research_api/container.py`

- [ ] **Step 1: Settings additions:**
  - `file_size_cap_mb: int = 50`
  - `ai_timeout_s: int = 60`
  - `allowed_upload_mime: list[str] = ["application/pdf", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"]`

- [ ] **Step 2: Container changes** — add `storage: FileStorage` and `ai: AIProvider` fields. `build_container` constructs `LocalFsStorage(root=settings.data_dir)` and `GeminiProvider(api_key=settings.gemini_api_key)` when key present; otherwise an `UnconfiguredAI` stub that raises `AIProviderUnavailable("no key")`.

- [ ] **Step 3: Update `/health` route** to call `container.ai.list_active_models()` (a new method on `AIProvider` returning `dict[str, str | None]`) for the real status. Keep the Phase 1 fallback when no AI is configured.

- [ ] **Step 4: Full test sweep stays green. Commit:**

```bash
git commit -am "feat(phase2): wire FileStorage + AIProvider into Container; /health calls real provider"
```

---

## Task 14: Signed-URL file serving route — TDD

**Files:**
- Create: `apps/api/src/research_api/routes/files.py`
- Create: `apps/api/tests/test_files_route.py`

- [ ] **Step 1: Tests:**
  - `GET /files/{token}` with valid token returns 200 + bytes + correct content-type
  - Expired token → 410 Gone
  - Tampered token → 403
  - Missing file (token valid but file deleted) → 404

- [ ] **Step 2: Implement route** — verify token via `signed_urls.verify_token`, fetch ref, `storage.read(ref)`, sniff MIME, return `Response(content=..., media_type=...)`.

- [ ] **Step 3: Wire** into `main.py` router includes.

- [ ] **Step 4: Tests pass. Commit:**

```bash
git commit -am "feat(phase2): /files/{token} — HMAC-verified file serving"
```

---

## Task 15: `/api/articles` routes — TDD

**Files:**
- Create: `apps/api/src/research_api/routes/articles.py`
- Create: `apps/api/tests/test_articles_route.py`

Endpoints:
- `POST /api/projects/{project_id}/articles/upload` (multipart `file`) — saves, extracts, dedup-checks, returns `UploadResponse`
- `GET /api/projects/{project_id}/articles` — supports query params `q`, `review_status`, `study_design`, `sort` (`year|title|created`)
- `GET /api/articles/{id}` — single article
- `PATCH /api/articles/{id}` — partial update (title, authors, review_status, study_design, exclusion_reason, COI, etc.)
- `DELETE /api/articles/{id}` — soft? No — hard delete; also delete file via storage.

- [ ] **Step 1: Tests** using fixtures with a fake AI that returns a known `CitationMetadata`. Verify:
  - Upload returns 201 with metadata extracted
  - Duplicate upload returns `duplicate_of` populated
  - Invalid MIME → 415
  - File over 50 MB → 413
  - Path-traversal filename normalised
  - List supports search/filter/sort
  - Cross-user access blocked

- [ ] **Step 2: Implement** — orchestrate: `_validate_upload` → `storage.save` → `pdf_text.extract` → `ai.extract_citation` (catch errors, fall through to CrossRef if DOI present) → `crossref.lookup_doi` if needed → merge metadata (CrossRef wins on overlap) → `repo.find_duplicate` → `repo.create` → return `UploadResponse`.

- [ ] **Step 3: Tests pass. Full sweep. Commit:**

```bash
git commit -am "feat(phase2): /api/articles routes — upload+extract pipeline, list with filters, CRUD, dedup"
```

---

## Task 16: Frontend API client — Article endpoints

**Files:**
- Modify: `apps/web/src/lib/api.ts`

- [ ] **Step 1: Add to api.ts:**
  - `ArticleSchema`, `ArticleCreateSchema`, `UploadResponseSchema`
  - `articlesApi.list(projectId, filters)`, `articlesApi.upload(projectId, file)`, `articlesApi.get(id)`, `articlesApi.update(id, patch)`, `articlesApi.delete(id)`
  - File URL helper: `articleFileUrl(article) → /files/{token}` (token returned by upload + list as part of `file_ref`, so backend should return signed URLs in responses — adjust backend if needed; **decision:** return `file_url` field via a `before_response` hook on routes)

- [ ] **Step 2: Typecheck. Commit:**

```bash
git commit -am "feat(phase2): frontend API client — articlesApi (list/upload/get/update/delete)"
```

---

## Task 17: Active project store (Zustand)

**Files:**
- Create: `apps/web/src/lib/projectContext.ts`

- [ ] **Step 1: Implement** a Zustand store `useActiveProject` with `{ projectId: string | null, set: (id) => void }`. Persist to localStorage under `research-active-project`.

- [ ] **Step 2: Modify `ProjectCard.tsx`** to be a `<button>` that calls `set(project.id)` then navigates to `/library`.

- [ ] **Step 3: Modify `LibraryPage.tsx`** to read `useActiveProject` — if null, render `<ProjectSelectGate />` (a friendly "Pick a project first" with a button to go to Dashboard).

- [ ] **Step 4: Commit:**

```bash
git commit -am "feat(phase2): active-project Zustand store + ProjectCard navigation"
```

---

## Task 18: `UploadZone` component

**Files:**
- Create: `apps/web/src/components/library/UploadZone.tsx`

- [ ] **Step 1: Implement** with `react-dropzone`. Accept `.pdf, .docx`. On drop, mutate via `articlesApi.upload`. Show:
  - Idle state: large dashed border, "Drop PDFs or Word docs here, or click to choose" — Lucide `UploadCloud` icon
  - Drag-over: accent ring + scale-up via Framer
  - Uploading: per-file row with progress + spinner (Framer)
  - Result: success card with article title or duplicate warning
  - Multiple files supported, processed sequentially (avoid Gemini rate limit)

- [ ] **Step 2: On success**, invalidate `['articles', projectId]` query.

- [ ] **Step 3: Browser verify with a real PDF.** Commit:

```bash
git commit -am "feat(phase2): UploadZone — drag-and-drop + click-to-upload with progress and dup detection"
```

---

## Task 19: `MetadataConfirmDialog`

**Files:**
- Create: `apps/web/src/components/library/MetadataConfirmDialog.tsx`

- [ ] **Step 1: Implement** as a shadcn Dialog. Opens after upload returns. Pre-filled form (RHF + zod): title, authors (comma-separated input → array), journal, year, volume, issue, pages, DOI, study_design (select), confidence shown as a small `<Badge>`. Buttons: "Looks right — save" (calls update via PATCH) / "Edit later".

- [ ] **Step 2: Wire into UploadZone**: after each successful upload, open dialog for that article. Stack dialogs sequentially when multiple files are uploaded.

- [ ] **Step 3: Commit:**

```bash
git commit -am "feat(phase2): MetadataConfirmDialog — review/edit AI-extracted citation before save"
```

---

## Task 20: `ArticleFilters` + `ArticleListItem` + `LibraryPage`

**Files:**
- Create: `apps/web/src/components/library/ArticleFilters.tsx`
- Create: `apps/web/src/components/library/ArticleListItem.tsx`
- Modify: `apps/web/src/routes/LibraryPage.tsx` (full implementation, replace Phase 1 stub)

- [ ] **Step 1: `ArticleFilters`** — search input (debounced 250 ms), Select for `review_status`, Select for `study_design`, Select for sort. Mounted at top of page.

- [ ] **Step 2: `ArticleListItem`** — full row: title (bold), authors (truncated), journal · year · doi, badges (review status, study design colour-coded). Hover: subtle elevation. Click: opens detail drawer (Phase 2 omits detail editor; click handler stubbed for now — POLISH log).

- [ ] **Step 3: `LibraryPage`** — composition:
  - If no active project → `ProjectSelectGate`
  - Else: `<header>` with project title + count → `<UploadZone>` → `<ArticleFilters>` → list (virtualised optional, plain map for v1)
  - Empty state when project has no articles

- [ ] **Step 4: Typecheck. Commit:**

```bash
git commit -am "feat(phase2): LibraryPage — gate, upload zone, filters, article list"
```

---

## Task 21: Sidebar Library route now lights up — visual polish pass

**Files:**
- Modify: `apps/web/src/components/projects/ProjectCard.tsx` (visual hint that clicking goes to library)

- [ ] **Step 1: Add a small "Open library →" affordance** on hover in `ProjectCard`.

- [ ] **Step 2: Verify the active-bar Framer animation still works** when navigating via card click.

- [ ] **Step 3: Commit:**

```bash
git commit -am "polish(phase2): ProjectCard hover affordance + sidebar transition verify"
```

---

## Task 22: End-to-end browser verification

- [ ] **Step 1: Boot both servers** (`npm run dev`).

- [ ] **Step 2: Drive Chrome via MCP** through the full flow:
  1. Create a new project ("Phase 2 verification") on Dashboard
  2. Click the project card → lands on Library with empty state
  3. Drop a real PDF onto UploadZone (use a known test PDF, e.g. an arXiv paper)
  4. Wait for metadata confirm dialog → verify fields populated → click "Looks right"
  5. Article appears in list with extracted metadata
  6. Drop the same PDF again → see duplicate warning
  7. Search → filter by review_status → results narrow
  8. Reload page → article persists
  9. Visit Settings → Gemini still configured + active model populated (was null in Phase 1)

- [ ] **Step 3: Screenshot at each step + a11y audit pass.**

- [ ] **Step 4: Run `/security-review` on the upload pipeline** (per spec — file upload + AI integration both warrant it).

- [ ] **Step 5: Update BUILD_LOG.md + POLISH.md** with what shipped and any leftover nits.

- [ ] **Step 6: Tag**

```bash
git tag -a phase-2 -m "Phase 2 — Library module complete"
```

---

## Acceptance check (from spec §7 Phase 2)

- [ ] Drag-and-drop PDF + Word → extraction within ~10s → user confirms → article in list
- [ ] Same PDF re-uploaded → duplicate warning shown
- [ ] Search by author finds the article
- [ ] All 14 Phase 1 tests still pass + ~30 new tests pass
- [ ] `/health` now shows live active Gemini model (e.g. `gemini-2.5-flash`)
- [ ] `/security-review` passes (no path traversal, MIME validated, size capped, signed URLs HMAC'd)

---

## Self-Review

**Spec coverage (spec §7 Phase 2):**
- File upload PDF + .docx ✅ Task 18
- AI citation extraction ✅ Task 6 + 15
- CrossRef fallback ✅ Task 8 + 15
- Metadata confirmation ✅ Task 19
- Library list sortable/searchable/filterable ✅ Task 20
- Duplicate detection ✅ Task 9 + 12 + 15
- Per-article fields (study design, review status, exclusion reason, COI) ✅ Task 11 schema + 19 dialog allows editing of study_design; COI/exclusion editing covered by PATCH route. Detail editor for COI/exclusion deferred to a polish task in Phase 7 (systematic review module uses these heavily).

**Spec §6.2 (AI robustness):** model chain ✅ Task 5, retry/demote ✅ Task 6, safety BLOCK_NONE ✅ Task 6, /health reflects active model ✅ Task 13.

**POLISH carry-over:** mobile nav ✅ Task 1.

**Placeholder scan:** ✅ no TBDs/TODOs/"handle edge cases".

**Type consistency:** `CitationMetadata` defined Task 4, reused Tasks 6, 8, 15. `StorageRef` Task 2, used in Task 11 schemas, Task 14 routes. `ModelChain` Task 5, used in Task 6.

**Self-check ok. Proceeding to execution.**
