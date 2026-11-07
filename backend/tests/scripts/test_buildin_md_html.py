"""Конвертация markdown BuildIn → HTML для импорта документов."""

from __future__ import annotations

import pytest
from buildin_import.md_html import (
    extract_uuid_from_href,
    markdown_to_html,
    rewrite_internal_links,
)

_PAGE_UUID = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"


@pytest.mark.parametrize(
    ("href", "expected"),
    [
        (f"Page+{_PAGE_UUID}.md", _PAGE_UUID),
        (f"/path/to/Page+{_PAGE_UUID}.md", _PAGE_UUID),
        ("https://external.com", None),
        ("javascript:alert(1)", None),
    ],
)
def test_extract_uuid_from_href(href: str, expected: str | None) -> None:
    assert extract_uuid_from_href(href) == expected


def test_rewrite_internal_links_replaces_md_hrefs() -> None:
    uid = _PAGE_UUID
    html_in = f'<a href="Child+{uid}.md">link</a>'
    mapping = {uid: "/documents/abc"}
    html_out = rewrite_internal_links(html_in, mapping)
    assert 'href="/documents/abc"' in html_out


def test_rewrite_internal_links_preserves_unknown_uuid() -> None:
    uid = _PAGE_UUID
    html_in = f'<a href="Child+{uid}.md">link</a>'
    html_out = rewrite_internal_links(html_in, {})
    assert f'href="Child+{uid}.md"' in html_out


def test_rewrite_internal_links_skips_non_md_hrefs() -> None:
    html_in = '<a href="https://example.com/page">ext</a>'
    html_out = rewrite_internal_links(html_in, {_PAGE_UUID: "/documents/x"})
    assert 'href="https://example.com/page"' in html_out


@pytest.mark.parametrize(
    ("md", "forbidden"),
    [
        ("[click](javascript:alert(1))", 'href="javascript:'),
        ("<script>alert(1)</script>", "<script>"),
        ("[x](data:text/html,hi)", 'href="data:'),
    ],
)
def test_markdown_blocks_unsafe_href_and_escapes_html(md: str, forbidden: str) -> None:
    html = markdown_to_html(md)
    assert forbidden not in html


def test_markdown_table_strips_empty_pipe_row() -> None:
    md = """Список менторов

||||||||
|-|-|-|-|-|-|-|
|Направление|ментор|ТГ|ментор2|ТГ|
|SA|Денис|@leonov|Владимир|@bar|
"""
    html = markdown_to_html(md)
    assert "<table" in html
    assert "<th>Направление</th>" in html
    assert "<td>SA</td>" in html
    assert "@leonov" in html
    assert "||||" not in html


def test_markdown_toggle_indented_ol() -> None:
    md = "- Toggle title\n\n    1. шаг один\n\n    2. шаг два\n"
    html = markdown_to_html(md)
    assert '<details class="buildin-toggle">' in html
    assert "<summary>" in html and "Toggle title" in html
    assert "шаг один" in html and "шаг два" in html
    assert html.count("<ol>") == 1
    assert html.count("<li>") == 2


def test_markdown_plain_bullet_not_toggle() -> None:
    md = "- пункт один\n- пункт два\n"
    html = markdown_to_html(md)
    assert "<details" not in html
    assert "<ul><li>пункт один</li><li>пункт два</li></ul>" in html.replace("\n", "")


def test_markdown_image_line_becomes_figure() -> None:
    md = "текст\n\n![photo.jpg](folder/photo.jpg)\n"
    html = markdown_to_html(md)
    assert '<figure class="buildin-figure">' in html
    assert 'src="folder/photo.jpg"' in html
    assert "!<a" not in html


def test_markdown_checklist_task_list() -> None:
    md = "- [x] done\n- [ ] todo\n"
    html = markdown_to_html(md)
    assert '<ul class="buildin-task-list">' in html
    assert "<li><s>done</s></li>" in html
    assert "<li>todo</li>" in html


def test_markdown_code_and_blockquote() -> None:
    md = "> quote line\n\n```python\nprint(1)\n```\n\ninline `code` ok"
    html = markdown_to_html(md)
    assert "<blockquote>" in html and "quote line" in html
    assert '<pre><code class="language-python">' in html
    assert "print(1)" in html
    assert "<code>code</code>" in html


@pytest.mark.parametrize(
    ("level", "tag"),
    [(1, "h1"), (2, "h2"), (3, "h3"), (4, "h4"), (5, "h5"), (6, "h6")],
)
def test_markdown_headings(level: int, tag: str) -> None:
    hashes = "#" * level
    html = markdown_to_html(f"{hashes} Title {level}\n")
    assert f"<{tag}>Title {level}</{tag}>" in html


def test_markdown_bold_and_link() -> None:
    html = markdown_to_html("**bold** and [site](https://example.com)\n")
    assert "<strong>bold</strong>" in html
    assert '<a href="https://example.com">site</a>' in html


def test_markdown_merge_split_lists() -> None:
    md = "- a\n\n- b\n"
    html = markdown_to_html(md)
    assert html.count("<ul>") == 1
    assert "<li>a</li>" in html and "<li>b</li>" in html


def test_markdown_strips_volna_overtime_tail() -> None:
    md = """### овертайм

шаг внутри

1. Берем часы из ТШ специалистов и вносим их в сводную
2. лишний корневой шаг
"""
    html = markdown_to_html(md)
    assert "лишний корневой шаг" not in html
    assert "шаг внутри" in html


def test_markdown_empty_input() -> None:
    assert markdown_to_html("") == ""
    assert markdown_to_html("   \n\n  ") == ""


def test_markdown_crlf_normalized() -> None:
    html = markdown_to_html("# Title\r\n\r\nparagraph\r\n")
    assert "<h1>Title</h1>" in html
    assert "<p>paragraph</p>" in html
