# project/ — карта кода (brownfield)

Код портала живёт в корне (`backend/`, `frontend/`). Перенос в `project/` ломает Makefile и compose.

## Где код

| Зона | Путь |
|------|------|
| API | [`backend/`](../backend/) — `backend/app/`, `backend/tests/`, `backend/pyproject.toml` |
| SPA | [`frontend/`](../frontend/) — `frontend/src/`, `frontend/tests/` |
| Локальный стенд | [`stand/`](../stand/) |
| Деплой | [`deploy/`](../deploy/) |
| Стендовые Playwright | [`tests/integration/`](../tests/integration/) |
| Требования и TC | [`docs/product/`](../docs/product/) |
| Правила для агента | [`AGENTS.md`](../AGENTS.md) |
