from __future__ import annotations

import logging
import uuid
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, File, Query, UploadFile, status
from sqlalchemy import select

from app.api.deps import DbSession, HttpClient
from app.api.deps_auth import CurrentUser
from app.core.config import get_settings
from app.infrastructure.db.models.portal_document import PortalDocument
from app.portal_collab.schemas.task import (
    PortalTaskCreate,
    PortalTaskHistoryRead,
    PortalTaskRead,
    PortalTaskUpdate,
    TaskReorderRequest,
)
from app.portal_collab.services import task as svc
from app.portal_collab.services._task_reads import single_task_to_read, tasks_to_reads
from app.portal_search.services import embedding as emb_svc
from app.portal_search.services.entity_text import task_meta, task_to_text
from app.schemas.rich_media import RichMediaRead
from app.services import rich_media as rich_media_svc
from app.services.file_upload_validation import open_upload_stream

router = APIRouter(prefix="/portal", tags=["Задачи"])
logger = logging.getLogger(__name__)


async def _enrich_document_titles(session: DbSession, reads: list[PortalTaskRead]) -> None:
    """Один IN-запрос к portal_documents для обогащения списка задач названиями документов."""
    doc_ids = list({r.document_id for r in reads if r.document_id is not None})
    if not doc_ids:
        return
    result = await session.execute(
        select(PortalDocument.id, PortalDocument.title).where(PortalDocument.id.in_(doc_ids))
    )
    titles: dict[uuid.UUID, str] = {row[0]: row[1] for row in result.all()}
    for r in reads:
        if r.document_id is not None:
            r.document_title = titles.get(r.document_id)


@router.get(
    "/tasks",
    summary="Список задач",
    response_model=list[PortalTaskRead],
)
async def list_tasks(
    user: CurrentUser,
    db: DbSession,
    mine_only: bool = Query(
        default=False,
        description=("Только задачи, где пользователь исполнитель, либо исполнитель не задан и пользователь автор"),
    ),
    assignee_sub: Annotated[
        list[str],
        Query(
            description=(
                "Повторяемый query-параметр: фильтр по одному или нескольким исполнителям (OR). "
                "Чужие задачи — только portal_admin или руководитель (IdP)."
            ),
        ),
    ] = [],
    document_id: uuid.UUID | None = Query(default=None),
    chat_id: uuid.UUID | None = Query(default=None),
    status: Annotated[
        list[str],
        Query(description="Повторяемый параметр: один или несколько статусов (OR)."),
    ] = [],
    priority: Annotated[
        list[str],
        Query(description="Повторяемый параметр: приоритеты (OR); включает родителя/подзадачи при совпадении."),
    ] = [],
    tag_id: Annotated[
        list[uuid.UUID],
        Query(description="Повторяемый параметр: задачи с любым из указанных тегов (OR)."),
    ] = [],
    parent_task_id: uuid.UUID | None = Query(default=None, description="Фильтр по родительской задаче"),
    overdue_only: bool = Query(
        default=False,
        description=(
            "Только просроченные: календарный день срока раньше сегодняшнего дня портала, статус не done/cancelled"
        ),
    ),
    done_this_month: bool = Query(
        default=False,
        description="Только закрытые (done/cancelled) с начала текущего месяца UTC",
    ),
    no_assignee: bool = Query(
        default=False,
        description="Только KPI-активные задачи без исполнителя (колонка и junction)",
    ),
    kpi_open_only: bool = Query(
        default=False,
        description="Только KPI-активные задачи (как счётчик «Открытых задач» на главной)",
    ),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
) -> list[PortalTaskRead]:
    rows = await svc.list_tasks(
        db,
        user,
        mine_only=mine_only,
        assignee_sub=assignee_sub or None,
        document_id=document_id,
        chat_id=chat_id,
        status=status or None,
        priority=priority or None,
        tag_id=tag_id or None,
        parent_task_id=parent_task_id,
        overdue_only=overdue_only,
        done_this_month=done_this_month,
        no_assignee=no_assignee,
        kpi_open_only=kpi_open_only,
        skip=skip,
        limit=limit,
    )
    reads = await tasks_to_reads(db, rows)
    await _enrich_document_titles(db, reads)
    return reads


@router.post(
    "/tasks",
    summary="Создать задачу",
    response_model=PortalTaskRead,
    status_code=201,
)
async def create_task(
    user: CurrentUser,
    db: DbSession,
    body: PortalTaskCreate,
    bg: BackgroundTasks,
) -> PortalTaskRead:
    task = await svc.create_task(db, user, body)
    bg.add_task(
        emb_svc.upsert_embedding_bg,
        "task",
        str(task.id),
        task_to_text(task.title, task.description),
        task_meta(
            creator_sub=task.creator_sub,
            assignee_sub=task.assignee_sub,
            status=task.status,
        ),
    )
    return await single_task_to_read(db, task)


@router.post(
    "/tasks/reorder",
    summary="Переупорядочить задачу в колонке канбана",
    response_model=PortalTaskRead,
)
async def reorder_task(
    user: CurrentUser,
    db: DbSession,
    body: TaskReorderRequest,
) -> PortalTaskRead:
    task = await svc.reorder_task(
        db,
        user,
        body.task_id,
        body.status,
        after_task_id=body.after_task_id,
        before_task_id=body.before_task_id,
    )
    read = await single_task_to_read(db, task)
    await _enrich_document_titles(db, [read])
    return read


@router.get(
    "/tasks/by-number/{number}",
    summary="Задача по порядковому номеру",
    response_model=PortalTaskRead,
)
async def get_task_by_number(
    number: int,
    user: CurrentUser,
    db: DbSession,
) -> PortalTaskRead:
    """Возвращает задачу по её порядковому номеру."""
    task = await svc.get_task_by_number(db, user, number)
    return await single_task_to_read(db, task)


@router.get(
    "/tasks/{task_id}",
    summary="Задача по ID",
    response_model=PortalTaskRead,
)
async def get_task(
    task_id: uuid.UUID,
    user: CurrentUser,
    db: DbSession,
) -> PortalTaskRead:
    task = await svc.get_task(db, user, task_id)
    read = await single_task_to_read(db, task)
    await _enrich_document_titles(db, [read])
    return read


@router.patch(
    "/tasks/{task_id}",
    summary="Обновить задачу",
    response_model=PortalTaskRead,
)
async def update_task(
    task_id: uuid.UUID,
    user: CurrentUser,
    db: DbSession,
    body: PortalTaskUpdate,
    bg: BackgroundTasks,
) -> PortalTaskRead:
    task = await svc.update_task(db, user, task_id, body)
    bg.add_task(
        emb_svc.upsert_embedding_bg,
        "task",
        str(task.id),
        task_to_text(task.title, task.description),
        task_meta(
            creator_sub=task.creator_sub,
            assignee_sub=task.assignee_sub,
            status=task.status,
        ),
    )
    read = await single_task_to_read(db, task)
    await _enrich_document_titles(db, [read])
    return read


@router.post(
    "/tasks/{task_id}/rich-media",
    summary="Загрузить изображение для описания задачи",
    response_model=RichMediaRead,
    status_code=status.HTTP_201_CREATED,
)
async def upload_task_rich_media(
    task_id: uuid.UUID,
    user: CurrentUser,
    db: DbSession,
    file: UploadFile = File(...),
) -> RichMediaRead:
    """Загружает изображение в хранилище; в HTML сохраняйте file_path из ответа."""
    async with open_upload_stream(file, get_settings().attachment_max_size_bytes) as (file_data, file_size):
        media = await rich_media_svc.upload_task_rich_media(
            db,
            user,
            task_id,
            file_data=file_data,
            file_size=file_size,
            content_type=file.content_type or "application/octet-stream",
            original_filename=file.filename or "image",
        )
    return rich_media_svc.rich_media_to_read(media)


@router.delete(
    "/tasks/{task_id}",
    summary="Удалить задачу",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_task(
    task_id: uuid.UUID,
    user: CurrentUser,
    db: DbSession,
    bg: BackgroundTasks,
) -> None:
    await svc.delete_task(db, user, task_id)
    bg.add_task(emb_svc.delete_embedding_bg, "task", str(task_id))


@router.get(
    "/tasks/{task_id}/history",
    summary="История изменений задачи",
    response_model=list[PortalTaskHistoryRead],
)
async def list_task_history(
    task_id: uuid.UUID,
    user: CurrentUser,
    db: DbSession,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
) -> list[PortalTaskHistoryRead]:
    items = await svc.list_task_history(db, user, task_id, skip=skip, limit=limit)
    return [PortalTaskHistoryRead.model_validate(h) for h in items]


@router.post(
    "/tasks/jira/backfill",
    summary="Backfill задач в Jira TASKS (только portal_admin; jira_tasks_sync_enabled)",
)
async def backfill_tasks_jira(
    user: CurrentUser,
    db: DbSession,
    http_client: HttpClient,
    limit: int | None = Query(default=None, ge=1, le=500),
) -> dict[str, int]:
    from app.core.config import get_settings
    from app.core.exceptions import ForbiddenError, ServiceUnavailableError
    from app.portal_collab.services.task_jira_backfill import backfill_tasks_to_jira

    if not user.is_portal_admin:
        raise ForbiddenError("Backfill Jira — только администратор портала")
    if not get_settings().jira_tasks_outbound_enabled:
        raise ServiceUnavailableError("Outbound Jira задач выключен (JIRA_TASKS_SYNC_ENABLED)")
    return await backfill_tasks_to_jira(db, http_client, limit=limit)
