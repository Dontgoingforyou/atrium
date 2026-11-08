.DEFAULT_GOAL := help

.PHONY: help \
	install install-backend install-frontend venv-backend \
	test test-backend test-frontend test-all test-integration \
	lint lint-backend lint-frontend format format-backend typecheck \
	coverage coverage-backend coverage-frontend clean \
	build up-build up down restart logs logs-api logs-gateway shell-api status rebuild \
	migrate migrate-local alembic-revision \
	import-buildin import-buildin-local import-buildin-dry-run seed \
	ci-test ci-test-backend ci-test-frontend \
	pre-commit dev-backend dev-frontend ensure-tmp

BLUE := \033[0;34m
GREEN := \033[0;32m
YELLOW := \033[1;33m
NC := \033[0m

BACKEND_DIR := backend
FRONTEND_DIR := frontend
COMPOSE_LOCAL := docker compose --project-directory .

# Абсолютный путь: в рецептах есть «cd backend && …», относительный backend/.venv/... ломается
BACKEND_VENV_PY := $(wildcard $(BACKEND_DIR)/.venv/bin/python)
ifeq ($(BACKEND_VENV_PY),)
  BACKEND_PY := python3
else
  BACKEND_PY := $(abspath $(BACKEND_VENV_PY))
endif

BACKEND_PRE_COMMIT := $(wildcard $(BACKEND_DIR)/.venv/bin/pre-commit)
ifeq ($(BACKEND_PRE_COMMIT),)
  PRE_COMMIT_CMD := pre-commit
else
  PRE_COMMIT_CMD := $(abspath $(BACKEND_PRE_COMMIT))
endif

# Для ci-test-backend: БД из корневого docker-compose.yml (порт 5435 на localhost).
# 5433 — это backend/docker-compose.yml, его ci-test-backend не поднимает.
CI_DATABASE_URL ?= postgresql+asyncpg://dev:dev@127.0.0.1:5435/atrium

PROJECT_TMP := $(abspath .tmp)
export TMPDIR := $(PROJECT_TMP)

ensure-tmp:
	mkdir -p $(PROJECT_TMP)

# pytest-xdist: число воркеров и распределение по файлам (asyncio fixture loop scope = module)
PYTEST_NUMWORKERS ?= 2
PYTEST_XDIST_FLAGS := -n $(PYTEST_NUMWORKERS) --dist=loadfile

# Coverage для локального прогона (Cobertura: backend/coverage.xml)
PYTEST_CI_FLAGS := $(PYTEST_XDIST_FLAGS) --cov=app --cov-config=pyproject.toml --cov-report=term --cov-report=xml:coverage.xml --cov-fail-under=70 --tb=short -q

help:
	@echo "$(BLUE)=========================================$(NC)"
	@echo "$(GREEN)  Atrium$(NC)"
	@echo "$(BLUE)=========================================$(NC)"
	@echo ""
	@echo "Доступные команды:"
	@echo ""
	@echo "  $(GREEN)Разработка (Python / Node):$(NC)"
	@echo "    make venv-backend     - Создать backend/.venv и установить зависимости"
	@echo "    make install-backend  - pip install -e \".[dev]\" в backend (нужен venv или системный Python)"
	@echo "    make install-frontend - npm ci в frontend"
	@echo "    make install          - install-backend и install-frontend"
	@echo "    make test             - pytest в backend, xdist $(PYTEST_NUMWORKERS) (сужение: TEST_ARGS=tests/.../test_x.py -q)"
	@echo "    make test-frontend    - vitest в frontend"
	@echo "    make test-integration - Playwright (tests/integration; нужен env)"
	@echo "    make test-all         - backend + frontend (без Playwright)"
	@echo "    make lint             - ruff (backend) + eslint (frontend)"
	@echo "    make format           - ruff check --fix + ruff format (backend, запись)"
	@echo "    make format-backend   - то же, только backend"
	@echo "    make typecheck        - mypy app"
	@echo "    make coverage         - backend + frontend coverage"
	@echo "    make coverage-backend - pytest + coverage (htmlcov/, порог 70%)"
	@echo "    make coverage-frontend - vitest coverage domain+utils (пол: lines/stmt/fn 70%, branches 55%)"
	@echo "    make clean            - кэши Python, отчёты coverage, frontend/dist"
	@echo "    make dev-backend      - uvicorn --reload :8000"
	@echo "    make dev-frontend     - vite dev"
	@echo ""
	@echo "  $(GREEN)Docker (docker-compose.yml):$(NC)"
	@echo "    make up-build         - up --build (сборка + старт, логи в терминале)"
	@echo "    make build            - только собрать образы"
	@echo "    make up / down        - up -d / остановить стек"
	@echo "    make restart          - down + up"
	@echo "    make logs             - логи всех сервисов"
	@echo "    make logs-api         - логи api"
	@echo "    make logs-gateway     - логи gateway (9088)"
	@echo "    make shell-api        - shell в контейнере api"
	@echo "    make migrate          - alembic upgrade head в контейнере api"
	@echo "    make status           - docker compose ps"
	@echo "    make rebuild          - down -v, build --no-cache, up -d $(YELLOW)(сброс томов БД)$(NC)"
	@echo ""
	@echo "  $(GREEN)Alembic (на хосте):$(NC)"
	@echo "    make migrate-local    - upgrade head (нужен DATABASE_URL в окружении)"
	@echo "    make alembic-revision MSG=\"...\"  - revision --autogenerate"
	@echo "    make import-buildin-dry-run - отчёт импорта документов BuildIn"
	@echo "    make import-buildin-local   - импорт документов BuildIn на хост (DATABASE_URL, MinIO)"
	@echo "    make import-buildin         - импорт документов BuildIn в контейнер api"
	@echo "    make seed                 - учебные данные и векторы документов, задач и сообщений"
	@echo ""
	@echo "  $(GREEN)Локальные проверки:$(NC)"
	@echo "    make ci-test-backend    - поднять db через compose, затем lint, mypy и pytest"
	@echo "    make ci-test-frontend   - npm ci, lint, test, build"
	@echo "    make ci-test            - ci-test-backend + ci-test-frontend"
	@echo ""
	@echo "  $(GREEN)Прочее:$(NC)"
	@echo "    make pre-commit       - pre-commit run --all-files (из корня репозитория)"
	@echo ""

# -----------------------------------------------------------------------------
# Установка
# -----------------------------------------------------------------------------

venv-backend:
	@echo "$(BLUE)📦 Создание venv и установка backend-зависимостей...$(NC)"
	cd $(BACKEND_DIR) && python3 -m venv .venv
	cd $(BACKEND_DIR) && .venv/bin/python -m pip install -U pip
	cd $(BACKEND_DIR) && .venv/bin/pip install -e ".[dev]"
	@echo "$(GREEN)✅ Готово: $(BACKEND_DIR)/.venv$(NC)"

install-backend:
	@echo "$(BLUE)📦 Установка backend (pip install -e \".[dev]\")...$(NC)"
	cd $(BACKEND_DIR) && $(BACKEND_PY) -m pip install -U pip
	cd $(BACKEND_DIR) && $(BACKEND_PY) -m pip install -e ".[dev]"
	@echo "$(GREEN)✅ Backend-зависимости установлены$(NC)"

install-frontend:
	@echo "$(BLUE)📦 npm ci в frontend...$(NC)"
	cd $(FRONTEND_DIR) && npm ci
	@echo "$(GREEN)✅ Frontend-зависимости установлены$(NC)"

install: install-backend install-frontend

# -----------------------------------------------------------------------------
# Тесты и качество
# -----------------------------------------------------------------------------

# Сужение прогона: make test-backend TEST_ARGS="tests/portal_chat/test_foo.py -q"
# Другой параллелизм: make test-backend PYTEST_NUMWORKERS=2
# Отключить xdist: make test-backend TEST_ARGS="-p no:xdist --dist=no"
TEST_ARGS ?=

test: test-backend

test-backend: ensure-tmp
	@echo "$(BLUE)🧪 pytest (backend, xdist $(PYTEST_NUMWORKERS) workers)...$(NC)"
	cd $(BACKEND_DIR) && $(BACKEND_PY) -m pytest $(PYTEST_XDIST_FLAGS) $(TEST_ARGS)
	@echo "$(GREEN)✅ Тесты backend завершены$(NC)"

test-frontend:
	@echo "$(BLUE)🧪 vitest (frontend)...$(NC)"
	cd $(FRONTEND_DIR) && npm run test
	@echo "$(GREEN)✅ Тесты frontend завершены$(NC)"

# Стендовые Playwright: отдельно от unit; без env → blocked (см. tests/integration/README.md)
test-integration:
	@echo "$(BLUE)🧪 Playwright integration...$(NC)"
	./tests/integration/run-integration.sh
	@echo "$(GREEN)✅ Playwright integration завершён$(NC)"

test-all: test-backend test-frontend

lint-backend:
	@echo "$(BLUE)🔍 ruff (backend)...$(NC)"
	cd $(BACKEND_DIR) && $(BACKEND_PY) -m ruff check alembic app tests
	cd $(BACKEND_DIR) && $(BACKEND_PY) -m ruff format --check alembic app tests
	@echo "$(GREEN)✅ Ruff завершён$(NC)"

lint-frontend:
	@echo "$(BLUE)🔍 eslint (frontend)...$(NC)"
	cd $(FRONTEND_DIR) && npm run lint
	@echo "$(GREEN)✅ ESLint завершён$(NC)"

lint: lint-backend lint-frontend

format-backend:
	@echo "$(BLUE)✏️  ruff check --fix + format (backend)...$(NC)"
	cd $(BACKEND_DIR) && $(BACKEND_PY) -m ruff check --fix alembic app tests
	cd $(BACKEND_DIR) && $(BACKEND_PY) -m ruff format alembic app tests
	@echo "$(GREEN)✅ format-backend завершён$(NC)"

format: format-backend
	@echo "$(GREEN)✅ Форматирование применено$(NC)"

typecheck:
	@echo "$(BLUE)🔍 mypy...$(NC)"
	cd $(BACKEND_DIR) && $(BACKEND_PY) -m mypy app
	@echo "$(GREEN)✅ mypy завершён$(NC)"

coverage-backend:
	@echo "$(BLUE)📊 pytest + coverage (xdist $(PYTEST_NUMWORKERS) workers, порог 70%)...$(NC)"
	cd $(BACKEND_DIR) && $(BACKEND_PY) -m pytest $(PYTEST_XDIST_FLAGS) \
		--cov=app \
		--cov-config=pyproject.toml \
		--cov-report=html \
		--cov-report=term \
		--cov-fail-under=70
	@echo "$(GREEN)✅ Отчёт: $(BACKEND_DIR)/htmlcov/index.html$(NC)"

coverage-frontend:
	@echo "$(BLUE)📊 vitest + coverage (domain+utils, пол lines/stmt/fn 70%, branches 55%)...$(NC)"
	cd $(FRONTEND_DIR) && npm run test:coverage
	@echo "$(GREEN)✅ Отчёт: $(FRONTEND_DIR)/coverage/index.html$(NC)"

coverage: coverage-backend coverage-frontend

pre-commit:
	@echo "$(BLUE)🔍 pre-commit (все файлы)...$(NC)"
	$(PRE_COMMIT_CMD) run --all-files
	@echo "$(GREEN)✅ pre-commit завершён$(NC)"

clean:
	@echo "$(BLUE)🧹 Очистка временных файлов...$(NC)"
	find $(BACKEND_DIR) -type d -name "__pycache__" -prune -exec rm -rf {} + 2>/dev/null || true
	find $(BACKEND_DIR) -type f \( -name "*.pyc" -o -name "*.pyo" \) -delete 2>/dev/null || true
	find $(BACKEND_DIR) -type d -name ".pytest_cache" -prune -exec rm -rf {} + 2>/dev/null || true
	find $(BACKEND_DIR) -type d -name "*.egg-info" -prune -exec rm -rf {} + 2>/dev/null || true
	rm -rf $(BACKEND_DIR)/htmlcov $(BACKEND_DIR)/.coverage $(BACKEND_DIR)/coverage.xml
	rm -rf $(BACKEND_DIR)/pytest-of-* $(PROJECT_TMP)
	rm -rf $(FRONTEND_DIR)/coverage $(FRONTEND_DIR)/dist
	@echo "$(GREEN)✅ Очистка завершена$(NC)"

# -----------------------------------------------------------------------------
# Локальные dev-серверы
# -----------------------------------------------------------------------------

dev-backend:
	cd $(BACKEND_DIR) && $(BACKEND_PY) -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

dev-frontend:
	cd $(FRONTEND_DIR) && npm run dev

# -----------------------------------------------------------------------------
# Docker (локальный стек)
# -----------------------------------------------------------------------------

build: ensure-tmp
	@echo "$(BLUE)🔨 Сборка образов...$(NC)"
	$(COMPOSE_LOCAL) build
	@echo "$(GREEN)✅ Сборка завершена$(NC)"

up-build: ensure-tmp
	@echo "$(BLUE)🚀 docker compose up --build (foreground)...$(NC)"
	$(COMPOSE_LOCAL) up --build

up: ensure-tmp
	@echo "$(BLUE)🚀 Запуск контейнеров...$(NC)"
	$(COMPOSE_LOCAL) up -d
	@echo "$(GREEN)✅ Стек поднят. Шлюз: http://localhost:9088/$(NC)"

down:
	@echo "$(BLUE)🛑 Остановка контейнеров...$(NC)"
	$(COMPOSE_LOCAL) down
	@echo "$(GREEN)✅ Контейнеры остановлены$(NC)"

restart: down up

logs:
	$(COMPOSE_LOCAL) logs -f --tail=100

logs-api:
	$(COMPOSE_LOCAL) logs -f --tail=100 api

logs-gateway:
	$(COMPOSE_LOCAL) logs -f --tail=100 gateway

shell-api:
	$(COMPOSE_LOCAL) exec api sh

status:
	$(COMPOSE_LOCAL) ps

rebuild:
	@echo "$(YELLOW)⚠️  Удаляются тома (в т.ч. данные БД).$(NC)"
	$(COMPOSE_LOCAL) down -v
	$(COMPOSE_LOCAL) build --no-cache
	$(COMPOSE_LOCAL) up -d
	@echo "$(GREEN)✅ Пересборка завершена$(NC)"

migrate:
	@echo "$(BLUE)📊 alembic upgrade head (контейнер api)...$(NC)"
	$(COMPOSE_LOCAL) exec api python -m alembic upgrade head
	@echo "$(GREEN)✅ Миграции применены$(NC)"

migrate-local:
	@echo "$(BLUE)📊 alembic upgrade head (хост, нужен DATABASE_URL)...$(NC)"
	test -n "$$DATABASE_URL" || { echo "$(YELLOW)Задайте DATABASE_URL$(NC)" >&2; exit 1; }
	cd $(BACKEND_DIR) && $(BACKEND_PY) -m alembic upgrade head
	@echo "$(GREEN)✅ Миграции применены$(NC)"

alembic-revision:
	@test -n "$(MSG)" || { echo "$(YELLOW)Укажите MSG=\"краткое описание\"$(NC)" >&2; exit 1; }
	test -n "$$DATABASE_URL" || { echo "$(YELLOW)Для autogenerate задайте DATABASE_URL$(NC)" >&2; exit 1; }
	cd $(BACKEND_DIR) && $(BACKEND_PY) -m alembic revision --autogenerate -m "$(MSG)"

BUILDIN_IMPORT_ROOT ?=

import-buildin-dry-run:
	@echo "$(BLUE)📋 Импорт BuildIn: dry-run (без записи)...$(NC)"
	cd $(BACKEND_DIR) && BUILDIN_IMPORT_ROOT="$(BUILDIN_IMPORT_ROOT)" $(BACKEND_PY) scripts/import_buildin.py --dry-run
	@echo "$(GREEN)✅ Dry-run завершён$(NC)"

import-buildin-local:
	@echo "$(BLUE)📥 Импорт BuildIn (хост, DATABASE_URL + MinIO)...$(NC)"
	test -n "$$DATABASE_URL" || { echo "$(YELLOW)Задайте DATABASE_URL (см. make migrate-local)$(NC)" >&2; exit 1; }
	cd $(BACKEND_DIR) && BUILDIN_IMPORT_ROOT="$(BUILDIN_IMPORT_ROOT)" $(BACKEND_PY) scripts/import_buildin.py
	@echo "$(GREEN)✅ Импорт завершён$(NC)"

seed:
	@echo "$(BLUE)📚 Учебные данные и векторизация (PostgreSQL :5435)...$(NC)"
	cd $(BACKEND_DIR) && DATABASE_URL=postgresql+asyncpg://dev:dev@127.0.0.1:5435/atrium $(BACKEND_PY) scripts/seed_demo.py
	@echo "$(GREEN)✅ Учебные данные и векторы записаны$(NC)"

import-buildin:
	@echo "$(BLUE)📥 Импорт BuildIn (контейнер api)...$(NC)"
	$(COMPOSE_LOCAL) exec api mkdir -p /app/scripts/buildin_import
	docker cp backend/scripts/import_buildin.py $$($(COMPOSE_LOCAL) ps -q api):/app/scripts/import_buildin.py
	docker cp backend/scripts/buildin_import $$($(COMPOSE_LOCAL) ps -q api):/app/scripts/buildin_import
	@echo "$(YELLOW)Скопируйте экспорт в контейнер или смонтируйте BUILDIN_IMPORT_ROOT$(NC)"
	$(COMPOSE_LOCAL) exec -e BUILDIN_IMPORT_ROOT="$(BUILDIN_IMPORT_ROOT)" api python scripts/import_buildin.py
	@echo "$(GREEN)✅ Импорт завершён$(NC)"

# -----------------------------------------------------------------------------
# Локальный прогон проверок
# -----------------------------------------------------------------------------

ci-test-backend: ensure-tmp
	@echo "$(BLUE)🧪 Backend: lint, mypy, pytest (нужен доступ к Docker)...$(NC)"
	$(COMPOSE_LOCAL) up -d db
	@echo "$(BLUE)Ожидание PostgreSQL...$(NC)"
	@sleep 8
	cd $(BACKEND_DIR) && $(BACKEND_PY) -m pip install -U pip
	cd $(BACKEND_DIR) && $(BACKEND_PY) -m pip install -e ".[dev]"
	cd $(BACKEND_DIR) && $(BACKEND_PY) -m ruff check alembic app tests
	cd $(BACKEND_DIR) && $(BACKEND_PY) -m ruff format --check alembic app tests
	cd $(BACKEND_DIR) && $(BACKEND_PY) -m mypy app
	cd $(BACKEND_DIR) && DATABASE_URL=$(CI_DATABASE_URL) $(BACKEND_PY) -m alembic upgrade head
	cd $(BACKEND_DIR) && DATABASE_URL=$(CI_DATABASE_URL) $(BACKEND_PY) -m pytest $(PYTEST_CI_FLAGS)
	@echo "$(GREEN)✅ ci-test-backend завершён$(NC)"
	@echo "$(YELLOW)Контейнер db оставлен запущенным; остановка: make down$(NC)"

ci-test-frontend:
	@echo "$(BLUE)🧪 Frontend: npm ci, lint, test:coverage, build...$(NC)"
	cd $(FRONTEND_DIR) && npm ci
	cd $(FRONTEND_DIR) && npm run lint
	cd $(FRONTEND_DIR) && npm run test:coverage
	cd $(FRONTEND_DIR) && npm run build
	@echo "$(GREEN)✅ Frontend-прогон завершён$(NC)"

ci-test: ci-test-backend ci-test-frontend
