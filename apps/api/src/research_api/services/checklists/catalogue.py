"""Phase 20 (MP20) — Reporting-guideline checklist catalogues.

12 catalogues are shipped as static JSON files in ``catalogues/`` (see
``catalogues/consort_2010.json`` etc.). This module loads them on first
access and caches the parsed dicts for the lifetime of the process. The
backwards-compat ``CHECKLISTS`` mapping (introduced as a Phase 18 stub)
remains exported so older imports do not break.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any


CATALOGUES_DIR = Path(__file__).resolve().parent / "catalogues"


@dataclass(frozen=True)
class ChecklistItem:
    """One row in a reporting checklist."""

    id: str
    title: str
    description: str
    section_hint: str


@dataclass(frozen=True)
class ChecklistCatalogue:
    """The full, immutable definition of a published reporting checklist."""

    key: str
    name: str
    description: str
    version: str
    default_section: str
    items: tuple[ChecklistItem, ...]

    @property
    def item_count(self) -> int:
        return len(self.items)


def _parse(data: dict[str, Any]) -> ChecklistCatalogue:
    items_raw = data.get("items") or []
    items: list[ChecklistItem] = []
    for raw in items_raw:
        items.append(
            ChecklistItem(
                id=str(raw["id"]),
                title=str(raw.get("title") or ""),
                description=str(raw.get("description") or ""),
                section_hint=str(
                    raw.get("section_hint")
                    or data.get("default_section")
                    or "Methods"
                ),
            )
        )
    return ChecklistCatalogue(
        key=str(data["key"]),
        name=str(data.get("name") or data["key"]),
        description=str(data.get("description") or ""),
        version=str(data.get("version") or ""),
        default_section=str(data.get("default_section") or "Methods"),
        items=tuple(items),
    )


@lru_cache(maxsize=1)
def _load_all() -> dict[str, ChecklistCatalogue]:
    out: dict[str, ChecklistCatalogue] = {}
    if not CATALOGUES_DIR.exists():  # pragma: no cover - shipped in repo
        return out
    for path in sorted(CATALOGUES_DIR.glob("*.json")):
        try:
            with path.open(encoding="utf-8") as fh:
                data = json.load(fh)
        except (OSError, json.JSONDecodeError):  # pragma: no cover
            continue
        cat = _parse(data)
        out[cat.key] = cat
    return out


def list_catalogues() -> list[dict[str, Any]]:
    """Return a lightweight metadata list (no item bodies)."""
    catalogues = _load_all()
    return [
        {
            "key": c.key,
            "name": c.name,
            "description": c.description,
            "version": c.version,
            "default_section": c.default_section,
            "item_count": c.item_count,
        }
        for c in catalogues.values()
    ]


def get_catalogue(key: str) -> ChecklistCatalogue | None:
    return _load_all().get(key)


def all_keys() -> list[str]:
    return list(_load_all().keys())


# ── Backwards-compat alias (Phase 18 stub) ─────────────────────────────────
# Older code (CHEERS DOCX exporter) imports `CHECKLISTS["cheers_2022"]` from
# this module. Preserve the lowercase key + the shape it expects.
def _legacy_cheers_dict() -> dict[str, Any] | None:
    cat = get_catalogue("CHEERS_2022")
    if cat is None:
        return None
    return {
        "key": "cheers_2022",
        "name": cat.name,
        "version": cat.version,
        "source_citation": (
            "Husereau D, Drummond M, Augustovski F, et al. Consolidated Health "
            "Economic Evaluation Reporting Standards 2022 (CHEERS 2022) "
            "Statement. Value Health 2022;25(1):3-9."
        ),
        "items": [
            {
                "n": it.id,
                "section": it.section_hint,
                "topic": it.title,
                "recommendation": it.description,
            }
            for it in cat.items
        ],
    }


def _build_legacy_map() -> dict[str, dict[str, Any]]:
    legacy: dict[str, dict[str, Any]] = {}
    cheers = _legacy_cheers_dict()
    if cheers is not None:
        legacy["cheers_2022"] = cheers
    return legacy


CHECKLISTS: dict[str, dict[str, Any]] = _build_legacy_map()
# Legacy named binding so older imports keep working.
CHEERS_2022: dict[str, Any] | None = CHECKLISTS.get("cheers_2022")


__all__ = [
    "CATALOGUES_DIR",
    "CHECKLISTS",
    "CHEERS_2022",
    "ChecklistCatalogue",
    "ChecklistItem",
    "all_keys",
    "get_catalogue",
    "list_catalogues",
]
