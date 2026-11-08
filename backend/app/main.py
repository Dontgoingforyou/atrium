import asyncio
import logging
import sys
from collections.abc import AsyncIterator, Awaitable
from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import urlparse, urlunparse

import httpx
import redis.asyncio as aioredis
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqladmin import Admin
from starlette.middleware.sessions import SessionMiddleware
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

from app.admin.auth import KeycloakAdminAuth
from app.admin.exit_router import router as admin_exit_router
from app.admin.views.document_history import PortalDocumentHistoryAdmin, PortalDocumentTagAdmin
from app.admin.views.documents import PortalDocumentAdmin, PortalTagAdmin
from app.api.docs_router import router as docs_router
from app.api.exception_handlers import register_exception_handlers
from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.logging_config import configure_logging
from app.infrastructure.cache.token_cache import set_redis_client
from app.infrastructure.db.session import dispose_engine, engine
from app.infrastructure.storage.client import ensure_bucket_exists
from app.infrastructure.ws.inbox_manager import init_inbox_manager
from app.infrastructure.ws.managers import init_ws_managers
from app.jobs.bench_sheets_sync import run_bench_sheets_sync_loop
from app.jobs.calendar_facts import run_calendar_facts_loop
from app.jobs.calendar_reminders import run_calendar_reminders_loop
from app.jobs.chat_orphan_attachments_nightly import run_chat_orphan_attachment_purge_loop
from app.jobs.document_trash_nightly import run_document_trash_purge_loop
from app.jobs.task_due_reminders import run_task_due_reminders_loop
from app.middleware.rate_limit import ApiRateLimitMiddleware, AuthRateLimitMiddleware
from app.middleware.request_id import RequestIdMiddleware
from app.middleware.security_headers import SecurityHeadersMiddleware
from app.portal_calendar.admin import (
    PortalCalendarAdmin,
    PortalCalendarAttendeeAdmin,
    PortalCalendarEventAdmin,
    PortalCalendarEventOverrideAdmin,
    PortalCalendarInviteTokenAdmin,
    PortalCalendarMemberAdmin,
    PortalCalendarReminderAdmin,
    PortalCalendarReminderSentAdmin,
)
from app.portal_collab.admin import (
    PortalAgreementAdmin,
    PortalTaskAdmin,
    PortalTaskColumnAdmin,
    PortalTaskCommentAdmin,
    PortalTaskHistoryAdmin,
    PortalTaskReminderSentAdmin,
    PortalTimeEntryAdmin,
)
from app.portal_finance.admin import (
    PortalContractAdmin,
    PortalCounterpartyAdmin,
    PortalInvoiceAdmin,
    PortalPaymentAdmin,
    PortalProcurementRequestAdmin,
)
from app.portal_learning.admin import (
    PortalChecklistAdmin,
    PortalChecklistItemAdmin,
    PortalLearningMaterialAdmin,
    PortalQuizAdmin,
    PortalQuizAnswerAdmin,
    PortalQuizAttemptAdmin,
    PortalQuizQuestionAdmin,
    PortalUserChecklistAdmin,
)
from app.portal_mcp.server import McpMountSlash, build_mcp_app, mcp_session_lifespan
from app.portal_specialists.admin import (
    PortalSpecialistColumnAdmin,
    PortalSpecialistProfileAdmin,
    PortalSpecialistStatusAdmin,
)
from app.portal_telegram.bot.runner import init_telegram_bot, shutdown_telegram_bot
from app.portal_telegram.webhook import build_telegram_webhook_router
from app.services.demo_content import seed_demo_portal
from app.services.demo_vectors import vectorize_portal_if_local

logger = logging.getLogger(__name__)

_ADMIN_TEMPLATES_DIR = Path(__file__).parent / "admin" / "templates"
_ADMIN_STATIC_DIR = Path(__file__).parent / "admin" / "static"


def _mask_url_password(url: str) -> str:
    """Маскирует пароль в URL для безопасного логирования.

    При ошибке разбора не возвращает исходную строку — в ней мог быть пароль.
    """
    try:
        parsed = urlparse(url)
        if parsed.password:
            masked_netloc = parsed.hostname or ""
            if parsed.port:
                masked_netloc = f"{masked_netloc}:{parsed.port}"
            if parsed.username:
                masked_netloc = f"{parsed.username}:***@{masked_netloc}"
            else:
                masked_netloc = f":***@{masked_netloc}"
            return urlunparse(parsed._replace(netloc=masked_netloc))
        return url
    except Exception:
        logger.warning("Не удалось разобрать URL для маскирования пароля")
        return "***"


_INSECURE_MINIO_DEFAULTS = frozenset({"", "minioadmin"})
_JOB_SHUTDOWN_TIMEOUT_SEC = 15.0


async def _stop_background_job(
    stop_event: asyncio.Event | None,
    task: asyncio.Task[None] | None,
) -> None:
    """Остановка цикла job через Event; cancel только если итерация не уложилась в таймаут."""
    if stop_event is not None:
        stop_event.set()
    if task is None:
        return
    try:
        await asyncio.wait_for(task, timeout=_JOB_SHUTDOWN_TIMEOUT_SEC)
    except TimeoutError:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
    except asyncio.CancelledError:
        pass


def _reject_insecure_minio_defaults(settings: object) -> None:
    """Запретить дефолтные MinIO credentials вне debug/pytest."""
    import os  # noqa: PLC0415
    import sys  # noqa: PLC0415

    from app.core.config import Settings  # noqa: PLC0415

    if not isinstance(settings, Settings):
        return
    if settings.debug or "pytest" in sys.modules or bool(os.environ.get("TESTING")):
        return
    access = settings.minio_access_key.strip()
    secret = settings.minio_secret_key.strip()
    if access in _INSECURE_MINIO_DEFAULTS or secret in _INSECURE_MINIO_DEFAULTS:
        raise RuntimeError(
            "MINIO_ACCESS_KEY/MINIO_SECRET_KEY не заданы или равны небезопасным дефолтам "
            "(minioadmin). Задайте уникальные ключи в окружении перед запуском."
        )


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    s = get_settings()
    logger.info("Запуск приложения: %s", s.app_name)

    redis_client: aioredis.Redis | None = None
    redis_url = s.effective_redis_url()
    if redis_url:
        try:
            redis_client = aioredis.from_url(
                redis_url,
                encoding="utf-8",
                decode_responses=True,
                socket_connect_timeout=5,
                # socket_timeout намеренно не задаём: pub/sub listen() — долгоживущая
                # подписка без фиксированного таймаута; короткий timeout обрывает её.
            )
            ping = redis_client.ping()
            if isinstance(ping, Awaitable):
                await ping
            set_redis_client(redis_client)
            logger.info("Redis подключён: %s", _mask_url_password(redis_url))
        except Exception as exc:
            logger.warning("Redis недоступен, кэш токенов отключён: %s", exc)
            redis_client = None

    init_ws_managers(redis_client)
    init_inbox_manager(redis_client)
    tg_tasks = await init_telegram_bot(redis_client)

    try:
        ensure_bucket_exists(s.minio_bucket)
    except Exception as exc:
        logger.warning("MinIO недоступен при старте, бакет не создан: %s", exc)

    ep = (s.minio_endpoint or "").strip().lower()
    pub = (s.minio_public_endpoint or "").strip()
    if ep.startswith("minio") and not pub:
        logger.warning(
            "MINIO_PUBLIC_ENDPOINT не задан, presigned URL для вложений будут с внутренним хостом "
            "(%s) — браузеры пользователей не смогут их открыть. Задайте публичный хост в конфиге.",
            s.minio_endpoint,
        )

    trash_purge_stop: asyncio.Event | None = None
    trash_purge_task: asyncio.Task[None] | None = None
    if s.document_trash_purge_enabled:
        trash_purge_stop = asyncio.Event()
        trash_purge_task = asyncio.create_task(run_document_trash_purge_loop(trash_purge_stop, s))

    orphan_att_stop: asyncio.Event | None = None
    orphan_att_task: asyncio.Task[None] | None = None
    if s.chat_orphan_attachment_purge_enabled:
        orphan_att_stop = asyncio.Event()
        orphan_att_task = asyncio.create_task(run_chat_orphan_attachment_purge_loop(orphan_att_stop, s))

    calendar_facts_stop: asyncio.Event | None = None
    calendar_facts_task: asyncio.Task[None] | None = None
    if s.calendar_facts_enabled and s.calendar_kafka_bootstrap_servers.strip():
        calendar_facts_stop = asyncio.Event()
        calendar_facts_task = asyncio.create_task(run_calendar_facts_loop(calendar_facts_stop, s))

    calendar_reminders_stop: asyncio.Event | None = None
    calendar_reminders_task: asyncio.Task[None] | None = None
    if s.calendar_reminders_enabled:
        calendar_reminders_stop = asyncio.Event()
        calendar_reminders_task = asyncio.create_task(run_calendar_reminders_loop(calendar_reminders_stop, s))

    task_due_reminders_stop: asyncio.Event | None = None
    task_due_reminders_task: asyncio.Task[None] | None = None
    if s.task_due_reminders_enabled:
        task_due_reminders_stop = asyncio.Event()
        task_due_reminders_task = asyncio.create_task(run_task_due_reminders_loop(task_due_reminders_stop, s))

    bench_sync_stop: asyncio.Event | None = None
    bench_sync_task: asyncio.Task[None] | None = None
    if s.google_sheets_sync_enabled:
        bench_sync_stop = asyncio.Event()
        bench_sync_task = asyncio.create_task(run_bench_sheets_sync_loop(bench_sync_stop, s))

    if s.debug and "pytest" not in sys.modules:
        try:
            await seed_demo_portal()
        except Exception:
            logger.exception("Учебные данные не записаны")
        try:
            await vectorize_portal_if_local()
        except Exception:
            logger.exception("Векторы документов, задач и сообщений не посчитаны")

    async with httpx.AsyncClient(timeout=s.http_client_timeout_seconds, trust_env=False) as client:
        _app.state.http_client = client
        # Сессия MCP живёт в родителе: lifespan вложенного ASGI-приложения FastAPI не запускает.
        async with mcp_session_lifespan():
            yield

    logger.info("Остановка приложения")
    await _stop_background_job(calendar_facts_stop, calendar_facts_task)
    await _stop_background_job(calendar_reminders_stop, calendar_reminders_task)
    await _stop_background_job(task_due_reminders_stop, task_due_reminders_task)
    await _stop_background_job(bench_sync_stop, bench_sync_task)
    await _stop_background_job(trash_purge_stop, trash_purge_task)
    await _stop_background_job(orphan_att_stop, orphan_att_task)
    await shutdown_telegram_bot(tg_tasks)
    if redis_client is not None:
        set_redis_client(None)
        await redis_client.aclose()
    await dispose_engine()


def _setup_admin(application: FastAPI, session_secret: str) -> None:
    """Инициализирует SQLAdmin: аутентификация, вьюхи, кастомный шаблон входа."""
    auth_backend = KeycloakAdminAuth(secret_key=session_secret)
    admin = Admin(
        application,
        engine,
        authentication_backend=auth_backend,
        title="Atrium Admin",
        templates_dir=str(_ADMIN_TEMPLATES_DIR),
    )

    admin.add_view(PortalTagAdmin)
    admin.add_view(PortalDocumentAdmin)
    admin.add_view(PortalDocumentTagAdmin)
    admin.add_view(PortalDocumentHistoryAdmin)
    admin.add_view(PortalTaskAdmin)
    admin.add_view(PortalTaskHistoryAdmin)
    admin.add_view(PortalTaskCommentAdmin)
    admin.add_view(PortalTaskColumnAdmin)
    admin.add_view(PortalTaskReminderSentAdmin)
    admin.add_view(PortalTimeEntryAdmin)
    admin.add_view(PortalAgreementAdmin)
    admin.add_view(PortalCalendarAdmin)
    admin.add_view(PortalCalendarMemberAdmin)
    admin.add_view(PortalCalendarEventAdmin)
    admin.add_view(PortalCalendarAttendeeAdmin)
    admin.add_view(PortalCalendarEventOverrideAdmin)
    admin.add_view(PortalCalendarReminderAdmin)
    admin.add_view(PortalCalendarInviteTokenAdmin)
    admin.add_view(PortalCalendarReminderSentAdmin)
    admin.add_view(PortalCounterpartyAdmin)
    admin.add_view(PortalContractAdmin)
    admin.add_view(PortalInvoiceAdmin)
    admin.add_view(PortalPaymentAdmin)
    admin.add_view(PortalProcurementRequestAdmin)
    admin.add_view(PortalLearningMaterialAdmin)
    admin.add_view(PortalChecklistAdmin)
    admin.add_view(PortalChecklistItemAdmin)
    admin.add_view(PortalUserChecklistAdmin)
    admin.add_view(PortalQuizAdmin)
    admin.add_view(PortalQuizQuestionAdmin)
    admin.add_view(PortalQuizAnswerAdmin)
    admin.add_view(PortalQuizAttemptAdmin)
    admin.add_view(PortalSpecialistColumnAdmin)
    admin.add_view(PortalSpecialistStatusAdmin)
    admin.add_view(PortalSpecialistProfileAdmin)


def create_app() -> FastAPI:
    configure_logging()
    s = get_settings()

    session_secret = s.admin_session_secret.strip()
    if not session_secret:
        import os  # noqa: PLC0415
        import secrets  # noqa: PLC0415
        import sys  # noqa: PLC0415

        _is_testing = "pytest" in sys.modules or bool(os.environ.get("TESTING"))
        if s.debug or _is_testing:
            session_secret = secrets.token_hex(32)
            # Пишем в Settings, чтобы HMAC photo URL и SessionMiddleware делили один секрет.
            s.admin_session_secret = session_secret
            logger.warning(
                "ADMIN_SESSION_SECRET не задан — используется случайный эфемерный секрет. "
                "После перезапуска все admin-сессии сбросятся. "
                "Задайте ADMIN_SESSION_SECRET в .env для стабильных сессий."
            )
        else:
            raise RuntimeError(
                "ADMIN_SESSION_SECRET не задан. Задайте переменную окружения ADMIN_SESSION_SECRET перед запуском."
            )

    _reject_insecure_minio_defaults(s)

    application = FastAPI(
        title=s.app_name,
        lifespan=lifespan,
        openapi_tags=[
            {"name": "Служебное"},
            {"name": "Авторизация"},
            {"name": "Главная"},
            {"name": "Навигация"},
            {"name": "Избранное"},
            {"name": "Аккаунт"},
            {"name": "Теги"},
            {"name": "Чаты"},
            {"name": "Задачи"},
            {"name": "Договорённости"},
            {"name": "Уведомления"},
            {"name": "Документы"},
            {"name": "Портал · Календарь"},
            {"name": "Специалисты — доска"},
            {"name": "Специалисты — карточка"},
            {"name": "Специалисты — Jira"},
            {"name": "Таймшиты"},
            {"name": "Поиск"},
            {"name": "Финансы · Контрагенты"},
            {"name": "Финансы · Договоры"},
            {"name": "Финансы · Счета и акты"},
            {"name": "Финансы · Платежи"},
            {"name": "Финансы · Отчёты"},
            {"name": "Закупки · Заявки"},
            {"name": "Обучение · Материалы"},
            {"name": "Обучение · Чек-листы"},
            {"name": "Обучение · Тесты"},
            {"name": "Telegram"},
            {"name": "Администрирование"},
        ],
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )

    # Порядок важен (Starlette: последний add_middleware — внешний слой при входе запроса):
    # ApiRateLimit → AuthRateLimit → RequestId → SecurityHeaders → CORS → SessionMiddleware → ProxyHeaders (внешний).
    # ProxyHeaders обрабатывает X-Forwarded-Proto/For до выбора схемы; Session не самый внешний.
    application.add_middleware(ApiRateLimitMiddleware)
    application.add_middleware(AuthRateLimitMiddleware)
    application.add_middleware(RequestIdMiddleware)
    application.add_middleware(SecurityHeadersMiddleware, debug=s.debug)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=s.cors_origins_list,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "Accept", "X-Request-ID"],
    )
    application.add_middleware(
        SessionMiddleware,
        secret_key=session_secret,
        session_cookie="admin_session",
        https_only=not s.debug,
        same_site="lax",
        max_age=s.admin_session_max_age_seconds,
    )
    application.add_middleware(ProxyHeadersMiddleware, trusted_hosts=s.forwarded_allow_ips)

    register_exception_handlers(application)

    if s.telegram_bot_token.strip() and not s.telegram_use_polling:
        application.include_router(build_telegram_webhook_router())

    application.include_router(docs_router)
    application.include_router(api_router, prefix="/api/v1")
    application.mount("/api/v1/mcp", build_mcp_app())
    application.include_router(admin_exit_router)

    # Локальные vendor-бандлы для Swagger UI и ReDoc — избегаем зависимости от CDN.
    _vendor_dir = Path(__file__).parent / "static" / "vendor"
    if _vendor_dir.is_dir():
        application.mount("/vendor", StaticFiles(directory=str(_vendor_dir)), name="vendor")

    if _ADMIN_STATIC_DIR.is_dir():
        # Под /static/ — nginx уже проксирует на API (не SPA catch-all).
        application.mount(
            "/static/admin-brand",
            StaticFiles(directory=str(_ADMIN_STATIC_DIR)),
            name="admin_brand",
        )

    _setup_admin(application, session_secret)
    application.add_middleware(McpMountSlash)

    return application


app = create_app()
