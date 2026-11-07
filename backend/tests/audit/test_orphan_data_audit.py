"""Инварианты «мусора»: осиротевшие эмбеддинги, stale-вложения, корни корзины.

Счётчики эмбеддингов/вложений — SQL в тесте (в проде нет публичного count).
Корзина — семантика прода (`count_trash_document_roots` / `_trash_roots_base_stmt`).
Удаление мусора проверяют job-тесты, не этот файл.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from app.infrastructure.db.models.portal_chat import PortalChat, PortalChatAttachment, PortalChatMessage
from app.infrastructure.db.models.portal_document import PortalDocument
from app.infrastructure.db.models.portal_embedding import PortalEmbedding
from app.portal_documents.services.portal_document_trash import (
    DOCUMENT_TRASH_TTL_DAYS,
    _trash_roots_base_stmt,
    count_trash_document_roots,
)
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession


def _now() -> datetime:
    return datetime.now(UTC)


async def count_orphan_document_embeddings(session: AsyncSession) -> int:
    """Строки portal_embedding для document без живой записи portal_document."""
    live_ids = {str(i) for i in (await session.scalars(select(PortalDocument.id))).all()}
    embs = (await session.scalars(select(PortalEmbedding).where(PortalEmbedding.entity_type == "document"))).all()
    return sum(1 for e in embs if e.entity_id not in live_ids)


async def count_orphan_chat_message_embeddings(session: AsyncSession) -> int:
    live_ids = {str(i) for i in (await session.scalars(select(PortalChatMessage.id))).all()}
    embs = (await session.scalars(select(PortalEmbedding).where(PortalEmbedding.entity_type == "chat_message"))).all()
    return sum(1 for e in embs if e.entity_id not in live_ids)


async def count_orphan_chat_attachments(session: AsyncSession, *, min_age_hours: float) -> int:
    cutoff = _now() - timedelta(hours=min_age_hours)
    stmt = select(PortalChatAttachment).where(
        PortalChatAttachment.message_id.is_(None),
        PortalChatAttachment.created_at < cutoff,
    )
    return len((await session.scalars(stmt)).all())


async def count_expired_trash_roots(session: AsyncSession) -> int:
    """Просроченные корни корзины — тот же stmt, что nightly purge."""
    cutoff = _now() - timedelta(days=DOCUMENT_TRASH_TTL_DAYS)
    rows = (await session.execute(_trash_roots_base_stmt(expired_before=cutoff))).scalars().all()
    return len(rows)


def _embedding(*, entity_type: str, entity_id: str) -> PortalEmbedding:
    return PortalEmbedding(
        entity_type=entity_type,
        entity_id=entity_id,
        text_content="ghost",
        embedding=[0.0] * 8,
        meta={},
        updated_at=_now(),
    )


def _document(*, title: str, deleted_at: datetime | None = None, parent_id: uuid.UUID | None = None) -> PortalDocument:
    return PortalDocument(
        title=title,
        author_sub="admin-sub",
        parent_document_id=parent_id,
        deleted_at=deleted_at,
        created_at=_now(),
        updated_at=_now(),
    )


async def _chat_with_optional_message(
    session: AsyncSession,
    *,
    with_message: bool,
) -> tuple[PortalChat, PortalChatMessage | None]:
    chat = PortalChat(title="audit-chat", created_by_sub="admin-sub", created_at=_now(), updated_at=_now())
    session.add(chat)
    await session.flush()
    msg: PortalChatMessage | None = None
    if with_message:
        msg = PortalChatMessage(chat_id=chat.id, author_sub="admin-sub", body="hi", created_at=_now())
        session.add(msg)
        await session.flush()
    return chat, msg


@pytest.mark.asyncio
async def test_audit_helpers_zero_on_clean_db(sqlite_session: AsyncSession) -> None:
    assert await count_orphan_document_embeddings(sqlite_session) == 0
    assert await count_orphan_chat_message_embeddings(sqlite_session) == 0
    assert await count_orphan_chat_attachments(sqlite_session, min_age_hours=1) == 0
    assert await count_expired_trash_roots(sqlite_session) == 0
    assert await count_trash_document_roots(sqlite_session) == 0


@pytest.mark.asyncio
async def test_audit_detects_orphan_document_embedding(sqlite_session: AsyncSession) -> None:
    sqlite_session.add(_embedding(entity_type="document", entity_id="00000000-0000-0000-0000-000000000099"))
    await sqlite_session.commit()
    assert await count_orphan_document_embeddings(sqlite_session) == 1


@pytest.mark.asyncio
async def test_live_document_embedding_is_not_orphan(sqlite_session: AsyncSession) -> None:
    doc = _document(title="live")
    sqlite_session.add(doc)
    await sqlite_session.flush()
    sqlite_session.add(_embedding(entity_type="document", entity_id=str(doc.id)))
    await sqlite_session.commit()
    assert await count_orphan_document_embeddings(sqlite_session) == 0


@pytest.mark.asyncio
async def test_audit_detects_orphan_chat_message_embedding(sqlite_session: AsyncSession) -> None:
    sqlite_session.add(_embedding(entity_type="chat_message", entity_id="00000000-0000-0000-0000-000000000088"))
    await sqlite_session.commit()
    assert await count_orphan_chat_message_embeddings(sqlite_session) == 1


@pytest.mark.asyncio
async def test_live_chat_message_embedding_is_not_orphan(sqlite_session: AsyncSession) -> None:
    _chat, msg = await _chat_with_optional_message(sqlite_session, with_message=True)
    assert msg is not None
    sqlite_session.add(_embedding(entity_type="chat_message", entity_id=str(msg.id)))
    await sqlite_session.commit()
    assert await count_orphan_chat_message_embeddings(sqlite_session) == 0


@pytest.mark.asyncio
async def test_audit_detects_stale_orphan_attachment(sqlite_session: AsyncSession) -> None:
    chat, _ = await _chat_with_optional_message(sqlite_session, with_message=False)
    att = PortalChatAttachment(
        chat_id=chat.id,
        uploader_sub="admin-sub",
        original_filename="stale.bin",
        content_type="application/octet-stream",
        file_size=1,
        storage_key="audit-stale-orphan",
        message_id=None,
    )
    sqlite_session.add(att)
    await sqlite_session.flush()
    old = _now() - timedelta(hours=3)
    await sqlite_session.execute(
        update(PortalChatAttachment).where(PortalChatAttachment.id == att.id).values(created_at=old)
    )
    await sqlite_session.commit()
    assert await count_orphan_chat_attachments(sqlite_session, min_age_hours=1) == 1


@pytest.mark.asyncio
async def test_fresh_orphan_attachment_is_not_counted(sqlite_session: AsyncSession) -> None:
    chat, _ = await _chat_with_optional_message(sqlite_session, with_message=False)
    sqlite_session.add(
        PortalChatAttachment(
            chat_id=chat.id,
            uploader_sub="admin-sub",
            original_filename="fresh.bin",
            content_type="application/octet-stream",
            file_size=1,
            storage_key="audit-fresh-orphan",
            message_id=None,
        )
    )
    await sqlite_session.commit()
    assert await count_orphan_chat_attachments(sqlite_session, min_age_hours=1) == 0


@pytest.mark.asyncio
async def test_linked_old_attachment_is_not_orphan(sqlite_session: AsyncSession) -> None:
    chat, msg = await _chat_with_optional_message(sqlite_session, with_message=True)
    assert msg is not None
    att = PortalChatAttachment(
        chat_id=chat.id,
        uploader_sub="admin-sub",
        original_filename="linked.bin",
        content_type="application/octet-stream",
        file_size=1,
        storage_key="audit-linked",
        message_id=msg.id,
    )
    sqlite_session.add(att)
    await sqlite_session.flush()
    old = _now() - timedelta(hours=3)
    await sqlite_session.execute(
        update(PortalChatAttachment).where(PortalChatAttachment.id == att.id).values(created_at=old)
    )
    await sqlite_session.commit()
    assert await count_orphan_chat_attachments(sqlite_session, min_age_hours=1) == 0


@pytest.mark.asyncio
async def test_expired_trash_root_counts(sqlite_session: AsyncSession) -> None:
    expired = _now() - timedelta(days=DOCUMENT_TRASH_TTL_DAYS + 1)
    sqlite_session.add(_document(title="expired-root", deleted_at=expired))
    await sqlite_session.commit()
    assert await count_expired_trash_roots(sqlite_session) == 1
    assert await count_trash_document_roots(sqlite_session) == 1


@pytest.mark.asyncio
async def test_fresh_trash_root_is_not_expired(sqlite_session: AsyncSession) -> None:
    sqlite_session.add(_document(title="fresh-trash", deleted_at=_now()))
    await sqlite_session.commit()
    assert await count_expired_trash_roots(sqlite_session) == 0
    assert await count_trash_document_roots(sqlite_session) == 1


@pytest.mark.asyncio
async def test_deleted_child_with_live_parent_is_trash_root(sqlite_session: AsyncSession) -> None:
    """Прод: корень = parent NULL или родитель жив. Упрощённый parent IS NULL врёт."""
    parent = _document(title="live-parent")
    sqlite_session.add(parent)
    await sqlite_session.flush()
    expired = _now() - timedelta(days=DOCUMENT_TRASH_TTL_DAYS + 1)
    sqlite_session.add(_document(title="deleted-child", deleted_at=expired, parent_id=parent.id))
    await sqlite_session.commit()
    assert await count_trash_document_roots(sqlite_session) == 1
    assert await count_expired_trash_roots(sqlite_session) == 1


@pytest.mark.asyncio
async def test_deleted_child_under_deleted_parent_is_not_separate_root(sqlite_session: AsyncSession) -> None:
    expired = _now() - timedelta(days=DOCUMENT_TRASH_TTL_DAYS + 1)
    parent = _document(title="deleted-parent", deleted_at=expired)
    sqlite_session.add(parent)
    await sqlite_session.flush()
    sqlite_session.add(_document(title="nested-child", deleted_at=expired, parent_id=parent.id))
    await sqlite_session.commit()
    assert await count_trash_document_roots(sqlite_session) == 1
    assert await count_expired_trash_roots(sqlite_session) == 1
