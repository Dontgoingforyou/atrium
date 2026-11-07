from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter, File, Header, Query, Response, UploadFile
from fastapi.responses import Response as StarletteResponse

from app.api.deps import DbSession, HttpClient
from app.api.deps_auth import CurrentUser, extract_bearer_token, is_plausible_jwt, verify_access_token
from app.core.exceptions import UnauthorizedError
from app.core.utils import decode_jwt_payload_unverified
from app.schemas.pagination import PagedResponse
from app.schemas.portal_user import (
    AvatarUploadRead,
    PortalPresenceUpdate,
    PortalUserPresenceRead,
    PortalUserRead,
    PresenceBeaconBody,
)
from app.services import portal_user as svc
from app.services import portal_user_avatar as avatar_svc
from app.services.portal_last_seen import finalize_last_seen_in_db, touch_last_seen_in_db
from app.services.portal_presence import bulk_last_seen_iso, record_presence, set_last_seen_iso_now
from app.services.portal_presence import presence_for_subs as bulk_presence
from app.services.portal_user_photo_proxy import fetch_user_photo_for_proxy

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/portal", tags=["Пользователи"])

# Beacon-эндпоинты: JWT передаётся в теле, поэтому подключаются БЕЗ глобального
# require_non_developer (который требует Authorization-заголовок).
beacon_router = APIRouter(prefix="/portal", tags=["Пользователи"])


@router.get(
    "/users",
    summary="Список пользователей портала",
    response_model=PagedResponse[PortalUserRead],
    description=(
        "Пользователи с профилем и portal_chat_allowed=True (пикер чатов и фильтров задач). "
        "Студенты без чатов (portal_chat_allowed=False) не входят в список. "
        "Тестовые учётки, явный список AUTASKS-413, чужой отдел (gid не АУ) "
        "и почты, которых нет среди активных в Effective Admin, скрыты. "
        "Поле presence — из Redis при доступном REDIS_URL."
    ),
)
async def list_portal_users(
    _user: CurrentUser,
    db: DbSession,
    http_client: HttpClient,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=200, ge=1, le=500),
) -> PagedResponse[PortalUserRead]:
    users, total = await svc.list_portal_users(db, skip=skip, limit=limit, http=http_client)
    subs = [u.sub for u in users]
    pr = await bulk_presence(subs)
    enriched = [u.model_copy(update={"presence": pr.get(u.sub, "offline")}) for u in users]
    return PagedResponse(items=enriched, total=total, skip=skip, limit=limit)


@router.get(
    "/users/specialists",
    summary="Специалисты: список студентов портала",
    description=(
        "Пользователи с профилем ``portal_chat_allowed=false`` (роль students без чатов). "
        "Доступ: менеджер АУ (основной отдел, gid_number=10000) или администратор портала."
    ),
    response_model=PagedResponse[PortalUserRead],
)
async def list_portal_students_for_specialists(
    user: CurrentUser,
    db: DbSession,
    limit: int = Query(default=100, ge=1, le=200),
    skip: int = Query(default=0, ge=0),
) -> PagedResponse[PortalUserRead]:
    items, total = await svc.list_portal_students_for_specialists(db, user, skip=skip, limit=limit)
    subs = [u.sub for u in items]
    pr = await bulk_presence(subs)
    enriched = [u.model_copy(update={"presence": pr.get(u.sub, "offline")}) for u in items]
    return PagedResponse(items=enriched, total=total, skip=skip, limit=limit)


@router.get(
    "/users/presence",
    summary="Присутствие пользователей портала (без аватаров)",
    response_model=PagedResponse[PortalUserPresenceRead],
    description=(
        "Лёгкий снимок статусов из Redis для того же набора пользователей, что и GET /portal/users "
        "(те же skip/limit, порядок и скрытие уволенных/тестовых). Без URL аватаров — чтобы обновлять "
        "только presence в кэше клиента."
    ),
)
async def list_portal_users_presence(
    _user: CurrentUser,
    db: DbSession,
    http_client: HttpClient,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=200, ge=1, le=500),
) -> PagedResponse[PortalUserPresenceRead]:
    subs, total = await svc.list_portal_user_subs_ordered(db, skip=skip, limit=limit, http=http_client)
    pr, lsi_redis, lsi_db = await asyncio.gather(
        bulk_presence(subs),
        bulk_last_seen_iso(subs),
        svc.bulk_last_seen_from_profile(db, subs),
    )
    out: list[PortalUserPresenceRead] = []
    for s in subs:
        last_seen = lsi_redis.get(s)
        if last_seen is None:
            last_seen = lsi_db.get(s)
        out.append(
            PortalUserPresenceRead(sub=s, presence=pr.get(s, "offline"), last_seen_at=last_seen),
        )
    return PagedResponse(items=out, total=total, skip=skip, limit=limit)


@router.post(
    "/users/me/presence",
    summary="Обновить своё присутствие (heartbeat)",
    status_code=204,
    response_class=Response,
)
async def post_my_presence(
    user: CurrentUser,
    db: DbSession,
    body: PortalPresenceUpdate,
) -> Response:
    await record_presence(user_sub=user.sub, visible=body.visible, active=body.active)
    if body.visible:
        await touch_last_seen_in_db(db, user_sub=user.sub, visible=True)
    return Response(status_code=204)


@beacon_router.post(
    "/users/me/presence-beacon",
    summary="Обновить присутствие через sendBeacon (закрытие вкладки)",
    status_code=204,
    response_class=Response,
)
async def presence_beacon(
    body: PresenceBeaconBody,
    db: DbSession,
    http_client: HttpClient,
) -> Response:
    """Beacon-endpoint для события pagehide: JWT передаётся в теле запроса,
    так как sendBeacon не поддерживает заголовок Authorization.

    Безопасность: не логирует токен; на любую ошибку возвращает 204 (как logout-beacon),
    чтобы браузер не считал beacon неуспешным и не повторял запрос.
    """
    token = (body.access_token or "").strip()
    if not token or not is_plausible_jwt(token):
        return Response(status_code=204)
    try:
        user = await verify_access_token(token, db, http_client)
    except Exception as exc:
        logger.warning("presence-beacon: ошибка верификации токена: %s", exc)
        return Response(status_code=204)
    await record_presence(user_sub=user.sub, visible=body.visible, active=body.active)
    if not body.visible:
        await set_last_seen_iso_now(user_sub=user.sub)
        await finalize_last_seen_in_db(db, user_sub=user.sub)
    return Response(status_code=204)


@router.get(
    "/users/{user_sub}/photo",
    summary="Прокси фото пользователя из Effective Admin",
    description=(
        "Signed query (exp+sig). Service token на бэкенде для чужих фото; "
        "свой аватар — опционально с Authorization Bearer (без service token)."
    ),
    response_class=StarletteResponse,
)
async def get_user_photo_proxy(
    user_sub: str,
    db: DbSession,
    http_client: HttpClient,
    exp: int = Query(...),
    sig: str = Query(...),
    authorization: str | None = Header(default=None),
) -> StarletteResponse:
    viewer_bearer = extract_bearer_token(authorization)
    viewer_sub = _jwt_sub_unverified(viewer_bearer) if viewer_bearer else None
    photo = await fetch_user_photo_for_proxy(
        db,
        http_client,
        user_sub=user_sub,
        exp=exp,
        sig=sig,
        viewer_bearer=viewer_bearer,
        viewer_sub=viewer_sub,
    )
    return StarletteResponse(
        content=photo.content,
        media_type=photo.content_type,
        headers={"Cache-Control": "private, max-age=3600"},
    )


def _jwt_sub_unverified(token: str) -> str | None:
    """sub из JWT без проверки подписи — только для выбора /me vs service token."""
    payload = decode_jwt_payload_unverified(token)
    if not payload:
        return None
    sub = payload.get("sub")
    return str(sub) if sub else None


@router.post(
    "/users/me/avatar",
    summary="Загрузить аватар текущего пользователя",
    description=(
        f"Изображение до {avatar_svc.AVATAR_MAX_BYTES // (1024 * 1024)} МБ: JPEG, PNG, WebP или GIF. "
        "Пишется в Effective Admin (/me/photo)."
    ),
)
async def post_my_avatar(
    user: CurrentUser,
    db: DbSession,
    http_client: HttpClient,
    file: UploadFile = File(...),
    authorization: str | None = Header(default=None),
) -> AvatarUploadRead:
    token = extract_bearer_token(authorization)
    if not token:
        raise UnauthorizedError("Требуется Authorization: Bearer")
    return await avatar_svc.save_user_avatar(
        db,
        user_sub=user.sub,
        bearer_token=token,
        file=file,
        http=http_client,
    )


@router.delete(
    "/users/me/avatar",
    summary="Удалить аватар текущего пользователя",
    status_code=204,
    response_class=Response,
)
async def delete_my_avatar(
    user: CurrentUser,
    db: DbSession,
    http_client: HttpClient,
    authorization: str | None = Header(default=None),
) -> Response:
    token = extract_bearer_token(authorization)
    if not token:
        raise UnauthorizedError("Требуется Authorization: Bearer")
    await avatar_svc.clear_user_avatar(db, user_sub=user.sub, bearer_token=token, http=http_client)
    return Response(status_code=204)
