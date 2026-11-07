"""CSV → HTML-таблица для тела документа."""

from __future__ import annotations

import html


def csv_rows_to_html(rows: list[dict[str, str]], *, caption: str | None = None) -> str:
    if not rows:
        return "<p><em>Пустая таблица</em></p>"
    headers = list(rows[0].keys())
    parts: list[str] = []
    if caption:
        parts.append(f"<p><strong>{html.escape(caption)}</strong></p>")
    parts.append('<table class="buildin-csv-import"><thead><tr>')
    for h in headers:
        parts.append(f"<th>{html.escape(h)}</th>")
    parts.append("</tr></thead><tbody>")
    for row in rows:
        parts.append("<tr>")
        for h in headers:
            val = row.get(h, "") or ""
            parts.append(f"<td>{html.escape(val)}</td>")
        parts.append("</tr>")
    parts.append("</tbody></table>")
    return "".join(parts)
