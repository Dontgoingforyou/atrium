# Минимальная длина запроса после trim (защита от слишком широкой выборки).
# SPA: frontend/src/constants/search.ts. Синхронизация:
# frontend/tests/search/portalSearchMinQueryLenSync.test.ts
PORTAL_SEARCH_MIN_QUERY_LEN: int = 2

# Ограничение длины строки поиска в query-параметре.
PORTAL_SEARCH_QUERY_MAX_LEN: int = 500

# Лимит текста эмбеддинга (~7 000 токенов RU; запас до 8 192 у OpenAI).
EMBEDDING_TEXT_MAX_CHARS: int = 15_000

# Допустимые значения types= для глобального поиска.
PORTAL_SEARCH_ENTITY_TYPE_DOCUMENT: str = "document"
PORTAL_SEARCH_ENTITY_TYPE_CHAT_MESSAGE: str = "chat_message"
PORTAL_SEARCH_ENTITY_TYPE_AGREEMENT: str = "agreement"
PORTAL_SEARCH_ENTITY_TYPE_TASK: str = "task"
PORTAL_SEARCH_ENTITY_TYPE_LEARNING_MATERIAL: str = "learning_material"
PORTAL_SEARCH_ENTITY_TYPE_SPECIALIST: str = "specialist"
PORTAL_SEARCH_ENTITY_TYPE_SPECIALIST_NOTE: str = "specialist_note"
PORTAL_SEARCH_ENTITY_TYPE_CALENDAR_EVENT: str = "calendar_event"

PORTAL_SEARCH_ENTITY_TYPES: frozenset[str] = frozenset(
    {
        PORTAL_SEARCH_ENTITY_TYPE_DOCUMENT,
        PORTAL_SEARCH_ENTITY_TYPE_CHAT_MESSAGE,
        PORTAL_SEARCH_ENTITY_TYPE_TASK,
        PORTAL_SEARCH_ENTITY_TYPE_SPECIALIST,
        PORTAL_SEARCH_ENTITY_TYPE_CALENDAR_EVENT,
    }
)

PORTAL_SEMANTIC_ENTITY_TYPES: frozenset[str] = frozenset(
    {
        PORTAL_SEARCH_ENTITY_TYPE_DOCUMENT,
        PORTAL_SEARCH_ENTITY_TYPE_CHAT_MESSAGE,
        PORTAL_SEARCH_ENTITY_TYPE_AGREEMENT,
        PORTAL_SEARCH_ENTITY_TYPE_TASK,
        PORTAL_SEARCH_ENTITY_TYPE_LEARNING_MATERIAL,
        PORTAL_SEARCH_ENTITY_TYPE_SPECIALIST,
        PORTAL_SEARCH_ENTITY_TYPE_SPECIALIST_NOTE,
        PORTAL_SEARCH_ENTITY_TYPE_CALENDAR_EVENT,
    }
)

# Дефолт GET /portal/search/semantic без ?types= — как SPA (без agreement).
# types=agreement по-прежнему валиден; reindex берёт PORTAL_SEMANTIC_ENTITY_TYPES.
PORTAL_SEMANTIC_DEFAULT_TYPES: frozenset[str] = frozenset(
    {
        PORTAL_SEARCH_ENTITY_TYPE_DOCUMENT,
        PORTAL_SEARCH_ENTITY_TYPE_CHAT_MESSAGE,
        PORTAL_SEARCH_ENTITY_TYPE_TASK,
        PORTAL_SEARCH_ENTITY_TYPE_LEARNING_MATERIAL,
        PORTAL_SEARCH_ENTITY_TYPE_SPECIALIST,
        PORTAL_SEARCH_ENTITY_TYPE_SPECIALIST_NOTE,
        PORTAL_SEARCH_ENTITY_TYPE_CALENDAR_EVENT,
    }
)
