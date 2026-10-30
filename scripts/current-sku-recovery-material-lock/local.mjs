// Exact frozen local SQL control body plus explicitly declared policy doubles.
// One PGlite session cannot prove NOWAIT contention or real Native finance.
import {readFileSync} from 'node:fs';
import {createHash} from 'node:crypto';
import {dirname,resolve} from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
import assert from 'node:assert/strict';

const here=dirname(fileURLToPath(import.meta.url)),root=resolve(here,'../..');
const old=resolve(root,'scripts/cp7_sku_pair_conversion/recovery_local');
const cfg=JSON.parse(readFileSync(resolve(here,'SOURCE.json')));
const sha=x=>createHash('sha256').update(x).digest('hex');
const once=(text,a,b,label)=>{
  assert.equal(text.split(a).length-1,1,label);
  const i=text.indexOf(a),result=text.slice(0,i)+b+text.slice(i+a.length);
  assert.equal(result.slice(0,i)+a+result.slice(i+b.length),text,label+' reversible');return result;
};
assert.equal(once('before OLD after','OLD','$$begin $& $` literal $$','literal SQL dollars'),
  'before $$begin $& $` literal $$ after');
const pinned=name=>{
  const raw=readFileSync(resolve(root,name));assert.deepEqual({bytes:raw.length,sha256:sha(raw)},cfg.local_originals[name]);return raw.toString();
};
let body=pinned('scripts/cp7_sku_pair_conversion/recovery_local/check.mjs');
let fixture=pinned('scripts/cp7_sku_pair_conversion/recovery_local/fixture.sql');
fixture=once(fixture,"create function erp.bc_require_policy_v1(k text,label text)",
  "create table erp.test_policy(mode text not null check(mode in('MOVING_AVERAGE','NONE')));insert into erp.test_policy values('MOVING_AVERAGE');\ncreate function erp.bc_require_policy_v1(k text,label text)",'local policy table only');
fixture=once(fixture,"'unit_value_cap','MOVING_AVERAGE'","'unit_value_cap',(select mode from erp.test_policy)",'local Native policy reader double');
body=once(body,"const here=dirname(fileURLToPath(import.meta.url)),product=resolve(here,'..');",
  `const here=${JSON.stringify(old)},product=resolve(here,'..');`,'exact frozen local file paths');
assert(process.env.F04_PGLITE_MODULE,'F04_PGLITE_MODULE explicit pinned local runtime required');
const runtimeURL=process.env.F04_PGLITE_MODULE.startsWith('/')
  ?pathToFileURL(process.env.F04_PGLITE_MODULE).href:process.env.F04_PGLITE_MODULE;
body=once(body,'await import(runtime)',`await import(${JSON.stringify(runtimeURL)})`,
  'absolute local runtime URL from data-module context');
body=once(body,"await db.exec(readFileSync(resolve(here,'fixture.sql'),'utf8'));",
  `await db.exec(${JSON.stringify(fixture)});`,'declared policy fixture only');
const added=String.raw`
 // Additional NONE branch controls; all old forty-five assertions follow intact.
 for(const[unit,hpp,total]of[['20.01','0.005000','0.010000'],['20.02','0.000000','0.000000']]){
  await setup(unit);await db.exec("update erp.test_policy set mode='NONE'");
  assert.equal(await scalar("(erp.bc_require_policy_v1('ACC_DEC03','x')->>'unit_value_cap')"),'NONE');
  const response=await command(payload(unit));assert.equal(response.status,'POSTED');assert.equal(response.value,unit);
  assert.equal(await scalar("(select hpp_per_pcs::text from erp.v_current_hpp where lot_id='"+ids.dest+"')"),hpp);
  assert.equal(await scalar("(select total_cost::text from erp.v_current_hpp where lot_id='"+ids.dest+"')"),total);
  assert.equal(await scalar("(select total_cost::text from erp.v_current_hpp where lot_id='"+ids.dest2+"')"),'40.040000');
  assert.equal(await scalar("(select cached_stock_qty::text from erp.materials where id='"+ids.material+"')"),'101.000000');
  const a=await census();assert.deepEqual(await command(payload(unit)),response);assert.deepEqual(await census(),a);
  pass('NONE_'+(unit==='20.01'?'UNDER':'EQUAL')+'_POST_EXACT_REPLAY',{unit,Native_BE_HPP_hpp:hpp,Native_BE_HPP_total:total,complete_local_replay_census_equal:true});
  await end();
 }
 await setup('30.03');await db.exec("update erp.test_policy set mode='NONE'");
 await refuse('NONE_SAME_NATIVE_OVER_BUDGET_BEFORE_ANY_EFFECT',()=>command(),/^BE_RECOVERY_EXCEEDS_VALUE:/);await end();
 await setup('20.02');await db.exec("update erp.test_policy set mode='NONE';update erp.test_actor set revoke_after_lot=true");
 await refuse('NONE_AUTH_AFTER_NATIVE_BCLOT_WAIT_DOUBLE',()=>command(payload('20.02')),/OWNER_ADMIN_REQUIRED/);await end();
`;
body=once(body," await install(true);await setup();await refuse('SAME_NEGATIVE_BEFORE_FIRST_EFFECT'",
  added+" await install(true);await setup();await refuse('SAME_NEGATIVE_BEFORE_FIRST_EFFECT'",'four additional NONE controls before retained assertions');
// Install the unchanged two captured Native bodies before the new prelude.
// The retained first old-error control ran with originals and restored its rows.
body=once(body,added,' await install(true);\n'+added,'derived installation before new NONE controls');
body=once(body,"proof_kind:'EXACT_CAPTURED_BC_SERVICE_AND_UNCHANGED_BE_HPP_WITH_DECLARED_LOCAL_DOUBLES'",
  "proof_kind:'EXACT_CAPTURED_BC_SERVICE_BE_HPP_WITH_DECLARED_LOCAL_POLICY_AUTH_MATERIAL_JOURNAL_DOUBLES',retained_controls:45,additional_NONE_controls:4,real_NOWAIT_contention_proven:false",'honest local evidence scope');
await import('data:text/javascript;base64,'+Buffer.from(body).toString('base64'));
