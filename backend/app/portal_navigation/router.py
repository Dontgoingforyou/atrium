from fastapi import APIRouter

from app.portal_navigation.routes.navigation import router as navigation_pages_router

portal_router = APIRouter()
portal_router.include_router(navigation_pages_router)

__all__ = ["portal_router"]
