# project/ — карта кода (brownfield)

Код портала живёт в корне (`backend/`, `frontend/`). Перенос в `project/` ломает Makefile и compose.

## Где код

| Зона | Путь |
|------|------|
| API | [`backend/`](../backend/) — `backend/app/`, `backend/tests/`, `backend/pyproject.toml` |
| SPA | [`frontend/`](../frontend/) — `frontend/src/`, `frontend/tests/` |
| Локальный Docker | [`docker-compose.yml`](../docker-compose.yml) |
| Деплой | [`deploy/`](../deploy/) |
| Playwright | [`tests/integration/`](../tests/integration/) |
| Карта репозитория | [`AGENTS.md`](../AGENTS.md) |
