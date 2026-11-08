"""Локальные векторы: общий корень слова ближе, чем чужой текст."""

from __future__ import annotations

from app.portal_search.services._embedding_local import LOCAL_SEMANTIC_MIN_SCORE, local_embedding
from app.portal_search.services.entity_text import document_to_text


def _cosine(left: list[float], right: list[float]) -> float:
    return sum(a * b for a, b in zip(left, right, strict=True))


def test_local_embedding_matches_vacation_regulation() -> None:
    vacation = document_to_text(
        "Регламент отпусков",
        "Заявку на отпуск пишут заранее, задачу ставит руководитель, статус меняют на доске задач.",
    )
    query = local_embedding("отпуск", 1536)
    hit = local_embedding(vacation, 1536)
    other = local_embedding("Календарь встреч на пятницу", 1536)

    assert abs(sum(value * value for value in query) - 1.0) < 1e-6
    assert _cosine(query, hit) >= LOCAL_SEMANTIC_MIN_SCORE
    assert _cosine(query, hit) > _cosine(query, other)


def test_local_embedding_empty_is_zero() -> None:
    assert local_embedding("   ", 4) == [0.0, 0.0, 0.0, 0.0]
