"""Тесты модуля сессии БД (`app.infrastructure.db.session`)."""

from __future__ import annotations

import os
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.infrastructure.db import session as db_session


def test_skip_background_tasks_using_global_engine_under_pytest() -> None:
    assert os.environ.get("PYTEST_CURRENT_TEST") is not None
    assert db_session.skip_background_tasks_using_global_engine() is True


def test_skip_background_tasks_using_global_engine_without_pytest(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    assert db_session.skip_background_tasks_using_global_engine() is False


def test_register_pgvector_logs_warning_on_postgres_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        db_session,
        "_s",
        SimpleNamespace(database_url="postgresql+asyncpg://localhost/test"),
    )
    conn = MagicMock()
    conn.run_sync.side_effect = RuntimeError("pgvector unavailable")
    with (
        patch("pgvector.asyncpg.register_vector", MagicMock(), create=True),
        patch.object(db_session.logger, "warning") as log_warning,
    ):
        db_session._register_pgvector(conn, None)
    log_warning.assert_called_once()
    assert "vector" in log_warning.call_args.args[0].lower()


def test_register_pgvector_sqlite_failure_silent(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        db_session,
        "_s",
        SimpleNamespace(database_url="sqlite+aiosqlite:///:memory:"),
    )
    with (
        patch("pgvector.asyncpg.register_vector", side_effect=ImportError("no pgvector"), create=True),
        patch.object(db_session.logger, "warning") as log_warning,
    ):
        db_session._register_pgvector(MagicMock(), None)
    log_warning.assert_not_called()


@pytest.mark.asyncio
async def test_get_db_session_yields_async_session() -> None:
    mock_session = MagicMock()
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=mock_session)
    cm.__aexit__ = AsyncMock(return_value=None)
    with patch.object(db_session, "async_session_factory", return_value=cm):
        gen = db_session.get_db_session()
        session = await gen.__anext__()
        assert session is mock_session
        with pytest.raises(StopAsyncIteration):
            await gen.__anext__()
        cm.__aexit__.assert_awaited_once()


@pytest.mark.asyncio
async def test_dispose_engine() -> None:
    mock_engine = MagicMock()
    mock_engine.dispose = AsyncMock()
    with patch.object(db_session, "engine", mock_engine):
        await db_session.dispose_engine()
    mock_engine.dispose.assert_awaited_once()
