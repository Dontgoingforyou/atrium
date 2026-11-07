from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import LearningMaterialStatus
from app.core.permissions import is_manager_or_admin
from app.core.portal_search_constants import (
    PORTAL_SEARCH_ENTITY_TYPE_AGREEMENT,
    PORTAL_SEARCH_ENTITY_TYPE_CHAT_MESSAGE,
    PORTAL_SEARCH_ENTITY_TYPE_LEARNING_MATERIAL,
    PORTAL_SEARCH_ENTITY_TYPE_SPECIALIST,
    PORTAL_SEARCH_ENTITY_TYPE_SPECIALIST_NOTE,
    PORTAL_SEARCH_ENTITY_TYPE_TASK,
)
from app.portal_documents.services.portal_document_queries import developer_docs_readable_ids
from app.portal_search.services._embedding_sql import vec_literal
from app.schemas.auth import UserPublic
from app.services import rbac

_SPECIALIST_ENTITY_TYPES = (
    PORTAL_SEARCH_ENTITY_TYPE_SPECIALIST,
    PORTAL_SEARCH_ENTITY_TYPE_SPECIALIST_NOTE,
)

_SQL_CHAT_RBAC = """
              AND (
                pe.entity_type <> :chat_msg_et
                OR EXISTS (
                  SELECT 1
                  FROM portal_chat c
                  INNER JOIN portal_chat_member pcm
                    ON pcm.chat_id = c.id AND pcm.user_sub = :viewer_sub
                  INNER JOIN portal_chat_message m
                    ON m.chat_id = c.id
                   AND m.id = CAST(pe.entity_id AS uuid)
                  WHERE c.id = (pe.meta->>'chat_id')::uuid
                    AND NOT (
                      c.canonical_dm_key IS NULL
                      AND (c.title IS NULL OR btrim(c.title) = '')
                    )
                    AND m.deleted_for_all_at IS NULL
                    AND m.body IS NOT NULL
                    AND btrim(m.body) <> ''
                    AND NOT EXISTS (
                      SELECT 1 FROM portal_chat_message_hidden h
                      WHERE h.message_id = m.id AND h.user_sub = :viewer_sub
                    )
                )
              )
            """

_SQL_TASK_RBAC = """
              AND (
                pe.entity_type <> :task_et
                OR EXISTS (
                  SELECT 1 FROM portal_task pt
                  WHERE pt.id = CAST(pe.entity_id AS uuid)
                    AND (
                      pt.creator_sub = :viewer_sub
                      OR pt.assignee_sub = :viewer_sub
                      OR pt.id IN (
                        SELECT pta.task_id FROM portal_task_assignee pta
                        WHERE pta.assignee_sub = :viewer_sub
                      )
                      OR pt.chat_id IN (
                        SELECT pcm.chat_id FROM portal_chat_member pcm
                        WHERE pcm.user_sub = :viewer_sub
                      )
                      OR pt.source_message_id IN (
                        SELECT m.id FROM portal_chat_message m
                        INNER JOIN portal_chat_member pcm2
                          ON pcm2.chat_id = m.chat_id AND pcm2.user_sub = :viewer_sub
                      )
                    )
                )
              )
            """

_SQL_LEARNING_RBAC = """
              AND (
                pe.entity_type <> :lm_et
                OR EXISTS (
                  SELECT 1 FROM portal_learning_material lm
                  WHERE lm.id = CAST(pe.entity_id AS uuid)
                    AND lm.status = :lm_active
                    AND (
                      NOT EXISTS (
                        SELECT 1 FROM portal_learning_material_idp_group g
                        WHERE g.material_id = lm.id
                      )
                      OR EXISTS (
                        SELECT 1 FROM portal_learning_material_idp_group g
                        WHERE g.material_id = lm.id
                          AND g.idp_group = ANY(:user_idp_groups)
                      )
                    )
                )
              )
            """

_SQL_SPECIALIST_EXCLUDE = """
              AND NOT (pe.entity_type = ANY(:specialist_et))
            """

_SQL_SPECIALIST_MANAGER_SCOPE = """
              AND (
                NOT (pe.entity_type = ANY(:specialist_et))
                OR EXISTS (
                  SELECT 1 FROM portal_manager_specialist ms
                  WHERE ms.specialist_sub = COALESCE(pe.meta->>'specialist_sub', pe.entity_id)
                    AND ms.manager_sub = :viewer_sub
                )
              )
            """


def merge_cap(skip: int, limit: int) -> int:
    """Вычислить ёмкость выборки для каждого источника при мультитиповом поиске."""
    return min(skip + limit + 100, 500)


def _as_utc(dt: datetime) -> datetime:
    """Наивный datetime → UTC-aware; aware — оставить как есть."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt


def merge_and_slice(
    *hit_streams: list[tuple[datetime, Any]],
    skip: int,
    limit: int,
) -> list[Any]:
    """Слить потоки результатов из нескольких источников по дате (убывание), применить skip/limit.

    Каждый поток — список кортежей (sort_date, hit_object).
    Возвращает список hit_object в порядке убывания даты.
    Наивные datetime нормализуются к UTC перед сравнением.
    """
    merged: list[tuple[datetime, Any]] = []
    for stream in hit_streams:
        merged.extend(stream)
    merged.sort(key=lambda x: _as_utc(x[0]), reverse=True)
    return [hit for _, hit in merged[skip : skip + limit]]


def _user_sees_all_tasks_in_collab_search(user: UserPublic) -> bool:
    """Те же границы, что ``search_tasks_for_user`` / ``_user_has_team_access``."""
    return is_manager_or_admin(user)


def _user_can_see_specialists(user: UserPublic) -> bool:
    """Специалисты видны только менеджерам АУ (gid_number) и portal_admin."""
    return is_manager_or_admin(user)


def _sql_agreement_rbac(document_clause: str) -> str:
    """Условия agreement для non-admin: автор, чат, видимые задачи, политика document_id."""
    return f"""
              AND (
                pe.entity_type <> :agr_et
                OR EXISTS (
                  SELECT 1 FROM portal_agreement pa
                  WHERE pa.id = CAST(pe.entity_id AS uuid)
                    AND (
                      pa.created_by_sub = :viewer_sub
                      OR pa.source_message_id IN (
                        SELECT m.id FROM portal_chat_message m
                        INNER JOIN portal_chat_member pcm
                          ON pcm.chat_id = m.chat_id AND pcm.user_sub = :viewer_sub
                      )
                      OR pa.task_id IN (
                        SELECT pt.id FROM portal_task pt
                        WHERE pt.creator_sub = :viewer_sub
                          OR pt.assignee_sub = :viewer_sub
                          OR pt.id IN (
                            SELECT pta.task_id FROM portal_task_assignee pta
                            WHERE pta.assignee_sub = :viewer_sub
                          )
                          OR pt.chat_id IN (
                            SELECT pcm3.chat_id FROM portal_chat_member pcm3
                            WHERE pcm3.user_sub = :viewer_sub
                          )
                      )
                      {document_clause}
                    )
                )
              )
            """


async def _agreement_document_clause(
    db: AsyncSession,
    user: UserPublic,
    params: dict[str, Any],
) -> str:
    """Та же политика, что ``_agreement_document_visibility_condition``."""
    if rbac.user_can_access_documents(user):
        return "OR pa.document_id IS NOT NULL"
    if rbac.user_can_access_developer_docs(user):
        dev_ids = await developer_docs_readable_ids(db)
        if not dev_ids:
            return ""
        params["agr_dev_ids"] = [str(x) for x in dev_ids]
        return "OR pa.document_id = ANY(CAST(:agr_dev_ids AS uuid[]))"
    return ""


async def semantic_search(
    db: AsyncSession,
    query_embedding: list[float],
    entity_types: list[str],
    top_k: int,
    min_score: float,
    *,
    user: UserPublic,
) -> list[dict[str, Any]]:
    """Семантический поиск по таблице portal_embedding.

    Выполняет косинусный поиск ближайших векторов через оператор pgvector ``<=>``.

    Для ``chat_message`` (если тип запрошен): DM и групповые инбокс-чаты, где пользователь
    — участник, с теми же исключениями чатов, что и ``search_messages_for_user``.

    Для ``task``: если пользователь не админ и не в группе менеджеров — условия видимости
    как у ``search_tasks_for_user`` (создатель, исполнитель, доп. assignee, чат, сообщение).

    Для ``agreement``: для не-админов — условия как у ``search_agreements_for_user``.

    Для ``learning_material``: non-admin — только ACTIVE и IdP-группы, как ``_is_material_visible``.

    Для ``specialist`` / ``specialist_note``: не-менеджеры не видят; менеджер — только своих.

    Возвращает список словарей с полями:
        entity_type, entity_id, text_content, similarity_score, meta.
    """
    viewer_sub = user.sub
    vec_str = vec_literal(query_embedding)
    entity_types_tuple = tuple(entity_types)

    sql = """
        SELECT
            pe.entity_type,
            pe.entity_id,
            pe.text_content,
            pe.meta,
            1 - (pe.embedding <=> CAST(:vec AS vector)) AS similarity_score
        FROM portal_embedding pe
        WHERE pe.entity_type = ANY(:types)
          AND 1 - (pe.embedding <=> CAST(:vec2 AS vector)) >= :min_score
    """
    params: dict[str, Any] = {
        "vec": vec_str,
        "vec2": vec_str,
        "types": list(entity_types_tuple),
        "min_score": min_score,
        "viewer_sub": viewer_sub,
    }

    if PORTAL_SEARCH_ENTITY_TYPE_CHAT_MESSAGE in entity_types:
        sql += _SQL_CHAT_RBAC
        params["chat_msg_et"] = PORTAL_SEARCH_ENTITY_TYPE_CHAT_MESSAGE

    if PORTAL_SEARCH_ENTITY_TYPE_TASK in entity_types and not _user_sees_all_tasks_in_collab_search(user):
        sql += _SQL_TASK_RBAC
        params["task_et"] = PORTAL_SEARCH_ENTITY_TYPE_TASK

    if PORTAL_SEARCH_ENTITY_TYPE_AGREEMENT in entity_types and not user.is_portal_admin:
        doc_clause = await _agreement_document_clause(db, user, params)
        sql += _sql_agreement_rbac(doc_clause)
        params["agr_et"] = PORTAL_SEARCH_ENTITY_TYPE_AGREEMENT

    if PORTAL_SEARCH_ENTITY_TYPE_LEARNING_MATERIAL in entity_types and not user.is_portal_admin:
        sql += _SQL_LEARNING_RBAC
        params["lm_et"] = PORTAL_SEARCH_ENTITY_TYPE_LEARNING_MATERIAL
        params["lm_active"] = LearningMaterialStatus.ACTIVE
        params["user_idp_groups"] = list(user.idp_groups)

    specialist_types_in_query = [et for et in entity_types if et in _SPECIALIST_ENTITY_TYPES]
    if specialist_types_in_query:
        if not _user_can_see_specialists(user):
            sql += _SQL_SPECIALIST_EXCLUDE
            params["specialist_et"] = list(specialist_types_in_query)
        elif not user.is_portal_admin:
            sql += _SQL_SPECIALIST_MANAGER_SCOPE
            params["specialist_et"] = list(specialist_types_in_query)

    sql += " ORDER BY similarity_score DESC LIMIT :top_k"
    params["top_k"] = top_k

    rows = (await db.execute(sa.text(sql), params)).fetchall()

    return [
        {
            "entity_type": r.entity_type,
            "entity_id": r.entity_id,
            "text_content": r.text_content,
            "similarity_score": float(r.similarity_score),
            "meta": r.meta if isinstance(r.meta, dict) else {},
        }
        for r in rows
    ]
