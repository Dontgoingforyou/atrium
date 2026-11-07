"""Удаление «осиротевших» вложений: message_id IS NULL и возраст старше порога.

Запуск:
    python scripts/purge_orphan_chat_attachments.py --min-age-hours 48

Требуются DATABASE_URL и доступ к MinIO.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.portal_chat.services import attachment as att_svc  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine  # noqa: E402


async def _run(min_age_hours: float) -> None:
    database_url = os.environ.get("DATABASE_URL", "").strip()
    if not database_url:
        print("Ошибка: задайте DATABASE_URL", file=sys.stderr)
        raise SystemExit(2)

    engine = create_async_engine(database_url)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        assert isinstance(session, AsyncSession)
        n = await att_svc.purge_orphan_attachments_older_than(session, min_age_hours=min_age_hours)
    await engine.dispose()
    print(f"Удалено осиротевших вложений: {n}")


def main() -> None:
    p = argparse.ArgumentParser(description="Очистка вложений чата без message_id")
    p.add_argument(
        "--min-age-hours",
        type=float,
        required=True,
        help="Удалять только записи старше этого порога (часы)",
    )
    args = p.parse_args()
    asyncio.run(_run(args.min_age_hours))


if __name__ == "__main__":
    main()
