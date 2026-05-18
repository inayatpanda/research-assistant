"""figures + consort_data + Project.template_journal

Revision ID: 0010
Revises: 0009
Create Date: 2026-05-18 09:00:00.000000

Phase 8.7 — Figures, CONSORT, and journal-template-key column.
"""
from alembic import op
import sqlalchemy as sa


revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "figures",
        sa.Column("id", sa.String(length=32), primary_key=True, nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column(
            "project_id",
            sa.String(length=32),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("file_ref", sa.JSON(), nullable=False),
        sa.Column("file_type", sa.String(length=64), nullable=False),
        sa.Column("figure_number", sa.Integer(), nullable=False),
        sa.Column("caption", sa.Text(), nullable=False, server_default=""),
        sa.Column("alt_text", sa.String(length=500), nullable=False, server_default=""),
        sa.Column("width_px", sa.Integer(), nullable=True),
        sa.Column("height_px", sa.Integer(), nullable=True),
        sa.Column("byte_size", sa.Integer(), nullable=False),
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
    with op.batch_alter_table("figures", schema=None) as batch_op:
        batch_op.create_index("ix_figures_user_id", ["user_id"])
        batch_op.create_index("ix_figures_project", ["project_id"])
        batch_op.create_index(
            "uq_figures_project_user_number",
            ["project_id", "user_id", "figure_number"],
            unique=True,
        )

    op.create_table(
        "consort_data",
        sa.Column("id", sa.String(length=32), primary_key=True, nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column(
            "project_id",
            sa.String(length=32),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("enrollment_assessed", sa.Integer(), nullable=True),
        sa.Column("enrollment_excluded", sa.Integer(), nullable=True),
        sa.Column("enrollment_excluded_reasons", sa.JSON(), nullable=True),
        sa.Column("randomised", sa.Integer(), nullable=True),
        sa.Column("allocated_intervention", sa.Integer(), nullable=True),
        sa.Column("allocated_control", sa.Integer(), nullable=True),
        sa.Column("intervention_received", sa.Integer(), nullable=True),
        sa.Column("control_received", sa.Integer(), nullable=True),
        sa.Column("intervention_lost_followup", sa.Integer(), nullable=True),
        sa.Column("control_lost_followup", sa.Integer(), nullable=True),
        sa.Column("intervention_discontinued", sa.Integer(), nullable=True),
        sa.Column("control_discontinued", sa.Integer(), nullable=True),
        sa.Column("intervention_analysed", sa.Integer(), nullable=True),
        sa.Column("control_analysed", sa.Integer(), nullable=True),
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
    with op.batch_alter_table("consort_data", schema=None) as batch_op:
        batch_op.create_index("ix_consort_user_id", ["user_id"])
        batch_op.create_index(
            "uq_consort_project_user",
            ["project_id", "user_id"],
            unique=True,
        )

    with op.batch_alter_table("projects", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("template_journal", sa.String(length=64), nullable=True)
        )


def downgrade() -> None:
    with op.batch_alter_table("projects", schema=None) as batch_op:
        batch_op.drop_column("template_journal")

    with op.batch_alter_table("consort_data", schema=None) as batch_op:
        batch_op.drop_index("uq_consort_project_user")
        batch_op.drop_index("ix_consort_user_id")
    op.drop_table("consort_data")

    with op.batch_alter_table("figures", schema=None) as batch_op:
        batch_op.drop_index("uq_figures_project_user_number")
        batch_op.drop_index("ix_figures_project")
        batch_op.drop_index("ix_figures_user_id")
    op.drop_table("figures")
