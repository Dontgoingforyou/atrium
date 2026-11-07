"""API Jira для карточки специалиста."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Query, Response, status

from app.api.deps import DbSession, HttpClient
from app.api.deps_auth import CurrentUser, PortalAdminUser
from app.core.config import get_settings
from app.infrastructure.db.models.portal_specialist_profile import PortalSpecialistProfile
from app.integrations.jira.normalize import filter_jira_groups_for_display
from app.portal_specialists.schemas.jira import JiraFieldGroupRead, JiraLinkRequest, JiraSearchHit, SpecialistJiraRead
from app.portal_specialists.services import jira_board_sync as board_sync_svc
from app.portal_specialists.services import jira_import as jira_svc

router = APIRouter(prefix="/portal/specialists", tags=["Специалисты — Jira"])


def _to_jira_read(profile: PortalSpecialistProfile) -> SpecialistJiraRead:
    settings = get_settings()
    groups_raw = filter_jira_groups_for_display((profile.jira_fields or {}).get("groups") or [])
    groups = [JiraFieldGroupRead.model_validate(g) for g in groups_raw]
    return SpecialistJiraRead(
        specialist_sub=profile.specialist_sub,
        jira_issue_key=profile.jira_issue_key,
        jira_browse_url=settings.jira_browse_url(profile.jira_issue_key) if profile.jira_issue_key else None,
        jira_synced_at=profile.jira_synced_at,
        groups=groups,
    )


@router.get(
    "/jira/search",
    response_model=list[JiraSearchHit],
    summary="Поиск специалистов в Jira (менеджер или admin)",
)
async def search_jira(
    user: CurrentUser,
    http: HttpClient,
    q: Annotated[str, Query(min_length=2, max_length=100)],
) -> list[JiraSearchHit]:
    hits = await jira_svc.search_jira_specialists(user, http, q)
    return [JiraSearchHit.model_validate(h) for h in hits]


@router.get(
    "/{specialist_sub}/jira",
    response_model=SpecialistJiraRead,
    summary="Состояние привязки Jira (менеджер или admin)",
)
async def get_specialist_jira(
    specialist_sub: str,
    user: CurrentUser,
    session: DbSession,
) -> SpecialistJiraRead:
    profile = await jira_svc.get_specialist_jira_state(session, user, specialist_sub)
    return _to_jira_read(profile)


@router.post(
    "/{specialist_sub}/jira/link",
    response_model=SpecialistJiraRead,
    summary="Привязать специалиста к задаче Jira и импортировать данные",
)
async def link_specialist_jira(
    specialist_sub: str,
    body: JiraLinkRequest,
    user: CurrentUser,
    session: DbSession,
    http: HttpClient,
) -> SpecialistJiraRead:
    profile = await jira_svc.link_specialist_to_jira(session, user, http, specialist_sub, body.issue_key)
    return _to_jira_read(profile)


@router.post(
    "/{specialist_sub}/jira/sync",
    response_model=SpecialistJiraRead,
    summary="Обновить данные из Jira для привязанного специалиста",
)
async def sync_specialist_jira(
    specialist_sub: str,
    user: CurrentUser,
    session: DbSession,
    http: HttpClient,
) -> SpecialistJiraRead:
    profile = await jira_svc.sync_specialist_from_jira(session, user, http, specialist_sub)
    return _to_jira_read(profile)


@router.delete(
    "/{specialist_sub}/jira/link",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Отвязать специалиста от Jira",
)
async def unlink_specialist_jira(
    specialist_sub: str,
    user: CurrentUser,
    session: DbSession,
) -> Response:
    await jira_svc.unlink_specialist_from_jira(session, user, specialist_sub)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/columns/sync-from-jira",
    summary="Синхронизировать колонки воронки с доской Jira (admin)",
)
async def sync_columns_from_jira(
    user: PortalAdminUser,
    session: DbSession,
    http: HttpClient,
) -> dict[str, int]:
    cols = await board_sync_svc.sync_columns_from_jira(session, user, http)
    return {"synced": len(cols)}
