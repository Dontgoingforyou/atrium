"""Константы домена документов портала."""

from __future__ import annotations

import uuid

# Фиксированный id корневого контейнера раздела (сам документ в UI не показывается).
DEVELOPER_DOCS_ROOT_ID = uuid.UUID("a1b2c3d4-e5f6-4a70-8b9c-0d1e2f3a4b5c")
DEVELOPER_DOCS_TITLE = "Документы для разработчиков"

# Виртуальные корни GET /portal/navigation-tree (не строки portal_document).
VIRTUAL_DOCS_ROOT_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
VIRTUAL_DOCS_ROOT_SLUG = "__documents__"
VIRTUAL_DEVELOPER_DOCS_ROOT_ID = uuid.UUID("00000000-0000-0000-0000-000000000003")
VIRTUAL_DEVELOPER_DOCS_ROOT_SLUG = "__developer_docs__"
