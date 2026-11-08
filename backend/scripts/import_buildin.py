#!/usr/bin/env python3
"""Импорт документов из экспорта BuildIn в Atrium.

Переносит все страницы (.md), CSV-таблицы (кроме «Задачи») и вложения (MinIO).
Папка «Задачи» в экспорте не трогается. Идемпотентно по UUID из имён файлов BuildIn.

Примеры:
    BUILDIN_IMPORT_ROOT="/path/to/buildin-export" \\
      DATABASE_URL=postgresql+asyncpg://dev:dev@127.0.0.1:5433/atrium \\
      python scripts/import_buildin.py --dry-run

    make import-buildin-local

Переменные окружения:
    DATABASE_URL — обязательна для записи (без --dry-run)
    BUILDIN_IMPORT_ROOT — каталог экспорта
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from buildin_import.importer import print_report, run_import  # noqa: E402
from buildin_import.scan import resolve_workspace_root, scan_workspace  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine  # noqa: E402

_DEFAULT_IMPORT_ROOT = Path.home() / "buildin-export"


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Импорт документов BuildIn в Atrium")
    p.add_argument("--dry-run", action="store_true", help="Только отчёт, без БД и MinIO")
    p.add_argument("--import-root", type=Path, default=None, help="Каталог экспорта")
    return p.parse_args()


async def _main() -> None:
    args = _parse_args()
    import_root = args.import_root or Path(os.environ.get("BUILDIN_IMPORT_ROOT", _DEFAULT_IMPORT_ROOT))
    workspace = resolve_workspace_root(import_root)

    scan = scan_workspace(workspace)
    print(f"Корень workspace: {workspace}")
    from buildin_import.importer import _count_tasks_tree

    print(
        f"Скан (документы): markdown={len(scan.markdown_pages)}, "
        f"csv={len(scan.csv_tables)}, вложения={len(scan.assets)}; "
        f"в «Задачи» пропустим файлов: {_count_tasks_tree(workspace)}"
    )

    if args.dry_run:
        class _NoopSession:
            async def get(self, *args: object, **kwargs: object) -> None:
                return None

        stats = await run_import(import_root=import_root, dry_run=True, session=_NoopSession())  # type: ignore[arg-type]
        print_report(stats, workspace, dry_run=True)
        return

    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        print("ОШИБКА: задайте DATABASE_URL")
        sys.exit(1)

    engine = create_async_engine(db_url, echo=False, pool_pre_ping=True)
    session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    async with session_factory() as session:
        async with session.begin():
            stats = await run_import(import_root=import_root, dry_run=False, session=session)

    await engine.dispose()
    print_report(stats, workspace, dry_run=False)
    print("\n✅ Импорт завершён. Документы доступны по дереву parent_document_id (nav_node_id=NULL).")


if __name__ == "__main__":
    asyncio.run(_main())
