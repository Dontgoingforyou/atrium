from __future__ import annotations

import logging
import uuid

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError
from app.core.utils import now_utc as _now_utc
from app.infrastructure.db.models.portal_learning import (
    PortalLearningMaterial,
    PortalQuiz,
    PortalQuizAnswer,
    PortalQuizAttempt,
    PortalQuizAttemptAnswer,
    PortalQuizQuestion,
)
from app.portal_learning.schemas.quiz import (
    AttemptAnswerResultRead,
    AttemptResultRead,
    AttemptSubmit,
    QuizAnswerWithCorrectRead,
    QuizCreate,
    QuizQuestionWrite,
    QuizUpdate,
)
from app.portal_learning.services.material import _is_material_visible
from app.schemas.auth import UserPublic

logger = logging.getLogger(__name__)


def _is_quiz_visible(quiz: PortalQuiz, user: UserPublic) -> bool:
    """Тест виден пользователю, если он не привязан к материалу
    или привязанный материал доступен пользователю."""
    if user.is_portal_admin:
        return True
    if quiz.material is None:
        return True
    return _is_material_visible(quiz.material, user)


async def _load_quiz_with_questions(session: AsyncSession, quiz_id: uuid.UUID) -> PortalQuiz | None:
    stmt = (
        select(PortalQuiz)
        .where(PortalQuiz.id == quiz_id)
        .options(
            selectinload(PortalQuiz.questions).selectinload(PortalQuizQuestion.answers),
            selectinload(PortalQuiz.material).selectinload(PortalLearningMaterial.idp_group_rows),
        )
    )
    return (await session.execute(stmt)).scalar_one_or_none()


async def list_quizzes(
    session: AsyncSession,
    user: UserPublic,
    *,
    limit: int = 100,
    offset: int = 0,
) -> list[PortalQuiz]:
    """Список тестов, видимых пользователю."""
    stmt = (
        select(PortalQuiz)
        .options(
            selectinload(PortalQuiz.questions).selectinload(PortalQuizQuestion.answers),
            selectinload(PortalQuiz.material).selectinload(PortalLearningMaterial.idp_group_rows),
        )
        .order_by(PortalQuiz.created_at.desc())
    )
    rows = list((await session.scalars(stmt)).all())
    visible = [r for r in rows if _is_quiz_visible(r, user)]
    return visible[offset : offset + limit]


def _require_visible_quiz(quiz: PortalQuiz | None, user: UserPublic, quiz_id: uuid.UUID) -> PortalQuiz:
    """Скрытый или отсутствующий тест — 404, чтобы не палить существование id."""
    if quiz is None or not _is_quiz_visible(quiz, user):
        if quiz is not None:
            logger.warning(
                "Отказ в доступе к тесту: user_sub=%s quiz_id=%s",
                user.sub,
                quiz_id,
            )
        raise NotFoundError("Тест не найден")
    return quiz


async def _require_material_if_set(session: AsyncSession, material_id: uuid.UUID | None) -> None:
    if material_id is None:
        return
    if await session.get(PortalLearningMaterial, material_id) is None:
        raise NotFoundError("Материал не найден")


async def get_quiz(
    session: AsyncSession,
    user: UserPublic,
    quiz_id: uuid.UUID,
) -> PortalQuiz:
    row = await _load_quiz_with_questions(session, quiz_id)
    return _require_visible_quiz(row, user, quiz_id)


async def get_quiz_for_admin_edit(
    session: AsyncSession,
    user: UserPublic,
    quiz_id: uuid.UUID,
) -> PortalQuiz:
    """Загрузка теста с ответами и флагом is_correct — только для администратора портала."""
    if not user.is_portal_admin:
        raise ForbiddenError("Просмотр структуры теста для редактирования доступен только администраторам")
    row = await _load_quiz_with_questions(session, quiz_id)
    if row is None:
        raise NotFoundError("Тест не найден")
    return row


async def create_quiz(
    session: AsyncSession,
    user: UserPublic,
    data: QuizCreate,
) -> PortalQuiz:
    if not user.is_portal_admin:
        raise ForbiddenError("Создание тестов доступно только администраторам")
    await _require_material_if_set(session, data.material_id)
    row = PortalQuiz(
        title=data.title,
        description=data.description,
        material_id=data.material_id,
    )
    session.add(row)
    await session.commit()
    loaded = await _load_quiz_with_questions(session, row.id)
    return loaded  # type: ignore[return-value]


async def update_quiz(
    session: AsyncSession,
    user: UserPublic,
    quiz_id: uuid.UUID,
    data: QuizUpdate,
) -> PortalQuiz:
    if not user.is_portal_admin:
        raise ForbiddenError("Редактирование тестов доступно только администраторам")
    row = await session.get(PortalQuiz, quiz_id)
    if row is None:
        raise NotFoundError("Тест не найден")
    patch = data.model_dump(exclude_unset=True)
    if "material_id" in patch:
        await _require_material_if_set(session, patch["material_id"])
    for field, value in patch.items():
        setattr(row, field, value)
    row.updated_at = _now_utc()
    await session.commit()
    loaded = await _load_quiz_with_questions(session, quiz_id)
    return loaded  # type: ignore[return-value]


async def replace_quiz_questions(
    session: AsyncSession,
    user: UserPublic,
    quiz_id: uuid.UUID,
    questions: list[QuizQuestionWrite],
) -> PortalQuiz:
    """Полная замена вопросов и ответов; удаляет все попытки прохождения."""
    if not user.is_portal_admin:
        raise ForbiddenError("Изменение структуры теста доступно только администраторам")
    row = await _load_quiz_with_questions(session, quiz_id)
    if row is None:
        raise NotFoundError("Тест не найден")
    attempts = list(
        (await session.scalars(select(PortalQuizAttempt).where(PortalQuizAttempt.quiz_id == quiz_id))).all()
    )
    for attempt in attempts:
        await session.delete(attempt)
    for question in list(row.questions):
        for answer in list(question.answers):
            await session.delete(answer)
        await session.delete(question)
    await session.flush()
    session.expire(row, ["questions"])
    for order, q in enumerate(questions):
        pq = PortalQuizQuestion(quiz_id=quiz_id, text=q.text, order_index=order)
        session.add(pq)
        await session.flush()
        for ans in q.answers:
            session.add(
                PortalQuizAnswer(
                    question_id=pq.id,
                    text=ans.text,
                    is_correct=ans.is_correct,
                )
            )
    row.updated_at = _now_utc()
    await session.commit()
    session.expire(row, ["questions"])
    loaded = await _load_quiz_with_questions(session, quiz_id)
    return loaded  # type: ignore[return-value]


async def _delete_quiz_graph(session: AsyncSession, quiz: PortalQuiz) -> None:
    """Сначала дети, иначе identity map ставит quiz_id=NULL (NOT NULL)."""
    attempts = list(
        (await session.scalars(select(PortalQuizAttempt).where(PortalQuizAttempt.quiz_id == quiz.id))).all()
    )
    for attempt in attempts:
        await session.delete(attempt)
    for question in list(quiz.questions):
        for answer in list(question.answers):
            await session.delete(answer)
        await session.delete(question)
    await session.delete(quiz)


async def delete_quiz(session: AsyncSession, user: UserPublic, quiz_id: uuid.UUID) -> None:
    if not user.is_portal_admin:
        raise ForbiddenError("Удаление тестов доступно только администраторам")
    row = await _load_quiz_with_questions(session, quiz_id)
    if row is None:
        raise NotFoundError("Тест не найден")
    await _delete_quiz_graph(session, row)
    await session.commit()


async def start_attempt(
    session: AsyncSession,
    user: UserPublic,
    quiz_id: uuid.UUID,
) -> PortalQuizAttempt:
    """Начать новую попытку теста."""
    _require_visible_quiz(await _load_quiz_with_questions(session, quiz_id), user, quiz_id)
    attempt = PortalQuizAttempt(
        user_sub=user.sub,
        quiz_id=quiz_id,
        score=0,
        max_score=0,
    )
    session.add(attempt)
    await session.commit()
    await session.refresh(attempt)
    return attempt


async def _load_attempt_for_submit(
    session: AsyncSession,
    user: UserPublic,
    quiz_id: uuid.UUID,
    attempt_id: uuid.UUID,
) -> tuple[PortalQuizAttempt, PortalQuiz]:
    """Найти попытку и тест, проверить, что попытка не завершена и тест доступен."""
    stmt = select(PortalQuizAttempt).where(
        PortalQuizAttempt.id == attempt_id,
        PortalQuizAttempt.quiz_id == quiz_id,
        PortalQuizAttempt.user_sub == user.sub,
    )
    attempt = (await session.execute(stmt)).scalar_one_or_none()
    if attempt is None:
        raise NotFoundError("Попытка не найдена")
    if attempt.finished_at is not None:
        raise ForbiddenError("Попытка уже завершена")

    quiz = _require_visible_quiz(await _load_quiz_with_questions(session, quiz_id), user, quiz_id)
    return attempt, quiz


async def _score_and_save_answers(
    session: AsyncSession,
    attempt: PortalQuizAttempt,
    quiz: PortalQuiz,
    submitted_by_question: dict[uuid.UUID, uuid.UUID | None],
) -> None:
    """Сохранить ответы попытки и посчитать score; коммитит транзакцию.

    Второй параллельный submit той же попытки упадёт на UNIQUE(attempt_id, question_id)
    (`PortalQuizAttemptAnswer`) -> `ConflictError`, вместо задвоенных строк ответов.
    """
    answers_map: dict[uuid.UUID, PortalQuizAnswer] = {a.id: a for q in quiz.questions for a in q.answers}
    score = 0
    for q in quiz.questions:
        chosen_answer_id = submitted_by_question.get(q.id)
        session.add(PortalQuizAttemptAnswer(attempt_id=attempt.id, question_id=q.id, answer_id=chosen_answer_id))
        chosen = answers_map.get(chosen_answer_id) if chosen_answer_id else None
        if chosen is not None and chosen.question_id == q.id and chosen.is_correct:
            score += 1

    attempt.score = score
    attempt.max_score = len(quiz.questions)
    attempt.finished_at = _now_utc()
    try:
        await session.commit()
    except IntegrityError as e:
        await session.rollback()
        raise ConflictError("Попытка уже отправлена параллельным запросом") from e


def _build_attempt_result(
    attempt: PortalQuizAttempt,
    quiz: PortalQuiz,
    quiz_id: uuid.UUID,
    user: UserPublic,
    submitted_by_question: dict[uuid.UUID, uuid.UUID | None],
) -> AttemptResultRead:
    answer_results = [
        AttemptAnswerResultRead(
            question_id=q.id,
            question_text=q.text,
            selected_answer_id=submitted_by_question.get(q.id),
            answers=[
                QuizAnswerWithCorrectRead(id=a.id, question_id=a.question_id, text=a.text, is_correct=a.is_correct)
                for a in q.answers
            ],
        )
        for q in quiz.questions
    ]
    return AttemptResultRead(
        id=attempt.id,
        quiz_id=quiz_id,
        user_sub=user.sub,
        score=attempt.score,
        max_score=attempt.max_score,
        started_at=attempt.started_at,
        finished_at=attempt.finished_at,
        answers=answer_results,
    )


async def submit_attempt(
    session: AsyncSession,
    user: UserPublic,
    quiz_id: uuid.UUID,
    attempt_id: uuid.UUID,
    data: AttemptSubmit,
) -> AttemptResultRead:
    """Отправить ответы, подсчитать score, вернуть результат с правильными ответами."""
    attempt, quiz = await _load_attempt_for_submit(session, user, quiz_id, attempt_id)
    submitted_by_question: dict[uuid.UUID, uuid.UUID | None] = {ans.question_id: ans.answer_id for ans in data.answers}
    await _score_and_save_answers(session, attempt, quiz, submitted_by_question)
    return _build_attempt_result(attempt, quiz, quiz_id, user, submitted_by_question)


async def list_my_attempts(
    session: AsyncSession,
    user: UserPublic,
    quiz_id: uuid.UUID,
) -> list[PortalQuizAttempt]:
    _require_visible_quiz(await _load_quiz_with_questions(session, quiz_id), user, quiz_id)
    stmt = (
        select(PortalQuizAttempt)
        .where(PortalQuizAttempt.quiz_id == quiz_id, PortalQuizAttempt.user_sub == user.sub)
        .order_by(PortalQuizAttempt.started_at.desc())
    )
    return list((await session.scalars(stmt)).all())
