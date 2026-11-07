# Cosmolet

Портал на **FastAPI** и **React / Vite**: документы, задачи, календарь, чаты.

Вход — через SSO (Keycloak или совместимый шлюз). Адрес шлюза, Jira и Telegram задаются в `.env`. Пустые значения означают, что интеграция выключена.

## Временно скрыто в UI

Разделы **Договорённости**, **Финансы** и **Обучение** скрыты из меню и SPA-маршрутов (редирект на главную). Код страниц, backend API и SQLAdmin сохранены.

## Makefile

Команды из корня репозитория. Справка: `make` или `make help`.

- Локальный стек: **`make up-build`** (логи в терминале) или **`make up`** в фоне. Остановка: **`make down`**.
- Проверки с PostgreSQL из compose: **`make ci-test-backend`**. Frontend: **`make ci-test-frontend`**.

## Backend

```bash
make venv-backend
make dev-backend
```

→ http://127.0.0.1:8000/docs

## Frontend

```bash
make install-frontend
make dev-frontend
```

→ http://127.0.0.1:5173 (прокси `/api` на порт **9062**)

Перед Vite поднимите API:

```bash
docker compose --project-directory . -f stand/docker-compose.yml up -d db api
```

либо `make up`.

## Docker

Образ `web` собирается из [`deploy/docker/Dockerfile.web`](deploy/docker/Dockerfile.web). Отдельно собирать `frontend/dist` не нужно.

```bash
cp .env.example .env
make up-build
make migrate
```

Единая точка входа: http://127.0.0.1:9088/ · API напрямую: http://127.0.0.1:9062/

Логи Grafana: http://127.0.0.1:9090 (по умолчанию `admin` / `admin`).

## Окружение

Шаблон — [`.env.example`](.env.example). Файл `.env` в git не коммитится.

Обязательно задать свой `ADMIN_SESSION_SECRET` перед использованием `/admin` не на локальной машине. SSO: `SSO_SERVICE_URL` и пара `SSO_CLIENT_ID` / `SSO_CLIENT_SECRET`. Jira: `JIRA_BASE_URL` и токен, иначе синхронизация не стартует.
