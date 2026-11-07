from __future__ import annotations

from pydantic import BaseModel, Field


class PasswordLoginRequest(BaseModel):
    email: str = Field(min_length=1, max_length=255, description="Email пользователя")
    password: str = Field(min_length=1, max_length=1024, description="Пароль")
    redirect_uri: str | None = Field(
        default=None,
        max_length=2048,
        description="redirect_uri SPA для выбора oauth client_id (whitelist)",
    )


class TokenExchangeRequest(BaseModel):
    code: str = Field(min_length=1, max_length=2048)
    redirect_uri: str = Field(min_length=1, max_length=2048)
    code_verifier: str | None = Field(
        default=None,
        min_length=43,
        max_length=128,
        description="PKCE S256 verifier (43–128 символов)",
    )


class RefreshTokenRequest(BaseModel):
    refresh_token: str | None = Field(
        default=None,
        max_length=8192,
        description=(
            "Refresh-токен. Предпочтительный способ — httpOnly cookie 'rt', "
            "это поле поддерживается для обратной совместимости."
        ),
    )
    client_id: str | None = Field(
        default=None,
        max_length=128,
        description="OAuth client_id, которым был выдан refresh (обязателен при нескольких клиентах в .env)",
    )


class UserPublic(BaseModel):
    sub: str
    email: str
    username: str
    full_name: str
    idp_groups: list[str]
    is_portal_admin: bool
    position: str | None = None
    gid_number: str | None = None
    avatar_url: str | None = None
    avatar_focal_x: float | None = None
    avatar_focal_y: float | None = None


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str | None = None
    expires_in: int
    oauth_client_id: str = Field(
        description="client_id IdP для этого входа; для /auth/refresh при нескольких клиентах",
    )
    user: UserPublic
    redirect_after_login: str | None = Field(default=None, description="Подсказка для SPA после входа")


class RefreshTokenResponse(BaseModel):
    access_token: str
    refresh_token: str | None = None
    expires_in: int
    oauth_client_id: str = Field(description="client_id, которым выполнялся refresh")


class LogoutBeaconRequest(BaseModel):
    """Тело для /auth/logout-beacon (sendBeacon не поддерживает заголовки)."""

    access_token: str = Field(
        max_length=8192,
        description="Bearer access token, который нужно инвалидировать",
    )
