"""Plots + analysis plans + plan runs

Revision ID: 0017
Revises: 0016
Create Date: 2026-05-19 10:00:00.000000

Phase 13.5 (MP13.5)
- ``dataset_plots``: grammar-of-graphics style saved plots per dataset.
  Each row stores a JSON spec ({geom, x, y?, color?, facet?, args?}) plus
  the rendered PNG as a base64 data URI cached at create time.
- ``analysis_plans``: a named, ordered list of steps (transform / test /
  plot). Scoped per (project, user). Used to re-run the same chain of
  ops against different datasets.
- ``analysis_plan_runs``: append-only execution log. Each run captures
  a per-step result blob + a roll-up status ("ok" | "partial" | "failed").
"""
from alembic import op
import sqlalchemy as sa


revision = "0017"
down_revision = "0016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "dataset_plots",
        sa.Column("id", sa.String(length=32), primary_key=True),
        sa.Column("user_id", sa.String(length=64), nullable=False, index=True),
        sa.Column(
            "project_id",
            sa.String(length=32),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "dataset_id",
            sa.String(length=32),
            sa.ForeignKey("datasets.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("title", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("spec", sa.JSON(), nullable=False),
        sa.Column("png_data_uri", sa.Text(), nullable=False, server_default=""),
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
        "ix_dataset_plots_dataset_user",
        "dataset_plots",
        ["dataset_id", "user_id"],
    )

    op.create_table(
        "analysis_plans",
        sa.Column("id", sa.String(length=32), primary_key=True),
        sa.Column("user_id", sa.String(length=64), nullable=False, index=True),
        sa.Column(
            "project_id",
            sa.String(length=32),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("steps", sa.JSON(), nullable=False),
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
        "ix_analysis_plans_project_user",
        "analysis_plans",
        ["project_id", "user_id"],
    )

    op.create_table(
        "analysis_plan_runs",
        sa.Column("id", sa.String(length=32), primary_key=True),
        sa.Column("user_id", sa.String(length=64), nullable=False, index=True),
        sa.Column(
            "plan_id",
            sa.String(length=32),
            sa.ForeignKey("analysis_plans.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("dataset_id", sa.String(length=32), nullable=False),
        sa.Column(
            "executed_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("result_blob", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
    )
    op.create_index(
        "ix_analysis_plan_runs_plan",
        "analysis_plan_runs",
        ["plan_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_analysis_plan_runs_plan", table_name="analysis_plan_runs")
    op.drop_table("analysis_plan_runs")
    op.drop_index("ix_analysis_plans_project_user", table_name="analysis_plans")
    op.drop_table("analysis_plans")
    op.drop_index("ix_dataset_plots_dataset_user", table_name="dataset_plots")
    op.drop_table("dataset_plots")
