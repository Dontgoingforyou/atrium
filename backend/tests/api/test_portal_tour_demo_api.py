"""Учебные сущности guided tour (таймшиты, developer-docs)."""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from tests.portal_documents.dev_docs_fixtures import ensure_developer_docs_root

_TIME_ENTRIES = "/api/v1/portal/time-entries"
_TOUR_DEMO_DOC_ENSURE = "/api/v1/portal/documents/tour-demo/ensure"
_TOUR_DEMO_DOC_PURGE = "/api/v1/portal/documents/tour-demo"


@pytest.mark.asyncio
async def test_create_tour_demo_time_entry(client_developer: AsyncClient) -> None:
    r = await client_developer.post(
        _TIME_ENTRIES,
        json={
            "worked_on": "2026-08-20",
            "minutes": 60,
            "task_name": "Учебная запись",
            "note": "demo",
            "is_tour_demo": True,
        },
    )
    assert r.status_code == 201
    body = r.json()
    assert body["is_tour_demo"] is True
    assert body["task_name"] == "Учебная запись"

    listed = await client_developer.get(_TIME_ENTRIES)
    assert listed.status_code == 200
    demo = [row for row in listed.json()["items"] if row["is_tour_demo"]]
    assert len(demo) >= 1

    delete_r = await client_developer.delete(f"{_TIME_ENTRIES}/{body['id']}")
    assert delete_r.status_code == 204


@pytest.mark.asyncio
async def test_tour_demo_document_ensure_and_purge(
    client_developer: AsyncClient,
    sqlite_session: AsyncSession,
) -> None:
    await ensure_developer_docs_root(sqlite_session)

    r1 = await client_developer.post(_TOUR_DEMO_DOC_ENSURE)
    assert r1.status_code == 200
    body1 = r1.json()
    doc_id = body1["id"]
    assert body1["created"] is True

    r2 = await client_developer.post(_TOUR_DEMO_DOC_ENSURE)
    assert r2.status_code == 200
    assert r2.json()["id"] == doc_id
    assert r2.json()["created"] is False

    get_r = await client_developer.get(f"/api/v1/portal/documents/{doc_id}")
    assert get_r.status_code == 200
    assert get_r.json()["title"] == "Учебный документ"

    purge_r = await client_developer.delete(_TOUR_DEMO_DOC_PURGE)
    assert purge_r.status_code == 204

    get_after = await client_developer.get(f"/api/v1/portal/documents/{doc_id}")
    assert get_after.status_code == 404
