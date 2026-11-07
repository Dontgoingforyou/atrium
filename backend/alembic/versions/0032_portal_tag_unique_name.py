"""Уникальность имени тега по lower(btrim(name)) и дедупликация данных.

Revision ID: 0032_portal_tag_unique_name
Revises: 0031_portal_doc_hierarchy
Create Date: 2026-04-27

Data migration не идемпотентна (повторный upgrade на «грязных» данных может дать неверный результат).
Downgrade удаляет только индекс; обратный merge дубликатов не выполняется.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0032_portal_tag_unique_name"
down_revision: str | Sequence[str] | None = "0031_portal_doc_hierarchy"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    # --- Дедупликация по lower(btrim(name)): победитель — минимальный id (array_agg: min(uuid) в старых PG нет)
    op.execute(
        sa.text(
            """
            WITH winners AS (
                SELECT lower(btrim(name)) AS nk, (array_agg(id ORDER BY id))[1] AS winner_id
                FROM portal_tag
                GROUP BY lower(btrim(name))
            ),
            losers AS (
                SELECT t.id AS loser_id, w.winner_id AS winner_id
                FROM portal_tag t
                INNER JOIN winners w ON lower(btrim(t.name)) = w.nk AND t.id <> w.winner_id
            )
            INSERT INTO portal_document_tag (document_id, tag_id)
            SELECT p.document_id, l.winner_id
            FROM portal_document_tag p
            INNER JOIN losers l ON p.tag_id = l.loser_id
            ON CONFLICT DO NOTHING
            """
        )
    )
    op.execute(
        sa.text(
            """
            WITH winners AS (
                SELECT lower(btrim(name)) AS nk, (array_agg(id ORDER BY id))[1] AS winner_id
                FROM portal_tag
                GROUP BY lower(btrim(name))
            ),
            losers AS (
                SELECT t.id AS loser_id, w.winner_id AS winner_id
                FROM portal_tag t
                INNER JOIN winners w ON lower(btrim(t.name)) = w.nk AND t.id <> w.winner_id
            )
            DELETE FROM portal_document_tag p
            USING losers l
            WHERE p.tag_id = l.loser_id
            """
        )
    )

    op.execute(
        sa.text(
            """
            WITH winners AS (
                SELECT lower(btrim(name)) AS nk, (array_agg(id ORDER BY id))[1] AS winner_id
                FROM portal_tag
                GROUP BY lower(btrim(name))
            ),
            losers AS (
                SELECT t.id AS loser_id, w.winner_id AS winner_id
                FROM portal_tag t
                INNER JOIN winners w ON lower(btrim(t.name)) = w.nk AND t.id <> w.winner_id
            )
            INSERT INTO portal_task_tag (task_id, tag_id)
            SELECT p.task_id, l.winner_id
            FROM portal_task_tag p
            INNER JOIN losers l ON p.tag_id = l.loser_id
            ON CONFLICT DO NOTHING
            """
        )
    )
    op.execute(
        sa.text(
            """
            WITH winners AS (
                SELECT lower(btrim(name)) AS nk, (array_agg(id ORDER BY id))[1] AS winner_id
                FROM portal_tag
                GROUP BY lower(btrim(name))
            ),
            losers AS (
                SELECT t.id AS loser_id, w.winner_id AS winner_id
                FROM portal_tag t
                INNER JOIN winners w ON lower(btrim(t.name)) = w.nk AND t.id <> w.winner_id
            )
            DELETE FROM portal_task_tag p
            USING losers l
            WHERE p.tag_id = l.loser_id
            """
        )
    )

    op.execute(
        sa.text(
            """
            WITH winners AS (
                SELECT lower(btrim(name)) AS nk, (array_agg(id ORDER BY id))[1] AS winner_id
                FROM portal_tag
                GROUP BY lower(btrim(name))
            ),
            losers AS (
                SELECT t.id AS loser_id
                FROM portal_tag t
                INNER JOIN winners w ON lower(btrim(t.name)) = w.nk AND t.id <> w.winner_id
            )
            DELETE FROM portal_tag WHERE id IN (SELECT loser_id FROM losers)
            """
        )
    )

    # Без CONCURRENTLY — таблица portal_tag небольшая
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_portal_tag_name_lower ON portal_tag (lower(btrim(name)))")


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    op.execute(sa.text("DROP INDEX IF EXISTS uq_portal_tag_name_lower"))
