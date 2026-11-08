-- EXPLAIN без ANALYZE: только план по статистике, запросы не выполняются. Staging и production; при необходимости — локаль.
-- Локально: PGPASSWORD=dev psql -h 127.0.0.1 -p 5433 -U dev -d atrium -v ON_ERROR_STOP=1 -f backend/perf/explain_key_queries_plan_only.sql
-- На сервере (staging): PGPASSWORD=… psql -h … -p … -U … -d … "sslmode=require" -v ON_ERROR_STOP=1 -f /opt/atrium-staging/backend/perf/explain_key_queries_plan_only.sql
-- На сервере (production): … -f /opt/atrium-prod/backend/perf/explain_key_queries_plan_only.sql

EXPLAIN (VERBOSE, FORMAT JSON)
SELECT t.id, t.title, t.status, t."position"
FROM portal_task t
LEFT OUTER JOIN portal_task_tag AS ptt ON t.id = ptt.task_id
LEFT OUTER JOIN portal_tag AS pt ON pt.id = ptt.tag_id
WHERE t.status = 'todo'
ORDER BY t."position" ASC, t.created_at DESC
LIMIT 100;

EXPLAIN (VERBOSE, FORMAT JSON)
SELECT pnr.node_id, r.slug
FROM portal_nav_node_role pnr
JOIN portal_role r ON r.id = pnr.role_id;

EXPLAIN (VERBOSE, FORMAT JSON)
SELECT worked_on, minutes
FROM portal_time_entry
WHERE user_sub = 'user-sub'
ORDER BY worked_on
LIMIT 500;

EXPLAIN (VERBOSE, FORMAT JSON)
SELECT d.id, d.title
FROM portal_document d
LEFT OUTER JOIN portal_document_tag pdt ON d.id = pdt.document_id
LEFT OUTER JOIN portal_tag t ON t.id = pdt.tag_id
ORDER BY d.created_at DESC
LIMIT 50;
