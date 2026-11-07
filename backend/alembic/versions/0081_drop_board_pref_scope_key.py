"""Упрощение portal_user_task_board_pref: убрать scope_key (единственный скоуп — global).

Revision ID: 0081_drop_board_pref_scope_key
Revises: 0080_drop_nav_node_legacy
Create Date: 2026-07-19

Контекст: 693c471 перевёл доску задач на единый глобальный скоуп — сервис
(``app/portal_collab/services/task_board_pref.py``) с этого момента всегда читает/пишет
строки с ``scope_key = 'global'``. Колонка ``scope_key`` осталась в схеме как «мёртвая»
константа, а составной ``UniqueConstraint(user_sub, scope_key)`` не несёт смысла — сосед
по домену ``portal_user_specialist_board_pref`` уже использует простой
``UniqueConstraint(user_sub)``.

До удаления колонки чистим строки с ``scope_key != 'global'`` (не-global скоуп существовал
только для per-nav_node настроек — недостижимы приложением уже с 693c471, т.к. RBAC по
nav_node и сам nav_node удалены), иначе ``UniqueConstraint(user_sub)`` может конфликтовать
с оставшимися дублями по одному user_sub.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0081_drop_board_pref_scope_key"
down_revision: str | None = "0080_drop_nav_node_legacy"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

logger = logging.getLogger(__name__)

_TABLE = "portal_user_task_board_pref"


def upgrade() -> None:
    conn = op.get_bind()

    orphaned = conn.execute(
        sa.text(f"SELECT count(*) FROM {_TABLE} WHERE scope_key != 'global'")  # noqa: S608
    ).scalar()
    logger.info("0081_drop_board_pref_scope_key: удаляем %s строк с scope_key != 'global'", orphaned)
    conn.execute(sa.text(f"DELETE FROM {_TABLE} WHERE scope_key != 'global'"))  # noqa: S608

    op.drop_constraint("uq_portal_user_task_board_pref_scope", _TABLE, type_="unique")
    op.drop_column(_TABLE, "scope_key")
    op.create_unique_constraint("uq_portal_user_task_board_pref_user", _TABLE, ["user_sub"])


def downgrade() -> None:
    op.drop_constraint("uq_portal_user_task_board_pref_user", _TABLE, type_="unique")
    op.add_column(_TABLE, sa.Column("scope_key", sa.String(40), nullable=False, server_default="global"))
    op.alter_column(_TABLE, "scope_key", server_default=None)
    op.create_unique_constraint(
        "uq_portal_user_task_board_pref_scope",
        _TABLE,
        ["user_sub", "scope_key"],
    )
