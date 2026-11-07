from typing import Annotated

import httpx
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import HTTPConnection

from app.core.config import get_settings
from app.infrastructure.db.session import get_db_session

DbSession = Annotated[AsyncSession, Depends(get_db_session)]


async def get_http_client(conn: HTTPConnection) -> httpx.AsyncClient:
    """Возвращает singleton AsyncClient из lifespan (app.state).

    Параметр ``HTTPConnection`` — общий базовый тип для HTTP ``Request`` и ``WebSocket``,
    чтобы зависимость работала и в REST, и в WebSocket-апгрейде (см. глобальные Depends на роутерах).
    """
    client: httpx.AsyncClient | None = getattr(conn.app.state, "http_client", None)
    if client is None:
        # Fallback для тестов без lifespan
        client = httpx.AsyncClient(timeout=get_settings().http_client_timeout_seconds)
    return client


HttpClient = Annotated[httpx.AsyncClient, Depends(get_http_client)]
