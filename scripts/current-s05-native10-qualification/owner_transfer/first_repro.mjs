// Local PGlite role/DDL experiment only. No ERP schema, Native or network.
import { createRequire } from 'node:module'
import { readFile, writeFile, access } from 'node:fs/promises'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import { createHash } from 'node:crypto'
const here = dirname(fileURLToPath(import.meta.url))
const require = createRequire(import.meta.url)
const dependency = process.env.S05_PGLITE_MODULE
if (!dependency) throw new Error('S05_PGLITE_MODULE must name an already installed local PGlite module; no download is performed')
const { PGlite } = require(dependency)
const db = new PGlite()
const report = { classification: 'LOCAL_PGLITE_ROLE_DDL_REPRO_NOT_NATIVE', Native_executions: 0, production_go: false, independent_acceptance: false, steps: [] }
const rows = async sql => (await db.query(sql)).rows
async function step(label, sql) {
  const result = { label, sql }
  try { result.rows = await rows(sql); result.status = 'EXECUTED' }
  catch (error) { result.status = 'REJECTED'; result.error = { code: error.code, message: error.message, detail: error.detail, hint: error.hint } }
  report.steps.push(result)
  return result
}
try {
  report.version = await rows('select version()')
  report.dependency = JSON.parse(await readFile(resolve(dependency, 'package.json'), 'utf8')).version
  const original = await readFile(resolve(here, 'retained/report.sql'))
  report.report_before = { bytes: original.length, sha256: createHash('sha256').update(original).digest('hex') }
  await db.exec("create role s05_installer nologin nosuperuser createrole noinherit; grant usage,create on schema public to s05_installer;")
  await step('SESSION_SUPERUSER_CURRENT_ROLE_NONSUPER', "set role s05_installer")
  await step('IDENTITY', "select current_user,session_user,(select rolsuper from pg_roles where rolname=current_user) current_super,(select rolsuper from pg_roles where rolname=session_user) session_super,current_setting('createrole_self_grant')")
  await step('CREATE_READER_AS_INSTALLER', 'create role cp7_accessory_standard_read nologin noinherit nosuperuser nocreatedb nocreaterole noreplication nobypassrls')
  await step('CREATOR_MEMBERSHIP', "select pg_get_userbyid(roleid) role,pg_get_userbyid(member) member,admin_option,inherit_option,set_option from pg_auth_members where roleid='cp7_accessory_standard_read'::regrole")
  await step('CREATE_STUB_WITH_SAME_PUBLIC_IDENTITY', "create function public.erp_cp7_get_accessory_standard_report_v1(date,date,uuid,uuid,text,integer,integer)returns jsonb language sql as $$select '{}'::jsonb$$")
  await step('READER_LACKS_CREATE', "select has_schema_privilege('cp7_accessory_standard_read','public','CREATE') allowed,nspacl::text raw_acl from pg_namespace where nspname='public'")
  const transfer = 'alter function public.erp_cp7_get_accessory_standard_report_v1(date,date,uuid,uuid,text,integer,integer) owner to cp7_accessory_standard_read'
  await step('ORIGINAL_OWNER_TRANSFER', transfer)
  await step('TEMPORARY_CREATE', 'grant create on schema public to cp7_accessory_standard_read')
  await step('TRANSFER_WITH_CREATE', transfer)
  await step('REVOKE_TEMPORARY_CREATE', 'revoke create on schema public from cp7_accessory_standard_read')
  await step('IDENTITY_OWNER_AND_ACL_AFTER', "select pg_get_userbyid(proowner) owner,(select nspacl::text from pg_namespace where nspname='public') raw_acl,has_schema_privilege('cp7_accessory_standard_read','public','CREATE') reader_create from pg_proc where oid='public.erp_cp7_get_accessory_standard_report_v1(date,date,uuid,uuid,text,integer,integer)'::regprocedure")
  await db.exec('reset role; create schema s05_null_acl;')
  report.null_acl_before = await rows("select nspacl::text raw_acl from pg_namespace where nspname='s05_null_acl'")
  await db.exec('grant create on schema s05_null_acl to cp7_accessory_standard_read; revoke create on schema s05_null_acl from cp7_accessory_standard_read;')
  report.null_acl_after = await rows("select nspacl::text raw_acl from pg_namespace where nspname='s05_null_acl'")
} finally {
  await db.close()
  const destination = resolve(here, 'FIRST_REPRO.json')
  try { await access(destination); throw new Error('FIRST_REPRO already exists; refusing overwrite') }
  catch (error) { if (error.code !== 'ENOENT') throw error }
  await writeFile(destination, JSON.stringify(report, null, 2) + '\n')
  process.stdout.write(JSON.stringify(report, null, 2) + '\n')
}
