from __future__ import annotations

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Query
from fastapi.responses import Response

from app.api.deps import DbSession, HttpClient
from app.api.deps_auth import CurrentUser, PortalAdminUser
from app.portal_collab.schemas.task import (
    PortalTaskColumnCreate,
    PortalTaskColumnRead,
    PortalTaskColumnUpdate,
    TaskBoardPrefRead,
    TaskBoardPrefWrite,
)
from app.portal_collab.services import task as task_svc
from app.portal_collab.services import task_board_pref as board_pref_svc
from app.portal_collab.services import task_column as column_svc
from app.portal_collab.services import task_jira_column_sync as column_jira_sync

router = APIRouter(prefix="/portal", tags=["Задачи"])


@router.get(
    "/task-columns",
    summary="Список колонок канбана",
    response_model=list[PortalTaskColumnRead],
)
async def list_task_columns(
    user: CurrentUser,
    db: DbSession,
) -> list[PortalTaskColumnRead]:
    rows = await column_svc.list_task_columns(db, user)
    return [PortalTaskColumnRead.model_validate(r) for r in rows]


@router.post(
    "/task-columns",
    summary="Создать колонку канбана",
    response_model=PortalTaskColumnRead,
    status_code=201,
)
async def create_task_column(
    user: CurrentUser,
    db: DbSession,
    http: HttpClient,
    body: PortalTaskColumnCreate,
) -> PortalTaskColumnRead:
    column = await column_svc.create_task_column(db, user, body, http=http)
    return PortalTaskColumnRead.model_validate(column)


@router.post(
    "/task-columns/jira/sync-mapping",
    summary="Привязать колонки канбана к статусам доски AUTASKS (portal_admin)",
)
async def sync_task_column_jira_mapping(
    user: PortalAdminUser,
    db: DbSession,
    http: HttpClient,
) -> dict[str, Any]:
    return await column_jira_sync.sync_task_column_jira_status_ids(db, user, http)


@router.get(
    "/task-columns/{column_id}/export",
    summary="Выгрузка задач колонки в TXT",
    description=(
        "Возвращает текстовый файл с подробными карточками задач колонки: номер, название, "
        "приоритет, срок, исполнители, создатель, теги, Jira-ключ, ссылки, описание, "
        "родительская задача (номер/название/описание) и комментарии с ответами. "
        "RBAC и фильтры — как у GET /portal/tasks (видимость list_tasks; "
        "чужой assignee_sub — только менеджер/admin). Управление колонками не требуется. "
        "Без PagedResponse: обоснованный column-export с жёстким LIMIT 2000."
    ),
    response_class=Response,
)
async def export_task_column_tasks(
    column_id: uuid.UUID,
    user: CurrentUser,
    db: DbSession,
    mine_only: bool = Query(
        default=False,
        description=("Только задачи, где пользователь исполнитель, либо исполнитель не задан и пользователь автор"),
    ),
    assignee_sub: Annotated[
        list[str],
        Query(description="Фильтр по исполнителям (повтор query-параметра)"),
    ] = [],
) -> Response:
    file_bytes, filename, content_type = await task_svc.export_column_tasks_txt(
        db,
        user,
        column_id,
        mine_only=mine_only,
        assignee_sub=assignee_sub or None,
    )
    return Response(
        content=file_bytes,
        media_type=content_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.patch(
    "/task-columns/{column_id}",
    summary="Обновить колонку канбана",
    response_model=PortalTaskColumnRead,
)
async def update_task_column(
    column_id: uuid.UUID,
    user: CurrentUser,
    db: DbSession,
    http: HttpClient,
    body: PortalTaskColumnUpdate,
) -> PortalTaskColumnRead:
    column = await column_svc.update_task_column(db, user, column_id, body, http=http)
    return PortalTaskColumnRead.model_validate(column)


@router.delete(
    "/task-columns/{column_id}",
    summary="Удалить колонку канбана",
    status_code=204,
)
async def delete_task_column(
    column_id: uuid.UUID,
    user: CurrentUser,
    db: DbSession,
) -> None:
    await column_svc.delete_task_column(db, user, column_id)


@router.get(
    "/me/task-board-pref",
    summary="Персональные настройки канбана задач (текущий пользователь)",
    response_model=TaskBoardPrefRead,
)
async def get_my_task_board_pref(
    user: CurrentUser,
    db: DbSession,
) -> TaskBoardPrefRead:
    return await board_pref_svc.get_task_board_pref(db, user)


@router.put(
    "/me/task-board-pref",
    summary="Сохранить персональные настройки канбана задач",
    response_model=TaskBoardPrefRead,
)
async def put_my_task_board_pref(
    user: CurrentUser,
    db: DbSession,
    body: TaskBoardPrefWrite,
) -> TaskBoardPrefRead:
    return await board_pref_svc.put_task_board_pref(db, user, body)
