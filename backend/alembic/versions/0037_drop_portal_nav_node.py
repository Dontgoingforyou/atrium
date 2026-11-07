"""drop portal_nav_node table

Revision ID: 0037_drop_portal_nav_node
Revises: 0036_drop_document_type
Create Date: 2026-05-01

Разделы (nav-узлы) полностью удалены из UI-логики.
Перед удалением таблицы:
  1. Явно обнуляем nav_node_id в portal_document (FK ON DELETE SET NULL сделал бы это
     автоматически, но явный UPDATE безопаснее при batch-миграции).
  2. Удаляем FK-ограничение portal_document -> portal_nav_node.
  3. Удаляем таблицу portal_nav_node и все зависимые таблицы
     (portal_nav_node_idp_group, portal_nav_node_favorite).
"""

from __future__ import annotations

from alembic import op

revision = "0037_drop_portal_nav_node"
down_revision = "0036_drop_document_type"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Обнуляем ссылки на nav-узлы в документах
    op.execute("UPDATE portal_document SET nav_node_id = NULL WHERE nav_node_id IS NOT NULL")

    # 2. Удаляем FK-ограничение (имя может отличаться, используем IF EXISTS через DDL)
    op.execute(
        """
        DO $$
        DECLARE
            r RECORD;
        BEGIN
            FOR r IN
                SELECT conname, conrelid::regclass AS tbl
                FROM pg_constraint
                WHERE contype = 'f'
                  AND confrelid = 'portal_nav_node'::regclass
            LOOP
                EXECUTE format('ALTER TABLE %s DROP CONSTRAINT IF EXISTS %I', r.tbl, r.conname);
            END LOOP;
        END;
        $$;
        """
    )

    # 3. Удаляем зависимые таблицы и саму portal_nav_node
    op.execute("DROP TABLE IF EXISTS portal_nav_node_idp_group CASCADE")
    op.execute("DROP TABLE IF EXISTS portal_nav_node_favorite CASCADE")
    op.execute("DROP TABLE IF EXISTS portal_nav_node CASCADE")


def downgrade() -> None:
    # Восстановление таблицы не предусмотрено — миграция необратима.
    raise NotImplementedError("Downgrade не поддерживается для этой миграции.")
