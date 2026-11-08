# portal_specialists — Доска воронки специалистов («Мои специалисты»)

## Назначение

Раздел «Мои специалисты»: менеджеры ведут персональную Kanban-доску с карточками специалистов
(студентов портала), перемещая их по этапам воронки. **Направление, город, Telegram и CV-ссылки
синхронизируются из Jira** (проект BASE) при привязке issue `BASE-xxxx`.

Подробности интеграции — [`../integrations/README.md`](../integrations/README.md).

## Структура

```
portal_specialists/
  router.py            ← агрегирующий роутер (include_router → api/v1/router.py)
  routes/
    board.py                    ← GET/POST /columns, board, statuses (legacy)
    jira.py                     ← Jira: search, link, sync, unlink, sync columns
    specialist_board_ws.py      ← WS real-time (тикет + менеджер/админ)
    specialist_board_pref.py    ← персональный порядок/скрытие колонок канбана
    specialist_detail.py        ← профиль, ссылки, заметки (API карточки)
  services/
    board.py                  ← реэкспорт API сервиса
    board_shared.py           ← RBAC (require_manager_or_admin, require_specialist_write_access), маппинг DTO
    board_columns_statuses.py ← колонки; CRUD portal_specialist_status (legacy)
    board_entries.py          ← записи на доске, reassign, directory
    board_realtime.py         ← Redis pub/sub события доски
    specialist_board_pref.py  ← CRUD персонального pref канбана
    jira_import.py            ← привязка, импорт полей, webhook
    jira_import_board.py      ← колонка доски и ссылки последнего импорта
    jira_board_sync.py        ← sync колонок из Jira
    specialist_jira_status_map.py ← все status id колонки Jira → column_key
    sso_profile_normalize.py  ← нормализация Telegram/даты рождения из SSO/Jira
    specialist_detail.py      ← профиль, ссылки, заметки (сервисный слой)
    search.py                 ← fulltext-поиск специалистов (RBAC для portal_search)
  schemas/
    board.py, jira.py, specialist_detail.py
  admin/
    board.py    ← PortalSpecialistColumnAdmin, PortalSpecialistStatusAdmin (legacy), PortalManagerSpecialistAdmin
    profile.py  ← PortalSpecialistProfileAdmin
  README.md            ← этот файл
```

ORM-модели (в `infrastructure/db/models/`):
- `portal_specialist_column.py` — колонки воронки (+ `jira_status_id`, только primary)
- `portal_specialist_jira_status_map.py` — все status id колонки Jira → `column_id`
- `portal_manager_specialist.py` — записи на доске менеджера
- `portal_specialist_profile.py` — профиль специалиста (+ `direction`, `jira_*`)
- `portal_specialist_link.py` — произвольные ссылки (CV из Jira upsert)
- `portal_specialist_status.py` — **legacy** справочник «направлений» (до Jira); в UI не используется

Миграции:
- `0059_portal_specialist_board.py` — колонки и `portal_manager_specialist`
- `0060_portal_specialist_status.py` — `portal_specialist_status`, FK `status_id` (legacy)
- `0067_specialist_jira` — поля Jira в профиле, `jira_status_id` на колонках
- `0068_spec_profile_direction` — `portal_specialist_profile.direction`
- `0097_specialist_board_idx` — индекс `(manager_sub, column_key, position)`
- `0110_specialist_jira_status_map` — маппинг всех status id колонки Jira

## Jira (кратко)

| Данные | Источник в Atrium |
|--------|---------------------|
| Направление | `profile.direction` ← Jira; на канбане — `status_title` из join профиля |
| Город, Telegram | `profile.location`, `profile.telegram` |
| CV-ссылки | `portal_specialist_link` |
| Колонка воронки | `status` issue → `column_key` по **всем** status id колонки доски (`portal_specialist_jira_status_map`; fallback — primary `jira_status_id` / title). У **всех** менеджеров с этим специалистом. Колонки и маппинг подтягиваются при link/sync/webhook (`ensure_specialist_columns_from_jira`); admin `POST .../columns/sync-from-jira` — тот же upsert. |
| Прочие поля Jira | read-only секция «Jira» (`jira_fields`) |

Ручной picker «направлений» и фильтры по `status_id` **убраны из UI**; источник правды — Jira.
Параметр поиска `status_ids` — **legacy** (`portal_manager_specialist.status_id`), не `profile.direction`.

Webhook/sync колонки — единая воронка по статусу Jira: карточка сдвигается у каждого
закрепления этого специалиста (не персональная колонка менеджера).

## RBAC

### Кросс-видимость менеджеров (продуктовая политика)

Менеджеры (`IDP_GROUP_MANAGER`) и администраторы портала **видят закрепления специалистов
друг друга** (`GET /board?directory=true`, карточка профиля). Мутации чужой доски по-прежнему
запрещены менеджеру (кроме admin с `?manager_sub=`).

| Операция | Требуемая роль |
|---|---|
| GET /columns, GET/PUT pref | менеджер отдела (`gid_number=10000`) ИЛИ portal_admin |
| POST/PATCH/DELETE /columns | только portal_admin |
| GET /board, POST /board | менеджер отдела ИЛИ portal_admin |
| PATCH/DELETE /board/{sub} | владелец записи ИЛИ portal_admin |
| GET карточки (профиль/ссылки/заметки/Jira) | менеджер/admin; цель — студент (`portal_chat_allowed=False`) или уже на доске |
| Jira link/sync/unlink, PATCH профиля | менеджер отдела с закреплением ИЛИ portal_admin |
| POST /columns/sync-from-jira | только portal_admin |
| GET/POST /statuses | **legacy** API; GET — менеджер/admin; POST — менеджер/admin (исключение для справочника) |

Механизм RBAC «менеджер»: `app.core.permissions.is_manager_or_admin`, единая точка входа
в модуле — `board_shared.require_manager_or_admin` / `require_specialist_write_access`.

GET профиля и GET Jira **не создают** строку `portal_specialist_profile` (insert только в write/link/sync).

**OpenAPI теги:** `Специалисты — доска`, `Специалисты — карточка`, `Специалисты — Jira`.

`GET /board` и `GET .../notes` отдают `list[T]` (контракт SPA) с SQL safety cap, без `PagedResponse`.
Тело заметки — `max_length` = лимит эмбеддинга (`EMBEDDING_TEXT_MAX_CHARS`).
Unlink Jira удаляет только CV-ссылки последнего import; ручные ссылки остаются.

## IDOR-защита

`move_on_board` и `remove_from_board` фильтруют запись по `(specialist_sub, manager_sub == user.sub)`.
Jira link/sync — `require_specialist_write_access` на `specialist_sub`.
Заметки: `note.specialist_sub` обязан совпасть с path. При отсутствии записи — `NotFoundError`.

## SQLAdmin

- **PortalSpecialistColumnAdmin** — CRUD колонок воронки.
- **PortalSpecialistStatusAdmin** — legacy CRUD направлений; данные из Jira в `profile.direction`.
- Записи на досках — через API, не через SQLAdmin.

## Стратегия загрузки отношений

`PortalManagerSpecialist` — display-only связи с `lazy="noload"`.  
Направление на канбане — join `PortalSpecialistProfile.direction`, не `status_id`.
