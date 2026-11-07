"""Форматирование текста уведомления для Telegram."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from app.core.config import Settings
from app.portal_telegram.services.notification_message import format_portal_notification_telegram


def _settings() -> Settings:
    return Settings(
        database_url="sqlite+aiosqlite:///:memory:",
        portal_public_url="https://portal.example.com",
    )


def _author_profile_mock(full_name: str = "Иван Назначивший") -> MagicMock:
    p = MagicMock()
    p.full_name = full_name
    p.email = ""
    p.username = ""
    p.sub = "author-sub"
    return p


def _first_line(text: str) -> str:
    return text.splitlines()[0]


def test_format_task_due_soon_includes_title() -> None:
    tid = uuid4()
    task = MagicMock()
    task.title = "Дедлайн близко"
    task.description = None
    notif = MagicMock()
    notif.type = "task_due_soon"
    notif.task_id = tid
    notif.task = task
    notif.document = None
    notif.document_id = None
    notif.comment = None
    notif.document_comment = None
    notif.author_sub = "author-sub"
    notif.author_profile = _author_profile_mock()
    text, url = format_portal_notification_telegram(notif, _settings())
    assert _first_line(text) == "⏰ Новое уведомление на портале"
    assert "Срок задачи через 2 дня" in text
    assert "Дедлайн близко" in text
    assert f"task={tid}" in url


def test_format_task_overdue_includes_title() -> None:
    tid = uuid4()
    task = MagicMock()
    task.title = "Уже поздно"
    task.description = None
    notif = MagicMock()
    notif.type = "task_overdue"
    notif.task_id = tid
    notif.task = task
    notif.document = None
    notif.document_id = None
    notif.comment = None
    notif.document_comment = None
    notif.author_sub = "author-sub"
    notif.author_profile = _author_profile_mock()
    text, url = format_portal_notification_telegram(notif, _settings())
    assert _first_line(text) == "⏰ Новое уведомление на портале"
    assert "Задача просрочена" in text
    assert "Уже поздно" in text
    assert f"task={tid}" in url


def test_format_task_assigned_includes_title() -> None:
    tid = uuid4()
    task = MagicMock()
    task.title = "Моя задача"
    task.description = None
    notif = MagicMock()
    notif.type = "task_assigned"
    notif.task_id = tid
    notif.task = task
    notif.document = None
    notif.document_id = None
    notif.comment = None
    notif.document_comment = None
    notif.author_sub = "author-sub"
    notif.author_profile = _author_profile_mock()
    text, url = format_portal_notification_telegram(notif, _settings())
    assert _first_line(text) == "📋 Новое уведомление на портале"
    assert "Моя задача" in text
    assert "От:" not in text
    assert f"task={tid}" in url


def test_format_task_assigned_description_preview() -> None:
    tid = uuid4()
    task = MagicMock()
    task.title = "Задача"
    task.description = "Описание задачи для превью в Telegram"
    notif = MagicMock()
    notif.type = "task_assigned"
    notif.task_id = tid
    notif.task = task
    notif.document = None
    notif.document_id = None
    notif.comment = None
    notif.document_comment = None
    notif.author_sub = "author-sub"
    notif.author_profile = _author_profile_mock()
    text, _url = format_portal_notification_telegram(notif, _settings())
    assert "Описание задачи для превью" in text


def test_format_task_assigned_strips_script_from_description() -> None:
    tid = uuid4()
    task = MagicMock()
    task.title = "Задача"
    task.description = "<script>alert(1)</script><p>Безопасный текст</p>"
    notif = MagicMock()
    notif.type = "task_assigned"
    notif.task_id = tid
    notif.task = task
    notif.document = None
    notif.document_id = None
    notif.comment = None
    notif.document_comment = None
    notif.author_sub = "author-sub"
    notif.author_profile = _author_profile_mock()
    text, _url = format_portal_notification_telegram(notif, _settings())
    assert "Безопасный текст" in text
    assert "<script>" not in text
    assert "style=" not in text


def test_format_document_mention_splits_leading_mention_line() -> None:
    did = uuid4()
    doc = MagicMock()
    doc.title = "Документ X"
    comment = MagicMock()
    comment.body = "@Mira Holt привет в документе"
    notif = MagicMock()
    notif.type = "document_mention"
    notif.document_id = did
    notif.document = doc
    notif.task = None
    notif.comment = None
    notif.document_comment = comment
    notif.author_sub = "author-sub"
    notif.author_profile = _author_profile_mock("Комментатор")
    text, url = format_portal_notification_telegram(
        notif,
        _settings(),
        mention_labels_longest_first=["Mira Holt", "Mira"],
    )
    assert _first_line(text) == "📌 Новое уведомление на портале"
    assert "Документ X" in text
    assert "От:" not in text
    assert "«привет в документе»" in text
    assert "@" not in text
    assert f"/documents/{did}" in url


def test_format_task_mention_splits_leading_mention_line() -> None:
    tid = uuid4()
    task = MagicMock()
    task.title = "Задача Y"
    comment = MagicMock()
    comment.body = "@Mira Holt проверьте сроки"
    notif = MagicMock()
    notif.type = "task_mention"
    notif.task_id = tid
    notif.task = task
    notif.document = None
    notif.comment = comment
    notif.document_comment = None
    notif.author_sub = "author-sub"
    notif.author_profile = _author_profile_mock("Автор комментария")
    text, url = format_portal_notification_telegram(
        notif,
        _settings(),
        mention_labels_longest_first=["Mira Holt"],
    )
    assert _first_line(text) == "📌 Новое уведомление на портале"
    assert "Задача Y" in text
    assert "От:" not in text
    assert "«проверьте сроки»" in text
    assert "@" not in text
    assert f"task={tid}" in url


def test_format_task_comment_includes_title_and_preview() -> None:
    tid = uuid4()
    task = MagicMock()
    task.title = "Статус спринта"
    comment = MagicMock()
    comment.body = "Проверьте статус"
    notif = MagicMock()
    notif.type = "task_comment"
    notif.task_id = tid
    notif.task = task
    notif.document = None
    notif.comment = comment
    notif.document_comment = None
    notif.author_sub = "author-sub"
    notif.author_profile = _author_profile_mock()
    text, url = format_portal_notification_telegram(notif, _settings())
    assert _first_line(text) == "💬 Новое уведомление на портале"
    assert "Новый комментарий в задаче: «Статус спринта»" in text
    assert "«Проверьте статус»" in text
    assert f"task={tid}" in url


def test_format_task_mention_strips_at_when_no_label_match() -> None:
    tid = uuid4()
    task = MagicMock()
    task.title = "Задача Y"
    comment = MagicMock()
    comment.body = "Привет @unknown текст"
    notif = MagicMock()
    notif.type = "task_mention"
    notif.task_id = tid
    notif.task = task
    notif.document = None
    notif.comment = comment
    notif.document_comment = None
    notif.author_sub = "author-sub"
    notif.author_profile = _author_profile_mock("Автор")
    text, _url = format_portal_notification_telegram(
        notif,
        _settings(),
        mention_labels_longest_first=[],
    )
    assert "«Привет unknown текст»" in text
    assert "@" not in text


def test_format_unknown_notification_type_fallback() -> None:
    notif = MagicMock()
    notif.type = "unknown_future"
    notif.task = None
    notif.task_id = None
    notif.document = None
    notif.document_id = None
    notif.comment = None
    notif.document_comment = None
    notif.author_sub = "author-sub"
    notif.author_profile = _author_profile_mock()
    text, url = format_portal_notification_telegram(notif, _settings())
    assert _first_line(text) == "🔔 Новое уведомление на портале"
    assert url == "https://portal.example.com"


@pytest.mark.parametrize(
    ("notif_type", "emoji"),
    [
        ("task_assigned", "📋"),
        ("task_due_soon", "⏰"),
        ("task_overdue", "⏰"),
        ("task_comment", "💬"),
        ("document_trashed", "🗑"),
        ("task_mention", "📌"),
        ("document_mention", "📌"),
        ("unknown_future", "🔔"),
    ],
)
def test_format_non_calendar_header_is_portal_default(notif_type: str, emoji: str) -> None:
    notif = MagicMock()
    notif.type = notif_type
    notif.task_id = uuid4()
    notif.task = MagicMock(title="t", description=None)
    notif.document_id = uuid4()
    notif.document = MagicMock(title="d")
    notif.comment = MagicMock(body="c")
    notif.document_comment = MagicMock(body="c")
    notif.author_sub = "author-sub"
    notif.author_profile = _author_profile_mock()
    text, _url = format_portal_notification_telegram(notif, _settings())
    assert _first_line(text) == f"{emoji} Новое уведомление на портале"


def test_format_calendar_reminder_header_is_event() -> None:
    eid = uuid4()
    starts = datetime(2026, 8, 6, 10, 0, tzinfo=UTC)
    notif = SimpleNamespace(
        type="calendar_reminder",
        calendar_event_id=eid,
        calendar_occurrence_starts_at=starts,
        calendar_event=SimpleNamespace(
            title="тест Диана",
            location="в телемосте",
            timezone="UTC",
            starts_at=starts,
        ),
        task=None,
        task_id=None,
        document=None,
        document_id=None,
        comment=None,
        document_comment=None,
        author_sub="author-sub",
        author_profile=_author_profile_mock(),
    )
    insp = MagicMock()
    insp.unloaded = set()
    with patch(
        "app.portal_telegram.services.notification_message.sa_inspect",
        return_value=insp,
    ):
        text, url = format_portal_notification_telegram(notif, _settings())  # type: ignore[arg-type]
    assert _first_line(text) == "📅 Событие!"
    assert "Новое уведомление на портале" not in text
    assert "Напоминание о событии" not in text
    assert "Когда:" not in text
    assert "Место:" not in text
    assert "«тест Диана»" in text
    assert "13:00 МСК" in text
    assert "в телемосте" in text
    assert str(eid) in url
    assert "event=" in url


def test_format_calendar_invite_includes_when_location_and_event_path() -> None:
    eid = uuid4()
    starts = datetime(2026, 8, 20, 13, 35, tzinfo=UTC)
    notif = SimpleNamespace(
        type="calendar_invite",
        calendar_event_id=eid,
        calendar_occurrence_starts_at=starts,
        calendar_event=SimpleNamespace(
            title="созвон",
            location="https://telemost.yandex.ru/j/9",
            timezone="UTC",
            starts_at=starts,
        ),
        task=None,
        task_id=None,
        document=None,
        document_id=None,
        comment=None,
        document_comment=None,
        author_sub="author-sub",
        author_profile=_author_profile_mock(),
    )
    insp = MagicMock()
    insp.unloaded = set()
    with patch(
        "app.portal_telegram.services.notification_message.sa_inspect",
        return_value=insp,
    ):
        text, url = format_portal_notification_telegram(notif, _settings())  # type: ignore[arg-type]
    assert _first_line(text) == "📅 Событие!"
    assert "Вас пригласили на событие" not in text
    assert "Когда:" not in text
    assert "Место:" not in text
    assert "«созвон»" in text
    assert "20.08.2026 16:35 МСК" in text
    assert "telemost" in text
    assert str(eid) in url


def _calendar_notif(
    *,
    notif_type: str,
    title: str,
    location: str | None,
    description: str | None,
) -> SimpleNamespace:
    starts = datetime(2026, 8, 20, 13, 35, tzinfo=UTC)
    eid = uuid4()
    return SimpleNamespace(
        type=notif_type,
        calendar_event_id=eid,
        calendar_occurrence_starts_at=starts,
        calendar_event=SimpleNamespace(
            title=title,
            location=location,
            description=description,
            timezone="UTC",
            starts_at=starts,
        ),
        task=None,
        task_id=None,
        document=None,
        document_id=None,
        comment=None,
        document_comment=None,
        author_sub="author-sub",
        author_profile=_author_profile_mock(),
    )


def test_format_calendar_invite_appends_url_from_description_only() -> None:
    notif = _calendar_notif(
        notif_type="calendar_invite",
        title="созвон",
        location=None,
        description="повестка и https://telemost.yandex.ru/j/desc остальные заметки",
    )
    insp = MagicMock()
    insp.unloaded = set()
    with patch(
        "app.portal_telegram.services.notification_message.sa_inspect",
        return_value=insp,
    ):
        text, _url = format_portal_notification_telegram(notif, _settings())  # type: ignore[arg-type]
    assert "https://telemost.yandex.ru/j/desc" in text
    assert "повестка" not in text
    assert "остальные заметки" not in text
    assert "«созвон»" in text
    assert "20.08.2026 16:35 МСК" in text
    assert text.rstrip().endswith("https://telemost.yandex.ru/j/desc")


def test_format_calendar_reminder_keeps_location_and_adds_description_url() -> None:
    notif = _calendar_notif(
        notif_type="calendar_reminder",
        title="стендап",
        location="Переговорка 3",
        description="ссылка https://zoom.us/j/555",
    )
    insp = MagicMock()
    insp.unloaded = set()
    with patch(
        "app.portal_telegram.services.notification_message.sa_inspect",
        return_value=insp,
    ):
        text, _url = format_portal_notification_telegram(notif, _settings())  # type: ignore[arg-type]
    assert "Переговорка 3" in text
    assert "https://zoom.us/j/555" in text
    assert text.count("https://zoom.us/j/555") == 1


def test_format_calendar_invite_does_not_duplicate_location_url() -> None:
    telemost = "https://telemost.yandex.ru/j/9"
    notif = _calendar_notif(
        notif_type="calendar_invite",
        title="созвон",
        location=telemost,
        description=f"дубль {telemost}",
    )
    insp = MagicMock()
    insp.unloaded = set()
    with patch(
        "app.portal_telegram.services.notification_message.sa_inspect",
        return_value=insp,
    ):
        text, _url = format_portal_notification_telegram(notif, _settings())  # type: ignore[arg-type]
    assert text.count(telemost) == 1


def test_format_calendar_reminder_no_empty_line_without_url() -> None:
    notif = _calendar_notif(
        notif_type="calendar_reminder",
        title="тест Диана",
        location="в телемосте",
        description="без ссылки",
    )
    insp = MagicMock()
    insp.unloaded = set()
    with patch(
        "app.portal_telegram.services.notification_message.sa_inspect",
        return_value=insp,
    ):
        text, _url = format_portal_notification_telegram(notif, _settings())  # type: ignore[arg-type]
    assert "в телемосте" in text
    assert "https://" not in text
    assert "без ссылки" not in text
    assert "«тест Диана»" in text


def test_format_task_assigned_without_task_model_uses_default_title() -> None:
    tid = uuid4()
    notif = MagicMock()
    notif.type = "task_assigned"
    notif.task_id = tid
    notif.task = None
    notif.document = None
    notif.document_id = None
    notif.comment = None
    notif.document_comment = None
    notif.author_sub = "author-sub"
    notif.author_profile = _author_profile_mock()
    text, url = format_portal_notification_telegram(notif, _settings())
    assert "задача" in text.lower()
    assert f"task={tid}" in url


def test_format_task_assigned_missing_task_id_empty_path() -> None:
    task = MagicMock()
    task.title = "Без id"
    task.description = None
    notif = MagicMock()
    notif.type = "task_assigned"
    notif.task_id = None
    notif.task = task
    notif.document = None
    notif.document_id = None
    notif.comment = None
    notif.document_comment = None
    notif.author_sub = "author-sub"
    notif.author_profile = _author_profile_mock()
    _text, url = format_portal_notification_telegram(notif, _settings())
    assert "/tasks/" not in url
    assert url == "https://portal.example.com"


def test_format_document_mention_without_document_id() -> None:
    doc = MagicMock()
    doc.title = "Док без id в поле"
    notif = MagicMock()
    notif.type = "document_mention"
    notif.document_id = None
    notif.document = doc
    notif.task = None
    notif.comment = None
    notif.document_comment = MagicMock()
    notif.document_comment.body = "комментарий"
    notif.author_sub = "author-sub"
    notif.author_profile = _author_profile_mock()
    _text, url = format_portal_notification_telegram(notif, _settings())
    assert "/documents/" not in url
