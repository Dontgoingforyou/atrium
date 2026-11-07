"""Константы выгрузки бенча для RAG."""

from __future__ import annotations

import uuid

# Id документа «Бенч» на prod; смена — через BENCH_EXPORT_DOCUMENT_ID, не из query.
DEFAULT_BENCH_DOCUMENT_ID = uuid.UUID("60629368-c9e8-492c-9def-67e3c4aa092c")

BENCH_EXPORT_PATH = "/api/v1/integrations/bench"
CSV_FILENAME = "bench.csv"
CSV_CONTENT_TYPE = "text/csv; charset=utf-8-sig"
CSV_DELIMITER = ";"
UTF8_BOM = b"\xef\xbb\xbf"

CSV_COLUMNS: tuple[str, ...] = (
    "name",
    "experience",
    "stack",
    "grade",
    "cv",
    "location",
    "status",
)

# Заголовки TipTap (без регистра) → колонки эталона AUAUTO-112.
HEADER_ALIASES: dict[str, str] = {
    "имя": "name",
    "опыт": "experience",
    "стек": "stack",
    "грейд": "grade",
    "cv": "cv",
    "локация": "location",
    "статус": "status",
}
