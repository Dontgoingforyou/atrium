"""HTTP-контракт тегов: CRUD, валидация, конфликты."""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from tests.portal_tags.conftest import TAGS_API, assert_api_error, assert_pydantic_422

# Фиксированные UUID для parametrize и 404 — иначе xdist собирает разные node id на воркерах.
_UNKNOWN_TAG_ID = "00000000-0000-4000-8000-000000000001"
_PATCH_VALIDATE_NAME_TAG_ID = "00000000-0000-4000-8000-000000000002"
_PATCH_VALIDATE_COLOR_TAG_ID = "00000000-0000-4000-8000-000000000003"


@pytest.mark.parametrize(
    ("first", "second"),
    [
        ("Важно", "важно"),
        ("Важно", "Важно "),
        ("важно", "  ВАЖНО  "),
    ],
)
async def test_create_tag_with_duplicate_name_returns_409(
    client_admin: AsyncClient,
    first: str,
    second: str,
) -> None:
    r1 = await client_admin.post(TAGS_API, json={"name": first, "color": "#445566"})
    assert r1.status_code == 201, r1.text
    assert r1.json()["slug"]
    r2 = await client_admin.post(TAGS_API, json={"name": second, "color": "#445566"})
    assert_api_error(r2, 409, "conflict")
    assert "уже существует" in r2.json()["message"]


async def test_update_tag_to_existing_name_returns_409(client_admin: AsyncClient) -> None:
    await client_admin.post(TAGS_API, json={"name": "УникальныйА", "color": "#445566"})
    b = (await client_admin.post(TAGS_API, json={"name": "УникальныйБ", "color": "#445566"})).json()
    r = await client_admin.patch(
        f"{TAGS_API}/{b['id']}",
        json={"expected_version": b["version"], "name": "УникальныйА"},
    )
    assert_api_error(r, 409, "conflict")
    assert "уже существует" in r.json()["message"]


async def test_delete_unknown_tag_returns_404(client_admin: AsyncClient) -> None:
    r = await client_admin.delete(f"{TAGS_API}/{_UNKNOWN_TAG_ID}")
    assert_api_error(r, 404, "not_found")
    assert "не найден" in r.json()["message"].lower()


async def test_delete_tag_in_use_returns_409(client_admin: AsyncClient) -> None:
    tag = (await client_admin.post(TAGS_API, json={"name": "НаДокументе", "color": "#AABBCC"})).json()
    doc = await client_admin.post(
        "/api/v1/admin/portal-documents",
        json={
            "title": "С тегом",
            "body": "",
            "tag_ids": [tag["id"]],
        },
    )
    assert doc.status_code == 201, doc.text
    r = await client_admin.delete(f"{TAGS_API}/{tag['id']}")
    assert_api_error(r, 409, "conflict")
    assert "используется" in r.json()["message"]


async def test_delete_tag_in_use_by_task_returns_409(client_admin: AsyncClient) -> None:
    tag = (await client_admin.post(TAGS_API, json={"name": "НаЗадаче", "color": "#AABBCC"})).json()
    task = await client_admin.post(
        "/api/v1/portal/tasks",
        json={"title": "С тегом", "tag_ids": [tag["id"]], "assignee_sub": "admin-sub"},
    )
    assert task.status_code == 201, task.text
    r = await client_admin.delete(f"{TAGS_API}/{tag['id']}")
    assert_api_error(r, 409, "conflict")
    assert "используется" in r.json()["message"]


async def test_update_unknown_tag_returns_404(client_admin: AsyncClient) -> None:
    r = await client_admin.patch(
        f"{TAGS_API}/{_UNKNOWN_TAG_ID}",
        json={"expected_version": 1, "color": "#445566"},
    )
    assert_api_error(r, 404, "not_found")


async def test_tags_mutations_allowed_for_manager(client_manager: AsyncClient) -> None:
    """Менеджер (outstaff) может создавать, менять и удалять теги."""
    r_create = await client_manager.post(TAGS_API, json={"name": "МенеджерТег", "color": "#AABBCC"})
    assert r_create.status_code == 201, r_create.text
    body = r_create.json()
    tid = body["id"]
    assert body["slug"]

    r_patch = await client_manager.patch(
        f"{TAGS_API}/{tid}",
        json={"expected_version": body["version"], "color": "#445566"},
    )
    assert r_patch.status_code == 200
    assert r_patch.json()["color"] == "#445566"

    r_del = await client_manager.delete(f"{TAGS_API}/{tid}")
    assert r_del.status_code == 204


async def test_list_tags_sorted_by_name(client_admin: AsyncClient) -> None:
    z = (await client_admin.post(TAGS_API, json={"name": "ЯТегСписок", "color": "#A1B2C3"})).json()
    a = (await client_admin.post(TAGS_API, json={"name": "АТегСписок", "color": "#B2C3D4"})).json()

    r = await client_admin.get(TAGS_API, params={"skip": 0, "limit": 500})
    assert r.status_code == 200
    items = r.json()
    ids = [t["id"] for t in items]
    assert ids.index(a["id"]) < ids.index(z["id"])
    found = next(t for t in items if t["id"] == z["id"])
    assert found["name"] == "ЯТегСписок"
    assert found["color"] == "#A1B2C3"
    assert found["slug"]
    assert z["slug"]


async def test_list_tags_readable_by_non_manager(
    client_no_idp: AsyncClient,
    sqlite_session: AsyncSession,
) -> None:
    from app.schemas.tags import PortalTagCreate
    from app.services.portal_tags import create_tag

    tag = await create_tag(sqlite_session, PortalTagCreate(name="ОбщийТег", color="#A1B2C3"))
    r = await client_no_idp.get(TAGS_API)
    assert r.status_code == 200
    assert str(tag.id) in {t["id"] for t in r.json()}


async def test_patch_tag_rename_updates_slug(client_admin: AsyncClient) -> None:
    created = (await client_admin.post(TAGS_API, json={"name": "СтароеИмя", "color": "#445566"})).json()
    old_slug = created["slug"]
    r = await client_admin.patch(
        f"{TAGS_API}/{created['id']}",
        json={"expected_version": created["version"], "name": "Новое Имя"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["name"] == "Новое Имя"
    assert body["slug"] != old_slug
    assert body["slug"].startswith("novoe-imia")


async def test_create_tag_white_color_accepted(client_admin: AsyncClient) -> None:
    """Белый допустим на API — theme-aware проверка на фронте."""
    r = await client_admin.post(TAGS_API, json={"name": "БелыйТег", "color": "#FFFFFF"})
    assert r.status_code == 201, r.text
    assert r.json()["color"] == "#FFFFFF"


@pytest.mark.parametrize(
    ("method", "path", "kwargs"),
    [
        ("POST", TAGS_API, {"json": {"name": "ПлохойЦвет", "color": "#GGGGGG"}}),
        ("POST", TAGS_API, {"json": {"name": "   ", "color": "#445566"}}),
        ("PATCH", f"{TAGS_API}/{_PATCH_VALIDATE_NAME_TAG_ID}", {"json": {"name": "   "}}),
        ("PATCH", f"{TAGS_API}/{_PATCH_VALIDATE_COLOR_TAG_ID}", {"json": {"color": "#GGGGGG"}}),
    ],
)
async def test_tags_validation_returns_422(
    client_admin: AsyncClient,
    method: str,
    path: str,
    kwargs: dict[str, object],
) -> None:
    r = await client_admin.request(method, path, **kwargs)
    assert_pydantic_422(r)


@pytest.mark.parametrize(
    ("params",),
    [
        ({"skip": -1},),
        ({"limit": 0},),
        ({"limit": 501},),
    ],
)
async def test_list_tags_pagination_422(
    client_admin: AsyncClient,
    params: dict[str, int],
) -> None:
    assert_pydantic_422(await client_admin.get(TAGS_API, params=params))
