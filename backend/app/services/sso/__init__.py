"""SSO-сервисы: обмен токенов через шлюз, парсинг групп."""

from app.services.sso.client_resolver import (
    SsoCredentialsNotFoundError,
    resolve_sso_credentials_for_client_id,
    resolve_sso_credentials_for_redirect,
)
from app.services.sso.groups import extract_groups_from_claim
from app.services.sso.token_service import (
    exchange_authorization_code,
    fetch_user_info_from_gateway,
    refresh_access_token,
)

__all__ = [
    "SsoCredentialsNotFoundError",
    "exchange_authorization_code",
    "extract_groups_from_claim",
    "fetch_user_info_from_gateway",
    "refresh_access_token",
    "resolve_sso_credentials_for_client_id",
    "resolve_sso_credentials_for_redirect",
]
