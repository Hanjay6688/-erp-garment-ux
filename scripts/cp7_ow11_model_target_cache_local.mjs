// Actual current-source and cached workspace bodies with controlled access,
// cache rows and historical model data. No Native/Auth/runtime acceptance.
import {randomUUID,createHash} from 'node:crypto'
import {writeFile} from 'node:fs/promises'
import assert from 'node:assert/strict'
import {modelTargetSourceFixture} from './cp7_ow11_model_target_source_local_fixture.mjs'
const {db,read,sql,actor,key,setting,ready,current,reset,seed,rejects}=await modelTargetSourceFixture()
const before=process.argv.includes('--before'),cases=[]
const block=(s,name)=>{const start=s.indexOf('create or replace function '+name+'(');assert(start>=0,name);return s.slice(start,s.indexOf('$$;',start)+3)}
await db.exec(`create schema cp7_reorder_caller;
 create table cp7_reorder_caller.evaluations(target_key text,row jsonb);
 create table cp7_reorder_caller.use_marks(id boolean);
 insert into cp7_reorder_caller.use_marks values(true);
 create table cp7_stock_formula.runs(id boolean,computed_at timestamptz);
 insert into cp7_stock_formula.runs values(true,clock_timestamp());
 create function cp7_stock_formula.current_settings()returns jsonb language sql as $$select '{}'::jsonb$$;
 create function cp7_reorder_caller.wire_row(r jsonb,p_at timestamptz)returns jsonb language sql immutable as $$select jsonb_set(r,'{projection,stock_checked_at}',to_jsonb(cp7_planning.utc(p_at)))$$;`)
const source=before?await read('scripts/cp7_reorder_caller_stage/workspace.sql'):block(await read('scripts/cp7_model_target_consumer_stage/hooks.sql'),'cp7_stock_formula.workspace')
await db.exec(source)
const workspace=()=>sql("select cp7_stock_formula.workspace('{\"q\":\"\",\"filter\":\"ALL\",\"offset\":0,\"limit\":100}')v")
const initialize=async()=>{
 for(const[k,v]of Object.entries({actor,active:'true',model_access:'true',warehouse_access:'true',access_epoch:'1',facts:'original',change_second:'false',revoke_second:'false'}))await setting(k,v)
 await ready();const s=await current();await db.exec('truncate cp7_reorder_caller.evaluations')
 const row={target_key:key,sku:'CONTROLLED',product_name:'Controlled private model',state:'ABOVE',basis:'FORMULA',projection:{contract_version:'cp7.fg-reorder-projection.v3',stock_checked_at:s.checked_at,target_demand:{model:{source_hash:s.source_hash,actor_scope_id:s.actor_scope_id,policy_source:s.policy_source,run_id:s.rows[0].run_id}}}}
 await db.query('insert into cp7_reorder_caller.evaluations values($1,$2::jsonb)',[key,JSON.stringify(row)]);await reset();return row
}
const test=async(id,fn)=>{await db.exec('begin');try{cases.push({id,status:'PASS',observed:await fn()})}catch(e){cases.push({id,status:'FAIL',error:String(e.stack).slice(0,1400)})}finally{await db.exec('rollback')}console.log(id+': '+cases.at(-1).status)}
await test('CURRENT_OWNER_SAME_SOURCE_MAY_READ_OWN_CACHED_PROVENANCE',async()=>{
 const expected=await initialize(),w=await workspace();assert.equal(w.page.rows.length,1);assert.deepEqual(w.page.rows[0].projection.target_demand,expected.projection.target_demand)
 return{same_owned_cached_result_retained:true}
})
await test('OTHER_FG_ACTOR_CANNOT_READ_PRIVATE_OWNER_MODEL_CACHE',async()=>{
 await initialize();await setting('actor',randomUUID());await setting('model_access','false')
 await rejects(workspace,/CP7_MODEL_TARGET_REORDER_REFRESH_REQUIRED/)
 return{foreign_actor_refused_before_returning_cached_policy_or_run:true}
})
await test('SAME_ACTOR_REVOKED_MODEL_ACCESS_CANNOT_READ_OLD_CACHE',async()=>{
 await initialize();await setting('model_access','false');await rejects(workspace,/CP7_MODEL_TARGET_REORDER_REFRESH_REQUIRED/)
 return{FG_permission_alone_does_not_admit_private_old_model:true}
})
await test('CURRENT_PERMISSION_EPOCH_REQUIRES_NEW_COMPUTATION',async()=>{
 await initialize();await setting('access_epoch','2');await rejects(workspace,/CP7_MODEL_TARGET_REORDER_REFRESH_REQUIRED/)
 return{same_actor_changed_authority_not_replayed:true}
})
await test('CURRENT_POLICY_AND_PHYSICAL_SOURCE_RETIRE_CACHED_MODEL',async()=>{
 await initialize();await setting('facts','changed');await rejects(workspace,/CP7_MODEL_TARGET_REORDER_REFRESH_REQUIRED/)
 await setting('facts','original');const at=await sql('select cp7_planning.utc(clock_timestamp())v');await seed({revision:'2',state:'SUSPENDED',at});await rejects(workspace,/CP7_MODEL_TARGET_REORDER_REFRESH_REQUIRED/)
 return{old_policy_and_old_physical_source_refused:true}
})
await test('SOURCE_CHANGE_DURING_CACHED_READ_REFUSES_BEFORE_RETURN',async()=>{
 await initialize()
 await db.exec("create or replace function cp7_reorder_caller.wire_row(r jsonb,p_at timestamptz)returns jsonb language plpgsql volatile as $$begin perform set_config('model_target_test.facts','changed during cached read',true);return r;end$$")
 await rejects(workspace,/CP7_MODEL_TARGET_REORDER_REFRESH_REQUIRED/)
 return{source_checked_again_after_actual_workspace_assembly:true,controlled_mid_read_change:true}
})
await test('MODEL_CACHE_APPEARING_AFTER_LEGACY_PREFLIGHT_IS_NOT_RETURNED',async()=>{
 const row=await initialize();row.projection={contract_version:'cp7.fg-reorder-projection.v2',stock_checked_at:row.projection.stock_checked_at}
 await db.query('update cp7_reorder_caller.evaluations set row=$1::jsonb',[JSON.stringify(row)])
 await db.exec("create or replace function cp7_reorder_caller.wire_row(r jsonb,p_at timestamptz)returns jsonb language sql volatile as $$select jsonb_set(r,'{projection}',jsonb_build_object('contract_version','cp7.fg-reorder-projection.v3','target_demand',jsonb_build_object('model',jsonb_build_object('policy_source','CONTROLLED_PRIVATE_VALUE'))))$$")
 await rejects(workspace,/CP7_MODEL_TARGET_REORDER_REFRESH_REQUIRED/)
 return{no_unchecked_model_response_after_legacy_preflight:true,controlled_mid_read_cache_change:true}
})
await test('CURRENT_FG_ONLY_BASELINE_CACHE_HAS_NO_PRIVATE_MODEL_CONTEXT',async()=>{
 await initialize();await setting('model_access','false')
 const s=await sql('select cp7_model_target_source.capture_for_reorder($1::text[],clock_timestamp())v',[[key]])
 const model={source_hash:s.source_hash,actor_scope_id:s.actor_scope_id,policy_source:s.policy_source,run_id:s.rows[0].run_id}
 await db.query("update cp7_reorder_caller.evaluations set row=jsonb_set(row,'{projection,target_demand,model}',$1::jsonb)",[JSON.stringify(model)])
 await reset();const w=await workspace();assert.equal(w.page.rows.length,1);assert.equal(w.page.rows[0].projection.target_demand.model.policy_source,null);assert.equal(w.page.rows[0].projection.target_demand.model.run_id,null)
 assert.equal(await sql("select current_setting('model_target_test.history_calls')v"),'0')
 return{FG_only_current_reference_readable:true,no_global_model_history_scan_or_private_model_context:true,cache_rebuild_controlled_not_Native_refresh:true}
})
await test('LEGACY_CACHE_PATH_REMAINS_UNCHANGED',async()=>{
 const row=await initialize();row.projection={contract_version:'cp7.fg-reorder-projection.v2',stock_checked_at:row.projection.stock_checked_at}
 await db.query('update cp7_reorder_caller.evaluations set row=$1::jsonb',[JSON.stringify(row)])
 await setting('actor',randomUUID());await setting('model_access','false');await reset()
 const w=await workspace();assert.equal(w.page.rows.length,1);assert.equal(w.page.rows[0].projection.contract_version,'cp7.fg-reorder-projection.v2')
 assert.equal(await sql("select current_setting('model_target_test.history_calls')v"),'0')
 return{legacy_without_private_model_provenance_keeps_existing_FG_read:true}
})
const report={contract:'cp7.model-target-cache-local.v1',phase:before?'BEFORE':'AFTER',status:cases.every(c=>c.status==='PASS')?'PASS':'FAIL',counts:cases.reduce((a,c)=>(a[c.status]=(a[c.status]??0)+1,a),{}),cases,source_sha256:createHash('sha256').update(source).digest('hex'),actual_current_source_and_workspace_SQL:true,controlled_access_cache_and_history:true,actual_Native_capture:false,actual_Auth_HTTP_credit:false,production_go:false}
await writeFile('docs/cp7/d17-14/ow11/model-target-cache-'+(before?'before':'after')+'.json',JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report,null,2));await db.close();if(report.status!=='PASS')process.exitCode=1
