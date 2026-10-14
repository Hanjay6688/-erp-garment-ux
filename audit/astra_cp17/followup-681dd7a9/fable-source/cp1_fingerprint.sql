-- ERP Garment Checkpoint 1 independent revalidation fingerprint.
-- Algorithm: CP1_REVALIDATION_V1.
--
-- This script is intentionally read-only: one SELECT statement built from CTEs.
-- It performs no DDL, DML, transaction control, advisory locking, or function calls
-- that mutate application state.
--
-- Catalog scope:
--   * relations/columns/views/functions/triggers/indexes/constraints/policies:
--     schemas "erp" and "public";
--   * table_count and RLS counts: schema "erp" only;
--   * grants: information_schema role table/routine grants for "erp" and "public";
--   * runtime observations: auth.users, erp.app_users, storage, cron, migration
--     ledger, and other non-idle sessions at the instant this SELECT runs.
--
-- Hash construction:
--   * every object is serialized to an explicitly ordered text record;
--   * records are sorted bytewise by that text and joined with LF;
--   * each component is PostgreSQL md5(serialized_component);
--   * schema_fingerprint_v1 is md5(component hashes joined with "|").
--
-- The historical Checkpoint 1 fingerprint did not persist its source algorithm.
-- Therefore these V1 hashes are a new reproducible baseline and are not expected
-- to equal checkpoint_1_fingerprint.json's historical hashes.

WITH
relation_records AS (
  SELECT concat_ws('|',
    n.nspname,
    c.relname,
    c.relkind::text,
    c.relpersistence::text,
    c.relrowsecurity::text,
    c.relforcerowsecurity::text
  ) AS record
  FROM pg_catalog.pg_class AS c
  JOIN pg_catalog.pg_namespace AS n ON n.oid = c.relnamespace
  WHERE n.nspname IN ('erp', 'public')
    AND c.relkind IN ('r', 'p', 'v', 'm', 'S', 'f')
),
column_records AS (
  SELECT concat_ws('|',
    n.nspname,
    c.relname,
    a.attnum::text,
    a.attname,
    pg_catalog.format_type(a.atttypid, a.atttypmod),
    a.attnotnull::text,
    a.attidentity::text,
    a.attgenerated::text,
    coalesce(pg_catalog.pg_get_expr(d.adbin, d.adrelid), '')
  ) AS record
  FROM pg_catalog.pg_attribute AS a
  JOIN pg_catalog.pg_class AS c ON c.oid = a.attrelid
  JOIN pg_catalog.pg_namespace AS n ON n.oid = c.relnamespace
  LEFT JOIN pg_catalog.pg_attrdef AS d
    ON d.adrelid = a.attrelid
   AND d.adnum = a.attnum
  WHERE n.nspname IN ('erp', 'public')
    AND c.relkind IN ('r', 'p', 'v', 'm', 'f')
    AND a.attnum > 0
    AND NOT a.attisdropped
),
view_records AS (
  SELECT concat_ws('|',
    n.nspname,
    c.relname,
    c.relkind::text,
    pg_catalog.pg_get_viewdef(c.oid, true)
  ) AS record
  FROM pg_catalog.pg_class AS c
  JOIN pg_catalog.pg_namespace AS n ON n.oid = c.relnamespace
  WHERE n.nspname IN ('erp', 'public')
    AND c.relkind IN ('v', 'm')
),
function_records AS (
  SELECT concat_ws('|',
    n.nspname,
    p.proname,
    pg_catalog.pg_get_function_identity_arguments(p.oid),
    p.prokind::text,
    p.prosecdef::text,
    p.provolatile::text,
    p.proparallel::text,
    pg_catalog.pg_get_userbyid(p.proowner),
    pg_catalog.pg_get_functiondef(p.oid)
  ) AS record
  FROM pg_catalog.pg_proc AS p
  JOIN pg_catalog.pg_namespace AS n ON n.oid = p.pronamespace
  WHERE n.nspname IN ('erp', 'public')
    AND p.prokind IN ('f', 'p')
),
trigger_records AS (
  SELECT concat_ws('|',
    n.nspname,
    c.relname,
    t.tgname,
    t.tgenabled::text,
    pg_catalog.pg_get_triggerdef(t.oid, true)
  ) AS record
  FROM pg_catalog.pg_trigger AS t
  JOIN pg_catalog.pg_class AS c ON c.oid = t.tgrelid
  JOIN pg_catalog.pg_namespace AS n ON n.oid = c.relnamespace
  WHERE n.nspname IN ('erp', 'public')
    AND NOT t.tgisinternal
),
index_records AS (
  SELECT concat_ws('|',
    schemaname,
    tablename,
    indexname,
    indexdef
  ) AS record
  FROM pg_catalog.pg_indexes
  WHERE schemaname IN ('erp', 'public')
),
constraint_records AS (
  SELECT concat_ws('|',
    n.nspname,
    coalesce(c.relname, ''),
    con.conname,
    con.contype::text,
    con.condeferrable::text,
    con.condeferred::text,
    con.convalidated::text,
    pg_catalog.pg_get_constraintdef(con.oid, true)
  ) AS record
  FROM pg_catalog.pg_constraint AS con
  JOIN pg_catalog.pg_namespace AS n ON n.oid = con.connamespace
  LEFT JOIN pg_catalog.pg_class AS c ON c.oid = con.conrelid
  WHERE n.nspname IN ('erp', 'public')
),
policy_records AS (
  SELECT concat_ws('|',
    schemaname,
    tablename,
    policyname,
    permissive,
    coalesce(array_to_string(roles, ','), ''),
    cmd,
    coalesce(qual, ''),
    coalesce(with_check, '')
  ) AS record
  FROM pg_catalog.pg_policies
  WHERE schemaname IN ('erp', 'public')
),
table_grant_records AS (
  SELECT concat_ws('|',
    grantor,
    grantee,
    table_schema,
    table_name,
    privilege_type,
    is_grantable,
    coalesce(with_hierarchy, '')
  ) AS record
  FROM information_schema.role_table_grants
  WHERE table_schema IN ('erp', 'public')
),
routine_grant_records AS (
  SELECT concat_ws('|',
    grantor,
    grantee,
    specific_schema,
    specific_name,
    routine_schema,
    routine_name,
    privilege_type,
    is_grantable
  ) AS record
  FROM information_schema.role_routine_grants
  WHERE routine_schema IN ('erp', 'public')
),
component_hashes AS (
  SELECT
    (SELECT md5(coalesce(string_agg(record, E'\n' ORDER BY record COLLATE "C"), '')) FROM relation_records) AS relation_hash,
    (SELECT md5(coalesce(string_agg(record, E'\n' ORDER BY record COLLATE "C"), '')) FROM column_records) AS column_hash,
    (SELECT md5(coalesce(string_agg(record, E'\n' ORDER BY record COLLATE "C"), '')) FROM view_records) AS view_hash,
    (SELECT md5(coalesce(string_agg(record, E'\n' ORDER BY record COLLATE "C"), '')) FROM function_records) AS function_hash,
    (SELECT md5(coalesce(string_agg(record, E'\n' ORDER BY record COLLATE "C"), '')) FROM trigger_records) AS trigger_hash,
    (SELECT md5(coalesce(string_agg(record, E'\n' ORDER BY record COLLATE "C"), '')) FROM index_records) AS index_hash,
    (SELECT md5(coalesce(string_agg(record, E'\n' ORDER BY record COLLATE "C"), '')) FROM constraint_records) AS constraint_hash,
    (SELECT md5(coalesce(string_agg(record, E'\n' ORDER BY record COLLATE "C"), '')) FROM policy_records) AS policy_hash,
    (SELECT md5(coalesce(string_agg(record, E'\n' ORDER BY record COLLATE "C"), '')) FROM table_grant_records) AS table_grant_hash,
    (SELECT md5(coalesce(string_agg(record, E'\n' ORDER BY record COLLATE "C"), '')) FROM routine_grant_records) AS routine_grant_hash
),
object_counts AS (
  SELECT jsonb_build_object(
    'erp_tables', (
      SELECT count(*) FROM pg_catalog.pg_class AS c
      JOIN pg_catalog.pg_namespace AS n ON n.oid = c.relnamespace
      WHERE n.nspname = 'erp' AND c.relkind IN ('r', 'p')
    ),
    'scoped_relations', (SELECT count(*) FROM relation_records),
    'scoped_columns', (SELECT count(*) FROM column_records),
    'scoped_views', (SELECT count(*) FROM view_records),
    'scoped_functions', (SELECT count(*) FROM function_records),
    'scoped_triggers', (SELECT count(*) FROM trigger_records),
    'scoped_indexes', (SELECT count(*) FROM index_records),
    'scoped_constraints', (SELECT count(*) FROM constraint_records),
    'scoped_policies', (SELECT count(*) FROM policy_records),
    'scoped_table_grants', (SELECT count(*) FROM table_grant_records),
    'scoped_routine_grants', (SELECT count(*) FROM routine_grant_records),
    'scoped_grants_total',
      (SELECT count(*) FROM table_grant_records) +
      (SELECT count(*) FROM routine_grant_records)
  ) AS value
),
runtime_state AS (
  SELECT jsonb_build_object(
    'auth_users', (SELECT count(*) FROM auth.users),
    'app_users', (SELECT count(*) FROM erp.app_users),
    'erp_rls_enabled_tables', (
      SELECT count(*) FROM pg_catalog.pg_class AS c
      JOIN pg_catalog.pg_namespace AS n ON n.oid = c.relnamespace
      WHERE n.nspname = 'erp'
        AND c.relkind IN ('r', 'p')
        AND c.relrowsecurity
    ),
    'erp_rls_disabled_tables', (
      SELECT count(*) FROM pg_catalog.pg_class AS c
      JOIN pg_catalog.pg_namespace AS n ON n.oid = c.relnamespace
      WHERE n.nspname = 'erp'
        AND c.relkind IN ('r', 'p')
        AND NOT c.relrowsecurity
    ),
    'storage_buckets', (SELECT count(*) FROM storage.buckets),
    'storage_objects', (SELECT count(*) FROM storage.objects),
    'cron_jobs', (SELECT count(*) FROM cron.job),
    'active_cron_jobs', (SELECT count(*) FROM cron.job WHERE active),
    'other_nonidle_sessions', (
      SELECT count(*)
      FROM pg_catalog.pg_stat_activity
      WHERE pid <> pg_catalog.pg_backend_pid()
        AND backend_type = 'client backend'
        AND state IS DISTINCT FROM 'idle'
    ),
    'platform_migrations', (
      SELECT count(*) FROM supabase_migrations.schema_migrations
    ),
    'latest_platform_migration', (
      SELECT concat_ws('_', version, name)
      FROM supabase_migrations.schema_migrations
      ORDER BY version DESC
      LIMIT 1
    )
  ) AS value
),
final_fingerprint AS (
  SELECT
    h.*,
    md5(concat_ws('|',
      h.relation_hash,
      h.column_hash,
      h.view_hash,
      h.function_hash,
      h.trigger_hash,
      h.index_hash,
      h.constraint_hash,
      h.policy_hash,
      h.table_grant_hash,
      h.routine_grant_hash
    )) AS schema_fingerprint_v1
  FROM component_hashes AS h
)
SELECT jsonb_build_object(
  'algorithm', 'CP1_REVALIDATION_V1',
  'captured_at_utc', to_char(statement_timestamp() AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS.MS"Z"'),
  'database', current_database(),
  'server_version', current_setting('server_version'),
  'object_counts', object_counts.value,
  'hashes', to_jsonb(final_fingerprint),
  'runtime_state', runtime_state.value
) AS checkpoint_1_revalidation
FROM final_fingerprint
CROSS JOIN object_counts
CROSS JOIN runtime_state;
