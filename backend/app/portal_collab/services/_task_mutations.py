from __future__ import annotations

import logging
import uuid
from typing import Any

from sqlalchemy import delete, func, literal, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import TaskStatus
from app.core.exceptions import ForbiddenError, NotFoundError, ValidationError
from app.core.optimistic_lock import compare_and_swap_row
from app.core.utils import now_utc as _now_utc
from app.infrastructure.db.models.portal_chat import PortalChat
from app.infrastructure.db.models.portal_document import PortalDocument
from app.infrastructure.db.models.portal_task import PortalTask, PortalTaskHistory, PortalTaskTag
from app.infrastructure.ws.managers import get_task_board_manager
from app.infrastructure.ws.room_manager import TASK_BOARD_ROOM_ID
from app.portal_chat.services import chat as chat_svc
from app.portal_collab.schemas.task import PortalTaskCreate, PortalTaskUpdate
from app.portal_collab.services import notification as notification_svc
from app.portal_collab.services._task_assignees import (
    load_assignee_subs_for_task,
    normalize_assignee_subs,
    sync_task_assignees,
)
from app.portal_collab.services._task_queries import (
    _apply_list_tasks_filters,
    get_task,
    user_can_change_task_assignees,
    user_can_delete_task,
    user_can_edit_task,
)
from app.portal_collab.services.task_column import assert_valid_task_status
from app.portal_collab.services.task_jira_schedule import schedule_jira_issue_delete, schedule_task_jira_push
from app.schemas.auth import UserPublic
from app.services import rbac

logger = logging.getLogger(__name__)

_TASK_CAS_CONFLICT = "Задача изменена другим пользователем"
_TASK_ROW_FIELDS = frozenset(
    {
        "title",
        "description",
        "assignee_sub",
        "assignee_subs",
        "status",
        "priority",
        "due_at",
        "document_id",
        "parent_task_id",
    },
)
_PARENT_CHAIN_DEPTH_LIMIT = 32


async def _publish_board_event(event_type: str, task_id: uuid.UUID, actor_sub: str) -> None:
    """Публикует событие в единый глобальный WS-канал доски задач."""
    try:
        await get_task_board_manager().publish(
            TASK_BOARD_ROOM_ID,
            {"type": event_type, "task_id": str(task_id), "actor_sub": actor_sub},
        )
    except Exception:
        logger.exception("Не удалось опубликовать событие доски задач: %s task_id=%s", event_type, task_id)


async def _replace_task_tags(session: AsyncSession, task_id: uuid.UUID, tag_ids: list[uuid.UUID]) -> None:
    """Полностью пересинхронизировать теги задачи: удалить все и вставить новые."""
    await session.execute(delete(PortalTaskTag).where(PortalTaskTag.task_id == task_id))
    for tid in tag_ids:
        session.add(PortalTaskTag(task_id=task_id, tag_id=tid))


async def _write_history(session: AsyncSession, task_id: uuid.UUID, changed_by_sub: str, diff: dict[str, Any]) -> None:
    session.add(
        PortalTaskHistory(
            task_id=task_id,
            changed_by_sub=changed_by_sub,
            changed_at=_now_utc(),
            diff=diff,
        )
    )


async def _validate_task_links(
    session: AsyncSession,
    user: UserPublic,
    *,
    document_id: uuid.UUID | None,
    source_message_id: uuid.UUID | None,
    chat_id: uuid.UUID | None,
) -> None:
    if document_id is not None:
        doc = await session.get(PortalDocument, document_id)
        if doc is None or doc.deleted_at is not None:
            raise NotFoundError("Документ не найден")
        if not rbac.user_can_access_documents(user):
            logger.warning(
                "Отказ в доступе к документу при создании задачи: user_sub=%s document_id=%s",
                user.sub,
                document_id,
            )
            raise ForbiddenError("Нет доступа к документам")
    if source_message_id is not None:
        if not await chat_svc.user_can_access_message(session, user, source_message_id):
            logger.warning(
                "Отказ в доступе к сообщению при создании задачи: user_sub=%s message_id=%s",
                user.sub,
                source_message_id,
            )
            raise ForbiddenError("Нет доступа к сообщению")
    if chat_id is not None:
        ch = await session.get(PortalChat, chat_id)
        if ch is None:
            raise NotFoundError("Чат не найден")
        if not user.is_portal_admin and not await chat_svc.user_is_chat_member(session, chat_id, user.sub):
            logger.warning(
                "Отказ в доступе к чату при создании задачи: user_sub=%s chat_id=%s",
                user.sub,
                chat_id,
            )
            raise ForbiddenError("Нет доступа к чату")


async def create_task(session: AsyncSession, user: UserPublic, data: PortalTaskCreate) -> PortalTask:
    await _validate_task_links(
        session,
        user,
        document_id=data.document_id,
        source_message_id=data.source_message_id,
        chat_id=data.chat_id,
    )
    if data.parent_task_id is not None:
        parent_task = await get_task(session, user, data.parent_task_id)
    else:
        parent_task = None
    now = _now_utc()
    assignees_omitted = "assignee_subs" not in data.model_fields_set and "assignee_sub" not in data.model_fields_set
    if parent_task is not None and assignees_omitted:
        assignee_subs = normalize_assignee_subs([row.assignee_sub for row in parent_task.task_assignees])
    else:
        assignee_subs = normalize_assignee_subs(data.assignee_subs)
    tag_ids: list[uuid.UUID] = list(data.tag_ids) if data.tag_ids else []
    if parent_task is not None and not tag_ids:
        tag_rows = await session.execute(
            select(PortalTaskTag.tag_id).where(PortalTaskTag.task_id == parent_task.id),
        )
        tag_ids = list(tag_rows.scalars().all())
    task_status = data.status if data.status else TaskStatus.TODO.value
    if data.status is not None:
        await assert_valid_task_status(session, task_status)
    task = PortalTask(
        title=data.title,
        description=data.description,
        creator_sub=user.sub,
        assignee_sub=assignee_subs[0] if assignee_subs else None,
        status=task_status,
        priority=data.priority.value,
        due_at=data.due_at,
        document_id=data.document_id,
        source_message_id=data.source_message_id,
        chat_id=data.chat_id,
        parent_task_id=data.parent_task_id,
        is_tour_demo=bool(data.is_tour_demo),
        created_at=now,
        updated_at=now,
    )
    session.add(task)
    await session.flush()
    await sync_task_assignees(session, task, assignee_subs)
    await _write_history(
        session,
        task.id,
        user.sub,
        {"action": {"old": None, "new": "created"}},
    )
    if tag_ids:
        await _replace_task_tags(session, task.id, tag_ids)
    notified = await notification_svc.create_assignment_notifications(session, task, user.sub, assignee_subs)
    await session.commit()
    if notified:
        from app.portal_chat.services.inbox_publish import publish_portal_notification_updates

        await publish_portal_notification_updates(list(notified.keys()), notification_ids_by_sub=notified)
    await _publish_board_event("task_created", task.id, user.sub)
    schedule_task_jira_push(task.id)
    return await get_task(session, user, task.id)


async def _assert_parent_task_change(
    session: AsyncSession,
    user: UserPublic,
    task: PortalTask,
    parent_task_id: uuid.UUID | None,
) -> None:
    """Проверить смену родителя у уже созданной задачи."""
    if parent_task_id is None or parent_task_id == task.parent_task_id:
        return
    if parent_task_id == task.id:
        raise ValidationError("Нельзя назначить задачу родителем самой себя")
    if task.parent_task_id is not None:
        raise ValidationError("У задачи уже есть другой родитель")
    await get_task(session, user, parent_task_id)
    if await _parent_link_closes_cycle(session, task.id, parent_task_id):
        raise ValidationError("Нельзя замкнуть цикл родительских задач")


async def _parent_link_closes_cycle(
    session: AsyncSession,
    task_id: uuid.UUID,
    parent_task_id: uuid.UUID,
) -> bool:
    """True, если предложенный родитель уже лежит в потомках задачи."""
    table = PortalTask.__table__
    base = select(
        table.c.id,
        table.c.parent_task_id,
        literal(0).label("depth"),
    ).where(table.c.id == parent_task_id)
    ancestors = base.cte(name="task_parent_ancestors", recursive=True)
    step = select(
        table.c.id,
        table.c.parent_task_id,
        (ancestors.c.depth + 1).label("depth"),
    ).where(
        table.c.id == ancestors.c.parent_task_id,
        ancestors.c.depth < _PARENT_CHAIN_DEPTH_LIMIT,
    )
    ancestors = ancestors.union_all(step)
    found = await session.scalar(
        select(func.count()).select_from(ancestors).where(ancestors.c.id == task_id),
    )
    return bool(found)


async def update_task(
    session: AsyncSession,
    user: UserPublic,
    task_id: uuid.UUID,
    data: PortalTaskUpdate,
) -> PortalTask:
    task = await get_task(session, user, task_id)
    if not await user_can_edit_task(session, user, task):
        logger.warning(
            "Отказ в изменении задачи: user_sub=%s task_id=%s",
            user.sub,
            task_id,
        )
        raise ForbiddenError("Нет прав на изменение задачи")
    diff: dict[str, Any] = {}
    assign_notify_subs: dict[str, uuid.UUID] = {}
    update_patch = data.model_dump(exclude_unset=True)
    update_patch.pop("expected_version", None)

    has_row_changes = bool(_TASK_ROW_FIELDS.intersection(update_patch))
    has_tags = data.tag_ids is not None
    if not has_row_changes and not has_tags:
        return task

    values: dict[str, Any] = {"updated_at": _now_utc()}
    new_subs: list[str] | None = None
    old_subs: list[str] | None = None

    if data.title is not None and data.title != task.title:
        diff["title"] = {"old": task.title, "new": data.title}
        values["title"] = data.title
    if "description" in update_patch:
        next_description = update_patch["description"]
        if next_description != task.description:
            diff["description"] = {"old": task.description, "new": next_description}
            values["description"] = next_description
    if "assignee_subs" in update_patch or "assignee_sub" in update_patch:
        if not await user_can_change_task_assignees(session, user, task):
            logger.warning(
                "Отказ в смене исполнителей: user_sub=%s task_id=%s (только автор или portal_admin)",
                user.sub,
                task_id,
            )
            raise ForbiddenError("Менять исполнителей может только автор задачи или администратор портала")
        old_subs = await load_assignee_subs_for_task(session, task.id)
        if "assignee_subs" in update_patch:
            new_subs = normalize_assignee_subs(data.assignee_subs or [])
        else:
            new_subs = normalize_assignee_subs([data.assignee_sub] if data.assignee_sub else [])
        if new_subs != old_subs:
            diff["assignee_subs"] = {"old": old_subs, "new": new_subs}
            values["assignee_sub"] = new_subs[0] if new_subs else None
        else:
            new_subs = None
            old_subs = None
    if data.status is not None and data.status != task.status:
        await assert_valid_task_status(session, data.status)
        diff["status"] = {"old": task.status, "new": data.status}
        values["status"] = data.status
    if data.priority is not None and data.priority.value != task.priority:
        diff["priority"] = {"old": task.priority, "new": data.priority.value}
        values["priority"] = data.priority.value
    if "due_at" in update_patch and data.due_at != task.due_at:
        diff["due_at"] = {
            "old": str(task.due_at) if task.due_at else None,
            "new": str(data.due_at) if data.due_at else None,
        }
        values["due_at"] = data.due_at
    if "document_id" in update_patch:
        next_doc = update_patch["document_id"]
        if next_doc is not None:
            doc = await session.get(PortalDocument, next_doc)
            if doc is None or doc.deleted_at is not None:
                raise NotFoundError("Документ не найден")
            if not rbac.user_can_access_documents(user):
                logger.warning(
                    "Отказ в доступе к документу при обновлении задачи: user_sub=%s document_id=%s",
                    user.sub,
                    next_doc,
                )
                raise ForbiddenError("Нет доступа к документам")
        if next_doc != task.document_id:
            diff["document_id"] = {
                "old": str(task.document_id) if task.document_id else None,
                "new": str(next_doc) if next_doc else None,
            }
            values["document_id"] = next_doc
    if "parent_task_id" in update_patch:
        next_parent = update_patch["parent_task_id"]
        await _assert_parent_task_change(session, user, task, next_parent)
        if next_parent != task.parent_task_id:
            diff["parent_task_id"] = {
                "old": str(task.parent_task_id) if task.parent_task_id else None,
                "new": str(next_parent) if next_parent else None,
            }
            values["parent_task_id"] = next_parent

    if not diff and not has_tags and set(values.keys()) == {"updated_at"}:
        return task

    new_version = await compare_and_swap_row(
        session,
        PortalTask,
        entity_id=task_id,
        expected_version=data.expected_version,
        values=values,
        conflict_message=_TASK_CAS_CONFLICT,
    )
    await session.refresh(task)
    task.version = new_version

    if new_subs is not None and old_subs is not None:
        await sync_task_assignees(session, task, new_subs)
        assign_notify_subs = await notification_svc.create_assignment_notifications(
            session,
            task,
            user.sub,
            [s for s in new_subs if s not in old_subs],
        )
    if diff:
        await _write_history(session, task_id, user.sub, diff)
    if data.tag_ids is not None:
        await _replace_task_tags(session, task_id, data.tag_ids)
        session.expire(task, ["tags"])
    await session.commit()
    if assign_notify_subs:
        from app.portal_chat.services.inbox_publish import publish_portal_notification_updates

        await publish_portal_notification_updates(
            list(assign_notify_subs.keys()),
            notification_ids_by_sub=assign_notify_subs,
        )
    await _publish_board_event("task_updated", task_id, user.sub)
    schedule_task_jira_push(task_id)
    await session.refresh(task)
    return task


async def delete_task(session: AsyncSession, user: UserPublic, task_id: uuid.UUID) -> None:
    """Удалить задачу вместе с подзадачами.

    Право: ``portal_admin``; автор учебной ``is_tour_demo``; менеджер — только свои.
    """
    task = await get_task(session, user, task_id)
    if not user_can_delete_task(user, task):
        logger.warning(
            "Отказ в удалении задачи: user_sub=%s task_id=%s",
            user.sub,
            task_id,
        )
        raise ForbiddenError(
            "Удалять задачу может администратор портала, менеджер — свою, или автор учебной задачи онбординга",
        )

    subtasks_result = await session.execute(select(PortalTask).where(PortalTask.parent_task_id == task_id))
    subtasks = subtasks_result.scalars().all()
    notify_task_ids = [task_id, *[subtask.id for subtask in subtasks]]
    withdraw_subs = await notification_svc.recipient_subs_for_task_notifications(session, notify_task_ids)
    child_jira_keys = [subtask.jira_issue_key for subtask in subtasks if subtask.jira_issue_key]
    parent_jira_key = task.jira_issue_key
    for subtask in subtasks:
        await session.delete(subtask)

    await session.delete(task)
    await session.commit()
    if withdraw_subs:
        from app.portal_chat.services.inbox_publish import publish_portal_notification_withdrawals

        await publish_portal_notification_withdrawals(withdraw_subs)
    await _publish_board_event("task_deleted", task_id, user.sub)
    schedule_jira_issue_delete(child_jira_keys, parent_key=parent_jira_key)


def _resolve_reorder_insert_index(
    others: list[PortalTask],
    after_task_id: uuid.UUID | None,
    before_task_id: uuid.UUID | None,
) -> int:
    """Индекс вставки в ``others`` по якорю соседа (см. docstring ``reorder_task``)."""
    if after_task_id is not None:
        idx = next((i for i, t in enumerate(others) if t.id == after_task_id), None)
        return idx + 1 if idx is not None else len(others)
    if before_task_id is not None:
        idx = next((i for i, t in enumerate(others) if t.id == before_task_id), None)
        return idx if idx is not None else 0
    return 0


async def reorder_task(
    session: AsyncSession,
    user: UserPublic,
    task_id: uuid.UUID,
    status: str,
    after_task_id: uuid.UUID | None = None,
    before_task_id: uuid.UUID | None = None,
) -> PortalTask:
    """Переместить задачу в рамках статуса (может менять статус при перебросе колонки).

    Позиция задаётся ЯКОРЕМ соседней задачи (``after_task_id``/``before_task_id``), а не
    индексом: список задач на фронте может быть отфильтрован (например режим «Мои задачи»),
    тогда как здесь переиндексируются ВСЕ видимые пользователю по RBAC задачи статуса —
    индекс в отфильтрованном списке не соответствует индексу в этом полном списке. Якорь —
    ID конкретной соседней задачи — однозначен в обоих случаях.

    Если у задачи есть родитель и статус не меняется, переиндексируются только сёстры
    (любой статус): порядок списка подзадач и вложенного стека на канбане.
    """
    task = await get_task(session, user, task_id)
    if not await user_can_edit_task(session, user, task):
        logger.warning(
            "Отказ в перемещении задачи: user_sub=%s task_id=%s",
            user.sub,
            task_id,
        )
        raise ForbiddenError("Нет прав на перемещение задачи")
    await assert_valid_task_status(session, status)
    sibling_order = task.parent_task_id is not None and status == task.status
    if sibling_order:
        base_stmt = select(PortalTask).where(
            or_(
                PortalTask.parent_task_id == task.parent_task_id,
                PortalTask.id == task_id,
            )
        )
    else:
        base_stmt = select(PortalTask).where(
            or_(
                PortalTask.status == status,
                PortalTask.id == task_id,
            )
        )
    base_stmt = _apply_list_tasks_filters(
        base_stmt,
        user,
        mine_only=False,
    )
    base_stmt = base_stmt.order_by(PortalTask.id.asc())
    if session.get_bind().dialect.name == "postgresql":
        base_stmt = base_stmt.with_for_update()
    locked: list[PortalTask] = list((await session.execute(base_stmt)).scalars().all())
    task_moving = next((t for t in locked if t.id == task_id), None)
    if task_moving is None:
        raise NotFoundError("Запись не найдена")
    if sibling_order:
        others = [t for t in locked if t.id != task_id]
    else:
        others = [t for t in locked if t.status == status and t.id != task_id]
    others.sort(key=lambda t: (t.position, t.created_at, t.id))
    insert_at = _resolve_reorder_insert_index(others, after_task_id, before_task_id)
    others.insert(insert_at, task_moving)
    for i, t in enumerate(others):
        t.position = i
    task_moving.status = status
    task_moving.updated_at = _now_utc()
    logger.info(
        "Перемещение задачи: user_sub=%s task=#%s status=%s after=#%s before=#%s insert_at=%s/%s итоговый_порядок=%s",
        user.sub,
        task_moving.number,
        status,
        next((t.number for t in others if t.id == after_task_id), None) if after_task_id else None,
        next((t.number for t in others if t.id == before_task_id), None) if before_task_id else None,
        insert_at,
        len(others) - 1,
        [t.number for t in others],
    )
    await session.commit()
    await _publish_board_event("task_updated", task_id, user.sub)
    schedule_task_jira_push(task_id)
    return await get_task(session, user, task_id)
