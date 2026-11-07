"""Backfill существующих portal_task → AUTASKS (только prod / sync enabled)."""

from __future__ import annotations

import asyncio
import logging

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.infrastructure.db.models.portal_task import PortalTask
from app.infrastructure.db.session import async_session_factory
from app.portal_collab.services.task_jira_outbound import push_task_to_jira

logger = logging.getLogger(__name__)


async def backfill_tasks_to_jira(
    session: AsyncSession,
    http: httpx.AsyncClient,
    *,
    limit: int | None = None,
    settings: Settings | None = None,
) -> dict[str, int]:
    """Создаёт issue для задач без jira_issue_key: сначала top-level, затем subtasks."""
    s = settings or get_settings()
    if not s.jira_tasks_outbound_enabled:
        logger.info("Backfill Jira пропущен: jira_tasks_sync_enabled выключен")
        return {"skipped": 1, "ok": 0, "failed": 0}

    ok = 0
    failed = 0
    # Top-level first
    stmt_top = (
        select(PortalTask.id)
        .where(PortalTask.jira_issue_key.is_(None), PortalTask.parent_task_id.is_(None))
        .order_by(PortalTask.created_at.asc())
    )
    if limit is not None:
        stmt_top = stmt_top.limit(limit)
    top_ids = list((await session.execute(stmt_top)).scalars().all())
    for tid in top_ids:
        try:
            await push_task_to_jira(session, http, tid, settings=s)
            task = await session.get(PortalTask, tid)
            if task and task.jira_issue_key and not task.jira_sync_error:
                ok += 1
            else:
                failed += 1
        except Exception:
            logger.exception("Backfill top-level failed id=%s", tid)
            failed += 1
        await asyncio.sleep(0.15)

    stmt_sub = (
        select(PortalTask.id)
        .where(PortalTask.jira_issue_key.is_(None), PortalTask.parent_task_id.is_not(None))
        .order_by(PortalTask.created_at.asc())
    )
    if limit is not None:
        stmt_sub = stmt_sub.limit(max(0, limit - len(top_ids)))
    sub_ids = list((await session.execute(stmt_sub)).scalars().all())
    for tid in sub_ids:
        try:
            await push_task_to_jira(session, http, tid, settings=s)
            task = await session.get(PortalTask, tid)
            if task and task.jira_issue_key and not task.jira_sync_error:
                ok += 1
            else:
                failed += 1
        except Exception:
            logger.exception("Backfill subtask failed id=%s", tid)
            failed += 1
        await asyncio.sleep(0.15)

    return {"ok": ok, "failed": failed, "skipped": 0}


async def run_backfill_once(settings: Settings, *, limit: int | None = None) -> dict[str, int]:
    timeout = settings.http_client_timeout_seconds
    async with httpx.AsyncClient(timeout=timeout) as http:
        async with async_session_factory() as session:
            return await backfill_tasks_to_jira(session, http, limit=limit, settings=settings)
