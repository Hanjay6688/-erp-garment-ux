// Actual frozen Native history + current target bodies on controlled DTOs.
// The independent comparison uses the whole existing history_build, rather
// than replaying this adapter's chunk orchestration. This is not Native/Auth.
import {readFile, writeFile, mkdir} from 'node:fs/promises'
import {createHash} from 'node:crypto'
import assert from 'node:assert/strict'
import {beginLocalStageAudit} from './cp7_local_stage_audit.mjs'
import {createNativeReorderFixture} from './cp7_ow10_reorder_local_fixture.mjs'
const {db,stageAudit,id,clock,query,product,profile,movement,fixture,invoke,whole,defaults,lead,points,serverSource,readPoints,readerSnapshot,addMovement,stockSummary,sourceFixture,block,read,formula,nativeSourceSQL,manifest}=await createNativeReorderFixture()
const results=[]
const test=async(id,fn)=>{try{results.push({id,status:'PASS',observed:await fn()})}catch(e){results.push({id,status:'FAIL',error:String(e.stack).slice(0,3000)})}console.log(id+': '+results.at(-1).status)}
await test('OW10_INPUTS_ACTUAL_WHOLE_NATIVE_HISTORY_AND_STOCK_EQUAL',async()=>{
  const source=fixture(),a=await invoke(source),b=await whole(source)
  assert.deepEqual(a.history,b.history.rows);assert.deepEqual(a.current_stock,b.current_stock)
  const targets=(await db.query('select cp7_analysis_stage.baseline_rows($1::jsonb,$2::jsonb,$3::jsonb,$4)v',
    [JSON.stringify(source),JSON.stringify(b.history.rows),JSON.stringify(b.current_stock),a.source_hash])).rows[0].v
  assert.deepEqual(a.targets,targets)
  await db.exec('set role cp7_capture');assert.deepEqual(await invoke(source),a);await db.exec('reset role')
  return{whole_history_and_current_stock_full_JSON_equal:true,actual_staged_targets_full_JSON_equal:true,real_non_superuser_read:true}
})
await test('OW10_INPUTS_INTRADAY_STOCKOUT_NOT_LEGACY_START_DAY_AVAILABLE',async()=>{
  const a=await invoke(fixture()),row=a.history.find(x=>x.target_key.startsWith(id(1)))
  assert.equal(row.days.find(x=>x.date==='2026-09-26').state,'STOCKOUT')
  assert.equal(row.available_days,29);assert.equal(row.stockout_days,1);assert.equal(row.gross_observed_pcs,'10')
  const net=a.targets.find(x=>x.target_key===row.target_key).target
  assert.equal(net.reorder_point_pcs,'2');assert.equal(net.target_pcs,'5')
  return{start90_zero_then90_still_stockout:true,available_days:29,exact_total10_over29_point2_target5:true}
})
await test('OW10_INPUTS_PROFILE_MANUAL_AND_KNOWN_ZERO_REMAIN_NATIVE_CHOICES',async()=>{
  const a=await invoke(fixture()),two=a.targets.find(x=>x.target_key.startsWith(id(2))),zero=a.targets.find(x=>x.target_key.startsWith(id(3)))
  assert.equal(two.target.reorder_point_pcs,'10');assert.equal(two.target.target_pcs,'24')
  assert.equal(two.demand_estimate.basis,'SELECTED_MANUAL_ASSUMPTION')
  assert.equal(zero.target.reorder_point_pcs,'0');assert.equal(zero.target.target_pcs,'0')
  assert.equal(zero.target.status,'SCENARIO');assert.equal(a.history.find(x=>x.target_key===zero.target_key).available_days,0)
  return{selected_mean2_exact_native_point10_target24:true,selected_zero_known_despite_no_available_days:true}
})
await test('OW10_INPUTS_POSTED_REVERSED_AND_RETURN_GROSS_RULE_SAME',async()=>{
  const source=fixture();source.facts.returns.push({id:id(210),return_id:id(211),sale_item_id:id(200),qty_pcs:'4',physical_at:'2026-10-01T02:00:00Z'})
  source.facts.return_journals.push({id:id(212),return_id:id(211),posting_at:'2026-10-01T02:00:00Z',reversal_of_id:null})
  const a=await invoke(source),b=await whole(source);assert.deepEqual(a.history,b.history.rows)
  const first=a.history.find(x=>x.target_key.startsWith(id(1)));assert.equal(first.gross_observed_pcs,'10')
  assert.equal(first.days.find(x=>x.date==='2026-09-24').returned_pcs,'4')
  source.facts.sale_journals.push({id:id(220),sale_id:id(201),posting_at:'2026-10-02T02:00:00Z',
    transaction_date:'2026-10-02',reversal_of_id:id(202)})
  const reversed=await invoke(source);assert.deepEqual(reversed.history,(await whole(source)).history.rows)
  assert.equal(reversed.history.find(x=>x.target_key.startsWith(id(1))).gross_observed_pcs,'0')
  return{return4_not_subtracted_from_gross10:true,actual_journal_inverse_removes_gross:true,whole_history_equal_on_both:true}
})
await test('OW10_INPUTS_MULTIPLE_CHUNKS_KEEP_EVERY_PRODUCT_AND_DAY',async()=>{
  const source=fixture();source.facts.products=Array.from({length:420},(_,i)=>product(i+1));source.facts.sales=[];source.facts.sale_journals=[]
  source.facts.stock=source.facts.products.map((p,i)=>movement(i+10000,i+1,'100','2026-09-20T00:00:00Z'))
  source.profiles=source.facts.products.map((p,i)=>profile(i+1,'0'))
  const a=await invoke(source),b=await whole(source);assert.equal(a.history.length,420);assert.equal(a.targets.length,420)
  assert.deepEqual(a.history,b.history.rows);assert.deepEqual(a.current_stock,b.current_stock)
  assert.equal(a.history.reduce((n,r)=>n+r.days.length,0),12600)
  return{controlled_products:420,complete_days:12600,chunks:2,whole_history_full_JSON_equal:true,factory_SLA:false}
})
await test('OW10_INPUTS_CHANGED_PERIOD_SOURCE_UNKNOWN_CAPS_AND_ACL',async()=>{
  const source=fixture(),a=await invoke(source),q={...query,from_date:'2026-09-24'},changed=await invoke(source,q)
  assert.deepEqual(changed.history,(await whole(source,q)).history.rows);assert.notDeepEqual(changed.query,a.query)
  source.profiles[0].config.lead_days='4';assert.notEqual((await invoke(source)).source_hash,a.source_hash)
  await assert.rejects(()=>invoke({...source,status:'INCOMPLETE'}),/CP7_PLANNING_CAPTURE_INCOMPLETE/)
  await assert.rejects(()=>invoke(source,{...query,through_date:'2026-10-23'}),/CP7_DEMAND_COMPLETE_DAYS_REQUIRED/)
  await assert.rejects(()=>invoke(source,{...query,scope:'FILTERED_VARIANT'}),/CP7_WIP_FIELDS/)
  const tooMany=structuredClone(source);tooMany.facts.products=Array.from({length:1400},(_,i)=>product(i+1))
  await assert.rejects(()=>invoke(tooMany,{...query,from_date:'2025-10-23'}),/CP7_PLANNING_HISTORY_GRID_LIMIT/)
  for(const role of['anon','authenticated','service_role']){
    const r=(await db.query("select has_schema_privilege($1,'cp7_reorder_inputs','USAGE')s,has_function_privilege($1,'cp7_reorder_inputs.history(jsonb,jsonb)','EXECUTE')f",[role])).rows[0]
    assert.equal(r.s,false);assert.equal(r.f,false)
  }
  return{changed_query_and_profile_visible:true,incomplete_future_and_full_grid_refused:true,private_only:true}
})
await test('OW10_POINTS_REVIEWED_PROFILE_EXACT_TARGET_AND_NO_DOUBLE_BUFFER',async()=>{
  const input=await invoke(fixture()),a=await points(input,lead('9'))
  for(const r of a.rows){
    assert.deepEqual(r.target,input.targets.find(t=>t.target_key===r.target_key).target)
    assert.equal(r.point_pcs,r.target.reorder_point_pcs);assert.equal(r.formula_point_pcs,r.point_pcs)
    assert.equal(r.lead_days,'3');assert.equal(r.lead_basis,'PROFILE');assert.equal(r.supply_alignment,'NATIVE_TARGET')
  }
  assert.deepEqual(a.rows.map(r=>r.point_pcs),['2','10','0'])
  await db.exec('set role cp7_capture');assert.deepEqual(await points(input,lead('9')),a);await db.exec('reset role')
  return{same_full_Native_target_JSON:true,reviewed_lead3_wins_over_measured9:true,
    profile_manual_mean_and_known_zero_respected:true,no_second_buffer:true,non_superuser:true}
})
await test('OW10_POINTS_UNREVIEWED_DEFAULTS_USE_NATIVE_AVAILABLE_HISTORY',async()=>{
  const source=fixture();source.profiles=source.profiles.map(p=>({...p,quality:'UNREVIEWED',profile_id:null,revision:'0',config:null}))
  const input=await invoke(source),a=await points(input),r=a.rows[0]
  assert.equal(r.source_kind,'NATIVE_HISTORY_WITH_EXISTING_DEFAULTS');assert.equal(r.available_days,'29')
  assert.equal(r.available_total_pcs,'10');assert.equal(r.lead_basis,'MEASURED')
  // Independent arithmetic: 10/29*3 +1.6449*(10/sqrt29)*sqrt3 =6.323..., ceil7.
  assert.equal(r.point_pcs,'7');assert.equal(r.target.inputs.review_days,'0')
  assert.equal(r.supply_alignment,'NEEDS_EXPLICIT_BINDING')
  assert.equal(a.rows[1].point_pcs,'0');assert.equal(a.rows[1].point_basis,'FORMULA')
  assert.equal(a.rows[2].point_pcs,null);assert.equal(a.rows[2].reason,'FEWER_THAN_14_NATIVE_AVAILABLE_DAYS')
  const missing=await points(input,[]);assert.equal(missing.rows[0].point_pcs,null);assert.equal(missing.rows[0].reason,'NO_PROVEN_LEAD_TIME')
  const measuredZero=await points(input,lead('0'));assert.equal(measuredZero.rows[0].point_pcs,'0')
  await assert.rejects(()=>points(input,lead('3','2')),/CP7_REORDER_LEAD_UNPROVEN/)
  return{exact_independent_point7_from29_Native_days:true,existing14_day95pct_rule_only:true,
    known_zero_not_unknown:true,default_only_not_claimed_full_production_target:true,insufficient_lead_never_guessed:true}
})
await test('OW10_POINTS_MANUAL_REPLACES_CLEARS_OR_REQUIRES_IDENTITY_REVIEW',async()=>{
  const input=await invoke(fixture()),manual={root_id:id(1),product_version_id:id(1),size_id:id(9000),revision:'1',reorder_point_pcs:'25'}
  const active=(await points(input,lead(),[manual])).rows[0]
  assert.equal(active.point_basis,'MANUAL');assert.equal(active.point_pcs,'25');assert.equal(active.formula_point_pcs,'2')
  assert.equal(active.target.target_pcs,'5');assert.equal(active.supply_alignment,'NEEDS_EXPLICIT_BINDING')
  const zero=(await points(input,lead(),[{...manual,reorder_point_pcs:'0'}])).rows[0];assert.equal(zero.point_pcs,'0');assert.equal(zero.manual_state,'ACTIVE')
  const cleared=(await points(input,lead(),[{...manual,reorder_point_pcs:null}])).rows[0]
  assert.equal(cleared.point_pcs,'2');assert.equal(cleared.manual_state,'CLEARED')
  const stale=(await points(input,lead(),[{...manual,product_version_id:id(999)}])).rows[0]
  assert.equal(stale.point_pcs,null);assert.equal(stale.reason,'MANUAL_POINT_VERSION_CHANGED');assert.equal(stale.manual_reference.reorder_point_pcs,'25')
  await assert.rejects(()=>points(input,lead(),[{...manual,reorder_point_pcs:'10000001'}]),/CP7_REORDER_MANUAL_RANGE/)
  return{manual25_replaces_formula2_without_changing_target5:true,manual_zero_and_clear_distinct:true,
    changed_product_version_does_not_silently_activate_formula:true,existing_manual_limit_retained:true}
})
await test('OW10_POINTS_POLICY_HASH_UNKNOWN_PROFILE_AND_CLOSED_SCOPE',async()=>{
  const input=await invoke(fixture()),a=await points(input)
  assert.notEqual((await points(input,lead('4'))).selection_hash,a.selection_hash)
  assert.notEqual((await points(input,lead(),[],{...defaults,service_level:'0.99'})).selection_hash,a.selection_hash)
  const oldProfile=structuredClone(input);oldProfile.targets[0].profile.quality='PHYSICAL_VERSION_CHANGED'
  const stale=(await points(oldProfile)).rows[0];assert.equal(stale.point_pcs,null);assert.equal(stale.reason,'PROFILE_IDENTITY_OR_VERSION_CHANGED')
  await assert.rejects(()=>points(input,lead(),[],{...defaults,window_days:'31'}),/CP7_REORDER_INPUT_PERIOD/)
  await assert.rejects(()=>points(input,lead(),[],{...defaults,service_level:'0.96'}),/CP7_REORDER_INPUT_POLICY/)
  const filtered=structuredClone(input);filtered.targets=filtered.targets.slice(0,1)
  await assert.rejects(()=>points(filtered),/CP7_REORDER_HISTORY_SCOPE_MISMATCH/)
  const mismatched=structuredClone(input);mismatched.targets[0].profile.product_version_id=id(999)
  await assert.rejects(()=>points(mismatched),/CP7_REORDER_TARGET_PRODUCT_BINDING/)
  for(const role of['anon','authenticated','service_role'])assert.equal((await db.query("select has_function_privilege($1,'cp7_reorder_inputs.points(jsonb,jsonb,jsonb,jsonb)','EXECUTE')f",[role])).rows[0].f,false)
  return{lead_and_defaults_in_selection_hash:true,stale_profile_unknown:true,closed_policy_period_identity_and_full_scope:true,private_only:true}
})
await test('OW10_SOURCE_ACTUAL_SQL_LEAD_SETTINGS_AND_NATIVE_CAPTURE_CLOCK',async()=>{
 await sourceFixture();const r=await serverSource()
 assert.equal(r.status,'COMPLETE');assert.equal(r.captured_at,r.native.captured_at);assert.deepEqual(r.query,query);assert.deepEqual(r.defaults,defaults)
 assert.deepEqual(r.leads,[{model_id:id(9001),lead_days:'4.00',lot_count:'5',group_count:'3'}])
 assert.deepEqual(r.manuals,[]);assert.equal(r.native.facts.products.length,3);assert.equal(r.native.facts.stock.length,5)
 assert.equal(r.native.facts.sales[0].qty_pcs,'10');assert.equal(r.native.facts.sale_journals[0].id,id(202))
 const compiled=await points(await invoke(r.native,r.query),r.leads,r.manuals,r.defaults)
 assert.equal(compiled.rows[0].lead_days,'3');assert.equal(compiled.rows[0].point_pcs,'2')
 await db.exec('set role cp7_capture');const again=await serverSource();await db.exec('reset role')
 assert.equal(again.context_hash,r.context_hash);assert.deepEqual(again.native.facts,r.native.facts)
 return{actual_Native_baseline_and_history_source_bodies:true,profile_and_identity_adapters_controlled:true,
  actual_SQL_median4_from5_lots3_groups:true,draft_reversed_future_and_nonproduction_lots_excluded:true,
  current_settings_defaults_actual_SQL:true,same_capture_clock_and_read_only_capture_role:true}
})
await test('OW10_SOURCE_LATEST_MANUAL_AS_OF_CAPTURE_AND_PROVEN_LEAD_GUARD',async()=>{
 await sourceFixture()
 for(const [revision,point,at]of[[1,'0','2026-10-21'],[2,'25','2026-10-22'],[3,'99','2026-10-24']])await db.query(`
  insert into cp7_stock_formula.manual_points(root_id,revision,size_id,product_version_id,reorder_point_pcs,reason,actor,request_id,request_hash,recorded_at)
  values($1,$2,$3,$1,$4,'CONTROLLED_FIXTURE',$5,$6,$7,$8)`,[id(1),revision,id(9000),point,id(999),id(15000+revision),'a'.repeat(64),at+'T00:00:00Z'])
 const r=await serverSource();assert.deepEqual(r.manuals,[{root_id:id(1),product_version_id:id(1),size_id:id(9000),revision:'2',reorder_point_pcs:'25'}])
 const p=await points(await invoke(r.native),r.leads,r.manuals,r.defaults);assert.equal(p.rows[0].point_pcs,'25')
 await db.query('update erp.cutting_groups set material_issue_posted=false where id=$1',[id(11003)])
 const two=await serverSource();assert.equal(two.leads[0].group_count,'2');assert.equal(two.leads[0].lead_days,null)
 assert.notEqual(two.context_hash,r.context_hash)
 return{latest_revision_at_Native_capture_only:true,future_manual_not_active:true,manual25_from_server_only:true,
  fewer_than3_issued_groups_not_proven_lead:true,source_change_changes_context_hash:true}
})
await test('OW10_SOURCE_CLOSED_CAP_INCOMPLETE_AND_ENGINE_CURRENTNESS',async()=>{
 await sourceFixture();const r=await serverSource();assert.match(r.engine_hash,/^[a-f0-9]{64}$/);assert.match(r.context_hash,/^[a-f0-9]{64}$/)
 assert.equal((await serverSource(1)).status,'INCOMPLETE')
 await assert.rejects(()=>serverSource(0),/CP7_REORDER_SOURCE_PRODUCT_BOUND/)
 await assert.rejects(()=>serverSource(5001),/CP7_REORDER_SOURCE_PRODUCT_BOUND/)
 const sql=await read('scripts/cp7_reorder_inputs/points.sql')
 await db.exec(sql.replace('create function ','create or replace function ').replaceAll('CP7_REORDER_INPUT_POLICY','CP7_REORDER_INPUT_POLICY_CONTROL'))
 const changed=await serverSource();assert.notEqual(changed.engine_hash,r.engine_hash);assert.notEqual(changed.context_hash,r.context_hash)
 await db.exec(sql.replace('create function ','create or replace function '));assert.equal((await serverSource()).context_hash,r.context_hash)
 return{existing5000_product_bound_not_raised:true,incomplete_source_not_empty_success:true,
  actual_catalog_code_in_engine_and_context_hash:true,exact_private_body_restored:true}
})
await test('OW10_READ_COMPLETE_NATIVE_FULL_INPUTS_AND_POINTS_EQUAL',async()=>{
 await sourceFixture();const r=await readPoints(),source=await serverSource();source.native.captured_at=r.captured_at
 const native=await invoke(source.native,r.query)
 assert.deepEqual(r.inputs,native)
 assert.deepEqual(r.points,await points(native,source.leads,source.manuals,source.defaults))
 assert.equal(r.native_capture_status,'COMPLETE');assert.equal(r.input_path,'COMPLETE_NATIVE_CAPTURE')
 await db.exec('set role cp7_capture');const again=await readPoints();await db.exec('reset role')
 assert.equal(again.context_hash,r.context_hash);assert.equal(again.points.selection_hash,r.points.selection_hash)
 await db.query('update erp.fg_stock_movements set qty_signed=qty_signed+1 where id=$1',[id(100)])
 assert.notEqual((await readPoints()).context_hash,r.context_hash)
 await assert.rejects(()=>readPoints(1),/CP7_REORDER_NON_STOCK_SOURCE_INCOMPLETE/)
 return{actual_history_source_and_baseline_source:true,full_input_and_point_JSON_equal:true,
  read_only_capture_role:true,clock_only_change_same_cache_key:true,visible_stock_change_new_key:true,
  incomplete_product_universe_refused:true}
})
await test('OW10_COMPILE_ONE_CLOSED_SNAPSHOT_NO_SECOND_DATABASE_READ',async()=>{
 await sourceFixture();const source=await serverSource()
 const compile=async s=>(await db.query('select cp7_reorder_inputs.compile($1::jsonb)v',[JSON.stringify(s)])).rows[0].v
 const original=await compile(source)
 await addMovement(movement(730,1,'3','2026-10-22T00:00:00Z'))
 assert.deepEqual(await compile(source),original)
 const fresh=await serverSource();assert.notEqual(fresh.context_hash,source.context_hash)
 assert.notEqual((await compile(fresh)).context_hash,original.context_hash)
 await assert.rejects(()=>compile({...source,client_values:{}}),/CP7_/)
 await assert.rejects(()=>compile({...source,captured_at:'2026-10-22T00:00:00Z'}),/CP7_REORDER_SOURCE_SNAPSHOT_BINDING/)
 return{exact_same_snapshot_same_full_result_after_DB_change:true,fresh_snapshot_changes_key:true,
  no_second_source_read_in_immutable_compile:true,closed_snapshot_and_clock_binding:true,
  cache_key_not_freshness_proof:true}
})
await test('OW10_READ_OVERFLOW_RETAINS_ALL_OTHER_NATIVE_COMPLETENESS_GUARDS',async()=>{
 await sourceFixture()
 // Explicit fault injection into the lower source, not a Native qualification:
 // compact stock is never allowed to excuse a second missing collection or
 // an identity/journal conflict. Restore the pinned real body in finally.
 const injected=fixture();injected.status='INCOMPLETE';injected.facts.stock=Array(50001).fill({})
 const controlledSource=`create or replace function cp7_planning.history_source_within(p_products integer)returns jsonb
  language sql stable security invoker set search_path=''set TimeZone='UTC'as $$select c from public.reorder_native_fixture$$;`
 const denied=[]
 await db.exec(controlledSource)
 try{
  const reject=async(name,change,pattern=/CP7_REORDER_NON_STOCK_SOURCE_INCOMPLETE/)=>{
   const c=structuredClone(injected);change(c)
   await db.query('update public.reorder_native_fixture set c=$1::jsonb',[JSON.stringify(c)])
   await assert.rejects(()=>readPoints(),pattern);denied.push(name)
  }
  await reject('SQL stock has fewer rows than raw capture',()=>{},/CP7_REORDER_STOCK_SNAPSHOT_MISMATCH/)
  for(const name of['sales','sale_journals','returns','return_journals'])await reject(name+' overflow',c=>{c.facts[name]=Array(50001).fill({})})
  await reject('duplicate current root',c=>{c.facts.products.push(c.facts.products[0])})
  await reject('ambiguous current commercial',c=>{c.facts.products[0].commercial=[{},{}]})
  await reject('ambiguous sold commercial',c=>{c.facts.sales[0].sold_commercial=[{},{}]})
  await reject('missing posted original journal',c=>{c.facts.sale_journals=[]})
  await reject('duplicate original journal',c=>{c.facts.sale_journals.push({...c.facts.sale_journals[0],id:id(90002)})})
  await reject('unknown Native status',c=>{c.status='UNKNOWN'})
 }finally{
  await db.exec(nativeSourceSQL.replace('create function ','create or replace function '))
  await db.query('update public.reorder_native_fixture set c=$1::jsonb',[JSON.stringify(fixture())])
 }
 const body=(await db.query("select prosrc from pg_proc where oid='cp7_planning.history_source_within(integer)'::regprocedure")).rows[0].prosrc
 assert.equal(createHash('sha256').update(body).digest('hex'),manifest.existing_body_sha256['cp7_planning.history_source_within(integer)'])
 return{fault_injected_denials:denied,Native_body_exactly_restored:true,Native_qualification:false}
})
let installer
await test('OW10_INPUTS_REAL_INSTALLER_22_AND_CALLER_DEPENDENCY_REFUSAL',async()=>{
  // Actual SQL caller declaration, controlled fixture; no Native transaction
  // or persisted ERP use is claimed for this stateless helper's boundary.
  await db.exec(`create function cp7_analysis_stage.local_reorder_inputs_consumer(jsonb,jsonb)returns jsonb
    language sql immutable as $$select cp7_reorder_inputs.history($1,$2)$$;
    alter function cp7_analysis_stage.local_reorder_inputs_consumer(jsonb,jsonb)owner to cp7_capture;`)
  installer=await stageAudit.afterUse()
  assert.equal(installer.catalog_groups,22);assert.equal(installer.apply_rollback_reapply_exact,true)
  assert.equal(installer.after_use_refused_before_first_DDL,true)
  return{apply_admit_inverse_reapply_all22_exact:true,actual_installed_SQL_caller_requires_removal_first:true,
    caller_guard_before_DDL:true,persisted_Native_use_qualified:false}
})
const readerAudit=await beginLocalStageAudit(db,'cp7_reorder_reader_stage')
let readerInstaller
await test('OW10_CACHE_FIRST_COMPILE_THEN_REUSE_WITH_FRESH_CAPTURE_ROLE',async()=>{
 await sourceFixture();const a=await readerSnapshot(),b=await readerSnapshot()
 assert.equal(a.cache_hit,false);assert.equal(b.cache_hit,true);assert.deepEqual(b.points,a.points)
 assert.equal(b.threshold_captured_at,a.threshold_captured_at);assert.equal(b.threshold_hash,a.threshold_hash)
 await db.exec('set role cp7_capture');const c=await readerSnapshot();await db.exec('reset role')
 assert.equal(c.cache_hit,true);assert.deepEqual(c.current_stock,b.current_stock)
 assert.equal(c.live_ROP_caller_changed,false)
 return{actual_private_cache_miss_then_hit:true,original_threshold_time_and_full_points_retained:true,
  fresh_current_stock_each_read:true,capture_role_only:true,live_ROP_caller_changed:false}
})
await test('OW10_CACHE_TODAY_STOCK_FRESH_WITHOUT_HISTORY_RECOMPILE',async()=>{
 const a=await readerSnapshot(),now=new Date(Date.now()-1000).toISOString()
 await addMovement(movement(740,1,'3',now))
 const b=await readerSnapshot();assert.equal(b.cache_hit,true);assert.equal(b.threshold_hash,a.threshold_hash)
 assert.notEqual(b.context_hash,a.context_hash);assert.equal(b.threshold_captured_at,a.threshold_captured_at)
 assert.equal(a.current_stock[0].native_available_pcs,'90');assert.equal(b.current_stock[0].native_available_pcs,'93')
 assert.deepEqual(b.points,a.points)
 return{today_stock90_to93_without_old_stock_reuse:true,full_threshold_points_unchanged:true,
  same_threshold_hash_different_current_source_hash:true,threshold_time_retained:true}
})
await test('OW10_CACHE_BACKDATE_PROFILE_AND_MANUAL_INVALIDATE_THRESHOLD',async()=>{
 const a=await readerSnapshot();await addMovement(movement(741,1,'2','2026-09-25T02:00:00Z'))
 const b=await readerSnapshot();assert.equal(b.cache_hit,false);assert.notEqual(b.threshold_hash,a.threshold_hash)
 await db.query(`update public.reorder_native_fixture set c=jsonb_set(c,'{profiles,1,config,daily_pcs}','"4"'::jsonb)`)
 const c=await readerSnapshot();assert.equal(c.cache_hit,false);assert.equal(c.points.rows[1].point_pcs,'20')
 await db.query(`insert into cp7_stock_formula.manual_points(root_id,revision,size_id,product_version_id,reorder_point_pcs,reason,actor,request_id,request_hash)
  values($1,1,$2,$1,25,'CONTROLLED_FIXTURE',$3,$4,$5)`,[id(1),id(9000),id(999),id(15099),'f'.repeat(64)])
 const d=await readerSnapshot();assert.equal(d.cache_hit,false);assert.equal(d.points.rows[0].point_pcs,'25')
 return{later_known_backdate_recompiled:true,profile_mean4_point20_recompiled:true,manual25_recompiled:true,
  no_stale_threshold_after_operational_or_policy_change:true}
})
await test('OW10_CACHE_HIT_STILL_REFUSES_RESERVATION_CORRUPTION_AND_INCOMPLETE_SCOPE',async()=>{
 await sourceFixture();await readerSnapshot();const before=(await db.query('select threshold_hash from cp7_reorder_reader.cache')).rows[0].threshold_hash
 const now=new Date(Date.now()-1000).toISOString()
 await addMovement({...movement(742,1,'-4',now),movement_type:'SALE_RESERVE'})
 await assert.rejects(()=>readerSnapshot(),/CP7_PLANNING_NATIVE_RESERVATION_MISMATCH/)
 assert.equal((await db.query('select threshold_hash from cp7_reorder_reader.cache')).rows[0].threshold_hash,before)
 await db.query('delete from erp.fg_stock_movements where id=$1',[id(742)])
 await db.query('insert into erp.products(id,identity_root_id)values($1,$2)',[id(799),id(1)])
 await assert.rejects(()=>readerSnapshot(),/CP7_REORDER_NON_STOCK_SOURCE_INCOMPLETE/)
 assert.equal((await db.query('select threshold_hash from cp7_reorder_reader.cache')).rows[0].threshold_hash,before)
 return{cached_threshold_never_bypasses_fresh_draft_stock_validation:true,duplicate_current_identity_refused:true,
  failed_read_keeps_cache_unchanged:true}
})
await test('OW10_CACHE_22_GROUPS_AND_USE_MARK_SURVIVES_CACHE_EVICTION',async()=>{
 await db.exec('delete from cp7_reorder_reader.cache')
 assert.equal((await db.query('select count(*)::integer n from cp7_reorder_reader.cache')).rows[0].n,0)
 assert.equal((await db.query('select count(*)::integer n from cp7_reorder_reader.use_marks')).rows[0].n,1)
 await assert.rejects(()=>db.exec('delete from cp7_reorder_reader.use_marks'),/CP7_REORDER_USE_MARK_IMMUTABLE/)
 readerInstaller=await readerAudit.afterUse()
 assert.equal(readerInstaller.catalog_groups,22);assert.equal(readerInstaller.apply_rollback_reapply_exact,true)
 assert.equal(readerInstaller.after_use_refused_before_first_DDL,true)
 return{actual_apply_admit_inverse_reapply22:true,cache_evicted_but_immutable_use_mark_retained:true,
  after_use_requires_backup_restore_before_DDL:true,Native_or_A_chain:false}
})
// Pure consumer over actual Native points/net/project kernels. This does not
// install compute, a public facade, an Auth journey or a fresh-job adapter.
await db.exec(block(formula,'cp7_stock_formula.z'))
await db.exec(await read('scripts/cp7_production_stage/sql/cp7_baseline__net.sql'))
await db.exec(await read('scripts/cp7_reorder_supply/projection.sql'))
await db.exec(await read('scripts/cp7_reorder_caller_stage/evaluate.sql'))
const evaluate=async(v,supply)=>(await db.query('select cp7_reorder_caller.evaluate($1::jsonb,$2::jsonb)v',
 [JSON.stringify(v),JSON.stringify(supply)])).rows[0].v
const unknownSupply=v=>({contract_version:'cp7.reorder-supply-cache.v1',checked_at:v.captured_at,query:v.query,
 status:'UNKNOWN',reason:'GLOBAL_ANALYSIS_NEEDED',job:null,projection:null,apply_enabled:false,production_go:false})
const lowSnapshot=async()=>{
 await sourceFixture();const now=new Date(Date.now()-1000).toISOString()
 await addMovement(movement(750,1,'-90',now));await addMovement(movement(751,2,'-50',now))
 return readerSnapshot()
}
const projectedSupply=async(v,{kind='DIRECTED',quantity='4',eta=2,alloc='SCENARIO',split=null}={})=>{
 const snapshotId=id(9800),refs=[{kind:'CONTROLLED_GLOBAL_POSITION',id:'fixture',revision:'1'}]
 const at=async days=>(await db.query("select cp7_planning.utc($1::timestamptz+$2::numeric*interval'1 day')v",[v.captured_at,String(days)])).rows[0].v
 const etaAt=await at(eta),budget={physical_key:'CUT:FIXTURE',snapshot_id:snapshotId,size_id:id(9000),
  projected_good_pcs:quantity,eta:etaAt,eligible:true}
 const targets=[]
 for(let i=0;i<v.points.rows.length;i++){
  const p=v.points.rows[i],target={target_key:p.target_key,size_id:p.size_id,reorder_point_pcs:p.formula_point_pcs,
   target_pcs:p.target.target_pcs,available_fg_pcs:v.current_stock.find(s=>s.target_key===p.target_key).native_available_pcs,
   lead_deadline:await at(p.lead_days),deadline:await at(String(Number(p.lead_days)+Number(p.target.inputs.review_days))),supplies:[],refs}
  const qty=split?split[i]:i===0?quantity:null
  if(qty!==null||(!split&&i===0))target.supplies.push({physical_key:budget.physical_key,snapshot_id:snapshotId,target_key:p.target_key,
   size_id:p.size_id,kind,qty_pcs:qty,eta:etaAt,eligible:true,refs})
  targets.push(target)
 }
 const input={contract_version:'cp7.reorder-supply-input.v1',snapshot_id:snapshotId,scope_id:'GLOBAL_NATIVE_PLANNING',scenario_id:id(9801),
  captured_at:v.captured_at,checked_at:v.captured_at,source_hash:'a'.repeat(64),current_source_hash:'a'.repeat(64),source_state:'CURRENT',
  complete_scope:true,wip_status:'COMPLETE',allocation_status:alloc,query:v.query,expected_query:v.query,budgets:[budget],targets,refs}
 const projection=(await db.query('select cp7_reorder_supply.project($1::jsonb)v',[JSON.stringify(input)])).rows[0].v
 return{contract_version:'cp7.reorder-supply-cache.v1',checked_at:v.captured_at,query:v.query,status:projection.status,
  reason:projection.reason,job:{state:'DONE',run_id:id(9802),captured_at:v.captured_at,targets_total:targets.length},projection,apply_enabled:false,production_go:false}
}
await test('OW10_CALLER_UNKNOWN_WIP_KEEPS_FREE_STOCK_ALERT_AND_KNOWN_ZERO',async()=>{
 const v=await lowSnapshot(),r=await evaluate(v,unknownSupply(v))
 assert.equal(r.rows[0].state,'AT_OR_BELOW');assert.equal(r.rows[1].state,'AT_OR_BELOW');assert.equal(r.rows[2].state,'NO_POINT')
 assert.equal(r.rows[0].wip_pcs,null);assert.equal(r.rows[0].projection.base_position_pcs,null)
 assert.equal(r.rows[2].point,'0');assert.equal(r.rows[2].basis,'FORMULA')
 assert.ok(r.rows.every(x=>x.projection.raw_WIP_credited===false&&x.projection.candidate_mutes_alert===false))
 return{unknown_not_zero:true,free_stock_alert_not_waiting_for_analysis:true,known_profile_zero_preserved:true,public_caller_installed:false}
})
await test('OW10_CALLER_ONE_DIRECTED_GOOD_BUDGET_NOT_COPIED_TO_SAME_MODEL_VARIANT',async()=>{
 const v=await lowSnapshot(),r=await evaluate(v,await projectedSupply(v))
 assert.equal(r.rows[0].wip_pcs,'4');assert.equal(r.rows[0].state,'ABOVE')
 assert.equal(r.rows[1].wip_pcs,'0');assert.equal(r.rows[1].state,'AT_OR_BELOW')
 assert.equal(r.rows[0].projection.production_base_pcs,'1');assert.equal(r.rows[0].projection.target_pcs,'5')
 return{actual_Native_net_and_global_project:true,directed4_once_not_copied_to_other_variant:true,
  base_state_and_target5_quantity1_from_same_kernel:true,Native_job_reader_not_claimed:true}
})
await test('OW10_CALLER_GLOBAL_CANDIDATES_SEPARATE_NEVER_MUTE_BASE_ALERT',async()=>{
 const v=await lowSnapshot(),s=await projectedSupply(v,{kind:'ALLOCATED_CANDIDATE',quantity:'7',split:['3','4',null]}),r=await evaluate(v,s)
 assert.equal(r.rows[0].wip_pcs,'0');assert.equal(r.rows[0].projection.candidate_pcs,'3')
 assert.equal(r.rows[1].projection.candidate_pcs,'4');assert.equal(r.rows[0].state,'AT_OR_BELOW')
 assert.equal(r.rows[0].projection.conditional_position_pcs,'3');assert.equal(r.rows[0].projection.candidate_mutes_alert,false)
 assert.equal(BigInt(r.rows[0].projection.candidate_pcs)+BigInt(r.rows[1].projection.candidate_pcs),7n)
 const partial=await evaluate(v,await projectedSupply(v,{alloc:'UNKNOWN'}))
 assert.equal(partial.rows[0].wip_pcs,'4');assert.equal(partial.rows[0].projection.candidate_pcs,null)
 return{global_candidate_budget7_split3_and4:true,conditional_position_only:true,base_alert_still_open:true,
  proven_directed_kept_when_candidate_allocation_unknown:true}
})
await test('OW10_CALLER_LATE_GOOD_AT_TARGET_EXCLUDED_FROM_TRIGGER_AND_UNKNOWN_YIELD',async()=>{
 const v=await lowSnapshot(),late=await evaluate(v,await projectedSupply(v,{quantity:'7',eta:5}))
 assert.equal(late.rows[0].wip_pcs,'0');assert.equal(late.rows[0].state,'AT_OR_BELOW')
 assert.equal(late.rows[0].projection.production_base_pcs,'0')
 const unknown=await evaluate(v,await projectedSupply(v,{quantity:null}))
 assert.equal(unknown.rows[0].wip_pcs,null);assert.equal(unknown.rows[0].state,'AT_OR_BELOW')
 return{ETA5_excluded_from_lead3_included_in_target10:true,unknown_good_not_raw_PCS_or_100percent_yield:true,free_alert_preserved:true}
})
await test('OW10_CALLER_MANUAL_TRIGGER25_DOES_NOT_INVENT_TARGET25',async()=>{
 const v=await lowSnapshot();v.points.rows[0].point_pcs='25';v.points.rows[0].point_basis='MANUAL';v.points.rows[0].manual_state='ACTIVE'
 v.points.rows[0].manual_reference={root_id:id(1),product_version_id:id(1),size_id:id(9000),revision:'1',reorder_point_pcs:'25'}
 const r=await evaluate(v,await projectedSupply(v))
 assert.equal(r.rows[0].point,'25');assert.equal(r.rows[0].wip_pcs,'4');assert.equal(r.rows[0].state,'AT_OR_BELOW')
 assert.equal(r.rows[0].projection.target_pcs,'5');assert.equal(r.rows[0].projection.production_base_pcs,'1')
 return{manual25_compares_same_lead_position4:true,full_target5_unchanged:true,no_point_above_target_kernel_call:true,no_silent_target_bump:true}
})
await test('OW10_CALLER_FRESH_FREE_AND_HORIZON_BINDING_REFUSE_OLD_SUPPLY_CREDIT',async()=>{
 const v=await lowSnapshot(),s=await projectedSupply(v),changed=structuredClone(v)
 changed.current_stock[0].native_available_pcs='1'
 const a=await evaluate(changed,s);assert.equal(a.rows[0].wip_status,'UNKNOWN');assert.equal(a.rows[0].state,'AT_OR_BELOW')
 assert.equal(a.rows[0].wip_reason,'CURRENT_TARGET_STOCK_OR_HORIZON_CHANGED')
 const lead=structuredClone(v);lead.points.rows[0].lead_days='4';lead.points.rows[0].target.inputs.lead_days='4'
 const b=await evaluate(lead,s);assert.equal(b.rows[0].wip_pcs,null);assert.equal(b.rows[0].state,'AT_OR_BELOW')
 return{different_live_free_rejects_cached_position:true,different_lead_rejects_cached_ETA:true,free_alert_still_computed:true}
})
await test('OW10_CALLER_EXACT_POINT_ABOVE_JS_SAFE_INTEGER_AND_FULL_SCOPE_BEFORE_ACTIVE_FILTER',async()=>{
 await sourceFixture();await db.query(`update public.reorder_native_fixture set c=jsonb_set(jsonb_set(c,'{profiles,0,config,daily_pcs}','"2000000000000000"'::jsonb),'{profiles,0,config,mean_mode}','"SELECTED_MANUAL"'::jsonb)`)
 const v=await readerSnapshot(),r=await evaluate(v,unknownSupply(v));assert.equal(r.rows[0].point,'10000000000000000')
 assert.equal(r.rows[0].formula_point,'10000000000000000')
 const low=await lowSnapshot(),s=await projectedSupply(low),inactive=structuredClone(low);inactive.products[1].is_active=false
 const a=await evaluate(inactive,s);assert.equal(a.rows.length,2);assert.equal(a.rows[0].wip_pcs,'4')
 const missing=structuredClone(s);missing.projection.rows.splice(1,1)
 await assert.rejects(()=>evaluate(inactive,missing),/CP7_REORDER_EVALUATE_SUPPLY_SCOPE/)
 return{exact_decimal_point_10000000000000000:true,no_JS_number_or_int32_cast:true,
  complete_global_scope_validated_before_active_filter:true,filtered_projection_refused:true}
})
await test('OW10_STOCK_SUMMARY_FULL_NATIVE_AVAILABILITY_AND_BOTH_CLOCKS',async()=>{
 await sourceFixture();const r=await stockSummary(),source={...fixture(),captured_at:r.captured_at}
 const expected=(await db.query('select cp7_planning.history_availability($1::jsonb,$2::jsonb)v',[JSON.stringify(source),JSON.stringify(query)])).rows[0].v
 assert.deepEqual(r.availability,expected);assert.equal(r.raw_rows_read,5)
 const current=(await whole(source)).current_stock
 for(const row of r.current_stock){const native=current.find(x=>x.target_key===row.target_key)
  assert.equal(row.free_pcs,native.native_available_pcs);assert.equal(row.physical_pcs,native.availability.inputs.fg_pcs)
 }
 for(const m of[{...movement(700,1,'999','2026-10-24T00:00:00Z'),system_created_at:'2026-10-22T00:00:00Z'},
   {...movement(701,1,'999','2026-10-22T00:00:00Z'),system_created_at:'2026-10-24T00:00:00Z'}])await addMovement(m)
 assert.deepEqual(await stockSummary(),r)
 await db.exec('set role cp7_capture');assert.deepEqual(await stockSummary(),r);await db.exec('reset role')
 return{complete_actual_Native_availability_JSON_equal:true,current_free_and_physical_same:true,
  future_physical_and_later_known_rows_both_excluded:true,non_superuser_read:true,canonical_Native_clock:true}
})
await test('OW10_STOCK_SUMMARY_RESERVATION_INVERSE_AND_INTRADAY_UNKNOWN',async()=>{
 await sourceFixture();const source=fixture()
 const reserve={...movement(710,1,'-4','2026-10-20T03:00:00Z'),movement_type:'SALE_RESERVE'}
 await addMovement(reserve);source.facts.stock.push(reserve)
 source.facts.sales.push({id:id(711),sale_id:id(712),root_id:id(1),size_id:id(9000),qty_pcs:'4',status:'DRAFT',revision:'1',
  sale_date:'2026-10-20T03:00:00Z',created_at:'2026-10-20T03:00:00Z',updated_at:'2026-10-20T03:00:00Z',sold_commercial:[]})
 let r=await stockSummary();source.captured_at=r.captured_at
 let native=await whole(source);assert.equal(r.current_stock[0].free_pcs,'86');assert.equal(r.current_stock[0].physical_pcs,'90')
 assert.equal(native.current_stock[0].native_available_pcs,'86')
 const inverse={...movement(713,1,'4','2026-10-21T03:00:00Z'),reversal_of_id:reserve.id}
 await addMovement(inverse);source.facts.stock.push(inverse);source.facts.sales.at(-1).status='CANCELLED'
 r=await stockSummary();native=await whole(source);assert.equal(r.current_stock[0].physical_pcs,'90');assert.equal(native.current_stock[0].native_available_pcs,'90')
 for(const m of[movement(714,1,'-100','2026-10-18T01:00:00Z',1),movement(715,1,'100','2026-10-18T02:00:00Z',2)]){
  await addMovement(m);source.facts.stock.push(m)
 }
 r=await stockSummary();assert.deepEqual(r.availability,(await db.query('select cp7_planning.history_availability($1::jsonb,$2::jsonb)v',
  [JSON.stringify(source),JSON.stringify(query)])).rows[0].v)
 assert.equal(r.availability.find(x=>x.target_key.startsWith(id(1))&&x.date==='2026-10-18').state,'UNKNOWN')
 return{reservation_subtracted_once_inverse_excluded_from_physical:true,
  negative_intraday_state_UNKNOWN_never_zero:true,full_Native_availability_JSON_equal:true}
})
await test('OW10_STOCK_SUMMARY_202000_ROWS_2000_PRODUCTS_NO_TRUNCATION',async()=>{
 await db.exec('truncate erp.products,erp.fg_stock_movements')
 const products=Array.from({length:2000},(_,i)=>product(i+1))
 await db.query('insert into erp.products(id,identity_root_id)select (p->>\'id\')::uuid,(p->>\'root_id\')::uuid from jsonb_array_elements($1::jsonb)p',[JSON.stringify(products)])
 await db.exec(`insert into erp.fg_stock_movements(id,product_id,qty_signed,physical_at,system_created_at,quality_grade,movement_type,reversal_of_id,book_order)
  select md5('opening'||p.id::text)::uuid,p.id,800,'2026-06-15T00:00:00Z','2026-06-15T00:00:00Z','GRADE_A','OPENING',null,1 from erp.products p;
  insert into erp.fg_stock_movements(id,product_id,qty_signed,physical_at,system_created_at,quality_grade,movement_type,reversal_of_id,book_order)
  select md5(p.id::text||':'||g::text)::uuid,p.id,-(1+g%6),'2026-10-23T00:00:00Z'::timestamptz-g*interval'1 day'-interval'2 hours',
   '2026-10-22T00:00:00Z','GRADE_A','SALE',null,g+1 from erp.products p cross join generate_series(1,100)g;`)
 const t=performance.now(),r=await stockSummary(products),ms=Math.round(performance.now()-t)
 assert.equal(r.raw_rows_read,202000);assert.equal(r.current_stock.length,2000);assert.equal(r.availability.length,60000)
 assert.ok(r.availability.every(x=>x.state==='AVAILABLE'))
 const free=String(800-Array.from({length:100},(_,i)=>1+(i+1)%6).reduce((a,b)=>a+b,0))
 assert.ok(r.current_stock.every(x=>x.free_pcs===free&&x.physical_pcs===free))
 assert.equal(r.raw_rows_truncated,false);assert.equal(r.Native_capture_status_overridden,false)
 return{controlled_SQL_rows:202000,products:2000,complete_days:60000,all_free_pcs:free,
  local_SQL_ms:ms,no_source_row_sampled:true,Native_Auth_or_factory_SLA:false}
})
await test('OW10_READ_202000_SQL_ROWS_FULL_NATIVE_HISTORY_TARGETS_AND_POINTS',async()=>{
 // Reuse the complete 202000-row SQL fixture above. These products have a
 // genuinely old test created_at, so Native knowledge covers the whole grid.
 await db.exec('truncate erp.sales_items,erp.sales_headers,erp.journal_entries')
 const source=fixture();source.profiles=Array.from({length:2000},(_,i)=>profile(i+1,'0'))
 await db.query('update public.reorder_native_fixture set c=$1::jsonb',[JSON.stringify(source)])
 const raw=await serverSource();assert.equal(raw.status,'INCOMPLETE');assert.equal(raw.native.facts.stock.length,50001)
 const t=performance.now(),r=await readPoints(),ms=Math.round(performance.now()-t)
 assert.equal(r.native_capture_status,'INCOMPLETE');assert.equal(r.input_path,'COMPLETE_SQL_STOCK_SUMMARY_RAW_NATIVE_INCOMPLETE')
 assert.equal(r.complete_stock_raw_rows_read,202000);assert.equal(r.inputs.history.length,2000)
 assert.equal(r.inputs.targets.length,2000);assert.equal(r.inputs.current_stock.length,2000);assert.equal(r.points.rows.length,2000)
 assert.ok(r.inputs.history.every(x=>x.available_days===30&&x.days.length===30&&x.gross_observed_pcs==='0'))
 assert.ok(r.inputs.current_stock.every(x=>x.native_available_pcs==='450'))
 assert.ok(r.inputs.targets.every(x=>x.target.reorder_point_pcs==='0'&&x.target.target_pcs==='0'))
 assert.ok(r.points.rows.every(x=>x.point_pcs==='0'&&x.available_days==='30'&&x.lead_basis==='PROFILE'))
 assert.notEqual(r.inputs.source_hash,raw.context_hash)
 const outside=(await db.query('select id from erp.fg_stock_movements order by id desc limit 1')).rows[0].id
 assert.ok(!raw.native.facts.stock.some(m=>m.id===outside))
 await db.query('update erp.fg_stock_movements set qty_signed=qty_signed+1 where id=$1',[outside])
 const changed=await serverSource();assert.deepEqual(changed.native.facts.stock,raw.native.facts.stock)
 assert.notEqual(changed.stock_summary.data_hash,raw.stock_summary.data_hash);assert.notEqual(changed.context_hash,raw.context_hash)
 const wrong=structuredClone(raw);wrong.stock_summary.captured_at='2026-10-22T00:00:00Z'
 await assert.rejects(()=>db.query('select cp7_reorder_inputs.compile($1::jsonb)',[JSON.stringify(wrong)]),/CP7_REORDER_STOCK_SNAPSHOT_MISMATCH/)
 return{actual_Native_source_cap_still50001:true,Native_status_still_INCOMPLETE:true,SQL_rows:202000,
  full_targets:2000,full_history_days:60000,full_points:2000,free450_exact:true,known_zero_profile_not_unknown:true,
  local_full_pipeline_ms:ms,outside_raw_prefix_change_invalidates_context:true,summary_clock_binding_refused:true,
  Native_Auth_or_factory_SLA:false,live_ROP_caller_changed:false}
})
await test('OW10_CACHE_2000_POINTS_WARM_CURRENT_STOCK_WITHOUT_HISTORY_RECOMPILE',async()=>{
 const coldStart=performance.now(),a=await readerSnapshot(),coldMs=Math.round(performance.now()-coldStart)
 const warmStart=performance.now(),b=await readerSnapshot(),warmMs=Math.round(performance.now()-warmStart)
 assert.equal(a.cache_hit,false);assert.equal(b.cache_hit,true);assert.equal(b.points.rows.length,2000)
 assert.deepEqual(b.points,a.points);assert.deepEqual(b.current_stock,a.current_stock)
 assert.equal(b.threshold_captured_at,a.threshold_captured_at)
 const now=new Date(Date.now()-1000).toISOString();await addMovement(movement(79999,1,'1',now))
 const c=await readerSnapshot();assert.equal(c.cache_hit,true);assert.equal(c.threshold_hash,b.threshold_hash)
 const before=b.current_stock.find(x=>x.root_id===id(1)),after=c.current_stock.find(x=>x.root_id===id(1))
 assert.equal(BigInt(after.native_available_pcs),BigInt(before.native_available_pcs)+1n)
 assert.equal(c.points.rows.length,2000);assert.deepEqual(c.points,b.points)
 return{complete_points_and_current_stock:2000,actual_history_cache_hit:true,
  cold_local_ms:coldMs,warm_local_ms:warmMs,today_stock_change_still_fresh_without_history_recompute:true,
  Native_Auth_or_factory_SLA:false,live_ROP_caller_changed:false}
})
await test('OW10_STOCK_SUMMARY_SCOPE_REFUSED_AND_DATA_HASH_EXCLUDES_ONLY_CLOCK',async()=>{
 await sourceFixture();const a=await stockSummary(),b=await stockSummary(fixture().facts.products,'2026-10-23T00:01:00Z')
 assert.notEqual(a.captured_at,b.captured_at);assert.equal(a.data_hash,b.data_hash)
 await addMovement(movement(720,1,'3','2026-10-22T00:00:00Z'))
 assert.notEqual((await stockSummary()).data_hash,a.data_hash)
 await assert.rejects(()=>stockSummary(fixture().facts.products,clock,{...query,through_date:'2026-10-23'}),/CP7_REORDER_STOCK_SCOPE_BOUND/)
 await assert.rejects(()=>stockSummary(Array.from({length:1400},(_,i)=>product(i+1)),clock,{...query,from_date:'2025-10-23'}),/CP7_REORDER_STOCK_SCOPE_BOUND/)
 return{clock_only_change_not_data_change:true,actual_visible_stock_change_changes_hash:true,
  existing_grid_and_closed_day_caps_preserved:true,not_a_complete_Native_capture_claim:true}
})
const report={classification:'LOCAL_ACTUAL_NATIVE_HISTORY_AND_STAGED_TARGET_KERNELS_CONTROLLED_SOURCE_NOT_NATIVE_OR_LIVE_ROP',
  status:results.every(x=>x.status==='PASS')?'PASS':'FAIL',passed:results.filter(x=>x.status==='PASS').length,total:results.length,
  sql_sha256:createHash('sha256').update(await read('scripts/cp7_reorder_inputs/history.sql')).digest('hex'),
  points_sql_sha256:createHash('sha256').update(await read('scripts/cp7_reorder_inputs/points.sql')).digest('hex'),results,
  source_sql_sha256:createHash('sha256').update(await read('scripts/cp7_reorder_inputs/source.sql')).digest('hex'),
  stock_sql_sha256:createHash('sha256').update(await read('scripts/cp7_reorder_inputs/stock.sql')).digest('hex'),
  read_sql_sha256:createHash('sha256').update(await read('scripts/cp7_reorder_inputs/read.sql')).digest('hex'),
  reader_cache_sql_sha256:createHash('sha256').update(await read('scripts/cp7_reorder_reader_stage/cache.sql')).digest('hex'),
  caller_evaluate_sql_sha256:createHash('sha256').update(await read('scripts/cp7_reorder_caller_stage/evaluate.sql')).digest('hex'),
  installer,reader_installer:readerInstaller,
  ROP_caller_changed:false,full_A_chain_qualified:false,production_go:false}
await mkdir('docs/cp7/d17-14/ow10',{recursive:true})
await writeFile('docs/cp7/d17-14/ow10/local-reorder-inputs.json',JSON.stringify(report,null,2)+'\n')
console.log(JSON.stringify(report,null,2));await db.close();if(report.status!=='PASS')process.exitCode=1
