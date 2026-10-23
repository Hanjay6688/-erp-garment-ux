// Execute the actual history_source SQL against a controlled relational
// fixture. The proof adapter is a fixture, NOT a Native manufacturing proof;
// the separate Native20 suite exercises the unchanged real proof adapter.
import {readFile, writeFile, mkdir} from 'node:fs/promises'
import {execFileSync} from 'node:child_process'
import {createHash} from 'node:crypto'
import assert from 'node:assert/strict'

const modulePath = process.env.CP7_PGLITE_MODULE ?? '@electric-sql/pglite'
const {PGlite} = await import(modulePath)
const before = process.argv.includes('--before')
const path = 'scripts/cp7-src/plan-native/history-yield.sql'
const source = before ? execFileSync('git', ['show', `416f190:${path}`], {encoding: 'utf8'}) : await readFile(path, 'utf8')
const definition = name => {
  const start = source.indexOf(`create function cp7_plan_native.${name}(`)
  assert(start >= 0)
  const end = source.indexOf('end $$;', start)
  assert(end > start)
  return source.slice(start, end + 'end $$;'.length)
}
const db = new PGlite()
const uuid = n => `${n.toString(16).padStart(8, '0')}-0000-4000-8000-000000000000`
const root = uuid(1), size = uuid(2), model = uuid(3), otherModel = uuid(4), po = uuid(5)
await db.exec(`
 create schema erp; create schema cp7_plan_native; create schema cp7_private;
 create schema cp7_yield_policy; create schema cp7_supply_native;
 create function cp7_private.access_now() returns jsonb language sql as $$select '{"actor":"fixture"}'::jsonb$$;
 create function cp7_supply_native.proof_kernel() returns text language sql as $$select 'fixture-kernel'::text$$;
 create table erp.products(id uuid,identity_root_id uuid,size_id uuid,model_id uuid,effective_from timestamptz,effective_to timestamptz);
 create table erp.production_orders(id uuid,model_id uuid);
 create table erp.cutting_groups(id uuid,po_id uuid,material_issue_posted boolean,cut_at timestamptz);
 create table erp.qc_inspections(id uuid,status text);
 create table erp.qc_inspection_items(cutting_group_id uuid,inspection_id uuid,final_product_id uuid);
 create table cp7_supply_native.exhaustion_proofs(id uuid,group_id uuid,kernel_version text,captured_at timestamptz);
 create table cp7_yield_policy.policies(id uuid,revision bigint,state text,window_days int,min_groups int,min_cut_pcs int,
   confidence text,actor_role text,recorded_at timestamptz);
 create table public.fixture_groups(id uuid primary key,value jsonb,unverified boolean default false,incomplete boolean default false);
 create function cp7_plan_native.history_groups(ids uuid[],at timestamptz,kernel text) returns jsonb language plpgsql as $$
 begin
  if cardinality(ids)>50 then raise exception 'Fixture proof adapter batch exceeds the real reader limit';end if;
  if exists(select 1 from public.fixture_groups where id=any(ids) and incomplete)then
   return '{"status":"UNKNOWN","reason":"HISTORY_SOURCE_INCOMPLETE"}'::jsonb;end if;
  return jsonb_build_object('status','COMPLETE','groups',coalesce((select jsonb_agg(value order by id)
   from public.fixture_groups where id=any(ids)and not unverified),'[]'::jsonb),'unverified',
   coalesce((select jsonb_agg(id)from public.fixture_groups where id=any(ids)and unverified),'[]'::jsonb));
 end $$;
 insert into erp.products values('${root}','${root}','${size}','${model}',now()-interval '1 year',null);
 insert into erp.production_orders values('${po}','${model}');
 insert into cp7_yield_policy.policies values('${uuid(6)}',1,'ACTIVE',180,5,200,'0.90','OWNER',now());
`)
await db.exec(definition('wilson_permille') + '\n' + definition('history_source'))
async function fixture(count, productLevel = true) {
  await db.exec(`truncate erp.cutting_groups,erp.qc_inspections,erp.qc_inspection_items,cp7_supply_native.exhaustion_proofs,public.fixture_groups`)
  const rows = Array.from({length: count}, (_, i) => ({id: uuid(100 + i), proof: uuid(10000 + i)}))
  for (const {id, proof} of rows) {
    await db.query(`insert into erp.cutting_groups values($1,$2,true,now()-interval '1 day');
    `, [id, po])
    await db.query(`insert into cp7_supply_native.exhaustion_proofs values($1,$2,'fixture-kernel',now())`, [proof, id])
    if (productLevel) {
      await db.query(`insert into erp.qc_inspections values($1,'POSTED')`, [proof])
      await db.query(`insert into erp.qc_inspection_items values($1,$2,$3)`, [id, proof, root])
    }
    const value = {group_id:id, proof:{proof_id:proof,facts_hash:id,captured_at:new Date().toISOString()},
      finished_at:new Date(Date.now()-86400000).toISOString(),model_id:model,qc_models:[model],
      pools:[{size_id:size,input_pcs:'40',fg_pcs:'37',spent:true,qc_roots:[root]}]}
    await db.query('insert into public.fixture_groups(id,value)values($1,$2::jsonb)', [id, JSON.stringify(value)])
  }
  return rows
}
const read = async () => (await db.query('select cp7_plan_native.history_source($1,$2::uuid) value',[`${root}:${size}`,model])).rows[0].value
const results = []
async function test(id, fn) {
  try { results.push({id,status:'PASS',observed:await fn()}) }
  catch(error) { results.push({id,status:'FAIL',error:String(error.message).slice(0,1500)}) }
}
for (const count of [200,201,501]) await test(`COMPLETE_PRODUCT_SIZE_${count}`,async()=>{
  const groups=await fixture(count),h=await read()
  assert.equal(h.status,'AVAILABLE',`expected all ${count} groups, observed ${h.status}/${h.reason}`)
  assert.equal(h.groups,String(count));assert.equal(h.cut_pcs,String(count*40));assert.equal(h.fg_pcs,String(count*37))
  assert.deepEqual(h.proofs.map(x=>x.group_id).sort(),groups.map(x=>x.id).sort())
  return {groups:h.groups,cut_pcs:h.cut_pcs,fg_pcs:h.fg_pcs,all_proofs_matched:true}
})
await test('COMPLETE_MODEL_FALLBACK_501',async()=>{
  await fixture(501,false);const h=await read()
  assert.equal(h.status,'AVAILABLE');assert.equal(h.level,'MODEL');assert.equal(h.groups,'501')
  return {level:h.level,groups:h.groups}
})
await test('STALE_PROOF_AFTER_GROUP_200_EXCLUDED_EXACTLY',async()=>{
  const groups=await fixture(501)
  await db.query('update public.fixture_groups set unverified=true where id=$1',[groups.at(-1).id])
  const h=await read();assert.equal(h.status,'AVAILABLE');assert.equal(h.groups,'500')
  assert.equal(h.excluded.stale_or_unverifiable,'1');assert.equal(h.cut_pcs,'20000');assert.equal(h.fg_pcs,'18500')
  assert(!h.proofs.some(x=>x.group_id===groups.at(-1).id))
  return {groups:h.groups,stale_excluded:h.excluded.stale_or_unverifiable}
})
await test('LATE_BATCH_FAILURE_NEVER_RETURNS_PARTIAL_YIELD',async()=>{
  const groups=await fixture(501)
  await db.query('update public.fixture_groups set incomplete=true where id=$1',[groups.at(-1).id])
  const h=await read();assert.equal(h.status,'UNKNOWN');assert.equal(h.reason,'HISTORY_SOURCE_INCOMPLETE')
  assert.equal(h.lower_bound,null);assert.deepEqual(h.proofs,[])
  return {status:h.status,reason:h.reason,lower_bound:h.lower_bound}
})
const report={label:before?'OW13B_READER_BEFORE':'OW13B_READER_AFTER',scope:'ACTUAL_READER_SQL_WITH_CONTROLLED_RELATIONAL_FIXTURE_AND_STUBBED_PROOF_ADAPTER_NOT_NATIVE_PROOF',
  source_sha256:createHash('sha256').update(source).digest('hex'),status:results.every(x=>x.status==='PASS')?'PASS':'FAIL',cases:results}
await mkdir('cp6-proof/ow13b',{recursive:true})
await writeFile(`cp6-proof/ow13b/${before?'READER_BEFORE':'READER_AFTER'}.json`,JSON.stringify(report,null,2)+'\n')
console.log(JSON.stringify(report,null,2))
await db.close()
if (!before && report.status!=='PASS')process.exitCode=1
