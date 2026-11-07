"""Построение diff для истории изменений документа."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from app.infrastructure.db.models.portal_document import PortalDocument
from app.portal_documents.schemas.document import PortalDocumentUpdate


def _s(v: object | None) -> str | None:
    return str(v) if v is not None else None


def compute_document_update_diff(
    prev: SimpleNamespace,
    doc: PortalDocument,
    patch: dict[str, Any],
    data: PortalDocumentUpdate,
) -> dict[str, Any]:
    """Словарь изменённых полей {field: {old, new}} после применения patch к документу."""
    diff: dict[str, Any] = {}
    if data.title is not None and data.title != prev.title:
        diff["title"] = {"old": prev.title, "new": data.title}
    if "icon_emoji" in patch and (prev.icon_emoji or "") != (doc.icon_emoji or ""):
        diff["icon_emoji"] = {"old": prev.icon_emoji, "new": doc.icon_emoji}
    if "parent_document_id" in patch and _s(doc.parent_document_id) != _s(prev.parent_document_id):
        diff["parent_document_id"] = {"old": _s(prev.parent_document_id), "new": _s(doc.parent_document_id)}
    if data.body is not None and (data.body or "") != (prev.body or ""):
        diff["body"] = {"old": prev.body, "new": data.body}
    if data.owner_sub is not None and (prev.owner_sub or None) != (data.owner_sub or None):
        diff["owner_sub"] = {"old": _s(prev.owner_sub), "new": _s(data.owner_sub)}
    if data.tag_ids is not None and "tag_ids" not in diff:
        diff["tag_ids"] = {"old": "replaced", "new": "replaced"}
    return diff


def compute_document_field_diff(old_doc: PortalDocument, update: PortalDocumentUpdate) -> dict[str, Any]:
    """Diff по схеме обновления без применения patch (unit-тесты и простые сценарии)."""
    diff: dict[str, Any] = {}
    fields_map = {
        "title": "title",
        "parent_document_id": "parent_document_id",
        "body": "body",
        "owner_sub": "owner_sub",
    }
    for attr, field_name in fields_map.items():
        new_val = getattr(update, attr)
        if new_val is None:
            continue
        old_val = getattr(old_doc, attr)
        new_val_str = str(new_val) if new_val is not None else None
        old_val_str = str(old_val) if old_val is not None else None
        if new_val_str != old_val_str:
            diff[field_name] = {"old": old_val_str, "new": new_val_str}
    if "icon_emoji" in update.model_fields_set:
        new_e = update.icon_emoji
        old_e = getattr(old_doc, "icon_emoji", None)
        if (old_e or "") != (new_e or ""):
            diff["icon_emoji"] = {"old": old_e, "new": new_e}
    return diff
