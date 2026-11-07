# document-collab (Hocuspocus)

Self-hosted Yjs sync для body `portal_document`. Auth и CAS-snapshot — через Cosmolet
`/api/v1/internal/document-collab/*` и заголовок `X-Collab-Service-Token`.

## Env

| Переменная | Описание |
|---|---|
| `PORT` | WS порт (по умолчанию 1234) |
| `COSMOLET_API_BASE_URL` | `http://api:8000/api/v1` |
| `DOCUMENT_COLLAB_SERVICE_TOKEN` | Shared secret с API |
| `DOCUMENT_COLLAB_STORE_DEBOUNCE_MS` | Debounce onStore (по умолчанию 2000) |

Публичный path за nginx: `/collab` → этот сервис.

## Схема редактора

HTML↔Y.Doc использует тот же набор нод, что SPA (`RichTextEditor`): таблицы,
highlight (`<mark>`), task-list, кастомные toggle/image/document-link.
Список — `src/schema.mjs`. Если на фронте добавили ноду — добавить и сюда,
иначе hydrate/snapshot молча выкинет её из body.
