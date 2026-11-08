"""Учебные документы, задачи, чат и доска специалистов для локального Docker.

Запись идемпотентна: стабильные id, повторный запуск ничего не дублирует.
В тестах не вызывается — только при DEBUG и без pytest.
"""

from __future__ import annotations

import uuid
from datetime import date, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_constants import SSO_GID_OUTSTAFF
from app.core.enums import FavoriteTargetType, TaskPriority, TaskStatus
from app.core.utils import now_utc
from app.infrastructure.db.models.portal_chat import PortalChat, PortalChatMember, PortalChatMessage
from app.infrastructure.db.models.portal_document import PortalDocument, PortalDocumentTag, PortalTag
from app.infrastructure.db.models.portal_favorite import PortalFavorite
from app.infrastructure.db.models.portal_manager_specialist import PortalManagerSpecialist
from app.infrastructure.db.models.portal_specialist_column import PortalSpecialistColumn
from app.infrastructure.db.models.portal_specialist_profile import PortalSpecialistProfile
from app.infrastructure.db.models.portal_specialist_status import PortalSpecialistStatus
from app.infrastructure.db.models.portal_task import PortalTask
from app.infrastructure.db.models.portal_task_assignee import PortalTaskAssignee
from app.infrastructure.db.models.portal_user_profile import PortalUserProfile
from app.infrastructure.db.session import async_session_factory

_NS = uuid.UUID("a3c1e8d0-5b24-4f6a-9e17-0c4d8b2a6f51")

SUB_ADMIN = "demo:admin"
SUB_MANAGER = "demo:manager"
SUB_USER = "demo:user"
SUB_PETR = "demo:petr"
SUB_OLGA = "demo:olga"


def _sid(name: str) -> uuid.UUID:
    return uuid.uuid5(_NS, name)


async def _missing(session: AsyncSession, model: type[Any], pk: Any) -> bool:
    return await session.get(model, pk) is None


async def seed_demo_content(session: AsyncSession) -> None:
    """Дописать учебные строки, если их ещё нет."""
    await _profiles(session)
    await _documents(session)
    await _tasks(session)
    await _chat(session)
    await _board(session)


async def seed_demo_portal() -> None:
    """Открыть сессию и записать учебные данные."""
    async with async_session_factory() as session:
        await seed_demo_content(session)
        await session.commit()


async def _profiles(session: AsyncSession) -> None:
    specs: tuple[dict[str, Any], ...] = (
        {
            "sub": SUB_ADMIN,
            "email": "demo-admin@example.com",
            "full_name": "Анна Иванова",
            "username": "admin",
            "is_portal_admin": True,
            "portal_chat_allowed": True,
        },
        {
            "sub": SUB_MANAGER,
            "email": "demo-manager@example.com",
            "full_name": "Иван Петров",
            "username": "manager",
            "gid_number": SSO_GID_OUTSTAFF,
            "portal_chat_allowed": True,
        },
        {
            "sub": SUB_USER,
            "email": "demo-user@example.com",
            "full_name": "Мария Соколова",
            "username": "user",
            "portal_chat_allowed": True,
        },
        {
            "sub": SUB_PETR,
            "email": "demo-petr@example.com",
            "full_name": "Пётр Орлов",
            "username": "petr",
            "portal_chat_allowed": False,
        },
        {
            "sub": SUB_OLGA,
            "email": "demo-olga@example.com",
            "full_name": "Ольга Демина",
            "username": "olga",
            "portal_chat_allowed": False,
        },
    )
    for spec in specs:
        row = await session.get(PortalUserProfile, spec["sub"])
        if row is None:
            session.add(PortalUserProfile(guided_tour_completed=True, **spec))
            continue
        row.guided_tour_completed = True
    await session.flush()


async def _documents(session: AsyncSession) -> None:
    tag_rules = _sid("tag-rules")
    tag_onboarding = _sid("tag-onboarding")
    if await _missing(session, PortalTag, tag_rules):
        session.add(PortalTag(id=tag_rules, name="Регламенты", slug="reglamenty", color="#0f766e"))
    if await _missing(session, PortalTag, tag_onboarding):
        session.add(PortalTag(id=tag_onboarding, name="Онбординг", slug="onbording", color="#115e59"))

    guide = _sid("doc-guide")
    vacation = _sid("doc-vacation")
    note = _sid("doc-note")
    docs = (
        (
            guide,
            "Как устроен Атриум",
            "Коротко: документы, задачи, чат и доска специалистов живут в одном портале. "
            "Эта страница — учебный пример, её можно править.",
        ),
        (
            vacation,
            "Регламент отпусков",
            "Заявку на отпуск пишут заранее, задачу ставит руководитель, статус меняют на доске задач.",
        ),
        (
            note,
            "Заметка по порталу",
            "Три входа на форме: admin, manager и user. Пароли рядом с логинами. "
            "Пётр Орлов и Ольга Демина есть только на доске специалистов.",
        ),
    )
    for doc_id, title, body in docs:
        existing_doc = await session.get(PortalDocument, doc_id)
        if existing_doc is None:
            session.add(
                PortalDocument(
                    id=doc_id,
                    title=title,
                    body=body,
                    author_sub=SUB_ADMIN,
                    author_display_name="Анна Иванова",
                    owner_sub=SUB_ADMIN,
                    icon_emoji="📄",
                )
            )
        elif existing_doc.title == "Заметка со стенда":
            existing_doc.title = title
            existing_doc.body = body
    await session.flush()
    if await _missing(session, PortalDocumentTag, (guide, tag_onboarding)):
        session.add(PortalDocumentTag(document_id=guide, tag_id=tag_onboarding))
    if await _missing(session, PortalDocumentTag, (vacation, tag_rules)):
        session.add(PortalDocumentTag(document_id=vacation, tag_id=tag_rules))

    favorite_id = _sid("fav-guide")
    if await _missing(session, PortalFavorite, favorite_id):
        session.add(
            PortalFavorite(
                id=favorite_id,
                user_sub=SUB_ADMIN,
                target_type=FavoriteTargetType.DOCUMENT,
                target_id=guide,
            )
        )


async def _tasks(session: AsyncSession) -> None:
    now = now_utc()
    rows = (
        (
            "task-onboarding",
            "Подготовить онбординг",
            "Собрать первую неделю для нового человека: документы, доступы, знакомство в чате.",
            SUB_ADMIN,
            TaskStatus.TODO,
            TaskPriority.HIGH,
            now + timedelta(days=3),
        ),
        (
            "task-access",
            "Проверить доступы",
            "Срок уже прошёл: учебный пример просроченной задачи на главной.",
            SUB_ADMIN,
            TaskStatus.IN_PROGRESS,
            TaskPriority.MEDIUM,
            now - timedelta(days=1),
        ),
        (
            "task-regulation",
            "Обновить регламент",
            "Сверить текст отпуска с заметкой в документах.",
            SUB_MANAGER,
            TaskStatus.TODO,
            TaskPriority.LOW,
            now + timedelta(days=7),
        ),
        (
            "task-intro",
            "Закрыть вводную встречу",
            "Встреча прошла, задача для примера статуса «готово».",
            SUB_USER,
            TaskStatus.DONE,
            TaskPriority.MEDIUM,
            now - timedelta(days=2),
        ),
    )
    for key, title, description, assignee, status, priority, due_at in rows:
        task_id = _sid(key)
        existing_task = await session.get(PortalTask, task_id)
        if existing_task is not None:
            if existing_task.description and "стенд" in existing_task.description:
                existing_task.description = description
            continue
        session.add(
            PortalTask(
                id=task_id,
                title=title,
                description=description,
                creator_sub=SUB_ADMIN,
                assignee_sub=assignee,
                status=status,
                priority=priority,
                due_at=due_at,
            )
        )
        await session.flush()
        session.add(
            PortalTaskAssignee(
                id=_sid(f"{key}-assignee"),
                task_id=task_id,
                assignee_sub=assignee,
            )
        )


async def _chat(session: AsyncSession) -> None:
    chat_id = _sid("chat-common")
    if await _missing(session, PortalChat, chat_id):
        session.add(PortalChat(id=chat_id, title="Общий", created_by_sub=SUB_ADMIN))
        await session.flush()
    for sub in (SUB_ADMIN, SUB_MANAGER, SUB_USER):
        if await _missing(session, PortalChatMember, (chat_id, sub)):
            session.add(PortalChatMember(chat_id=chat_id, user_sub=sub))
    messages = (
        ("msg-1", SUB_ADMIN, "Добро пожаловать в учебный чат. Здесь можно писать, как в обычном."),
        ("msg-2", SUB_MANAGER, "Задачи уже на доске: онбординг, доступы и регламент."),
        ("msg-3", SUB_USER, "Регламент отпусков лежит в документах, я его открыла."),
    )
    for key, author, body in messages:
        message_id = _sid(key)
        if await _missing(session, PortalChatMessage, message_id):
            session.add(PortalChatMessage(id=message_id, chat_id=chat_id, author_sub=author, body=body))


async def _board(session: AsyncSession) -> None:
    # Колонки воронки уже есть из миграции (key уникален). Свои добавляем только в пустую таблицу.
    existing = list(await session.scalars(select(PortalSpecialistColumn).order_by(PortalSpecialistColumn.position)))
    if not existing:
        for key, title, color, position in (
            ("new", "Новые", "#0f766e", 0),
            ("interview", "Собеседование", "#115e59", 1),
            ("offer", "Оффер", "#14b8a6", 2),
        ):
            session.add(
                PortalSpecialistColumn(id=_sid(f"col-{key}"), key=key, title=title, color=color, position=position)
            )
        column_keys = ["new", "interview"]
    else:
        column_keys = [row.key for row in existing]

    status = await session.scalar(select(PortalSpecialistStatus).where(PortalSpecialistStatus.title == "В работе"))
    if status is None:
        status_id = _sid("status-active")
        session.add(PortalSpecialistStatus(id=status_id, title="В работе", color="#0f766e"))
        await session.flush()
    else:
        status_id = status.id

    profiles = (
        (SUB_PETR, date(1996, 3, 14), "Казань", "petr_demo", "Бэкенд"),
        (SUB_OLGA, date(1999, 11, 2), "Новосибирск", "olga_demo", "Дизайн"),
    )
    for sub, birthdate, location, telegram, direction in profiles:
        if await _missing(session, PortalSpecialistProfile, sub):
            session.add(
                PortalSpecialistProfile(
                    specialist_sub=sub,
                    birthdate=birthdate,
                    location=location,
                    telegram=telegram,
                    direction=direction,
                    jira_fields={},
                )
            )
    await session.flush()
    first_key = column_keys[0]
    second_key = column_keys[1] if len(column_keys) > 1 else first_key
    # И у администратора, и у менеджера своя доска: вход с формы открывает «мою».
    cards = (
        ("card-olga-admin", SUB_ADMIN, SUB_OLGA, first_key, 0),
        ("card-petr-admin", SUB_ADMIN, SUB_PETR, second_key, 0),
        ("card-olga", SUB_MANAGER, SUB_OLGA, first_key, 0),
        ("card-petr", SUB_MANAGER, SUB_PETR, second_key, 0),
    )
    for key, manager_sub, specialist_sub, column_key, position in cards:
        card_id = _sid(key)
        if await _missing(session, PortalManagerSpecialist, card_id):
            session.add(
                PortalManagerSpecialist(
                    id=card_id,
                    manager_sub=manager_sub,
                    specialist_sub=specialist_sub,
                    column_key=column_key,
                    position=position,
                    status_id=status_id,
                )
            )
