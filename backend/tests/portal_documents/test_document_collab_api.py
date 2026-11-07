"""Collab ticket + internal authenticate/snapshot (CAS) для Hocuspocus."""

from __future__ import annotations

from collections.abc import AsyncIterator

import pytest
from app.api.deps import get_db_session
from app.api.deps_auth import get_current_user
from app.core.config import Settings
from app.main import app
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.testclient import TestClient

from tests.helpers.portal_test_users import user_portal_admin, user_portal_developer
from tests.portal_documents.conftest import override_dependency

_SERVICE = "test-collab-service-token"


@pytest.fixture
def collab_settings(patch_oidc_settings: Settings, monkeypatch: pytest.MonkeyPatch) -> Settings:
    monkeypatch.setattr(patch_oidc_settings, "document_collab_enabled", True)
    monkeypatch.setattr(patch_oidc_settings, "document_collab_service_token", _SERVICE)
    # Роут импортирует get_settings по имени — патчим модуль роутера, не только auth.
    monkeypatch.setattr(
        "app.portal_documents.routes.document_collab.get_settings",
        lambda: patch_oidc_settings,
    )
    return patch_oidc_settings


def test_collab_ticket_requires_manager(
    sqlite_session: AsyncSession,
    collab_settings: Settings,
) -> None:
    async def _db() -> AsyncIterator[AsyncSession]:
        yield sqlite_session

    with (
        override_dependency(get_db_session, _db),
        override_dependency(get_current_user, user_portal_developer),
    ):
        client = TestClient(app, raise_server_exceptions=False)
        r = client.post("/api/v1/portal/documents/00000000-0000-0000-0000-00000000aaaa/collab-ws-ticket")
        assert r.status_code == 403


def test_collab_ticket_authenticate_and_snapshot_cas(
    sqlite_session: AsyncSession,
    collab_settings: Settings,
) -> None:
    async def _db() -> AsyncIterator[AsyncSession]:
        yield sqlite_session

    with (
        override_dependency(get_db_session, _db),
        override_dependency(get_current_user, user_portal_admin),
    ):
        client = TestClient(app, raise_server_exceptions=False)
        created = client.post(
            "/api/v1/admin/portal-documents",
            json={"title": "Collab doc", "body": "<p>hi</p>", "tag_ids": []},
        )
        assert created.status_code == 201, created.text
        doc_id = created.json()["id"]
        version = created.json()["version"]

        ticket_r = client.post(f"/api/v1/portal/documents/{doc_id}/collab-ws-ticket")
        assert ticket_r.status_code == 201, ticket_r.text
        ticket = ticket_r.json()["ticket"]

        bad = client.post(
            "/api/v1/internal/document-collab/authenticate",
            json={"ticket": ticket},
            headers={"X-Collab-Service-Token": "wrong"},
        )
        assert bad.status_code == 401

        auth = client.post(
            "/api/v1/internal/document-collab/authenticate",
            json={"ticket": ticket},
            headers={"X-Collab-Service-Token": _SERVICE},
        )
        assert auth.status_code == 200, auth.text
        payload = auth.json()
        assert payload["document_id"] == doc_id
        assert payload["version"] == version
        assert payload["body"] == "<p>hi</p>"

        # Тикет одноразовый
        again = client.post(
            "/api/v1/internal/document-collab/authenticate",
            json={"ticket": ticket},
            headers={"X-Collab-Service-Token": _SERVICE},
        )
        assert again.status_code == 401

        snap = client.post(
            f"/api/v1/internal/document-collab/documents/{doc_id}/snapshot",
            json={
                "body": "<p>updated</p>",
                "expected_version": version,
                "actor_sub": "admin-sub",
                "actor_display_name": "Admin",
            },
            headers={"X-Collab-Service-Token": _SERVICE},
        )
        assert snap.status_code == 200, snap.text
        assert snap.json()["version"] == version + 1

        conflict = client.post(
            f"/api/v1/internal/document-collab/documents/{doc_id}/snapshot",
            json={
                "body": "<p>stale</p>",
                "expected_version": version,
                "actor_sub": "admin-sub",
            },
            headers={"X-Collab-Service-Token": _SERVICE},
        )
        assert conflict.status_code == 409
        assert conflict.json().get("code") == "conflict"


def test_collab_disabled_returns_503(
    sqlite_session: AsyncSession,
    patch_oidc_settings: Settings,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(patch_oidc_settings, "document_collab_enabled", False)
    monkeypatch.setattr(patch_oidc_settings, "document_collab_service_token", _SERVICE)
    monkeypatch.setattr(
        "app.portal_documents.routes.document_collab.get_settings",
        lambda: patch_oidc_settings,
    )

    async def _db() -> AsyncIterator[AsyncSession]:
        yield sqlite_session

    with (
        override_dependency(get_db_session, _db),
        override_dependency(get_current_user, user_portal_admin),
    ):
        client = TestClient(app, raise_server_exceptions=False)
        created = client.post(
            "/api/v1/admin/portal-documents",
            json={"title": "No collab", "body": None, "tag_ids": []},
        )
        assert created.status_code == 201
        doc_id = created.json()["id"]
        r = client.post(f"/api/v1/portal/documents/{doc_id}/collab-ws-ticket")
        assert r.status_code == 503
