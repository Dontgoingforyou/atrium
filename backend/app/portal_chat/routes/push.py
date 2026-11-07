from __future__ import annotations

from fastapi import APIRouter, Response, status

from app.api.deps import DbSession
from app.api.deps_auth import CurrentUser
from app.core.config import get_settings
from app.core.exceptions import NotFoundError
from app.portal_chat.schemas.push import PortalPushSubscribe, PortalPushUnsubscribe, PortalPushVapidPublicRead
from app.portal_chat.services import web_push as push_svc

router = APIRouter(prefix="/portal", tags=["Чаты"])


@router.get(
    "/push/vapid-public-key",
    summary="Публичный ключ VAPID для Web Push",
    response_model=PortalPushVapidPublicRead,
)
async def get_vapid_public_key(_user: CurrentUser) -> PortalPushVapidPublicRead:
    """Ключ не секретный, но эндпоинт закрыт ``CurrentUser`` (как и остальные chat-маршруты)."""
    pk = get_settings().vapid_public_key.strip()
    if not pk:
        raise NotFoundError("Web Push не настроен на сервере")
    return PortalPushVapidPublicRead(public_key=pk)


@router.post(
    "/push/subscribe",
    summary="Сохранить подписку Web Push текущего пользователя",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
async def subscribe_push(user: CurrentUser, db: DbSession, body: PortalPushSubscribe) -> None:
    await push_svc.upsert_push_subscription(db, user, body.model_dump(mode="json"))


@router.post(
    "/push/unsubscribe",
    summary="Удалить подписку Web Push",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
async def unsubscribe_push(user: CurrentUser, db: DbSession, body: PortalPushUnsubscribe) -> None:
    await push_svc.delete_push_subscription(db, user, body.endpoint)
