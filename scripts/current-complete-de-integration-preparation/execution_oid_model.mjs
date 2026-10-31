// Disposable PostgreSQL17 model only; never connects to an ERP database.
import assert from 'node:assert/strict'
import { readFile, writeFile } from 'node:fs/promises'
import { fileURLToPath, pathToFileURL } from 'node:url'
import { dirname, resolve, isAbsolute } from 'node:path'
import { createHash } from 'node:crypto'

assert.ok(isAbsolute(process.env.DE_PGLITE_MODULE || ''))
assert.ok(isAbsolute(process.env.DE_METADATA_MODEL_OUT || ''))
const { PGlite } = await import(pathToFileURL(process.env.DE_PGLITE_MODULE).href)
const here = dirname(fileURLToPath(import.meta.url))
const raw = await readFile(resolve(here, 'EXECUTION_OID_QUERIES.json'))
const declaration = JSON.parse(raw)
const inherited = JSON.parse(await readFile(resolve(here, '../current-final-s03-sku-s05-preparation/metadata/QUERIES.json'))).queries
const db = new PGlite()
try {
  await db.exec(`
    create table public.metadata_called (value text);
    create function public.metadata_probe_equal(integer,integer) returns boolean language plpgsql volatile
      as 'begin insert into public.metadata_called values (''integer''); return $1=$2; end';
    create function public.metadata_probe_equal(text,text) returns boolean language plpgsql volatile
      as 'begin insert into public.metadata_called values (''text''); return $1=$2; end';
    create operator public.=== (leftarg=integer,rightarg=integer,function=public.metadata_probe_equal);
    create operator public.=== (leftarg=text,rightarg=text,function=public.metadata_probe_equal);
  `)
  await db.exec('begin isolation level repeatable read read only; set local search_path=pg_catalog;')
  const version = (await db.query('show server_version')).rows[0].server_version
  assert.ok(version.startsWith('17.'))
  const snapshot = async () => (await db.query("select pg_current_snapshot()::text snapshot,current_setting('transaction_read_only') ro,current_setting('transaction_isolation') isolation")).rows[0]
  const before = await snapshot()
  const original_groups = {}
  for (const name of ['routines','types','operators','languages']) {
    const rows = Object.values((await db.query(inherited[name])).rows[0])[0]
    // Only numeric identities are needed by the pure cross-reference control.
    original_groups[name] = { rows: rows.map(row => ({ oid: row.oid })) }
  }
  const groups = {}
  for (const [name, spec] of Object.entries(declaration.groups)) {
    groups[name] = Object.values((await db.query(spec.query)).rows[0])[0]
  }
  const counterexample = (await db.query("select o.oid::text, o.oprcode::oid::text exact_function_oid, (to_jsonb(o)->>'oprcode') prior_json_value from pg_operator o where o.oprname='===' order by o.oid")).rows
  assert.equal(counterexample.length, 2)
  assert.equal(new Set(counterexample.map(r => r.prior_json_value)).size, 1)
  assert.equal(new Set(counterexample.map(r => r.exact_function_oid)).size, 2)
  for (const row of counterexample) {
    assert.equal(groups.operator_routine_oids.find(r => r.oid === row.oid).oprcode, row.exact_function_oid)
  }
  const invoked = Number((await db.query('select count(*) n from public.metadata_called')).rows[0].n)
  assert.equal(invoked, 0)
  assert.deepEqual(await snapshot(), before)
  await db.exec('rollback')
  const result = { classification:'DISPOSABLE_POSTGRESQL17_METADATA_MODEL_NOT_ERP', version,
    declaration_sha256:createHash('sha256').update(raw).digest('hex'), before,
    original_groups, groups, counterexample, provider_functions_invoked:invoked,
    original_queries_used:4, additional_queries_executed:4,
    actual_ERP_calls:0, actual_Native_case_credit:0, production_go:false }
  await writeFile(process.env.DE_METADATA_MODEL_OUT, JSON.stringify(result, null, 2)+'\n')
  console.log(JSON.stringify({ ...result, original_groups:undefined,groups:undefined }))
} catch (error) {
  console.error(JSON.stringify({status:'MODEL_FAILED',message:error.message,sqlstate:error.code}))
  process.exitCode = 1
} finally {
  await db.close()
}
