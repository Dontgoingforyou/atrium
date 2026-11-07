"""PATCH parent_task_id: привязка уже созданных задач как родителя и подзадачи."""

from __future__ import annotations

import pytest
from httpx import AsyncClient, Response
from sqlalchemy.ext.asyncio import AsyncSession

from tests.helpers.portal_test_users import user_portal_regular, user_portal_user_b
from tests.portal_collab.conftest import assert_api_error, async_client_as

_TASKS = "/api/v1/portal/tasks"


async def _create_task(client: AsyncClient, title: str, assignee_sub: str) -> dict[str, object]:
    response = await client.post(_TASKS, json={"title": title, "assignee_sub": assignee_sub})
    assert response.status_code == 201, response.text
    body: dict[str, object] = response.json()
    return body


def _parent_history_values(history: Response) -> list[dict[str, object]]:
    values: list[dict[str, object]] = []
    for item in history.json():
        diff = item["diff"].get("parent_task_id")
        if isinstance(diff, dict):
            values.append(diff)
    return values


@pytest.mark.asyncio
async def test_patch_parent_links_existing_tasks_on_both_sides(client_admin: AsyncClient) -> None:
    parent = await _create_task(client_admin, "Родитель", "admin-sub")
    child = await _create_task(client_admin, "Уже созданная", "admin-sub")
    parent_id = str(parent["id"])
    child_id = str(child["id"])

    linked = await client_admin.patch(
        f"{_TASKS}/{child_id}",
        json={"expected_version": child["version"], "parent_task_id": parent_id},
    )
    assert linked.status_code == 200, linked.text
    assert linked.json()["parent_task_id"] == parent_id

    child_card = await client_admin.get(f"{_TASKS}/{child_id}")
    assert child_card.status_code == 200
    assert child_card.json()["parent_task_id"] == parent_id

    siblings = await client_admin.get(_TASKS, params={"parent_task_id": parent_id})
    assert siblings.status_code == 200
    assert child_id in {item["id"] for item in siblings.json()}

    history = await client_admin.get(f"{_TASKS}/{child_id}/history")
    assert history.status_code == 200
    assert {"old": None, "new": parent_id} in _parent_history_values(history)

    titled = await client_admin.patch(
        f"{_TASKS}/{child_id}",
        json={"expected_version": linked.json()["version"], "title": "Уже созданная"},
    )
    assert titled.status_code == 200, titled.text
    assert titled.json()["parent_task_id"] == parent_id

    unlinked = await client_admin.patch(
        f"{_TASKS}/{child_id}",
        json={"expected_version": titled.json()["version"], "parent_task_id": None},
    )
    assert unlinked.status_code == 200, unlinked.text
    assert unlinked.json()["parent_task_id"] is None

    siblings_after = await client_admin.get(_TASKS, params={"parent_task_id": parent_id})
    assert child_id not in {item["id"] for item in siblings_after.json()}


@pytest.mark.asyncio
async def test_patch_parent_rejects_self_cycle_and_taken_parent(client_admin: AsyncClient) -> None:
    root = await _create_task(client_admin, "Корень", "admin-sub")
    middle = await _create_task(client_admin, "Середина", "admin-sub")
    other = await _create_task(client_admin, "Другой родитель", "admin-sub")
    root_id = str(root["id"])
    middle_id = str(middle["id"])
    other_id = str(other["id"])

    self_link = await client_admin.patch(
        f"{_TASKS}/{root_id}",
        json={"expected_version": root["version"], "parent_task_id": root_id},
    )
    assert_api_error(self_link, 422, "validation_error")
    assert "самой себя" in self_link.json()["message"]

    linked = await client_admin.patch(
        f"{_TASKS}/{middle_id}",
        json={"expected_version": middle["version"], "parent_task_id": root_id},
    )
    assert linked.status_code == 200, linked.text

    cycle = await client_admin.patch(
        f"{_TASKS}/{root_id}",
        json={"expected_version": root["version"], "parent_task_id": middle_id},
    )
    assert_api_error(cycle, 422, "validation_error")
    assert "цикл" in cycle.json()["message"]

    taken = await client_admin.patch(
        f"{_TASKS}/{middle_id}",
        json={"expected_version": linked.json()["version"], "parent_task_id": other_id},
    )
    assert_api_error(taken, 422, "validation_error")
    assert "другой родитель" in taken.json()["message"]
    still = await client_admin.get(f"{_TASKS}/{middle_id}")
    assert still.json()["parent_task_id"] == root_id


@pytest.mark.asyncio
async def test_patch_parent_forbidden_for_viewer_who_cannot_edit(
    sqlite_session: AsyncSession,
    patch_oidc_settings: object,
) -> None:
    author = user_portal_regular()
    async with async_client_as(sqlite_session, user_portal_regular) as author_client:
        parent = await _create_task(author_client, "Видимый родитель", author.sub)
        child = await _create_task(author_client, "Чужая задача", author.sub)

    async with async_client_as(sqlite_session, user_portal_user_b) as viewer:
        response = await viewer.patch(
            f"{_TASKS}/{child['id']}",
            json={"expected_version": child["version"], "parent_task_id": parent["id"]},
        )
        assert_api_error(response, 403, "forbidden")
