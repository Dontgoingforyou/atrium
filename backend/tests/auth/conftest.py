"""Фикстуры пакета auth."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from app.services import user_profile as up


@pytest.fixture(autouse=True)
def clear_sso_alias_caches() -> Iterator[None]:
    """Иначе alias-кэш профиля протекает между тестами."""
    up._sso_canonical_sub_by_alias.clear()
    up._logged_sso_sub_remaps.clear()
    yield
    up._sso_canonical_sub_by_alias.clear()
    up._logged_sso_sub_remaps.clear()
