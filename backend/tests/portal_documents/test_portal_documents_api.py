"""HTTP-контракт документов: CRUD, корзина, reorder, duplicate, история."""

from __future__ import annotations

import io
import uuid
from unittest.mock import AsyncMock, patch

from httpx import AsyncClient

from tests.portal_documents.conftest import DOCS_ADMIN, DOCS_API, assert_api_error, create_doc, post_tag

_PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32


async def test_create_and_get_document(client_admin: AsyncClient) -> None:
    doc = await create_doc(client_admin, title="Регламент онбординга")
    assert doc["title"] == "Регламент онбординга"
    assert "document_type" not in doc
    assert "status" not in doc
    assert doc["author_sub"] == "admin-sub"
    assert doc["author_email"] == "admin@example.com"

    r = await client_admin.get(f"{DOCS_API}/documents/{doc['id']}")
    assert r.status_code == 200
    assert r.json()["id"] == doc["id"]
    assert r.json()["body"] == "Тело документа"


async def test_list_documents_contains_created(client_admin: AsyncClient) -> None:
    a = await create_doc(client_admin, title="Первый-уник-list")
    b = await create_doc(client_admin, title="Второй-уник-list")
    r = await client_admin.get(f"{DOCS_API}/documents")
    assert r.status_code == 200
    data = r.json()
    ids = {item["id"] for item in data["items"]}
    assert a["id"] in ids
    assert b["id"] in ids
    assert data["total"] >= 2


async def test_list_documents_skip_limit(client_admin: AsyncClient) -> None:
    created = [await create_doc(client_admin, title=f"Страница-уник-{i}") for i in range(3)]
    first = await client_admin.get(f"{DOCS_API}/documents?skip=0&limit=2")
    assert first.status_code == 200
    assert len(first.json()["items"]) == 2
    first_ids = [item["id"] for item in first.json()["items"]]

    second = await client_admin.get(f"{DOCS_API}/documents?skip=2&limit=2")
    assert second.status_code == 200
    second_ids = [item["id"] for item in second.json()["items"]]
    assert not set(first_ids) & set(second_ids)
    created_ids = {d["id"] for d in created}
    assert created_ids & set(first_ids + second_ids)


async def test_filter_documents_by_tag_and_owner(client_admin: AsyncClient) -> None:
    tag = await post_tag(client_admin, name="filter-tag")
    with_tag = await create_doc(client_admin, title="С тегом", tag_ids=[tag["id"]])
    await create_doc(client_admin, title="Без тега")
    r = await client_admin.get(f"{DOCS_API}/documents?tag_slug=filter-tag")
    assert r.status_code == 200
    titles = [d["title"] for d in r.json()["items"]]
    assert "С тегом" in titles
    assert "Без тега" not in titles
    assert any(t["slug"] == "filter-tag" for t in with_tag["tags"])

    await create_doc(client_admin, title="С владельцем", owner_sub="specific-owner")
    r = await client_admin.get(f"{DOCS_API}/documents?owner_sub=specific-owner")
    assert r.status_code == 200
    assert all(d["owner_sub"] == "specific-owner" for d in r.json()["items"])
    assert any(d["title"] == "С владельцем" for d in r.json()["items"])


async def test_update_document_title_body_tags_and_icon(client_admin: AsyncClient) -> None:
    tag_a = await post_tag(client_admin, name="tag-a")
    tag_b = await post_tag(client_admin, name="tag-b")
    doc = await create_doc(client_admin, title="До обновления", body="Исходное тело", tag_ids=[tag_a["id"]])

    r = await client_admin.patch(
        f"{DOCS_ADMIN}/{doc['id']}",
        json={
            "expected_version": doc["version"],
            "title": "После обновления",
            "body": "Обновлённое тело",
            "tag_ids": [tag_b["id"]],
            "icon_emoji": "📎",
        },
    )
    assert r.status_code == 200
    data = r.json()
    assert data["title"] == "После обновления"
    assert data["body"] == "Обновлённое тело"
    assert data["icon_emoji"] == "📎"
    assert data["version"] == doc["version"] + 1
    slugs = {t["slug"] for t in data["tags"]}
    assert slugs == {"tag-b"}

    r_clear = await client_admin.patch(
        f"{DOCS_ADMIN}/{doc['id']}",
        json={"expected_version": data["version"], "icon_emoji": None},
    )
    assert r_clear.status_code == 200
    assert not r_clear.json().get("icon_emoji")


async def test_update_clears_parent_and_empty_patch_skips_history(client_admin: AsyncClient) -> None:
    parent = await create_doc(client_admin, title="Родитель сброса")
    child = await create_doc(client_admin, title="Ребёнок сброса", parent_document_id=parent["id"])
    r = await client_admin.patch(
        f"{DOCS_ADMIN}/{child['id']}",
        json={"expected_version": child["version"], "parent_document_id": None},
    )
    assert r.status_code == 200
    assert r.json()["parent_document_id"] is None
    child_ver = r.json()["version"]

    hist = await client_admin.get(f"{DOCS_API}/documents/{child['id']}/history")
    assert hist.status_code == 200
    before = len(hist.json())
    r = await client_admin.patch(f"{DOCS_ADMIN}/{child['id']}", json={"expected_version": child_ver})
    assert r.status_code == 200
    hist2 = await client_admin.get(f"{DOCS_API}/documents/{child['id']}/history")
    assert len(hist2.json()) == before


async def test_history_records_title_old_and_new(client_admin: AsyncClient) -> None:
    doc = await create_doc(client_admin, title="Старое")
    await client_admin.patch(
        f"{DOCS_ADMIN}/{doc['id']}",
        json={"expected_version": doc["version"], "title": "Новое"},
    )
    r = await client_admin.get(f"{DOCS_API}/documents/{doc['id']}/history")
    assert r.status_code == 200
    history = r.json()
    assert history[0]["changed_by_sub"] == "admin-sub"
    update_entry = next(h for h in history if "title" in h["diff"] and h["diff"]["title"]["old"] is not None)
    assert update_entry["diff"]["title"]["old"] == "Старое"
    assert update_entry["diff"]["title"]["new"] == "Новое"


async def test_related_lists_tasks(client_admin: AsyncClient) -> None:
    doc = await create_doc(client_admin, title="Документ со связями")
    tk = await client_admin.post(
        f"{DOCS_API}/tasks",
        json={"title": "Задача по документу", "document_id": doc["id"], "assignee_sub": "admin-sub"},
    )
    assert tk.status_code == 201, tk.text
    rel = await client_admin.get(f"{DOCS_API}/documents/{doc['id']}/related")
    assert rel.status_code == 200
    payload = rel.json()
    assert payload["chats"] == []
    assert any(t["id"] == tk.json()["id"] for t in payload["tasks"])


async def test_quick_create_and_parent_cycle(client_admin: AsyncClient) -> None:
    r = await client_admin.post(f"{DOCS_ADMIN}/quick-create", json={})
    assert r.status_code == 201
    doc_id = r.json()["id"]
    r2 = await client_admin.get(f"{DOCS_API}/documents/{doc_id}")
    assert r2.status_code == 200
    assert r2.json()["title"] == "Без названия"

    parent = await create_doc(client_admin, title="Цикл A")
    child = await create_doc(client_admin, title="Цикл B", parent_document_id=parent["id"])
    r = await client_admin.patch(
        f"{DOCS_ADMIN}/{parent['id']}",
        json={"expected_version": parent["version"], "parent_document_id": child["id"]},
    )
    assert_api_error(r, 409, "conflict")
    r = await client_admin.patch(
        f"{DOCS_ADMIN}/{parent['id']}",
        json={"expected_version": parent["version"], "parent_document_id": parent["id"]},
    )
    assert_api_error(r, 409, "conflict")


async def test_create_with_unknown_or_trashed_parent(client_admin: AsyncClient) -> None:
    r = await client_admin.post(
        DOCS_ADMIN,
        json={"title": "Сирота", "parent_document_id": "00000000-0000-0000-0000-000000000001"},
    )
    assert_api_error(r, 404, "not_found")

    parent = await create_doc(client_admin, title="Удалённый родитель")
    await client_admin.delete(f"{DOCS_ADMIN}/{parent['id']}")
    r = await client_admin.post(
        DOCS_ADMIN,
        json={"title": "Ребёнок удалённого", "parent_document_id": parent["id"]},
    )
    assert_api_error(r, 404, "not_found")


async def test_soft_delete_restore_purge_and_subtree(client_admin: AsyncClient) -> None:
    parent = await create_doc(client_admin, title="Корень корзины")
    child = await create_doc(client_admin, title="Вложенный", parent_document_id=parent["id"])
    r = await client_admin.delete(f"{DOCS_ADMIN}/{parent['id']}")
    assert r.status_code == 204
    r = await client_admin.get(f"{DOCS_API}/documents/{parent['id']}")
    assert_api_error(r, 404, "not_found")
    r = await client_admin.get(f"{DOCS_API}/documents/{child['id']}")
    assert_api_error(r, 404, "not_found")
    r = await client_admin.get(f"{DOCS_API}/documents/{parent['id']}/history")
    assert_api_error(r, 404, "not_found")

    r2 = await client_admin.delete(f"{DOCS_ADMIN}/{parent['id']}")
    assert r2.status_code == 204

    tr = await client_admin.get(f"{DOCS_ADMIN}/trash")
    assert tr.status_code == 200
    trash_ids = {row["id"] for row in tr.json()["items"]}
    assert parent["id"] in trash_ids
    assert child["id"] not in trash_ids

    r = await client_admin.post(f"{DOCS_ADMIN}/{child['id']}/restore")
    assert_api_error(r, 422, "validation_error")
    r = await client_admin.delete(f"{DOCS_ADMIN}/{child['id']}/purge")
    assert_api_error(r, 422, "validation_error")

    r = await client_admin.post(f"{DOCS_ADMIN}/{parent['id']}/restore")
    assert r.status_code == 200
    r = await client_admin.get(f"{DOCS_API}/documents/{child['id']}")
    assert r.status_code == 200
    assert r.json()["title"] == "Вложенный"

    live = await create_doc(client_admin, title="Активный restore")
    r = await client_admin.post(f"{DOCS_ADMIN}/{live['id']}/restore")
    assert r.status_code == 200
    assert r.json()["id"] == live["id"]

    r = await client_admin.delete(f"{DOCS_ADMIN}/{parent['id']}/purge")
    assert r.status_code == 204
    r = await client_admin.get(f"{DOCS_API}/documents/{parent['id']}")
    assert_api_error(r, 404, "not_found")


async def test_reorder_siblings_and_validation(client_admin: AsyncClient) -> None:
    parent = await create_doc(client_admin, title="Родитель reorder")
    older = await create_doc(client_admin, title="Ребёнок старше", parent_document_id=parent["id"])
    newer = await create_doc(client_admin, title="Ребёнок новее", parent_document_id=parent["id"])

    before = await client_admin.get(f"{DOCS_API}/documents/{parent['id']}/children")
    assert before.status_code == 200
    assert [d["id"] for d in before.json()] == [newer["id"], older["id"]]

    r = await client_admin.patch(f"{DOCS_ADMIN}/{newer['id']}/reorder", json={"after_id": older["id"]})
    assert r.status_code == 200, r.text
    after = await client_admin.get(f"{DOCS_API}/documents/{parent['id']}/children")
    assert [d["id"] for d in after.json()] == [older["id"], newer["id"]]

    r = await client_admin.patch(f"{DOCS_ADMIN}/{newer['id']}/reorder", json={"before_id": older["id"]})
    assert r.status_code == 200
    after_before = await client_admin.get(f"{DOCS_API}/documents/{parent['id']}/children")
    assert [d["id"] for d in after_before.json()] == [newer["id"], older["id"]]

    r = await client_admin.patch(
        f"{DOCS_ADMIN}/{newer['id']}/reorder",
        json={"before_id": older["id"], "after_id": older["id"]},
    )
    assert r.status_code == 422
    assert "detail" in r.json()
    r = await client_admin.patch(f"{DOCS_ADMIN}/{newer['id']}/reorder", json={})
    assert r.status_code == 422
    assert "detail" in r.json()
    r = await client_admin.patch(
        f"{DOCS_ADMIN}/{newer['id']}/reorder",
        json={"before_id": str(uuid.uuid4())},
    )
    assert_api_error(r, 422, "validation_error")


async def test_list_children_and_empty(client_admin: AsyncClient) -> None:
    parent = await create_doc(client_admin, title="Родитель Дети")
    child = await create_doc(client_admin, title="Ребёнок 1", parent_document_id=parent["id"])
    r = await client_admin.get(f"{DOCS_API}/documents/{parent['id']}/children")
    assert r.status_code == 200
    ids = {d["id"] for d in r.json()}
    assert child["id"] in ids
    assert parent["id"] not in ids

    lonely = await create_doc(client_admin, title="Одиночка")
    r = await client_admin.get(f"{DOCS_API}/documents/{lonely['id']}/children")
    assert r.status_code == 200
    assert r.json() == []


async def test_duplicate_subtree(client_admin: AsyncClient) -> None:
    tag = await post_tag(client_admin, name="dup-tag")
    parent = await create_doc(client_admin, title="Оригинал", body="Тело родителя", tag_ids=[tag["id"]])
    child = await create_doc(client_admin, title="Дочерний", body="Тело дочернего", parent_document_id=parent["id"])
    r = await client_admin.post(f"{DOCS_ADMIN}/{parent['id']}/duplicate")
    assert r.status_code == 201, r.text
    copy_id = r.json()["id"]
    copy_doc = (await client_admin.get(f"{DOCS_API}/documents/{copy_id}")).json()
    assert copy_doc["title"] == "Оригинал (копия)"
    assert copy_doc["body"] == "Тело родителя"
    assert {t["id"] for t in copy_doc["tags"]} == {tag["id"]}
    children = (await client_admin.get(f"{DOCS_API}/documents/{copy_id}/children")).json()
    assert len(children) == 1
    assert children[0]["title"] == "Дочерний"
    assert children[0]["id"] != child["id"]

    await client_admin.delete(f"{DOCS_ADMIN}/{parent['id']}")
    r = await client_admin.post(f"{DOCS_ADMIN}/{parent['id']}/duplicate")
    assert_api_error(r, 404, "not_found")


async def test_upload_document_rich_media(client_admin: AsyncClient) -> None:
    doc = await create_doc(client_admin, title="Документ с картинкой", body="")
    with (
        patch("app.services.rich_media_upload.async_upload_stream_to_key", new_callable=AsyncMock),
        patch("app.services.rich_media.get_presigned_url", return_value="https://minio.local/img"),
    ):
        r = await client_admin.post(
            f"{DOCS_API}/documents/{doc['id']}/rich-media",
            files={"file": ("pic.png", io.BytesIO(_PNG), "image/png")},
        )
        assert r.status_code == 201, r.text
        media_id = r.json()["id"]
        r = await client_admin.get(f"{DOCS_API}/rich-media/{media_id}")
        assert r.status_code == 200, r.text
        assert r.json()["id"] == media_id
