"""ingestion: Article.pmid + Article.source

Revision ID: 0009
Revises: 0008
Create Date: 2026-05-18 04:00:00.000000

Phase 8.6 — Ingestion. Adds two columns to ``articles``:

* ``pmid``  — nullable, indexed, supports future PubMed re-sync.
* ``source`` — provenance for every ingested article. Defaults to
  ``'upload'`` for all existing rows via the server_default during the
  upgrade; subsequent inserts must set the column explicitly (ORM
  default = ``'upload'``) so we strip the server_default afterwards.
"""
from alembic import op
import sqlalchemy as sa


revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("articles", schema=None) as batch_op:
        batch_op.add_column(sa.Column("pmid", sa.String(length=16), nullable=True))
        batch_op.add_column(
            sa.Column(
                "source",
                sa.String(length=16),
                nullable=False,
                server_default=sa.text("'upload'"),
            )
        )
        batch_op.create_index("ix_articles_pmid", ["pmid"])

    # Strip the server_default — every future insert sets `source` via the ORM
    # (the model carries a Python-side default of 'upload', and every ingest
    # call site sets it explicitly). The data-migration default has already
    # back-filled all existing rows above.
    with op.batch_alter_table("articles", schema=None) as batch_op:
        batch_op.alter_column("source", server_default=None)


def downgrade() -> None:
    with op.batch_alter_table("articles", schema=None) as batch_op:
        batch_op.drop_index("ix_articles_pmid")
        batch_op.drop_column("source")
        batch_op.drop_column("pmid")
