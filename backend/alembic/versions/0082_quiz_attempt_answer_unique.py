"""Уникальное ограничение (attempt_id, question_id) в portal_quiz_attempt_answer.

Revision ID: 0082_quiz_attempt_answer_unique
Revises: 0081_drop_board_pref_scope_key
Create Date: 2026-07-21

Контекст: аудит app/portal_learning под обновлённые правила (services.mdc, «Гонки»).
`submit_attempt` проверяет `finished_at is None`, затем пишет ответы — без блокировки
это допускает параллельный повторный submit одной попытки, который задваивает строки
ответов на один и тот же вопрос. UNIQUE(attempt_id, question_id) превращает второй
параллельный коммит в `IntegrityError` -> `ConflictError` на уровне сервиса, вместо
задвоенных данных.

Перед созданием ограничения чистим уже накопленные дубликаты (если были) — оставляем
одну (последнюю по `id`) строку на пару (attempt_id, question_id).
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0082_quiz_attempt_answer_unique"
down_revision: str | None = "0081_drop_board_pref_scope_key"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLE = "portal_quiz_attempt_answer"


def upgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        sa.text(
            f"DELETE FROM {_TABLE} a USING {_TABLE} b "  # noqa: S608
            "WHERE a.attempt_id = b.attempt_id AND a.question_id = b.question_id AND a.id < b.id"
        )
    )
    op.create_unique_constraint(
        "uq_quiz_attempt_answer_attempt_question",
        _TABLE,
        ["attempt_id", "question_id"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_quiz_attempt_answer_attempt_question", _TABLE, type_="unique")
