// Actual caller/installers/public RPC SQL, Native profile/source/read/project
// bodies, controlled ERP facts, claims, access and lower operational adapters.
// This is local SQL evidence, not Auth/PostgREST, concurrency or Native/SLA.
import {readFile,writeFile,mkdir} from 'node:fs/promises'
import {createHash} from 'node:crypto'
import assert from 'node:assert/strict'
import {createNativeReorderFixture} from './cp7_ow10_reorder_local_fixture.mjs'
import {controlledSupplyDb} from './cp7_ow10_supply_local_fixture.mjs'
import {beginLocalStageAudit} from './cp7_local_stage_audit.mjs'
const {db,stageAudit,id,fixture,sourceFixture:baseSourceFixture,readerSnapshot,serverSource,block,formula}=await createNativeReorderFixture()
const read=p=>readFile(p,'utf8'),sha=s=>createHash('sha256').update(s).digest('hex')
await db.exec(`create function cp7_analysis_stage.local_reorder_consumer(jsonb,jsonb)returns jsonb
 language sql immutable as $$select cp7_reorder_inputs.history($1,$2)$$;
 alter function cp7_analysis_stage.local_reorder_consumer(jsonb,jsonb)owner to cp7_capture;`)
const inputsInstaller=await stageAudit.afterUse()
const readerAudit=await beginLocalStageAudit(db,'cp7_reorder_reader_stage')
await baseSourceFixture();await readerSnapshot()
const readerInstaller=await readerAudit.afterUse()
await controlledSupplyDb(db)
await db.exec(`create schema cp7_private;
 create function cp7_private.immutable_run()returns trigger language plpgsql as $$begin raise exception 'CP7_RUN_IMMUTABLE';end$$;
 create function cp7_netting_native.fingerprint(c jsonb)returns text language sql immutable as $$
  select encode(sha256(convert_to((c-'captured_at')::text,'UTF8')),'hex')$$;`)
const analysis=await read('scripts/cp7-src/planning/analysis.sql')
for(const name of['cp7_analysis_native.fingerprint','cp7_analysis_native.finance_mode'])await db.exec(block(analysis,name))
await db.exec(`create or replace function cp7_netting_native.source_within(p_products integer,p_match integer)returns jsonb
 language sql stable security invoker set search_path=''set TimeZone='UTC'as $$
  select cp7_baseline_native.source_within(p_products)||jsonb_build_object('controlled_operational_adapter',true)
 $$;
 do $$declare f record;begin for f in select p.oid::regprocedure s from pg_proc p join pg_namespace n on n.oid=p.pronamespace
  where n.nspname in('cp7_analysis_native','cp7_netting_native','cp7_fabric_native')and p.prokind='f'loop
   execute format('alter function %s owner to cp7_capture',f.s);
   execute format('revoke all on function %s from public,anon,authenticated,service_role,cp7_alert',f.s);
  end loop;end$$;`)
const supplyAudit=await beginLocalStageAudit(db,'cp7_reorder_supply')
await db.query(`insert into cp7_analysis_stage.jobs(id,actor,request_id,query,reference,run_id,access_at_capture,captured_at,source_hash,state,
 unit_count,units_done,plan_final,targets_total,created_at,updated_at)values($1,$2,$3,'{}','{"reorder_supply_engine":"cp7.reorder-supply.v1","financial_capture":"DEFERRED"}',
 $4,'{}',clock_timestamp(),$5,'RUNNING',1,0,false,0,clock_timestamp(),clock_timestamp())`,[id(9701),id(9702),id(9703),id(9704),'a'.repeat(64)])
const supplyInstaller=await supplyAudit.afterUse()
// Actual profile source over its actual table; no convenient preselected DTO
// can hide an unreviewed or changed physical product version in this probe.
const profileSQL=await read('scripts/cp7-src/planning/profile.sql')
const profileStart=profileSQL.indexOf('create table cp7_profile.profiles(')
await db.exec(profileSQL.slice(profileStart,profileSQL.indexOf(');',profileStart)+2))
await db.exec(block(profileSQL,'cp7_profile.source').replace('create function ','create or replace function '))
await db.exec('alter table cp7_profile.profiles owner to cp7_capture;grant select on cp7_profile.profiles to cp7_capture')
const sourceFixture=async()=>{
 await baseSourceFixture();await db.exec('truncate cp7_profile.profiles')
 for(const p of fixture().profiles)await db.query(`insert into cp7_profile.profiles(id,root_id,product_version_id,size_id,revision,config,reason,actor,request_id,recorded_at)
  values($1,$2,$3,$4,1,$5::jsonb,'CONTROLLED_FIXTURE',$6,$7,'2026-09-01T00:00:00Z')`,
  [p.profile_id,p.root_id,p.product_version_id,id(9000),JSON.stringify(p.config),id(999),id(16000+Number(p.root_id.slice(0,8)))])
}
for(const name of['wip_models','evaluations','runs']){
 const start=formula.indexOf('create table cp7_stock_formula.'+name+'(')
 await db.exec(formula.slice(start,formula.indexOf(');',start)+2))
 await db.exec('alter table cp7_stock_formula.'+name+' owner to cp7_capture')
}
const guardStart=formula.indexOf('create function cp7_stock_formula.append_only(')
await db.exec(formula.slice(guardStart,formula.indexOf('create function cp7_stock_formula.z(',guardStart)))
for(const name of['settings','manual_points','wip_models','evaluations','runs'])await db.exec(`
 alter table cp7_stock_formula.${name} owner to cp7_capture;
 alter table cp7_stock_formula.${name} enable row level security;
 create policy formula_no_access on cp7_stock_formula.${name} for all to public using(false)with check(false);
 revoke all on cp7_stock_formula.${name} from public,anon,authenticated,service_role;`)
await db.exec(`create schema auth;
 create function auth.uid()returns uuid language sql stable as $$select nullif(current_setting('request.jwt.claim.sub',true),'')::uuid$$;
 create function auth.jwt()returns jsonb language sql stable as $$select jsonb_build_object('role',current_setting('request.jwt.claim.role',true))$$;
 create table public.reorder_access_control(allowed boolean,permission boolean,role_code text,revoke_after bigint,busy boolean,material_calls integer);
 insert into public.reorder_access_control values(true,true,'OWNER',null,false,0);
 create sequence public.reorder_access_calls;
 create function erp.get_my_access_v1()returns jsonb language sql volatile as $$
  select jsonb_build_object('allowed',allowed and(revoke_after is null or nextval('public.reorder_access_calls')<revoke_after),
   'profile',jsonb_build_object('role_code',role_code))from public.reorder_access_control$$;
 create function erp.has_permission(text)returns boolean language sql volatile as $$
  select allowed and permission and(revoke_after is null or not s.is_called or s.last_value<revoke_after)
  from public.reorder_access_control cross join public.reorder_access_calls s$$;
 create function cp7_stock_formula.compute_materials(p_at timestamptz)returns jsonb
  language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$begin
   update public.reorder_access_control set material_calls=material_calls+1;
   return '{"materials":0,"materials_at_or_below":0}'::jsonb;end$$;
 create function cp7_stock_formula.ensure_computed()returns boolean
  language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$begin
   if(select busy from public.reorder_access_control)then return false;end if;
   perform cp7_stock_formula.compute(clock_timestamp(),interval'2 seconds');return true;end$$;
 create table erp.sizes(id uuid primary key,size_code text);
 insert into erp.sizes values('00009000-1111-4111-8111-111111111111','M');
 grant usage on schema auth to cp7_capture;grant select,update on public.reorder_access_control to cp7_capture;
 grant usage,select on sequence public.reorder_access_calls to cp7_capture;
 grant select on erp.sizes to cp7_capture;`)
for(const name of['z','access_now','alert_row','workspace','fg_source','refresh','save_manual','save_settings'])await db.exec(block(formula,'cp7_stock_formula.'+name))
await db.exec(await read('scripts/cp7_target_policy_stage/sql/cp7_stock_formula__compute.sql'))
const alertsSQL=await read('scripts/cp7-src/alerts/alerts.sql')
await db.exec('create schema cp7_alert_native authorization cp7_alert')
for(const name of['num','rp','tgl'])await db.exec(block(alertsSQL,'cp7_alert_native.'+name))
await db.exec(await read('scripts/cp7_production_stage/sql/cp7_alert_native__item_line.sql'))
await db.exec(`do $$declare f record;begin for f in select p.oid::regprocedure s from pg_proc p join pg_namespace n on n.oid=p.pronamespace
 where n.nspname='cp7_stock_formula'and p.prokind='f'loop
  execute format('alter function %s owner to cp7_capture',f.s);
  execute format('revoke all on function %s from public,anon,authenticated,service_role',f.s);
 end loop;
 for f in select p.oid::regprocedure s from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname='cp7_alert_native'and p.prokind='f'loop
  execute format('alter function %s owner to cp7_alert',f.s);
 end loop;end$$;
 grant execute on function cp7_stock_formula.fg_source()to cp7_alert;`)
for(const name of['erp_cp7_get_fg_reorder_v1','erp_cp7_refresh_fg_reorder_v1','erp_cp7_save_fg_reorder_manual_v1','erp_cp7_save_stock_formula_settings_v1']){
 await db.exec(block(formula,'public.'+name))
 const args={'erp_cp7_get_fg_reorder_v1':'jsonb','erp_cp7_refresh_fg_reorder_v1':'','erp_cp7_save_fg_reorder_manual_v1':'jsonb,uuid','erp_cp7_save_stock_formula_settings_v1':'jsonb,uuid'}[name]
 await db.exec(`alter function public.${name}(${args})owner to cp7_capture;
 revoke all on function public.${name}(${args})from public,anon,authenticated,service_role;
 grant execute on function public.${name}(${args})to authenticated;`)
}
await db.query("select set_config('request.jwt.claim.sub',$1,false),set_config('request.jwt.claim.role','authenticated',false)",[id(999)])
await sourceFixture()
const callerAudit=await beginLocalStageAudit(db,'cp7_reorder_caller_stage')
const results=[],wireExamples={classification:'ACTUAL_SQL_OUTPUTS_OVER_SYNTHETIC_ERP_FIXTURE_NOT_PRODUCTION_DATA'}
const test=async(id,fn)=>{try{results.push({id,status:'PASS',observed:await fn()})}catch(e){results.push({id,status:'FAIL',error:String(e.stack).slice(0,4000)})}console.log(id+': '+results.at(-1).status)}
const rpc=async(name,params=[])=>{
 await db.exec('set role authenticated')
 try{return(await db.query('select public.'+name+'('+params.map((_,i)=>'$'+(i+1)).join(',')+')v',params)).rows[0].v}
 finally{await db.exec('reset role').catch(()=>{/* Preserve original error in an aborted fixture transaction. */})}
}
await test('OW10_LIVE_CALLER_COMPUTE_AND_V2_WORKSPACE',async()=>{
 const empty=await rpc('erp_cp7_get_fg_reorder_v1',[JSON.stringify({q:'',filter:'ALL',offset:0,limit:25})])
 assert.equal(empty.contract_version,'cp7.fg-reorder.v2');assert.equal(empty.run,null)
 const got=await rpc('erp_cp7_refresh_fg_reorder_v1');assert.equal(got.items,3)
 const w=await rpc('erp_cp7_get_fg_reorder_v1',[JSON.stringify({q:'',filter:'ALL',offset:0,limit:25})])
 assert.equal(w.counts.items,3);assert.equal(w.page.rows.length,3)
 assert.equal(w.page.rows.find(x=>x.root_id===id(1)).point,'2')
 assert.equal(w.page.rows.find(x=>x.root_id===id(2)).point,'10')
 assert.equal(w.page.rows.find(x=>x.root_id===id(2)).daily_mean,'2.0000000000000000')
 assert.ok(w.page.rows.every(x=>x.contract_version==='cp7.fg-reorder-row.v2'&&x.wip_pcs===null))
 wireExamples.initial=w
 return{actual_compute_and_public_workspace_SQL:true,decimal_text_points:[2,10,0],actual_Native_profile_source:true,
  current_stock_snapshot_and_no_legacy_raw_WIP_credit:true,controlled_claims_not_Auth_PostgREST:true}
})
let callerInstaller
await test('OW10_LIVE_CALLER_REAL_INSTALLER_22_AFTER_USE_REFUSED',async()=>{
 callerInstaller=await callerAudit.afterUse();assert.equal(callerInstaller.catalog_groups,22)
 assert.equal(callerInstaller.apply_rollback_reapply_exact,true);assert.equal(callerInstaller.after_use_refused_before_first_DDL,true)
 return{three_predecessor_installers_and_actual_caller_API:true,caller_apply_admit_inverse_reapply22:true,after_use_refusal_before_DDL:true}
})
const workspace=()=>rpc('erp_cp7_get_fg_reorder_v1',[JSON.stringify({q:'',filter:'ALL',offset:0,limit:25})])
const firstRow=async()=>(await workspace()).page.rows.find(x=>x.root_id===id(1))
const erpFacts=async()=>{
 const tables=(await db.query("select tablename from pg_tables where schemaname='erp'order by tablename")).rows
 const out={};for(const {tablename:t}of tables)out[t]=(await db.query(`select md5(coalesce(jsonb_agg(to_jsonb(x)order by to_jsonb(x)::text),'[]'::jsonb)::text)h from erp.${t} x`)).rows[0].h
 return out
}
const manual=(point,revision,request=18001)=>rpc('erp_cp7_save_fg_reorder_manual_v1',[
 JSON.stringify({root_id:id(1),expected_revision:revision,reorder_point_pcs:point,reason:'CONTROLLED_MANUAL'}),id(request)])
await test('OW10_LIVE_MANUAL_REPLAY_STALE_CLEAR_AND_POSTED_FACTS_UNCHANGED',async()=>{
 const before=await erpFacts(),original=await firstRow()
 const saved=await manual(25,0);assert.equal(saved.contract_version,'cp7.fg-reorder-manual.v2')
 wireExamples.manual=saved
 assert.equal(saved.evaluation.point,'25');assert.equal(saved.evaluation.formula_point,'2')
 assert.equal(saved.evaluation.projection.target_pcs,original.projection.target_pcs)
 assert.equal((await manual(25,0)).replay,true)
 await assert.rejects(()=>manual(26,0),/CP7_FORMULA_REQUEST_REUSED/)
 await assert.rejects(()=>manual(26,0,18002),/CP7_FORMULA_MANUAL_STALE/)
 assert.equal((await db.query('select count(*)n from cp7_stock_formula.manual_points')).rows[0].n,1)
 const clear=await manual(null,1,18003);assert.equal(clear.evaluation.point,'2');assert.equal(clear.evaluation.manual_point,null)
 wireExamples.cleared=clear
 assert.equal(clear.evaluation.manual_revision,2);assert.deepEqual(await erpFacts(),before)
 await assert.rejects(()=>db.exec("update cp7_stock_formula.manual_points set reason='EDITED'"),/CP7_FORMULA_APPEND_ONLY/)
 return{manual_only_changes_trigger:true,request_replay_single_row:true,changed_payload_and_stale_revision_refused:true,
  clear_returns_to_same_Native_formula:true,posted_ERP_facts_unchanged:true,append_only:true}
})
await test('OW10_LIVE_ACCESS_RECHECK_BEFORE_WRITE_AND_AFTER_COMPUTE_ATOMIC',async()=>{
 const before=await erpFacts(),countBefore=(await db.query('select count(*)n from cp7_stock_formula.manual_points')).rows[0].n
 for(const boundary of[2,3]){
  await db.query('update public.reorder_access_control set revoke_after=$1',[boundary])
  await db.exec("select setval('public.reorder_access_calls',1,false)")
  await assert.rejects(()=>manual(25,2,18010+boundary),/CP7_FORMULA_ACCESS_(DENIED|CHANGED)/)
  await db.exec('update public.reorder_access_control set revoke_after=null')
  assert.equal((await db.query('select count(*)n from cp7_stock_formula.manual_points')).rows[0].n,countBefore)
 }
 await db.exec('update public.reorder_access_control set revoke_after=3')
 await db.exec("select setval('public.reorder_access_calls',1,false)")
 await assert.rejects(()=>manual(25,0),/CP7_FORMULA_ACCESS_(DENIED|CHANGED)/)
 await db.exec('update public.reorder_access_control set revoke_after=null')
 await db.exec("update public.reorder_access_control set role_code='STAFF'")
 assert.equal((await workspace()).can_manage,false)
 await assert.rejects(()=>manual(25,2,18016),/CP7_FORMULA_ACCESS_DENIED/)
 await db.exec("update public.reorder_access_control set role_code='OWNER',permission=false")
 await assert.rejects(()=>workspace(),/CP7_FORMULA_ACCESS_DENIED/)
 await db.exec('update public.reorder_access_control set permission=true')
 assert.deepEqual(await erpFacts(),before)
 return{actual_public_RPC_bodies:true,controlled_revocation_after_lock_and_after_compute:true,all_new_manual_writes_rolled_back:true,
  read_only_role_and_missing_permission_refused:true,not_Native_two_session_concurrency:true}
})
await test('OW10_LIVE_SETTINGS_REPLAY_AND_STALE_REVISION',async()=>{
 const before=await erpFacts(),payload={expected_revision:0,service_level:'0.90',window_days:30,reason:'CONTROLLED_SETTINGS'}
 const save=(p,r)=>rpc('erp_cp7_save_stock_formula_settings_v1',[JSON.stringify(p),id(r)])
 assert.equal((await save(payload,18101)).settings.service_level,'0.90')
 assert.equal((await save(payload,18101)).replay,true)
 await db.exec('update public.reorder_access_control set revoke_after=3')
 await db.exec("select setval('public.reorder_access_calls',1,false)")
 await assert.rejects(()=>save(payload,18101),/CP7_FORMULA_ACCESS_(DENIED|CHANGED)/)
 await db.exec('update public.reorder_access_control set revoke_after=null')
 await assert.rejects(()=>save({...payload,service_level:'0.99'},18101),/CP7_FORMULA_REQUEST_REUSED/)
 await assert.rejects(()=>save(payload,18102),/CP7_FORMULA_SETTINGS_STALE/)
 assert.equal((await db.query('select count(*)n from cp7_stock_formula.settings')).rows[0].n,1)
 assert.deepEqual(await erpFacts(),before)
 return{settings_and_manual_share_global_lock:true,append_single_revision_and_replay:true,stale_and_reused_requests_refused:true,posted_ERP_facts_unchanged:true}
})
await test('OW10_LIVE_BUSY_NEW_LOW_ITEM_FRESH_STOCK_AND_STABLE_ALERT_FACTS',async()=>{
 await rpc('erp_cp7_refresh_fg_reorder_v1')
 const before=(await db.query("select row from cp7_reorder_caller.evaluations where root_id=$1",[id(1)])).rows[0].row
 await db.query(`insert into erp.fg_stock_movements(id,product_id,qty_signed,physical_at,system_created_at,quality_grade,movement_type,book_order)
  values($1,$2,-90,clock_timestamp(),clock_timestamp(),'GRADE_A','ADJUSTMENT',100)`,[id(18201),id(1)])
 await db.exec('update public.reorder_access_control set busy=true')
 const busy=(await db.query('select cp7_stock_formula.fg_source()v')).rows[0].v
 const low=busy.rows.find(x=>x.subject_key===`${id(1)}:${id(9000)}`)
 assert.equal(low.detail.free_pcs,'0');assert.equal(low.detail.wip_pcs,null);assert.equal(low.detail.position_pcs,null)
 assert.equal(low.detail.projection.candidate_mutes_alert,false)
 assert.deepEqual((await db.query('select row from cp7_reorder_caller.evaluations where root_id=$1',[id(1)])).rows[0].row,before)
 await db.exec('update public.reorder_access_control set busy=false')
 const a=(await db.query('select cp7_stock_formula.fg_source()v')).rows[0].v
 const b=(await db.query('select cp7_stock_formula.fg_source()v')).rows[0].v
 assert.deepEqual(a,b)
 return{busy_checks_every_item_and_current_stock:true,no_old_WIP_credit:true,no_busy_evaluation_write:true,
  same_facts_no_new_alert_hash_per_tick:true}
})
await test('OW10_LIVE_CURRENT_NATIVE_READER_DIRECTED_CANDIDATE_MANUAL_AND_STALE',async()=>{
 const s=await serverSource(),snap=(await db.query('select cp7_reorder_reader.snapshot($1::jsonb)v',[JSON.stringify(s)])).rows[0].v
 const c=(await db.query('select cp7_analysis_native.source_within(5000,10000)v')).rows[0].v
 const reference={...c,financial_source:null,financial_capture:'DEFERRED'},captured=c.captured_at
 const hash=(await db.query('select cp7_analysis_native.fingerprint($1::jsonb)v',[JSON.stringify(reference)])).rows[0].v
 const eta=new Date(Date.parse(captured)+86400000).toISOString(),snapshot='controlled-global-live-supply',job=id(19001),run=id(19004)
 const refs=[{kind:'CONTROLLED_GLOBAL_SUPPLY',id:'cut-1',revision:'1'}]
 const entry=(p,kind,qty,key)=>({physical_key:key,snapshot_id:snapshot,target_key:p.target_key,size_id:p.size_id,kind,qty_pcs:qty,eta,eligible:true,refs})
 const values=snap.points.rows.map(p=>({target_key:p.target_key,size_id:p.size_id,target:p.target,
  available_fg_pcs:snap.current_stock.find(x=>x.target_key===p.target_key).native_available_pcs,
  supplies:p.target_key.startsWith(id(1))?[entry(p,'DIRECTED','4','CUT:direct:M'),entry(p,'ALLOCATED_CANDIDATE','3','CUT:candidate:M')]
   :p.target_key.startsWith(id(2))?[entry(p,'ALLOCATED_CANDIDATE','4','CUT:candidate:M')]:[]}))
 await db.query(`insert into cp7_analysis_stage.jobs(id,actor,request_id,query,reference,run_id,access_at_capture,captured_at,source_hash,state,
  unit_count,units_done,plan_final,targets_total,created_at,updated_at)values($1,$2,$3,$4::jsonb,$5::jsonb,$6,'{}',$7,$8,'DONE',1,1,true,3,$7,$7)`,
 [job,id(19002),id(19003),JSON.stringify(s.query),JSON.stringify(reference),run,captured,hash])
 await db.query('insert into cp7_analysis_stage.capture_marks values($1,null)',[job])
 const body='{"controlled":"valid-hashed-header"}',page='{"controlled":"valid-hashed-page"}',h=sha(body),p=sha(page)
 await db.query(`insert into cp7_analysis_stage.headers(run_id,job_id,body,utf8_bytes,sha256,paged,targets_total,page_count,cuts)
  values($1,$2,$3,$4,$5,'{}',3,1,'[[1,3]]')`,[run,job,body,Buffer.byteLength(body),h])
 await db.query(`insert into cp7_analysis_stage.pages(run_id,idx,target_lo,target_hi,counts,offsets,summary,body,utf8_bytes,sha256)
  values($1,0,1,3,'{}','{}','{}',$2,$3,$4)`,[run,page,Buffer.byteLength(page),p])
 await db.query(`insert into cp7_analysis_stage.page_sets values($1,$2,'{"targets":3}',clock_timestamp())`,[run,sha(h+'\n'+p)])
 const scope={alloc_status:'SCENARIO',wip_status:'COMPLETE',schedule_state:'SELECTED_ASSUMPTIONS',schedule:{plan_id:'CONTROLLED_GLOBAL_CALENDAR',revision:'1'},
  reorder_supply_budget:{contract_version:'cp7.reorder-supply-budget.v1',status:'COMPLETE',snapshot_id:snapshot,reason:null,
   rows:[['CUT:direct:M','4'],['CUT:candidate:M','7']].map(([physical_key,qty])=>({physical_key,snapshot_id:snapshot,size_id:id(9000),projected_good_pcs:qty,eta,eligible:true}))}}
 await db.query('insert into cp7_analysis_stage.plan_scope values($1,$2::jsonb)',[job,JSON.stringify(scope)])
 for(let i=0;i<values.length;i++)await db.query('insert into cp7_analysis_stage.plan_targets values($1,$2,$3,$4::jsonb)',[job,i+1,values[i].target_key,JSON.stringify(values[i])])
 const before=await erpFacts()
 const refreshed=await rpc('erp_cp7_refresh_fg_reorder_v1');assert.equal(refreshed.wip_read,1)
 const first=await firstRow();assert.equal(first.wip_pcs,'4');assert.equal(first.state,'ABOVE');assert.equal(first.projection.candidate_pcs,'3')
 assert.equal(first.projection.base_position_pcs,'4');assert.equal(first.projection.conditional_position_pcs,'7')
 const second=(await workspace()).page.rows.find(x=>x.root_id===id(2));assert.equal(second.wip_pcs,'0');assert.equal(second.projection.candidate_pcs,'4')
 const saved=await manual(25,2,19005);assert.equal(saved.evaluation.point,'25');assert.equal(saved.evaluation.state,'AT_OR_BELOW')
 assert.equal(saved.evaluation.projection.target_pcs,'5');assert.equal(saved.evaluation.projection.production_base_pcs,'1')
 wireExamples.projected=await workspace()
 const alert=(await db.query('select cp7_stock_formula.fg_source()v')).rows[0].v.rows.find(x=>x.subject_key===`${id(1)}:${id(9000)}`)
 wireExamples.alert={...alert,kind:'FG_AT_REORDER_POINT'}
 wireExamples.alertLine=(await db.query("select cp7_alert_native.item_line($1::jsonb,'SUMMARY')v",[JSON.stringify(wireExamples.alert)])).rows[0].v
 assert.deepEqual(await erpFacts(),before)
 await db.query(`insert into erp.fg_stock_movements(id,product_id,qty_signed,physical_at,system_created_at,quality_grade,movement_type,book_order)
  values($1,$2,1,clock_timestamp(),clock_timestamp(),'GRADE_A','ADJUSTMENT',101)`,[id(19006),id(1)])
 await rpc('erp_cp7_refresh_fg_reorder_v1')
 const stale=await firstRow();assert.equal(stale.free_pcs,'1');assert.equal(stale.wip_pcs,null);assert.equal(stale.wip_status,'UNKNOWN')
 assert.equal(stale.projection.candidate_pcs,null);assert.equal(stale.state,'AT_OR_BELOW')
 return{actual_Native_source_fingerprint_read_job_project_and_net_called:true,controlled_lower_source_hash_and_completed_job_not_full_worker:true,
  directed4_only_for_target1:true,candidate7_split3and4_never_mutes_alert:true,manual25_preserves_target5_and_production1:true,
  fresh_stock_change_invalidates_completed_analysis:true,posted_ERP_facts_unchanged_by_RPC:true}
})
await test('OW10_LIVE_SIZE_CONFLICT_WITH_POSTED_HISTORY_REFUSED_WITHOUT_PARTIAL_WRITES',async()=>{
 await db.exec('begin')
 try{
  const before=(await db.query('select jsonb_agg(to_jsonb(e)order by target_key)v from cp7_reorder_caller.evaluations e')).rows[0].v
  await db.query('update erp.products set effective_to=clock_timestamp(),is_active=false where id=$1',[id(1)])
  await db.query(`insert into erp.products(id,identity_root_id,size_id,model_id,sku,product_name,effective_from)
   values($1,$2,$3,$4,'CONFLICT-L','Controlled incompatible successor',clock_timestamp())`,[id(18300),id(1),id(9002),id(9001)])
  await assert.rejects(()=>rpc('erp_cp7_refresh_fg_reorder_v1'),/CP7_DEMAND_TARGET_SIZE/)
  // The failed statement aborts this controlled fixture transaction; restore
  // it before inspecting the unchanged committed evaluation state.
  await db.exec('rollback')
  assert.deepEqual((await db.query('select jsonb_agg(to_jsonb(e)order by target_key)v from cp7_reorder_caller.evaluations e')).rows[0].v,before)
 }finally{await db.exec('rollback')}
 return{Native_old_sale_size_not_reassigned_to_current_size:true,corruption_refused:true,previous_evaluations_preserved:true}
})
await test('OW10_LIVE_SUCCESSOR_SIZE_DROPS_OLD_KEY_AND_STALE_MANUAL',async()=>{
 // Root3 has no posted sale in another size. A physical successor here does
 // not manufacture a cross-size sale history just to reach the upsert.
 await rpc('erp_cp7_save_fg_reorder_manual_v1',[
  JSON.stringify({root_id:id(3),expected_revision:0,reorder_point_pcs:25,reason:'CONTROLLED_MANUAL'}),id(18301)])
 await db.query('insert into erp.sizes values($1,\'L\')',[id(9002)])
 await db.exec('update public.reorder_access_control set busy=true')
 await db.query('update erp.products set effective_to=clock_timestamp(),is_active=false where id=$1',[id(3)])
 await db.query(`insert into erp.products(id,identity_root_id,size_id,model_id,sku,product_name,effective_from)
  values($1,$2,$3,$4,'SUCCESSOR-L','Controlled successor',clock_timestamp())`,[id(18302),id(3),id(9002),id(9001)])
 await assert.rejects(()=>db.query('select cp7_stock_formula.fg_source()'),/CP7_FORMULA_BUSY_SOURCE_CHANGED/)
 await db.exec('update public.reorder_access_control set busy=false')
 await rpc('erp_cp7_refresh_fg_reorder_v1')
 const r=(await workspace()).page.rows.find(x=>x.root_id===id(3));assert.equal(r.target_key,`${id(3)}:${id(9002)}`);assert.equal(r.product_id,id(18302))
 assert.equal(r.manual_point,null);assert.equal(r.projection.manual_state,'STALE_IDENTITY')
 assert.equal(r.projection.manual_reference.reorder_point_pcs,'25')
 wireExamples.successor=await workspace()
 assert.equal((await db.query('select count(*)n from cp7_reorder_caller.evaluations where root_id=$1',[id(3)])).rows[0].n,1)
 assert.equal((await db.query('select count(*)n from cp7_reorder_caller.evaluations where target_key=$1',[`${id(3)}:${id(9000)}`])).rows[0].n,0)
 return{same_root_new_size_replaces_old_key_without_unique_collision:true,old_manual_retained_as_reference_only:true,
  busy_changed_threshold_does_not_clear_existing_alerts:true}
})
const report={classification:'LOCAL_ACTUAL_REORDER_CALLER_PUBLIC_RPC_SQL_NATIVE_PROFILE_AND_SUPPLY_READER_BODIES_CONTROLLED_CLAIMS_ERP_AND_LOWER_OPERATIONAL_ADAPTERS_NOT_NATIVE_AUTH_OR_RACES',
 status:results.every(x=>x.status==='PASS')?'PASS':'FAIL',passed:results.filter(x=>x.status==='PASS').length,total:results.length,results,
 inputs_installer:inputsInstaller,reader_installer:readerInstaller,supply_installer:supplyInstaller,caller_installer:callerInstaller,
 sql_sha256:Object.fromEntries(await Promise.all(['evaluate.sql','state.sql','compute.sql','workspace.sql','fg_source.sql','alert_row.sql','save_manual.sql','save_settings.sql','refresh.sql','item_line.sql']
  .map(async f=>[f,sha(await read('scripts/cp7_reorder_caller_stage/'+f))]))),
 controlled_material_compute:true,controlled_lock_busy_adapter:true,Native_Auth_or_factory_SLA:false,full_A_chain_qualified:false,production_go:false}
await mkdir('docs/cp7/d17-14/ow10',{recursive:true});await writeFile('docs/cp7/d17-14/ow10/local-reorder-caller.json',JSON.stringify(report,null,2)+'\n')
if(report.status==='PASS')await writeFile('tests/fixtures/reorderCallerSql.json',JSON.stringify(wireExamples,null,2)+'\n')
console.log(JSON.stringify(report,null,2));await db.close();if(report.status!=='PASS')process.exitCode=1
