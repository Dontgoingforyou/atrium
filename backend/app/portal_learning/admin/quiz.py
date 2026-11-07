from __future__ import annotations

from typing import Any

from sqladmin import ModelView
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload
from starlette.requests import Request

from app.admin.formatters import fmt_datetime
from app.admin.sqladmin_categories import SQLADMIN_CATEGORY_TESTING
from app.infrastructure.db.models.portal_learning import (
    PortalLearningMaterial,
    PortalQuiz,
    PortalQuizAnswer,
    PortalQuizAttempt,
    PortalQuizQuestion,
)
from app.portal_collab.admin.formatters import fmt_user_sub


def _fmt_bool_ru(model: Any, attr: str) -> str:
    return "Да" if getattr(model, attr, False) else "Нет"


def _fmt_score(model: Any, attr: str) -> str:
    score = getattr(model, "score", 0)
    max_score = getattr(model, "max_score", 0)
    return f"{score} / {max_score}"


class PortalQuizAdmin(ModelView, model=PortalQuiz):
    name = "Тест"
    name_plural = "Тесты"
    icon = "fa-solid fa-circle-question"
    category = SQLADMIN_CATEGORY_TESTING
    category_icon = "fa-solid fa-clipboard-question"

    form_ajax_refs = {
        "material": {
            "fields": (PortalLearningMaterial.title,),
            "order_by": PortalLearningMaterial.title,
        },
    }

    column_list = [
        PortalQuiz.title,
        "material",
        PortalQuiz.created_at,
    ]
    column_labels = {
        "title": "Название",
        "description": "Описание",
        "material": "Учебный материал",
        "material_id": "Учебный материал (ID)",
        "questions": "Вопросы",
        "attempts": "Попытки пользователей",
        "created_at": "Создан",
        "updated_at": "Обновлён",
    }
    column_formatters = {
        "created_at": fmt_datetime,  # type: ignore[dict-item, unused-ignore]
        "updated_at": fmt_datetime,  # type: ignore[dict-item, unused-ignore]
    }
    column_formatters_detail = {
        "created_at": fmt_datetime,  # type: ignore[dict-item, unused-ignore]
        "updated_at": fmt_datetime,  # type: ignore[dict-item, unused-ignore]
    }
    column_details_list = [
        PortalQuiz.title,
        PortalQuiz.description,
        "material",
        PortalQuiz.created_at,
        PortalQuiz.updated_at,
    ]
    can_view_details = True
    column_searchable_list = [PortalQuiz.title]
    column_sortable_list = [PortalQuiz.title, PortalQuiz.created_at]
    column_default_sort = [(PortalQuiz.created_at, True)]
    form_columns = ["title", "description", "material"]

    def list_query(self, request: Request) -> Any:
        return select(PortalQuiz).options(selectinload(PortalQuiz.material))

    def count_query(self, request: Request) -> Any:
        return select(func.count(PortalQuiz.id))

    def details_query(self, request: Request) -> Any:
        return self.form_edit_query(request).options(selectinload(PortalQuiz.material))


class PortalQuizQuestionAdmin(ModelView, model=PortalQuizQuestion):
    name = "Вопрос теста"
    name_plural = "Вопросы тестов"
    icon = "fa-solid fa-question"
    category = SQLADMIN_CATEGORY_TESTING

    form_ajax_refs = {
        "quiz": {
            "fields": (PortalQuiz.title,),
            "order_by": PortalQuiz.title,
        },
    }

    column_list = [
        "quiz",
        PortalQuizQuestion.order_index,
        PortalQuizQuestion.text,
    ]
    column_labels = {
        "quiz": "Тест",
        "quiz_id": "Тест (ID)",
        "order_index": "Порядок",
        "text": "Текст вопроса",
        "answers": "Варианты ответов",
        "attempt_answers": "Ответы в попытках",
    }
    column_sortable_list = [PortalQuizQuestion.order_index]
    form_columns = ["quiz", "order_index", "text"]
    column_details_list = [
        "quiz",
        PortalQuizQuestion.order_index,
        PortalQuizQuestion.text,
    ]
    can_view_details = True

    def list_query(self, request: Request) -> Any:
        return select(PortalQuizQuestion).options(selectinload(PortalQuizQuestion.quiz))

    def count_query(self, request: Request) -> Any:
        return select(func.count(PortalQuizQuestion.id))

    def details_query(self, request: Request) -> Any:
        return self.form_edit_query(request).options(selectinload(PortalQuizQuestion.quiz))


class PortalQuizAnswerAdmin(ModelView, model=PortalQuizAnswer):
    name = "Вариант ответа"
    name_plural = "Варианты ответов"
    icon = "fa-solid fa-spell-check"
    category = SQLADMIN_CATEGORY_TESTING

    form_ajax_refs = {
        "question": {
            "fields": (PortalQuizQuestion.text,),
            "order_by": PortalQuizQuestion.order_index,
        },
    }

    column_list = [
        "question",
        PortalQuizAnswer.text,
        PortalQuizAnswer.is_correct,
    ]
    column_labels = {
        "question": "Вопрос",
        "question_id": "Вопрос",
        "text": "Текст ответа",
        "is_correct": "Правильный",
    }
    column_formatters = {
        "is_correct": _fmt_bool_ru,  # type: ignore[dict-item, unused-ignore]
    }
    column_formatters_detail = {
        "is_correct": _fmt_bool_ru,  # type: ignore[dict-item, unused-ignore]
    }
    form_columns = ["question", "text", "is_correct"]
    column_details_list = [
        "question",
        PortalQuizAnswer.text,
        PortalQuizAnswer.is_correct,
    ]
    can_view_details = True

    def list_query(self, request: Request) -> Any:
        return select(PortalQuizAnswer).options(selectinload(PortalQuizAnswer.question))

    def count_query(self, request: Request) -> Any:
        return select(func.count(PortalQuizAnswer.id))

    def details_query(self, request: Request) -> Any:
        return self.form_edit_query(request).options(selectinload(PortalQuizAnswer.question))


class PortalQuizAttemptAdmin(ModelView, model=PortalQuizAttempt):
    name = "Попытка теста"
    name_plural = "Попытки тестов"
    icon = "fa-solid fa-trophy"
    category = SQLADMIN_CATEGORY_TESTING

    can_create = False
    can_edit = False
    can_delete = True

    column_list = [
        PortalQuizAttempt.user_sub,
        "quiz",
        PortalQuizAttempt.score,
        PortalQuizAttempt.started_at,
        PortalQuizAttempt.finished_at,
    ]
    column_labels = {
        "user_sub": "Пользователь",
        "user_profile": "Пользователь (профиль)",
        "quiz": "Тест",
        "quiz_id": "Тест (ID)",
        "score": "Баллы",
        "max_score": "Максимум",
        "attempt_answers": "Ответы по вопросам",
        "started_at": "Начата",
        "finished_at": "Завершена",
    }
    column_formatters = {
        "user_sub": fmt_user_sub,  # type: ignore[dict-item, unused-ignore]
        "score": _fmt_score,  # type: ignore[dict-item, unused-ignore]
        "started_at": fmt_datetime,  # type: ignore[dict-item, unused-ignore]
        "finished_at": fmt_datetime,  # type: ignore[dict-item, unused-ignore]
    }
    column_formatters_detail = {
        "user_sub": fmt_user_sub,  # type: ignore[dict-item, unused-ignore]
        "score": _fmt_score,  # type: ignore[dict-item, unused-ignore]
        "started_at": fmt_datetime,  # type: ignore[dict-item, unused-ignore]
        "finished_at": fmt_datetime,  # type: ignore[dict-item, unused-ignore]
    }
    column_details_list = [
        PortalQuizAttempt.user_sub,
        "quiz",
        PortalQuizAttempt.score,
        PortalQuizAttempt.started_at,
        PortalQuizAttempt.finished_at,
    ]
    can_view_details = True
    column_sortable_list = [PortalQuizAttempt.started_at]
    column_default_sort = [(PortalQuizAttempt.started_at, True)]

    def list_query(self, request: Request) -> Any:
        return select(PortalQuizAttempt).options(
            selectinload(PortalQuizAttempt.user_profile),
            selectinload(PortalQuizAttempt.quiz),
        )

    def count_query(self, request: Request) -> Any:
        return select(func.count(PortalQuizAttempt.id))

    def details_query(self, request: Request) -> Any:
        return self.form_edit_query(request).options(
            selectinload(PortalQuizAttempt.user_profile),
            selectinload(PortalQuizAttempt.quiz),
        )
