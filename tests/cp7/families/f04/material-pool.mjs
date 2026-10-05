import assert from 'node:assert/strict'
import {readFileSync,writeFileSync,mkdirSync} from 'node:fs'
import {dirname} from 'node:path'
import {openRuntime,digest} from './runtime.mjs'

// Synthetic private-kernel controls only. They cannot qualify Native ERP,
// current Auth, a real domain command, a race, a browser or all of P08/P19.
const source=readFileSync('scripts/cp7-src/plan-native/preflight.sql','utf8')
const helper=source.slice(0,source.indexOf('create function cp7_plan_native.preflight('))
const roll='11111111-1111-4111-8111-111111111111',location='22222222-2222-4222-8222-222222222222'
const group='33333333-3333-4333-8333-333333333333',line='44444444-4444-4444-8444-444444444444'
const db=await openRuntime(),cases=[]
try{
 await db.execute(`create schema erp;create schema cp7_plan_native;
 create table erp.material_stock_movements(roll_id uuid,location_id uuid,physical_at timestamptz,qty_signed numeric);
 create table erp.cutting_groups(id uuid primary key,row_version bigint,source_location_id uuid,material_issue_posted boolean);
 create table erp.cutting_group_rolls(id uuid primary key,cutting_group_id uuid,roll_id uuid,qty_issued numeric);
 create table cp7_plan_native.intents(cutting_group_id uuid);
 ${helper}`)
 const read=async()=> (await db.query(`select cp7_plan_native.material_pool('${roll}','${location}')as result`))[0].result
 const check=async(id,wanted)=>{
  const r=await read();assert.deepEqual([r.native_available,r.linked_native_draft_qty,r.free_for_new_plan],wanted,id)
  assert.equal(r.roll_id,roll);assert.equal(r.location_id,location)
  assert.equal(r.basis,'CURRENT_NATIVE_LINKED_UNPOSTED_DRAFT_BUDGET_NOT_STOCK_RESERVATION')
  cases.push({id,status:'PASS',complete_receipt:r})
 }
 const reset=async()=>db.execute('truncate erp.material_stock_movements,erp.cutting_groups,erp.cutting_group_rolls,cp7_plan_native.intents;')
 const stock=async(qty)=>db.execute(`insert into erp.material_stock_movements values('${roll}','${location}',clock_timestamp()-interval'1 day',${qty});`)
 const linked=async(qty)=>db.execute(`insert into erp.cutting_groups values('${group}',1,'${location}',false);
 insert into erp.cutting_group_rolls values('${line}','${group}','${roll}',${qty});
 insert into cp7_plan_native.intents values('${group}');`)
 await check('empty_is_known_zero',['0','0','0'])
 await stock('10');await linked('6');await check('one_global_physical_roll_budget',['10','6','4'])
 await db.execute(`insert into cp7_plan_native.intents values('${group}');`);await check('one_Native_group_not_duplicate_metadata',['10','6','4'])
 await db.execute(`update erp.cutting_group_rolls set qty_issued=3;update erp.cutting_groups set row_version=2;`)
 await check('current_Native_draft_edit_not_old_estimate',['10','3','7'])
 assert.equal((await read()).linked_native_drafts[0].group_revision,'2')
 await db.execute(`update erp.cutting_groups set material_issue_posted=true;insert into erp.material_stock_movements values('${roll}','${location}',clock_timestamp()-interval'1 minute',-6);`)
 await check('posted_physical_issue_not_deducted_twice',['4','0','4'])
 await reset();await stock('10');await linked('6')
 await db.execute(`insert into erp.material_stock_movements values('99999999-9999-4999-8999-999999999999','${location}',clock_timestamp(),999),('${roll}','99999999-9999-4999-8999-999999999999',clock_timestamp(),999);`)
 await check('other_roll_and_location_never_fill_pool',['10','6','4'])
 await db.execute(`insert into erp.material_stock_movements values('${roll}','${location}',clock_timestamp()+interval'1 day',999);`)
 await check('future_physical_stock_excluded',['10','6','4'])
 await db.execute('truncate cp7_plan_native.intents;');await check('ordinary_unlinked_draft_no_false_reservation',['10','0','10'])
 await reset();await stock('10.000001');await linked('10');await check('decimal_micro_quantity_preserved',['10.000001','10','0.000001'])
 await reset();await stock('-1');await linked('6');await check('negative_physical_source_not_zero_fallback',['-1','6',null])
 await reset();await stock('4');await linked('6');await check('existing_plan_oversubscription_no_new_capacity',['4','6','0'])
 await reset();await stock('10');await linked('6')
 await db.execute(`insert into erp.cutting_groups values('55555555-5555-4555-8555-555555555555',1,'${location}',false);
 insert into erp.cutting_group_rolls values('66666666-6666-4666-8666-666666666666','55555555-5555-4555-8555-555555555555','${roll}',3);
 insert into cp7_plan_native.intents values('55555555-5555-4555-8555-555555555555');`)
 await check('all_linked_targets_share_whole_pool',['10','9','1'])
 const receipt={contract:'cp7.shared-material-pool-private-kernel.v1',status:'PASS',runtime:db.flavor,version:db.version,
  source_sha256:digest(helper),cases,passed:cases.length,Native_business_case_credit:0,Auth_HTTP_credit:0,browser_credit:0,
  full_P08_acceptance:false,full_P19_acceptance:false,stock_reservation_created:false,cleanup:'CLOSED_DISPOSABLE_RUNTIME'}
 if(process.env.F04_RECEIPT_PATH){mkdirSync(dirname(process.env.F04_RECEIPT_PATH),{recursive:true});writeFileSync(process.env.F04_RECEIPT_PATH,JSON.stringify(receipt,null,2)+'\n')}
 console.log(JSON.stringify(receipt))
}finally{await db.close()}
