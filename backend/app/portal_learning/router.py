from __future__ import annotations

from fastapi import APIRouter

from app.portal_learning.routes import checklists, materials, quizzes

router = APIRouter(prefix="/portal")
router.include_router(materials.router)
router.include_router(checklists.router)
router.include_router(quizzes.router)
