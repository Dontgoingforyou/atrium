"""Разовая уборка: вложения у сообщений с deleted_for_all_at (остатки до очистки в delete_message_for_all).

Идемпотентно. Требуются рабочие DATABASE_URL и доступ к MinIO (как у API).

Запуск:
    docker compose exec api python scripts/purge_soft_deleted_chat_attachments.py
    DATABASE_URL=postgresql+asyncpg://... python scripts/purge_soft_deleted_chat_attachments.py
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.portal_chat.services import attachment as att_svc  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine  # noqa: E402


async def _run() -> None:
    database_url = os.environ.get("DATABASE_URL", "").strip()
    if not database_url:
        print("Ошибка: задайте DATABASE_URL", file=sys.stderr)
        raise SystemExit(2)

    engine = create_async_engine(database_url)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        assert isinstance(session, AsyncSession)
        n = await att_svc.purge_attachments_linked_to_soft_deleted_messages(session)
    await engine.dispose()
    print(f"Удалено вложений (MinIO + БД): {n}")


if __name__ == "__main__":
    asyncio.run(_run())
