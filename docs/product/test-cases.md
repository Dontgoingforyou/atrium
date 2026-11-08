# Atrium — тест-кейсы

Critical path портала. Автотесты: `backend/tests/`, `frontend/tests/`, `tests/integration/` (Playwright).

## TC-001 — Вход демо-учёткой

| Поле | Значение |
|------|----------|
| Связь | FR-001 |
| Риск | A |
| Экран | login |
| Дано | пользователь не авторизован, на форме есть admin / demo-admin |
| Когда | POST `/api/v1/auth/login` с этими логином и паролем |
| Тогда | 200, профиль администратора и refresh cookie |
| Автотест | backend/tests/auth/test_demo_login.py |

## TC-002 — Health API отвечает 200

| Поле | Значение |
|------|----------|
| Связь | FR-016 |
| Риск | C |
| Экран | n/a |
| Дано | API запущен |
| Когда | GET `/api/v1/health` |
| Тогда | 200 |
| Автотест | backend/tests |

## TC-003 — Тихий refresh после перезагрузки

| Поле | Значение |
|------|----------|
| Связь | FR-002 |
| Риск | A |
| Экран | app-shell |
| Дано | валидный refresh cookie, access token сброшен |
| Когда | POST `/api/v1/auth/refresh` |
| Тогда | 200 и новый access token |
| Автотест | backend/tests/auth; tests/integration/specs/session-reload.spec.ts |

## TC-004 — Открытие главной

| Поле | Значение |
|------|----------|
| Связь | FR-003 |
| Риск | B |
| Экран | home |
| Дано | авторизованный сотрудник (не student) |
| Когда | GET `/api/v1/portal/home` или открытие `/` |
| Тогда | 200 и сводка главной |
| Автотест | backend/tests/portal_home; tests/integration/specs/app-shell-smoke.spec.ts |

## TC-005 — Список задач с RBAC

| Поле | Значение |
|------|----------|
| Связь | FR-004 |
| Риск | A |
| Экран | tasks |
| Дано | авторизованный user с правом на задачи |
| Когда | открывает `/tasks` или list API |
| Тогда | только задачи своего контура прав |
| Автотест | backend/tests; tests/integration/specs/app-shell-smoke.spec.ts |

## TC-006 — Создание задачи

| Поле | Значение |
|------|----------|
| Связь | FR-004 |
| Риск | B |
| Экран | tasks |
| Дано | user с правом создавать задачи |
| Когда | создаёт задачу на `/tasks/new` или через API |
| Тогда | 201 / задача в списке |
| Автотест | backend/tests |

## TC-007 — Карточка задачи по номеру

| Поле | Значение |
|------|----------|
| Связь | FR-005 |
| Риск | B |
| Экран | task-detail |
| Дано | известный номер задачи и право на чтение |
| Когда | переход `/tasks/task-:taskNumber` |
| Тогда | карточка задачи или редирект на id |
| Автотест | frontend/tests, backend/tests |

## TC-008 — Документ без прав — отказ

| Поле | Значение |
|------|----------|
| Связь | FR-006 |
| Риск | A |
| Экран | document |
| Дано | user без права на документ |
| Когда | GET документа по id |
| Тогда | 403 или 404 без тела документа |
| Автотест | backend/tests/portal_documents |

## TC-009 — Открытие документа с правом чтения

| Поле | Значение |
|------|----------|
| Связь | FR-006 |
| Риск | B |
| Экран | document |
| Дано | user с правом чтения |
| Когда | GET `/documents/:documentId` или API документа |
| Тогда | 200 и тело документа |
| Автотест | backend/tests/portal_documents |

## TC-010 — Список чатов участника

| Поле | Значение |
|------|----------|
| Связь | FR-007 |
| Риск | B |
| Экран | chats |
| Дано | user — участник чата |
| Когда | открывает `/chats` или API чатов |
| Тогда | свои чаты в выдаче, чужие отсутствуют |
| Автотест | backend/tests/portal_chat; tests/integration/specs/app-shell-smoke.spec.ts |

## TC-011 — Принятие invite календаря

| Поле | Значение |
|------|----------|
| Связь | FR-008 |
| Риск | B |
| Экран | calendar |
| Дано | валидный invite token |
| Когда | открывает `/calendar/invite/:token` |
| Тогда | приглашение принято или показано по API-контракту |
| Автотест | backend/tests/portal_calendar |

## TC-012 — Поиск не отдаёт чужие сущности

| Поле | Значение |
|------|----------|
| Связь | FR-009 |
| Риск | A |
| Экран | search |
| Дано | сущности только во втором контуре прав |
| Когда | поиск от user первого контура |
| Тогда | чужие сущности не в выдаче |
| Автотест | backend/tests/portal_search |

## TC-013 — Каталог специалистов

| Поле | Значение |
|------|----------|
| Связь | FR-010 |
| Риск | B |
| Экран | specialists |
| Дано | авторизованный user |
| Когда | открывает `/specialists` |
| Тогда | список в рамках RBAC |
| Автотест | backend/tests/portal_specialists |

## TC-014 — Таймшиты в аналитике

| Поле | Значение |
|------|----------|
| Связь | FR-011 |
| Риск | B |
| Экран | analytics |
| Дано | авторизованный user |
| Когда | открывает `/analytics/timesheets` |
| Тогда | данные таймшитов в рамках прав |
| Автотест | backend/tests/portal_time_entries |

## TC-015 — Список тегов. Просмотр каталога

| Поле | Значение |
|------|----------|
| Связь | FR-012 |
| Риск | C |
| Экран | tags |
| Дано | авторизованный user |
| Когда | открывает `/tags` |
| Тогда | список тегов по правам |
| Автотест | backend/tests/portal_tags |

## TC-016 — Профиль текущего пользователя

| Поле | Значение |
|------|----------|
| Связь | FR-013 |
| Риск | B |
| Экран | account |
| Дано | авторизованный user |
| Когда | GET `/api/v1/auth/me` и `/account` |
| Тогда | только данные текущего пользователя |
| Автотест | backend/tests/auth |

## TC-017 — Admin bridge без прав

| Поле | Значение |
|------|----------|
| Связь | FR-014 |
| Риск | A |
| Экран | admin-bridge |
| Дано | user без admin |
| Когда | открывает admin-контур |
| Тогда | 403 или редирект без `/admin` |
| Автотест | backend/tests/admin; tests/integration/specs/rbac-ui.spec.ts |

## TC-018 — Корзина только manager/admin

| Поле | Значение |
|------|----------|
| Связь | FR-015 |
| Риск | A |
| Экран | trash |
| Дано | user без manager/admin |
| Когда | открывает `/p/trash` |
| Тогда | отказ в доступе |
| Автотест | frontend RequireManagerOrAdmin, backend RBAC; tests/integration/specs/rbac-ui.spec.ts |

## TC-019 — Вход на локальном Docker

| Поле | Значение |
|------|----------|
| Связь | FR-001 |
| Риск | A |
| Экран | login |
| Дано | портал поднят, на форме демо-учётка |
| Когда | вход логином и паролем с формы |
| Тогда | сессия в портале, refresh cookie установлен |
| Автотест | tests/integration/specs/sso-login.spec.ts |

## TC-020 — Проверка локального Docker

| Поле | Значение |
|------|----------|
| Связь | FR-016 |
| Риск | B |
| Экран | n/a |
| Дано | локальный compose |
| Когда | API и веб подняты |
| Тогда | health отвечает, вход демо-учёткой открывает главную |
| Автотест | ручная проверка compose |

## TC-021 — Автостарт guided tour

| Поле | Значение |
|------|----------|
| Связь | FR-017 |
| Риск | B |
| Экран | app-shell |
| Дано | авторизованный user (`guided_tour_completed=false`): regular/manager/admin или timesheet-only (au_specialist) |
| Когда | открывает портал после загрузки preferences |
| Тогда | показывается welcome / старт тура |
| Автотест | frontend/src/onboarding |

## TC-022 — После завершения тура автостарт не повторяется

| Поле | Значение |
|------|----------|
| Связь | FR-017 |
| Риск | B |
| Экран | app-shell |
| Дано | пользователь завершил или пропустил тур |
| Когда | повторный вход / перезагрузка SPA |
| Тогда | `guided_tour_completed=true`, автостарт не запускается |
| Автотест | frontend/src/onboarding; backend/tests/api/test_portal_account_api.py |

## TC-023 — Пройти обучение заново

| Поле | Значение |
|------|----------|
| Связь | FR-017 |
| Риск | C |
| Экран | account (regular/manager/admin) или app-shell nav «Обучение» (timesheet-only) |
| Дано | тур ранее завершён |
| Когда | нажимает «Пройти обучение заново» на `/account` или «Обучение» в меню (АУ) |
| Тогда | флаг сбрасывается, тур запускается снова |
| Автотест | frontend/src/onboarding; backend/tests/api/test_portal_account_api.py |

## TC-024 — Preferences guided_tour_completed доступен user и timesheet-only

| Поле | Значение |
|------|----------|
| Связь | FR-017 |
| Риск | A |
| Экран | n/a |
| Дано | обычный user или timesheet-only с профилем |
| Когда | GET/PATCH `/api/v1/portal/account/preferences` с `guided_tour_completed` |
| Тогда | 200 и значение сохранено; `notify_document_trash` для timesheet-only — 403 |
| Автотест | backend/tests/api/test_portal_account_api.py |

## TC-025 — Role-фильтр шагов тура по разделам

| Поле | Значение |
|------|----------|
| Связь | FR-017 |
| Риск | C |
| Экран | app-shell |
| Дано | regular / manager / portal admin / timesheet-only |
| Когда | resolveGuidedTourSteps(ctx) |
| Тогда | specialists/trash только manager\|admin; trash-purge и nav-admin только admin; chats/calendar/tags/analytics/documents — у regular user; timesheet-only — таймшиты + developer-docs + nav «Обучение», без задач/чатов/аккаунта; walkthrough полей формы (`tasks-create-title`…) и секций карточки (`tasks-detail-*`) — только manager\|admin |
| Автотест | frontend/tests/domain/guidedTour.test.ts |

## TC-026 — Guided tour: walkthrough формы и карточки задачи (manager/admin)

| Поле | Значение |
|------|----------|
| Связь | FR-017 |
| Риск | C |
| Экран | `/tasks/new`, `/tasks/{demoTaskId}` |
| Дано | manager или portal admin, guided tour running; учебная задача с cleanup |
| Когда | шаги после «Создать задачу» |
| Тогда | обзор формы + поля (название, исполнители, приоритет, срок, теги, описание) без обязательного «Создать»; затем секции карточки подзадачи/комментарии/ссылки/файлы; timesheet-only этих шагов не видит; черновик пользователя сверх demo не остаётся |
| Автотест | frontend/tests/domain/guidedTour.test.ts |
