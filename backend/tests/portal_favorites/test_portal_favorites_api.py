"""HTTP-контракт избранного: RBAC, изоляция, корзина, пагинация после JOIN."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from app.core.enums import FavoriteTargetType
from app.infrastructure.db.models.portal_document import PortalDocument
from app.infrastructure.db.models.portal_favorite import PortalFavorite
from httpx import AsyncClient, Response
from sqlalchemy.ext.asyncio import AsyncSession

from tests.portal_documents.conftest import DOCS_ADMIN, create_doc
from tests.portal_favorites.conftest import FAV_API, as_user_b, as_user_regular, assert_api_error

_AUTH_UUID = "00000000-0000-4000-8000-000000000001"


def _fav_body(document_id: str) -> dict[str, str]:
    return {"target_type": "document", "target_id": document_id}


def assert_pydantic_422(response: Response) -> None:
    assert response.status_code == 422, response.text
    assert "detail" in response.json()


@pytest.mark.parametrize(
    ("method", "path", "kwargs"),
    [
        ("GET", FAV_API, {}),
        ("POST", FAV_API, {"json": _fav_body(_AUTH_UUID)}),
        ("DELETE", f"{FAV_API}/{_AUTH_UUID}", {}),
    ],
)
async def test_favorites_require_auth(
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
        ("GET", FAV_API, {}),
        ("POST", FAV_API, {"json": _fav_body(_AUTH_UUID)}),
        ("DELETE", f"{FAV_API}/{_AUTH_UUID}", {}),
    ],
)
async def test_timesheet_forbidden_on_favorites(
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
        ("POST", FAV_API, {"json": {}}),
        ("POST", FAV_API, {"json": {"target_type": "foo", "target_id": _AUTH_UUID}}),
        ("POST", FAV_API, {"json": {"target_type": "document", "target_id": "not-a-uuid"}}),
        ("GET", FAV_API, {"params": {"limit": 0}}),
        ("GET", FAV_API, {"params": {"limit": 501}}),
        ("GET", FAV_API, {"params": {"skip": -1}}),
        ("DELETE", f"{FAV_API}/not-a-uuid", {}),
    ],
)
async def test_favorites_validation_returns_422(
    client_user: AsyncClient,
    method: str,
    path: str,
    kwargs: dict[str, object],
) -> None:
    r = await client_user.request(method, path, **kwargs)
    assert_pydantic_422(r)


async def test_regular_user_add_list_delete_and_readd(client_admin: AsyncClient) -> None:
    doc = await create_doc(client_admin, title="Док для избранного")
    with as_user_regular():
        r = await client_admin.post(FAV_API, json=_fav_body(doc["id"]))
        assert r.status_code == 201, r.text
        fav = r.json()
        assert fav["target_type"] == "document"
        assert fav["target_id"] == doc["id"]
        assert fav["title"] == "Док для избранного"
        assert "created_at" in fav

        r = await client_admin.get(FAV_API)
        assert r.status_code == 200
        items = r.json()
        assert len(items) == 1
        assert items[0]["id"] == fav["id"]

        r = await client_admin.delete(f"{FAV_API}/{fav['id']}")
        assert r.status_code == 204

        r = await client_admin.get(FAV_API)
        assert r.json() == []

        r = await client_admin.post(FAV_API, json=_fav_body(doc["id"]))
        assert r.status_code == 201, r.text
        r = await client_admin.get(FAV_API)
        assert len(r.json()) == 1


async def test_list_is_isolated_and_same_document_can_be_starred_by_two_users(
    client_admin: AsyncClient,
) -> None:
    doc = await create_doc(client_admin, title="Общий документ")
    body = _fav_body(doc["id"])
    with as_user_regular():
        r = await client_admin.post(FAV_API, json=body)
        assert r.status_code == 201, r.text
        a_id = r.json()["id"]
    with as_user_b():
        r = await client_admin.get(FAV_API)
        assert r.status_code == 200
        assert r.json() == []
        r = await client_admin.post(FAV_API, json=body)
        assert r.status_code == 201, r.text
        b_id = r.json()["id"]
        items = (await client_admin.get(FAV_API)).json()
        assert [item["id"] for item in items] == [b_id]
    with as_user_regular():
        items = (await client_admin.get(FAV_API)).json()
        assert [item["id"] for item in items] == [a_id]


async def test_add_duplicate_favorite_returns_409(client_admin: AsyncClient) -> None:
    doc = await create_doc(client_admin, title="Дубль избранного")
    body = _fav_body(doc["id"])
    r = await client_admin.post(FAV_API, json=body)
    assert r.status_code == 201
    r = await client_admin.post(FAV_API, json=body)
    assert_api_error(r, 409, "conflict")


async def test_add_unknown_document_returns_404(client_admin: AsyncClient) -> None:
    r = await client_admin.post(FAV_API, json=_fav_body(str(uuid.uuid4())))
    assert_api_error(r, 404, "not_found")


async def test_add_navigation_node_returns_404(client_admin: AsyncClient) -> None:
    r = await client_admin.post(
        FAV_API,
        json={"target_type": "navigation_node", "target_id": str(uuid.uuid4())},
    )
    assert_api_error(r, 404, "not_found")


async def test_delete_missing_favorite_returns_404(client_admin: AsyncClient) -> None:
    r = await client_admin.delete(f"{FAV_API}/{uuid.uuid4()}")
    assert_api_error(r, 404, "not_found")


async def test_delete_other_users_favorite_returns_404(client_admin: AsyncClient) -> None:
    doc = await create_doc(client_admin, title="Чужое избранное")
    with as_user_b():
        r = await client_admin.post(FAV_API, json=_fav_body(doc["id"]))
        assert r.status_code == 201, r.text
        foreign_id = r.json()["id"]

    r = await client_admin.delete(f"{FAV_API}/{foreign_id}")
    assert_api_error(r, 404, "not_found")

    with as_user_b():
        r = await client_admin.get(FAV_API)
        assert r.status_code == 200
        assert any(item["id"] == foreign_id for item in r.json())


async def test_add_favorite_deleted_document_returns_404(client_admin: AsyncClient) -> None:
    doc = await create_doc(client_admin, title="Удалённый документ")
    r = await client_admin.delete(f"{DOCS_ADMIN}/{doc['id']}")
    assert r.status_code == 204
    r = await client_admin.post(FAV_API, json=_fav_body(doc["id"]))
    assert_api_error(r, 404, "not_found")


async def test_list_skips_deleted_and_nav_node_in_limit_and_skip(
    client_user: AsyncClient,
    sqlite_session: AsyncSession,
) -> None:
    """LIMIT/OFFSET после JOIN: дыры не вытесняют живые и не считаются в skip."""
    now = datetime.now(UTC)
    live_old = PortalDocument(title="Живой старше", author_sub="user-sub", body="x")
    live_new = PortalDocument(title="Живой новее", author_sub="user-sub", body="x")
    deleted_a = PortalDocument(title="Корзина A", author_sub="user-sub", body="x", deleted_at=now)
    deleted_b = PortalDocument(title="Корзина B", author_sub="user-sub", body="x", deleted_at=now)
    sqlite_session.add_all([live_old, live_new, deleted_a, deleted_b])
    await sqlite_session.commit()
    await sqlite_session.refresh(live_old)
    await sqlite_session.refresh(live_new)
    await sqlite_session.refresh(deleted_a)
    await sqlite_session.refresh(deleted_b)

    sqlite_session.add_all(
        [
            PortalFavorite(
                user_sub="user-sub",
                target_type=FavoriteTargetType.DOCUMENT.value,
                target_id=live_old.id,
                created_at=now - timedelta(hours=4),
            ),
            PortalFavorite(
                user_sub="user-sub",
                target_type=FavoriteTargetType.DOCUMENT.value,
                target_id=live_new.id,
                created_at=now - timedelta(hours=2),
            ),
            PortalFavorite(
                user_sub="user-sub",
                target_type=FavoriteTargetType.DOCUMENT.value,
                target_id=deleted_a.id,
                created_at=now - timedelta(hours=1),
            ),
            PortalFavorite(
                user_sub="user-sub",
                target_type=FavoriteTargetType.NAVIGATION_NODE.value,
                target_id=uuid.uuid4(),
                created_at=now - timedelta(minutes=30),
            ),
            PortalFavorite(
                user_sub="user-sub",
                target_type=FavoriteTargetType.DOCUMENT.value,
                target_id=deleted_b.id,
                created_at=now,
            ),
        ]
    )
    await sqlite_session.commit()

    r = await client_user.get(FAV_API, params={"limit": 1})
    assert r.status_code == 200, r.text
    items = r.json()
    assert len(items) == 1
    assert items[0]["target_id"] == str(live_new.id)
    assert items[0]["title"] == "Живой новее"

    r = await client_user.get(FAV_API, params={"skip": 1, "limit": 1})
    assert r.status_code == 200, r.text
    items = r.json()
    assert len(items) == 1
    assert items[0]["target_id"] == str(live_old.id)
    assert items[0]["title"] == "Живой старше"


async def test_list_title_follows_document_rename(client_admin: AsyncClient) -> None:
    doc = await create_doc(client_admin, title="Старое имя")
    r = await client_admin.post(FAV_API, json=_fav_body(doc["id"]))
    assert r.status_code == 201, r.text

    r = await client_admin.patch(
        f"{DOCS_ADMIN}/{doc['id']}",
        json={"expected_version": doc["version"], "title": "Новое имя"},
    )
    assert r.status_code == 200, r.text

    r = await client_admin.get(FAV_API)
    assert r.status_code == 200
    items = r.json()
    assert len(items) == 1
    assert items[0]["target_id"] == doc["id"]
    assert items[0]["title"] == "Новое имя"


async def test_soft_delete_then_restore_keeps_favorite(client_admin: AsyncClient) -> None:
    doc = await create_doc(client_admin, title="В корзину со звездой")
    r = await client_admin.post(FAV_API, json=_fav_body(doc["id"]))
    assert r.status_code == 201, r.text
    fav_id = r.json()["id"]

    r = await client_admin.delete(f"{DOCS_ADMIN}/{doc['id']}")
    assert r.status_code == 204

    r = await client_admin.get(FAV_API)
    assert r.status_code == 200
    assert all(item["id"] != fav_id for item in r.json())

    r = await client_admin.post(f"{DOCS_ADMIN}/{doc['id']}/restore")
    assert r.status_code == 200, r.text

    r = await client_admin.get(FAV_API)
    assert r.status_code == 200
    assert any(item["id"] == fav_id and item["target_id"] == doc["id"] for item in r.json())


async def test_purge_parent_removes_subtree_favorites_keeps_neighbor(
    client_admin: AsyncClient,
) -> None:
    parent = await create_doc(client_admin, title="Корень со звёздами")
    child = await create_doc(client_admin, title="Потомок со звездой", parent_document_id=parent["id"])
    neighbor = await create_doc(client_admin, title="Сосед со звездой")

    for doc in (parent, child, neighbor):
        r = await client_admin.post(FAV_API, json=_fav_body(doc["id"]))
        assert r.status_code == 201, r.text

    r = await client_admin.delete(f"{DOCS_ADMIN}/{parent['id']}/purge")
    assert r.status_code == 204, r.text

    r = await client_admin.get(FAV_API)
    assert r.status_code == 200
    items = r.json()
    assert [item["target_id"] for item in items] == [neighbor["id"]]
    assert items[0]["title"] == "Сосед со звездой"
