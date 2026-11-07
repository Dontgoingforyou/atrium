"""Интеграционные тесты: уведомления о @ в комментариях к задачам."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from app.core.config import Settings
from app.core.enums import TaskPriority, TaskStatus
from app.infrastructure.db.models.portal_document import PortalDocument
from app.infrastructure.db.models.portal_document_comment import PortalDocumentComment
from app.infrastructure.db.models.portal_notification import PortalNotification
from app.infrastructure.db.models.portal_task import PortalTask
from app.infrastructure.db.models.portal_user_profile import PortalUserProfile
from app.schemas.auth import UserPublic
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tests.helpers.portal_test_users import user_portal_manager, user_portal_regular, user_portal_user_b
from tests.portal_collab.conftest import assert_api_error, async_client_as

_MANAGER = user_portal_manager()

# ---------------------------------------------------------------------------
# Вспомогательные функции
# ---------------------------------------------------------------------------


def _user_a() -> UserPublic:
    """Пользователь A — обычный (user-sub)."""
    return user_portal_regular()


def _user_b() -> UserPublic:
    """Пользователь B (user-b)."""
    return user_portal_user_b()


async def _create_task_for_user(
    client: AsyncClient,
    title: str = "Тестовая задача",
    assignee_sub: str = "user-sub",
) -> dict:
    r = await client.post("/api/v1/portal/tasks", json={"title": title, "assignee_sub": assignee_sub})
    assert r.status_code == 201, r.text
    return r.json()


async def _create_comment_with_mention(
    client: AsyncClient,
    task_id: str,
    body: str,
    mentions: list[str],
) -> dict:
    r = await client.post(
        f"/api/v1/portal/tasks/{task_id}/comments",
        json={"body": body, "mentions": mentions},
    )
    assert r.status_code == 201, r.text
    return r.json()


# ---------------------------------------------------------------------------
# Создание уведомлений
# ---------------------------------------------------------------------------


async def test_create_comment_creates_notification_for_mentioned_user(
    sqlite_session: AsyncSession,
    patch_oidc_settings: Settings,
) -> None:
    """Комментарий с @mention создаёт уведомление для получателя."""

    # Профиль user-b должен существовать, иначе нет смысла упоминать (recipient_can_view_task)
    # В данном тесте user-b является assignee задачи — это даёт доступ
    # Создаём задачу от user-a с assignee = user-b
    async with async_client_as(sqlite_session, _user_a) as client:
        r = await client.post(
            "/api/v1/portal/tasks",
            json={"title": "Задача с упоминанием", "assignee_sub": "user-b"},
        )
        assert r.status_code == 201
        task_id = r.json()["id"]

        # Комментарий от user-a с упоминанием user-b
        r = await client.post(
            f"/api/v1/portal/tasks/{task_id}/comments",
            json={"body": "Привет @user-b!", "mentions": ["user-b"]},
        )
        assert r.status_code == 201

    # Проверяем, что user-b видит уведомление
    async with async_client_as(sqlite_session, _user_b) as client:
        r = await client.get("/api/v1/portal/notifications")
        assert r.status_code == 200
        notifs = r.json()
        assert len(notifs) == 2
        mention = next(n for n in notifs if n["type"] == "task_mention")
        assert mention["recipient_sub"] == "user-b"
        assert mention["author_sub"] == "user-sub"
        assert mention["read_at"] is None
        assert mention["task_title"] == "Задача с упоминанием"
        assert any(n["type"] == "task_assigned" and n["task_id"] == task_id for n in notifs)
        assert not any(n["type"] == "task_comment" for n in notifs)


async def test_author_does_not_receive_own_mention(
    sqlite_session: AsyncSession,
    patch_oidc_settings: Settings,
) -> None:
    """Автор комментария не получает уведомление о самоупоминании."""

    async with async_client_as(sqlite_session, _user_a) as client:
        r = await client.post("/api/v1/portal/tasks", json={"title": "Задача", "assignee_sub": "user-sub"})
        task_id = r.json()["id"]
        await client.post(
            f"/api/v1/portal/tasks/{task_id}/comments",
            json={"body": "Самоупоминание @user-sub", "mentions": ["user-sub"]},
        )

        r = await client.get("/api/v1/portal/notifications")
        assert r.status_code == 200
        assert r.json() == []


async def test_create_comment_without_mention_notifies_assignee_and_creator(
    sqlite_session: AsyncSession,
    patch_oidc_settings: Settings,
) -> None:
    """Комментарий без @ — task_comment исполнителю и создателю, не автору."""

    async with async_client_as(sqlite_session, _user_a) as client:
        r = await client.post(
            "/api/v1/portal/tasks",
            json={"title": "Комментарий руководителя", "assignee_sub": "user-b"},
        )
        assert r.status_code == 201, r.text
        task_id = r.json()["id"]

    async with async_client_as(sqlite_session, lambda: _MANAGER) as client:
        r = await client.post(
            f"/api/v1/portal/tasks/{task_id}/comments",
            json={"body": "Проверьте статус", "mentions": []},
        )
        assert r.status_code == 201, r.text

    async with async_client_as(sqlite_session, _user_b) as client:
        r = await client.get("/api/v1/portal/notifications")
        assert r.status_code == 200
        comments = [n for n in r.json() if n["type"] == "task_comment" and n["task_id"] == task_id]
        assert len(comments) == 1
        assert comments[0]["recipient_sub"] == "user-b"
        assert comments[0]["author_sub"] == _MANAGER.sub
        assert comments[0]["comment_id"] is not None
        assert comments[0]["task_title"] == "Комментарий руководителя"

    async with async_client_as(sqlite_session, _user_a) as client:
        r = await client.get("/api/v1/portal/notifications")
        assert r.status_code == 200
        comments = [n for n in r.json() if n["type"] == "task_comment" and n["task_id"] == task_id]
        assert len(comments) == 1
        assert comments[0]["recipient_sub"] == "user-sub"
        assert comments[0]["author_sub"] == _MANAGER.sub

    async with async_client_as(sqlite_session, lambda: _MANAGER) as client:
        r = await client.get("/api/v1/portal/notifications")
        assert r.status_code == 200
        assert not any(n["type"] == "task_comment" for n in r.json())


async def test_create_task_notifies_all_assignees_with_assignee_subs(
    sqlite_session: AsyncSession,
    patch_oidc_settings: Settings,
) -> None:
    """Несколько исполнителей при создании — task_assigned каждому (не только первому в assignee_sub)."""

    async with async_client_as(sqlite_session, _user_a) as client:
        r = await client.post(
            "/api/v1/portal/tasks",
            json={
                "title": "Два исполнителя",
                "assignee_subs": ["user-b", _MANAGER.sub],
            },
        )
        assert r.status_code == 201, r.text
        task_id = r.json()["id"]

    for recipient, user_factory in (
        ("user-b", _user_b),
        (_MANAGER.sub, lambda: _MANAGER),
    ):
        async with async_client_as(sqlite_session, user_factory) as client:
            r = await client.get("/api/v1/portal/notifications")
            assert r.status_code == 200
            assigned = [n for n in r.json() if n["type"] == "task_assigned" and n["task_id"] == task_id]
            assert len(assigned) == 1, f"ожидалось одно task_assigned для {recipient}"
            assert assigned[0]["recipient_sub"] == recipient


async def test_update_task_notifies_new_co_assignee(
    sqlite_session: AsyncSession,
    patch_oidc_settings: Settings,
) -> None:
    """Добавление второго исполнителя после создания — уведомление новому."""

    async with async_client_as(sqlite_session, _user_a) as client:
        r = await client.post(
            "/api/v1/portal/tasks",
            json={"title": "Один исполнитель", "assignee_subs": ["user-b"]},
        )
        assert r.status_code == 201, r.text
        task_id = r.json()["id"]

        r = await client.patch(
            f"/api/v1/portal/tasks/{task_id}",
            json={"expected_version": 1, "assignee_subs": ["user-b", _MANAGER.sub]},
        )
        assert r.status_code == 200, r.text

    async with async_client_as(sqlite_session, lambda: _MANAGER) as client:
        r = await client.get("/api/v1/portal/notifications")
        assert r.status_code == 200
        assigned = [n for n in r.json() if n["type"] == "task_assigned" and n["task_id"] == task_id]
        assert len(assigned) == 1
        assert assigned[0]["recipient_sub"] == _MANAGER.sub


async def test_create_task_notifies_assignee_with_task_assigned(
    sqlite_session: AsyncSession,
    patch_oidc_settings: Settings,
) -> None:
    """Создание задачи с исполнителем — уведомление task_assigned с полями задачи."""

    async with async_client_as(sqlite_session, _user_a) as client:
        r = await client.post(
            "/api/v1/portal/tasks",
            json={
                "title": "Назначение",
                "assignee_sub": "user-b",
                "priority": "high",
            },
        )
        assert r.status_code == 201, r.text

    async with async_client_as(sqlite_session, _user_b) as client:
        r = await client.get("/api/v1/portal/notifications")
        assert r.status_code == 200
        notifs = r.json()
        assert len(notifs) == 1
        n = notifs[0]
        assert n["type"] == "task_assigned"
        assert n["recipient_sub"] == "user-b"
        assert n["author_sub"] == "user-sub"
        assert n["comment_id"] is None
        assert n["task_title"] == "Назначение"
        assert n["task_priority"] == "high"
        assert n["task_status"] == "todo"
        assert n["task_due_at"] is None


async def test_create_task_no_assignee_notification_when_self_assigned(
    sqlite_session: AsyncSession,
    patch_oidc_settings: Settings,
) -> None:
    """Создатель, назначивший себя исполнителем, не получает task_assigned."""

    async with async_client_as(sqlite_session, _user_a) as client:
        r = await client.post(
            "/api/v1/portal/tasks",
            json={"title": "Самоназначение", "assignee_sub": "user-sub"},
        )
        assert r.status_code == 201, r.text

    async with async_client_as(sqlite_session, _user_a) as client:
        r = await client.get("/api/v1/portal/notifications")
        assert r.json() == []


async def test_patch_reassign_notifies_new_assignee(
    sqlite_session: AsyncSession,
    patch_oidc_settings: Settings,
) -> None:
    """Смена исполнителя — уведомление у нового."""

    async with async_client_as(sqlite_session, _user_a) as client:
        r = await client.post(
            "/api/v1/portal/tasks",
            json={"title": "Передача", "assignee_sub": "user-b"},
        )
        assert r.status_code == 201, r.text
        task_id = r.json()["id"]
        r = await client.patch(
            f"/api/v1/portal/tasks/{task_id}",
            json={"expected_version": 1, "assignee_sub": "manager-sub"},
        )
        assert r.status_code == 200, r.text

    async with async_client_as(sqlite_session, user_portal_manager) as client:
        r = await client.get("/api/v1/portal/notifications?unread_only=false")
        assert r.status_code == 200
        assign_for_manager = [n for n in r.json() if n["type"] == "task_assigned" and n["task_id"] == task_id]
        assert len(assign_for_manager) == 1
        assert assign_for_manager[0]["author_sub"] == "user-sub"
        assert assign_for_manager[0]["task_title"] == "Передача"


# ---------------------------------------------------------------------------
# unread-count
# ---------------------------------------------------------------------------


async def test_unread_count_increments_and_resets(
    sqlite_session: AsyncSession,
    patch_oidc_settings: Settings,
) -> None:
    """unread-count растёт при новых уведомлениях и сбрасывается после mark-all-read."""

    async with async_client_as(sqlite_session, _user_a) as client_a:
        r = await client_a.post(
            "/api/v1/portal/tasks",
            json={"title": "Задача для счётчика", "assignee_sub": "user-b"},
        )
        task_id = r.json()["id"]

        # Два комментария с разными комментариями (разные comment_id)
        await client_a.post(
            f"/api/v1/portal/tasks/{task_id}/comments",
            json={"body": "Первое", "mentions": ["user-b"]},
        )
        await client_a.post(
            f"/api/v1/portal/tasks/{task_id}/comments",
            json={"body": "Второе", "mentions": ["user-b"]},
        )

    async with async_client_as(sqlite_session, _user_b) as client_b:
        r = await client_b.get("/api/v1/portal/notifications/unread-count")
        assert r.status_code == 200
        assert r.json()["unread_count"] == 3

        # Mark all read
        r = await client_b.post("/api/v1/portal/notifications/mark-all-read")
        assert r.status_code == 200
        assert r.json()["unread_count"] == 0

        # Список теперь пуст (только непрочитанные по умолчанию)
        r = await client_b.get("/api/v1/portal/notifications")
        assert r.status_code == 200
        assert r.json() == []


# ---------------------------------------------------------------------------
# mark one read
# ---------------------------------------------------------------------------


async def test_mark_single_notification_read(
    sqlite_session: AsyncSession,
    patch_oidc_settings: Settings,
) -> None:
    """POST /{id}/read выставляет read_at и уведомление пропадает из непрочитанных."""

    async with async_client_as(sqlite_session, _user_a) as ca:
        r = await ca.post(
            "/api/v1/portal/tasks",
            json={"title": "Задача mark-read", "assignee_sub": "user-b"},
        )
        task_id = r.json()["id"]
        await ca.post(
            f"/api/v1/portal/tasks/{task_id}/comments",
            json={"body": "@user-b проверь", "mentions": ["user-b"]},
        )

    async with async_client_as(sqlite_session, _user_b) as cb:
        r = await cb.get("/api/v1/portal/notifications")
        notifs = r.json()
        assert len(notifs) == 2
        notif_mention = next(n for n in notifs if n["type"] == "task_mention")
        notif_id = notif_mention["id"]

        r = await cb.post(f"/api/v1/portal/notifications/{notif_id}/read")
        assert r.status_code == 200
        assert r.json()["read_at"] is not None

        r = await cb.get("/api/v1/portal/notifications")
        assert len(r.json()) == 1

        notif_assign = r.json()[0]
        r = await cb.post(f"/api/v1/portal/notifications/{notif_assign['id']}/read")
        assert r.status_code == 200

        r = await cb.get("/api/v1/portal/notifications")
        assert r.json() == []

        # unread-count = 0
        r = await cb.get("/api/v1/portal/notifications/unread-count")
        assert r.json()["unread_count"] == 0


async def test_mark_single_notification_read_twice_idempotent(
    sqlite_session: AsyncSession,
    patch_oidc_settings: Settings,
) -> None:
    """Повторный POST read для уже прочитанного уведомления — 200, read_at без повторного commit."""

    async with async_client_as(sqlite_session, _user_a) as ca:
        r = await ca.post(
            "/api/v1/portal/tasks",
            json={"title": "Задача mark-read-2x", "assignee_sub": "user-b"},
        )
        task_id = r.json()["id"]
        await ca.post(
            f"/api/v1/portal/tasks/{task_id}/comments",
            json={"body": "@user-b", "mentions": ["user-b"]},
        )

    async with async_client_as(sqlite_session, _user_b) as cb:
        notif_id = next(
            n["id"] for n in (await cb.get("/api/v1/portal/notifications")).json() if n["type"] == "task_mention"
        )
        r1 = await cb.post(f"/api/v1/portal/notifications/{notif_id}/read")
        assert r1.status_code == 200
        read_at_first = r1.json()["read_at"]
        r2 = await cb.post(f"/api/v1/portal/notifications/{notif_id}/read")
        assert r2.status_code == 200
        raw2 = r2.json()["read_at"]
        t1 = datetime.fromisoformat(read_at_first.replace("Z", "+00:00"))
        t2 = datetime.fromisoformat(raw2.replace("Z", "+00:00") if raw2.endswith("Z") else raw2)
        assert t1.replace(tzinfo=None) == t2.replace(tzinfo=None)


# ---------------------------------------------------------------------------
# RBAC: 403 на чужое уведомление
# ---------------------------------------------------------------------------


async def test_mark_read_403_foreign_notification(
    sqlite_session: AsyncSession,
    patch_oidc_settings: Settings,
) -> None:
    """user-a не может прочитать уведомление user-b."""

    async with async_client_as(sqlite_session, _user_a) as ca:
        r = await ca.post(
            "/api/v1/portal/tasks",
            json={"title": "Задача 403", "assignee_sub": "user-b"},
        )
        task_id = r.json()["id"]
        await ca.post(
            f"/api/v1/portal/tasks/{task_id}/comments",
            json={"body": "@user-b привет", "mentions": ["user-b"]},
        )

    # user-b получает уведомления — user-a пробует чужое прочитать
    async with async_client_as(sqlite_session, _user_b) as cb:
        r = await cb.get("/api/v1/portal/notifications")
        notif_id = next(n["id"] for n in r.json() if n["type"] == "task_mention")

    async with async_client_as(sqlite_session, _user_a) as ca:
        r = await ca.post(f"/api/v1/portal/notifications/{notif_id}/read")
        assert_api_error(r, 403, "forbidden")


# ---------------------------------------------------------------------------
# Упоминания в комментариях к документу
# ---------------------------------------------------------------------------


async def test_document_comment_mention_creates_notification(
    sqlite_session: AsyncSession,
    patch_oidc_settings: Settings,
) -> None:
    """Комментарий к документу с @mention создаёт уведомление document_mention."""
    from app.infrastructure.db.models.portal_document import PortalDocument

    doc = PortalDocument(
        title="Док для @",
        author_sub="user-sub",
        author_display_name="User",
        author_email="user@example.com",
        owner_sub="user-sub",
        body="тело",
        parent_document_id=None,
    )
    sqlite_session.add(doc)
    await sqlite_session.commit()
    await sqlite_session.refresh(doc)

    async with async_client_as(sqlite_session, _user_a) as client:
        r = await client.post(
            f"/api/v1/portal/documents/{doc.id}/comments",
            json={"body": "Привет @B", "mentions": ["user-b"]},
        )
        assert r.status_code == 201, r.text

    async with async_client_as(sqlite_session, _user_b) as client:
        r = await client.get("/api/v1/portal/notifications")
        assert r.status_code == 200
        notifs = r.json()
        mention = next(n for n in notifs if n["type"] == "document_mention")
        assert mention["recipient_sub"] == "user-b"
        assert mention["author_sub"] == "user-sub"
        assert mention["document_id"] == str(doc.id)
        assert mention["document_title"] == "Док для @"
        assert mention["read_at"] is None


# ---------------------------------------------------------------------------
# 401 без авторизации
# ---------------------------------------------------------------------------


async def test_notifications_401_anon(client_sqlite_only: AsyncClient) -> None:
    """Анонимный запрос возвращает 401."""
    r = await client_sqlite_only.get("/api/v1/portal/notifications")
    assert_api_error(r, 401, "unauthorized")
    r = await client_sqlite_only.get("/api/v1/portal/notifications/unread-count")
    assert_api_error(r, 401, "unauthorized")
    r = await client_sqlite_only.delete("/api/v1/portal/notifications")
    assert_api_error(r, 401, "unauthorized")
    r = await client_sqlite_only.delete(f"/api/v1/portal/notifications/{uuid.uuid4()}")
    assert_api_error(r, 401, "unauthorized")
    r = await client_sqlite_only.post("/api/v1/portal/notifications/mark-all-read")
    assert_api_error(r, 401, "unauthorized")
    r = await client_sqlite_only.post(f"/api/v1/portal/notifications/{uuid.uuid4()}/read")
    assert_api_error(r, 401, "unauthorized")


# ---------------------------------------------------------------------------
# unread_only=false возвращает прочитанные тоже
# ---------------------------------------------------------------------------


async def test_list_notifications_all(
    sqlite_session: AsyncSession,
    patch_oidc_settings: Settings,
) -> None:
    """unread_only=false включает прочитанные уведомления."""

    async with async_client_as(sqlite_session, _user_a) as ca:
        r = await ca.post(
            "/api/v1/portal/tasks",
            json={"title": "Задача all", "assignee_sub": "user-b"},
        )
        task_id = r.json()["id"]
        await ca.post(
            f"/api/v1/portal/tasks/{task_id}/comments",
            json={"body": "@user-b test", "mentions": ["user-b"]},
        )

    async with async_client_as(sqlite_session, _user_b) as cb:
        # Отмечаем прочитанным
        r = await cb.post("/api/v1/portal/notifications/mark-all-read")
        assert r.status_code == 200

        # Без флага — пусто
        r = await cb.get("/api/v1/portal/notifications")
        assert r.json() == []

        # С unread_only=false — видим прочитанное (назначение + комментарий)
        r = await cb.get("/api/v1/portal/notifications?unread_only=false")
        assert r.status_code == 200
        assert len(r.json()) == 2
        assert all(n["read_at"] is not None for n in r.json())


# ---------------------------------------------------------------------------
# DELETE: одна запись / все
# ---------------------------------------------------------------------------


async def test_delete_notification_204(
    sqlite_session: AsyncSession,
    patch_oidc_settings: Settings,
) -> None:
    """DELETE /{id} удаляет уведомление, список (все) пуст, счётчик 0."""

    async with async_client_as(sqlite_session, _user_a) as ca:
        r = await ca.post(
            "/api/v1/portal/tasks",
            json={"title": "Задача del-one", "assignee_sub": "user-b"},
        )
        task_id = r.json()["id"]
        await ca.post(
            f"/api/v1/portal/tasks/{task_id}/comments",
            json={"body": "@user-b del", "mentions": ["user-b"]},
        )

    async with async_client_as(sqlite_session, _user_b) as cb:
        for notif in (await cb.get("/api/v1/portal/notifications?unread_only=false")).json():
            r = await cb.delete(f"/api/v1/portal/notifications/{notif['id']}")
            assert r.status_code == 204

        r = await cb.get("/api/v1/portal/notifications?unread_only=false")
        assert r.json() == []
        r = await cb.get("/api/v1/portal/notifications/unread-count")
        assert r.json()["unread_count"] == 0


async def test_delete_all_notifications_204(
    sqlite_session: AsyncSession,
    patch_oidc_settings: Settings,
) -> None:
    """DELETE /notifications очищает все уведомления пользователя."""

    async with async_client_as(sqlite_session, _user_a) as ca:
        r = await ca.post(
            "/api/v1/portal/tasks",
            json={"title": "Задача del-all", "assignee_sub": "user-b"},
        )
        task_id = r.json()["id"]
        await ca.post(
            f"/api/v1/portal/tasks/{task_id}/comments",
            json={"body": "1", "mentions": ["user-b"]},
        )
        await ca.post(
            f"/api/v1/portal/tasks/{task_id}/comments",
            json={"body": "2", "mentions": ["user-b"]},
        )

    async with async_client_as(sqlite_session, _user_b) as cb:
        assert len((await cb.get("/api/v1/portal/notifications?unread_only=false")).json()) == 3

        r = await cb.delete("/api/v1/portal/notifications")
        assert r.status_code == 204

        assert (await cb.get("/api/v1/portal/notifications?unread_only=false")).json() == []
        r = await cb.get("/api/v1/portal/notifications/unread-count")
        assert r.json()["unread_count"] == 0


async def test_delete_notification_403_foreign(
    sqlite_session: AsyncSession,
    patch_oidc_settings: Settings,
) -> None:
    """user-a не может DELETE чужого уведомления user-b."""

    async with async_client_as(sqlite_session, _user_a) as ca:
        r = await ca.post(
            "/api/v1/portal/tasks",
            json={"title": "403 del", "assignee_sub": "user-b"},
        )
        task_id = r.json()["id"]
        await ca.post(
            f"/api/v1/portal/tasks/{task_id}/comments",
            json={"body": "@user-b x", "mentions": ["user-b"]},
        )

    async with async_client_as(sqlite_session, _user_b) as cb:
        notif_id = next(
            n["id"] for n in (await cb.get("/api/v1/portal/notifications")).json() if n["type"] == "task_mention"
        )

    async with async_client_as(sqlite_session, _user_a) as ca:
        r = await ca.delete(f"/api/v1/portal/notifications/{notif_id}")
        assert_api_error(r, 403, "forbidden")


async def test_delete_notification_404(
    sqlite_session: AsyncSession,
    patch_oidc_settings: Settings,
) -> None:
    """DELETE несуществующего id — 404."""

    async with async_client_as(sqlite_session, _user_b) as client:
        r = await client.delete(f"/api/v1/portal/notifications/{uuid.uuid4()}")
        assert_api_error(r, 404, "not_found")


async def test_list_notifications_batch_enriches_task_and_document(
    sqlite_session: AsyncSession,
    patch_oidc_settings: Settings,
) -> None:
    """Один GET: уведомления с task_id и document_id — актуальные ветки _enrich_notifications."""
    now = datetime.now(UTC)
    task = PortalTask(
        title="Задача батч",
        creator_sub="user-sub",
        status=TaskStatus.TODO.value,
        priority=TaskPriority.MEDIUM.value,
        position=0,
        created_at=now,
        updated_at=now,
    )
    sqlite_session.add(task)
    await sqlite_session.flush()
    doc = PortalDocument(
        title="Док батч",
        author_sub="user-sub",
        author_display_name="A",
        author_email="a@example.com",
        owner_sub="user-sub",
        body="b",
        parent_document_id=None,
    )
    sqlite_session.add(doc)
    await sqlite_session.flush()
    dcomment = PortalDocumentComment(
        document_id=doc.id,
        parent_id=None,
        author_sub="user-sub",
        body="c",
        mentions=[],
        created_at=now,
        updated_at=now,
    )
    sqlite_session.add(dcomment)
    await sqlite_session.flush()
    sqlite_session.add_all(
        [
            PortalNotification(
                recipient_sub="user-b",
                type="task_assigned",
                author_sub="user-sub",
                task_id=task.id,
            ),
            PortalNotification(
                recipient_sub="user-b",
                type="document_mention",
                author_sub="user-sub",
                document_id=doc.id,
                document_comment_id=dcomment.id,
            ),
        ]
    )
    await sqlite_session.commit()

    async with async_client_as(sqlite_session, _user_b) as client:
        r = await client.get("/api/v1/portal/notifications?unread_only=false")
        assert r.status_code == 200, r.text
        items = r.json()
        assert len(items) == 2
        by_type = {n["type"]: n for n in items}
        assert by_type["task_assigned"]["task_title"] == "Задача батч"
        assert by_type["task_assigned"]["task_status"] == TaskStatus.TODO.value
        assert by_type["document_mention"]["document_title"] == "Док батч"


async def test_list_notifications_author_display_name_username_only(
    sqlite_session: AsyncSession,
    patch_oidc_settings: Settings,
) -> None:
    """author_display_name: fallback на username при пустых full_name и email."""
    now = datetime.now(UTC)
    doc = PortalDocument(
        title="Док для fallback",
        author_sub="user-sub",
        author_display_name="A",
        author_email="a@example.com",
        owner_sub="user-sub",
        body="b",
        parent_document_id=None,
    )
    sqlite_session.add(doc)
    await sqlite_session.flush()
    dcomment = PortalDocumentComment(
        document_id=doc.id,
        parent_id=None,
        author_sub="user-sub",
        body="x",
        mentions=[],
        created_at=now,
        updated_at=now,
    )
    sqlite_session.add(dcomment)
    await sqlite_session.flush()
    sqlite_session.add(
        PortalNotification(
            recipient_sub="user-b",
            type="document_mention",
            author_sub="user-sub",
            document_id=doc.id,
            document_comment_id=dcomment.id,
        )
    )
    prof = (
        await sqlite_session.execute(select(PortalUserProfile).where(PortalUserProfile.sub == "user-sub"))
    ).scalar_one()
    old_fn, old_em, old_un = prof.full_name, prof.email, prof.username
    prof.full_name = None
    prof.email = None
    prof.username = "only_username_display"
    await sqlite_session.commit()

    try:
        async with async_client_as(sqlite_session, _user_b) as client:
            r = await client.get("/api/v1/portal/notifications")
            assert r.status_code == 200, r.text
            assert r.json()[0]["author_display_name"] == "only_username_display"
    finally:
        prof.full_name = old_fn
        prof.email = old_em
        prof.username = old_un
        await sqlite_session.commit()


async def test_mark_read_returns_enriched_task_fields(
    sqlite_session: AsyncSession,
    patch_oidc_settings: Settings,
) -> None:
    """POST .../read возвращает обогащённые поля задачи для task_mention."""

    async with async_client_as(sqlite_session, _user_a) as ca:
        r = await ca.post(
            "/api/v1/portal/tasks",
            json={"title": "Задача для read enrich", "assignee_sub": "user-b"},
        )
        assert r.status_code == 201, r.text
        task_id = r.json()["id"]
        await ca.post(
            f"/api/v1/portal/tasks/{task_id}/comments",
            json={"body": "@user-b", "mentions": ["user-b"]},
        )

    async with async_client_as(sqlite_session, _user_b) as cb:
        notif_id = next(
            n["id"] for n in (await cb.get("/api/v1/portal/notifications")).json() if n["type"] == "task_mention"
        )
        r = await cb.post(f"/api/v1/portal/notifications/{notif_id}/read")
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["task_title"] == "Задача для read enrich"
        assert body["task_id"] == task_id


async def test_list_notifications_empty_ok(
    sqlite_session: AsyncSession,
    patch_oidc_settings: Settings,
) -> None:
    """Пустой список уведомлений — 200 и [] (ветка обогащения без строк БД)."""
    from tests.helpers.portal_test_users import user_portal_procurement

    async with async_client_as(sqlite_session, user_portal_procurement) as client:
        r = await client.get("/api/v1/portal/notifications")
        assert r.status_code == 200
        assert r.json() == []
