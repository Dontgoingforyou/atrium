from __future__ import annotations

import httpx
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import DbSession, HttpClient
from app.api.deps_auth import extract_bearer_token, verify_access_token
from app.core.config import get_settings
from app.core.exceptions import AppError, NotFoundError, UnauthorizedError, build_error_payload

router = APIRouter(include_in_schema=False)

_SWAGGER_HTML = """\
<!DOCTYPE html>
<html lang="ru">
<head>
  <title>{title} — документация</title>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <link rel="stylesheet" href="/vendor/swagger-ui/swagger-ui.css">
</head>
<body>
<div id="swagger-ui"></div>
<script src="/vendor/swagger-ui/swagger-ui-bundle.js"></script>
<script src="/vendor/swagger-ui/swagger-ui-standalone-preset.js"></script>
<script>
var DOCS_TOKEN_KEY = 'portal_docs_token';
var AUTH_STORAGE_KEY = 'cosmolet-auth';
var REFRESH_URL = '/api/v1/auth/refresh';

function _readPersistedAuth() {{
  try {{
    var raw = localStorage.getItem(AUTH_STORAGE_KEY);
    if (!raw) return null;
    return JSON.parse(raw).state || null;
  }} catch (e) {{ return null; }}
}}

function _getTokenSync() {{
  try {{
    return sessionStorage.getItem(DOCS_TOKEN_KEY);
  }} catch (e) {{ return null; }}
}}

async function _acquireToken() {{
  var cached = _getTokenSync();
  if (cached) return cached;

  var state = _readPersistedAuth();
  if (!state || !state.expiresAt) return null;

  try {{
    var body = state.oauthClientId
      ? JSON.stringify({{ client_id: state.oauthClientId }})
      : '{{}}';
    var res = await fetch(REFRESH_URL, {{
      method: 'POST',
      headers: {{ 'Content-Type': 'application/json' }},
      credentials: 'include',
      body: body,
    }});
    if (!res.ok) return null;
    var data = await res.json();
    var token = data && data.access_token;
    if (token) {{
      try {{ sessionStorage.setItem(DOCS_TOKEN_KEY, token); }} catch (e) {{}}
    }}
    return token || null;
  }} catch (e) {{
    return null;
  }}
}}

window.addEventListener('load', async function () {{
  var token = await _acquireToken();
  if (!token) {{
    sessionStorage.setItem('auth_next', '/docs');
    window.location.href = '/login';
    return;
  }}

  var ui = SwaggerUIBundle({{
    url: '/openapi.json',
    dom_id: '#swagger-ui',
    presets: [SwaggerUIBundle.presets.apis, SwaggerUIStandalonePreset],
    layout: 'StandaloneLayout',
    requestInterceptor: function (req) {{
      var t = _getTokenSync();
      if (t) req.headers['Authorization'] = 'Bearer ' + t;
      return req;
    }},
  }});
  window.ui = ui;
}});
</script>
</body>
</html>
"""

_REDOC_HTML = """\
<!DOCTYPE html>
<html lang="ru">
<head>
  <title>{title} — ReDoc</title>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1">
</head>
<body>
  <div id="redoc-container"></div>
  <script src="/vendor/redoc/redoc.standalone.js"></script>
  <script>
  var DOCS_TOKEN_KEY = 'portal_docs_token';
  var AUTH_STORAGE_KEY = 'cosmolet-auth';
  var REFRESH_URL = '/api/v1/auth/refresh';

  function _readPersistedAuth() {{
    try {{
      var raw = localStorage.getItem(AUTH_STORAGE_KEY);
      if (!raw) return null;
      return JSON.parse(raw).state || null;
    }} catch (e) {{ return null; }}
  }}

  async function _acquireToken() {{
    try {{
      var cached = sessionStorage.getItem(DOCS_TOKEN_KEY);
      if (cached) return cached;
    }} catch (e) {{}}

    var state = _readPersistedAuth();
    if (!state || !state.expiresAt) return null;

    try {{
      var body = state.oauthClientId
        ? JSON.stringify({{ client_id: state.oauthClientId }})
        : '{{}}';
      var res = await fetch(REFRESH_URL, {{
        method: 'POST',
        headers: {{ 'Content-Type': 'application/json' }},
        credentials: 'include',
        body: body,
      }});
      if (!res.ok) return null;
      var data = await res.json();
      var token = data && data.access_token;
      if (token) {{
        try {{ sessionStorage.setItem(DOCS_TOKEN_KEY, token); }} catch (e) {{}}
      }}
      return token || null;
    }} catch (e) {{
      return null;
    }}
  }}

  window.addEventListener('load', async function () {{
    var token = await _acquireToken();
    if (!token) {{
      sessionStorage.setItem('auth_next', '/redoc');
      window.location.href = '/login';
      return;
    }}

    try {{
      var res = await fetch('/openapi.json', {{
        headers: {{ 'Authorization': 'Bearer ' + token }}
      }});
      if (!res.ok) {{
        sessionStorage.setItem('auth_next', '/redoc');
        window.location.href = '/login';
        return;
      }}
      var spec = await res.json();
      Redoc.init(spec, {{}}, document.getElementById('redoc-container'));
    }} catch (e) {{
      document.body.innerHTML = '<p style="padding:2rem;color:#b00">Ошибка загрузки документации</p>';
    }}
  }});
  </script>
</body>
</html>
"""


async def _verify_openapi_bearer(
    request: Request,
    db: AsyncSession,
    http_client: httpx.AsyncClient,
) -> JSONResponse | None:
    """Проверить Bearer для доступа к OpenAPI; ``None`` — токен валиден.

    Особый случай (не `AppError`/`HTTPException` — см. error-handling.mdc): ответ должен
    нести заголовок ``WWW-Authenticate: Bearer`` (RFC 7235) для 401, а глобальный обработчик
    `AppError`/`HTTPException` (exception_handlers.py) кастомные заголовки не проставляет —
    поэтому `JSONResponse` собирается здесь вручную. Тело при этом приведено к единому
    формату `{code, message, request_id}` через `build_error_payload`, как и у остальных ошибок API.

    Использует `verify_access_token` (с Redis-кэшем) — согласованная политика с основным API.
    """
    token = extract_bearer_token(request.headers.get("authorization"))
    if token is None:
        return JSONResponse(
            status_code=401,
            content=build_error_payload(
                code="unauthorized",
                message="Требуется заголовок Authorization: Bearer для доступа к схеме API",
            ),
            headers={"WWW-Authenticate": "Bearer"},
        )

    s = get_settings()
    if not s.sso_enabled:
        return JSONResponse(
            status_code=503,
            content=build_error_payload(code="service_unavailable", message=s.sso_disabled_detail),
        )

    try:
        await verify_access_token(token, db, http_client)
    except UnauthorizedError as exc:
        return JSONResponse(
            status_code=401,
            content=build_error_payload(code="unauthorized", message=exc.message),
            headers={"WWW-Authenticate": "Bearer"},
        )
    except AppError as exc:
        return JSONResponse(
            status_code=exc.status_code,
            content=build_error_payload(code=exc.code, message=exc.message),
        )
    return None


def _ensure_docs_enabled() -> None:
    """Публичные стенды: UI и спецификация выключены (DEV-2715), не только SSO на JSON."""
    if not get_settings().docs_enabled:
        raise NotFoundError("Документация API отключена")


@router.get("/docs", response_class=HTMLResponse)
async def swagger_ui(request: Request) -> HTMLResponse:
    """Swagger UI: без Bearer отдаётся оболочка; JS редиректит на login; ``/openapi.json`` — только с Bearer."""
    _ensure_docs_enabled()
    title = request.app.title
    return HTMLResponse(_SWAGGER_HTML.format(title=title))


@router.get("/redoc", response_class=HTMLResponse)
async def redoc_ui(request: Request) -> HTMLResponse:
    """ReDoc: без Bearer отдаётся оболочка; JS редиректит на login; схема — только с Bearer."""
    _ensure_docs_enabled()
    title = request.app.title
    return HTMLResponse(_REDOC_HTML.format(title=title))


@router.get("/openapi.json")
async def openapi_schema(request: Request, db: DbSession, http_client: HttpClient) -> JSONResponse:
    """OpenAPI-схема: требует Bearer-токен из заголовка Authorization."""
    _ensure_docs_enabled()
    auth_err = await _verify_openapi_bearer(request, db, http_client)
    if auth_err is not None:
        return auth_err
    return JSONResponse(request.app.openapi())
