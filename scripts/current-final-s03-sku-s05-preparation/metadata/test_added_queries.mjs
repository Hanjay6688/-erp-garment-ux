// Only the four added queries. Original23 controls remain separately retained.
import assert from'node:assert/strict'
import{readFileSync,writeFileSync}from'node:fs'
import{dirname,resolve}from'node:path'
import{fileURLToPath,pathToFileURL}from'node:url'
import{createHash}from'node:crypto'
const here=dirname(fileURLToPath(import.meta.url))
assert.ok(process.env.GLOBAL_METADATA_PGLITE_MODULE,'EXPLICIT_ISOLATED_POSTGRES_MODULE_REQUIRED')
const{PGlite}=await import(pathToFileURL(resolve(process.env.GLOBAL_METADATA_PGLITE_MODULE)).href)
const db=new PGlite(),q=JSON.parse(readFileSync(resolve(here,'QUERIES.json'))).queries
const marker='PROFILE_ADDITIONAL_CONTROL_PRIVATE_SENTINEL',hash=s=>createHash('sha256').update(s).digest('hex')
try{
 await db.exec('begin isolation level repeatable read read only')
 const groups={}
 for(const name of['subscriptions','subscription_relations','replication_slots','backend_activity']){
  const rows=Object.values((await db.query(q[name])).rows[0])[0]
  assert.ok(Array.isArray(rows));groups[name]=rows
 }
 await db.exec('rollback')
 // Embedded PostgreSQL exposes no real live backend rows. Do not turn an
 // empty observation into a live-backend redaction or ERP proof.
 const relation='from pg_catalog.pg_stat_activity a'
 assert.equal(q.backend_activity.split(relation).length-1,1)
 const values=`from(values(1,'${marker}'::text,'127.0.0.1'::pg_catalog.inet,'${marker}'::text,'${marker}'::text))as a(pid,query,client_addr,client_hostname,application_name)`
 const projected=q.backend_activity.replace(relation,values)
 const row=Object.values((await db.query(projected)).rows[0])[0][0]
 assert.equal(JSON.stringify(row).includes(marker),false)
 assert.equal(row.query_sha256,hash(marker));assert.equal(row.application_sha256,hash(marker))
 assert.equal(row.client_is_local,true)
 const subrelation='from pg_catalog.pg_subscription s'
 assert.equal(q.subscriptions.split(subrelation).length-1,1)
 const subquery=q.subscriptions.replace(subrelation,`from(values(1,'${marker}'::text))as s(oid,subconninfo)`)
 const subscription=Object.values((await db.query(subquery)).rows[0])[0][0]
 assert.equal(JSON.stringify(subscription).includes(marker),false)
 assert.equal(subscription.connection_sha256,hash(marker))
 const result={status:'ACTUAL_ISOLATED_POSTGRES_FOUR_ADDED_QUERY_SYNTAX_AND_SYNTHETIC_PROJECTION_CONTROLS_PASS',
  actual_catalog_queries_executed:4,old23_query_controls_reused:true,
  actual_catalog_counts:Object.fromEntries(Object.entries(groups).map(([k,v])=>[k,v.length])),
  actual_live_backend_redaction_observed:groups.backend_activity.length>0,
  explicitly_synthetic_SQL_projection_controls:2,
  backend_query_configuration_and_subscription_connection_values_withheld_in_synthetic_projections:true,
  actual_ERP_Native_cases:0,writer_closure:false,production_go:false,independent_acceptance:false}
 if(process.env.GLOBAL_METADATA_ADDED_CONTROL_OUTPUT)writeFileSync(process.env.GLOBAL_METADATA_ADDED_CONTROL_OUTPUT,JSON.stringify(result,null,2)+'\n')
 console.log(JSON.stringify(result))
}finally{await db.close()}
