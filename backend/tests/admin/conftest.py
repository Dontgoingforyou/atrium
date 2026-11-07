"""Фикстуры HTTP-клиента для контура SQLAdmin."""

from __future__ import annotations

from collections.abc import AsyncIterator

import pytest
from app.main import app
from httpx import ASGITransport, AsyncClient


@pytest.fixture
async def admin_http_client() -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test", follow_redirects=False) as ac:
        yield ac
