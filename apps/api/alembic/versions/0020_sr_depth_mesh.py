"""SR depth + MeSH (MP19)

Revision ID: 0020
Revises: 0019
Create Date: 2026-05-19 12:00:00.000000

Phase 19 (MP19) — Systematic Review depth + MeSH catalogue
- ``mesh_terms``: cached NCBI MeSH descriptor lookups scoped per project.
- ``search_strategies``: per-review query builder rows, with cross-DB
  translation lineage via ``translated_from_id`` (self FK).
- ``narrative_synthesis_entries``: per-outcome qualitative summary table
  for SR multi-instrument comparison.
- ``outcome_instruments``: many-to-many studies x instruments grid (rows
  carry a JSON list of {article_id, group_label, value, sd_or_ci, n}).
- ``reviews.tool_per_study``: when true, each RoB row may use a different
  appraisal tool (for mixed-design reviews).

Notes
-----
``articles.study_design`` already exists as a ``String(64)`` column — the
allowed Literal values are validated at the Pydantic boundary in
``schemas/article.py``; no DDL change is necessary, so we only update the
schema layer.
"""
from alembic import op
import sqlalchemy as sa


revision = "0020"
down_revision = "0019"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "mesh_terms",
        sa.Column("id", sa.String(length=32), primary_key=True),
        sa.Column("user_id", sa.String(length=64), nullable=False, index=True),
        sa.Column(
            "project_id",
            sa.String(length=32),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("descriptor_ui", sa.String(length=32), nullable=False),
        sa.Column("descriptor_name", sa.String(length=500), nullable=False),
        sa.Column("scope_note", sa.Text(), nullable=True),
        sa.Column("tree_numbers", sa.JSON(), nullable=False),
        sa.Column("entry_terms", sa.JSON(), nullable=False),
        sa.Column(
            "source", sa.String(length=16), nullable=False, server_default="ncbi_lookup"
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "uq_mesh_terms_project_ui",
        "mesh_terms",
        ["project_id", "descriptor_ui"],
        unique=True,
    )

    op.create_table(
        "search_strategies",
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
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("database", sa.String(length=32), nullable=False),
        sa.Column("query_text", sa.Text(), nullable=False),
        sa.Column("mesh_term_ids", sa.JSON(), nullable=False),
        sa.Column(
            "translated_from_id",
            sa.String(length=32),
            sa.ForeignKey("search_strategies.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "is_locked",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column("warnings", sa.JSON(), nullable=True),
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
        "ix_search_strategies_review",
        "search_strategies",
        ["review_id"],
    )

    op.create_table(
        "narrative_synthesis_entries",
        sa.Column("id", sa.String(length=32), primary_key=True),
        sa.Column("user_id", sa.String(length=64), nullable=False, index=True),
        sa.Column(
            "review_id",
            sa.String(length=32),
            sa.ForeignKey("reviews.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("outcome_label", sa.String(length=255), nullable=False),
        sa.Column("instrument", sa.String(length=255), nullable=False),
        sa.Column("range_text", sa.String(length=255), nullable=True),
        sa.Column(
            "direction", sa.String(length=20), nullable=False, server_default="neutral"
        ),
        sa.Column("narrative_html", sa.Text(), nullable=False, server_default=""),
        sa.Column("study_citations", sa.JSON(), nullable=False),
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
        "ix_narrative_synthesis_review",
        "narrative_synthesis_entries",
        ["review_id"],
    )

    op.create_table(
        "outcome_instruments",
        sa.Column("id", sa.String(length=32), primary_key=True),
        sa.Column("user_id", sa.String(length=64), nullable=False, index=True),
        sa.Column(
            "review_id",
            sa.String(length=32),
            sa.ForeignKey("reviews.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("outcome_label", sa.String(length=255), nullable=False),
        sa.Column("instrument_name", sa.String(length=255), nullable=False),
        sa.Column("score_range_low", sa.Float(), nullable=True),
        sa.Column("score_range_high", sa.Float(), nullable=True),
        sa.Column("mid", sa.Float(), nullable=True),
        sa.Column("study_values", sa.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_outcome_instruments_review",
        "outcome_instruments",
        ["review_id"],
    )

    # reviews.tool_per_study — Mixed-design RoB flag.
    with op.batch_alter_table("reviews") as batch:
        batch.add_column(
            sa.Column(
                "tool_per_study",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("0"),
            )
        )


def downgrade() -> None:
    with op.batch_alter_table("reviews") as batch:
        batch.drop_column("tool_per_study")
    op.drop_index(
        "ix_outcome_instruments_review", table_name="outcome_instruments"
    )
    op.drop_table("outcome_instruments")
    op.drop_index(
        "ix_narrative_synthesis_review", table_name="narrative_synthesis_entries"
    )
    op.drop_table("narrative_synthesis_entries")
    op.drop_index("ix_search_strategies_review", table_name="search_strategies")
    op.drop_table("search_strategies")
    op.drop_index("uq_mesh_terms_project_ui", table_name="mesh_terms")
    op.drop_table("mesh_terms")
