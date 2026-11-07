-- =============================================================================
-- Миграция: удаление дублей portal_user_profile после смены SSO (убран Keycloak)
-- Среда: prod
-- Дата: 2026-06-24
--
-- Итого 8 пользователей с двумя профилями каждый.
--
-- Маппинг (новый v1 → старый v4, который оставляем):
--   d0b09e34-2e6a-1040-99b4-6700a4844527  →  6c76ac76-2c1e-4531-8652-2bfb3cd02605
--   02af17a0-5b28-1040-8340-c5c1dba40387  →  f885afec-d4f7-49df-94fb-2621f40fa571
--   b5049528-e086-103f-967c-e1084cf42626  →  07c273c0-82c0-4a6a-8ccf-6ac7cff86630
--   ce15b18a-1b52-1040-9991-6700a4844527  →  94e06cc5-8950-42e3-9620-fded96d4d19d
--   71d1fa2a-e086-103f-967a-e1084cf42626  →  4bbceea1-c02c-460f-a647-a40b26e868ee
--   97b830e2-e086-103f-967b-e1084cf42626  →  da2b0e36-1126-48c3-b4f2-0d4518d54bef
--   bf5d02d6-e175-103f-968e-e1084cf42626  →  97a7e80d-0a13-455c-98bd-69c128e6f5f9
--   cb7076f6-e13a-103f-9680-e1084cf42626  →  05dcd709-ff4e-4eab-9c47-de40be559052
-- =============================================================================

BEGIN;

-- portal_notification: recipient_sub
UPDATE portal_notification
SET recipient_sub = CASE recipient_sub
    WHEN 'd0b09e34-2e6a-1040-99b4-6700a4844527' THEN '6c76ac76-2c1e-4531-8652-2bfb3cd02605'
    WHEN '02af17a0-5b28-1040-8340-c5c1dba40387' THEN 'f885afec-d4f7-49df-94fb-2621f40fa571'
    WHEN 'b5049528-e086-103f-967c-e1084cf42626' THEN '07c273c0-82c0-4a6a-8ccf-6ac7cff86630'
    WHEN 'ce15b18a-1b52-1040-9991-6700a4844527' THEN '94e06cc5-8950-42e3-9620-fded96d4d19d'
    WHEN '71d1fa2a-e086-103f-967a-e1084cf42626' THEN '4bbceea1-c02c-460f-a647-a40b26e868ee'
    WHEN '97b830e2-e086-103f-967b-e1084cf42626' THEN 'da2b0e36-1126-48c3-b4f2-0d4518d54bef'
    WHEN 'bf5d02d6-e175-103f-968e-e1084cf42626' THEN '97a7e80d-0a13-455c-98bd-69c128e6f5f9'
    WHEN 'cb7076f6-e13a-103f-9680-e1084cf42626' THEN '05dcd709-ff4e-4eab-9c47-de40be559052'
END
WHERE recipient_sub IN (
    'd0b09e34-2e6a-1040-99b4-6700a4844527',
    '02af17a0-5b28-1040-8340-c5c1dba40387',
    'b5049528-e086-103f-967c-e1084cf42626',
    'ce15b18a-1b52-1040-9991-6700a4844527',
    '71d1fa2a-e086-103f-967a-e1084cf42626',
    '97b830e2-e086-103f-967b-e1084cf42626',
    'bf5d02d6-e175-103f-968e-e1084cf42626',
    'cb7076f6-e13a-103f-9680-e1084cf42626'
);

-- portal_notification: author_sub
UPDATE portal_notification
SET author_sub = CASE author_sub
    WHEN 'd0b09e34-2e6a-1040-99b4-6700a4844527' THEN '6c76ac76-2c1e-4531-8652-2bfb3cd02605'
    WHEN '02af17a0-5b28-1040-8340-c5c1dba40387' THEN 'f885afec-d4f7-49df-94fb-2621f40fa571'
    WHEN 'b5049528-e086-103f-967c-e1084cf42626' THEN '07c273c0-82c0-4a6a-8ccf-6ac7cff86630'
    WHEN 'ce15b18a-1b52-1040-9991-6700a4844527' THEN '94e06cc5-8950-42e3-9620-fded96d4d19d'
    WHEN '71d1fa2a-e086-103f-967a-e1084cf42626' THEN '4bbceea1-c02c-460f-a647-a40b26e868ee'
    WHEN '97b830e2-e086-103f-967b-e1084cf42626' THEN 'da2b0e36-1126-48c3-b4f2-0d4518d54bef'
    WHEN 'bf5d02d6-e175-103f-968e-e1084cf42626' THEN '97a7e80d-0a13-455c-98bd-69c128e6f5f9'
    WHEN 'cb7076f6-e13a-103f-9680-e1084cf42626' THEN '05dcd709-ff4e-4eab-9c47-de40be559052'
END
WHERE author_sub IN (
    'd0b09e34-2e6a-1040-99b4-6700a4844527',
    '02af17a0-5b28-1040-8340-c5c1dba40387',
    'b5049528-e086-103f-967c-e1084cf42626',
    'ce15b18a-1b52-1040-9991-6700a4844527',
    '71d1fa2a-e086-103f-967a-e1084cf42626',
    '97b830e2-e086-103f-967b-e1084cf42626',
    'bf5d02d6-e175-103f-968e-e1084cf42626',
    'cb7076f6-e13a-103f-9680-e1084cf42626'
);

-- portal_task: creator_sub
UPDATE portal_task
SET creator_sub = CASE creator_sub
    WHEN 'd0b09e34-2e6a-1040-99b4-6700a4844527' THEN '6c76ac76-2c1e-4531-8652-2bfb3cd02605'
    WHEN '02af17a0-5b28-1040-8340-c5c1dba40387' THEN 'f885afec-d4f7-49df-94fb-2621f40fa571'
    WHEN 'b5049528-e086-103f-967c-e1084cf42626' THEN '07c273c0-82c0-4a6a-8ccf-6ac7cff86630'
    WHEN 'ce15b18a-1b52-1040-9991-6700a4844527' THEN '94e06cc5-8950-42e3-9620-fded96d4d19d'
    WHEN '71d1fa2a-e086-103f-967a-e1084cf42626' THEN '4bbceea1-c02c-460f-a647-a40b26e868ee'
    WHEN '97b830e2-e086-103f-967b-e1084cf42626' THEN 'da2b0e36-1126-48c3-b4f2-0d4518d54bef'
    WHEN 'bf5d02d6-e175-103f-968e-e1084cf42626' THEN '97a7e80d-0a13-455c-98bd-69c128e6f5f9'
    WHEN 'cb7076f6-e13a-103f-9680-e1084cf42626' THEN '05dcd709-ff4e-4eab-9c47-de40be559052'
END
WHERE creator_sub IN (
    'd0b09e34-2e6a-1040-99b4-6700a4844527',
    '02af17a0-5b28-1040-8340-c5c1dba40387',
    'b5049528-e086-103f-967c-e1084cf42626',
    'ce15b18a-1b52-1040-9991-6700a4844527',
    '71d1fa2a-e086-103f-967a-e1084cf42626',
    '97b830e2-e086-103f-967b-e1084cf42626',
    'bf5d02d6-e175-103f-968e-e1084cf42626',
    'cb7076f6-e13a-103f-9680-e1084cf42626'
);

-- portal_task: assignee_sub
UPDATE portal_task
SET assignee_sub = CASE assignee_sub
    WHEN 'd0b09e34-2e6a-1040-99b4-6700a4844527' THEN '6c76ac76-2c1e-4531-8652-2bfb3cd02605'
    WHEN '02af17a0-5b28-1040-8340-c5c1dba40387' THEN 'f885afec-d4f7-49df-94fb-2621f40fa571'
    WHEN 'b5049528-e086-103f-967c-e1084cf42626' THEN '07c273c0-82c0-4a6a-8ccf-6ac7cff86630'
    WHEN 'ce15b18a-1b52-1040-9991-6700a4844527' THEN '94e06cc5-8950-42e3-9620-fded96d4d19d'
    WHEN '71d1fa2a-e086-103f-967a-e1084cf42626' THEN '4bbceea1-c02c-460f-a647-a40b26e868ee'
    WHEN '97b830e2-e086-103f-967b-e1084cf42626' THEN 'da2b0e36-1126-48c3-b4f2-0d4518d54bef'
    WHEN 'bf5d02d6-e175-103f-968e-e1084cf42626' THEN '97a7e80d-0a13-455c-98bd-69c128e6f5f9'
    WHEN 'cb7076f6-e13a-103f-9680-e1084cf42626' THEN '05dcd709-ff4e-4eab-9c47-de40be559052'
END
WHERE assignee_sub IN (
    'd0b09e34-2e6a-1040-99b4-6700a4844527',
    '02af17a0-5b28-1040-8340-c5c1dba40387',
    'b5049528-e086-103f-967c-e1084cf42626',
    'ce15b18a-1b52-1040-9991-6700a4844527',
    '71d1fa2a-e086-103f-967a-e1084cf42626',
    '97b830e2-e086-103f-967b-e1084cf42626',
    'bf5d02d6-e175-103f-968e-e1084cf42626',
    'cb7076f6-e13a-103f-9680-e1084cf42626'
);

-- portal_task_assignee: UNIQUE(task_id, assignee_sub) — DELETE конфликтов, потом UPDATE
DELETE FROM portal_task_assignee v1_row
WHERE v1_row.assignee_sub IN (
    'd0b09e34-2e6a-1040-99b4-6700a4844527',
    '02af17a0-5b28-1040-8340-c5c1dba40387',
    'b5049528-e086-103f-967c-e1084cf42626',
    'ce15b18a-1b52-1040-9991-6700a4844527',
    '71d1fa2a-e086-103f-967a-e1084cf42626',
    '97b830e2-e086-103f-967b-e1084cf42626',
    'bf5d02d6-e175-103f-968e-e1084cf42626',
    'cb7076f6-e13a-103f-9680-e1084cf42626'
)
AND EXISTS (
    SELECT 1 FROM portal_task_assignee v4_row
    WHERE v4_row.task_id = v1_row.task_id
      AND v4_row.assignee_sub = CASE v1_row.assignee_sub
        WHEN 'd0b09e34-2e6a-1040-99b4-6700a4844527' THEN '6c76ac76-2c1e-4531-8652-2bfb3cd02605'
        WHEN '02af17a0-5b28-1040-8340-c5c1dba40387' THEN 'f885afec-d4f7-49df-94fb-2621f40fa571'
        WHEN 'b5049528-e086-103f-967c-e1084cf42626' THEN '07c273c0-82c0-4a6a-8ccf-6ac7cff86630'
        WHEN 'ce15b18a-1b52-1040-9991-6700a4844527' THEN '94e06cc5-8950-42e3-9620-fded96d4d19d'
        WHEN '71d1fa2a-e086-103f-967a-e1084cf42626' THEN '4bbceea1-c02c-460f-a647-a40b26e868ee'
        WHEN '97b830e2-e086-103f-967b-e1084cf42626' THEN 'da2b0e36-1126-48c3-b4f2-0d4518d54bef'
        WHEN 'bf5d02d6-e175-103f-968e-e1084cf42626' THEN '97a7e80d-0a13-455c-98bd-69c128e6f5f9'
        WHEN 'cb7076f6-e13a-103f-9680-e1084cf42626' THEN '05dcd709-ff4e-4eab-9c47-de40be559052'
      END
);
UPDATE portal_task_assignee
SET assignee_sub = CASE assignee_sub
    WHEN 'd0b09e34-2e6a-1040-99b4-6700a4844527' THEN '6c76ac76-2c1e-4531-8652-2bfb3cd02605'
    WHEN '02af17a0-5b28-1040-8340-c5c1dba40387' THEN 'f885afec-d4f7-49df-94fb-2621f40fa571'
    WHEN 'b5049528-e086-103f-967c-e1084cf42626' THEN '07c273c0-82c0-4a6a-8ccf-6ac7cff86630'
    WHEN 'ce15b18a-1b52-1040-9991-6700a4844527' THEN '94e06cc5-8950-42e3-9620-fded96d4d19d'
    WHEN '71d1fa2a-e086-103f-967a-e1084cf42626' THEN '4bbceea1-c02c-460f-a647-a40b26e868ee'
    WHEN '97b830e2-e086-103f-967b-e1084cf42626' THEN 'da2b0e36-1126-48c3-b4f2-0d4518d54bef'
    WHEN 'bf5d02d6-e175-103f-968e-e1084cf42626' THEN '97a7e80d-0a13-455c-98bd-69c128e6f5f9'
    WHEN 'cb7076f6-e13a-103f-9680-e1084cf42626' THEN '05dcd709-ff4e-4eab-9c47-de40be559052'
END
WHERE assignee_sub IN (
    'd0b09e34-2e6a-1040-99b4-6700a4844527',
    '02af17a0-5b28-1040-8340-c5c1dba40387',
    'b5049528-e086-103f-967c-e1084cf42626',
    'ce15b18a-1b52-1040-9991-6700a4844527',
    '71d1fa2a-e086-103f-967a-e1084cf42626',
    '97b830e2-e086-103f-967b-e1084cf42626',
    'bf5d02d6-e175-103f-968e-e1084cf42626',
    'cb7076f6-e13a-103f-9680-e1084cf42626'
);

-- portal_task_comment: author_sub
UPDATE portal_task_comment
SET author_sub = CASE author_sub
    WHEN 'd0b09e34-2e6a-1040-99b4-6700a4844527' THEN '6c76ac76-2c1e-4531-8652-2bfb3cd02605'
    WHEN '02af17a0-5b28-1040-8340-c5c1dba40387' THEN 'f885afec-d4f7-49df-94fb-2621f40fa571'
    WHEN 'b5049528-e086-103f-967c-e1084cf42626' THEN '07c273c0-82c0-4a6a-8ccf-6ac7cff86630'
    WHEN 'ce15b18a-1b52-1040-9991-6700a4844527' THEN '94e06cc5-8950-42e3-9620-fded96d4d19d'
    WHEN '71d1fa2a-e086-103f-967a-e1084cf42626' THEN '4bbceea1-c02c-460f-a647-a40b26e868ee'
    WHEN '97b830e2-e086-103f-967b-e1084cf42626' THEN 'da2b0e36-1126-48c3-b4f2-0d4518d54bef'
    WHEN 'bf5d02d6-e175-103f-968e-e1084cf42626' THEN '97a7e80d-0a13-455c-98bd-69c128e6f5f9'
    WHEN 'cb7076f6-e13a-103f-9680-e1084cf42626' THEN '05dcd709-ff4e-4eab-9c47-de40be559052'
END
WHERE author_sub IN (
    'd0b09e34-2e6a-1040-99b4-6700a4844527',
    '02af17a0-5b28-1040-8340-c5c1dba40387',
    'b5049528-e086-103f-967c-e1084cf42626',
    'ce15b18a-1b52-1040-9991-6700a4844527',
    '71d1fa2a-e086-103f-967a-e1084cf42626',
    '97b830e2-e086-103f-967b-e1084cf42626',
    'bf5d02d6-e175-103f-968e-e1084cf42626',
    'cb7076f6-e13a-103f-9680-e1084cf42626'
);

-- portal_task_link: created_by_sub
UPDATE portal_task_link
SET created_by_sub = CASE created_by_sub
    WHEN 'd0b09e34-2e6a-1040-99b4-6700a4844527' THEN '6c76ac76-2c1e-4531-8652-2bfb3cd02605'
    WHEN '02af17a0-5b28-1040-8340-c5c1dba40387' THEN 'f885afec-d4f7-49df-94fb-2621f40fa571'
    WHEN 'b5049528-e086-103f-967c-e1084cf42626' THEN '07c273c0-82c0-4a6a-8ccf-6ac7cff86630'
    WHEN 'ce15b18a-1b52-1040-9991-6700a4844527' THEN '94e06cc5-8950-42e3-9620-fded96d4d19d'
    WHEN '71d1fa2a-e086-103f-967a-e1084cf42626' THEN '4bbceea1-c02c-460f-a647-a40b26e868ee'
    WHEN '97b830e2-e086-103f-967b-e1084cf42626' THEN 'da2b0e36-1126-48c3-b4f2-0d4518d54bef'
    WHEN 'bf5d02d6-e175-103f-968e-e1084cf42626' THEN '97a7e80d-0a13-455c-98bd-69c128e6f5f9'
    WHEN 'cb7076f6-e13a-103f-9680-e1084cf42626' THEN '05dcd709-ff4e-4eab-9c47-de40be559052'
END
WHERE created_by_sub IN (
    'd0b09e34-2e6a-1040-99b4-6700a4844527',
    '02af17a0-5b28-1040-8340-c5c1dba40387',
    'b5049528-e086-103f-967c-e1084cf42626',
    'ce15b18a-1b52-1040-9991-6700a4844527',
    '71d1fa2a-e086-103f-967a-e1084cf42626',
    '97b830e2-e086-103f-967b-e1084cf42626',
    'bf5d02d6-e175-103f-968e-e1084cf42626',
    'cb7076f6-e13a-103f-9680-e1084cf42626'
);

-- portal_task_history: changed_by_sub
UPDATE portal_task_history
SET changed_by_sub = CASE changed_by_sub
    WHEN 'd0b09e34-2e6a-1040-99b4-6700a4844527' THEN '6c76ac76-2c1e-4531-8652-2bfb3cd02605'
    WHEN '02af17a0-5b28-1040-8340-c5c1dba40387' THEN 'f885afec-d4f7-49df-94fb-2621f40fa571'
    WHEN 'b5049528-e086-103f-967c-e1084cf42626' THEN '07c273c0-82c0-4a6a-8ccf-6ac7cff86630'
    WHEN 'ce15b18a-1b52-1040-9991-6700a4844527' THEN '94e06cc5-8950-42e3-9620-fded96d4d19d'
    WHEN '71d1fa2a-e086-103f-967a-e1084cf42626' THEN '4bbceea1-c02c-460f-a647-a40b26e868ee'
    WHEN '97b830e2-e086-103f-967b-e1084cf42626' THEN 'da2b0e36-1126-48c3-b4f2-0d4518d54bef'
    WHEN 'bf5d02d6-e175-103f-968e-e1084cf42626' THEN '97a7e80d-0a13-455c-98bd-69c128e6f5f9'
    WHEN 'cb7076f6-e13a-103f-9680-e1084cf42626' THEN '05dcd709-ff4e-4eab-9c47-de40be559052'
END
WHERE changed_by_sub IN (
    'd0b09e34-2e6a-1040-99b4-6700a4844527',
    '02af17a0-5b28-1040-8340-c5c1dba40387',
    'b5049528-e086-103f-967c-e1084cf42626',
    'ce15b18a-1b52-1040-9991-6700a4844527',
    '71d1fa2a-e086-103f-967a-e1084cf42626',
    '97b830e2-e086-103f-967b-e1084cf42626',
    'bf5d02d6-e175-103f-968e-e1084cf42626',
    'cb7076f6-e13a-103f-9680-e1084cf42626'
);

-- portal_document: author_sub, owner_sub
UPDATE portal_document
SET author_sub = CASE author_sub
    WHEN 'd0b09e34-2e6a-1040-99b4-6700a4844527' THEN '6c76ac76-2c1e-4531-8652-2bfb3cd02605'
    WHEN '02af17a0-5b28-1040-8340-c5c1dba40387' THEN 'f885afec-d4f7-49df-94fb-2621f40fa571'
    WHEN 'b5049528-e086-103f-967c-e1084cf42626' THEN '07c273c0-82c0-4a6a-8ccf-6ac7cff86630'
    WHEN 'ce15b18a-1b52-1040-9991-6700a4844527' THEN '94e06cc5-8950-42e3-9620-fded96d4d19d'
    WHEN '71d1fa2a-e086-103f-967a-e1084cf42626' THEN '4bbceea1-c02c-460f-a647-a40b26e868ee'
    WHEN '97b830e2-e086-103f-967b-e1084cf42626' THEN 'da2b0e36-1126-48c3-b4f2-0d4518d54bef'
    WHEN 'bf5d02d6-e175-103f-968e-e1084cf42626' THEN '97a7e80d-0a13-455c-98bd-69c128e6f5f9'
    WHEN 'cb7076f6-e13a-103f-9680-e1084cf42626' THEN '05dcd709-ff4e-4eab-9c47-de40be559052'
END
WHERE author_sub IN (
    'd0b09e34-2e6a-1040-99b4-6700a4844527',
    '02af17a0-5b28-1040-8340-c5c1dba40387',
    'b5049528-e086-103f-967c-e1084cf42626',
    'ce15b18a-1b52-1040-9991-6700a4844527',
    '71d1fa2a-e086-103f-967a-e1084cf42626',
    '97b830e2-e086-103f-967b-e1084cf42626',
    'bf5d02d6-e175-103f-968e-e1084cf42626',
    'cb7076f6-e13a-103f-9680-e1084cf42626'
);
UPDATE portal_document
SET owner_sub = CASE owner_sub
    WHEN 'd0b09e34-2e6a-1040-99b4-6700a4844527' THEN '6c76ac76-2c1e-4531-8652-2bfb3cd02605'
    WHEN '02af17a0-5b28-1040-8340-c5c1dba40387' THEN 'f885afec-d4f7-49df-94fb-2621f40fa571'
    WHEN 'b5049528-e086-103f-967c-e1084cf42626' THEN '07c273c0-82c0-4a6a-8ccf-6ac7cff86630'
    WHEN 'ce15b18a-1b52-1040-9991-6700a4844527' THEN '94e06cc5-8950-42e3-9620-fded96d4d19d'
    WHEN '71d1fa2a-e086-103f-967a-e1084cf42626' THEN '4bbceea1-c02c-460f-a647-a40b26e868ee'
    WHEN '97b830e2-e086-103f-967b-e1084cf42626' THEN 'da2b0e36-1126-48c3-b4f2-0d4518d54bef'
    WHEN 'bf5d02d6-e175-103f-968e-e1084cf42626' THEN '97a7e80d-0a13-455c-98bd-69c128e6f5f9'
    WHEN 'cb7076f6-e13a-103f-9680-e1084cf42626' THEN '05dcd709-ff4e-4eab-9c47-de40be559052'
END
WHERE owner_sub IN (
    'd0b09e34-2e6a-1040-99b4-6700a4844527',
    '02af17a0-5b28-1040-8340-c5c1dba40387',
    'b5049528-e086-103f-967c-e1084cf42626',
    'ce15b18a-1b52-1040-9991-6700a4844527',
    '71d1fa2a-e086-103f-967a-e1084cf42626',
    '97b830e2-e086-103f-967b-e1084cf42626',
    'bf5d02d6-e175-103f-968e-e1084cf42626',
    'cb7076f6-e13a-103f-9680-e1084cf42626'
);

-- portal_document_comment: author_sub
UPDATE portal_document_comment
SET author_sub = CASE author_sub
    WHEN 'd0b09e34-2e6a-1040-99b4-6700a4844527' THEN '6c76ac76-2c1e-4531-8652-2bfb3cd02605'
    WHEN '02af17a0-5b28-1040-8340-c5c1dba40387' THEN 'f885afec-d4f7-49df-94fb-2621f40fa571'
    WHEN 'b5049528-e086-103f-967c-e1084cf42626' THEN '07c273c0-82c0-4a6a-8ccf-6ac7cff86630'
    WHEN 'ce15b18a-1b52-1040-9991-6700a4844527' THEN '94e06cc5-8950-42e3-9620-fded96d4d19d'
    WHEN '71d1fa2a-e086-103f-967a-e1084cf42626' THEN '4bbceea1-c02c-460f-a647-a40b26e868ee'
    WHEN '97b830e2-e086-103f-967b-e1084cf42626' THEN 'da2b0e36-1126-48c3-b4f2-0d4518d54bef'
    WHEN 'bf5d02d6-e175-103f-968e-e1084cf42626' THEN '97a7e80d-0a13-455c-98bd-69c128e6f5f9'
    WHEN 'cb7076f6-e13a-103f-9680-e1084cf42626' THEN '05dcd709-ff4e-4eab-9c47-de40be559052'
END
WHERE author_sub IN (
    'd0b09e34-2e6a-1040-99b4-6700a4844527',
    '02af17a0-5b28-1040-8340-c5c1dba40387',
    'b5049528-e086-103f-967c-e1084cf42626',
    'ce15b18a-1b52-1040-9991-6700a4844527',
    '71d1fa2a-e086-103f-967a-e1084cf42626',
    '97b830e2-e086-103f-967b-e1084cf42626',
    'bf5d02d6-e175-103f-968e-e1084cf42626',
    'cb7076f6-e13a-103f-9680-e1084cf42626'
);

-- portal_nav_node_comment: author_sub
UPDATE portal_nav_node_comment
SET author_sub = CASE author_sub
    WHEN 'd0b09e34-2e6a-1040-99b4-6700a4844527' THEN '6c76ac76-2c1e-4531-8652-2bfb3cd02605'
    WHEN '02af17a0-5b28-1040-8340-c5c1dba40387' THEN 'f885afec-d4f7-49df-94fb-2621f40fa571'
    WHEN 'b5049528-e086-103f-967c-e1084cf42626' THEN '07c273c0-82c0-4a6a-8ccf-6ac7cff86630'
    WHEN 'ce15b18a-1b52-1040-9991-6700a4844527' THEN '94e06cc5-8950-42e3-9620-fded96d4d19d'
    WHEN '71d1fa2a-e086-103f-967a-e1084cf42626' THEN '4bbceea1-c02c-460f-a647-a40b26e868ee'
    WHEN '97b830e2-e086-103f-967b-e1084cf42626' THEN 'da2b0e36-1126-48c3-b4f2-0d4518d54bef'
    WHEN 'bf5d02d6-e175-103f-968e-e1084cf42626' THEN '97a7e80d-0a13-455c-98bd-69c128e6f5f9'
    WHEN 'cb7076f6-e13a-103f-9680-e1084cf42626' THEN '05dcd709-ff4e-4eab-9c47-de40be559052'
END
WHERE author_sub IN (
    'd0b09e34-2e6a-1040-99b4-6700a4844527',
    '02af17a0-5b28-1040-8340-c5c1dba40387',
    'b5049528-e086-103f-967c-e1084cf42626',
    'ce15b18a-1b52-1040-9991-6700a4844527',
    '71d1fa2a-e086-103f-967a-e1084cf42626',
    '97b830e2-e086-103f-967b-e1084cf42626',
    'bf5d02d6-e175-103f-968e-e1084cf42626',
    'cb7076f6-e13a-103f-9680-e1084cf42626'
);

-- portal_agreement: created_by_sub
UPDATE portal_agreement
SET created_by_sub = CASE created_by_sub
    WHEN 'd0b09e34-2e6a-1040-99b4-6700a4844527' THEN '6c76ac76-2c1e-4531-8652-2bfb3cd02605'
    WHEN '02af17a0-5b28-1040-8340-c5c1dba40387' THEN 'f885afec-d4f7-49df-94fb-2621f40fa571'
    WHEN 'b5049528-e086-103f-967c-e1084cf42626' THEN '07c273c0-82c0-4a6a-8ccf-6ac7cff86630'
    WHEN 'ce15b18a-1b52-1040-9991-6700a4844527' THEN '94e06cc5-8950-42e3-9620-fded96d4d19d'
    WHEN '71d1fa2a-e086-103f-967a-e1084cf42626' THEN '4bbceea1-c02c-460f-a647-a40b26e868ee'
    WHEN '97b830e2-e086-103f-967b-e1084cf42626' THEN 'da2b0e36-1126-48c3-b4f2-0d4518d54bef'
    WHEN 'bf5d02d6-e175-103f-968e-e1084cf42626' THEN '97a7e80d-0a13-455c-98bd-69c128e6f5f9'
    WHEN 'cb7076f6-e13a-103f-9680-e1084cf42626' THEN '05dcd709-ff4e-4eab-9c47-de40be559052'
END
WHERE created_by_sub IN (
    'd0b09e34-2e6a-1040-99b4-6700a4844527',
    '02af17a0-5b28-1040-8340-c5c1dba40387',
    'b5049528-e086-103f-967c-e1084cf42626',
    'ce15b18a-1b52-1040-9991-6700a4844527',
    '71d1fa2a-e086-103f-967a-e1084cf42626',
    '97b830e2-e086-103f-967b-e1084cf42626',
    'bf5d02d6-e175-103f-968e-e1084cf42626',
    'cb7076f6-e13a-103f-9680-e1084cf42626'
);

-- portal_chat: created_by_sub
UPDATE portal_chat
SET created_by_sub = CASE created_by_sub
    WHEN 'd0b09e34-2e6a-1040-99b4-6700a4844527' THEN '6c76ac76-2c1e-4531-8652-2bfb3cd02605'
    WHEN '02af17a0-5b28-1040-8340-c5c1dba40387' THEN 'f885afec-d4f7-49df-94fb-2621f40fa571'
    WHEN 'b5049528-e086-103f-967c-e1084cf42626' THEN '07c273c0-82c0-4a6a-8ccf-6ac7cff86630'
    WHEN 'ce15b18a-1b52-1040-9991-6700a4844527' THEN '94e06cc5-8950-42e3-9620-fded96d4d19d'
    WHEN '71d1fa2a-e086-103f-967a-e1084cf42626' THEN '4bbceea1-c02c-460f-a647-a40b26e868ee'
    WHEN '97b830e2-e086-103f-967b-e1084cf42626' THEN 'da2b0e36-1126-48c3-b4f2-0d4518d54bef'
    WHEN 'bf5d02d6-e175-103f-968e-e1084cf42626' THEN '97a7e80d-0a13-455c-98bd-69c128e6f5f9'
    WHEN 'cb7076f6-e13a-103f-9680-e1084cf42626' THEN '05dcd709-ff4e-4eab-9c47-de40be559052'
END
WHERE created_by_sub IN (
    'd0b09e34-2e6a-1040-99b4-6700a4844527',
    '02af17a0-5b28-1040-8340-c5c1dba40387',
    'b5049528-e086-103f-967c-e1084cf42626',
    'ce15b18a-1b52-1040-9991-6700a4844527',
    '71d1fa2a-e086-103f-967a-e1084cf42626',
    '97b830e2-e086-103f-967b-e1084cf42626',
    'bf5d02d6-e175-103f-968e-e1084cf42626',
    'cb7076f6-e13a-103f-9680-e1084cf42626'
);

-- portal_chat_message: author_sub
UPDATE portal_chat_message
SET author_sub = CASE author_sub
    WHEN 'd0b09e34-2e6a-1040-99b4-6700a4844527' THEN '6c76ac76-2c1e-4531-8652-2bfb3cd02605'
    WHEN '02af17a0-5b28-1040-8340-c5c1dba40387' THEN 'f885afec-d4f7-49df-94fb-2621f40fa571'
    WHEN 'b5049528-e086-103f-967c-e1084cf42626' THEN '07c273c0-82c0-4a6a-8ccf-6ac7cff86630'
    WHEN 'ce15b18a-1b52-1040-9991-6700a4844527' THEN '94e06cc5-8950-42e3-9620-fded96d4d19d'
    WHEN '71d1fa2a-e086-103f-967a-e1084cf42626' THEN '4bbceea1-c02c-460f-a647-a40b26e868ee'
    WHEN '97b830e2-e086-103f-967b-e1084cf42626' THEN 'da2b0e36-1126-48c3-b4f2-0d4518d54bef'
    WHEN 'bf5d02d6-e175-103f-968e-e1084cf42626' THEN '97a7e80d-0a13-455c-98bd-69c128e6f5f9'
    WHEN 'cb7076f6-e13a-103f-9680-e1084cf42626' THEN '05dcd709-ff4e-4eab-9c47-de40be559052'
END
WHERE author_sub IN (
    'd0b09e34-2e6a-1040-99b4-6700a4844527',
    '02af17a0-5b28-1040-8340-c5c1dba40387',
    'b5049528-e086-103f-967c-e1084cf42626',
    'ce15b18a-1b52-1040-9991-6700a4844527',
    '71d1fa2a-e086-103f-967a-e1084cf42626',
    '97b830e2-e086-103f-967b-e1084cf42626',
    'bf5d02d6-e175-103f-968e-e1084cf42626',
    'cb7076f6-e13a-103f-9680-e1084cf42626'
);

-- portal_chat_attachment: uploader_sub
UPDATE portal_chat_attachment
SET uploader_sub = CASE uploader_sub
    WHEN 'd0b09e34-2e6a-1040-99b4-6700a4844527' THEN '6c76ac76-2c1e-4531-8652-2bfb3cd02605'
    WHEN '02af17a0-5b28-1040-8340-c5c1dba40387' THEN 'f885afec-d4f7-49df-94fb-2621f40fa571'
    WHEN 'b5049528-e086-103f-967c-e1084cf42626' THEN '07c273c0-82c0-4a6a-8ccf-6ac7cff86630'
    WHEN 'ce15b18a-1b52-1040-9991-6700a4844527' THEN '94e06cc5-8950-42e3-9620-fded96d4d19d'
    WHEN '71d1fa2a-e086-103f-967a-e1084cf42626' THEN '4bbceea1-c02c-460f-a647-a40b26e868ee'
    WHEN '97b830e2-e086-103f-967b-e1084cf42626' THEN 'da2b0e36-1126-48c3-b4f2-0d4518d54bef'
    WHEN 'bf5d02d6-e175-103f-968e-e1084cf42626' THEN '97a7e80d-0a13-455c-98bd-69c128e6f5f9'
    WHEN 'cb7076f6-e13a-103f-9680-e1084cf42626' THEN '05dcd709-ff4e-4eab-9c47-de40be559052'
END
WHERE uploader_sub IN (
    'd0b09e34-2e6a-1040-99b4-6700a4844527',
    '02af17a0-5b28-1040-8340-c5c1dba40387',
    'b5049528-e086-103f-967c-e1084cf42626',
    'ce15b18a-1b52-1040-9991-6700a4844527',
    '71d1fa2a-e086-103f-967a-e1084cf42626',
    '97b830e2-e086-103f-967b-e1084cf42626',
    'bf5d02d6-e175-103f-968e-e1084cf42626',
    'cb7076f6-e13a-103f-9680-e1084cf42626'
);

-- portal_specialist_note: author_sub
UPDATE portal_specialist_note
SET author_sub = CASE author_sub
    WHEN 'd0b09e34-2e6a-1040-99b4-6700a4844527' THEN '6c76ac76-2c1e-4531-8652-2bfb3cd02605'
    WHEN '02af17a0-5b28-1040-8340-c5c1dba40387' THEN 'f885afec-d4f7-49df-94fb-2621f40fa571'
    WHEN 'b5049528-e086-103f-967c-e1084cf42626' THEN '07c273c0-82c0-4a6a-8ccf-6ac7cff86630'
    WHEN 'ce15b18a-1b52-1040-9991-6700a4844527' THEN '94e06cc5-8950-42e3-9620-fded96d4d19d'
    WHEN '71d1fa2a-e086-103f-967a-e1084cf42626' THEN '4bbceea1-c02c-460f-a647-a40b26e868ee'
    WHEN '97b830e2-e086-103f-967b-e1084cf42626' THEN 'da2b0e36-1126-48c3-b4f2-0d4518d54bef'
    WHEN 'bf5d02d6-e175-103f-968e-e1084cf42626' THEN '97a7e80d-0a13-455c-98bd-69c128e6f5f9'
    WHEN 'cb7076f6-e13a-103f-9680-e1084cf42626' THEN '05dcd709-ff4e-4eab-9c47-de40be559052'
END
WHERE author_sub IN (
    'd0b09e34-2e6a-1040-99b4-6700a4844527',
    '02af17a0-5b28-1040-8340-c5c1dba40387',
    'b5049528-e086-103f-967c-e1084cf42626',
    'ce15b18a-1b52-1040-9991-6700a4844527',
    '71d1fa2a-e086-103f-967a-e1084cf42626',
    '97b830e2-e086-103f-967b-e1084cf42626',
    'bf5d02d6-e175-103f-968e-e1084cf42626',
    'cb7076f6-e13a-103f-9680-e1084cf42626'
);

-- portal_rich_media: uploader_sub
UPDATE portal_rich_media
SET uploader_sub = CASE uploader_sub
    WHEN 'd0b09e34-2e6a-1040-99b4-6700a4844527' THEN '6c76ac76-2c1e-4531-8652-2bfb3cd02605'
    WHEN '02af17a0-5b28-1040-8340-c5c1dba40387' THEN 'f885afec-d4f7-49df-94fb-2621f40fa571'
    WHEN 'b5049528-e086-103f-967c-e1084cf42626' THEN '07c273c0-82c0-4a6a-8ccf-6ac7cff86630'
    WHEN 'ce15b18a-1b52-1040-9991-6700a4844527' THEN '94e06cc5-8950-42e3-9620-fded96d4d19d'
    WHEN '71d1fa2a-e086-103f-967a-e1084cf42626' THEN '4bbceea1-c02c-460f-a647-a40b26e868ee'
    WHEN '97b830e2-e086-103f-967b-e1084cf42626' THEN 'da2b0e36-1126-48c3-b4f2-0d4518d54bef'
    WHEN 'bf5d02d6-e175-103f-968e-e1084cf42626' THEN '97a7e80d-0a13-455c-98bd-69c128e6f5f9'
    WHEN 'cb7076f6-e13a-103f-9680-e1084cf42626' THEN '05dcd709-ff4e-4eab-9c47-de40be559052'
END
WHERE uploader_sub IN (
    'd0b09e34-2e6a-1040-99b4-6700a4844527',
    '02af17a0-5b28-1040-8340-c5c1dba40387',
    'b5049528-e086-103f-967c-e1084cf42626',
    'ce15b18a-1b52-1040-9991-6700a4844527',
    '71d1fa2a-e086-103f-967a-e1084cf42626',
    '97b830e2-e086-103f-967b-e1084cf42626',
    'bf5d02d6-e175-103f-968e-e1084cf42626',
    'cb7076f6-e13a-103f-9680-e1084cf42626'
);

-- portal_time_entry: user_sub
UPDATE portal_time_entry
SET user_sub = CASE user_sub
    WHEN 'd0b09e34-2e6a-1040-99b4-6700a4844527' THEN '6c76ac76-2c1e-4531-8652-2bfb3cd02605'
    WHEN '02af17a0-5b28-1040-8340-c5c1dba40387' THEN 'f885afec-d4f7-49df-94fb-2621f40fa571'
    WHEN 'b5049528-e086-103f-967c-e1084cf42626' THEN '07c273c0-82c0-4a6a-8ccf-6ac7cff86630'
    WHEN 'ce15b18a-1b52-1040-9991-6700a4844527' THEN '94e06cc5-8950-42e3-9620-fded96d4d19d'
    WHEN '71d1fa2a-e086-103f-967a-e1084cf42626' THEN '4bbceea1-c02c-460f-a647-a40b26e868ee'
    WHEN '97b830e2-e086-103f-967b-e1084cf42626' THEN 'da2b0e36-1126-48c3-b4f2-0d4518d54bef'
    WHEN 'bf5d02d6-e175-103f-968e-e1084cf42626' THEN '97a7e80d-0a13-455c-98bd-69c128e6f5f9'
    WHEN 'cb7076f6-e13a-103f-9680-e1084cf42626' THEN '05dcd709-ff4e-4eab-9c47-de40be559052'
END
WHERE user_sub IN (
    'd0b09e34-2e6a-1040-99b4-6700a4844527',
    '02af17a0-5b28-1040-8340-c5c1dba40387',
    'b5049528-e086-103f-967c-e1084cf42626',
    'ce15b18a-1b52-1040-9991-6700a4844527',
    '71d1fa2a-e086-103f-967a-e1084cf42626',
    '97b830e2-e086-103f-967b-e1084cf42626',
    'bf5d02d6-e175-103f-968e-e1084cf42626',
    'cb7076f6-e13a-103f-9680-e1084cf42626'
);

-- Таблицы которые могут отсутствовать + таблицы с UNIQUE(user_sub, ...)
DO $$
DECLARE
    v1_subs TEXT[] := ARRAY[
        'd0b09e34-2e6a-1040-99b4-6700a4844527',
        '02af17a0-5b28-1040-8340-c5c1dba40387',
        'b5049528-e086-103f-967c-e1084cf42626',
        'ce15b18a-1b52-1040-9991-6700a4844527',
        '71d1fa2a-e086-103f-967a-e1084cf42626',
        '97b830e2-e086-103f-967b-e1084cf42626',
        'bf5d02d6-e175-103f-968e-e1084cf42626',
        'cb7076f6-e13a-103f-9680-e1084cf42626'
    ];
BEGIN
    -- portal_learning (может отсутствовать)
    IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'portal_learning') THEN
        UPDATE portal_learning SET created_by_sub = CASE created_by_sub
            WHEN 'd0b09e34-2e6a-1040-99b4-6700a4844527' THEN '6c76ac76-2c1e-4531-8652-2bfb3cd02605'
            WHEN '02af17a0-5b28-1040-8340-c5c1dba40387' THEN 'f885afec-d4f7-49df-94fb-2621f40fa571'
            WHEN 'b5049528-e086-103f-967c-e1084cf42626' THEN '07c273c0-82c0-4a6a-8ccf-6ac7cff86630'
            WHEN 'ce15b18a-1b52-1040-9991-6700a4844527' THEN '94e06cc5-8950-42e3-9620-fded96d4d19d'
            WHEN '71d1fa2a-e086-103f-967a-e1084cf42626' THEN '4bbceea1-c02c-460f-a647-a40b26e868ee'
            WHEN '97b830e2-e086-103f-967b-e1084cf42626' THEN 'da2b0e36-1126-48c3-b4f2-0d4518d54bef'
            WHEN 'bf5d02d6-e175-103f-968e-e1084cf42626' THEN '97a7e80d-0a13-455c-98bd-69c128e6f5f9'
            WHEN 'cb7076f6-e13a-103f-9680-e1084cf42626' THEN '05dcd709-ff4e-4eab-9c47-de40be559052'
        END WHERE created_by_sub = ANY(v1_subs);
    END IF;

    -- portal_user_task_board_pref: UNIQUE(user_sub, scope_key) — удаляем v1 целиком
    IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'portal_user_task_board_pref') THEN
        DELETE FROM portal_user_task_board_pref WHERE user_sub = ANY(v1_subs);
    END IF;

    -- portal_user_specialist_board_pref: удаляем v1 целиком
    IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'portal_user_specialist_board_pref') THEN
        DELETE FROM portal_user_specialist_board_pref WHERE user_sub = ANY(v1_subs);
    END IF;

    -- portal_web_push: удаляем v1 целиком
    IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'portal_web_push') THEN
        DELETE FROM portal_web_push WHERE user_sub = ANY(v1_subs);
    END IF;

    -- portal_favorite: DELETE конфликтов, UPDATE остальных
    IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'portal_favorite') THEN
        DELETE FROM portal_favorite v1_row
        WHERE v1_row.user_sub = ANY(v1_subs)
          AND EXISTS (
              SELECT 1 FROM portal_favorite v4_row
              WHERE v4_row.user_sub = CASE v1_row.user_sub
                  WHEN 'd0b09e34-2e6a-1040-99b4-6700a4844527' THEN '6c76ac76-2c1e-4531-8652-2bfb3cd02605'
                  WHEN '02af17a0-5b28-1040-8340-c5c1dba40387' THEN 'f885afec-d4f7-49df-94fb-2621f40fa571'
                  WHEN 'b5049528-e086-103f-967c-e1084cf42626' THEN '07c273c0-82c0-4a6a-8ccf-6ac7cff86630'
                  WHEN 'ce15b18a-1b52-1040-9991-6700a4844527' THEN '94e06cc5-8950-42e3-9620-fded96d4d19d'
                  WHEN '71d1fa2a-e086-103f-967a-e1084cf42626' THEN '4bbceea1-c02c-460f-a647-a40b26e868ee'
                  WHEN '97b830e2-e086-103f-967b-e1084cf42626' THEN 'da2b0e36-1126-48c3-b4f2-0d4518d54bef'
                  WHEN 'bf5d02d6-e175-103f-968e-e1084cf42626' THEN '97a7e80d-0a13-455c-98bd-69c128e6f5f9'
                  WHEN 'cb7076f6-e13a-103f-9680-e1084cf42626' THEN '05dcd709-ff4e-4eab-9c47-de40be559052'
              END
              AND v4_row.ctid <> v1_row.ctid
          );
        UPDATE portal_favorite SET user_sub = CASE user_sub
            WHEN 'd0b09e34-2e6a-1040-99b4-6700a4844527' THEN '6c76ac76-2c1e-4531-8652-2bfb3cd02605'
            WHEN '02af17a0-5b28-1040-8340-c5c1dba40387' THEN 'f885afec-d4f7-49df-94fb-2621f40fa571'
            WHEN 'b5049528-e086-103f-967c-e1084cf42626' THEN '07c273c0-82c0-4a6a-8ccf-6ac7cff86630'
            WHEN 'ce15b18a-1b52-1040-9991-6700a4844527' THEN '94e06cc5-8950-42e3-9620-fded96d4d19d'
            WHEN '71d1fa2a-e086-103f-967a-e1084cf42626' THEN '4bbceea1-c02c-460f-a647-a40b26e868ee'
            WHEN '97b830e2-e086-103f-967b-e1084cf42626' THEN 'da2b0e36-1126-48c3-b4f2-0d4518d54bef'
            WHEN 'bf5d02d6-e175-103f-968e-e1084cf42626' THEN '97a7e80d-0a13-455c-98bd-69c128e6f5f9'
            WHEN 'cb7076f6-e13a-103f-9680-e1084cf42626' THEN '05dcd709-ff4e-4eab-9c47-de40be559052'
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
                    WHEN 'ce15b18a-1b52-1040-9991-6700a4844527' THEN '94e06cc5-8950-42e3-9620-fded96d4d19d'
                    WHEN '71d1fa2a-e086-103f-967a-e1084cf42626' THEN '4bbceea1-c02c-460f-a647-a40b26e868ee'
                    WHEN '97b830e2-e086-103f-967b-e1084cf42626' THEN 'da2b0e36-1126-48c3-b4f2-0d4518d54bef'
                    WHEN 'bf5d02d6-e175-103f-968e-e1084cf42626' THEN '97a7e80d-0a13-455c-98bd-69c128e6f5f9'
                    WHEN 'cb7076f6-e13a-103f-9680-e1084cf42626' THEN '05dcd709-ff4e-4eab-9c47-de40be559052'
                END
          );
        UPDATE portal_manager_specialist SET manager_sub = CASE manager_sub
            WHEN 'd0b09e34-2e6a-1040-99b4-6700a4844527' THEN '6c76ac76-2c1e-4531-8652-2bfb3cd02605'
            WHEN '02af17a0-5b28-1040-8340-c5c1dba40387' THEN 'f885afec-d4f7-49df-94fb-2621f40fa571'
            WHEN 'b5049528-e086-103f-967c-e1084cf42626' THEN '07c273c0-82c0-4a6a-8ccf-6ac7cff86630'
            WHEN 'ce15b18a-1b52-1040-9991-6700a4844527' THEN '94e06cc5-8950-42e3-9620-fded96d4d19d'
            WHEN '71d1fa2a-e086-103f-967a-e1084cf42626' THEN '4bbceea1-c02c-460f-a647-a40b26e868ee'
            WHEN '97b830e2-e086-103f-967b-e1084cf42626' THEN 'da2b0e36-1126-48c3-b4f2-0d4518d54bef'
            WHEN 'bf5d02d6-e175-103f-968e-e1084cf42626' THEN '97a7e80d-0a13-455c-98bd-69c128e6f5f9'
            WHEN 'cb7076f6-e13a-103f-9680-e1084cf42626' THEN '05dcd709-ff4e-4eab-9c47-de40be559052'
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
                    WHEN 'ce15b18a-1b52-1040-9991-6700a4844527' THEN '94e06cc5-8950-42e3-9620-fded96d4d19d'
                    WHEN '71d1fa2a-e086-103f-967a-e1084cf42626' THEN '4bbceea1-c02c-460f-a647-a40b26e868ee'
                    WHEN '97b830e2-e086-103f-967b-e1084cf42626' THEN 'da2b0e36-1126-48c3-b4f2-0d4518d54bef'
                    WHEN 'bf5d02d6-e175-103f-968e-e1084cf42626' THEN '97a7e80d-0a13-455c-98bd-69c128e6f5f9'
                    WHEN 'cb7076f6-e13a-103f-9680-e1084cf42626' THEN '05dcd709-ff4e-4eab-9c47-de40be559052'
                END
          );
        UPDATE portal_manager_specialist SET specialist_sub = CASE specialist_sub
            WHEN 'd0b09e34-2e6a-1040-99b4-6700a4844527' THEN '6c76ac76-2c1e-4531-8652-2bfb3cd02605'
            WHEN '02af17a0-5b28-1040-8340-c5c1dba40387' THEN 'f885afec-d4f7-49df-94fb-2621f40fa571'
            WHEN 'b5049528-e086-103f-967c-e1084cf42626' THEN '07c273c0-82c0-4a6a-8ccf-6ac7cff86630'
            WHEN 'ce15b18a-1b52-1040-9991-6700a4844527' THEN '94e06cc5-8950-42e3-9620-fded96d4d19d'
            WHEN '71d1fa2a-e086-103f-967a-e1084cf42626' THEN '4bbceea1-c02c-460f-a647-a40b26e868ee'
            WHEN '97b830e2-e086-103f-967b-e1084cf42626' THEN 'da2b0e36-1126-48c3-b4f2-0d4518d54bef'
            WHEN 'bf5d02d6-e175-103f-968e-e1084cf42626' THEN '97a7e80d-0a13-455c-98bd-69c128e6f5f9'
            WHEN 'cb7076f6-e13a-103f-9680-e1084cf42626' THEN '05dcd709-ff4e-4eab-9c47-de40be559052'
        END WHERE specialist_sub = ANY(v1_subs);
    END IF;
END $$;

-- Финансовые таблицы
DO $$
DECLARE
    v1_subs TEXT[] := ARRAY[
        'd0b09e34-2e6a-1040-99b4-6700a4844527',
        '02af17a0-5b28-1040-8340-c5c1dba40387',
        'b5049528-e086-103f-967c-e1084cf42626',
        'ce15b18a-1b52-1040-9991-6700a4844527',
        '71d1fa2a-e086-103f-967a-e1084cf42626',
        '97b830e2-e086-103f-967b-e1084cf42626',
        'bf5d02d6-e175-103f-968e-e1084cf42626',
        'cb7076f6-e13a-103f-9680-e1084cf42626'
    ];
BEGIN
    IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'portal_counterparty') THEN
        UPDATE portal_counterparty SET author_sub = CASE author_sub
            WHEN 'd0b09e34-2e6a-1040-99b4-6700a4844527' THEN '6c76ac76-2c1e-4531-8652-2bfb3cd02605'
            WHEN '02af17a0-5b28-1040-8340-c5c1dba40387' THEN 'f885afec-d4f7-49df-94fb-2621f40fa571'
            WHEN 'b5049528-e086-103f-967c-e1084cf42626' THEN '07c273c0-82c0-4a6a-8ccf-6ac7cff86630'
            WHEN 'ce15b18a-1b52-1040-9991-6700a4844527' THEN '94e06cc5-8950-42e3-9620-fded96d4d19d'
            WHEN '71d1fa2a-e086-103f-967a-e1084cf42626' THEN '4bbceea1-c02c-460f-a647-a40b26e868ee'
            WHEN '97b830e2-e086-103f-967b-e1084cf42626' THEN 'da2b0e36-1126-48c3-b4f2-0d4518d54bef'
            WHEN 'bf5d02d6-e175-103f-968e-e1084cf42626' THEN '97a7e80d-0a13-455c-98bd-69c128e6f5f9'
            WHEN 'cb7076f6-e13a-103f-9680-e1084cf42626' THEN '05dcd709-ff4e-4eab-9c47-de40be559052'
        END WHERE author_sub = ANY(v1_subs);
    END IF;
    IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'portal_contract') THEN
        UPDATE portal_contract SET author_sub = CASE author_sub
            WHEN 'd0b09e34-2e6a-1040-99b4-6700a4844527' THEN '6c76ac76-2c1e-4531-8652-2bfb3cd02605'
            WHEN '02af17a0-5b28-1040-8340-c5c1dba40387' THEN 'f885afec-d4f7-49df-94fb-2621f40fa571'
            WHEN 'b5049528-e086-103f-967c-e1084cf42626' THEN '07c273c0-82c0-4a6a-8ccf-6ac7cff86630'
            WHEN 'ce15b18a-1b52-1040-9991-6700a4844527' THEN '94e06cc5-8950-42e3-9620-fded96d4d19d'
            WHEN '71d1fa2a-e086-103f-967a-e1084cf42626' THEN '4bbceea1-c02c-460f-a647-a40b26e868ee'
            WHEN '97b830e2-e086-103f-967b-e1084cf42626' THEN 'da2b0e36-1126-48c3-b4f2-0d4518d54bef'
            WHEN 'bf5d02d6-e175-103f-968e-e1084cf42626' THEN '97a7e80d-0a13-455c-98bd-69c128e6f5f9'
            WHEN 'cb7076f6-e13a-103f-9680-e1084cf42626' THEN '05dcd709-ff4e-4eab-9c47-de40be559052'
        END WHERE author_sub = ANY(v1_subs);
        UPDATE portal_contract SET owner_sub = CASE owner_sub
            WHEN 'd0b09e34-2e6a-1040-99b4-6700a4844527' THEN '6c76ac76-2c1e-4531-8652-2bfb3cd02605'
            WHEN '02af17a0-5b28-1040-8340-c5c1dba40387' THEN 'f885afec-d4f7-49df-94fb-2621f40fa571'
            WHEN 'b5049528-e086-103f-967c-e1084cf42626' THEN '07c273c0-82c0-4a6a-8ccf-6ac7cff86630'
            WHEN 'ce15b18a-1b52-1040-9991-6700a4844527' THEN '94e06cc5-8950-42e3-9620-fded96d4d19d'
            WHEN '71d1fa2a-e086-103f-967a-e1084cf42626' THEN '4bbceea1-c02c-460f-a647-a40b26e868ee'
            WHEN '97b830e2-e086-103f-967b-e1084cf42626' THEN 'da2b0e36-1126-48c3-b4f2-0d4518d54bef'
            WHEN 'bf5d02d6-e175-103f-968e-e1084cf42626' THEN '97a7e80d-0a13-455c-98bd-69c128e6f5f9'
            WHEN 'cb7076f6-e13a-103f-9680-e1084cf42626' THEN '05dcd709-ff4e-4eab-9c47-de40be559052'
        END WHERE owner_sub = ANY(v1_subs);
    END IF;
    IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'portal_invoice') THEN
        UPDATE portal_invoice SET author_sub = CASE author_sub
            WHEN 'd0b09e34-2e6a-1040-99b4-6700a4844527' THEN '6c76ac76-2c1e-4531-8652-2bfb3cd02605'
            WHEN '02af17a0-5b28-1040-8340-c5c1dba40387' THEN 'f885afec-d4f7-49df-94fb-2621f40fa571'
            WHEN 'b5049528-e086-103f-967c-e1084cf42626' THEN '07c273c0-82c0-4a6a-8ccf-6ac7cff86630'
            WHEN 'ce15b18a-1b52-1040-9991-6700a4844527' THEN '94e06cc5-8950-42e3-9620-fded96d4d19d'
            WHEN '71d1fa2a-e086-103f-967a-e1084cf42626' THEN '4bbceea1-c02c-460f-a647-a40b26e868ee'
            WHEN '97b830e2-e086-103f-967b-e1084cf42626' THEN 'da2b0e36-1126-48c3-b4f2-0d4518d54bef'
            WHEN 'bf5d02d6-e175-103f-968e-e1084cf42626' THEN '97a7e80d-0a13-455c-98bd-69c128e6f5f9'
            WHEN 'cb7076f6-e13a-103f-9680-e1084cf42626' THEN '05dcd709-ff4e-4eab-9c47-de40be559052'
        END WHERE author_sub = ANY(v1_subs);
    END IF;
    IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'portal_payment') THEN
        UPDATE portal_payment SET author_sub = CASE author_sub
            WHEN 'd0b09e34-2e6a-1040-99b4-6700a4844527' THEN '6c76ac76-2c1e-4531-8652-2bfb3cd02605'
            WHEN '02af17a0-5b28-1040-8340-c5c1dba40387' THEN 'f885afec-d4f7-49df-94fb-2621f40fa571'
            WHEN 'b5049528-e086-103f-967c-e1084cf42626' THEN '07c273c0-82c0-4a6a-8ccf-6ac7cff86630'
            WHEN 'ce15b18a-1b52-1040-9991-6700a4844527' THEN '94e06cc5-8950-42e3-9620-fded96d4d19d'
            WHEN '71d1fa2a-e086-103f-967a-e1084cf42626' THEN '4bbceea1-c02c-460f-a647-a40b26e868ee'
            WHEN '97b830e2-e086-103f-967b-e1084cf42626' THEN 'da2b0e36-1126-48c3-b4f2-0d4518d54bef'
            WHEN 'bf5d02d6-e175-103f-968e-e1084cf42626' THEN '97a7e80d-0a13-455c-98bd-69c128e6f5f9'
            WHEN 'cb7076f6-e13a-103f-9680-e1084cf42626' THEN '05dcd709-ff4e-4eab-9c47-de40be559052'
        END WHERE author_sub = ANY(v1_subs);
    END IF;
    IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'portal_procurement_request') THEN
        UPDATE portal_procurement_request SET author_sub = CASE author_sub
            WHEN 'd0b09e34-2e6a-1040-99b4-6700a4844527' THEN '6c76ac76-2c1e-4531-8652-2bfb3cd02605'
            WHEN '02af17a0-5b28-1040-8340-c5c1dba40387' THEN 'f885afec-d4f7-49df-94fb-2621f40fa571'
            WHEN 'b5049528-e086-103f-967c-e1084cf42626' THEN '07c273c0-82c0-4a6a-8ccf-6ac7cff86630'
            WHEN 'ce15b18a-1b52-1040-9991-6700a4844527' THEN '94e06cc5-8950-42e3-9620-fded96d4d19d'
            WHEN '71d1fa2a-e086-103f-967a-e1084cf42626' THEN '4bbceea1-c02c-460f-a647-a40b26e868ee'
            WHEN '97b830e2-e086-103f-967b-e1084cf42626' THEN 'da2b0e36-1126-48c3-b4f2-0d4518d54bef'
            WHEN 'bf5d02d6-e175-103f-968e-e1084cf42626' THEN '97a7e80d-0a13-455c-98bd-69c128e6f5f9'
            WHEN 'cb7076f6-e13a-103f-9680-e1084cf42626' THEN '05dcd709-ff4e-4eab-9c47-de40be559052'
        END WHERE author_sub = ANY(v1_subs);
    END IF;
END $$;

-- Таблицы с PK = sub
DELETE FROM portal_telegram_binding WHERE user_sub IN (
    'd0b09e34-2e6a-1040-99b4-6700a4844527',
    '02af17a0-5b28-1040-8340-c5c1dba40387',
    'b5049528-e086-103f-967c-e1084cf42626',
    'ce15b18a-1b52-1040-9991-6700a4844527',
    '71d1fa2a-e086-103f-967a-e1084cf42626',
    '97b830e2-e086-103f-967b-e1084cf42626',
    'bf5d02d6-e175-103f-968e-e1084cf42626',
    'cb7076f6-e13a-103f-9680-e1084cf42626'
);

DELETE FROM portal_chat_member WHERE user_sub IN (
    'd0b09e34-2e6a-1040-99b4-6700a4844527',
    '02af17a0-5b28-1040-8340-c5c1dba40387',
    'b5049528-e086-103f-967c-e1084cf42626',
    'ce15b18a-1b52-1040-9991-6700a4844527',
    '71d1fa2a-e086-103f-967a-e1084cf42626',
    '97b830e2-e086-103f-967b-e1084cf42626',
    'bf5d02d6-e175-103f-968e-e1084cf42626',
    'cb7076f6-e13a-103f-9680-e1084cf42626'
);

-- specialist_profile (пересоздадутся из SSO при логине)
DELETE FROM portal_specialist_profile WHERE specialist_sub IN (
    'd0b09e34-2e6a-1040-99b4-6700a4844527',
    '02af17a0-5b28-1040-8340-c5c1dba40387',
    'b5049528-e086-103f-967c-e1084cf42626',
    'ce15b18a-1b52-1040-9991-6700a4844527',
    '71d1fa2a-e086-103f-967a-e1084cf42626',
    '97b830e2-e086-103f-967b-e1084cf42626',
    'bf5d02d6-e175-103f-968e-e1084cf42626',
    'cb7076f6-e13a-103f-9680-e1084cf42626'
);

-- Финальное удаление дублей
DELETE FROM portal_user_profile WHERE sub IN (
    'd0b09e34-2e6a-1040-99b4-6700a4844527',
    '02af17a0-5b28-1040-8340-c5c1dba40387',
    'b5049528-e086-103f-967c-e1084cf42626',
    'ce15b18a-1b52-1040-9991-6700a4844527',
    '71d1fa2a-e086-103f-967a-e1084cf42626',
    '97b830e2-e086-103f-967b-e1084cf42626',
    'bf5d02d6-e175-103f-968e-e1084cf42626',
    'cb7076f6-e13a-103f-9680-e1084cf42626'
);

-- Проверка: должно вернуть 0 строк
SELECT email, COUNT(DISTINCT sub) AS subs
FROM portal_user_profile
WHERE email IS NOT NULL AND email != ''
GROUP BY email
HAVING COUNT(DISTINCT sub) > 1;

COMMIT;
