"""Dataset transformations stack

Revision ID: 0015
Revises: 0014
Create Date: 2026-05-18 21:00:00.000000

Phase 13 (MP13) — A user-editable, ordered stack of pure-function operations
applied to a dataset BEFORE any test runs. Each row is one op (filter,
mutate, select, recode, drop_na, log_transform, z_score, group_summarise).

The original uploaded CSV is never mutated; transformations are stored as
JSON op_args and replayed by the runner on every analysis run. Reordering
is done via a transactional "replace_all" so position is always dense.
"""
from alembic import op
import sqlalchemy as sa


revision = "0015"
down_revision = "0014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "dataset_transformations",
        sa.Column("id", sa.String(length=32), primary_key=True),
        sa.Column("user_id", sa.String(length=64), nullable=False, index=True),
        sa.Column(
            "dataset_id",
            sa.String(length=32),
            sa.ForeignKey("datasets.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("op_type", sa.String(length=32), nullable=False),
        sa.Column("op_args", sa.JSON(), nullable=False),
        sa.Column("label", sa.String(length=255), nullable=False, server_default=""),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_dataset_transformations_dataset_position",
        "dataset_transformations",
        ["dataset_id", "position"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_dataset_transformations_dataset_position",
        table_name="dataset_transformations",
    )
    op.drop_table("dataset_transformations")
