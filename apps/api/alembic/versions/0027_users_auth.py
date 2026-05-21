"""Phase S1 — Multi-user auth.

Revision ID: 0027
Revises: 0026
Create Date: 2026-05-21 11:00:00.000000

Adds three tables backing real authentication + invitation flow:

* ``users`` — account records (email + password_hash + display_name).
* ``sessions`` — server-side session rows (httpOnly cookie surface). The
  cookie value is a 32-byte URL-safe random string; only its SHA-256 hash
  ever touches the DB.
* ``invitations`` — pending per-project invites. Token works the same way
  as sessions (raw → SHA-256 → DB).
* ``audit_events`` — light audit log (signup / login / logout /
  password-change / invitation-create / invitation-accept).

All foreign keys are explicitly named (lesson from 0014/0016/0021).
"""
from alembic import op
import sqlalchemy as sa


revision = "0027"
down_revision = "0026"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("display_name", sa.String(length=200), nullable=False),
        sa.Column(
            "is_admin",
            sa.Boolean(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "sessions",
        sa.Column("id", sa.String(length=32), primary_key=True),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("token_hash", sa.String(length=128), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "last_seen_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("user_agent", sa.String(length=500), nullable=True),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_sessions_user_id",
            ondelete="CASCADE",
        ),
    )
    op.create_index(
        "ix_sessions_token_hash", "sessions", ["token_hash"], unique=True
    )
    op.create_index("ix_sessions_user_id", "sessions", ["user_id"])

    op.create_table(
        "invitations",
        sa.Column("id", sa.String(length=32), primary_key=True),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("project_id", sa.String(length=32), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("token_hash", sa.String(length=128), nullable=False),
        sa.Column("invited_by", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("accepted_by", sa.String(length=64), nullable=True),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            name="fk_invitations_project_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["invited_by"],
            ["users.id"],
            name="fk_invitations_invited_by",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["accepted_by"],
            ["users.id"],
            name="fk_invitations_accepted_by",
            ondelete="SET NULL",
        ),
    )
    op.create_index(
        "ix_invitations_token_hash", "invitations", ["token_hash"], unique=True
    )
    op.create_index(
        "ix_invitations_project_email", "invitations", ["project_id", "email"]
    )

    op.create_table(
        "audit_events",
        sa.Column("id", sa.String(length=32), primary_key=True),
        sa.Column("user_id", sa.String(length=64), nullable=True),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_audit_events_user_action_created",
        "audit_events",
        ["user_id", "action", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_audit_events_user_action_created", table_name="audit_events")
    op.drop_table("audit_events")

    op.drop_index("ix_invitations_project_email", table_name="invitations")
    op.drop_index("ix_invitations_token_hash", table_name="invitations")
    op.drop_table("invitations")

    op.drop_index("ix_sessions_user_id", table_name="sessions")
    op.drop_index("ix_sessions_token_hash", table_name="sessions")
    op.drop_table("sessions")

    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
