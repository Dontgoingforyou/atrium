"""CSV → HTML для импорта BuildIn."""

from __future__ import annotations

from buildin_import.csv_html import csv_rows_to_html


def test_csv_rows_to_html_empty() -> None:
    assert csv_rows_to_html([]) == "<p><em>Пустая таблица</em></p>"


def test_csv_rows_to_html_renders_table_with_caption() -> None:
    rows = [{"col1": "a", "col2": "b"}]
    html = csv_rows_to_html(rows, caption="Caption <script>")
    assert "<strong>Caption &lt;script&gt;</strong>" in html
    assert '<table class="buildin-csv-import">' in html
    assert "<th>col1</th><th>col2</th>" in html.replace("\n", "")
    assert "<td>a</td><td>b</td>" in html.replace("\n", "")


def test_csv_rows_to_html_escapes_cell_xss() -> None:
    rows = [{"x": "<script>alert(1)</script>"}]
    html = csv_rows_to_html(rows)
    assert "<script>" not in html
    assert "&lt;script&gt;" in html
