import logging
import os
from collections.abc import AsyncGenerator

from sqlalchemy import event
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import get_settings

logger = logging.getLogger(__name__)

_s = get_settings()

engine = create_async_engine(
    _s.database_url,
    echo=False,
    pool_pre_ping=True,
    # SQLite (тесты) не поддерживает pool_size/max_overflow
    **(
        {}
        if "sqlite" in _s.database_url
        else {
            "pool_size": _s.db_pool_size,
            "max_overflow": _s.db_max_overflow,
        }
    ),
)


@event.listens_for(engine.sync_engine, "connect")
def _register_pgvector(dbapi_conn: object, _conn_record: object) -> None:
    """Регистрирует тип vector для pgvector в asyncpg-соединении.

    Asyncpg предоставляет метод run_sync; используем его для вызова async-регистратора.
    В тестах (SQLite) ошибка регистрации не логируется. На PostgreSQL сбой пишется в лог
    (семантический поиск с типом ``vector`` иначе может падать с неочевидной причиной).
    """
    try:
        from pgvector.asyncpg import register_vector  # type: ignore[import-untyped, unused-ignore]

        # asyncpg connection объект имеет метод run_sync для вызова async-функций
        if hasattr(dbapi_conn, "run_sync"):
            dbapi_conn.run_sync(register_vector)
    except Exception as exc:
        if "sqlite" not in (_s.database_url or ""):
            logger.warning(
                "Не удалось зарегистрировать тип vector (pgvector) для соединения asyncpg: %s",
                exc,
            )


async_session_factory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


def skip_background_tasks_using_global_engine() -> bool:
    """True во время выполнения pytest-теста.

    Интеграционные тесты подменяют ``get_db_session`` на SQLite in-memory, а фоновые
    задачи (FastAPI ``BackgroundTasks``), которые открывают ``async_session_factory``,
    продолжали бы ходить в «боевой» ``database_url`` (часто Postgres/asyncpg). Это даёт
    лишний трафик к БД и под pytest-asyncio (module-scoped loop + xdist) — нестабильные
    ``RuntimeError: ... attached to a different loop``.
    """
    return os.environ.get("PYTEST_CURRENT_TEST") is not None


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        yield session


async def dispose_engine() -> None:
    await engine.dispose()
