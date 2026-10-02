// @vitest-environment node
import {readFileSync}from'node:fs'
import {beforeAll,beforeEach,afterAll,test,expect}from'vitest'
import {syntheticCuttingInputs,actor,group,roll,size}from'./f04/cutting-input-fixture.mjs'
import {jsonArg}from'./f04/runtime.mjs'
let db:Awaited<ReturnType<typeof syntheticCuttingInputs>>
const family={brand:'B',mill:'M',variant:'V',spec_revision:'1'}
const input=()=>({group_id:group,expected_group_version:'1',expected_input_version:null,marker_key:'marker-1',planned_mix:[{size_id:size,drawings:'3'}],roll_inputs:[{roll_id:roll,family,width_cm:null}],explicit_review:true})
beforeAll(async()=>{db=await syntheticCuttingInputs();await db.execute(readFileSync('scripts/cp7-src/cutting-yield/observations.sql','utf8'))},120000)
beforeEach(async()=>{
 await db.execute(`truncate cp7_cutting_observations.requests,cp7_cutting_observations.runs,cp7_cutting_inputs.requests,cp7_cutting_inputs.plans;
 update public.control_cutting_access set actor='${actor}',allowed=true,write_allowed=true;
 update erp.cutting_groups set row_version=1,cut_at=clock_timestamp()-interval '1 year',material_issue_posted=false;
 update public.control_cutting_slices set slices=${jsonArg([{slice_id:roll,group_id:group,roll_id:roll,material_id:roll,material_sku:'REAL-SYNTHETIC-SOURCE',unit_code:'YARD',outputs:[{yield_id:size,size_id:size,qty_pcs:'60'}],consumed_native:'60'}])}`)
})
afterAll(async()=>{if(db)await db.close()})
const capture=async(p:unknown,id=crypto.randomUUID(),lookup=false)=>(await db.query(`select public.${lookup?'erp_cp7_get_cutting_observation_request_v1':'erp_cp7_capture_cutting_observation_v1'}(${jsonArg(p)},'${id}') r`))[0].r
async function planAndPost(zero=false){
 await db.query(`select public.erp_cp7_record_cutting_inputs_v1(${jsonArg(input())},'${crypto.randomUUID()}')`)
 await db.execute(`update erp.cutting_groups set cut_at=clock_timestamp(),row_version=2,material_issue_posted=true;`)
 if(zero)await db.execute(`update public.control_cutting_slices set slices=jsonb_set(slices,'{0,outputs,0,qty_pcs}','"0"'::jsonb)`)
 return{group_id:group,expected_group_version:'2',expected_input_version:'1'}
}
test('source-derived observation preserves explicit zero output, Native unit/context and real clocks without manufacturing width',async()=>{
 const p=await planAndPost(true),before=await db.query('select *from erp.cutting_groups'),out=await capture(p),r=out.result.observation.records[0]
 expect(out.result.status).toBe('COMMITTED');expect(r.native_valid).toBe(true);expect(r.actual_pcs).toBe('0');expect(r.consumed).toBe('60');expect(r.width_cm).toBeNull();expect(r.context.unit).toBe('YARD');expect(r.context.planned_mix).toEqual([{size_id:size,drawings:'1'}])
 expect(out.model_trained).toBe(false);expect(out.original_matches_current_native).toBe(true);expect(out.original_matches_current_inputs).toBe(true);expect(await db.query('select *from erp.cutting_groups')).toEqual(before)
 expect(BigInt(Date.parse(r.known_at))).toBeGreaterThanOrEqual(BigInt(Date.parse(r.physical_at)))
 await db.execute("update public.control_cutting_slices set slices=jsonb_set(slices,'{0,outputs}','[]'::jsonb)")
 const missing=(await capture(p)).result.observation;expect(missing.records[0].actual_pcs).toBeNull();expect(missing.records[0].native_valid).toBe(false);expect(missing.exclusions[0].reason).toBe('NATIVE_OUTPUT_OR_CONSUMPTION_UNAVAILABLE')
})
test('same UUID recovery preserves Original, changed payload refuses and sealed absent lookup never becomes a new capture',async()=>{
 const p=await planAndPost(),key=crypto.randomUUID(),first=await capture(p,key);expect((await capture(p,key,true)).result).toEqual(first.result)
 await expect(capture({...p,expected_input_version:'2'},key)).rejects.toThrow('CP7_CUTTING_OBSERVATION_REQUEST_CHANGED')
 const absent=crypto.randomUUID();expect((await capture(p,absent,true)).result.status).toBe('NOT_COMMITTED');expect((await capture(p,absent)).result.status).toBe('NOT_COMMITTED')
 expect((await db.query('select count(*)::int n from cp7_cutting_observations.runs'))[0].n).toBe(1)
 await expect(db.execute("update cp7_cutting_observations.runs set records='[]'")).rejects.toThrow('CONTROL_IMMUTABLE');await expect(db.execute('delete from cp7_cutting_observations.requests')).rejects.toThrow('CONTROL_IMMUTABLE')
})
test('current cancellation is an invalid latest revision, preserving old source and physical identity rather than resurrecting training',async()=>{
 const p=await planAndPost(),first=await capture(p);await db.execute('update erp.cutting_groups set material_issue_posted=false,row_version=3')
 const latest=await capture({...p,expected_group_version:'3'});expect(latest.result.observation.records[0].native_valid).toBe(false);expect(latest.result.observation.records[0].physical_at).toBe(first.result.observation.records[0].physical_at)
 expect(latest.result.observation.exclusions[0].reason).toBe('NATIVE_UNPOSTED_OR_CANCELLED')
 expect((await capture(p,first.result.request_id,true)).result).toEqual(first.result);expect((await capture(p,first.result.request_id,true)).original_matches_current_native).toBe(false)
 const records=[...first.result.observation.records,...latest.result.observation.records]
 const dataset=(await db.query(`select cp7_cutting_learning.dataset(${jsonArg(records)},${jsonArg(first.result.observation.records[0].context)},null,clock_timestamp(),'excluded-current') d`))[0].d
 expect(JSON.stringify(dataset)).not.toContain(roll)
})
test('changed physical date and removed slice suppress the old physical record; latest unavailable input never defaults to actual mix',async()=>{
 const p=await planAndPost(),first=await capture(p);await db.execute("update erp.cutting_groups set cut_at=cut_at-interval '1 day',row_version=3")
 const shifted=await capture({...p,expected_group_version:'3'});expect(shifted.result.observation.records[0].native_valid).toBe(false);expect(shifted.result.observation.records[0].physical_at).toBe(first.result.observation.records[0].physical_at);expect(shifted.result.observation.exclusions[0].reason).toBe('NATIVE_PHYSICAL_IDENTITY_CHANGED')
 await db.execute("update public.control_cutting_slices set slices='[]'");const removed=await capture({...p,expected_group_version:'3'});expect(removed.result.observation.records[0].native_valid).toBe(false);expect(removed.result.observation.exclusions[0].reason).toBe('NATIVE_SLICE_OR_GROUP_REMOVED')
 expect((await capture(p,first.result.request_id,true)).result).toEqual(first.result)
})
test('caller training facts or clocks refuse, actual source versions and current authority govern cached Originals',async()=>{
 const p=await planAndPost(),first=await capture(p)
 for(const extra of[{source_complete:true},{known_at:'2025-01-01T00:00:00Z'},{actual_pcs:'0'},{unit:'M'}])await expect(capture({...p,...extra})).rejects.toThrow()
 await expect(capture({...p,expected_group_version:'1'})).rejects.toThrow('CP7_CUTTING_OBSERVATION_SOURCE_CHANGED')
 await db.execute('update public.control_cutting_access set allowed=false');await expect(capture(p,first.result.request_id,true)).rejects.toThrow('CONTROL_CURRENT_ACCESS_DENIED')
})
