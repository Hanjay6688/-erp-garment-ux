import {it,expect} from 'vitest'
import * as f from '../tests/fixtures/nativePlan'
import {parseStagedPlanOptions,stagedPlanPayload,validateStagedPlanCommit,parseStagedPlanSaved,parseStagedPlanPreview} from './nativeStagedPlan'
import {parsePlanOptions,parsePlanPreview} from './nativePlanDraft'

const saved=()=>parseStagedPlanSaved(f.stagedSaved(),f.actor,f.draft)
const form={orderId:f.order,patternId:f.pattern,locationId:f.location,cutAt:'',notes:'',reason:'Reviewed from the dated snapshot',reviewed:true,rolls:[{id:f.roll,issued:'1',consumed:'0.5',remaining:'0.5',pcs:'60'}]}

it('binds options to the staged run, its identity hash and its "data per" time, never to a whole Original',()=>{
 const o=parseStagedPlanOptions(f.stagedOptions(),f.actor,f.stagedContext)
 expect([o.sourceHash,o.dataAsOf,o.availableFg,o.pageIndex,o.needed,o.capacity]).toEqual([f.identityHash,f.dataAsOf,'5',0,'100','60'])
 for(const[key,value]of[['identity_hash','d'.repeat(64)],['data_as_of','2026-10-08T02:00:00Z'],['run_id',f.plan],['live_recheck','NEVER'],['contract_version','cp7.plan-options.v2']]as const)
  expect(()=>parseStagedPlanOptions({...f.stagedOptions(),[key]:value},f.actor,f.stagedContext)).toThrow()
 // A v1 parser never accepts a staged context, and the staged parser never a v1 reply.
 expect(()=>parsePlanOptions(f.options(),f.actor,f.stagedContext)).toThrow()
 expect(()=>parseStagedPlanOptions(f.options(),f.actor,f.stagedContext)).toThrow()
})
it('sends the identity hash in place of a source hash, with the same reviewed composition as v1',()=>{
 const p=stagedPlanPayload(parseStagedPlanOptions(f.stagedOptions(),f.actor,f.stagedContext),form,'2026-10-08T08:00:00Z',null) as Record<string,unknown>
 expect(p.identity_hash).toBe(f.identityHash);expect('source_hash'in p).toBe(false)
 expect(Object.keys(p).sort()).toEqual(['cutting','expected_revision','identity_hash','new_start_yield','plan_id','reason','reviewed_assumption_ids','run_id','target_key'])
})
it('reads a saved v2 plan with its snapshot values and refuses a v1 read',()=>{
 const s=saved();expect([s.sourceHash,s.dataAsOf,s.snapshot.need,s.snapshot.availableFg,s.snapshot.wip,s.snapshot.capacity]).toEqual([f.identityHash,f.dataAsOf,'100','5','8','60'])
 expect(()=>parseStagedPlanSaved(f.saved(),f.actor,f.draft)).toThrow()
 const other=f.stagedSaved();other.payload.identity_hash='d'.repeat(64);expect(()=>parseStagedPlanSaved(other,f.actor,f.draft)).toThrow()
})
it('accepts an unchanged recheck: the live numbers equal the snapshot and every check is OK',()=>{
 const p=parseStagedPlanPreview(f.stagedPreview(),f.actor,saved())
 expect([p.live.needNow,p.live.cutLimitNow,p.live.capacityNow,p.live.applyReady,p.dataAsOf]).toEqual(['100','100','60',true,f.dataAsOf])
 expect(()=>parsePlanPreview(f.stagedPreview(),f.actor,saved())).toThrow()
})
it('recomputes the need now from stock and WIP: 45 more finished pieces leave 55, below the plan of 60, refused',()=>{
 const p=parseStagedPlanPreview(f.stagedPreview('50'),f.actor,saved())
 expect([p.live.increase,p.live.needNow,p.live.cutLimitNow,p.live.applyReady]).toEqual(['45','55','55',false])
 expect(p.live.verdicts.find(v=>v.check==='NEED')).toEqual({check:'NEED',status:'REFUSED',code:'CP7_PLAN_V2_NEED_CHANGED'})
 // A server reply whose numbers or verdict disagree is not shown.
 for(const mutate of[(x:ReturnType<typeof f.stagedPreview>)=>{x.live.need_now_pcs='60'},(x:ReturnType<typeof f.stagedPreview>)=>{x.live.cut_limit_now_pcs='60'},
  (x:ReturnType<typeof f.stagedPreview>)=>{x.live.verdicts[5]={check:'NEED',status:'OK',code:null}},(x:ReturnType<typeof f.stagedPreview>)=>{x.live.apply_ready=true},
  (x:ReturnType<typeof f.stagedPreview>)=>{x.status='READY_FOR_EXPLICIT_NATIVE_DRAFT'},(x:ReturnType<typeof f.stagedPreview>)=>{x.live.increase_pcs='0'}]){
  const x=f.stagedPreview('50');mutate(x);expect(()=>parseStagedPlanPreview(x,f.actor,saved())).toThrow()
 }
})
it('recomputes the capacity left: 10 used by other plans leaves 50, below 60, refused as capacity used',()=>{
 const p=parseStagedPlanPreview(f.stagedPreview('5','10'),f.actor,saved())
 expect([p.live.capacityNow,p.live.capacityUsed,p.live.applyReady]).toEqual(['50','10',false])
 expect(p.live.verdicts.find(v=>v.check==='CAPACITY')?.code).toBe('CP7_PLAN_V2_CAPACITY_USED')
 const x=f.stagedPreview('5','10');x.live.capacity_now_pcs='60';expect(()=>parseStagedPlanPreview(x,f.actor,saved())).toThrow()
 const y=f.stagedPreview('5','10');y.live.verdicts[6]={check:'CAPACITY',status:'REFUSED',code:'CP7_PLAN_V2_CAPACITY_EXPIRED'};expect(()=>parseStagedPlanPreview(y,f.actor,saved())).toThrow()
})
it('keeps the need unknown when WIP is unknown, and refuses a reply that still states it',()=>{
 const x=f.stagedPreview();Object.assign(x.live,{wip_status:'UNKNOWN',wip_now_pcs:null,increase_pcs:null,need_now_pcs:null,cut_limit_now_pcs:null,apply_ready:false});x.status='REVIEW_REQUIRED'
 x.live.verdicts[4]={check:'WIP',status:'REFUSED',code:'CP7_PLAN_V2_WIP_UNKNOWN'};x.live.verdicts[5]={check:'NEED',status:'UNKNOWN',code:null}
 expect(parseStagedPlanPreview(x,f.actor,saved()).live.needNow).toBeNull()
 const y=structuredClone(x);y.live.need_now_pcs='100';expect(()=>parseStagedPlanPreview(y,f.actor,saved())).toThrow()
})
it('validates v2 commit receipts only: a v1 receipt or an apply without a passed recheck is refused',()=>{
 const request='cccccccc-cccc-4ccc-8ccc-cccccccccccc',payload={run_id:f.run,target_key:f.stagedContext.targetKey,identity_hash:f.identityHash}
 const env={action:'SAVE_DRAFT',payload,expectedVersion:null,fingerprint:'x',id:request,createdAt:'2026-10-08T03:00:00Z'}
 expect(validateStagedPlanCommit(f.stagedSaveOutcome(request),env,f.actor).sourceHash).toBe(f.identityHash)
 expect(()=>validateStagedPlanCommit(f.saveOutcome(request),env,f.actor)).toThrow()
 expect(()=>validateStagedPlanCommit({...f.stagedSaveOutcome(request),identity_hash:'d'.repeat(64)},env,f.actor)).toThrow()
})
