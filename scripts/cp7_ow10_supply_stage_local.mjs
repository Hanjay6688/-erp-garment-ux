// Real stage APIs/catalog/DDL and frozen predecessor bodies; controlled Native
// source/identity/job data. Does not execute the full run_unit or production chain.
import {writeFile,mkdir} from 'node:fs/promises'
import assert from 'node:assert/strict'
import {beginLocalStageAudit} from './cp7_local_stage_audit.mjs'
import {controlledSupplyDb} from './cp7_ow10_supply_local_fixture.mjs'
const db=await controlledSupplyDb()
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
