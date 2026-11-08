from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_constants import IDP_GROUP_PORTAL_ADMIN, normalize_sso_gid_number
from app.core.permissions import is_timesheet_only
from app.core.utils import now_utc
from app.infrastructure.db.models.portal_specialist_profile import PortalSpecialistProfile
from app.infrastructure.db.models.portal_user_profile import PortalUserProfile
from app.portal_specialists.services.sso_profile_normalize import (
    normalize_telegram_from_sso,
    parse_birthday_from_sso,
)
from app.schemas.auth import UserPublic
from app.services.sso.groups import extract_groups_from_claim
from app.services.user_photo_url import build_user_photo_proxy_url

logger = logging.getLogger(__name__)

_sso_canonical_sub_by_alias: dict[str, str] = {}
_logged_sso_sub_remaps: set[str] = set()


def _remember_sso_sub_alias(*, jwt_sub: str, email: str, canonical_sub: str) -> None:
    if jwt_sub and jwt_sub != canonical_sub:
        _sso_canonical_sub_by_alias[jwt_sub] = canonical_sub
    email_key = email.strip().lower() if email else ""
    if email_key:
        _sso_canonical_sub_by_alias[email_key] = canonical_sub


def _full_name_from_payload(payload: dict[str, Any]) -> str:
    name = payload.get("name")
    if isinstance(name, str) and name.strip():
        return name.strip()
    gn = payload.get("given_name") or ""
    fn = payload.get("family_name") or ""
    if isinstance(gn, str) and isinstance(fn, str):
        return f"{gn} {fn}".strip()
    return ""


def _username_from_payload(payload: dict[str, Any], email: str) -> str:
    pu = payload.get("preferred_username")
    if isinstance(pu, str) and pu.strip():
        return pu.strip()
    if email and "@" in email:
        return email.split("@", 1)[0]
    return str(payload.get("sub", ""))


def _position_from_payload(payload: dict[str, Any]) -> str | None:
    raw = payload.get("position")
    if not isinstance(raw, str):
        return None
    t = raw.strip()
    return t or None


async def _upsert_specialist_profile_from_sso(
    session: AsyncSession,
    *,
    sub: str,
    raw_telegram: object,
    raw_birthday: object,
) -> None:
    """Синхронизация telegram/birthdate из SSO; пустые/невалидные значения не затирают БД."""
    telegram = normalize_telegram_from_sso(str(raw_telegram).strip() if raw_telegram else None)
    birthday = parse_birthday_from_sso(str(raw_birthday).strip() if raw_birthday else None)
    if telegram is None and birthday is None:
        return
    try:
        profile = await session.get(PortalSpecialistProfile, sub)
        if profile is None:
            profile = PortalSpecialistProfile(specialist_sub=sub)
            session.add(profile)
        if telegram is not None:
            profile.telegram = telegram
        if birthday is not None:
            profile.birthdate = birthday
        await session.commit()
    except Exception as exc:
        logger.warning("Не удалось синхронизировать профиль специалиста sub=%s: %s", sub, exc)
        await session.rollback()


async def _upsert_user_profile(
    session: AsyncSession,
    sub: str,
    email: str,
    full_name: str,
    username: str,
    is_portal_admin: bool,
    *,
    portal_chat_allowed: bool,
    is_developer: bool,
    gid_number: str | None,
) -> PortalUserProfile | None:
    """Сохранить/обновить поля профиля из SSO.

    Если профиль по ``sub`` не найден, но email совпадает с существующей записью —
    возвращаем её (без создания дубля). Это покрывает смену идентификатора sub при
    изменениях на стороне SSO.

    Поле аватара больше не хранится в профиле — фото в сервисе профилей.
    """
    try:
        now = now_utc()
        existing: PortalUserProfile | None = None

        alias = _sso_canonical_sub_by_alias.get(sub)
        if alias is None and email:
            alias = _sso_canonical_sub_by_alias.get(email.strip().lower())
        if alias:
            existing = await session.get(PortalUserProfile, alias)

        if existing is None:
            existing = await session.get(PortalUserProfile, sub)

        if existing is None and email:
            result = await session.execute(select(PortalUserProfile).where(PortalUserProfile.email == email).limit(1))
            existing = result.scalar_one_or_none()
            if existing is not None:
                if sub not in _logged_sso_sub_remaps:
                    _logged_sso_sub_remaps.add(sub)
                    logger.warning(
                        "SSO sub изменился: профиль по email, оставляем sub=%s вместо нового sub=%s",
                        existing.sub,
                        sub,
                    )

        if existing is not None:
            _remember_sso_sub_alias(jwt_sub=sub, email=email, canonical_sub=existing.sub)
            new_email = email or None
            new_full_name = full_name or None
            new_username = username or None
            unchanged = (
                existing.email == new_email
                and existing.full_name == new_full_name
                and existing.username == new_username
                and existing.is_portal_admin == is_portal_admin
                and existing.portal_chat_allowed == portal_chat_allowed
                and existing.is_developer == is_developer
                and existing.gid_number == gid_number
            )
            if unchanged:
                return existing
            existing.email = new_email
            existing.full_name = new_full_name
            existing.username = new_username
            existing.is_portal_admin = is_portal_admin
            existing.portal_chat_allowed = portal_chat_allowed
            existing.is_developer = is_developer
            existing.gid_number = gid_number
            existing.updated_at = now
            out = existing
        else:
            out = PortalUserProfile(
                sub=sub,
                email=email or None,
                full_name=full_name or None,
                username=username or None,
                is_portal_admin=is_portal_admin,
                portal_chat_allowed=portal_chat_allowed,
                is_developer=is_developer,
                gid_number=gid_number,
                updated_at=now,
            )
            session.add(out)
        await session.commit()
        await session.refresh(out)
        _remember_sso_sub_alias(jwt_sub=sub, email=email, canonical_sub=out.sub)
        return out
    except Exception as exc:
        logger.warning("Не удалось сохранить профиль пользователя sub=%s: %s", sub, exc)
        await session.rollback()
        return None


async def build_user_public(
    session: AsyncSession,
    payload: dict[str, Any],
    *,
    groups_claim_path: str,
) -> UserPublic:
    sub = str(payload["sub"])
    email = str(payload.get("email") or "")
    idp_groups = extract_groups_from_claim(payload, groups_claim_path)
    is_portal_admin = IDP_GROUP_PORTAL_ADMIN in idp_groups
    position = _position_from_payload(payload)
    gid_number = normalize_sso_gid_number(payload.get("gid_number"))
    full_name = _full_name_from_payload(payload)
    username = _username_from_payload(payload, email)

    profile_user = UserPublic(
        sub=sub,
        email=email,
        username=username,
        full_name=full_name,
        idp_groups=idp_groups,
        is_portal_admin=is_portal_admin,
        position=position,
        gid_number=gid_number,
    )
    timesheet_only = is_timesheet_only(profile_user)
    portal_chat_allowed = not timesheet_only

    # Сохраняем/обновляем профиль — чтобы email и имя были доступны другим пользователям.
    # profile.sub может отличаться от sub (SSO), если email-fallback нашёл существующий профиль.
    profile = await _upsert_user_profile(
        session,
        sub=sub,
        email=email,
        full_name=full_name,
        username=username,
        is_portal_admin=is_portal_admin,
        portal_chat_allowed=portal_chat_allowed,
        # is_developer — кэш «students / timesheet-only» для idp_groups_from_profile, не роль разработчика.
        is_developer=timesheet_only,
        gid_number=gid_number,
    )

    # Канонический sub — из профиля в БД; при смене sub на стороне SSO он остаётся прежним.
    canonical_sub = profile.sub if profile is not None else sub

    raw_birthday = (
        payload.get("birthday") or payload.get("birthdate") or payload.get("birth_date") or payload.get("date_of_birth")
    )
    await _upsert_specialist_profile_from_sso(
        session,
        sub=canonical_sub,
        raw_telegram=payload.get("telegram"),
        raw_birthday=raw_birthday,
    )

    avatar_url = build_user_photo_proxy_url(user_sub=canonical_sub, email=email)

    return UserPublic(
        sub=canonical_sub,
        email=email,
        username=username,
        full_name=full_name,
        idp_groups=idp_groups,
        is_portal_admin=is_portal_admin,
        position=position,
        gid_number=gid_number,
        avatar_url=avatar_url,
        avatar_focal_x=None,
        avatar_focal_y=None,
    )
