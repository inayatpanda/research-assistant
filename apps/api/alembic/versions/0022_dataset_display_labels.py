"""Dataset display labels (DEMO-FIX-C)

Revision ID: 0022
Revises: 0021
Create Date: 2026-05-20 09:00:00.000000

DEMO-FIX-C — Column display labels.

Each ``dataset_variables`` row gains a free-text ``display_label`` used by
chart axes, AI prose, OutputViewer cards and PDF exports. The runner still
operates on the canonical ``name`` column (Python-identifier-safe). The
``display_label`` is back-populated from the existing ``name`` so charts
keep rendering identically until a user edits it.
"""
from alembic import op
import sqlalchemy as sa


revision = "0022"
down_revision = "0021"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("dataset_variables") as batch:
        batch.add_column(
            sa.Column("display_label", sa.Text(), nullable=True)
        )
    # Back-fill: every existing variable's display_label = its canonical name.
    op.execute(
        "UPDATE dataset_variables SET display_label = name WHERE display_label IS NULL"
    )


def downgrade() -> None:
    with op.batch_alter_table("dataset_variables") as batch:
        batch.drop_column("display_label")
