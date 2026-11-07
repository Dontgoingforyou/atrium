"""HTTP-контракт глобального полнотекстового поиска."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from app.core.enums import TaskPriority, TaskStatus
from app.infrastructure.db.models.portal_document import PortalDocument
from app.infrastructure.db.models.portal_manager_specialist import PortalManagerSpecialist
from app.infrastructure.db.models.portal_specialist_column import PortalSpecialistColumn
from app.infrastructure.db.models.portal_specialist_status import PortalSpecialistStatus
from app.infrastructure.db.models.portal_task import PortalTask
from app.infrastructure.db.models.portal_user_profile import PortalUserProfile
from app.portal_search.services.search import merge_cap
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.helpers.portal_test_users import (
    user_portal_manager,
    user_portal_no_idp_groups,
    user_portal_regular,
    user_portal_user_b,
)
from tests.portal_calendar.conftest import create_event, ensure_primary
from tests.portal_documents.conftest import DOCS_ADMIN, create_doc
from tests.portal_search.conftest import SEARCH_API, as_user, assert_api_error, assert_pydantic_422


def test_search_merge_cap_respects_max() -> None:
    assert merge_cap(400, 200) == 500


@pytest.mark.parametrize(
    "path",
    [
        f"{SEARCH_API}?q=ab",
        f"{SEARCH_API}?q=ab&types=document",
    ],
)
async def test_search_requires_auth(client_sqlite_only: AsyncClient, path: str) -> None:
    r = await client_sqlite_only.get(path)
    assert_api_error(r, 401, "unauthorized")


@pytest.mark.parametrize(
    "path",
    [
        f"{SEARCH_API}?q=ab",
        f"{SEARCH_API}?q=ab&types=document",
    ],
)
async def test_search_timesheet_forbidden(client_developer: AsyncClient, path: str) -> None:
    r = await client_developer.get(path)
    assert_api_error(r, 403, "forbidden")


async def test_search_q_too_short_after_trim_returns_422(client_admin: AsyncClient) -> None:
    r = await client_admin.get(f"{SEARCH_API}?q=a")
    assert_api_error(r, 422, "validation_error")


async def test_search_q_whitespace_only_returns_422(client_admin: AsyncClient) -> None:
    r = await client_admin.get(f"{SEARCH_API}?q=%20%20")
    assert_api_error(r, 422, "validation_error")


async def test_search_unknown_entity_type_returns_422(client_admin: AsyncClient) -> None:
    r = await client_admin.get(f"{SEARCH_API}?q=ab&types=chat")
    assert_api_error(r, 422, "validation_error")


async def test_search_types_agreement_rejected(client_admin: AsyncClient) -> None:
    r = await client_admin.get(f"{SEARCH_API}?q=ab&types=agreement")
    assert_api_error(r, 422, "validation_error")


async def test_search_limit_out_of_range_is_pydantic_422(client_admin: AsyncClient) -> None:
    r = await client_admin.get(f"{SEARCH_API}?q=ab&limit=0")
    assert_pydantic_422(r)


async def test_search_finds_active_document_by_substring(client_admin: AsyncClient) -> None:
    doc = await create_doc(
        client_admin,
        title="Прочее",
        body="Внутри есть маркерSEARCHMARKER123",
    )
    r = await client_admin.get(f"{SEARCH_API}?q=SEARCHMARKER123")
    assert r.status_code == 200, r.text
    data = r.json()
    assert any(h["document"]["id"] == doc["id"] for h in data if h["entity_type"] == "document")


async def test_search_soft_deleted_document_excluded(client_admin: AsyncClient) -> None:
    marker = "SOFTDELSEARCH77"
    doc = await create_doc(client_admin, title=f"Живой {marker}", body="x")
    trashed = await create_doc(client_admin, title=f"Корзина {marker}", body="x")
    r = await client_admin.delete(f"{DOCS_ADMIN}/{trashed['id']}")
    assert r.status_code == 204, r.text

    r = await client_admin.get(f"{SEARCH_API}?q={marker}&types=document")
    assert r.status_code == 200, r.text
    ids = {h["document"]["id"] for h in r.json() if h["entity_type"] == "document"}
    assert doc["id"] in ids
    assert trashed["id"] not in ids


async def test_search_escapes_like_wildcards(client_admin: AsyncClient) -> None:
    doc = await create_doc(client_admin, title=r"50%_скидка", body="x")
    r = await client_admin.get(f"{SEARCH_API}?q=50%_скидка")
    assert r.status_code == 200, r.text
    ids = {h["document"]["id"] for h in r.json() if h["entity_type"] == "document"}
    assert doc["id"] in ids


async def test_search_non_manager_sees_all_active_documents(
    client_admin: AsyncClient,
    sqlite_session: AsyncSession,
) -> None:
    """Разделов с ограничением доступа нет — активные документы видны без менеджерской роли."""
    doc_a = PortalDocument(title="ПерваяМаркерRBACX7", author_sub="admin-sub", body="текст")
    doc_b = PortalDocument(title="ВтораяМаркерRBACX7", author_sub="admin-sub", body="текст")
    sqlite_session.add_all([doc_a, doc_b])
    await sqlite_session.commit()

    with as_user(user_portal_no_idp_groups):
        r = await client_admin.get(f"{SEARCH_API}?q=RBACX7")
    assert r.status_code == 200, r.text
    ids = {h["document"]["id"] for h in r.json() if h["entity_type"] == "document"}
    assert str(doc_a.id) in ids
    assert str(doc_b.id) in ids


async def test_search_multi_types_document_and_task_merges(client_admin: AsyncClient) -> None:
    marker = "MERGEMULTI99ZZ"
    await create_doc(client_admin, title="t", body=f"prefix {marker} suffix")
    r = await client_admin.post(
        "/api/v1/portal/chats",
        json={"title": "merge-ch", "member_subs": [user_portal_regular().sub]},
    )
    cid = r.json()["id"]
    r2 = await client_admin.post(f"/api/v1/portal/chats/{cid}/messages", json={"body": "msg"})
    mid = r2.json()["id"]
    await client_admin.post(
        "/api/v1/portal/tasks",
        json={
            "title": f"task-{marker}",
            "source_message_id": mid,
            "chat_id": cid,
            "assignee_sub": "admin-sub",
        },
    )
    r = await client_admin.get(f"{SEARCH_API}?q={marker}&types=document&types=task")
    assert r.status_code == 200, r.text
    types_found = {h["entity_type"] for h in r.json()}
    assert "document" in types_found
    assert "task" in types_found


async def test_search_long_chat_message_uses_excerpt_truncation(client_admin: AsyncClient) -> None:
    tail = "UNIQUELONGEX99"
    long_body = ("x" * 260) + tail
    r = await client_admin.post("/api/v1/portal/chats/direct", json={"other_user_sub": "user-b"})
    assert r.status_code == 200, r.text
    cid = r.json()["id"]
    await client_admin.post(f"/api/v1/portal/chats/{cid}/messages", json={"body": long_body})
    r = await client_admin.get(f"{SEARCH_API}?q={tail}&types=chat_message")
    assert r.status_code == 200, r.text
    hit = next(h for h in r.json() if h["entity_type"] == "chat_message")
    excerpt = hit["message"]["body_excerpt"]
    assert "…" in excerpt
    assert len(excerpt) < len(long_body)


def _naive_utc(s: str) -> datetime:
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt


def _search_hit_created_at(h: dict) -> datetime:
    et = h["entity_type"]
    if et == "document":
        return _naive_utc(h["document"]["created_at"])
    if et == "task":
        return _naive_utc(h["task"]["created_at"])
    if et == "chat_message":
        return _naive_utc(h["message"]["created_at"])
    msg = f"неизвестный entity_type: {et}"
    raise AssertionError(msg)


async def test_search_types_task_finds_by_title(client_admin: AsyncClient) -> None:
    marker = "TASKONLYS9MS6"
    r = await client_admin.post(
        "/api/v1/portal/chats",
        json={"title": f"tk-{marker}", "member_subs": [user_portal_regular().sub]},
    )
    cid = r.json()["id"]
    r2 = await client_admin.post(f"/api/v1/portal/chats/{cid}/messages", json={"body": "m"})
    mid = r2.json()["id"]
    r3 = await client_admin.post(
        "/api/v1/portal/tasks",
        json={
            "title": f"task {marker} title",
            "source_message_id": mid,
            "chat_id": cid,
            "assignee_sub": "admin-sub",
        },
    )
    assert r3.status_code == 201, r3.text
    r = await client_admin.get(f"{SEARCH_API}?q={marker}&types=task")
    assert r.status_code == 200, r.text
    hits = r.json()
    assert all(h["entity_type"] == "task" for h in hits)
    assert str(r3.json()["id"]) in {h["task"]["id"] for h in hits}


async def test_search_task_with_custom_kanban_status_does_not_500(
    client_admin: AsyncClient,
    sqlite_session: AsyncSession,
) -> None:
    """Динамический status_key канбана не должен валить fulltext search."""
    marker = "CUSTSTATSEARCH42"
    tsk = PortalTask(
        title=f"Задача {marker}",
        description=None,
        creator_sub="admin-sub",
        assignee_sub="admin-sub",
        status="col_review_custom",
        priority=TaskPriority.MEDIUM,
        document_id=None,
        source_message_id=None,
        chat_id=None,
    )
    sqlite_session.add(tsk)
    await sqlite_session.commit()
    await sqlite_session.refresh(tsk)

    r = await client_admin.get(f"{SEARCH_API}?q={marker}&types=task")
    assert r.status_code == 200, r.text
    task_hit = next(h for h in r.json() if h["entity_type"] == "task")
    assert task_hit["task"]["status"] == "col_review_custom"
    assert task_hit["task"]["id"] == str(tsk.id)


async def test_search_multitype_document_and_task_order_by_date_desc(client_admin: AsyncClient) -> None:
    marker = "DTSORTMS6ZZ"
    await create_doc(client_admin, title="d", body=f"doc {marker} body here")
    r = await client_admin.post(
        "/api/v1/portal/chats",
        json={"title": f"ch-{marker}", "member_subs": [user_portal_regular().sub]},
    )
    cid = r.json()["id"]
    r2 = await client_admin.post(f"/api/v1/portal/chats/{cid}/messages", json={"body": "x"})
    mid = r2.json()["id"]
    t = await client_admin.post(
        "/api/v1/portal/tasks",
        json={
            "title": f"title-{marker}-task",
            "source_message_id": mid,
            "chat_id": cid,
            "assignee_sub": "admin-sub",
        },
    )
    assert t.status_code == 201, t.text
    r = await client_admin.get(f"{SEARCH_API}?q={marker}&types=document&types=task")
    assert r.status_code == 200, r.text
    hits = r.json()
    assert {h["entity_type"] for h in hits} == {"document", "task"}
    dts = [_search_hit_created_at(h) for h in hits]
    assert dts == sorted(dts, reverse=True)


async def test_search_merged_document_chat_message_and_task(client_admin: AsyncClient) -> None:
    marker = "THREETYPE99ZZ"
    await create_doc(client_admin, title="t", body=f"doc {marker}")
    r = await client_admin.post("/api/v1/portal/chats/direct", json={"other_user_sub": "user-b"})
    assert r.status_code == 200, r.text
    cid = r.json()["id"]
    r2 = await client_admin.post(f"/api/v1/portal/chats/{cid}/messages", json={"body": f"chat {marker}"})
    mid = r2.json()["id"]
    await client_admin.post(
        "/api/v1/portal/tasks",
        json={
            "title": f"task {marker}",
            "source_message_id": mid,
            "chat_id": cid,
            "assignee_sub": "admin-sub",
        },
    )
    r = await client_admin.get(
        f"{SEARCH_API}?q={marker}&types=document&types=chat_message&types=task",
    )
    assert r.status_code == 200, r.text
    assert {h["entity_type"] for h in r.json()} == {"document", "chat_message", "task"}


async def test_search_multitype_author_sees_own_task_and_docs(
    client_admin: AsyncClient,
    sqlite_session: AsyncSession,
) -> None:
    doc = PortalDocument(title="Секрет MULTIMARK99RBAC", author_sub="user-no-idp", body="т")
    tsk = PortalTask(
        title="Задача MULTIMARK99RBAC",
        description=None,
        creator_sub="user-no-idp",
        assignee_sub=None,
        status=TaskStatus.TODO,
        priority=TaskPriority.MEDIUM,
        document_id=None,
        source_message_id=None,
        chat_id=None,
    )
    sqlite_session.add_all([doc, tsk])
    await sqlite_session.commit()
    await sqlite_session.refresh(tsk)

    with as_user(user_portal_no_idp_groups):
        r = await client_admin.get(f"{SEARCH_API}?q=MULTIMARK99RBAC&types=document&types=task")
    assert r.status_code == 200, r.text
    hits = r.json()
    assert {h["entity_type"] for h in hits} == {"task", "document"}
    assert str(tsk.id) in {h["task"]["id"] for h in hits if h["entity_type"] == "task"}


async def test_search_tag_slug_filters_documents(client_admin: AsyncClient) -> None:
    r_tag = await client_admin.post(
        "/api/v1/portal/tags",
        json={"name": "Тег поиска TAGSEARCHUNIQ88", "color": "#AABBCC"},
    )
    assert r_tag.status_code == 201, r_tag.text
    tag = r_tag.json()

    doc_with_tag = await create_doc(
        client_admin,
        title="TAGSEARCHUNIQ88 с тегом",
        body="TAGSEARCHUNIQ88 контент",
        tag_ids=[tag["id"]],
    )
    doc_without = await create_doc(
        client_admin,
        title="TAGSEARCHUNIQ88 без тега",
        body="TAGSEARCHUNIQ88 другой",
        tag_ids=[],
    )

    r = await client_admin.get(
        f"{SEARCH_API}?q=TAGSEARCHUNIQ88&types=document&tag_slug={tag['slug']}",
    )
    assert r.status_code == 200, r.text
    ids = {h["document"]["id"] for h in r.json() if h["entity_type"] == "document"}
    assert doc_with_tag["id"] in ids
    assert doc_without["id"] not in ids


async def test_search_unknown_tag_slug_returns_empty(client_admin: AsyncClient) -> None:
    await create_doc(client_admin, title="TAGSEARCHUNIQ99 нет тега", body="TAGSEARCHUNIQ99 x")
    r = await client_admin.get(
        f"{SEARCH_API}?q=TAGSEARCHUNIQ99&types=document&tag_slug=nonexistent-tag-xyzzy",
    )
    assert r.status_code == 200, r.text
    assert [h for h in r.json() if h["entity_type"] == "document"] == []


async def test_search_status_ids_ignored_for_documents(client_admin: AsyncClient) -> None:
    """status_ids — legacy фильтр специалистов; на document-поиск не влияет."""
    marker = "STATUSIDIGNORED55"
    doc = await create_doc(client_admin, title=marker, body="x")
    fake_status = uuid.uuid4()
    r = await client_admin.get(
        f"{SEARCH_API}?q={marker}&types=document&status_ids={fake_status}",
    )
    assert r.status_code == 200, r.text
    ids = {h["document"]["id"] for h in r.json() if h["entity_type"] == "document"}
    assert doc["id"] in ids


async def test_search_specialist_non_manager_degrades_to_empty(
    client_admin: AsyncClient,
    sqlite_session: AsyncSession,
) -> None:
    """Нет прав на специалистов → пустой список, не 403/500 на весь /search."""
    sqlite_session.add(
        PortalUserProfile(
            sub="spec-search-sub",
            email="spec.search@example.com",
            full_name="СпецМаркерSPECDEGRADE01",
            username="specsearch",
            portal_chat_allowed=False,
        )
    )
    sqlite_session.add(PortalSpecialistColumn(key="new", title="Новичок", color="#6366f1", position=0))
    sqlite_session.add(
        PortalManagerSpecialist(
            manager_sub="manager-sub",
            specialist_sub="spec-search-sub",
            column_key="new",
            position=0,
        )
    )
    await sqlite_session.commit()

    with as_user(user_portal_no_idp_groups):
        r = await client_admin.get(f"{SEARCH_API}?q=SPECDEGRADE01&types=specialist")
    assert r.status_code == 200, r.text
    assert r.json() == []


async def test_search_specialist_manager_sees_own(
    client_admin: AsyncClient,
    sqlite_session: AsyncSession,
) -> None:
    marker = "SPECMGRHIT88"
    sqlite_session.add(
        PortalUserProfile(
            sub="spec-mgr-hit-sub",
            email=f"{marker.lower()}@example.com",
            full_name=f"Имя {marker}",
            username="specmgrhit",
            portal_chat_allowed=False,
        )
    )
    sqlite_session.add(PortalSpecialistColumn(key="new", title="Новичок", color="#6366f1", position=0))
    sqlite_session.add(
        PortalManagerSpecialist(
            manager_sub=user_portal_manager().sub,
            specialist_sub="spec-mgr-hit-sub",
            column_key="new",
            position=0,
        )
    )
    await sqlite_session.commit()

    with as_user(user_portal_manager):
        r = await client_admin.get(f"{SEARCH_API}?q={marker}&types=specialist")
    assert r.status_code == 200, r.text
    hits = r.json()
    assert len(hits) == 1
    assert hits[0]["entity_type"] == "specialist"
    assert hits[0]["specialist"]["sub"] == "spec-mgr-hit-sub"


async def test_search_specialist_status_ids_filter_via_public_helper(
    sqlite_session: AsyncSession,
) -> None:
    """Фильтр status_ids на SQLite — через публичный specialist_subs_for_status_ids
    (fulltext SQL использует PG ANY; здесь проверяем контракт фильтра на реальной БД).
    """
    from app.portal_search.services.search_filters import specialist_subs_for_status_ids

    status_a = PortalSpecialistStatus(title="Направление A", color="#111111")
    status_b = PortalSpecialistStatus(title="Направление B", color="#222222")
    sqlite_session.add_all([status_a, status_b])
    await sqlite_session.flush()
    sqlite_session.add(PortalSpecialistColumn(key="new", title="Новичок", color="#6366f1", position=0))
    sqlite_session.add_all(
        [
            PortalManagerSpecialist(
                manager_sub="manager-sub",
                specialist_sub="spec-a-sub",
                column_key="new",
                position=0,
                status_id=status_a.id,
            ),
            PortalManagerSpecialist(
                manager_sub="manager-sub",
                specialist_sub="spec-b-sub",
                column_key="new",
                position=1,
                status_id=status_b.id,
            ),
        ]
    )
    await sqlite_session.commit()

    allowed = await specialist_subs_for_status_ids(sqlite_session, [status_a.id])
    assert allowed == {"spec-a-sub"}


async def test_search_calendar_event_own_hit_and_peer_silent_drop(
    client_user: AsyncClient,
) -> None:
    marker = "CALSEARCHHIT99"
    primary_a = await ensure_primary(client_user)
    starts = datetime.now(UTC) + timedelta(days=2)
    starts = starts.replace(hour=11, minute=0, second=0, microsecond=0)

    own = await create_event(
        client_user,
        primary_a["id"],
        title=f"Моё {marker}",
        starts_at=starts,
        organizer_sub="user-sub",
    )

    with as_user(user_portal_user_b):
        primary_b = await ensure_primary(client_user)
        peer = await create_event(
            client_user,
            primary_b["id"],
            title=f"Чужое {marker}",
            starts_at=starts + timedelta(hours=2),
            organizer_sub="user-b",
        )

    r = await client_user.get(f"{SEARCH_API}?q={marker}&types=calendar_event")
    assert r.status_code == 200, r.text
    hits = r.json()
    assert all(h["entity_type"] == "calendar_event" for h in hits)
    ids = {h["calendar_event"]["id"] for h in hits}
    assert own["id"] in ids
    assert peer["id"] not in ids


async def test_search_multitype_arbitrary_query_does_not_error(client_admin: AsyncClient) -> None:
    """Произвольный запрос с specialist не падает (degrade → [])."""
    r = await client_admin.get(
        f"{SEARCH_API}?q=2222&types=document&types=chat_message&types=task&types=specialist&skip=0&limit=20",
    )
    assert r.status_code == 200, r.text
    assert isinstance(r.json(), list)
