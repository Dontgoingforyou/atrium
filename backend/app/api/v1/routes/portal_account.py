from __future__ import annotations

from fastapi import APIRouter

from app.api.deps import DbSession
from app.api.deps_auth import CurrentUser
from app.schemas.portal_account import PortalAccountPreferencesRead, PortalAccountPreferencesUpdate
from app.services import portal_account as svc

router = APIRouter(prefix="/portal/account", tags=["Аккаунт"])


@router.get(
    "/preferences",
    summary="Настройки уведомлений аккаунта",
    response_model=PortalAccountPreferencesRead,
)
async def get_account_preferences(
    user: CurrentUser,
    db: DbSession,
) -> PortalAccountPreferencesRead:
    profile = await svc.get_profile(db, user.sub)
    return PortalAccountPreferencesRead.model_validate(profile)


@router.patch(
    "/preferences",
    summary="Обновить настройки уведомлений аккаунта",
    response_model=PortalAccountPreferencesRead,
)
async def patch_account_preferences(
    data: PortalAccountPreferencesUpdate,
    user: CurrentUser,
    db: DbSession,
) -> PortalAccountPreferencesRead:
    profile = await svc.update_account_preferences(db, user, data)
    return PortalAccountPreferencesRead.model_validate(profile)
