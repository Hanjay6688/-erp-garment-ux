BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY;
SET LOCAL TIME ZONE 'UTC';
SET LOCAL search_path = pg_catalog;
WITH parent AS (
    SELECT 'realtime.messages'::regclass AS oid
), children AS (
    SELECT c.oid, n.nspname AS schema, c.relname AS name, c.relkind AS kind,
           c.relispartition AS is_partition,
           pg_get_expr(c.relpartbound, c.oid) AS bound
    FROM pg_inherits i
    JOIN pg_class c ON c.oid = i.inhrelid
    JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE i.inhparent = (SELECT oid FROM parent)
), detached AS (
    SELECT c.relname AS name
    FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE n.nspname = 'realtime' AND c.relkind IN ('r', 'p', 'f')
      AND c.relname ~ '^messages_[0-9]{4}_[0-9]{2}_[0-9]{2}$'
      AND NOT EXISTS (SELECT FROM children WHERE oid = c.oid)
)
SELECT jsonb_build_object(
    'database', current_database(),
    'read_only', current_setting('transaction_read_only'),
    'postmaster_started_utc', to_char(pg_postmaster_start_time(), 'YYYY-MM-DD"T"HH24:MI:SS.US"Z"'),
    'postmaster_day_utc', (pg_postmaster_start_time() AT TIME ZONE 'UTC')::date,
    'children', COALESCE((SELECT jsonb_agg(to_jsonb(ch) - 'oid' ORDER BY ch.schema, ch.name)
                          FROM children ch), '[]'::jsonb),
    'detached_daily_tables', COALESCE((SELECT jsonb_agg(name ORDER BY name) FROM detached), '[]'::jsonb)
);
COMMIT;
