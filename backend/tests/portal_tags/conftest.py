"""Фикстуры и хелперы для тестов portal_tags."""

from __future__ import annotations

from httpx import Response

TAGS_API = "/api/v1/portal/tags"


def assert_api_error(response: Response, status: int, code: str) -> None:
    """Ошибка AppError: и HTTP-статус, и контрактный `code`."""
    assert response.status_code == status, response.text
    assert response.json()["code"] == code


def assert_pydantic_422(response: Response) -> None:
    assert response.status_code == 422, response.text
    assert "detail" in response.json()
