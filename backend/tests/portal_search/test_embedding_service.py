"""Тесты embedding: upsert/delete, skip-trash reindex, bg-guards (без coverage empty/one_row)."""

from __future__ import annotations

import json
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import app.portal_search.services.embedding as emb
import pytest
from app.core.portal_search_constants import PORTAL_SEARCH_ENTITY_TYPE_DOCUMENT
from app.portal_search.services.embedding import (
    bulk_reindex,
    bulk_reindex_bg,
    delete_embedding,
    delete_embedding_bg,
    upsert_embedding,
    upsert_embedding_bg,
)


def test_vec_literal_formats_floats() -> None:
    assert emb.vec_literal([1.0, 2.5]) == "[1.00000000,2.50000000]"
    assert emb.vec_literal([]) == "[]"


@pytest.mark.asyncio
async def test_upsert_embedding_indexes_without_openai_key() -> None:
    with patch.object(emb, "generate_embedding", new_callable=AsyncMock, return_value=[0.5, 0.5]):
        db = MagicMock()
        db.execute = AsyncMock()
        db.commit = AsyncMock()
        await upsert_embedding(db, PORTAL_SEARCH_ENTITY_TYPE_DOCUMENT, "e1", "отпуск", {})
    db.execute.assert_awaited_once()
    db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_upsert_embedding_inserts_and_commits() -> None:
    with patch.object(emb, "generate_embedding", new_callable=AsyncMock, return_value=[0.25, 0.75]):
        db = MagicMock()
        db.execute = AsyncMock()
        db.commit = AsyncMock()
        await upsert_embedding(db, "document", "id-1", "hello", {"nav": "x"})

    db.execute.assert_awaited_once()
    _stmt, params = db.execute.await_args[0]
    assert params["entity_id"] == "id-1"
    assert params["text_content"] == "hello"
    assert params["vec"] == "[0.25000000,0.75000000]"
    assert json.loads(params["meta"]) == {"nav": "x"}
    db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_upsert_embedding_logs_exception_on_failure() -> None:
    with patch.object(emb, "generate_embedding", new_callable=AsyncMock, return_value=[0.0]):
        db = MagicMock()
        db.execute = AsyncMock(side_effect=RuntimeError("db"))
        with patch.object(emb, "logger") as log:
            await upsert_embedding(db, "document", "e2", "t", {})
    log.exception.assert_called()


@pytest.mark.asyncio
async def test_delete_embedding_commits_and_logs_exception() -> None:
    db = MagicMock()
    db.execute = AsyncMock()
    db.commit = AsyncMock()
    await delete_embedding(db, "task", "t-1")
    db.execute.assert_awaited_once()
    db.commit.assert_awaited_once()

    db2 = MagicMock()
    db2.execute = AsyncMock(side_effect=OSError("io"))
    with patch.object(emb, "logger") as log2:
        await delete_embedding(db2, "task", "t-2")
    log2.exception.assert_called()


@pytest.mark.asyncio
async def test_bulk_reindex_documents_skips_trashed(
    sqlite_session: object,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.portal_documents.schemas.document import PortalDocumentCreate
    from app.portal_documents.services.portal_document_mutations import create_document
    from app.portal_documents.services.portal_document_trash import soft_delete_document
    from app.portal_search.services._embedding_bulk_reindex import bulk_reindex_documents

    await create_document(
        sqlite_session,
        PortalDocumentCreate(title="Живой"),
        author_sub="admin-sub",
    )
    trashed = await create_document(
        sqlite_session,
        PortalDocumentCreate(title="В корзине"),
        author_sub="admin-sub",
    )
    await soft_delete_document(sqlite_session, trashed.id, deleted_by_sub="admin-sub")

    indexed: list[str] = []

    async def _fake_batch(texts: list[str]) -> list[list[float]]:
        indexed.extend(texts)
        return [[0.1, 0.2] for _ in texts]

    monkeypatch.setattr(
        "app.portal_search.services._embedding_chunk.generate_embeddings_batch",
        _fake_batch,
    )
    orig_execute = sqlite_session.execute

    async def _execute(statement: object, *args: object, **kwargs: object) -> object:
        raw = str(statement).lower()
        if "portal_embedding" in raw or "on conflict" in raw:
            return MagicMock()
        return await orig_execute(statement, *args, **kwargs)

    monkeypatch.setattr(sqlite_session, "execute", _execute)

    n = await bulk_reindex_documents(sqlite_session)
    assert n == 1
    assert any("Живой" in t for t in indexed)
    assert not any("В корзине" in t for t in indexed)


@pytest.mark.asyncio
async def test_bulk_reindex_unknown_type_warns() -> None:
    db = MagicMock()
    with patch("app.portal_search.services._embedding_bulk_reindex.time") as timemod:
        timemod.monotonic.side_effect = [0.0, 1.0]
        with patch("app.portal_search.services._embedding_bulk_reindex.logger") as log:
            out = await bulk_reindex(db, ["not_a_real_entity_type"])
    assert out == {}
    log.warning.assert_called()


@pytest.mark.asyncio
async def test_bulk_reindex_handler_exception_sets_minus_one() -> None:
    from app.portal_search.services._embedding_bulk_reindex import _REINDEX_HANDLERS

    db = MagicMock()

    async def _boom(_: object) -> int:
        raise RuntimeError("fail")

    with patch.dict(_REINDEX_HANDLERS, {PORTAL_SEARCH_ENTITY_TYPE_DOCUMENT: _boom}):
        with patch("app.portal_search.services._embedding_bulk_reindex.time") as timemod:
            timemod.monotonic.side_effect = [0.0, 2.0]
            with patch("app.portal_search.services._embedding_bulk_reindex.logger") as log:
                out = await bulk_reindex(db, [PORTAL_SEARCH_ENTITY_TYPE_DOCUMENT])
    assert out[PORTAL_SEARCH_ENTITY_TYPE_DOCUMENT] == -1
    log.exception.assert_called()


@pytest.mark.asyncio
async def test_upsert_embedding_bg_skips_under_pytest_guard() -> None:
    with patch.object(emb, "upsert_embedding", new_callable=AsyncMock) as up:
        await upsert_embedding_bg("document", "e", "t", {})
    up.assert_not_called()


@pytest.mark.asyncio
async def test_upsert_embedding_bg_runs_with_session(monkeypatch: pytest.MonkeyPatch) -> None:
    mock_sess = MagicMock()

    @asynccontextmanager
    async def _cm() -> object:
        yield mock_sess

    factory = MagicMock(return_value=_cm())
    monkeypatch.setattr("app.infrastructure.db.session.async_session_factory", factory)
    with (
        patch(
            "app.portal_search.services._embedding_background.skip_background_tasks_using_global_engine",
            return_value=False,
        ),
        patch.object(emb, "upsert_embedding", new_callable=AsyncMock) as up,
    ):
        await upsert_embedding_bg("task", "tid", "body", {"k": "v"})
    up.assert_awaited_once_with(mock_sess, "task", "tid", "body", {"k": "v"})


@pytest.mark.asyncio
async def test_delete_embedding_bg_skips_and_runs(monkeypatch: pytest.MonkeyPatch) -> None:
    with patch.object(emb, "delete_embedding", new_callable=AsyncMock) as de:
        await delete_embedding_bg("a", "b")
    de.assert_not_called()

    mock_sess = MagicMock()

    @asynccontextmanager
    async def _cm() -> object:
        yield mock_sess

    factory = MagicMock(return_value=_cm())
    monkeypatch.setattr("app.infrastructure.db.session.async_session_factory", factory)
    with (
        patch(
            "app.portal_search.services._embedding_background.skip_background_tasks_using_global_engine",
            return_value=False,
        ),
        patch.object(emb, "delete_embedding", new_callable=AsyncMock) as de2,
    ):
        await delete_embedding_bg("x", "y")
    de2.assert_awaited_once_with(mock_sess, "x", "y")


@pytest.mark.asyncio
async def test_bulk_reindex_bg_releases_lock(monkeypatch: pytest.MonkeyPatch) -> None:
    with (
        patch.object(emb, "bulk_reindex", new_callable=AsyncMock) as br,
        patch("app.infrastructure.cache.reindex_lock.release_reindex_lock", new_callable=AsyncMock) as rel,
    ):
        await bulk_reindex_bg(["document"], "tok-skip")
    br.assert_not_called()
    rel.assert_awaited_once_with("tok-skip")

    mock_sess = MagicMock()

    @asynccontextmanager
    async def _cm() -> object:
        yield mock_sess

    factory = MagicMock(return_value=_cm())
    monkeypatch.setattr("app.infrastructure.db.session.async_session_factory", factory)
    with (
        patch(
            "app.portal_search.services._embedding_background.skip_background_tasks_using_global_engine",
            return_value=False,
        ),
        patch(
            "app.portal_search.services._embedding_bulk_reindex.bulk_reindex",
            new_callable=AsyncMock,
        ) as br2,
        patch("app.infrastructure.cache.reindex_lock.release_reindex_lock", new_callable=AsyncMock) as rel2,
    ):
        await bulk_reindex_bg(["task"], "tok-run")
    br2.assert_awaited_once_with(mock_sess, ["task"])
    rel2.assert_awaited_once_with("tok-run")
