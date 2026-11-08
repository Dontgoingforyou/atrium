# Atrium — фронтенд портала

SPA портала: **Vite**, **React 19**, **TypeScript**, **React Router**, **TanStack Query**, **Zustand** (сессия). HTTP — **fetch** через [`src/api/rawClient.ts`](src/api/rawClient.ts).

## Запуск из корня репозитория

Типовые команды — через **`make`** (см. корневой `Makefile`):

- `make dev-frontend` — dev-сервер Vite
- `make test-frontend` — Vitest
- `make ci-test-frontend` — npm ci, lint, тесты и сборка

Локально в каталоге `frontend/`: `npm run dev`, `npm run test`, `npm run lint`, `npm run build`.

## Соглашения

- Данные сервера — TanStack Query, состояние сессии — Zustand.
- **Стили:** токены в [`src/styles/tokens.css`](src/styles/tokens.css), глобальная база в [`src/styles/global.css`](src/styles/global.css); в TSX — `var(--…)`, новые экраны по возможности с **CSS Modules** рядом с компонентом.
- **Ошибки API для пользователя:** [`src/utils/apiUserMessage.ts`](src/utils/apiUserMessage.ts) и единый разбор ответов в [`src/api/parseResponse.ts`](src/api/parseResponse.ts); в UI для неизвестных ошибок — `userFacingMessageFromUnknown`.

## OpenAPI и типы

Прокси на `openapi.json` настроен в [`vite.config.ts`](vite.config.ts). Генерация клиента и типов из OpenAPI — по решению команды (пока типы ручные в `src/types/`).

## Переменные окружения

См. [`frontend/.env.example`](.env.example).
