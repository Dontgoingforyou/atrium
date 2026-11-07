"""Выгрузка списка задач колонки канбана в TXT.

Исключение из правила «сервис возвращает ORM»: специализированный read-сценарий,
возвращает (bytes, filename, content_type) — как portal_time_entries._export.

Выборка без PagedResponse обоснована: column-export с жёстким LIMIT
(api-pagination.mdc / fastapi-backend.mdc).
"""

from __future__ import annotations

import html
import re
import uuid
from collections import defaultdict
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.admin.enum_labels import TASK_PRIORITY_LABELS_RU
from app.core.exceptions import NotFoundError
from app.core.utils import now_utc
from app.infrastructure.db.models.portal_task import (
    PortalTask,
    PortalTaskColumn,
    PortalTaskComment,
    PortalTaskLink,
)
from app.infrastructure.db.models.portal_user_profile import PortalUserProfile
from app.portal_collab.services._task_queries import list_tasks_by_exact_status, visible_task_ids_subquery
from app.schemas.auth import UserPublic

# Жёсткий cap column-export: не отдаём неограниченный dump всей таблицы.
_EXPORT_TASK_LIMIT = 2000
_EXPORT_COMMENTS_PER_TASK = 200
_CONTENT_TYPE = "text/plain; charset=utf-8"
_EMPTY_PLACEHOLDER = "—"
_BLOCK_SEPARATOR = "----------"
_HTML_BLOCK_BREAK_RE = re.compile(
    r"<br\s*/?>|</p>|</div>|</li>|</h[1-6]>|</tr>",
    re.IGNORECASE,
)
_HTML_TAG_RE = re.compile(r"<[^>]+>", re.DOTALL)


def _safe_filename_part(value: str) -> str:
    cleaned = re.sub(r"[^\w\-.]+", "_", value.strip(), flags=re.UNICODE)
    return cleaned.strip("_") or "column"


def _assignee_subs_from_task(task: PortalTask) -> list[str]:
    if task.task_assignees:
        return [a.assignee_sub for a in task.task_assignees]
    if task.assignee_sub:
        return [task.assignee_sub]
    return []


def _format_due_at(task: PortalTask) -> str:
    if task.due_at is None:
        return _EMPTY_PLACEHOLDER
    return task.due_at.date().isoformat()


def _format_priority(priority: str | None) -> str:
    if not priority:
        return _EMPTY_PLACEHOLDER
    return TASK_PRIORITY_LABELS_RU.get(priority, priority)


def _format_number(number: int | None) -> str:
    if number is None:
        return f"#{_EMPTY_PLACEHOLDER}"
    return f"#{number}"


def _display_name(sub: str | None, names_by_sub: dict[str, str]) -> str:
    if not sub:
        return _EMPTY_PLACEHOLDER
    return names_by_sub.get(sub, sub)


def _assignee_labels(subs: list[str], names_by_sub: dict[str, str]) -> str:
    if not subs:
        return _EMPTY_PLACEHOLDER
    return ", ".join(_display_name(sub, names_by_sub) for sub in subs)


def _html_to_plain_multiline(raw: str | None) -> str:
    """HTML редактора → читаемый plain text с переносами абзацев."""
    if not raw:
        return ""
    text = html.unescape(raw)
    text = _HTML_BLOCK_BREAK_RE.sub("\n", text)
    text = _HTML_TAG_RE.sub("", text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    collapsed: list[str] = []
    blank_streak = 0
    for line in text.split("\n"):
        stripped = line.strip()
        if stripped:
            blank_streak = 0
            collapsed.append(stripped)
        else:
            blank_streak += 1
            if blank_streak == 1 and collapsed:
                collapsed.append("")
    return "\n".join(collapsed).strip()


def _indent_block(text: str, prefix: str = "  ") -> list[str]:
    if not text:
        return [f"{prefix}{_EMPTY_PLACEHOLDER}"]
    return [f"{prefix}{line}" if line else "" for line in text.split("\n")]


def _format_comment_timestamp(value: datetime) -> str:
    # Экспорт всегда в UTC; naive из БД трактуем как UTC.
    aware = value if value.tzinfo is not None else value.replace(tzinfo=UTC)
    stamp = aware.astimezone(UTC).strftime("%Y-%m-%d %H:%M")
    return f"[{stamp} UTC]"


def _format_comments_section(
    comments: list[PortalTaskComment],
    names_by_sub: dict[str, str],
) -> list[str]:
    if not comments:
        return [f"Комментарии: {_EMPTY_PLACEHOLDER}"]
    lines = ["Комментарии:"]
    for comment in comments[:_EXPORT_COMMENTS_PER_TASK]:
        author = _display_name(comment.author_sub, names_by_sub)
        stamp = _format_comment_timestamp(comment.created_at)
        lines.append(f"  {stamp} {author}:")
        lines.extend(_indent_block(_html_to_plain_multiline(comment.body), "    "))
        for reply in comment.replies or []:
            reply_author = _display_name(reply.author_sub, names_by_sub)
            reply_stamp = _format_comment_timestamp(reply.created_at)
            lines.append(f"    [ответ] {reply_stamp} {reply_author}:")
            lines.extend(_indent_block(_html_to_plain_multiline(reply.body), "      "))
    return lines


def _format_links_section(links: list[PortalTaskLink]) -> list[str]:
    if not links:
        return [f"Ссылки: {_EMPTY_PLACEHOLDER}"]
    lines = ["Ссылки:"]
    for link in links:
        title = (link.title or "").strip() or _EMPTY_PLACEHOLDER
        lines.append(f"  - {title}: {link.url}")
    return lines


def _format_parent_section(parent: PortalTask | None) -> list[str]:
    if parent is None:
        return []
    title = (parent.title or "").replace("\n", " ").strip() or _EMPTY_PLACEHOLDER
    lines = [f"Родительская задача: {_format_number(parent.number)} {title}", "Описание родителя:"]
    lines.extend(_indent_block(_html_to_plain_multiline(parent.description)))
    return lines


def _format_task_block(
    task: PortalTask,
    *,
    names_by_sub: dict[str, str],
    parent: PortalTask | None,
    links: list[PortalTaskLink],
    comments: list[PortalTaskComment],
) -> list[str]:
    title = (task.title or "").replace("\n", " ").strip() or _EMPTY_PLACEHOLDER
    tags = ", ".join(t.name for t in (task.tags or []) if t.name) or _EMPTY_PLACEHOLDER
    lines = [
        f"{_format_number(task.number)} {title}",
        f"Приоритет: {_format_priority(task.priority)}",
        f"Срок: {_format_due_at(task)}",
        f"Исполнители: {_assignee_labels(_assignee_subs_from_task(task), names_by_sub)}",
        f"Создатель: {_display_name(task.creator_sub, names_by_sub)}",
        f"Теги: {tags}",
    ]
    if task.jira_issue_key:
        lines.append(f"Jira: {task.jira_issue_key}")
    lines.extend(_format_links_section(links))
    parent_lines = _format_parent_section(parent)
    if parent_lines:
        lines.append("")
        lines.extend(parent_lines)
    lines.append("")
    lines.append("Описание:")
    lines.extend(_indent_block(_html_to_plain_multiline(task.description)))
    lines.append("")
    lines.extend(_format_comments_section(comments, names_by_sub))
    return lines


def _build_txt(
    column_title: str,
    tasks: list[PortalTask],
    *,
    names_by_sub: dict[str, str],
    parents_by_id: dict[uuid.UUID, PortalTask],
    links_by_task_id: dict[uuid.UUID, list[PortalTaskLink]],
    comments_by_task_id: dict[uuid.UUID, list[PortalTaskComment]],
) -> bytes:
    lines = [f"Колонка: {column_title}", ""]
    for index, task in enumerate(tasks):
        if index > 0:
            lines.append(_BLOCK_SEPARATOR)
            lines.append("")
        parent = parents_by_id.get(task.parent_task_id) if task.parent_task_id else None
        lines.extend(
            _format_task_block(
                task,
                names_by_sub=names_by_sub,
                parent=parent,
                links=links_by_task_id.get(task.id, []),
                comments=comments_by_task_id.get(task.id, []),
            ),
        )
        lines.append("")
    body = "\n".join(lines).rstrip() + ("\n" if tasks or column_title else "")
    # UTF-8 BOM — совместимость с Windows Notepad / Excel.
    return b"\xef\xbb\xbf" + body.encode("utf-8")


async def _load_display_names(session: AsyncSession, subs: set[str]) -> dict[str, str]:
    if not subs:
        return {}
    rows = (
        await session.execute(
            select(PortalUserProfile.sub, PortalUserProfile.full_name).where(PortalUserProfile.sub.in_(subs)),
        )
    ).all()
    out: dict[str, str] = {}
    for sub, full_name in rows:
        label = (full_name or "").strip()
        if label:
            out[str(sub)] = label
    return out


async def _load_parents_by_id(
    session: AsyncSession,
    user: UserPublic,
    parent_ids: set[uuid.UUID],
) -> dict[uuid.UUID, PortalTask]:
    """Родитель в TXT только если пользователь проходит ту же видимость, что ``get_task``."""
    if not parent_ids:
        return {}
    rows = (
        (
            await session.execute(
                select(PortalTask).where(
                    PortalTask.id.in_(parent_ids),
                    PortalTask.id.in_(visible_task_ids_subquery(user)),
                ),
            )
        )
        .scalars()
        .all()
    )
    return {row.id: row for row in rows}


async def _load_links_by_task_id(
    session: AsyncSession,
    task_ids: list[uuid.UUID],
) -> dict[uuid.UUID, list[PortalTaskLink]]:
    if not task_ids:
        return {}
    rows = (
        (
            await session.execute(
                select(PortalTaskLink)
                .where(PortalTaskLink.task_id.in_(task_ids))
                .order_by(PortalTaskLink.created_at.asc()),
            )
        )
        .scalars()
        .all()
    )
    out: dict[uuid.UUID, list[PortalTaskLink]] = defaultdict(list)
    for link in rows:
        out[link.task_id].append(link)
    return out


async def _load_comments_by_task_id(
    session: AsyncSession,
    task_ids: list[uuid.UUID],
) -> dict[uuid.UUID, list[PortalTaskComment]]:
    if not task_ids:
        return {}
    rows = (
        (
            await session.execute(
                select(PortalTaskComment)
                .where(
                    PortalTaskComment.task_id.in_(task_ids),
                    PortalTaskComment.parent_id.is_(None),
                )
                .options(selectinload(PortalTaskComment.replies))
                .order_by(PortalTaskComment.created_at.asc()),
            )
        )
        .scalars()
        .all()
    )
    out: dict[uuid.UUID, list[PortalTaskComment]] = defaultdict(list)
    for comment in rows:
        bucket = out[comment.task_id]
        if len(bucket) < _EXPORT_COMMENTS_PER_TASK:
            bucket.append(comment)
    return out


def _collect_name_subs(
    tasks: list[PortalTask],
    comments_by_task_id: dict[uuid.UUID, list[PortalTaskComment]],
) -> set[str]:
    all_subs: set[str] = set()
    for task in tasks:
        all_subs.update(_assignee_subs_from_task(task))
        if task.creator_sub:
            all_subs.add(task.creator_sub)
        for comment in comments_by_task_id.get(task.id, []):
            if comment.author_sub:
                all_subs.add(comment.author_sub)
            for reply in comment.replies or []:
                if reply.author_sub:
                    all_subs.add(reply.author_sub)
    return all_subs


async def export_column_tasks_txt(
    session: AsyncSession,
    user: UserPublic,
    column_id: uuid.UUID,
    *,
    mine_only: bool = False,
    assignee_sub: list[str] | None = None,
) -> tuple[bytes, str, str]:
    """Выгрузить видимые пользователю задачи колонки в подробный TXT.

    RBAC: та же политика видимости и фильтра ``assignee_sub``, что у ``list_tasks``.
    Управление колонками не требуется.
    """
    column = await session.get(PortalTaskColumn, column_id)
    if column is None:
        raise NotFoundError("Колонка не найдена")

    tasks = await list_tasks_by_exact_status(
        session,
        user,
        [column.status_key],
        mine_only=mine_only,
        assignee_sub=assignee_sub,
        skip=0,
        limit=_EXPORT_TASK_LIMIT,
    )

    task_ids = [task.id for task in tasks]
    parent_ids = {task.parent_task_id for task in tasks if task.parent_task_id is not None}

    parents_by_id = await _load_parents_by_id(session, user, parent_ids)
    links_by_task_id = await _load_links_by_task_id(session, task_ids)
    comments_by_task_id = await _load_comments_by_task_id(session, task_ids)
    names_by_sub = await _load_display_names(session, _collect_name_subs(tasks, comments_by_task_id))

    file_bytes = _build_txt(
        column.title,
        tasks,
        names_by_sub=names_by_sub,
        parents_by_id=parents_by_id,
        links_by_task_id=links_by_task_id,
        comments_by_task_id=comments_by_task_id,
    )
    day = now_utc().date().isoformat().replace("-", "")
    safe_key = _safe_filename_part(column.status_key)
    filename = f"tasks_{safe_key}_{day}.txt"
    return file_bytes, filename, _CONTENT_TYPE
