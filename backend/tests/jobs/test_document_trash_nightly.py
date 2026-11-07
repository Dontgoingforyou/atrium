"""Тесты цикла ночной очистки корзины документов."""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from app.core.config import Settings
from app.jobs.document_trash_nightly import (
    run_document_trash_purge_loop,
    seconds_until_next_run_utc,
)


def _session_factory(session: AsyncMock) -> MagicMock:
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=session)
    cm.__aexit__ = AsyncMock(return_value=None)
    return MagicMock(return_value=cm)


def test_seconds_until_next_run_same_hour_zero() -> None:
    now = datetime(2026, 5, 7, 3, 0, 0, tzinfo=UTC)
    assert seconds_until_next_run_utc(now, 3) == 0.0


def test_seconds_until_next_run_future_hour_same_day() -> None:
    now = datetime(2026, 5, 7, 2, 0, 0, tzinfo=UTC)
    assert seconds_until_next_run_utc(now, 3) == 3600.0


def test_seconds_until_next_run_next_day_if_passed() -> None:
    now = datetime(2026, 5, 7, 4, 0, 0, tzinfo=UTC)
    sec = seconds_until_next_run_utc(now, 3)
    assert 23 * 3600 - 1 < sec < 23 * 3600 + 1


def test_seconds_until_next_run_after_hour_rolls_to_next_day() -> None:
    now = datetime(2026, 5, 7, 3, 0, 1, tzinfo=UTC)
    sec = seconds_until_next_run_utc(now, 3)
    assert sec == 24 * 3600 - 1


def test_seconds_until_next_run_naive_datetime_treated_as_utc() -> None:
    now = datetime(2026, 5, 7, 3, 0, 0)
    assert seconds_until_next_run_utc(now, 3) == 0.0


def test_seconds_until_next_run_aware_non_utc_converted() -> None:
    msk = timezone(timedelta(hours=3))
    now = datetime(2026, 5, 7, 6, 0, 0, tzinfo=msk)
    assert seconds_until_next_run_utc(now, 3) == 0.0


@pytest.mark.asyncio
async def test_document_trash_purge_loop_disabled_does_not_call_purge(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seconds = MagicMock(return_value=0.0)
    monkeypatch.setattr("app.jobs.document_trash_nightly.seconds_until_next_run_utc", seconds)
    purge = AsyncMock()
    monkeypatch.setattr("app.jobs.document_trash_nightly.purge_expired_document_trash", purge)

    stop = asyncio.Event()
    settings = Settings(
        database_url="sqlite+aiosqlite:///:memory:",
        document_trash_purge_enabled=False,
    )
    await run_document_trash_purge_loop(stop, settings)

    seconds.assert_not_called()
    purge.assert_not_awaited()


@pytest.mark.asyncio
async def test_document_trash_purge_loop_passes_hour_from_settings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    hours: list[int] = []
    stop = asyncio.Event()

    def capture_hour(_now: datetime, hour: int) -> float:
        hours.append(hour)
        stop.set()
        return 3600.0

    monkeypatch.setattr("app.jobs.document_trash_nightly.seconds_until_next_run_utc", capture_hour)
    purge = AsyncMock()
    monkeypatch.setattr("app.jobs.document_trash_nightly.purge_expired_document_trash", purge)

    settings = Settings(
        database_url="sqlite+aiosqlite:///:memory:",
        document_trash_purge_enabled=True,
        document_trash_purge_hour_utc=7,
    )
    await run_document_trash_purge_loop(stop, settings)

    assert hours == [7]
    purge.assert_not_awaited()


@pytest.mark.asyncio
async def test_document_trash_purge_loop_runs_purge_after_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "app.jobs.document_trash_nightly.seconds_until_next_run_utc",
        lambda _now, _hour: 0.0,
    )
    purge = AsyncMock()
    monkeypatch.setattr("app.jobs.document_trash_nightly.purge_expired_document_trash", purge)
    session = AsyncMock()
    monkeypatch.setattr(
        "app.jobs.document_trash_nightly.async_session_factory",
        _session_factory(session),
    )

    stop = asyncio.Event()
    settings = Settings(
        database_url="sqlite+aiosqlite:///:memory:",
        document_trash_purge_enabled=True,
    )

    async def stop_after_purge(_session: AsyncMock) -> None:
        stop.set()

    purge.side_effect = stop_after_purge

    await run_document_trash_purge_loop(stop, settings)

    purge.assert_awaited_once_with(session)


@pytest.mark.asyncio
async def test_document_trash_purge_loop_returns_after_timeout_if_stop_set(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "app.jobs.document_trash_nightly.seconds_until_next_run_utc",
        lambda _now, _hour: 0.0,
    )
    purge = AsyncMock()
    monkeypatch.setattr("app.jobs.document_trash_nightly.purge_expired_document_trash", purge)

    stop = asyncio.Event()
    real_wait_for = asyncio.wait_for

    async def wait_for_sets_stop_on_timeout(awaitable: object, timeout: float | None = None) -> object:
        try:
            return await real_wait_for(awaitable, timeout=timeout)
        except TimeoutError:
            stop.set()
            raise

    monkeypatch.setattr("app.jobs.document_trash_nightly.asyncio.wait_for", wait_for_sets_stop_on_timeout)

    settings = Settings(
        database_url="sqlite+aiosqlite:///:memory:",
        document_trash_purge_enabled=True,
    )
    await run_document_trash_purge_loop(stop, settings)

    purge.assert_not_awaited()


@pytest.mark.asyncio
async def test_document_trash_purge_loop_stops_when_event_set_during_wait(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "app.jobs.document_trash_nightly.seconds_until_next_run_utc",
        lambda _now, _hour: 3600.0,
    )
    purge = AsyncMock()
    monkeypatch.setattr("app.jobs.document_trash_nightly.purge_expired_document_trash", purge)

    stop = asyncio.Event()
    settings = Settings(
        database_url="sqlite+aiosqlite:///:memory:",
        document_trash_purge_enabled=True,
    )

    task = asyncio.create_task(run_document_trash_purge_loop(stop, settings))
    await asyncio.sleep(0)
    stop.set()
    await asyncio.wait_for(task, timeout=1.0)

    purge.assert_not_awaited()


@pytest.mark.asyncio
async def test_document_trash_purge_loop_continues_after_purge_error(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    monkeypatch.setattr(
        "app.jobs.document_trash_nightly.seconds_until_next_run_utc",
        lambda _now, _hour: 0.0,
    )
    stop = asyncio.Event()
    session = AsyncMock()
    monkeypatch.setattr(
        "app.jobs.document_trash_nightly.async_session_factory",
        _session_factory(session),
    )

    async def fail_then_stop(_session: AsyncMock) -> None:
        if purge.await_count == 1:
            raise RuntimeError("purge failed")
        stop.set()

    purge = AsyncMock(side_effect=fail_then_stop)
    monkeypatch.setattr("app.jobs.document_trash_nightly.purge_expired_document_trash", purge)

    settings = Settings(
        database_url="sqlite+aiosqlite:///:memory:",
        document_trash_purge_enabled=True,
    )

    caplog.set_level(logging.ERROR, logger="app.jobs.document_trash_nightly")
    await run_document_trash_purge_loop(stop, settings)

    assert purge.await_count == 2
    assert any("Ошибка фоновой очистки корзины документов" in rec.message for rec in caplog.records)
