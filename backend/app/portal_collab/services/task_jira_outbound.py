"""Outbound push portal_task → Jira AUTASKS (только при jira_tasks_sync_enabled)."""

from __future__ import annotations

import logging
import re
import uuid
from html import unescape
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.exceptions import AppError
from app.core.utils import now_utc
from app.infrastructure.db.models.portal_task import PortalTask, PortalTaskColumn
from app.infrastructure.db.models.portal_task_assignee import PortalTaskAssignee
from app.infrastructure.db.models.portal_user_profile import PortalUserProfile
from app.integrations.jira.write_client import JiraWriteClient

logger = logging.getLogger(__name__)

_TAG_RE = re.compile(r"<[^>]+>")


def _plain_description(html: str | None) -> str:
    if not html:
        return ""
    text = _TAG_RE.sub(" ", html)
    return unescape(re.sub(r"\s+", " ", text)).strip()[:30000]


def _priority_name(priority: str) -> str:
    mapping = {"low": "Low", "medium": "Medium", "high": "High"}
    return mapping.get(priority, "Medium")


async def _assignee_emails(session: AsyncSession, task_id: uuid.UUID) -> list[str]:
    """Все email исполнителей; первый — primary assignee, остальные → watchers."""
    stmt = (
        select(PortalTaskAssignee.assignee_sub)
        .where(PortalTaskAssignee.task_id == task_id)
        .order_by(PortalTaskAssignee.assignee_sub)
    )
    subs = list((await session.execute(stmt)).scalars().all())
    if not subs:
        return []
    profiles = (await session.execute(select(PortalUserProfile).where(PortalUserProfile.sub.in_(subs)))).scalars().all()
    by_sub = {p.sub: p for p in profiles}
    emails: list[str] = []
    for sub in subs:
        profile = by_sub.get(sub)
        if profile and profile.email:
            emails.append(profile.email)
    return emails


async def push_task_to_jira(
    session: AsyncSession,
    http: httpx.AsyncClient,
    task_id: uuid.UUID,
    *,
    settings: Settings | None = None,
) -> None:
    """Создаёт или обновляет issue в AUTASKS; пишет ключ/ошибку в portal_task."""
    s = settings or get_settings()
    if not s.jira_tasks_outbound_enabled:
        return

    stmt = select(PortalTask).where(PortalTask.id == task_id)
    if session.get_bind().dialect.name == "postgresql":
        stmt = stmt.with_for_update()
    task = (await session.execute(stmt)).scalar_one_or_none()
    if task is None:
        return

    client = JiraWriteClient(s, http)
    try:
        fields: dict[str, Any] = {
            "project": {"key": s.jira_tasks_project_key},
            "summary": task.title[:255],
            "description": _build_description(task, s),
            "issuetype": {"name": s.jira_tasks_issue_type},
            "priority": {"name": _priority_name(str(task.priority))},
        }
        # duedate на экране создания AUTASKS нет — срок только в description.

        emails = await _assignee_emails(session, task.id)
        watcher_names: list[str] = []
        if emails:
            primary = await client.find_user_by_email(emails[0])
            if primary and primary.get("name"):
                fields["assignee"] = {"name": primary["name"]}
            for extra_email in emails[1:]:
                u = await client.find_user_by_email(extra_email)
                name = u.get("name") if u else None
                if name:
                    watcher_names.append(str(name))

        if task.parent_task_id:
            parent = await session.get(PortalTask, task.parent_task_id)
            if parent and parent.jira_issue_key:
                fields["parent"] = {"key": parent.jira_issue_key}
                # Server often uses issuetype Sub-task
                fields["issuetype"] = {"name": "Подзадача"}

        if task.jira_issue_key:
            update_fields = {k: v for k, v in fields.items() if k not in ("project", "issuetype", "parent")}
            await client.update_issue(task.jira_issue_key, update_fields)
            await _apply_status_transition(session, client, task)
            for wname in watcher_names:
                await client.add_watcher(task.jira_issue_key, wname)
            task.jira_synced_at = now_utc()
            task.jira_sync_error = None
        else:
            created = await client.create_issue(fields)
            task.jira_issue_key = str(created.get("key") or "")
            task.jira_issue_id = str(created.get("id") or "") or None
            await _apply_status_transition(session, client, task)
            if task.jira_issue_key:
                for wname in watcher_names:
                    await client.add_watcher(task.jira_issue_key, wname)
            task.jira_synced_at = now_utc()
            task.jira_sync_error = None
        await session.commit()
    except Exception as exc:
        logger.exception("Outbound Jira sync failed task_id=%s", task_id)
        await session.rollback()
        task = await session.get(PortalTask, task_id)
        if task is not None:
            if isinstance(exc, AppError):
                task.jira_sync_error = exc.message[:2000]
            else:
                task.jira_sync_error = "Jira недоступна"
            await session.commit()


async def delete_jira_issues_for_deleted_task(
    http: httpx.AsyncClient,
    issue_keys: list[str],
    *,
    parent_key: str | None,
    settings: Settings | None = None,
) -> None:
    """Удалить зеркала в Jira. Отказ не переводится в Done: карточка остаётся как есть."""
    s = settings or get_settings()
    if not s.jira_tasks_outbound_enabled:
        return
    client = JiraWriteClient(s, http)
    for issue_key in issue_keys:
        if not issue_key:
            continue
        try:
            await client.delete_issue(issue_key, delete_subtasks=issue_key == parent_key)
        except AppError as exc:
            logger.warning("Jira не удалила issue_key=%s: %s", issue_key, exc.message)
        except Exception:
            logger.exception("Не удалось удалить Jira issue_key=%s", issue_key)


def _build_description(task: PortalTask, settings: Settings) -> str:
    base = settings.portal_public_url.rstrip("/")
    link = f"{base}/tasks?task={task.id}"
    parts = [
        _plain_description(task.description),
        "",
    ]
    if task.due_at is not None:
        parts.append(f"Срок (Cosmolet): {task.due_at.date().isoformat()}")
    parts.extend(
        [
            f"Открыть в Космолете: {link}",
            f"Cosmolet task #{task.number or task.id}",
        ]
    )
    return "\n".join(p for p in parts if p is not None).strip()


async def _apply_status_transition(
    session: AsyncSession,
    client: JiraWriteClient,
    task: PortalTask,
) -> None:
    if not task.jira_issue_key:
        return
    col = (
        await session.execute(select(PortalTaskColumn).where(PortalTaskColumn.status_key == task.status).limit(1))
    ).scalar_one_or_none()
    if col is None or not col.jira_status_id:
        return
    transitions = await client.get_transitions(task.jira_issue_key)
    for tr in transitions:
        to_status = (tr.get("to") or {}).get("id")
        if str(to_status) == str(col.jira_status_id):
            await client.transition_issue(task.jira_issue_key, str(tr["id"]))
            return
