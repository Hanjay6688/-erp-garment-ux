// Fresh PG17 model for previously unobserved support/aggregate/index references.
import assert from 'node:assert/strict'
import { readFile, writeFile } from 'node:fs/promises'
import { dirname, resolve, isAbsolute } from 'node:path'
import { fileURLToPath, pathToFileURL } from 'node:url'
import { createHash } from 'node:crypto'

assert.ok(isAbsolute(process.env.DE_PGLITE_MODULE || ''))
assert.ok(isAbsolute(process.env.DE_DISPATCH_MODEL_OUT || ''))
const { PGlite } = await import(pathToFileURL(process.env.DE_PGLITE_MODULE).href)
const here=dirname(fileURLToPath(import.meta.url))
const raw=await readFile(resolve(here,'DISPATCH_OID_QUERIES.json'))
const declaration=JSON.parse(raw)
const execution=JSON.parse(await readFile(resolve(here,'EXECUTION_OID_QUERIES.json')))
const inherited=JSON.parse(await readFile(resolve(here,'../current-final-s03-sku-s05-preparation/metadata/QUERIES.json'))).queries
const db=new PGlite()
try {
  await db.exec(`
    create table public.dispatch_called(value text);
    create function public.metadata_probe_transition(integer,integer) returns integer language plpgsql volatile
      as 'begin insert into public.dispatch_called values (''integer''); return $1+$2; end';
    create function public.metadata_probe_transition(text,text) returns text language plpgsql volatile
      as 'begin insert into public.dispatch_called values (''text''); return $1||$2; end';
    create aggregate public.metadata_probe_agg(integer)
      (sfunc=public.metadata_probe_transition,stype=integer,initcond='0');
    create aggregate public.metadata_probe_agg(text)
      (sfunc=public.metadata_probe_transition,stype=text,initcond='');
  `)
  await db.exec('begin isolation level repeatable read read only; set local search_path=pg_catalog;')
  const version=(await db.query('show server_version')).rows[0].server_version
  assert.ok(version.startsWith('17.'))
  const snapshot=async()=>(await db.query("select pg_current_snapshot()::text snapshot,current_setting('transaction_read_only') ro,current_setting('transaction_isolation') isolation")).rows[0]
  const before=await snapshot()
  const query=async sql=>Object.values((await db.query(sql)).rows[0])[0]
  const original_groups={}
  for(const name of ['routines','types','operators','relations']) {
    const rows=await query(inherited[name])
    original_groups[name]={rows:rows.map(row=>name==='routines'?{oid:row.oid,prokind:row.prokind}:
      name==='relations'?{oid:row.oid,relam:row.relam}:{oid:row.oid})}
  }
  // Only this group is required to verify range-to-operator-class references.
  const execution_groups={range_execution_oids:await query(execution.groups.range_execution_oids.query)}
  const groups={}
  for(const [name,spec]of Object.entries(declaration.groups))groups[name]=await query(spec.query)
  const counterexample=(await db.query("select a.aggfnoid::oid::text aggregate_oid,a.aggtransfn::oid::text transition_oid,to_jsonb(a)->>'aggfnoid' old_aggregate_name,to_jsonb(a)->>'aggtransfn' old_transition_name from pg_aggregate a join pg_proc p on p.oid=a.aggfnoid where p.proname='metadata_probe_agg' order by a.aggfnoid::oid")).rows
  assert.equal(counterexample.length,2)
  for(const key of ['old_aggregate_name','old_transition_name'])assert.equal(new Set(counterexample.map(r=>r[key])).size,1)
  for(const key of ['aggregate_oid','transition_oid'])assert.equal(new Set(counterexample.map(r=>r[key])).size,2)
  for(const row of counterexample)assert.equal(groups.aggregate_support_oids.find(r=>r.aggfnoid===row.aggregate_oid).aggtransfn,row.transition_oid)
  const invoked=Number((await db.query('select count(*) n from public.dispatch_called')).rows[0].n)
  assert.equal(invoked,0);assert.deepEqual(await snapshot(),before)
  await db.exec('rollback')
  const result={classification:'DISPOSABLE_POSTGRESQL17_DISPATCH_MODEL_NOT_ERP',version,
    declaration_sha256:createHash('sha256').update(raw).digest('hex'),before,
    original_groups,execution_groups,groups,counterexample,
    provider_functions_invoked:invoked,original_queries_used:4,range_query_used:1,
    new_dispatch_queries_executed:7,actual_ERP_calls:0,actual_Native_case_credit:0,production_go:false}
  await writeFile(process.env.DE_DISPATCH_MODEL_OUT,JSON.stringify(result,null,2)+'\n')
  console.log(JSON.stringify({...result,original_groups:undefined,execution_groups:undefined,groups:undefined}))
} catch(error) {
  console.error(JSON.stringify({status:'DISPATCH_MODEL_FAILED',message:error.message,sqlstate:error.code}))
  process.exitCode=1
} finally { await db.close() }
