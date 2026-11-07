from __future__ import annotations

from app.portal_chat.services.inbox_preview import build_inbox_preview_text


def test_preview_truncates_long_body() -> None:
    body = "x" * 200
    out = build_inbox_preview_text(body=body, attachment_content_types=[])
    assert out.endswith("…")
    assert len(out) == 160


def test_preview_voice_only_attachments() -> None:
    out = build_inbox_preview_text(body="  ", attachment_content_types=["audio/webm"])
    assert out == "Голосовое сообщение"


def test_preview_mixed_attachments() -> None:
    out = build_inbox_preview_text(body="", attachment_content_types=["audio/webm", "image/png"])
    assert out == "Вложения"
