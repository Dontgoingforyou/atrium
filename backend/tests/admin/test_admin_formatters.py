"""Тесты общих форматтеров SQLAdmin (`app.admin.formatters`)."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from types import SimpleNamespace
from typing import Any
from zoneinfo import ZoneInfo

import pytest
from app.admin.formatters import (
    fmt_agreement_status,
    fmt_calendar_attendee_status,
    fmt_calendar_invite_kind,
    fmt_calendar_member_role,
    fmt_calendar_reminder_channel,
    fmt_color,
    fmt_contract_status,
    fmt_contract_type,
    fmt_counterparty_type,
    fmt_datetime,
    fmt_diff,
    fmt_invoice_status,
    fmt_invoice_type,
    fmt_learning_material_status,
    fmt_learning_material_type,
    fmt_payment_category,
    fmt_procurement_status,
    fmt_task_priority,
    fmt_task_status,
    fmt_user_checklist_status,
)
from markupsafe import Markup

_Fmt = Callable[[Any, str], str]


@pytest.mark.parametrize(
    ("fmt", "value", "expected"),
    [
        (fmt_agreement_status, "draft", "Черновик"),
        (fmt_agreement_status, "confirmed", "Подтверждена"),
        (fmt_agreement_status, "completed", "Выполнена"),
        (fmt_agreement_status, "cancelled", "Отменена"),
        (fmt_agreement_status, "unknown", "unknown"),
        (fmt_agreement_status, "", ""),
        (fmt_task_status, "todo", "К выполнению"),
        (fmt_task_status, "in_progress", "В работе"),
        (fmt_task_status, "done", "Готово"),
        (fmt_task_status, "cancelled", "Отменена"),
        (fmt_task_status, "draft", "draft"),
        (fmt_task_status, "", ""),
        (fmt_task_priority, "low", "Низкий"),
        (fmt_task_priority, "medium", "Средний"),
        (fmt_task_priority, "high", "Высокий"),
        (fmt_task_priority, "unknown", "unknown"),
        (fmt_counterparty_type, "vendor", "Поставщик"),
        (fmt_counterparty_type, "client", "Клиент"),
        (fmt_counterparty_type, "partner", "Партнёр"),
        (fmt_contract_type, "template", "Шаблон"),
        (fmt_contract_type, "active", "Действующий"),
        (fmt_contract_status, "draft", "Черновик"),
        (fmt_contract_status, "active", "Активный"),
        (fmt_invoice_type, "invoice", "Счёт"),
        (fmt_invoice_type, "act", "Акт"),
        (fmt_invoice_status, "sent", "Отправлен"),
        (fmt_invoice_status, "paid", "Оплачен"),
        (fmt_payment_category, "contract", "По договору"),
        (fmt_payment_category, "admin_expense", "Административные расходы"),
        (fmt_payment_category, "other", "Прочее"),
        (fmt_procurement_status, "pending_approval", "На согласовании"),
        (fmt_procurement_status, "approved", "Утверждена"),
        (fmt_learning_material_type, "article", "Статья"),
        (fmt_learning_material_type, "video", "Видео"),
        (fmt_learning_material_status, "active", "Опубликован"),
        (fmt_learning_material_status, "", "—"),
        (fmt_user_checklist_status, "in_progress", "В процессе"),
        (fmt_user_checklist_status, "completed", "Завершён"),
        (fmt_calendar_member_role, "editor", "Редактор"),
        (fmt_calendar_member_role, "owner", "Владелец"),
        (fmt_calendar_member_role, "unknown", "unknown"),
        (fmt_calendar_member_role, "", "—"),
        (fmt_calendar_attendee_status, "accepted", "Принято"),
        (fmt_calendar_attendee_status, "", "—"),
        (fmt_calendar_reminder_channel, "telegram", "Telegram"),
        (fmt_calendar_reminder_channel, "portal", "Портал"),
        (fmt_calendar_invite_kind, "share", "Шаринг календаря"),
        (fmt_calendar_invite_kind, "event", "Событие"),
    ],
)
def test_enum_formatters_known_unknown_empty(fmt: _Fmt, value: str, expected: str) -> None:
    assert fmt(SimpleNamespace(field=value), "field") == expected


def test_fmt_agreement_status_missing_attr() -> None:
    assert fmt_agreement_status(SimpleNamespace(), "unknown_attr") == ""


def test_fmt_datetime_none_and_naive() -> None:
    assert fmt_datetime(SimpleNamespace(dt=None), "dt") == "—"
    naive = datetime(2024, 3, 9, 14, 30)
    # naive — деградация: без метки МСК (в БД должны быть aware UTC)
    assert fmt_datetime(SimpleNamespace(dt=naive), "dt") == "09.03.2024 14:30"
    assert "(МСК)" not in fmt_datetime(SimpleNamespace(dt=naive), "dt")


def test_fmt_datetime_non_datetime_and_tz_aware() -> None:
    assert fmt_datetime(SimpleNamespace(dt="не дата"), "dt") == "не дата"

    utc = ZoneInfo("UTC")
    dt_utc = datetime(2024, 6, 1, 9, 0, tzinfo=utc)
    msk = dt_utc.astimezone(ZoneInfo("Europe/Moscow"))
    expected = msk.strftime("%d.%m.%Y %H:%M (МСК)")
    assert fmt_datetime(SimpleNamespace(dt=dt_utc), "dt") == expected


def test_fmt_color() -> None:
    out = fmt_color(SimpleNamespace(color="#aabbcc"), "color")
    assert isinstance(out, Markup)
    assert "background:#aabbcc" in str(out)
    assert "#aabbcc" in str(out)


def test_fmt_color_empty_is_dash_not_empty_background() -> None:
    empty = fmt_color(SimpleNamespace(color=None), "color")
    assert str(empty) == "—"
    assert "background" not in str(empty)


def test_fmt_color_rejects_css_injection() -> None:
    out = fmt_color(SimpleNamespace(color="red;expression(alert(1))"), "color")
    s = str(out)
    assert "background:" not in s
    assert "<span" not in s
    assert "expression" in s


def test_fmt_color_escapes_html() -> None:
    s = str(fmt_color(SimpleNamespace(color='"><script>alert(1)</script>'), "color"))
    assert "<script>" not in s
    assert "background:" not in s
    assert "&lt;script&gt;" in s or "&quot;" in s


def test_fmt_diff_empty() -> None:
    assert str(fmt_diff(SimpleNamespace(d=None), "d")) == "—"
    assert str(fmt_diff(SimpleNamespace(d={}), "d")) == "—"


def test_fmt_diff_old_new_and_plain() -> None:
    out = fmt_diff(
        SimpleNamespace(
            d={
                "title": {"old": "a", "new": "b"},
                "status": {"old": "todo", "new": "done"},
                "custom_field": {"old": None, "new": "x"},
                "raw": "created",
            }
        ),
        "d",
    )
    assert isinstance(out, Markup)
    s = str(out)
    assert "<b>Заголовок</b>: a → b" in s
    assert "<b>Статус</b>: К выполнению → Готово" in s
    assert "<b>custom_field</b>: — → x" in s
    assert "<b>raw</b>: создано" in s
    assert "<br>" in s


def test_fmt_diff_unknown_label_and_none_string() -> None:
    s = str(fmt_diff(SimpleNamespace(d={"unknown_key": {"old": "None", "new": "none"}}), "d"))
    assert "<b>unknown_key</b>: — → —" in s


def test_fmt_diff_escapes_html_in_title() -> None:
    s = str(
        fmt_diff(
            SimpleNamespace(
                d={"title": {"old": "<img onerror=alert(1)>", "new": "<script>x</script>"}},
            ),
            "d",
        )
    )
    assert "<script>" not in s
    assert "<img " not in s
    assert "&lt;img" in s
    assert "&lt;script&gt;" in s
