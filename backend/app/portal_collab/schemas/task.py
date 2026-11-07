from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.core.enums import TaskPriority
from app.schemas.rich_media import RichMediaRead
from app.schemas.tags import PortalTagRead


class PortalTaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=512)
    description: str | None = None
    assignee_sub: str | None = None
    assignee_subs: list[str] = Field(
        default_factory=list,
        description=(
            "Исполнители. У подзадачи, если это поле и assignee_sub не переданы, "
            "копируются исполнители родителя. Явный пустой список оставляет подзадачу без исполнителей."
        ),
    )
    status: str | None = None
    priority: TaskPriority = TaskPriority.MEDIUM
    due_at: datetime | None = None
    document_id: uuid.UUID | None = None
    source_message_id: uuid.UUID | None = None
    chat_id: uuid.UUID | None = None
    parent_task_id: uuid.UUID | None = None
    tag_ids: list[uuid.UUID] = Field(default_factory=list)
    # Только create: нельзя «превратить» обычную задачу в учебную через PATCH.
    is_tour_demo: bool = False

    @model_validator(mode="before")
    @classmethod
    def _merge_legacy_assignee(cls, data: object) -> object:
        if isinstance(data, dict):
            legacy = data.get("assignee_sub")
            subs = data.get("assignee_subs")
            if legacy and not subs:
                data = {**data, "assignee_subs": [legacy]}
        return data

    @model_validator(mode="after")
    def _require_assignee_for_top_level_task(self) -> PortalTaskCreate:
        """Задача верхнего уровня (не подзадача) должна иметь хотя бы одного исполнителя.

        У подзадачи явный пустой список допустим. Пропуск полей исполнителя
        не проверяется здесь: create_task копирует исполнителей родителя.
        """
        if self.parent_task_id is None:
            has_assignee = bool(self.assignee_sub) or bool(self.assignee_subs)
            if not has_assignee:
                raise ValueError("Необходимо назначить хотя бы одного исполнителя")
        return self


class PortalTaskUpdate(BaseModel):
    expected_version: int = Field(..., ge=1, description="Версия задачи, прочитанная клиентом (CAS)")
    title: str | None = Field(default=None, min_length=1, max_length=512)
    description: str | None = None
    assignee_sub: str | None = None
    assignee_subs: list[str] | None = None
    status: str | None = None
    priority: TaskPriority | None = None
    due_at: datetime | None = None
    tag_ids: list[uuid.UUID] | None = None
    document_id: uuid.UUID | None = None
    parent_task_id: uuid.UUID | None = None

    @model_validator(mode="before")
    @classmethod
    def _merge_legacy_assignee(cls, data: object) -> object:
        if isinstance(data, dict):
            legacy = data.get("assignee_sub")
            subs = data.get("assignee_subs")
            if legacy is not None and subs is None:
                data = {**data, "assignee_subs": [legacy] if legacy else []}
        return data


class PortalTaskRead(BaseModel):
    model_config = ConfigDict(from_attributes=True, use_enum_values=True)

    id: uuid.UUID
    number: int | None = None
    title: str
    description: str | None
    creator_sub: str
    assignee_sub: str | None
    assignee_subs: list[str] = Field(default_factory=list)
    status: str
    priority: TaskPriority
    due_at: datetime | None
    document_id: uuid.UUID | None
    source_message_id: uuid.UUID | None
    chat_id: uuid.UUID | None
    parent_task_id: uuid.UUID | None
    position: int = 0
    jira_issue_key: str | None = None
    jira_sync_error: str | None = None
    is_tour_demo: bool = False
    version: int = Field(description="Версия для optimistic locking (CAS)")
    created_at: datetime
    updated_at: datetime
    tags: list[PortalTagRead] = []
    document_title: str | None = None


class PortalTaskHistoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    task_id: uuid.UUID
    changed_by_sub: str
    changed_at: datetime
    diff: dict[str, Any]


class TaskReorderRequest(BaseModel):
    task_id: uuid.UUID
    status: str = Field(min_length=1, max_length=32)
    after_task_id: uuid.UUID | None = None
    before_task_id: uuid.UUID | None = None


# --- Комментарии ---


class TaskCommentCreate(BaseModel):
    body: str = Field(min_length=0, max_length=4096, default="")
    parent_id: uuid.UUID | None = None
    mentions: list[str] = Field(default_factory=list)
    media_ids: list[uuid.UUID] = Field(default_factory=list)

    @model_validator(mode="after")
    def body_or_media_required(self) -> TaskCommentCreate:
        if not self.body.strip() and not self.media_ids:
            raise ValueError("Необходимо указать текст или прикрепить изображение")
        return self


class TaskCommentUpdate(BaseModel):
    expected_version: int = Field(..., ge=1, description="Версия комментария, прочитанная клиентом (CAS)")
    body: str | None = Field(default=None, min_length=1, max_length=4096)
    mentions: list[str] | None = None


class TaskCommentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    task_id: uuid.UUID
    parent_id: uuid.UUID | None
    author_sub: str
    body: str
    mentions: list[str]
    version: int = Field(description="Версия для optimistic locking (CAS)")
    created_at: datetime
    updated_at: datetime
    replies: list[TaskCommentRead] = []
    media: list[RichMediaRead] = []


TaskCommentRead.model_rebuild()


# --- Колонки канбана ---


class PortalTaskColumnRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    color: str
    status_key: str
    position: int
    exclude_from_kpi: bool = False
    jira_status_id: str | None = None


class PortalTaskColumnCreate(BaseModel):
    title: str = Field(min_length=1, max_length=128)
    color: str = Field(default="#6131cf", max_length=32)
    status_key: str = Field(min_length=1, max_length=32)
    position: int = Field(default=0, ge=0)
    exclude_from_kpi: bool = False


class PortalTaskColumnUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=128)
    color: str | None = Field(default=None, max_length=32)
    position: int | None = Field(default=None, ge=0)
    exclude_from_kpi: bool | None = None
    jira_status_id: str | None = Field(
        default=None,
        max_length=32,
        description="ID статуса Jira на доске AUTASKS (только portal_admin)",
    )


# --- Персональные настройки канбана ---


class TaskBoardPrefRead(BaseModel):
    """Порядок колонок (status_key), скрытые статусы и локальные подписи — только для текущего пользователя."""

    column_order: list[str] = Field(default_factory=list)
    hidden_status_keys: list[str] = Field(default_factory=list)
    title_overrides: dict[str, str] = Field(default_factory=dict)
    subtasks_flat: bool = False
    hide_subtasks: bool = False


class TaskBoardPrefWrite(BaseModel):
    column_order: list[str] = Field(default_factory=list)
    hidden_status_keys: list[str] = Field(default_factory=list)
    title_overrides: dict[str, str] = Field(default_factory=dict)
    subtasks_flat: bool = False
    hide_subtasks: bool = False

    @field_validator("column_order", "hidden_status_keys")
    @classmethod
    def _validate_status_lists(cls, v: list[str]) -> list[str]:
        if len(v) > 64:
            raise ValueError("Слишком много элементов (максимум 64)")
        for s in v:
            if len(s) > 32:
                raise ValueError("Ключ статуса не длиннее 32 символов")
        return v

    @field_validator("title_overrides")
    @classmethod
    def _validate_overrides(cls, v: dict[str, str]) -> dict[str, str]:
        if len(v) > 32:
            raise ValueError("Не более 32 переопределений заголовков")
        for key, title in v.items():
            if len(key) > 32:
                raise ValueError("Ключ статуса не длиннее 32 символов")
            if len(title) > 128:
                raise ValueError("Заголовок не длиннее 128 символов")
        return v

    @model_validator(mode="after")
    def _hide_overrides_flat(self) -> TaskBoardPrefWrite:
        """Скрытие подзадач важнее плоского режима."""
        if self.hide_subtasks and self.subtasks_flat:
            return self.model_copy(update={"subtasks_flat": False})
        return self


# --- Ссылки к задачам ---


class TaskLinkCreate(BaseModel):
    title: str | None = Field(default=None, max_length=512)
    url: str = Field(min_length=1, max_length=2048)

    @field_validator("title")
    @classmethod
    def _blank_title_to_none(cls, v: str | None) -> str | None:
        if v is None:
            return None
        stripped = v.strip()
        return stripped or None

    @field_validator("url")
    @classmethod
    def _http_https_only(cls, v: str) -> str:
        stripped = v.strip()
        parsed = urlparse(stripped)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            raise ValueError("Допустимы только ссылки http:// и https://")
        return stripped


class TaskLinkRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    task_id: uuid.UUID
    title: str | None
    url: str
    created_by_sub: str
    created_at: datetime


# --- Файлы, прикреплённые к задачам ---


class TaskFileRead(BaseModel):
    """Собирается вручную в роутере (нужны вычисляемые presigned URL)."""

    id: uuid.UUID
    task_id: uuid.UUID
    original_filename: str
    content_type: str
    file_size: int
    download_url: str
    view_url: str
    uploaded_by_sub: str
    created_at: datetime
