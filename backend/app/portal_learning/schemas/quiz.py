from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class QuizAnswerRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    question_id: uuid.UUID
    text: str
    # is_correct не отдаётся пользователю в карточке квиза; только в результате попытки


class QuizAnswerEditRead(BaseModel):
    """Вариант ответа для редактирования теста (только portal_admin)."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    question_id: uuid.UUID
    text: str
    is_correct: bool


class QuizQuestionEditRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    quiz_id: uuid.UUID
    text: str
    order_index: int
    answers: list[QuizAnswerEditRead] = []


class QuizEditRead(BaseModel):
    """Карточка теста для админского редактора (включая is_correct у ответов)."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    description: str | None
    material_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime
    questions: list[QuizQuestionEditRead] = []


class QuizAnswerWithCorrectRead(QuizAnswerRead):
    """Расширенная схема с правильным ответом — используется в результатах попытки."""

    is_correct: bool


class QuizQuestionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    quiz_id: uuid.UUID
    text: str
    order_index: int
    answers: list[QuizAnswerRead] = []


class QuizRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    description: str | None
    material_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime
    questions: list[QuizQuestionRead] = []


class QuizCreate(BaseModel):
    title: str = Field(min_length=1, max_length=512)
    description: str | None = None
    material_id: uuid.UUID | None = None


class QuizUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=512)
    description: str | None = None
    material_id: uuid.UUID | None = None


class QuizAnswerWrite(BaseModel):
    text: str = Field(min_length=1, max_length=1024)
    is_correct: bool = False


class QuizQuestionWrite(BaseModel):
    text: str = Field(min_length=1, max_length=4096)
    answers: list[QuizAnswerWrite] = Field(min_length=1, description="Минимум один вариант ответа")


class QuizReplaceQuestionsBody(BaseModel):
    """Полная замена вопросов и ответов; удаляет все попытки прохождения этого теста."""

    questions: list[QuizQuestionWrite] = Field(default_factory=list)


class QuizAttemptStart(BaseModel):
    """Тело ответа при начале попытки."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    quiz_id: uuid.UUID
    user_sub: str
    score: int
    max_score: int
    started_at: datetime
    finished_at: datetime | None


class AnswerSubmit(BaseModel):
    question_id: uuid.UUID
    answer_id: uuid.UUID | None = None


class AttemptSubmit(BaseModel):
    answers: list[AnswerSubmit]


class AttemptAnswerResultRead(BaseModel):
    question_id: uuid.UUID
    question_text: str
    selected_answer_id: uuid.UUID | None
    answers: list[QuizAnswerWithCorrectRead] = []


class AttemptResultRead(BaseModel):
    id: uuid.UUID
    quiz_id: uuid.UUID
    user_sub: str
    score: int
    max_score: int
    started_at: datetime
    finished_at: datetime | None
    answers: list[AttemptAnswerResultRead] = []


class AttemptHistoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    quiz_id: uuid.UUID
    user_sub: str
    score: int
    max_score: int
    started_at: datetime
    finished_at: datetime | None
