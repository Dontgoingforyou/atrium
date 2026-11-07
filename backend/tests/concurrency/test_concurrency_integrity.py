"""Параллельные вызовы с UNIQUE: теги, избранное, отправка попытки квиза."""

from __future__ import annotations

import asyncio
import uuid

import pytest
from app.core.enums import FavoriteTargetType
from app.core.exceptions import ConflictError
from app.infrastructure.db.models.portal_document import PortalDocument, PortalTag
from app.infrastructure.db.models.portal_favorite import PortalFavorite
from app.infrastructure.db.models.portal_learning import (
    PortalQuiz,
    PortalQuizAnswer,
    PortalQuizAttempt,
    PortalQuizAttemptAnswer,
    PortalQuizQuestion,
)
from app.portal_favorites.schemas.favorite import PortalFavoriteCreate
from app.portal_favorites.services import favorite as fav_svc
from app.portal_learning.schemas.quiz import AnswerSubmit, AttemptSubmit
from app.portal_learning.services import quiz as quiz_svc
from app.schemas.auth import UserPublic
from app.schemas.tags import PortalTagCreate
from app.services import portal_tags as portal_tags_svc
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker


@pytest.mark.asyncio
async def test_parallel_create_tag_same_display_name_one_row(
    sqlite_concurrency_factory: async_sessionmaker[AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """UNIQUE lower(trim(name)): IntegrityError на commit, не только Python pre-check."""

    async def _skip_precheck(*_args: object, **_kwargs: object) -> None:
        return None

    monkeypatch.setattr(portal_tags_svc, "_ensure_name_available", _skip_precheck)

    body = PortalTagCreate(name="ПараллельноеИмя", color="#AABBCC")
    outcomes: list[str] = []

    async def try_create() -> None:
        async with sqlite_concurrency_factory() as sess:
            try:
                await portal_tags_svc.create_tag(sess, body)
                outcomes.append("ok")
            except ConflictError:
                outcomes.append("conflict")

    await asyncio.gather(try_create(), try_create())

    assert sorted(outcomes) == ["conflict", "ok"]

    async with sqlite_concurrency_factory() as s:
        q = await s.execute(select(func.count()).select_from(PortalTag).where(PortalTag.name == "ПараллельноеИмя"))
        assert q.scalar_one() == 1


@pytest.mark.asyncio
async def test_parallel_add_favorite_same_target_one_row(
    sqlite_concurrency_factory: async_sessionmaker[AsyncSession],
) -> None:
    doc_id = uuid.uuid4()
    async with sqlite_concurrency_factory() as s:
        s.add(PortalDocument(id=doc_id, title="Doc", author_sub="author"))
        await s.commit()

    user = UserPublic(
        sub="fav-user",
        email="f@e.com",
        username="f",
        full_name="F",
        idp_groups=[],
        is_portal_admin=False,
    )
    data = PortalFavoriteCreate(target_type=FavoriteTargetType.DOCUMENT, target_id=doc_id)
    outcomes: list[str] = []

    async def try_add() -> None:
        async with sqlite_concurrency_factory() as sess:
            try:
                await fav_svc.add_favorite(sess, user, data)
                outcomes.append("ok")
            except ConflictError:
                outcomes.append("conflict")

    await asyncio.gather(try_add(), try_add())

    assert sorted(outcomes) == ["conflict", "ok"]

    async with sqlite_concurrency_factory() as s:
        q = await s.execute(
            select(func.count())
            .select_from(PortalFavorite)
            .where(
                PortalFavorite.user_sub == user.sub,
                PortalFavorite.target_type == FavoriteTargetType.DOCUMENT.value,
                PortalFavorite.target_id == doc_id,
            )
        )
        assert q.scalar_one() == 1


@pytest.mark.asyncio
async def test_parallel_submit_quiz_attempt_one_success(
    sqlite_concurrency_factory: async_sessionmaker[AsyncSession],
) -> None:
    """Два параллельных submit: UNIQUE(attempt_id, question_id); проигравший — ConflictError."""
    quiz_id = uuid.uuid4()
    question_id = uuid.uuid4()
    answer_id = uuid.uuid4()
    attempt_id = uuid.uuid4()
    user = UserPublic(
        sub="quiz-attempt-user",
        email="qa@e.com",
        username="qa",
        full_name="QA",
        idp_groups=[],
        is_portal_admin=False,
    )

    async with sqlite_concurrency_factory() as s:
        s.add(PortalQuiz(id=quiz_id, title="Гоночный тест"))
        s.add(PortalQuizQuestion(id=question_id, quiz_id=quiz_id, order_index=0, text="2+2?"))
        s.add(PortalQuizAnswer(id=answer_id, question_id=question_id, text="4", is_correct=True))
        s.add(
            PortalQuizAttempt(
                id=attempt_id,
                quiz_id=quiz_id,
                user_sub=user.sub,
                score=0,
                max_score=0,
            )
        )
        await s.commit()

    data = AttemptSubmit(answers=[AnswerSubmit(question_id=question_id, answer_id=answer_id)])
    outcomes: list[str] = []

    async def try_submit() -> None:
        async with sqlite_concurrency_factory() as sess:
            try:
                await quiz_svc.submit_attempt(sess, user, quiz_id, attempt_id, data)
                outcomes.append("ok")
            except ConflictError:
                outcomes.append("conflict")

    await asyncio.gather(try_submit(), try_submit())

    assert sorted(outcomes) == ["conflict", "ok"]

    async with sqlite_concurrency_factory() as s:
        answers = await s.execute(
            select(func.count())
            .select_from(PortalQuizAttemptAnswer)
            .where(PortalQuizAttemptAnswer.attempt_id == attempt_id)
        )
        assert answers.scalar_one() == 1
        attempt = await s.get(PortalQuizAttempt, attempt_id)
        assert attempt is not None
        assert attempt.finished_at is not None
        assert attempt.max_score == 1
        assert attempt.score == 1
