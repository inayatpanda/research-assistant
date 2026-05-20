"""MP16 — Citation depth.

Revision ID: 0025
Revises: 0024
Create Date: 2026-05-20 16:00:00.000000

Adds three new optional columns:

* ``articles.reference_type`` (TEXT, default 'journal_article') — categorises
  the reference so grey-literature variants (theses, preprints, registry
  records, web resources) can be rendered with their style-specific suffix.
* ``articles.url`` (TEXT, NULL) — surfaced by web-resource / registry refs
  whose authoritative location is a URL rather than a DOI.
* ``projects.inline_citation_mode`` (TEXT, default 'bracket_numeric') —
  controls how the TipTap CitationNodeView renders inline citations:
  ``bracket_numeric`` | ``superscript_numeric`` | ``author_year_parens``.

All three columns are nullable / have defaults so existing rows are
back-populated by SQLite's column-default semantics (UPDATE is a no-op).
"""
from alembic import op
import sqlalchemy as sa


revision = "0025"
down_revision = "0024"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "articles",
        sa.Column(
            "reference_type",
            sa.String(length=32),
            nullable=False,
            server_default="journal_article",
        ),
    )
    op.add_column(
        "articles",
        sa.Column("url", sa.Text(), nullable=True),
    )
    # Explicit UPDATE to back-populate already-existing rows in case the
    # backend uses a DB engine that does not retroactively apply the
    # server_default to existing rows.
    op.execute(
        "UPDATE articles SET reference_type = 'journal_article' "
        "WHERE reference_type IS NULL"
    )

    op.add_column(
        "projects",
        sa.Column(
            "inline_citation_mode",
            sa.String(length=32),
            nullable=False,
            server_default="bracket_numeric",
        ),
    )
    op.execute(
        "UPDATE projects SET inline_citation_mode = 'bracket_numeric' "
        "WHERE inline_citation_mode IS NULL"
    )


def downgrade() -> None:
    with op.batch_alter_table("projects") as batch:
        batch.drop_column("inline_citation_mode")
    with op.batch_alter_table("articles") as batch:
        batch.drop_column("url")
        batch.drop_column("reference_type")
