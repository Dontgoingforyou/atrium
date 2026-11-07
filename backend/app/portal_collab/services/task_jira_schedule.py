"""Планирование async outbound в Jira после commit."""

from __future__ import annotations

import asyncio
import logging
import uuid

import httpx

from app.core.config import get_settings
from app.infrastructure.db.session import async_session_factory

logger = logging.getLogger(__name__)


def schedule_task_jira_push(task_id: uuid.UUID) -> None:
    if not get_settings().jira_tasks_outbound_enabled:
        return
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return
    loop.create_task(_run_task_push(task_id))


def schedule_jira_issue_delete(issue_keys: list[str], *, parent_key: str | None = None) -> None:
    ordered = [key for key in issue_keys if key]
    if parent_key and parent_key not in ordered:
        ordered.append(parent_key)
    if not get_settings().jira_tasks_outbound_enabled or not ordered:
        return
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return
    loop.create_task(_run_issue_delete(ordered, parent_key=parent_key))


def schedule_comment_jira_push(comment_id: uuid.UUID) -> None:
    if not get_settings().jira_tasks_outbound_enabled:
        return
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return
    loop.create_task(_run_comment_push(comment_id))


def schedule_file_jira_push(file_id: uuid.UUID) -> None:
    if not get_settings().jira_tasks_outbound_enabled:
        return
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return
    loop.create_task(_run_file_push(file_id))


async def _run_task_push(task_id: uuid.UUID) -> None:
    from app.portal_collab.services.task_jira_outbound import push_task_to_jira

    settings = get_settings()
    try:
        async with httpx.AsyncClient(timeout=settings.http_client_timeout_seconds) as http:
            async with async_session_factory() as session:
                await push_task_to_jira(session, http, task_id, settings=settings)
    except Exception:
        logger.exception("Фоновый outbound задачи в Jira упал task_id=%s", task_id)


async def _run_issue_delete(issue_keys: list[str], *, parent_key: str | None) -> None:
    from app.portal_collab.services.task_jira_outbound import delete_jira_issues_for_deleted_task

    settings = get_settings()
    try:
        async with httpx.AsyncClient(timeout=settings.http_client_timeout_seconds) as http:
            await delete_jira_issues_for_deleted_task(
                http,
                issue_keys,
                parent_key=parent_key,
                settings=settings,
            )
    except Exception:
        logger.exception("Фоновое удаление Jira issue упало")


async def _run_comment_push(comment_id: uuid.UUID) -> None:
    from app.portal_collab.services.task_jira_comments_files import push_comment_to_jira

    settings = get_settings()
    try:
        async with httpx.AsyncClient(timeout=settings.http_client_timeout_seconds) as http:
            async with async_session_factory() as session:
                await push_comment_to_jira(session, http, comment_id)
    except Exception:
        logger.exception("Фоновый outbound комментария в Jira упал comment_id=%s", comment_id)


async def _run_file_push(file_id: uuid.UUID) -> None:
    from app.portal_collab.services.task_jira_comments_files import push_file_to_jira

    settings = get_settings()
    try:
        async with httpx.AsyncClient(timeout=settings.http_client_timeout_seconds) as http:
            async with async_session_factory() as session:
                await push_file_to_jira(session, http, file_id)
    except Exception:
        logger.exception("Фоновый outbound файла в Jira упал file_id=%s", file_id)
