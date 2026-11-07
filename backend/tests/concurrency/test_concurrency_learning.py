"""Гонки чек-листа: старт прохождения, отметка пункта и CAS материала."""

from __future__ import annotations

import asyncio
import uuid

import pytest
from app.core.enums import LearningMaterialStatus, LearningMaterialType, UserChecklistStatus
from app.core.exceptions import ConflictError
from app.infrastructure.db.models.portal_learning import (
    PortalChecklist,
    PortalChecklistItem,
    PortalLearningMaterial,
    PortalUserChecklist,
    PortalUserChecklistItem,
)
from app.portal_learning.schemas.checklist import MarkItemBody
from app.portal_learning.schemas.material import LearningMaterialUpdate
from app.portal_learning.services import material as material_svc
from app.portal_learning.services.checklist import mark_item, start_checklist
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from tests.helpers.portal_test_users import user_portal_admin, user_portal_regular


@pytest.mark.asyncio
async def test_parallel_update_material_same_version_one_ok(
    sqlite_concurrency_factory: async_sessionmaker[AsyncSession],
) -> None:
    """Два concurrent update материала с одним expected_version → один ok, один ConflictError."""
    admin = user_portal_admin()
    material_id = uuid.uuid4()
    async with sqlite_concurrency_factory() as s:
        s.add(
            PortalLearningMaterial(
                id=material_id,
                title="Материал",
                body="v0",
                material_type=LearningMaterialType.ARTICLE.value,
                status=LearningMaterialStatus.DRAFT.value,
                created_by_sub=admin.sub,
                version=1,
            )
        )
        await s.commit()

    outcomes: list[str] = []

    async def try_update(body: str) -> None:
        async with sqlite_concurrency_factory() as sess:
            try:
                await material_svc.update_material(
                    sess,
                    admin,
                    material_id,
                    LearningMaterialUpdate(expected_version=1, body=body),
                )
                outcomes.append("ok")
            except ConflictError:
                outcomes.append("conflict")

    await asyncio.gather(try_update("from-a"), try_update("from-b"))

    assert sorted(outcomes) == ["conflict", "ok"]

    async with sqlite_concurrency_factory() as s:
        row = (
            await s.execute(select(PortalLearningMaterial).where(PortalLearningMaterial.id == material_id))
        ).scalar_one()
        assert row.version == 2
        assert row.body in ("from-a", "from-b")


@pytest.mark.asyncio
async def test_parallel_start_checklist_one_progress(
    sqlite_concurrency_factory: async_sessionmaker[AsyncSession],
) -> None:
    user = user_portal_regular()
    checklist_id = uuid.uuid4()
    item_id = uuid.uuid4()
    async with sqlite_concurrency_factory() as s:
        s.add(PortalChecklist(id=checklist_id, title="Онбординг", idp_group=""))
        s.add(PortalChecklistItem(id=item_id, checklist_id=checklist_id, order_index=0, text="Пункт"))
        await s.commit()

    started: list[uuid.UUID] = []

    async def try_start() -> None:
        async with sqlite_concurrency_factory() as sess:
            row = await start_checklist(sess, user, checklist_id)
            started.append(row.id)

    await asyncio.gather(try_start(), try_start())
    assert len(started) == 2
    assert started[0] == started[1]

    async with sqlite_concurrency_factory() as s:
        n = await s.execute(
            select(func.count())
            .select_from(PortalUserChecklist)
            .where(PortalUserChecklist.user_sub == user.sub, PortalUserChecklist.checklist_id == checklist_id)
        )
        assert n.scalar_one() == 1


@pytest.mark.asyncio
async def test_parallel_mark_item_one_row(
    sqlite_concurrency_factory: async_sessionmaker[AsyncSession],
) -> None:
    user = user_portal_regular()
    checklist_id = uuid.uuid4()
    item_id = uuid.uuid4()
    uc_id = uuid.uuid4()
    async with sqlite_concurrency_factory() as s:
        s.add(PortalChecklist(id=checklist_id, title="Онбординг", idp_group=""))
        s.add(PortalChecklistItem(id=item_id, checklist_id=checklist_id, order_index=0, text="Пункт"))
        s.add(
            PortalUserChecklist(
                id=uc_id,
                user_sub=user.sub,
                checklist_id=checklist_id,
                status=UserChecklistStatus.IN_PROGRESS.value,
            )
        )
        await s.commit()

    body = MarkItemBody(is_done=True)

    async def try_mark() -> None:
        async with sqlite_concurrency_factory() as sess:
            await mark_item(sess, user, checklist_id, item_id, body)

    await asyncio.gather(try_mark(), try_mark())

    async with sqlite_concurrency_factory() as s:
        n = await s.execute(
            select(func.count()).select_from(PortalUserChecklistItem).where(PortalUserChecklistItem.item_id == item_id)
        )
        assert n.scalar_one() == 1
