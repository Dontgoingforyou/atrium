from __future__ import annotations

import os

os.environ.setdefault("ADMIN_SESSION_SECRET", "dev-secret-change-me")

from collections.abc import AsyncIterator
from typing import Any

import app.infrastructure.db.models  # noqa: F401 — регистрация ORM-таблиц в metadata
import pytest
from app.api.deps import get_db_session
from app.api.deps_auth import get_current_user
from app.core.config import Settings, get_settings
from app.infrastructure.db.base import Base
from app.infrastructure.db.models.portal_user_profile import PortalUserProfile
from app.main import app
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from tests.helpers.portal_test_users import (
    user_outstaff_not_manager,
    user_portal_admin,
    user_portal_developer,
    user_portal_manager,
    user_portal_no_idp_groups,
    user_portal_procurement,
    user_portal_regular,
    user_portal_user_b,
)


@pytest.fixture(autouse=True)
def calendar_routes_stay_on_local_services(monkeypatch: pytest.MonkeyPatch) -> None:
    """Экранные ручки зовут микросервис. В тестах его подменяет местный календарь."""
    from tests.portal_calendar.local_gateway import local_remote

    monkeypatch.setattr("app.portal_calendar.routes.calendars.require_remote", local_remote)
    monkeypatch.setattr("app.portal_calendar.routes.events.require_remote", local_remote)


@pytest.fixture(autouse=True)
def clear_memory_rate_limit_windows() -> Any:
    from app.infrastructure.cache.rate_limit import _memory_windows

    _memory_windows.clear()
    yield
    _memory_windows.clear()


@pytest.fixture(autouse=True)
def clear_settings_cache() -> Any:
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


def make_oidc_settings(**kwargs: Any) -> Settings:
    """Настройки с включённым SSO для тестов."""
    data: dict[str, Any] = {
        "database_url": "sqlite+aiosqlite:///:memory:",
        "sso_client_id": "test-client",
        "sso_client_secret": "test-secret",
        "sso_client_id_5173": "",
        "sso_client_secret_5173": "",
        "sso_client_id_9088": "",
        "sso_client_secret_9088": "",
        "sso_client_id_stage": "",
        "sso_client_secret_stage": "",
        "sso_client_id_prod": "",
        "sso_client_secret_prod": "",
        "sso_service_url": "https://sso.example",
        "sso_api_prefix": "/api/",
        "sso_auth_page_path": "/auth",
        "sso_token_path": "auth/oauth2/token",
        "sso_allowed_redirect_uris": "http://localhost:5173/auth/callback",
        "sso_groups_claim": "groups",
        "api_mutation_rate_limit": 1_000_000,
        "api_mutation_ip_rate_limit": 1_000_000,
        "health_rate_limit": 1_000_000,
        "semantic_search_rate_limit": 1_000_000,
        "semantic_search_ip_rate_limit": 1_000_000,
        "bench_export_rate_limit": 1_000_000,
    }
    data.update(kwargs)
    return Settings(**data)


@pytest.fixture
def patch_oidc_settings(monkeypatch: pytest.MonkeyPatch) -> Settings:
    """Патчит get_settings в роутерах авторизации (импорт по ссылке на функцию)."""
    s = make_oidc_settings()
    monkeypatch.setattr("app.api.v1.routes.auth.get_settings", lambda: s)
    monkeypatch.setattr("app.api.v1.routes.auth_session.get_settings", lambda: s)
    monkeypatch.setattr("app.api.deps_auth.get_settings", lambda: s)
    return s


@pytest.fixture
async def sqlite_session() -> AsyncIterator[AsyncSession]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")

    @event.listens_for(engine.sync_engine, "connect")
    def _sqlite_enable_foreign_keys(dbapi_connection: object, _connection_record: object) -> None:
        cursor = dbapi_connection.cursor()  # type: ignore[union-attr]
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        for u in (
            user_portal_admin(),
            user_portal_regular(),
            user_portal_user_b(),
            user_portal_no_idp_groups(),
            user_portal_procurement(),
            user_portal_manager(),
            user_portal_developer(),
            user_outstaff_not_manager(),
        ):
            session.add(
                PortalUserProfile(
                    sub=u.sub,
                    email=u.email,
                    full_name=u.full_name,
                    username=u.username,
                    is_portal_admin=u.is_portal_admin,
                    portal_chat_allowed=u.sub != "dev-sub",
                )
            )
        await session.commit()
        yield session
    await engine.dispose()


def _pop_db_override() -> None:
    app.dependency_overrides.pop(get_db_session, None)


def _pop_db_and_user_overrides() -> None:
    app.dependency_overrides.pop(get_db_session, None)
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
async def client_sqlite_only(
    sqlite_session: AsyncSession,
    patch_oidc_settings: Settings,
) -> AsyncIterator[AsyncClient]:
    """API с SQLite для эндпоинтов, которым нужна БД без подмены пользователя."""

    async def _override_db() -> AsyncIterator[AsyncSession]:
        yield sqlite_session

    app.dependency_overrides[get_db_session] = _override_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    _pop_db_override()


# ---------------------------------------------------------------------------
# Интеграционные клиенты API (testing.mdc — общие фикстуры в conftest)
# ---------------------------------------------------------------------------


@pytest.fixture
async def client_admin(
    sqlite_session: AsyncSession,
    patch_oidc_settings: Settings,
) -> AsyncIterator[AsyncClient]:
    async def _db() -> AsyncIterator[AsyncSession]:
        yield sqlite_session

    app.dependency_overrides[get_db_session] = _db
    app.dependency_overrides[get_current_user] = user_portal_admin
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    _pop_db_and_user_overrides()


@pytest.fixture
async def client_user(
    sqlite_session: AsyncSession,
    patch_oidc_settings: Settings,
) -> AsyncIterator[AsyncClient]:
    async def _db() -> AsyncIterator[AsyncSession]:
        yield sqlite_session

    app.dependency_overrides[get_db_session] = _db
    app.dependency_overrides[get_current_user] = user_portal_regular
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    _pop_db_and_user_overrides()


@pytest.fixture
async def client_user_b(
    sqlite_session: AsyncSession,
    patch_oidc_settings: Settings,
) -> AsyncIterator[AsyncClient]:
    async def _db() -> AsyncIterator[AsyncSession]:
        yield sqlite_session

    app.dependency_overrides[get_db_session] = _db
    app.dependency_overrides[get_current_user] = user_portal_user_b
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    _pop_db_and_user_overrides()


@pytest.fixture
async def client_admin_session() -> AsyncIterator[AsyncClient]:
    """Клиент без подмены БД (только для эндпоинтов вроде admin-session)."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
async def client_developer(
    sqlite_session: AsyncSession,
    patch_oidc_settings: Settings,
) -> AsyncIterator[AsyncClient]:
    async def _db() -> AsyncIterator[AsyncSession]:
        yield sqlite_session

    app.dependency_overrides[get_db_session] = _db
    app.dependency_overrides[get_current_user] = user_portal_developer
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    _pop_db_and_user_overrides()


@pytest.fixture
async def client_manager(
    sqlite_session: AsyncSession,
    patch_oidc_settings: Settings,
) -> AsyncIterator[AsyncClient]:
    async def _db() -> AsyncIterator[AsyncSession]:
        yield sqlite_session

    app.dependency_overrides[get_db_session] = _db
    app.dependency_overrides[get_current_user] = user_portal_manager
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    _pop_db_and_user_overrides()


@pytest.fixture
async def client_no_idp(
    sqlite_session: AsyncSession,
    patch_oidc_settings: Settings,
) -> AsyncIterator[AsyncClient]:
    async def _db() -> AsyncIterator[AsyncSession]:
        yield sqlite_session

    app.dependency_overrides[get_db_session] = _db
    app.dependency_overrides[get_current_user] = user_portal_no_idp_groups
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    _pop_db_and_user_overrides()


@pytest.fixture
async def client_outstaff_not_manager(
    sqlite_session: AsyncSession,
    patch_oidc_settings: Settings,
) -> AsyncIterator[AsyncClient]:
    async def _db() -> AsyncIterator[AsyncSession]:
        yield sqlite_session

    app.dependency_overrides[get_db_session] = _db
    app.dependency_overrides[get_current_user] = user_outstaff_not_manager
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    _pop_db_and_user_overrides()
