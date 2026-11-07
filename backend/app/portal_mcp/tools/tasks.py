"""Задачи и колонки канбана."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from app.portal_mcp.auth import clamp_limit, dump_dict, dump_list, mcp_call
from app.portal_mcp.constants import LIST_LIMIT_DEFAULT
from app.portal_mcp.tools._values import parse_datetime, parse_uuid, parse_uuids

_TASK_DESCRIPTION_REQUIRED = (
    "Заполните описание задачи по шаблону: Проблема, Результат, Критерий «готово», Что сделать, Связанные материалы."
)

_TASK_CREATE_TEMPLATE = """Шаблон задачи в Космолёте. Заполните поля, после этого карточку можно создавать.

Название — обязательно. Короткая формулировка действия, без префиксов вроде «Срочно» или «Задача».

Описание — обязательно. Пять блоков, только смысл работы.
Исполнителя, колонку, приоритет, срок и теги в текст не дублировать.

Проблема
[Что сейчас не так / что нужно сделать. Факты, границы, кто затронут.]

Результат
[Какое проверяемое состояние будет после выполнения.]

Критерий «готово»
• [Условие приёмки 1]
• [Условие приёмки 2]

Что сделать
1. [Где / канал / система] — [действие] — [как проверить]
2. …

Связанные материалы
• [Ссылка или источник, который реально нужен]
• [Если внешних материалов нет — «диалог-постановка» / дейлик / чат]

Исполнители — обязательно хотя бы одно имя. «Я» — текущий пользователь (whoami).
Чужое имя найдите в portal_users_list и при нескольких совпадениях переспросите. sub не выдумывать.

Колонка — по умолчанию «Бэклог»: ключ статуса из task_columns_list. Если такой колонки нет, статус не передавать.
Приоритет, срок, теги, родительская задача и документ — только если их указали. Теги брать из tags_list.

После создания: ссылки — tasks_links_add, файлы — tasks_files_add, только если их заполнили.
"""


def register(mcp: FastMCP) -> None:
    @mcp.tool(description="Список задач портала. Менеджер и админ видят полный список.")
    async def tasks_list(
        limit: int = LIST_LIMIT_DEFAULT,
        skip: int = 0,
        mine_only: bool = False,
        assignee_sub: list[str] | None = None,
        status: list[str] | None = None,
        overdue_only: bool = False,
        no_assignee: bool = False,
    ) -> list[dict[str, object]]:
        from app.portal_collab.services._task_reads import tasks_to_reads
        from app.portal_collab.services.task import list_tasks

        async with mcp_call("tasks_list") as call:
            rows = await list_tasks(
                call.session,
                call.user,
                mine_only=mine_only,
                assignee_sub=assignee_sub,
                status=status,
                overdue_only=overdue_only,
                no_assignee=no_assignee,
                skip=skip,
                limit=clamp_limit(limit),
            )
            return dump_list(await tasks_to_reads(call.session, rows))

    @mcp.tool(
        description=(
            "Карточка задачи по идентификатору. В ответе всегда есть списки links и files, в том числе пустые."
        ),
    )
    async def tasks_get(task_id: str) -> dict[str, object]:
        from app.portal_collab.schemas.task import TaskFileRead, TaskLinkRead
        from app.portal_collab.services import task_file as file_svc
        from app.portal_collab.services import task_link as link_svc
        from app.portal_collab.services._task_reads import single_task_to_read
        from app.portal_collab.services.task import get_task

        async with mcp_call("tasks_get") as call:
            parsed_id = parse_uuid(task_id)
            task = await get_task(call.session, call.user, parsed_id)
            card = dump_dict(await single_task_to_read(call.session, task))
            link_rows = await link_svc.list_links(call.session, call.user, parsed_id)
            file_rows = await file_svc.list_files(call.session, call.user, parsed_id)
            card["links"] = dump_list([TaskLinkRead.model_validate(row) for row in link_rows])
            card["files"] = dump_list(
                [
                    TaskFileRead(
                        id=row.id,
                        task_id=row.task_id,
                        original_filename=row.original_filename,
                        content_type=row.content_type,
                        file_size=row.file_size,
                        download_url=file_svc.build_download_url(row),
                        view_url=file_svc.build_view_url(row),
                        uploaded_by_sub=row.uploaded_by_sub,
                        created_at=row.created_at,
                    )
                    for row in file_rows
                ]
            )
            return card

    @mcp.tool(
        description=(
            "Шаблон создания задачи. Покажите текст человеку и заполните его до вызова tasks_create. "
            "Задачу не создаёт. Без названия, пяти блоков описания и хотя бы одного исполнителя "
            "tasks_create не вызывать."
        ),
    )
    async def tasks_template() -> dict[str, str]:
        async with mcp_call("tasks_template"):
            return {"template": _TASK_CREATE_TEMPLATE}

    @mcp.tool(
        description=(
            "Создать задачу. Сначала вызовите tasks_template и покажите текст человеку. "
            "Не вызывайте, пока нет названия, описания по этому шаблону и хотя бы одного assignee_subs. "
            "Колонка, приоритет, срок, теги, родитель и документ необязательны. "
            "Смена исполнителей чужой задачи остаётся в сервисе."
        ),
    )
    async def tasks_create(
        title: str,
        description: str,
        assignee_subs: list[str] | None = None,
        status: str | None = None,
        priority: str | None = None,
        due_at: str | None = None,
        parent_task_id: str | None = None,
        document_id: str | None = None,
        tag_ids: list[str] | None = None,
    ) -> dict[str, object]:
        from app.portal_collab.schemas.task import PortalTaskCreate
        from app.portal_collab.services._task_reads import single_task_to_read
        from app.portal_collab.services.task import create_task

        text = description.strip()
        if not text:
            from app.core.exceptions import ValidationError

            raise ValidationError(_TASK_DESCRIPTION_REQUIRED)
        payload: dict[str, object] = {"title": title, "description": text}
        if assignee_subs is not None:
            payload["assignee_subs"] = assignee_subs
        if status is not None:
            payload["status"] = status
        if priority is not None:
            payload["priority"] = priority
        if due_at is not None:
            payload["due_at"] = parse_datetime(due_at)
        if parent_task_id is not None:
            payload["parent_task_id"] = parse_uuid(parent_task_id)
        if document_id is not None:
            payload["document_id"] = parse_uuid(document_id)
        if tag_ids is not None:
            payload["tag_ids"] = parse_uuids(tag_ids)
        async with mcp_call("tasks_create") as call:
            task = await create_task(call.session, call.user, PortalTaskCreate.model_validate(payload))
            return dump_dict(await single_task_to_read(call.session, task))

    @mcp.tool(description="Изменить задачу. Нужна версия карточки. Права автора, исполнителя и админа — в сервисе.")
    async def tasks_update(
        task_id: str,
        expected_version: int,
        title: str | None = None,
        description: str | None = None,
        assignee_subs: list[str] | None = None,
        status: str | None = None,
        priority: str | None = None,
        due_at: str | None = None,
        tag_ids: list[str] | None = None,
    ) -> dict[str, object]:
        from app.portal_collab.schemas.task import PortalTaskUpdate
        from app.portal_collab.services._task_reads import single_task_to_read
        from app.portal_collab.services.task import update_task

        payload: dict[str, object] = {"expected_version": expected_version}
        if title is not None:
            payload["title"] = title
        if description is not None:
            payload["description"] = description
        if assignee_subs is not None:
            payload["assignee_subs"] = assignee_subs
        if status is not None:
            payload["status"] = status
        if priority is not None:
            payload["priority"] = priority
        if due_at is not None:
            payload["due_at"] = parse_datetime(due_at)
        if tag_ids is not None:
            payload["tag_ids"] = parse_uuids(tag_ids)
        async with mcp_call("tasks_update") as call:
            task = await update_task(
                call.session,
                call.user,
                parse_uuid(task_id),
                PortalTaskUpdate.model_validate(payload),
            )
            return dump_dict(await single_task_to_read(call.session, task))

    @mcp.tool(description="Перенести задачу в колонку. Позиция — соседняя задача after или before.")
    async def tasks_move(
        task_id: str,
        status: str,
        after_task_id: str | None = None,
        before_task_id: str | None = None,
    ) -> dict[str, object]:
        from app.portal_collab.services._task_reads import single_task_to_read
        from app.portal_collab.services.task import reorder_task

        async with mcp_call("tasks_move") as call:
            task = await reorder_task(
                call.session,
                call.user,
                parse_uuid(task_id),
                status,
                parse_uuid(after_task_id) if after_task_id else None,
                parse_uuid(before_task_id) if before_task_id else None,
            )
            return dump_dict(await single_task_to_read(call.session, task))

    @mcp.tool(description="Удалить задачу. Менеджер удаляет только свою, админ — любую.")
    async def tasks_delete(task_id: str) -> dict[str, bool]:
        from app.portal_collab.services.task import delete_task

        async with mcp_call("tasks_delete") as call:
            await delete_task(call.session, call.user, parse_uuid(task_id))
            return {"ok": True}

    @mcp.tool(description="Колонки канбана.")
    async def task_columns_list() -> list[dict[str, object]]:
        from app.portal_collab.schemas.task import PortalTaskColumnRead
        from app.portal_collab.services.task_column import list_task_columns

        async with mcp_call("task_columns_list") as call:
            rows = await list_task_columns(call.session, call.user)
            return dump_list([PortalTaskColumnRead.model_validate(row) for row in rows])

    @mcp.tool(description="Создать колонку канбана. Исключение из KPI принимает только админ, это решает сервис.")
    async def task_columns_create(
        title: str,
        status_key: str,
        color: str = "#6131cf",
        position: int = 0,
        exclude_from_kpi: bool = False,
    ) -> dict[str, object]:
        from app.portal_collab.schemas.task import PortalTaskColumnCreate, PortalTaskColumnRead
        from app.portal_collab.services.task_column import create_task_column

        data = PortalTaskColumnCreate(
            title=title,
            status_key=status_key,
            color=color,
            position=position,
            exclude_from_kpi=exclude_from_kpi,
        )
        async with mcp_call("task_columns_create") as call:
            column = await create_task_column(call.session, call.user, data, http=call.http)
            return dump_dict(PortalTaskColumnRead.model_validate(column))

    @mcp.tool(
        description="Переименовать колонку, сменить цвет или порядок. KPI и Jira — только админ, это решает сервис.",
    )
    async def task_columns_update(
        column_id: str,
        title: str | None = None,
        color: str | None = None,
        position: int | None = None,
        exclude_from_kpi: bool | None = None,
        jira_status_id: str | None = None,
    ) -> dict[str, object]:
        from app.portal_collab.schemas.task import PortalTaskColumnRead, PortalTaskColumnUpdate
        from app.portal_collab.services.task_column import update_task_column

        data = PortalTaskColumnUpdate(
            title=title,
            color=color,
            position=position,
            exclude_from_kpi=exclude_from_kpi,
            jira_status_id=jira_status_id,
        )
        async with mcp_call("task_columns_update") as call:
            column = await update_task_column(
                call.session,
                call.user,
                parse_uuid(column_id),
                data,
                http=call.http,
            )
            return dump_dict(PortalTaskColumnRead.model_validate(column))
