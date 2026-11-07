-- =============================================================================
-- Миграция: удаление дублей portal_user_profile после смены SSO (убран Keycloak)
-- Среда: staging
-- Дата: 2026-06-24
--
-- Причина: после того как коллега убрал Keycloak из цепочки SSO, генератор токенов
-- начал отдавать UUID v1 вместо UUID v4. Код искал профиль только по sub (PK),
-- не находил и создавал дубль. Итого 5 пользователей с двумя профилями каждый.
--
-- Решение:
--   1. Перенести данные с новых (v1) sub → старые (v4) sub во всех таблицах
--   2. Удалить specialist_profile для v1 sub (пересоздадутся из SSO при следующем логине)
--   3. Удалить дублирующие portal_user_profile с v1 sub
--
-- Маппинг (новый v1 → старый v4, который оставляем):
--   d0b09e34-2e6a-1040-99b4-6700a4844527  →  6c76ac76-2c1e-4531-8652-2bfb3cd02605  (darya.shahbazyan)
--   02af17a0-5b28-1040-8340-c5c1dba40387  →  f885afec-d4f7-49df-94fb-2621f40fa571  (diana.vasileva)
--   b5049528-e086-103f-967c-e1084cf42626  →  07c273c0-82c0-4a6a-8ccf-6ac7cff86630  (kseniya.v)
--   dea9fb32-4357-1040-82f0-c5c1dba40387  →  3d2fc355-0a8b-4438-b3a3-f6eb0ade5343  (mihail.mihailusov)
--   ce15b18a-1b52-1040-9991-6700a4844527  →  94e06cc5-8950-42e3-9620-fded96d4d19d  (nadejda.klyagina)
--
-- Запуск:
--   docker compose -f docker-compose.staging.yml exec db \
--     psql -U cosmolet -d cosmolet_staging -f /path/to/this.sql
-- =============================================================================

BEGIN;

-- ---------------------------------------------------------------------------
-- Вспомогательный маппинг v1 → v4 (используется ниже через CASE WHEN)
-- ---------------------------------------------------------------------------

-- portal_notification: recipient_sub
UPDATE portal_notification
SET recipient_sub = CASE recipient_sub
    WHEN 'd0b09e34-2e6a-1040-99b4-6700a4844527' THEN '6c76ac76-2c1e-4531-8652-2bfb3cd02605'
    WHEN '02af17a0-5b28-1040-8340-c5c1dba40387' THEN 'f885afec-d4f7-49df-94fb-2621f40fa571'
    WHEN 'b5049528-e086-103f-967c-e1084cf42626' THEN '07c273c0-82c0-4a6a-8ccf-6ac7cff86630'
    WHEN 'dea9fb32-4357-1040-82f0-c5c1dba40387' THEN '3d2fc355-0a8b-4438-b3a3-f6eb0ade5343'
    WHEN 'ce15b18a-1b52-1040-9991-6700a4844527' THEN '94e06cc5-8950-42e3-9620-fded96d4d19d'
END
WHERE recipient_sub IN (
    'd0b09e34-2e6a-1040-99b4-6700a4844527',
    '02af17a0-5b28-1040-8340-c5c1dba40387',
    'b5049528-e086-103f-967c-e1084cf42626',
    'dea9fb32-4357-1040-82f0-c5c1dba40387',
    'ce15b18a-1b52-1040-9991-6700a4844527'
);

-- portal_notification: author_sub
UPDATE portal_notification
SET author_sub = CASE author_sub
    WHEN 'd0b09e34-2e6a-1040-99b4-6700a4844527' THEN '6c76ac76-2c1e-4531-8652-2bfb3cd02605'
    WHEN '02af17a0-5b28-1040-8340-c5c1dba40387' THEN 'f885afec-d4f7-49df-94fb-2621f40fa571'
    WHEN 'b5049528-e086-103f-967c-e1084cf42626' THEN '07c273c0-82c0-4a6a-8ccf-6ac7cff86630'
    WHEN 'dea9fb32-4357-1040-82f0-c5c1dba40387' THEN '3d2fc355-0a8b-4438-b3a3-f6eb0ade5343'
    WHEN 'ce15b18a-1b52-1040-9991-6700a4844527' THEN '94e06cc5-8950-42e3-9620-fded96d4d19d'
END
WHERE author_sub IN (
    'd0b09e34-2e6a-1040-99b4-6700a4844527',
    '02af17a0-5b28-1040-8340-c5c1dba40387',
    'b5049528-e086-103f-967c-e1084cf42626',
    'dea9fb32-4357-1040-82f0-c5c1dba40387',
    'ce15b18a-1b52-1040-9991-6700a4844527'
);

-- portal_task: creator_sub
UPDATE portal_task
SET creator_sub = CASE creator_sub
    WHEN 'd0b09e34-2e6a-1040-99b4-6700a4844527' THEN '6c76ac76-2c1e-4531-8652-2bfb3cd02605'
    WHEN '02af17a0-5b28-1040-8340-c5c1dba40387' THEN 'f885afec-d4f7-49df-94fb-2621f40fa571'
    WHEN 'b5049528-e086-103f-967c-e1084cf42626' THEN '07c273c0-82c0-4a6a-8ccf-6ac7cff86630'
    WHEN 'dea9fb32-4357-1040-82f0-c5c1dba40387' THEN '3d2fc355-0a8b-4438-b3a3-f6eb0ade5343'
    WHEN 'ce15b18a-1b52-1040-9991-6700a4844527' THEN '94e06cc5-8950-42e3-9620-fded96d4d19d'
END
WHERE creator_sub IN (
    'd0b09e34-2e6a-1040-99b4-6700a4844527',
    '02af17a0-5b28-1040-8340-c5c1dba40387',
    'b5049528-e086-103f-967c-e1084cf42626',
    'dea9fb32-4357-1040-82f0-c5c1dba40387',
    'ce15b18a-1b52-1040-9991-6700a4844527'
);

-- portal_task: assignee_sub
UPDATE portal_task
SET assignee_sub = CASE assignee_sub
    WHEN 'd0b09e34-2e6a-1040-99b4-6700a4844527' THEN '6c76ac76-2c1e-4531-8652-2bfb3cd02605'
    WHEN '02af17a0-5b28-1040-8340-c5c1dba40387' THEN 'f885afec-d4f7-49df-94fb-2621f40fa571'
    WHEN 'b5049528-e086-103f-967c-e1084cf42626' THEN '07c273c0-82c0-4a6a-8ccf-6ac7cff86630'
    WHEN 'dea9fb32-4357-1040-82f0-c5c1dba40387' THEN '3d2fc355-0a8b-4438-b3a3-f6eb0ade5343'
    WHEN 'ce15b18a-1b52-1040-9991-6700a4844527' THEN '94e06cc5-8950-42e3-9620-fded96d4d19d'
END
WHERE assignee_sub IN (
    'd0b09e34-2e6a-1040-99b4-6700a4844527',
    '02af17a0-5b28-1040-8340-c5c1dba40387',
    'b5049528-e086-103f-967c-e1084cf42626',
    'dea9fb32-4357-1040-82f0-c5c1dba40387',
    'ce15b18a-1b52-1040-9991-6700a4844527'
);

-- portal_task_assignee (many-to-many, уникальный индекс по (task_id, assignee_sub))
-- Сначала удаляем конфликтные строки: v1-запись для задачи, где v4 уже есть
DELETE FROM portal_task_assignee v1_row
WHERE v1_row.assignee_sub IN (
    'd0b09e34-2e6a-1040-99b4-6700a4844527',
    '02af17a0-5b28-1040-8340-c5c1dba40387',
    'b5049528-e086-103f-967c-e1084cf42626',
    'dea9fb32-4357-1040-82f0-c5c1dba40387',
    'ce15b18a-1b52-1040-9991-6700a4844527'
)
AND EXISTS (
    SELECT 1 FROM portal_task_assignee v4_row
    WHERE v4_row.task_id = v1_row.task_id
    AND v4_row.assignee_sub = CASE v1_row.assignee_sub
        WHEN 'd0b09e34-2e6a-1040-99b4-6700a4844527' THEN '6c76ac76-2c1e-4531-8652-2bfb3cd02605'
        WHEN '02af17a0-5b28-1040-8340-c5c1dba40387' THEN 'f885afec-d4f7-49df-94fb-2621f40fa571'
        WHEN 'b5049528-e086-103f-967c-e1084cf42626' THEN '07c273c0-82c0-4a6a-8ccf-6ac7cff86630'
        WHEN 'dea9fb32-4357-1040-82f0-c5c1dba40387' THEN '3d2fc355-0a8b-4438-b3a3-f6eb0ade5343'
        WHEN 'ce15b18a-1b52-1040-9991-6700a4844527' THEN '94e06cc5-8950-42e3-9620-fded96d4d19d'
    END
);

-- Оставшиеся v1-строки без конфликта просто обновляем
UPDATE portal_task_assignee
SET assignee_sub = CASE assignee_sub
    WHEN 'd0b09e34-2e6a-1040-99b4-6700a4844527' THEN '6c76ac76-2c1e-4531-8652-2bfb3cd02605'
    WHEN '02af17a0-5b28-1040-8340-c5c1dba40387' THEN 'f885afec-d4f7-49df-94fb-2621f40fa571'
    WHEN 'b5049528-e086-103f-967c-e1084cf42626' THEN '07c273c0-82c0-4a6a-8ccf-6ac7cff86630'
    WHEN 'dea9fb32-4357-1040-82f0-c5c1dba40387' THEN '3d2fc355-0a8b-4438-b3a3-f6eb0ade5343'
    WHEN 'ce15b18a-1b52-1040-9991-6700a4844527' THEN '94e06cc5-8950-42e3-9620-fded96d4d19d'
END
WHERE assignee_sub IN (
    'd0b09e34-2e6a-1040-99b4-6700a4844527',
    '02af17a0-5b28-1040-8340-c5c1dba40387',
    'b5049528-e086-103f-967c-e1084cf42626',
    'dea9fb32-4357-1040-82f0-c5c1dba40387',
    'ce15b18a-1b52-1040-9991-6700a4844527'
);

-- portal_task_comment: author_sub
UPDATE portal_task_comment
SET author_sub = CASE author_sub
    WHEN 'd0b09e34-2e6a-1040-99b4-6700a4844527' THEN '6c76ac76-2c1e-4531-8652-2bfb3cd02605'
    WHEN '02af17a0-5b28-1040-8340-c5c1dba40387' THEN 'f885afec-d4f7-49df-94fb-2621f40fa571'
    WHEN 'b5049528-e086-103f-967c-e1084cf42626' THEN '07c273c0-82c0-4a6a-8ccf-6ac7cff86630'
    WHEN 'dea9fb32-4357-1040-82f0-c5c1dba40387' THEN '3d2fc355-0a8b-4438-b3a3-f6eb0ade5343'
    WHEN 'ce15b18a-1b52-1040-9991-6700a4844527' THEN '94e06cc5-8950-42e3-9620-fded96d4d19d'
END
WHERE author_sub IN (
    'd0b09e34-2e6a-1040-99b4-6700a4844527',
    '02af17a0-5b28-1040-8340-c5c1dba40387',
    'b5049528-e086-103f-967c-e1084cf42626',
    'dea9fb32-4357-1040-82f0-c5c1dba40387',
    'ce15b18a-1b52-1040-9991-6700a4844527'
);

-- portal_task_link: created_by_sub
UPDATE portal_task_link
SET created_by_sub = CASE created_by_sub
    WHEN 'd0b09e34-2e6a-1040-99b4-6700a4844527' THEN '6c76ac76-2c1e-4531-8652-2bfb3cd02605'
    WHEN '02af17a0-5b28-1040-8340-c5c1dba40387' THEN 'f885afec-d4f7-49df-94fb-2621f40fa571'
    WHEN 'b5049528-e086-103f-967c-e1084cf42626' THEN '07c273c0-82c0-4a6a-8ccf-6ac7cff86630'
    WHEN 'dea9fb32-4357-1040-82f0-c5c1dba40387' THEN '3d2fc355-0a8b-4438-b3a3-f6eb0ade5343'
    WHEN 'ce15b18a-1b52-1040-9991-6700a4844527' THEN '94e06cc5-8950-42e3-9620-fded96d4d19d'
END
WHERE created_by_sub IN (
    'd0b09e34-2e6a-1040-99b4-6700a4844527',
    '02af17a0-5b28-1040-8340-c5c1dba40387',
    'b5049528-e086-103f-967c-e1084cf42626',
    'dea9fb32-4357-1040-82f0-c5c1dba40387',
    'ce15b18a-1b52-1040-9991-6700a4844527'
);

-- portal_task_history: changed_by_sub
UPDATE portal_task_history
SET changed_by_sub = CASE changed_by_sub
    WHEN 'd0b09e34-2e6a-1040-99b4-6700a4844527' THEN '6c76ac76-2c1e-4531-8652-2bfb3cd02605'
    WHEN '02af17a0-5b28-1040-8340-c5c1dba40387' THEN 'f885afec-d4f7-49df-94fb-2621f40fa571'
    WHEN 'b5049528-e086-103f-967c-e1084cf42626' THEN '07c273c0-82c0-4a6a-8ccf-6ac7cff86630'
    WHEN 'dea9fb32-4357-1040-82f0-c5c1dba40387' THEN '3d2fc355-0a8b-4438-b3a3-f6eb0ade5343'
    WHEN 'ce15b18a-1b52-1040-9991-6700a4844527' THEN '94e06cc5-8950-42e3-9620-fded96d4d19d'
END
WHERE changed_by_sub IN (
    'd0b09e34-2e6a-1040-99b4-6700a4844527',
    '02af17a0-5b28-1040-8340-c5c1dba40387',
    'b5049528-e086-103f-967c-e1084cf42626',
    'dea9fb32-4357-1040-82f0-c5c1dba40387',
    'ce15b18a-1b52-1040-9991-6700a4844527'
);

-- portal_document: author_sub, owner_sub
UPDATE portal_document
SET author_sub = CASE author_sub
    WHEN 'd0b09e34-2e6a-1040-99b4-6700a4844527' THEN '6c76ac76-2c1e-4531-8652-2bfb3cd02605'
    WHEN '02af17a0-5b28-1040-8340-c5c1dba40387' THEN 'f885afec-d4f7-49df-94fb-2621f40fa571'
    WHEN 'b5049528-e086-103f-967c-e1084cf42626' THEN '07c273c0-82c0-4a6a-8ccf-6ac7cff86630'
    WHEN 'dea9fb32-4357-1040-82f0-c5c1dba40387' THEN '3d2fc355-0a8b-4438-b3a3-f6eb0ade5343'
    WHEN 'ce15b18a-1b52-1040-9991-6700a4844527' THEN '94e06cc5-8950-42e3-9620-fded96d4d19d'
END
WHERE author_sub IN (
    'd0b09e34-2e6a-1040-99b4-6700a4844527',
    '02af17a0-5b28-1040-8340-c5c1dba40387',
    'b5049528-e086-103f-967c-e1084cf42626',
    'dea9fb32-4357-1040-82f0-c5c1dba40387',
    'ce15b18a-1b52-1040-9991-6700a4844527'
);

UPDATE portal_document
SET owner_sub = CASE owner_sub
    WHEN 'd0b09e34-2e6a-1040-99b4-6700a4844527' THEN '6c76ac76-2c1e-4531-8652-2bfb3cd02605'
    WHEN '02af17a0-5b28-1040-8340-c5c1dba40387' THEN 'f885afec-d4f7-49df-94fb-2621f40fa571'
    WHEN 'b5049528-e086-103f-967c-e1084cf42626' THEN '07c273c0-82c0-4a6a-8ccf-6ac7cff86630'
    WHEN 'dea9fb32-4357-1040-82f0-c5c1dba40387' THEN '3d2fc355-0a8b-4438-b3a3-f6eb0ade5343'
    WHEN 'ce15b18a-1b52-1040-9991-6700a4844527' THEN '94e06cc5-8950-42e3-9620-fded96d4d19d'
END
WHERE owner_sub IN (
    'd0b09e34-2e6a-1040-99b4-6700a4844527',
    '02af17a0-5b28-1040-8340-c5c1dba40387',
    'b5049528-e086-103f-967c-e1084cf42626',
    'dea9fb32-4357-1040-82f0-c5c1dba40387',
    'ce15b18a-1b52-1040-9991-6700a4844527'
);

-- portal_document_comment: author_sub
UPDATE portal_document_comment
SET author_sub = CASE author_sub
    WHEN 'd0b09e34-2e6a-1040-99b4-6700a4844527' THEN '6c76ac76-2c1e-4531-8652-2bfb3cd02605'
    WHEN '02af17a0-5b28-1040-8340-c5c1dba40387' THEN 'f885afec-d4f7-49df-94fb-2621f40fa571'
    WHEN 'b5049528-e086-103f-967c-e1084cf42626' THEN '07c273c0-82c0-4a6a-8ccf-6ac7cff86630'
    WHEN 'dea9fb32-4357-1040-82f0-c5c1dba40387' THEN '3d2fc355-0a8b-4438-b3a3-f6eb0ade5343'
    WHEN 'ce15b18a-1b52-1040-9991-6700a4844527' THEN '94e06cc5-8950-42e3-9620-fded96d4d19d'
END
WHERE author_sub IN (
    'd0b09e34-2e6a-1040-99b4-6700a4844527',
    '02af17a0-5b28-1040-8340-c5c1dba40387',
    'b5049528-e086-103f-967c-e1084cf42626',
    'dea9fb32-4357-1040-82f0-c5c1dba40387',
    'ce15b18a-1b52-1040-9991-6700a4844527'
);

-- portal_nav_node_comment: author_sub
UPDATE portal_nav_node_comment
SET author_sub = CASE author_sub
    WHEN 'd0b09e34-2e6a-1040-99b4-6700a4844527' THEN '6c76ac76-2c1e-4531-8652-2bfb3cd02605'
    WHEN '02af17a0-5b28-1040-8340-c5c1dba40387' THEN 'f885afec-d4f7-49df-94fb-2621f40fa571'
    WHEN 'b5049528-e086-103f-967c-e1084cf42626' THEN '07c273c0-82c0-4a6a-8ccf-6ac7cff86630'
    WHEN 'dea9fb32-4357-1040-82f0-c5c1dba40387' THEN '3d2fc355-0a8b-4438-b3a3-f6eb0ade5343'
    WHEN 'ce15b18a-1b52-1040-9991-6700a4844527' THEN '94e06cc5-8950-42e3-9620-fded96d4d19d'
END
WHERE author_sub IN (
    'd0b09e34-2e6a-1040-99b4-6700a4844527',
    '02af17a0-5b28-1040-8340-c5c1dba40387',
    'b5049528-e086-103f-967c-e1084cf42626',
    'dea9fb32-4357-1040-82f0-c5c1dba40387',
    'ce15b18a-1b52-1040-9991-6700a4844527'
);

-- portal_agreement: created_by_sub
UPDATE portal_agreement
SET created_by_sub = CASE created_by_sub
    WHEN 'd0b09e34-2e6a-1040-99b4-6700a4844527' THEN '6c76ac76-2c1e-4531-8652-2bfb3cd02605'
    WHEN '02af17a0-5b28-1040-8340-c5c1dba40387' THEN 'f885afec-d4f7-49df-94fb-2621f40fa571'
    WHEN 'b5049528-e086-103f-967c-e1084cf42626' THEN '07c273c0-82c0-4a6a-8ccf-6ac7cff86630'
    WHEN 'dea9fb32-4357-1040-82f0-c5c1dba40387' THEN '3d2fc355-0a8b-4438-b3a3-f6eb0ade5343'
    WHEN 'ce15b18a-1b52-1040-9991-6700a4844527' THEN '94e06cc5-8950-42e3-9620-fded96d4d19d'
END
WHERE created_by_sub IN (
    'd0b09e34-2e6a-1040-99b4-6700a4844527',
    '02af17a0-5b28-1040-8340-c5c1dba40387',
    'b5049528-e086-103f-967c-e1084cf42626',
    'dea9fb32-4357-1040-82f0-c5c1dba40387',
    'ce15b18a-1b52-1040-9991-6700a4844527'
);

-- portal_chat: created_by_sub
UPDATE portal_chat
SET created_by_sub = CASE created_by_sub
    WHEN 'd0b09e34-2e6a-1040-99b4-6700a4844527' THEN '6c76ac76-2c1e-4531-8652-2bfb3cd02605'
    WHEN '02af17a0-5b28-1040-8340-c5c1dba40387' THEN 'f885afec-d4f7-49df-94fb-2621f40fa571'
    WHEN 'b5049528-e086-103f-967c-e1084cf42626' THEN '07c273c0-82c0-4a6a-8ccf-6ac7cff86630'
    WHEN 'dea9fb32-4357-1040-82f0-c5c1dba40387' THEN '3d2fc355-0a8b-4438-b3a3-f6eb0ade5343'
    WHEN 'ce15b18a-1b52-1040-9991-6700a4844527' THEN '94e06cc5-8950-42e3-9620-fded96d4d19d'
END
WHERE created_by_sub IN (
    'd0b09e34-2e6a-1040-99b4-6700a4844527',
    '02af17a0-5b28-1040-8340-c5c1dba40387',
    'b5049528-e086-103f-967c-e1084cf42626',
    'dea9fb32-4357-1040-82f0-c5c1dba40387',
    'ce15b18a-1b52-1040-9991-6700a4844527'
);

-- portal_chat_message: author_sub
UPDATE portal_chat_message
SET author_sub = CASE author_sub
    WHEN 'd0b09e34-2e6a-1040-99b4-6700a4844527' THEN '6c76ac76-2c1e-4531-8652-2bfb3cd02605'
    WHEN '02af17a0-5b28-1040-8340-c5c1dba40387' THEN 'f885afec-d4f7-49df-94fb-2621f40fa571'
    WHEN 'b5049528-e086-103f-967c-e1084cf42626' THEN '07c273c0-82c0-4a6a-8ccf-6ac7cff86630'
    WHEN 'dea9fb32-4357-1040-82f0-c5c1dba40387' THEN '3d2fc355-0a8b-4438-b3a3-f6eb0ade5343'
    WHEN 'ce15b18a-1b52-1040-9991-6700a4844527' THEN '94e06cc5-8950-42e3-9620-fded96d4d19d'
END
WHERE author_sub IN (
    'd0b09e34-2e6a-1040-99b4-6700a4844527',
    '02af17a0-5b28-1040-8340-c5c1dba40387',
    'b5049528-e086-103f-967c-e1084cf42626',
    'dea9fb32-4357-1040-82f0-c5c1dba40387',
    'ce15b18a-1b52-1040-9991-6700a4844527'
);

-- portal_chat_attachment: uploader_sub
UPDATE portal_chat_attachment
SET uploader_sub = CASE uploader_sub
    WHEN 'd0b09e34-2e6a-1040-99b4-6700a4844527' THEN '6c76ac76-2c1e-4531-8652-2bfb3cd02605'
    WHEN '02af17a0-5b28-1040-8340-c5c1dba40387' THEN 'f885afec-d4f7-49df-94fb-2621f40fa571'
    WHEN 'b5049528-e086-103f-967c-e1084cf42626' THEN '07c273c0-82c0-4a6a-8ccf-6ac7cff86630'
    WHEN 'dea9fb32-4357-1040-82f0-c5c1dba40387' THEN '3d2fc355-0a8b-4438-b3a3-f6eb0ade5343'
    WHEN 'ce15b18a-1b52-1040-9991-6700a4844527' THEN '94e06cc5-8950-42e3-9620-fded96d4d19d'
END
WHERE uploader_sub IN (
    'd0b09e34-2e6a-1040-99b4-6700a4844527',
    '02af17a0-5b28-1040-8340-c5c1dba40387',
    'b5049528-e086-103f-967c-e1084cf42626',
    'dea9fb32-4357-1040-82f0-c5c1dba40387',
    'ce15b18a-1b52-1040-9991-6700a4844527'
);

-- portal_specialist_note: author_sub
UPDATE portal_specialist_note
SET author_sub = CASE author_sub
    WHEN 'd0b09e34-2e6a-1040-99b4-6700a4844527' THEN '6c76ac76-2c1e-4531-8652-2bfb3cd02605'
    WHEN '02af17a0-5b28-1040-8340-c5c1dba40387' THEN 'f885afec-d4f7-49df-94fb-2621f40fa571'
    WHEN 'b5049528-e086-103f-967c-e1084cf42626' THEN '07c273c0-82c0-4a6a-8ccf-6ac7cff86630'
    WHEN 'dea9fb32-4357-1040-82f0-c5c1dba40387' THEN '3d2fc355-0a8b-4438-b3a3-f6eb0ade5343'
    WHEN 'ce15b18a-1b52-1040-9991-6700a4844527' THEN '94e06cc5-8950-42e3-9620-fded96d4d19d'
END
WHERE author_sub IN (
    'd0b09e34-2e6a-1040-99b4-6700a4844527',
    '02af17a0-5b28-1040-8340-c5c1dba40387',
    'b5049528-e086-103f-967c-e1084cf42626',
    'dea9fb32-4357-1040-82f0-c5c1dba40387',
    'ce15b18a-1b52-1040-9991-6700a4844527'
);

-- portal_learning: created_by_sub, user_sub (таблица может отсутствовать на старых средах)
DO $$
BEGIN
    IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'portal_learning') THEN
        UPDATE portal_learning
        SET created_by_sub = CASE created_by_sub
            WHEN 'd0b09e34-2e6a-1040-99b4-6700a4844527' THEN '6c76ac76-2c1e-4531-8652-2bfb3cd02605'
            WHEN '02af17a0-5b28-1040-8340-c5c1dba40387' THEN 'f885afec-d4f7-49df-94fb-2621f40fa571'
            WHEN 'b5049528-e086-103f-967c-e1084cf42626' THEN '07c273c0-82c0-4a6a-8ccf-6ac7cff86630'
            WHEN 'dea9fb32-4357-1040-82f0-c5c1dba40387' THEN '3d2fc355-0a8b-4438-b3a3-f6eb0ade5343'
            WHEN 'ce15b18a-1b52-1040-9991-6700a4844527' THEN '94e06cc5-8950-42e3-9620-fded96d4d19d'
        END
        WHERE created_by_sub IN (
            'd0b09e34-2e6a-1040-99b4-6700a4844527',
            '02af17a0-5b28-1040-8340-c5c1dba40387',
            'b5049528-e086-103f-967c-e1084cf42626',
            'dea9fb32-4357-1040-82f0-c5c1dba40387',
            'ce15b18a-1b52-1040-9991-6700a4844527'
        );
    END IF;
END $$;

-- portal_rich_media: uploader_sub
UPDATE portal_rich_media
SET uploader_sub = CASE uploader_sub
    WHEN 'd0b09e34-2e6a-1040-99b4-6700a4844527' THEN '6c76ac76-2c1e-4531-8652-2bfb3cd02605'
    WHEN '02af17a0-5b28-1040-8340-c5c1dba40387' THEN 'f885afec-d4f7-49df-94fb-2621f40fa571'
    WHEN 'b5049528-e086-103f-967c-e1084cf42626' THEN '07c273c0-82c0-4a6a-8ccf-6ac7cff86630'
    WHEN 'dea9fb32-4357-1040-82f0-c5c1dba40387' THEN '3d2fc355-0a8b-4438-b3a3-f6eb0ade5343'
    WHEN 'ce15b18a-1b52-1040-9991-6700a4844527' THEN '94e06cc5-8950-42e3-9620-fded96d4d19d'
END
WHERE uploader_sub IN (
    'd0b09e34-2e6a-1040-99b4-6700a4844527',
    '02af17a0-5b28-1040-8340-c5c1dba40387',
    'b5049528-e086-103f-967c-e1084cf42626',
    'dea9fb32-4357-1040-82f0-c5c1dba40387',
    'ce15b18a-1b52-1040-9991-6700a4844527'
);

-- portal_time_entry: user_sub
UPDATE portal_time_entry
SET user_sub = CASE user_sub
    WHEN 'd0b09e34-2e6a-1040-99b4-6700a4844527' THEN '6c76ac76-2c1e-4531-8652-2bfb3cd02605'
    WHEN '02af17a0-5b28-1040-8340-c5c1dba40387' THEN 'f885afec-d4f7-49df-94fb-2621f40fa571'
    WHEN 'b5049528-e086-103f-967c-e1084cf42626' THEN '07c273c0-82c0-4a6a-8ccf-6ac7cff86630'
    WHEN 'dea9fb32-4357-1040-82f0-c5c1dba40387' THEN '3d2fc355-0a8b-4438-b3a3-f6eb0ade5343'
    WHEN 'ce15b18a-1b52-1040-9991-6700a4844527' THEN '94e06cc5-8950-42e3-9620-fded96d4d19d'
END
WHERE user_sub IN (
    'd0b09e34-2e6a-1040-99b4-6700a4844527',
    '02af17a0-5b28-1040-8340-c5c1dba40387',
    'b5049528-e086-103f-967c-e1084cf42626',
    'dea9fb32-4357-1040-82f0-c5c1dba40387',
    'ce15b18a-1b52-1040-9991-6700a4844527'
);

-- Оставшиеся таблицы — единый DO-блок.
-- Для таблиц с UNIQUE(user_sub, ...) применяем паттерн: сначала DELETE конфликтов, потом UPDATE.
-- Таблицы настроек (board_pref, web_push) — просто DELETE v1 целиком (пересоздадутся автоматически).
DO $$
DECLARE
    v1_subs TEXT[] := ARRAY[
        'd0b09e34-2e6a-1040-99b4-6700a4844527',
        '02af17a0-5b28-1040-8340-c5c1dba40387',
        'b5049528-e086-103f-967c-e1084cf42626',
        'dea9fb32-4357-1040-82f0-c5c1dba40387',
        'ce15b18a-1b52-1040-9991-6700a4844527'
    ];
BEGIN
    -- portal_user_task_board_pref: UNIQUE(user_sub, scope_key) — удаляем v1 целиком
    IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'portal_user_task_board_pref') THEN
        DELETE FROM portal_user_task_board_pref WHERE user_sub = ANY(v1_subs);
    END IF;

    -- portal_user_specialist_board_pref: аналогично — удаляем v1 целиком
    IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'portal_user_specialist_board_pref') THEN
        DELETE FROM portal_user_specialist_board_pref WHERE user_sub = ANY(v1_subs);
    END IF;

    -- portal_web_push: пуш-токены, привязаны к устройству — удаляем v1 целиком
    IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'portal_web_push') THEN
        DELETE FROM portal_web_push WHERE user_sub = ANY(v1_subs);
    END IF;

    -- portal_favorite: DELETE конфликтов (где v4 уже есть), UPDATE остальных
    IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'portal_favorite') THEN
        DELETE FROM portal_favorite v1_row
        WHERE v1_row.user_sub = ANY(v1_subs)
          AND EXISTS (
              SELECT 1 FROM portal_favorite v4_row
              WHERE v4_row.user_sub = CASE v1_row.user_sub
                  WHEN 'd0b09e34-2e6a-1040-99b4-6700a4844527' THEN '6c76ac76-2c1e-4531-8652-2bfb3cd02605'
                  WHEN '02af17a0-5b28-1040-8340-c5c1dba40387' THEN 'f885afec-d4f7-49df-94fb-2621f40fa571'
                  WHEN 'b5049528-e086-103f-967c-e1084cf42626' THEN '07c273c0-82c0-4a6a-8ccf-6ac7cff86630'
                  WHEN 'dea9fb32-4357-1040-82f0-c5c1dba40387' THEN '3d2fc355-0a8b-4438-b3a3-f6eb0ade5343'
                  WHEN 'ce15b18a-1b52-1040-9991-6700a4844527' THEN '94e06cc5-8950-42e3-9620-fded96d4d19d'
              END
              AND v4_row.ctid <> v1_row.ctid
          );
        UPDATE portal_favorite SET user_sub = CASE user_sub
            WHEN 'd0b09e34-2e6a-1040-99b4-6700a4844527' THEN '6c76ac76-2c1e-4531-8652-2bfb3cd02605'
            WHEN '02af17a0-5b28-1040-8340-c5c1dba40387' THEN 'f885afec-d4f7-49df-94fb-2621f40fa571'
            WHEN 'b5049528-e086-103f-967c-e1084cf42626' THEN '07c273c0-82c0-4a6a-8ccf-6ac7cff86630'
            WHEN 'dea9fb32-4357-1040-82f0-c5c1dba40387' THEN '3d2fc355-0a8b-4438-b3a3-f6eb0ade5343'
            WHEN 'ce15b18a-1b52-1040-9991-6700a4844527' THEN '94e06cc5-8950-42e3-9620-fded96d4d19d'
        END WHERE user_sub = ANY(v1_subs);
    END IF;

    -- portal_manager_specialist: DELETE конфликтов, UPDATE остальных
    IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'portal_manager_specialist') THEN
        DELETE FROM portal_manager_specialist v1_row
        WHERE v1_row.manager_sub = ANY(v1_subs)
          AND EXISTS (
              SELECT 1 FROM portal_manager_specialist v4_row
              WHERE v4_row.specialist_sub = v1_row.specialist_sub
                AND v4_row.manager_sub = CASE v1_row.manager_sub
                    WHEN 'd0b09e34-2e6a-1040-99b4-6700a4844527' THEN '6c76ac76-2c1e-4531-8652-2bfb3cd02605'
                    WHEN '02af17a0-5b28-1040-8340-c5c1dba40387' THEN 'f885afec-d4f7-49df-94fb-2621f40fa571'
                    WHEN 'b5049528-e086-103f-967c-e1084cf42626' THEN '07c273c0-82c0-4a6a-8ccf-6ac7cff86630'
                    WHEN 'dea9fb32-4357-1040-82f0-c5c1dba40387' THEN '3d2fc355-0a8b-4438-b3a3-f6eb0ade5343'
                    WHEN 'ce15b18a-1b52-1040-9991-6700a4844527' THEN '94e06cc5-8950-42e3-9620-fded96d4d19d'
                END
          );
        UPDATE portal_manager_specialist SET manager_sub = CASE manager_sub
            WHEN 'd0b09e34-2e6a-1040-99b4-6700a4844527' THEN '6c76ac76-2c1e-4531-8652-2bfb3cd02605'
            WHEN '02af17a0-5b28-1040-8340-c5c1dba40387' THEN 'f885afec-d4f7-49df-94fb-2621f40fa571'
            WHEN 'b5049528-e086-103f-967c-e1084cf42626' THEN '07c273c0-82c0-4a6a-8ccf-6ac7cff86630'
            WHEN 'dea9fb32-4357-1040-82f0-c5c1dba40387' THEN '3d2fc355-0a8b-4438-b3a3-f6eb0ade5343'
            WHEN 'ce15b18a-1b52-1040-9991-6700a4844527' THEN '94e06cc5-8950-42e3-9620-fded96d4d19d'
        END WHERE manager_sub = ANY(v1_subs);

        DELETE FROM portal_manager_specialist v1_row
        WHERE v1_row.specialist_sub = ANY(v1_subs)
          AND EXISTS (
              SELECT 1 FROM portal_manager_specialist v4_row
              WHERE v4_row.manager_sub = v1_row.manager_sub
                AND v4_row.specialist_sub = CASE v1_row.specialist_sub
                    WHEN 'd0b09e34-2e6a-1040-99b4-6700a4844527' THEN '6c76ac76-2c1e-4531-8652-2bfb3cd02605'
                    WHEN '02af17a0-5b28-1040-8340-c5c1dba40387' THEN 'f885afec-d4f7-49df-94fb-2621f40fa571'
                    WHEN 'b5049528-e086-103f-967c-e1084cf42626' THEN '07c273c0-82c0-4a6a-8ccf-6ac7cff86630'
                    WHEN 'dea9fb32-4357-1040-82f0-c5c1dba40387' THEN '3d2fc355-0a8b-4438-b3a3-f6eb0ade5343'
                    WHEN 'ce15b18a-1b52-1040-9991-6700a4844527' THEN '94e06cc5-8950-42e3-9620-fded96d4d19d'
                END
          );
        UPDATE portal_manager_specialist SET specialist_sub = CASE specialist_sub
            WHEN 'd0b09e34-2e6a-1040-99b4-6700a4844527' THEN '6c76ac76-2c1e-4531-8652-2bfb3cd02605'
            WHEN '02af17a0-5b28-1040-8340-c5c1dba40387' THEN 'f885afec-d4f7-49df-94fb-2621f40fa571'
            WHEN 'b5049528-e086-103f-967c-e1084cf42626' THEN '07c273c0-82c0-4a6a-8ccf-6ac7cff86630'
            WHEN 'dea9fb32-4357-1040-82f0-c5c1dba40387' THEN '3d2fc355-0a8b-4438-b3a3-f6eb0ade5343'
            WHEN 'ce15b18a-1b52-1040-9991-6700a4844527' THEN '94e06cc5-8950-42e3-9620-fded96d4d19d'
        END WHERE specialist_sub = ANY(v1_subs);
    END IF;
END $$;

-- portal_counterparty / portal_contract / portal_invoice / portal_payment / portal_procurement_request
DO $$
DECLARE
    v1_subs TEXT[] := ARRAY[
        'd0b09e34-2e6a-1040-99b4-6700a4844527',
        '02af17a0-5b28-1040-8340-c5c1dba40387',
        'b5049528-e086-103f-967c-e1084cf42626',
        'dea9fb32-4357-1040-82f0-c5c1dba40387',
        'ce15b18a-1b52-1040-9991-6700a4844527'
    ];
BEGIN
    UPDATE portal_counterparty
    SET author_sub = CASE author_sub
        WHEN 'd0b09e34-2e6a-1040-99b4-6700a4844527' THEN '6c76ac76-2c1e-4531-8652-2bfb3cd02605'
        WHEN '02af17a0-5b28-1040-8340-c5c1dba40387' THEN 'f885afec-d4f7-49df-94fb-2621f40fa571'
        WHEN 'b5049528-e086-103f-967c-e1084cf42626' THEN '07c273c0-82c0-4a6a-8ccf-6ac7cff86630'
        WHEN 'dea9fb32-4357-1040-82f0-c5c1dba40387' THEN '3d2fc355-0a8b-4438-b3a3-f6eb0ade5343'
        WHEN 'ce15b18a-1b52-1040-9991-6700a4844527' THEN '94e06cc5-8950-42e3-9620-fded96d4d19d'
    END WHERE author_sub = ANY(v1_subs);

    UPDATE portal_contract SET author_sub = CASE author_sub
        WHEN 'd0b09e34-2e6a-1040-99b4-6700a4844527' THEN '6c76ac76-2c1e-4531-8652-2bfb3cd02605'
        WHEN '02af17a0-5b28-1040-8340-c5c1dba40387' THEN 'f885afec-d4f7-49df-94fb-2621f40fa571'
        WHEN 'b5049528-e086-103f-967c-e1084cf42626' THEN '07c273c0-82c0-4a6a-8ccf-6ac7cff86630'
        WHEN 'dea9fb32-4357-1040-82f0-c5c1dba40387' THEN '3d2fc355-0a8b-4438-b3a3-f6eb0ade5343'
        WHEN 'ce15b18a-1b52-1040-9991-6700a4844527' THEN '94e06cc5-8950-42e3-9620-fded96d4d19d'
    END WHERE author_sub = ANY(v1_subs);

    UPDATE portal_contract SET owner_sub = CASE owner_sub
        WHEN 'd0b09e34-2e6a-1040-99b4-6700a4844527' THEN '6c76ac76-2c1e-4531-8652-2bfb3cd02605'
        WHEN '02af17a0-5b28-1040-8340-c5c1dba40387' THEN 'f885afec-d4f7-49df-94fb-2621f40fa571'
        WHEN 'b5049528-e086-103f-967c-e1084cf42626' THEN '07c273c0-82c0-4a6a-8ccf-6ac7cff86630'
        WHEN 'dea9fb32-4357-1040-82f0-c5c1dba40387' THEN '3d2fc355-0a8b-4438-b3a3-f6eb0ade5343'
        WHEN 'ce15b18a-1b52-1040-9991-6700a4844527' THEN '94e06cc5-8950-42e3-9620-fded96d4d19d'
    END WHERE owner_sub = ANY(v1_subs);

    UPDATE portal_invoice SET author_sub = CASE author_sub
        WHEN 'd0b09e34-2e6a-1040-99b4-6700a4844527' THEN '6c76ac76-2c1e-4531-8652-2bfb3cd02605'
        WHEN '02af17a0-5b28-1040-8340-c5c1dba40387' THEN 'f885afec-d4f7-49df-94fb-2621f40fa571'
        WHEN 'b5049528-e086-103f-967c-e1084cf42626' THEN '07c273c0-82c0-4a6a-8ccf-6ac7cff86630'
        WHEN 'dea9fb32-4357-1040-82f0-c5c1dba40387' THEN '3d2fc355-0a8b-4438-b3a3-f6eb0ade5343'
        WHEN 'ce15b18a-1b52-1040-9991-6700a4844527' THEN '94e06cc5-8950-42e3-9620-fded96d4d19d'
    END WHERE author_sub = ANY(v1_subs);

    UPDATE portal_payment SET author_sub = CASE author_sub
        WHEN 'd0b09e34-2e6a-1040-99b4-6700a4844527' THEN '6c76ac76-2c1e-4531-8652-2bfb3cd02605'
        WHEN '02af17a0-5b28-1040-8340-c5c1dba40387' THEN 'f885afec-d4f7-49df-94fb-2621f40fa571'
        WHEN 'b5049528-e086-103f-967c-e1084cf42626' THEN '07c273c0-82c0-4a6a-8ccf-6ac7cff86630'
        WHEN 'dea9fb32-4357-1040-82f0-c5c1dba40387' THEN '3d2fc355-0a8b-4438-b3a3-f6eb0ade5343'
        WHEN 'ce15b18a-1b52-1040-9991-6700a4844527' THEN '94e06cc5-8950-42e3-9620-fded96d4d19d'
    END WHERE author_sub = ANY(v1_subs);

    UPDATE portal_procurement_request SET author_sub = CASE author_sub
        WHEN 'd0b09e34-2e6a-1040-99b4-6700a4844527' THEN '6c76ac76-2c1e-4531-8652-2bfb3cd02605'
        WHEN '02af17a0-5b28-1040-8340-c5c1dba40387' THEN 'f885afec-d4f7-49df-94fb-2621f40fa571'
        WHEN 'b5049528-e086-103f-967c-e1084cf42626' THEN '07c273c0-82c0-4a6a-8ccf-6ac7cff86630'
        WHEN 'dea9fb32-4357-1040-82f0-c5c1dba40387' THEN '3d2fc355-0a8b-4438-b3a3-f6eb0ade5343'
        WHEN 'ce15b18a-1b52-1040-9991-6700a4844527' THEN '94e06cc5-8950-42e3-9620-fded96d4d19d'
    END WHERE author_sub = ANY(v1_subs);
END $$;

-- ---------------------------------------------------------------------------
-- Таблицы с PK = sub — требуют DELETE, данных там нет (см. диагностику выше)
-- ---------------------------------------------------------------------------

-- portal_telegram_binding: user_sub — PK; удаляем если вдруг есть
DELETE FROM portal_telegram_binding
WHERE user_sub IN (
    'd0b09e34-2e6a-1040-99b4-6700a4844527',
    '02af17a0-5b28-1040-8340-c5c1dba40387',
    'b5049528-e086-103f-967c-e1084cf42626',
    'dea9fb32-4357-1040-82f0-c5c1dba40387',
    'ce15b18a-1b52-1040-9991-6700a4844527'
);

-- portal_chat_member: user_sub — PK (composite); чат-членств у v1 нет (подтверждено)
DELETE FROM portal_chat_member
WHERE user_sub IN (
    'd0b09e34-2e6a-1040-99b4-6700a4844527',
    '02af17a0-5b28-1040-8340-c5c1dba40387',
    'b5049528-e086-103f-967c-e1084cf42626',
    'dea9fb32-4357-1040-82f0-c5c1dba40387',
    'ce15b18a-1b52-1040-9991-6700a4844527'
);

-- ---------------------------------------------------------------------------
-- Удаление specialist_profile для v1 sub — пересоздадутся из SSO при логине
-- ---------------------------------------------------------------------------
DELETE FROM portal_specialist_profile
WHERE specialist_sub IN (
    'd0b09e34-2e6a-1040-99b4-6700a4844527',
    '02af17a0-5b28-1040-8340-c5c1dba40387',
    'b5049528-e086-103f-967c-e1084cf42626',
    'dea9fb32-4357-1040-82f0-c5c1dba40387',
    'ce15b18a-1b52-1040-9991-6700a4844527'
);

-- ---------------------------------------------------------------------------
-- Финальное удаление дублирующих user_profile (v1)
-- ---------------------------------------------------------------------------
DELETE FROM portal_user_profile
WHERE sub IN (
    'd0b09e34-2e6a-1040-99b4-6700a4844527',
    '02af17a0-5b28-1040-8340-c5c1dba40387',
    'b5049528-e086-103f-967c-e1084cf42626',
    'dea9fb32-4357-1040-82f0-c5c1dba40387',
    'ce15b18a-1b52-1040-9991-6700a4844527'
);

-- ---------------------------------------------------------------------------
-- Проверка: дублей больше не должно быть
-- ---------------------------------------------------------------------------
SELECT email, COUNT(DISTINCT sub) AS subs
FROM portal_user_profile
WHERE email IS NOT NULL AND email != ''
GROUP BY email
HAVING COUNT(DISTINCT sub) > 1;

COMMIT;
