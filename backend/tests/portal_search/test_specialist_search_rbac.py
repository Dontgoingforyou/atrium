"""entity_text для специалистов (публичные хелперы индексации).

RBAC специалистов в fulltext — HTTP в test_portal_search_api
(degrade → [] / manager hit). Константы типов — в portal_search_constants
и semantic default-types HTTP.
"""

from __future__ import annotations

from app.portal_search.services import entity_text as txt


def test_specialist_to_text_full() -> None:
    text = txt.specialist_to_text(
        full_name="Иван Пупкин",
        email="ivan@example.com",
        location="Москва",
        telegram="@ivan",
    )
    assert "Иван Пупкин" in text
    assert "ivan@example.com" in text
    assert "Москва" in text
    assert "@ivan" in text


def test_specialist_to_text_partial() -> None:
    text = txt.specialist_to_text(
        full_name="Мария Иванова",
        email=None,
        location=None,
        telegram=None,
    )
    assert text.strip() == "Мария Иванова"


def test_specialist_to_text_all_none() -> None:
    assert txt.specialist_to_text(None, None, None, None) == ""


def test_specialist_note_to_text() -> None:
    body = "  Специалист отлично справляется с задачами  "
    assert txt.specialist_note_to_text(body) == "Специалист отлично справляется с задачами"


def test_specialist_meta() -> None:
    assert txt.specialist_meta("user-123") == {"specialist_sub": "user-123"}


def test_specialist_note_meta() -> None:
    assert txt.specialist_note_meta("specialist-sub", "author-sub") == {
        "specialist_sub": "specialist-sub",
        "author_sub": "author-sub",
    }
