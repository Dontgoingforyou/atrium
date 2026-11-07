"""Тесты записи last_seen_at в профиль (дополнение к Redis-присутствию)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from app.infrastructure.db.models.portal_user_profile import PortalUserProfile
from app.services import portal_last_seen as pls
from sqlalchemy.ext.asyncio import AsyncSession


def _patch_now_utc(monkeypatch: pytest.MonkeyPatch, instants: datetime | list[datetime]) -> None:
    """Подменяем ``now_utc`` фиксированным или последовательным временем."""
    if isinstance(instants, datetime):
        monkeypatch.setattr(pls, "now_utc", lambda: instants)
        return
    it = iter(instants)
    monkeypatch.setattr(pls, "now_utc", lambda: next(it))


def _assert_last_seen_equals(row: PortalUserProfile | None, expected: datetime) -> None:
    """SQLite в тестах часто отдаёт naive UTC — сравниваем по моменту времени."""
    assert row is not None
    got = row.last_seen_at
    assert got is not None
    if got.tzinfo is None:
        got = got.replace(tzinfo=UTC)
    assert got == expected


@pytest.mark.asyncio
async def test_touch_last_seen_visible_false_is_noop(
    sqlite_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    row = await sqlite_session.get(PortalUserProfile, "admin-sub")
    assert row is not None
    stale = datetime(2020, 1, 1, 0, 0, 0, tzinfo=UTC)
    row.last_seen_at = stale
    await sqlite_session.commit()

    fixed = datetime(2024, 6, 15, 10, 30, 0, tzinfo=UTC)
    _patch_now_utc(monkeypatch, fixed)

    await pls.touch_last_seen_in_db(sqlite_session, user_sub="admin-sub", visible=False)

    await sqlite_session.refresh(row)
    _assert_last_seen_equals(row, stale)


@pytest.mark.asyncio
async def test_finalize_last_seen_in_db_sets_timestamp(
    sqlite_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixed = datetime(2024, 6, 15, 10, 30, 0, tzinfo=UTC)
    _patch_now_utc(monkeypatch, fixed)

    await pls.finalize_last_seen_in_db(sqlite_session, user_sub="admin-sub")

    row = await sqlite_session.get(PortalUserProfile, "admin-sub")
    _assert_last_seen_equals(row, fixed)


@pytest.mark.asyncio
async def test_touch_last_seen_visible_true_updates_when_last_seen_null(
    sqlite_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    row = await sqlite_session.get(PortalUserProfile, "admin-sub")
    assert row is not None
    row.last_seen_at = None
    await sqlite_session.commit()

    fixed = datetime(2024, 7, 1, 8, 0, 0, tzinfo=UTC)
    _patch_now_utc(monkeypatch, fixed)

    await pls.touch_last_seen_in_db(sqlite_session, user_sub="admin-sub", visible=True)

    await sqlite_session.refresh(row)
    _assert_last_seen_equals(row, fixed)


@pytest.mark.asyncio
async def test_touch_last_seen_visible_true_throttled_when_within_window(
    sqlite_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    t_first = datetime(2024, 8, 1, 12, 0, 0, tzinfo=UTC)
    t_second = t_first + timedelta(seconds=10)
    _patch_now_utc(monkeypatch, [t_first, t_second])

    await pls.touch_last_seen_in_db(sqlite_session, user_sub="admin-sub", visible=True)
    row = await sqlite_session.get(PortalUserProfile, "admin-sub")
    assert row is not None
    await sqlite_session.refresh(row)
    _assert_last_seen_equals(row, t_first)

    # Иначе при втором UPDATE ORM сравнивает naive last_seen из SQLite с aware threshold в Python
    sqlite_session.expire_all()

    await pls.touch_last_seen_in_db(sqlite_session, user_sub="admin-sub", visible=True)
    row = await sqlite_session.get(PortalUserProfile, "admin-sub")
    await sqlite_session.refresh(row)
    _assert_last_seen_equals(row, t_first)


@pytest.mark.asyncio
async def test_touch_last_seen_visible_true_updates_when_older_than_throttle(
    sqlite_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    row = await sqlite_session.get(PortalUserProfile, "admin-sub")
    assert row is not None
    stale = datetime(2020, 1, 1, 0, 0, 0, tzinfo=UTC)
    row.last_seen_at = stale
    await sqlite_session.commit()

    t_new = datetime(2024, 9, 1, 15, 0, 0, tzinfo=UTC)
    _patch_now_utc(monkeypatch, t_new)

    await pls.touch_last_seen_in_db(sqlite_session, user_sub="admin-sub", visible=True)

    await sqlite_session.refresh(row)
    _assert_last_seen_equals(row, t_new)


@pytest.mark.asyncio
async def test_touch_last_seen_visible_true_updates_after_throttle_window(
    sqlite_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """После паузы дольше окна троттлинга снова пишем (строго > N с: при now=T+N порог T, равенство не проходит)."""
    t_first = datetime(2024, 10, 1, 12, 0, 0, tzinfo=UTC)
    t_next = t_first + timedelta(seconds=pls._LAST_SEEN_THROTTLE_SEC + 1)
    _patch_now_utc(monkeypatch, [t_first, t_next])

    await pls.touch_last_seen_in_db(sqlite_session, user_sub="admin-sub", visible=True)
    row = await sqlite_session.get(PortalUserProfile, "admin-sub")
    assert row is not None
    await sqlite_session.refresh(row)
    _assert_last_seen_equals(row, t_first)

    sqlite_session.expire_all()

    await pls.touch_last_seen_in_db(sqlite_session, user_sub="admin-sub", visible=True)
    row = await sqlite_session.get(PortalUserProfile, "admin-sub")
    await sqlite_session.refresh(row)
    _assert_last_seen_equals(row, t_next)


@pytest.mark.asyncio
async def test_touch_last_seen_unknown_sub_is_noop(
    sqlite_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """UPDATE без совпадения sub не меняет существующие профили."""
    row = await sqlite_session.get(PortalUserProfile, "admin-sub")
    assert row is not None
    stale = datetime(2020, 1, 1, 0, 0, 0, tzinfo=UTC)
    row.last_seen_at = stale
    await sqlite_session.commit()

    fixed = datetime(2024, 11, 1, 9, 0, 0, tzinfo=UTC)
    _patch_now_utc(monkeypatch, fixed)

    await pls.touch_last_seen_in_db(sqlite_session, user_sub="no-such-sub", visible=True)

    await sqlite_session.refresh(row)
    _assert_last_seen_equals(row, stale)


@pytest.mark.asyncio
async def test_touch_last_seen_at_exact_threshold_not_updated(
    sqlite_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """При ``last_seen_at == now - throttle`` UPDATE не проходит (строго ``< threshold``)."""
    t_base = datetime(2024, 12, 1, 12, 0, 0, tzinfo=UTC)
    t_touch = t_base + timedelta(seconds=pls._LAST_SEEN_THROTTLE_SEC)
    row = await sqlite_session.get(PortalUserProfile, "admin-sub")
    assert row is not None
    row.last_seen_at = t_base
    await sqlite_session.commit()

    _patch_now_utc(monkeypatch, t_touch)

    await pls.touch_last_seen_in_db(sqlite_session, user_sub="admin-sub", visible=True)

    await sqlite_session.refresh(row)
    _assert_last_seen_equals(row, t_base)
