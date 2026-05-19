"""Living systematic review jobs + hits

Revision ID: 0019
Revises: 0018
Create Date: 2026-05-19 10:00:00.000000

Phase 15 (MP15) — Living systematic review auto-rerun
- ``living_review_jobs``: one job per review carrying the saved PubMed query,
  schedule cadence, enabled flag, and a lease_holder column used by the
  APScheduler runner to avoid double-firing across instances.
- ``living_review_hits``: per-run new-PMID rows with a tri-state decision
  (new|dismissed|accepted). Hits are transient — they reset on bundle import.
"""
from alembic import op
import sqlalchemy as sa


revision = "0019"
down_revision = "0018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "living_review_jobs",
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
        sa.Column("pubmed_query", sa.Text(), nullable=False),
        sa.Column(
            "schedule", sa.String(length=16), nullable=False, server_default="weekly"
        ),
        sa.Column(
            "enabled", sa.Boolean(), nullable=False, server_default=sa.text("1")
        ),
        sa.Column("last_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_hit_count", sa.Integer(), nullable=True),
        sa.Column("lease_holder", sa.String(length=128), nullable=True),
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
        "uq_living_review_jobs_review",
        "living_review_jobs",
        ["review_id"],
        unique=True,
    )
    op.create_index(
        "ix_living_review_jobs_user_enabled",
        "living_review_jobs",
        ["user_id", "enabled"],
    )

    op.create_table(
        "living_review_hits",
        sa.Column("id", sa.String(length=32), primary_key=True),
        sa.Column("user_id", sa.String(length=64), nullable=False, index=True),
        sa.Column(
            "job_id",
            sa.String(length=32),
            sa.ForeignKey("living_review_jobs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "run_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("pmid", sa.String(length=16), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column(
            "decision", sa.String(length=16), nullable=False, server_default="new"
        ),
        sa.Column(
            "seen_in_baseline",
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
    )
    op.create_index(
        "ix_living_review_hits_job_decision",
        "living_review_hits",
        ["job_id", "decision"],
    )
    op.create_index(
        "uq_living_review_hits_job_pmid",
        "living_review_hits",
        ["job_id", "pmid"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(
        "uq_living_review_hits_job_pmid", table_name="living_review_hits"
    )
    op.drop_index(
        "ix_living_review_hits_job_decision", table_name="living_review_hits"
    )
    op.drop_table("living_review_hits")
    op.drop_index(
        "ix_living_review_jobs_user_enabled", table_name="living_review_jobs"
    )
    op.drop_index(
        "uq_living_review_jobs_review", table_name="living_review_jobs"
    )
    op.drop_table("living_review_jobs")
