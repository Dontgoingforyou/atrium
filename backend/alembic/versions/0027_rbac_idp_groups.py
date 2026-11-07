"""Удаление catalog portal_role; M2M на строки idp_group (Keycloak); чек-лист role_slug -> idp_group.

Revision ID: 0027_rbac_idp_groups  (≤32 символа для alembic_version.version_num)
Revises: 0026_normalize_task_status
Create Date: 2026-04-26

downgrade: откат не поднимает данные в portal_role / user_portal_role (требуется вручную).
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0027_rbac_idp_groups"
down_revision: str | None = "0026_normalize_task_status"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_table("portal_nav_node_role")
    op.drop_table("portal_learning_material_role")
    op.drop_table("user_portal_role")
    op.drop_table("portal_role")

    op.execute(sa.text("ALTER TABLE portal_checklist RENAME COLUMN role_slug TO idp_group"))
    bind = op.get_bind()
    if bind is not None and bind.dialect.name == "postgresql":
        op.execute(
            sa.text("ALTER INDEX IF EXISTS ix_portal_checklist_role_slug RENAME TO ix_portal_checklist_idp_group")
        )

    op.create_table(
        "portal_nav_node_idp_group",
        sa.Column("node_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("idp_group", sa.String(255), nullable=False),
        sa.ForeignKeyConstraint(["node_id"], ["portal_nav_node.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("node_id", "idp_group", name="pk_portal_nav_node_idp_group"),
    )
    op.create_index("ix_portal_nav_node_idp_group_idp_group", "portal_nav_node_idp_group", ["idp_group"])

    op.create_table(
        "portal_learning_material_idp_group",
        sa.Column("material_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("idp_group", sa.String(255), nullable=False),
        sa.ForeignKeyConstraint(["material_id"], ["portal_learning_material.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("material_id", "idp_group", name="pk_portal_learning_material_idp_group"),
    )
    op.create_index("ix_p_lm_idp_group", "portal_learning_material_idp_group", ["idp_group"])


def downgrade() -> None:
    # Восстановление portal_role и M2M по UUID не автоматизировано; только откат схемы.
    op.drop_index("ix_p_lm_idp_group", table_name="portal_learning_material_idp_group")
    op.drop_table("portal_learning_material_idp_group")
    op.drop_index("ix_portal_nav_node_idp_group_idp_group", table_name="portal_nav_node_idp_group")
    op.drop_table("portal_nav_node_idp_group")

    op.execute(sa.text("ALTER TABLE portal_checklist RENAME COLUMN idp_group TO role_slug"))
    bind = op.get_bind()
    if bind is not None and bind.dialect.name == "postgresql":
        op.execute(
            sa.text("ALTER INDEX IF EXISTS ix_portal_checklist_idp_group RENAME TO ix_portal_checklist_role_slug")
        )

    op.create_table(
        "portal_role",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("slug", sa.String(64), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug", name="uq_portal_role_slug"),
    )
    op.create_table(
        "user_portal_role",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_sub", sa.String(255), nullable=False),
        sa.Column("user_display_name", sa.String(255), nullable=True),
        sa.Column("user_email", sa.String(255), nullable=True),
        sa.Column("role_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(["role_id"], ["portal_role.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_sub", "role_id", name="uq_user_portal_role_sub_role"),
    )
    op.create_index("ix_user_portal_role_user_sub", "user_portal_role", ["user_sub"], unique=False)

    op.create_table(
        "portal_nav_node_role",
        sa.Column("node_id", sa.Uuid(), nullable=False),
        sa.Column("role_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(["node_id"], ["portal_nav_node.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["role_id"], ["portal_role.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("node_id", "role_id"),
    )
    op.create_table(
        "portal_learning_material_role",
        sa.Column("material_id", sa.Uuid(), nullable=False),
        sa.Column("role_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(["material_id"], ["portal_learning_material.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["role_id"], ["portal_role.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("material_id", "role_id"),
    )
