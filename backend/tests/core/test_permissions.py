from __future__ import annotations

import pytest
from app.api.deps_auth import require_portal_manager_or_admin
from app.core.auth_constants import (
    IDP_GROUP_DEVELOPER,
    IDP_GROUP_MANAGER,
    IDP_GROUP_OUTSTAFF,
    SSO_GID_OUTSTAFF,
    SSO_POSITION_AU_SPECIALIST,
    SSO_POSITION_STUDENT,
    normalize_sso_gid_number,
)
from app.core.exceptions import ForbiddenError
from app.core.permissions import is_manager_or_admin, is_timesheet_only, require_manager_or_admin
from app.schemas.auth import UserPublic


def _user(
    *,
    idp_groups: list[str],
    is_portal_admin: bool = False,
    position: str | None = None,
    gid_number: str | None = None,
) -> UserPublic:
    return UserPublic(
        sub="test-sub",
        email="t@example.com",
        username="test",
        full_name="Test",
        idp_groups=idp_groups,
        is_portal_admin=is_portal_admin,
        position=position,
        gid_number=gid_number,
    )


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("10000", "10000"),
        (" 10000 ", "10000"),
        (10000, "10000"),
        (10001, "10001"),
        ("", None),
        (None, None),
        (True, None),
        (False, None),
    ],
)
def test_normalize_sso_gid_number(raw: object, expected: str | None) -> None:
    assert normalize_sso_gid_number(raw) == expected


@pytest.mark.parametrize(
    ("idp_groups", "position", "is_portal_admin", "gid_number", "expected"),
    [
        ([IDP_GROUP_DEVELOPER], SSO_POSITION_STUDENT, False, None, True),
        ([IDP_GROUP_DEVELOPER, IDP_GROUP_MANAGER], SSO_POSITION_AU_SPECIALIST, False, SSO_GID_OUTSTAFF, True),
        ([IDP_GROUP_DEVELOPER, IDP_GROUP_MANAGER], "au_chief", False, SSO_GID_OUTSTAFF, False),
        ([IDP_GROUP_DEVELOPER], None, False, None, True),
        ([IDP_GROUP_DEVELOPER, IDP_GROUP_MANAGER], None, False, SSO_GID_OUTSTAFF, False),
        ([], SSO_POSITION_AU_SPECIALIST, False, SSO_GID_OUTSTAFF, True),
        ([IDP_GROUP_MANAGER], SSO_POSITION_AU_SPECIALIST, False, SSO_GID_OUTSTAFF, True),
        ([IDP_GROUP_DEVELOPER], SSO_POSITION_STUDENT, True, None, False),
        ([IDP_GROUP_DEVELOPER, IDP_GROUP_MANAGER], "au_chief", False, "10001", True),
        ([], None, False, None, False),
        ([IDP_GROUP_OUTSTAFF], None, False, None, False),
    ],
)
def test_is_timesheet_only(
    idp_groups: list[str],
    position: str | None,
    is_portal_admin: bool,
    gid_number: str | None,
    expected: bool,
) -> None:
    user = _user(
        idp_groups=idp_groups,
        position=position,
        is_portal_admin=is_portal_admin,
        gid_number=gid_number,
    )
    assert is_timesheet_only(user) is expected


@pytest.mark.parametrize(
    ("idp_groups", "position", "is_portal_admin", "gid_number", "expected"),
    [
        ([IDP_GROUP_MANAGER], "au_chief", False, SSO_GID_OUTSTAFF, True),
        ([], "au_chief", False, SSO_GID_OUTSTAFF, True),
        ([IDP_GROUP_MANAGER], "au_chief", False, "10001", False),
        ([IDP_GROUP_MANAGER], "au_chief", False, None, False),
        ([IDP_GROUP_MANAGER], SSO_POSITION_AU_SPECIALIST, False, SSO_GID_OUTSTAFF, False),
        ([IDP_GROUP_DEVELOPER, IDP_GROUP_MANAGER], "au_chief", False, SSO_GID_OUTSTAFF, True),
        ([IDP_GROUP_DEVELOPER, IDP_GROUP_MANAGER], SSO_POSITION_AU_SPECIALIST, False, SSO_GID_OUTSTAFF, False),
        ([], None, True, None, True),
        ([IDP_GROUP_DEVELOPER], None, False, None, False),
    ],
)
def test_is_manager_or_admin(
    idp_groups: list[str],
    position: str | None,
    is_portal_admin: bool,
    gid_number: str | None,
    expected: bool,
) -> None:
    user = _user(
        idp_groups=idp_groups,
        position=position,
        is_portal_admin=is_portal_admin,
        gid_number=gid_number,
    )
    assert is_manager_or_admin(user) is expected


def test_require_manager_or_admin_raises_default_and_custom() -> None:
    user = _user(idp_groups=[IDP_GROUP_DEVELOPER])
    with pytest.raises(ForbiddenError, match="менеджера или администратора"):
        require_manager_or_admin(user)
    with pytest.raises(ForbiddenError, match="только отчёт"):
        require_manager_or_admin(user, detail="только отчёт")


def test_require_manager_or_admin_passes_admin_and_manager() -> None:
    admin = _user(idp_groups=[], is_portal_admin=True)
    assert require_manager_or_admin(admin) is None
    manager = _user(idp_groups=[], gid_number=SSO_GID_OUTSTAFF)
    assert require_manager_or_admin(manager) is None


@pytest.mark.asyncio
async def test_require_portal_manager_or_admin_dep() -> None:
    admin = _user(idp_groups=[], is_portal_admin=True)
    assert await require_portal_manager_or_admin(admin) is admin
    manager = _user(idp_groups=[], gid_number=SSO_GID_OUTSTAFF)
    assert await require_portal_manager_or_admin(manager) is manager
    denied = _user(idp_groups=[IDP_GROUP_DEVELOPER])
    with pytest.raises(ForbiddenError, match="Требуется роль менеджера или администратора портала"):
        await require_portal_manager_or_admin(denied)
