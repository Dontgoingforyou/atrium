"""Тесты цикла фоновых напоминаний календаря."""

from __future__ import annotations

import asyncio
import logging
from unittest.mock import AsyncMock, MagicMock

import pytest
from app.core.config import Settings
from app.jobs.calendar_reminders import run_calendar_reminders_loop


def _session_factory(session: AsyncMock) -> MagicMock:
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=session)
    cm.__aexit__ = AsyncMock(return_value=None)
    return MagicMock(return_value=cm)


@pytest.mark.asyncio
async def test_calendar_reminders_loop_disabled_does_not_call_process(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    process = AsyncMock()
    monkeypatch.setattr("app.jobs.calendar_reminders.process_due_reminders", process)
    wait_for = AsyncMock()
    monkeypatch.setattr("app.jobs.calendar_reminders.asyncio.wait_for", wait_for)

    stop = asyncio.Event()
    settings = Settings(
        database_url="sqlite+aiosqlite:///:memory:",
        calendar_reminders_enabled=False,
    )
    await run_calendar_reminders_loop(stop, settings)

    wait_for.assert_not_awaited()
    process.assert_not_awaited()


@pytest.mark.asyncio
async def test_calendar_reminders_loop_runs_process_after_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    process = AsyncMock(return_value=2)
    monkeypatch.setattr("app.jobs.calendar_reminders.process_due_reminders", process)
    session = AsyncMock()
    monkeypatch.setattr(
        "app.jobs.calendar_reminders.async_session_factory",
        _session_factory(session),
    )

    stop = asyncio.Event()
    settings = Settings(
        database_url="sqlite+aiosqlite:///:memory:",
        calendar_reminders_enabled=True,
        calendar_reminders_interval_seconds=15,
    )

    async def stop_after_process(_session: AsyncMock) -> int:
        stop.set()
        return 2

    process.side_effect = stop_after_process

    async def first_wait_times_out(awaitable: object, timeout: object = None) -> None:
        if asyncio.iscoroutine(awaitable):
            awaitable.close()
        raise TimeoutError

    monkeypatch.setattr("app.jobs.calendar_reminders.asyncio.wait_for", first_wait_times_out)

    await run_calendar_reminders_loop(stop, settings)

    process.assert_awaited_once_with(session)


@pytest.mark.asyncio
async def test_calendar_reminders_loop_floors_interval_to_15(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    timeouts: list[float] = []
    stop = asyncio.Event()

    async def capture_wait(awaitable: object, timeout: object = None) -> None:
        timeouts.append(float(timeout) if timeout is not None else 0.0)
        if asyncio.iscoroutine(awaitable):
            awaitable.close()
        stop.set()

    monkeypatch.setattr("app.jobs.calendar_reminders.asyncio.wait_for", capture_wait)
    process = AsyncMock()
    monkeypatch.setattr("app.jobs.calendar_reminders.process_due_reminders", process)

    settings = Settings(
        database_url="sqlite+aiosqlite:///:memory:",
        calendar_reminders_enabled=True,
        calendar_reminders_interval_seconds=15,
    )
    object.__setattr__(settings, "calendar_reminders_interval_seconds", 5)

    await run_calendar_reminders_loop(stop, settings)

    assert timeouts == [15.0]
    process.assert_not_awaited()


@pytest.mark.asyncio
async def test_calendar_reminders_loop_returns_after_timeout_if_stop_set(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    process = AsyncMock()
    monkeypatch.setattr("app.jobs.calendar_reminders.process_due_reminders", process)

    stop = asyncio.Event()
    real_wait_for = asyncio.wait_for

    async def wait_for_sets_stop_on_timeout(awaitable: object, timeout: float | None = None) -> object:
        try:
            return await real_wait_for(awaitable, timeout=timeout)
        except TimeoutError:
            stop.set()
            raise

    monkeypatch.setattr("app.jobs.calendar_reminders.asyncio.wait_for", wait_for_sets_stop_on_timeout)

    settings = Settings(
        database_url="sqlite+aiosqlite:///:memory:",
        calendar_reminders_enabled=True,
        calendar_reminders_interval_seconds=15,
    )
    await run_calendar_reminders_loop(stop, settings)

    process.assert_not_awaited()


@pytest.mark.asyncio
async def test_calendar_reminders_loop_stops_when_event_set_during_wait(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    process = AsyncMock()
    monkeypatch.setattr("app.jobs.calendar_reminders.process_due_reminders", process)

    stop = asyncio.Event()
    settings = Settings(
        database_url="sqlite+aiosqlite:///:memory:",
        calendar_reminders_enabled=True,
        calendar_reminders_interval_seconds=600,
    )

    task = asyncio.create_task(run_calendar_reminders_loop(stop, settings))
    await asyncio.sleep(0)
    stop.set()
    await asyncio.wait_for(task, timeout=1.0)

    process.assert_not_awaited()


@pytest.mark.asyncio
async def test_calendar_reminders_loop_continues_after_process_error(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    process = AsyncMock()
    monkeypatch.setattr("app.jobs.calendar_reminders.process_due_reminders", process)
    session = AsyncMock()
    monkeypatch.setattr(
        "app.jobs.calendar_reminders.async_session_factory",
        _session_factory(session),
    )

    stop = asyncio.Event()

    async def fail_then_stop(_session: AsyncMock) -> int:
        if process.await_count == 1:
            raise RuntimeError("reminders failed")
        stop.set()
        return 0

    process.side_effect = fail_then_stop

    async def always_timeout_until_stopped(awaitable: object, timeout: object = None) -> None:
        if asyncio.iscoroutine(awaitable):
            awaitable.close()
        if stop.is_set():
            return None
        raise TimeoutError

    monkeypatch.setattr("app.jobs.calendar_reminders.asyncio.wait_for", always_timeout_until_stopped)

    settings = Settings(
        database_url="sqlite+aiosqlite:///:memory:",
        calendar_reminders_enabled=True,
        calendar_reminders_interval_seconds=15,
    )

    caplog.set_level(logging.ERROR, logger="app.jobs.calendar_reminders")
    await run_calendar_reminders_loop(stop, settings)

    assert process.await_count == 2
    assert any("Ошибка фоновой отправки напоминаний календаря" in rec.message for rec in caplog.records)
