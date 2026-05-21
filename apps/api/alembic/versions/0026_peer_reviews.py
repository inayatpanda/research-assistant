"""Phase 4.6 — Peer reviews (AI critique).

Revision ID: 0026
Revises: 0025
Create Date: 2026-05-21 09:00:00.000000

Adds the ``peer_reviews`` table backing the new AI peer-review module.
Two source modes share the table:

* ``manuscript`` — reviews the user's own in-app manuscript (a frozen
  snapshot of the sections is stored in ``manuscript_snapshot``).
* ``uploaded_pdf`` / ``uploaded_docx`` — reviews an external document
  uploaded by the user (the storage ref + original filename + size live
  in ``source_file_ref``).

The structured critique JSON is the wire-format the AI provider
returns; see ``services/ai/prompts/peer_review.py`` for the schema.

All foreign keys are explicitly named to avoid unnamed-constraint
issues observed in earlier migrations (0014/0016/0021) when running
``batch_alter_table`` against SQLite.
"""
from alembic import op
import sqlalchemy as sa


revision = "0026"
down_revision = "0025"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "peer_reviews",
        sa.Column("id", sa.String(length=32), primary_key=True),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("project_id", sa.String(length=32), nullable=False),
        sa.Column("source_type", sa.String(length=32), nullable=False),
        sa.Column("source_file_ref", sa.JSON(), nullable=True),
        sa.Column("source_title", sa.String(length=1000), nullable=False),
        sa.Column("manuscript_snapshot", sa.JSON(), nullable=True),
        sa.Column("critique", sa.JSON(), nullable=False),
        sa.Column("recommendation", sa.String(length=32), nullable=False),
        sa.Column("ai_model", sa.String(length=64), nullable=False),
        sa.Column(
            "status",
            sa.String(length=32),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("error", sa.Text(), nullable=True),
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
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            name="fk_peer_reviews_project_id",
            ondelete="CASCADE",
        ),
    )
    op.create_index(
        "ix_peer_reviews_project_user_created",
        "peer_reviews",
        ["project_id", "user_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_peer_reviews_project_user_created", table_name="peer_reviews"
    )
    op.drop_table("peer_reviews")
