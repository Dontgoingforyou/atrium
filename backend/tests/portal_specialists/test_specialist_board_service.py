"""Юнит-тесты сервиса `app.portal_specialists.services.board`."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.infrastructure.db.models.portal_user_profile import PortalUserProfile
from app.portal_specialists.schemas.board import (
    ManagerSpecialistAdd,
    ManagerSpecialistPatch,
    ManagerSpecialistReorder,
    SpecialistColumnCreate,
    SpecialistColumnUpdate,
    SpecialistStatusCreate,
    SpecialistStatusUpdate,
)
from app.portal_specialists.services import board as svc
from app.portal_specialists.services.board import build_entry_read
from sqlalchemy.ext.asyncio import AsyncSession

from tests.helpers.portal_test_users import user_portal_admin, user_portal_manager
from tests.portal_specialists.conftest import user_portal_manager_b


def test_build_entry_read_without_and_with_avatar() -> None:
    base = dict(
        id=uuid.uuid4(),
        specialist_sub="spec",
        specialist_name="Имя",
        specialist_email="e@x.test",
        column_key="new",
        position=0,
        version=1,
        manager_sub="mgr",
        manager_name="Менеджер",
        status_id=None,
        status_title=None,
        status_color=None,
        created_at=datetime.now(UTC),
    )
    row_no = SimpleNamespace(**{**base, "specialist_email": None})
    settings = SimpleNamespace(avatar_presign_ttl_seconds=120)
    with patch(
        "app.portal_specialists.services.board_shared.build_user_photo_proxy_url",
        return_value=None,
    ):
        out0 = build_entry_read(row_no, settings)
    assert out0.avatar_url is None

    row_av = SimpleNamespace(**base)
    with patch(
        "app.portal_specialists.services.board_shared.build_user_photo_proxy_url",
        return_value="/api/v1/portal/users/specialist-sub/photo?exp=1&sig=x",
    ) as m_url:
        out1 = build_entry_read(row_av, settings)
    m_url.assert_called_once()
    assert out1.avatar_url == "/api/v1/portal/users/specialist-sub/photo?exp=1&sig=x"


@pytest.mark.anyio
async def test_list_specialist_statuses_empty_then_create_and_duplicate(
    session_with_board: AsyncSession,
) -> None:
    before = await svc.list_specialist_statuses(session_with_board, user_portal_manager())
    assert isinstance(before, list)

    title = f"Статус-{uuid.uuid4().hex[:8]}"
    st = await svc.create_specialist_status(
        session_with_board,
        user_portal_manager(),
        SpecialistStatusCreate(title=title, color="#abcdef"),
    )
    assert st.title == title

    with pytest.raises(ConflictError, match="уже существует"):
        await svc.create_specialist_status(
            session_with_board,
            user_portal_admin(),
            SpecialistStatusCreate(title=title, color="#000000"),
        )


@pytest.mark.anyio
async def test_column_create_duplicate_and_update_delete(
    session_with_board: AsyncSession,
) -> None:
    adm = user_portal_admin()

    with pytest.raises(ConflictError, match="уже существует"):
        await svc.create_specialist_column(
            session_with_board,
            adm,
            SpecialistColumnCreate(key="new", title="Дубликат", color="#222222"),
        )

    col = await svc.create_specialist_column(
        session_with_board,
        adm,
        SpecialistColumnCreate(key=f"col-{uuid.uuid4().hex[:8]}", title="Вр", color="#333333", position=3),
    )

    missing = uuid.uuid4()
    with pytest.raises(NotFoundError, match="не найдена"):
        await svc.update_specialist_column(
            session_with_board,
            adm,
            missing,
            SpecialistColumnUpdate(title="X"),
        )

    upd = await svc.update_specialist_column(
        session_with_board,
        adm,
        col.id,
        SpecialistColumnUpdate(title="Новое имя", color="#444444", position=7),
    )
    assert upd.title == "Новое имя"
    assert upd.color == "#444444"
    assert upd.position == 7

    noop = await svc.update_specialist_column(
        session_with_board,
        adm,
        col.id,
        SpecialistColumnUpdate(),
    )
    assert noop.title == "Новое имя"

    with pytest.raises(NotFoundError, match="не найдена"):
        await svc.delete_specialist_column(session_with_board, adm, missing)

    await svc.delete_specialist_column(session_with_board, adm, col.id)


@pytest.mark.anyio
async def test_status_update_forbidden_not_found_conflict_delete(
    session_with_board: AsyncSession,
) -> None:
    adm = user_portal_admin()
    mgr = user_portal_manager()

    a = await svc.create_specialist_status(
        session_with_board,
        mgr,
        SpecialistStatusCreate(title=f"A-{uuid.uuid4().hex[:6]}", color="#111111"),
    )
    b = await svc.create_specialist_status(
        session_with_board,
        mgr,
        SpecialistStatusCreate(title=f"B-{uuid.uuid4().hex[:6]}", color="#222222"),
    )
    a_id, b_id, title_a = a.id, b.id, a.title

    with pytest.raises(NotFoundError, match="не найден"):
        await svc.update_specialist_status(
            session_with_board,
            adm,
            uuid.uuid4(),
            SpecialistStatusUpdate(title="X"),
        )

    with pytest.raises(ConflictError, match="названием уже существует"):
        await svc.update_specialist_status(
            session_with_board,
            adm,
            b_id,
            SpecialistStatusUpdate(title=title_a),
        )

    b2 = await svc.update_specialist_status(
        session_with_board,
        adm,
        b_id,
        SpecialistStatusUpdate(title="Другое имя", color="#999999"),
    )
    assert b2.title == "Другое имя"
    assert b2.color == "#999999"

    with pytest.raises(NotFoundError, match="не найден"):
        await svc.delete_specialist_status(session_with_board, adm, uuid.uuid4())

    await svc.delete_specialist_status(session_with_board, adm, a_id)
    await svc.delete_specialist_status(session_with_board, adm, b_id)


@pytest.mark.anyio
async def test_add_to_board_conflict(session_with_board: AsyncSession) -> None:
    with pytest.raises(ConflictError, match="уже добавлен"):
        await svc.add_to_board(
            session_with_board,
            user_portal_manager(),
            ManagerSpecialistAdd(specialist_sub="specialist-sub", column_key="new"),
        )


@pytest.mark.anyio
async def test_add_to_board_success_manager_b(session_with_board: AsyncSession) -> None:
    entry = await svc.add_to_board(
        session_with_board,
        user_portal_manager_b(),
        ManagerSpecialistAdd(specialist_sub="specialist-sub", column_key="new"),
    )
    assert entry.manager_sub == "manager-b-sub"


@pytest.mark.anyio
async def test_add_to_board_rejects_unknown_column_and_non_student(
    session_with_board: AsyncSession,
) -> None:
    mgr = user_portal_manager()
    with pytest.raises(NotFoundError, match="Колонка"):
        await svc.add_to_board(
            session_with_board,
            mgr,
            ManagerSpecialistAdd(specialist_sub="specialist-sub", column_key="no-such-col"),
        )
    with pytest.raises(NotFoundError, match="Пользователь"):
        await svc.add_to_board(
            session_with_board,
            mgr,
            ManagerSpecialistAdd(specialist_sub="ghost-sub", column_key="new"),
        )
    with pytest.raises(ValidationError, match="специалиста"):
        await svc.add_to_board(
            session_with_board,
            mgr,
            ManagerSpecialistAdd(specialist_sub="manager-b-sub", column_key="new"),
        )


@pytest.mark.anyio
async def test_move_on_board_not_found_and_fields_and_admin_target(
    session_with_board: AsyncSession,
) -> None:
    mgr = user_portal_manager()
    adm = user_portal_admin()

    with pytest.raises(NotFoundError, match="не найдена"):
        await svc.move_on_board(
            session_with_board,
            mgr,
            "unknown-specialist-sub",
            ManagerSpecialistPatch(expected_version=1, column_key="cv_sent"),
        )

    moved = await svc.move_on_board(
        session_with_board,
        mgr,
        "specialist-sub",
        ManagerSpecialistPatch(expected_version=1, column_key="cv_sent", position=3),
    )
    assert moved.column_key == "cv_sent"
    assert moved.position == 3
    assert moved.status_id is None
    assert moved.version == 2

    by_admin = await svc.move_on_board(
        session_with_board,
        adm,
        "specialist-sub",
        ManagerSpecialistPatch(expected_version=2, column_key="hired"),
        target_manager_sub="manager-sub",
    )
    assert by_admin.column_key == "hired"
    assert by_admin.version == 3


@pytest.mark.anyio
async def test_reorder_on_board_uses_entry_anchor_and_reindexes(
    session_with_board: AsyncSession,
) -> None:
    manager = user_portal_manager()
    first_rows = await svc.list_board_entries(session_with_board, manager)
    first_id = first_rows[0].id
    session_with_board.add_all(
        [
            PortalUserProfile(
                sub="specialist-second",
                email="s2@example.com",
                full_name="Second",
                username="s2",
                portal_chat_allowed=False,
            ),
            PortalUserProfile(
                sub="specialist-third",
                email="s3@example.com",
                full_name="Third",
                username="s3",
                portal_chat_allowed=False,
            ),
        ]
    )
    await session_with_board.commit()
    second = await svc.add_to_board(
        session_with_board,
        manager,
        ManagerSpecialistAdd(specialist_sub="specialist-second", column_key="new"),
    )
    third = await svc.add_to_board(
        session_with_board,
        manager,
        ManagerSpecialistAdd(specialist_sub="specialist-third", column_key="new"),
    )
    await svc.move_on_board(
        session_with_board,
        manager,
        second.specialist_sub,
        ManagerSpecialistPatch(expected_version=1, position=1),
    )
    await svc.move_on_board(
        session_with_board,
        manager,
        third.specialist_sub,
        ManagerSpecialistPatch(expected_version=1, position=2),
    )

    await svc.reorder_on_board(
        session_with_board,
        manager,
        ManagerSpecialistReorder(
            entry_id=third.id,
            column_key="new",
            before_entry_id=first_id,
        ),
    )
    rows = await svc.list_board_entries(session_with_board, manager)
    new_rows = sorted(
        (row for row in rows if row.column_key == "new"),
        key=lambda row: row.position,
    )

    assert [row.id for row in new_rows] == [third.id, first_id, second.id]
    assert [row.position for row in new_rows] == [0, 1, 2]


@pytest.mark.anyio
async def test_remove_from_board_not_found_success_admin_target(session_with_board: AsyncSession) -> None:
    mgr = user_portal_manager()
    adm = user_portal_admin()

    with pytest.raises(NotFoundError, match="не найдена"):
        await svc.remove_from_board(session_with_board, mgr, "no-such-specialist")

    await svc.remove_from_board(session_with_board, mgr, "specialist-sub")

    await svc.add_to_board(
        session_with_board,
        user_portal_manager_b(),
        ManagerSpecialistAdd(specialist_sub="specialist-sub", column_key="new"),
    )
    await svc.remove_from_board(
        session_with_board,
        adm,
        "specialist-sub",
        target_manager_sub="manager-b-sub",
    )
