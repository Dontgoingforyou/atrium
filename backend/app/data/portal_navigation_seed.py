"""Сид-данные дерева «разделов» (portal_nav_node) — историческое, не для нового кода.

Концепция `nav_node`/`portal_nav_node` полностью удалена из продукта (см.
0037_drop_portal_nav_node и 0080_drop_nav_node_legacy). Модуль оставлен по двум причинам:

1. На `portal_nav_seed_flat_dicts()` ссылается уже применённая историческая миграция
   `0003_portal_nav_tree.py` — переписывать/удалять применённые ревизии Alembic нельзя,
   иначе воспроизведение `alembic upgrade` с нуля на чистой БД перестанет работать.
2. `PORTAL_NAV_NAMESPACE` переиспользуется в `scripts/buildin_import/ids.py` как база для
   не связанного с навигацией стабильного UUID-namespace импорта (`BUILDIN_IMPORT_NS`) —
   удаление константы сломает этот скрипт.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

# Фиксированное пространство имён — стабильные UUID по slug между окружениями.
PORTAL_NAV_NAMESPACE = uuid.UUID("c4f8a1b2-6d3e-4f5a-9c7e-1a2b3c4d5e6f")


def nav_node_id(slug: str) -> uuid.UUID:
    return uuid.uuid5(PORTAL_NAV_NAMESPACE, slug)


@dataclass(frozen=True, slots=True)
class NavSeedRow:
    """parent_slug=None — корневой раздел."""

    parent_slug: str | None
    slug: str
    title: str
    sort_order: int


# Порядок: корни (10,20,…), затем дети с шагом 10 внутри ветки.
PORTAL_NAV_SEED: tuple[NavSeedRow, ...] = (
    NavSeedRow(None, "reglamenty", "Регламенты", 10),
    NavSeedRow("reglamenty", "reglamenty-obshchie", "Общие регламенты", 10),
    NavSeedRow("reglamenty", "reglamenty-napravleniya", "По направлениям", 20),
    NavSeedRow("reglamenty", "reglamenty-cv-shablony", "CV и шаблоны", 30),
    NavSeedRow("reglamenty", "reglamenty-instruktsii", "Инструкции", 40),
    NavSeedRow("reglamenty", "reglamenty-operau", "Операционные регламенты АУ", 50),
    NavSeedRow("reglamenty", "reglamenty-shablony-pisem", "Шаблоны писем и скрипты", 60),
    NavSeedRow("reglamenty", "reglamenty-partnery", "Работа с партнёрами", 70),
    NavSeedRow(None, "obuchenie", "Обучение", 20),
    NavSeedRow("obuchenie", "obuchenie-onboarding", "Онбординг по ролям", 10),
    NavSeedRow("obuchenie", "obuchenie-baza", "База знаний по процессам", 20),
    NavSeedRow("obuchenie", "obuchenie-materialy", "Материалы и курсы", 30),
    NavSeedRow("obuchenie", "obuchenie-proverka", "Проверка знаний", 40),
    NavSeedRow(None, "analitika", "Аналитика", 30),
    NavSeedRow("analitika", "analitika-tajmshity", "Таймшиты", 10),
    NavSeedRow("analitika", "analitika-otchety", "Отчёты", 20),
    NavSeedRow("analitika", "analitika-dashbordy", "Дашборды и планирование", 30),
    NavSeedRow("analitika", "analitika-retro", "Ретро", 40),
    NavSeedRow(None, "kommunikatsii", "Коммуникации", 40),
    NavSeedRow("kommunikatsii", "kommunikatsii-shablony", "Шаблоны и скрипты", 10),
    NavSeedRow("kommunikatsii", "kommunikatsii-tov", "Правила коммуникации и ToV", 20),
    NavSeedRow("kommunikatsii", "kommunikatsii-chaty", "Встроенные чаты", 30),
    NavSeedRow("kommunikatsii", "kommunikatsii-dogovorennosti", "Реестр договорённостей", 40),
    NavSeedRow(None, "finansy", "Финансы", 50),
    NavSeedRow("finansy", "finansy-dogovory", "Договоры, акты и счета", 10),
    NavSeedRow("finansy", "finansy-platezhi", "Платежи и расчёты", 20),
    NavSeedRow("finansy", "finansy-otchetnost", "Отчётность", 30),
    NavSeedRow("finansy", "finansy-admin", "Административные расходы", 40),
    NavSeedRow(None, "zakupki", "Закупки", 60),
    NavSeedRow("zakupki", "zakupki-protsessy", "Процессы", 10),
    NavSeedRow("zakupki", "zakupki-zayavki", "Заявки и конкурсы", 20),
    NavSeedRow("zakupki", "zakupki-kontragenty", "Контрагенты", 30),
    NavSeedRow("zakupki", "zakupki-otchety", "Отчёты и дашборды", 40),
    NavSeedRow(None, "prochee", "Прочее", 70),
    NavSeedRow("prochee", "prochee-arhiv", "Архив", 10),
    NavSeedRow("prochee", "prochee-chernoviki", "Черновики", 20),
    NavSeedRow("prochee", "prochee-sluzhebnoe", "Служебные материалы", 30),
)


def portal_nav_seed_flat_dicts() -> list[dict[str, object]]:
    """Строки для bulk_insert: id, parent_id, slug, title, sort_order."""
    rows: list[dict[str, object]] = []
    for r in PORTAL_NAV_SEED:
        pid = nav_node_id(r.parent_slug) if r.parent_slug else None
        rows.append(
            {
                "id": nav_node_id(r.slug),
                "parent_id": pid,
                "slug": r.slug,
                "title": r.title,
                "sort_order": r.sort_order,
            }
        )
    return rows
