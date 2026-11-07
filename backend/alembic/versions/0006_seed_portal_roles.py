"""Seed предустановленных ролей портала из ТЗ (эпик 5).

Revision ID: 0006_seed_portal_roles
Revises: 0005_display_names
Create Date: 2026-04-07

"""

import uuid
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0006_seed_portal_roles"
down_revision: str | Sequence[str] | None = "0005_display_names"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_NAMESPACE = uuid.UUID("a1b2c3d4-e5f6-7890-abcd-ef1234567890")

_SEED = [
    ("manager", "Руководитель", "Полный доступ к аналитике, финансам, всем разделам портала и управлению командой."),
    (
        "account-manager",
        "Аккаунт-менеджер",
        "Работа с клиентами, коммуникациями, реестром договорённостей и регламентами.",
    ),
    ("project-manager", "Проект-менеджер", "Управление задачами, командой, онбордингом и проектной документацией."),
    ("procurement", "Закупщик", "Доступ к разделу закупок: заявки, конкурсы, контрагенты, шаблоны документов."),
    ("contractor", "Подрядчик", "Ограниченный доступ: регламенты, задачи и материалы, относящиеся к своим проектам."),
]

_EXPECTED_SLUGS = frozenset(slug for slug, _, __ in _SEED)


def upgrade() -> None:
    rows = [
        {"id": uuid.uuid5(_NAMESPACE, slug), "slug": slug, "name": name, "description": desc}
        for slug, name, desc in _SEED
    ]
    op.bulk_insert(
        sa.table(
            "portal_role",
            sa.column("id", postgresql.UUID(as_uuid=True)),
            sa.column("slug", sa.String()),
            sa.column("name", sa.String()),
            sa.column("description", sa.Text()),
        ),
        rows,
    )


def downgrade() -> None:
    op.execute(
        sa.text("DELETE FROM portal_role WHERE slug = ANY(:slugs)").bindparams(
            slugs=list(_EXPECTED_SLUGS),
        )
    )
