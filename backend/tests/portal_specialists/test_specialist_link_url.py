"""Валидация URL ссылок специалиста — только http(s)."""

from __future__ import annotations

import pytest
from app.portal_specialists.schemas.specialist_detail import SpecialistLinkCreate
from pydantic import ValidationError


def test_specialist_link_accepts_https() -> None:
    data = SpecialistLinkCreate(title="CV", url="https://example.com/cv.pdf")
    assert data.url == "https://example.com/cv.pdf"


def test_specialist_link_rejects_javascript() -> None:
    with pytest.raises(ValidationError, match="http"):
        SpecialistLinkCreate(title="x", url="javascript:alert(1)")


def test_specialist_link_rejects_ftp() -> None:
    with pytest.raises(ValidationError, match="http"):
        SpecialistLinkCreate(title="x", url="ftp://files.example/info")


def test_specialist_link_rejects_data_url() -> None:
    with pytest.raises(ValidationError, match="http"):
        SpecialistLinkCreate(title="x", url="data:text/html,alert(1)")
