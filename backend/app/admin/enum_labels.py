"""Единый источник русских подписей для enum-полей портала в SQLAdmin.

Используется и формой (``model_converter.CosmoletAdminModelConverter``,
``form_args["choices"]`` для полей без SQLAlchemy Enum-типа), и форматтерами
списков/деталей (``formatters.py``) — не дублировать подписи в разных модулях.
"""

from __future__ import annotations

AGREEMENT_STATUS_LABELS_RU: dict[str, str] = {
    "draft": "Черновик",
    "confirmed": "Подтверждена",
    "completed": "Выполнена",
    "cancelled": "Отменена",
}

TASK_STATUS_LABELS_RU: dict[str, str] = {
    "todo": "К выполнению",
    "in_progress": "В работе",
    "done": "Готово",
    "cancelled": "Отменена",
}

TASK_PRIORITY_LABELS_RU: dict[str, str] = {
    "low": "Низкий",
    "medium": "Средний",
    "high": "Высокий",
}

COUNTERPARTY_TYPE_LABELS_RU: dict[str, str] = {
    "vendor": "Поставщик",
    "client": "Клиент",
    "partner": "Партнёр",
}

CONTRACT_TYPE_LABELS_RU: dict[str, str] = {
    "template": "Шаблон",
    "active": "Действующий",
}

CONTRACT_STATUS_LABELS_RU: dict[str, str] = {
    "draft": "Черновик",
    "active": "Активный",
    "completed": "Завершён",
    "cancelled": "Отменён",
}

INVOICE_TYPE_LABELS_RU: dict[str, str] = {
    "invoice": "Счёт",
    "act": "Акт",
}

INVOICE_STATUS_LABELS_RU: dict[str, str] = {
    "draft": "Черновик",
    "sent": "Отправлен",
    "paid": "Оплачен",
    "overdue": "Просрочен",
    "cancelled": "Отменён",
}

PAYMENT_CATEGORY_LABELS_RU: dict[str, str] = {
    "contract": "По договору",
    "admin_expense": "Административные расходы",
    "other": "Прочее",
}

PROCUREMENT_STATUS_LABELS_RU: dict[str, str] = {
    "draft": "Черновик",
    "pending_approval": "На согласовании",
    "approved": "Утверждена",
    "rejected": "Отклонена",
    "in_progress": "В работе",
    "completed": "Завершена",
    "cancelled": "Отменена",
}

LEARNING_MATERIAL_TYPE_LABELS_RU: dict[str, str] = {
    "article": "Статья",
    "video": "Видео",
    "presentation": "Презентация",
    "instruction": "Инструкция",
}

LEARNING_MATERIAL_STATUS_LABELS_RU: dict[str, str] = {
    "draft": "Черновик",
    "active": "Опубликован",
    "archived": "Архив",
}

USER_CHECKLIST_STATUS_LABELS_RU: dict[str, str] = {
    "in_progress": "В процессе",
    "completed": "Завершён",
}

CALENDAR_MEMBER_ROLE_LABELS_RU: dict[str, str] = {
    "owner": "Владелец",
    "editor": "Редактор",
    "viewer": "Наблюдатель",
}

CALENDAR_ATTENDEE_STATUS_LABELS_RU: dict[str, str] = {
    "pending": "Ожидает",
    "accepted": "Принято",
    "declined": "Отклонено",
    "tentative": "Под вопросом",
}

CALENDAR_REMINDER_CHANNEL_LABELS_RU: dict[str, str] = {
    "portal": "Портал",
    "telegram": "Telegram",
    "email": "Email",
}

CALENDAR_INVITE_KIND_LABELS_RU: dict[str, str] = {
    "event": "Событие",
    "share": "Шаринг календаря",
}
