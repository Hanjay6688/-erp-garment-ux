// Real stage APIs/catalog/DDL and frozen predecessor bodies; controlled Native
// source/identity/job data. Does not execute the full run_unit or production chain.
import {readFile,writeFile,mkdir} from 'node:fs/promises'
import assert from 'node:assert/strict'
import {beginLocalStageAudit} from './cp7_local_stage_audit.mjs'
const {PGlite}=await import(process.env.CP7_PGLITE_MODULE??'@electric-sql/pglite')
const db=new PGlite(),read=p=>readFile(p,'utf8')
const block=(s,name)=>{const a=s.indexOf('create function '+name+'(');assert.ok(a>=0,name);return s.slice(a,s.indexOf('$$;',s.indexOf('as $$',a))+3)}
await db.exec(`create role cp7_capture nologin noinherit nosuperuser nocreatedb nocreaterole noreplication bypassrls;
 create role cp7_alert nologin;create role anon nologin;create role authenticated nologin;create role service_role nologin;
 create schema cp7_planning;create schema cp7_analysis_stage;create schema cp7_analysis_native;create schema cp7_netting_native;
 create schema cp7_fabric_native;create schema erp;create schema extensions;
 create function extensions.digest(bytea,text)returns bytea language sql immutable as $$select sha256($1)$$;
 create function cp7_netting_native.source_within(integer,integer)returns jsonb language sql stable as $$
  select '{"captured_at":"2026-10-23T00:00:00Z","facts":{"products":[]},"controlled_native":true}'::jsonb$$;
 create function cp7_analysis_native.material_source(jsonb,timestamptz)returns jsonb language sql stable as $$select '{}'::jsonb$$;
 create function cp7_fabric_native.source(jsonb,timestamptz)returns jsonb language sql stable as $$select '{}'::jsonb$$;
 create function erp.get_owner_financial_snapshot_v2(date,date,date)returns jsonb language sql stable as $$select '{}'::jsonb$$;
 create table cp7_analysis_native.runs(id uuid,actor uuid,request_id uuid,query jsonb,captured_at timestamptz,access_at_capture jsonb,facts jsonb,result jsonb,dependency_hash text);`)
for(const p of['scripts/cp7-src/wip/bootstrap.sql','scripts/cp7-src/demand/bootstrap.sql','scripts/cp7_production_stage/sql/cp7_baseline__net.sql'])await db.exec(await read(p))
const planning=await read('scripts/cp7-src/planning/bootstrap.sql');await db.exec(block(planning,'cp7_planning.utc'))
const stages=await read('scripts/cp7-src/planning/analysis-stages.sql')
await db.exec(stages.slice(stages.indexOf('create table cp7_analysis_stage.jobs('),stages.indexOf('create function cp7_analysis_stage.work_immutable(')))
await db.exec(block(stages,'cp7_analysis_stage.bounds'));await db.exec(block(stages,'cp7_analysis_stage.run_unit'))
await db.exec(block(await read('scripts/cp7-src/planning/analysis.sql'),'cp7_analysis_native.source_within'))
await db.exec(`alter function cp7_analysis_stage.run_unit(cp7_analysis_stage.jobs,cp7_analysis_stage.units)owner to cp7_capture;
 alter function cp7_analysis_native.source_within(integer,integer)owner to cp7_capture;
 grant usage on schema erp,extensions,cp7_netting_native,cp7_analysis_native,cp7_analysis_stage,cp7_fabric_native,cp7_planning to cp7_capture;
 revoke all on function cp7_analysis_stage.run_unit(cp7_analysis_stage.jobs,cp7_analysis_stage.units),
 cp7_analysis_native.source_within(integer,integer)from public,anon,authenticated,service_role;`)
const audit=await beginLocalStageAudit(db,'cp7_reorder_supply')
const source=(await db.query('select cp7_analysis_native.source_within(5000,10000)v')).rows[0].v
assert.equal(source.reorder_supply_engine,'cp7.reorder-supply.v1')
await db.query(`insert into cp7_analysis_stage.jobs(id,actor,request_id,query,reference,run_id,access_at_capture,captured_at,source_hash,
 state,unit_count,created_at,updated_at)values('00000000-1111-4111-8111-111111111111','00000000-2222-4222-8222-222222222222',
 '00000000-3333-4333-8333-333333333333','{}',$1::jsonb,'00000000-4444-4444-8444-444444444444','{}',
 '2026-10-23T00:00:00Z',repeat('a',64),'RUNNING',1,'2026-10-23T00:00:00Z','2026-10-23T00:00:00Z')`,[JSON.stringify(source)])
const installer=await audit.afterUse()
const report={classification:'LOCAL_REAL_PRODUCER_STAGE_INSTALL_AND_22_PG_CATALOG_GROUPS_WITH_CONTROLLED_NATIVE_ADAPTER_NOT_NATIVE',status:'PASS',
 installer,actual_new_source_marker_captured_in_job:true,full_run_unit_and_K3_executed:false,live_ROP_caller_changed:false,
 full_A_chain_qualified:false,production_go:false}
await mkdir('docs/cp7/d17-14/ow10',{recursive:true});await writeFile('docs/cp7/d17-14/ow10/local-supply-stage.json',JSON.stringify(report,null,2)+'\n')
console.log(JSON.stringify(report,null,2));await db.close()
