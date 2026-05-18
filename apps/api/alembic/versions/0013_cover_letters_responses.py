"""Cover letters + reviewer responses

Revision ID: 0013
Revises: 0012
Create Date: 2026-05-18 18:00:00.000000

Phase 12 — Two new tables that close the submission loop:
  - cover_letters: one body per (project_id, user_id) UNIQUE — auto-created
    on first GET. Stores target_journal (key from JournalTemplate catalogue),
    novelty_points (JSON list[str]), body_html (TipTap HTML), ai_model.
  - reviewer_responses: many rows per project. `comments` JSON column carries
    a list of {comment_text, response_html} objects produced by the AI's
    segmenter and edited by the human.

Both scoped per (project_id, user_id).
"""
from alembic import op
import sqlalchemy as sa


revision = "0013"
down_revision = "0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "cover_letters",
        sa.Column("id", sa.String(length=32), primary_key=True, nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column(
            "project_id",
            sa.String(length=32),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("target_journal", sa.String(length=64), nullable=True),
        sa.Column(
            "novelty_points", sa.JSON(), nullable=False, server_default=sa.text("'[]'")
        ),
        sa.Column("body_html", sa.Text(), nullable=False, server_default=""),
        sa.Column("ai_model", sa.String(length=64), nullable=True),
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
    with op.batch_alter_table("cover_letters", schema=None) as batch_op:
        batch_op.create_index(
            "uq_cover_letters_project_user",
            ["project_id", "user_id"],
            unique=True,
        )

    op.create_table(
        "reviewer_responses",
        sa.Column("id", sa.String(length=32), primary_key=True, nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column(
            "project_id",
            sa.String(length=32),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("reviewer_label", sa.String(length=64), nullable=False),
        sa.Column(
            "comments", sa.JSON(), nullable=False, server_default=sa.text("'[]'")
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
    with op.batch_alter_table("reviewer_responses", schema=None) as batch_op:
        batch_op.create_index(
            "ix_reviewer_responses_project_user",
            ["project_id", "user_id"],
        )


def downgrade() -> None:
    with op.batch_alter_table("reviewer_responses", schema=None) as batch_op:
        batch_op.drop_index("ix_reviewer_responses_project_user")
    op.drop_table("reviewer_responses")

    with op.batch_alter_table("cover_letters", schema=None) as batch_op:
        batch_op.drop_index("uq_cover_letters_project_user")
    op.drop_table("cover_letters")
