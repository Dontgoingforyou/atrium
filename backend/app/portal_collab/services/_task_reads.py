"""Сборка PortalTaskRead с исполнителями."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db.models.portal_task import PortalTask
from app.portal_collab.schemas.task import PortalTaskRead
from app.portal_collab.services._task_assignees import load_assignee_subs_by_task_ids, load_assignee_subs_for_task


def _subs_from_task(task: PortalTask) -> list[str]:
    if task.task_assignees:
        return [a.assignee_sub for a in task.task_assignees]
    if task.assignee_sub:
        return [task.assignee_sub]
    return []


def task_to_read(task: PortalTask, assignee_subs: list[str] | None = None) -> PortalTaskRead:
    subs = assignee_subs if assignee_subs is not None else _subs_from_task(task)
    read = PortalTaskRead.model_validate(task)
    read.assignee_subs = subs
    if read.assignee_sub is None and subs:
        read.assignee_sub = subs[0]
    return read


async def tasks_to_reads(session: AsyncSession, tasks: list[PortalTask]) -> list[PortalTaskRead]:
    if not tasks:
        return []
    ids = [t.id for t in tasks]
    subs_map = await load_assignee_subs_by_task_ids(session, ids)
    return [task_to_read(t, subs_map.get(t.id, _subs_from_task(t))) for t in tasks]


async def single_task_to_read(session: AsyncSession, task: PortalTask) -> PortalTaskRead:
    subs = _subs_from_task(task)
    if not subs:
        subs = await load_assignee_subs_for_task(session, task.id)
    return task_to_read(task, subs)
