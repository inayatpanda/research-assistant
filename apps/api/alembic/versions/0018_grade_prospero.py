"""GRADE certainty + PROSPERO drafts

Revision ID: 0018
Revises: 0017
Create Date: 2026-05-19 09:00:00.000000

Phase 14 (MP14) — GRADE + PROSPERO
- ``grade_assessments``: one row per outcome (within a review) carrying the
  five downgrade domains, three upgrade domains, derived certainty (persisted
  for query speed but always recomputed on write), and a free-text note. The
  optional ``meta_id`` link lets the SoF builder pull pooled estimate + CI
  for outcomes that are quantitatively synthesised; it's nullable for
  narrative-synthesis outcomes.
- ``prospero_drafts``: pre-fillable 22-field PROSPERO registration form
  stored as a flat JSON dict; one row per (review, user). Exists purely to
  help researchers copy-paste into the PROSPERO web form — we never POST to
  PROSPERO ourselves.
"""
from alembic import op
import sqlalchemy as sa


revision = "0018"
down_revision = "0017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "grade_assessments",
        sa.Column("id", sa.String(length=32), primary_key=True),
        sa.Column("user_id", sa.String(length=64), nullable=False, index=True),
        sa.Column(
            "project_id",
            sa.String(length=32),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "review_id",
            sa.String(length=32),
            sa.ForeignKey("reviews.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "meta_id",
            sa.String(length=32),
            sa.ForeignKey("meta_analyses.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("outcome_label", sa.String(length=255), nullable=False),
        sa.Column("starting_certainty", sa.String(length=16), nullable=False, server_default="high"),
        sa.Column("domain_risk_of_bias", sa.String(length=16), nullable=False, server_default="not_serious"),
        sa.Column("domain_inconsistency", sa.String(length=16), nullable=False, server_default="not_serious"),
        sa.Column("domain_indirectness", sa.String(length=16), nullable=False, server_default="not_serious"),
        sa.Column("domain_imprecision", sa.String(length=16), nullable=False, server_default="not_serious"),
        sa.Column("domain_publication_bias", sa.String(length=16), nullable=False, server_default="not_serious"),
        sa.Column("upgrade_large_effect", sa.String(length=16), nullable=False, server_default="none"),
        sa.Column("upgrade_dose_response", sa.String(length=16), nullable=False, server_default="none"),
        sa.Column("upgrade_confounders_against", sa.String(length=16), nullable=False, server_default="none"),
        sa.Column("certainty", sa.String(length=16), nullable=False, server_default="high"),
        sa.Column("notes", sa.Text(), nullable=True),
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
    op.create_index(
        "ix_grade_assessments_review_user",
        "grade_assessments",
        ["review_id", "user_id"],
    )
    op.create_index(
        "uq_grade_assessments_review_outcome",
        "grade_assessments",
        ["review_id", "outcome_label"],
        unique=True,
    )

    op.create_table(
        "prospero_drafts",
        sa.Column("id", sa.String(length=32), primary_key=True),
        sa.Column("user_id", sa.String(length=64), nullable=False, index=True),
        sa.Column(
            "project_id",
            sa.String(length=32),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "review_id",
            sa.String(length=32),
            sa.ForeignKey("reviews.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("fields", sa.JSON(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "uq_prospero_drafts_review_user",
        "prospero_drafts",
        ["review_id", "user_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(
        "uq_prospero_drafts_review_user", table_name="prospero_drafts"
    )
    op.drop_table("prospero_drafts")
    op.drop_index(
        "uq_grade_assessments_review_outcome", table_name="grade_assessments"
    )
    op.drop_index(
        "ix_grade_assessments_review_user", table_name="grade_assessments"
    )
    op.drop_table("grade_assessments")
