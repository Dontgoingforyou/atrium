"""Эфемерные WS-события чата: typing, voice_recording, emoji_pong (без записи в БД)."""

from __future__ import annotations

import json
import logging
import time
from typing import Any

from app.schemas.auth import UserPublic

logger = logging.getLogger(__name__)

_MIN_INTERVAL_SEC = 2.0
_GAME_CONTROL_INTERVAL_SEC = 0.25
_GAME_FAST_INTERVAL_SEC = 0.02
_STALE_ENTRY_SEC = 300.0
_last_sent: dict[str, tuple[float, bool]] = {}

_TYPING_EVENTS = frozenset({"typing", "voice_recording"})
_GAME_CONTROL_EVENTS = frozenset(
    {
        "emoji_pong_invite",
        "emoji_pong_accept",
        "emoji_pong_decline",
        "emoji_pong_end",
    }
)
_GAME_FAST_EVENTS = frozenset({"emoji_pong_paddle", "emoji_pong_state"})
_ALLOWED_EVENTS = _TYPING_EVENTS | _GAME_CONTROL_EVENTS | _GAME_FAST_EVENTS

_STATE_FLOAT_KEYS = (
    "ball_x",
    "ball_y",
    "vx",
    "vy",
    "host_paddle_x",
    "guest_paddle_x",
)
_STATE_INT_KEYS = ("host_score", "guest_score")


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def _parse_session_id(data: dict[str, Any]) -> str | None:
    session_id = data.get("session_id")
    if not isinstance(session_id, str):
        return None
    sid = session_id.strip()
    if not (8 <= len(sid) <= 64):
        return None
    return sid


def _parse_emoji_pong_event(data: dict[str, Any]) -> dict[str, Any] | None:
    event = data.get("event")
    if event not in _GAME_CONTROL_EVENTS and event not in _GAME_FAST_EVENTS:
        return None
    session_id = _parse_session_id(data)
    if session_id is None:
        return None
    out: dict[str, Any] = {
        "event": event,
        "session_id": session_id,
        "active": True,
    }
    if event == "emoji_pong_invite":
        emoji = data.get("emoji")
        if not isinstance(emoji, str) or not emoji or len(emoji) > 32:
            return None
        out["emoji"] = emoji
        return out
    if event in {"emoji_pong_accept", "emoji_pong_decline"}:
        return out
    if event == "emoji_pong_paddle":
        px = data.get("paddle_x")
        if not isinstance(px, (int, float)):
            return None
        out["paddle_x"] = _clamp01(float(px))
        return out
    if event == "emoji_pong_state":
        for key in _STATE_FLOAT_KEYS:
            raw = data.get(key)
            if not isinstance(raw, (int, float)):
                return None
            out[key] = float(raw)
        for key in _STATE_INT_KEYS:
            raw = data.get(key)
            if not isinstance(raw, (int, float)):
                return None
            out[key] = max(0, min(999, int(raw)))
        out["finished"] = bool(data.get("finished", False))
        out["host_paddle_x"] = _clamp01(out["host_paddle_x"])
        out["guest_paddle_x"] = _clamp01(out["guest_paddle_x"])
        out["ball_x"] = _clamp01(out["ball_x"])
        out["ball_y"] = max(0.0, min(1.2, out["ball_y"]))
        return out
    if event == "emoji_pong_end":
        for key in _STATE_INT_KEYS:
            raw = data.get(key)
            if not isinstance(raw, (int, float)):
                return None
            out[key] = max(0, min(999, int(raw)))
        return out
    return None


def parse_client_ephemeral_event(raw: str) -> dict[str, Any] | None:
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict):
        return None
    event = data.get("event")
    if event not in _ALLOWED_EVENTS:
        return None
    if event in _TYPING_EVENTS:
        return {
            "event": event,
            "active": bool(data.get("active", True)),
        }
    return _parse_emoji_pong_event(data)


def _prune_stale_rate_limit_entries(now: float) -> None:
    """Удалить записи rate limit старше _STALE_ENTRY_SEC (защита от роста памяти)."""
    stale = [k for k, (t, _) in _last_sent.items() if now - t > _STALE_ENTRY_SEC]
    for k in stale:
        del _last_sent[k]


def should_rate_limit(chat_id: str, user_sub: str, event: str, *, active: bool) -> bool:
    """True — пропустить публикацию (слишком часто).

    typing/voice: active=False всегда проходит; active=True — не чаще раза в _MIN_INTERVAL_SEC.
    emoji_pong_*: отдельные интервалы (control / fast sync).
    """
    key = f"{chat_id}:{user_sub}:{event}"
    now = time.monotonic()
    _prune_stale_rate_limit_entries(now)

    if event in _GAME_FAST_EVENTS:
        last_time, _ = _last_sent.get(key, (0.0, False))
        if now - last_time < _GAME_FAST_INTERVAL_SEC:
            return True
        _last_sent[key] = (now, True)
        return False

    if event in _GAME_CONTROL_EVENTS:
        last_time, _ = _last_sent.get(key, (0.0, False))
        if now - last_time < _GAME_CONTROL_INTERVAL_SEC:
            return True
        _last_sent[key] = (now, True)
        return False

    last_time, last_active = _last_sent.get(key, (0.0, False))
    if not active:
        _last_sent[key] = (now, False)
        return False
    if not last_active:
        _last_sent[key] = (now, True)
        return False
    if now - last_time < _MIN_INTERVAL_SEC:
        return True
    _last_sent[key] = (now, True)
    return False


def build_ephemeral_broadcast(event: dict[str, Any], user: UserPublic) -> dict[str, Any]:
    display = (user.full_name or user.username or user.email or user.sub).strip()
    payload: dict[str, Any] = {
        "event": event["event"],
        "user_sub": user.sub,
        "display_name": display[:120],
        "active": bool(event.get("active", True)),
    }
    for key in (
        "session_id",
        "emoji",
        "paddle_x",
        "ball_x",
        "ball_y",
        "vx",
        "vy",
        "host_paddle_x",
        "guest_paddle_x",
        "host_score",
        "guest_score",
        "finished",
    ):
        if key in event:
            payload[key] = event[key]
    return payload
