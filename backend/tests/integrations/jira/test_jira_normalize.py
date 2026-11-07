"""Модульные тесты нормализации полей Jira (`app.integrations.jira.normalize`)."""

from __future__ import annotations

from typing import Any

import pytest
from app.integrations.jira.fields import (
    CF_CONTACTS,
    CF_CV,
    CF_CV_AU,
    CF_GROUP,
    CF_HR,
    CF_INTERVIEW_INFO,
    CF_TELEGRAM,
    issue_key_regex,
)
from app.integrations.jira.normalize import (
    extract_jira_field_text,
    extract_link_urls,
    filter_jira_groups_for_display,
    get_field_value,
    is_http_url,
    normalize_issue_fields,
    parse_jira_date,
)


def test_extract_jira_field_text_user_with_name_and_email() -> None:
    value = {"displayName": "Иван", "emailAddress": "ivan@example.com"}
    assert extract_jira_field_text("assignee", value) == "Иван (ivan@example.com)"


def test_extract_jira_field_text_user_name_only() -> None:
    assert extract_jira_field_text("reporter", {"displayName": "Иван"}) == "Иван"


def test_extract_jira_field_text_user_email_only() -> None:
    assert extract_jira_field_text("creator", {"emailAddress": "ivan@example.com"}) == "ivan@example.com"


def test_extract_jira_field_text_user_invalid_type() -> None:
    assert extract_jira_field_text("assignee", "not-a-dict") is None


def test_extract_jira_field_text_multi_users() -> None:
    users = [
        {"displayName": "А", "emailAddress": "a@x.com"},
        {"displayName": "Б"},
        "строка",
        {"name": ""},
    ]
    assert extract_jira_field_text(CF_HR, users) == "А (a@x.com); Б; строка"


def test_extract_jira_field_text_status_and_priority() -> None:
    assert extract_jira_field_text("status", {"name": "Новичок"}) == "Новичок"
    assert extract_jira_field_text("priority", [{"value": "High"}, {"name": "Low"}]) == "High, Low"


def test_extract_jira_field_text_labels_and_fix_versions() -> None:
    assert extract_jira_field_text("labels", ["alpha", "beta"]) == "alpha, beta"
    assert extract_jira_field_text("fixVersions", [{"name": "1.0"}, {"value": "2.0"}]) == "1.0, 2.0"


def test_extract_jira_field_text_customfield_users_and_options() -> None:
    assert extract_jira_field_text(CF_GROUP, [{"value": "A"}, {"value": "B"}]) == "A, B"
    assert extract_jira_field_text(CF_GROUP, {"displayName": "Менеджер"}) == "Менеджер"
    assert extract_jira_field_text(CF_CONTACTS, ["контакт1", "", "контакт2"]) == "контакт1, контакт2"


def test_extract_jira_field_text_empty_values() -> None:
    assert extract_jira_field_text("summary", None) is None
    assert extract_jira_field_text("summary", "   ") is None
    assert extract_jira_field_text("summary", {}) is None
    assert extract_jira_field_text(CF_CONTACTS, []) is None
    assert extract_jira_field_text(CF_GROUP, {}) is None


def test_extract_jira_field_text_numeric_fallback() -> None:
    assert extract_jira_field_text("environment", 42) == "42"


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("2024-06-15", "2024-06-15"),
        ("15.06.2024", "2024-06-15"),
        ("15-06-2024", "2024-06-15"),
        ("not-a-date", None),
        ("", None),
        (None, None),
        (123, None),
    ],
)
def test_parse_jira_date(raw: str | None, expected: str | None) -> None:
    result = parse_jira_date(raw)
    assert (None if result is None else result.isoformat()) == expected


def test_extract_link_urls_skips_empty_and_non_string() -> None:
    fields: dict[str, Any] = {
        CF_CV: "   ",
        CF_INTERVIEW_INFO: 123,
        "customfield_unused": "https://ignored.example",
    }
    assert extract_link_urls(fields) == []


def test_issue_key_regex_follows_project_key() -> None:
    assert issue_key_regex("BASE") == r"^BASE-\d+$"
    assert issue_key_regex("autasks") == r"^AUTASKS-\d+$"
    import re

    assert re.compile(issue_key_regex("FOO.BAR")).match("FOO.BAR-9")
    assert re.compile(issue_key_regex("FOO.BAR")).match("FOOXBAR-9") is None
    assert issue_key_regex("") == r"^BASE-\d+$"
    assert issue_key_regex("   ") == r"^BASE-\d+$"


def test_extract_link_urls_collects_only_http_urls() -> None:
    fields = {
        CF_CV: "https://example.com/cv.pdf",
        CF_CV_AU: "javascript:alert(1)",
        CF_INTERVIEW_INFO: "data:text/html,<script>alert(1)</script>",
    }
    assert extract_link_urls(fields) == [
        ("CV", "https://example.com/cv.pdf"),
    ]


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("https://example.com/x", True),
        ("http://example.com", True),
        ("javascript:alert(1)", False),
        ("data:text/html,<script>", False),
        ("ftp://files.example/info", False),
        ("https://", False),
        ("//evil.com", False),
    ],
)
def test_is_http_url(url: str, expected: bool) -> None:
    assert is_http_url(url) is expected


def test_get_field_value() -> None:
    raw = {CF_TELEGRAM: "@user"}
    assert get_field_value(raw, CF_TELEGRAM) == "@user"
    assert get_field_value(raw, "missing") is None


def test_normalize_issue_fields_user_kind_and_url_kind() -> None:
    issue = {
        "key": "BASE-10",
        "fields": {
            "summary": "Тест",
            "assignee": {"displayName": "Исполнитель"},
            "description": "https://docs.example.com/readme",
        },
        "names": {},
    }
    data = normalize_issue_fields(issue)
    people = next(g for g in data["groups"] if g["key"] == "people")
    assignee = next(f for f in people["fields"] if f["id"] == "assignee")
    assert assignee["kind"] == "user"
    other = next(g for g in data["groups"] if g["key"] == "other")
    description = next(f for f in other["fields"] if f["id"] == "description")
    assert description["kind"] == "url"


def test_normalize_issue_fields_skips_group_without_fields(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "app.integrations.jira.normalize.GROUP_LABELS",
        {"profile": "Профиль", "empty": "Пустая"},
    )
    data = normalize_issue_fields({"key": "BASE-1", "fields": {"summary": "X"}, "names": {}})
    keys = {g["key"] for g in data["groups"]}
    assert "empty" not in keys


def test_filter_jira_groups_for_display_none_and_all_hidden() -> None:
    assert filter_jira_groups_for_display(None) == []
    hidden_only = [
        {
            "key": "profile",
            "label": "Профиль",
            "fields": [{"id": CF_TELEGRAM, "label": "Telegram", "value": "@x", "kind": "text"}],
        },
    ]
    assert filter_jira_groups_for_display(hidden_only) == []


def test_extract_jira_field_text_option_edge_cases() -> None:
    assert extract_jira_field_text("status", None) is None
    assert extract_jira_field_text("status", [{}, {"value": ""}]) is None
    assert extract_jira_field_text("priority", [{}, {"name": ""}]) is None
    assert extract_jira_field_text(CF_GROUP, "  x  ") == "x"
    assert extract_jira_field_text("environment", "   ") is None
    assert extract_jira_field_text(CF_GROUP, {"id": "opt-only"}) is None


def test_filter_jira_groups_applies_portal_label() -> None:
    groups = [
        {
            "key": "profile",
            "label": "Профиль",
            "fields": [{"id": "summary", "label": "Тема", "value": "Иван", "kind": "text"}],
        },
    ]
    out = filter_jira_groups_for_display(groups)
    assert out[0]["fields"][0]["label"] == "ФИО"


def test_filter_jira_groups_keeps_unknown_field_label() -> None:
    groups = [
        {
            "key": "other",
            "label": "Прочее",
            "fields": [{"id": "custom_unknown", "label": "Своё имя", "value": "v", "kind": "text"}],
        },
    ]
    out = filter_jira_groups_for_display(groups)
    assert out[0]["fields"][0]["label"] == "Своё имя"
