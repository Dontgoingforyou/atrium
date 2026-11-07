"""HTTP-контракт семантического поиска и reindex."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from app.core.exceptions import ServiceUnavailableError
from app.core.portal_search_constants import PORTAL_SEARCH_ENTITY_TYPE_AGREEMENT
from app.infrastructure.db.models.portal_document import PortalDocument, PortalDocumentTag, PortalTag
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest import make_oidc_settings
from tests.portal_search.conftest import (
    REINDEX_API,
    SEMANTIC_API,
    assert_api_error,
)


@pytest.mark.parametrize("path", [SEMANTIC_API + "?q=ab", REINDEX_API])
async def test_semantic_and_reindex_require_auth(
    client_sqlite_only: AsyncClient,
    path: str,
) -> None:
    if path == REINDEX_API:
        r = await client_sqlite_only.post(path)
    else:
        r = await client_sqlite_only.get(path)
    assert_api_error(r, 401, "unauthorized")


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("GET", SEMANTIC_API + "?q=ab"),
        ("POST", REINDEX_API),
    ],
)
async def test_semantic_and_reindex_timesheet_forbidden(
    client_developer: AsyncClient,
    method: str,
    path: str,
) -> None:
    r = await client_developer.request(method, path)
    assert_api_error(r, 403, "forbidden")


async def test_semantic_search_q_too_short_returns_422(client_admin: AsyncClient) -> None:
    r = await client_admin.get(f"{SEMANTIC_API}?q=a")
    assert_api_error(r, 422, "validation_error")


async def test_semantic_search_unknown_entity_type_returns_422(client_admin: AsyncClient) -> None:
    r = await client_admin.get(f"{SEMANTIC_API}?q=ab&types=unknown_type")
    assert_api_error(r, 422, "validation_error")


async def test_semantic_search_no_openai_key_returns_503(client_admin: AsyncClient) -> None:
    r = await client_admin.get(f"{SEMANTIC_API}?q=ab")
    assert_api_error(r, 503, ServiceUnavailableError().code)


async def test_semantic_search_openai_failure_returns_503(
    client_admin: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    s = make_oidc_settings(openai_api_key="sk-test-integration")
    monkeypatch.setattr("app.api.deps_auth.get_settings", lambda: s)
    monkeypatch.setattr("app.core.config.get_settings", lambda: s)

    async def _boom(_text: str) -> list[float]:
        raise RuntimeError("openai down")

    monkeypatch.setattr(
        "app.portal_search.services.embedding.generate_embedding",
        _boom,
    )
    r = await client_admin.get(f"{SEMANTIC_API}?q=ab")
    assert_api_error(r, 503, ServiceUnavailableError().code)


async def test_semantic_search_pgvector_dimension_error_returns_503(
    client_admin: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Разная длина query/index (1024 vs 1536) не должна отдавать сырой 500."""
    s = make_oidc_settings(openai_api_key="sk-test-integration")
    monkeypatch.setattr("app.api.deps_auth.get_settings", lambda: s)
    monkeypatch.setattr("app.core.config.get_settings", lambda: s)

    async def _fake_generate_embedding(_text: str) -> list[float]:
        return [0.0] * s.embedding_dimension

    async def _boom(**_kwargs: object) -> list[dict[str, object]]:
        raise RuntimeError("different vector dimensions 1536 and 1024")

    monkeypatch.setattr(
        "app.portal_search.services.embedding.generate_embedding",
        _fake_generate_embedding,
    )
    monkeypatch.setattr(
        "app.portal_search.services.search_orchestrator.search_svc.semantic_search",
        _boom,
    )
    r = await client_admin.get(f"{SEMANTIC_API}?q=пёс")
    assert_api_error(r, 503, ServiceUnavailableError().code)


async def test_semantic_search_ok_with_openai_mock(
    client_admin: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Мок только OpenAI/embedding и semantic SQL (pgvector); filter — реальный."""
    s = make_oidc_settings(openai_api_key="sk-test-integration")
    monkeypatch.setattr("app.api.deps_auth.get_settings", lambda: s)
    monkeypatch.setattr("app.core.config.get_settings", lambda: s)

    entity_id = str(uuid.uuid4())

    async def _fake_generate_embedding(_text: str) -> list[float]:
        return [0.0] * s.embedding_dimension

    async def _fake_semantic_search(**_kwargs: object) -> list[dict[str, object]]:
        return [
            {
                "entity_type": "document",
                "entity_id": entity_id,
                "text_content": "Пример текста для превью",
                "similarity_score": 0.91,
                "meta": {},
            }
        ]

    monkeypatch.setattr(
        "app.portal_search.services.embedding.generate_embedding",
        _fake_generate_embedding,
    )
    monkeypatch.setattr(
        "app.portal_search.services.search_orchestrator.search_svc.semantic_search",
        _fake_semantic_search,
    )

    r = await client_admin.get(f"{SEMANTIC_API}?q=поиск")
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["query"] == "поиск"
    assert data["total_found"] == 1
    assert data["results"][0]["entity_type"] == "document"
    assert data["results"][0]["similarity_score"] == pytest.approx(0.91)
    assert "Пример" in data["results"][0]["text_excerpt"]


async def test_semantic_search_default_types_exclude_agreement(
    client_admin: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    s = make_oidc_settings(openai_api_key="sk-test-integration")
    monkeypatch.setattr("app.api.deps_auth.get_settings", lambda: s)
    monkeypatch.setattr("app.core.config.get_settings", lambda: s)
    captured: dict[str, object] = {}

    async def _fake_generate_embedding(_text: str) -> list[float]:
        return [0.0] * s.embedding_dimension

    async def _fake_semantic_search(**kwargs: object) -> list[dict[str, object]]:
        captured["entity_types"] = kwargs["entity_types"]
        return []

    monkeypatch.setattr(
        "app.portal_search.services.embedding.generate_embedding",
        _fake_generate_embedding,
    )
    monkeypatch.setattr(
        "app.portal_search.services.search_orchestrator.search_svc.semantic_search",
        _fake_semantic_search,
    )

    r = await client_admin.get(f"{SEMANTIC_API}?q=ab")
    assert r.status_code == 200, r.text
    types = captured["entity_types"]
    assert isinstance(types, list)
    assert PORTAL_SEARCH_ENTITY_TYPE_AGREEMENT not in types


async def test_semantic_search_applies_real_tag_filter(
    client_admin: AsyncClient,
    sqlite_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Мок OpenAI + semantic SQL; filter_semantic_hits — реальный (tag_slug по БД)."""
    s = make_oidc_settings(openai_api_key="sk-test-integration")
    monkeypatch.setattr("app.api.deps_auth.get_settings", lambda: s)
    monkeypatch.setattr("app.core.config.get_settings", lambda: s)

    tagged_id = uuid.uuid4()
    other_id = uuid.uuid4()
    tag = PortalTag(name="Urgent SEMTAG99", slug="urgent-semtag99", color="#ff0000")
    sqlite_session.add(tag)
    await sqlite_session.flush()
    sqlite_session.add_all(
        [
            PortalDocument(id=tagged_id, title="tagged", author_sub="admin-sub", body="a"),
            PortalDocument(id=other_id, title="other", author_sub="admin-sub", body="b"),
            PortalDocumentTag(document_id=tagged_id, tag_id=tag.id),
        ]
    )
    await sqlite_session.commit()

    async def _fake_generate_embedding(_text: str) -> list[float]:
        return [0.0] * s.embedding_dimension

    async def _fake_semantic_search(**_kwargs: object) -> list[dict[str, object]]:
        return [
            {
                "entity_type": "document",
                "entity_id": str(tagged_id),
                "text_content": "a",
                "similarity_score": 0.9,
                "meta": {},
            },
            {
                "entity_type": "document",
                "entity_id": str(other_id),
                "text_content": "b",
                "similarity_score": 0.8,
                "meta": {},
            },
        ]

    monkeypatch.setattr(
        "app.portal_search.services.embedding.generate_embedding",
        _fake_generate_embedding,
    )
    monkeypatch.setattr(
        "app.portal_search.services.search_orchestrator.search_svc.semantic_search",
        _fake_semantic_search,
    )

    r = await client_admin.get(f"{SEMANTIC_API}?q=ab&tag_slug=urgent-semtag99")
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["total_found"] == 1
    assert data["results"][0]["entity_id"] == str(tagged_id)


async def test_semantic_search_pins_fulltext_hit_first(
    client_admin: AsyncClient,
    sqlite_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Слово из реального полнотекста не тонет за семантическим шумом."""
    s = make_oidc_settings(openai_api_key="sk-test-integration")
    monkeypatch.setattr("app.api.deps_auth.get_settings", lambda: s)
    monkeypatch.setattr("app.core.config.get_settings", lambda: s)
    lex_id = uuid.uuid4()
    sem_id = uuid.uuid4()
    marker = "BENCHLEXX99"
    sqlite_session.add(PortalDocument(id=lex_id, title=f"Документ {marker}", author_sub="admin-sub", body="x"))
    await sqlite_session.commit()

    async def _fake_generate_embedding(_text: str) -> list[float]:
        return [0.0] * s.embedding_dimension

    async def _fake_semantic_search(**_kwargs: object) -> list[dict[str, object]]:
        return [
            {
                "entity_type": "document",
                "entity_id": str(sem_id),
                "text_content": "чужой",
                "similarity_score": 0.55,
                "meta": {},
            }
        ]

    monkeypatch.setattr(
        "app.portal_search.services.embedding.generate_embedding",
        _fake_generate_embedding,
    )
    monkeypatch.setattr(
        "app.portal_search.services.search_orchestrator.search_svc.semantic_search",
        _fake_semantic_search,
    )

    r = await client_admin.get(f"{SEMANTIC_API}?q={marker}&types=document")
    assert r.status_code == 200, r.text
    data = r.json()
    assert [row["entity_id"] for row in data["results"]] == [str(lex_id), str(sem_id)]
    assert data["results"][0]["similarity_score"] is None
    assert data["results"][1]["similarity_score"] == pytest.approx(0.55)


async def test_reindex_forbidden_for_non_admin(client_user: AsyncClient) -> None:
    r = await client_user.post(REINDEX_API)
    assert_api_error(r, 403, "forbidden")


async def test_reindex_unknown_entity_type_returns_422(client_admin: AsyncClient) -> None:
    r = await client_admin.post(f"{REINDEX_API}?entity_types=chat")
    assert_api_error(r, 422, "validation_error")


async def test_reindex_accepted_for_admin(client_admin: AsyncClient) -> None:
    with patch(
        "app.portal_search.routes.search.try_acquire_reindex_lock",
        new=AsyncMock(return_value="lock-token"),
    ):
        r = await client_admin.post(REINDEX_API)
    assert r.status_code == 202, r.text
    data = r.json()
    assert data["status"] == "started"
    assert isinstance(data["entity_types"], list)


async def test_reindex_conflict_when_lock_held(client_admin: AsyncClient) -> None:
    with patch(
        "app.portal_search.routes.search.try_acquire_reindex_lock",
        new=AsyncMock(return_value=None),
    ):
        r = await client_admin.post(REINDEX_API)
    assert_api_error(r, 409, "conflict")
