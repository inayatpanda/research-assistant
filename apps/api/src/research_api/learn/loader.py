"""Phase 5a + 5b — Learn hub loader.

Walks Markdown files under ``learn/<category>/*.md``, parses YAML
frontmatter + Markdown body, validates each entry against a Pydantic
schema, and exposes an in-memory index keyed by ``(category, slug)``.

Phase 5b generalised the loader to support four categories; Phase 5c
adds a fifth (``walkthroughs``):

* ``stat_tests``   — original 27 statistical-test references.
* ``checklists``   — reporting-guideline checklists (CONSORT etc.).
* ``economics``    — health-economics concept reference.
* ``submission``   — manuscript-submission how-to topics.
* ``walkthroughs`` — long-form, end-to-end study workflow narratives.

Each category declares its own frontmatter schema (subclass of
``_BaseFrontmatter``) and its own immutable entry dataclass. The
public surface is two helpers:

* :func:`load_category` — return every parsed entry for ``category``.
* :func:`get_entry`     — fetch one entry by ``(category, slug)``.

Category-specific shortcuts (``load_all_stat_tests``, ``list_stat_tests``,
``get_stat_test``) are preserved for backwards-compat with Phase 5a
tests and route handlers.

The loader has zero new third-party deps: it parses frontmatter with a
tiny inline scanner (no ``python-frontmatter``) and validates with
Pydantic v2 (already pinned). Markdown body is returned as raw text —
the frontend renders it.

CLI: ``python -m research_api.learn.loader --count`` prints the entry
count per category. Useful as a smoke check.
"""
from __future__ import annotations

import argparse
import logging
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field, ValidationError, field_validator

logger = logging.getLogger("research_api.learn.loader")

_LEARN_ROOT = Path(__file__).resolve().parent
STAT_TESTS_DIR = _LEARN_ROOT / "stat_tests"
CHECKLISTS_DIR = _LEARN_ROOT / "checklists"
ECONOMICS_DIR = _LEARN_ROOT / "economics"
SUBMISSION_DIR = _LEARN_ROOT / "submission"
WALKTHROUGHS_DIR = _LEARN_ROOT / "walkthroughs"

_CATEGORY_DIRS: dict[str, Path] = {
    "stat_tests": STAT_TESTS_DIR,
    "checklists": CHECKLISTS_DIR,
    "economics": ECONOMICS_DIR,
    "submission": SUBMISSION_DIR,
    "walkthroughs": WALKTHROUGHS_DIR,
}

_FRONTMATTER_RE = re.compile(
    r"^---\s*\n(?P<fm>.*?)\n---\s*\n(?P<body>.*)$",
    re.DOTALL,
)

# Acceptable values for `worked_example_domain`. Keep tight so the test
# suite can guarantee the ortho/medicine/surgery split.
_ALLOWED_DOMAINS = {"orthopaedics", "medicine", "surgery"}


# ---------------------------------------------------------------------------
# Frontmatter schemas
# ---------------------------------------------------------------------------


class _BaseFrontmatter(BaseModel):
    """Common keys that every Learn entry must declare."""

    slug: str = Field(..., min_length=1, max_length=80)
    title: str = Field(..., min_length=1)
    worked_example_domain: str
    related_concepts: list[str] = Field(default_factory=list)

    @field_validator("slug")
    @classmethod
    def _slug_kebab(cls, v: str) -> str:
        if not re.match(r"^[a-z0-9]+(?:-[a-z0-9]+)*$", v):
            raise ValueError(
                f"slug {v!r} must be lower-kebab-case (a-z, 0-9, dashes)"
            )
        return v

    @field_validator("worked_example_domain")
    @classmethod
    def _domain_known(cls, v: str) -> str:
        if v not in _ALLOWED_DOMAINS:
            raise ValueError(
                f"worked_example_domain {v!r} not in {sorted(_ALLOWED_DOMAINS)}"
            )
        return v


class StatTestFrontmatter(_BaseFrontmatter):
    family: str = Field(..., min_length=1)
    when_to_use: str = Field(..., min_length=1)
    assumptions: list[str] = Field(default_factory=list)
    alternatives: list[str] = Field(default_factory=list)
    worked_example_dataset: str = Field(..., min_length=1)


class ChecklistFrontmatter(_BaseFrontmatter):
    reporting_standard: str = Field(..., min_length=1)
    applies_to_study_types: list[str] = Field(default_factory=list)
    version: str = Field(..., min_length=1)
    official_url: str = Field(..., min_length=1)


class EconomicsFrontmatter(_BaseFrontmatter):
    concept_family: str = Field(..., min_length=1)
    formula: str = ""
    units: str = ""


class SubmissionFrontmatter(_BaseFrontmatter):
    topic: str = Field(..., min_length=1)
    topic_family: str = Field(..., min_length=1)


class WalkthroughFrontmatter(_BaseFrontmatter):
    """Phase 5c — long-form walkthrough narratives."""

    estimated_reading_minutes: int = Field(..., ge=1, le=120)
    study_type: str = Field(..., min_length=1)
    sections: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Entry dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class StatTestEntry:
    """A parsed stat-test reference entry."""

    slug: str
    title: str
    family: str
    when_to_use: str
    assumptions: tuple[str, ...]
    alternatives: tuple[str, ...]
    worked_example_domain: str
    worked_example_dataset: str
    related_concepts: tuple[str, ...]
    body_md: str

    @property
    def short_blurb(self) -> str:
        s = self.when_to_use.strip()
        if len(s) > 180:
            cut = s[:180]
            tail = cut.rfind(" ")
            return (cut[:tail] if tail > 80 else cut) + "…"
        return s

    def to_summary(self) -> "StatTestSummary":
        return StatTestSummary(
            slug=self.slug,
            title=self.title,
            family=self.family,
            short_blurb=self.short_blurb,
            worked_example_domain=self.worked_example_domain,
        )


@dataclass(frozen=True)
class ChecklistEntry:
    slug: str
    title: str
    reporting_standard: str
    applies_to_study_types: tuple[str, ...]
    version: str
    official_url: str
    worked_example_domain: str
    related_concepts: tuple[str, ...]
    body_md: str

    @property
    def short_blurb(self) -> str:
        # First sentence of the body that isn't a heading.
        for line in self.body_md.splitlines():
            stripped = line.strip()
            if stripped and not stripped.startswith("#"):
                return stripped[:200]
        return f"{self.reporting_standard} reporting checklist."

    def to_summary(self) -> "ChecklistSummary":
        return ChecklistSummary(
            slug=self.slug,
            title=self.title,
            reporting_standard=self.reporting_standard,
            applies_to_study_types=list(self.applies_to_study_types),
            version=self.version,
            short_blurb=self.short_blurb,
            worked_example_domain=self.worked_example_domain,
        )


@dataclass(frozen=True)
class EconomicsEntry:
    slug: str
    title: str
    concept_family: str
    formula: str
    units: str
    worked_example_domain: str
    related_concepts: tuple[str, ...]
    body_md: str

    @property
    def short_blurb(self) -> str:
        for line in self.body_md.splitlines():
            stripped = line.strip()
            if stripped and not stripped.startswith("#"):
                return stripped[:200]
        return f"{self.title} ({self.concept_family})."

    def to_summary(self) -> "EconomicsSummary":
        return EconomicsSummary(
            slug=self.slug,
            title=self.title,
            concept_family=self.concept_family,
            formula=self.formula,
            units=self.units,
            short_blurb=self.short_blurb,
            worked_example_domain=self.worked_example_domain,
        )


@dataclass(frozen=True)
class SubmissionEntry:
    slug: str
    title: str
    topic: str
    topic_family: str
    worked_example_domain: str
    related_concepts: tuple[str, ...]
    body_md: str

    @property
    def short_blurb(self) -> str:
        for line in self.body_md.splitlines():
            stripped = line.strip()
            if stripped and not stripped.startswith("#"):
                return stripped[:200]
        return f"{self.title}."

    def to_summary(self) -> "SubmissionSummary":
        return SubmissionSummary(
            slug=self.slug,
            title=self.title,
            topic=self.topic,
            topic_family=self.topic_family,
            short_blurb=self.short_blurb,
            worked_example_domain=self.worked_example_domain,
        )


@dataclass(frozen=True)
class WalkthroughEntry:
    slug: str
    title: str
    study_type: str
    estimated_reading_minutes: int
    sections: tuple[str, ...]
    worked_example_domain: str
    related_concepts: tuple[str, ...]
    body_md: str

    @property
    def short_blurb(self) -> str:
        for line in self.body_md.splitlines():
            stripped = line.strip()
            if stripped and not stripped.startswith("#"):
                return stripped[:200]
        return f"{self.title}."

    def to_summary(self) -> "WalkthroughSummary":
        return WalkthroughSummary(
            slug=self.slug,
            title=self.title,
            study_type=self.study_type,
            estimated_reading_minutes=self.estimated_reading_minutes,
            sections=list(self.sections),
            short_blurb=self.short_blurb,
            worked_example_domain=self.worked_example_domain,
        )


LearnEntry = (
    StatTestEntry
    | ChecklistEntry
    | EconomicsEntry
    | SubmissionEntry
    | WalkthroughEntry
)


# ---------------------------------------------------------------------------
# Pydantic read/summary models (HTTP layer)
# ---------------------------------------------------------------------------


class StatTestSummary(BaseModel):
    slug: str
    title: str
    family: str
    short_blurb: str
    worked_example_domain: str


class StatTestRead(BaseModel):
    slug: str
    title: str
    family: str
    when_to_use: str
    assumptions: list[str]
    alternatives: list[str]
    worked_example_domain: str
    worked_example_dataset: str
    related_concepts: list[str]
    body_md: str


class ChecklistSummary(BaseModel):
    slug: str
    title: str
    reporting_standard: str
    applies_to_study_types: list[str]
    version: str
    short_blurb: str
    worked_example_domain: str


class ChecklistRead(BaseModel):
    slug: str
    title: str
    reporting_standard: str
    applies_to_study_types: list[str]
    version: str
    official_url: str
    worked_example_domain: str
    related_concepts: list[str]
    body_md: str


class EconomicsSummary(BaseModel):
    slug: str
    title: str
    concept_family: str
    formula: str
    units: str
    short_blurb: str
    worked_example_domain: str


class EconomicsRead(BaseModel):
    slug: str
    title: str
    concept_family: str
    formula: str
    units: str
    worked_example_domain: str
    related_concepts: list[str]
    body_md: str


class SubmissionSummary(BaseModel):
    slug: str
    title: str
    topic: str
    topic_family: str
    short_blurb: str
    worked_example_domain: str


class SubmissionRead(BaseModel):
    slug: str
    title: str
    topic: str
    topic_family: str
    worked_example_domain: str
    related_concepts: list[str]
    body_md: str


class WalkthroughSummary(BaseModel):
    slug: str
    title: str
    study_type: str
    estimated_reading_minutes: int
    sections: list[str]
    short_blurb: str
    worked_example_domain: str


class WalkthroughRead(BaseModel):
    slug: str
    title: str
    study_type: str
    estimated_reading_minutes: int
    sections: list[str]
    worked_example_domain: str
    related_concepts: list[str]
    body_md: str


class LearnSearchHit(BaseModel):
    """A single cross-category search result."""

    category: str
    slug: str
    title: str
    snippet: str


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------


class LearnParseError(RuntimeError):
    """Raised when a Markdown file has malformed frontmatter or body."""


def _read_frontmatter(path: Path) -> tuple[dict[str, Any], str]:
    raw = path.read_text(encoding="utf-8")
    m = _FRONTMATTER_RE.match(raw)
    if not m:
        raise LearnParseError(f"{path.name}: missing/invalid YAML frontmatter")
    try:
        fm_dict: Any = yaml.safe_load(m.group("fm")) or {}
    except yaml.YAMLError as exc:
        raise LearnParseError(f"{path.name}: bad YAML — {exc}") from exc
    if not isinstance(fm_dict, dict):
        raise LearnParseError(f"{path.name}: frontmatter must be a mapping")
    body = m.group("body").strip()
    if not body:
        raise LearnParseError(f"{path.name}: empty body")
    return fm_dict, body


def _expect_filename_matches_slug(path: Path, slug: str) -> None:
    expected = f"{slug}.md"
    if path.name != expected:
        raise LearnParseError(
            f"{path.name}: slug {slug!r} expects filename {expected!r}"
        )


def _parse_stat_test(path: Path) -> StatTestEntry:
    fm_dict, body = _read_frontmatter(path)
    try:
        fm = StatTestFrontmatter.model_validate(fm_dict)
    except ValidationError as exc:
        raise LearnParseError(f"{path.name}: frontmatter validation — {exc}") from exc
    _expect_filename_matches_slug(path, fm.slug)
    return StatTestEntry(
        slug=fm.slug,
        title=fm.title,
        family=fm.family,
        when_to_use=fm.when_to_use,
        assumptions=tuple(fm.assumptions),
        alternatives=tuple(fm.alternatives),
        worked_example_domain=fm.worked_example_domain,
        worked_example_dataset=fm.worked_example_dataset,
        related_concepts=tuple(fm.related_concepts),
        body_md=body,
    )


def _parse_checklist(path: Path) -> ChecklistEntry:
    fm_dict, body = _read_frontmatter(path)
    try:
        fm = ChecklistFrontmatter.model_validate(fm_dict)
    except ValidationError as exc:
        raise LearnParseError(f"{path.name}: frontmatter validation — {exc}") from exc
    _expect_filename_matches_slug(path, fm.slug)
    return ChecklistEntry(
        slug=fm.slug,
        title=fm.title,
        reporting_standard=fm.reporting_standard,
        applies_to_study_types=tuple(fm.applies_to_study_types),
        version=fm.version,
        official_url=fm.official_url,
        worked_example_domain=fm.worked_example_domain,
        related_concepts=tuple(fm.related_concepts),
        body_md=body,
    )


def _parse_economics(path: Path) -> EconomicsEntry:
    fm_dict, body = _read_frontmatter(path)
    try:
        fm = EconomicsFrontmatter.model_validate(fm_dict)
    except ValidationError as exc:
        raise LearnParseError(f"{path.name}: frontmatter validation — {exc}") from exc
    _expect_filename_matches_slug(path, fm.slug)
    return EconomicsEntry(
        slug=fm.slug,
        title=fm.title,
        concept_family=fm.concept_family,
        formula=fm.formula,
        units=fm.units,
        worked_example_domain=fm.worked_example_domain,
        related_concepts=tuple(fm.related_concepts),
        body_md=body,
    )


def _parse_submission(path: Path) -> SubmissionEntry:
    fm_dict, body = _read_frontmatter(path)
    try:
        fm = SubmissionFrontmatter.model_validate(fm_dict)
    except ValidationError as exc:
        raise LearnParseError(f"{path.name}: frontmatter validation — {exc}") from exc
    _expect_filename_matches_slug(path, fm.slug)
    return SubmissionEntry(
        slug=fm.slug,
        title=fm.title,
        topic=fm.topic,
        topic_family=fm.topic_family,
        worked_example_domain=fm.worked_example_domain,
        related_concepts=tuple(fm.related_concepts),
        body_md=body,
    )


def _parse_walkthrough(path: Path) -> WalkthroughEntry:
    fm_dict, body = _read_frontmatter(path)
    try:
        fm = WalkthroughFrontmatter.model_validate(fm_dict)
    except ValidationError as exc:
        raise LearnParseError(f"{path.name}: frontmatter validation — {exc}") from exc
    _expect_filename_matches_slug(path, fm.slug)
    return WalkthroughEntry(
        slug=fm.slug,
        title=fm.title,
        study_type=fm.study_type,
        estimated_reading_minutes=fm.estimated_reading_minutes,
        sections=tuple(fm.sections),
        worked_example_domain=fm.worked_example_domain,
        related_concepts=tuple(fm.related_concepts),
        body_md=body,
    )


_PARSERS = {
    "stat_tests": _parse_stat_test,
    "checklists": _parse_checklist,
    "economics": _parse_economics,
    "submission": _parse_submission,
    "walkthroughs": _parse_walkthrough,
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


@lru_cache(maxsize=8)
def load_category(category: str) -> tuple[LearnEntry, ...]:
    """Scan + parse every Markdown file in ``learn/<category>/``.

    Cached at module level. Duplicate slugs raise :class:`LearnParseError`.
    Unknown categories raise :class:`ValueError`.
    """
    if category not in _CATEGORY_DIRS:
        raise ValueError(f"unknown learn category: {category!r}")
    directory = _CATEGORY_DIRS[category]
    if not directory.exists():
        logger.warning("learn: %s dir missing at %s", category, directory)
        return ()
    parse = _PARSERS[category]
    entries: list[LearnEntry] = []
    seen: dict[str, Path] = {}
    for md_path in sorted(directory.glob("*.md")):
        entry = parse(md_path)
        if entry.slug in seen:
            raise LearnParseError(
                f"duplicate slug {entry.slug!r}: {md_path.name} and {seen[entry.slug].name}"
            )
        seen[entry.slug] = md_path
        entries.append(entry)
    return tuple(entries)


def get_entry(category: str, slug: str) -> LearnEntry | None:
    for e in load_category(category):
        if e.slug == slug:
            return e
    return None


def _reset_cache() -> None:
    """Test hook — drop the lru_cache so a fresh scan runs on next call."""
    load_category.cache_clear()


# --- Phase 5a back-compat shortcuts (stat-tests) ---


def load_all_stat_tests() -> tuple[StatTestEntry, ...]:
    return load_category("stat_tests")  # type: ignore[return-value]


def list_stat_tests() -> list[StatTestSummary]:
    return [e.to_summary() for e in load_all_stat_tests()]


def get_stat_test(slug: str) -> StatTestEntry | None:
    e = get_entry("stat_tests", slug)
    return e if isinstance(e, StatTestEntry) else None


# --- Phase 5b shortcuts ---


def load_all_checklists() -> tuple[ChecklistEntry, ...]:
    return load_category("checklists")  # type: ignore[return-value]


def list_checklists() -> list[ChecklistSummary]:
    return [e.to_summary() for e in load_all_checklists()]


def get_checklist(slug: str) -> ChecklistEntry | None:
    e = get_entry("checklists", slug)
    return e if isinstance(e, ChecklistEntry) else None


def load_all_economics() -> tuple[EconomicsEntry, ...]:
    return load_category("economics")  # type: ignore[return-value]


def list_economics() -> list[EconomicsSummary]:
    return [e.to_summary() for e in load_all_economics()]


def get_economics(slug: str) -> EconomicsEntry | None:
    e = get_entry("economics", slug)
    return e if isinstance(e, EconomicsEntry) else None


def load_all_submission() -> tuple[SubmissionEntry, ...]:
    return load_category("submission")  # type: ignore[return-value]


def list_submission() -> list[SubmissionSummary]:
    return [e.to_summary() for e in load_all_submission()]


def get_submission(slug: str) -> SubmissionEntry | None:
    e = get_entry("submission", slug)
    return e if isinstance(e, SubmissionEntry) else None


# --- Phase 5c shortcuts ---


def load_all_walkthroughs() -> tuple[WalkthroughEntry, ...]:
    return load_category("walkthroughs")  # type: ignore[return-value]


def list_walkthroughs() -> list[WalkthroughSummary]:
    return [e.to_summary() for e in load_all_walkthroughs()]


def get_walkthrough(slug: str) -> WalkthroughEntry | None:
    e = get_entry("walkthroughs", slug)
    return e if isinstance(e, WalkthroughEntry) else None


# --- Cross-category search ---


def search_all(query: str, *, limit: int = 30) -> list[LearnSearchHit]:
    """Naive substring search across every category. Case-insensitive."""
    q = query.strip().lower()
    if not q:
        return []
    hits: list[LearnSearchHit] = []
    for category in _CATEGORY_DIRS:
        try:
            entries = load_category(category)
        except LearnParseError:
            continue
        for entry in entries:
            hay = " ".join(
                [
                    entry.title.lower(),
                    entry.slug.lower(),
                    entry.body_md.lower(),
                ]
            )
            if q in hay:
                body_lc = entry.body_md.lower()
                idx = body_lc.find(q)
                if idx == -1:
                    snippet = entry.body_md[:160].replace("\n", " ").strip()
                else:
                    start = max(0, idx - 60)
                    end = min(len(entry.body_md), idx + 100)
                    snippet = entry.body_md[start:end].replace("\n", " ").strip()
                hits.append(
                    LearnSearchHit(
                        category=category,
                        slug=entry.slug,
                        title=entry.title,
                        snippet=snippet,
                    )
                )
                if len(hits) >= limit:
                    return hits
    return hits


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _main() -> int:
    parser = argparse.ArgumentParser(description="Learn hub loader")
    parser.add_argument("--count", action="store_true", help="print entry count per category")
    parser.add_argument("--list", action="store_true", help="print slugs per category")
    parser.add_argument(
        "--category",
        choices=tuple(_CATEGORY_DIRS),
        help="restrict --count/--list to one category",
    )
    args = parser.parse_args()

    cats = (args.category,) if args.category else tuple(_CATEGORY_DIRS)

    if args.count:
        for cat in cats:
            try:
                entries = load_category(cat)
            except LearnParseError as exc:
                print(f"{cat}: ERROR {exc}")
                return 1
            print(f"{cat}\t{len(entries)}")
        return 0

    if args.list:
        for cat in cats:
            try:
                entries = load_category(cat)
            except LearnParseError as exc:
                print(f"{cat}: ERROR {exc}")
                return 1
            for e in entries:
                print(f"{cat}\t{e.slug}\t{e.title}")
        return 0

    parser.print_help()
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entry
    raise SystemExit(_main())
