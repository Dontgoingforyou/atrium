from __future__ import annotations

import logging
import uuid
from typing import Any

from sqlalchemy import func as sa_func
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.sql import Select

from app.core.enums import TaskStatus
from app.core.exceptions import ForbiddenError, NotFoundError
from app.core.permissions import is_manager_or_admin
from app.core.text_search import escape_ilike_pattern
from app.core.utils import now_utc
from app.infrastructure.db.models.portal_chat import PortalChatMember, PortalChatMessage
from app.infrastructure.db.models.portal_task import PortalTask, PortalTaskHistory, PortalTaskTag
from app.infrastructure.db.models.portal_task_assignee import PortalTaskAssignee
from app.portal_chat.services import chat as chat_svc
from app.portal_collab.services._task_assignees import normalize_assignee_subs, user_is_task_assignee
from app.portal_collab.services._task_home_common import (
    _is_overdue_expr,
    apply_done_this_month_filter,
    apply_no_assignee_filter,
)
from app.portal_collab.services.task_column import (
    TaskColumnStatusSets,
    apply_kpi_active_filter,
    task_column_status_sets,
)
from app.schemas.auth import UserPublic

logger = logging.getLogger(__name__)


def _message_ids_in_user_chats_subquery(user_sub: str) -> Any:
    return (
        select(PortalChatMessage.id)
        .join(PortalChatMember, PortalChatMember.chat_id == PortalChatMessage.chat_id)
        .where(PortalChatMember.user_sub == user_sub)
    )


async def user_can_view_task(session: AsyncSession, user: UserPublic, task: PortalTask) -> bool:
    """Право видеть задачу — та же политика, что у ``_list_tasks_visibility_filters``."""
    if is_manager_or_admin(user):
        return True
    if task.creator_sub == user.sub or task.assignee_sub == user.sub:
        return True
    if await user_is_task_assignee(session, task.id, user.sub):
        return True
    if task.chat_id and await chat_svc.user_is_chat_member(session, task.chat_id, user.sub):
        return True
    if task.source_message_id and await chat_svc.user_can_access_message(session, user, task.source_message_id):
        return True
    return False


async def task_user_is_assignee(session: AsyncSession, task: PortalTask, user_sub: str) -> bool:
    """Пользователь — основной или дополнительный исполнитель задачи."""
    if task.assignee_sub == user_sub:
        return True
    return await user_is_task_assignee(session, task.id, user_sub)


async def user_can_edit_task(session: AsyncSession, user: UserPublic, task: PortalTask) -> bool:
    """Право менять поля задачи и перемещать на доске — автор, исполнитель или portal_admin."""
    if user.is_portal_admin:
        return True
    if task.creator_sub == user.sub:
        return True
    return await task_user_is_assignee(session, task, user.sub)


async def user_can_change_task_assignees(session: AsyncSession, user: UserPublic, task: PortalTask) -> bool:
    """Смена исполнителей — автор задачи или portal_admin."""
    _ = session
    if user.is_portal_admin:
        return True
    return task.creator_sub == user.sub


def user_can_delete_task(user: UserPublic, task: PortalTask) -> bool:
    """Удаление: portal_admin; автор учебной ``is_tour_demo``; менеджер — только свои."""
    if user.is_portal_admin:
        return True
    if task.creator_sub != user.sub:
        return False
    if bool(task.is_tour_demo):
        return True
    return is_manager_or_admin(user)


def _task_ids_for_assignee_sub(user_sub: str) -> Any:
    return select(PortalTaskAssignee.task_id).where(PortalTaskAssignee.assignee_sub == user_sub)


def _list_tasks_visibility_filters(user: UserPublic) -> list[Any]:
    """Условия видимости задач в списках (как у ``list_tasks``)."""
    if is_manager_or_admin(user):
        return []
    msg_sq = _message_ids_in_user_chats_subquery(user.sub)
    assignee_task_ids = _task_ids_for_assignee_sub(user.sub)
    return [
        or_(
            PortalTask.creator_sub == user.sub,
            PortalTask.assignee_sub == user.sub,
            PortalTask.id.in_(assignee_task_ids),
            PortalTask.chat_id.in_(select(PortalChatMember.chat_id).where(PortalChatMember.user_sub == user.sub)),
            PortalTask.source_message_id.in_(msg_sq),
        )
    ]


def visible_task_ids_subquery(user: UserPublic) -> Any:
    """Подзапрос id задач, видимых пользователю — та же политика, что у ``list_tasks``.

    Переиспользуется другими доменными сервисами вместо
    собственной копии условий видимости задач.
    """
    stmt: Select[Any] = select(PortalTask.id)
    for f in _list_tasks_visibility_filters(user):
        stmt = stmt.where(f)
    return stmt


def _apply_list_tasks_filters(stmt: Select[Any], user: UserPublic, *, mine_only: bool) -> Select[Any]:
    from sqlalchemy import and_

    for f in _list_tasks_visibility_filters(user):
        stmt = stmt.where(f)
    if mine_only:
        assignee_task_ids = _task_ids_for_assignee_sub(user.sub)
        stmt = stmt.where(
            or_(
                PortalTask.assignee_sub == user.sub,
                PortalTask.id.in_(assignee_task_ids),
                and_(
                    PortalTask.assignee_sub.is_(None),
                    ~PortalTask.id.in_(select(PortalTaskAssignee.task_id)),
                    PortalTask.creator_sub == user.sub,
                ),
            ),
        )
    return stmt


def _apply_board_subtask_isolation(stmt: Select[Any], user: UserPublic) -> Select[Any]:
    """Подзадача в ленте канбана у сотрудника — только автор или исполнитель этой строки.

    Роль руководителя видит все подзадачи, как и родительские задачи.
    """
    if is_manager_or_admin(user):
        return stmt
    assignee_task_ids = _task_ids_for_assignee_sub(user.sub)
    return stmt.where(
        or_(
            PortalTask.parent_task_id.is_(None),
            PortalTask.creator_sub == user.sub,
            PortalTask.assignee_sub == user.sub,
            PortalTask.id.in_(assignee_task_ids),
        ),
    )


def _normalize_status_filters(status: list[str] | None) -> list[str]:
    if not status:
        return []
    return list(dict.fromkeys(s.strip() for s in status if s and s.strip()))


def _expand_status_filters(statuses: list[str], sets: TaskColumnStatusSets) -> list[str]:
    """Чип «Завершена» (done) → done-like ключи, не колонка «На согласовании» с ключом done."""
    if not statuses:
        return []
    if TaskStatus.DONE.value not in statuses and TaskStatus.CANCELLED.value not in statuses:
        return statuses
    out: list[str] = []
    seen: set[str] = set()

    def _add(key: str) -> None:
        if key not in seen:
            seen.add(key)
            out.append(key)

    for status_key in statuses:
        if status_key == TaskStatus.DONE.value:
            if sets.done_like:
                for key in sets.done_like:
                    _add(key)
            elif TaskStatus.DONE.value not in sets.approval_like:
                _add(TaskStatus.DONE.value)
        elif status_key == TaskStatus.CANCELLED.value:
            _add(TaskStatus.CANCELLED.value)
            for key in sets.cancelled_like:
                _add(key)
        else:
            _add(status_key)
    return out


def _normalize_priority_filters(priority: list[str] | None) -> list[str]:
    if not priority:
        return []
    return list(dict.fromkeys(s.strip() for s in priority if s and s.strip()))


def _apply_priority_filter_with_family(stmt: Select[Any], priorities: list[str]) -> Select[Any]:
    """Фильтр приоритетов с учётом связи родитель ↔ подзадача."""
    match_priority = PortalTask.priority.in_(priorities)
    parents_of_matching = select(PortalTask.parent_task_id).where(
        match_priority,
        PortalTask.parent_task_id.isnot(None),
    )
    children_of_matching = select(PortalTask.id).where(
        PortalTask.parent_task_id.in_(select(PortalTask.id).where(match_priority)),
    )
    return stmt.where(
        or_(
            match_priority,
            PortalTask.id.in_(parents_of_matching),
            PortalTask.id.in_(children_of_matching),
        ),
    )


def _normalize_tag_ids(tag_ids: list[uuid.UUID] | None) -> list[uuid.UUID]:
    if not tag_ids:
        return []
    return list(dict.fromkeys(tag_ids))


def _normalize_assignee_filter(user: UserPublic, assignee_sub: list[str] | None) -> list[str]:
    subs_norm = normalize_assignee_subs(assignee_sub)
    if subs_norm and any(s != user.sub for s in subs_norm) and not is_manager_or_admin(user):
        logger.warning(
            "Отказ в доступе: просмотр задач чужого исполнителя запрещён user_sub=%s assignee_subs=%s",
            user.sub,
            subs_norm,
        )
        raise ForbiddenError("Просматривать задачи других исполнителей может только администратор или руководитель")
    return subs_norm


async def _fetch_listed_tasks(
    session: AsyncSession,
    user: UserPublic,
    *,
    mine_only: bool,
    assignee_sub: list[str] | None,
    document_id: uuid.UUID | None,
    chat_id: uuid.UUID | None,
    statuses: list[str],
    priority: list[str] | None,
    tag_id: list[uuid.UUID] | None,
    parent_task_id: uuid.UUID | None,
    overdue_only: bool,
    done_this_month: bool,
    no_assignee: bool,
    kpi_open_only: bool,
    skip: int,
    limit: int,
    column_sets: TaskColumnStatusSets | None,
) -> list[PortalTask]:
    """Общая выборка list_tasks / колонки: RBAC, assignee, точные статусы, LIMIT."""
    subs_norm = _normalize_assignee_filter(user, assignee_sub)
    stmt = _apply_list_tasks_filters(
        select(PortalTask).options(selectinload(PortalTask.tags), selectinload(PortalTask.task_assignees)),
        user,
        mine_only=mine_only,
    )
    if document_id is not None:
        stmt = stmt.where(PortalTask.document_id == document_id)
    if chat_id is not None:
        stmt = stmt.where(PortalTask.chat_id == chat_id)
    if statuses:
        stmt = stmt.where(PortalTask.status.in_(statuses))
    priorities_norm = _normalize_priority_filters(priority)
    if priorities_norm:
        stmt = _apply_priority_filter_with_family(stmt, priorities_norm)
    tag_ids_norm = _normalize_tag_ids(tag_id)
    if tag_ids_norm:
        stmt = stmt.where(
            PortalTask.id.in_(select(PortalTaskTag.task_id).where(PortalTaskTag.tag_id.in_(tag_ids_norm))),
        )
    if parent_task_id is not None:
        stmt = stmt.where(PortalTask.parent_task_id == parent_task_id)
    else:
        stmt = _apply_board_subtask_isolation(stmt, user)
    if subs_norm:
        stmt = stmt.where(
            or_(
                PortalTask.assignee_sub.in_(subs_norm),
                PortalTask.id.in_(
                    select(PortalTaskAssignee.task_id).where(PortalTaskAssignee.assignee_sub.in_(subs_norm)),
                ),
            ),
        )
    if overdue_only:
        assert column_sets is not None
        stmt = stmt.where(_is_overdue_expr(now_utc(), column_sets.kpi_inactive, column_sets.closed))
    if done_this_month:
        assert column_sets is not None
        stmt = apply_done_this_month_filter(stmt, column_sets.closed)
    if no_assignee:
        assert column_sets is not None
        stmt = apply_kpi_active_filter(apply_no_assignee_filter(stmt), column_sets.kpi_inactive)
    if kpi_open_only:
        assert column_sets is not None
        stmt = apply_kpi_active_filter(stmt, column_sets.kpi_inactive)
    stmt = stmt.order_by(PortalTask.position.asc(), PortalTask.created_at.desc()).offset(skip).limit(limit)
    return list((await session.execute(stmt)).scalars().all())


async def list_tasks(
    session: AsyncSession,
    user: UserPublic,
    *,
    mine_only: bool = False,
    assignee_sub: list[str] | None = None,
    document_id: uuid.UUID | None = None,
    chat_id: uuid.UUID | None = None,
    status: list[str] | None = None,
    priority: list[str] | None = None,
    tag_id: list[uuid.UUID] | None = None,
    parent_task_id: uuid.UUID | None = None,
    overdue_only: bool = False,
    done_this_month: bool = False,
    no_assignee: bool = False,
    kpi_open_only: bool = False,
    skip: int = 0,
    limit: int = 100,
) -> list[PortalTask]:
    statuses_raw = _normalize_status_filters(status)
    need_column_sets = (
        overdue_only
        or done_this_month
        or no_assignee
        or kpi_open_only
        or TaskStatus.DONE.value in statuses_raw
        or TaskStatus.CANCELLED.value in statuses_raw
    )
    column_sets = await task_column_status_sets(session) if need_column_sets else None
    statuses_norm = _expand_status_filters(statuses_raw, column_sets) if column_sets is not None else statuses_raw
    if statuses_raw and not statuses_norm:
        return []
    return await _fetch_listed_tasks(
        session,
        user,
        mine_only=mine_only,
        assignee_sub=assignee_sub,
        document_id=document_id,
        chat_id=chat_id,
        statuses=statuses_norm,
        priority=priority,
        tag_id=tag_id,
        parent_task_id=parent_task_id,
        overdue_only=overdue_only,
        done_this_month=done_this_month,
        no_assignee=no_assignee,
        kpi_open_only=kpi_open_only,
        skip=skip,
        limit=limit,
        column_sets=column_sets,
    )


async def list_tasks_by_exact_status(
    session: AsyncSession,
    user: UserPublic,
    statuses: list[str],
    *,
    mine_only: bool = False,
    assignee_sub: list[str] | None = None,
    skip: int = 0,
    limit: int = 100,
) -> list[PortalTask]:
    """Задачи колонки по точным status_key, без раскрытия чипа «Завершена»."""
    statuses_norm = _normalize_status_filters(statuses)
    if not statuses_norm:
        return []
    return await _fetch_listed_tasks(
        session,
        user,
        mine_only=mine_only,
        assignee_sub=assignee_sub,
        document_id=None,
        chat_id=None,
        statuses=statuses_norm,
        priority=None,
        tag_id=None,
        parent_task_id=None,
        overdue_only=False,
        done_this_month=False,
        no_assignee=False,
        kpi_open_only=False,
        skip=skip,
        limit=limit,
        column_sets=None,
    )


async def get_task(session: AsyncSession, user: UserPublic, task_id: uuid.UUID) -> PortalTask:
    stmt = select(PortalTask).options(selectinload(PortalTask.task_assignees)).where(PortalTask.id == task_id)
    task = (await session.execute(stmt)).scalar_one_or_none()
    if task is None:
        raise NotFoundError("Задача не найдена")
    if not await user_can_view_task(session, user, task):
        logger.warning(
            "Отказ в доступе к задаче: user_sub=%s task_id=%s",
            user.sub,
            task_id,
        )
        raise ForbiddenError("Нет доступа к задаче")
    return task


async def get_task_by_number(session: AsyncSession, user: UserPublic, number: int) -> PortalTask:
    """Поиск задачи по порядковому номеру (поле number). Те же правила доступа, что у get_task."""
    stmt = select(PortalTask).options(selectinload(PortalTask.task_assignees)).where(PortalTask.number == number)
    task = (await session.execute(stmt)).scalar_one_or_none()
    if task is None:
        raise NotFoundError("Задача не найдена")
    if not await user_can_view_task(session, user, task):
        logger.warning(
            "Отказ в доступе к задаче: user_sub=%s task_number=%s",
            user.sub,
            number,
        )
        raise ForbiddenError("Нет доступа к задаче")
    return task


async def list_task_history(
    session: AsyncSession,
    user: UserPublic,
    task_id: uuid.UUID,
    *,
    skip: int = 0,
    limit: int = 100,
) -> list[PortalTaskHistory]:
    await get_task(session, user, task_id)
    stmt = (
        select(PortalTaskHistory)
        .where(PortalTaskHistory.task_id == task_id)
        .order_by(PortalTaskHistory.changed_at)
        .offset(skip)
        .limit(limit)
    )
    return list((await session.execute(stmt)).scalars().all())


async def search_tasks_for_user(
    session: AsyncSession,
    user: UserPublic,
    q: str,
    *,
    skip: int = 0,
    limit: int = 100,
) -> list[PortalTask]:
    pl = f"%{escape_ilike_pattern(q.lower())}%"
    stmt = (
        select(PortalTask)
        .options(selectinload(PortalTask.tags))
        .where(
            or_(
                sa_func.lower(PortalTask.title).like(pl, escape="\\"),
                sa_func.lower(PortalTask.description).like(pl, escape="\\"),
            )
        )
    )
    stmt = _apply_list_tasks_filters(stmt, user, mine_only=False)
    stmt = stmt.order_by(PortalTask.created_at.desc()).offset(skip).limit(limit)
    return list((await session.execute(stmt)).scalars().all())
