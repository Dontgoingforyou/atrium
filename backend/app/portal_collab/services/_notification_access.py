"""Проверки доступа для создания уведомлений."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_constants import IDP_GROUP_DEVELOPER, IDP_GROUP_PORTAL_ADMIN
from app.infrastructure.db.models.portal_chat import PortalChatMember, PortalChatMessage
from app.infrastructure.db.models.portal_task import PortalTask
from app.infrastructure.db.models.portal_task_assignee import PortalTaskAssignee
from app.infrastructure.db.models.portal_user_profile import PortalUserProfile
from app.schemas.auth import UserPublic
from app.services import rbac
from app.services.user_photo_url import build_user_photo_proxy_url

NOTIFICATION_TYPE_MENTION = "task_mention"
NOTIFICATION_TYPE_COMMENT = "task_comment"
NOTIFICATION_TYPE_ASSIGNED = "task_assigned"
NOTIFICATION_TYPE_TASK_DUE_SOON = "task_due_soon"
NOTIFICATION_TYPE_TASK_OVERDUE = "task_overdue"
TASK_REMINDER_KIND_DUE_SOON = "due_soon"
TASK_REMINDER_KIND_OVERDUE = "overdue"
NOTIFICATION_TYPE_DOCUMENT_MENTION = "document_mention"
NOTIFICATION_TYPE_DOCUMENT_TRASHED = "document_trashed"
NOTIFICATION_TYPE_CALENDAR_INVITE = "calendar_invite"
NOTIFICATION_TYPE_CALENDAR_SHARE = "calendar_share"
NOTIFICATION_TYPE_CALENDAR_REMINDER = "calendar_reminder"
NOTIFICATION_TYPE_CALENDAR_EVENT_UPDATED = "calendar_event_updated"
NOTIFICATION_TYPE_CALENDAR_EVENT_CANCELLED = "calendar_event_cancelled"
NOTIFICATION_TYPE_CALENDAR_SHARE_REVOKED = "calendar_share_revoked"


def idp_groups_from_profile(profile: PortalUserProfile) -> list[str]:
    """Восстановить IdP-группы из кэшированных полей профиля."""
    groups: list[str] = []
    if profile.is_portal_admin:
        groups.append(IDP_GROUP_PORTAL_ADMIN)
    if profile.is_developer:
        groups.append(IDP_GROUP_DEVELOPER)
    return groups


def batch_document_access_check(
    candidate_subs: set[str],
    profiles_by_sub: dict[str, PortalUserProfile],
) -> set[str]:
    """Батч-проверка доступа к документу: та же политика, что ``user_can_read_document``."""
    can_access: set[str] = set()
    for sub in candidate_subs:
        profile = profiles_by_sub.get(sub)
        if profile is None:
            continue
        user = UserPublic(
            sub=profile.sub,
            email=profile.email or "",
            username=profile.username or "",
            full_name=profile.full_name or "",
            idp_groups=idp_groups_from_profile(profile),
            is_portal_admin=profile.is_portal_admin,
            avatar_url=None,
        )
        if rbac.user_can_access_documents(user):
            can_access.add(sub)
    return can_access


async def batch_task_access_check(
    session: AsyncSession,
    candidate_subs: set[str],
    task: PortalTask,
    profiles_by_sub: dict[str, PortalUserProfile],
) -> set[str]:
    """Батч-проверка доступа к задаче для набора пользователей."""
    can_access: set[str] = set()
    needs_chat_check: set[str] = set()

    junction_assignees: set[str] = set()
    if task.id is not None:
        junction_result = await session.execute(
            select(PortalTaskAssignee.assignee_sub).where(
                PortalTaskAssignee.task_id == task.id,
                PortalTaskAssignee.assignee_sub.in_(list(candidate_subs)),
            )
        )
        junction_assignees = {row[0] for row in junction_result.all()}

    for sub in candidate_subs:
        profile = profiles_by_sub.get(sub)
        if profile is None:
            continue
        if profile.is_portal_admin or sub == task.creator_sub or sub == task.assignee_sub or sub in junction_assignees:
            can_access.add(sub)
        elif task.chat_id:
            needs_chat_check.add(sub)

    if needs_chat_check and task.chat_id:
        result = await session.execute(
            select(PortalChatMember.user_sub).where(
                PortalChatMember.chat_id == task.chat_id,
                PortalChatMember.user_sub.in_(list(needs_chat_check)),
            )
        )
        can_access |= {row.user_sub for row in result.all()}

    remaining_for_message = {
        sub for sub in candidate_subs if sub not in can_access and profiles_by_sub.get(sub) is not None
    }
    if remaining_for_message and task.source_message_id:
        msg_chat_id = (
            await session.execute(
                select(PortalChatMessage.chat_id).where(PortalChatMessage.id == task.source_message_id)
            )
        ).scalar_one_or_none()
        if msg_chat_id:
            result = await session.execute(
                select(PortalChatMember.user_sub).where(
                    PortalChatMember.chat_id == msg_chat_id,
                    PortalChatMember.user_sub.in_(list(remaining_for_message)),
                )
            )
            can_access |= {row.user_sub for row in result.all()}

    return can_access


async def user_public_from_profile_sub(session: AsyncSession, recipient_sub: str) -> UserPublic | None:
    """Минимальный UserPublic из кэша профиля."""
    profile = await session.get(PortalUserProfile, recipient_sub)
    if profile is None:
        return None
    av = build_user_photo_proxy_url(user_sub=profile.sub, email=profile.email)
    return UserPublic(
        sub=profile.sub,
        email=profile.email or "",
        username=profile.username or "",
        full_name=profile.full_name or "",
        idp_groups=idp_groups_from_profile(profile),
        is_portal_admin=profile.is_portal_admin,
        avatar_url=av,
    )
