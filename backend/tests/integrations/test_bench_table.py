"""Разбор HTML-таблицы бенча (TipTap) в строки CSV."""

from __future__ import annotations

import pytest
from app.core.exceptions import ValidationError
from app.integrations.bench._table import bench_rows_to_csv, parse_bench_table
from app.integrations.bench.constants import CSV_COLUMNS, UTF8_BOM


def test_parse_tiptap_tbody_with_th_headers() -> None:
    html = """
    <p>вступление</p>
    <table class="portal-rich-table">
      <tbody>
        <tr>
          <th>Имя</th><th>Опыт</th><th>Стек</th><th>Грейд</th>
          <th>CV</th><th>Локация</th><th>Статус</th>
        </tr>
        <tr>
          <td>Кирилл Б.</td><td>4.5</td><td>Python</td><td>Middle</td>
          <td></td><td>Москва</td><td>Доступен</td>
        </tr>
      </tbody>
    </table>
    """
    rows = parse_bench_table(html)
    assert rows == [
        {
            "name": "Кирилл Б.",
            "experience": "4.5",
            "stack": "Python",
            "grade": "Middle",
            "cv": "",
            "location": "Москва",
            "status": "Доступен",
        }
    ]


def test_parse_thead_and_td_only_headers() -> None:
    html = """
    <table>
      <thead><tr>
        <td> имя </td><td>ОПЫТ</td><td>стек</td><td>грейд</td>
        <td>cv</td><td>локация</td><td>статус</td>
      </tr></thead>
      <tbody><tr>
        <td>Максим</td><td>2</td><td>Java</td><td>Junior</td>
        <td></td><td>Казань</td><td></td>
      </tr></tbody>
    </table>
    """
    rows = parse_bench_table(html)
    assert rows[0]["name"] == "Максим"
    assert rows[0]["grade"] == "Junior"
    assert rows[0]["status"] == ""


def test_parse_cv_prefers_href() -> None:
    html = """
    <table>
      <tr><th>Имя</th><th>CV</th></tr>
      <tr><td>Анна</td><td><a href="https://example.com/cv.pdf">файл</a></td></tr>
    </table>
    """
    rows = parse_bench_table(html)
    assert rows[0]["cv"] == "https://example.com/cv.pdf"
    assert rows[0]["name"] == "Анна"
    assert rows[0]["stack"] == ""


def test_parse_skips_empty_rows_and_unknown_columns() -> None:
    html = """
    <table>
      <tr><th>Имя</th><th>Лишнее</th><th>Стек</th></tr>
      <tr><td></td><td>x</td><td></td></tr>
      <tr><td>Пётр</td><td>y</td><td>Go</td></tr>
    </table>
    """
    rows = parse_bench_table(html)
    assert len(rows) == 1
    assert rows[0]["name"] == "Пётр"
    assert rows[0]["stack"] == "Go"
    assert "лишнее" not in rows[0]


def test_parse_first_table_only() -> None:
    html = """
    <table>
      <tr><th>Имя</th></tr>
      <tr><td>Первый</td></tr>
    </table>
    <table>
      <tr><th>Имя</th></tr>
      <tr><td>Второй</td></tr>
    </table>
    """
    rows = parse_bench_table(html)
    assert [r["name"] for r in rows] == ["Первый"]


def test_parse_no_table_raises() -> None:
    with pytest.raises(ValidationError, match="нет таблицы"):
        parse_bench_table("<p>просто текст</p>")


def test_parse_empty_body_raises() -> None:
    with pytest.raises(ValidationError, match="нет таблицы"):
        parse_bench_table(None)
    with pytest.raises(ValidationError, match="нет таблицы"):
        parse_bench_table("   ")


def test_parse_unknown_headers_raises() -> None:
    with pytest.raises(ValidationError, match="известных колонок"):
        parse_bench_table("<table><tr><th>Foo</th><th>Bar</th></tr><tr><td>1</td><td>2</td></tr></table>")


def test_bench_rows_to_csv_bom_and_semicolon() -> None:
    rows = [
        {
            "name": "Кирилл",
            "experience": "4",
            "stack": "Python; Django",
            "grade": "Middle",
            "cv": "",
            "location": "Москва",
            "status": "Доступен",
        }
    ]
    raw = bench_rows_to_csv(rows)
    assert raw.startswith(UTF8_BOM)
    text = raw[len(UTF8_BOM) :].decode("utf-8")
    header, data = text.splitlines()[:2]
    assert header.split(";") == list(CSV_COLUMNS)
    assert data.startswith("Кирилл;4;")
    assert "Python; Django" in data or '"Python; Django"' in data
