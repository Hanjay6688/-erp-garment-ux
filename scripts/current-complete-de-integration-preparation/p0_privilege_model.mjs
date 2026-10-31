// Execute only the new catalog queries against disposable PostgreSQL17 roles.
import assert from 'node:assert/strict'
import { readFile, writeFile } from 'node:fs/promises'
import { dirname, resolve, isAbsolute } from 'node:path'
import { fileURLToPath, pathToFileURL } from 'node:url'
import { createHash } from 'node:crypto'

assert.ok(isAbsolute(process.env.DE_PGLITE_MODULE||''))
assert.ok(isAbsolute(process.env.DE_P0_PRIVILEGE_MODEL_OUT||''))
const {PGlite}=await import(pathToFileURL(process.env.DE_PGLITE_MODULE).href)
const here=dirname(fileURLToPath(import.meta.url))
const raw=await readFile(resolve(here,'P0_PRIVILEGE_QUERIES.json'))
const declaration=JSON.parse(raw)
const dependencies=JSON.parse(await readFile(resolve(here,'P0_DEPENDENCIES.json')))
const original=JSON.parse(await readFile(resolve(here,'../current-final-s03-sku-s05-preparation/metadata/QUERIES.json'))).queries
const db=new PGlite()
try {
  await db.exec(`create schema cp7_credit;create schema ow04_source_proposal;
    create table public.p0_called(value text);
    create role p0_granted nologin;
    create role p0_inherited nologin inherit;
    create role p0_noinherit nologin noinherit;
    create role p0_columns nologin;
    create role p0_hidden nologin;
    create role p0_plain nologin;
    grant p0_granted to p0_inherited with inherit true;
    grant p0_granted to p0_noinherit with inherit false;
    grant usage on schema cp7_credit,ow04_source_proposal to p0_granted,p0_columns,p0_plain;
    create table cp7_credit.return_families(id integer,obsolete text,value text);
    alter table cp7_credit.return_families drop column obsolete;
    create table cp7_credit.return_family_members(id integer,value text);
    grant select on cp7_credit.return_families to p0_granted;
    grant update(value) on cp7_credit.return_families to p0_columns;`)
  const signatures=Object.keys(dependencies.functions)
  for(const [signature,spec]of Object.entries(dependencies.functions)) {
    await db.exec(`create function ${signature} returns boolean language plpgsql
      ${spec.security_definer?'security definer':'security invoker'} ${spec.volatility==='s'?'stable':'volatile'}
      as 'begin insert into public.p0_called values (''called''); return true; end';`)
  }
  await db.exec(`revoke execute on function ${signatures[1]} from public;
    grant execute on function ${signatures[1]} to p0_granted;
    revoke execute on function ${signatures[5]} from public;
    grant execute on function ${signatures[5]} to p0_hidden;`)
  await db.exec('begin isolation level repeatable read read only;set local search_path=pg_catalog;')
  const version=(await db.query('show server_version')).rows[0].server_version
  const server_version_num=(await db.query('show server_version_num')).rows[0].server_version_num
  assert.ok(version.startsWith('17.'))
  const snapshot=async()=>(await db.query("select current_user::text current_role,session_user::text session_role,pg_current_snapshot()::text snapshot,current_setting('transaction_read_only') ro,current_setting('transaction_isolation') isolation,current_setting('search_path') search_path")).rows[0]
  const before=await snapshot()
  const query=async(sql,params=[])=>Object.values((await db.query(sql,params)).rows[0])[0]
  const original_groups={}
  for(const name of ['roles','schemas','routines','relations'])original_groups[name]={rows:await query(original[name])}
  const selected={functions:{},relations:{}}
  for(const row of original_groups.routines.rows)if(row.signature in dependencies.functions)selected.functions[row.signature]=row
  for(const row of original_groups.relations.rows)if(`${row.schema}.${row.relname}`in dependencies.relations)selected.relations[`${row.schema}.${row.relname}`]=row
  assert.equal(Object.keys(selected.functions).length,6)
  assert.equal(Object.keys(selected.relations).length,2)
  const params={roles:original_groups.roles.rows.map(r=>String(r.oid)),functions:Object.values(selected.functions).map(r=>String(r.oid)),relations:Object.values(selected.relations).map(r=>String(r.oid))}
  const groups={}
  for(const [name,spec]of Object.entries(declaration.groups)) {
    let parameter=0
    groups[name]=await query(spec.query.replace(/%s/g,()=>`$${++parameter}`),spec.parameters.map(k=>params[k]))
  }
  const role=name=>String(original_groups.roles.rows.find(r=>r.rolname===name).oid)
  const fn=signature=>String(selected.functions[signature].oid)
  const table=String(selected.relations['cp7_credit.return_families'].oid)
  const f=(r,s)=>groups.functions.find(x=>x.role_oid===role(r)&&x.function_oid===fn(s))
  const t=r=>groups.tables.find(x=>x.role_oid===role(r)&&x.relation_oid===table)
  const c=(r,a)=>groups.column_privileges.find(x=>x.role_oid===role(r)&&x.relation_oid===table&&x.attnum===a)
  assert.equal(selected.functions[signatures[0]].proacl,null)
  assert.equal(f('p0_plain',signatures[0]).execute,true)
  assert.equal(f('p0_plain',signatures[0]).schema_usage,true)
  assert.equal(f('p0_plain',signatures[1]).execute,false)
  assert.equal(f('p0_inherited',signatures[1]).execute,true)
  assert.equal(f('p0_noinherit',signatures[1]).execute,false)
  assert.equal(f('p0_hidden',signatures[5]).execute,true)
  assert.equal(f('p0_hidden',signatures[5]).schema_usage,false)
  assert.equal(t('p0_inherited').select,true)
  assert.equal(t('p0_noinherit').select,false)
  assert.equal(t('p0_columns').update,false)
  assert.equal(c('p0_columns',3).update,true)
  assert.equal(c('p0_columns',1).update,false)
  assert.equal(groups.columns.find(x=>x.relation_oid===table&&x.attnum===2).attisdropped,true)
  assert.equal(groups.column_privileges.some(x=>x.relation_oid===table&&x.attnum===2),false)
  const called=Number((await db.query('select count(*) n from public.p0_called')).rows[0].n)
  assert.equal(called,0);assert.deepEqual(await snapshot(),before)
  await db.exec('rollback')
  const base={classification:'ACTUAL_READ_ONLY_ALL_NAMESPACE_SYSTEM_CRON_METADATA_NOT_WRITER_CLOSURE',
    database:'cp6_rollback',primary_scheduler_database:false,server_version_num,
    current_role:before.current_role,session_role:before.session_role,snapshot:before.snapshot,groups:original_groups}
  const result={classification:'DISPOSABLE_PG17_P0_PRIVILEGE_MODEL_NOT_ERP',version,base,selected,groups,before,
    declaration_sha256:createHash('sha256').update(raw).digest('hex'),
    assertions:['NULL_ACL_PUBLIC_EXECUTE','REVOKED_PUBLIC_EXECUTE','INHERITED_MEMBERSHIP','NOINHERIT_MEMBERSHIP',
      'EXECUTE_WITHOUT_SCHEMA_USAGE','COLUMN_UPDATE_WITHOUT_TABLE_UPDATE','DROPPED_COLUMN_INVENTORY','READONLY_SAME_SNAPSHOT'],
    original_queries_used:4,new_privilege_queries_executed:4,provider_functions_invoked:called,
    actual_ERP_calls:0,actual_Native_case_credit:0,production_go:false,independent_acceptance:false}
  await writeFile(process.env.DE_P0_PRIVILEGE_MODEL_OUT,JSON.stringify(result,null,2)+'\n')
  console.log(JSON.stringify({...result,base:undefined,selected:undefined,groups:undefined}))
}catch(error){console.error(JSON.stringify({status:'P0_PRIVILEGE_MODEL_FAILED',message:error.message,sqlstate:error.code}));process.exitCode=1}
finally{await db.close()}
