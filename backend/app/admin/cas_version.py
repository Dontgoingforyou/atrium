"""CAS version в SQLAdmin: не править вручную, при edit — инкремент (как SPA не обходит version)."""

from __future__ import annotations

from typing import Any


def bump_cas_version_on_edit(
    data: dict[str, Any],
    model: Any,
    *,
    is_created: bool,
) -> None:
    """Исключать ``version`` из формы; при сохранении edit — увеличить на 1 от текущего ORM."""
    if is_created:
        data.setdefault("version", 1)
        return
    current = getattr(model, "version", None)
    data["version"] = (int(current) if current is not None else 1) + 1
