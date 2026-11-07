from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from app.core.exceptions import ForbiddenError, NotFoundError
from app.infrastructure.db.models.portal_document import PortalDocument
from app.infrastructure.db.models.portal_rich_media import PortalRichMedia
from app.infrastructure.db.models.portal_task import PortalTask
from app.portal_collab.schemas.agreement import PortalAgreementCreate
from app.portal_collab.schemas.task import PortalTaskCreate, TaskCommentCreate
from app.portal_collab.services import agreement as agreement_svc
from app.portal_collab.services import task as task_svc
from app.portal_collab.services import task_comment as comment_svc
from app.schemas.auth import UserPublic
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.helpers.portal_test_users import (
    user_portal_admin,
    user_portal_developer,
    user_portal_no_idp_groups,
    user_portal_regular,
)
from tests.portal_collab.conftest import assert_api_error


@pytest.mark.asyncio
async def test_get_task_allowed_for_manager_not_creator_not_assignee(sqlite_session: AsyncSession) -> None:
    """Менеджер должен видеть чужую задачу через get_task — так же, как list_tasks её отдаёт."""
    from tests.helpers.portal_test_users import user_portal_manager

    creator = user_portal_regular()
    manager = user_portal_manager()
    task = await task_svc.create_task(
        sqlite_session,
        creator,
        PortalTaskCreate(title="Чужая для менеджера", assignee_sub=creator.sub),
    )

    listed = await task_svc.list_tasks(sqlite_session, manager)
    assert any(t.id == task.id for t in listed)

    fetched = await task_svc.get_task(sqlite_session, manager, task.id)
    assert fetched.id == task.id


@pytest.mark.asyncio
async def test_get_task_still_forbidden_for_unrelated_regular_user(sqlite_session: AsyncSession) -> None:
    """Пользователь без роли менеджера/админа и без связи с задачей — как и раньше, получает 403."""
    creator = user_portal_admin()
    other = user_portal_no_idp_groups()
    task = await task_svc.create_task(
        sqlite_session,
        creator,
        PortalTaskCreate(title="Не для чужих", assignee_sub=creator.sub),
    )
    with pytest.raises(ForbiddenError):
        await task_svc.get_task(sqlite_session, other, task.id)


@pytest.mark.asyncio
async def test_list_agreements_hides_document_leak_for_timesheet_only_user(
    sqlite_session: AsyncSession,
) -> None:
    """Пользователь в режиме «только таймшиты» не должен видеть агримент чужого документа
    вне developer-docs только по факту наличия document_id."""
    owner = user_portal_admin()
    student = user_portal_developer()

    doc = PortalDocument(
        title="Обычный документ",
        author_sub=owner.sub,
        author_display_name="A",
        author_email="a@e.com",
        owner_sub=owner.sub,
        body="x",
        parent_document_id=None,
    )
    sqlite_session.add(doc)
    await sqlite_session.flush()

    row = await agreement_svc.create_agreement(
        sqlite_session,
        owner,
        PortalAgreementCreate(body="Договорённость по документу", document_id=doc.id),
    )

    rows = await agreement_svc.list_agreements(sqlite_session, student)
    assert row.id not in {r.id for r in rows}

    found = await agreement_svc.search_agreements_for_user(sqlite_session, student, "Договорённость")
    assert row.id not in {r.id for r in found}

    with pytest.raises(ForbiddenError):
        await agreement_svc.get_agreement(sqlite_session, student, row.id)


@pytest.mark.asyncio
async def test_list_agreements_shows_document_agreement_for_regular_user(
    sqlite_session: AsyncSession,
) -> None:
    """Обычный (не «только таймшиты») пользователь — как раньше — видит агримент по документу."""
    owner = user_portal_admin()
    regular = user_portal_regular()

    doc = PortalDocument(
        title="Документ для всех",
        author_sub=owner.sub,
        author_display_name="A",
        author_email="a@e.com",
        owner_sub=owner.sub,
        body="x",
        parent_document_id=None,
    )
    sqlite_session.add(doc)
    await sqlite_session.flush()

    row = await agreement_svc.create_agreement(
        sqlite_session,
        owner,
        PortalAgreementCreate(body="Видна всем", document_id=doc.id),
    )

    rows = await agreement_svc.list_agreements(sqlite_session, regular)
    assert row.id in {r.id for r in rows}


@pytest.mark.asyncio
async def test_create_agreement_forbidden_for_document_outside_access(sqlite_session: AsyncSession) -> None:
    owner = user_portal_admin()
    student = user_portal_developer()

    doc = PortalDocument(
        title="Недоступный студенту",
        author_sub=owner.sub,
        author_display_name="A",
        author_email="a@e.com",
        owner_sub=owner.sub,
        body="x",
        parent_document_id=None,
    )
    sqlite_session.add(doc)
    await sqlite_session.flush()

    with pytest.raises(ForbiddenError, match="документ"):
        await agreement_svc.create_agreement(
            sqlite_session,
            student,
            PortalAgreementCreate(body="Попытка привязки", document_id=doc.id),
        )


@pytest.mark.asyncio
async def test_create_agreement_task_link_uses_task_svc_visibility(sqlite_session: AsyncSession) -> None:
    """Привязка агримента к задаче должна использовать ту же RBAC-политику, что get_task."""
    creator = user_portal_admin()
    outsider = user_portal_no_idp_groups()
    task = await task_svc.create_task(
        sqlite_session,
        creator,
        PortalTaskCreate(title="Задача для агримента", assignee_sub=creator.sub),
    )

    with pytest.raises(ForbiddenError, match="задач"):
        await agreement_svc.create_agreement(
            sqlite_session,
            outsider,
            PortalAgreementCreate(body="Не видит задачу", task_id=task.id),
        )

    row = await agreement_svc.create_agreement(
        sqlite_session,
        creator,
        PortalAgreementCreate(body="Автор видит свою задачу", task_id=task.id),
    )
    assert row.task_id == task.id


async def _make_task(session: AsyncSession, user: UserPublic, title: str) -> PortalTask:
    return await task_svc.create_task(session, user, PortalTaskCreate(title=title, assignee_sub=user.sub))


@pytest.mark.asyncio
async def test_create_comment_rejects_media_from_other_task(sqlite_session: AsyncSession) -> None:
    admin = user_portal_admin()
    task = await _make_task(sqlite_session, admin, "Задача 1")
    other_task = await _make_task(sqlite_session, admin, "Задача 2")

    media = PortalRichMedia(
        storage_key="k1",
        content_type="image/png",
        original_filename="a.png",
        file_size=10,
        uploader_sub=admin.sub,
        task_id=other_task.id,
    )
    sqlite_session.add(media)
    await sqlite_session.commit()

    with pytest.raises(ForbiddenError):
        await comment_svc.create_comment(
            sqlite_session,
            admin,
            task.id,
            TaskCommentCreate(body="текст", media_ids=[media.id]),
        )


@pytest.mark.asyncio
async def test_create_comment_rejects_media_uploaded_by_other_user(sqlite_session: AsyncSession) -> None:
    admin = user_portal_admin()
    other = user_portal_regular()
    task = await _make_task(sqlite_session, admin, "Задача 3")

    media = PortalRichMedia(
        storage_key="k2",
        content_type="image/png",
        original_filename="b.png",
        file_size=10,
        uploader_sub=other.sub,
        task_id=task.id,
    )
    sqlite_session.add(media)
    await sqlite_session.commit()

    with pytest.raises(ForbiddenError):
        await comment_svc.create_comment(
            sqlite_session,
            admin,
            task.id,
            TaskCommentCreate(body="текст", media_ids=[media.id]),
        )


@pytest.mark.asyncio
async def test_create_comment_rejects_missing_media_id(sqlite_session: AsyncSession) -> None:
    admin = user_portal_admin()
    task = await _make_task(sqlite_session, admin, "Задача 4")

    with pytest.raises(NotFoundError):
        await comment_svc.create_comment(
            sqlite_session,
            admin,
            task.id,
            TaskCommentCreate(body="текст", media_ids=[uuid.uuid4()]),
        )


@pytest.mark.asyncio
async def test_create_comment_accepts_own_media_of_same_task(sqlite_session: AsyncSession) -> None:
    admin = user_portal_admin()
    task = await _make_task(sqlite_session, admin, "Задача 5")

    media = PortalRichMedia(
        storage_key="k3",
        content_type="image/png",
        original_filename="c.png",
        file_size=10,
        uploader_sub=admin.sub,
        task_id=task.id,
    )
    sqlite_session.add(media)
    await sqlite_session.commit()

    comment = await comment_svc.create_comment(
        sqlite_session,
        admin,
        task.id,
        TaskCommentCreate(body="текст", media_ids=[media.id]),
    )
    assert len(comment.comment_media) == 1
    assert comment.comment_media[0].media_id == media.id


@pytest.mark.asyncio
async def test_task_board_ws_ticket_forbidden_for_timesheet_only_user(
    client_developer: AsyncClient,
) -> None:
    r = await client_developer.post("/api/v1/portal/tasks/board/ws-ticket")
    assert_api_error(r, 403, "forbidden")


@pytest.mark.asyncio
async def test_portal_task_admin_on_model_change_sets_creator_and_assignee_sub() -> None:
    from app.portal_collab.admin.tasks import PortalTaskAdmin

    admin = PortalTaskAdmin()
    data: dict = {
        "creator_user": SimpleNamespace(sub="creator-from-form"),
        "assignee_user": SimpleNamespace(sub="assignee-from-form"),
    }
    await admin.on_model_change(data, None, True, MagicMock())
    assert data["creator_sub"] == "creator-from-form"
    assert data["assignee_sub"] == "assignee-from-form"


@pytest.mark.asyncio
async def test_portal_task_admin_on_model_change_clears_assignee_sub_when_unset() -> None:
    from app.portal_collab.admin.tasks import PortalTaskAdmin

    admin = PortalTaskAdmin()
    data: dict = {"creator_user": SimpleNamespace(sub="creator-x"), "assignee_user": None}
    await admin.on_model_change(data, None, False, MagicMock())
    assert data["creator_sub"] == "creator-x"
    assert data["assignee_sub"] is None


def test_fmt_status_key_uses_shared_enum_labels_source() -> None:
    from app.admin.enum_labels import TASK_STATUS_LABELS_RU
    from app.portal_collab.admin.tasks import _fmt_status_key

    out = _fmt_status_key(SimpleNamespace(status_key="done"), "status_key")
    assert TASK_STATUS_LABELS_RU["done"] in out
    assert "Готово" in out
