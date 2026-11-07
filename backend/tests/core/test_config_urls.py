"""Сборка URL из Settings (SSO, CORS, Redis)."""

from __future__ import annotations

from app.core.config import Settings


def test_cors_origins_list_empty_and_split() -> None:
    s = Settings(database_url="sqlite:///:memory:", cors_origins="")
    assert s.cors_origins_list == []

    s2 = Settings(database_url="sqlite:///:memory:", cors_origins=" http://a , http://b ")
    assert s2.cors_origins_list == ["http://a", "http://b"]


def test_sso_redirect_uris_list() -> None:
    s = Settings(
        database_url="sqlite:///:memory:",
        sso_allowed_redirect_uris=" http://x , http://y ",
    )
    assert s.sso_redirect_uris_list == ["http://x", "http://y"]


def test_sso_authorization_entry_url_empty_service() -> None:
    s = Settings(database_url="sqlite:///:memory:", sso_service_url="")
    assert s.sso_authorization_entry_url() == ""


def test_sso_authorization_entry_url_builds() -> None:
    s = Settings(
        database_url="sqlite:///:memory:",
        sso_service_url="https://gw.example",
        sso_auth_page_path="auth",
    )
    assert s.sso_authorization_entry_url() == "https://gw.example/auth"


def test_sso_authorization_entry_url_normalizes_path() -> None:
    s = Settings(
        database_url="sqlite:///:memory:",
        sso_service_url="https://gw.example/",
        sso_auth_page_path="/custom",
    )
    assert s.sso_authorization_entry_url() == "https://gw.example/custom"


def test_sso_token_and_refresh_and_userinfo_urls() -> None:
    s = Settings(
        database_url="sqlite:///:memory:",
        sso_service_url="https://gw.example",
        sso_api_prefix="api/",
        sso_token_path="auth/oauth2/token",
        sso_refresh_path="auth/refresh",
        sso_userinfo_path="auth/me",
    )
    assert s.sso_token_endpoint_url() == "https://gw.example/api/auth/oauth2/token"
    assert s.sso_refresh_endpoint_url() == "https://gw.example/api/auth/refresh"
    assert s.sso_userinfo_url() == "https://gw.example/api/auth/me"


def test_sso_login_and_logout_urls() -> None:
    s = Settings(
        database_url="sqlite:///:memory:",
        sso_service_url="https://gw.example",
        sso_api_prefix="api/",
        sso_login_path="auth/login",
        sso_logout_path="auth/logout",
    )
    assert s.sso_login_endpoint_url() == "https://gw.example/api/auth/login"
    assert s.sso_logout_endpoint_url() == "https://gw.example/api/auth/logout"


def test_sso_login_and_logout_urls_use_defaults_when_path_empty() -> None:
    s = Settings(
        database_url="sqlite:///:memory:",
        sso_service_url="https://gw.example",
        sso_api_prefix="api/",
        sso_login_path="",
        sso_logout_path="",
    )
    assert s.sso_login_endpoint_url() == "https://gw.example/api/auth/login"
    assert s.sso_logout_endpoint_url() == "https://gw.example/api/auth/logout"


def test_sso_token_endpoint_prefix_without_slash() -> None:
    s = Settings(
        database_url="sqlite:///:memory:",
        sso_service_url="https://gw.example",
        sso_api_prefix="api",
        sso_token_path="/auth/oauth2/token",
    )
    assert "/api/" in s.sso_token_endpoint_url()


def test_sso_urls_empty_when_no_service_url() -> None:
    s = Settings(
        database_url="sqlite:///:memory:",
        sso_service_url="",
        sso_api_prefix="/api/",
        sso_token_path="t",
    )
    assert s.sso_token_endpoint_url() == ""
    assert s.sso_refresh_endpoint_url() == ""
    assert s.sso_userinfo_url() == ""
    assert s.sso_login_endpoint_url() == ""
    assert s.sso_logout_endpoint_url() == ""


def test_sso_disabled_detail_messages() -> None:
    s1 = Settings(
        database_url="sqlite:///:memory:",
        sso_client_id="",
        sso_client_secret="",
        sso_service_url="https://x",
    )
    assert "client_id" in s1.sso_disabled_detail

    s2 = Settings(
        database_url="sqlite:///:memory:",
        sso_client_id="c",
        sso_client_secret="s",
        sso_service_url="",
    )
    assert "SSO_SERVICE_URL" in s2.sso_disabled_detail


def test_effective_redis_url_injects_password() -> None:
    s = Settings(
        database_url="sqlite:///:memory:",
        redis_url="redis://redis:6379/0",
        redis_password="s3cret!",
    )
    assert s.effective_redis_url() == "redis://:s3cret%21@redis:6379/0"
