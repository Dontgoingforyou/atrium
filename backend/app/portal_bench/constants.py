"""Константы дашборда бенч."""

from pathlib import Path

FROZEN_YEAR = 2025
SEED_SOURCE = "seed"
SHEETS_SOURCE = "sheets"
SYNC_STATE_ID = 1
STALE_MESSAGE = "Данные не свежие. Показан последний успешный снимок."
LOCAL_SEED_YEAR = 2026
_DATA_DIR = Path(__file__).resolve().parent / "data"


def committed_seed_json_path(stem: str) -> Path:
    return _DATA_DIR / f"{stem}.json"


def seed_json_path(stem: str) -> Path:
    """Обезличенный сид в git; дамп с ФИО — только `*.local.json` (gitignore)."""
    local = _DATA_DIR / f"{stem}.local.json"
    if local.is_file():
        return local
    return committed_seed_json_path(stem)
