from __future__ import annotations

import logging
import uuid
from typing import Any

from sqlalchemy import false as sa_false
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.enums import AgreementStatus
from app.core.exceptions import ForbiddenError, NotFoundError
from app.core.text_search import escape_ilike_pattern
from app.core.utils import now_utc as _now_utc
from app.infrastructure.db.models.portal_agreement import PortalAgreement
from app.infrastructure.db.models.portal_chat import PortalChatMember, PortalChatMessage
from app.infrastructure.db.models.portal_document import PortalDocument
from app.infrastructure.db.models.portal_task import PortalTask
from app.portal_chat.services import chat as chat_svc
from app.portal_collab.schemas.agreement import PortalAgreementCreate, PortalAgreementUpdate
from app.portal_collab.services import task as task_svc
from app.portal_documents.services.portal_document_queries import (
    developer_docs_readable_ids,
    user_can_read_document,
)
from app.schemas.auth import UserPublic
from app.services import rbac

logger = logging.getLogger(__name__)


def _message_ids_visible_in_user_chats_subquery(user_sub: str) -> Any:
    return (
        select(PortalChatMessage.id)
        .join(PortalChatMember, PortalChatMember.chat_id == PortalChatMessage.chat_id)
        .where(PortalChatMember.user_sub == user_sub)
    )


async def _agreement_document_visibility_condition(session: AsyncSession, user: UserPublic) -> Any:
    """Условие видимости agreement.document_id — та же политика, что у ``user_can_read_document``.

    Большинство пользователей видят любой документ (``rbac.user_can_access_documents``);
    пользователи в режиме «только таймшиты» — только документы из developer-docs;
    остальным — документная ветка недоступна вовсе.
    """
    if rbac.user_can_access_documents(user):
        return PortalAgreement.document_id.isnot(None)
    if rbac.user_can_access_developer_docs(user):
        dev_ids = await developer_docs_readable_ids(session)
        return PortalAgreement.document_id.in_(dev_ids)
    return sa_false()


async def _validate_agreement_links(
    session: AsyncSession,
    user: UserPublic,
    *,
    source_message_id: uuid.UUID | None,
    document_id: uuid.UUID | None,
    task_id: uuid.UUID | None,
) -> None:
    if document_id is not None:
        doc = await session.get(PortalDocument, document_id)
        if doc is None:
            raise NotFoundError("Документ не найден")
        if not await user_can_read_document(session, user, document_id):
            logger.warning(
                "Отказ в доступе к документу при привязке договорённости: user_sub=%s document_id=%s",
                user.sub,
                document_id,
            )
            raise ForbiddenError("Нет доступа к документу")
    if source_message_id is not None:
        if not await chat_svc.user_can_access_message(session, user, source_message_id):
            logger.warning(
                "Отказ в доступе к сообщению при привязке договорённости: user_sub=%s message_id=%s",
                user.sub,
                source_message_id,
            )
            raise ForbiddenError("Нет доступа к сообщению")
    if task_id is not None:
        # get_task уже проверяет существование и доступ (NotFoundError/ForbiddenError + WARNING-лог)
        await task_svc.get_task(session, user, task_id)


async def user_can_view_agreement(session: AsyncSession, user: UserPublic, row: PortalAgreement) -> bool:
    if user.is_portal_admin:
        return True
    if row.created_by_sub == user.sub:
        return True
    if row.source_message_id:
        if await chat_svc.user_can_access_message(session, user, row.source_message_id):
            return True
    if row.task_id:
        task = await session.get(PortalTask, row.task_id)
        if task and await task_svc.user_can_view_task(session, user, task):
            return True
    if row.document_id:
        if await user_can_read_document(session, user, row.document_id):
            return True
    return False


async def create_agreement(session: AsyncSession, user: UserPublic, data: PortalAgreementCreate) -> PortalAgreement:
    await _validate_agreement_links(
        session,
        user,
        source_message_id=data.source_message_id,
        document_id=data.document_id,
        task_id=data.task_id,
    )
    now = _now_utc()
    if data.status is not None and not user.is_portal_admin:
        logger.warning(
            "Отказ в доступе: задание статуса договорённости при создании доступно только администратору user_sub=%s",
            user.sub,
        )
        raise ForbiddenError("Только администратор портала может задавать статус при создании")
    initial_status = data.status.value if data.status is not None else AgreementStatus.DRAFT.value
    row = PortalAgreement(
        body=data.body,
        status=initial_status,
        source_message_id=data.source_message_id,
        document_id=data.document_id,
        task_id=data.task_id,
        created_by_sub=user.sub,
        created_at=now,
        updated_at=now,
    )
    session.add(row)
    await session.commit()
    await session.refresh(row, ["source_message"])
    return row


async def list_agreements(
    session: AsyncSession,
    user: UserPublic,
    *,
    status: str | None = None,
    document_id: uuid.UUID | None = None,
    task_id: uuid.UUID | None = None,
    skip: int = 0,
    limit: int = 100,
) -> list[PortalAgreement]:
    stmt = select(PortalAgreement).options(selectinload(PortalAgreement.source_message))
    if not user.is_portal_admin:
        msg_sq = _message_ids_visible_in_user_chats_subquery(user.sub)
        task_sq = task_svc.visible_task_ids_subquery(user)
        doc_condition = await _agreement_document_visibility_condition(session, user)
        conditions: list[Any] = [
            PortalAgreement.created_by_sub == user.sub,
            PortalAgreement.source_message_id.in_(msg_sq),
            PortalAgreement.task_id.in_(task_sq),
            doc_condition,
        ]
        stmt = stmt.where(or_(*conditions))
    if status is not None:
        stmt = stmt.where(PortalAgreement.status == status)
    if document_id is not None:
        stmt = stmt.where(PortalAgreement.document_id == document_id)
    if task_id is not None:
        stmt = stmt.where(PortalAgreement.task_id == task_id)
    stmt = stmt.order_by(PortalAgreement.created_at.desc()).offset(skip).limit(limit)
    return list((await session.execute(stmt)).scalars().all())


async def get_agreement(session: AsyncSession, user: UserPublic, agreement_id: uuid.UUID) -> PortalAgreement:
    stmt = (
        select(PortalAgreement)
        .where(PortalAgreement.id == agreement_id)
        .options(selectinload(PortalAgreement.source_message))
    )
    row = (await session.execute(stmt)).scalar_one_or_none()
    if row is None:
        raise NotFoundError("Договорённость не найдена")
    if not await user_can_view_agreement(session, user, row):
        logger.warning(
            "Отказ в доступе к договорённости: user_sub=%s agreement_id=%s",
            user.sub,
            agreement_id,
        )
        raise ForbiddenError("Нет доступа к договорённости")
    return row


async def update_agreement(
    session: AsyncSession,
    user: UserPublic,
    agreement_id: uuid.UUID,
    data: PortalAgreementUpdate,
) -> PortalAgreement:
    row = await get_agreement(session, user, agreement_id)
    if not user.is_portal_admin and row.created_by_sub != user.sub:
        logger.warning(
            "Отказ в доступе: изменение чужой договорённости user_sub=%s agreement_id=%s",
            user.sub,
            agreement_id,
        )
        raise ForbiddenError("Нет прав на изменение договорённости")
    patch = data.model_dump(exclude_unset=True)
    if not patch:
        return row

    next_doc = patch["document_id"] if "document_id" in patch else row.document_id
    next_src = patch["source_message_id"] if "source_message_id" in patch else row.source_message_id
    next_task = patch["task_id"] if "task_id" in patch else row.task_id

    if any(k in patch for k in ("document_id", "source_message_id", "task_id")):
        await _validate_agreement_links(
            session,
            user,
            source_message_id=next_src,
            document_id=next_doc,
            task_id=next_task,
        )

    if "body" in patch:
        row.body = patch["body"]
    if "status" in patch:
        st = patch["status"]
        row.status = st.value if isinstance(st, AgreementStatus) else str(st)
    if "document_id" in patch:
        row.document_id = patch["document_id"]
    if "source_message_id" in patch:
        row.source_message_id = patch["source_message_id"]
    if "task_id" in patch:
        row.task_id = patch["task_id"]

    row.updated_at = _now_utc()
    await session.commit()
    await session.refresh(row, ["source_message"])
    return row


async def search_agreements_for_user(
    session: AsyncSession,
    user: UserPublic,
    q: str,
    *,
    skip: int = 0,
    limit: int = 100,
) -> list[PortalAgreement]:
    from sqlalchemy import func as sa_func

    pl = f"%{escape_ilike_pattern(q.lower())}%"
    base = (
        select(PortalAgreement)
        .options(selectinload(PortalAgreement.source_message))
        .where(sa_func.lower(PortalAgreement.body).like(pl, escape="\\"))
    )
    if user.is_portal_admin:
        stmt = base.order_by(PortalAgreement.created_at.desc()).offset(skip).limit(limit)
    else:
        msg_sq = _message_ids_visible_in_user_chats_subquery(user.sub)
        task_sq = task_svc.visible_task_ids_subquery(user)
        doc_condition = await _agreement_document_visibility_condition(session, user)
        conditions: list[Any] = [
            PortalAgreement.created_by_sub == user.sub,
            PortalAgreement.source_message_id.in_(msg_sq),
            PortalAgreement.task_id.in_(task_sq),
            doc_condition,
        ]
        stmt = base.where(or_(*conditions)).order_by(PortalAgreement.created_at.desc()).offset(skip).limit(limit)
    return list((await session.execute(stmt)).scalars().all())
