"""RBAC / IDOR / 401 обучения: матрица auth, timesheet, write-403, скрытое → 404."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from app.core.auth_constants import IDP_GROUP_DEVELOPER, IDP_GROUP_PORTAL_ADMIN
from app.core.enums import LearningMaterialStatus
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.helpers.portal_test_users import user_portal_manager, user_portal_no_idp_groups
from tests.portal_learning.conftest import (
    CHECKLISTS,
    MATERIALS,
    QUIZZES,
    add_checklist,
    add_material,
    add_quiz_with_question,
    as_user,
    as_user_b,
    as_user_regular,
    assert_api_error,
)

_AUTH_UUID = "00000000-0000-4000-8000-000000000001"
_AUTH_ITEM = "00000000-0000-4000-8000-000000000003"
_AUTH_ATTEMPT = "00000000-0000-4000-8000-000000000002"

_AUTH_CASES: list[tuple[str, str, dict[str, object]]] = [
    ("GET", MATERIALS, {}),
    ("GET", f"{MATERIALS}/{_AUTH_UUID}", {}),
    ("POST", MATERIALS, {"json": {"title": "T", "material_type": "article", "status": "draft"}}),
    ("PATCH", f"{MATERIALS}/{_AUTH_UUID}", {"json": {"expected_version": 1, "body": "x"}}),
    ("DELETE", f"{MATERIALS}/{_AUTH_UUID}", {}),
    ("GET", CHECKLISTS, {}),
    ("GET", f"{CHECKLISTS}/{_AUTH_UUID}", {}),
    ("POST", CHECKLISTS, {"json": {"title": "C", "items": ["a"]}}),
    ("PATCH", f"{CHECKLISTS}/{_AUTH_UUID}", {"json": {"expected_version": 1, "title": "N"}}),
    ("DELETE", f"{CHECKLISTS}/{_AUTH_UUID}", {}),
    ("POST", f"{CHECKLISTS}/{_AUTH_UUID}/start", {}),
    ("GET", f"{CHECKLISTS}/{_AUTH_UUID}/my-progress", {}),
    ("PATCH", f"{CHECKLISTS}/{_AUTH_UUID}/items/{_AUTH_ITEM}", {"json": {"is_done": True}}),
    ("GET", QUIZZES, {}),
    ("GET", f"{QUIZZES}/{_AUTH_UUID}", {}),
    ("GET", f"{QUIZZES}/{_AUTH_UUID}/for-edit", {}),
    ("POST", QUIZZES, {"json": {"title": "Q"}}),
    ("PATCH", f"{QUIZZES}/{_AUTH_UUID}", {"json": {"title": "N"}}),
    ("PUT", f"{QUIZZES}/{_AUTH_UUID}/questions", {"json": {"questions": []}}),
    ("DELETE", f"{QUIZZES}/{_AUTH_UUID}", {}),
    ("POST", f"{QUIZZES}/{_AUTH_UUID}/attempts", {}),
    ("POST", f"{QUIZZES}/{_AUTH_UUID}/attempts/{_AUTH_ATTEMPT}/submit", {"json": {"answers": []}}),
    ("GET", f"{QUIZZES}/{_AUTH_UUID}/attempts", {}),
]


@pytest.mark.parametrize(("method", "path", "kwargs"), _AUTH_CASES)
async def test_learning_endpoints_require_auth(
    client_sqlite_only: AsyncClient,
    method: str,
    path: str,
    kwargs: dict[str, object],
) -> None:
    r = await client_sqlite_only.request(method, path, **kwargs)
    assert_api_error(r, 401, "unauthorized")


@pytest.mark.parametrize(("method", "path", "kwargs"), _AUTH_CASES)
async def test_timesheet_forbidden_on_learning(
    client_developer: AsyncClient,
    method: str,
    path: str,
    kwargs: dict[str, object],
) -> None:
    r = await client_developer.request(method, path, **kwargs)
    assert_api_error(r, 403, "forbidden")


@pytest.mark.parametrize(
    ("method", "url", "body"),
    [
        ("POST", MATERIALS, {"title": "X", "material_type": "article", "status": "draft"}),
        ("POST", CHECKLISTS, {"title": "CL", "items": ["a"]}),
        ("POST", QUIZZES, {"title": "QZ"}),
    ],
)
async def test_learning_create_forbidden_for_regular_and_manager(
    client_admin: AsyncClient,
    method: str,
    url: str,
    body: dict[str, object],
) -> None:
    with as_user_regular():
        r = await client_admin.request(method, url, json=body)
        assert_api_error(r, 403, "forbidden")
    with as_user(user_portal_manager):
        r = await client_admin.request(method, url, json=body)
        assert_api_error(r, 403, "forbidden")


async def test_learning_write_forbidden_for_regular(
    client_admin: AsyncClient,
    sqlite_session: AsyncSession,
) -> None:
    mat = await add_material(sqlite_session, title="Материал")
    cl, _items = await add_checklist(sqlite_session, title="ЧЛ", items=["a"])
    quiz, _q, _ok, _bad = await add_quiz_with_question(sqlite_session, title="Тест")
    await sqlite_session.commit()

    with as_user_regular():
        r = await client_admin.patch(
            f"{MATERIALS}/{mat.id}",
            json={"expected_version": mat.version, "body": "x"},
        )
        assert_api_error(r, 403, "forbidden")
        r = await client_admin.delete(f"{MATERIALS}/{mat.id}")
        assert_api_error(r, 403, "forbidden")
        r = await client_admin.patch(
            f"{CHECKLISTS}/{cl.id}",
            json={"expected_version": cl.version, "title": "N"},
        )
        assert_api_error(r, 403, "forbidden")
        r = await client_admin.delete(f"{CHECKLISTS}/{cl.id}")
        assert_api_error(r, 403, "forbidden")
        r = await client_admin.patch(f"{QUIZZES}/{quiz.id}", json={"title": "N"})
        assert_api_error(r, 403, "forbidden")
        r = await client_admin.put(f"{QUIZZES}/{quiz.id}/questions", json={"questions": []})
        assert_api_error(r, 403, "forbidden")
        r = await client_admin.delete(f"{QUIZZES}/{quiz.id}")
        assert_api_error(r, 403, "forbidden")
        r = await client_admin.get(f"{QUIZZES}/{quiz.id}/for-edit")
        assert_api_error(r, 403, "forbidden")


async def test_unknown_ids_return_404(client_admin: AsyncClient) -> None:
    missing = uuid.uuid4()
    r = await client_admin.get(f"{MATERIALS}/{missing}")
    assert_api_error(r, 404, "not_found")
    r = await client_admin.patch(f"{MATERIALS}/{missing}", json={"expected_version": 1, "body": "x"})
    assert_api_error(r, 404, "not_found")
    r = await client_admin.delete(f"{MATERIALS}/{missing}")
    assert_api_error(r, 404, "not_found")
    r = await client_admin.get(f"{CHECKLISTS}/{missing}")
    assert_api_error(r, 404, "not_found")
    r = await client_admin.patch(f"{CHECKLISTS}/{missing}", json={"expected_version": 1, "title": "N"})
    assert_api_error(r, 404, "not_found")
    r = await client_admin.delete(f"{CHECKLISTS}/{missing}")
    assert_api_error(r, 404, "not_found")
    r = await client_admin.get(f"{QUIZZES}/{missing}")
    assert_api_error(r, 404, "not_found")
    r = await client_admin.patch(f"{QUIZZES}/{missing}", json={"title": "N"})
    assert_api_error(r, 404, "not_found")
    r = await client_admin.delete(f"{QUIZZES}/{missing}")
    assert_api_error(r, 404, "not_found")
    r = await client_admin.post(QUIZZES, json={"title": "Q", "material_id": str(missing)})
    assert_api_error(r, 404, "not_found")


async def test_draft_and_archived_hidden_from_regular(
    client_admin: AsyncClient,
    sqlite_session: AsyncSession,
) -> None:
    draft = await add_material(sqlite_session, title="Черновик", status=LearningMaterialStatus.DRAFT.value)
    archived = await add_material(sqlite_session, title="Архив", status=LearningMaterialStatus.ARCHIVED.value)
    await sqlite_session.commit()

    r = await client_admin.get(f"{MATERIALS}/{draft.id}")
    assert r.status_code == 200
    r = await client_admin.get(MATERIALS, params={"status": "draft"})
    assert r.status_code == 200
    assert str(draft.id) in {x["id"] for x in r.json()}

    with as_user_regular():
        r = await client_admin.get(f"{MATERIALS}/{draft.id}")
        assert_api_error(r, 404, "not_found")
        r = await client_admin.get(f"{MATERIALS}/{archived.id}")
        assert_api_error(r, 404, "not_found")
        r = await client_admin.get(MATERIALS, params={"status": "draft"})
        assert r.status_code == 200
        ids = {x["id"] for x in r.json()}
        assert str(draft.id) not in ids
        assert str(archived.id) not in ids


async def test_material_idp_groups_visibility(
    client_admin: AsyncClient,
    sqlite_session: AsyncSession,
) -> None:
    outstaff = await add_material(sqlite_session, title="Outstaff", idp_groups=["outstaff"])
    students = await add_material(sqlite_session, title="Students", idp_groups=[IDP_GROUP_DEVELOPER])
    admin_only = await add_material(sqlite_session, title="Admin", idp_groups=[IDP_GROUP_PORTAL_ADMIN])
    await sqlite_session.commit()

    with as_user_regular():
        r = await client_admin.get(f"{MATERIALS}/{outstaff.id}")
        assert r.status_code == 200
        assert r.json()["title"] == "Outstaff"
        r = await client_admin.get(f"{MATERIALS}/{students.id}")
        assert_api_error(r, 404, "not_found")
        r = await client_admin.get(f"{MATERIALS}/{admin_only.id}")
        assert_api_error(r, 404, "not_found")

    with as_user(user_portal_no_idp_groups):
        r = await client_admin.get(f"{MATERIALS}/{outstaff.id}")
        assert_api_error(r, 404, "not_found")
        listed = await client_admin.get(MATERIALS)
        assert listed.status_code == 200
        assert str(outstaff.id) not in {x["id"] for x in listed.json()}


async def test_materials_pagination_skips_hidden(
    client_admin: AsyncClient,
    sqlite_session: AsyncSession,
) -> None:
    base = datetime(2030, 1, 1, tzinfo=UTC)
    visible_1 = await add_material(sqlite_session, title="v1", created_at=base)
    await add_material(
        sqlite_session,
        title="hidden",
        idp_groups=[IDP_GROUP_PORTAL_ADMIN],
        created_at=base + timedelta(seconds=1),
    )
    visible_2 = await add_material(sqlite_session, title="v2", created_at=base + timedelta(seconds=2))
    await sqlite_session.commit()

    with as_user_regular():
        page1 = await client_admin.get(MATERIALS, params={"limit": 1, "offset": 0})
        assert page1.status_code == 200
        assert [m["id"] for m in page1.json()] == [str(visible_2.id)]
        page2 = await client_admin.get(MATERIALS, params={"limit": 1, "offset": 1})
        assert page2.status_code == 200
        assert [m["id"] for m in page2.json()] == [str(visible_1.id)]


async def test_checklist_hidden_and_pagination(
    client_admin: AsyncClient,
    sqlite_session: AsyncSession,
) -> None:
    base = datetime(2030, 1, 1, tzinfo=UTC)
    vis1, _ = await add_checklist(sqlite_session, title="v1", items=["a"], created_at=base)
    hidden, _ = await add_checklist(
        sqlite_session,
        title="hidden",
        items=["a"],
        idp_group=IDP_GROUP_PORTAL_ADMIN,
        created_at=base + timedelta(seconds=1),
    )
    vis2, _ = await add_checklist(sqlite_session, title="v2", items=["a"], created_at=base + timedelta(seconds=2))
    await sqlite_session.commit()

    r = await client_admin.get(f"{CHECKLISTS}/{hidden.id}")
    assert r.status_code == 200

    with as_user_regular():
        r = await client_admin.get(f"{CHECKLISTS}/{hidden.id}")
        assert_api_error(r, 404, "not_found")
        r = await client_admin.post(f"{CHECKLISTS}/{hidden.id}/start")
        assert_api_error(r, 404, "not_found")
        page1 = await client_admin.get(CHECKLISTS, params={"limit": 1, "offset": 0})
        assert [c["id"] for c in page1.json()] == [str(vis2.id)]
        page2 = await client_admin.get(CHECKLISTS, params={"limit": 1, "offset": 1})
        assert [c["id"] for c in page2.json()] == [str(vis1.id)]


async def test_checklist_progress_hidden_after_idp_change(
    client_admin: AsyncClient,
    sqlite_session: AsyncSession,
) -> None:
    cl, items = await add_checklist(sqlite_session, title="Онбординг", items=["Шаг"])
    await sqlite_session.commit()

    with as_user_regular():
        r = await client_admin.post(f"{CHECKLISTS}/{cl.id}/start")
        assert r.status_code == 201, r.text

    r = await client_admin.patch(
        f"{CHECKLISTS}/{cl.id}",
        json={"expected_version": cl.version, "idp_group": IDP_GROUP_PORTAL_ADMIN},
    )
    assert r.status_code == 200

    with as_user_regular():
        r = await client_admin.get(f"{CHECKLISTS}/{cl.id}/my-progress")
        assert_api_error(r, 404, "not_found")
        r = await client_admin.patch(
            f"{CHECKLISTS}/{cl.id}/items/{items[0].id}",
            json={"is_done": True},
        )
        assert_api_error(r, 404, "not_found")


async def test_checklist_item_idor(
    client_user: AsyncClient,
    sqlite_session: AsyncSession,
) -> None:
    cl_a, _items_a = await add_checklist(sqlite_session, title="A", items=["a"])
    _cl_b, items_b = await add_checklist(sqlite_session, title="B", items=["b"])
    await sqlite_session.commit()

    r = await client_user.post(f"{CHECKLISTS}/{cl_a.id}/start")
    assert r.status_code == 201, r.text
    r = await client_user.patch(
        f"{CHECKLISTS}/{cl_a.id}/items/{items_b[0].id}",
        json={"is_done": True},
    )
    assert_api_error(r, 404, "not_found")


async def test_hidden_quiz_is_404_not_403(
    client_admin: AsyncClient,
    sqlite_session: AsyncSession,
) -> None:
    mat = await add_material(sqlite_session, title="Секрет", idp_groups=[IDP_GROUP_PORTAL_ADMIN])
    quiz, _q, _ok, _bad = await add_quiz_with_question(sqlite_session, title="Скрытый", material_id=mat.id)
    await sqlite_session.commit()

    with as_user_regular():
        r = await client_admin.get(f"{QUIZZES}/{quiz.id}")
        assert_api_error(r, 404, "not_found")
        r = await client_admin.post(f"{QUIZZES}/{quiz.id}/attempts")
        assert_api_error(r, 404, "not_found")
        r = await client_admin.get(f"{QUIZZES}/{quiz.id}/attempts")
        assert_api_error(r, 404, "not_found")
        listed = await client_admin.get(QUIZZES)
        assert listed.status_code == 200
        assert str(quiz.id) not in {x["id"] for x in listed.json()}


async def test_quizzes_pagination_skips_hidden(
    client_admin: AsyncClient,
    sqlite_session: AsyncSession,
) -> None:
    base = datetime(2030, 1, 1, tzinfo=UTC)
    q1, *_ = await add_quiz_with_question(sqlite_session, title="v1", created_at=base)
    mat = await add_material(sqlite_session, title="Секрет", idp_groups=[IDP_GROUP_PORTAL_ADMIN])
    await add_quiz_with_question(
        sqlite_session,
        title="hidden",
        material_id=mat.id,
        created_at=base + timedelta(seconds=1),
    )
    q2, *_ = await add_quiz_with_question(sqlite_session, title="v2", created_at=base + timedelta(seconds=2))
    await sqlite_session.commit()

    with as_user_regular():
        page1 = await client_admin.get(QUIZZES, params={"limit": 1, "offset": 0})
        assert [x["id"] for x in page1.json()] == [str(q2.id)]
        page2 = await client_admin.get(QUIZZES, params={"limit": 1, "offset": 1})
        assert [x["id"] for x in page2.json()] == [str(q1.id)]


async def test_quiz_card_hides_is_correct_for_edit_is_admin_only(
    client_admin: AsyncClient,
    sqlite_session: AsyncSession,
) -> None:
    quiz, _q, _ok, _bad = await add_quiz_with_question(sqlite_session, title="Карточка")
    await sqlite_session.commit()

    with as_user_regular():
        r = await client_admin.get(f"{QUIZZES}/{quiz.id}")
        assert r.status_code == 200
        answers = r.json()["questions"][0]["answers"]
        assert answers
        assert all("is_correct" not in a for a in answers)
        r = await client_admin.get(f"{QUIZZES}/{quiz.id}/for-edit")
        assert_api_error(r, 403, "forbidden")

    r = await client_admin.get(f"{QUIZZES}/{quiz.id}/for-edit")
    assert r.status_code == 200
    flags = {a["text"]: a["is_correct"] for a in r.json()["questions"][0]["answers"]}
    assert flags["4"] is True
    assert flags["5"] is False


async def test_quiz_attempt_idor(
    client_admin: AsyncClient,
    sqlite_session: AsyncSession,
) -> None:
    quiz_a, q_a, ok_a, _bad_a = await add_quiz_with_question(sqlite_session, title="A")
    quiz_b, _q_b, _ok_b, _bad_b = await add_quiz_with_question(sqlite_session, title="B")
    await sqlite_session.commit()

    with as_user_regular():
        started = await client_admin.post(f"{QUIZZES}/{quiz_a.id}/attempts")
        assert started.status_code == 201, started.text
        attempt_a = started.json()["id"]

    with as_user_b():
        r = await client_admin.post(
            f"{QUIZZES}/{quiz_a.id}/attempts/{attempt_a}/submit",
            json={"answers": [{"question_id": str(q_a.id), "answer_id": str(ok_a.id)}]},
        )
        assert_api_error(r, 404, "not_found")
        r = await client_admin.get(f"{QUIZZES}/{quiz_a.id}/attempts")
        assert r.status_code == 200
        assert r.json() == []

    with as_user_regular():
        r = await client_admin.post(
            f"{QUIZZES}/{quiz_b.id}/attempts/{attempt_a}/submit",
            json={"answers": [{"question_id": str(q_a.id), "answer_id": str(ok_a.id)}]},
        )
        assert_api_error(r, 404, "not_found")
