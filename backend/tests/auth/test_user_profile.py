"""Unit-тесты вспомогательных функций профиля пользователя из SSO."""

from __future__ import annotations

from datetime import date
from unittest.mock import patch

import pytest
from app.core.auth_constants import IDP_GROUP_PORTAL_ADMIN
from app.infrastructure.db.models.portal_specialist_profile import PortalSpecialistProfile
from app.infrastructure.db.models.portal_user_profile import PortalUserProfile
from app.services import user_profile as up
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


def test_full_name_prefers_name_field() -> None:
    assert up._full_name_from_payload({"name": "  Full Name  "}) == "Full Name"


def test_full_name_from_given_and_family() -> None:
    assert up._full_name_from_payload({"given_name": "Ivan", "family_name": "Petrov"}) == "Ivan Petrov"


def test_full_name_empty_when_no_parts() -> None:
    assert up._full_name_from_payload({"name": 123}) == ""  # type: ignore[arg-type]


def test_username_from_preferred() -> None:
    assert up._username_from_payload({"preferred_username": "  ivan  "}, "a@b.c") == "ivan"


def test_username_from_email_local_part() -> None:
    assert up._username_from_payload({}, "user.name@example.com") == "user.name"


def test_username_fallback_sub() -> None:
    assert up._username_from_payload({"sub": "kc-id-9"}, "") == "kc-id-9"


def test_position_from_payload() -> None:
    assert up._position_from_payload({"position": "  au_specialist  "}) == "au_specialist"
    assert up._position_from_payload({"position": ""}) is None
    assert up._position_from_payload({}) is None


@pytest.mark.asyncio
async def test_build_user_public_reads_gid_number(sqlite_session: AsyncSession) -> None:
    payload = {
        "sub": "gid-sub-1",
        "email": "g@example.com",
        "name": "Gid User",
        "preferred_username": "gid",
        "groups": ["outstaff"],
        "gid_number": "10000",
    }
    user = await up.build_user_public(sqlite_session, payload, groups_claim_path="groups")
    assert user.gid_number == "10000"
    row = (
        await sqlite_session.execute(select(PortalUserProfile).where(PortalUserProfile.sub == "gid-sub-1"))
    ).scalar_one()
    assert row.gid_number == "10000"


@pytest.mark.asyncio
async def test_build_user_public_persists_profile(sqlite_session: AsyncSession) -> None:
    payload = {
        "sub": "prof-sub-1",
        "email": "e@example.com",
        "name": "Visible Name",
        "preferred_username": "vis",
        "groups": [],
    }
    user = await up.build_user_public(sqlite_session, payload, groups_claim_path="groups")
    assert user.sub == "prof-sub-1"
    assert user.username == "vis"
    assert user.full_name == "Visible Name"

    row = (
        await sqlite_session.execute(select(PortalUserProfile).where(PortalUserProfile.sub == "prof-sub-1"))
    ).scalar_one()
    assert row.email == "e@example.com"
    assert row.full_name == "Visible Name"


@pytest.mark.asyncio
async def test_build_user_public_avatar_uses_ea_proxy_url(sqlite_session: AsyncSession) -> None:
    """build_user_public собирает signed proxy URL фото EA."""
    payload = {"sub": "admin-sub", "email": "admin@example.com", "groups": []}
    with patch(
        "app.services.user_profile.build_user_photo_proxy_url",
        return_value="/api/v1/portal/users/admin-sub/photo?exp=1&sig=a",
    ) as b:
        user = await up.build_user_public(sqlite_session, payload, groups_claim_path="groups")

    assert user.avatar_url and user.avatar_url.startswith("/api/v1/portal/users/")
    b.assert_called_once()


@pytest.mark.asyncio
async def test_upsert_finds_existing_profile_by_email_when_sub_changes(sqlite_session: AsyncSession) -> None:
    """При смене sub на стороне SSO профиль находится по email, дубль не создаётся."""
    old_sub = "old-keycloak-uuid"
    new_sub = "new-sso-uuid-v1"
    email = "sso-fallback-test@example.com"

    # Создаём профиль со старым sub
    old_payload = {
        "sub": old_sub,
        "email": email,
        "name": "User Name",
        "preferred_username": "username",
        "groups": [],
    }
    user_old = await up.build_user_public(sqlite_session, old_payload, groups_claim_path="groups")
    assert user_old.sub == old_sub

    # Логин с новым sub (тот же email)
    new_payload = {
        "sub": new_sub,
        "email": email,
        "name": "User Name",
        "preferred_username": "username",
        "groups": [],
    }
    user_new = await up.build_user_public(sqlite_session, new_payload, groups_claim_path="groups")

    # Должен вернуться старый canonical sub, а не новый
    assert user_new.sub == old_sub

    # В БД по-прежнему один профиль с этим email
    rows = (
        (await sqlite_session.execute(select(PortalUserProfile).where(PortalUserProfile.email == email)))
        .scalars()
        .all()
    )
    assert len(rows) == 1
    assert rows[0].sub == old_sub


@pytest.mark.asyncio
async def test_email_remap_without_field_changes_skips_commit(sqlite_session: AsyncSession) -> None:
    """Повторный логин с другим SSO sub и теми же полями не должен писать в БД."""
    old_sub = "stable-uuid-sub"
    email = "remap-nochang@example.com"
    await up.build_user_public(
        sqlite_session,
        {
            "sub": old_sub,
            "email": email,
            "name": "Same Name",
            "preferred_username": "same",
            "groups": [],
        },
        groups_claim_path="groups",
    )
    row = await sqlite_session.get(PortalUserProfile, old_sub)
    assert row is not None
    updated_before = row.updated_at

    user = await up.build_user_public(
        sqlite_session,
        {
            "sub": "email-as-sub@example.com",
            "email": email,
            "name": "Same Name",
            "preferred_username": "same",
            "groups": [],
        },
        groups_claim_path="groups",
    )
    assert user.sub == old_sub
    row2 = await sqlite_session.get(PortalUserProfile, old_sub)
    assert row2 is not None
    assert row2.updated_at == updated_before


@pytest.mark.asyncio
async def test_sso_alias_skips_email_lookup_on_second_token(sqlite_session: AsyncSession) -> None:
    """После первого remap email→UUID повтор с новым JWT-sub идёт через alias без дубля."""
    email = "alias-cache@example.com"
    await up.build_user_public(
        sqlite_session,
        {"sub": "canon-uuid-1", "email": email, "name": "A", "preferred_username": "a", "groups": []},
        groups_claim_path="groups",
    )
    u1 = await up.build_user_public(
        sqlite_session,
        {"sub": "first-email-token@example.com", "email": email, "name": "A", "preferred_username": "a", "groups": []},
        groups_claim_path="groups",
    )
    assert u1.sub == "canon-uuid-1"
    assert up._sso_canonical_sub_by_alias.get(email) == "canon-uuid-1"

    u2 = await up.build_user_public(
        sqlite_session,
        {"sub": "second-email-token@example.com", "email": email, "name": "A", "preferred_username": "a", "groups": []},
        groups_claim_path="groups",
    )
    assert u2.sub == "canon-uuid-1"
    assert up._sso_canonical_sub_by_alias.get("second-email-token@example.com") == "canon-uuid-1"


@pytest.mark.asyncio
async def test_build_user_public_syncs_specialist_sso_fields(sqlite_session: AsyncSession) -> None:
    payload = {
        "sub": "spec-sso-1",
        "email": "pupkin@example.com",
        "name": "Pupkin Ivan",
        "preferred_username": "pupkin",
        "groups": ["students"],
        "telegram": "https://t.me/dontgoingforyou",
        "birthday": "1998-06-20",
    }
    await up.build_user_public(sqlite_session, payload, groups_claim_path="groups")
    profile = await sqlite_session.get(PortalSpecialistProfile, "spec-sso-1")
    assert profile is not None
    assert profile.telegram == "https://t.me/dontgoingforyou"
    assert profile.birthdate == date(1998, 6, 20)


@pytest.mark.asyncio
async def test_build_user_public_admin_group_sets_flag(sqlite_session: AsyncSession) -> None:
    user = await up.build_user_public(
        sqlite_session,
        {
            "sub": "admin-from-sso",
            "email": "adm@example.com",
            "preferred_username": "adm",
            "groups": [IDP_GROUP_PORTAL_ADMIN],
        },
        groups_claim_path="groups",
    )
    assert user.is_portal_admin is True
    row = await sqlite_session.get(PortalUserProfile, "admin-from-sso")
    assert row is not None
    assert row.is_portal_admin is True


@pytest.mark.asyncio
async def test_build_user_public_timesheet_only_flags(sqlite_session: AsyncSession) -> None:
    await up.build_user_public(
        sqlite_session,
        {
            "sub": "au-spec-sub",
            "email": "spec@example.com",
            "preferred_username": "spec",
            "groups": ["students"],
            "position": "au_specialist",
        },
        groups_claim_path="groups",
    )
    row = await sqlite_session.get(PortalUserProfile, "au-spec-sub")
    assert row is not None
    assert row.portal_chat_allowed is False
    assert row.is_developer is True


@pytest.mark.asyncio
async def test_build_user_public_updates_changed_fields(sqlite_session: AsyncSession) -> None:
    await up.build_user_public(
        sqlite_session,
        {
            "sub": "chg-sub",
            "email": "old@example.com",
            "name": "Old Name",
            "preferred_username": "old",
            "groups": [],
        },
        groups_claim_path="groups",
    )
    row = await sqlite_session.get(PortalUserProfile, "chg-sub")
    assert row is not None
    before = row.updated_at
    await up.build_user_public(
        sqlite_session,
        {
            "sub": "chg-sub",
            "email": "new@example.com",
            "name": "New Name",
            "preferred_username": "new",
            "groups": [],
        },
        groups_claim_path="groups",
    )
    row2 = await sqlite_session.get(PortalUserProfile, "chg-sub")
    assert row2 is not None
    assert row2.email == "new@example.com"
    assert row2.full_name == "New Name"
    assert row2.updated_at != before


@pytest.mark.asyncio
async def test_invalid_specialist_sso_fields_do_not_overwrite(sqlite_session: AsyncSession) -> None:
    await up.build_user_public(
        sqlite_session,
        {
            "sub": "keep-spec",
            "email": "keep@example.com",
            "preferred_username": "keep",
            "groups": [],
            "telegram": "https://t.me/keepmeok",
            "birthday": "1998-06-20",
        },
        groups_claim_path="groups",
    )
    await up.build_user_public(
        sqlite_session,
        {
            "sub": "keep-spec",
            "email": "keep@example.com",
            "preferred_username": "keep",
            "groups": [],
            "telegram": "!!!not-a-handle",
            "birthday": "not-a-date",
        },
        groups_claim_path="groups",
    )
    profile = await sqlite_session.get(PortalSpecialistProfile, "keep-spec")
    assert profile is not None
    assert profile.telegram == "https://t.me/keepmeok"
    assert profile.birthdate == date(1998, 6, 20)
