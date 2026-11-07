"""RBAC / 401 / timesheet 403: матрица REST portal_tags."""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from tests.portal_tags.conftest import TAGS_API, assert_api_error

_AUTH_UUID = "00000000-0000-4000-8000-000000000001"


def _create_body() -> dict[str, str]:
    return {"name": "X", "color": "#445566"}


@pytest.mark.parametrize(
    ("method", "path", "kwargs"),
    [
        ("GET", TAGS_API, {}),
        ("POST", TAGS_API, {"json": _create_body()}),
        ("PATCH", f"{TAGS_API}/{_AUTH_UUID}", {"json": {"expected_version": 1, "color": "#445566"}}),
        ("DELETE", f"{TAGS_API}/{_AUTH_UUID}", {}),
    ],
)
async def test_tags_require_auth(
    client_sqlite_only: AsyncClient,
    method: str,
    path: str,
    kwargs: dict[str, object],
) -> None:
    r = await client_sqlite_only.request(method, path, **kwargs)
    assert_api_error(r, 401, "unauthorized")


@pytest.mark.parametrize(
    ("method", "path", "kwargs"),
    [
        ("GET", TAGS_API, {}),
        ("POST", TAGS_API, {"json": _create_body()}),
        ("PATCH", f"{TAGS_API}/{_AUTH_UUID}", {"json": {"expected_version": 1, "color": "#445566"}}),
        ("DELETE", f"{TAGS_API}/{_AUTH_UUID}", {}),
    ],
)
async def test_tags_timesheet_forbidden(
    client_developer: AsyncClient,
    method: str,
    path: str,
    kwargs: dict[str, object],
) -> None:
    r = await client_developer.request(method, path, **kwargs)
    assert_api_error(r, 403, "forbidden")


@pytest.mark.parametrize(
    ("method", "path", "kwargs"),
    [
        ("POST", TAGS_API, {"json": {"name": "ЮзерТег", "color": "#FF00FF"}}),
        ("PATCH", f"{TAGS_API}/{_AUTH_UUID}", {"json": {"expected_version": 1, "color": "#00FF00"}}),
        ("DELETE", f"{TAGS_API}/{_AUTH_UUID}", {}),
    ],
)
async def test_tags_mutations_forbidden_without_manager_role(
    client_no_idp: AsyncClient,
    method: str,
    path: str,
    kwargs: dict[str, object],
) -> None:
    r = await client_no_idp.request(method, path, **kwargs)
    assert_api_error(r, 403, "forbidden")
    if method == "POST":
        assert "менеджера или администратора" in r.json()["message"]


async def test_tags_outstaff_without_gid_cannot_mutate(
    client_outstaff_not_manager: AsyncClient,
) -> None:
    r = await client_outstaff_not_manager.post(TAGS_API, json={"name": "НеМенеджер", "color": "#445566"})
    assert_api_error(r, 403, "forbidden")


async def test_tags_mutations_forbidden_on_existing_tag(
    client_no_idp: AsyncClient,
    sqlite_session: AsyncSession,
) -> None:
    from app.schemas.tags import PortalTagCreate
    from app.services.portal_tags import create_tag

    tag = await create_tag(sqlite_session, PortalTagCreate(name="ЧужойТег", color="#445566"))
    tid = str(tag.id)
    assert_api_error(
        await client_no_idp.patch(
            f"{TAGS_API}/{tid}",
            json={"expected_version": tag.version, "color": "#00FF00"},
        ),
        403,
        "forbidden",
    )
    assert_api_error(await client_no_idp.delete(f"{TAGS_API}/{tid}"), 403, "forbidden")
