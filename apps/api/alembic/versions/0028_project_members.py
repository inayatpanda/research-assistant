"""Phase S1 — Project membership + RBAC.

Revision ID: 0028
Revises: 0027
Create Date: 2026-05-21 11:30:00.000000

Adds the ``project_members`` join table powering per-project sharing and
role-based access control (owner / editor / viewer).

Also performs a one-time data migration:
* Inserts a single ``local@research-assistant.local`` legacy user row so
  every existing ``projects.user_id`` value points at a valid users row.
* For every existing project, inserts a matching ``project_members`` row
  with role ``owner``.

After this migration, access is determined by ``project_members``;
``projects.user_id`` is retained as a denormalised "creator tag" but is
no longer used for authorisation.
"""
from alembic import op
import sqlalchemy as sa


revision = "0028"
down_revision = "0027"
branch_labels = None
depends_on = None


LEGACY_USER_EMAIL = "local@research-assistant.local"


def upgrade() -> None:
    op.create_table(
        "project_members",
        sa.Column("id", sa.String(length=32), primary_key=True),
        sa.Column("project_id", sa.String(length=32), nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("invited_by", sa.String(length=64), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            name="fk_project_members_project_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_project_members_user_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["invited_by"],
            ["users.id"],
            name="fk_project_members_invited_by",
            ondelete="SET NULL",
        ),
    )
    op.create_index(
        "uq_project_members_project_user",
        "project_members",
        ["project_id", "user_id"],
        unique=True,
    )
    op.create_index(
        "ix_project_members_user", "project_members", ["user_id"]
    )

    # ── Data migration — give legacy single-user data a real owner row ──
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    # projects table may not exist yet in some test contexts; gate to be safe.
    table_names = inspector.get_table_names()
    if "projects" not in table_names or "users" not in table_names:
        return

    rows = bind.execute(
        sa.text("SELECT id, user_id FROM projects")
    ).fetchall()
    if not rows:
        return

    # Discover the distinct legacy user_ids and seed a User row for each.
    legacy_user_ids = sorted({r[1] for r in rows if r[1]})
    for legacy_id in legacy_user_ids:
        # Skip if a real user row already exists with this id.
        existing = bind.execute(
            sa.text("SELECT 1 FROM users WHERE id = :id"),
            {"id": legacy_id},
        ).first()
        if existing:
            continue
        email = (
            LEGACY_USER_EMAIL
            if legacy_id == "local-user"
            else f"{legacy_id}@research-assistant.local"
        )
        # Empty password_hash means this row cannot be logged into directly —
        # the "claim legacy data" flow re-points rows to a real user.
        bind.execute(
            sa.text(
                "INSERT INTO users (id, email, password_hash, display_name, is_admin, created_at, updated_at) "
                "VALUES (:id, :email, '', :name, 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
            ),
            {
                "id": legacy_id,
                "email": email,
                "name": "Legacy local user",
            },
        )

    # Seed owner rows for every existing project.
    for project_id, user_id in rows:
        # idempotency belt-and-braces
        existing = bind.execute(
            sa.text(
                "SELECT 1 FROM project_members WHERE project_id = :p AND user_id = :u"
            ),
            {"p": project_id, "u": user_id},
        ).first()
        if existing:
            continue
        import uuid as _uuid

        bind.execute(
            sa.text(
                "INSERT INTO project_members "
                "(id, project_id, user_id, role, invited_by, created_at) "
                "VALUES (:id, :p, :u, 'owner', NULL, CURRENT_TIMESTAMP)"
            ),
            {
                "id": _uuid.uuid4().hex,
                "p": project_id,
                "u": user_id,
            },
        )


def downgrade() -> None:
    op.drop_index("ix_project_members_user", table_name="project_members")
    op.drop_index(
        "uq_project_members_project_user", table_name="project_members"
    )
    op.drop_table("project_members")
