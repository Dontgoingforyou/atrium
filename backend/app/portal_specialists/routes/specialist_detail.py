from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, File, Path, UploadFile, status

from app.api.deps import DbSession
from app.api.deps_auth import CurrentUser, PortalAdminUser
from app.core.config import get_settings
from app.core.portal_search_constants import (
    PORTAL_SEARCH_ENTITY_TYPE_SPECIALIST,
    PORTAL_SEARCH_ENTITY_TYPE_SPECIALIST_NOTE,
)
from app.portal_search.services import embedding as emb_svc
from app.portal_search.services import entity_text as txt
from app.portal_specialists.schemas.specialist_detail import (
    SpecialistLinkCreate,
    SpecialistLinkRead,
    SpecialistNoteCreate,
    SpecialistNoteRead,
    SpecialistNoteUpdate,
    SpecialistProfileRead,
    SpecialistProfileUpdate,
)
from app.portal_specialists.services import specialist_detail as svc
from app.portal_specialists.services import specialist_note as note_svc
from app.schemas.rich_media import RichMediaRead
from app.services import rich_media as rich_media_svc
from app.services.file_upload_validation import open_upload_stream

router = APIRouter(prefix="/portal/specialists", tags=["Специалисты — карточка"])

SpecialistSubPath = Annotated[str, Path(description="sub специалиста в Keycloak")]
NoteIdPath = Annotated[uuid.UUID, Path(description="UUID заметки")]
LinkIdPath = Annotated[uuid.UUID, Path(description="UUID ссылки")]


# ---------------------------------------------------------------------------
# Профиль
# ---------------------------------------------------------------------------


@router.get(
    "/{specialist_sub}/profile",
    response_model=SpecialistProfileRead,
    summary="Профиль специалиста (менеджер или admin)",
)
async def get_specialist_profile(
    specialist_sub: SpecialistSubPath,
    user: CurrentUser,
    session: DbSession,
) -> SpecialistProfileRead:
    return await svc.get_specialist_profile(session, user, specialist_sub)


@router.patch(
    "/{specialist_sub}/profile",
    response_model=SpecialistProfileRead,
    summary="Обновить профиль специалиста (закреплённый менеджер или admin)",
)
async def patch_specialist_profile(
    specialist_sub: SpecialistSubPath,
    data: SpecialistProfileUpdate,
    user: CurrentUser,
    session: DbSession,
    bg: BackgroundTasks,
) -> SpecialistProfileRead:
    result = await svc.update_specialist_profile(session, user, specialist_sub, data)
    bg.add_task(
        emb_svc.upsert_embedding_bg,
        PORTAL_SEARCH_ENTITY_TYPE_SPECIALIST,
        specialist_sub,
        txt.specialist_to_text(result.full_name, result.email, result.location, result.telegram),
        txt.specialist_meta(specialist_sub),
    )
    return result


@router.delete(
    "/{specialist_sub}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Удалить специалиста из портала (администратор)",
    description=(
        "Удаляет portal_user_profile и связанные данные (доска, профиль, ссылки, заметки). "
        "Учётка Keycloak сохраняется; при повторном входе профиль создаётся заново."
    ),
)
async def purge_specialist(
    specialist_sub: SpecialistSubPath,
    user: PortalAdminUser,
    session: DbSession,
    bg: BackgroundTasks,
) -> None:
    note_ids = await svc.purge_specialist_from_portal(session, user, specialist_sub)
    bg.add_task(
        emb_svc.delete_embedding_bg,
        PORTAL_SEARCH_ENTITY_TYPE_SPECIALIST,
        specialist_sub,
    )
    for note_id in note_ids:
        bg.add_task(
            emb_svc.delete_embedding_bg,
            PORTAL_SEARCH_ENTITY_TYPE_SPECIALIST_NOTE,
            str(note_id),
        )


# ---------------------------------------------------------------------------
# Ссылки
# ---------------------------------------------------------------------------


@router.get(
    "/{specialist_sub}/links",
    response_model=list[SpecialistLinkRead],
    summary="Список ссылок специалиста",
    # Малый набор (CV + ручные); SQL LIMIT в list_specialist_links.
)
async def list_specialist_links(
    specialist_sub: SpecialistSubPath,
    user: CurrentUser,
    session: DbSession,
) -> list[SpecialistLinkRead]:
    return await svc.list_specialist_links(session, user, specialist_sub)


@router.post(
    "/{specialist_sub}/links",
    response_model=SpecialistLinkRead,
    status_code=status.HTTP_201_CREATED,
    summary="Добавить ссылку специалисту",
)
async def create_specialist_link(
    specialist_sub: SpecialistSubPath,
    data: SpecialistLinkCreate,
    user: CurrentUser,
    session: DbSession,
) -> SpecialistLinkRead:
    return await svc.create_specialist_link(session, user, specialist_sub, data)


@router.delete(
    "/{specialist_sub}/links/{link_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Удалить ссылку специалиста",
)
async def delete_specialist_link(
    specialist_sub: SpecialistSubPath,
    link_id: LinkIdPath,
    user: CurrentUser,
    session: DbSession,
) -> None:
    await svc.delete_specialist_link(session, user, specialist_sub, link_id)


# ---------------------------------------------------------------------------
# Заметки
# ---------------------------------------------------------------------------


@router.get(
    "/{specialist_sub}/notes",
    response_model=list[SpecialistNoteRead],
    summary="Список заметок о специалисте",
    # Контракт SPA — list[T]. Лимит режет корни треда в list_specialist_notes.
)
async def list_specialist_notes(
    specialist_sub: SpecialistSubPath,
    user: CurrentUser,
    session: DbSession,
) -> list[SpecialistNoteRead]:
    return await note_svc.list_specialist_notes(session, user, specialist_sub)


@router.post(
    "/{specialist_sub}/notes",
    response_model=SpecialistNoteRead,
    status_code=status.HTTP_201_CREATED,
    summary="Добавить заметку о специалисте",
)
async def create_specialist_note(
    specialist_sub: SpecialistSubPath,
    data: SpecialistNoteCreate,
    user: CurrentUser,
    session: DbSession,
    bg: BackgroundTasks,
) -> SpecialistNoteRead:
    result = await note_svc.create_specialist_note(session, user, specialist_sub, data)
    bg.add_task(
        emb_svc.upsert_embedding_bg,
        PORTAL_SEARCH_ENTITY_TYPE_SPECIALIST_NOTE,
        str(result.id),
        txt.specialist_note_to_text(result.body),
        txt.specialist_note_meta(specialist_sub, result.author_sub),
    )
    return result


@router.post(
    "/{specialist_sub}/notes/rich-media",
    response_model=RichMediaRead,
    status_code=status.HTTP_201_CREATED,
    summary="Загрузить изображение для комментария о специалисте",
)
async def upload_specialist_note_rich_media(
    specialist_sub: SpecialistSubPath,
    user: CurrentUser,
    session: DbSession,
    file: UploadFile = File(...),
) -> RichMediaRead:
    async with open_upload_stream(file, get_settings().attachment_max_size_bytes) as (file_data, file_size):
        media = await rich_media_svc.upload_specialist_rich_media(
            session,
            user,
            specialist_sub,
            file_data=file_data,
            file_size=file_size,
            content_type=file.content_type or "application/octet-stream",
            original_filename=file.filename or "image",
        )
    return rich_media_svc.rich_media_to_read(media)


@router.patch(
    "/{specialist_sub}/notes/{note_id}",
    response_model=SpecialistNoteRead,
    summary="Редактировать заметку о специалисте",
)
async def update_specialist_note(
    specialist_sub: SpecialistSubPath,
    note_id: NoteIdPath,
    data: SpecialistNoteUpdate,
    user: CurrentUser,
    session: DbSession,
    bg: BackgroundTasks,
) -> SpecialistNoteRead:
    result = await note_svc.update_specialist_note(session, user, specialist_sub, note_id, data)
    bg.add_task(
        emb_svc.upsert_embedding_bg,
        PORTAL_SEARCH_ENTITY_TYPE_SPECIALIST_NOTE,
        str(result.id),
        txt.specialist_note_to_text(result.body),
        txt.specialist_note_meta(result.specialist_sub, result.author_sub),
    )
    return result


@router.delete(
    "/{specialist_sub}/notes/{note_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Удалить заметку о специалисте",
)
async def delete_specialist_note(
    specialist_sub: SpecialistSubPath,
    note_id: NoteIdPath,
    user: CurrentUser,
    session: DbSession,
    bg: BackgroundTasks,
) -> None:
    doomed = await note_svc.delete_specialist_note(session, user, specialist_sub, note_id)
    for doomed_id in doomed:
        bg.add_task(
            emb_svc.delete_embedding_bg,
            PORTAL_SEARCH_ENTITY_TYPE_SPECIALIST_NOTE,
            str(doomed_id),
        )
