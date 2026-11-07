"""HTTP: сервисная выгрузка бенча для RAG (Bearer, не SSO JWT)."""

from __future__ import annotations

from app.api.deps import DbSession
from app.core.config import get_settings
from app.integrations.bench.constants import CSV_CONTENT_TYPE, CSV_FILENAME
from app.integrations.bench.services import export_bench_csv, require_bench_export_token
from fastapi import APIRouter, Header
from fastapi.responses import Response

router = APIRouter(prefix="/integrations", tags=["Интеграции — бенч RAG"])


def _bearer_token(authorization: str | None) -> str | None:
    if authorization is None:
        return None
    scheme, _, value = authorization.partition(" ")
    if scheme.lower() != "bearer" or not value.strip():
        return None
    return value.strip()


@router.get(
    "/bench",
    summary="Выгрузка актуального бенча для сценария RAG",
    description=(
        "Read-only CSV из HTML-таблицы документа «Бенч». "
        "Авторизация — service token в Authorization: Bearer, не JWT пользователя. "
        "Идентификатор документа берётся только из настроек сервера."
    ),
)
async def get_bench_export(
    db: DbSession,
    authorization: str | None = Header(default=None),
) -> Response:
    settings = get_settings()
    require_bench_export_token(settings, _bearer_token(authorization))
    payload = await export_bench_csv(db, settings)
    return Response(
        content=payload,
        media_type=CSV_CONTENT_TYPE,
        headers={"Content-Disposition": f'attachment; filename="{CSV_FILENAME}"'},
    )
