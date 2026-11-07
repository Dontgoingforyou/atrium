from __future__ import annotations

from fastapi import APIRouter

from app.portal_telegram.routes.telegram import router as telegram_bind_router

router = APIRouter(prefix="/telegram", tags=["Telegram"])
router.include_router(telegram_bind_router)
