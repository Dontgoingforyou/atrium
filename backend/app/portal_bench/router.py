from fastapi import APIRouter

from app.portal_bench.routes.dashboard import router as dashboard_router
from app.portal_bench.routes.export import router as export_router

router = APIRouter()
router.include_router(dashboard_router)
router.include_router(export_router)
