"""PSM-matched datasets

Revision ID: 0014
Revises: 0013
Create Date: 2026-05-18 19:00:00.000000

Phase 13 — Propensity-score matching reuses the existing `datasets` table
but tags a matched-output dataset with a `derived_from_dataset_id` FK back
to its source. A JSON `dataset_metadata` column carries the covariate
balance table (pre/post SMDs) and matching parameters. Both columns are
nullable / backwards-compatible.
"""
from alembic import op
import sqlalchemy as sa


revision = "0014"
down_revision = "0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("datasets", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "derived_from_dataset_id",
                sa.String(length=32),
                sa.ForeignKey(
                    "datasets.id",
                    name="fk_datasets_derived_from_dataset_id",
                    ondelete="SET NULL",
                ),
                nullable=True,
            )
        )
        batch_op.add_column(
            sa.Column("dataset_metadata", sa.JSON(), nullable=True)
        )


def downgrade() -> None:
    with op.batch_alter_table("datasets", schema=None) as batch_op:
        batch_op.drop_column("dataset_metadata")
        batch_op.drop_column("derived_from_dataset_id")
