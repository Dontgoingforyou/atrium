# Atrium

Atrium — портал для небольшой команды. В одном месте лежат документы, задачи, общий чат, календарь и доска специалистов. Вход локальный: на форме три демо-учётки с разными правами — администратор, руководитель и сотрудник.

Поиск двух видов. «По тексту» ищет точное совпадение. «По смыслу» сравнивает запрос с векторами в PostgreSQL (pgvector). Без ключа модели векторы считаются на портале по словам текста. Если в `.env` задан `OPENAI_API_KEY`, и запрос, и индекс идут во внешнюю модель эмбеддингов.

Учебные документы, задачи, чат и специалисты записывает `make seed`. Команда заодно считает векторы документов, задач и сообщений. Повторный запуск не создаёт копии. Нужен уже запущенный PostgreSQL из `make up` (порт 5435). При `DEBUG=true` то же самое происходит при старте API, если ключ модели пустой.

Портал на **FastAPI** и **React / Vite**.

Вход — локальными демо-учётками. Внешний шлюз, Jira и Telegram задаются в `.env` и остаются выключенными, пока адреса пустые.

Демо-учётки: `admin` / `demo-admin`, `manager` / `demo-manager`, `user` / `demo-user`. Вместо логина можно почту `demo-admin@example.com`, `demo-manager@example.com`, `demo-user@example.com`. Пароли публичные.

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
docker compose up -d db api
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

Обязательно задать свой `ADMIN_SESSION_SECRET` перед использованием `/admin` не на локальной машине. Jira: `JIRA_BASE_URL` и токен, иначе синхронизация не стартует.
