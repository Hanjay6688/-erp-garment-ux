import {beforeEach,afterEach,test,expect}from'vitest'
import {readFileSync}from'node:fs'
import {syntheticCuttingInputs,actor,group,roll,size,pattern}from'./f04/cutting-input-fixture.mjs'
import {jsonArg}from'./f04/runtime.mjs'
let db:any
beforeEach(async()=>{db=await syntheticCuttingInputs();await db.execute(readFileSync('scripts/cp7-src/cutting-yield/observations.sql','utf8'));await db.execute(readFileSync('scripts/cp7-src/cutting-yield/model-producer.sql','utf8'))})
afterEach(async()=>{await db?.close()})
const family={brand:'RECORDED BRAND',mill:'RECORDED MILL',variant:'RECORDED VARIANT',spec_revision:'1'}
async function input(g=group,r=roll,width:string|null=null){
 const p={group_id:g,expected_group_version:'1',expected_input_version:null,marker_key:'preknown marker',planned_mix:[{size_id:size,drawings:'1'}],roll_inputs:[{roll_id:r,family,width_cm:width}],explicit_review:true}
 return(await db.query(`select public.erp_cp7_record_cutting_inputs_v1(${jsonArg(p)},'${crypto.randomUUID()}') v`))[0].v
}
async function command(p:any,key=crypto.randomUUID(),lookup=false){return(await db.query(`select public.${lookup?'erp_cp7_get_cutting_model_request_v1':'erp_cp7_capture_cutting_model_v1'}(${jsonArg(p)},'${key}') v`))[0].v}
const policyPayload=()=>({action:'POLICY',group_id:group,roll_id:roll,expected_group_version:'1',expected_input_version:'1',expected_policy_id:null,coverage:'0.75',train_batches:'3',calibration_batches:'4',holdout_batches:'3',explicit_review:true})
async function observation(g=group){
 const p={group_id:g,expected_group_version:'2',expected_input_version:'1'}
 return(await db.query(`select public.erp_cp7_capture_cutting_observation_v1(${jsonArg(p)},'${crypto.randomUUID()}') v`))[0].v
}
async function nativeStub(g:string,r:string,sid:string,pcs:string){
 await db.execute(`insert into erp.cutting_groups values('${g}','${g}',1,clock_timestamp()-interval '1 year',false,'${pattern}','r1');insert into erp.cutting_group_size_slots values('${g}','${size}');
  insert into public.control_cutting_slices values('${g}',${jsonArg([{slice_id:sid,group_id:g,roll_id:r,material_id:roll,unit_code:'YARD',material_sku:'MATERIAL-STUB',consumed_native:'60',outputs:[{yield_id:size,size_id:size,qty_pcs:pcs}]}])});`)
}
async function postStub(g=group){await db.execute(`update erp.cutting_groups set row_version=2,cut_at=clock_timestamp(),material_issue_posted=true where id='${g}'`);await observation(g)}
async function cohort(){
 await input(group,roll,'160');const policy=(await command(policyPayload())).result.policy
 // All these sources are explicit synthetic controls, zero Native credit.
 await db.execute(`update public.control_cutting_slices set slices=jsonb_set(slices,'{0,outputs,0,qty_pcs}','"48"')where group_id='${group}'`);await postStub()
 for(const width of[170,180,160,170,180,170,160,180,170]){
  const g=crypto.randomUUID(),r=crypto.randomUUID();await nativeStub(g,r,crypto.randomUUID(),String(width*0.3));await input(g,r,String(width));await postStub(g)
 }
 const g=crypto.randomUUID(),r=crypto.randomUUID();await nativeStub(g,r,crypto.randomUUID(),'51');await input(g,r,'170')
 return{policy,g,r,p:{action:'CHECK',group_id:g,roll_id:r,expected_group_version:'1',expected_input_version:'1',policy_id:policy.id}}
}
test('prospective policy is immutable and server timed; rejected fields/counts/CAS cannot create partial metadata',async()=>{
 await input();const before=await db.query('select *from erp.cutting_groups'),p=policyPayload(),first=await command(p)
 expect(first.result.policy.context.unit).toBe('YARD');expect(first.result.policy.policy_kind).toBe('EXPLICIT_PROSPECTIVE_PROPOSAL_NOT_FACTORY_GUARANTEE')
 for(const bad of[{...p,known_at:'2025-01-01T00:00:00Z'},{...p,coverage:'0.95'},{...p,holdout_batches:'2'},{...p,expected_group_version:'9'}])await expect(command(bad)).rejects.toThrow()
 await expect(command(p)).rejects.toThrow('CP7_CUTTING_MODEL_POLICY_CHANGED');await expect(db.execute("update cp7_cutting_model.policies set coverage=0.5")).rejects.toThrow('CONTROL_IMMUTABLE');expect(await db.query('select *from erp.cutting_groups')).toEqual(before)
})
test('ten prospectively captured independent batches qualify the fixed width challenger without business mutation',async()=>{
 const{p}=await cohort(),before=await db.query('select *from erp.cutting_groups'),out=await command(p),e=out.result.model.evaluation
 expect(e.status).toBe('PREDICTION_ONLY');expect(e.basis).toBe('WITH_RECORDED_WIDTH');expect(Number(e.interval.center_pcs)).toBe(51)
 expect(Number(e.width_score.interval_score)).toBeLessThan(Number(e.baseline_score.interval_score));expect([e.train_rows.length,e.calibration_rows.length,e.holdout_rows.length]).toEqual([3,4,3])
 expect(new Set([...e.train_rows,...e.calibration_rows,...e.holdout_rows].map((x:any)=>x.batch_key)).size).toBe(10)
 expect(out.original_matches_current_inputs&&out.original_matches_current_history).toBe(true);expect(out.business_write||out.automatic_activation||out.production_go).toBe(false);expect(await db.query('select *from erp.cutting_groups')).toEqual(before)
})
test('a new policy cannot claim past batches and a missing current observation cannot resurrect older history',async()=>{
 const{p}=await cohort(),first=await command(p),source=first.result.model.source_scope
 const old=source.input_groups.find((x:any)=>x.group_id!==p.group_id);await db.execute(`update erp.cutting_groups set row_version=row_version+1,material_issue_posted=false where id='${old.group_id}'`)
 const fresh=await command(p);expect(fresh.result.model.evaluation.reason).toBe('CURRENT_HISTORY_RECAPTURE_REQUIRED');expect(fresh.result.model.evaluation.interval).toBeNull()
 const recovered=await command(p,first.result.request_id,true);expect(recovered.result).toEqual(first.result);expect(recovered.original_matches_current_history).toBe(false)
 const w=(await db.query(`select public.erp_cp7_get_cutting_model_workspace_v1('${p.group_id}','${p.roll_id}') v`))[0].v
 const next={...policyPayload(),group_id:p.group_id,roll_id:p.roll_id,expected_policy_id:w.policy.id};const policy=(await command(next)).result.policy
 await db.execute(`update erp.cutting_groups set row_version=row_version-1,material_issue_posted=true where id='${old.group_id}'`)
 expect((await command({...p,policy_id:policy.id})).result.model.evaluation.reason).toBe('PROSPECTIVE_SEPARATE_BATCHES_REQUIRED')
})
test('UUID recovery and permanently sealed absent receipt preserve actor Original; current denial applies to caches',async()=>{
 await input();const p=policyPayload(),key=crypto.randomUUID(),first=await command(p,key);expect((await command(p,key,true)).result).toEqual(first.result)
 await expect(command({...p,coverage:'0.7'},key)).rejects.toThrow('CP7_CUTTING_MODEL_REQUEST_CHANGED')
 const absent=crypto.randomUUID();expect((await command(p,absent,true)).result.status).toBe('NOT_COMMITTED');expect((await command(p,absent)).result.status).toBe('NOT_COMMITTED')
 expect((await db.query('select count(*)::int n from cp7_cutting_model.policies'))[0].n).toBe(1)
 await db.execute('update public.control_cutting_access set allowed=false');await expect(command(p,key,true)).rejects.toThrow('CONTROL_CURRENT_ACCESS_DENIED')
})
test('metadata-only model has no public private-schema access or authenticated business DML grant',async()=>{
 expect((await db.query("select count(*)::int n from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname='cp7_cutting_model'and(p.prosecdef or pg_get_userbyid(p.proowner)<>'cp7_capture' or not('search_path=\"\"'=any(p.proconfig)))"))[0].n).toBe(0)
 for(const who of['authenticated','anon','service_role']){
  expect((await db.query(`select has_schema_privilege('${who}','cp7_cutting_model','USAGE') v`))[0].v).toBe(false)
  expect((await db.query(`select has_table_privilege('${who}','cp7_cutting_model.runs','INSERT,UPDATE,DELETE') v`))[0].v).toBe(false)
 }
 await db.execute(`update public.control_cutting_access set actor='${crypto.randomUUID()}'`)
 const w=(await db.query(`select public.erp_cp7_get_cutting_model_workspace_v1('${group}','${roll}') v`))[0].v
 expect(w.feature).toBeNull();expect(w.policy).toBeNull()
})
