"""Health economics (MP18)

Revision ID: 0023
Revises: 0022
Create Date: 2026-05-20 12:00:00.000000

MP18 — Health Economics Module.

Adds two tables backing the cost-effectiveness workspace:

  * ``economic_analyses`` — one configuration per cost-effectiveness analysis
    on a project/dataset (currency, perspective, time horizon, discount
    rates, WTP thresholds, utility value-set choice, bootstrap n + seed, the
    treatment column, comparator/intervention labels, the cost-column
    bindings, and an optional AI interpretation paragraph).
  * ``economic_results`` — the single result row per analysis (mean cost
    diff, mean QALY diff, ICER, dominance status, NMB-at-thresholds,
    CEAC curve data, plane bootstrap reps, sensitivity output, and two
    embedded PNG data URIs — the CE plane + the CEAC curve).

Both tables FK to ``projects.id`` / ``datasets.id`` / ``economic_analyses.id``
with ON DELETE CASCADE so deleting the parent project tidies up the
economic artefacts. ``dataset_id`` is nullable on ``economic_analyses`` so
the analysis can be persisted before the cost columns are bound to a
specific dataset (though the run endpoint requires it).
"""
from alembic import op
import sqlalchemy as sa


revision = "0023"
down_revision = "0022"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "economic_analyses",
        sa.Column("id", sa.String(length=32), primary_key=True),
        sa.Column("user_id", sa.String(length=64), nullable=False),
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
            nullable=True,
        ),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("currency", sa.String(length=8), nullable=False, server_default="GBP"),
        sa.Column("time_horizon_months", sa.Integer(), nullable=False, server_default="12"),
        sa.Column(
            "perspective",
            sa.String(length=32),
            nullable=False,
            server_default="healthcare_system",
        ),
        sa.Column(
            "discount_rate_costs", sa.Float(), nullable=False, server_default="0.035"
        ),
        sa.Column(
            "discount_rate_qalys", sa.Float(), nullable=False, server_default="0.035"
        ),
        sa.Column("wtp_thresholds", sa.JSON(), nullable=False),
        sa.Column(
            "utility_value_set",
            sa.String(length=32),
            nullable=False,
            server_default="EQ5D_5L_UK",
        ),
        sa.Column("bootstrap_n", sa.Integer(), nullable=False, server_default="1000"),
        sa.Column("seed", sa.Integer(), nullable=False, server_default="42"),
        sa.Column("treatment_col", sa.String(length=255), nullable=False),
        sa.Column("comparator_label", sa.String(length=255), nullable=False),
        sa.Column("intervention_label", sa.String(length=255), nullable=False),
        sa.Column("cost_columns", sa.JSON(), nullable=False),
        sa.Column("ai_interpretation", sa.Text(), nullable=True),
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
    )
    op.create_index(
        "ix_economic_analyses_project_user",
        "economic_analyses",
        ["project_id", "user_id"],
    )

    op.create_table(
        "economic_results",
        sa.Column("id", sa.String(length=32), primary_key=True),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column(
            "economic_analysis_id",
            sa.String(length=32),
            sa.ForeignKey("economic_analyses.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("mean_cost_diff", sa.Float(), nullable=False),
        sa.Column("mean_qaly_diff", sa.Float(), nullable=False),
        sa.Column("icer", sa.Float(), nullable=True),
        sa.Column("dominance_status", sa.String(length=32), nullable=False),
        sa.Column("nmb_at_thresholds", sa.JSON(), nullable=False),
        sa.Column("ceac_data", sa.JSON(), nullable=False),
        sa.Column("plane_bootstrap", sa.JSON(), nullable=False),
        sa.Column("sensitivity", sa.JSON(), nullable=True),
        sa.Column("plane_png_uri", sa.Text(), nullable=False),
        sa.Column("ceac_png_uri", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_table("economic_results")
    op.drop_index(
        "ix_economic_analyses_project_user", table_name="economic_analyses"
    )
    op.drop_table("economic_analyses")
