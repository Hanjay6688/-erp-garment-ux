// Actual isolated PostgreSQL query controls, not ERP Native or writer proofs.
import assert from 'node:assert/strict'
import {readFileSync,writeFileSync} from 'node:fs'
import {resolve,dirname} from 'node:path'
import {fileURLToPath,pathToFileURL} from 'node:url'
import {createHash} from 'node:crypto'

const here=dirname(fileURLToPath(import.meta.url))
assert.ok(process.env.GLOBAL_METADATA_PGLITE_MODULE,'EXPLICIT_ISOLATED_POSTGRES_MODULE_REQUIRED')
const {PGlite}=await import(pathToFileURL(resolve(process.env.GLOBAL_METADATA_PGLITE_MODULE)).href)
const db=new PGlite()
const declaration=JSON.parse(readFileSync(resolve(here,'QUERIES.json')))
const query=declaration.queries
const marker='SOURCE_PROFILE_CONTROL_PRIVATE_SENTINEL'
const hash=v=>createHash('sha256').update(v).digest('hex')
const output=process.env.GLOBAL_METADATA_CONTROL_OUTPUT
try{
 await db.exec(`
 create role metadata_profile_control;
 alter role metadata_profile_control set app.private_control='${marker}';
 create function public.metadata_profile_function(p text default '${marker}') returns text
 language sql set app.private_control='${marker}' as $$select '${marker}'::text$$;
 create domain public.metadata_profile_domain as text default '${marker}' check(value<>'${marker}');
 create table public.metadata_profile_table(a text default '${marker}');
 insert into public.metadata_profile_table values('ordinary control row');
 create policy metadata_profile_policy on public.metadata_profile_table using(a<>'${marker}');
 create view public.metadata_profile_view as select '${marker}'::text as value;
 create table public.metadata_profile_partitioned(k text)partition by list(k);
 create table public.metadata_profile_partition partition of public.metadata_profile_partitioned for values in('${marker}');
 create function public.metadata_profile_trigger()returns trigger language plpgsql as $$begin return new;end$$;
 create trigger metadata_profile_trigger before insert on public.metadata_profile_table
 for each row execute function public.metadata_profile_trigger('${marker}');
 create sequence public.metadata_profile_sequence start with 42;
 select nextval('public.metadata_profile_sequence');
 `)
 const state=async()=>({rows:(await db.query('select * from public.metadata_profile_table order by a')).rows,
  sequence:(await db.query('select last_value,is_called from public.metadata_profile_sequence')).rows})
 const before=await state()
 const groups={}
 await db.exec('begin isolation level repeatable read read only')
 for(const[name,sql]of Object.entries(query)){
  if(name==='cron_jobs')continue
  const value=Object.values((await db.query(sql)).rows[0])[0]
  assert.ok(Array.isArray(value),'ACTUAL_METADATA_ARRAY_REQUIRED:'+name)
  groups[name]=value
 }
 await db.exec('rollback')
 assert.equal(JSON.stringify(groups).includes(marker),false,'SQL_BODY_DEFAULT_CONFIG_OR_ARGUMENT_VALUE_LEAKED')
 const fixture=groups.routines.find(r=>r.proname==='metadata_profile_function')
 assert.ok(fixture?.source_sha256&&fixture?.defaults_sha256&&fixture?.config_sha256)
 assert.equal('prosrc'in fixture||'proargdefaults'in fixture||'proconfig'in fixture,false)
 const role=groups.roles.find(r=>r.rolname==='metadata_profile_control')
 assert.ok(role?.config_keys.includes('app.private_control'))
 assert.equal('rolpassword'in role||'rolconfig'in role,false)
 const pg=(await db.query('select version()as version')).rows[0].version
 const absent=(await db.query("select to_regclass('cron.job')is null as absent")).rows[0].absent
 assert.equal(absent,true)
 await db.exec(`create schema cron;create table cron.job(jobid bigint,command text,nodename text,active boolean,database text);
 insert into cron.job values(1,'select ''${marker}''','postgres://control:${marker}@remote.invalid',true,'cp6_rollback');`)
 await db.exec('begin isolation level repeatable read read only')
 const cron=Object.values((await db.query(query.cron_jobs)).rows[0])[0]
 await db.exec('rollback')
 assert.equal(cron.length,1);assert.equal(cron[0].active,true);assert.equal(cron[0].node_is_loopback,false)
 assert.equal('command'in cron[0]||'nodename'in cron[0],false)
 assert.equal(JSON.stringify(cron).includes(marker),false)
 assert.equal(cron[0].command_sha256,hash(`select '${marker}'`))
 assert.equal(cron[0].node_sha256,hash(`postgres://control:${marker}@remote.invalid`))
 assert.deepEqual(await state(),before,'METADATA_CAPTURE_CHANGED_EXISTING_ROWS_OR_SEQUENCE')
 const report={status:'ACTUAL_ISOLATED_POSTGRES_SYSTEM_CRON_QUERY_CONTROLS_PASS_NOT_NATIVE',
  PostgreSQL:pg,queries:Object.keys(query).length,all_namespace_metadata_queries_executed:Object.keys(groups).length,
  synthetic_cron_present_and_absent_controls:true,SQL_default_body_role_config_trigger_partition_values_withheld:true,
  cron_command_and_node_values_withheld:true,existing_control_rows_and_sequence_equal:true,
  function_catalog_includes_system:groups.routines.some(r=>r.schema==='pg_catalog'),
  group_counts:Object.fromEntries(Object.entries(groups).map(([k,v])=>[k,v.length])),
  actual_ERP_Native_cases:0,writer_closure:false,production_go:false,independent_acceptance:false}
 assert.equal(report.function_catalog_includes_system,true)
 if(output)writeFileSync(output,JSON.stringify(report,null,2)+'\n')
 console.log(JSON.stringify(report))
}finally{await db.close()}
