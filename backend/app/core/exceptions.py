from typing import Any

from app.core.request_context import get_request_id


def build_error_payload(*, code: str, message: str) -> dict[str, Any]:
    """Единый формат тела ошибки ``{code, message, request_id}``.

    Единый источник для всех мест, формирующих тело ошибки API вручную:
    `docs_router.py` (нужен кастомный заголовок ``WWW-Authenticate``,
    который обработчик `AppError`/`HTTPException` не проставляет) и `middleware/rate_limit.py`
    (429 отдаётся напрямую из ASGI-middleware, минуя `exception_handler`).
    """
    body: dict[str, Any] = {"code": code, "message": message}
    rid = get_request_id()
    if rid:
        body["request_id"] = rid
    return body


class AppError(Exception):
    def __init__(
        self,
        message: str,
        *,
        code: str = "error",
        status_code: int = 400,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code


class BadRequestError(AppError):
    def __init__(self, message: str, *, code: str = "bad_request") -> None:
        super().__init__(message, code=code, status_code=400)


class UnauthorizedError(AppError):
    def __init__(self, message: str = "Требуется аутентификация", *, code: str = "unauthorized") -> None:
        super().__init__(message, code=code, status_code=401)


class NotFoundError(AppError):
    def __init__(self, message: str = "Не найдено", *, code: str = "not_found") -> None:
        super().__init__(message, code=code, status_code=404)


class ForbiddenError(AppError):
    def __init__(self, message: str = "Недостаточно прав", *, code: str = "forbidden") -> None:
        super().__init__(message, code=code, status_code=403)


class ConflictError(AppError):
    def __init__(self, message: str, *, code: str = "conflict") -> None:
        super().__init__(message, code=code, status_code=409)


class ValidationError(AppError):
    def __init__(self, message: str, *, code: str = "validation_error") -> None:
        super().__init__(message, code=code, status_code=422)


class StorageUnavailableError(AppError):
    """S3/MinIO недоступен или отказал при обязательной операции с объектом."""

    def __init__(
        self,
        message: str = "Файловое хранилище временно недоступно. Повторите попытку позже.",
        *,
        code: str = "storage_unavailable",
    ) -> None:
        super().__init__(message, code=code, status_code=503)


class ServiceUnavailableError(AppError):
    """Внешний сервис (SSO/шлюз и т.п.) недоступен или отказал — не про файловое хранилище."""

    def __init__(
        self,
        message: str = "Внешний сервис временно недоступен. Повторите попытку позже.",
        *,
        code: str = "service_unavailable",
    ) -> None:
        super().__init__(message, code=code, status_code=503)


class RateLimitError(AppError):
    def __init__(
        self,
        message: str = "Слишком много запросов. Попробуйте позже.",
        *,
        code: str = "rate_limited",
    ) -> None:
        super().__init__(message, code=code, status_code=429)


class PayloadTooLargeError(AppError):
    """Загружаемый файл превышает допустимый размер (аватары и т.п.)."""

    def __init__(self, message: str, *, code: str = "payload_too_large") -> None:
        super().__init__(message, code=code, status_code=413)
