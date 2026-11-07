import uuid
from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Cosmolet API"
    debug: bool = Field(
        default=False,
        description="Режим отладки: отключает строгие проверки секретов и разрешает HTTP для admin cookie",
    )
    docs_enabled: bool = Field(
        default=True,
        description=(
            "Отдавать /docs, /redoc и /openapi.json. На staging/prod выключать "
            "(DOCS_ENABLED=false): с WAN не должно быть UI и спецификации"
        ),
    )
    database_url: str = "postgresql+asyncpg://user:password@localhost:5432/cosmolet"
    cors_origins: str = "http://127.0.0.1:5173,http://localhost:5173"
    log_level: str = "INFO"
    sqlalchemy_echo: bool = Field(
        default=False,
        description=(
            "Логировать SQL (logger sqlalchemy.engine на INFO); только при явном включении, не для prod по умолчанию"
        ),
    )
    forwarded_allow_ips: str = Field(
        default="127.0.0.1",
        description=(
            "Как у Uvicorn: доверенные хосты для X-Forwarded-Proto / X-Forwarded-For "
            "(IP, CIDR через запятую; * только в local compose за nginx). "
            "Иначе схема остаётся http и абсолютные URL (SQLAdmin static) ломают HTTPS (mixed content)."
        ),
    )
    db_pool_size: int = Field(default=10, description="Размер пула соединений с БД")
    db_max_overflow: int = Field(default=20, description="Максимум дополнительных соединений сверх пула БД")

    redis_url: str = Field(default="", description="Redis URL (пусто — кэш отключён, напр. redis://redis:6379/0)")
    redis_password: str = Field(
        default="",
        description=(
            "Пароль Redis (requirepass). Если задан, подставляется в redis_url при подключении; "
            "в .env можно не дублировать пароль в REDIS_URL"
        ),
    )
    token_cache_ttl: int = Field(default=300, description="TTL кэша SSO-токена в секундах (по умолчанию 5 мин)")

    http_client_timeout_seconds: float = Field(
        default=20.0,
        description="Таймаут httpx.AsyncClient для внешних HTTP-вызовов (SSO, шлюз и т.п.), секунды",
    )
    calendar_service_url: str = Field(
        default="",
        description=(
            "Базовый URL микросервиса календаря без завершающего слэша "
            "(REST и WS-прокси сетки). Пусто — календарь недоступен через BFF."
        ),
    )
    calendar_product: str = Field(
        default="",
        description=(
            "Имя продукта для заголовка X-Product к микросервису календаря. "
            "Должно совпадать с ключом в SSO_TENANT_ADMINS на стороне календаря."
        ),
    )
    calendar_facts_enabled: bool = Field(
        default=True,
        description="Читать факты календаря из Kafka и создавать уведомления портала",
    )
    calendar_kafka_bootstrap_servers: str = Field(
        default="",
        description="Брокеры фактов календаря. Пусто — читатель не запускается",
    )
    calendar_kafka_topic: str = Field(default="calendar", description="Топик фактов календаря")
    calendar_kafka_group: str = Field(
        default="cosmolet-calendar",
        description="Группа читателя фактов календаря",
    )

    telegram_bot_token: str = Field(
        default="",
        description="Токен Telegram-бота (@BotFather); пусто — модуль бота не запускается",
    )
    telegram_bot_username: str = Field(
        default="",
        description="Username бота без @ для deep link; если пусто — подставляется из getMe при старте",
    )
    portal_public_url: str = Field(
        default="http://localhost:5173",
        description="Публичный URL SPA для ссылок в Telegram (без завершающего /)",
    )

    vapid_public_key: str = Field(
        default="",
        description="Публичный ключ VAPID (base64url) для Web Push; пусто — подписка отключена",
    )
    vapid_private_key: str = Field(
        default="",
        description="Приватный ключ VAPID (PEM); только в окружении, не в репозитории",
    )
    vapid_contact_email: str = Field(
        default="",
        description="Контакт для VAPID claims, например admin@example.com или mailto:admin@example.com",
    )
    telegram_use_polling: bool = Field(
        default=True,
        description="true — long polling (локально и stage/prod за Amnezia); false — webhook",
    )
    telegram_webhook_base_url: str = Field(
        default="",
        description="Базовый HTTPS-URL API для setWebhook, например https://api.example.com",
    )
    telegram_webhook_path: str = Field(
        default="/tg/webhook",
        description="Путь POST webhook относительно корня приложения (не /api/v1)",
    )
    telegram_webhook_secret: str = Field(
        default="",
        description="Значение X-Telegram-Bot-Api-Secret-Token; пусто — производится от токена бота",
    )
    telegram_proxy_url: str = Field(
        default="",
        description="SOCKS5/HTTP прокси для Telegram API, например socks5://x.x.x.x:1080; пусто — прямое подключение",
    )

    minio_endpoint: str = Field(default="localhost:9063", description="MinIO/S3 endpoint (host:port, без схемы)")
    minio_public_endpoint: str = Field(
        default="",
        description=(
            "Публичный MinIO endpoint для генерации presigned URL (host:port, без схемы). "
            "Если пусто — используется minio_endpoint."
        ),
    )
    minio_access_key: str = Field(
        default="minioadmin",
        description="MinIO/S3 access key (на non-debug запрещены пустые/minioadmin — см. create_app)",
    )
    minio_secret_key: str = Field(
        default="minioadmin",
        description="MinIO/S3 secret key (только в окружении; на non-debug запрещён дефолт minioadmin)",
    )
    minio_bucket: str = Field(default="chat-attachments", description="Бакет для вложений чата")
    minio_internal_secure: bool = Field(
        default=False,
        description=(
            "HTTPS для MINIO_ENDPOINT (запись/удаление из API в Docker-сети). "
            "Обычно false: minio:9000 без TLS. Не путать с MINIO_SECURE для presigned URL."
        ),
    )
    minio_secure: bool = Field(
        default=False,
        description=(
            "HTTPS для MINIO_PUBLIC_ENDPOINT при подписи presigned URL (браузер → nginx → MinIO). "
            "Внутренний клиент использует minio_internal_secure."
        ),
    )
    attachment_max_size_bytes: int = Field(
        default=2_147_483_648,
        description="Максимальный размер загружаемого вложения в байтах (по умолчанию 2 ГБ)",
    )
    attachment_presign_ttl_seconds: int = Field(
        default=3600,
        description="TTL presigned URL для скачивания вложений (по умолчанию 1 час)",
    )
    avatar_presign_ttl_seconds: int = Field(
        default=604800,
        description="TTL presigned URL для аватарок групп чата в MinIO (по умолчанию 7 дней)",
    )
    effective_admin_base_url: str = Field(
        default="",
        description="Базовый URL Effective Admin (фото сотрудников); пусто — интеграция выключена",
    )
    effective_admin_service_token: str = Field(
        default="",
        description=(
            "Сервисный Bearer Effective Admin: чужие фото и POST /api/v1/emails/check. "
            "Пусто — фото только с токеном пользователя, сверка почт выключена"
        ),
    )
    effective_admin_timeout_seconds: float = Field(
        default=15.0,
        description="Таймаут HTTP к Effective Admin photo API (секунды)",
    )
    user_photo_url_ttl_seconds: int = Field(
        default=3600,
        description="TTL HMAC-подписи URL прокси фото пользователя (секунды)",
    )
    user_photo_meta_cache_seconds: int = Field(
        default=300,
        description="TTL кэша meta фото в Redis (секунды)",
    )

    openai_api_key: str = Field(
        default="",
        description="Ключ LLM API для эмбеддингов поиска и транскрибации Whisper",
    )
    openai_base_url: str = Field(
        default="",
        description="Base URL LLM API для эмбеддингов и Whisper (пусто — api.openai.com)",
    )
    embedding_model_name: str = Field(
        default="text-embedding-3-small",
        description="Модель OpenAI для эмбеддингов (text-embedding-3-small — 1536 dim)",
    )
    embedding_dimension: int = Field(default=1536, description="Размерность вектора (совпадает с моделью)")
    embedding_batch_size: int = Field(default=100, description="Максимальный размер батча для bulk-индексации")
    openai_whisper_model: str = Field(
        default="whisper-1",
        description="Модель OpenAI для транскрибации голосовых сообщений чата",
    )
    openai_whisper_timeout_seconds: float = Field(
        default=60.0,
        description="Таймаут HTTP-клиента OpenAI для Whisper (длиннее общего http_client_timeout)",
    )
    chat_whisper_max_size_bytes: int = Field(
        default=26_214_400,
        ge=1024,
        description="Максимальный размер файла для Whisper (по умолчанию 25 МиБ — лимит OpenAI)",
    )
    chat_whisper_rate_limit: int = Field(
        default=10,
        ge=1,
        description="Макс. запросов транскрибации на пользователя за окно",
    )
    chat_whisper_rate_window_seconds: int = Field(
        default=60,
        ge=1,
        description="Окно rate limit транскрибации (секунды)",
    )
    semantic_search_top_k: int = Field(default=20, description="Максимальное число результатов семантического поиска")
    semantic_search_min_score: float = Field(
        default=0.40,
        description="Минимальный порог косинусной похожести (0–1); результаты ниже не возвращаются",
    )

    document_trash_purge_enabled: bool = Field(
        default=True,
        description="Фоновая очистка корзины документов старше TTL (раз в сутки по UTC)",
    )
    document_trash_purge_hour_utc: int = Field(
        default=3,
        ge=0,
        le=23,
        description="Час UTC запуска очистки корзины документов (0–23)",
    )
    document_collab_service_token: str = Field(
        default="",
        description=(
            "Shared secret для Hocuspocus (заголовок X-Collab-Service-Token). "
            "Пусто — internal collab API отклоняет запросы (503)"
        ),
    )
    document_collab_enabled: bool = Field(
        default=False,
        description="Включить выдачу collab-ws-ticket и internal snapshot API",
    )
    bench_export_service_token: str = Field(
        default="",
        description=(
            "Shared secret выгрузки бенча для RAG (Authorization: Bearer). "
            "Только production. Пусто — GET /integrations/bench отвечает 503"
        ),
    )
    bench_export_document_id: uuid.UUID = Field(
        default=uuid.UUID("60629368-c9e8-492c-9def-67e3c4aa092c"),
        description="Id документа «Бенч»; не принимать из query (токен открывает только этот id)",
    )
    bench_export_rate_limit: int = Field(
        default=60,
        ge=1,
        description="Макс. GET /integrations/bench с одного IP за окно",
    )
    bench_export_rate_window_seconds: int = Field(
        default=60,
        ge=1,
        description="Окно rate limit выгрузки бенча (секунды)",
    )

    chat_orphan_attachment_purge_enabled: bool = Field(
        default=True,
        description="Фоновая очистка вложений чата без message_id старше порога (раз в сутки UTC)",
    )
    chat_orphan_attachment_purge_hour_utc: int = Field(
        default=4,
        ge=0,
        le=23,
        description="Час UTC запуска очистки осиротевших вложений чата (0–23)",
    )
    chat_orphan_attachment_purge_min_age_hours: float = Field(
        default=48.0,
        gt=0,
        description="Минимальный возраст осиротевшего вложения (часы) перед удалением",
    )

    calendar_reminders_enabled: bool = Field(
        default=True,
        description="Фоновая отправка напоминаний календаря",
    )
    calendar_reminders_interval_seconds: int = Field(
        default=60,
        ge=15,
        le=600,
        description="Интервал опроса due-напоминаний календаря (секунды)",
    )
    task_due_reminders_enabled: bool = Field(
        default=True,
        description="Фоновая отправка уведомлений о сроке задач",
    )
    task_due_reminders_interval_seconds: int = Field(
        default=60,
        ge=15,
        le=600,
        description="Интервал опроса напоминаний о сроке задач (секунды)",
    )
    calendar_invite_ttl_days: int = Field(
        default=14,
        ge=1,
        le=90,
        description="Срок жизни invite-токена календаря (дни)",
    )

    smtp_enabled: bool = Field(default=False, description="Включить отправку email через SMTP")
    smtp_host: str = Field(default="localhost", description="SMTP-хост")
    smtp_port: int = Field(default=587, ge=1, le=65535, description="SMTP-порт")
    smtp_user: str = Field(default="", description="SMTP-пользователь")
    smtp_password: str = Field(default="", description="SMTP-пароль")
    smtp_from: str = Field(default="noreply@localhost", description="Адрес From для писем")
    smtp_start_tls: bool = Field(default=True, description="STARTTLS для SMTP")
    smtp_use_tls: bool = Field(default=False, description="Implicit TLS (SMTPS) для SMTP")
    smtp_timeout_seconds: float = Field(
        default=30.0,
        ge=1,
        le=300,
        description="Таймаут SMTP-отправки (секунды)",
    )

    chat_message_body_max_length: int = Field(
        default=32_000,
        ge=1_000,
        le=100_000,
        description="Максимальная длина текста сообщения чата (символы)",
    )
    chat_attachment_upload_rate_limit: int = Field(
        default=30,
        ge=1,
        description="Макс. загрузок вложений чата на пользователя за окно (sliding window)",
    )
    chat_attachment_upload_rate_window_seconds: int = Field(
        default=60,
        ge=1,
        description="Окно rate limit загрузок вложений (секунды)",
    )
    chat_message_post_rate_limit_per_user: int = Field(
        default=120,
        ge=1,
        description="Макс. отправок сообщений на пользователя за окно",
    )
    chat_message_post_rate_limit_per_chat: int = Field(
        default=60,
        ge=1,
        description="Макс. отправок сообщений одним пользователем в один чат за окно",
    )
    chat_message_post_rate_window_seconds: int = Field(
        default=60,
        ge=1,
        description="Окно rate limit отправки сообщений (секунды)",
    )
    reindex_lock_ttl_seconds: int = Field(
        default=14_400,
        ge=60,
        description="TTL Redis-lock переиндексации (с safety-net, lock снимается по завершении задачи)",
    )
    api_mutation_rate_limit: int = Field(
        default=240,
        ge=1,
        description="Макс. mutating-запросов (POST/PUT/PATCH/DELETE) на /api/v1 на клиента за окно",
    )
    api_mutation_ip_rate_limit: int = Field(
        default=1200,
        ge=1,
        description=(
            "Потолок mutating /api/v1 с одного IP за окно (защита от обхода per-token "
            "уникальными Bearer). Должен быть выше api_mutation_rate_limit, чтобы офис за NAT не упирался"
        ),
    )
    api_mutation_rate_window_seconds: int = Field(
        default=60,
        ge=1,
        description="Окно rate limit mutating API (секунды)",
    )
    health_rate_limit: int = Field(
        default=120,
        ge=1,
        description="Макс. GET /api/v1/health с одного IP за окно (защита от flood без auth)",
    )
    health_rate_window_seconds: int = Field(
        default=60,
        ge=1,
        description="Окно rate limit health (секунды)",
    )
    semantic_search_rate_limit: int = Field(
        default=30,
        ge=1,
        description="Макс. GET /portal/search/semantic на клиента за окно",
    )
    semantic_search_ip_rate_limit: int = Field(
        default=120,
        ge=1,
        description="Потолок GET /portal/search/semantic с одного IP за окно (обход уникальными Bearer)",
    )
    semantic_search_rate_window_seconds: int = Field(
        default=60,
        ge=1,
        description="Окно rate limit семантического поиска (секунды)",
    )
    auth_login_rate_limit: int = Field(
        default=10,
        ge=1,
        description="Макс. POST /auth/login с одного IP за окно",
    )
    auth_token_rate_limit: int = Field(
        default=20,
        ge=1,
        description="Макс. POST /auth/token с одного IP за окно",
    )
    auth_refresh_rate_limit: int = Field(
        default=20,
        ge=1,
        description="Макс. POST /auth/refresh с одного IP за окно",
    )
    auth_logout_beacon_rate_limit: int = Field(
        default=60,
        ge=1,
        description="Макс. POST /auth/logout-beacon с одного IP за окно",
    )
    auth_authorization_url_rate_limit: int = Field(
        default=30,
        ge=1,
        description="Макс. GET /auth/authorization-url с одного IP за окно",
    )
    presence_beacon_rate_limit: int = Field(
        default=60,
        ge=1,
        description="Макс. POST /portal/users/me/presence-beacon с одного IP за окно",
    )
    auth_rate_window_seconds: int = Field(
        default=60,
        ge=1,
        description="Окно rate limit для auth- и beacon-эндпоинтов (секунды)",
    )

    jira_base_url: str = Field(
        default="",
        description="Базовый URL Jira. Пусто — интеграция выключена",
    )
    jira_personal_access_token: str = Field(
        default="",
        description="Personal Access Token Jira; только в окружении",
    )
    jira_project_key: str = Field(default="BASE", description="Ключ проекта Jira (База сотрудников)")
    jira_board_id: int = Field(default=68, description="ID доски Jira (rapidView)")
    jira_webhook_secret: str = Field(
        default="",
        description="Секрет webhook Jira; только в окружении",
    )
    jira_search_rate_limit: int = Field(
        default=30,
        ge=1,
        description="Макс. поисковых запросов Jira на пользователя за окно",
    )
    jira_search_rate_window_seconds: int = Field(
        default=60,
        ge=1,
        description="Окно rate limit поиска Jira (секунды)",
    )
    jira_webhook_debounce_seconds: int = Field(
        default=20,
        ge=1,
        description="Debounce webhook по issue_key (секунды)",
    )
    jira_tasks_project_key: str = Field(
        default="AUTASKS",
        description="Ключ Jira-проекта для зеркала задач портала (outbound)",
    )
    jira_tasks_board_id: int = Field(
        default=86,
        description="ID доски Jira задач портала (rapidView)",
    )
    jira_tasks_sync_enabled: bool = Field(
        default=False,
        description="Outbound Cosmolet→Jira задач; включать только на production",
    )
    jira_tasks_issue_type: str = Field(
        default="Задача",
        description="Имя типа issue при create в проекте задач",
    )

    google_sheets_sync_enabled: bool = Field(
        default=False,
        description="Фоновая синхронизация дашборда бенч из Google Таблицы",
    )
    google_sheets_spreadsheet_id: str = Field(
        default="",
        description="ID Google Таблицы со сводными листами бенч. Пусто — sync не стартует",
    )
    google_sheets_sync_interval_seconds: int = Field(
        default=600,
        ge=60,
        le=3600,
        description="Интервал sync дашборда бенч (секунды)",
    )
    google_sheets_stale_after_seconds: int = Field(
        default=900,
        ge=60,
        description="Через сколько секунд без успешного sync считать данные несвежими",
    )
    google_sheets_service_account_json: str = Field(
        default="",
        description="JSON ключ service account (строка); только в окружении, не в git",
    )
    google_sheets_timeout_seconds: float = Field(
        default=20.0,
        gt=0,
        description="Таймаут httpx для Google Sheets API (секунды)",
    )

    admin_session_secret: str = Field(
        default="",
        description="Секрет для подписи cookie-сессии панели администратора (генерируйте: openssl rand -hex 32)",
    )
    admin_session_max_age_seconds: int = Field(
        default=8 * 60 * 60,
        description="TTL cookie-сессии панели администратора (сек); по истечении — повторный вход через /admin-session",
    )

    sso_client_id: str = Field(
        default="",
        description="OAuth2 client_id по умолчанию (fallback, если redirect_uri не сопоставлён с портом/stage/prod)",
    )
    sso_client_secret: str = Field(default="", description="client_secret только в окружении, не в репозитории")
    sso_client_id_5173: str = Field(default="", description="SSO-клиент для SPA на порту 5173")
    sso_client_secret_5173: str = Field(default="")
    sso_client_id_9088: str = Field(default="", description="SSO-клиент для SPA на порту 9088 (Docker/шлюз)")
    sso_client_secret_9088: str = Field(default="")
    sso_client_id_stage: str = Field(default="", description="SSO-клиент для stage (cosmolet.stage.*)")
    sso_client_secret_stage: str = Field(default="")
    sso_client_id_prod: str = Field(default="", description="SSO-клиент для production-хоста")
    sso_client_secret_prod: str = Field(default="")
    sso_allowed_redirect_uris: str = Field(
        default=(
            "http://localhost:5173/auth/callback,"
            "http://127.0.0.1:5173/auth/callback,"
            "http://localhost:5173,"
            "http://127.0.0.1:5173,"
            "http://localhost:9088/auth/callback,"
            "http://127.0.0.1:9088/auth/callback,"
            "http://localhost:9088,"
            "http://127.0.0.1:9088"
        ),
        description="Полные redirect_uri SPA, через запятую (whitelist для обмена кода)",
    )
    sso_scopes: str = Field(default="openid profile email", description="Параметр scope при редиректе на IdP")
    sso_groups_claim: str = Field(
        default="groups",
        description="Путь к списку групп в access token (например groups или realm_access.roles)",
    )
    portal_login_allowlist: str = Field(
        default="",
        description=(
            "Белый список email для входа, через запятую. Пусто — без ограничения "
            "(локально и prod). На staging задавать PORTAL_LOGIN_ALLOWLIST."
        ),
    )

    sso_service_url: str = Field(
        default="",
        description="Базовый URL SSO-шлюза. Пусто — вход через шлюз не настроен",
    )
    sso_api_prefix: str = Field(
        default="/api/",
        description="Префикс API шлюза, token endpoint: {url}{prefix}auth/oauth2/token",
    )
    sso_auth_page_path: str = Field(
        default="/auth",
        description="Путь страницы авторизации на шлюзе",
    )
    sso_token_path: str = Field(
        default="auth/oauth2/token",
        description="Путь до token endpoint относительно префикса API шлюза (authorization_code grant)",
    )
    sso_refresh_path: str = Field(
        default="auth/refresh",
        description="Путь до refresh endpoint относительно префикса API шлюза (refresh_token grant)",
    )
    sso_userinfo_path: str = Field(
        default="auth/me",
        description="Путь GET профиля пользователя на шлюзе",
    )
    sso_logout_path: str = Field(
        default="auth/logout",
        description="Путь POST logout на шлюзе (инвалидирует токен в IdP)",
    )
    sso_login_path: str = Field(
        default="auth/login",
        description="Путь POST входа email+password относительно префикса API шлюза",
    )

    @field_validator("cors_origins", mode="before")
    @classmethod
    def strip_origins(cls, v: object) -> object:
        if isinstance(v, str):
            return ",".join(part.strip() for part in v.split(",") if part.strip())
        return v

    @field_validator("sso_allowed_redirect_uris", mode="before")
    @classmethod
    def strip_redirect_uris(cls, v: object) -> object:
        if isinstance(v, str):
            return ",".join(part.strip() for part in v.split(",") if part.strip())
        return v

    @property
    def cors_origins_list(self) -> list[str]:
        if not self.cors_origins.strip():
            return []
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def sso_redirect_uris_list(self) -> list[str]:
        if not self.sso_allowed_redirect_uris.strip():
            return []
        return [u.strip() for u in self.sso_allowed_redirect_uris.split(",") if u.strip()]

    @property
    def portal_login_allowlist_emails(self) -> frozenset[str]:
        if not self.portal_login_allowlist.strip():
            return frozenset()
        return frozenset(part.strip().lower() for part in self.portal_login_allowlist.split(",") if part.strip())

    def sso_authorization_entry_url(self) -> str:
        """Полный URL входа на шлюзе: {SSO_SERVICE_URL}{SSO_AUTH_PAGE_PATH}."""
        if not self.sso_service_url.strip():
            return ""
        base = self.sso_service_url.rstrip("/")
        path = self.sso_auth_page_path.strip() or "/auth"
        if not path.startswith("/"):
            path = "/" + path
        return f"{base}{path}"

    def _build_sso_endpoint_url(self, path: str, default: str) -> str:
        """Общая сборка URL эндпоинта шлюза: {SSO_SERVICE_URL}{SSO_API_PREFIX}{path|default}."""
        if not self.sso_service_url.strip():
            return ""
        base = self.sso_service_url.rstrip("/")
        p = (self.sso_api_prefix.strip() or "/api/").strip()
        if not p.startswith("/"):
            p = "/" + p
        p = p.rstrip("/") + "/"
        ep = path.strip().lstrip("/") or default
        return f"{base}{p}{ep}"

    def sso_token_endpoint_url(self) -> str:
        """Token endpoint шлюза: {SSO_SERVICE_URL}{SSO_API_PREFIX}{SSO_TOKEN_PATH}."""
        return self._build_sso_endpoint_url(self.sso_token_path, "auth/oauth2/token")

    def sso_refresh_endpoint_url(self) -> str:
        """Refresh endpoint шлюза: {SSO_SERVICE_URL}{SSO_API_PREFIX}{SSO_REFRESH_PATH}."""
        return self._build_sso_endpoint_url(self.sso_refresh_path, "auth/refresh")

    def sso_userinfo_url(self) -> str:
        """Userinfo endpoint шлюза: {SSO_SERVICE_URL}{SSO_API_PREFIX}{SSO_USERINFO_PATH}."""
        return self._build_sso_endpoint_url(self.sso_userinfo_path, "auth/me")

    def sso_login_endpoint_url(self) -> str:
        """Login endpoint шлюза: {SSO_SERVICE_URL}{SSO_API_PREFIX}{SSO_LOGIN_PATH}."""
        return self._build_sso_endpoint_url(self.sso_login_path, "auth/login")

    def sso_logout_endpoint_url(self) -> str:
        """Logout endpoint шлюза: {SSO_SERVICE_URL}{SSO_API_PREFIX}{SSO_LOGOUT_PATH}."""
        return self._build_sso_endpoint_url(self.sso_logout_path, "auth/logout")

    def sso_client_credential_pairs(self) -> list[tuple[str, str]]:
        """Все пары (client_id, secret) с непустыми значениями."""
        pairs: list[tuple[str, str]] = [
            (self.sso_client_id, self.sso_client_secret),
            (self.sso_client_id_5173, self.sso_client_secret_5173),
            (self.sso_client_id_9088, self.sso_client_secret_9088),
            (self.sso_client_id_stage, self.sso_client_secret_stage),
            (self.sso_client_id_prod, self.sso_client_secret_prod),
        ]
        return [(c.strip(), s.strip()) for c, s in pairs if c.strip() and s.strip()]

    @property
    def jira_enabled(self) -> bool:
        return bool(self.jira_base_url.strip() and self.jira_personal_access_token.strip())

    @property
    def google_sheets_enabled(self) -> bool:
        return bool(
            self.google_sheets_sync_enabled
            and self.google_sheets_spreadsheet_id.strip()
            and self.google_sheets_service_account_json.strip()
        )

    @property
    def jira_tasks_outbound_enabled(self) -> bool:
        """Live/backfill задач в AUTASKS: нужен флаг + настроенный Jira."""
        return self.jira_tasks_sync_enabled and self.jira_enabled

    @property
    def effective_admin_photos_enabled(self) -> bool:
        return bool(self.effective_admin_base_url.strip())

    @property
    def effective_admin_emails_check_enabled(self) -> bool:
        return bool(self.effective_admin_base_url.strip() and self.effective_admin_service_token.strip())

    def jira_browse_url(self, issue_key: str) -> str:
        base = self.jira_base_url.rstrip("/")
        return f"{base}/browse/{issue_key}"

    @property
    def sso_enabled(self) -> bool:
        return bool(self.sso_client_credential_pairs()) and bool(self.sso_service_url.strip())

    @property
    def sso_disabled_detail(self) -> str:
        """Сообщение для HTTP 503, если SSO выключен (sso_enabled ложен)."""
        if not self.sso_client_credential_pairs():
            return (
                "SSO не настроен: нет полной пары client_id/client_secret "
                "(SSO_CLIENT_ID или SSO_CLIENT_ID_5173 / _9088 / _STAGE / _PROD)."
            )
        return "SSO не настроен: задайте SSO_SERVICE_URL."

    def effective_redis_url(self) -> str:
        """URL для подключения к Redis с учётом ``REDIS_PASSWORD``."""
        from app.core.redis_url import build_redis_url_with_password  # noqa: PLC0415

        return build_redis_url_with_password(self.redis_url, self.redis_password)


@lru_cache
def get_settings() -> Settings:
    return Settings()
