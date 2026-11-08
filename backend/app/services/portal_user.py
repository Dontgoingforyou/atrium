from __future__ import annotations

import logging
from collections.abc import Collection
from datetime import datetime

import httpx
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement
from sqlalchemy.sql.selectable import Subquery

from app.core.exceptions import ForbiddenError
from app.core.permissions import is_manager_or_admin
from app.infrastructure.db.models.portal_user_profile import PortalUserProfile
from app.integrations.profile_directory.client import PhotoMeta
from app.integrations.profile_directory.username import username_from_email
from app.schemas.auth import UserPublic
from app.schemas.portal_user import PortalUserRead
from app.services.portal_user_visibility import directory_employee_visible_sql, hidden_emails_for_directory
from app.services.user_photo_meta_cache import get_cached_photo_meta, get_cached_photo_meta_bulk
from app.services.user_photo_url import build_user_photo_proxy_url

logger = logging.getLogger(__name__)


async def _avatar_url_for_profile(
    *,
    user_sub: str,
    email: str | None,
    meta: PhotoMeta | None = None,
) -> str | None:
    """Signed proxy URL; если в Redis meta.has_photo=false — None; иначе URL (+version при кэше)."""
    uname = username_from_email(email)
    version: int | None = None
    if meta is None and uname:
        meta = await get_cached_photo_meta(uname)
    if meta is not None and not meta.has_photo:
        return None
    if meta is not None:
        version = meta.version
    return build_user_photo_proxy_url(user_sub=user_sub, email=email, version=version)


async def _avatar_urls_for_rows(
    rows: list[tuple[str, str | None]],
) -> list[str | None]:
    """``rows`` — пары (sub, email); один Redis pipeline на страницу."""
    unames = [username_from_email(email) for _, email in rows]
    wanted = [u for u in unames if u]
    meta_by_uname = await get_cached_photo_meta_bulk(wanted) if wanted else {}
    out: list[str | None] = []
    for (sub, email), uname in zip(rows, unames, strict=True):
        meta = meta_by_uname.get(uname) if uname else None
        out.append(await _avatar_url_for_profile(user_sub=sub, email=email, meta=meta))
    return out


async def avatar_urls_for_subs(
    session: AsyncSession,
    subs: Collection[str],
) -> dict[str, str | None]:
    """Signed EA proxy URL по sub: один SELECT профилей + bulk Redis meta.

    Нет профиля — ключа нет. ``has_photo=false`` в meta — ``None`` (как в каталоге).
    """
    wanted = {s for s in subs if s}
    if not wanted:
        return {}
    stmt = select(PortalUserProfile.sub, PortalUserProfile.email).where(PortalUserProfile.sub.in_(wanted))
    rows = (await session.execute(stmt)).all()
    pairs = [(row.sub, row.email) for row in rows]
    avatars = await _avatar_urls_for_rows(pairs)
    return {sub: av for (sub, _email), av in zip(pairs, avatars, strict=True)}


async def portal_user_subs_registered(session: AsyncSession, subs: Collection[str]) -> set[str]:
    """Подмножество ``subs`` с живым профилем и разрешёнными чатами портала."""
    wanted = {s for s in subs if s}
    if not wanted:
        return set()
    stmt = select(PortalUserProfile.sub).where(
        PortalUserProfile.sub.in_(wanted),
        PortalUserProfile.portal_chat_allowed.is_(True),
    )
    rows = (await session.execute(stmt)).scalars().all()
    return set(rows)


async def assert_subs_may_use_portal_chat(session: AsyncSession, subs: Collection[str]) -> None:
    """Отказ, если нет профиля или у профиля запрещены чаты портала."""
    wanted = {s for s in subs if s}
    if not wanted:
        return
    allowed = await portal_user_subs_registered(session, wanted)
    if wanted - allowed:
        logger.warning("Отказ в доступе: resource=portal_chat denied_subs=%s", sorted(wanted - allowed))
        raise ForbiddenError("Этому пользователю недоступны чаты портала")


def _visible_profile_clause(hidden_emails: Collection[str]) -> ColumnElement[bool]:
    profile = PortalUserProfile
    cond: ColumnElement[bool] = and_(
        profile.portal_chat_allowed.is_(True),
        directory_employee_visible_sql(),
    )
    if hidden_emails:
        cond = and_(
            cond,
            or_(
                profile.email.is_(None),
                func.lower(func.trim(profile.email)).notin_(list(hidden_emails)),
            ),
        )
    return cond


def _portal_users_visible_subquery(hidden_emails: Collection[str] = ()) -> Subquery:
    """sub с живым профилем и ``portal_chat_allowed=True`` — один фильтр для list и count."""
    profile = PortalUserProfile
    return select(profile.sub).where(_visible_profile_clause(hidden_emails)).subquery()


async def _hidden_picker_emails(
    session: AsyncSession,
    http: httpx.AsyncClient | None,
) -> set[str]:
    emails = (
        (
            await session.execute(
                select(PortalUserProfile.email).where(
                    PortalUserProfile.portal_chat_allowed.is_(True),
                    PortalUserProfile.email.is_not(None),
                )
            )
        )
        .scalars()
        .all()
    )
    return await hidden_emails_for_directory(http, emails)


async def _count_portal_users(session: AsyncSession, hidden_emails: Collection[str] = ()) -> int:
    """Общее число уникальных пользователей портала (для ``total`` в ``PagedResponse``)."""
    stmt = select(func.count()).select_from(_portal_users_visible_subquery(hidden_emails))
    return int((await session.execute(stmt)).scalar_one())


async def list_portal_users(
    session: AsyncSession,
    *,
    skip: int = 0,
    limit: int = 200,
    http: httpx.AsyncClient | None = None,
) -> tuple[list[PortalUserRead], int]:
    """Вернуть пользователей портала с живым профилем и разрешёнными чатами.

    Источник — только ``portal_user_profile`` (без «призраков» из истории чатов).
    Исключаются пользователи с ``portal_chat_allowed=False``, тестовые учётки,
    явный список скрытых адресов, чужой отдел (gid известен и это не основной отдел)
    и почты not_found в сервисе профилей (если сверка настроена).
    """
    hidden = await _hidden_picker_emails(session, http)
    total = await _count_portal_users(session, hidden)
    profile = PortalUserProfile
    stmt = (
        select(
            profile.sub,
            profile.full_name.label("display_name"),
            profile.email,
            profile.username,
            profile.last_seen_at,
        )
        .where(_visible_profile_clause(hidden))
        .order_by(profile.full_name.asc().nulls_last(), profile.email.asc().nulls_last(), profile.sub.asc())
        .offset(skip)
        .limit(limit)
    )

    rows = (await session.execute(stmt)).all()
    avatars = await _avatar_urls_for_rows([(row.sub, row.email) for row in rows])
    out: list[PortalUserRead] = []
    for row, av in zip(rows, avatars, strict=True):
        out.append(
            PortalUserRead(
                sub=row.sub,
                display_name=row.display_name,
                email=row.email,
                username=row.username,
                avatar_url=av,
                last_seen_at=row.last_seen_at,
                avatar_focal_x=None,
                avatar_focal_y=None,
            ),
        )
    return out, total


async def list_portal_students_for_specialists(
    session: AsyncSession,
    user: UserPublic,
    *,
    skip: int = 0,
    limit: int = 200,
) -> tuple[list[PortalUserRead], int]:
    """Профили с ``portal_chat_allowed=False`` (студенты без чатов): только менеджер/админ портала."""

    if not (user.is_portal_admin or is_manager_or_admin(user)):
        logger.warning("Отказ в доступе: user_sub=%s resource=portal_users/students", user.sub)
        raise ForbiddenError("Доступ к списку специалистов — только для менеджера или администратора портала")

    profile = PortalUserProfile
    base_where = profile.portal_chat_allowed.is_(False)
    count_stmt = select(func.count()).select_from(profile).where(base_where)
    total = int((await session.execute(count_stmt)).scalar_one())

    stmt = (
        select(
            profile.sub,
            profile.full_name,
            profile.email,
            profile.username,
            profile.last_seen_at,
        )
        .where(base_where)
        .order_by(
            profile.full_name.asc().nulls_last(),
            profile.email.asc().nulls_last(),
            profile.sub.asc(),
        )
        .offset(skip)
        .limit(limit)
    )
    rows = (await session.execute(stmt)).all()
    avatars = await _avatar_urls_for_rows([(row.sub, row.email) for row in rows])
    out: list[PortalUserRead] = []
    for row, av in zip(rows, avatars, strict=True):
        out.append(
            PortalUserRead(
                sub=row.sub,
                display_name=row.full_name,
                email=row.email,
                username=row.username,
                avatar_url=av,
                last_seen_at=row.last_seen_at,
                avatar_focal_x=None,
                avatar_focal_y=None,
            ),
        )
    return out, total


async def bulk_last_seen_from_profile(
    session: AsyncSession,
    subs: Collection[str],
) -> dict[str, datetime | None]:
    """``last_seen_at`` из PostgreSQL для списка sub (fallback при отсутствии ключа в Redis)."""
    wanted = [s for s in subs if s]
    if not wanted:
        return {}
    stmt = select(PortalUserProfile.sub, PortalUserProfile.last_seen_at).where(
        PortalUserProfile.sub.in_(wanted),
    )
    rows = (await session.execute(stmt)).all()
    return {sub: last_seen for sub, last_seen in rows}


async def list_portal_user_subs_ordered(
    session: AsyncSession,
    *,
    skip: int = 0,
    limit: int = 200,
    http: httpx.AsyncClient | None = None,
) -> tuple[list[str], int]:
    """Те же пользователи, порядок и общее число, что у ``list_portal_users``, но только ``sub``."""
    hidden = await _hidden_picker_emails(session, http)
    total = await _count_portal_users(session, hidden)
    profile = PortalUserProfile
    stmt = (
        select(profile.sub)
        .where(_visible_profile_clause(hidden))
        .order_by(profile.full_name.asc().nulls_last(), profile.email.asc().nulls_last(), profile.sub.asc())
        .offset(skip)
        .limit(limit)
    )
    rows = (await session.execute(stmt)).scalars().all()
    return list(rows), total
