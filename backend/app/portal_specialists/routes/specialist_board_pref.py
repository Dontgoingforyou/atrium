from __future__ import annotations

from fastapi import APIRouter

from app.api.deps import DbSession
from app.api.deps_auth import CurrentUser
from app.portal_specialists.schemas.board import SpecialistBoardPrefRead, SpecialistBoardPrefWrite
from app.portal_specialists.services import specialist_board_pref as pref_svc

router = APIRouter(prefix="/portal", tags=["Специалисты — доска"])


@router.get(
    "/me/specialist-board-pref",
    response_model=SpecialistBoardPrefRead,
    summary="Персональный порядок колонок канбана специалистов",
)
async def get_specialist_board_pref(
    user: CurrentUser,
    session: DbSession,
) -> SpecialistBoardPrefRead:
    return await pref_svc.get_specialist_board_pref(session, user)


@router.put(
    "/me/specialist-board-pref",
    response_model=SpecialistBoardPrefRead,
    summary="Сохранить персональный порядок колонок канбана специалистов",
)
async def put_specialist_board_pref(
    user: CurrentUser,
    body: SpecialistBoardPrefWrite,
    session: DbSession,
) -> SpecialistBoardPrefRead:
    return await pref_svc.put_specialist_board_pref(session, user, body)
