"""Тесты эфемерных WS-событий чата."""

from __future__ import annotations

import time

from app.portal_chat.services import ephemeral_events as ep


def test_should_rate_limit_allows_stop_immediately() -> None:
    ep._last_sent.clear()
    assert ep.should_rate_limit("c1", "u1", "typing", active=False) is False


def test_should_rate_limit_allows_keepalive_after_interval() -> None:
    ep._last_sent.clear()
    assert ep.should_rate_limit("c1", "u1", "typing", active=True) is False
    assert ep.should_rate_limit("c1", "u1", "typing", active=True) is True
    ep._last_sent["c1:u1:typing"] = (time.monotonic() - 3.0, True)
    assert ep.should_rate_limit("c1", "u1", "typing", active=True) is False


def test_parse_client_ephemeral_event_valid() -> None:
    raw = '{"event": "typing", "active": true}'
    parsed = ep.parse_client_ephemeral_event(raw)
    assert parsed == {"event": "typing", "active": True}


def test_parse_client_ephemeral_event_rejects_unknown() -> None:
    assert ep.parse_client_ephemeral_event('{"event": "hack"}') is None
    assert ep.parse_client_ephemeral_event("not-json") is None
    assert ep.parse_client_ephemeral_event('{"type":"pong"}') is None


def test_build_ephemeral_broadcast_truncates_display_name() -> None:
    from app.schemas.auth import UserPublic

    user = UserPublic(
        sub="u1",
        email="e@example.com",
        username="u",
        full_name="x" * 200,
        idp_groups=[],
        is_portal_admin=False,
    )
    out = ep.build_ephemeral_broadcast({"event": "typing", "active": True}, user)
    assert len(out["display_name"]) <= 120


def test_parse_emoji_pong_invite_and_paddle() -> None:
    invite = ep.parse_client_ephemeral_event('{"event":"emoji_pong_invite","session_id":"abcd1234","emoji":"😍"}')
    assert invite is not None
    assert invite["event"] == "emoji_pong_invite"
    assert invite["emoji"] == "😍"

    paddle = ep.parse_client_ephemeral_event('{"event":"emoji_pong_paddle","session_id":"abcd1234","paddle_x":0.42}')
    assert paddle is not None
    assert paddle["paddle_x"] == 0.42


def test_parse_emoji_pong_rejects_bad_session() -> None:
    assert ep.parse_client_ephemeral_event('{"event":"emoji_pong_invite","session_id":"x","emoji":"😍"}') is None


def test_game_fast_rate_limit_allows_high_frequency() -> None:
    ep._last_sent.clear()
    assert ep.should_rate_limit("c1", "u1", "emoji_pong_paddle", active=True) is False
    assert ep.should_rate_limit("c1", "u1", "emoji_pong_paddle", active=True) is True
    ep._last_sent["c1:u1:emoji_pong_paddle"] = (time.monotonic() - 0.025, True)
    assert ep.should_rate_limit("c1", "u1", "emoji_pong_paddle", active=True) is False


def test_prune_stale_rate_limit_entries() -> None:
    ep._last_sent.clear()
    ep._last_sent["old:key:typing"] = (time.monotonic() - 400.0, True)
    ep._last_sent["fresh:key:typing"] = (time.monotonic(), True)
    ep.should_rate_limit("c1", "u1", "typing", active=False)
    assert "old:key:typing" not in ep._last_sent
    assert "fresh:key:typing" in ep._last_sent
