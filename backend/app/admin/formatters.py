"""Общие форматтеры для SQLAdmin-представлений."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from markupsafe import Markup, escape

from app.admin.enum_labels import (
    AGREEMENT_STATUS_LABELS_RU,
    CALENDAR_ATTENDEE_STATUS_LABELS_RU,
    CALENDAR_INVITE_KIND_LABELS_RU,
    CALENDAR_MEMBER_ROLE_LABELS_RU,
    CALENDAR_REMINDER_CHANNEL_LABELS_RU,
    CONTRACT_STATUS_LABELS_RU,
    CONTRACT_TYPE_LABELS_RU,
    COUNTERPARTY_TYPE_LABELS_RU,
    INVOICE_STATUS_LABELS_RU,
    INVOICE_TYPE_LABELS_RU,
    LEARNING_MATERIAL_STATUS_LABELS_RU,
    LEARNING_MATERIAL_TYPE_LABELS_RU,
    PAYMENT_CATEGORY_LABELS_RU,
    PROCUREMENT_STATUS_LABELS_RU,
    TASK_PRIORITY_LABELS_RU,
    TASK_STATUS_LABELS_RU,
    USER_CHECKLIST_STATUS_LABELS_RU,
)

_MOSCOW_TZ = ZoneInfo("Europe/Moscow")
_HEX_COLOR_RE = re.compile(r"^#(?:[0-9A-Fa-f]{3,4}|[0-9A-Fa-f]{6}|[0-9A-Fa-f]{8})$")


def fmt_datetime(model: Any, attr: str) -> str:
    """Форматировать datetime в читаемый вид (МСК)."""
    value = getattr(model, attr, None)
    if value is None:
        return "—"
    if not isinstance(value, datetime):
        return str(value)
    if value.tzinfo is None:
        return value.strftime("%d.%m.%Y %H:%M")
    return value.astimezone(_MOSCOW_TZ).strftime("%d.%m.%Y %H:%M (МСК)")


def fmt_color(model: Any, attr: str) -> Markup:
    """Форматировать hex-цвет: цветной квадратик + значение."""
    raw = getattr(model, attr, None)
    val = str(raw).strip() if raw is not None else ""
    if not val:
        return Markup("—")
    safe_text = escape(val)
    if not _HEX_COLOR_RE.fullmatch(val):
        return Markup(safe_text)
    return Markup(
        f'<span style="display:inline-block;width:14px;height:14px;'
        f"background:{val};border:1px solid #ccc;border-radius:3px;"
        f'vertical-align:middle;margin-right:6px"></span>{safe_text}'
    )


def fmt_agreement_status(model: Any, attr: str) -> str:
    """Форматировать статус договорённости на русском."""
    val = str(getattr(model, attr, "") or "")
    return AGREEMENT_STATUS_LABELS_RU.get(val, val)


def fmt_task_status(model: Any, attr: str) -> str:
    """Форматировать статус задачи на русском."""
    val = str(getattr(model, attr, "") or "")
    return TASK_STATUS_LABELS_RU.get(val, val)


def fmt_task_priority(model: Any, attr: str) -> str:
    """Форматировать приоритет задачи на русском."""
    val = str(getattr(model, attr, "") or "")
    return TASK_PRIORITY_LABELS_RU.get(val, val)


def fmt_counterparty_type(model: Any, attr: str) -> str:
    """Форматировать тип контрагента на русском."""
    val = str(getattr(model, attr, "") or "")
    return COUNTERPARTY_TYPE_LABELS_RU.get(val, val)


def fmt_contract_type(model: Any, attr: str) -> str:
    """Форматировать тип договора на русском."""
    val = str(getattr(model, attr, "") or "")
    return CONTRACT_TYPE_LABELS_RU.get(val, val)


def fmt_contract_status(model: Any, attr: str) -> str:
    """Форматировать статус договора на русском."""
    val = str(getattr(model, attr, "") or "")
    return CONTRACT_STATUS_LABELS_RU.get(val, val)


def fmt_invoice_type(model: Any, attr: str) -> str:
    """Форматировать тип счёта/акта на русском."""
    val = str(getattr(model, attr, "") or "")
    return INVOICE_TYPE_LABELS_RU.get(val, val)


def fmt_invoice_status(model: Any, attr: str) -> str:
    """Форматировать статус счёта/акта на русском."""
    val = str(getattr(model, attr, "") or "")
    return INVOICE_STATUS_LABELS_RU.get(val, val)


def fmt_payment_category(model: Any, attr: str) -> str:
    """Форматировать категорию платежа на русском."""
    val = str(getattr(model, attr, "") or "")
    return PAYMENT_CATEGORY_LABELS_RU.get(val, val)


def fmt_procurement_status(model: Any, attr: str) -> str:
    """Форматировать статус закупочной заявки на русском."""
    val = str(getattr(model, attr, "") or "")
    return PROCUREMENT_STATUS_LABELS_RU.get(val, val)


def fmt_learning_material_type(model: Any, attr: str) -> str:
    """Форматировать тип учебного материала на русском."""
    val = str(getattr(model, attr, "") or "").lower()
    return LEARNING_MATERIAL_TYPE_LABELS_RU.get(val, val or "—")


def fmt_learning_material_status(model: Any, attr: str) -> str:
    """Форматировать статус учебного материала на русском."""
    val = str(getattr(model, attr, "") or "").lower()
    return LEARNING_MATERIAL_STATUS_LABELS_RU.get(val, val or "—")


def fmt_user_checklist_status(model: Any, attr: str) -> str:
    """Форматировать статус прохождения чек-листа на русском."""
    val = str(getattr(model, attr, "") or "").lower()
    return USER_CHECKLIST_STATUS_LABELS_RU.get(val, val or "—")


def fmt_calendar_member_role(model: Any, attr: str) -> str:
    val = str(getattr(model, attr, "") or "")
    return CALENDAR_MEMBER_ROLE_LABELS_RU.get(val, val or "—")


def fmt_calendar_attendee_status(model: Any, attr: str) -> str:
    val = str(getattr(model, attr, "") or "")
    return CALENDAR_ATTENDEE_STATUS_LABELS_RU.get(val, val or "—")


def fmt_calendar_reminder_channel(model: Any, attr: str) -> str:
    val = str(getattr(model, attr, "") or "")
    return CALENDAR_REMINDER_CHANNEL_LABELS_RU.get(val, val or "—")


def fmt_calendar_invite_kind(model: Any, attr: str) -> str:
    val = str(getattr(model, attr, "") or "")
    return CALENDAR_INVITE_KIND_LABELS_RU.get(val, val or "—")


_DIFF_FIELD_LABELS: dict[str, str] = {
    "action": "Действие",
    "status": "Статус",
    "priority": "Приоритет",
    "title": "Заголовок",
    "body": "Текст",
    "description": "Описание",
    "due_at": "Срок",
    "assignee_sub": "Исполнитель",
    "creator_sub": "Создатель",
}

_DIFF_VALUE_RU: dict[str, str] = {
    **AGREEMENT_STATUS_LABELS_RU,
    **TASK_STATUS_LABELS_RU,
    **TASK_PRIORITY_LABELS_RU,
    "created": "создано",
    "updated": "обновлено",
    "deleted": "удалено",
    "None": "—",
    "none": "—",
    "": "—",
}


def fmt_diff(model: Any, attr: str) -> Markup:
    """Форматировать diff-словарь изменений в читаемый вид."""
    diff = getattr(model, attr, None) or {}
    if not diff:
        return Markup("—")
    lines: list[str] = []
    for field, change in diff.items():
        label = _DIFF_FIELD_LABELS.get(field, field)
        if isinstance(change, dict) and "old" in change and "new" in change:
            old_raw = str(change["old"]) if change["old"] is not None else ""
            new_raw = str(change["new"]) if change["new"] is not None else ""
            old = _DIFF_VALUE_RU.get(old_raw, old_raw or "—")
            new = _DIFF_VALUE_RU.get(new_raw, new_raw or "—")
            lines.append(f"<b>{escape(label)}</b>: {escape(old)} → {escape(new)}")
        else:
            val_raw = str(change) if change is not None else ""
            val = _DIFF_VALUE_RU.get(val_raw, val_raw or "—")
            lines.append(f"<b>{escape(label)}</b>: {escape(val)}")
    return Markup("<br>".join(lines))
