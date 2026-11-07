"""Склейка полнотекста и семантики: лексика первая, без дублей."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from app.portal_documents.schemas.document import PortalDocumentListItem
from app.portal_search.schemas.search import PortalSearchHitDocument
from app.portal_search.services._search_merge import (
    fulltext_hit_to_lexical_dict,
    merge_lexical_first,
)


def test_fulltext_document_to_lexical_dict() -> None:
    doc_id = uuid.uuid4()
    hit = PortalSearchHitDocument(
        document=PortalDocumentListItem(
            id=doc_id,
            title="Бенч",
            parent_document_id=None,
            author_sub="u",
            owner_sub=None,
            version=1,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
    )
    row = fulltext_hit_to_lexical_dict(hit)
    assert row is not None
    assert row["entity_type"] == "document"
    assert row["entity_id"] == str(doc_id)
    assert row["text_content"] == "Бенч"
    assert row["similarity_score"] is None


def test_merge_lexical_first_pins_fulltext_and_keeps_semantic_score() -> None:
    lexical = [
        {
            "entity_type": "document",
            "entity_id": "bench",
            "text_content": "Бенч",
            "similarity_score": None,
            "meta": {},
        }
    ]
    semantic = [
        {
            "entity_type": "document",
            "entity_id": "other",
            "text_content": "чужой",
            "similarity_score": 0.55,
            "meta": {},
        },
        {
            "entity_type": "document",
            "entity_id": "bench",
            "text_content": "Бенч специалистов",
            "similarity_score": 0.33,
            "meta": {},
        },
    ]
    merged = merge_lexical_first(lexical, semantic)
    assert [h["entity_id"] for h in merged] == ["bench", "other"]
    assert merged[0]["similarity_score"] == 0.33
    assert merged[0]["text_content"] == "Бенч специалистов"


def test_merge_lexical_first_keeps_lexical_only_without_score() -> None:
    lexical = [
        {
            "entity_type": "task",
            "entity_id": "t1",
            "text_content": "бенч",
            "similarity_score": None,
            "meta": {},
        }
    ]
    merged = merge_lexical_first(lexical, [])
    assert len(merged) == 1
    assert merged[0]["similarity_score"] is None
