import logging

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from app.core.exceptions import AppError, build_error_payload

logger = logging.getLogger(__name__)


def _http_exception_code(status_code: int) -> str:
    mapping = {
        400: "bad_request",
        401: "unauthorized",
        403: "forbidden",
        404: "not_found",
        409: "conflict",
        422: "validation_error",
        429: "rate_limited",
        503: "service_unavailable",
    }
    return mapping.get(status_code, f"http_{status_code}")


def _http_exception_message(exc: HTTPException) -> str:
    detail = exc.detail
    if isinstance(detail, str):
        return detail
    if isinstance(detail, list | dict):
        return str(detail)
    return str(detail)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def app_error_handler(_request: Request, exc: AppError) -> JSONResponse:
        logger.warning(
            "Ошибка приложения: code=%s status=%s message=%s",
            exc.code,
            exc.status_code,
            exc.message,
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=build_error_payload(code=exc.code, message=exc.message),
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(_request: Request, exc: HTTPException) -> JSONResponse:
        code = _http_exception_code(exc.status_code)
        message = _http_exception_message(exc)
        if exc.status_code >= 500:
            logger.exception("HTTPException %s: %s", exc.status_code, message)
        else:
            logger.warning("HTTPException %s code=%s message=%s", exc.status_code, code, message)
        return JSONResponse(
            status_code=exc.status_code,
            content=build_error_payload(code=code, message=message),
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(_request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Необработанное исключение: %s", exc)
        return JSONResponse(
            status_code=500,
            content=build_error_payload(
                code="internal_error",
                message="Внутренняя ошибка сервера. Попробуйте позже.",
            ),
        )
