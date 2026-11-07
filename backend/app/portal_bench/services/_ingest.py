"""Разбор листов «… сводная» и ставок из «ОБЩИЙ СТАТУС ПО ЗАПРОСАМ»."""

from __future__ import annotations

import re
from datetime import date, datetime, timedelta
from typing import Any

from app.core.utils import now_utc

MONTHS = {
    1: "Январь",
    2: "Февраль",
    3: "Март",
    4: "Апрель",
    5: "Май",
    6: "Июнь",
    7: "Июль",
    8: "Август",
    9: "Сентябрь",
    10: "Октябрь",
    11: "Ноябрь",
    12: "Декабрь",
}
MONTH_BY_NAME = {
    "январь": 1,
    "февраль": 2,
    "март": 3,
    "апрель": 4,
    "май": 5,
    "июнь": 6,
    "июль": 7,
    "август": 8,
    "сентябр": 9,
    "октябр": 10,
    "ноябр": 11,
    "декабр": 12,
}
SKIP_SHEETS = {"справочник", "общий статус по запросам", "май", "апрель"}
SKIP_NAMES = {
    "",
    "nan",
    "none",
    "разработчик:",
    "разработчик",
    "итого",
    "всего",
    "статус рассмотрения",
}
FIELD_LABELS = {
    "дата",
    "разработчик",
    "партнер",
    "партнёр",
    "проект & id запроса",
    "ставка",
    "статус заявки",
    "статус рассмотрения",
    "время",
    "ответственный менеджер",
}
# «bia» и «да» раньше «ba»: иначе BIA/ДА становятся BA или Other.
SPEC_RULES = [
    ("android", "Android"),
    ("flutter", "Flutter"),
    ("devops", "DevOps"),
    ("aqa", "AQA"),
    ("python", "Python"),
    ("java", "Java"),
    ("ios", "iOS"),
    ("bia", "DA"),
    ("ба", "BA"),
    ("ba", "BA"),
    ("са", "SA"),
    ("sa", "SA"),
    ("да", "DA"),
    ("da", "DA"),
    ("go", "Go"),
]
STATUS_SHEET = "общий статус по запросам"
_RATE_MIN = 500.0
_RATE_MAX = 8000.0

BenchRecord = dict[str, Any]


def extract_specialization(name: str) -> str:
    """Метка — отдельное слово (DA, СА), не подстрока имени: «са» в «Александр»."""
    tokens = [part.lower() for part in name.split() if part]
    for needle, spec in SPEC_RULES:
        if needle in tokens or spec.lower() in tokens:
            return spec
    return "Other"


def apply_current_specialization(record: BenchRecord) -> BenchRecord:
    name = str(record.get("developer") or "")
    if not name:
        return record
    spec = extract_specialization(name)
    if record.get("specialization") == spec:
        return record
    return {**record, "specialization": spec}


def to_int(value: object) -> int:
    if value is None or isinstance(value, bool):
        return int(value) if isinstance(value, bool) else 0
    if isinstance(value, (int, float)):
        return int(value)
    text = str(value).strip().replace("\xa0", "").replace(" ", "")
    if not text:
        return 0
    try:
        return int(float(text.replace(",", ".")))
    except ValueError:
        return 0


def parse_rate_cell(value: object) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        rate = float(value)
        return rate if _RATE_MIN <= rate <= _RATE_MAX else None
    cleaned = re.sub(r"[^\d.,]", "", str(value).replace("Отправили CV", ""))
    if not cleaned:
        return None
    try:
        rate = float(cleaned.replace(",", "."))
    except ValueError:
        return None
    if _RATE_MIN <= rate <= _RATE_MAX:
        return rate
    return None


def month_from_sheet_name(name: str) -> tuple[str, int] | None:
    low = name.strip().lower()
    if "сводн" not in low:
        return None
    for key, num in MONTH_BY_NAME.items():
        if key in low:
            return MONTHS[num], num
    return None


def parse_start_date(comment: object, year: int) -> str | None:
    if not comment:
        return None
    text = str(comment)
    if not re.search(r"выход", text, re.IGNORECASE):
        return None
    named = re.search(
        r"(\d{1,2})\s+(января|февраля|марта|апреля|мая|июня|июля|августа|сентября|октября|ноября|декабря)",
        text,
        re.IGNORECASE,
    )
    if named:
        day = int(named.group(1))
        month_word = named.group(2).lower()
        month_map = {
            "января": 1,
            "февраля": 2,
            "марта": 3,
            "апреля": 4,
            "мая": 5,
            "июня": 6,
            "июля": 7,
            "августа": 8,
            "сентября": 9,
            "октября": 10,
            "ноября": 11,
            "декабря": 12,
        }
        month_num = month_map.get(month_word)
        if month_num:
            return f"{day:02d}.{month_num:02d}.{year}"
    match = re.search(r"(\d{1,2})[./](\d{1,2})(?:[./](\d{2,4}))?", text)
    if match:
        day = int(match.group(1))
        month = int(match.group(2))
        raw_year = match.group(3)
        if raw_year:
            y = int(raw_year)
            if y < 100:
                y += 2000
        else:
            y = year
        if 1 <= month <= 12 and 1 <= day <= 31:
            return f"{day:02d}.{month:02d}.{y}"
    return None


def normalize_dev_name(name: str) -> str:
    return " ".join(name.lower().split())


def name_tokens_key(name: str) -> str:
    return " ".join(sorted(normalize_dev_name(name).split()))


def lookup_rate(rates: dict[str, float], developer: str) -> float | None:
    if not developer:
        return None
    if developer in rates:
        return rates[developer]
    exact = normalize_dev_name(developer)
    if exact in rates:
        return rates[exact]
    tokens = name_tokens_key(developer)
    if tokens in rates:
        return rates[tokens]
    return None


def _store_rate(rates: dict[str, float], developer: str, value: float) -> None:
    rates[developer] = value
    rates[normalize_dev_name(developer)] = value
    rates[name_tokens_key(developer)] = value


def load_developer_rates(rows: list[list[object]]) -> dict[str, float]:
    rates: dict[str, float] = {}
    current_dev: str | None = None
    for row in rows:
        if not row:
            continue
        first = row[0]
        if first is None or first == "":
            continue
        label = str(first).replace("\n", " ").strip()
        low = label.lower()
        if low in FIELD_LABELS or low.startswith("№"):
            if low == "ставка" and current_dev:
                found = [rate for cell in row[1:] if (rate := parse_rate_cell(cell)) is not None]
                if found:
                    _store_rate(rates, current_dev, sum(found) / len(found))
            continue
        current_dev = label
    return rates


def _year_from_cell(value: object) -> int | None:
    if isinstance(value, datetime):
        return value.year
    if isinstance(value, date):
        return value.year
    if isinstance(value, (int, float)) and not isinstance(value, bool) and value > 40000:
        # Excel serial (дни с 1899-12-30)
        try:
            parsed = datetime(1899, 12, 30) + timedelta(days=int(value))
            return parsed.year
        except (OverflowError, ValueError, OSError):
            return None
    if isinstance(value, str):
        text = value.strip()
        match = re.search(r"(20\d{2})", text)
        if match:
            return int(match.group(1))
    return None


def year_from_status_rows(rows: list[list[object]], fallback: int) -> int:
    if not rows:
        return fallback
    first = rows[0]
    for cell in first[1:40]:
        year = _year_from_cell(cell)
        if year is not None:
            return year
    return fallback


def _cell(row: list[object], idx: int) -> object:
    return row[idx] if len(row) > idx else None


def parse_monthly_rows(
    rows: list[list[object]],
    month_name: str,
    month_num: int,
    year: int,
    rates: dict[str, float],
) -> list[BenchRecord]:
    records: list[BenchRecord] = []
    for row in rows[2:]:
        if not row:
            continue
        raw_name = row[0]
        if raw_name is None or raw_name == "":
            continue
        developer = str(raw_name).replace("\n", " ").strip()
        if not developer or developer.lower() in SKIP_NAMES:
            continue
        if "отправили" in developer.lower():
            continue
        comment = ""
        if len(row) > 10 and row[10] is not None:
            comment = str(row[10]).strip()
            if comment.lower() in {"none", "nan"}:
                comment = ""
        records.append(
            {
                "year": year,
                "month": month_name,
                "month_num": month_num,
                "developer": developer,
                "specialization": extract_specialization(developer),
                "cv_sent": to_int(_cell(row, 1)),
                "screening": to_int(_cell(row, 2)),
                "internal_interview": to_int(_cell(row, 3)),
                "tech_stage_1": to_int(_cell(row, 4)),
                "final_stage": to_int(_cell(row, 5)),
                "osup": to_int(_cell(row, 6)),
                "rejection": to_int(_cell(row, 7)),
                "offer": to_int(_cell(row, 8)),
                "project_start": to_int(_cell(row, 9)),
                "comment": comment,
                "rate": lookup_rate(rates, developer),
                "start_date": parse_start_date(comment, year),
                "request_date": f"01.{month_num:02d}.{year}",
            }
        )
    return records


def ingest_sheet_values(
    sheets: dict[str, list[list[object]]],
    *,
    year: int | None = None,
) -> tuple[list[BenchRecord], int, dict[str, float]]:
    """Читает значения листов Google/Excel: ключ — имя листа, значение — строки."""
    status_rows: list[list[object]] = []
    for name, rows in sheets.items():
        if name.strip().lower() == STATUS_SHEET:
            status_rows = rows
            break
    detected_year = year_from_status_rows(status_rows, year or now_utc().year)
    rates = load_developer_rates(status_rows)
    records: list[BenchRecord] = []
    for sheet_name, rows in sheets.items():
        if sheet_name.strip().lower() in SKIP_SHEETS:
            continue
        parsed_month = month_from_sheet_name(sheet_name)
        if parsed_month is None:
            continue
        month_name, month_num = parsed_month
        records.extend(parse_monthly_rows(rows, month_name, month_num, detected_year, rates))
    return records, detected_year, rates
