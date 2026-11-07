"""Markdown BuildIn → HTML для portal_document.body (без внешних зависимостей)."""

from __future__ import annotations

import html
import re
from urllib.parse import unquote, urlparse

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+)$")
_CHECKLIST_RE = re.compile(r"^(\s*)[-*]\s+\[([ xX])\]\s+(.+)$")
_UL_RE = re.compile(r"^(\s*)[-*]\s+(.+)$")
_OL_RE = re.compile(r"^(\s*)\d+\.\s+(.+)$")
_BLOCKQUOTE_RE = re.compile(r"^>\s?(.*)$")
_FENCE_RE = re.compile(r"^```(\w*)\s*$")
_IMG_RE = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")
_IMG_LINE_RE = re.compile(r"^!\[([^\]]*)\]\(([^)]+)\)\s*$")
_LINK_RE = re.compile(r"(?<!!)\[([^\]]+)\]\(([^)]+)\)")
_BOLD_RE = re.compile(r"\*\*(.+?)\*\*")
_INLINE_CODE_RE = re.compile(r"`([^`]+)`")
_PAGE_UUID_IN_LINK = re.compile(
    r"([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})",
    re.IGNORECASE,
)
_HREF_RE = re.compile(r'href=(["\'])([^"\']+)\1')
_TABLE_ROW_RE = re.compile(r"\|.+\|")
_SEPARATOR_CELL_RE = re.compile(r"^:?-+:?$")
_ROOT_VOLNA_TAIL_RE = re.compile(
    r"^1\.\s+Берем часы из ТШ специалистов и вносим их в сводную\s*$",
    re.IGNORECASE,
)


def _line_indent(line: str) -> int:
    return len(line) - len(line.lstrip(" "))


def _img_tag(alt: str, src: str) -> str:
    return (
        f'<img class="buildin-inline-image" alt="{html.escape(alt)}" '
        f'src="{html.escape(src, quote=True)}" loading="lazy" />'
    )


def _is_safe_link_href(href: str) -> bool:
    """Относительные пути и http(s) — да; javascript:/data: — нет (XSS в body документа)."""
    stripped = href.strip()
    if not stripped:
        return False
    lower = stripped.lower()
    if lower.startswith(("javascript:", "data:", "vbscript:")):
        return False
    if "://" in lower:
        parsed = urlparse(stripped)
        return parsed.scheme in ("http", "https") and bool(parsed.netloc)
    return True


def _link_tag(label: str, href: str) -> str:
    if not _is_safe_link_href(href):
        return html.escape(label)
    return f'<a href="{html.escape(href, quote=True)}">{html.escape(label)}</a>'


def _inline_md(text: str) -> str:
    s = html.escape(text)
    s = _INLINE_CODE_RE.sub(r"<code>\1</code>", s)
    s = _BOLD_RE.sub(r"<strong>\1</strong>", s)
    # Сначала картинки — иначе ![alt](url) превращается в !<a>alt</a>
    s = _IMG_RE.sub(lambda m: _img_tag(m.group(1), m.group(2)), s)
    s = _LINK_RE.sub(lambda m: _link_tag(m.group(1), m.group(2)), s)
    return s


def _is_table_row(line: str) -> bool:
    stripped = line.strip()
    return bool(stripped) and "|" in stripped and _TABLE_ROW_RE.search(stripped) is not None


def _split_table_row(line: str) -> list[str]:
    stripped = line.strip()
    if stripped.startswith("|"):
        stripped = stripped[1:]
    if stripped.endswith("|"):
        stripped = stripped[:-1]
    return [cell.strip() for cell in stripped.split("|")]


def _is_separator_row(cells: list[str]) -> bool:
    if not cells:
        return False
    return all(not c or _SEPARATOR_CELL_RE.match(c) for c in cells)


def _row_is_empty(cells: list[str]) -> bool:
    return not any(cells)


def _table_lines_to_html(table_lines: list[str]) -> str:
    parsed = [_split_table_row(line) for line in table_lines if line.strip()]
    if not parsed:
        return ""

    while parsed and _row_is_empty(parsed[0]):
        parsed.pop(0)
    if not parsed:
        return ""

    header: list[str] | None = None
    body_rows: list[list[str]] = []
    idx = 0

    if idx < len(parsed) and _is_separator_row(parsed[idx]):
        idx += 1

    if idx < len(parsed) and not _is_separator_row(parsed[idx]):
        header = parsed[idx]
        idx += 1

    if idx < len(parsed) and _is_separator_row(parsed[idx]):
        idx += 1

    while idx < len(parsed):
        if not _is_separator_row(parsed[idx]):
            body_rows.append(parsed[idx])
        idx += 1

    if header is None and body_rows:
        header = body_rows[0]
        body_rows = body_rows[1:]

    if header is None:
        header = parsed[0]
        body_rows = parsed[1:]

    parts: list[str] = ['<table class="buildin-md-table"><thead><tr>']
    for cell in header:
        parts.append(f"<th>{_inline_md(cell)}</th>")
    parts.append("</tr></thead><tbody>")
    for row in body_rows:
        parts.append("<tr>")
        for cell in row:
            parts.append(f"<td>{_inline_md(cell)}</td>")
        parts.append("</tr>")
    parts.append("</tbody></table>")
    return "".join(parts)


def _blockquote_to_html(lines: list[str]) -> str:
    inner = " ".join(_inline_md(line) for line in lines if line.strip())
    return f"<blockquote><p>{inner}</p></blockquote>"


def _dedent_block_lines(lines: list[str]) -> list[str]:
    non_empty = [ln for ln in lines if ln.strip()]
    if not non_empty:
        return lines
    min_ind = min(_line_indent(ln) for ln in non_empty)
    if min_ind <= 0:
        return lines
    return [ln[min_ind:] if len(ln) >= min_ind else ln for ln in lines]


def _is_toggle_header(line: str, lines: list[str], index: int) -> bool:
    ulm = _UL_RE.match(line)
    if ulm is None:
        return False
    header_indent = _line_indent(line)
    j = index + 1
    while j < len(lines) and not lines[j].strip():
        j += 1
    if j >= len(lines):
        return False
    return _line_indent(lines[j]) > header_indent


def _collect_toggle_body(lines: list[str], start: int, header_indent: int) -> tuple[list[str], int]:
    j = start
    collected: list[str] = []
    while j < len(lines):
        raw = lines[j]
        if not raw.strip():
            collected.append(raw)
            j += 1
            continue
        ind = _line_indent(raw)
        if ind > header_indent:
            collected.append(raw)
            j += 1
            continue
        break
    return collected, j


def _next_non_empty_index(lines: list[str], start: int) -> int | None:
    j = start
    while j < len(lines):
        if lines[j].strip():
            return j
        j += 1
    return None


def _list_continues_after_blank(
    lines: list[str],
    blank_index: int,
    tag: str | None,
    last_list_line: str | None,
) -> bool:
    if tag is None or last_list_line is None:
        return False
    j = _next_non_empty_index(lines, blank_index + 1)
    if j is None:
        return False
    line = lines[j]
    if tag == "ol":
        return _OL_RE.match(line) is not None
    if tag == "ul":
        m = _UL_RE.match(line)
        return m is not None and _line_indent(line) == _line_indent(last_list_line)
    if tag == "task":
        return _CHECKLIST_RE.match(line) is not None
    return False


def _strip_accidental_root_numbered_tail(md_text: str) -> str:
    """Срезает ошибочный хвост экспорта BuildIn (повтор шагов Volna без отступа)."""
    lines = md_text.replace("\r\n", "\n").split("\n")
    after_overtime = False
    cut: int | None = None
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("###") and "овертайм" in stripped.lower():
            after_overtime = True
            continue
        if not after_overtime or _line_indent(line) > 0:
            continue
        if _ROOT_VOLNA_TAIL_RE.match(stripped):
            cut = i
            break
    if cut is None:
        return md_text
    return "\n".join(lines[:cut]).rstrip() + "\n"


def _merge_split_lists(html: str) -> str:
    """Склеивает </ol><ol> и </ul><ul>, если список разорван пустыми строками в md."""
    html = re.sub(r"</ol>\s*<ol>", "", html)
    html = re.sub(r"</ul>\s*<ul>", "", html)
    return html


def markdown_to_html(md_text: str) -> str:
    md_text = _strip_accidental_root_numbered_tail(md_text)
    lines = md_text.replace("\r\n", "\n").split("\n")
    out: list[str] = []
    para: list[str] = []
    list_tag: str | None = None
    list_items: list[str] = []
    last_list_line: str | None = None
    i = 0

    def flush_para() -> None:
        nonlocal para
        if para:
            text = " ".join(para).strip()
            if text:
                out.append(f"<p>{_inline_md(text)}</p>")
            para = []

    def flush_list() -> None:
        nonlocal list_tag, list_items, last_list_line
        if list_tag and list_items:
            cls = ' class="buildin-task-list"' if list_tag == "task" else ""
            tag = "ul" if list_tag in {"ul", "task"} else "ol"
            items = "".join(f"<li>{item}</li>" for item in list_items)
            out.append(f"<{tag}{cls}>{items}</{tag}>")
        list_tag = None
        list_items = []
        last_list_line = None

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        if stripped.startswith("```"):
            flush_list()
            flush_para()
            fence = _FENCE_RE.match(stripped)
            lang = fence.group(1) if fence else ""
            i += 1
            code_lines: list[str] = []
            while i < len(lines) and not lines[i].strip().startswith("```"):
                code_lines.append(lines[i])
                i += 1
            if i < len(lines):
                i += 1
            code = html.escape("\n".join(code_lines))
            lang_attr = f' class="language-{html.escape(lang)}"' if lang else ""
            out.append(f"<pre><code{lang_attr}>{code}</code></pre>")
            continue

        if _is_table_row(line):
            flush_list()
            flush_para()
            table_lines = [line]
            i += 1
            while i < len(lines) and _is_table_row(lines[i]):
                table_lines.append(lines[i])
                i += 1
            out.append(_table_lines_to_html(table_lines))
            continue

        bqm = _BLOCKQUOTE_RE.match(line)
        if bqm and bqm.group(1) is not None:
            flush_list()
            flush_para()
            bq_parts: list[str] = []
            while i < len(lines):
                m = _BLOCKQUOTE_RE.match(lines[i])
                if m is None:
                    break
                bq_parts.append(m.group(1))
                i += 1
            out.append(_blockquote_to_html(bq_parts))
            continue

        img_line = _IMG_LINE_RE.match(stripped)
        if img_line:
            flush_list()
            flush_para()
            alt, src = img_line.group(1), img_line.group(2)
            out.append(f'<figure class="buildin-figure">{_img_tag(alt, src)}</figure>')
            i += 1
            continue

        if not stripped:
            if _list_continues_after_blank(lines, i, list_tag, last_list_line):
                i += 1
                continue
            flush_list()
            flush_para()
            i += 1
            continue

        hm = _HEADING_RE.match(stripped)
        if hm:
            flush_list()
            flush_para()
            level = len(hm.group(1))
            out.append(f"<h{level}>{_inline_md(hm.group(2))}</h{level}>")
            i += 1
            continue

        clm = _CHECKLIST_RE.match(line)
        if clm:
            flush_para()
            if list_tag not in (None, "task"):
                flush_list()
            list_tag = "task"
            checked = clm.group(2).lower() == "x"
            item = _inline_md(clm.group(3))
            if checked:
                item = f"<s>{item}</s>"
            list_items.append(item)
            last_list_line = line
            i += 1
            continue

        ulm = _UL_RE.match(line)
        if ulm and _is_toggle_header(line, lines, i):
            flush_list()
            flush_para()
            summary = _inline_md(ulm.group(2))
            header_indent = _line_indent(line)
            body_lines, i = _collect_toggle_body(lines, i + 1, header_indent)
            body_md = "\n".join(_dedent_block_lines(body_lines)).strip()
            body_html = markdown_to_html(body_md) if body_md else ""
            out.append(
                '<details class="buildin-toggle">'
                f"<summary>{summary}</summary>"
                f'<div class="buildin-toggle-body">{body_html}</div>'
                "</details>"
            )
            continue

        if ulm:
            flush_para()
            if list_tag not in (None, "ul"):
                flush_list()
            list_tag = "ul"
            list_items.append(_inline_md(ulm.group(2)))
            last_list_line = line
            i += 1
            continue

        olm = _OL_RE.match(line)
        if olm:
            flush_para()
            if list_tag not in (None, "ol"):
                flush_list()
            list_tag = "ol"
            list_items.append(_inline_md(olm.group(2)))
            last_list_line = line
            i += 1
            continue

        flush_list()
        para.append(stripped)
        i += 1

    flush_list()
    flush_para()
    return _merge_split_lists("\n".join(out))


def extract_uuid_from_href(href: str) -> str | None:
    decoded = unquote(href)
    m = _PAGE_UUID_IN_LINK.search(decoded)
    return m.group(1).lower() if m else None


def rewrite_internal_links(html_body: str, uuid_to_doc_url: dict[str, str]) -> str:
    def repl_href(match: re.Match[str]) -> str:
        quote = match.group(1)
        href = match.group(2)
        uid = extract_uuid_from_href(href)
        if uid is None or ".md" not in unquote(href).lower():
            return match.group(0)
        new_url = uuid_to_doc_url.get(uid)
        if not new_url:
            return match.group(0)
        return f"href={quote}{new_url}{quote}"

    return _HREF_RE.sub(repl_href, html_body)
