-- Read-only observation for the exact owning disposable database.
-- Compare each result with the actual relation review and the installer plan.
-- Run only in the already authorized owning review transaction.

SELECT current_database() AS database_name,
       session_user AS login_role,
       current_user AS effective_role,
       pg_catalog.current_setting('session_replication_role') AS trigger_mode,
       pg_catalog.current_setting('transaction_isolation') AS isolation,
       pg_catalog.current_setting('search_path') AS search_path,
       pg_catalog.current_setting('server_version_num') AS server_version;

WITH expected(signature, symbol) AS (
    VALUES ('extensions.digest(bytea,text)', 'pg_digest'),
           ('extensions.digest(text,text)', 'pg_digest'),
           ('extensions.gen_random_uuid()', 'pg_random_uuid')
)
SELECT expected.signature,
       expected.symbol AS expected_symbol,
       p.oid AS routine_oid,
       p.probin AS observed_shared_library,
       p.prosrc AS observed_symbol,
       l.lanname AS observed_language,
       pg_catalog.pg_get_userbyid(p.proowner) AS routine_owner,
       p.prosecdef AS security_definer,
       p.proacl::text AS raw_routine_acl,
       e.extname AS observed_extension_member_of,
       e.extversion AS extension_version,
       n.nspname AS extension_schema,
       pg_catalog.pg_get_userbyid(e.extowner) AS extension_owner
FROM expected
LEFT JOIN pg_catalog.pg_proc p ON p.oid = pg_catalog.to_regprocedure(expected.signature)
LEFT JOIN pg_catalog.pg_language l ON l.oid = p.prolang
LEFT JOIN pg_catalog.pg_depend d ON d.classid = 'pg_catalog.pg_proc'::regclass
    AND d.objid = p.oid AND d.objsubid = 0
    AND d.refclassid = 'pg_catalog.pg_extension'::regclass
    AND d.refobjsubid = 0 AND d.deptype = 'e'
LEFT JOIN pg_catalog.pg_extension e ON e.oid = d.refobjid
LEFT JOIN pg_catalog.pg_namespace n ON n.oid = e.extnamespace
ORDER BY expected.signature COLLATE "C";

-- Resolve all current origin-enabled outside RI edges from a reviewed relation list.
-- Bind %(relations)s as text[] using the owning cursor. Keep catalogue OIDs and raw ACLs.
WITH reviewed(qualified_name) AS (
    SELECT pg_catalog.unnest(%(relations)s::text[])
), relations AS (
    SELECT r.qualified_name, c.oid AS relation_oid, c.relkind, c.relpersistence,
           pg_catalog.pg_get_userbyid(c.relowner) AS owner, c.relrowsecurity, c.relforcerowsecurity,
           CASE WHEN c.relacl IS NULL THEN NULL ELSE
               ARRAY(SELECT acl::text FROM pg_catalog.unnest(c.relacl) acl ORDER BY acl::text COLLATE "C") END AS raw_acl
    FROM reviewed r
    LEFT JOIN pg_catalog.pg_class c ON c.oid = pg_catalog.to_regclass(r.qualified_name)
)
SELECT qualified_name, relation_oid, relkind, relpersistence, owner, relrowsecurity, relforcerowsecurity, raw_acl
FROM relations
ORDER BY qualified_name COLLATE "C";

WITH reviewed(qualified_name, relation_oid) AS (
    SELECT input.qualified_name, pg_catalog.to_regclass(input.qualified_name)
    FROM pg_catalog.unnest(%(relations)s::text[]) AS input(qualified_name)
)
SELECT parent.qualified_name AS parent,
       child_ns.nspname || '.' || child.relname AS child,
       t.oid AS trigger_oid,
       t.tgname AS actual_trigger_name,
       t.tgtype AS event_bits,
       t.tgenabled AS enabled_mode,
       p.oid AS action_function_oid,
       p.proname AS action_function,
       con.oid AS constraint_oid,
       con.conname AS constraint_name,
       con.convalidated AS validated,
       pg_catalog.pg_get_constraintdef(con.oid) AS constraint_definition
FROM reviewed parent
JOIN pg_catalog.pg_trigger t ON t.tgrelid = parent.relation_oid
JOIN pg_catalog.pg_proc p ON p.oid = t.tgfoid
JOIN pg_catalog.pg_constraint con ON con.oid = t.tgconstraint
JOIN pg_catalog.pg_class child ON child.oid = con.conrelid
JOIN pg_catalog.pg_namespace child_ns ON child_ns.oid = child.relnamespace
WHERE t.tgisinternal AND t.tgenabled IN ('O', 'A') AND con.contype = 'f'
  AND con.confrelid = parent.relation_oid
  AND p.pronamespace = 'pg_catalog'::regnamespace
  AND p.proname IN ('RI_FKey_cascade_del', 'RI_FKey_cascade_upd', 'RI_FKey_setnull_del',
                    'RI_FKey_setnull_upd', 'RI_FKey_setdefault_del', 'RI_FKey_setdefault_upd')
  AND NOT EXISTS (SELECT 1 FROM reviewed r WHERE r.relation_oid = child.oid)
ORDER BY parent.qualified_name COLLATE "C", child_ns.nspname COLLATE "C", child.relname COLLATE "C", t.tgname COLLATE "C";

-- Bind %(roles)s to the actual observed role names and %(routines)s to exact regprocedure signatures.
WITH actors(role_name) AS (
    SELECT pg_catalog.unnest(%(roles)s::text[])
), calls(signature) AS (
    SELECT pg_catalog.unnest(%(routines)s::text[])
)
SELECT actors.role_name,
       calls.signature,
       caller.oid AS caller_oid,
       p.oid AS routine_oid,
       pg_catalog.pg_get_userbyid(p.proowner) AS routine_owner,
       p.prosecdef AS security_definer,
       p.proconfig AS routine_settings,
       p.proacl::text AS raw_routine_acl,
       pg_catalog.has_schema_privilege(caller.oid, p.pronamespace, 'USAGE') AS effective_schema_usage,
       pg_catalog.has_function_privilege(caller.oid, p.oid, 'EXECUTE') AS effective_execute
FROM actors CROSS JOIN calls
LEFT JOIN pg_catalog.pg_roles caller ON caller.rolname = actors.role_name
LEFT JOIN pg_catalog.pg_proc p ON p.oid = pg_catalog.to_regprocedure(calls.signature)
ORDER BY actors.role_name COLLATE "C", calls.signature COLLATE "C";

WITH actors(role_name) AS (
    SELECT pg_catalog.unnest(%(roles)s::text[])
), reviewed(qualified_name) AS (
    SELECT pg_catalog.unnest(%(relations)s::text[])
)
SELECT actors.role_name,
       reviewed.qualified_name,
       caller.oid AS caller_oid,
       c.oid AS relation_oid,
       caller.rolsuper,
       caller.rolbypassrls,
       pg_catalog.has_schema_privilege(caller.oid, c.relnamespace, 'USAGE') AS effective_schema_usage,
       pg_catalog.has_any_column_privilege(caller.oid, c.oid, 'SELECT') AS any_column_select,
       pg_catalog.has_any_column_privilege(caller.oid, c.oid, 'INSERT') AS any_column_insert,
       pg_catalog.has_any_column_privilege(caller.oid, c.oid, 'UPDATE') AS any_column_update,
       pg_catalog.has_table_privilege(caller.oid, c.oid, 'DELETE') AS effective_delete,
       pg_catalog.has_table_privilege(caller.oid, c.oid, 'TRUNCATE') AS effective_truncate
FROM actors CROSS JOIN reviewed
LEFT JOIN pg_catalog.pg_roles caller ON caller.rolname = actors.role_name
LEFT JOIN pg_catalog.pg_class c ON c.oid = pg_catalog.to_regclass(reviewed.qualified_name)
ORDER BY actors.role_name COLLATE "C", reviewed.qualified_name COLLATE "C";
