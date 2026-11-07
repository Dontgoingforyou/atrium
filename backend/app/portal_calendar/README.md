# Календарь портала (`portal_calendar`)

События, RRULE, участники портала, напоминания (in-app / Telegram).

**SPA-шаринг календаря снят:** просмотр чужого календаря — только peer-view
(`GET /occurrences?user_sub=`). Публичных `POST .../share` / `DELETE .../members` нет.
Членство `PortalCalendarMember` (owner и legacy viewer/editor) остаётся в модели и SQLAdmin;
legacy invite share-token (`accept_share_token`) сохранён.

## API

Префикс: `/api/v1/portal/calendar` (роутер `router.py`).

Основные ресурсы: календари, события, occurrences (развёртка окна дат), участники события (`user_sub`), invite-токены (legacy email).

`ends_at` события — опционален (точечное событие без окончания).

При создании события обязателен хотя бы один участник. В **своём** календаре организатор
автоматически добавляется в attendees (accepted). При cross-create в календарь коллеги —
только явный список `attendees`.

### Peer-view чужого календаря

`GET /occurrences?from=&to=&user_sub=<sub>` — любой авторизованный пользователь портала может
просматривать **owned**-календари коллеги (название, время, описание, место, участники) как
read-only **замену** своей сетки (`is_peer_view=true` на всех вхождениях). Дополнительно
отдаются события, где коллега — attendee, **если** текущий пользователь сам имеет к ним доступ
(организатор, член календаря или attendee). Чужие приглашения коллеги не утекают.

Write (PATCH/DELETE события, изменение участников) — роль календаря owner|editor
**или** организатор события (`organizer_sub`), в том числе без членства (cross-create).
Peer-view чужого события по-прежнему read-only.

**Cross-create:** любой авторизованный пользователь портала (не timesheet-only) может
`POST /events` в **owned**-календарь коллеги (`GET /calendars/peer-context?user_sub=` для
primary `calendar_id`). Организатор (`organizer_sub`) — создатель; в attendees попадает
только явно указанный список (создатель **не** добавляется автоматически, если его нет
в `attendees`). Уведомления — участникам из списка. `GET /calendars/peer-context?user_sub=`
идемпотентно создаёт primary коллеге при отсутствии.

RRULE: валидация на create/update, запрет `SECONDLY`,
cap развёртки 2000 вхождений.

Peer-view occurrences: если у коллеги ещё нет календарей — пустой список (primary для
просмотра не создаём автоматически; peer-context при create — создаёт).

События, где пользователь **attendee**, остаются в своей сетке даже если календарь организатора
не выбран в `calendar_id` (фильтр галочек).

## Сервисный слой

| Модуль | Назначение |
|--------|------------|
| `_access.py` | RBAC календаря/события, lookup профилей по email |
| `_calendars.py` | CRUD календарей, primary calendar |
| `_events.py` | CRUD событий, occurrences (лимит окна 93 дня / 2000 вхождений) |
| `_attendees.py` | гости, accept invite |
| `_sharing.py` | legacy accept share-token |
| `_reminders.py` | джоб напоминаний |
| `_recurrence.py` | развёртка RRULE + overrides |

Уведомления — только через фасад `portal_collab.services.notification`.
Email внешним гостям — `app.infrastructure.email` **после** commit транзакции.

## Фоновые задачи

`app.jobs.calendar_reminders` — цикл в lifespan приложения (`CALENDAR_REMINDERS_*`).

## Real-time

`POST /portal/calendar/ws-ticket` + `WS /portal/calendar/ws` — единая комната; при create/update/delete календаря и событий клиенты инвалидируют React Query (как доска задач).

## SQLAdmin

Админ-вьюхи — `portal_calendar/admin/` (календари, события, members при необходимости).

## Env

См. `Settings`: `SMTP_*`, `CALENDAR_REMINDERS_*`, `CALENDAR_INVITE_TTL_DAYS`, `PORTAL_PUBLIC_URL`. Ключи в `deploy/ci-upload-env.sh` (`OPTIONAL_CI_KEYS`).
