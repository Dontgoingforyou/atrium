"""Юнит-тесты для _extract_token_exp и _cache_ttl из deps_auth."""

from __future__ import annotations

import base64
import json
import time

import pytest
from app.api.deps_auth import _cache_ttl, _extract_token_exp


def _make_jwt(payload: dict[str, object]) -> str:
    """Собирает минимальный JWT-like токен (header.payload.signature) без подписи."""

    def b64(data: bytes) -> str:
        return base64.urlsafe_b64encode(data).rstrip(b"=").decode()

    header = b64(b'{"alg":"RS256","typ":"JWT"}')
    body = b64(json.dumps(payload).encode())
    return f"{header}.{body}.fakesig"


class TestExtractTokenExp:
    def test_valid_jwt_with_exp(self) -> None:
        exp = int(time.time()) + 300
        token = _make_jwt({"sub": "u1", "exp": exp})
        assert _extract_token_exp(token) == exp

    def test_jwt_without_exp_claim(self) -> None:
        token = _make_jwt({"sub": "u1"})
        assert _extract_token_exp(token) is None

    def test_not_a_jwt(self) -> None:
        assert _extract_token_exp("not.a.valid") is None
        assert _extract_token_exp("totallyrandom") is None

    def test_empty_string(self) -> None:
        assert _extract_token_exp("") is None

    def test_exp_in_past(self) -> None:
        exp = int(time.time()) - 60
        token = _make_jwt({"exp": exp})
        assert _extract_token_exp(token) == exp

    def test_malformed_base64_payload(self) -> None:
        # Второй сегмент содержит невалидный base64
        assert _extract_token_exp("header.!!!invalid!!!.sig") is None

    def test_payload_not_json(self) -> None:
        payload_b64 = base64.urlsafe_b64encode(b"not-json").rstrip(b"=").decode()
        assert _extract_token_exp(f"header.{payload_b64}.sig") is None


class TestCacheTtl:
    def test_future_exp_smaller_than_max_ttl(self) -> None:
        remaining = 120
        exp = int(time.time()) + remaining
        token = _make_jwt({"exp": exp})
        # TTL должен быть ≈ remaining (±1 с из-за выполнения теста)
        result = _cache_ttl(token, max_ttl=300)
        assert 1 <= result <= remaining

    def test_future_exp_larger_than_max_ttl(self) -> None:
        exp = int(time.time()) + 3600  # токен живёт час
        token = _make_jwt({"exp": exp})
        result = _cache_ttl(token, max_ttl=300)
        assert result == 300

    def test_expired_token_returns_one(self) -> None:
        exp = int(time.time()) - 10
        token = _make_jwt({"exp": exp})
        assert _cache_ttl(token, max_ttl=300) == 1

    def test_no_exp_returns_max_ttl(self) -> None:
        token = _make_jwt({"sub": "u1"})
        assert _cache_ttl(token, max_ttl=300) == 300

    def test_undecodable_token_returns_max_ttl(self) -> None:
        assert _cache_ttl("garbage", max_ttl=180) == 180

    @pytest.mark.parametrize("max_ttl", [1, 60, 300, 1800])
    def test_result_never_exceeds_max_ttl(self, max_ttl: int) -> None:
        exp = int(time.time()) + 9999
        token = _make_jwt({"exp": exp})
        assert _cache_ttl(token, max_ttl=max_ttl) <= max_ttl
