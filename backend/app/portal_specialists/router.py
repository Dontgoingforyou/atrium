from fastapi import APIRouter

from app.portal_specialists.routes.board import router as board_router
from app.portal_specialists.routes.jira import router as jira_router
from app.portal_specialists.routes.specialist_board_pref import router as board_pref_router
from app.portal_specialists.routes.specialist_board_ws import router as board_ws_router
from app.portal_specialists.routes.specialist_detail import router as detail_router

router = APIRouter()
router.include_router(board_pref_router)
router.include_router(jira_router)
router.include_router(board_router)
router.include_router(detail_router)

# WS: тикет-авторизация; без Depends(require_non_developer) на уровне api_router.
ws_router = board_ws_router
