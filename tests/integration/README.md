# Интеграционные тесты (Playwright)

Прогон против поднятого портала Atrium (SPA + API).
Не входит в `make test-frontend` / `make test-all` / coverage. Правила: .

## Запуск

1. Один раз зависимости npm (браузер Chromium `make test-integration` поставит сам при необходимости):

```bash
cd tests/integration && npm ci
```

2. Переменные — в **корневом** `.env` репозитория и/или в `tests/integration/.env`
   (нужны `APP_BASE_URL`, `E2E_SSO_USER_EMAIL`, `E2E_SSO_USER_PASSWORD`;
   если нет `APP_BASE_URL`, возьмётся `PORTAL_PUBLIC_URL`).

Шаблон только для integration: `cp tests/integration/.env.example tests/integration/.env`

3. Из корня (портал уже отвечает, учётка для входа задана в env):

```bash
make test-integration
```

`run-integration.sh` сам читает корневой `.env` и/или `tests/integration/.env`.
Уже экспортированные в shell переменные **перезаписываются** значениями из файла.

## CI (GitLab)

Job integration запускается после ручной выкладки.

Нужны CI/CD Variables:

- `APP_BASE_URL` — адрес портала
- `E2E_SSO_USER_EMAIL`, `E2E_SSO_USER_PASSWORD` — Masked

`allow_failure: true`, пока учётка для входа не стабильна. Не входит в обычный MR unit-пайплайн.

Пустые / `change-me` / нет env → статус **blocked** (не ложный failed).

## Переменные (`contracts.json`)

**Обязательные:**

- `APP_BASE_URL` — URL портала в браузере (локально обычно `http://127.0.0.1:9088`, не путать с Vite `:5173`)
- `E2E_SSO_USER_EMAIL`, `E2E_SSO_USER_PASSWORD` — пользователь **без** manager/admin

**Опциональные:** `SSO_BASE_URL`, `SSO_CLIENT_ID`, `SSO_CLIENT_SECRET`, `SSO_REDIRECT_URI`

## Specs

| Файл | TC |
|------|-----|
| `specs/sso-login.spec.ts` | TC-019 |
| `specs/session-reload.spec.ts` | TC-003 |
| `specs/app-shell-smoke.spec.ts` | TC-004, TC-005, TC-010 |
| `specs/rbac-ui.spec.ts` | TC-017, TC-018 (отказ или доступ — по роли E2E-пользователя) |
