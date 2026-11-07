"""Публичный контракт SMTP (`app.infrastructure.email.smtp.send_email`)."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from app.infrastructure.email.smtp import send_email


def _smtp_settings(*, enabled: bool) -> SimpleNamespace:
    return SimpleNamespace(
        smtp_enabled=enabled,
        smtp_from="noreply@example.com",
        smtp_host="smtp.example.com",
        smtp_port=587,
        smtp_user="user",
        smtp_password="pass",
        smtp_start_tls=True,
        smtp_use_tls=False,
        smtp_timeout_seconds=10,
    )


async def test_send_email_disabled_does_not_call_smtp() -> None:
    with (
        patch("app.infrastructure.email.smtp.get_settings", return_value=_smtp_settings(enabled=False)),
        patch("app.infrastructure.email.smtp.aiosmtplib.send", new=AsyncMock()) as send,
    ):
        assert (
            await send_email(
                to="a@example.com",
                subject="Тема",
                text_body="текст",
                html_body="<p>html</p>",
            )
            is False
        )
    send.assert_not_called()


async def test_send_email_success_adds_html_alternative() -> None:
    with (
        patch("app.infrastructure.email.smtp.get_settings", return_value=_smtp_settings(enabled=True)),
        patch("app.infrastructure.email.smtp.aiosmtplib.send", new=AsyncMock()) as send,
    ):
        assert (
            await send_email(
                to="a@example.com",
                subject="Тема",
                text_body="текст",
                html_body="<p>html</p>",
            )
            is True
        )

    send.assert_awaited_once()
    msg = send.await_args.args[0]
    kwargs = send.await_args.kwargs
    assert msg["From"] == "noreply@example.com"
    assert msg["To"] == "a@example.com"
    assert msg["Subject"] == "Тема"
    html_part = next(p for p in msg.walk() if p.get_content_type() == "text/html")
    assert "<p>html</p>" in html_part.get_content()
    assert kwargs["hostname"] == "smtp.example.com"
    assert kwargs["port"] == 587
    assert kwargs["username"] == "user"
    assert kwargs["password"] == "pass"
    assert kwargs["start_tls"] is True
    assert kwargs["use_tls"] is False
    assert kwargs["timeout"] == 10


async def test_send_email_smtp_error_returns_false() -> None:
    with (
        patch("app.infrastructure.email.smtp.get_settings", return_value=_smtp_settings(enabled=True)),
        patch(
            "app.infrastructure.email.smtp.aiosmtplib.send",
            new=AsyncMock(side_effect=OSError("smtp down")),
        ),
    ):
        assert (
            await send_email(
                to="a@example.com",
                subject="Тема",
                text_body="текст",
            )
            is False
        )
