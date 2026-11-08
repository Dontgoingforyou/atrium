from __future__ import annotations

import logging
import uuid
from typing import Annotated, Any

from fastapi import APIRouter, BackgroundTasks, Header, Query

from app.api.deps import DbSession, HttpClient
from app.api.deps_auth import CurrentUser, PortalAdminUser
from app.core.exceptions import ConflictError, ValidationError
from app.core.portal_search_constants import (
    PORTAL_SEARCH_ENTITY_TYPES,
    PORTAL_SEARCH_MIN_QUERY_LEN,
    PORTAL_SEARCH_QUERY_MAX_LEN,
    PORTAL_SEMANTIC_DEFAULT_TYPES,
    PORTAL_SEMANTIC_ENTITY_TYPES,
)
from app.infrastructure.cache.reindex_lock import try_acquire_reindex_lock
from app.portal_calendar.remote import calendar_remote_for_search
from app.portal_search.schemas.search import (
    PortalSearchHitResponseUnion,
    PortalSemanticSearchResponse,
)
from app.portal_search.services import embedding as emb_svc
from app.portal_search.services._embedding_local import LOCAL_SEMANTIC_MIN_SCORE
from app.portal_search.services.search_orchestrator import run_fulltext_search, run_semantic_search

router = APIRouter(prefix="/portal", tags=["Поиск"])
logger = logging.getLogger(__name__)


@router.get(
    "/search",
    summary="Глобальный поиск по порталу",
    description=(
        "Типы сущностей: document, chat_message, task, specialist, calendar_event. "
        "Несколько types объединяются, сортировка по дате (убывание), затем skip/limit. "
        "Один тип — пагинация передаётся в соответствующий запрос."
    ),
    response_model=list[PortalSearchHitResponseUnion],
)
async def portal_search(
    user: CurrentUser,
    db: DbSession,
    http: HttpClient,
    q: Annotated[
        str,
        Query(
            min_length=1,
            max_length=PORTAL_SEARCH_QUERY_MAX_LEN,
            description="Поисковая строка",
        ),
    ],
    types: Annotated[
        list[str] | None,
        Query(description="Типы сущностей (можно несколько)"),
    ] = None,
    tag_slug: Annotated[
        list[str] | None,
        Query(description="Фильтр по slug тегов документов (можно несколько)"),
    ] = None,
    status_ids: Annotated[
        list[uuid.UUID] | None,
        Query(
            description=(
                "Legacy UUID направлений portal_specialist_status (portal_manager_specialist.status_id), "
                "не Jira profile.direction"
            )
        ),
    ] = None,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    authorization: Annotated[str | None, Header()] = None,
) -> list[PortalSearchHitResponseUnion]:
    qt = q.strip()
    if len(qt) < PORTAL_SEARCH_MIN_QUERY_LEN:
        raise ValidationError(
            f"Параметр q после удаления пробелов должен быть не короче {PORTAL_SEARCH_MIN_QUERY_LEN} символов",
        )

    resolved_types = types if types else list(PORTAL_SEARCH_ENTITY_TYPES)
    unknown = set(resolved_types) - PORTAL_SEARCH_ENTITY_TYPES
    if unknown:
        raise ValidationError(
            f"Неизвестные типы сущностей: {', '.join(sorted(unknown))}",
        )

    calendar_remote, omit_calendar = calendar_remote_for_search(user, authorization, http)
    return await run_fulltext_search(
        db,
        user,
        qt,
        resolved_types,
        tag_slug=tag_slug,
        status_ids=status_ids,
        skip=skip,
        limit=limit,
        calendar_remote=calendar_remote,
        omit_calendar=omit_calendar,
    )


@router.get(
    "/search/semantic",
    summary="Семантический поиск по всему контенту портала",
    description=(
        "Поиск по смыслу: запрос и тексты сравниваются как векторы в pgvector. "
        "Без ключа модели векторы считаются на портале по словам. "
        "С ключом запрос уходит во внешнюю модель эмбеддингов. "
        "Нужен индекс: make seed или POST /portal/admin/search/reindex."
    ),
)
async def portal_semantic_search(
    user: CurrentUser,
    db: DbSession,
    http: HttpClient,
    q: Annotated[
        str,
        Query(
            min_length=1,
            max_length=PORTAL_SEARCH_QUERY_MAX_LEN,
            description="Поисковый запрос на естественном языке",
        ),
    ],
    types: Annotated[
        list[str] | None,
        Query(
            description=(
                "Типы сущностей: document, task, chat_message, learning_material, "
                "specialist, specialist_note, calendar_event; agreement — по явному types=. "
                "Типы specialist/specialist_note доступны только менеджерам и portal_admin."
            )
        ),
    ] = None,
    tag_slug: Annotated[
        list[str] | None,
        Query(description="Фильтр по slug тегов документов (можно несколько)"),
    ] = None,
    status_ids: Annotated[
        list[uuid.UUID] | None,
        Query(
            description=(
                "Legacy UUID направлений portal_specialist_status (portal_manager_specialist.status_id), "
                "не Jira profile.direction"
            )
        ),
    ] = None,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    authorization: Annotated[str | None, Header()] = None,
) -> PortalSemanticSearchResponse:
    from app.core.config import get_settings

    qt = q.strip()
    if len(qt) < PORTAL_SEARCH_MIN_QUERY_LEN:
        raise ValidationError(
            f"Параметр q после удаления пробелов должен быть не короче {PORTAL_SEARCH_MIN_QUERY_LEN} символов",
        )

    resolved_types = list(types) if types else list(PORTAL_SEMANTIC_DEFAULT_TYPES)
    unknown = set(resolved_types) - PORTAL_SEMANTIC_ENTITY_TYPES
    if unknown:
        raise ValidationError(
            f"Неизвестные типы сущностей: {', '.join(sorted(unknown))}",
        )

    settings = get_settings()
    min_score = settings.semantic_search_min_score
    if not settings.openai_api_key:
        min_score = min(min_score, LOCAL_SEMANTIC_MIN_SCORE)

    calendar_remote, omit_calendar = calendar_remote_for_search(user, authorization, http)
    return await run_semantic_search(
        db,
        user,
        qt,
        resolved_types,
        tag_slug=tag_slug,
        status_ids=status_ids,
        skip=skip,
        limit=limit,
        min_score=min_score,
        calendar_remote=calendar_remote,
        omit_calendar=omit_calendar,
    )


@router.post(
    "/admin/search/reindex",
    summary="Запустить переиндексацию контента для семантического поиска",
    description=(
        "Доступно только администраторам портала. "
        "Запускает bulk-переиндексацию в фоне. "
        "Если entity_types не указаны — переиндексирует все типы."
    ),
    status_code=202,
)
async def trigger_reindex(
    admin: PortalAdminUser,
    background_tasks: BackgroundTasks,
    entity_types: Annotated[
        list[str] | None,
        Query(description="Типы для переиндексации; пусто — все"),
    ] = None,
) -> dict[str, Any]:
    if entity_types:
        unknown = set(entity_types) - PORTAL_SEMANTIC_ENTITY_TYPES
        if unknown:
            raise ValidationError(f"Неизвестные типы: {', '.join(sorted(unknown))}")

    targets = list(entity_types) if entity_types else list(PORTAL_SEMANTIC_ENTITY_TYPES)

    lock_token = await try_acquire_reindex_lock()
    if lock_token is None:
        raise ConflictError(
            "Переиндексация уже выполняется. Дождитесь завершения текущей задачи.",
        )

    background_tasks.add_task(emb_svc.bulk_reindex_bg, targets, lock_token)
    logger.info("Переиндексация запущена в фоне: %s (admin=%s)", targets, admin.sub)

    return {"status": "started", "entity_types": targets}
