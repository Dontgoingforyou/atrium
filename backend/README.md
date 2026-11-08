# Backend

Префикс HTTP API: `/api/v1/` · OpenAPI: http://127.0.0.1:8000/docs

## Локально (venv)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -e ".[dev]"
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Копия настроек: `cp .env.example .env` · PostgreSQL на `localhost` (например порт **5433** при `docker compose` из этого каталога).

## Миграции (Alembic)

```bash
cd backend && source .venv/bin/activate
export DATABASE_URL=postgresql+asyncpg://dev:dev@localhost:5433/atrium
python -m alembic upgrade head
```

В Docker (корневой [`docker-compose.yml`](../docker-compose.yml), из корня репо):  
`docker compose exec api python -m alembic upgrade head`

Если раньше собирали образ без зависимости `alembic`, пересоберите API:  
`docker compose build --no-cache api`

## Docker (только API + БД)

```bash
docker compose up --build
```

## Проверки качества

```bash
ruff check alembic app tests && ruff format --check alembic app tests
mypy app
python -m pytest
```

## Pre-commit (из корня репозитория)

`pre-commit` ставится вместе с dev-зависимостями (`pip install -e ".[dev]"`). Хуки ставятся из **корня** репозитория (рядом с `.git`):

```bash
source .venv/bin/activate   # из каталога backend
cd ..
pre-commit install
pre-commit run --all-files
```

Либо без активации: `backend/.venv/bin/pre-commit install` из корня репозитория.
