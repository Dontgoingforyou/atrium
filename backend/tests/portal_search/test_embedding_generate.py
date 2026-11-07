"""Генерация эмбеддингов: публичный generate_* (мок OpenAI, без сети и без _get_client)."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import app.portal_search.services._embedding_generate as eg
import pytest
from app.portal_search.services._embedding_generate import (
    _MAX_CHARS,
    coerce_embedding_dimension,
    generate_embedding,
    generate_embeddings_batch,
)

from tests.conftest import make_oidc_settings


def test_coerce_embedding_dimension_pads_and_truncates() -> None:
    assert coerce_embedding_dimension([0.1, 0.2], 2) == [0.1, 0.2]
    assert coerce_embedding_dimension([0.1, 0.2], 4) == [0.1, 0.2, 0.0, 0.0]
    assert coerce_embedding_dimension([0.1, 0.2, 0.3, 0.4], 2) == [0.1, 0.2]


def _reset_client_singleton() -> None:
    eg._client = None


@pytest.mark.asyncio
async def test_generate_embedding_empty_text_returns_zeros(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _reset_client_singleton()
    s = make_oidc_settings(openai_api_key="unused", embedding_dimension=3)
    monkeypatch.setattr(eg, "get_settings", lambda: s)
    with patch("app.services.openai_client.AsyncOpenAI") as AO:
        out = await generate_embedding("")
        out2 = await generate_embedding("   \n\t  ")
    AO.assert_not_called()
    assert out == [0.0, 0.0, 0.0]
    assert out2 == [0.0, 0.0, 0.0]


@pytest.mark.asyncio
async def test_generate_embedding_missing_api_key_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    _reset_client_singleton()
    s = make_oidc_settings(openai_api_key="")
    monkeypatch.setattr(eg, "get_settings", lambda: s)
    with pytest.raises(RuntimeError, match="OPENAI_API_KEY"):
        await generate_embedding("hello")


@pytest.mark.asyncio
async def test_generate_embedding_truncates_and_calls_api(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _reset_client_singleton()
    s = make_oidc_settings(
        openai_api_key="sk-x",
        embedding_model_name="text-embedding-test",
        embedding_dimension=2,
    )
    monkeypatch.setattr(eg, "get_settings", lambda: s)

    long_body = "я" * (_MAX_CHARS + 50)
    emb = [0.1, 0.2, 0.3]

    async def _create(**kwargs: object) -> SimpleNamespace:
        inp = str(kwargs["input"])
        assert len(inp) == _MAX_CHARS
        assert str(kwargs["model"]) == "text-embedding-test"
        return SimpleNamespace(data=[SimpleNamespace(embedding=emb)])

    client = MagicMock()
    client.embeddings.create = AsyncMock(side_effect=_create)

    try:
        with patch("app.services.openai_client.AsyncOpenAI", return_value=client) as AO:
            out = await generate_embedding(long_body)
            kwargs = AO.call_args.kwargs
            assert kwargs["api_key"] == "sk-x"
            assert kwargs["timeout"] == s.http_client_timeout_seconds
    finally:
        _reset_client_singleton()

    assert out == [0.1, 0.2]
    client.embeddings.create.assert_awaited_once()


@pytest.mark.asyncio
async def test_generate_embeddings_batch_empty_returns_empty_list() -> None:
    assert await generate_embeddings_batch([]) == []


@pytest.mark.asyncio
async def test_generate_embeddings_batch_skips_blank_texts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _reset_client_singleton()
    s = make_oidc_settings(openai_api_key="sk-blank", embedding_dimension=2, embedding_batch_size=10)
    monkeypatch.setattr(eg, "get_settings", lambda: s)
    client = MagicMock()
    client.embeddings.create = AsyncMock(return_value=SimpleNamespace(data=[SimpleNamespace(embedding=[1.0, 2.0])]))
    try:
        with patch("app.services.openai_client.AsyncOpenAI", return_value=client):
            out = await generate_embeddings_batch(["", "  ", "ok"])
    finally:
        _reset_client_singleton()
    assert out[0] == [0.0, 0.0]
    assert out[1] == [0.0, 0.0]
    assert out[2] == [1.0, 2.0]
    assert client.embeddings.create.await_count == 1


@pytest.mark.asyncio
async def test_generate_embeddings_batch_respects_batch_size_and_truncation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _reset_client_singleton()
    s = make_oidc_settings(
        openai_api_key="sk-batch",
        embedding_model_name="m",
        embedding_batch_size=2,
        embedding_dimension=2,
    )
    monkeypatch.setattr(eg, "get_settings", lambda: s)

    long = "z" * (_MAX_CHARS + 10)
    texts = ["a", long, "ccc"]

    async def _create(**kwargs: object) -> SimpleNamespace:
        inp = kwargs["input"]
        assert isinstance(inp, list)
        batch = [str(t) for t in inp]
        assert all(len(t) <= _MAX_CHARS for t in batch)
        vecs = [[float(ord(t[0])), float(len(t))] for t in batch]
        return SimpleNamespace(data=[SimpleNamespace(embedding=v) for v in vecs])

    client = MagicMock()
    client.embeddings.create = AsyncMock(side_effect=_create)

    try:
        with patch("app.services.openai_client.AsyncOpenAI", return_value=client):
            out = await generate_embeddings_batch(texts)
    finally:
        _reset_client_singleton()

    assert len(out) == 3
    assert out[0] == [97.0, 1.0]
    assert out[1][1] == float(_MAX_CHARS)
    assert out[2] == [99.0, 3.0]
    assert client.embeddings.create.await_count == 2


@pytest.mark.asyncio
async def test_generate_embedding_pads_provider_1024_to_settings_dim(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Infinity/прокси отдаёт 1024 при колонке vector(1536) — иначе pgvector DataError."""
    _reset_client_singleton()
    s = make_oidc_settings(openai_api_key="sk-x", embedding_dimension=4)
    monkeypatch.setattr(eg, "get_settings", lambda: s)
    client = MagicMock()
    client.embeddings.create = AsyncMock(
        return_value=SimpleNamespace(data=[SimpleNamespace(embedding=[0.1, 0.2])]),
    )
    try:
        with patch("app.services.openai_client.AsyncOpenAI", return_value=client):
            out = await generate_embedding("пёс")
    finally:
        _reset_client_singleton()
    assert out == [0.1, 0.2, 0.0, 0.0]
