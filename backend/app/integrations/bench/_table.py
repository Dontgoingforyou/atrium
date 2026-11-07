"""Разбор первой HTML-таблицы документа бенча в строки CSV."""

from __future__ import annotations

import csv
import io
from html.parser import HTMLParser

from app.core.exceptions import ValidationError
from app.integrations.bench.constants import (
    CSV_COLUMNS,
    CSV_DELIMITER,
    HEADER_ALIASES,
    UTF8_BOM,
)


class _FirstTableParser(HTMLParser):
    """Собирает ячейки только первой таблицы (вложенные таблицы пропускает)."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.rows: list[list[str]] = []
        self._table_depth = 0
        self._finished = False
        self._row: list[str] | None = None
        self._cell_parts: list[str] | None = None
        self._cell_href: str | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if self._finished:
            return
        if tag == "table":
            self._table_depth += 1
            return
        if self._table_depth != 1:
            return
        if tag == "tr":
            self._row = []
            return
        if tag in {"td", "th"}:
            self._cell_parts = []
            self._cell_href = None
            return
        if tag == "a" and self._cell_parts is not None:
            href = dict(attrs).get("href")
            if href and href.strip():
                self._cell_href = href.strip()
            return
        if tag == "br" and self._cell_parts is not None:
            self._cell_parts.append(" ")

    def handle_endtag(self, tag: str) -> None:
        if self._finished:
            return
        if tag in {"td", "th"} and self._cell_parts is not None and self._row is not None:
            text = " ".join("".join(self._cell_parts).split())
            self._row.append(self._cell_href or text)
            self._cell_parts = None
            self._cell_href = None
            return
        if tag == "tr" and self._row is not None:
            if self._table_depth == 1:
                self.rows.append(self._row)
            self._row = None
            return
        if tag == "table" and self._table_depth > 0:
            self._table_depth -= 1
            if self._table_depth == 0:
                self._finished = True

    def handle_data(self, data: str) -> None:
        if not self._finished and self._table_depth == 1 and self._cell_parts is not None:
            self._cell_parts.append(data)


def _normalize_header(cell: str) -> str | None:
    return HEADER_ALIASES.get(cell.strip().casefold())


def parse_bench_table(html: str | None) -> list[dict[str, str]]:
    """Вернуть строки бенча или ValidationError, если таблицы/колонок нет."""
    if html is None or not html.strip():
        raise ValidationError("В документе бенча нет таблицы")
    parser = _FirstTableParser()
    parser.feed(html)
    parser.close()
    if not parser.rows:
        raise ValidationError("В документе бенча нет таблицы")
    keys = [_normalize_header(cell) for cell in parser.rows[0]]
    if not any(key is not None for key in keys):
        raise ValidationError("В таблице бенча нет известных колонок")
    rows: list[dict[str, str]] = []
    for raw in parser.rows[1:]:
        mapped = {col: "" for col in CSV_COLUMNS}
        for idx, key in enumerate(keys):
            if key is None or idx >= len(raw):
                continue
            mapped[key] = raw[idx]
        if any(mapped[col] for col in CSV_COLUMNS):
            rows.append(mapped)
    return rows


def bench_rows_to_csv(rows: list[dict[str, str]]) -> bytes:
    """CSV UTF-8 с BOM, разделитель ``;``."""
    buf = io.StringIO()
    writer = csv.writer(buf, delimiter=CSV_DELIMITER, lineterminator="\r\n", quoting=csv.QUOTE_MINIMAL)
    writer.writerow(CSV_COLUMNS)
    for row in rows:
        writer.writerow([row.get(col, "") for col in CSV_COLUMNS])
    return UTF8_BOM + buf.getvalue().encode("utf-8")
