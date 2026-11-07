"""Сид корневого документа «Документы для разработчиков».

Revision ID: 0076_dev_docs_root
Revises: 0075_task_file
Create Date: 2026-07-16

Имя ревизии не длиннее 32 символов — колонка alembic_version.version_num VARCHAR(32).
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0076_dev_docs_root"
down_revision: str | None = "0075_task_file"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Синхронизировано с app.portal_documents.constants
_DEV_DOCS_ROOT_ID = "a1b2c3d4-e5f6-4a70-8b9c-0d1e2f3a4b5c"
_DEV_DOCS_TITLE = "Документы для разработчиков"
_DOCS_SIBLING_TITLE = "Документы"


def upgrade() -> None:
    conn = op.get_bind()
    exists = conn.execute(
        sa.text("SELECT 1 FROM portal_document WHERE id = CAST(:id AS uuid)"),
        {"id": _DEV_DOCS_ROOT_ID},
    ).scalar()
    if exists:
        return

    # sort_order сразу после корневого «Документы», иначе в конец корней.
    sibling = conn.execute(
        sa.text(
            """
            SELECT sort_order FROM portal_document
            WHERE parent_document_id IS NULL
              AND deleted_at IS NULL
              AND title = :title
            ORDER BY sort_order ASC
            LIMIT 1
            """
        ),
        {"title": _DOCS_SIBLING_TITLE},
    ).scalar()

    if sibling is not None:
        sort_order = int(sibling) + 1
        conn.execute(
            sa.text(
                """
                UPDATE portal_document
                SET sort_order = sort_order + 1
                WHERE parent_document_id IS NULL
                  AND deleted_at IS NULL
                  AND sort_order >= :sort_order
                """
            ),
            {"sort_order": sort_order},
        )
    else:
        max_sort = conn.execute(
            sa.text(
                """
                SELECT COALESCE(MAX(sort_order), -1) FROM portal_document
                WHERE parent_document_id IS NULL AND deleted_at IS NULL
                """
            )
        ).scalar()
        sort_order = int(max_sort) + 1

    conn.execute(
        sa.text(
            """
            INSERT INTO portal_document (
                id, title, icon_emoji, nav_node_id, parent_document_id,
                author_sub, author_display_name, author_email,
                owner_sub, owner_email, body, sort_order,
                deleted_at, deleted_by_sub, deleted_by_display_name, deleted_by_email,
                created_at, updated_at
            ) VALUES (
                CAST(:id AS uuid), :title, NULL, NULL, NULL,
                'system', 'Система', NULL,
                NULL, NULL, NULL, :sort_order,
                NULL, NULL, NULL, NULL,
                now(), now()
            )
            """
        ),
        {"id": _DEV_DOCS_ROOT_ID, "title": _DEV_DOCS_TITLE, "sort_order": sort_order},
    )


def downgrade() -> None:
    """Удаляет только пустой корень; при наличии потомков откат пропускается."""
    conn = op.get_bind()
    child = conn.execute(
        sa.text(
            """
            SELECT 1 FROM portal_document
            WHERE parent_document_id = CAST(:id AS uuid)
            LIMIT 1
            """
        ),
        {"id": _DEV_DOCS_ROOT_ID},
    ).scalar()
    if child:
        return
    conn.execute(
        sa.text("DELETE FROM portal_document WHERE id = CAST(:id AS uuid)"),
        {"id": _DEV_DOCS_ROOT_ID},
    )
