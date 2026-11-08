# `portal_favorites` — избранное по документам

## Назначение

Пакет отвечает за **персональное избранное**: пользователь помечает **документы** звёздочкой (запись в `portal_favorite`), просматривает свой список и удаляет свои записи.

HTTP-роутер подключён с **`NON_DEVELOPER_ROUTE_DEPENDENCIES`**: timesheet-only (АУ/студенты) получают 403. Для остальных авторизованных ролей документы глобально читаемы — отдельного object-ACL нет.

`POST` вызывает `ensure_user_can_read_document` (документ существует, не в корзине, роль может его читать). `GET` список **не** сужает выдачу повторным RBAC: аудитория та же, что прошла зависимость роутера; в выборку попадают только живые документы текущего `user.sub`.

Тип цели **`navigation_node`** в API **не поддерживается** (ответ 404): наследие схемы БД; такие строки в список не попадают (фильтр в SQL до `LIMIT`).

**Сквозные политики** навигации и RBAC чтения документов — [../MODULES.md](../MODULES.md).

## HTTP

Роутер: [`routes/favorites.py`](routes/favorites.py), префикс **`/portal`** (итоговые пути после `/api/v1`).

**OpenAPI тег:** `Избранное`

| Метод | Путь | Описание |
|-------|------|----------|
| GET | `/portal/favorites` | Список избранного текущего пользователя (только активные документы). SPA передаёт `limit=500` (потолок Query) — полный набор для звезды на карточке |
| POST | `/portal/favorites` | Добавить документ в избранное (`target_type`: `document`) |
| DELETE | `/portal/favorites/{favorite_id}` | Удалить свою запись (чужая → 404) |

Реэкспорт: [`router.py`](router.py). Подключение в [../api/v1/router.py](../api/v1/router.py).

## Карта пакета

| Путь | Содержимое |
|------|------------|
| `routes/favorites.py` | Эндпоинты избранного |
| `services/favorite.py` | `add_favorite`, `remove_favorite`, `remove_favorites_for_documents`, `list_favorites` |
| `schemas/favorite.py` | `PortalFavoriteCreate`, `PortalFavoriteRead` |

ORM: [../infrastructure/db/models/portal_favorite.py](../infrastructure/db/models/portal_favorite.py).

При **безвозвратном удалении** и очистке корзины по TTL записи избранного на документ и поддерево удаляются фасадом `remove_favorites_for_documents` из
[`../portal_documents/services/portal_document_trash.py`](../portal_documents/services/portal_document_trash.py)
(не прямой `DELETE` по `PortalFavorite` в чужом домене — ).

**Soft-delete избранное не снимает:** список скрывает документы в корзине (`deleted_at IS NULL` в JOIN); `restore` снова показывает те же звёзды.

## Зависимости

- **`app.portal_documents.services.portal_document_queries`** — `ensure_user_can_read_document` при добавлении.
- **`app.infrastructure.db.models.portal_favorite`**, **`app.core.enums.FavoriteTargetType`**

**Обратная зависимость:** `app.portal_documents.services.portal_document_trash` вызывает
`remove_favorites_for_documents` из этого пакета при purge/TTL — не при soft-delete.

## Тесты

[`../../tests/portal_favorites/`](../../tests/portal_favorites/).

## См. также

- [../MODULES.md](../MODULES.md) — раздел `portal_favorites`.
- [../portal_home/](../portal_home/) — превью избранного на главной (`list_favorites`).
