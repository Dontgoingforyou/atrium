"""Материалы обучения: доступ по ролям через M2M вместо JSON.

Revision ID: 0017_learning_material_roles
Revises: 0016_portal_learning
Create Date: 2026-04-20
"""

from __future__ import annotations

import json
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0017_learning_material_roles"
down_revision: str | None = "0016_portal_learning"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "portal_learning_material_role",
        sa.Column(
            "material_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("portal_learning_material.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "role_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("portal_role.id", ondelete="CASCADE"),
            primary_key=True,
        ),
    )

    conn = op.get_bind()
    rows = conn.execute(sa.text("SELECT id, role_slugs_json FROM portal_learning_material")).mappings().all()
    for row in rows:
        mid = row["id"]
        raw = row["role_slugs_json"] or "[]"
        try:
            slugs = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            slugs = []
        if not isinstance(slugs, list):
            continue
        for slug in slugs:
            if not isinstance(slug, str) or not slug.strip():
                continue
            rid = conn.execute(
                sa.text("SELECT id FROM portal_role WHERE slug = :slug LIMIT 1"),
                {"slug": slug.strip()},
            ).scalar()
            if rid is None:
                continue
            exists = conn.execute(
                sa.text(
                    "SELECT 1 FROM portal_learning_material_role WHERE material_id = :mid AND role_id = :rid LIMIT 1"
                ),
                {"mid": mid, "rid": rid},
            ).scalar()
            if exists:
                continue
            conn.execute(
                sa.text("INSERT INTO portal_learning_material_role (material_id, role_id) VALUES (:mid, :rid)"),
                {"mid": mid, "rid": rid},
            )

    op.drop_column("portal_learning_material", "role_slugs_json")


def downgrade() -> None:
    op.add_column(
        "portal_learning_material",
        sa.Column("role_slugs_json", sa.Text(), nullable=False, server_default="[]"),
    )

    conn = op.get_bind()
    rows = conn.execute(sa.text("SELECT id FROM portal_learning_material")).mappings().all()
    for row in rows:
        mid = row["id"]
        rows = conn.execute(
            sa.text(
                "SELECT r.slug FROM portal_role r "
                "JOIN portal_learning_material_role m ON m.role_id = r.id "
                "WHERE m.material_id = :mid ORDER BY r.slug"
            ),
            {"mid": mid},
        ).fetchall()
        slugs = [r[0] for r in rows]
        payload = json.dumps(slugs, ensure_ascii=False)
        conn.execute(
            sa.text("UPDATE portal_learning_material SET role_slugs_json = :js WHERE id = :mid"),
            {"js": payload, "mid": mid},
        )

    op.drop_table("portal_learning_material_role")
