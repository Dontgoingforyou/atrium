"""Юнит-тесты пост-фильтров семантического поиска."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock

import pytest
from app.core.portal_search_constants import (
    PORTAL_SEARCH_ENTITY_TYPE_CALENDAR_EVENT,
    PORTAL_SEARCH_ENTITY_TYPE_DOCUMENT,
    PORTAL_SEARCH_ENTITY_TYPE_SPECIALIST,
    PORTAL_SEARCH_ENTITY_TYPE_TASK,
)
from app.portal_search.services import search_filters as svc


@pytest.mark.asyncio
async def test_filter_semantic_hits_by_tag_slug(monkeypatch: pytest.MonkeyPatch) -> None:
    doc_id = uuid.uuid4()
    monkeypatch.setattr(
        svc,
        "document_ids_for_tag_slugs",
        AsyncMock(return_value={doc_id}),
    )
    monkeypatch.setattr(
        svc,
        "specialist_subs_for_status_ids",
        AsyncMock(return_value=set()),
    )

    hits = [
        {"entity_type": PORTAL_SEARCH_ENTITY_TYPE_DOCUMENT, "entity_id": str(doc_id)},
        {"entity_type": PORTAL_SEARCH_ENTITY_TYPE_DOCUMENT, "entity_id": str(uuid.uuid4())},
        {"entity_type": PORTAL_SEARCH_ENTITY_TYPE_TASK, "entity_id": str(uuid.uuid4())},
    ]
    session = AsyncMock()
    out = await svc.filter_semantic_hits(session, hits, tag_slugs=["urgent"], status_ids=None)
    assert len(out) == 2
    assert all(h["entity_type"] != PORTAL_SEARCH_ENTITY_TYPE_DOCUMENT or h["entity_id"] == str(doc_id) for h in out)


@pytest.mark.asyncio
async def test_filter_semantic_hits_by_status_ids(monkeypatch: pytest.MonkeyPatch) -> None:
    status_id = uuid.uuid4()
    monkeypatch.setattr(
        svc,
        "document_ids_for_tag_slugs",
        AsyncMock(return_value=set()),
    )
    monkeypatch.setattr(
        svc,
        "specialist_subs_for_status_ids",
        AsyncMock(return_value={"sub-allowed"}),
    )

    hits = [
        {
            "entity_type": PORTAL_SEARCH_ENTITY_TYPE_SPECIALIST,
            "entity_id": "sub-allowed",
            "meta": {},
        },
        {
            "entity_type": PORTAL_SEARCH_ENTITY_TYPE_SPECIALIST,
            "entity_id": "sub-other",
            "meta": {},
        },
        {"entity_type": PORTAL_SEARCH_ENTITY_TYPE_TASK, "entity_id": str(uuid.uuid4())},
    ]
    session = AsyncMock()
    out = await svc.filter_semantic_hits(session, hits, tag_slugs=None, status_ids=[status_id])
    assert len(out) == 2
    specialist_hits = [h for h in out if h["entity_type"] == PORTAL_SEARCH_ENTITY_TYPE_SPECIALIST]
    assert len(specialist_hits) == 1
    assert specialist_hits[0]["entity_id"] == "sub-allowed"


@pytest.mark.asyncio
async def test_filter_semantic_hits_calendar_rbac(monkeypatch: pytest.MonkeyPatch) -> None:
    allowed = uuid.uuid4()
    denied = uuid.uuid4()
    monkeypatch.setattr(
        "app.portal_calendar.services.accessible_calendar_event_ids",
        AsyncMock(return_value={allowed}),
    )
    hits = [
        {"entity_type": PORTAL_SEARCH_ENTITY_TYPE_CALENDAR_EVENT, "entity_id": str(allowed)},
        {"entity_type": PORTAL_SEARCH_ENTITY_TYPE_CALENDAR_EVENT, "entity_id": str(denied)},
        {"entity_type": PORTAL_SEARCH_ENTITY_TYPE_TASK, "entity_id": str(uuid.uuid4())},
    ]
    session = AsyncMock()
    viewer = object()
    out = await svc.filter_semantic_hits(
        session,
        hits,
        tag_slugs=None,
        status_ids=None,
        viewer_user=viewer,
    )
    assert len(out) == 2
    cal = [h for h in out if h["entity_type"] == PORTAL_SEARCH_ENTITY_TYPE_CALENDAR_EVENT]
    assert len(cal) == 1
    assert cal[0]["entity_id"] == str(allowed)


@pytest.mark.asyncio
async def test_nav_slug_map_uses_single_subtree_query(monkeypatch: pytest.MonkeyPatch) -> None:
    """Один запрос поддерева developer-docs, без gather на той же сессии."""
    from app.portal_documents.constants import VIRTUAL_DEVELOPER_DOCS_ROOT_SLUG, VIRTUAL_DOCS_ROOT_SLUG
    from app.portal_search.services._search_format import nav_slug_map_for_documents

    dev_id = uuid.uuid4()
    other_id = uuid.uuid4()
    calls = {"n": 0}

    async def _fake_dev_ids(_session: object) -> list[uuid.UUID]:
        calls["n"] += 1
        return [dev_id]

    monkeypatch.setattr(
        "app.portal_search.services._search_format.developer_docs_readable_ids",
        _fake_dev_ids,
    )
    session = AsyncMock()
    out = await nav_slug_map_for_documents(session, {dev_id, other_id})
    assert calls["n"] == 1
    session.execute.assert_not_called()
    assert out[dev_id] == VIRTUAL_DEVELOPER_DOCS_ROOT_SLUG
    assert out[other_id] == VIRTUAL_DOCS_ROOT_SLUG


@pytest.mark.asyncio
async def test_filter_semantic_hits_document_allowlist() -> None:
    allowed = uuid.uuid4()
    denied = uuid.uuid4()
    hits = [
        {"entity_type": PORTAL_SEARCH_ENTITY_TYPE_DOCUMENT, "entity_id": str(allowed)},
        {"entity_type": PORTAL_SEARCH_ENTITY_TYPE_DOCUMENT, "entity_id": str(denied)},
        {"entity_type": PORTAL_SEARCH_ENTITY_TYPE_TASK, "entity_id": str(uuid.uuid4())},
    ]
    out = await svc.filter_semantic_hits(
        AsyncMock(),
        hits,
        tag_slugs=None,
        status_ids=None,
        allowed_document_ids=[allowed],
    )
    doc_ids = [h["entity_id"] for h in out if h["entity_type"] == PORTAL_SEARCH_ENTITY_TYPE_DOCUMENT]
    assert doc_ids == [str(allowed)]
    assert any(h["entity_type"] == PORTAL_SEARCH_ENTITY_TYPE_TASK for h in out)


@pytest.mark.asyncio
async def test_nav_slug_map_empty_skips_query() -> None:
    from app.portal_search.services._search_format import nav_slug_map_for_documents

    session = AsyncMock()
    assert await nav_slug_map_for_documents(session, set()) == {}
    session.execute.assert_not_called()
