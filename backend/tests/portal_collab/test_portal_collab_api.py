"""Интеграционные тесты: договорённости и задачи."""

from __future__ import annotations

from httpx import AsyncClient

from tests.helpers.portal_test_users import user_portal_regular
from tests.portal_collab.conftest import assert_api_error
from tests.portal_documents.conftest import post_tag as _post_tag


async def test_agreement_and_task_flow(client_admin: AsyncClient) -> None:
    r = await client_admin.post(
        "/api/v1/portal/chats",
        json={"title": "Для договорённости", "member_subs": [user_portal_regular().sub]},
    )
    cid = r.json()["id"]
    r = await client_admin.post(f"/api/v1/portal/chats/{cid}/messages", json={"body": "Договорились о сроке"})
    mid = r.json()["id"]

    r = await client_admin.post(
        "/api/v1/portal/agreements",
        json={"body": "Срок — пятница", "source_message_id": mid},
    )
    assert r.status_code == 201, r.text
    aid = r.json()["id"]

    r = await client_admin.post(
        "/api/v1/portal/tasks",
        json={"title": "Сделать отчёт", "source_message_id": mid, "chat_id": cid, "assignee_sub": "admin-sub"},
    )
    assert r.status_code == 201, r.text
    tid = r.json()["id"]

    r = await client_admin.patch(f"/api/v1/portal/agreements/{aid}", json={"task_id": tid})
    assert r.status_code == 200

    r = await client_admin.get(f"/api/v1/portal/tasks/{tid}/history")
    assert r.status_code == 200
    assert len(r.json()) >= 1


async def test_task_crud_list_filters_and_patch(client_admin: AsyncClient) -> None:
    r = await client_admin.post(
        "/api/v1/portal/chats",
        json={"title": "Для задач API", "member_subs": [user_portal_regular().sub]},
    )
    cid = r.json()["id"]
    r2 = await client_admin.post(f"/api/v1/portal/chats/{cid}/messages", json={"body": "контекст"})
    mid = r2.json()["id"]
    r3 = await client_admin.post(
        "/api/v1/portal/tasks",
        json={
            "title": "Задача фильтры",
            "source_message_id": mid,
            "chat_id": cid,
            "priority": "high",
            "assignee_sub": "admin-sub",
        },
    )
    assert r3.status_code == 201, r3.text
    tid = r3.json()["id"]
    assert r3.json().get("assignee_sub") == "admin-sub"

    r = await client_admin.get(f"/api/v1/portal/tasks/{tid}")
    assert r.status_code == 200
    assert r.json()["title"] == "Задача фильтры"

    r = await client_admin.get("/api/v1/portal/tasks?mine_only=true")
    assert r.status_code == 200
    assert any(t["id"] == tid for t in r.json())

    r = await client_admin.get(f"/api/v1/portal/tasks?chat_id={cid}")
    assert r.status_code == 200
    assert any(t["id"] == tid for t in r.json())

    r = await client_admin.patch(
        f"/api/v1/portal/tasks/{tid}",
        json={"expected_version": 1, "status": "in_progress", "assignee_sub": "someone-else"},
    )
    assert r.status_code == 200
    assert r.json()["status"] == "in_progress"
    assert r.json()["assignee_sub"] == "someone-else"

    r = await client_admin.get("/api/v1/portal/tasks?mine_only=true")
    assert r.status_code == 200
    assert not any(t["id"] == tid for t in r.json())

    r = await client_admin.get("/api/v1/portal/tasks?status=in_progress")
    assert r.status_code == 200
    assert any(t["id"] == tid for t in r.json())


async def test_list_tasks_filter_by_multiple_statuses(client_admin: AsyncClient) -> None:
    r_chat = await client_admin.post(
        "/api/v1/portal/chats",
        json={"title": "Статусы", "member_subs": [user_portal_regular().sub]},
    )
    cid = r_chat.json()["id"]
    r_msg = await client_admin.post(f"/api/v1/portal/chats/{cid}/messages", json={"body": "x"})
    mid = r_msg.json()["id"]

    r_todo = await client_admin.post(
        "/api/v1/portal/tasks",
        json={"title": "Todo task", "source_message_id": mid, "chat_id": cid, "assignee_sub": "admin-sub"},
    )
    r_done = await client_admin.post(
        "/api/v1/portal/tasks",
        json={"title": "Done task", "source_message_id": mid, "chat_id": cid, "assignee_sub": "admin-sub"},
    )
    assert r_todo.status_code == 201 and r_done.status_code == 201
    tid_todo, tid_done = r_todo.json()["id"], r_done.json()["id"]
    await client_admin.patch(f"/api/v1/portal/tasks/{tid_done}", json={"expected_version": 1, "status": "done"})

    r = await client_admin.get(
        "/api/v1/portal/tasks",
        params=[("status", "todo"), ("status", "done")],
    )
    assert r.status_code == 200, r.text
    got = {t["id"] for t in r.json()}
    assert tid_todo in got and tid_done in got

    r_todo_only = await client_admin.get("/api/v1/portal/tasks", params={"status": "todo"})
    assert r_todo_only.status_code == 200
    got_todo = {t["id"] for t in r_todo_only.json()}
    assert tid_todo in got_todo and tid_done not in got_todo


async def test_list_tasks_filter_by_multiple_priorities(client_admin: AsyncClient) -> None:
    r_chat = await client_admin.post(
        "/api/v1/portal/chats",
        json={"title": "Приоритеты", "member_subs": [user_portal_regular().sub]},
    )
    cid = r_chat.json()["id"]
    r_msg = await client_admin.post(f"/api/v1/portal/chats/{cid}/messages", json={"body": "x"})
    mid = r_msg.json()["id"]

    r_high = await client_admin.post(
        "/api/v1/portal/tasks",
        json={
            "title": "High task",
            "source_message_id": mid,
            "chat_id": cid,
            "assignee_sub": "admin-sub",
            "priority": "high",
        },
    )
    r_low = await client_admin.post(
        "/api/v1/portal/tasks",
        json={
            "title": "Low task",
            "source_message_id": mid,
            "chat_id": cid,
            "assignee_sub": "admin-sub",
            "priority": "low",
        },
    )
    assert r_high.status_code == 201 and r_low.status_code == 201
    tid_high, tid_low = r_high.json()["id"], r_low.json()["id"]

    r_sub = await client_admin.post(
        "/api/v1/portal/tasks",
        json={
            "title": "Sub high",
            "source_message_id": mid,
            "chat_id": cid,
            "assignee_sub": "admin-sub",
            "priority": "medium",
            "parent_task_id": tid_high,
        },
    )
    assert r_sub.status_code == 201
    tid_sub = r_sub.json()["id"]

    r = await client_admin.get(
        "/api/v1/portal/tasks",
        params=[("priority", "high"), ("priority", "low")],
    )
    assert r.status_code == 200, r.text
    got = {t["id"] for t in r.json()}
    assert tid_high in got and tid_low in got

    r_high_only = await client_admin.get("/api/v1/portal/tasks", params={"priority": "high"})
    assert r_high_only.status_code == 200
    got_high = {t["id"] for t in r_high_only.json()}
    assert tid_high in got_high and tid_low not in got_high
    assert tid_sub in got_high


async def test_list_tasks_filter_by_multiple_assignees(client_admin: AsyncClient) -> None:
    r = await client_admin.post(
        "/api/v1/portal/chats",
        json={"title": "Мульти исполнители", "member_subs": [user_portal_regular().sub]},
    )
    cid = r.json()["id"]
    r_msg = await client_admin.post(f"/api/v1/portal/chats/{cid}/messages", json={"body": "x"})
    mid = r_msg.json()["id"]

    r1 = await client_admin.post(
        "/api/v1/portal/tasks",
        json={"title": "T1", "source_message_id": mid, "chat_id": cid, "assignee_sub": "admin-sub"},
    )
    r2 = await client_admin.post(
        "/api/v1/portal/tasks",
        json={"title": "T2", "source_message_id": mid, "chat_id": cid, "assignee_sub": "admin-sub"},
    )
    assert r1.status_code == 201 and r2.status_code == 201, (r1.text, r2.text)
    tid1, tid2 = r1.json()["id"], r2.json()["id"]

    await client_admin.patch(f"/api/v1/portal/tasks/{tid1}", json={"expected_version": 1, "assignee_sub": "user-alpha"})
    await client_admin.patch(f"/api/v1/portal/tasks/{tid2}", json={"expected_version": 1, "assignee_sub": "user-beta"})

    r = await client_admin.get(
        "/api/v1/portal/tasks",
        params=[("assignee_sub", "user-alpha"), ("assignee_sub", "user-beta")],
    )
    assert r.status_code == 200, r.text
    got = {t["id"] for t in r.json()}
    assert tid1 in got and tid2 in got

    r_single = await client_admin.get("/api/v1/portal/tasks", params={"assignee_sub": "user-alpha"})
    assert r_single.status_code == 200
    got_s = {t["id"] for t in r_single.json()}
    assert tid1 in got_s and tid2 not in got_s


async def test_patch_task_tag_ids(client_admin: AsyncClient) -> None:
    tag_a = await _post_tag(client_admin, name="Тег-А", color="#FF0000")
    tag_b = await _post_tag(client_admin, name="Тег-Б", color="#00FF00")

    r = await client_admin.post(
        "/api/v1/portal/tasks",
        json={"title": "Задача с тегами", "tag_ids": [tag_a["id"]], "assignee_sub": "admin-sub"},
    )
    assert r.status_code == 201, r.text
    tid = r.json()["id"]
    assert any(t["id"] == tag_a["id"] for t in r.json()["tags"])

    r = await client_admin.patch(
        f"/api/v1/portal/tasks/{tid}",
        json={"expected_version": 1, "tag_ids": [tag_b["id"]]},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    tag_ids = {t["id"] for t in body["tags"]}
    assert tag_b["id"] in tag_ids
    assert tag_a["id"] not in tag_ids

    r = await client_admin.patch(
        f"/api/v1/portal/tasks/{tid}",
        json={"expected_version": body["version"], "tag_ids": []},
    )
    assert r.status_code == 200, r.text
    assert r.json()["tags"] == []


async def test_patch_task_context_links(client_admin: AsyncClient) -> None:
    """PATCH document_id через блок «Связи» — chat_id и nav_node_id больше не принимаются через PATCH."""
    r = await client_admin.post(
        "/api/v1/portal/tasks",
        json={"title": "Связи patch", "assignee_sub": "admin-sub"},
    )
    assert r.status_code == 201, r.text
    tid = r.json()["id"]

    # Изменение заголовка должно работать корректно
    r = await client_admin.patch(
        f"/api/v1/portal/tasks/{tid}",
        json={"expected_version": 1, "title": "Обновлённый заголовок"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["title"] == "Обновлённый заголовок"


async def test_agreement_list_get_patch(client_admin: AsyncClient) -> None:
    r = await client_admin.post(
        "/api/v1/portal/chats",
        json={"title": "Для договорённости API", "member_subs": [user_portal_regular().sub]},
    )
    cid = r.json()["id"]
    r2 = await client_admin.post(f"/api/v1/portal/chats/{cid}/messages", json={"body": "текст соглашения"})
    mid = r2.json()["id"]
    r3 = await client_admin.post(
        "/api/v1/portal/agreements",
        json={"body": "Условие AGRAPI88", "source_message_id": mid},
    )
    assert r3.status_code == 201, r3.text
    aid = r3.json()["id"]

    r = await client_admin.get(f"/api/v1/portal/agreements/{aid}")
    assert r.status_code == 200
    body = r.json()
    assert "AGRAPI88" in body["body"]
    assert body.get("source_message_id") == mid
    assert body.get("source_chat_id") == cid

    r = await client_admin.get("/api/v1/portal/agreements?status=draft")
    assert r.status_code == 200
    assert any(a["id"] == aid for a in r.json())

    r = await client_admin.patch(f"/api/v1/portal/agreements/{aid}", json={"body": "Обновлено AGRAPI88"})
    assert r.status_code == 200
    assert "Обновлено" in r.json()["body"]


async def test_regular_user_cannot_set_initial_status_on_agreement_create(client_user: AsyncClient) -> None:
    r = await client_user.post(
        "/api/v1/portal/agreements",
        json={"body": "текст", "status": "confirmed"},
    )
    assert_api_error(r, 403, "forbidden")


async def test_admin_can_set_initial_status_on_agreement_create(client_admin: AsyncClient) -> None:
    r = await client_admin.post(
        "/api/v1/portal/agreements",
        json={"body": "со статусом", "status": "confirmed"},
    )
    assert r.status_code == 201, r.text
    assert r.json()["status"] == "confirmed"


async def test_list_tasks_filter_by_tag_id(client_admin: AsyncClient) -> None:
    import uuid

    tag = await _post_tag(client_admin, name=f"TagFilter{uuid.uuid4().hex[:6]}", color="#00AA00")
    r = await client_admin.post(
        "/api/v1/portal/tasks",
        json={"title": "С тегом для фильтра", "tag_ids": [tag["id"]], "assignee_sub": "admin-sub"},
    )
    assert r.status_code == 201, r.text
    tid = r.json()["id"]
    r = await client_admin.get(f"/api/v1/portal/tasks?tag_id={tag['id']}")
    assert r.status_code == 200, r.text
    assert tid in {t["id"] for t in r.json()}


async def test_list_task_history_skip_limit(client_admin: AsyncClient) -> None:
    r = await client_admin.post("/api/v1/portal/tasks", json={"title": "История skip", "assignee_sub": "admin-sub"})
    assert r.status_code == 201, r.text
    tid = r.json()["id"]
    version = r.json()["version"]
    for i in range(3):
        patched = await client_admin.patch(
            f"/api/v1/portal/tasks/{tid}",
            json={"expected_version": version, "title": f"Шаг {i}"},
        )
        assert patched.status_code == 200, patched.text
        version = patched.json()["version"]
    r = await client_admin.get(f"/api/v1/portal/tasks/{tid}/history?skip=1&limit=2")
    assert r.status_code == 200, r.text
    assert len(r.json()) <= 2
