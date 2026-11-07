from __future__ import annotations

from app.core.config import Settings


class SsoCredentialsNotFoundError(Exception):
    """Нет настроенной пары учётных данных для данного redirect_uri или client_id."""


def _pair(cid: str, secret: str) -> tuple[str, str] | None:
    c, s = cid.strip(), secret.strip()
    if c and s:
        return c, s
    return None


def resolve_sso_credentials_for_redirect(redirect_uri: str, settings: Settings) -> tuple[str, str]:
    """
    Сопоставление redirect из whitelist с одним из зарегистрированных SSO-клиентов.
    Порядок: stage → prod → :9088 → :5173 → пара по умолчанию SSO_CLIENT_ID.
    """
    ul = redirect_uri.strip().lower()

    if "cosmolet.stage.example.com" in ul:
        p = _pair(settings.sso_client_id_stage, settings.sso_client_secret_stage)
        if p:
            return p
    if "cosmolet.example.com" in ul and "cosmolet.stage." not in ul and ".stage." not in ul:
        p = _pair(settings.sso_client_id_prod, settings.sso_client_secret_prod)
        if p:
            return p
    if ":9088" in ul:
        p = _pair(settings.sso_client_id_9088, settings.sso_client_secret_9088)
        if p:
            return p
    if ":5173" in ul:
        p = _pair(settings.sso_client_id_5173, settings.sso_client_secret_5173)
        if p:
            return p

    p = _pair(settings.sso_client_id, settings.sso_client_secret)
    if p:
        return p

    raise SsoCredentialsNotFoundError(redirect_uri)


def resolve_sso_credentials_for_client_id(client_id: str, settings: Settings) -> tuple[str, str]:
    """Пара для refresh и прочих вызовов, когда известен client_id."""
    want = client_id.strip()
    if not want:
        raise SsoCredentialsNotFoundError("")

    candidates: list[tuple[str, str]] = [
        (settings.sso_client_id, settings.sso_client_secret),
        (settings.sso_client_id_5173, settings.sso_client_secret_5173),
        (settings.sso_client_id_9088, settings.sso_client_secret_9088),
        (settings.sso_client_id_stage, settings.sso_client_secret_stage),
        (settings.sso_client_id_prod, settings.sso_client_secret_prod),
    ]
    for cid, sec in candidates:
        if cid.strip() == want:
            p = _pair(cid, sec)
            if p:
                return p
            break

    raise SsoCredentialsNotFoundError(want)
