"""Чистый парсер сводных листов дашборда бенч (без БД)."""

from __future__ import annotations

from datetime import date, datetime

from app.portal_bench.services._ingest import (
    apply_current_specialization,
    extract_specialization,
    ingest_sheet_values,
    lookup_rate,
    month_from_sheet_name,
    parse_rate_cell,
    parse_start_date,
)


def test_extract_specialization_known_and_other() -> None:
    assert extract_specialization("Кандидат Тестовый iOS") == "iOS"
    assert extract_specialization("Иванов AQA Java") == "AQA"
    assert extract_specialization("Петров БА") == "BA"
    assert extract_specialization("Сидоров СА") == "SA"
    assert extract_specialization("Без метки") == "Other"


def test_extract_specialization_da_not_swallowed_by_ba() -> None:
    assert extract_specialization("Иванов DA") == "DA"
    assert extract_specialization("Иванов ДА") == "DA"
    assert extract_specialization("Иванов BIA") == "DA"
    assert extract_specialization("Петров BA") == "BA"
    assert extract_specialization("Петров БА") == "BA"


def test_extract_specialization_ignores_needles_inside_names() -> None:
    assert extract_specialization("Александр Анфимов DA") == "DA"
    assert extract_specialization("Абдуллаев Бабек SA") == "SA"
    assert extract_specialization("Даниэл Пянзин BA") == "BA"
    assert extract_specialization("Муртазин Даниль Android") == "Android"


def test_apply_current_specialization_fixes_stored_sa_for_da_name() -> None:
    fixed = apply_current_specialization(
        {"developer": "Александр Анфимов DA", "specialization": "SA", "offer": 0, "project_start": 1}
    )
    assert fixed["specialization"] == "DA"
    assert fixed["project_start"] == 1


def test_month_from_sheet_name_requires_svodnaya() -> None:
    assert month_from_sheet_name("Январь сводная") == ("Январь", 1)
    assert month_from_sheet_name("Август сводная  ") == ("Август", 8)
    assert month_from_sheet_name("МАЙ") is None
    assert month_from_sheet_name("справочник") is None


def test_parse_start_date_formats() -> None:
    assert parse_start_date("выход 02.02", 2026) == "02.02.2026"
    assert parse_start_date("Выход на проект 13.04", 2026) == "13.04.2026"
    assert parse_start_date("выход 19 августа", 2026) == "19.08.2026"
    assert parse_start_date("выход 3.08.2026", 2026) == "03.08.2026"
    assert parse_start_date("просто комментарий", 2026) is None


def test_parse_rate_cell_skips_labels_and_out_of_range() -> None:
    assert parse_rate_cell(2300) == 2300.0
    assert parse_rate_cell("Отправили CV") is None
    assert parse_rate_cell(100) is None
    assert parse_rate_cell(9000) is None


def test_lookup_rate_matches_swapped_name() -> None:
    rates = {
        "иванов петр ios": 2000.0,
        "ios иванов петр": 2000.0,
    }
    assert lookup_rate(rates, "Петр Иванов iOS") == 2000.0


def test_ingest_reads_svodnaya_skips_directory_and_totals() -> None:
    sheets: dict[str, list[list[object]]] = {
        "справочник": [["65apps"], ["BSS"]],
        "ОБЩИЙ СТАТУС ПО ЗАПРОСАМ": [
            [None, datetime(2026, 3, 1)],
            ["Иванов Петр iOS"],
            ["Ставка", 2100, 2300],
        ],
        "Январь сводная": [
            ["шапка"],
            ["шапка2"],
            ["Иванов Петр iOS", 4, 1, 1, 1, 1, 0, 0, 2, 1, "выход 15.01"],
            ["Итого", 4, 0, 0, 0, 0, 0, 0, 0, 0, ""],
        ],
        "МАЙ": [["старый недельный"]],
    }
    records, year, rates = ingest_sheet_values(sheets, year=2026)
    assert year == 2026
    assert records == [
        {
            "year": 2026,
            "month": "Январь",
            "month_num": 1,
            "developer": "Иванов Петр iOS",
            "specialization": "iOS",
            "cv_sent": 4,
            "screening": 1,
            "internal_interview": 1,
            "tech_stage_1": 1,
            "final_stage": 1,
            "osup": 0,
            "rejection": 0,
            "offer": 2,
            "project_start": 1,
            "comment": "выход 15.01",
            "rate": 2200.0,
            "start_date": "15.01.2026",
            "request_date": "01.01.2026",
        }
    ]
    assert rates["Иванов Петр iOS"] == 2200.0


def test_year_from_date_cell() -> None:
    sheets = {
        "ОБЩИЙ СТАТУС ПО ЗАПРОСАМ": [[None, date(2026, 8, 1)]],
        "Февраль сводная": [
            [],
            [],
            ["Разработчик Android", 1, 0, 0, 0, 0, 0, 0, 0, 0, ""],
        ],
    }
    records, year, _rates = ingest_sheet_values(sheets)
    assert year == 2026
    assert records[0]["month"] == "Февраль"
