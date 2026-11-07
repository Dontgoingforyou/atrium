"""Фикстуры и хелперы для тестов portal_navigation."""

from __future__ import annotations

import uuid
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from datetime import UTC, datetime

from app.api.deps_auth import get_current_user
from app.infrastructure.db.models.portal_document import PortalDocument
from app.main import app
from app.schemas.auth import UserPublic
from httpx import Response
from sqlalchemy.ext.asyncio import AsyncSession

NAV_API = "/api/v1/portal/navigation-tree"


def assert_api_error(response: Response, status: int, code: str) -> None:
    """Ошибка AppError: и HTTP-статус, и контрактный `code`."""
    assert response.status_code == status, response.text
    assert response.json()["code"] == code


@contextmanager
def override_dependency(
    dependency: object,
    override: object,
) -> Iterator[None]:
    """Подменить Depends без clear()."""
    previous = app.dependency_overrides.get(dependency)
    app.dependency_overrides[dependency] = override
    try:
        yield
    finally:
        if previous is not None:
            app.dependency_overrides[dependency] = previous
        else:
            app.dependency_overrides.pop(dependency, None)


@contextmanager
def as_user(user_factory: Callable[[], UserPublic]) -> Iterator[None]:
    """Временно подменить get_current_user без clear()."""
    previous = app.dependency_overrides.get(get_current_user)
    app.dependency_overrides[get_current_user] = user_factory
    try:
        yield
    finally:
        if previous is not None:
            app.dependency_overrides[get_current_user] = previous
        else:
            app.dependency_overrides.pop(get_current_user, None)


async def add_doc(
    session: AsyncSession,
    *,
    title: str,
    author_sub: str = "user-sub",
    parent_document_id: uuid.UUID | None = None,
    sort_order: int = 0,
    icon_emoji: str | None = None,
    deleted_at: datetime | None = None,
    created_at: datetime | None = None,
    doc_id: uuid.UUID | None = None,
) -> PortalDocument:
    """Документ для дерева; commit — на вызывающем."""
    row = PortalDocument(
        title=title,
        author_sub=author_sub,
        parent_document_id=parent_document_id,
        sort_order=sort_order,
        icon_emoji=icon_emoji,
        deleted_at=deleted_at,
        body="",
    )
    if doc_id is not None:
        row.id = doc_id
    if created_at is not None:
        row.created_at = created_at
        row.updated_at = created_at
    session.add(row)
    await session.flush()
    return row


def now_utc() -> datetime:
    return datetime.now(UTC)
