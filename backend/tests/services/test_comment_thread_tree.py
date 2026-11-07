"""Сборка дерева комментариев."""

from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

from app.services.comment_thread import attach_comment_replies


def _comment(body: str, parent_id: object = None, comment_id: object | None = None) -> SimpleNamespace:
    return SimpleNamespace(id=comment_id or uuid4(), parent_id=parent_id, body=body, replies=[])


def test_reply_to_reply_stays_under_parent_not_root() -> None:
    root = _comment("корень")
    reply = _comment("ответ", parent_id=root.id)
    nested = _comment("ответ на ответ", parent_id=reply.id)

    roots = attach_comment_replies([root, reply, nested])

    assert [item.body for item in roots] == ["корень"]
    assert [item.body for item in roots[0].replies] == ["ответ"]
    assert [item.body for item in roots[0].replies[0].replies] == ["ответ на ответ"]


def test_parent_cycle_is_not_promoted_to_root() -> None:
    first_id = uuid4()
    second_id = uuid4()
    first = _comment("первый", parent_id=second_id, comment_id=first_id)
    second = _comment("второй", parent_id=first_id, comment_id=second_id)

    assert attach_comment_replies([first, second]) == []


def test_cycle_under_root_stops_without_duplicating_node() -> None:
    root = _comment("корень")
    reply = _comment("ответ", parent_id=root.id)
    back = SimpleNamespace(id=reply.id, parent_id=reply.id, body="назад к ответу", replies=[])

    roots = attach_comment_replies([root, reply, back])

    assert [item.body for item in roots] == ["корень"]
    assert [item.body for item in roots[0].replies] == ["ответ"]
    assert roots[0].replies[0].replies == []
