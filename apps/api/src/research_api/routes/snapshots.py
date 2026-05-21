"""Phase 11 — Manuscript snapshot routes.

Endpoints (under /api/projects/{project_id}/snapshots):

  GET    /                       list snapshots (newest first, summary only)
  POST   /                       create snapshot (label + optional description)
  GET    /{snapshot_id}          get full snapshot (incl. blob)
  GET    /{snapshot_id}/diff     diff against another snapshot OR current
  DELETE /{snapshot_id}          delete snapshot

The diff endpoint uses `difflib.unified_diff` (stdlib only) per section.
Each section's HTML is split on newlines and passed to unified_diff with
n=0 (no context); the result is post-processed into a list of
`{type: '+' | '-' | '=', line: ...}` records keyed by section_name.

Section names not present in the BASE snapshot but present in the TARGET
appear as all-additions; sections only in BASE appear as all-deletions.
"""
from __future__ import annotations

import difflib
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..container import Container, get_container
from ..auth_deps import get_current_user
from ..schemas.auth import UserRead
from ..repositories.projects import SqliteProjectRepository
from ..repositories.snapshots import (
    SnapshotLabelConflict,
    SqliteSnapshotRepository,
)
from ..schemas.snapshots import (
    DiffLine,
    SnapshotCreate,
    SnapshotDiffResponse,
    SnapshotRead,
    SnapshotSummary,
)


router = APIRouter(tags=["snapshots"])


async def _session(
    container: Container = Depends(get_container),
) -> AsyncIterator[AsyncSession]:
    async with container.session_factory() as s:
        yield s


def _user_id(user: UserRead = Depends(get_current_user)) -> str:
    # Phase S1 — delegate to the real session-derived user. The legacy
    # static-id flow remains available via ``RMA_DISABLE_AUTH=1``.
    return user.id


# ── Diff helpers ─────────────────────────────────────────────────────


def _sections_from_blob(blob: dict | None) -> dict[str, str]:
    """Map section_name → HTML content from a snapshot blob."""
    if not blob:
        return {}
    out: dict[str, str] = {}
    for row in blob.get("manuscript_sections") or []:
        name = row.get("section_name")
        if not name:
            continue
        out[name] = row.get("content") or ""
    return out


def _diff_html(base_html: str, target_html: str) -> list[DiffLine]:
    """Line-by-line unified diff between two HTML strings.

    Granularity: line-by-line (HTML lines as produced by TipTap, one per
    `<p>` / block element). Word-by-word diffs were considered but rejected
    — TipTap emits one block per line, so line granularity yields readable
    surgical diffs without pulling in a JS / Python word-diff dep. The
    consumer (`VersionDiffView`) post-renders each line as `<ins>`/`<del>`.

    Returns `[]` when the two strings are identical.
    """
    if base_html == target_html:
        return []
    base_lines = base_html.splitlines()
    target_lines = target_html.splitlines()
    raw = list(
        difflib.unified_diff(
            base_lines,
            target_lines,
            lineterm="",
            n=0,  # no context — keep diffs surgical
        )
    )
    out: list[DiffLine] = []
    for line in raw:
        # Skip difflib's `--- / +++ / @@` headers; we don't need them.
        if line.startswith("---") or line.startswith("+++"):
            continue
        if line.startswith("@@"):
            continue
        if line.startswith("+"):
            out.append(DiffLine(type="+", line=line[1:]))
        elif line.startswith("-"):
            out.append(DiffLine(type="-", line=line[1:]))
        else:
            # `unified_diff` with n=0 normally won't emit unchanged lines, but
            # be defensive — strip the leading space if difflib ever does.
            out.append(DiffLine(type="=", line=line[1:] if line.startswith(" ") else line))
    return out


# ── Routes ───────────────────────────────────────────────────────────


@router.get(
    "/projects/{project_id}/snapshots",
    response_model=list[SnapshotSummary],
)
async def list_snapshots(
    project_id: str,
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> list[SnapshotSummary]:
    project = await SqliteProjectRepository(session).get(project_id, user_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    repo = SqliteSnapshotRepository(session)
    rows = await repo.list_for_project(project_id=project_id, user_id=user_id)
    return [SnapshotSummary.model_validate(r) for r in rows]


@router.post(
    "/projects/{project_id}/snapshots",
    response_model=SnapshotRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_snapshot(
    project_id: str,
    body: SnapshotCreate,
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> SnapshotRead:
    project = await SqliteProjectRepository(session).get(project_id, user_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    repo = SqliteSnapshotRepository(session)
    try:
        snap = await repo.create_from_current(
            project_id=project_id,
            user_id=user_id,
            label=body.label,
            description=body.description,
        )
    except SnapshotLabelConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from None
    return SnapshotRead.model_validate(snap)


@router.get(
    "/projects/{project_id}/snapshots/{snapshot_id}",
    response_model=SnapshotRead,
)
async def get_snapshot(
    project_id: str,
    snapshot_id: str,
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> SnapshotRead:
    project = await SqliteProjectRepository(session).get(project_id, user_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    repo = SqliteSnapshotRepository(session)
    snap = await repo.get(snapshot_id, user_id)
    if snap is None or snap.project_id != project_id:
        raise HTTPException(status_code=404, detail="Snapshot not found")
    return SnapshotRead.model_validate(snap)


@router.get(
    "/projects/{project_id}/snapshots/{snapshot_id}/diff",
    response_model=SnapshotDiffResponse,
)
async def diff_snapshot(
    project_id: str,
    snapshot_id: str,
    target: str | None = Query(
        default=None,
        description=(
            "Snapshot id to diff against. Omit to diff against the CURRENT "
            "project state."
        ),
    ),
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> SnapshotDiffResponse:
    project = await SqliteProjectRepository(session).get(project_id, user_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    repo = SqliteSnapshotRepository(session)
    base = await repo.get(snapshot_id, user_id)
    if base is None or base.project_id != project_id:
        raise HTTPException(status_code=404, detail="Snapshot not found")

    if target is None:
        # Compare against the live state — assemble a transient blob.
        target_blob = await repo._assemble_blob(  # noqa: SLF001 — internal helper
            project_id=project_id, user_id=user_id
        )
        target_id = None
    else:
        target_snap = await repo.get(target, user_id)
        if target_snap is None or target_snap.project_id != project_id:
            raise HTTPException(
                status_code=404, detail="Target snapshot not found"
            )
        target_blob = target_snap.full_blob or {}
        target_id = target_snap.id

    base_sections = _sections_from_blob(base.full_blob)
    target_sections = _sections_from_blob(target_blob)
    all_names = sorted(set(base_sections) | set(target_sections))

    sections_out: dict[str, list[DiffLine]] = {}
    for name in all_names:
        lines = _diff_html(
            base_sections.get(name, ""), target_sections.get(name, "")
        )
        if lines:
            sections_out[name] = lines

    return SnapshotDiffResponse(
        base_snapshot_id=base.id,
        target_snapshot_id=target_id,
        sections=sections_out,
    )


@router.delete(
    "/projects/{project_id}/snapshots/{snapshot_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_snapshot(
    project_id: str,
    snapshot_id: str,
    session: AsyncSession = Depends(_session),
    user_id: str = Depends(_user_id),
) -> None:
    project = await SqliteProjectRepository(session).get(project_id, user_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    repo = SqliteSnapshotRepository(session)
    snap = await repo.get(snapshot_id, user_id)
    if snap is None or snap.project_id != project_id:
        raise HTTPException(status_code=404, detail="Snapshot not found")
    await repo.delete(snapshot_id, user_id)
    return None
