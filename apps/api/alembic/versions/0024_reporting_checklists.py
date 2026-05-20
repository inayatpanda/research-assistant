"""Interactive reporting checklists (MP20)

Revision ID: 0024
Revises: 0023
Create Date: 2026-05-20 14:00:00.000000

MP20 — Interactive reporting checklists.

Adds the ``checklist_runs`` table backing the 12 published reporting
guidelines exposed by the static catalogues in
``services/checklists/catalogues/``. One row per (project, user, checklist
key, title) — the unique constraint lets a project hold multiple runs of
the same checklist (e.g. ``v1 submission to JBJS`` and
``v2 resubmission after revisions``).

The ``items`` JSON column stores the user-edited statuses + comments +
section mappings. Each entry is::

    {
        "item_id": "1a",
        "item_text": "Identification as a randomised trial in the title",
        "status": "pass" | "fail" | "unclear" | "na",
        "comment": str,
        "mapped_section": str | null,
        "mapped_text_excerpt": str | null,
    }

``overall_compliance_pct`` is a derived snapshot ``= pass / (total - na)``
maintained by the repository on every PATCH so the list endpoint stays
cheap.
"""
from alembic import op
import sqlalchemy as sa


revision = "0024"
down_revision = "0023"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "checklist_runs",
        sa.Column("id", sa.String(length=32), primary_key=True),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column(
            "project_id",
            sa.String(length=32),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("checklist_key", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("items", sa.JSON(), nullable=False),
        sa.Column(
            "overall_compliance_pct",
            sa.Float(),
            nullable=False,
            server_default="0.0",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "project_id",
            "user_id",
            "checklist_key",
            "title",
            name="uq_checklist_runs_project_user_key_title",
        ),
    )
    op.create_index(
        "ix_checklist_runs_project_user",
        "checklist_runs",
        ["project_id", "user_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_checklist_runs_project_user", table_name="checklist_runs")
    op.drop_table("checklist_runs")
