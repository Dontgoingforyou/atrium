"""Фикстуры и хелперы для тестов portal_home."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from datetime import UTC, datetime

from app.api.deps_auth import get_current_user
from app.core.auth_constants import IDP_GROUP_MANAGER, IDP_GROUP_PORTAL_ADMIN
from app.core.enums import FavoriteTargetType, TaskPriority, TaskStatus
from app.infrastructure.db.models.portal_document import PortalDocument
from app.infrastructure.db.models.portal_favorite import PortalFavorite
from app.infrastructure.db.models.portal_task import PortalTask
from app.infrastructure.db.models.portal_task_assignee import (
    PortalTaskAssignee,
)
from app.main import app
from app.schemas.auth import UserPublic
from httpx import Response
from sqlalchemy.ext.asyncio import AsyncSession

HOME_API = "/api/v1/portal/home"


def assert_api_error(response: Response, status: int, code: str) -> None:
    """Ошибка AppError: и HTTP-статус, и контрактный `code`."""
    assert response.status_code == status, response.text
    assert response.json()["code"] == code


def assert_pydantic_422(response: Response) -> None:
    assert response.status_code == 422, response.text
    assert "detail" in response.json()


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


def user_admin_and_manager() -> UserPublic:
    """Обе группы Keycloak: admin-блок есть, manager остаётся null."""
    return UserPublic(
        sub="both-sub",
        email="both@example.com",
        username="both",
        full_name="Both",
        idp_groups=[IDP_GROUP_PORTAL_ADMIN, IDP_GROUP_MANAGER],
        is_portal_admin=True,
    )


async def add_task(
    session: AsyncSession,
    *,
    title: str,
    creator_sub: str = "creator-sub",
    assignee_sub: str | None = None,
    assignee_subs: list[str] | None = None,
    status: str = TaskStatus.TODO.value,
    priority: str = TaskPriority.MEDIUM.value,
    due_at: datetime | None = None,
    created_at: datetime | None = None,
    updated_at: datetime | None = None,
) -> PortalTask:
    """Добавляет задачу (flush); commit — на вызывающем."""
    now = datetime.now(UTC)
    task = PortalTask(
        title=title,
        creator_sub=creator_sub,
        assignee_sub=assignee_sub,
        status=status,
        priority=priority,
        due_at=due_at,
        created_at=created_at or now,
        updated_at=updated_at or now,
    )
    session.add(task)
    await session.flush()
    for sub in assignee_subs or []:
        session.add(PortalTaskAssignee(task_id=task.id, assignee_sub=sub))
    await session.flush()
    return task


async def add_favorite_doc(
    session: AsyncSession,
    *,
    title: str,
    user_sub: str,
    deleted_at: datetime | None = None,
    fav_created_at: datetime | None = None,
) -> tuple[PortalDocument, PortalFavorite]:
    """Документ + звезда; commit — на вызывающем."""
    now = datetime.now(UTC)
    doc = PortalDocument(
        title=title,
        author_sub=user_sub,
        body="x",
        deleted_at=deleted_at,
    )
    session.add(doc)
    await session.flush()
    fav = PortalFavorite(
        user_sub=user_sub,
        target_type=FavoriteTargetType.DOCUMENT.value,
        target_id=doc.id,
        created_at=fav_created_at or now,
    )
    session.add(fav)
    await session.flush()
    return doc, fav
