"""Сервисный слой: управление доской воронки специалистов.

RBAC: менеджеры и администраторы видят закрепления и задачи команды друг друга
(см. README модуля); мутации чужой доски — только у portal_admin.

Реализация разбита по файлам: board_shared, board_columns_statuses, board_entries.
"""

from __future__ import annotations

from app.portal_specialists.services.board_columns_statuses import (
    create_specialist_column,
    create_specialist_status,
    delete_specialist_column,
    delete_specialist_status,
    list_specialist_columns,
    list_specialist_statuses,
    update_specialist_column,
    update_specialist_status,
)
from app.portal_specialists.services.board_entries import (
    add_to_board,
    list_board_entries,
    list_managers_for_specialist,
    move_on_board,
    reassign_manager,
    remove_from_board,
    reorder_on_board,
)
from app.portal_specialists.services.board_shared import (
    build_entry_read,
    require_manager_or_admin,
    require_specialist_write_access,
)

__all__ = [
    "add_to_board",
    "build_entry_read",
    "create_specialist_column",
    "create_specialist_status",
    "delete_specialist_column",
    "delete_specialist_status",
    "list_board_entries",
    "list_managers_for_specialist",
    "list_specialist_columns",
    "list_specialist_statuses",
    "move_on_board",
    "reassign_manager",
    "remove_from_board",
    "reorder_on_board",
    "require_manager_or_admin",
    "require_specialist_write_access",
    "update_specialist_column",
    "update_specialist_status",
]
