# Cosmolet — реестр экранов (SPA)

Канон UI — React. Ниже screen_id для Softgen FR/TC.

| screen_id | Маршрут | Primary FR | Примечание |
|-----------|---------|------------|------------|
| login | `/login` | FR-001 | SSO |
| app-shell | (layout) | FR-002 | тихий refresh; FR-017 guided tour overlay |
| home | `/` | FR-003 | шаги тура MVP |
| tasks | `/tasks`, `/tasks/new` | FR-004 | шаги тура MVP |
| task-detail | `/tasks/:taskId`, `/tasks/task-:n` | FR-005 | |
| document | `/documents/:id`, `/p/:slug/documents/:id` | FR-006 | |
| chats | `/chats` | FR-007 | |
| calendar | `/calendar`, `/calendar/invite/:token` | FR-008 | |
| search | `/search` | FR-009 | шаги тура MVP |
| specialists | `/specialists` | FR-010 | |
| analytics | `/analytics/*` | FR-011 | `/analytics/bench` — менеджер или portal_admin |
| tags | `/tags` | FR-012 | |
| account | `/account` | FR-013 | FR-017 повтор тура |
| changelog | модалка в шапке | FR-018 | иконка слева от смены темы, без маршрута |
| admin-bridge | `/admin-bridge` | FR-014 | |
| trash | `/p/trash` | FR-015 | manager/admin |

Заморожено в UI (редирект на `/`): `/agreements`, `/finance`, `/learning`.
