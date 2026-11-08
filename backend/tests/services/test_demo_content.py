"""Учебные данные пишутся один раз и не плодятся при повторе."""

from app.infrastructure.db.models.portal_chat import PortalChatMessage
from app.infrastructure.db.models.portal_document import PortalDocument
from app.infrastructure.db.models.portal_manager_specialist import PortalManagerSpecialist
from app.infrastructure.db.models.portal_task import PortalTask
from app.services.demo_content import seed_demo_content
from sqlalchemy import func, select


async def test_seed_demo_content_idempotent(sqlite_session) -> None:
    await seed_demo_content(sqlite_session)
    await sqlite_session.commit()
    await seed_demo_content(sqlite_session)
    await sqlite_session.commit()

    docs = await sqlite_session.scalar(select(func.count()).select_from(PortalDocument))
    tasks = await sqlite_session.scalar(select(func.count()).select_from(PortalTask))
    messages = await sqlite_session.scalar(select(func.count()).select_from(PortalChatMessage))
    cards = await sqlite_session.scalar(select(func.count()).select_from(PortalManagerSpecialist))

    assert docs == 3
    assert tasks == 4
    assert messages == 3
    assert cards == 4
