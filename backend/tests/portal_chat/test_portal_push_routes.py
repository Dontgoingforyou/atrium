from __future__ import annotations

from unittest.mock import patch

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_vapid_public_key_404_when_not_configured(client_admin: AsyncClient) -> None:
    with patch("app.portal_chat.routes.push.get_settings") as gs:
        m = gs.return_value
        m.vapid_public_key = ""
        r = await client_admin.get("/api/v1/portal/push/vapid-public-key")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_vapid_public_key_ok(client_admin: AsyncClient) -> None:
    with patch("app.portal_chat.routes.push.get_settings") as gs:
        m = gs.return_value
        m.vapid_public_key = "BHxTestKeyBase64UrlEncodedExampleValue"
        r = await client_admin.get("/api/v1/portal/push/vapid-public-key")
    assert r.status_code == 200
    assert r.json()["public_key"] == "BHxTestKeyBase64UrlEncodedExampleValue"


@pytest.mark.asyncio
async def test_push_subscribe_persists(client_admin: AsyncClient) -> None:
    body = {
        "endpoint": "https://push.example.test/endpoint-unique-1",
        "keys": {"p256dh": "dGVzdA", "auth": "dGVzdDI"},
    }
    r = await client_admin.post("/api/v1/portal/push/subscribe", json=body)
    assert r.status_code == 204


@pytest.mark.asyncio
async def test_push_unsubscribe(client_admin: AsyncClient) -> None:
    body = {
        "endpoint": "https://push.example.test/endpoint-unique-2",
        "keys": {"p256dh": "dGVzdA", "auth": "dGVzdDI"},
    }
    await client_admin.post("/api/v1/portal/push/subscribe", json=body)
    r = await client_admin.post("/api/v1/portal/push/unsubscribe", json={"endpoint": body["endpoint"]})
    assert r.status_code == 204
