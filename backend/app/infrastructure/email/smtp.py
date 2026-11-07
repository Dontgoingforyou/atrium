"""SMTP-отправка писем."""

from __future__ import annotations

import logging
from email.message import EmailMessage

import aiosmtplib

from app.core.config import get_settings

logger = logging.getLogger(__name__)


async def send_email(
    *,
    to: str,
    subject: str,
    text_body: str,
    html_body: str | None = None,
) -> bool:
    """Отправить письмо. При smtp_enabled=false — только лог, без ошибки."""
    settings = get_settings()
    if not settings.smtp_enabled:
        logger.info("SMTP отключён, письмо не отправлено: to=%s subject=%s", to, subject)
        return False

    msg = EmailMessage()
    msg["From"] = settings.smtp_from
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(text_body)
    if html_body:
        msg.add_alternative(html_body, subtype="html")

    try:
        await aiosmtplib.send(
            msg,
            hostname=settings.smtp_host,
            port=settings.smtp_port,
            username=settings.smtp_user or None,
            password=settings.smtp_password or None,
            start_tls=settings.smtp_start_tls,
            use_tls=settings.smtp_use_tls,
            timeout=settings.smtp_timeout_seconds,
        )
    except Exception:
        logger.exception("Ошибка SMTP при отправке на %s", to)
        return False
    return True
