"""API настроек аккаунта."""

from __future__ import annotations

import pytest
from app.infrastructure.db.models.portal_document import PortalDocument
from app.infrastructure.db.models.portal_user_profile import PortalUserProfile
from httpx import AsyncClient
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession
from tests.helpers.portal_test_users import user_portal_admin, user_portal_regular

_PREFS = "/api/v1/portal/account/preferences"


def _user_sub() -> str:
    return user_portal_regular().sub


def _admin_sub() -> str:
    return user_portal_admin().sub


@pytest.mark.parametrize(
    ("method", "json_body"),
    [
        ("GET", None),
        ("PATCH", {"guided_tour_completed": True}),
    ],
)
@pytest.mark.asyncio
async def test_account_preferences_401_without_token(
    client_sqlite_only: AsyncClient,
    method: str,
    json_body: dict[str, bool] | None,
) -> None:
    r = await client_sqlite_only.request(method, _PREFS, json=json_body)
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_account_preferences_developer_can_toggle_guided_tour(client_developer: AsyncClient) -> None:
    """Timesheet-only (students / АУ): guided tour prefs без доступа к остальным разделам аккаунта."""
    r = await client_developer.get(_PREFS)
    assert r.status_code == 200
    assert r.json()["guided_tour_completed"] is False

    r = await client_developer.patch(_PREFS, json={"guided_tour_completed": True})
    assert r.status_code == 200
    assert r.json()["guided_tour_completed"] is True

    r = await client_developer.patch(_PREFS, json={"guided_tour_completed": False})
    assert r.status_code == 200
    assert r.json()["guided_tour_completed"] is False


@pytest.mark.asyncio
async def test_account_preferences_developer_cannot_toggle_trash(
    client_developer: AsyncClient,
    sqlite_session: AsyncSession,
) -> None:
    from tests.helpers.portal_test_users import user_portal_developer

    profile = await sqlite_session.get(PortalUserProfile, user_portal_developer().sub)
    assert profile is not None
    before = profile.notify_document_trash
    r = await client_developer.patch(_PREFS, json={"notify_document_trash": False})
    assert r.status_code == 403
    assert r.json()["code"] == "forbidden"
    await sqlite_session.refresh(profile)
    assert profile.notify_document_trash is before


@pytest.mark.asyncio
async def test_account_preferences_admin_get_patch(
    client_admin: AsyncClient,
    sqlite_session: AsyncSession,
) -> None:
    r = await client_admin.get(_PREFS)
    assert r.status_code == 200
    body = r.json()
    assert set(body) >= {"notify_document_trash", "guided_tour_completed"}
    assert body["notify_document_trash"] is True
    assert body["guided_tour_completed"] is False

    r = await client_admin.patch(_PREFS, json={"notify_document_trash": False})
    assert r.status_code == 200
    assert r.json()["notify_document_trash"] is False
    assert r.json()["guided_tour_completed"] is False

    await sqlite_session.refresh(await sqlite_session.get(PortalUserProfile, _admin_sub()))
    profile = await sqlite_session.get(PortalUserProfile, _admin_sub())
    assert profile is not None
    assert profile.notify_document_trash is False
    assert profile.guided_tour_completed is False

    r = await client_admin.patch(_PREFS, json={"notify_document_trash": True})
    assert r.status_code == 200
    assert r.json()["notify_document_trash"] is True


@pytest.mark.asyncio
async def test_account_preferences_admin_partial_tour_keeps_trash(
    client_admin: AsyncClient,
    sqlite_session: AsyncSession,
) -> None:
    await client_admin.patch(_PREFS, json={"notify_document_trash": False})
    r = await client_admin.patch(_PREFS, json={"guided_tour_completed": True})
    assert r.status_code == 200
    assert r.json()["notify_document_trash"] is False
    assert r.json()["guided_tour_completed"] is True
    profile = await sqlite_session.get(PortalUserProfile, _admin_sub())
    assert profile is not None
    assert profile.notify_document_trash is False


@pytest.mark.asyncio
async def test_account_preferences_admin_both_fields(
    client_admin: AsyncClient,
    sqlite_session: AsyncSession,
) -> None:
    r = await client_admin.patch(
        _PREFS,
        json={"notify_document_trash": False, "guided_tour_completed": True},
    )
    assert r.status_code == 200
    assert r.json()["notify_document_trash"] is False
    assert r.json()["guided_tour_completed"] is True
    profile = await sqlite_session.get(PortalUserProfile, _admin_sub())
    assert profile is not None
    assert profile.notify_document_trash is False
    assert profile.guided_tour_completed is True


@pytest.mark.asyncio
async def test_account_preferences_regular_cannot_toggle_trash(
    client_user: AsyncClient,
    sqlite_session: AsyncSession,
) -> None:
    profile = await sqlite_session.get(PortalUserProfile, _user_sub())
    assert profile is not None
    before = profile.notify_document_trash
    r = await client_user.patch(_PREFS, json={"notify_document_trash": False})
    assert r.status_code == 403
    assert r.json()["code"] == "forbidden"
    assert "администратор" in r.json()["message"].lower()
    await sqlite_session.refresh(profile)
    assert profile.notify_document_trash is before


@pytest.mark.asyncio
async def test_account_preferences_regular_mixed_patch_does_not_save_tour(
    client_user: AsyncClient,
    sqlite_session: AsyncSession,
) -> None:
    r = await client_user.patch(
        _PREFS,
        json={"notify_document_trash": False, "guided_tour_completed": True},
    )
    assert r.status_code == 403
    profile = await sqlite_session.get(PortalUserProfile, _user_sub())
    assert profile is not None
    assert profile.guided_tour_completed is False
    assert profile.notify_document_trash is True


@pytest.mark.asyncio
async def test_account_preferences_regular_can_toggle_guided_tour(client_user: AsyncClient) -> None:
    """TC-024: обычный user может PATCH guided_tour_completed."""
    r = await client_user.get(_PREFS)
    assert r.status_code == 200
    assert r.json()["guided_tour_completed"] is False
    assert r.json()["notify_document_trash"] is True

    r = await client_user.patch(_PREFS, json={"guided_tour_completed": True})
    assert r.status_code == 200
    assert r.json()["guided_tour_completed"] is True

    r = await client_user.patch(_PREFS, json={"guided_tour_completed": False})
    assert r.status_code == 200
    assert r.json()["guided_tour_completed"] is False


@pytest.mark.asyncio
async def test_account_preferences_forbidden_without_profile(
    client_user: AsyncClient,
    sqlite_session: AsyncSession,
) -> None:
    await sqlite_session.execute(delete(PortalUserProfile).where(PortalUserProfile.sub == _user_sub()))
    await sqlite_session.commit()

    r_get = await client_user.get(_PREFS)
    assert r_get.status_code == 403
    assert r_get.json()["code"] == "forbidden"
    assert "профиль" in r_get.json()["message"].lower()

    r_patch = await client_user.patch(_PREFS, json={"guided_tour_completed": True})
    assert r_patch.status_code == 403
    assert r_patch.json()["code"] == "forbidden"
    assert "профиль" in r_patch.json()["message"].lower()


@pytest.mark.asyncio
async def test_account_preferences_admin_forbidden_without_profile(
    client_admin: AsyncClient,
    sqlite_session: AsyncSession,
) -> None:
    await sqlite_session.execute(delete(PortalUserProfile).where(PortalUserProfile.sub == _admin_sub()))
    await sqlite_session.commit()
    r = await client_admin.get(_PREFS)
    assert r.status_code == 403
    assert "профиль" in r.json()["message"].lower()


@pytest.mark.asyncio
async def test_account_preferences_patch_without_trash_field(
    client_user: AsyncClient,
    sqlite_session: AsyncSession,
) -> None:
    await sqlite_session.execute(delete(PortalUserProfile).where(PortalUserProfile.sub == _user_sub()))
    sqlite_session.add(
        PortalUserProfile(
            sub=_user_sub(),
            email="user@example.com",
            full_name="User",
            username="user",
            is_portal_admin=False,
            notify_document_trash=True,
            guided_tour_completed=False,
        ),
    )
    await sqlite_session.commit()

    r = await client_user.patch(_PREFS, json={})
    assert r.status_code == 200
    assert r.json()["notify_document_trash"] is True
    assert r.json()["guided_tour_completed"] is False

    profile = await sqlite_session.get(PortalUserProfile, _user_sub())
    assert profile is not None
    assert profile.notify_document_trash is True
    assert profile.guided_tour_completed is False


@pytest.mark.asyncio
async def test_account_preferences_null_fields_are_noop(
    client_user: AsyncClient,
    sqlite_session: AsyncSession,
) -> None:
    r = await client_user.patch(
        _PREFS,
        json={"notify_document_trash": None, "guided_tour_completed": None},
    )
    assert r.status_code == 200
    profile = await sqlite_session.get(PortalUserProfile, _user_sub())
    assert profile is not None
    assert profile.notify_document_trash is True
    assert profile.guided_tour_completed is False


@pytest.mark.asyncio
async def test_account_preferences_invalid_type_422(client_user: AsyncClient) -> None:
    r = await client_user.patch(_PREFS, json={"guided_tour_completed": ["not-bool"]})
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_account_preferences_trash_off_excludes_admin_from_notifications(
    client_admin: AsyncClient,
    sqlite_session: AsyncSession,
) -> None:
    from app.portal_collab.services.notification import create_document_trashed_notifications

    r = await client_admin.patch(_PREFS, json={"notify_document_trash": False})
    assert r.status_code == 200

    doc = PortalDocument(
        title="Удаляемый после выключения prefs",
        author_sub="other-sub",
        body="",
    )
    sqlite_session.add(doc)
    await sqlite_session.commit()
    await sqlite_session.refresh(doc)

    notified = await create_document_trashed_notifications(
        sqlite_session,
        doc.id,
        author_sub="other-sub",
    )
    assert _admin_sub() not in notified
