"""Цикл фоновой синхронизации бенч из Google Таблицы."""

from __future__ import annotations

import asyncio
import logging
from unittest.mock import AsyncMock, MagicMock

import pytest
from app.core.config import Settings
from app.jobs.bench_sheets_sync import run_bench_sheets_sync_loop


def _session_factory(session: AsyncMock) -> MagicMock:
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=session)
    cm.__aexit__ = AsyncMock(return_value=None)
    return MagicMock(return_value=cm)


def _http_factory() -> MagicMock:
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=AsyncMock())
    cm.__aexit__ = AsyncMock(return_value=None)
    return MagicMock(return_value=cm)


@pytest.mark.asyncio
async def test_bench_sync_loop_disabled_does_not_call(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sync = AsyncMock()
    monkeypatch.setattr("app.jobs.bench_sheets_sync.sync_bench_from_sheets", sync)
    settings = Settings(database_url="sqlite+aiosqlite:///:memory:", google_sheets_sync_enabled=False)
    await run_bench_sheets_sync_loop(asyncio.Event(), settings)
    sync.assert_not_awaited()


@pytest.mark.asyncio
async def test_bench_sync_loop_runs_immediately_then_stops(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sync = AsyncMock(return_value=True)
    monkeypatch.setattr("app.jobs.bench_sheets_sync.sync_bench_from_sheets", sync)
    session = AsyncMock()
    monkeypatch.setattr("app.jobs.bench_sheets_sync.async_session_factory", _session_factory(session))
    monkeypatch.setattr("app.jobs.bench_sheets_sync.httpx.AsyncClient", _http_factory())

    stop = asyncio.Event()

    async def sync_and_stop(*_args: object, **_kwargs: object) -> bool:
        stop.set()
        return True

    sync.side_effect = sync_and_stop
    settings = Settings(
        database_url="sqlite+aiosqlite:///:memory:",
        google_sheets_sync_enabled=True,
        google_sheets_sync_interval_seconds=60,
    )
    await run_bench_sheets_sync_loop(stop, settings)
    sync.assert_awaited_once()


@pytest.mark.asyncio
async def test_bench_sync_loop_continues_after_error(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    sync = AsyncMock()
    monkeypatch.setattr("app.jobs.bench_sheets_sync.sync_bench_from_sheets", sync)
    session = AsyncMock()
    monkeypatch.setattr("app.jobs.bench_sheets_sync.async_session_factory", _session_factory(session))
    monkeypatch.setattr("app.jobs.bench_sheets_sync.httpx.AsyncClient", _http_factory())

    stop = asyncio.Event()

    async def fail_then_stop(*_args: object, **_kwargs: object) -> bool:
        if sync.await_count == 1:
            raise RuntimeError("sync failed")
        stop.set()
        return False

    sync.side_effect = fail_then_stop

    async def timeout_until_stopped(awaitable: object, timeout: object = None) -> None:
        if asyncio.iscoroutine(awaitable):
            awaitable.close()
        if stop.is_set():
            return None
        raise TimeoutError

    monkeypatch.setattr("app.jobs.bench_sheets_sync.asyncio.wait_for", timeout_until_stopped)
    settings = Settings(
        database_url="sqlite+aiosqlite:///:memory:",
        google_sheets_sync_enabled=True,
        google_sheets_sync_interval_seconds=60,
    )
    caplog.set_level(logging.ERROR, logger="app.jobs.bench_sheets_sync")
    await run_bench_sheets_sync_loop(stop, settings)
    assert sync.await_count == 2
    assert any("Ошибка фоновой синхронизации бенч" in rec.message for rec in caplog.records)
