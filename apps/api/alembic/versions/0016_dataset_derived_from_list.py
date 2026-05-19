"""Dataset.derived_from_dataset_ids list

Revision ID: 0016
Revises: 0015
Create Date: 2026-05-18 21:10:00.000000

Phase 13 (MP13) — Cross-dataset ops (merge / append / join) can derive a new
dataset from TWO+ sources. The existing scalar ``derived_from_dataset_id``
(0014, used by PSM) is kept for backwards compatibility — it points to the
single PSM source. The new ``derived_from_dataset_ids`` JSON column holds a
list of source ids for any multi-source op. Both columns are nullable and
mutually independent.
"""
from alembic import op
import sqlalchemy as sa


revision = "0016"
down_revision = "0015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 0014's FK on `derived_from_dataset_id` was added without an explicit name.
    # SQLite batch mode would otherwise raise "Constraint must have a name" when
    # it re-creates the table to add a new column. A naming_convention here
    # auto-names existing anonymous FKs during the batch operation.
    naming_convention = {
        "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s"
    }
    with op.batch_alter_table(
        "datasets", schema=None, naming_convention=naming_convention
    ) as batch_op:
        batch_op.add_column(
            sa.Column("derived_from_dataset_ids", sa.JSON(), nullable=True)
        )


def downgrade() -> None:
    naming_convention = {
        "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s"
    }
    with op.batch_alter_table(
        "datasets", schema=None, naming_convention=naming_convention
    ) as batch_op:
        batch_op.drop_column("derived_from_dataset_ids")
