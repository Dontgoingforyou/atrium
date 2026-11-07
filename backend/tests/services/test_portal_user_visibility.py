"""Правила скрытия людей в пикерах каталога."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from app.integrations.effective_admin.emails_check import EmailsCheckResult
from app.services.portal_user_visibility import (
    HIDDEN_DIRECTORY_EMAILS,
    hidden_emails_for_directory,
    is_explicitly_hidden_directory_email,
    is_hidden_test_account_email,
)
from tests.conftest import make_oidc_settings


@pytest.mark.parametrize(
    ("email", "hidden"),
    [
        ("test.managerau@example.com", True),
        ("Test.Outstaff@example.com", True),
        ("  test.managerau@example.com  ", True),
        ("user.two@example.com", False),
        ("testing.user@example.com", False),
        (None, False),
        ("", False),
    ],
)
def test_is_hidden_test_account_email(email: str | None, hidden: bool) -> None:
    assert is_hidden_test_account_email(email) is hidden


@pytest.mark.parametrize(
    ("email", "hidden"),
    [
        ("hidden.three@example.com", True),
        ("Hidden.Three@example.com", True),
        ("hidden.four@example.com", True),
        ("hidden.five@example.com", True),
        ("hidden.one@example.com", True),
        ("hidden.two@example.com", True),
        ("test.managerau@example.com", True),
        ("user.extra@example.com", False),
        (None, False),
    ],
)
def test_is_explicitly_hidden_directory_email(email: str | None, hidden: bool) -> None:
    assert is_explicitly_hidden_directory_email(email) is hidden


def test_hidden_directory_emails_lists_explicit_addresses() -> None:
    assert "hidden.three@example.com" in HIDDEN_DIRECTORY_EMAILS
    assert "hidden.four@example.com" in HIDDEN_DIRECTORY_EMAILS
    assert "hidden.one@example.com" in HIDDEN_DIRECTORY_EMAILS
    assert "hidden.two@example.com" in HIDDEN_DIRECTORY_EMAILS


@pytest.mark.asyncio
async def test_hidden_emails_always_hides_test_without_http() -> None:
    hidden = await hidden_emails_for_directory(
        None,
        [
            "test.managerau@example.com",
            "ivan@example.com",
            "hidden.three@example.com",
        ],
    )
    assert hidden == {"test.managerau@example.com", "hidden.three@example.com"}


@pytest.mark.asyncio
async def test_hidden_emails_adds_not_found_from_admin() -> None:
    settings = make_oidc_settings(
        effective_admin_base_url="https://ea.example",
        effective_admin_service_token="svc-token",
    )
    result = EmailsCheckResult(
        found=frozenset({"ivan@example.com"}),
        not_found=frozenset({"hidden.one@example.com"}),
    )
    with (
        patch("app.services.portal_user_visibility.get_settings", return_value=settings),
        patch(
            "app.services.portal_user_visibility.get_cached_email_active_bulk",
            new=AsyncMock(
                return_value={
                    "ivan@example.com": None,
                    "hidden.one@example.com": None,
                }
            ),
        ),
        patch("app.services.portal_user_visibility.set_cached_email_active_bulk", new=AsyncMock()),
        patch(
            "app.services.portal_user_visibility.EffectiveAdminEmailsClient.check_emails",
            new=AsyncMock(return_value=result),
        ),
    ):
        hidden = await hidden_emails_for_directory(
            AsyncMock(),
            [
                "ivan@example.com",
                "hidden.one@example.com",
                "test.outstaff@example.com",
            ],
        )
    assert hidden == {"hidden.one@example.com", "test.outstaff@example.com"}


@pytest.mark.asyncio
async def test_hidden_emails_fail_open_when_check_unavailable() -> None:
    settings = make_oidc_settings(
        effective_admin_base_url="https://ea.example",
        effective_admin_service_token="svc-token",
    )
    with (
        patch("app.services.portal_user_visibility.get_settings", return_value=settings),
        patch(
            "app.services.portal_user_visibility.get_cached_email_active_bulk",
            new=AsyncMock(return_value={"ivan@example.com": None}),
        ),
        patch(
            "app.services.portal_user_visibility.EffectiveAdminEmailsClient.check_emails",
            new=AsyncMock(return_value=None),
        ),
    ):
        hidden = await hidden_emails_for_directory(AsyncMock(), ["ivan@example.com"])
    assert hidden == set()
