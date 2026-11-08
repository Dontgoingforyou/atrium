from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Query

from app.api.deps import DbSession
from app.api.deps_auth import CurrentUser
from app.portal_home.schemas.home import PortalHomeRead
from app.portal_home.services import home as portal_home_svc

router = APIRouter(prefix="/portal", tags=["Главная"])


@router.get(
    "/home",
    summary="Данные для главной страницы",
    description=(
        "Превью «мои задачи» и избранного, сводки по открытым/просроченным задачам. "
        "Глобальный поиск — отдельно: см. поле `search.get_path`. "
        "Администратор портала — поле `admin`: задачи команды за текущий месяц. "
        "Поле `manager` зарезервировано и всегда null (панель руководителя не реализована)."
    ),
    response_model=PortalHomeRead,
)
async def get_portal_home(
    user: CurrentUser,
    db: DbSession,
    assignee_sub: Annotated[
        str | None,
        Query(max_length=255, description="Drill-down: sub исполнителя (только задачи)"),
    ] = None,
) -> PortalHomeRead:
    return await portal_home_svc.build_portal_home(db, user, assignee_sub=assignee_sub)
