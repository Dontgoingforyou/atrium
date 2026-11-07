"""Фикстуры для тестов WebSocket / тикетов."""

from __future__ import annotations

import app.infrastructure.ws.tickets as ws_tickets
import pytest


@pytest.fixture(autouse=True)
def _clear_ws_ticket_memory_store() -> None:
    ws_tickets._mem_store.clear()
    yield
    ws_tickets._mem_store.clear()
