"""Web Push: подписки и фоновая отправка при новом сообщении в чате."""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from functools import partial
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import ValidationError
from app.infrastructure.db.models.portal_web_push import PortalWebPushSubscription
from app.infrastructure.db.session import skip_background_tasks_using_global_engine
from app.portal_chat.services._queries import get_unread_counts_for_chat_members, list_chat_members
from app.schemas.auth import UserPublic

# Для групповых чатов: не отправлять Web Push, если у получателя уже ≥ N непрочитанных
_GROUP_PUSH_SUPPRESS_UNREAD_THRESHOLD = 3

logger = logging.getLogger(__name__)


def _normalize_vapid_private_key(raw: str) -> str:
    """В .env одной строкой часто задают PEM с литеральными ``\\n`` — приводим к настоящим переносам."""
    s = raw.strip()
    if not s:
        return s
    if "\\n" in s:
        s = s.replace("\\n", "\n")
    return s.strip()


def _vapid_from_private_key_string(priv: str) -> Any:
    """Экземпляр VAPID для pywebpush.

    ``webpush(..., vapid_private_key=str)`` внутри вызывает ``Vapid.from_string`` — тот **не** разбирает
    PEM PKCS8 (только сырой base64url/DER), из-за чего валидный многострочный PEM из .env ломается.
    Для ``-----BEGIN ...-----`` используем ``Vapid.from_pem``.
    """
    from py_vapid import Vapid  # type: ignore[import-untyped, unused-ignore]

    if "-----BEGIN" in priv:
        return Vapid.from_pem(priv.encode("utf-8"))
    return Vapid.from_string(priv)


async def upsert_push_subscription(
    session: AsyncSession,
    user: UserPublic,
    data: dict[str, Any],
) -> None:
    endpoint = str(data["endpoint"])
    keys = data.get("keys") or {}
    p256dh = str(keys.get("p256dh") or "")
    auth = str(keys.get("auth") or "")
    if not p256dh or not auth:
        raise ValidationError("Некорректные ключи подписки push")

    stmt = select(PortalWebPushSubscription).where(PortalWebPushSubscription.endpoint == endpoint)
    row = (await session.execute(stmt)).scalar_one_or_none()
    if row is None:
        session.add(
            PortalWebPushSubscription(
                user_sub=user.sub,
                endpoint=endpoint,
                p256dh=p256dh,
                auth=auth,
            )
        )
    else:
        row.user_sub = user.sub
        row.p256dh = p256dh
        row.auth = auth
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raced = (await session.execute(stmt)).scalar_one_or_none()
        if raced is None:
            raise
        raced.user_sub = user.sub
        raced.p256dh = p256dh
        raced.auth = auth
        await session.commit()


async def delete_push_subscription(session: AsyncSession, user: UserPublic, endpoint: str) -> None:
    await session.execute(
        delete(PortalWebPushSubscription).where(
            PortalWebPushSubscription.user_sub == user.sub,
            PortalWebPushSubscription.endpoint == endpoint,
        )
    )
    await session.commit()


async def send_chat_message_web_push_bg(
    chat_id: uuid.UUID,
    author_sub: str,
    preview_text: str,
    chat_title: str | None,
    is_direct: bool,
    message_id: uuid.UUID | None = None,
    mention_subs: list[str] | None = None,
) -> None:
    """BackgroundTasks: отдельная сессия БД; не падает при отсутствии VAPID."""
    settings = get_settings()
    priv = _normalize_vapid_private_key(settings.vapid_private_key)
    pub = settings.vapid_public_key.strip()
    mailto_raw = settings.vapid_contact_email.strip()
    if not priv or not pub or not mailto_raw:
        return
    if "BEGIN" in priv and "END PRIVATE" not in priv:
        logger.error(
            "VAPID_PRIVATE_KEY неполный: в окружении попала только первая строка PEM. "
            "Docker Compose нередко обрезает многострочные значения в env_file. "
            "Задайте ключ одной строкой в кавычках с \\n между строками PEM "
            "(см. вывод backend/scripts/generate_vapid_keys.py, блок «Docker»)."
        )
        return
    mailto = mailto_raw if mailto_raw.startswith("mailto:") else f"mailto:{mailto_raw}"

    title = (
        chat_title.strip()
        if chat_title and chat_title.strip()
        else ("Личные сообщения" if is_direct else "Групповой чат")
    )
    body = preview_text.strip() if preview_text.strip() else "Новое сообщение"
    base = settings.portal_public_url.rstrip("/")
    url = f"{base}/chats?chat={chat_id}"
    if message_id is not None:
        url = f"{url}&message={message_id}"
    payload = json.dumps({"title": title, "body": body, "url": url, "tag": str(chat_id)}, ensure_ascii=False)
    vapid_claims = {"sub": mailto}

    try:
        from pywebpush import WebPushException, webpush  # type: ignore[import-untyped, unused-ignore]
    except ImportError:
        logger.warning("pywebpush не установлен — Web Push пропущен")
        return

    try:
        vapid = _vapid_from_private_key_string(priv)
    except Exception:
        logger.exception("VAPID: не удалось разобрать приватный ключ")
        return

    if skip_background_tasks_using_global_engine():
        return

    from app.infrastructure.db.session import async_session_factory

    async with async_session_factory() as session:
        members = await list_chat_members(session, chat_id)
        recipient_subs = [m.user_sub for m in members if m.user_sub != author_sub]
        if not recipient_subs:
            return

        all_subs_result = await session.execute(
            select(PortalWebPushSubscription).where(PortalWebPushSubscription.user_sub.in_(recipient_subs))
        )
        subs_by_user: dict[str, list[PortalWebPushSubscription]] = {}
        for sub in all_subs_result.scalars().all():
            subs_by_user.setdefault(sub.user_sub, []).append(sub)

        # Для групповых чатов — один запрос на всех получателей сразу.
        # Личные чаты — без ограничений; группы — подавляем если непрочитанных уже ≥ порога,
        # но @упомянутые получатели всегда получают push вне зависимости от порога.
        mention_subs_set: frozenset[str] = frozenset(mention_subs or [])
        unread_by_user: dict[str, int] = {}
        if not is_direct:
            unread_by_user = await get_unread_counts_for_chat_members(session, chat_id, recipient_subs)

        for user_sub in recipient_subs:
            is_mentioned = user_sub in mention_subs_set
            if not is_direct and not is_mentioned:
                unread_n = unread_by_user.get(user_sub, 0)
                if unread_n >= _GROUP_PUSH_SUPPRESS_UNREAD_THRESHOLD:
                    logger.debug(
                        "Web Push: пропуск для группового чата user_sub=%s chat_id=%s unread=%d",
                        user_sub,
                        chat_id,
                        unread_n,
                    )
                    continue
            subs = subs_by_user.get(user_sub, [])
            for sub in subs:
                info = {"endpoint": sub.endpoint, "keys": {"p256dh": sub.p256dh, "auth": sub.auth}}
                try:
                    await asyncio.to_thread(
                        partial(
                            webpush,
                            info,
                            data=payload,
                            vapid_private_key=vapid,
                            vapid_claims=vapid_claims,
                        ),
                    )
                except WebPushException as e:
                    status = getattr(e.response, "status_code", None) if e.response is not None else None
                    if status in (410, 403):
                        # 410 Gone — подписка удалена на стороне push-сервиса.
                        # 403 Forbidden — подписка создана с другим VAPID-ключом (устаревшая);
                        # обе ситуации требуют удаления записи, чтобы не спамить невалидными запросами.
                        logger.info(
                            "Web Push: удаляем устаревшую подписку user_sub=%s status=%s",
                            user_sub,
                            status,
                        )
                        await session.delete(sub)
                        await session.commit()
                    else:
                        logger.warning(
                            "Web Push не доставлен: user_sub=%s status=%s",
                            user_sub,
                            status,
                        )
                except Exception:
                    logger.exception("Web Push: неожиданная ошибка для user_sub=%s", user_sub)
