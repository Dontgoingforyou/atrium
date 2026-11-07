from __future__ import annotations

import json
import logging
import sys
import time
from typing import Final

from app.core.config import get_settings
from app.core.request_context import get_request_id

_LOG_LEVEL_NAMES: Final[dict[str, int]] = {
    "CRITICAL": logging.CRITICAL,
    "ERROR": logging.ERROR,
    "WARNING": logging.WARNING,
    "INFO": logging.INFO,
    "DEBUG": logging.DEBUG,
    "NOTSET": logging.NOTSET,
}


class _JsonFormatter(logging.Formatter):
    """Форматирует каждую запись лога как одну строку JSON для Loki/stdout."""

    # time.gmtime — встроенная C-функция, не Python-функция.
    # Дескриптор не срабатывает, self не подставляется → converter работает корректно.
    converter = time.gmtime  # type: ignore[assignment]

    def format(self, record: logging.LogRecord) -> str:
        record.message = record.getMessage()
        if record.exc_info:
            record.exc_text = self.formatException(record.exc_info)

        ts = self.formatTime(record, datefmt="%Y-%m-%dT%H:%M:%SZ")
        doc: dict[str, object] = {
            "timestamp": ts,
            "level": record.levelname,
            "logger": record.name,
            "message": record.message,
            "request_id": get_request_id(),
        }
        if record.exc_text:
            doc["exc_info"] = record.exc_text
        # Любые дополнительные поля, добавленные через extra={}
        for key, val in record.__dict__.items():
            if key not in {
                "name",
                "msg",
                "args",
                "created",
                "filename",
                "funcName",
                "levelname",
                "levelno",
                "lineno",
                "module",
                "msecs",
                "pathname",
                "process",
                "processName",
                "relativeCreated",
                "thread",
                "threadName",
                "exc_info",
                "exc_text",
                "stack_info",
                "message",
                "taskName",
            }:
                doc[key] = val
        return json.dumps(doc, ensure_ascii=False, default=str)


def configure_logging() -> None:
    """Инициализирует корневой логгер один раз (идемпотентно)."""
    level = _LOG_LEVEL_NAMES.get(get_settings().log_level.upper(), logging.INFO)
    root = logging.getLogger()
    if root.handlers:
        root.setLevel(level)
    else:
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(level)
        handler.setFormatter(_JsonFormatter())
        root.setLevel(level)
        root.addHandler(handler)

        # httpx логирует каждый исходящий HTTP-запрос на INFO — слишком шумно для SSO-вызовов.
        logging.getLogger("httpx").setLevel(logging.WARNING)
        logging.getLogger("httpcore").setLevel(logging.WARNING)

    if get_settings().sqlalchemy_echo:
        logging.getLogger("sqlalchemy.engine").setLevel(logging.INFO)
