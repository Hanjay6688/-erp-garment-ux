// Exact captured BC/service + exact unchanged BE/HPP functions. All other
// Native/Auth/material/journal entrypoints are explicit fixture.sql doubles.
// This is local SQL evidence, NEVER actual Native financial qualification.
import {readFileSync,writeFileSync}from'node:fs';
import {createHash}from'node:crypto';
import {execFileSync}from'node:child_process';
import {dirname,resolve}from'node:path';
import {fileURLToPath}from'node:url';
import assert from'node:assert/strict';
const here=dirname(fileURLToPath(import.meta.url)),product=resolve(here,'..');
const runtime=process.env.F04_PGLITE_MODULE;
assert(runtime,'F04_PGLITE_MODULE explicit pinned local runtime required; no green skip');
const {PGlite}=await import(runtime),db=new PGlite();
const sha=x=>createHash('sha256').update(x).digest('hex');
const original=JSON.parse(readFileSync(resolve(here,'NATIVE_UNCHANGED.json')));
for(const pin of Object.values(original.functions))assert.equal(sha(pin.definition),pin.sha256);
const patched=JSON.parse(execFileSync('python',['-c',`import importlib.util,json,pathlib
p=pathlib.Path(${JSON.stringify(resolve(product,'recovery_delta.py'))})
s=importlib.util.spec_from_file_location('local_recovery_delta',p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
print(json.dumps(m.patched({k:(p.parent/v['path']).read_text()for k,v in m.profile()['captures'].items()})))`],{encoding:'utf8'}));
const before={};for(const sig of Object.keys(patched))before[sig]=readFileSync(resolve(product,JSON.parse(readFileSync(resolve(product,'recovery_profile.json'))).captures[sig].path),'utf8');
const u=n=>`10000000-0000-4000-8000-${String(n).padStart(12,'0')}`;
const ids={c:u(11),c2:u(12),root:u(21),root2:u(22),dest:u(31),dest2:u(32),a:u(41),a2:u(42),lot:u(51),out:u(52),material:u(61),loc:u(62),group:u(1)};
const literal=x=>`'${JSON.stringify(x).replaceAll("'","''")}'::jsonb`;
const scalar=async sql=>Object.values((await db.query(`select ${sql}`)).rows[0])[0];
const results=[];const pass=(id,details={})=>results.push({id,status:'PASS',...details});
async function census(){
 const tables=(await db.query("select schemaname,tablename from pg_tables where schemaname in('erp','cp7_sku_conversion')order by 1,2")).rows;
 const rows={};for(const t of tables){const name=`${t.schemaname}.${t.tablename}`;rows[name]=await scalar(`coalesce((select jsonb_agg(to_jsonb(r)order by to_jsonb(r)::text)from ${name} r),'[]'::jsonb)::text`);}
 const seq={};for(const s of(await db.query("select schemaname,sequencename from pg_sequences where schemaname in('erp','cp7_sku_conversion')order by 1,2")).rows){const name=`${s.schemaname}.${s.sequencename}`;seq[name]=(await db.query(`select last_value::text,is_called from ${name}`)).rows[0];}
 const session=(await db.query("select current_user,session_user,current_setting('search_path')search_path,current_setting('TimeZone')timezone,current_setting('app.change_reason',true)reason")).rows[0];
 return{all_local_table_rows:rows,all_local_sequences:seq,session};
}
function payload(unit='30.03',qty='1'){return{lot_id:ids.lot,condition:'USABLE',qty,unit_value:unit,location_id:ids.loc,physical_at:'2026-10-20T10:00:00Z',reason:'Declared local managed recovery'};}
const command=(p=payload(),request=u(71))=>scalar(`erp.save_accessory_service_action_v1('VALUE_CUSTODY',${literal(p)},'${request}')`);
async function refuse(id,operation,pattern){
 const a=await census();await db.exec('savepoint local_refusal');let error;
 try{await operation();}catch(e){error=e;}
 await db.exec('rollback to savepoint local_refusal;release savepoint local_refusal');
 assert(error,`${id}: expected refusal`);assert.match(error.message,pattern);assert.equal(error.code,'P0001');
 const b=await census();assert.deepEqual(b,a,`${id}: all local table rows, sequences and session must be unchanged`);
 pass(id,{sqlstate:error.code,message:error.message,complete_local_census_equal:true,before_sha256:sha(JSON.stringify(a)),after_sha256:sha(JSON.stringify(b))});return error;
}
async function setup(avg='30.03',managed=true,po=false){
 await db.exec('begin');const poId=po?`'${u(80)}'`:'null',origin=po?'PRODUCTION':'OPENING';
 await db.exec(`insert into cp7_sku_conversion.groups_v1 values('${ids.group}');
 insert into erp.product_conversions values('${ids.c}','POSTED','${u(100)}','${u(101)}'),('${ids.c2}','POSTED','${u(100)}','${u(101)}');
 insert into erp.fg_lots values('${ids.root}',${poId},'${origin}',null,'${u(100)}'),('${ids.root2}',${poId},'${origin}',null,'${u(100)}'),
 ('${ids.dest}',${poId},'CONVERSION','${ids.root}','${u(101)}'),('${ids.dest2}',${poId},'CONVERSION','${ids.root2}','${u(101)}');
 insert into erp.product_conversion_allocations values('${ids.a}','${ids.c}','${ids.root}','${ids.dest}',2,0),('${ids.a2}','${ids.c2}','${ids.root2}','${ids.dest2}',2,0);
 insert into erp.be_conversion_sources_v1 values('${ids.c}','${ids.root}'),('${ids.c2}','${ids.root2}');
 insert into erp.be_conversion_returns_v1 values('${ids.c}','${ids.out}');
 insert into erp.hpp_versions(lot_id,version_no,cost_state,qty_basis_pcs,total_cost,is_current)values
 ('${ids.root}',1,'ORIGINAL',2,20.02,true),('${ids.root2}',1,'ORIGINAL',2,40.04,true),('${ids.dest}',1,'ORIGINAL',2,20.02,true),('${ids.dest2}',1,'ORIGINAL',2,40.04,true);
 insert into erp.materials values('${ids.material}',${avg},100,null);
 insert into erp.material_purchase_items values('${u(64)}','${u(65)}','${ids.material}');
 insert into erp.material_stock_movements(id,material_id,physical_at,qty_signed,unit_cost_snapshot,input_unit_cost,is_cost_recalculated,source_type,source_id)
 values('${u(63)}','${ids.material}','2026-10-10T00:00:00Z',100,${avg},${avg},true,'MATERIAL_PURCHASE_ITEM','${u(64)}');
 insert into erp.material_cost_history values('${ids.material}','${u(63)}','2026-10-10T00:00:00Z',0,100,0,${avg},100,${avg});
 insert into erp.bc_return_lots_v1 values('${ids.lot}',null,null,'${ids.out}','${ids.material}','PENDING','2026-10-19T00:00:00Z');`);
 if(managed)await db.exec(`insert into cp7_sku_conversion.members_v1 values('${ids.c}','${ids.group}',1),('${ids.c2}','${ids.group}',2);`);
}
async function end(){await db.exec('rollback');}
async function install(derived){for(const definition of Object.values(derived?patched:before))await db.exec(definition);}
try{
 await db.exec(readFileSync(resolve(here,'fixture.sql'),'utf8'));
 for(const name of['bc_set_policy_v1','bc_register_zone_v1','bc_internal_use_v1','bc_receive_return_v1','bc_inspect_v1','bc_credit_note_return_v1','bc_allocate_carry_v1','bc_dispose_stock_v1','bc_close_custody_v1','bc_count_post_v1','bc_resolve_variance_v1','bc_round_note_v1','bc_reverse_v1'])
  await db.exec(`create function erp.${name}(p jsonb,r uuid)returns jsonb language plpgsql as $$begin raise exception 'UNEXPECTED_LOCAL_UNRELATED_ACTION';end$$`);
 for(const name of['bc_move_post_v1','bc_customer_garment_v1'])await db.exec(`create function erp.${name}(a text,p jsonb,r uuid)returns jsonb language plpgsql as $$begin raise exception 'UNEXPECTED_LOCAL_UNRELATED_ACTION';end$$`);
 const nativeOrder=['erp.be_conversion_extra_v1(uuid)','erp.be_allocation_extra_v1(uuid)','erp.be_nonpo_admitted_v1(uuid)'];
 for(const sig of[...nativeOrder,...Object.keys(original.functions).filter(s=>!nativeOrder.includes(s))])await db.exec(original.functions[sig].definition);
 await db.exec(readFileSync(resolve(product,'recovery.sql'),'utf8'));
 await install(false);await setup();
 const oldA=await census();await db.exec('savepoint old_late_refusal');let oldError;
 try{await command();}catch(e){oldError=e;}
 await db.exec('rollback to savepoint old_late_refusal;release savepoint old_late_refusal');
 assert.match(oldError?.message||'',/^BE_RECOVERY_EXCEEDS_VALUE:/);const oldB=await census();
 assert.deepEqual(oldA.all_local_table_rows,oldB.all_local_table_rows);assert.deepEqual(oldA.session,oldB.session);
 assert.equal(BigInt(oldB.all_local_sequences['erp.audit_logs_id_seq'].last_value)-BigInt(oldA.all_local_sequences['erp.audit_logs_id_seq'].last_value),oldA.all_local_sequences['erp.audit_logs_id_seq'].is_called?5n:4n);
 pass('RETAINED_OLD_LATE_NATIVE_NEGATIVE_FIRST_FAILURE',{sqlstate:oldError.code,message:oldError.message,rows_restored:true,all_sequences_restored:false,before:oldA.all_local_sequences,after:oldB.all_local_sequences,declared_material_audit_double_count:4,exact_BE_journal_audit_double_count:1});await end();
 await install(true);await setup();await refuse('SAME_NEGATIVE_BEFORE_FIRST_EFFECT',()=>command(),/^BE_RECOVERY_EXCEEDS_VALUE:/);await end();
 for(const[unit,hpp,total]of[['20.01','0.005000','0.010000'],['20.02','0.000000','0.000000']]){
  await setup(unit);const response=await command(payload(unit));assert.equal(response.status,'POSTED');assert.equal(response.value,unit);
  assert.equal(await scalar(`(select hpp_per_pcs::text from erp.v_current_hpp where lot_id='${ids.dest}')`),hpp);
  assert.equal(await scalar(`(select total_cost::text from erp.v_current_hpp where lot_id='${ids.dest}')`),total);
  assert.equal(await scalar(`(select total_cost::text from erp.v_current_hpp where lot_id='${ids.dest2}')`),'40.040000');
  assert.equal(await scalar(`(select cached_stock_qty::text from erp.materials where id='${ids.material}')`),'101.000000');
  assert.equal(await scalar('(select count(*)::int from erp.be_conversion_cost_events_v1)'),1);
  const event=await scalar('(select target_amount::text from erp.be_conversion_cost_events_v1)');assert.equal(Number(event),-Number(unit));
  const a=await census();assert.deepEqual(await command(payload(unit)),response);assert.deepEqual(await census(),a);
  pass(unit==='20.01'?'UNDER_CAPACITY_POST_AND_EXACT_REPLAY':'EQUAL_CAPACITY_POST_AND_EXACT_REPLAY',{response,Native_BE_HPP_hpp:hpp,Native_BE_HPP_total:total,material_local_double_stock:'101.000000',local_census_replay_equal:true});
  await db.exec("update erp.test_actor set role_name='STAFF'");await refuse('CACHED_REPLAY_CURRENT_ROLE_'+unit,()=>command(payload(unit)),/OWNER_ADMIN_REQUIRED/);
  await db.exec("update erp.test_actor set role_name='OWNER',permissions=array['warehouse.accessory.view']");await refuse('CACHED_REPLAY_CURRENT_PERMISSION_'+unit,()=>command(payload(unit)),/ACCESS_DENIED/);
  await db.exec("update erp.test_actor set permissions=array['warehouse.accessory.view','finance.hpp.manage'],revoke_after_begin=true");await refuse('CACHED_REPLAY_AFTER_REQUEST_WAIT_DOUBLE_'+unit,()=>command(payload(unit)),/OWNER_ADMIN_REQUIRED/);
  await end();
 }
 await setup('30.03',false);const legacy=await census();await db.exec('savepoint legacy');let legacyError;
 try{await command();}catch(e){legacyError=e;}await db.exec('rollback to savepoint legacy;release savepoint legacy');
 assert.match(legacyError?.message||'',/^BE_RECOVERY_EXCEEDS_VALUE:/);assert.notDeepEqual((await census()).all_local_sequences,legacy.all_local_sequences);
 pass('UNMANAGED_NATIVE_PATH_UNCHANGED',{message:legacyError.message,retained_late_sequence_allocation:true});await end();
 await setup('20.02',false);assert.equal((await command(payload('20.02'))).status,'POSTED');pass('UNMANAGED_LAWFUL_NATIVE_POST_UNCHANGED');await end();
 // Current HPP rather than historical allocation cost: recost both current
 // source and its Native-normalized child, then admit the new capacity.
 await setup('24.00');await db.exec(`update erp.hpp_versions set total_cost=30 where lot_id in('${ids.root}','${ids.dest}');`);
 assert.equal((await command(payload('24.00'))).status,'POSTED');assert.equal(await scalar(`(select hpp_per_pcs::text from erp.v_current_hpp where lot_id='${ids.dest}')`),'3.000000');pass('CURRENT_RECOSTED_SOURCE_USED');await end();
 // Native sees every descendant and every unrelated branch in its scope.
 await setup('10.00');await db.exec(`insert into erp.product_conversions values('${u(13)}','POSTED','${u(101)}','${u(102)}');
 insert into erp.fg_lots values('${u(33)}',null,'CONVERSION','${ids.dest}','${u(102)}');insert into erp.be_conversion_sources_v1 values('${u(13)}','${ids.dest}');
 insert into erp.product_conversion_allocations values('${u(43)}','${u(13)}','${ids.dest}','${u(33)}',1,-9);
 insert into erp.hpp_versions(lot_id,version_no,cost_state,qty_basis_pcs,total_cost,is_current)values('${u(33)}',1,'ADJUSTED',1,1.01,true);`);
 await refuse('DESCENDANT_NEGATIVE_BEFORE_ANY_AUDIT',()=>command(payload('10.00')),/^BE_RECOVERY_EXCEEDS_VALUE:/);await end();
 await setup('1.00');await db.exec(`update erp.product_conversion_allocations set conversion_cost_allocated=-50 where id='${ids.a2}';`);
 await refuse('UNRELATED_VISITED_NEGATIVE_BEFORE_ANY_AUDIT',()=>command(payload('1.00')),/^BE_RECOVERY_EXCEEDS_VALUE:/);await end();
 await setup('1.00');await db.exec(`update erp.fg_lots set lot_origin='OPENING'where id='${ids.dest2}';`);
 await refuse('UNRELATED_NATIVE_ORPHAN_BEFORE_ANY_AUDIT',()=>command(payload('1.00')),/^BE_NON_PO_LINEAGE_ORPHAN_OR_CYCLE/);await end();
 await setup('0.01');const half=await command(payload('0.01','0.5'));assert.equal(half.value,'0.01');
 assert.equal(await scalar(`(select hpp_per_pcs::text from erp.v_current_hpp where lot_id='${ids.dest}')`),'10.005000');pass('PENDING_HALF_CENT_NATIVE_ROUND_ONLY',{pending_recovery:'0.01',hpp:'10.005000'});await end();
 await setup('20.02',true,true);assert.equal((await command(payload('20.02'))).status,'POSTED');assert.equal(await scalar(`(select hpp_per_pcs::text from erp.v_current_hpp where lot_id='${ids.dest}')`),'0.000000');pass('EXACT_PO_NATIVE_PROPAGATION_EQUAL');await end();
 async function existingCost(amount='1.00'){
  await db.exec(`insert into erp.bc_documents_v1(id)values('${u(72)}');insert into erp.material_adjustments values('${u(73)}',${amount},'POSTED');
   insert into erp.material_adjustment_items(adjustment_id,material_id)values('${u(73)}','${ids.material}');
   insert into erp.bc_adjustment_purposes_v1 values('${u(73)}','${u(72)}','RECOVERY_VALUATION','${u(99)}');
   insert into erp.be_conversion_cost_sources_v1 values('${u(72)}','${ids.c}','RECOVERY');
   insert into erp.be_conversion_cost_events_v1(id,document_id,adjustment_id,previous_amount,target_amount)values('${u(74)}','${u(72)}','${u(73)}',0,-1);
   update erp.hpp_versions set total_cost=19.02 where lot_id='${ids.dest}';`);
 }
 await setup('20.02');await existingCost();await refuse('ACTUAL_PRIOR_ALLOCATION_EXTRA_INCLUDED',()=>command(payload('20.02')),/^BE_RECOVERY_EXCEEDS_VALUE:/);await end();
 await setup('20.02');await existingCost('2.00');await refuse('UNRECONCILED_EXISTING_NATIVE_COST_SOURCE',()=>command(payload('20.02')),/^CP7_SKU_RECOVERY_PROFILE_REVIEW_REQUIRED:/);await end();
 await setup('20.02');await db.exec(`insert into erp.material_cost_checkpoints values('${ids.material}','2026-10-09',0,0,null);`);
 assert.equal((await command(payload('20.02'))).status,'POSTED');pass('NATIVE_EMPTY_CLOSED_CHECKPOINT_ALLOWED');await end();
 await setup('20.02');await db.exec(`update erp.materials set accessory_category_id='${u(88)}'`);
 assert.equal((await command(payload('20.02'))).status,'POSTED');pass('CATEGORY_WITHOUT_NATIVE_REBUILD_SNAPSHOTS_ALLOWED');await end();
 await setup('20.02');await db.exec(`insert into erp.fg_lots values('${u(140)}','${u(180)}','PRODUCTION',null,'${u(100)}'),
 ('${u(141)}',null,'VOIDED_PRODUCTION',null,'${u(100)}'),('${u(142)}','${u(180)}','PRODUCTION',null,'${u(100)}');
 insert into erp.hpp_versions(lot_id,version_no,cost_state,qty_basis_pcs,total_cost,is_current)values
 ('${u(140)}',1,'ORIGINAL',0,0,true),('${u(141)}',1,'ORIGINAL',0,0,true),('${u(142)}',1,'ORIGINAL',1,'NaN'::numeric,true);`);
 assert.equal((await command(payload('20.02'))).status,'POSTED');pass('UNVISITED_OTHER_PO_AND_VOIDED_NULL_NAN_HPP_DO_NOT_REFUSE');await end();
 await setup('20.02');await db.exec(`update erp.hpp_versions set qty_basis_pcs=0 where lot_id='${ids.root}'`);
 await refuse('VISITED_NULL_SOURCE_HPP_REFUSES_BEFORE_EFFECT',()=>command(payload('20.02')),/^CP7_SKU_RECOVERY_PROFILE_REVIEW_REQUIRED:/);await end();
 const negatives=[
  ['REPRICING_UNIT_DIFFERS_FROM_CURRENT_AVERAGE',"",'20.01'],
  ['BACKDATED_APPEND',`update erp.material_stock_movements set physical_at='2026-10-20T10:00:00Z'`],
  ['INCOMPLETE_MATERIAL_COST','update erp.material_stock_movements set is_cost_recalculated=false'],
  ['NEGATIVE_CONSUMER','update erp.material_stock_movements set qty_signed=-100'],
  ['TRANSFER_CONSUMER',"update erp.material_stock_movements set source_type='MATERIAL_TRANSFER'"],
  ['CUTTING_CONSUMER',"update erp.material_stock_movements set source_type='CUTTING_GROUP'"],
  ['CONTRACTOR_CONSUMER',"update erp.material_stock_movements set source_type='CONTRACTOR_MATERIAL_ISSUE_ITEM'"],
  ['REVERSED_CONSUMER',`update erp.material_stock_movements set reversal_of_id='${u(77)}'`],
  ['MATERIAL_HISTORY_MISSING','delete from erp.material_cost_history'],
  ['MATERIAL_HISTORY_PREFIX_WRONG','update erp.material_cost_history set stock_after=101'],
  ['MATERIAL_CACHED_STOCK_WRONG','update erp.materials set cached_stock_qty=99'],
  ['SHARED_PURCHASE_RECURSIVE_REVALUATION',`insert into erp.material_purchase_items values('${u(66)}','${u(65)}','${u(67)}')`],
  ['UNKNOWN_PURCHASE_LINEAGE','delete from erp.material_purchase_items'],
  ['MATERIAL_CHECKPOINT_WRONG',`insert into erp.material_cost_checkpoints values('${ids.material}','2026-10-15',99,20.02,'${u(63)}')`],
  ['CATEGORY_NATIVE_REBUILD',`update erp.materials set accessory_category_id='${u(88)}';insert into erp.fg_accessory_cost_snapshots(category_id,hpp_method)values('${u(88)}','CATEGORY_MOVING_AVG')`],
  ['INCOMPLETE_COST_QUEUE','insert into erp.cost_recalc_queue(completed_at)values(null)'],
  ['UNNORMALIZED_NATIVE_GRAPH',`update erp.hpp_versions set total_cost=19 where lot_id='${ids.dest}'`],
  ['AMBIGUOUS_NATIVE_ALLOCATION',`insert into erp.product_conversion_allocations values('${u(44)}','${ids.c}','${ids.root}','${ids.dest}',2,0)`],
 ];
 for(const[id,sql,unit='20.02']of negatives){await setup('20.02');if(sql)await db.exec(sql);await refuse(id,()=>command(payload(unit)),/^CP7_SKU_RECOVERY_PROFILE_REVIEW_REQUIRED:/);await end();}
 await setup('20.02');await db.exec("update erp.test_actor set revoke_after_begin=true");await refuse('MISS_AUTH_AFTER_IDEMPOTENCY_DOUBLE',()=>command(payload('20.02')),/OWNER_ADMIN_REQUIRED/);await end();
 await setup('20.02');await db.exec("update erp.test_actor set revoke_after_lot=true");await refuse('MISS_AUTH_AFTER_BCLOT_MATERIAL_WAIT_DOUBLE',()=>command(payload('20.02')),/OWNER_ADMIN_REQUIRED/);await end();
 // Local selected busy-branch injection. Actual NOWAIT/FG contention still
 // requires two real server sessions in the separate prepared qualifier.
 const body=readFileSync(resolve(product,'recovery.sql'),'utf8');const anchor="if not pg_try_advisory_xact_lock(hashtextextended('FG_HPP_SALES_V2620C',0))then";
 assert.equal(body.split(anchor).length-1,1);const busy=body.slice(body.indexOf('create function cp7_sku_conversion.recovery_preflight_v1(')).replace('create function','create or replace function').replace(anchor,'if true then');
 await db.exec(busy);await setup('20.02');await refuse('BUSY_BRANCH_LOCAL_DOUBLE_BEFORE_EFFECT',()=>command(payload('20.02')),/^CP7_SKU_RECOVERY_BUSY:/);await end();
 const report={status:'PASS',count:results.length,proof_kind:'EXACT_CAPTURED_BC_SERVICE_AND_UNCHANGED_BE_HPP_WITH_DECLARED_LOCAL_DOUBLES',actual_Native_financial:0,actual_two_session_races:0,all_original_23_callbacks_edited:0,
  sequence_scope:'Refused commands/replay compare every local sequence. Successful/old-red allocations are never reseeded; only outer full backup restores actual run sequences.',sources:{recovery:sha(body),fixture:sha(readFileSync(resolve(here,'fixture.sql'))),unchanged_Native:Object.fromEntries(Object.entries(original.functions).map(([s,p])=>[s,p.sha256]))},cases:results,production_go:false,independent_acceptance:false};
 const output=process.env.SKU_RECOVERY_LOCAL_RECEIPT;assert(output,'SKU_RECOVERY_LOCAL_RECEIPT explicit output required');writeFileSync(output,JSON.stringify(report,null,2)+'\n');
 process.stdout.write(JSON.stringify({status:report.status,count:report.count,actual_Native_financial:0,actual_two_session_races:0})+'\n');
}finally{await db.close();}
