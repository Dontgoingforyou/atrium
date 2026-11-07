"""FastAPI-роуты для доски воронки специалистов."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Query

from app.api.deps import DbSession
from app.api.deps_auth import CurrentUser, PortalAdminUser, PortalManagerOrAdminUser
from app.infrastructure.db.models.portal_manager_specialist import PortalManagerSpecialist
from app.portal_specialists.schemas.board import (
    ManagerReassignBody,
    ManagerSpecialistAdd,
    ManagerSpecialistEntryRead,
    ManagerSpecialistPatch,
    ManagerSpecialistReorder,
    SpecialistColumnCreate,
    SpecialistColumnRead,
    SpecialistColumnUpdate,
    SpecialistManagerRef,
    SpecialistStatusCreate,
    SpecialistStatusRead,
    SpecialistStatusUpdate,
)
from app.portal_specialists.services import board as svc

router = APIRouter(prefix="/portal/specialists", tags=["Специалисты — доска"])


# ---------------------------------------------------------------------------
# Колонки воронки
# ---------------------------------------------------------------------------


@router.get(
    "/columns",
    response_model=list[SpecialistColumnRead],
    summary="Список колонок воронки специалистов",
    # Справочник воронки — малый набор (десятки колонок), без PagedResponse.
)
async def get_columns(
    user: PortalManagerOrAdminUser,
    session: DbSession,
) -> list[SpecialistColumnRead]:
    cols = await svc.list_specialist_columns(session, user)
    return [SpecialistColumnRead.model_validate(c) for c in cols]


@router.post(
    "/columns",
    response_model=SpecialistColumnRead,
    status_code=201,
    summary="Создать колонку воронки (администратор)",
)
async def create_column(
    user: PortalAdminUser,
    data: SpecialistColumnCreate,
    session: DbSession,
) -> SpecialistColumnRead:
    col = await svc.create_specialist_column(session, user, data)
    return SpecialistColumnRead.model_validate(col)


@router.patch(
    "/columns/{col_id}",
    response_model=SpecialistColumnRead,
    summary="Обновить колонку воронки (администратор)",
)
async def update_column(
    col_id: uuid.UUID,
    user: PortalAdminUser,
    data: SpecialistColumnUpdate,
    session: DbSession,
) -> SpecialistColumnRead:
    col = await svc.update_specialist_column(session, user, col_id, data)
    return SpecialistColumnRead.model_validate(col)


@router.delete(
    "/columns/{col_id}",
    status_code=204,
    summary="Удалить колонку воронки (администратор)",
)
async def delete_column(
    col_id: uuid.UUID,
    user: PortalAdminUser,
    session: DbSession,
) -> None:
    await svc.delete_specialist_column(session, user, col_id)


# ---------------------------------------------------------------------------
# Статусы специалистов
# ---------------------------------------------------------------------------


@router.get(
    "/statuses",
    response_model=list[SpecialistStatusRead],
    summary="Список статусов специалистов",
    # Legacy-справочник, малый набор; без PagedResponse.
)
async def get_statuses(
    user: PortalManagerOrAdminUser,
    session: DbSession,
) -> list[SpecialistStatusRead]:
    statuses = await svc.list_specialist_statuses(session, user)
    return [SpecialistStatusRead.model_validate(s) for s in statuses]


@router.post(
    "/statuses",
    response_model=SpecialistStatusRead,
    status_code=201,
    summary="Создать статус (менеджер или администратор)",
)
async def create_status(
    # Намеренное отступление от security.mdc (раздел «мутации глобальных справочников»):
    # статусы создаются «на лету» при выборе, как теги — PortalAdminUser здесь избыточен.
    # Обновление и удаление статусов закрыты за PortalAdminUser (см. update_status / delete_status).
    user: CurrentUser,
    data: SpecialistStatusCreate,
    session: DbSession,
) -> SpecialistStatusRead:
    status = await svc.create_specialist_status(session, user, data)
    return SpecialistStatusRead.model_validate(status)


@router.patch(
    "/statuses/{status_id}",
    response_model=SpecialistStatusRead,
    summary="Обновить статус (администратор)",
)
async def update_status(
    status_id: uuid.UUID,
    user: PortalAdminUser,
    data: SpecialistStatusUpdate,
    session: DbSession,
) -> SpecialistStatusRead:
    status = await svc.update_specialist_status(session, user, status_id, data)
    return SpecialistStatusRead.model_validate(status)


@router.delete(
    "/statuses/{status_id}",
    status_code=204,
    summary="Удалить статус (администратор)",
)
async def delete_status(
    status_id: uuid.UUID,
    user: PortalAdminUser,
    session: DbSession,
) -> None:
    await svc.delete_specialist_status(session, user, status_id)


# ---------------------------------------------------------------------------
# Доска специалистов
# ---------------------------------------------------------------------------


def _entry_read_or_fallback(
    rows: list[ManagerSpecialistEntryRead],
    entry: PortalManagerSpecialist,
) -> ManagerSpecialistEntryRead:
    """Найти обогащённую строку записи в свежем списке доски менеджера.

    Профиль/аватар специалиста подтягиваются JOIN'ом в list_board_entries; если запись
    там не нашлась (граничный случай гонки с параллельным удалением) — отдаём минимальный
    DTO из самой мутированной ORM-записи с пустыми display-полями, а не 500.
    """
    for row in rows:
        if row.id == entry.id:
            return row
    return ManagerSpecialistEntryRead(
        id=entry.id,
        specialist_sub=entry.specialist_sub,
        display_name=None,
        email=None,
        avatar_url=None,
        column_key=entry.column_key,
        position=entry.position,
        version=entry.version,
        manager_sub=entry.manager_sub,
        manager_display_name=None,
        status_id=None,
        status_title=None,
        status_color=None,
        created_at=entry.created_at,
    )


@router.get(
    "/board",
    response_model=list[ManagerSpecialistEntryRead],
    summary="Список специалистов на доске воронки",
    # Контракт SPA — list[T]. Directory может вырасти: SQL LIMIT в list_board_entries.
)
async def get_board(
    user: CurrentUser,
    session: DbSession,
    manager_sub: Annotated[str | None, Query(description="Фильтр по менеджеру")] = None,
    directory: Annotated[
        bool,
        Query(description="Справочник «Все специалисты»: все закрепления (чтение)"),
    ] = False,
) -> list[ManagerSpecialistEntryRead]:
    return await svc.list_board_entries(session, user, manager_sub=manager_sub, directory=directory)


@router.post(
    "/board",
    response_model=ManagerSpecialistEntryRead,
    status_code=201,
    summary="Добавить специалиста на доску воронки",
)
async def add_to_board(
    user: CurrentUser,
    data: ManagerSpecialistAdd,
    session: DbSession,
    manager_sub: Annotated[str | None, Query(description="Менеджер доски (только для администратора)")] = None,
) -> ManagerSpecialistEntryRead:
    entry = await svc.add_to_board(session, user, data, target_manager_sub=manager_sub)
    rows = await svc.list_board_entries(session, user, manager_sub=entry.manager_sub)
    return _entry_read_or_fallback(rows, entry)


@router.patch(
    "/board/{specialist_sub}",
    response_model=ManagerSpecialistEntryRead,
    summary="Переместить специалиста / сменить статус на доске",
)
async def patch_board_entry(
    specialist_sub: str,
    user: CurrentUser,
    data: ManagerSpecialistPatch,
    session: DbSession,
    manager_sub: Annotated[str | None, Query(description="Менеджер доски (только для администратора)")] = None,
) -> ManagerSpecialistEntryRead:
    entry = await svc.move_on_board(session, user, specialist_sub, data, target_manager_sub=manager_sub)
    rows = await svc.list_board_entries(session, user, manager_sub=entry.manager_sub)
    return _entry_read_or_fallback(rows, entry)


@router.post(
    "/board/reorder",
    response_model=ManagerSpecialistEntryRead,
    summary="Изменить порядок специалиста на доске менеджера",
)
async def reorder_board_entry(
    user: CurrentUser,
    data: ManagerSpecialistReorder,
    session: DbSession,
    manager_sub: Annotated[str | None, Query(description="Менеджер доски (только для администратора)")] = None,
) -> ManagerSpecialistEntryRead:
    entry = await svc.reorder_on_board(
        session,
        user,
        data,
        target_manager_sub=manager_sub,
    )
    rows = await svc.list_board_entries(session, user, manager_sub=entry.manager_sub)
    return _entry_read_or_fallback(rows, entry)


@router.post(
    "/board/{specialist_sub}/reassign-manager",
    status_code=204,
    summary="Сменить менеджера у закрепления специалиста (администратор)",
)
async def reassign_board_manager(
    specialist_sub: str,
    data: ManagerReassignBody,
    user: PortalAdminUser,
    session: DbSession,
) -> None:
    await svc.reassign_manager(
        session,
        user,
        specialist_sub,
        from_manager_sub=data.from_manager_sub,
        to_manager_sub=data.to_manager_sub,
    )


@router.delete(
    "/board/{specialist_sub}",
    status_code=204,
    summary="Убрать специалиста с доски воронки",
)
async def remove_from_board(
    specialist_sub: str,
    user: CurrentUser,
    session: DbSession,
    manager_sub: Annotated[str | None, Query(description="Менеджер доски (только для администратора)")] = None,
) -> None:
    await svc.remove_from_board(session, user, specialist_sub, target_manager_sub=manager_sub)


@router.get(
    "/board/by-specialist",
    response_model=list[SpecialistManagerRef],
    summary="Менеджеры, закреплённые за специалистом (только администратор)",
    description=(
        "Возвращает список всех менеджеров, у которых данный специалист добавлен на доску. "
        "Доступен только администратору портала. Малый набор (менеджеры одного специалиста)."
    ),
)
async def list_managers_for_specialist(
    specialist_sub: Annotated[str, Query(description="sub специалиста в Keycloak")],
    user: CurrentUser,
    session: DbSession,
) -> list[SpecialistManagerRef]:
    return await svc.list_managers_for_specialist(session, user, specialist_sub)
