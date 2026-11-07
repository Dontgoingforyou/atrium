from __future__ import annotations

import uuid

from fastapi import APIRouter, Query

from app.api.deps import DbSession
from app.api.deps_auth import CurrentUser
from app.portal_learning.schemas.quiz import (
    AttemptHistoryRead,
    AttemptResultRead,
    AttemptSubmit,
    QuizAttemptStart,
    QuizCreate,
    QuizEditRead,
    QuizRead,
    QuizReplaceQuestionsBody,
    QuizUpdate,
)
from app.portal_learning.services import quiz as svc

router = APIRouter(tags=["Обучение · Тесты"])


@router.get(
    "/learning/quizzes",
    summary="Список тестов",
    response_model=list[QuizRead],
)
async def list_quizzes(
    user: CurrentUser,
    db: DbSession,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> list[QuizRead]:
    rows = await svc.list_quizzes(db, user, limit=limit, offset=offset)
    return [QuizRead.model_validate(r) for r in rows]


@router.get(
    "/learning/quizzes/{quiz_id}",
    summary="Карточка теста с вопросами",
    response_model=QuizRead,
)
async def get_quiz(
    quiz_id: uuid.UUID,
    user: CurrentUser,
    db: DbSession,
) -> QuizRead:
    quiz = await svc.get_quiz(db, user, quiz_id)
    return QuizRead.model_validate(quiz)


@router.get(
    "/learning/quizzes/{quiz_id}/for-edit",
    summary="Тест для редактирования (с признаком верного ответа)",
    description="Только для администратора портала.",
    response_model=QuizEditRead,
)
async def get_quiz_for_edit(
    quiz_id: uuid.UUID,
    user: CurrentUser,
    db: DbSession,
) -> QuizEditRead:
    quiz = await svc.get_quiz_for_admin_edit(db, user, quiz_id)
    return QuizEditRead.model_validate(quiz)


@router.post(
    "/learning/quizzes",
    summary="Создать тест",
    description="Только для администратора портала.",
    response_model=QuizRead,
    status_code=201,
)
async def create_quiz(
    user: CurrentUser,
    db: DbSession,
    body: QuizCreate,
) -> QuizRead:
    quiz = await svc.create_quiz(db, user, body)
    return QuizRead.model_validate(quiz)


@router.patch(
    "/learning/quizzes/{quiz_id}",
    summary="Обновить тест",
    description="Только для администратора портала.",
    response_model=QuizRead,
)
async def update_quiz(
    quiz_id: uuid.UUID,
    user: CurrentUser,
    db: DbSession,
    body: QuizUpdate,
) -> QuizRead:
    quiz = await svc.update_quiz(db, user, quiz_id, body)
    return QuizRead.model_validate(quiz)


@router.put(
    "/learning/quizzes/{quiz_id}/questions",
    summary="Заменить вопросы и ответы теста",
    description=(
        "Только для администратора портала. Удаляет все попытки прохождения и задаёт новую структуру вопросов."
    ),
    response_model=QuizRead,
)
async def replace_quiz_questions(
    quiz_id: uuid.UUID,
    user: CurrentUser,
    db: DbSession,
    body: QuizReplaceQuestionsBody,
) -> QuizRead:
    quiz = await svc.replace_quiz_questions(db, user, quiz_id, body.questions)
    return QuizRead.model_validate(quiz)


@router.delete(
    "/learning/quizzes/{quiz_id}",
    summary="Удалить тест",
    description="Только для администратора портала.",
    status_code=204,
)
async def delete_quiz_row(
    quiz_id: uuid.UUID,
    user: CurrentUser,
    db: DbSession,
) -> None:
    await svc.delete_quiz(db, user, quiz_id)


@router.post(
    "/learning/quizzes/{quiz_id}/attempts",
    summary="Начать попытку теста",
    response_model=QuizAttemptStart,
    status_code=201,
)
async def start_attempt(
    quiz_id: uuid.UUID,
    user: CurrentUser,
    db: DbSession,
) -> QuizAttemptStart:
    attempt = await svc.start_attempt(db, user, quiz_id)
    return QuizAttemptStart.model_validate(attempt)


@router.post(
    "/learning/quizzes/{quiz_id}/attempts/{attempt_id}/submit",
    summary="Отправить ответы и получить результат",
    response_model=AttemptResultRead,
)
async def submit_attempt(
    quiz_id: uuid.UUID,
    attempt_id: uuid.UUID,
    user: CurrentUser,
    db: DbSession,
    body: AttemptSubmit,
) -> AttemptResultRead:
    return await svc.submit_attempt(db, user, quiz_id, attempt_id, body)


@router.get(
    "/learning/quizzes/{quiz_id}/attempts",
    summary="История моих попыток теста",
    response_model=list[AttemptHistoryRead],
)
async def list_my_attempts(
    quiz_id: uuid.UUID,
    user: CurrentUser,
    db: DbSession,
) -> list[AttemptHistoryRead]:
    rows = await svc.list_my_attempts(db, user, quiz_id)
    return [AttemptHistoryRead.model_validate(r) for r in rows]
