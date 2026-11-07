"""Сценарии второго аудита portal_collab: export RBAC, ссылки, files, mentions, documents."""

from __future__ import annotations

import io
import uuid
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.core.exceptions import NotFoundError, ValidationError
from app.core.utils import now_utc
from app.infrastructure.db.models.portal_document import PortalDocument
from app.infrastructure.db.models.portal_task import PortalTaskComment
from app.infrastructure.db.models.portal_user_profile import PortalUserProfile
from app.portal_chat.schemas.chat import PortalChatMessageCreate
from app.portal_chat.services import chat as chat_svc
from app.portal_collab.schemas.task import PortalTaskCreate, TaskLinkCreate
from app.portal_collab.services import notification as notification_svc
from app.portal_collab.services import task as task_svc
from app.portal_collab.services._notification_access import batch_task_access_check
from app.services.file_upload_validation import assert_declared_size_within_limit
from httpx import AsyncClient
from pydantic import ValidationError as PydanticValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from tests.helpers.portal_test_users import (
    user_portal_admin,
    user_portal_no_idp_groups,
    user_portal_user_b,
)
from tests.portal_collab.conftest import async_client_as


@pytest.mark.asyncio
async def test_task_column_export_omits_inaccessible_parent_description(
    client_admin: AsyncClient,
    sqlite_session: AsyncSession,
    patch_oidc_settings: object,
) -> None:
    """Подзадача видна исполнителю, описание чужого родителя в TXT не попадает."""
    status_key = f"exp_rbac_{uuid.uuid4().hex[:8]}"
    r = await client_admin.post(
        "/api/v1/portal/task-columns",
        json={"title": "Колонка RBAC", "color": "#111111", "status_key": status_key, "position": 80},
    )
    assert r.status_code == 201, r.text
    cid = r.json()["id"]

    viewer = user_portal_no_idp_groups()
    r = await client_admin.post(
        "/api/v1/portal/tasks",
        json={
            "title": "Секретный родитель",
            "assignee_sub": "admin-sub",
            "description": "<p>Секретное описание родителя XYZ</p>",
        },
    )
    assert r.status_code == 201, r.text
    parent_id = r.json()["id"]

    r = await client_admin.post(
        "/api/v1/portal/tasks",
        json={
            "title": "Видимая подзадача",
            "assignee_sub": viewer.sub,
            "status": status_key,
            "parent_task_id": parent_id,
            "description": "<p>Текст подзадачи</p>",
        },
    )
    assert r.status_code == 201, r.text

    async with async_client_as(sqlite_session, user_portal_no_idp_groups) as ac:
        r = await ac.get(f"/api/v1/portal/task-columns/{cid}/export")
        assert r.status_code == 200, r.text
        text = r.content.decode("utf-8-sig")
        assert "Видимая подзадача" in text
        assert "Секретное описание родителя XYZ" not in text
        assert "Секретный родитель" not in text


@pytest.mark.parametrize(
    "raw_url",
    ["javascript:alert(1)", "data:text/html,hi", "ftp://files.example.com/a"],
)
def test_task_link_create_rejects_unsafe_schemes(raw_url: str) -> None:
    with pytest.raises(PydanticValidationError):
        TaskLinkCreate(url=raw_url)


def test_task_link_create_accepts_https() -> None:
    body = TaskLinkCreate(url="https://example.com/docs")
    assert body.url == "https://example.com/docs"


@pytest.mark.asyncio
async def test_task_link_http_rejects_javascript(
    client_admin: AsyncClient,
) -> None:
    r = await client_admin.post(
        "/api/v1/portal/tasks",
        json={"title": "Задача со ссылкой", "assignee_sub": "admin-sub"},
    )
    assert r.status_code == 201, r.text
    tid = r.json()["id"]
    r = await client_admin.post(
        f"/api/v1/portal/tasks/{tid}/links",
        json={"url": "javascript:alert(1)"},
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_upload_task_rich_media_persists_without_router_commit(
    client_admin: AsyncClient,
) -> None:
    r = await client_admin.post(
        "/api/v1/portal/tasks",
        json={"title": "Задача с картинкой", "assignee_sub": "admin-sub"},
    )
    assert r.status_code == 201, r.text
    tid = r.json()["id"]
    jpeg = b"\xff\xd8\xff\xe0" + b"\x00" * 32
    with (
        patch("app.services.rich_media_upload.async_upload_stream_to_key", new_callable=AsyncMock),
        patch("app.services.rich_media.get_presigned_url", return_value="https://minio.local/img"),
    ):
        r = await client_admin.post(
            f"/api/v1/portal/tasks/{tid}/rich-media",
            files={"file": ("pic.jpg", jpeg, "image/jpeg")},
        )
        assert r.status_code == 201, r.text
        media_id = r.json()["id"]
        r = await client_admin.get(f"/api/v1/portal/rich-media/{media_id}")
        assert r.status_code == 200, r.text


def test_assert_declared_size_within_limit_rejects_oversize() -> None:
    assert_declared_size_within_limit(10, 100)
    with pytest.raises(ValidationError, match="МБ"):
        assert_declared_size_within_limit(200, 100)


@pytest.mark.asyncio
async def test_task_file_upload_rejects_declared_oversize_before_storage(
    client_admin: AsyncClient,
) -> None:
    r = await client_admin.post(
        "/api/v1/portal/tasks",
        json={"title": "Файл сверх лимита", "assignee_sub": "admin-sub"},
    )
    assert r.status_code == 201, r.text
    tid = r.json()["id"]
    with (
        patch(
            "app.portal_collab.routes.task_files.get_settings",
            return_value=SimpleNamespace(attachment_max_size_bytes=10),
        ),
        patch("app.portal_collab.services.task_file.async_upload_file", new_callable=AsyncMock) as up,
    ):
        r = await client_admin.post(
            f"/api/v1/portal/tasks/{tid}/files",
            files={"file": ("report.pdf", b"%PDF-1.4" + b"x" * 40, "application/pdf")},
        )
    assert r.status_code == 422
    up.assert_not_called()


@pytest.mark.asyncio
async def test_mention_notifies_user_with_source_message_access(
    sqlite_session: AsyncSession,
) -> None:
    admin = user_portal_admin()
    peer = user_portal_user_b()
    chat = await chat_svc.get_or_create_direct_chat(sqlite_session, admin, peer.sub)
    msg = await chat_svc.post_message(
        sqlite_session,
        admin,
        chat.id,
        PortalChatMessageCreate(body="источник задачи"),
    )
    task = await task_svc.create_task(
        sqlite_session,
        admin,
        PortalTaskCreate(title="Из сообщения", assignee_sub=admin.sub, source_message_id=msg.id),
    )
    now = datetime.now(UTC)
    comment = PortalTaskComment(
        task_id=task.id,
        parent_id=None,
        author_sub=admin.sub,
        body="@ub",
        mentions=[peer.sub],
        created_at=now,
        updated_at=now,
    )
    sqlite_session.add(comment)
    await sqlite_session.flush()

    profile = await sqlite_session.get(PortalUserProfile, peer.sub)
    assert profile is not None
    can_access = await batch_task_access_check(sqlite_session, {peer.sub}, task, {peer.sub: profile})
    assert peer.sub in can_access

    notified = await notification_svc.create_mention_notifications(sqlite_session, task, comment, admin.sub)
    assert peer.sub in notified


@pytest.mark.asyncio
async def test_create_task_rejects_soft_deleted_document(sqlite_session: AsyncSession) -> None:
    admin = user_portal_admin()
    doc = PortalDocument(
        title="В корзине",
        author_sub=admin.sub,
        author_display_name="A",
        author_email="a@e.com",
        owner_sub=admin.sub,
        body="x",
        parent_document_id=None,
        deleted_at=now_utc(),
    )
    sqlite_session.add(doc)
    await sqlite_session.flush()
    with pytest.raises(NotFoundError, match="Документ не найден"):
        await task_svc.create_task(
            sqlite_session,
            admin,
            PortalTaskCreate(title="К удалённому", assignee_sub=admin.sub, document_id=doc.id),
        )


@pytest.mark.asyncio
async def test_delete_file_skips_minio_when_db_commit_fails(sqlite_session: AsyncSession) -> None:
    from app.portal_collab.services import task_file as file_svc

    admin = user_portal_admin()
    task = await task_svc.create_task(
        sqlite_session,
        admin,
        PortalTaskCreate(title="Удаление файла", assignee_sub=admin.sub),
    )
    with patch(
        "app.portal_collab.services.task_file.async_upload_file",
        new_callable=AsyncMock,
        return_value="sk-del",
    ):
        row = await file_svc.upload_file(
            sqlite_session,
            admin,
            task.id,
            file_data=io.BytesIO(b"%PDF-1.4 test"),
            file_size=13,
            content_type="application/pdf",
            original_filename="report.pdf",
        )
    with (
        patch("app.portal_collab.services.task_file.async_delete_object", new_callable=AsyncMock) as del_mock,
        patch.object(sqlite_session, "commit", new_callable=AsyncMock, side_effect=RuntimeError("commit fail")),
    ):
        with pytest.raises(RuntimeError, match="commit fail"):
            await file_svc.delete_file(sqlite_session, admin, task.id, row.id)
    del_mock.assert_not_called()


@pytest.mark.asyncio
async def test_push_task_to_jira_locks_row_on_postgresql(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core.config import Settings
    from app.portal_collab.services import task_jira_outbound as mod

    captured: dict[str, object] = {}

    async def _execute(stmt: object) -> MagicMock:
        captured["stmt"] = stmt
        result = MagicMock()
        result.scalar_one_or_none.return_value = None
        return result

    session = MagicMock()
    session.get_bind.return_value.dialect.name = "postgresql"
    session.execute = _execute
    monkeypatch.setattr(
        mod,
        "get_settings",
        lambda: Settings(
            jira_base_url="https://jira.example",
            jira_personal_access_token="tok",
            jira_tasks_sync_enabled=True,
        ),
    )
    await mod.push_task_to_jira(session, MagicMock(), uuid.uuid4())
    stmt = captured["stmt"]
    assert getattr(stmt, "_for_update_arg", None) is not None
