// Execute actual extension DDL and the repository's grantee-first serializer.
// Parent request is controlled; this proves ACL parsing, not Native commands.
import assert from 'node:assert/strict'
import {readFile,writeFile} from 'node:fs/promises'
import {execFileSync} from 'node:child_process'
import {createHash} from 'node:crypto'
const {PGlite}=await import(process.env.CP7_PGLITE_MODULE??'@electric-sql/pglite')
const creator=process.env.CP7_FROZEN_ACL_CREATOR??'postgres'
assert.ok(['postgres','supabase_admin'].includes(creator))
const db=new PGlite(),read=p=>readFile(p,'utf8')
const block=(s,n)=>{const m=s.match(new RegExp('create (?:or replace )?function '+n.replaceAll('.','\\.')+'\\([\\s\\S]*?\\$\\$;','g'));assert.equal(m?.length,1,n);return m[0]}
const queries=JSON.parse(execFileSync('python',['-B','-c',"import sys,json;sys.path.insert(0,'scripts');from cp7_ow04_restore_bundle import QUERIES;print(json.dumps({k:QUERIES[k]for k in('schemas','functions')}))"],{encoding:'utf8'}))
try{
 await db.exec('create role cp7_capture;create role anon;create role authenticated;create role service_role;create role cp7_alert;create schema cp7_private;create schema cp7_analysis_stage authorization cp7_capture;revoke create on schema public from public;')
 await db.exec(block(await read('scripts/cp7-src/snapshot/bootstrap.sql'),'cp7_private.immutable_run'))
 await db.exec(await read('scripts/cp7-src/wip/bootstrap.sql'))
 const native=await read('scripts/cp7-src/planning/analysis-stages.sql')
 await db.exec(native.slice(native.indexOf('create table cp7_analysis_stage.jobs('),native.indexOf('-- Declared bounds, once.')))
 const choice=await read('scripts/cp7_product_analog_choice_stage/choice.sql')
 await db.exec(choice.slice(0,choice.indexOf('create function cp7_product_analog_choice.material(')))
 await db.exec("create schema cp7_frozen_analysis_units_v2;create function cp7_frozen_analysis_units_v2.request(jsonb,uuid)returns jsonb language sql as $$select null::jsonb$$;")
 // Reproduce public-schema defaults under both actual administrative creators.
 await db.exec('create role supabase_admin superuser;alter default privileges for role postgres in schema public grant all on functions to postgres,anon,authenticated,service_role;alter default privileges for role supabase_admin in schema public grant all on functions to postgres,anon,authenticated,service_role;set role '+creator)
 const sources={}
 for(const name of['scripts/cp7_frozen_analysis_facade_v2/facade.sql','scripts/cp7_frozen_analysis_readers_v2/reference.sql','scripts/cp7_frozen_analysis_readers_v2/reader.prepared.sql','scripts/cp7_frozen_analysis_choice_v2/choice.prepared.sql']){
  const sql=await read(name);sources[name]=createHash('sha256').update(sql).digest('hex');await db.exec(sql)
 }
 // Match _catalog's name resolution and timezone, as well as its query text.
 await db.exec("set search_path='';set TimeZone='UTC'")
 const catalog={}
 for(const[k,sql]of Object.entries(queries))catalog[k]=Object.fromEntries((await db.query(sql)).rows.map(r=>Object.values(r)))
 const report={contract:'cp7.frozen-actual-ACL-catalog-local.v2',status:'DDL_AND_RAW_SERIALIZATION_COMPLETE',creator,public_schema_defaults_reproduced:true,catalog,DDL_source_sha256:sources,query_sha256:Object.fromEntries(Object.entries(queries).map(([k,v])=>[k,createHash('sha256').update(v).digest('hex')])),server_version:(await db.query('select version()v')).rows[0].v,actual_Native:false,controlled_parent_request:true,actual_command_executed:false,production_go:false}
 assert.ok(process.env.CP7_FROZEN_ACL_REPORT)
 await writeFile(process.env.CP7_FROZEN_ACL_REPORT,JSON.stringify(report)+'\n')
 console.log(JSON.stringify({status:report.status,schemas:Object.keys(catalog.schemas).length,functions:Object.keys(catalog.functions).length}))
}finally{await db.close()}
