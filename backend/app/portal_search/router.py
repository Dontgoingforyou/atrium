from fastapi import APIRouter

from app.portal_search.routes.search import router as search_router

router = APIRouter()
router.include_router(search_router)
