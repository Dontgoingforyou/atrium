"""Юнит-тесты username EA и сборки signed photo URL (HTTP — tests/api)."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from app.core.exceptions import ForbiddenError
from app.integrations.effective_admin.username import username_from_email
from app.services.user_photo_url import build_user_photo_proxy_url, verify_user_photo_signature


def test_username_from_email_ok() -> None:
    assert username_from_email("Ivan.Ivanov@Effective-Mobile.ru") == "ivan.ivanov"


def test_username_from_email_bad() -> None:
    assert username_from_email(None) is None
    assert username_from_email("no-at") is None
    assert username_from_email("../admin@corp.ru") is None
    assert username_from_email("a/b@corp.ru") is None
    assert username_from_email("..@corp.ru") is None
    assert username_from_email("user name@corp.ru") is None


def test_build_url_disabled() -> None:
    with patch("app.services.user_photo_url.get_settings") as gs:
        gs.return_value.effective_admin_photos_enabled = False
        assert build_user_photo_proxy_url(user_sub="s", email="a@b.ru") is None


def test_build_url_without_signing_secret_returns_none() -> None:
    with patch("app.services.user_photo_url.get_settings") as gs:
        gs.return_value.effective_admin_photos_enabled = True
        gs.return_value.admin_session_secret = ""
        gs.return_value.sso_client_secret_prod = ""
        gs.return_value.sso_client_secret = ""
        assert build_user_photo_proxy_url(user_sub="s", email="a@b.ru") is None


def test_verify_without_signing_secret_forbidden() -> None:
    with patch("app.services.user_photo_url.get_settings") as gs:
        gs.return_value.admin_session_secret = ""
        gs.return_value.sso_client_secret_prod = ""
        gs.return_value.sso_client_secret = ""
        with pytest.raises(ForbiddenError, match="секрет"):
            verify_user_photo_signature(user_sub="s", exp=1, sig="x")
