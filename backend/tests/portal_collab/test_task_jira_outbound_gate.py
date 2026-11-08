"""Тесты gate outbound Jira задач."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from app.core.config import Settings


def test_jira_tasks_outbound_requires_flag_and_jira() -> None:
    s = Settings(
        jira_base_url="https://jira.example",
        jira_personal_access_token="tok",
        jira_tasks_sync_enabled=False,
    )
    assert s.jira_enabled is True
    assert s.jira_tasks_outbound_enabled is False

    s2 = Settings(
        jira_base_url="https://jira.example",
        jira_personal_access_token="tok",
        jira_tasks_sync_enabled=True,
        jira_tasks_project_key="TASKS",
    )
    assert s2.jira_tasks_outbound_enabled is True

    s3 = Settings(jira_tasks_sync_enabled=True, jira_base_url="", jira_personal_access_token="")
    assert s3.jira_tasks_outbound_enabled is False


@pytest.mark.asyncio
async def test_push_generic_error_for_unexpected_exception(monkeypatch: pytest.MonkeyPatch) -> None:
    from unittest.mock import AsyncMock
    from uuid import uuid4

    from app.core.exceptions import ServiceUnavailableError
    from app.portal_collab.services import task_jira_outbound as mod

    task_id = uuid4()
    task = MagicMock()
    task.id = task_id
    task.title = "T"
    task.description = None
    task.priority = "medium"
    task.parent_task_id = None
    task.jira_issue_key = None
    task.due_at = None
    task.number = 1

    exec_result = MagicMock()
    exec_result.scalar_one_or_none.return_value = task
    exec_result.scalars.return_value.all.return_value = []
    session = MagicMock()
    session.get = AsyncMock(return_value=task)
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.execute = AsyncMock(return_value=exec_result)
    session.get_bind.return_value.dialect.name = "sqlite"

    monkeypatch.setattr(
        mod,
        "get_settings",
        lambda: Settings(
            jira_base_url="https://jira.example",
            jira_personal_access_token="tok",
            jira_tasks_sync_enabled=True,
        ),
    )

    class _Boom(mod.JiraWriteClient):  # type: ignore[misc]
        def __init__(self, *args: object, **kwargs: object) -> None:
            pass

        async def find_user_by_email(self, email: str) -> None:
            return None

        async def create_issue(self, fields: dict) -> dict:
            raise RuntimeError("internal boom /secret")

    monkeypatch.setattr(mod, "JiraWriteClient", _Boom)
    monkeypatch.setattr(mod, "_assignee_emails", AsyncMock(return_value=[]))
    monkeypatch.setattr(mod, "_build_description", lambda task, settings: "d")

    await mod.push_task_to_jira(session, MagicMock(), task_id)
    assert task.jira_sync_error == "Jira недоступна"

    class _AppBoom(mod.JiraWriteClient):  # type: ignore[misc]
        def __init__(self, *args: object, **kwargs: object) -> None:
            pass

        async def find_user_by_email(self, email: str) -> None:
            return None

        async def create_issue(self, fields: dict) -> dict:
            raise ServiceUnavailableError("Jira не приняла создание задачи")

    monkeypatch.setattr(mod, "JiraWriteClient", _AppBoom)
    await mod.push_task_to_jira(session, MagicMock(), task_id)
    assert task.jira_sync_error == "Jira не приняла создание задачи"


@pytest.mark.asyncio
async def test_push_noop_when_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.portal_collab.services import task_jira_outbound as mod

    monkeypatch.setattr(
        mod,
        "get_settings",
        lambda: Settings(jira_tasks_sync_enabled=False),
    )
    session = MagicMock()
    http = MagicMock()
    await mod.push_task_to_jira(session, http, __import__("uuid").uuid4())
    session.get.assert_not_called()
