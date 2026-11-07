"""Удаление мёртвой колонки portal_user_profile.document_create_position.

Revision ID: 0083_drop_doc_create_position
Revises: 0082_quiz_attempt_answer_unique
Create Date: 2026-07-22

Контекст: аудит app/schemas под обновлённые правила. Фича «персональная позиция
нового документа» (top/bottom) была добавлена в d0fe959 и лишена UI/возможности
изменения в dd43f22 («убрать настройку позиции документа») — с этого момента
значение всегда 'top' (PortalAccountPreferencesUpdate не содержит этого поля).
Колонка, CHECK-constraint и Pydantic/TS-типы 'top'/'bottom' остались как мёртвый
код, вводящий в заблуждение о реально существующей возможности выбора.

Откат восстанавливает колонку со значением 'top' у всех строк (второе значение
'bottom' было недостижимо приложением уже с dd43f22 — данные не теряются).
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0083_drop_doc_create_position"
down_revision: str | None = "0082_quiz_attempt_answer_unique"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLE = "portal_user_profile"
_COLUMN = "document_create_position"
_CHECK_CONSTRAINT = "ck_portal_user_profile_document_create_position"


def upgrade() -> None:
    op.drop_constraint(_CHECK_CONSTRAINT, _TABLE, type_="check")
    op.drop_column(_TABLE, _COLUMN)


def downgrade() -> None:
    op.add_column(
        _TABLE,
        sa.Column(_COLUMN, sa.String(16), nullable=False, server_default="top"),
    )
    op.create_check_constraint(
        _CHECK_CONSTRAINT,
        _TABLE,
        f"{_COLUMN} IN ('top', 'bottom')",
    )
