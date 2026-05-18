"""Manuscript snapshots + margin comments

Revision ID: 0012
Revises: 0011
Create Date: 2026-05-18 12:00:00.000000

Phase 11 — Two new tables:
  - manuscript_snapshots: full point-in-time copy (JSON blob) of every
    section + ICMJE front-matter + figures + abbreviations + meta_analyses +
    extraction_records, per project + label (UNIQUE).
  - manuscript_comments: section-anchored note (anchor_start/end are
    ProseMirror integer positions) with a `resolved` flag.

Both scoped per (project_id, user_id).
"""
from alembic import op
import sqlalchemy as sa


revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "manuscript_snapshots",
        sa.Column("id", sa.String(length=32), primary_key=True, nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column(
            "project_id",
            sa.String(length=32),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("label", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("full_blob", sa.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    with op.batch_alter_table("manuscript_snapshots", schema=None) as batch_op:
        batch_op.create_index(
            "uq_manuscript_snapshots_project_user_label",
            ["project_id", "user_id", "label"],
            unique=True,
        )
        batch_op.create_index(
            "ix_manuscript_snapshots_project_user",
            ["project_id", "user_id"],
        )

    op.create_table(
        "manuscript_comments",
        sa.Column("id", sa.String(length=32), primary_key=True, nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column(
            "project_id",
            sa.String(length=32),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("section_name", sa.String(length=32), nullable=False),
        sa.Column("anchor_start", sa.Integer(), nullable=False),
        sa.Column("anchor_end", sa.Integer(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column(
            "resolved",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    with op.batch_alter_table("manuscript_comments", schema=None) as batch_op:
        batch_op.create_index(
            "ix_manuscript_comments_section",
            ["project_id", "user_id", "section_name", "resolved"],
        )


def downgrade() -> None:
    with op.batch_alter_table("manuscript_comments", schema=None) as batch_op:
        batch_op.drop_index("ix_manuscript_comments_section")
    op.drop_table("manuscript_comments")

    with op.batch_alter_table("manuscript_snapshots", schema=None) as batch_op:
        batch_op.drop_index("ix_manuscript_snapshots_project_user")
        batch_op.drop_index("uq_manuscript_snapshots_project_user_label")
    op.drop_table("manuscript_snapshots")
