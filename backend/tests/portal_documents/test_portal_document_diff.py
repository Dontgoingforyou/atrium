"""Unit-тесты диффа полей документа при обновлении."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from app.infrastructure.db.models.portal_document import PortalDocument
from app.portal_documents.schemas.document import PortalDocumentUpdate
from app.portal_documents.services.portal_document_diff import compute_document_field_diff


def _doc(**kwargs: object) -> PortalDocument:
    defaults: dict[str, object] = {
        "id": uuid.uuid4(),
        "title": "Old",
        "icon_emoji": None,
        "body": "body",
        "owner_sub": "owner",
        "author_sub": "a",
        "author_email": None,
        "created_at": datetime.now(UTC),
        "updated_at": datetime.now(UTC),
    }
    defaults.update(kwargs)
    return PortalDocument(**defaults)


def test_compute_diff_skips_unset_fields() -> None:
    doc = _doc()
    upd = PortalDocumentUpdate(expected_version=1)
    assert compute_document_field_diff(doc, upd) == {}


def test_compute_diff_detects_title_change() -> None:
    doc = _doc(title="A")
    upd = PortalDocumentUpdate(expected_version=1, title="B")
    d = compute_document_field_diff(doc, upd)
    assert d == {"title": {"old": "A", "new": "B"}}


def test_compute_diff_owner_sub_change() -> None:
    doc = _doc(owner_sub="owner")
    upd = PortalDocumentUpdate(expected_version=1, owner_sub="new-owner")
    d = compute_document_field_diff(doc, upd)
    assert d == {"owner_sub": {"old": "owner", "new": "new-owner"}}


def test_compute_diff_icon_emoji_set() -> None:
    doc = _doc(icon_emoji=None)
    upd = PortalDocumentUpdate.model_validate({"expected_version": 1, "icon_emoji": "🌟"})
    d = compute_document_field_diff(doc, upd)
    assert d == {"icon_emoji": {"old": None, "new": "🌟"}}


def test_compute_diff_icon_emoji_clear_explicit_null() -> None:
    doc = _doc(icon_emoji="📎")
    upd = PortalDocumentUpdate.model_validate({"expected_version": 1, "icon_emoji": None})
    assert "icon_emoji" in upd.model_fields_set
    d = compute_document_field_diff(doc, upd)
    assert d == {"icon_emoji": {"old": "📎", "new": None}}
