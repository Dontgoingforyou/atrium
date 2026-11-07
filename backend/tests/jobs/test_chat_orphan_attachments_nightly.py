"""Тесты цикла фоновой очистки осиротевших вложений чата."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from app.core.config import Settings
from app.jobs.chat_orphan_attachments_nightly import run_chat_orphan_attachment_purge_loop


def _session_factory(session: AsyncMock) -> MagicMock:
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=session)
    cm.__aexit__ = AsyncMock(return_value=None)
    return MagicMock(return_value=cm)


@pytest.mark.asyncio
async def test_orphan_purge_loop_disabled_does_not_call_purge(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seconds = MagicMock(return_value=0.0)
    monkeypatch.setattr("app.jobs.chat_orphan_attachments_nightly.seconds_until_next_run_utc", seconds)
    purge = AsyncMock()
    monkeypatch.setattr(
        "app.jobs.chat_orphan_attachments_nightly.att_svc.purge_orphan_attachments_older_than",
        purge,
    )

    stop = asyncio.Event()
    settings = Settings(
        database_url="sqlite+aiosqlite:///:memory:",
        chat_orphan_attachment_purge_enabled=False,
    )
    await run_chat_orphan_attachment_purge_loop(stop, settings)

    seconds.assert_not_called()
    purge.assert_not_awaited()


@pytest.mark.asyncio
async def test_orphan_purge_loop_passes_hour_from_settings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    hours: list[int] = []
    stop = asyncio.Event()

    def capture_hour(_now: datetime, hour: int) -> float:
        hours.append(hour)
        stop.set()
        return 3600.0

    monkeypatch.setattr("app.jobs.chat_orphan_attachments_nightly.seconds_until_next_run_utc", capture_hour)
    purge = AsyncMock()
    monkeypatch.setattr(
        "app.jobs.chat_orphan_attachments_nightly.att_svc.purge_orphan_attachments_older_than",
        purge,
    )

    settings = Settings(
        database_url="sqlite+aiosqlite:///:memory:",
        chat_orphan_attachment_purge_enabled=True,
        chat_orphan_attachment_purge_hour_utc=5,
    )
    await run_chat_orphan_attachment_purge_loop(stop, settings)

    assert hours == [5]
    purge.assert_not_awaited()


@pytest.mark.asyncio
async def test_orphan_purge_loop_runs_purge_after_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "app.jobs.chat_orphan_attachments_nightly.seconds_until_next_run_utc",
        lambda _now, _hour: 0.0,
    )
    purge = AsyncMock(return_value=2)
    monkeypatch.setattr(
        "app.jobs.chat_orphan_attachments_nightly.att_svc.purge_orphan_attachments_older_than",
        purge,
    )
    session = AsyncMock()
    monkeypatch.setattr(
        "app.jobs.chat_orphan_attachments_nightly.async_session_factory",
        _session_factory(session),
    )

    stop = asyncio.Event()
    settings = Settings(
        database_url="sqlite+aiosqlite:///:memory:",
        chat_orphan_attachment_purge_enabled=True,
        chat_orphan_attachment_purge_min_age_hours=48.0,
    )

    async def stop_after_purge(*_args: object, **_kwargs: object) -> int:
        stop.set()
        return 2

    purge.side_effect = stop_after_purge

    await run_chat_orphan_attachment_purge_loop(stop, settings)

    purge.assert_awaited_once_with(session, min_age_hours=48.0)


@pytest.mark.asyncio
async def test_orphan_purge_loop_returns_after_timeout_if_stop_set(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "app.jobs.chat_orphan_attachments_nightly.seconds_until_next_run_utc",
        lambda _now, _hour: 0.0,
    )
    purge = AsyncMock()
    monkeypatch.setattr(
        "app.jobs.chat_orphan_attachments_nightly.att_svc.purge_orphan_attachments_older_than",
        purge,
    )

    stop = asyncio.Event()
    real_wait_for = asyncio.wait_for

    async def wait_for_sets_stop_on_timeout(awaitable: object, timeout: float | None = None) -> object:
        try:
            return await real_wait_for(awaitable, timeout=timeout)
        except TimeoutError:
            stop.set()
            raise

    monkeypatch.setattr(
        "app.jobs.chat_orphan_attachments_nightly.asyncio.wait_for",
        wait_for_sets_stop_on_timeout,
    )

    settings = Settings(
        database_url="sqlite+aiosqlite:///:memory:",
        chat_orphan_attachment_purge_enabled=True,
    )
    await run_chat_orphan_attachment_purge_loop(stop, settings)

    purge.assert_not_awaited()


@pytest.mark.asyncio
async def test_orphan_purge_loop_stops_when_event_set_during_wait(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "app.jobs.chat_orphan_attachments_nightly.seconds_until_next_run_utc",
        lambda _now, _hour: 3600.0,
    )
    purge = AsyncMock()
    monkeypatch.setattr(
        "app.jobs.chat_orphan_attachments_nightly.att_svc.purge_orphan_attachments_older_than",
        purge,
    )

    stop = asyncio.Event()
    settings = Settings(
        database_url="sqlite+aiosqlite:///:memory:",
        chat_orphan_attachment_purge_enabled=True,
    )

    task = asyncio.create_task(run_chat_orphan_attachment_purge_loop(stop, settings))
    await asyncio.sleep(0)
    stop.set()
    await asyncio.wait_for(task, timeout=1.0)

    purge.assert_not_awaited()


@pytest.mark.asyncio
async def test_orphan_purge_loop_continues_after_purge_error(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    monkeypatch.setattr(
        "app.jobs.chat_orphan_attachments_nightly.seconds_until_next_run_utc",
        lambda _now, _hour: 0.0,
    )
    purge = AsyncMock()
    monkeypatch.setattr(
        "app.jobs.chat_orphan_attachments_nightly.att_svc.purge_orphan_attachments_older_than",
        purge,
    )
    session = AsyncMock()
    monkeypatch.setattr(
        "app.jobs.chat_orphan_attachments_nightly.async_session_factory",
        _session_factory(session),
    )

    stop = asyncio.Event()

    async def fail_then_stop(*_args: object, **_kwargs: object) -> int:
        if purge.await_count == 1:
            raise RuntimeError("purge failed")
        stop.set()
        return 0

    purge.side_effect = fail_then_stop

    settings = Settings(
        database_url="sqlite+aiosqlite:///:memory:",
        chat_orphan_attachment_purge_enabled=True,
    )

    caplog.set_level(logging.ERROR, logger="app.jobs.chat_orphan_attachments_nightly")
    await run_chat_orphan_attachment_purge_loop(stop, settings)

    assert purge.await_count == 2
    assert any("Ошибка фоновой очистки осиротевших вложений чата" in rec.message for rec in caplog.records)
