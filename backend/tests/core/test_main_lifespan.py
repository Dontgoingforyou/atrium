"""Тесты lifespan приложения (Redis, httpx-клиент, остановка)."""

from __future__ import annotations

import asyncio
import logging
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from app.core.config import Settings


@pytest.mark.asyncio
async def test_lifespan_without_redis_sets_http_client(monkeypatch: pytest.MonkeyPatch) -> None:
    s = Settings(
        database_url="sqlite+aiosqlite:///:memory:",
        redis_url="",
        document_trash_purge_enabled=False,
    )
    monkeypatch.setattr("app.main.get_settings", lambda: s)
    init_cm = MagicMock()
    init_inbox = MagicMock()
    monkeypatch.setattr("app.main.init_ws_managers", init_cm)
    monkeypatch.setattr("app.main.init_inbox_manager", init_inbox)
    init_tg = AsyncMock(return_value=None)
    shutdown_tg = AsyncMock()
    monkeypatch.setattr("app.main.init_telegram_bot", init_tg)
    monkeypatch.setattr("app.main.shutdown_telegram_bot", shutdown_tg)
    dispose = AsyncMock()
    monkeypatch.setattr("app.main.dispose_engine", dispose)

    from app.main import lifespan

    app_obj = MagicMock()
    app_obj.state = SimpleNamespace()

    async with lifespan(app_obj):
        assert getattr(app_obj.state, "http_client", None) is not None
        init_cm.assert_called_once_with(None)
        init_inbox.assert_called_once_with(None)
        init_tg.assert_awaited_once_with(None)

    shutdown_tg.assert_awaited_once_with(None)
    dispose.assert_awaited_once()


@pytest.mark.asyncio
async def test_lifespan_redis_connect_failure_continues_without_cache(monkeypatch: pytest.MonkeyPatch) -> None:
    s = Settings(
        database_url="sqlite+aiosqlite:///:memory:",
        redis_url="redis://localhost:6379/0",
        document_trash_purge_enabled=False,
    )
    monkeypatch.setattr("app.main.get_settings", lambda: s)

    mock_from_url = MagicMock(side_effect=RuntimeError("redis down"))
    monkeypatch.setattr("app.main.aioredis.from_url", mock_from_url)
    set_client = MagicMock()
    monkeypatch.setattr("app.main.set_redis_client", set_client)
    init_cm = MagicMock()
    init_inbox = MagicMock()
    monkeypatch.setattr("app.main.init_ws_managers", init_cm)
    monkeypatch.setattr("app.main.init_inbox_manager", init_inbox)
    init_tg = AsyncMock(return_value=None)
    shutdown_tg = AsyncMock()
    monkeypatch.setattr("app.main.init_telegram_bot", init_tg)
    monkeypatch.setattr("app.main.shutdown_telegram_bot", shutdown_tg)
    dispose = AsyncMock()
    monkeypatch.setattr("app.main.dispose_engine", dispose)

    from app.main import lifespan

    app_obj = MagicMock()
    app_obj.state = SimpleNamespace()

    async with lifespan(app_obj):
        init_cm.assert_called_once_with(None)
        init_inbox.assert_called_once_with(None)
        set_client.assert_not_called()
        init_tg.assert_awaited_once_with(None)

    shutdown_tg.assert_awaited_once_with(None)
    dispose.assert_awaited_once()


@pytest.mark.asyncio
async def test_lifespan_redis_ok_registers_and_closes(monkeypatch: pytest.MonkeyPatch) -> None:
    s = Settings(
        database_url="sqlite+aiosqlite:///:memory:",
        redis_url="redis://localhost:6379/0",
        document_trash_purge_enabled=False,
    )
    monkeypatch.setattr("app.main.get_settings", lambda: s)

    mock_redis = MagicMock()
    mock_redis.ping = AsyncMock()
    mock_redis.aclose = AsyncMock()
    mock_from_url = MagicMock(return_value=mock_redis)
    monkeypatch.setattr("app.main.aioredis.from_url", mock_from_url)
    set_client = MagicMock()
    monkeypatch.setattr("app.main.set_redis_client", set_client)
    init_cm = MagicMock()
    init_inbox = MagicMock()
    monkeypatch.setattr("app.main.init_ws_managers", init_cm)
    monkeypatch.setattr("app.main.init_inbox_manager", init_inbox)
    init_tg = AsyncMock(return_value=None)
    shutdown_tg = AsyncMock()
    monkeypatch.setattr("app.main.init_telegram_bot", init_tg)
    monkeypatch.setattr("app.main.shutdown_telegram_bot", shutdown_tg)
    dispose = AsyncMock()
    monkeypatch.setattr("app.main.dispose_engine", dispose)

    from app.main import lifespan

    app_obj = MagicMock()
    app_obj.state = SimpleNamespace()

    async with lifespan(app_obj):
        init_cm.assert_called_once_with(mock_redis)
        init_inbox.assert_called_once_with(mock_redis)
        set_client.assert_called_once_with(mock_redis)
        init_tg.assert_awaited_once_with(mock_redis)

    shutdown_tg.assert_awaited_once_with(None)
    set_client.assert_any_call(None)
    mock_redis.aclose.assert_awaited_once()
    dispose.assert_awaited_once()


@pytest.mark.asyncio
async def test_lifespan_starts_and_stops_background_purge_tasks(monkeypatch: pytest.MonkeyPatch) -> None:
    s = Settings(
        database_url="sqlite+aiosqlite:///:memory:",
        redis_url="",
        document_trash_purge_enabled=True,
        chat_orphan_attachment_purge_enabled=True,
        calendar_reminders_enabled=True,
        task_due_reminders_enabled=True,
    )
    monkeypatch.setattr("app.main.get_settings", lambda: s)
    monkeypatch.setattr("app.main.init_ws_managers", MagicMock())
    monkeypatch.setattr("app.main.init_inbox_manager", MagicMock())
    monkeypatch.setattr("app.main.init_telegram_bot", AsyncMock(return_value=None))
    monkeypatch.setattr("app.main.shutdown_telegram_bot", AsyncMock())
    monkeypatch.setattr("app.main.dispose_engine", AsyncMock())
    monkeypatch.setattr("app.main.ensure_bucket_exists", MagicMock())

    trash_stops: list[asyncio.Event] = []
    orphan_stops: list[asyncio.Event] = []
    calendar_stops: list[asyncio.Event] = []
    task_due_stops: list[asyncio.Event] = []

    async def fake_trash_loop(stop_event: asyncio.Event, _settings: Settings) -> None:
        trash_stops.append(stop_event)
        await stop_event.wait()

    async def fake_orphan_loop(stop_event: asyncio.Event, _settings: Settings) -> None:
        orphan_stops.append(stop_event)
        await stop_event.wait()

    async def fake_calendar_loop(stop_event: asyncio.Event, _settings: Settings) -> None:
        calendar_stops.append(stop_event)
        await stop_event.wait()

    async def fake_task_due_loop(stop_event: asyncio.Event, _settings: Settings) -> None:
        task_due_stops.append(stop_event)
        await stop_event.wait()

    monkeypatch.setattr("app.main.run_document_trash_purge_loop", fake_trash_loop)
    monkeypatch.setattr("app.main.run_chat_orphan_attachment_purge_loop", fake_orphan_loop)
    monkeypatch.setattr("app.main.run_calendar_reminders_loop", fake_calendar_loop)
    monkeypatch.setattr("app.main.run_task_due_reminders_loop", fake_task_due_loop)

    from app.main import lifespan

    app_obj = MagicMock()
    app_obj.state = SimpleNamespace()

    async with lifespan(app_obj):
        await asyncio.sleep(0)
        assert len(trash_stops) == 1
        assert len(orphan_stops) == 1
        assert len(calendar_stops) == 1
        assert len(task_due_stops) == 1
        assert trash_stops[0] is not orphan_stops[0]
        assert calendar_stops[0] is not trash_stops[0]
        assert task_due_stops[0] is not calendar_stops[0]

    assert trash_stops[0].is_set()
    assert orphan_stops[0].is_set()
    assert calendar_stops[0].is_set()
    assert task_due_stops[0].is_set()


@pytest.mark.asyncio
async def test_lifespan_warns_when_minio_public_endpoint_missing(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    s = Settings(
        database_url="sqlite+aiosqlite:///:memory:",
        redis_url="",
        document_trash_purge_enabled=False,
        minio_endpoint="minio:9000",
        minio_public_endpoint="",
    )
    monkeypatch.setattr("app.main.get_settings", lambda: s)
    monkeypatch.setattr("app.main.init_ws_managers", MagicMock())
    monkeypatch.setattr("app.main.init_inbox_manager", MagicMock())
    monkeypatch.setattr("app.main.init_telegram_bot", AsyncMock(return_value=None))
    monkeypatch.setattr("app.main.shutdown_telegram_bot", AsyncMock())
    monkeypatch.setattr("app.main.dispose_engine", AsyncMock())
    monkeypatch.setattr("app.main.ensure_bucket_exists", MagicMock())

    from app.main import lifespan

    app_obj = MagicMock()
    app_obj.state = SimpleNamespace()

    caplog.set_level(logging.WARNING, logger="app.main")
    async with lifespan(app_obj):
        pass

    assert any("MINIO_PUBLIC_ENDPOINT" in rec.message for rec in caplog.records)


@pytest.mark.asyncio
async def test_lifespan_continues_when_minio_bucket_ensure_fails(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    s = Settings(
        database_url="sqlite+aiosqlite:///:memory:",
        redis_url="",
        document_trash_purge_enabled=False,
    )
    monkeypatch.setattr("app.main.get_settings", lambda: s)
    monkeypatch.setattr("app.main.init_ws_managers", MagicMock())
    monkeypatch.setattr("app.main.init_inbox_manager", MagicMock())
    monkeypatch.setattr("app.main.init_telegram_bot", AsyncMock(return_value=None))
    monkeypatch.setattr("app.main.shutdown_telegram_bot", AsyncMock())
    monkeypatch.setattr("app.main.dispose_engine", AsyncMock())
    monkeypatch.setattr("app.main.ensure_bucket_exists", MagicMock(side_effect=RuntimeError("minio down")))

    from app.main import lifespan

    app_obj = MagicMock()
    app_obj.state = SimpleNamespace()

    caplog.set_level(logging.WARNING, logger="app.main")
    async with lifespan(app_obj):
        assert getattr(app_obj.state, "http_client", None) is not None

    assert any("MinIO недоступен" in rec.message for rec in caplog.records)


@pytest.mark.asyncio
async def test_lifespan_masks_redis_password_in_log(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    s = Settings(
        database_url="sqlite+aiosqlite:///:memory:",
        redis_url="redis://user:topsecret@redis:6379/0",
        document_trash_purge_enabled=False,
    )
    monkeypatch.setattr("app.main.get_settings", lambda: s)
    mock_redis = MagicMock()
    mock_redis.ping = AsyncMock()
    mock_redis.aclose = AsyncMock()
    monkeypatch.setattr("app.main.aioredis.from_url", MagicMock(return_value=mock_redis))
    monkeypatch.setattr("app.main.set_redis_client", MagicMock())
    monkeypatch.setattr("app.main.init_ws_managers", MagicMock())
    monkeypatch.setattr("app.main.init_inbox_manager", MagicMock())
    monkeypatch.setattr("app.main.init_telegram_bot", AsyncMock(return_value=None))
    monkeypatch.setattr("app.main.shutdown_telegram_bot", AsyncMock())
    monkeypatch.setattr("app.main.dispose_engine", AsyncMock())

    from app.main import lifespan

    app_obj = MagicMock()
    app_obj.state = SimpleNamespace()

    caplog.set_level(logging.INFO, logger="app.main")
    async with lifespan(app_obj):
        pass

    redis_logs = [rec.message for rec in caplog.records if "Redis подключён" in rec.message]
    assert len(redis_logs) == 1
    assert "topsecret" not in redis_logs[0]
    assert "***" in redis_logs[0]
