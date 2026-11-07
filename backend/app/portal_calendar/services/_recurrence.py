"""Развёртка RRULE в окне дат."""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import cast

from dateutil.rrule import SECONDLY, rrulestr  # type: ignore[import-untyped, unused-ignore]

from app.core.exceptions import BadRequestError
from app.infrastructure.db.models.portal_calendar import PortalCalendarEvent, PortalCalendarEventOverride

_MAX_OCCURRENCE_HITS = 2000


@dataclass(frozen=True, slots=True)
class Occurrence:
    event: PortalCalendarEvent
    original_start: datetime
    starts_at: datetime
    ends_at: datetime | None
    title: str
    description: str | None
    location: str | None
    is_cancelled: bool


def ensure_aware_utc(dt: datetime) -> datetime:
    """SQLite часто возвращает naive datetime из DateTime(timezone=True)."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def _rrule_freqs(rule: object) -> list[int]:
    freqs: list[int] = []
    freq = getattr(rule, "_freq", None)
    if isinstance(freq, int):
        freqs.append(freq)
    nested = getattr(rule, "_rrule", None)
    if nested:
        for inner in nested:
            inner_freq = getattr(inner, "_freq", None)
            if isinstance(inner_freq, int):
                freqs.append(inner_freq)
    return freqs


def _rrule_hits_until(
    rule: object,
    scan_start: datetime,
    window_end: datetime,
    max_hits: int,
) -> list[datetime]:
    """Вхождения с scan_start до window_end, не больше max_hits (без полной развёртки)."""
    hits: list[datetime] = []
    xafter = getattr(rule, "xafter", None)
    if callable(xafter):
        iterator: Iterator[datetime] = cast(Iterator[datetime], xafter(scan_start, inc=True))
    else:
        iterator = iter(cast(Iterable[datetime], rule))
    for hit in iterator:
        hit_aware = ensure_aware_utc(hit)
        if not callable(xafter) and hit_aware < scan_start:
            continue
        if hit_aware >= window_end:
            break
        hits.append(hit)
        if len(hits) >= max_hits:
            break
    return hits


def validate_rrule(rrule: str, dtstart: datetime) -> str:
    """Разобрать RRULE: невалидная строка / SECONDLY → BadRequestError."""
    cleaned = rrule.strip()
    if not cleaned:
        raise BadRequestError("Некорректное правило повторения")
    try:
        rule = rrulestr(cleaned, dtstart=ensure_aware_utc(dtstart))
    except (ValueError, TypeError, KeyError) as exc:
        raise BadRequestError("Некорректное правило повторения") from exc
    if SECONDLY in _rrule_freqs(rule):
        raise BadRequestError("Повтор с частотой SECONDLY не поддерживается")
    return cleaned


def expand_event_occurrences(
    event: PortalCalendarEvent,
    window_start: datetime,
    window_end: datetime,
    *,
    max_hits: int = _MAX_OCCURRENCE_HITS,
) -> list[Occurrence]:
    """Развернуть мастер-событие (с/без RRULE) в окно [window_start, window_end)."""
    window_start = ensure_aware_utc(window_start)
    window_end = ensure_aware_utc(window_end)
    starts = ensure_aware_utc(event.starts_at)
    ends_raw = event.ends_at
    if ends_raw is not None:
        ends = ensure_aware_utc(ends_raw)
        has_end = True
    else:
        ends = starts
        has_end = False
    duration = ends - starts if has_end else timedelta(0)
    if duration < timedelta(0):
        duration = timedelta(0)

    overrides_by_start = {ensure_aware_utc(o.original_start): o for o in (event.overrides or [])}

    if not event.rrule:
        eff_end = ends if has_end else starts
        if eff_end <= window_start or starts >= window_end:
            return []
        ov = overrides_by_start.get(starts)
        return [_apply_override(event, starts, duration, has_end, ov)]

    rule = rrulestr(event.rrule, dtstart=starts)
    if SECONDLY in _rrule_freqs(rule):
        raise BadRequestError("Повтор с частотой SECONDLY не поддерживается")
    # Итерация с cap: rule.between() сначала разворачивает всё окно (DoS на MINUTELY).
    hits = _rrule_hits_until(rule, window_start - duration, window_end, max_hits)
    result: list[Occurrence] = []
    for hit in hits:
        hit_aware = ensure_aware_utc(hit)
        ov = overrides_by_start.get(hit_aware)
        occ = _apply_override(event, hit_aware, duration, has_end, ov)
        occ_end = occ.ends_at if occ.ends_at is not None else occ.starts_at
        if occ_end <= window_start or occ.starts_at >= window_end:
            if not occ.is_cancelled:
                continue
        result.append(occ)
    return result


def _apply_override(
    event: PortalCalendarEvent,
    original_start: datetime,
    duration: timedelta,
    master_has_end: bool,
    override: PortalCalendarEventOverride | None,
) -> Occurrence:
    if override is None:
        return Occurrence(
            event=event,
            original_start=original_start,
            starts_at=original_start,
            ends_at=(original_start + duration) if master_has_end else None,
            title=event.title,
            description=event.description,
            location=event.location,
            is_cancelled=False,
        )
    starts = ensure_aware_utc(override.starts_at) if override.starts_at else original_start
    if override.ends_at is not None:
        ends: datetime | None = ensure_aware_utc(override.ends_at)
    elif master_has_end:
        ends = starts + duration
    else:
        ends = None
    return Occurrence(
        event=event,
        original_start=original_start,
        starts_at=starts,
        ends_at=ends,
        title=override.title if override.title is not None else event.title,
        description=override.description if override.description is not None else event.description,
        location=override.location if override.location is not None else event.location,
        is_cancelled=override.is_cancelled,
    )
