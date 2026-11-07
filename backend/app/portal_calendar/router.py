from fastapi import APIRouter

from app.api.deps_auth import NON_DEVELOPER_ROUTE_DEPENDENCIES
from app.portal_calendar.routes.calendar_ws import router as calendar_ws_router
from app.portal_calendar.routes.calendars import router as calendars_router
from app.portal_calendar.routes.events import router as events_router
from app.portal_calendar.routes.invites import router as invites_router

router = APIRouter(dependencies=NON_DEVELOPER_ROUTE_DEPENDENCIES)
router.include_router(calendars_router)
router.include_router(events_router)

# Invite accept — без NON_DEVELOPER (внешние гости по токену)
invites_standalone = APIRouter()
invites_standalone.include_router(invites_router)

# WS — тикеты; без глобальной NON_DEVELOPER на роутере (как task_board_ws)
ws_standalone = APIRouter()
ws_standalone.include_router(calendar_ws_router)
