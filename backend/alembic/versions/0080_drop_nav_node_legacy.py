"""Полное удаление legacy nav_node: колонки nav_node_id/nav_node_comment_id, portal_nav_node_comment.

Revision ID: 0080_drop_nav_node_legacy
Revises: 0079_chat_voice_transcript
Create Date: 2026-07-19

Контекст: таблица portal_nav_node (и её FK) уже удалена миграцией 0037_drop_portal_nav_node
(«Разделы полностью удалены из UI-логики»). RBAC по узлам навигации превращён в no-op-заглушки
в app/services/rbac.py. Тем не менее колонка nav_node_id (+ nav_node_comment_id у уведомлений)
осталась на 10 таблицах, а таблица portal_nav_node_comment («комментарии к разделу») не
использовалась ни одним HTTP/WS-роутером — только тестами. Эта миграция дочищает БД:

  1. Переписывает CHECK-constraint ck_portal_notification_context без ветки section_mention.
  2. Дропает колонки nav_node_id/nav_node_comment_id у portal_notification + зависимые индексы.
  3. Дропает таблицу portal_nav_node_comment (её собственный FK на portal_nav_node уже снят в 0037).
  4. Дропает колонку nav_node_id (+ индексы) на оставшихся 9 таблицах.

FK-ограничения на nav_node_id/nav_node_comment_id уже отсутствуют (сняты в 0037 либо дропаются
автоматически вместе с колонкой) — отдельный DROP CONSTRAINT не требуется.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0080_drop_nav_node_legacy"
down_revision: str | None = "0079_chat_voice_transcript"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

logger = logging.getLogger(__name__)

# Таблицы (кроме portal_notification/portal_nav_node_comment, обрабатываемых отдельно)
# с «мёртвой» колонкой nav_node_id и её индексом.
_SIMPLE_NAV_NODE_TABLES: tuple[tuple[str, str], ...] = (
    ("portal_document", "ix_portal_document_nav_node_id"),
    ("portal_task_column", "ix_portal_task_column_nav_node_id"),
    ("portal_chat", "ix_portal_chat_nav_node_id"),
    ("portal_agreement", "ix_portal_agreement_nav_node_id"),
    ("portal_user_task_board_pref", "ix_portal_user_task_board_pref_nav_node_id"),
    ("portal_contract", "ix_portal_contract_nav_node_id"),
    ("portal_invoice", "ix_portal_invoice_nav_node_id"),
    ("portal_procurement_request", "ix_portal_procurement_request_nav_node_id"),
    ("portal_learning_material", "ix_portal_learning_material_nav_node_id"),
)


def _log_orphan_counts(conn: sa.Connection) -> None:
    """Диагностика для протокола: сколько «мёртвых» значений теряем (не блокирует апгрейд)."""
    tables = [t for t, _ in _SIMPLE_NAV_NODE_TABLES] + ["portal_task"]
    for table in tables:
        count = conn.execute(sa.text(f"SELECT count(*) FROM {table} WHERE nav_node_id IS NOT NULL")).scalar()  # noqa: S608
        logger.info("0080_drop_nav_node_legacy: %s.nav_node_id IS NOT NULL — %s строк", table, count)
    section_mentions = conn.execute(
        sa.text("SELECT count(*) FROM portal_notification WHERE type = 'section_mention'")
    ).scalar()
    logger.info(
        "0080_drop_nav_node_legacy: portal_notification WHERE type='section_mention' — %s строк",
        section_mentions,
    )


def upgrade() -> None:
    conn = op.get_bind()
    _log_orphan_counts(conn)

    # 1. CHECK-constraint уведомлений: убираем ветку section_mention, ссылки на nav_node_*.
    op.drop_constraint("ck_portal_notification_context", "portal_notification", type_="check")
    op.create_check_constraint(
        "ck_portal_notification_context",
        "portal_notification",
        "(type IN ('task_mention', 'task_assigned') AND task_id IS NOT NULL AND document_id IS NULL AND "
        "document_comment_id IS NULL AND "
        "(type != 'task_mention' OR comment_id IS NOT NULL) AND "
        "(type != 'task_assigned' OR comment_id IS NULL)) OR "
        "(type = 'document_mention' AND task_id IS NULL AND comment_id IS NULL AND "
        "document_id IS NOT NULL AND document_comment_id IS NOT NULL) OR "
        "(type = 'document_trashed' AND task_id IS NULL AND comment_id IS NULL AND "
        "document_id IS NOT NULL AND document_comment_id IS NULL)",
    )

    # 2. portal_notification: индексы + колонки nav_node_id/nav_node_comment_id.
    op.drop_index("uq_portal_notif_recipient_nav_comment", table_name="portal_notification")
    op.drop_index("ix_portal_notification_nav_node_comment_id", table_name="portal_notification")
    op.drop_index("ix_portal_notification_nav_node_id", table_name="portal_notification")
    op.drop_column("portal_notification", "nav_node_comment_id")
    op.drop_column("portal_notification", "nav_node_id")

    # 3. portal_nav_node_comment: «комментарии к разделу» — не использовались HTTP/WS API.
    op.drop_table("portal_nav_node_comment")

    # 4. portal_task: помимо одиночного индекса, есть составной (nav_node_id, status, position).
    op.drop_index("ix_portal_task_nav_node_id_status_position", table_name="portal_task")
    op.drop_index("ix_portal_task_nav_node_id", table_name="portal_task")
    op.drop_column("portal_task", "nav_node_id")

    # 5. Остальные таблицы с одиночной колонкой nav_node_id.
    for table, index_name in _SIMPLE_NAV_NODE_TABLES:
        op.drop_index(index_name, table_name=table)
        op.drop_column(table, "nav_node_id")


def downgrade() -> None:
    # Восстановление не предусмотрено — миграция необратима (аналогично 0037).
    raise NotImplementedError("Downgrade не поддерживается для этой миграции.")
