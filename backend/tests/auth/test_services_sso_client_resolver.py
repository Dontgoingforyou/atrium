"""Unit-тесты резолва SSO client_id/secret по redirect_uri и client_id."""

from __future__ import annotations

import pytest
from app.core.config import Settings
from app.services.sso.client_resolver import (
    SsoCredentialsNotFoundError,
    resolve_sso_credentials_for_client_id,
    resolve_sso_credentials_for_redirect,
)


def _base_settings(**kwargs: object) -> Settings:
    data: dict[str, object] = {
        "database_url": "sqlite+aiosqlite:///:memory:",
        "sso_client_id": "default-id",
        "sso_client_secret": "default-secret",
        "sso_client_id_5173": "",
        "sso_client_secret_5173": "",
        "sso_client_id_9088": "",
        "sso_client_secret_9088": "",
        "sso_client_id_stage": "",
        "sso_client_secret_stage": "",
        "sso_client_id_prod": "",
        "sso_client_secret_prod": "",
    }
    data.update(kwargs)
    return Settings(**data)


def test_redirect_stage_wins() -> None:
    s = _base_settings(
        sso_client_id_stage="st-id",
        sso_client_secret_stage="st-sec",
        sso_client_id_5173="sp-id",
        sso_client_secret_5173="sp-sec",
    )
    uri = "https://atrium.stage.example.com/auth/callback"
    assert resolve_sso_credentials_for_redirect(uri, s) == ("st-id", "st-sec")


def test_redirect_prod_not_stage() -> None:
    s = _base_settings(
        sso_client_id_prod="prod-id",
        sso_client_secret_prod="prod-sec",
    )
    uri = "https://atrium.example.com/auth/callback"
    assert resolve_sso_credentials_for_redirect(uri, s) == ("prod-id", "prod-sec")


def test_redirect_prod_skips_when_stage_subdomain_in_host() -> None:
    """atrium.stage.* не должен попадать под ветку prod."""
    s = _base_settings(
        sso_client_id_prod="prod-id",
        sso_client_secret_prod="prod-sec",
        sso_client_id_stage="st-id",
        sso_client_secret_stage="st-sec",
    )
    uri = "https://app.atrium.stage.example.com/cb"
    assert resolve_sso_credentials_for_redirect(uri, s) == ("st-id", "st-sec")


def test_redirect_9088_port() -> None:
    s = _base_settings(
        sso_client_id_9088="gw-id",
        sso_client_secret_9088="gw-sec",
    )
    assert resolve_sso_credentials_for_redirect("http://localhost:9088/auth/callback", s) == ("gw-id", "gw-sec")


def test_redirect_5173_port() -> None:
    s = _base_settings(
        sso_client_id_5173="spa-id",
        sso_client_secret_5173="spa-sec",
    )
    assert resolve_sso_credentials_for_redirect("http://127.0.0.1:5173/auth/callback", s) == ("spa-id", "spa-sec")


def test_redirect_fallback_default_pair() -> None:
    s = _base_settings()
    assert resolve_sso_credentials_for_redirect("http://localhost:9999/cb", s) == ("default-id", "default-secret")


def test_redirect_stage_empty_pair_falls_through_to_default() -> None:
    """Пустая пара stage → дальше prod/порты не подходят → default."""
    s = _base_settings(
        sso_client_id_stage="",
        sso_client_secret_stage="",
        sso_client_id_5173="spa-id",
        sso_client_secret_5173="spa-sec",
    )
    uri = "https://atrium.stage.example.com/x"
    assert resolve_sso_credentials_for_redirect(uri, s) == ("default-id", "default-secret")


def test_redirect_raises_when_no_credentials() -> None:
    s = _base_settings(sso_client_id="", sso_client_secret="")
    with pytest.raises(SsoCredentialsNotFoundError):
        resolve_sso_credentials_for_redirect("http://localhost:3000/cb", s)


def test_client_id_empty_raises() -> None:
    s = _base_settings()
    with pytest.raises(SsoCredentialsNotFoundError):
        resolve_sso_credentials_for_client_id("  ", s)


def test_client_id_matches_default() -> None:
    s = _base_settings()
    assert resolve_sso_credentials_for_client_id("default-id", s) == ("default-id", "default-secret")


def test_client_id_matches_5173() -> None:
    s = _base_settings(
        sso_client_id_5173="c5173",
        sso_client_secret_5173="s5173",
    )
    assert resolve_sso_credentials_for_client_id("c5173", s) == ("c5173", "s5173")


def test_client_id_matches_9088_stage_prod_order() -> None:
    s = _base_settings(
        sso_client_id_9088="c8",
        sso_client_secret_9088="s8",
        sso_client_id_stage="cs",
        sso_client_secret_stage="ss",
        sso_client_id_prod="cp",
        sso_client_secret_prod="sp",
    )
    assert resolve_sso_credentials_for_client_id("c8", s) == ("c8", "s8")
    assert resolve_sso_credentials_for_client_id("cs", s) == ("cs", "ss")
    assert resolve_sso_credentials_for_client_id("cp", s) == ("cp", "sp")


def test_client_id_known_but_secret_empty_raises() -> None:
    s = _base_settings(sso_client_id_5173="x", sso_client_secret_5173="")
    with pytest.raises(SsoCredentialsNotFoundError):
        resolve_sso_credentials_for_client_id("x", s)


def test_client_id_unknown_raises() -> None:
    s = _base_settings()
    with pytest.raises(SsoCredentialsNotFoundError):
        resolve_sso_credentials_for_client_id("no-such-client", s)
