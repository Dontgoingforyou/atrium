"""Маршрут выхода из SQLAdmin с возвратом на портал."""

from __future__ import annotations

from fastapi import APIRouter, status
from starlette.requests import Request
from starlette.responses import RedirectResponse

router = APIRouter(include_in_schema=False)


@router.post("/admin/exit-to-portal")
async def admin_exit_to_portal(request: Request) -> RedirectResponse:
    """Сбрасывает cookie-сессию админки и отправляет на корень SPA.

    POST — защита от logout CSRF: GET-ссылку с другого сайта браузер откроет
    автоматически (SameSite=Lax не блокирует), а POST требует явной формы.
    Дополнительно проверяем наличие admin_sub, чтобы анонимный POST не трогал сессию.
    """
    if not request.session.get("admin_sub"):
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    request.session.clear()
    return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
