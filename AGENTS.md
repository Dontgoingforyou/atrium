# AGENTS.md

Карта репозитория до правок в коде. `README.md` — как запустить портал. Этот файл — что лежит в репозитории и чего не коммитить.

## Профиль

| Поле | Значение |
|------|----------|
| Тип | web-api |
| HTTP API | `docs/api/openapi.yaml` |
| Локальный Docker | `docker-compose.yml` |
| Код | `backend/`, `frontend/` в корне |

## Роль

`atrium` — портал: регламенты, документы, коммуникации, задачи. Вход локальный, демо-учётки описаны в README. Разграничение прав — обязательный контур.

Внешний шлюз входа, Jira и Telegram — опциональные интеграции. Без URL и секретов в окружении они не включаются.

## Стек

- **Backend:** Python 3.12, FastAPI, SQLAlchemy async, PostgreSQL, Redis — [`backend/`](backend/).
- **Frontend:** React, Vite, TypeScript — [`frontend/`](frontend/).
- Локальный Docker — [`docker-compose.yml`](docker-compose.yml). Образы и nginx — [`deploy/`](deploy/).

## Границы

Секреты не в git (`.env`). Не переносить `backend/` и `frontend/` в `project/`.

## Где требования

[`docs/product/requirements.md`](docs/product/requirements.md), [`docs/product/test-cases.md`](docs/product/test-cases.md), [`docs/product/screens-index.md`](docs/product/screens-index.md). OpenAPI — [`docs/api/openapi.yaml`](docs/api/openapi.yaml).

## Тестирование

| Уровень | Место |
|---------|--------|
| Unit / API backend | `backend/tests/` — `make test-backend` |
| Unit frontend | `frontend/tests/` — `make test-frontend` |
| Playwright | `tests/integration/` — `make test-integration` |

После задачи — тесты, связанные с правкой. Полный прогон — только по явной просьбе.

## Git

Ветка по умолчанию — `main`. Формат коммита: `<тип>(<область>): описание`.

## Команды

```bash
make help
make venv-backend && make install-frontend
make up-build
make up / make down
make test-backend
make test-frontend
make lint && make typecheck
```

Compose только из корня репозитория:

```bash
docker compose up --build
```
