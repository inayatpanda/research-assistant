"""Phase 5a — Learn hub loader.

Walks ``learn/stat_tests/*.md``, parses YAML frontmatter + Markdown body,
validates each entry against a Pydantic schema, and exposes an in-memory
index keyed by slug.

The loader has zero new third-party deps: it parses frontmatter with a tiny
inline scanner (no ``python-frontmatter``) and validates with Pydantic v2
(already pinned). Markdown body is returned as raw text — the frontend
renders it. Keeping rendering client-side avoids pulling ``markdown-it-py``
into the API.

Module-load behaviour: ``load_all_stat_tests()`` is invoked lazily the
first time the index is requested. Tests that mutate the on-disk catalogue
can call ``_reset_cache()`` to force a re-scan.

CLI: ``python -m research_api.learn.loader --count`` prints the number of
entries. Useful as a Phase 5a smoke check.
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

STAT_TESTS_DIR = Path(__file__).resolve().parent / "stat_tests"

_FRONTMATTER_RE = re.compile(
    r"^---\s*\n(?P<fm>.*?)\n---\s*\n(?P<body>.*)$",
    re.DOTALL,
)

# Acceptable values for `worked_example_domain`. Keep tight so the test
# suite can guarantee the ~9/9/9 ortho/med/surg split.
_ALLOWED_DOMAINS = {"orthopaedics", "medicine", "surgery"}


class StatTestFrontmatter(BaseModel):
    """Validated frontmatter for one stat-test entry."""

    slug: str = Field(..., min_length=1, max_length=80)
    title: str = Field(..., min_length=1)
    family: str = Field(..., min_length=1)
    when_to_use: str = Field(..., min_length=1)
    assumptions: list[str] = Field(default_factory=list)
    alternatives: list[str] = Field(default_factory=list)
    worked_example_domain: str
    worked_example_dataset: str = Field(..., min_length=1)
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


@dataclass(frozen=True)
class StatTestEntry:
    """A parsed stat-test reference entry.

    ``body_md`` is the raw Markdown (no frontmatter). ``short_blurb`` is
    the first sentence of ``when_to_use`` — small enough for list views.
    """

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
        # Use ``when_to_use`` as the snippet — already curated copy.
        s = self.when_to_use.strip()
        # Truncate to first sentence-ish boundary for very long blurbs.
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


class StatTestSummary(BaseModel):
    """List-view payload (no body)."""

    slug: str
    title: str
    family: str
    short_blurb: str
    worked_example_domain: str


class StatTestRead(BaseModel):
    """Detail-view payload."""

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


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------


class LearnParseError(RuntimeError):
    """Raised when a Markdown file has malformed frontmatter or body."""


def _parse_one(path: Path) -> StatTestEntry:
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

    try:
        fm = StatTestFrontmatter.model_validate(fm_dict)
    except ValidationError as exc:
        raise LearnParseError(f"{path.name}: frontmatter validation — {exc}") from exc

    body = m.group("body").strip()
    if not body:
        raise LearnParseError(f"{path.name}: empty body")

    # Filename must agree with the declared slug so URLs and on-disk
    # storage stay in lockstep.
    expected = f"{fm.slug}.md"
    if path.name != expected:
        raise LearnParseError(
            f"{path.name}: slug {fm.slug!r} expects filename {expected!r}"
        )

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


@lru_cache(maxsize=1)
def load_all_stat_tests() -> tuple[StatTestEntry, ...]:
    """Scan + parse every Markdown file in ``stat_tests/``.

    Cached at module level. Duplicate slugs raise ``LearnParseError``.
    """
    if not STAT_TESTS_DIR.exists():
        logger.warning("learn: stat_tests dir missing at %s", STAT_TESTS_DIR)
        return ()

    entries: list[StatTestEntry] = []
    seen: dict[str, Path] = {}
    for md_path in sorted(STAT_TESTS_DIR.glob("*.md")):
        entry = _parse_one(md_path)
        if entry.slug in seen:
            raise LearnParseError(
                f"duplicate slug {entry.slug!r}: {md_path.name} and {seen[entry.slug].name}"
            )
        seen[entry.slug] = md_path
        entries.append(entry)
    return tuple(entries)


def list_stat_tests() -> list[StatTestSummary]:
    return [e.to_summary() for e in load_all_stat_tests()]


def get_stat_test(slug: str) -> StatTestEntry | None:
    for e in load_all_stat_tests():
        if e.slug == slug:
            return e
    return None


def _reset_cache() -> None:
    """Test hook — drop the lru_cache so a fresh scan runs on next call."""
    load_all_stat_tests.cache_clear()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _main() -> int:
    parser = argparse.ArgumentParser(description="Learn hub loader")
    parser.add_argument("--count", action="store_true", help="print entry count")
    parser.add_argument("--list", action="store_true", help="print slugs")
    args = parser.parse_args()

    try:
        entries = load_all_stat_tests()
    except LearnParseError as exc:
        print(f"ERROR: {exc}")
        return 1

    if args.count:
        print(len(entries))
        return 0
    if args.list:
        for e in entries:
            print(f"{e.slug}\t{e.title}")
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entry
    raise SystemExit(_main())
