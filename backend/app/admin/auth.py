from __future__ import annotations

import logging

from sqladmin.authentication import AuthenticationBackend
from starlette.requests import Request

logger = logging.getLogger(__name__)


class KeycloakAdminAuth(AuthenticationBackend):
    """AuthenticationBackend для SQLAdmin: cookie-сессия после входа в портал.

    Пользователь сначала входит в SPA (единый OAuth PKCE и один client_id в IdP).
    Ссылка «Панель администратора» вызывает POST /api/v1/auth/admin-session с Bearer:
    бэкенд проверяет группу atrium_role_admin и записывает admin_sub в сессию.
    Страница /admin/login предлагает перейти на портал для входа.

    SessionMiddleware — в главном приложении (единый источник сессии).
    """

    def __init__(self, secret_key: str) -> None:
        super().__init__(secret_key=secret_key)
        # Убираем SessionMiddleware из admin sub-app: сессия управляется
        # SessionMiddleware главного приложения и прокидывается через scope.
        self.middlewares = []

    async def login(self, request: Request) -> bool:
        # Форма username/password не используется — вход только через SSO.
        return False

    async def logout(self, request: Request) -> bool:
        request.session.clear()
        return True

    async def authenticate(self, request: Request) -> bool:
        admin_sub = request.session.get("admin_sub")
        if not admin_sub:
            logger.warning("Отказ в доступе к /admin: нет активной admin-сессии")
            return False
        if not await self._profile_is_portal_admin(str(admin_sub)):
            logger.warning(
                "Отказ в доступе к /admin: user_sub=%s больше не portal_admin",
                admin_sub,
            )
            request.session.clear()
            return False
        return True

    async def _profile_is_portal_admin(self, admin_sub: str) -> bool:
        """Сверить кэш ``is_portal_admin`` в профиле; снятие роли в IdP закрывает /admin до logout."""
        from app.infrastructure.db.models.portal_user_profile import PortalUserProfile
        from app.infrastructure.db.session import async_session_factory

        try:
            async with async_session_factory() as session:
                profile = await session.get(PortalUserProfile, admin_sub)
        except Exception:
            logger.exception("SQLAdmin: не удалось проверить профиль admin_sub=%s", admin_sub)
            return False
        return profile is not None and profile.is_portal_admin
