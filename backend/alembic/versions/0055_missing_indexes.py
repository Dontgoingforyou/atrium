"""Добавление отсутствующих индексов БД (аудит производительности)."""

from __future__ import annotations

from alembic import op

revision = "0055_missing_indexes"
down_revision = "0054_time_entry_archive"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── High priority: горячие запросы ──────────────────────────────────────
    # «Все чаты пользователя» — PK(chat_id, user_sub) не покрывает фильтр только по user_sub
    op.create_index(
        "ix_portal_chat_member_user_sub",
        "portal_chat_member",
        ["user_sub"],
    )

    # Список чатов: ORDER BY updated_at DESC
    op.create_index(
        "ix_portal_chat_updated_at",
        "portal_chat",
        ["updated_at"],
    )

    # Сообщения чата: WHERE chat_id + ORDER BY created_at
    op.create_index(
        "ix_portal_chat_message_chat_id_created_at",
        "portal_chat_message",
        ["chat_id", "created_at"],
    )

    # Уведомления: WHERE recipient_sub + ORDER BY created_at DESC
    op.create_index(
        "ix_portal_notification_recipient_sub_created_at",
        "portal_notification",
        ["recipient_sub", "created_at"],
    )

    # Дедлайны задач на главной: фильтры/сортировка по due_at
    op.create_index(
        "ix_portal_task_due_at",
        "portal_task",
        ["due_at"],
    )

    # Документы по тегу: PK(document_id, tag_id) не начинается с tag_id
    op.create_index(
        "ix_portal_document_tag_tag_id",
        "portal_document_tag",
        ["tag_id"],
    )

    # Telegram binding: get_binding_by_chat_id
    op.create_index(
        "ix_portal_telegram_binding_telegram_chat_id",
        "portal_telegram_binding",
        ["telegram_chat_id"],
    )

    # ── Medium priority: ощутимо при росте ──────────────────────────────────
    # Доска задач по разделу: WHERE nav_node_id + status + ORDER BY position
    op.create_index(
        "ix_portal_task_nav_node_id_status_position",
        "portal_task",
        ["nav_node_id", "status", "position"],
    )

    # Тред комментариев к задаче: WHERE task_id + ORDER BY created_at
    op.create_index(
        "ix_portal_task_comment_task_id_created_at",
        "portal_task_comment",
        ["task_id", "created_at"],
    )

    # Список договорённостей: ORDER BY created_at
    op.create_index(
        "ix_portal_agreement_created_at",
        "portal_agreement",
        ["created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_portal_agreement_created_at", table_name="portal_agreement")
    op.drop_index("ix_portal_task_comment_task_id_created_at", table_name="portal_task_comment")
    op.drop_index("ix_portal_task_nav_node_id_status_position", table_name="portal_task")
    op.drop_index("ix_portal_telegram_binding_telegram_chat_id", table_name="portal_telegram_binding")
    op.drop_index("ix_portal_document_tag_tag_id", table_name="portal_document_tag")
    op.drop_index("ix_portal_task_due_at", table_name="portal_task")
    op.drop_index("ix_portal_notification_recipient_sub_created_at", table_name="portal_notification")
    op.drop_index("ix_portal_chat_message_chat_id_created_at", table_name="portal_chat_message")
    op.drop_index("ix_portal_chat_updated_at", table_name="portal_chat")
    op.drop_index("ix_portal_chat_member_user_sub", table_name="portal_chat_member")
