"""Комментарии о специалисте: RBAC карточки и тред из comment_thread."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import NotFoundError
from app.core.optimistic_lock import compare_and_swap_row
from app.core.utils import now_utc as _now_utc
from app.infrastructure.db.models.portal_specialist_note import (
    PortalSpecialistNote,
    PortalSpecialistNoteMedia,
)
from app.infrastructure.db.models.portal_user_profile import PortalUserProfile
from app.portal_specialists.constants import SPECIALIST_NOTES_LIST_CAP
from app.portal_specialists.schemas.specialist_detail import (
    SpecialistNoteCreate,
    SpecialistNoteRead,
    SpecialistNoteUpdate,
)
from app.portal_specialists.services.board_shared import (
    SPECIALIST_CARD_READ_FORBIDDEN,
    ensure_specialist_card_visible,
    require_manager_or_admin,
    require_specialist_write_access,
)
from app.schemas.auth import UserPublic
from app.services import comment_thread as thread_svc
from app.services import rich_media as rich_media_svc

_NOTE_LOAD_OPTIONS = (
    selectinload(PortalSpecialistNote.comment_media),
    selectinload(PortalSpecialistNote.replies).selectinload(PortalSpecialistNote.comment_media),
)


async def list_specialist_notes(
    session: AsyncSession,
    user: UserPublic,
    specialist_sub: str,
) -> list[SpecialistNoteRead]:
    """Список комментариев по специалисту."""
    require_manager_or_admin(user, SPECIALIST_CARD_READ_FORBIDDEN)
    user_profile = await session.get(PortalUserProfile, specialist_sub)
    if user_profile is None:
        raise NotFoundError("Пользователь не найден")
    await ensure_specialist_card_visible(session, user_profile)

    notes = await thread_svc.list_top_level_comments(
        session,
        PortalSpecialistNote,
        "specialist_sub",
        specialist_sub,
        limit=SPECIALIST_NOTES_LIST_CAP,
        extra_options=[selectinload(PortalSpecialistNote.comment_media)],
    )
    return [_note_to_read(n) for n in notes]


async def create_specialist_note(
    session: AsyncSession,
    user: UserPublic,
    specialist_sub: str,
    data: SpecialistNoteCreate,
) -> SpecialistNoteRead:
    """Добавить комментарий о специалисте."""
    await require_specialist_write_access(session, user, specialist_sub)
    if await session.get(PortalUserProfile, specialist_sub) is None:
        raise NotFoundError("Пользователь не найден")
    if data.parent_id is not None:
        await thread_svc.validate_parent_comment(
            session,
            PortalSpecialistNote,
            data.parent_id,
            specialist_sub,
            "specialist_sub",
        )
    await thread_svc.validate_comment_media_ids(
        session,
        user,
        data.media_ids,
        host_fk_attr="specialist_sub",
        host_id=specialist_sub,
    )

    now = _now_utc()
    note = PortalSpecialistNote(
        specialist_sub=specialist_sub,
        author_sub=user.sub,
        parent_id=data.parent_id,
        body=data.body,
        mentions=data.mentions,
        created_at=now,
        updated_at=now,
    )
    session.add(note)
    await session.flush()
    for media_id in data.media_ids:
        session.add(PortalSpecialistNoteMedia(comment_id=note.id, media_id=media_id))
    await session.commit()
    return _note_to_read(await _reload_note(session, note.id))


async def update_specialist_note(
    session: AsyncSession,
    user: UserPublic,
    specialist_sub: str,
    note_id: uuid.UUID,
    data: SpecialistNoteUpdate,
) -> SpecialistNoteRead:
    """Редактировать комментарий."""
    note = await session.get(PortalSpecialistNote, note_id)
    if note is None or note.specialist_sub != specialist_sub:
        raise NotFoundError("Заметка не найдена")
    thread_svc.assert_author_or_admin(user, note, detail="Редактировать комментарий может только его автор")

    values: dict[str, object] = {"body": data.body, "updated_at": _now_utc()}
    if data.mentions is not None:
        values["mentions"] = data.mentions
    await compare_and_swap_row(
        session,
        PortalSpecialistNote,
        entity_id=note_id,
        expected_version=data.expected_version if data.expected_version is not None else note.version,
        values=values,
        conflict_message="Комментарий изменён другим пользователем",
    )
    await session.commit()
    return _note_to_read(await _reload_note(session, note_id))


async def delete_specialist_note(
    session: AsyncSession,
    user: UserPublic,
    specialist_sub: str,
    note_id: uuid.UUID,
) -> list[uuid.UUID]:
    """Удалить комментарий вместе с ответами под ним."""
    note = await session.get(PortalSpecialistNote, note_id)
    if note is None or note.specialist_sub != specialist_sub:
        raise NotFoundError("Заметка не найдена")
    thread_svc.assert_author_or_admin(user, note, detail="Удалять комментарий может только его автор или администратор")

    doomed = await _subtree_note_ids(session, specialist_sub, note_id)
    await session.delete(note)
    await session.commit()
    return doomed


async def _reload_note(session: AsyncSession, note_id: uuid.UUID) -> PortalSpecialistNote:
    stmt = select(PortalSpecialistNote).where(PortalSpecialistNote.id == note_id).options(*_NOTE_LOAD_OPTIONS)
    return (await session.execute(stmt)).scalar_one()


def _note_to_read(note: PortalSpecialistNote) -> SpecialistNoteRead:
    author_name: str | None = None
    if note.author_profile is not None:
        author_name = note.author_profile.full_name or note.author_profile.email or note.author_profile.username
    return SpecialistNoteRead(
        id=note.id,
        specialist_sub=note.specialist_sub,
        parent_id=note.parent_id,
        author_sub=note.author_sub,
        author_display_name=author_name,
        body=note.body,
        mentions=list(note.mentions or []),
        version=note.version,
        created_at=note.created_at,
        updated_at=note.updated_at,
        replies=[_note_to_read(reply) for reply in (note.replies or [])],
        media=[rich_media_svc.rich_media_to_read(item) for item in note.media],
    )


async def _subtree_note_ids(
    session: AsyncSession,
    specialist_sub: str,
    root_id: uuid.UUID,
) -> list[uuid.UUID]:
    rows = list(
        (
            await session.execute(
                select(PortalSpecialistNote.id, PortalSpecialistNote.parent_id).where(
                    PortalSpecialistNote.specialist_sub == specialist_sub,
                ),
            )
        ).all(),
    )
    children: dict[uuid.UUID, list[uuid.UUID]] = {}
    for note_id, parent_id in rows:
        if parent_id is not None:
            children.setdefault(parent_id, []).append(note_id)
    doomed = [root_id]
    pending = [root_id]
    seen = {root_id}
    while pending:
        current = pending.pop()
        for child_id in children.get(current, []):
            if child_id in seen:
                continue
            seen.add(child_id)
            doomed.append(child_id)
            pending.append(child_id)
    return doomed
