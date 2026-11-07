"""Исполнители задачи (junction portal_task_assignee)."""

from __future__ import annotations

import uuid

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db.models.portal_task import PortalTask
from app.infrastructure.db.models.portal_task_assignee import PortalTaskAssignee


def normalize_assignee_subs(subs: list[str] | None) -> list[str]:
    if not subs:
        return []
    return list(dict.fromkeys(s.strip() for s in subs if s and s.strip()))


async def load_assignee_subs_for_task(session: AsyncSession, task_id: uuid.UUID) -> list[str]:
    rows = (
        (
            await session.execute(
                select(PortalTaskAssignee.assignee_sub)
                .where(PortalTaskAssignee.task_id == task_id)
                .order_by(PortalTaskAssignee.assignee_sub),
            )
        )
        .scalars()
        .all()
    )
    return list(rows)


async def load_assignee_subs_by_task_ids(
    session: AsyncSession,
    task_ids: list[uuid.UUID],
) -> dict[uuid.UUID, list[str]]:
    if not task_ids:
        return {}
    rows = (
        await session.execute(
            select(PortalTaskAssignee.task_id, PortalTaskAssignee.assignee_sub)
            .where(PortalTaskAssignee.task_id.in_(task_ids))
            .order_by(PortalTaskAssignee.assignee_sub),
        )
    ).all()
    out: dict[uuid.UUID, list[str]] = {tid: [] for tid in task_ids}
    for task_id, sub in rows:
        out[task_id].append(sub)
    return out


async def sync_task_assignees(
    session: AsyncSession,
    task: PortalTask,
    assignee_subs: list[str],
) -> list[str]:
    """Пересинхронизировать исполнителей; обновляет ``task.assignee_sub`` (первый или None)."""
    subs = normalize_assignee_subs(assignee_subs)
    await session.execute(delete(PortalTaskAssignee).where(PortalTaskAssignee.task_id == task.id))
    for sub in subs:
        session.add(PortalTaskAssignee(task_id=task.id, assignee_sub=sub))
    task.assignee_sub = subs[0] if subs else None
    return subs


async def user_is_task_assignee(session: AsyncSession, task_id: uuid.UUID, user_sub: str) -> bool:
    found = await session.scalar(
        select(PortalTaskAssignee.id)
        .where(PortalTaskAssignee.task_id == task_id, PortalTaskAssignee.assignee_sub == user_sub)
        .limit(1),
    )
    return found is not None
