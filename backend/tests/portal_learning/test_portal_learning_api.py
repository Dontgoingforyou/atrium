"""HTTP-контракт обучения: CRUD, прогресс, скоринг, валидация."""

from __future__ import annotations

import uuid

import pytest
from app.core.enums import UserChecklistStatus
from app.infrastructure.db.models.portal_learning import PortalQuizAnswer, PortalQuizQuestion
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.portal_learning.conftest import (
    CHECKLISTS,
    MATERIALS,
    QUIZZES,
    add_checklist,
    add_material,
    add_quiz_with_question,
    as_user_regular,
    assert_api_error,
    assert_pydantic_422,
)


@pytest.mark.parametrize(
    ("method", "path", "kwargs"),
    [
        ("GET", MATERIALS, {"params": {"limit": 0}}),
        ("GET", MATERIALS, {"params": {"limit": 501}}),
        ("GET", CHECKLISTS, {"params": {"offset": -1}}),
        ("POST", MATERIALS, {"json": {"title": "", "material_type": "article"}}),
        ("POST", CHECKLISTS, {"json": {"title": ""}}),
        ("POST", QUIZZES, {"json": {"title": ""}}),
        ("POST", MATERIALS, {"json": {"title": "X", "material_type": "nope"}}),
        ("DELETE", f"{MATERIALS}/not-a-uuid", {}),
        ("GET", f"{QUIZZES}/not-a-uuid/for-edit", {}),
    ],
)
async def test_learning_validation_returns_422(
    client_admin: AsyncClient,
    method: str,
    path: str,
    kwargs: dict[str, object],
) -> None:
    r = await client_admin.request(method, path, **kwargs)
    assert_pydantic_422(r)


async def test_materials_crud_as_admin(client_admin: AsyncClient) -> None:
    r = await client_admin.post(
        MATERIALS,
        json={
            "title": "Материал для теста",
            "body": "Текст",
            "material_type": "article",
            "status": "active",
            "idp_groups": ["no-such-idp-group", "outstaff"],
        },
    )
    assert r.status_code == 201, r.text
    created = r.json()
    mid = created["id"]
    assert created["title"] == "Материал для теста"
    assert created["status"] == "active"
    assert created["idp_groups"] == ["outstaff"]

    r = await client_admin.get(MATERIALS, params={"material_type": "article"})
    assert r.status_code == 200
    assert mid in {x["id"] for x in r.json()}

    r = await client_admin.patch(
        f"{MATERIALS}/{mid}",
        json={"expected_version": created["version"], "body": "Обновлённый текст"},
    )
    assert r.status_code == 200
    assert r.json()["body"] == "Обновлённый текст"

    r = await client_admin.delete(f"{MATERIALS}/{mid}")
    assert r.status_code == 204
    r = await client_admin.get(f"{MATERIALS}/{mid}")
    assert_api_error(r, 404, "not_found")


async def test_checklist_start_mark_complete_unmark(
    client_admin: AsyncClient,
    sqlite_session: AsyncSession,
) -> None:
    cl, items = await add_checklist(sqlite_session, title="Онбординг", items=["Шаг 1", "Шаг 2"])
    await sqlite_session.commit()
    item1, item2 = items[0].id, items[1].id

    with as_user_regular():
        first = await client_admin.post(f"{CHECKLISTS}/{cl.id}/start")
        assert first.status_code == 201, first.text
        assert first.json()["checklist_id"] == str(cl.id)
        again = await client_admin.post(f"{CHECKLISTS}/{cl.id}/start")
        assert again.status_code == 201
        assert again.json()["id"] == first.json()["id"]

        r = await client_admin.get(f"{CHECKLISTS}/{cl.id}/my-progress")
        assert r.status_code == 200
        assert r.json()["status"] == UserChecklistStatus.IN_PROGRESS.value

        r = await client_admin.patch(f"{CHECKLISTS}/{cl.id}/items/{item1}", json={"is_done": True})
        assert r.status_code == 200
        marks = {m["item_id"]: m["is_done"] for m in r.json()["item_marks"]}
        assert marks[str(item1)] is True
        assert r.json()["status"] == UserChecklistStatus.IN_PROGRESS.value

        r = await client_admin.patch(f"{CHECKLISTS}/{cl.id}/items/{item2}", json={"is_done": True})
        assert r.status_code == 200
        assert r.json()["status"] == UserChecklistStatus.COMPLETED.value
        assert r.json()["completed_at"] is not None

        r = await client_admin.patch(f"{CHECKLISTS}/{cl.id}/items/{item2}", json={"is_done": False})
        assert r.status_code == 200
        assert r.json()["status"] == UserChecklistStatus.IN_PROGRESS.value
        assert r.json()["completed_at"] is None


async def test_checklist_progress_requires_start(
    client_user: AsyncClient,
    sqlite_session: AsyncSession,
) -> None:
    cl, items = await add_checklist(sqlite_session, title="ЧЛ", items=["a"])
    await sqlite_session.commit()
    r = await client_user.get(f"{CHECKLISTS}/{cl.id}/my-progress")
    assert_api_error(r, 404, "not_found")
    r = await client_user.patch(f"{CHECKLISTS}/{cl.id}/items/{items[0].id}", json={"is_done": True})
    assert_api_error(r, 404, "not_found")


async def test_checklist_unknown_idp_group_normalized(
    client_admin: AsyncClient,
) -> None:
    r = await client_admin.post(
        CHECKLISTS,
        json={"title": "Неизвестная группа", "idp_group": "no-such-idp-group", "items": ["Шаг 1"]},
    )
    assert r.status_code == 201, r.text
    cid = r.json()["id"]
    assert r.json()["idp_group"] == ""

    r = await client_admin.patch(
        f"{CHECKLISTS}/{cid}",
        json={"expected_version": r.json()["version"], "items": ["Новый"]},
    )
    assert r.status_code == 200
    assert [i["text"] for i in r.json()["items"]] == ["Новый"]

    r = await client_admin.delete(f"{CHECKLISTS}/{cid}")
    assert r.status_code == 204
    r = await client_admin.get(f"{CHECKLISTS}/{cid}")
    assert_api_error(r, 404, "not_found")


async def test_checklist_replace_items_resets_progress(
    client_admin: AsyncClient,
    sqlite_session: AsyncSession,
) -> None:
    cl, items = await add_checklist(sqlite_session, title="ЧЛ", items=["Старый"])
    await sqlite_session.commit()

    with as_user_regular():
        r = await client_admin.post(f"{CHECKLISTS}/{cl.id}/start")
        assert r.status_code == 201
        r = await client_admin.patch(f"{CHECKLISTS}/{cl.id}/items/{items[0].id}", json={"is_done": True})
        assert r.status_code == 200

    r = await client_admin.patch(
        f"{CHECKLISTS}/{cl.id}",
        json={"expected_version": cl.version, "items": ["Новый пункт"]},
    )
    assert r.status_code == 200

    with as_user_regular():
        r = await client_admin.get(f"{CHECKLISTS}/{cl.id}/my-progress")
        assert_api_error(r, 404, "not_found")


async def test_quiz_submit_scores_and_rejects_cheat(
    client_admin: AsyncClient,
    sqlite_session: AsyncSession,
) -> None:
    quiz, q1, ok1, bad1 = await add_quiz_with_question(sqlite_session, title="Тест знаний")

    q2 = PortalQuizQuestion(quiz_id=quiz.id, order_index=1, text="3+3?")
    sqlite_session.add(q2)
    await sqlite_session.flush()
    q2_ok = PortalQuizAnswer(question_id=q2.id, text="6", is_correct=True)
    sqlite_session.add(q2_ok)
    await sqlite_session.commit()

    with as_user_regular():
        first = await client_admin.post(f"{QUIZZES}/{quiz.id}/attempts")
        assert first.status_code == 201, first.text
        attempt1 = first.json()["id"]
        assert first.json()["max_score"] == 0

        second = await client_admin.post(f"{QUIZZES}/{quiz.id}/attempts")
        assert second.status_code == 201
        assert second.json()["id"] != attempt1

        r = await client_admin.post(
            f"{QUIZZES}/{quiz.id}/attempts/{attempt1}/submit",
            json={"answers": [{"question_id": str(q1.id), "answer_id": str(ok1.id)}]},
        )
        assert r.status_code == 200, r.text
        assert r.json()["score"] == 1
        assert r.json()["max_score"] == 2
        assert r.json()["finished_at"] is not None
        by_text = {a["text"]: a["is_correct"] for a in r.json()["answers"][0]["answers"]}
        assert by_text["4"] is True
        assert by_text["5"] is False

        r = await client_admin.post(
            f"{QUIZZES}/{quiz.id}/attempts/{attempt1}/submit",
            json={"answers": []},
        )
        assert_api_error(r, 403, "forbidden")

        r = await client_admin.post(
            f"{QUIZZES}/{quiz.id}/attempts/{second.json()['id']}/submit",
            json={
                "answers": [
                    {"question_id": str(q1.id), "answer_id": str(q2_ok.id)},
                    {"question_id": str(q2.id), "answer_id": str(bad1.id)},
                ]
            },
        )
        assert r.status_code == 200, r.text
        assert r.json()["score"] == 0

        hist = await client_admin.get(f"{QUIZZES}/{quiz.id}/attempts")
        assert hist.status_code == 200
        assert len(hist.json()) == 2


async def test_quiz_empty_submit_scores_zero(
    client_user: AsyncClient,
    sqlite_session: AsyncSession,
) -> None:
    quiz, _q, _ok, _bad = await add_quiz_with_question(sqlite_session, title="Пустой")
    await sqlite_session.commit()
    started = await client_user.post(f"{QUIZZES}/{quiz.id}/attempts")
    assert started.status_code == 201
    r = await client_user.post(
        f"{QUIZZES}/{quiz.id}/attempts/{started.json()['id']}/submit",
        json={"answers": []},
    )
    assert r.status_code == 200, r.text
    assert r.json()["score"] == 0
    assert r.json()["max_score"] == 1


async def test_quiz_update_replace_questions_and_delete(
    client_admin: AsyncClient,
    sqlite_session: AsyncSession,
) -> None:
    quiz, q1, ok1, _bad = await add_quiz_with_question(sqlite_session, title="Старое")
    await sqlite_session.commit()

    r = await client_admin.patch(f"{QUIZZES}/{quiz.id}", json={"title": "Новое название"})
    assert r.status_code == 200
    assert r.json()["title"] == "Новое название"

    with as_user_regular():
        started = await client_admin.post(f"{QUIZZES}/{quiz.id}/attempts")
        assert started.status_code == 201
        r = await client_admin.post(
            f"{QUIZZES}/{quiz.id}/attempts/{started.json()['id']}/submit",
            json={"answers": [{"question_id": str(q1.id), "answer_id": str(ok1.id)}]},
        )
        assert r.status_code == 200
        hist = await client_admin.get(f"{QUIZZES}/{quiz.id}/attempts")
        assert len(hist.json()) == 1

    r = await client_admin.put(
        f"{QUIZZES}/{quiz.id}/questions",
        json={"questions": [{"text": "Новый?", "answers": [{"text": "да", "is_correct": True}]}]},
    )
    assert r.status_code == 200, r.text
    assert r.json()["questions"][0]["text"] == "Новый?"

    with as_user_regular():
        hist = await client_admin.get(f"{QUIZZES}/{quiz.id}/attempts")
        assert hist.status_code == 200
        assert hist.json() == []

    r = await client_admin.patch(f"{QUIZZES}/{quiz.id}", json={"material_id": str(uuid.uuid4())})
    assert_api_error(r, 404, "not_found")

    r = await client_admin.delete(f"{QUIZZES}/{quiz.id}")
    assert r.status_code == 204
    r = await client_admin.get(f"{QUIZZES}/{quiz.id}")
    assert_api_error(r, 404, "not_found")


async def test_quiz_bind_existing_material(
    client_admin: AsyncClient,
    sqlite_session: AsyncSession,
) -> None:
    mat = await add_material(sqlite_session, title="Связанный")
    await sqlite_session.commit()
    r = await client_admin.post(QUIZZES, json={"title": "С материалом", "material_id": str(mat.id)})
    assert r.status_code == 201, r.text
    assert r.json()["material_id"] == str(mat.id)
