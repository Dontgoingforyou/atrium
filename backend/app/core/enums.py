from enum import StrEnum
from typing import Literal

PresenceState = Literal["offline", "online", "away"]
"""Статус присутствия пользователя (Redis, эфемерный — не хранится в БД)."""


class FavoriteTargetType(StrEnum):
    """Тип объекта в избранном пользователя портала."""

    DOCUMENT = "document"
    NAVIGATION_NODE = "navigation_node"


class AgreementStatus(StrEnum):
    """Статус договорённости."""

    DRAFT = "draft"
    CONFIRMED = "confirmed"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class TaskStatus(StrEnum):
    """Статус задачи портала."""

    TODO = "todo"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    CANCELLED = "cancelled"


class TaskPriority(StrEnum):
    """Приоритет задачи."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class CounterpartyType(StrEnum):
    """Тип контрагента."""

    VENDOR = "vendor"  # Поставщик / исполнитель
    CLIENT = "client"  # Клиент
    PARTNER = "partner"  # Партнёр


class ContractType(StrEnum):
    """Тип договора."""

    TEMPLATE = "template"  # Шаблон
    ACTIVE = "active"  # Действующий


class ContractStatus(StrEnum):
    """Статус договора."""

    DRAFT = "draft"
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class InvoiceType(StrEnum):
    """Тип финансового документа."""

    INVOICE = "invoice"  # Счёт на оплату
    ACT = "act"  # Акт выполненных работ


class InvoiceStatus(StrEnum):
    """Статус счёта / акта."""

    DRAFT = "draft"
    SENT = "sent"
    PAID = "paid"
    OVERDUE = "overdue"
    CANCELLED = "cancelled"


class PaymentCategory(StrEnum):
    """Категория платежа."""

    CONTRACT = "contract"  # По договору
    ADMIN_EXPENSE = "admin_expense"  # Административные расходы
    OTHER = "other"


class ProcurementStatus(StrEnum):
    """Статус закупочной заявки."""

    DRAFT = "draft"  # Черновик
    PENDING_APPROVAL = "pending_approval"  # На согласовании
    APPROVED = "approved"  # Утверждена
    REJECTED = "rejected"  # Отклонена
    IN_PROGRESS = "in_progress"  # В работе
    COMPLETED = "completed"  # Завершена
    CANCELLED = "cancelled"  # Отменена


# ─── Обучение и проверка знаний ────────────────────────────────────


class LearningMaterialType(StrEnum):
    """Тип учебного материала."""

    ARTICLE = "article"  # Статья / текст
    VIDEO = "video"  # Видео
    PRESENTATION = "presentation"  # Презентация
    INSTRUCTION = "instruction"  # Инструкция


class LearningMaterialStatus(StrEnum):
    """Статус учебного материала."""

    DRAFT = "draft"
    ACTIVE = "active"
    ARCHIVED = "archived"


class UserChecklistStatus(StrEnum):
    """Статус прохождения чек-листа пользователем."""

    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


# ─── Календарь ─────────────────────────────────────────────────────


class CalendarMemberRole(StrEnum):
    """Роль участника календаря."""

    OWNER = "owner"
    EDITOR = "editor"
    VIEWER = "viewer"


class CalendarAttendeeStatus(StrEnum):
    """Статус участника события (колонка legacy; новые записи — accepted)."""

    PENDING = "pending"
    ACCEPTED = "accepted"
    DECLINED = "declined"
    TENTATIVE = "tentative"


class CalendarInviteKind(StrEnum):
    """Тип invite-токена календаря."""

    EVENT = "event"
    SHARE = "share"


class CalendarReminderChannel(StrEnum):
    """Канал напоминания о событии."""

    PORTAL = "portal"
    TELEGRAM = "telegram"
    EMAIL = "email"
