"""Duplicate-group finder over a project's articles.

Algorithm:

1. Bucket by lowercase DOI — any bucket with ≥ 2 → group ``doi_exact``.
2. Bucket the remaining rows by PMID — any bucket with ≥ 2 → ``pmid_exact``.
3. Among rows still ungrouped, run rapidfuzz ``token_set_ratio`` over
   normalised titles in O(n²). Any pair with ratio ≥ fuzzy_threshold AND
   ``|year_a - year_b| ≤ year_tolerance`` → group ``title_fuzzy``. Use
   union-find to keep transitively-related rows in a single group.

The first row in each group (input order — typically created_at ASC) is
the ``keep_candidate_id``. Groups are returned ordered by descending size,
then by ``keep_candidate_id`` ASC.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from rapidfuzz import fuzz

from ...schemas.ingest import DuplicateGroup


@dataclass(frozen=True)
class DuplicateCandidate:
    article_id: str
    title: str
    year: int | None
    doi: str | None
    pmid: str | None


_PUNCT = re.compile(r"[^\w\s]")
_WS = re.compile(r"\s+")


def _norm_title(t: str | None) -> str:
    if not t:
        return ""
    s = t.lower()
    s = _PUNCT.sub(" ", s)
    s = _WS.sub(" ", s).strip()
    return s


class _UnionFind:
    def __init__(self, items: list[str]) -> None:
        self._parent: dict[str, str] = {x: x for x in items}

    def find(self, x: str) -> str:
        # Path compression
        root = x
        while self._parent[root] != root:
            root = self._parent[root]
        while self._parent[x] != root:
            self._parent[x], x = root, self._parent[x]
        return root

    def union(self, a: str, b: str) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self._parent[rb] = ra


def find_duplicates(
    candidates: list[DuplicateCandidate],
    *,
    fuzzy_threshold: float = 0.92,
    year_tolerance: int = 1,
) -> list[DuplicateGroup]:
    """Return groups of likely duplicates (DOI exact > PMID exact > fuzzy title)."""
    if not candidates:
        return []

    order_index = {c.article_id: i for i, c in enumerate(candidates)}
    by_id = {c.article_id: c for c in candidates}

    grouped_ids: set[str] = set()
    groups: list[DuplicateGroup] = []

    # 1. DOI exact buckets
    doi_buckets: dict[str, list[str]] = {}
    for c in candidates:
        if c.doi:
            doi_buckets.setdefault(c.doi.strip().lower(), []).append(c.article_id)
    for bucket_ids in doi_buckets.values():
        if len(bucket_ids) >= 2:
            ordered = sorted(bucket_ids, key=lambda i: order_index[i])
            groups.append(
                DuplicateGroup(
                    keep_candidate_id=ordered[0],
                    candidate_ids=ordered,
                    reason="doi_exact",
                    score=1.0,
                )
            )
            grouped_ids.update(ordered)

    # 2. PMID exact buckets (skip already-grouped rows)
    pmid_buckets: dict[str, list[str]] = {}
    for c in candidates:
        if c.article_id in grouped_ids:
            continue
        if c.pmid:
            pmid_buckets.setdefault(c.pmid.strip(), []).append(c.article_id)
    for bucket_ids in pmid_buckets.values():
        if len(bucket_ids) >= 2:
            ordered = sorted(bucket_ids, key=lambda i: order_index[i])
            groups.append(
                DuplicateGroup(
                    keep_candidate_id=ordered[0],
                    candidate_ids=ordered,
                    reason="pmid_exact",
                    score=1.0,
                )
            )
            grouped_ids.update(ordered)

    # 3. Fuzzy title across remaining
    remaining = [c for c in candidates if c.article_id not in grouped_ids]
    if len(remaining) >= 2:
        uf = _UnionFind([c.article_id for c in remaining])
        pair_scores: dict[tuple[str, str], float] = {}
        for i in range(len(remaining)):
            a = remaining[i]
            ta = _norm_title(a.title)
            if not ta:
                continue
            for j in range(i + 1, len(remaining)):
                b = remaining[j]
                tb = _norm_title(b.title)
                if not tb:
                    continue
                if a.year is None or b.year is None:
                    continue
                if abs(a.year - b.year) > year_tolerance:
                    continue
                ratio = fuzz.token_set_ratio(ta, tb) / 100.0
                if ratio >= fuzzy_threshold:
                    uf.union(a.article_id, b.article_id)
                    key = (
                        min(a.article_id, b.article_id),
                        max(a.article_id, b.article_id),
                    )
                    pair_scores[key] = max(pair_scores.get(key, 0.0), ratio)

        # Collect components
        components: dict[str, list[str]] = {}
        for c in remaining:
            root = uf.find(c.article_id)
            components.setdefault(root, []).append(c.article_id)

        for ids in components.values():
            if len(ids) < 2:
                continue
            ordered = sorted(ids, key=lambda i: order_index[i])
            # Score = max pairwise ratio within the component
            comp_score = 0.0
            for i in range(len(ordered)):
                for j in range(i + 1, len(ordered)):
                    key = (
                        min(ordered[i], ordered[j]),
                        max(ordered[i], ordered[j]),
                    )
                    if key in pair_scores:
                        comp_score = max(comp_score, pair_scores[key])
            groups.append(
                DuplicateGroup(
                    keep_candidate_id=ordered[0],
                    candidate_ids=ordered,
                    reason="title_fuzzy",
                    score=round(comp_score, 4),
                )
            )

    # Order: largest group first, then keep_candidate_id ASC (deterministic)
    groups.sort(key=lambda g: (-len(g.candidate_ids), g.keep_candidate_id))
    return groups


__all__ = ["DuplicateCandidate", "find_duplicates"]
