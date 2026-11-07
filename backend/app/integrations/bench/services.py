"""Выгрузка CSV бенча: service-токен вместо JWT пользователя."""

from __future__ import annotations

import logging

from app.core.config import Settings
from app.core.exceptions import ServiceUnavailableError, UnauthorizedError
from app.core.utils import hmac_secrets_equal
from app.integrations.bench._table import bench_rows_to_csv, parse_bench_table
from app.portal_documents.services.portal_document_queries import get_document
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


def require_bench_export_token(settings: Settings, token: str | None) -> None:
    """Проверить shared secret. Пустой секрет — 503, неверный — 401."""
    expected = settings.bench_export_service_token.strip()
    if not expected:
        raise ServiceUnavailableError("Не настроен BENCH_EXPORT_SERVICE_TOKEN")
    if not hmac_secrets_equal(token, expected):
        logger.warning("Отказ в доступе: неверный service token выгрузки бенча")
        raise UnauthorizedError("Неверный service token выгрузки бенча")


async def export_bench_csv(session: AsyncSession, settings: Settings) -> bytes:
    """Прочитать body документа из Settings и собрать CSV."""
    doc = await get_document(session, settings.bench_export_document_id)
    rows = parse_bench_table(doc.body)
    return bench_rows_to_csv(rows)
