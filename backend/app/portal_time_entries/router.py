from fastapi import APIRouter

from app.portal_time_entries.routes.time_entries import router as time_entries_router

router = APIRouter()
router.include_router(time_entries_router)
