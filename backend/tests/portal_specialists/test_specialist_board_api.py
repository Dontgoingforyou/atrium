"""Интеграционные тесты API доски воронки специалистов."""

from __future__ import annotations

import uuid

import pytest
from app.infrastructure.db.models.portal_manager_specialist import PortalManagerSpecialist
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tests.portal_specialists.conftest import assert_api_error, async_client_as, user_portal_manager_b

# ---------------------------------------------------------------------------
# Колонки воронки
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_list_columns_manager(client_manager: AsyncClient) -> None:
    """Менеджер может получить список колонок воронки."""
    res = await client_manager.get("/api/v1/portal/specialists/columns")
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)
    assert len(data) >= 3
    keys = {c["key"] for c in data}
    assert "new" in keys
    assert "cv_sent" in keys


@pytest.mark.anyio
async def test_list_columns_specialist_forbidden(client_specialist_user: AsyncClient) -> None:
    """Специалист (студент) не имеет доступа к колонкам воронки."""
    res = await client_specialist_user.get("/api/v1/portal/specialists/columns")
    assert res.status_code == 403


@pytest.mark.anyio
async def test_create_column_admin(client_admin_board: AsyncClient) -> None:
    """Администратор может создать новую колонку воронки."""
    res = await client_admin_board.post(
        "/api/v1/portal/specialists/columns",
        json={"key": "test_col", "title": "Тестовая колонка", "color": "#aabbcc", "position": 99},
    )
    assert res.status_code == 201
    data = res.json()
    assert data["key"] == "test_col"
    assert data["title"] == "Тестовая колонка"


@pytest.mark.anyio
async def test_create_column_manager_forbidden(client_manager: AsyncClient) -> None:
    """Менеджер не может создавать колонки воронки (только admin)."""
    res = await client_manager.post(
        "/api/v1/portal/specialists/columns",
        json={"key": "mgr_col", "title": "Колонка менеджера", "color": "#000000"},
    )
    assert res.status_code == 403


@pytest.mark.anyio
async def test_update_column_admin(client_admin_board: AsyncClient) -> None:
    """Администратор может обновить колонку."""
    # Получаем id первой колонки
    res = await client_admin_board.get("/api/v1/portal/specialists/columns")
    assert res.status_code == 200
    cols = res.json()
    col_id = cols[0]["id"]

    res = await client_admin_board.patch(
        f"/api/v1/portal/specialists/columns/{col_id}",
        json={"title": "Обновлённое название"},
    )
    assert res.status_code == 200
    assert res.json()["title"] == "Обновлённое название"


@pytest.mark.anyio
async def test_delete_column_manager_forbidden(client_manager: AsyncClient) -> None:
    """Менеджер не может удалять колонки."""
    res = await client_manager.get("/api/v1/portal/specialists/columns")
    col_id = res.json()[0]["id"]
    res = await client_manager.delete(f"/api/v1/portal/specialists/columns/{col_id}")
    assert res.status_code == 403


@pytest.mark.anyio
async def test_delete_column_with_entries_conflict(client_admin_board: AsyncClient) -> None:
    """Нельзя удалить колонку, на которой есть закрепления."""
    res = await client_admin_board.get("/api/v1/portal/specialists/columns")
    assert res.status_code == 200
    new_col = next(c for c in res.json() if c["key"] == "new")
    res = await client_admin_board.delete(f"/api/v1/portal/specialists/columns/{new_col['id']}")
    assert res.status_code == 409
    assert "закреплен" in res.json()["message"].lower()


@pytest.mark.anyio
async def test_delete_empty_column_admin(client_admin_board: AsyncClient) -> None:
    """Администратор может удалить пустую колонку."""
    create_res = await client_admin_board.post(
        "/api/v1/portal/specialists/columns",
        json={"key": "empty_del_col", "title": "На удаление", "color": "#112233", "position": 999},
    )
    assert create_res.status_code == 201
    col_id = create_res.json()["id"]
    res = await client_admin_board.delete(f"/api/v1/portal/specialists/columns/{col_id}")
    assert res.status_code == 204


# ---------------------------------------------------------------------------
# Доска специалистов
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_list_board_manager_sees_own(client_manager: AsyncClient) -> None:
    """Менеджер видит только свою доску (заранее добавленного специалиста)."""
    res = await client_manager.get("/api/v1/portal/specialists/board")
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 1
    assert data[0]["specialist_sub"] == "specialist-sub"
    assert data[0]["manager_sub"] == "manager-sub"
    assert data[0]["column_key"] == "new"


@pytest.mark.anyio
async def test_reorder_board_entry_manager(client_manager: AsyncClient) -> None:
    board = (await client_manager.get("/api/v1/portal/specialists/board")).json()
    entry = board[0]

    res = await client_manager.post(
        "/api/v1/portal/specialists/board/reorder",
        json={
            "entry_id": entry["id"],
            "column_key": entry["column_key"],
            "after_entry_id": None,
            "before_entry_id": None,
        },
    )

    assert res.status_code == 200
    assert res.json()["id"] == entry["id"]
    assert res.json()["position"] == 0


@pytest.mark.anyio
async def test_reorder_board_entry_specialist_forbidden(
    client_specialist_user: AsyncClient,
) -> None:
    res = await client_specialist_user.post(
        "/api/v1/portal/specialists/board/reorder",
        json={
            "entry_id": "00000000-0000-0000-0000-000000000001",
            "column_key": "new",
            "after_entry_id": None,
            "before_entry_id": None,
        },
    )

    assert res.status_code == 403


@pytest.mark.anyio
async def test_list_board_manager_b_empty(client_manager_b: AsyncClient) -> None:
    """Второй менеджер видит пустую доску (его записей нет)."""
    res = await client_manager_b.get("/api/v1/portal/specialists/board")
    assert res.status_code == 200
    assert res.json() == []


@pytest.mark.anyio
async def test_list_board_directory_manager_sees_all_attachments(
    client_manager_b: AsyncClient,
) -> None:
    """Справочник: менеджер видит закрепления других менеджеров (только чтение)."""
    res = await client_manager_b.get("/api/v1/portal/specialists/board?directory=true")
    assert res.status_code == 200
    data = res.json()
    assert any(e["specialist_sub"] == "specialist-sub" for e in data)
    assert any(e["manager_sub"] == "manager-sub" for e in data)


@pytest.mark.anyio
async def test_list_board_admin_sees_all(client_admin_board: AsyncClient) -> None:
    """Администратор без manager_sub видит все записи всех менеджеров."""
    res = await client_admin_board.get("/api/v1/portal/specialists/board")
    assert res.status_code == 200
    data = res.json()
    assert len(data) >= 1


@pytest.mark.anyio
async def test_list_board_admin_filter_manager_sub(client_admin_board: AsyncClient) -> None:
    """Администратор с manager_sub видит только доску конкретного менеджера."""
    res = await client_admin_board.get("/api/v1/portal/specialists/board?manager_sub=manager-sub")
    assert res.status_code == 200
    data = res.json()
    assert all(e["manager_sub"] == "manager-sub" for e in data)

    res_b = await client_admin_board.get("/api/v1/portal/specialists/board?manager_sub=manager-b-sub")
    assert res_b.status_code == 200
    assert res_b.json() == []


@pytest.mark.anyio
async def test_list_board_specialist_forbidden(client_specialist_user: AsyncClient) -> None:
    """Специалист не имеет доступа к доске."""
    res = await client_specialist_user.get("/api/v1/portal/specialists/board")
    assert res.status_code == 403


@pytest.mark.anyio
async def test_add_to_board_success(client_manager_b: AsyncClient) -> None:
    """Менеджер B может добавить нового специалиста на свою доску."""
    res = await client_manager_b.post(
        "/api/v1/portal/specialists/board",
        json={"specialist_sub": "specialist-sub", "column_key": "new"},
    )
    assert res.status_code == 201
    data = res.json()
    assert data["specialist_sub"] == "specialist-sub"
    assert data["manager_sub"] == "manager-b-sub"


@pytest.mark.anyio
async def test_add_to_board_conflict(client_manager: AsyncClient) -> None:
    """Повторное добавление того же специалиста → 409 Conflict."""
    res = await client_manager.post(
        "/api/v1/portal/specialists/board",
        json={"specialist_sub": "specialist-sub", "column_key": "new"},
    )
    assert res.status_code == 409


@pytest.mark.anyio
async def test_move_on_board_success(client_manager: AsyncClient) -> None:
    """Менеджер может переместить своего специалиста в другую колонку."""
    res = await client_manager.patch(
        "/api/v1/portal/specialists/board/specialist-sub",
        json={"expected_version": 1, "column_key": "cv_sent"},
    )
    assert res.status_code == 200
    assert res.json()["column_key"] == "cv_sent"
    assert res.json()["version"] == 2


@pytest.mark.anyio
async def test_move_on_board_idor(client_manager_b: AsyncClient) -> None:
    """Менеджер B не может изменить запись на доске другого менеджера (IDOR)."""
    res = await client_manager_b.patch(
        "/api/v1/portal/specialists/board/specialist-sub",
        json={"expected_version": 1, "column_key": "hired"},
    )
    assert res.status_code == 404


@pytest.mark.anyio
async def test_remove_from_board_success(client_manager: AsyncClient) -> None:
    """Менеджер может удалить своего специалиста с доски."""
    res = await client_manager.delete("/api/v1/portal/specialists/board/specialist-sub")
    assert res.status_code == 204

    # Доска теперь пуста
    res2 = await client_manager.get("/api/v1/portal/specialists/board")
    assert res2.json() == []


@pytest.mark.anyio
async def test_remove_from_board_idor(client_manager_b: AsyncClient) -> None:
    """Менеджер B не может удалить запись с чужой доски (IDOR)."""
    res = await client_manager_b.delete("/api/v1/portal/specialists/board/specialist-sub")
    assert res.status_code == 404


@pytest.mark.anyio
async def test_remove_from_board_admin(client_admin_board: AsyncClient) -> None:
    """Администратор может удалить запись с доски любого менеджера."""
    res = await client_admin_board.delete("/api/v1/portal/specialists/board/specialist-sub?manager_sub=manager-sub")
    assert res.status_code == 204


# ---------------------------------------------------------------------------
# Legacy statuses + fallback DTO
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_statuses_list_and_create_manager(client_manager: AsyncClient) -> None:
    listed = await client_manager.get("/api/v1/portal/specialists/statuses")
    assert listed.status_code == 200
    assert listed.json() == []

    created = await client_manager.post(
        "/api/v1/portal/specialists/statuses",
        json={"title": "На паузе", "color": "#999999"},
    )
    assert created.status_code == 201
    assert created.json()["title"] == "На паузе"


@pytest.mark.anyio
async def test_statuses_update_delete_admin(client_admin_board: AsyncClient) -> None:
    created = await client_admin_board.post(
        "/api/v1/portal/specialists/statuses",
        json={"title": "На паузе", "color": "#999999"},
    )
    assert created.status_code == 201
    status_id = created.json()["id"]

    updated = await client_admin_board.patch(
        f"/api/v1/portal/specialists/statuses/{status_id}",
        json={"title": "На паузе (ред.)"},
    )
    assert updated.status_code == 200
    assert updated.json()["title"] == "На паузе (ред.)"

    deleted = await client_admin_board.delete(f"/api/v1/portal/specialists/statuses/{status_id}")
    assert deleted.status_code == 204


@pytest.mark.anyio
async def test_reorder_board_entry_idor_other_manager(
    session_with_board: AsyncSession,
    patch_oidc_settings: object,
) -> None:
    """manager_b не может reorder записи manager_a."""
    entry_id = (
        await session_with_board.execute(
            select(PortalManagerSpecialist.id).where(
                PortalManagerSpecialist.manager_sub == "manager-sub",
                PortalManagerSpecialist.specialist_sub == "specialist-sub",
            )
        )
    ).scalar_one()

    async with async_client_as(session_with_board, user_portal_manager_b) as ac:
        res = await ac.post(
            "/api/v1/portal/specialists/board/reorder",
            json={
                "entry_id": str(entry_id),
                "column_key": "new",
                "after_entry_id": None,
                "before_entry_id": None,
            },
        )
    assert_api_error(res, 404, "not_found")


@pytest.mark.anyio
async def test_update_column_unknown_404(client_admin_board: AsyncClient) -> None:
    res = await client_admin_board.patch(
        f"/api/v1/portal/specialists/columns/{uuid.uuid4()}",
        json={"title": "X"},
    )
    assert_api_error(res, 404, "not_found")


@pytest.mark.anyio
async def test_delete_status_unknown_404(client_admin_board: AsyncClient) -> None:
    res = await client_admin_board.delete(f"/api/v1/portal/specialists/statuses/{uuid.uuid4()}")
    assert_api_error(res, 404, "not_found")


@pytest.mark.anyio
async def test_create_status_forbidden_for_regular(client_regular_user: AsyncClient) -> None:
    res = await client_regular_user.post(
        "/api/v1/portal/specialists/statuses",
        json={"title": "X", "color": "#111111"},
    )
    assert_api_error(res, 403, "forbidden")
