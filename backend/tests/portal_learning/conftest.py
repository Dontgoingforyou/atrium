"""Фикстуры и хелперы для тестов portal_learning."""

from __future__ import annotations

import uuid
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from datetime import datetime

from app.api.deps_auth import get_current_user
from app.core.enums import LearningMaterialStatus, LearningMaterialType
from app.infrastructure.db.models.portal_learning import (
    PortalChecklist,
    PortalChecklistItem,
    PortalLearningMaterial,
    PortalLearningMaterialIdpGroup,
    PortalQuiz,
    PortalQuizAnswer,
    PortalQuizQuestion,
)
from app.main import app
from app.schemas.auth import UserPublic
from httpx import Response
from sqlalchemy.ext.asyncio import AsyncSession

from tests.helpers.portal_test_users import user_portal_regular, user_portal_user_b

LEARNING_API = "/api/v1/portal/learning"
MATERIALS = f"{LEARNING_API}/materials"
CHECKLISTS = f"{LEARNING_API}/checklists"
QUIZZES = f"{LEARNING_API}/quizzes"


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


@contextmanager
def as_user_regular() -> Iterator[None]:
    with as_user(user_portal_regular):
        yield


@contextmanager
def as_user_b() -> Iterator[None]:
    with as_user(user_portal_user_b):
        yield


async def add_material(
    session: AsyncSession,
    *,
    title: str,
    body: str | None = "Текст",
    material_type: str = LearningMaterialType.ARTICLE.value,
    status: str = LearningMaterialStatus.ACTIVE.value,
    idp_groups: list[str] | None = None,
    created_by_sub: str = "admin-sub",
    created_at: datetime | None = None,
) -> PortalLearningMaterial:
    """Учебный материал; commit — на вызывающем."""
    row = PortalLearningMaterial(
        title=title,
        body=body,
        material_type=material_type,
        status=status,
        created_by_sub=created_by_sub,
    )
    if created_at is not None:
        row.created_at = created_at
        row.updated_at = created_at
    session.add(row)
    await session.flush()
    for group in idp_groups or []:
        session.add(PortalLearningMaterialIdpGroup(material_id=row.id, idp_group=group))
    await session.flush()
    return row


async def add_checklist(
    session: AsyncSession,
    *,
    title: str,
    items: list[str],
    description: str | None = None,
    idp_group: str = "",
    created_at: datetime | None = None,
) -> tuple[PortalChecklist, list[PortalChecklistItem]]:
    """Чек-лист с пунктами; commit — на вызывающем."""
    row = PortalChecklist(title=title, description=description, idp_group=idp_group)
    if created_at is not None:
        row.created_at = created_at
        row.updated_at = created_at
    session.add(row)
    await session.flush()
    item_rows: list[PortalChecklistItem] = []
    for idx, text in enumerate(items):
        item = PortalChecklistItem(checklist_id=row.id, order_index=idx, text=text)
        session.add(item)
        item_rows.append(item)
    await session.flush()
    return row, item_rows


async def add_quiz_with_question(
    session: AsyncSession,
    *,
    title: str,
    question_text: str = "2+2?",
    correct: str = "4",
    wrong: str = "5",
    material_id: uuid.UUID | None = None,
    created_at: datetime | None = None,
) -> tuple[PortalQuiz, PortalQuizQuestion, PortalQuizAnswer, PortalQuizAnswer]:
    """Квиз с одним вопросом и двумя ответами; commit — на вызывающем."""
    quiz = PortalQuiz(title=title, description=None, material_id=material_id)
    if created_at is not None:
        quiz.created_at = created_at
        quiz.updated_at = created_at
    session.add(quiz)
    await session.flush()
    question = PortalQuizQuestion(quiz_id=quiz.id, order_index=0, text=question_text)
    session.add(question)
    await session.flush()
    ok = PortalQuizAnswer(question_id=question.id, text=correct, is_correct=True)
    bad = PortalQuizAnswer(question_id=question.id, text=wrong, is_correct=False)
    session.add_all([ok, bad])
    await session.flush()
    return quiz, question, ok, bad
