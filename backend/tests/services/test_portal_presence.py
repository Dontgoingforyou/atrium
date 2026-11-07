"""Тесты сервиса присутствия: фейковый async Redis (без реального подключения)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

import pytest
from app.services import portal_presence as presence

_TTL = presence._TTL_SEC  # 300


class _FakePipeline:
    def __init__(
        self,
        store: dict[str, dict[str, str]],
        string_store: dict[str, str],
        fail_execute: bool,
    ) -> None:
        self._store = store
        self._string_store = string_store
        self._fail_execute = fail_execute
        self._keys: list[str] = []
        self._mode: str = "hgetall"

    def hgetall(self, key: str) -> _FakePipeline:
        self._mode = "hgetall"
        self._keys.append(key)
        return self

    def get(self, key: str) -> _FakePipeline:
        self._mode = "get"
        self._keys.append(key)
        return self

    async def execute(self) -> list[Any]:
        if self._fail_execute:
            raise RuntimeError("redis pipeline down")
        if self._mode == "get":
            return [self._string_store.get(k) for k in self._keys]
        return [dict(self._store.get(k, {})) for k in self._keys]


class FakeAsyncRedis:
    def __init__(self, *, fail_execute: bool = False) -> None:
        self.store: dict[str, dict[str, str]] = {}
        self.string_store: dict[str, str] = {}
        self.delete_calls: list[str] = []
        self.expire_calls: list[tuple[str, int]] = []
        self.fail_execute = fail_execute

    async def delete(self, key: str) -> Any:
        self.delete_calls.append(key)
        self.store.pop(key, None)
        self.string_store.pop(key, None)
        return 1

    async def set(self, key: str, value: str, ex: int | None = None) -> Any:
        del ex
        self.string_store[key] = value
        return True

    async def get(self, key: str) -> str | None:
        return self.string_store.get(key)

    async def hset(self, key: str, mapping: dict[str, str] | None = None, **kwargs: Any) -> Any:
        if mapping:
            self.store.setdefault(key, {}).update(mapping)
        return 1

    async def hget(self, key: str, field: str) -> str | None:
        return self.store.get(key, {}).get(field)

    async def expire(self, key: str, ttl: int) -> Any:
        self.expire_calls.append((key, ttl))
        return True

    def pipeline(self) -> _FakePipeline:
        return _FakePipeline(self.store, self.string_store, self.fail_execute)


@pytest.fixture
def fake_redis() -> FakeAsyncRedis:
    return FakeAsyncRedis()


@pytest.mark.asyncio
async def test_record_presence_visible_false_deletes(
    monkeypatch: pytest.MonkeyPatch,
    fake_redis: FakeAsyncRedis,
) -> None:
    monkeypatch.setattr(presence, "get_redis_client", lambda: fake_redis)
    fake_redis.store["portal:presence:u1"] = {"last_seen": "1", "last_active": "1"}

    await presence.record_presence(user_sub="u1", visible=False, active=True)

    assert "portal:presence:u1" not in fake_redis.store
    assert fake_redis.delete_calls == ["portal:presence:u1"]


@pytest.mark.asyncio
async def test_record_presence_visible_false_does_not_update_iso(
    monkeypatch: pytest.MonkeyPatch,
    fake_redis: FakeAsyncRedis,
) -> None:
    monkeypatch.setattr(presence, "get_redis_client", lambda: fake_redis)
    iso_k = "portal:last_seen_iso:u1"
    fake_redis.string_store[iso_k] = "2024-01-01T00:00:00+00:00"

    await presence.record_presence(user_sub="u1", visible=False, active=False)

    assert fake_redis.string_store[iso_k] == "2024-01-01T00:00:00+00:00"


@pytest.mark.asyncio
async def test_set_last_seen_iso_now_writes_key(
    monkeypatch: pytest.MonkeyPatch,
    fake_redis: FakeAsyncRedis,
) -> None:
    monkeypatch.setattr(presence, "get_redis_client", lambda: fake_redis)
    fixed_iso = "2025-05-01T12:00:00+00:00"
    monkeypatch.setattr(presence, "_now_iso", lambda: fixed_iso)

    await presence.set_last_seen_iso_now(user_sub="u5")

    assert fake_redis.string_store["portal:last_seen_iso:u5"] == fixed_iso


@pytest.mark.asyncio
async def test_record_presence_active_sets_both_timestamps(
    monkeypatch: pytest.MonkeyPatch,
    fake_redis: FakeAsyncRedis,
) -> None:
    monkeypatch.setattr(presence, "get_redis_client", lambda: fake_redis)
    monkeypatch.setattr(presence.time, "time", lambda: 1_700_000_000)

    await presence.record_presence(user_sub="u2", visible=True, active=True)

    key = "portal:presence:u2"
    assert fake_redis.store[key]["last_seen"] == str(1_700_000_000)
    assert fake_redis.store[key]["last_active"] == str(1_700_000_000)
    assert fake_redis.expire_calls == [(key, _TTL)]


@pytest.mark.asyncio
async def test_record_presence_inactive_keeps_previous_last_active(
    monkeypatch: pytest.MonkeyPatch,
    fake_redis: FakeAsyncRedis,
) -> None:
    monkeypatch.setattr(presence, "get_redis_client", lambda: fake_redis)
    monkeypatch.setattr(presence.time, "time", lambda: 100)
    key = "portal:presence:u3"
    fake_redis.store[key] = {"last_seen": "50", "last_active": "42"}

    await presence.record_presence(user_sub="u3", visible=True, active=False)

    assert fake_redis.store[key]["last_active"] == "42"
    assert fake_redis.store[key]["last_seen"] == "100"
    assert fake_redis.expire_calls[-1] == (key, _TTL)


@pytest.mark.asyncio
async def test_record_presence_inactive_no_previous_last_active_uses_now(
    monkeypatch: pytest.MonkeyPatch,
    fake_redis: FakeAsyncRedis,
) -> None:
    monkeypatch.setattr(presence, "get_redis_client", lambda: fake_redis)
    monkeypatch.setattr(presence.time, "time", lambda: 999)
    key = "portal:presence:u4"
    fake_redis.store[key] = {"last_seen": "1"}

    await presence.record_presence(user_sub="u4", visible=True, active=False)

    assert fake_redis.store[key]["last_active"] == "999"
    assert fake_redis.store[key]["last_seen"] == "999"


@pytest.mark.asyncio
async def test_record_presence_active_updates_last_seen_iso(
    monkeypatch: pytest.MonkeyPatch,
    fake_redis: FakeAsyncRedis,
) -> None:
    monkeypatch.setattr(presence, "get_redis_client", lambda: fake_redis)
    fixed_iso = "2026-01-15T10:00:00+00:00"
    monkeypatch.setattr(presence, "_now_iso", lambda: fixed_iso)
    monkeypatch.setattr(presence.time, "time", lambda: 1_700_000_000)

    await presence.record_presence(user_sub="u6", visible=True, active=True)

    assert fake_redis.string_store["portal:last_seen_iso:u6"] == fixed_iso


@pytest.mark.asyncio
async def test_record_presence_no_redis_returns_quietly(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(presence, "get_redis_client", lambda: None)
    await presence.record_presence(user_sub="x", visible=True, active=True)
    assert presence.get_redis_client() is None


@pytest.mark.asyncio
async def test_record_presence_write_error_swallowed(monkeypatch: pytest.MonkeyPatch) -> None:
    class BadRedis(FakeAsyncRedis):
        async def hset(self, key: str, mapping: dict[str, str] | None = None, **kwargs: Any) -> Any:
            raise RuntimeError("boom")

    bad = BadRedis()
    bad.store["portal:presence:z"] = {"last_seen": "1", "last_active": "1"}
    monkeypatch.setattr(presence, "get_redis_client", lambda: bad)
    await presence.record_presence(user_sub="z", visible=True, active=True)
    assert bad.store["portal:presence:z"] == {"last_seen": "1", "last_active": "1"}
    assert bad.delete_calls == []


@pytest.mark.asyncio
async def test_bulk_last_seen_iso_empty_list(
    monkeypatch: pytest.MonkeyPatch,
    fake_redis: FakeAsyncRedis,
) -> None:
    monkeypatch.setattr(presence, "get_redis_client", lambda: fake_redis)
    assert await presence.bulk_last_seen_iso([]) == {}


@pytest.mark.asyncio
async def test_bulk_last_seen_iso_no_redis(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(presence, "get_redis_client", lambda: None)
    out = await presence.bulk_last_seen_iso(["a", "b"])
    assert out == {"a": None, "b": None}


@pytest.mark.asyncio
async def test_bulk_last_seen_iso_parses_str_and_bytes(
    monkeypatch: pytest.MonkeyPatch,
    fake_redis: FakeAsyncRedis,
) -> None:
    monkeypatch.setattr(presence, "get_redis_client", lambda: fake_redis)
    iso = "2026-02-01T08:30:00+00:00"
    fake_redis.string_store["portal:last_seen_iso:sub-a"] = iso
    fake_redis.string_store["portal:last_seen_iso:sub-b"] = iso.encode()

    out = await presence.bulk_last_seen_iso(["sub-a", "sub-b", "missing"])
    expected = datetime.fromisoformat(iso)
    assert out["sub-a"] == expected
    assert out["sub-b"] == expected
    assert out["missing"] is None


@pytest.mark.asyncio
async def test_bulk_last_seen_iso_invalid_iso_skipped(
    monkeypatch: pytest.MonkeyPatch,
    fake_redis: FakeAsyncRedis,
) -> None:
    monkeypatch.setattr(presence, "get_redis_client", lambda: fake_redis)
    fake_redis.string_store["portal:last_seen_iso:bad"] = "not-a-datetime"

    out = await presence.bulk_last_seen_iso(["bad"])
    assert out["bad"] is None


@pytest.mark.asyncio
async def test_bulk_last_seen_iso_pipeline_error_returns_none(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bad_redis = FakeAsyncRedis(fail_execute=True)
    monkeypatch.setattr(presence, "get_redis_client", lambda: bad_redis)
    out = await presence.bulk_last_seen_iso(["x"])
    assert out == {"x": None}


@pytest.mark.asyncio
async def test_presence_for_subs_no_redis_all_offline(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(presence, "get_redis_client", lambda: None)
    out = await presence.presence_for_subs(["a", "b"])
    assert out == {"a": "offline", "b": "offline"}


@pytest.mark.asyncio
async def test_presence_for_subs_empty_list(monkeypatch: pytest.MonkeyPatch, fake_redis: FakeAsyncRedis) -> None:
    monkeypatch.setattr(presence, "get_redis_client", lambda: fake_redis)
    out = await presence.presence_for_subs([])
    assert out == {}


@pytest.mark.asyncio
async def test_presence_for_subs_pipeline_success(
    monkeypatch: pytest.MonkeyPatch,
    fake_redis: FakeAsyncRedis,
) -> None:
    monkeypatch.setattr(presence, "get_redis_client", lambda: fake_redis)
    fix_now = 10_000
    monkeypatch.setattr(presence.time, "time", lambda: fix_now)

    # online: heartbeat fresh, active fresh
    fake_redis.store["portal:presence:on"] = {
        "last_seen": str(fix_now),
        "last_active": str(fix_now),
    }
    # away: heartbeat ok, active old
    fake_redis.store["portal:presence:aw"] = {
        "last_seen": str(fix_now),
        "last_active": str(fix_now - 400),
    }
    # offline: heartbeat stale
    fake_redis.store["portal:presence:off"] = {
        "last_seen": str(fix_now - 200),
        "last_active": str(fix_now - 200),
    }

    out = await presence.presence_for_subs(["on", "aw", "off", "missing"])
    assert out["on"] == "online"
    assert out["aw"] == "away"
    assert out["off"] == "offline"
    assert out["missing"] == "offline"


@pytest.mark.asyncio
async def test_presence_for_subs_invalid_hash_values_offline(
    monkeypatch: pytest.MonkeyPatch,
    fake_redis: FakeAsyncRedis,
) -> None:
    monkeypatch.setattr(presence, "get_redis_client", lambda: fake_redis)
    monkeypatch.setattr(presence.time, "time", lambda: 1000)
    fake_redis.store["portal:presence:bad"] = {"last_seen": "not-int", "last_active": "0"}

    out = await presence.presence_for_subs(["bad"])
    assert out["bad"] == "offline"


@pytest.mark.asyncio
async def test_presence_for_subs_execute_error_returns_all_offline(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bad_redis = FakeAsyncRedis(fail_execute=True)
    monkeypatch.setattr(presence, "get_redis_client", lambda: bad_redis)
    bad_redis.store["portal:presence:x"] = {"last_seen": "1", "last_active": "1"}

    out = await presence.presence_for_subs(["x"])
    assert out == {"x": "offline"}


class _RedisPipelineReturnsNone(FakeAsyncRedis):
    """Симулирует ответ pipeline, не являющийся dict (ветка ``else {}``)."""

    def pipeline(self) -> _FakePipeline:
        p = _FakePipeline(self.store, self.string_store, fail_execute=False)

        async def _exec() -> list[Any]:
            return [None]

        p.execute = _exec  # type: ignore[method-assign]
        return p


@pytest.mark.asyncio
async def test_presence_for_subs_non_dict_row_treated_empty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    r = _RedisPipelineReturnsNone()
    monkeypatch.setattr(presence, "get_redis_client", lambda: r)
    monkeypatch.setattr(presence.time, "time", lambda: 5000)

    out = await presence.presence_for_subs(["only"])
    assert out["only"] == "offline"
