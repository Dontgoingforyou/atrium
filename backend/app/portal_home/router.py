from fastapi import APIRouter

from app.portal_home.routes.home import router as home_router

router = APIRouter()
router.include_router(home_router)
