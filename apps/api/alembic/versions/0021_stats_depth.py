"""Stats depth (MP17)

Revision ID: 0021
Revises: 0020
Create Date: 2026-05-19 12:30:00.000000

Phase 17 (MP17) — Statistics depth
- ``analyses``: add ``population_id`` (FK NULL), ``is_locked`` bool,
  ``locked_at``, ``integrity_hash`` (sha256 hex string).
- ``analysis_plans``: add ``is_locked``, ``locked_at``, ``integrity_hash``.
- ``analysis_populations``: ITT / PP / safety / as-treated / economic /
  complete-case / imputed sub-population definitions for a dataset.
  ``definition`` carries a JSON dict ``{"filter": <pandas expr>, "label": str}``.
- ``imputation_runs``: MICE / KNN / mean / median / LOCF runs with pooled
  Rubin's-rule summaries.
- ``dataset_variables.instrument_key``: optional binding to the curated
  instrument catalogue (display metadata only).
"""
from alembic import op
import sqlalchemy as sa


revision = "0021"
down_revision = "0020"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. analysis_populations -----------------------------------------------
    op.create_table(
        "analysis_populations",
        sa.Column("id", sa.String(length=32), primary_key=True),
        sa.Column("user_id", sa.String(length=64), nullable=False, index=True),
        sa.Column(
            "dataset_id",
            sa.String(length=32),
            sa.ForeignKey("datasets.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("definition", sa.JSON(), nullable=False),
        sa.Column("study_assignment_field", sa.String(length=255), nullable=False),
        sa.Column(
            "treatment_received_field", sa.String(length=255), nullable=True
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_analysis_populations_dataset",
        "analysis_populations",
        ["dataset_id"],
    )

    # 2. imputation_runs ----------------------------------------------------
    op.create_table(
        "imputation_runs",
        sa.Column("id", sa.String(length=32), primary_key=True),
        sa.Column("user_id", sa.String(length=64), nullable=False, index=True),
        sa.Column(
            "dataset_id",
            sa.String(length=32),
            sa.ForeignKey("datasets.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("method", sa.String(length=32), nullable=False),
        sa.Column("n_imputations", sa.Integer(), nullable=False, server_default="5"),
        sa.Column("seed", sa.Integer(), nullable=False, server_default="42"),
        sa.Column("target_cols", sa.JSON(), nullable=False),
        sa.Column("pooled_summary", sa.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_imputation_runs_dataset",
        "imputation_runs",
        ["dataset_id"],
    )

    # 3. analyses: lock + population FK -------------------------------------
    with op.batch_alter_table("analyses") as batch:
        batch.add_column(
            sa.Column(
                "population_id",
                sa.String(length=32),
                sa.ForeignKey(
                    "analysis_populations.id", ondelete="SET NULL"
                ),
                nullable=True,
            )
        )
        batch.add_column(
            sa.Column(
                "is_locked",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("0"),
            )
        )
        batch.add_column(
            sa.Column("locked_at", sa.DateTime(timezone=True), nullable=True)
        )
        batch.add_column(
            sa.Column("integrity_hash", sa.String(length=64), nullable=True)
        )

    # 4. analysis_plans: lock fields ----------------------------------------
    with op.batch_alter_table("analysis_plans") as batch:
        batch.add_column(
            sa.Column(
                "is_locked",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("0"),
            )
        )
        batch.add_column(
            sa.Column("locked_at", sa.DateTime(timezone=True), nullable=True)
        )
        batch.add_column(
            sa.Column("integrity_hash", sa.String(length=64), nullable=True)
        )

    # 5. dataset_variables.instrument_key -----------------------------------
    with op.batch_alter_table("dataset_variables") as batch:
        batch.add_column(
            sa.Column("instrument_key", sa.String(length=64), nullable=True)
        )


def downgrade() -> None:
    with op.batch_alter_table("dataset_variables") as batch:
        batch.drop_column("instrument_key")
    with op.batch_alter_table("analysis_plans") as batch:
        batch.drop_column("integrity_hash")
        batch.drop_column("locked_at")
        batch.drop_column("is_locked")
    with op.batch_alter_table("analyses") as batch:
        batch.drop_column("integrity_hash")
        batch.drop_column("locked_at")
        batch.drop_column("is_locked")
        batch.drop_column("population_id")
    op.drop_index("ix_imputation_runs_dataset", table_name="imputation_runs")
    op.drop_table("imputation_runs")
    op.drop_index(
        "ix_analysis_populations_dataset", table_name="analysis_populations"
    )
    op.drop_table("analysis_populations")
