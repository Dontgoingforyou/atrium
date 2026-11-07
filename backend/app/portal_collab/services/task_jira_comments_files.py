"""Outbound комментариев и вложений задачи → Jira."""

from __future__ import annotations

import logging
import uuid

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.infrastructure.db.models.portal_task import PortalTask, PortalTaskComment, PortalTaskFile
from app.infrastructure.storage.client import async_download_object_bytes
from app.integrations.jira.write_client import JiraWriteClient

logger = logging.getLogger(__name__)


async def push_comment_to_jira(
    session: AsyncSession,
    http: httpx.AsyncClient,
    comment_id: uuid.UUID,
) -> None:
    settings = get_settings()
    if not settings.jira_tasks_outbound_enabled:
        return
    comment = await session.get(PortalTaskComment, comment_id)
    if comment is None or comment.jira_comment_id:
        return
    task = await session.get(PortalTask, comment.task_id)
    if task is None or not task.jira_issue_key:
        return
    client = JiraWriteClient(settings, http)
    try:
        created = await client.add_comment(task.jira_issue_key, comment.body)
        comment.jira_comment_id = str(created.get("id") or "")
        await session.commit()
    except Exception:
        logger.exception("Outbound Jira comment failed comment_id=%s", comment_id)
        await session.rollback()


async def push_file_to_jira(
    session: AsyncSession,
    http: httpx.AsyncClient,
    file_id: uuid.UUID,
) -> None:
    settings = get_settings()
    if not settings.jira_tasks_outbound_enabled:
        return
    tf = await session.get(PortalTaskFile, file_id)
    if tf is None or tf.jira_attachment_id:
        return
    task = await session.get(PortalTask, tf.task_id)
    if task is None or not task.jira_issue_key:
        return
    client = JiraWriteClient(settings, http)
    try:
        raw = await async_download_object_bytes(tf.storage_key)
        attachments = await client.add_attachment(
            task.jira_issue_key,
            filename=tf.original_filename,
            content=raw,
            content_type=tf.content_type,
        )
        if attachments:
            tf.jira_attachment_id = str(attachments[0].get("id") or "")
        await session.commit()
    except Exception:
        logger.exception("Outbound Jira attachment failed file_id=%s", file_id)
        await session.rollback()
