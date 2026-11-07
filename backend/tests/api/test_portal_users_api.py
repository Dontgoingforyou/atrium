"""API маршрутов portal_users: списки, presence, heartbeat, аватар, фото."""

from __future__ import annotations

import time
from datetime import UTC, datetime
from io import BytesIO
from unittest.mock import AsyncMock, patch
from urllib.parse import parse_qs, urlparse

import pytest
from app.infrastructure.db.models.portal_user_profile import PortalUserProfile
from app.integrations.effective_admin.client import PhotoBytes
from app.schemas.portal_user import AvatarUploadRead
from app.services.user_photo_url import build_user_photo_proxy_url, verify_user_photo_signature
from httpx import AsyncClient
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession
from tests.conftest import make_oidc_settings

_USERS = "/api/v1/portal/users"


@pytest.mark.parametrize(
    "path",
    [
        _USERS,
        f"{_USERS}/presence",
        f"{_USERS}/specialists",
    ],
)
@pytest.mark.asyncio
async def test_portal_users_list_401_without_token(client_sqlite_only: AsyncClient, path: str) -> None:
    r = await client_sqlite_only.get(path)
    assert r.status_code == 401


@pytest.mark.parametrize(
    ("method", "path", "kwargs"),
    [
        ("POST", f"{_USERS}/me/presence", {"json": {"visible": True, "active": True}}),
        ("POST", f"{_USERS}/me/avatar", {"files": {"file": ("a.jpg", BytesIO(b"\xff\xd8\xff\xe0"), "image/jpeg")}}),
        ("DELETE", f"{_USERS}/me/avatar", {}),
    ],
)
@pytest.mark.asyncio
async def test_portal_users_mutations_401_without_token(
    client_sqlite_only: AsyncClient,
    method: str,
    path: str,
    kwargs: dict[str, object],
) -> None:
    r = await client_sqlite_only.request(method, path, **kwargs)
    assert r.status_code == 401


@pytest.mark.parametrize("path", [_USERS, f"{_USERS}/presence", f"{_USERS}/specialists"])
@pytest.mark.asyncio
async def test_portal_users_developer_forbidden(client_developer: AsyncClient, path: str) -> None:
    r = await client_developer.get(path)
    assert r.status_code == 403
    assert r.json()["code"] == "forbidden"


@pytest.mark.asyncio
async def test_list_portal_users_empty(client_admin: AsyncClient, sqlite_session: AsyncSession) -> None:
    await sqlite_session.execute(delete(PortalUserProfile))
    await sqlite_session.commit()
    r = await client_admin.get(_USERS)
    assert r.status_code == 200
    assert r.json()["items"] == []
    assert r.json()["total"] == 0


@pytest.mark.asyncio
async def test_list_portal_users_after_profile_row(
    client_admin: AsyncClient,
    sqlite_session: AsyncSession,
) -> None:
    await sqlite_session.execute(delete(PortalUserProfile))
    await sqlite_session.commit()
    sqlite_session.add(
        PortalUserProfile(
            sub="john-sub",
            full_name="John",
            email="john@example.com",
            is_portal_admin=False,
        ),
    )
    await sqlite_session.commit()
    r = await client_admin.get(_USERS)
    assert r.status_code == 200
    data = r.json()["items"]
    assert len(data) == 1
    assert data[0]["sub"] == "john-sub"
    assert data[0]["display_name"] == "John"


@pytest.mark.asyncio
async def test_list_portal_users_excludes_chat_blocked_students(
    client_user: AsyncClient,
    sqlite_session: AsyncSession,
) -> None:
    sqlite_session.add(
        PortalUserProfile(
            sub="student-hidden",
            email="st@example.com",
            full_name="Студент",
            username="st",
            portal_chat_allowed=False,
        ),
    )
    await sqlite_session.commit()
    r = await client_user.get(_USERS)
    assert r.status_code == 200
    subs = {u["sub"] for u in r.json()["items"]}
    assert "student-hidden" not in subs
    assert "user-sub" in subs


@pytest.mark.parametrize(
    ("path", "params"),
    [
        (_USERS, {"skip": -1}),
        (_USERS, {"limit": 0}),
        (_USERS, {"limit": 501}),
        (f"{_USERS}/presence", {"limit": 501}),
    ],
)
@pytest.mark.asyncio
async def test_list_portal_users_pagination_422(
    client_admin: AsyncClient,
    path: str,
    params: dict[str, int],
) -> None:
    r = await client_admin.get(path, params=params)
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_list_portal_users_enriches_presence_from_redis(
    client_admin: AsyncClient,
    sqlite_session: AsyncSession,
) -> None:
    await sqlite_session.execute(delete(PortalUserProfile))
    sqlite_session.add(
        PortalUserProfile(
            sub="john-sub",
            full_name="John",
            email="john@example.com",
            is_portal_admin=False,
        ),
    )
    await sqlite_session.commit()

    with patch(
        "app.api.v1.routes.portal_users.bulk_presence",
        new=AsyncMock(return_value={"john-sub": "online"}),
    ):
        r = await client_admin.get(_USERS)

    assert r.status_code == 200
    assert r.json()["items"][0]["presence"] == "online"


@pytest.mark.asyncio
async def test_users_specialists_returns_chat_blocked_for_manager(
    client_manager: AsyncClient,
    sqlite_session: AsyncSession,
) -> None:
    sqlite_session.add(
        PortalUserProfile(
            sub="student-a",
            email="a@students.example",
            full_name="Студент А",
            username="sa",
            portal_chat_allowed=False,
        ),
    )
    await sqlite_session.commit()
    r = await client_manager.get(f"{_USERS}/specialists", params={"limit": 50})
    assert r.status_code == 200
    subs = {u["sub"] for u in r.json()["items"]}
    assert "student-a" in subs
    assert "manager-sub" not in subs


@pytest.mark.asyncio
async def test_users_specialists_ok_for_admin(
    client_admin: AsyncClient,
    sqlite_session: AsyncSession,
) -> None:
    sqlite_session.add(
        PortalUserProfile(
            sub="student-admin-list",
            email="sa2@students.example",
            full_name="Студент Б",
            username="sb",
            portal_chat_allowed=False,
        ),
    )
    await sqlite_session.commit()
    r = await client_admin.get(f"{_USERS}/specialists")
    assert r.status_code == 200
    assert "student-admin-list" in {u["sub"] for u in r.json()["items"]}


@pytest.mark.asyncio
async def test_users_specialists_forbidden_without_manager_role(client_no_idp: AsyncClient) -> None:
    r = await client_no_idp.get(f"{_USERS}/specialists")
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_list_portal_users_hides_test_account_email(
    client_admin: AsyncClient,
    sqlite_session: AsyncSession,
) -> None:
    await sqlite_session.execute(delete(PortalUserProfile))
    sqlite_session.add(PortalUserProfile(sub="ok-sub", email="ok@em.test", full_name="Ok"))
    sqlite_session.add(PortalUserProfile(sub="test-sub", email="test.managerau@em.test", full_name="Test Manager"))
    await sqlite_session.commit()
    r = await client_admin.get(_USERS)
    assert r.status_code == 200
    subs = {u["sub"] for u in r.json()["items"]}
    assert "ok-sub" in subs
    assert "test-sub" not in subs
    assert r.json()["total"] == 1


@pytest.mark.asyncio
async def test_list_portal_users_hides_autasks_and_other_dept(
    client_admin: AsyncClient,
    sqlite_session: AsyncSession,
) -> None:
    await sqlite_session.execute(delete(PortalUserProfile))
    sqlite_session.add(PortalUserProfile(sub="ok-sub", email="ok@em.test", full_name="Ok", gid_number="10000"))
    sqlite_session.add(
        PortalUserProfile(
            sub="hidden-sub",
            email="hidden.three@example.com",
            full_name="Hidden Three",
            gid_number="10000",
        )
    )
    sqlite_session.add(
        PortalUserProfile(
            sub="other-sub",
            email="other@em.test",
            full_name="Other",
            gid_number="20000",
        )
    )
    await sqlite_session.commit()
    r = await client_admin.get(_USERS)
    assert r.status_code == 200
    subs = {u["sub"] for u in r.json()["items"]}
    assert subs == {"ok-sub"}
    assert r.json()["total"] == 1


@pytest.mark.asyncio
async def test_users_specialists_keeps_test_student(
    client_manager: AsyncClient,
    sqlite_session: AsyncSession,
) -> None:
    sqlite_session.add(
        PortalUserProfile(
            sub="test-student",
            email="test.outstaff@example.com",
            full_name="Test Outstaff",
            username="test.outstaff",
            portal_chat_allowed=False,
        ),
    )
    await sqlite_session.commit()
    r = await client_manager.get(f"{_USERS}/specialists")
    assert r.status_code == 200
    assert "test-student" in {u["sub"] for u in r.json()["items"]}


@pytest.mark.asyncio
async def test_list_portal_students_enriches_presence(
    client_manager: AsyncClient,
    sqlite_session: AsyncSession,
) -> None:
    sqlite_session.add(
        PortalUserProfile(
            sub="student-a",
            email="a@students.example",
            full_name="Студент А",
            username="sa",
            portal_chat_allowed=False,
        ),
    )
    await sqlite_session.commit()
    with patch(
        "app.api.v1.routes.portal_users.bulk_presence",
        new=AsyncMock(return_value={"student-a": "away"}),
    ):
        r = await client_manager.get(f"{_USERS}/specialists", params={"limit": 10})
    assert r.status_code == 200
    found = next(u for u in r.json()["items"] if u["sub"] == "student-a")
    assert found["presence"] == "away"


@pytest.mark.asyncio
async def test_list_portal_users_presence_empty(client_admin: AsyncClient, sqlite_session: AsyncSession) -> None:
    await sqlite_session.execute(delete(PortalUserProfile))
    await sqlite_session.commit()
    r = await client_admin.get(f"{_USERS}/presence")
    assert r.status_code == 200
    assert r.json()["items"] == []
    assert r.json()["total"] == 0


@pytest.mark.asyncio
async def test_list_portal_users_presence_prefers_redis_last_seen(
    client_admin: AsyncClient,
    sqlite_session: AsyncSession,
) -> None:
    await sqlite_session.execute(delete(PortalUserProfile))
    sqlite_session.add(
        PortalUserProfile(
            sub="john-sub",
            full_name="John",
            email="john@example.com",
            is_portal_admin=False,
        ),
    )
    await sqlite_session.commit()

    with (
        patch(
            "app.api.v1.routes.portal_users.bulk_presence",
            new=AsyncMock(return_value={"john-sub": "online"}),
        ),
        patch(
            "app.api.v1.routes.portal_users.bulk_last_seen_iso",
            new=AsyncMock(return_value={"john-sub": "2026-03-01T10:00:00+00:00"}),
        ),
        patch(
            "app.api.v1.routes.portal_users.svc.bulk_last_seen_from_profile",
            new=AsyncMock(return_value={"john-sub": "2026-01-01T00:00:00+00:00"}),
        ),
    ):
        r = await client_admin.get(f"{_USERS}/presence")

    assert r.status_code == 200
    row = r.json()["items"][0]
    assert row["presence"] == "online"
    assert row["last_seen_at"] in ("2026-03-01T10:00:00+00:00", "2026-03-01T10:00:00Z")


@pytest.mark.asyncio
async def test_list_portal_users_presence_falls_back_to_profile_last_seen(
    client_admin: AsyncClient,
    sqlite_session: AsyncSession,
) -> None:
    await sqlite_session.execute(delete(PortalUserProfile))
    seen = datetime(2026, 2, 15, 8, 30, 0, tzinfo=UTC)
    sqlite_session.add(
        PortalUserProfile(
            sub="john-sub",
            full_name="John",
            email="john@example.com",
            is_portal_admin=False,
            last_seen_at=seen,
        ),
    )
    await sqlite_session.commit()

    with (
        patch("app.api.v1.routes.portal_users.bulk_presence", new=AsyncMock(return_value={})),
        patch("app.api.v1.routes.portal_users.bulk_last_seen_iso", new=AsyncMock(return_value={})),
    ):
        r = await client_admin.get(f"{_USERS}/presence")

    assert r.status_code == 200
    assert r.json()["items"][0]["last_seen_at"] in (
        "2026-02-15T08:30:00+00:00",
        "2026-02-15T08:30:00Z",
        "2026-02-15T08:30:00",
    )


@pytest.mark.asyncio
async def test_post_my_presence_visible_touches_last_seen(client_user: AsyncClient) -> None:
    with (
        patch("app.api.v1.routes.portal_users.record_presence", new=AsyncMock()) as mock_rec,
        patch("app.api.v1.routes.portal_users.touch_last_seen_in_db", new=AsyncMock()) as mock_touch,
    ):
        r = await client_user.post(f"{_USERS}/me/presence", json={"visible": True, "active": True})
    assert r.status_code == 204
    mock_rec.assert_awaited_once_with(user_sub="user-sub", visible=True, active=True)
    mock_touch.assert_awaited_once()
    assert mock_touch.await_args.kwargs == {"user_sub": "user-sub", "visible": True}


@pytest.mark.asyncio
async def test_post_my_presence_hidden_does_not_touch_last_seen(client_user: AsyncClient) -> None:
    with (
        patch("app.api.v1.routes.portal_users.record_presence", new=AsyncMock()),
        patch("app.api.v1.routes.portal_users.touch_last_seen_in_db", new=AsyncMock()) as mock_touch,
    ):
        r = await client_user.post(f"{_USERS}/me/presence", json={"visible": False, "active": False})
    assert r.status_code == 204
    mock_touch.assert_not_called()


@pytest.mark.asyncio
async def test_post_my_avatar_too_large_returns_413(
    client_user: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.services.avatar_upload_common import AVATAR_MAX_BYTES

    s = make_oidc_settings(
        effective_admin_base_url="https://ea.example",
        effective_admin_service_token="svc-token",
    )
    monkeypatch.setattr("app.services.portal_user_avatar.get_settings", lambda: s)
    big = b"x" * (AVATAR_MAX_BYTES + 1)
    r = await client_user.post(
        f"{_USERS}/me/avatar",
        files={"file": ("a.jpg", BytesIO(big), "image/jpeg")},
        headers={"Authorization": "Bearer test-token"},
    )
    assert r.status_code == 413
    assert r.json()["code"] == "payload_too_large"


@pytest.mark.asyncio
async def test_post_my_avatar_delegates_to_service(client_user: AsyncClient) -> None:
    expected = AvatarUploadRead(avatar_url=f"{_USERS}/user-sub/photo?exp=1&sig=x")
    with patch(
        "app.api.v1.routes.portal_users.avatar_svc.save_user_avatar",
        new=AsyncMock(return_value=expected),
    ) as mock_save:
        r = await client_user.post(
            f"{_USERS}/me/avatar",
            files={"file": ("a.jpg", BytesIO(b"\xff\xd8\xff\xe0"), "image/jpeg")},
            headers={"Authorization": "Bearer test-token"},
        )
    assert r.status_code == 200
    assert r.json() == expected.model_dump()
    mock_save.assert_awaited_once()
    assert mock_save.await_args.kwargs["user_sub"] == "user-sub"
    assert mock_save.await_args.kwargs["bearer_token"] == "test-token"


@pytest.mark.asyncio
async def test_delete_my_avatar_delegates_to_service(client_user: AsyncClient) -> None:
    with patch(
        "app.api.v1.routes.portal_users.avatar_svc.clear_user_avatar",
        new=AsyncMock(),
    ) as mock_clear:
        r = await client_user.delete(
            f"{_USERS}/me/avatar",
            headers={"Authorization": "Bearer test-token"},
        )
    assert r.status_code == 204
    mock_clear.assert_awaited_once()
    assert mock_clear.await_args.kwargs["user_sub"] == "user-sub"


@pytest.mark.asyncio
async def test_avatar_requires_bearer_even_with_current_user(client_user: AsyncClient) -> None:
    r = await client_user.post(
        f"{_USERS}/me/avatar",
        files={"file": ("a.jpg", BytesIO(b"\xff\xd8\xff\xe0"), "image/jpeg")},
    )
    assert r.status_code == 401
    r_del = await client_user.delete(f"{_USERS}/me/avatar")
    assert r_del.status_code == 401


def _photo_settings(*, enabled: bool = True) -> object:
    return make_oidc_settings(
        effective_admin_base_url="https://ea.example" if enabled else "",
        effective_admin_service_token="svc-token",
        admin_session_secret="dev-secret-change-me",
    )


@pytest.fixture
def patch_photo_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    s = _photo_settings()
    monkeypatch.setattr("app.services.user_photo_url.get_settings", lambda: s)
    monkeypatch.setattr("app.services.portal_user_photo_proxy.get_settings", lambda: s)


@pytest.mark.asyncio
async def test_user_photo_401_without_token(client_sqlite_only: AsyncClient) -> None:
    r = await client_sqlite_only.get(f"{_USERS}/user-sub/photo", params={"exp": 1, "sig": "x"})
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_user_photo_bad_signature_403(
    client_user: AsyncClient,
    patch_photo_settings: None,
) -> None:
    r = await client_user.get(
        f"{_USERS}/user-sub/photo",
        params={"exp": int(time.time()) + 100, "sig": "deadbeef"},
    )
    assert r.status_code == 403
    assert r.json()["code"] == "forbidden"


@pytest.mark.asyncio
async def test_user_photo_expired_401(
    client_user: AsyncClient,
    patch_photo_settings: None,
) -> None:
    r = await client_user.get(
        f"{_USERS}/user-sub/photo",
        params={"exp": int(time.time()) - 10, "sig": "x"},
    )
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_user_photo_unknown_sub_404(
    client_user: AsyncClient,
    patch_photo_settings: None,
) -> None:
    url = build_user_photo_proxy_url(user_sub="no-such-user", email="a@b.ru")
    assert url is not None
    q = parse_qs(urlparse(url).query)
    r = await client_user.get(
        f"{_USERS}/no-such-user/photo",
        params={"exp": q["exp"][0], "sig": q["sig"][0]},
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_user_photo_disabled_503(client_user: AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
    s_on = _photo_settings(enabled=True)
    monkeypatch.setattr("app.services.user_photo_url.get_settings", lambda: s_on)
    url = build_user_photo_proxy_url(user_sub="user-sub", email="user@example.com")
    assert url is not None
    q = parse_qs(urlparse(url).query)
    s_off = _photo_settings(enabled=False)
    monkeypatch.setattr("app.services.user_photo_url.get_settings", lambda: s_off)
    monkeypatch.setattr("app.services.portal_user_photo_proxy.get_settings", lambda: s_off)
    r = await client_user.get(
        f"{_USERS}/user-sub/photo",
        params={"exp": q["exp"][0], "sig": q["sig"][0]},
    )
    assert r.status_code == 503


@pytest.mark.asyncio
async def test_user_photo_ok_other_sub_with_valid_signature(
    client_user: AsyncClient,
    patch_photo_settings: None,
) -> None:
    url = build_user_photo_proxy_url(user_sub="admin-sub", email="admin@example.com")
    assert url is not None
    q = parse_qs(urlparse(url).query)
    verify_user_photo_signature(user_sub="admin-sub", exp=int(q["exp"][0]), sig=q["sig"][0])
    photo = PhotoBytes(content=b"\xff\xd8\xff\xe0jpeg", content_type="image/jpeg")
    with patch(
        "app.services.portal_user_photo_proxy.EffectiveAdminPhotoClient.get_user_photo",
        new=AsyncMock(return_value=photo),
    ):
        r = await client_user.get(
            f"{_USERS}/admin-sub/photo",
            params={"exp": q["exp"][0], "sig": q["sig"][0]},
        )
    assert r.status_code == 200
    assert r.content == photo.content
    assert r.headers["content-type"].startswith("image/jpeg")
