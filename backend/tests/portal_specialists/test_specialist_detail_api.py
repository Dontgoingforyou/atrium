"""HTTP-сценарии карточки специалиста: профиль, ссылки, заметки, RBAC."""

from __future__ import annotations

import uuid

import pytest
from app.core.auth_constants import IDP_GROUP_OUTSTAFF, SSO_GID_OUTSTAFF, SSO_POSITION_AU_SPECIALIST
from app.infrastructure.db.models.portal_specialist_link import PortalSpecialistLink
from app.infrastructure.db.models.portal_specialist_note import PortalSpecialistNote
from app.infrastructure.db.models.portal_specialist_profile import PortalSpecialistProfile
from app.portal_specialists.constants import SPECIALIST_NOTE_BODY_MAX_LENGTH
from app.schemas.auth import UserPublic
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.helpers.portal_test_users import user_portal_manager
from tests.portal_specialists.conftest import (
    as_user,
    assert_api_error,
    assert_pydantic_422,
    async_client_as,
    user_portal_manager_b,
)


def _au_manager_no_outstaff_group() -> UserPublic:
    return UserPublic(
        sub="au-mgr-sub",
        email="au@example.com",
        username="au_mgr",
        full_name="AU Manager",
        idp_groups=[],
        is_portal_admin=False,
        gid_number=SSO_GID_OUTSTAFF,
        position="au_chief",
    )


def _timesheet_au_specialist() -> UserPublic:
    return UserPublic(
        sub="ts-au-sub",
        email="ts@example.com",
        username="ts_au",
        full_name="TS AU",
        idp_groups=[IDP_GROUP_OUTSTAFF],
        is_portal_admin=False,
        position=SSO_POSITION_AU_SPECIALIST,
        gid_number=SSO_GID_OUTSTAFF,
    )


@pytest.mark.anyio
async def test_get_columns_and_statuses_forbidden_for_non_manager(client_regular_user: AsyncClient) -> None:
    cols = await client_regular_user.get("/api/v1/portal/specialists/columns")
    assert cols.status_code == 403
    statuses = await client_regular_user.get("/api/v1/portal/specialists/statuses")
    assert statuses.status_code == 403


@pytest.mark.anyio
async def test_pref_forbidden_for_non_manager(client_regular_user: AsyncClient) -> None:
    res = await client_regular_user.get("/api/v1/portal/me/specialist-board-pref")
    assert res.status_code == 403


@pytest.mark.anyio
async def test_get_profile_student_or_on_board(
    client_manager: AsyncClient,
    session_with_board: AsyncSession,
) -> None:
    on_board = await client_manager.get("/api/v1/portal/specialists/specialist-sub/profile")
    assert on_board.status_code == 200
    assert on_board.json()["specialist_sub"] == "specialist-sub"

    student = await client_manager.get("/api/v1/portal/specialists/purge-target-sub/profile")
    assert student.status_code == 200
    assert student.json()["location"] is None
    assert await session_with_board.get(PortalSpecialistProfile, "purge-target-sub") is None

    other_manager = await client_manager.get("/api/v1/portal/specialists/manager-b-sub/profile")
    assert other_manager.status_code == 404


@pytest.mark.anyio
async def test_get_profile_forbidden_for_student(client_specialist_user: AsyncClient) -> None:
    res = await client_specialist_user.get("/api/v1/portal/specialists/specialist-sub/profile")
    assert res.status_code == 403


@pytest.mark.anyio
async def test_patch_profile_success(client_manager: AsyncClient) -> None:
    ok = await client_manager.patch(
        "/api/v1/portal/specialists/specialist-sub/profile",
        json={"expected_version": 1, "location": "Донецк"},
    )
    assert ok.status_code == 200
    assert ok.json()["location"] == "Донецк"


@pytest.mark.anyio
async def test_patch_profile_forbidden_for_other_manager(client_manager_b: AsyncClient) -> None:
    denied = await client_manager_b.patch(
        "/api/v1/portal/specialists/specialist-sub/profile",
        json={"expected_version": 1, "location": "Москва"},
    )
    assert denied.status_code == 403


@pytest.mark.anyio
async def test_patch_profile_allowed_for_au_manager_without_outstaff_group(
    client_manager: AsyncClient,
    session_with_board: AsyncSession,
) -> None:
    from app.infrastructure.db.models.portal_manager_specialist import PortalManagerSpecialist

    session_with_board.add(
        PortalManagerSpecialist(
            manager_sub="au-mgr-sub",
            specialist_sub="specialist-sub",
            column_key="new",
            position=1,
        )
    )
    await session_with_board.commit()

    with as_user(_au_manager_no_outstaff_group):
        ok = await client_manager.patch(
            "/api/v1/portal/specialists/specialist-sub/profile",
            json={"expected_version": 1, "location": "Ростов"},
        )
    assert ok.status_code == 200
    assert ok.json()["location"] == "Ростов"


@pytest.mark.anyio
async def test_patch_profile_forbidden_for_timesheet_au_specialist(
    client_manager: AsyncClient,
) -> None:
    with as_user(_timesheet_au_specialist):
        denied = await client_manager.patch(
            "/api/v1/portal/specialists/specialist-sub/profile",
            json={"expected_version": 1, "location": "X"},
        )
    assert_api_error(denied, 403, "forbidden")


@pytest.mark.anyio
async def test_patch_profile_forbidden_birthdate_and_telegram(
    client_manager: AsyncClient,
) -> None:
    birth = await client_manager.patch(
        "/api/v1/portal/specialists/specialist-sub/profile",
        json={"expected_version": 1, "birthdate": "1990-01-01"},
    )
    assert_api_error(birth, 403, "forbidden")

    tg = await client_manager.patch(
        "/api/v1/portal/specialists/specialist-sub/profile",
        json={"expected_version": 1, "telegram": "@user"},
    )
    assert_api_error(tg, 403, "forbidden")


@pytest.mark.anyio
async def test_patch_profile_location_forbidden_when_jira_linked(
    client_manager: AsyncClient,
    session_with_board: AsyncSession,
) -> None:
    session_with_board.add(
        PortalSpecialistProfile(
            specialist_sub="specialist-sub",
            jira_issue_key="BASE-1",
            location="Старый",
        )
    )
    await session_with_board.commit()

    res = await client_manager.patch(
        "/api/v1/portal/specialists/specialist-sub/profile",
        json={"expected_version": 1, "location": "Новый"},
    )
    assert_api_error(res, 403, "forbidden")


@pytest.mark.anyio
async def test_get_profile_unknown_sub_404(client_manager: AsyncClient) -> None:
    res = await client_manager.get("/api/v1/portal/specialists/unknown-sub-xyz/profile")
    assert_api_error(res, 404, "not_found")


@pytest.mark.anyio
async def test_links_crud(client_manager: AsyncClient) -> None:
    created = await client_manager.post(
        "/api/v1/portal/specialists/specialist-sub/links",
        json={"title": "CV", "url": "https://example.com/cv.pdf"},
    )
    assert created.status_code == 201
    link_id = created.json()["id"]

    listed = await client_manager.get("/api/v1/portal/specialists/specialist-sub/links")
    assert listed.status_code == 200
    assert len(listed.json()) == 1

    deleted = await client_manager.delete(f"/api/v1/portal/specialists/specialist-sub/links/{link_id}")
    assert deleted.status_code == 204


@pytest.mark.anyio
async def test_create_link_forbidden_for_other_manager(client_manager_b: AsyncClient) -> None:
    denied = await client_manager_b.post(
        "/api/v1/portal/specialists/specialist-sub/links",
        json={"title": "X", "url": "https://example.com/x"},
    )
    assert denied.status_code == 403


@pytest.mark.anyio
async def test_delete_link_forbidden_for_non_author(
    session_with_board: AsyncSession,
    patch_oidc_settings: object,
) -> None:
    async with async_client_as(session_with_board, user_portal_manager) as ac:
        created = await ac.post(
            "/api/v1/portal/specialists/specialist-sub/links",
            json={"title": "CV", "url": "https://example.com/cv.pdf"},
        )
    assert created.status_code == 201
    link_id = created.json()["id"]

    async with async_client_as(session_with_board, user_portal_manager_b) as ac:
        denied = await ac.delete(f"/api/v1/portal/specialists/specialist-sub/links/{link_id}")
    assert_api_error(denied, 403, "forbidden")


@pytest.mark.anyio
async def test_delete_link_idor_wrong_specialist_path(
    client_manager: AsyncClient,
    session_with_board: AsyncSession,
) -> None:
    link = PortalSpecialistLink(
        specialist_sub="purge-target-sub",
        title="Other",
        url="https://example.com/other",
        created_by_sub="manager-sub",
    )
    session_with_board.add(link)
    await session_with_board.commit()
    await session_with_board.refresh(link)

    res = await client_manager.delete(
        f"/api/v1/portal/specialists/specialist-sub/links/{link.id}",
    )
    assert_api_error(res, 404, "not_found")


@pytest.mark.anyio
async def test_create_link_rejects_data_url(client_manager: AsyncClient) -> None:
    res = await client_manager.post(
        "/api/v1/portal/specialists/specialist-sub/links",
        json={"title": "bad", "url": "data:text/html,<script>alert(1)</script>"},
    )
    assert_pydantic_422(res)


@pytest.mark.anyio
async def test_notes_crud_and_path_idor(
    client_manager: AsyncClient,
    session_with_board: AsyncSession,
) -> None:
    created = await client_manager.post(
        "/api/v1/portal/specialists/specialist-sub/notes",
        json={"body": "Первая заметка"},
    )
    assert created.status_code == 201
    note_id = created.json()["id"]

    listed = await client_manager.get("/api/v1/portal/specialists/specialist-sub/notes")
    assert listed.status_code == 200
    assert listed.json()[0]["body"] == "Первая заметка"

    patched = await client_manager.patch(
        f"/api/v1/portal/specialists/specialist-sub/notes/{note_id}",
        json={"body": "Обновлено"},
    )
    assert patched.status_code == 200
    assert patched.json()["body"] == "Обновлено"

    wrong_path = await client_manager.patch(
        f"/api/v1/portal/specialists/purge-target-sub/notes/{note_id}",
        json={"body": "чужой path"},
    )
    assert wrong_path.status_code == 404
    note = await session_with_board.get(PortalSpecialistNote, uuid.UUID(note_id))
    assert note is not None
    assert note.body == "Обновлено"
    assert note.specialist_sub == "specialist-sub"

    deleted_wrong = await client_manager.delete(
        f"/api/v1/portal/specialists/purge-target-sub/notes/{note_id}",
    )
    assert deleted_wrong.status_code == 404

    deleted = await client_manager.delete(f"/api/v1/portal/specialists/specialist-sub/notes/{note_id}")
    assert deleted.status_code == 204

    too_long = await client_manager.post(
        "/api/v1/portal/specialists/specialist-sub/notes",
        json={"body": "x" * (SPECIALIST_NOTE_BODY_MAX_LENGTH + 1)},
    )
    assert too_long.status_code == 422


@pytest.mark.anyio
async def test_note_stores_mentions_like_other_threads(client_manager: AsyncClient) -> None:
    created = await client_manager.post(
        "/api/v1/portal/specialists/specialist-sub/notes",
        json={"body": "Смотри", "mentions": ["colleague-sub"]},
    )
    assert created.status_code == 201, created.text
    assert created.json()["mentions"] == ["colleague-sub"]
    assert created.json()["version"] == 1
    assert created.json()["media"] == []

    listed = (await client_manager.get("/api/v1/portal/specialists/specialist-sub/notes")).json()
    assert listed[0]["mentions"] == ["colleague-sub"]

    missing_media = await client_manager.post(
        "/api/v1/portal/specialists/specialist-sub/notes",
        json={"body": "картинка", "media_ids": [str(uuid.uuid4())]},
    )
    assert missing_media.status_code == 404


@pytest.mark.anyio
async def test_note_reply_to_reply_stays_in_thread(client_manager: AsyncClient) -> None:
    root = await client_manager.post(
        "/api/v1/portal/specialists/specialist-sub/notes",
        json={"body": "Корень"},
    )
    assert root.status_code == 201, root.text
    root_id = root.json()["id"]

    reply = await client_manager.post(
        "/api/v1/portal/specialists/specialist-sub/notes",
        json={"body": "Ответ", "parent_id": root_id},
    )
    assert reply.status_code == 201, reply.text
    reply_id = reply.json()["id"]

    nested = await client_manager.post(
        "/api/v1/portal/specialists/specialist-sub/notes",
        json={"body": "Ответ на ответ", "parent_id": reply_id},
    )
    assert nested.status_code == 201, nested.text

    listed = (await client_manager.get("/api/v1/portal/specialists/specialist-sub/notes")).json()
    assert [item["body"] for item in listed] == ["Корень"]
    assert listed[0]["replies"][0]["id"] == reply_id
    assert listed[0]["replies"][0]["replies"][0]["body"] == "Ответ на ответ"
    assert listed[0]["replies"][0]["replies"][0]["parent_id"] == reply_id


@pytest.mark.anyio
async def test_patch_note_forbidden_for_other_manager(
    client_manager_b: AsyncClient,
    session_with_board: AsyncSession,
) -> None:
    """Заметку создаём сервисом: два HTTP-клиента делят dependency_overrides."""
    from app.portal_specialists.schemas.specialist_detail import SpecialistNoteCreate
    from app.portal_specialists.services import specialist_note as note_svc

    from tests.helpers.portal_test_users import user_portal_manager

    note = await note_svc.create_specialist_note(
        session_with_board,
        user_portal_manager(),
        "specialist-sub",
        SpecialistNoteCreate(body="чужая"),
    )
    denied = await client_manager_b.patch(
        f"/api/v1/portal/specialists/specialist-sub/notes/{note.id}",
        json={"body": "не автор"},
    )
    assert_api_error(denied, 403, "forbidden")


@pytest.mark.anyio
async def test_admin_can_patch_and_delete_foreign_note(
    client_admin_board: AsyncClient,
    session_with_board: AsyncSession,
) -> None:
    from app.portal_specialists.schemas.specialist_detail import SpecialistNoteCreate
    from app.portal_specialists.services import specialist_note as note_svc

    from tests.helpers.portal_test_users import user_portal_manager

    note = await note_svc.create_specialist_note(
        session_with_board,
        user_portal_manager(),
        "specialist-sub",
        SpecialistNoteCreate(body="от менеджера"),
    )

    patched = await client_admin_board.patch(
        f"/api/v1/portal/specialists/specialist-sub/notes/{note.id}",
        json={"body": "правка admin"},
    )
    assert patched.status_code == 200
    assert patched.json()["body"] == "правка admin"

    deleted = await client_admin_board.delete(
        f"/api/v1/portal/specialists/specialist-sub/notes/{note.id}",
    )
    assert deleted.status_code == 204
