"""Конвертер полей WTForms для SQLAdmin: русские подписи у перечислений портала."""

from __future__ import annotations

import enum
from typing import Any, cast

from sqladmin.forms import ModelConverter, converts
from sqlalchemy.orm import ColumnProperty
from wtforms import SelectField, validators

from app.admin.enum_labels import (
    AGREEMENT_STATUS_LABELS_RU,
    CONTRACT_STATUS_LABELS_RU,
    CONTRACT_TYPE_LABELS_RU,
    COUNTERPARTY_TYPE_LABELS_RU,
    INVOICE_STATUS_LABELS_RU,
    INVOICE_TYPE_LABELS_RU,
    PAYMENT_CATEGORY_LABELS_RU,
    PROCUREMENT_STATUS_LABELS_RU,
    TASK_PRIORITY_LABELS_RU,
)
from app.core.enums import (
    AgreementStatus,
    ContractStatus,
    ContractType,
    CounterpartyType,
    InvoiceStatus,
    InvoiceType,
    PaymentCategory,
    ProcurementStatus,
    TaskPriority,
)

# Единственное место, где перечисление БД получает русские подписи в форме SQLAdmin:
# добавляя сюда новый портальный Enum-столбец, не нужно писать form_overrides в самой вьюхе.
_ENUM_LABELS_BY_CLASS: dict[type[enum.Enum], dict[str, str]] = {
    AgreementStatus: AGREEMENT_STATUS_LABELS_RU,
    TaskPriority: TASK_PRIORITY_LABELS_RU,
    CounterpartyType: COUNTERPARTY_TYPE_LABELS_RU,
    ContractType: CONTRACT_TYPE_LABELS_RU,
    ContractStatus: CONTRACT_STATUS_LABELS_RU,
    InvoiceType: INVOICE_TYPE_LABELS_RU,
    InvoiceStatus: INVOICE_STATUS_LABELS_RU,
    PaymentCategory: PAYMENT_CATEGORY_LABELS_RU,
    ProcurementStatus: PROCUREMENT_STATUS_LABELS_RU,
}


def _coerce_to_enum_member(py_enum: type[enum.Enum], value: Any) -> Any:
    """Значение из формы (имя DRAFT, значение draft или сам член) → член enum."""
    if value is None or value == "":
        return None
    if isinstance(value, py_enum):
        return value
    s = str(value)
    if s in py_enum.__members__:
        return py_enum[s]
    try:
        return py_enum(s)
    except ValueError as exc:
        raise ValueError(f"Недопустимое значение перечисления: {value!r}") from exc


class AtriumAdminModelConverter(ModelConverter):
    """Подмена conv_enum для перечислений портала (иначе sqladmin показывает DRAFT без перевода)."""

    @converts("Enum")  # type: ignore[untyped-decorator]
    def conv_enum(
        self,
        model: type,
        prop: ColumnProperty[Any],
        kwargs: dict[str, Any],
    ) -> SelectField:
        column = prop.columns[0]
        py_enum: type[enum.Enum] | None = getattr(column.type, "enum_class", None)

        if py_enum is not None and py_enum in _ENUM_LABELS_BY_CLASS:
            return self._select_enum_field(
                prop=prop,
                kwargs=kwargs,
                enum_cls=py_enum,
                labels=_ENUM_LABELS_BY_CLASS[py_enum],
            )
        return cast(SelectField, super().conv_enum(model, prop, kwargs))

    def _select_enum_field(
        self,
        *,
        prop: ColumnProperty[Any],
        kwargs: dict[str, Any],
        enum_cls: type[enum.Enum],
        labels: dict[str, str],
    ) -> SelectField:
        """В option value — имя члена (DRAFT), в БД через ORM уходит как у стандартного Enum SQLAlchemy."""
        column = prop.columns[0]
        choices = [(m.name, labels[m.value]) for m in enum_cls]
        members: list[enum.Enum | None] = [m for m in enum_cls]

        if column.nullable:
            kwargs["allow_blank"] = True
            members.append(None)
            filters = kwargs.get("filters", [])
            filters.append(lambda x: x or None)
            kwargs["filters"] = filters

        kwargs["choices"] = choices
        kwargs.setdefault("validators", [])
        kwargs["validators"].append(validators.AnyOf(members))
        kwargs["coerce"] = lambda v: _coerce_to_enum_member(enum_cls, v)
        return SelectField(**kwargs)
