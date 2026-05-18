"""ICMJE structured front-matter

Revision ID: 0011
Revises: 0010
Create Date: 2026-05-18 10:00:00.000000

Phase 10 — Authors, affiliations, author_affiliations (m2m), contributions
(CRediT), project_frontmatter (one row per project).
"""
from alembic import op
import sqlalchemy as sa


revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "authors",
        sa.Column("id", sa.String(length=32), primary_key=True, nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column(
            "project_id",
            sa.String(length=32),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("full_name", sa.String(length=500), nullable=False),
        sa.Column("given_name", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("family_name", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("orcid", sa.String(length=19), nullable=True),
        sa.Column("email", sa.String(length=320), nullable=True),
        sa.Column(
            "is_corresponding",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
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
    with op.batch_alter_table("authors", schema=None) as batch_op:
        batch_op.create_index("ix_authors_project_user", ["project_id", "user_id"])
        batch_op.create_index("ix_authors_user", ["user_id"])

    op.create_table(
        "affiliations",
        sa.Column("id", sa.String(length=32), primary_key=True, nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column(
            "project_id",
            sa.String(length=32),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=500), nullable=False),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("city", sa.String(length=255), nullable=True),
        sa.Column("country", sa.String(length=255), nullable=True),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    with op.batch_alter_table("affiliations", schema=None) as batch_op:
        batch_op.create_index(
            "ix_affiliations_project_user", ["project_id", "user_id"]
        )
        batch_op.create_index("ix_affiliations_user", ["user_id"])

    op.create_table(
        "author_affiliations",
        sa.Column("id", sa.String(length=32), primary_key=True, nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column(
            "author_id",
            sa.String(length=32),
            sa.ForeignKey("authors.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "affiliation_id",
            sa.String(length=32),
            sa.ForeignKey("affiliations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
    )
    with op.batch_alter_table("author_affiliations", schema=None) as batch_op:
        batch_op.create_index(
            "uq_author_affiliation_pair",
            ["author_id", "affiliation_id"],
            unique=True,
        )
        batch_op.create_index("ix_author_affiliations_user", ["user_id"])

    op.create_table(
        "contributions",
        sa.Column("id", sa.String(length=32), primary_key=True, nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column(
            "author_id",
            sa.String(length=32),
            sa.ForeignKey("authors.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("role", sa.String(length=64), nullable=False),
    )
    with op.batch_alter_table("contributions", schema=None) as batch_op:
        batch_op.create_index(
            "uq_contribution_author_role",
            ["author_id", "role"],
            unique=True,
        )
        batch_op.create_index("ix_contributions_user", ["user_id"])

    op.create_table(
        "project_frontmatter",
        sa.Column("id", sa.String(length=32), primary_key=True, nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column(
            "project_id",
            sa.String(length=32),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("funding_statement", sa.Text(), nullable=True),
        sa.Column("funders", sa.JSON(), nullable=True),
        sa.Column("ethics_irb", sa.Text(), nullable=True),
        sa.Column("ethics_approval_number", sa.Text(), nullable=True),
        sa.Column("ethics_consent", sa.Text(), nullable=True),
        sa.Column("conflicts_statement", sa.Text(), nullable=True),
        sa.Column(
            "structured_abstract_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column("structured_abstract", sa.JSON(), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    with op.batch_alter_table("project_frontmatter", schema=None) as batch_op:
        batch_op.create_index(
            "uq_project_frontmatter_project_user",
            ["project_id", "user_id"],
            unique=True,
        )
        batch_op.create_index("ix_project_frontmatter_user", ["user_id"])


def downgrade() -> None:
    with op.batch_alter_table("project_frontmatter", schema=None) as batch_op:
        batch_op.drop_index("ix_project_frontmatter_user")
        batch_op.drop_index("uq_project_frontmatter_project_user")
    op.drop_table("project_frontmatter")

    with op.batch_alter_table("contributions", schema=None) as batch_op:
        batch_op.drop_index("ix_contributions_user")
        batch_op.drop_index("uq_contribution_author_role")
    op.drop_table("contributions")

    with op.batch_alter_table("author_affiliations", schema=None) as batch_op:
        batch_op.drop_index("ix_author_affiliations_user")
        batch_op.drop_index("uq_author_affiliation_pair")
    op.drop_table("author_affiliations")

    with op.batch_alter_table("affiliations", schema=None) as batch_op:
        batch_op.drop_index("ix_affiliations_user")
        batch_op.drop_index("ix_affiliations_project_user")
    op.drop_table("affiliations")

    with op.batch_alter_table("authors", schema=None) as batch_op:
        batch_op.drop_index("ix_authors_user")
        batch_op.drop_index("ix_authors_project_user")
    op.drop_table("authors")
