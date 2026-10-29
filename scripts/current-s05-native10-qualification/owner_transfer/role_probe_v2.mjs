// Second local PGlite experiment. Never an ERP/Native qualification.
import { createRequire } from 'node:module'
import { readFile, writeFile, access } from 'node:fs/promises'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
const here = dirname(fileURLToPath(import.meta.url))
const dependency = process.env.S05_PGLITE_MODULE
if (!dependency) throw new Error('S05_PGLITE_MODULE must point to an installed local module')
const { PGlite } = createRequire(import.meta.url)(dependency)
const db = new PGlite()
const result = { classification: 'LOCAL_PGLITE_ROLE_DDL_ONLY_NOT_NATIVE', Native_executions: 0, steps: [] }
async function query(sql) { return (await db.query(sql)).rows }
async function step(label, sql) {
  const row = { label, sql }
  try { row.rows = await query(sql); row.status = 'EXECUTED' }
  catch (error) { row.status = 'REJECTED'; row.error = { code: error.code, message: error.message } }
  result.steps.push(row)
  return row
}
try {
  result.version = await query('select version()')
  result.dependency = JSON.parse(await readFile(resolve(dependency, 'package.json'), 'utf8')).version
  await db.exec('create role s05_installer nologin nosuperuser createrole noinherit; grant usage,create on schema public to s05_installer; grant create on database template1 to s05_installer; set role s05_installer;')
  const old = (await query("select current_setting('createrole_self_grant') old"))[0].old
  await step('BOUNDED_SELF_GRANT', "select set_config('createrole_self_grant','set, inherit',true)")
  // A session-local SET needs one enclosing transaction for this experiment.
  await db.exec('begin;')
  await step('BOUNDED_SELF_GRANT_IN_TRANSACTION', "select set_config('createrole_self_grant','set, inherit',true)")
  await step('CREATE_NEW_READER', 'create role cp7_accessory_standard_read nologin noinherit nosuperuser nocreatedb nocreaterole noreplication nobypassrls')
  await step('RESTORE_SELF_GRANT_BEFORE_OTHER_DDL', "select set_config('createrole_self_grant',"+"'"+old+"'"+",true)")
  await step('EXACT_AUTO_EDGE', "select pg_get_userbyid(roleid) role,pg_get_userbyid(member) member,pg_get_userbyid(grantor) grantor,admin_option,inherit_option,set_option from pg_auth_members where roleid='cp7_accessory_standard_read'::regrole")
  await step('SCHEMA_AUTHORIZATION', 'create schema s05_reader_test authorization cp7_accessory_standard_read')
  await db.exec("create function public.s05_role_probe()returns integer language sql as $$select 1$$")
  const aclBefore = await query("select nspacl::text raw_acl from pg_namespace where nspname='public'")
  await step('DENIED_BEFORE_CREATE', 'alter function public.s05_role_probe()owner to cp7_accessory_standard_read')
  // The failed statement marks the transaction aborted; keep that first exact
  // result and begin another isolated attempt with SET-capable creator setup.
  await db.exec('rollback; set role s05_installer; begin;')
  await db.exec("select set_config('createrole_self_grant','set, inherit',true); create role cp7_accessory_standard_read nologin noinherit; select set_config('createrole_self_grant','',true); create schema s05_reader_test authorization cp7_accessory_standard_read; create function public.s05_role_probe()returns integer language sql as $$select 1$$;")
  await step('TEMP_CREATE_ONLY_NEW_READER', 'grant create on schema public to cp7_accessory_standard_read')
  await step('ALLOWED_WITH_CREATE', 'alter function public.s05_role_probe()owner to cp7_accessory_standard_read')
  await step('REVOKE_TEMP_CREATE', 'revoke create on schema public from cp7_accessory_standard_read')
  result.explicit_acl_before = aclBefore
  result.explicit_acl_after = await query("select nspacl::text raw_acl from pg_namespace where nspname='public'")
  await step('REMOVE_ONLY_AUTO_EDGE', 'revoke cp7_accessory_standard_read from s05_installer')
  await step('ZERO_MEMBERSHIP_AFTER', "select count(*) n from pg_auth_members where roleid='cp7_accessory_standard_read'::regrole or member='cp7_accessory_standard_read'::regrole")
  await step('OWNER_AFTER', "select pg_get_userbyid(proowner) owner,has_schema_privilege('cp7_accessory_standard_read','public','CREATE') reader_create from pg_proc where oid='public.s05_role_probe()'::regprocedure")
  await step('DROP_OWNED_WITHOUT_HANDOVER', 'drop owned by cp7_accessory_standard_read cascade')
  await db.exec('rollback; reset role;')
} finally {
  await db.close()
  const destination = resolve(here, 'ROLE_PROBE_V2.json')
  try { await access(destination); throw new Error('ROLE_PROBE exists; refusing overwrite') } catch (error) { if (error.code !== 'ENOENT') throw error }
  await writeFile(destination, JSON.stringify(result, null, 2)+'\n')
  process.stdout.write(JSON.stringify(result, null, 2)+'\n')
}
