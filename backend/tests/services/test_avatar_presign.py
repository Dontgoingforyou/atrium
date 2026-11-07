"""Контракт presign_avatar_url: TTL avatar ≠ attachment, sync/async симметрия."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.core.config import Settings
from app.services import avatar_presign as avp


def _settings(*, avatar_ttl: int = 604_800, attachment_ttl: int = 3600) -> Settings:
    return Settings(
        database_url="sqlite:///:memory:",
        avatar_presign_ttl_seconds=avatar_ttl,
        attachment_presign_ttl_seconds=attachment_ttl,
    )


@pytest.mark.parametrize(
    ("storage_key", "expect_call"),
    [
        (None, False),
        ("", False),
        ("avatars/u/1.jpg", True),
    ],
)
def test_presign_avatar_url_falsy_key(storage_key: str | None, expect_call: bool) -> None:
    with patch("app.services.avatar_presign.get_presigned_url", MagicMock(return_value="https://u")) as m:
        result = avp.presign_avatar_url(storage_key)
    if expect_call:
        assert result == "https://u"
        m.assert_called_once()
    else:
        assert result is None
        m.assert_not_called()


def test_presign_avatar_url_uses_avatar_ttl_not_attachment() -> None:
    settings = _settings(avatar_ttl=604_800, attachment_ttl=3600)
    with (
        patch("app.services.avatar_presign.get_settings", return_value=settings),
        patch("app.services.avatar_presign.get_presigned_url", MagicMock(return_value="https://u")) as m,
    ):
        url = avp.presign_avatar_url("avatars/u/1.jpg")
    assert url == "https://u"
    m.assert_called_once_with("avatars/u/1.jpg", ttl_seconds=604_800)
    assert m.call_args.kwargs["ttl_seconds"] != settings.attachment_presign_ttl_seconds


def test_presign_avatar_url_explicit_ttl_override() -> None:
    with patch("app.services.avatar_presign.get_presigned_url", MagicMock(return_value="https://u")) as m:
        avp.presign_avatar_url("avatars/u/1.jpg", ttl_seconds=99)
    m.assert_called_once_with("avatars/u/1.jpg", ttl_seconds=99)


@pytest.mark.asyncio
async def test_async_presign_avatar_url_uses_avatar_ttl() -> None:
    settings = _settings(avatar_ttl=120, attachment_ttl=3600)
    mock_async = AsyncMock(return_value="https://async")
    with (
        patch("app.services.avatar_presign.get_settings", return_value=settings),
        patch("app.services.avatar_presign.async_get_presigned_url", mock_async),
    ):
        url = await avp.async_presign_avatar_url("avatars/u/2.jpg")
    assert url == "https://async"
    mock_async.assert_awaited_once_with("avatars/u/2.jpg", ttl_seconds=120)
