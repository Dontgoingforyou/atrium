"""Тесты конвертера enum-полей SQLAdmin (`app.admin.model_converter`)."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest
from app.admin.model_converter import (
    _ENUM_LABELS_BY_CLASS,
    CosmoletAdminModelConverter,
    _coerce_to_enum_member,
)
from app.core.enums import AgreementStatus, TaskPriority
from app.infrastructure.db.models.portal_agreement import PortalAgreement
from sqlalchemy.orm import class_mapper
from wtforms import validators
from wtforms.validators import ValidationError


def _fake_prop(*, enum_class: type, nullable: bool) -> Any:
    column = SimpleNamespace(type=SimpleNamespace(enum_class=enum_class), nullable=nullable)
    return SimpleNamespace(columns=[column])


def test_enum_labels_cover_every_member() -> None:
    for enum_cls, labels in _ENUM_LABELS_BY_CLASS.items():
        for member in enum_cls:
            assert member.value in labels, f"{enum_cls.__name__}.{member.name}={member.value!r}"


@pytest.mark.parametrize("enum_cls", list(_ENUM_LABELS_BY_CLASS))
def test_conv_enum_builds_localized_select_field(enum_cls: type) -> None:
    labels = _ENUM_LABELS_BY_CLASS[enum_cls]
    expected_choices = [(m.name, labels[m.value]) for m in enum_cls]
    converter = CosmoletAdminModelConverter()
    field = converter.conv_enum(object, _fake_prop(enum_class=enum_cls, nullable=False), {})

    assert field.kwargs["choices"] == expected_choices
    assert "allow_blank" not in field.kwargs


def test_conv_enum_nullable_column_allows_blank() -> None:
    converter = CosmoletAdminModelConverter()
    field = converter.conv_enum(object, _fake_prop(enum_class=TaskPriority, nullable=True), {})

    assert field.kwargs["allow_blank"] is True
    assert None in field.kwargs["validators"][0].values


def test_conv_enum_unknown_enum_falls_back_to_base_converter(monkeypatch: pytest.MonkeyPatch) -> None:
    """Для перечислений без записи в `_ENUM_LABELS_BY_CLASS` — стандартное поведение sqladmin."""
    import app.admin.model_converter as mc

    sentinel = object()
    monkeypatch.setattr(mc.ModelConverter, "conv_enum", lambda self, model, prop, kwargs: sentinel)
    converter = mc.CosmoletAdminModelConverter()
    prop = _fake_prop(enum_class=AgreementStatus, nullable=False)
    monkeypatch.delitem(mc._ENUM_LABELS_BY_CLASS, AgreementStatus)

    assert converter.conv_enum(object, prop, {}) is sentinel


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("LOW", TaskPriority.LOW),
        ("low", TaskPriority.LOW),
        (TaskPriority.HIGH, TaskPriority.HIGH),
        (None, None),
        ("", None),
        ("DRAFT", AgreementStatus.DRAFT),
        ("draft", AgreementStatus.DRAFT),
        (AgreementStatus.DRAFT, AgreementStatus.DRAFT),
    ],
)
def test_coerce_to_enum_member(value: Any, expected: object) -> None:
    if expected is None:
        assert _coerce_to_enum_member(TaskPriority, value) is None
    elif isinstance(expected, AgreementStatus):
        assert _coerce_to_enum_member(AgreementStatus, value) is expected
    else:
        assert _coerce_to_enum_member(TaskPriority, value) is expected


def test_coerce_to_enum_member_invalid_value_raises() -> None:
    with pytest.raises(ValueError, match="Недопустимое значение"):
        _coerce_to_enum_member(TaskPriority, "not-a-priority")


def test_conv_enum_validator_rejects_foreign_enum_member() -> None:
    converter = CosmoletAdminModelConverter()
    field = converter.conv_enum(object, _fake_prop(enum_class=TaskPriority, nullable=False), {})
    any_of = field.kwargs["validators"][0]
    assert isinstance(any_of, validators.AnyOf)
    assert AgreementStatus.DRAFT not in any_of.values

    fake_field = SimpleNamespace(data=AgreementStatus.DRAFT, gettext=lambda msg: msg)
    with pytest.raises(ValidationError):
        any_of(None, fake_field)


def test_conv_enum_agreement_status_from_mapper() -> None:
    mapper = class_mapper(PortalAgreement)
    converter = CosmoletAdminModelConverter()
    st_field = converter.conv_enum(PortalAgreement, mapper.get_property("status"), {})
    labels = _ENUM_LABELS_BY_CLASS[AgreementStatus]
    assert st_field.kwargs["choices"] == [(m.name, labels[m.value]) for m in AgreementStatus]
    assert getattr(st_field, "allow_blank", False) is False
