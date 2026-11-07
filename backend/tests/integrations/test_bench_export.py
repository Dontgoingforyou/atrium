"""HTTP-контракт GET /api/v1/integrations/bench (service Bearer, не SSO)."""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator

import pytest
from app.api.deps import get_db_session
from app.core.config import Settings
from app.infrastructure.db.models.portal_document import PortalDocument
from app.integrations.bench.constants import CSV_COLUMNS, CSV_FILENAME, UTF8_BOM
from app.main import app
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from tests.portal_documents.conftest import assert_api_error, override_dependency

_TOKEN = "test-bench-export-token"
_DOC_ID = uuid.UUID("60629368-c9e8-492c-9def-67e3c4aa092c")
_TIPTAP_BODY = """
<table class="portal-rich-table">
  <tbody>
    <tr>
      <th>Имя</th><th>Опыт</th><th>Стек</th><th>Грейд</th>
      <th>CV</th><th>Локация</th><th>Статус</th>
    </tr>
    <tr>
      <td>Кирилл Б.</td><td>4.5</td><td>Python</td><td>Middle</td>
      <td></td><td>Москва</td><td>Доступен</td>
    </tr>
  </tbody>
</table>
"""


@pytest.fixture
def bench_settings(patch_oidc_settings: Settings, monkeypatch: pytest.MonkeyPatch) -> Settings:
    monkeypatch.setattr(patch_oidc_settings, "bench_export_service_token", _TOKEN)
    monkeypatch.setattr(patch_oidc_settings, "bench_export_document_id", _DOC_ID)
    monkeypatch.setattr("app.integrations.bench.routes.get_settings", lambda: patch_oidc_settings)
    monkeypatch.setattr("app.middleware.rate_limit.get_settings", lambda: patch_oidc_settings)
    return patch_oidc_settings


async def _client(session: AsyncSession) -> AsyncIterator[AsyncClient]:
    async def _db() -> AsyncIterator[AsyncSession]:
        yield session

    with override_dependency(get_db_session, _db):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac


async def _insert_bench_doc(session: AsyncSession, *, body: str | None) -> None:
    session.add(PortalDocument(id=_DOC_ID, title="Бенч", author_sub="admin-sub", body=body))
    await session.commit()


async def test_bench_export_unauthorized_without_token(
    sqlite_session: AsyncSession,
    bench_settings: Settings,
) -> None:
    async for client in _client(sqlite_session):
        r = await client.get("/api/v1/integrations/bench")
        assert_api_error(r, 401, "unauthorized")


async def test_bench_export_unauthorized_wrong_token(
    sqlite_session: AsyncSession,
    bench_settings: Settings,
) -> None:
    async for client in _client(sqlite_session):
        r = await client.get(
            "/api/v1/integrations/bench",
            headers={"Authorization": "Bearer wrong-token-xxx"},
        )
        assert_api_error(r, 401, "unauthorized")


async def test_bench_export_unavailable_when_secret_empty(
    sqlite_session: AsyncSession,
    bench_settings: Settings,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(bench_settings, "bench_export_service_token", "")
    async for client in _client(sqlite_session):
        r = await client.get(
            "/api/v1/integrations/bench",
            headers={"Authorization": f"Bearer {_TOKEN}"},
        )
        assert_api_error(r, 503, "service_unavailable")


async def test_bench_export_not_found_without_document(
    sqlite_session: AsyncSession,
    bench_settings: Settings,
) -> None:
    async for client in _client(sqlite_session):
        r = await client.get(
            "/api/v1/integrations/bench",
            headers={"Authorization": f"Bearer {_TOKEN}"},
        )
        assert_api_error(r, 404, "not_found")


async def test_bench_export_validation_without_table(
    sqlite_session: AsyncSession,
    bench_settings: Settings,
) -> None:
    await _insert_bench_doc(sqlite_session, body="<p>нет таблицы</p>")
    async for client in _client(sqlite_session):
        r = await client.get(
            "/api/v1/integrations/bench",
            headers={"Authorization": f"Bearer {_TOKEN}"},
        )
        assert_api_error(r, 422, "validation_error")


async def test_bench_export_csv_success(
    sqlite_session: AsyncSession,
    bench_settings: Settings,
) -> None:
    await _insert_bench_doc(sqlite_session, body=_TIPTAP_BODY)
    async for client in _client(sqlite_session):
        r = await client.get(
            "/api/v1/integrations/bench",
            headers={"Authorization": f"Bearer {_TOKEN}"},
        )
        assert r.status_code == 200, r.text
        assert r.headers["content-type"].startswith("text/csv")
        assert CSV_FILENAME in r.headers.get("content-disposition", "")
        assert "attachment" in r.headers.get("content-disposition", "")
        assert r.content.startswith(UTF8_BOM)
        text = r.content[len(UTF8_BOM) :].decode("utf-8")
        header = text.splitlines()[0]
        assert header.split(";") == list(CSV_COLUMNS)
        assert "Кирилл Б.;4.5;Python;Middle;;Москва;Доступен" in text.replace("\r\n", "\n")
