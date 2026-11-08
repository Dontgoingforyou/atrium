#!/usr/bin/env python3
"""Учебные данные и векторный индекс документов, задач и сообщений.

Повторный запуск не создаёт вторые копии. Нужен PostgreSQL локального compose
(порт 5435). Запуск из корня: ``make seed``.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.demo_content import seed_demo_portal  # noqa: E402
from app.services.demo_vectors import vectorize_portal  # noqa: E402


async def _main() -> None:
    await seed_demo_portal()
    totals = await vectorize_portal()
    for entity_type, count in totals.items():
        print(f"{entity_type}: {count}")


if __name__ == "__main__":
    asyncio.run(_main())
