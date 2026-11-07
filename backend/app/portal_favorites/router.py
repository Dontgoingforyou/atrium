from fastapi import APIRouter

from app.portal_favorites.routes.favorites import router as favorites_router

router = APIRouter()
router.include_router(favorites_router)
