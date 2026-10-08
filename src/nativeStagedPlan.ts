import type {ProductionEnvelope} from './productionRecovery'
import {parseCuttingSaveResult} from './cuttingPersistence'
import {fail,rec,text,guid,hash,qty,revision,target,flags,optionsBody,previewBody,planPayload,type StagedPlanContext,type PlanOptions,type PlanForm,type PlanSaved,type PlanPreview} from './nativePlanDraft'

// Plan v2 (snapshot contract v2 §3): a plan from one target of a staged run.
// It is drafted from the run's dated snapshot ("data per"); preview reports
// and apply enforces the server's live recheck. Every number the screen shows
// about the recheck is recomputed here from the server's own values.
export const STAGED_PLAN_CHECKS=['PRODUCT','POLICY','TARGET_PLANS','LINKED_PLANS','WIP','NEED','CAPACITY'] as const
export type StagedPlanCheck=typeof STAGED_PLAN_CHECKS[number]
export type StagedVerdict={check:StagedPlanCheck;status:'OK'|'REFUSED'|'UNKNOWN';code:string|null}
export type StagedPlanOptions=PlanOptions&{dataAsOf:string;availableFg:string|null;pageIndex:number|null}
export type StagedSnapshot={need:string;availableFg:string;wip:string|null;capacity:string;productionState:string|null}
export type StagedPlanSaved=PlanSaved&{dataAsOf:string;snapshot:StagedSnapshot}
export type StagedLive={checkedAt:string;fgNow:string;fgSnapshot:string;wipNow:string|null;wipSnapshot:string|null;wipStatus:string;increase:string|null;needNow:string|null;
 cutLimitNow:string|null;capacityNow:string;capacityUsed:string;throughAt:string|null;policyState:string|null;verdicts:StagedVerdict[];applyReady:boolean}
export type StagedPlanPreview=PlanPreview&{dataAsOf:string;live:StagedLive;alreadyApplied:boolean}
const instant=(v:unknown):string=>typeof v==='string'&&Number.isFinite(Date.parse(v))?v:fail()
const maybe=(v:unknown)=>v===null?null:qty(v)
type Q={n:bigint;d:bigint}
const dec=(v:string):Q=>{const[a,b='']=v.split('.');return{n:BigInt(a+b),d:10n**BigInt(b.length)}}
const sub=(x:Q,y:Q):Q=>({n:x.n*y.d-y.n*x.d,d:x.d*y.d}),add=(x:Q,y:Q):Q=>({n:x.n*y.d+y.n*x.d,d:x.d*y.d})
const eq=(x:Q,y:Q)=>x.n*y.d===y.n*x.d,gt=(x:Q,y:Q)=>x.n*y.d>y.n*x.d,max0=(x:Q):Q=>x.n<0n?{n:0n,d:1n}:x
const ceil=(x:Q)=>(x.n+x.d-1n)/x.d

export function parseStagedPlanOptions(v:unknown,actor:string,c:StagedPlanContext):StagedPlanOptions{
 const r=rec(v);flags(r,actor,'cp7.plan-options-staged.v1')
 if(r.run_id!==c.runId||r.target_key!==c.targetKey||r.identity_hash!==c.identityHash||r.data_as_of!==c.dataAsOf||r.live_recheck!=='AT_PREVIEW_AND_APPLY')fail()
 const identity=hash(r.identity_hash),page=r.page_index===null?null:typeof r.page_index==='number'&&Number.isSafeInteger(r.page_index)&&r.page_index>=0?r.page_index:fail()
 // The body's binding hash is the run's identity hash (v2 has no Original source hash).
 return{...optionsBody({...r,source_hash:identity,core_hash:identity},identity,identity),dataAsOf:instant(r.data_as_of),availableFg:maybe(r.available_fg_pcs),pageIndex:page}
}
export function stagedPlanPayload(o:StagedPlanOptions,f:PlanForm,cutAt:string,saved:PlanSaved|null){
 const{source_hash,...p}=planPayload(o,f,cutAt,saved);return{...p,identity_hash:source_hash}
}
export function validateStagedPlanCommit(v:unknown,e:ProductionEnvelope,actor:string):PlanSaved{
 const r=rec(v),p=rec(e.payload);flags(r,actor,e.action==='SAVE_DRAFT'?'cp7.plan-draft.v2':'cp7.plan-apply-outcome.v2');if(r.request_id!==e.id)fail()
 if(e.action==='SAVE_DRAFT'){
  if(r.run_id!==p.run_id||r.target_key!==p.target_key||r.identity_hash!==p.identity_hash||r.state!=='SAVED')fail();instant(r.data_as_of)
  return{id:guid(r.draft_id),planId:guid(r.plan_id),revision:revision(r.revision),runId:guid(r.run_id),targetKey:target(r.target_key),sourceHash:hash(r.identity_hash),state:'SAVED',native:null}
 }
 if(e.action!=='APPLY'||r.kind!=='COMMITTED_OUTCOME'||r.draft_id!==p.draft_id||r.revision!==p.expected_revision||r.state!=='NATIVE_DRAFT_CREATED'||r.physical_production_confirmed!==false)fail()
 hash(r.identity_hash);instant(r.data_as_of);if(rec(r.live).apply_ready!==true)fail()
 const n=parseCuttingSaveResult(r.native);if(n.material_issue_posted!==false)fail()
 return{id:guid(r.draft_id),planId:'',revision:revision(r.revision),runId:'',targetKey:target(r.target_key),sourceHash:'',state:'NATIVE_DRAFT_CREATED',native:{id:guid(r.intent_id),groupId:guid(n.cutting_group_id),number:n.group_number,posted:false}}
}
export function parseStagedPlanSaved(v:unknown,actor:string,id:string):StagedPlanSaved{
 const r=rec(v);flags(r,actor,'cp7.plan-draft-read.v2');if(r.draft_id!==id||typeof r.is_latest!=='boolean'||!['SAVED','NATIVE_DRAFT_CREATED','NATIVE_DRAFT_DELETED','NATIVE_MATERIAL_POSTED'].includes(String(r.state)))fail()
 const p=rec(r.payload),s=rec(r.snapshot);if(p.run_id!==r.run_id||p.target_key!==r.target_key||p.identity_hash!==r.identity_hash)fail()
 const native=r.native_intent===null?null:rec(r.native_intent);if(native!==null&&native.material_issue_posted!==null&&typeof native.material_issue_posted!=='boolean')fail()
 return{id:guid(r.draft_id),planId:guid(r.plan_id),revision:revision(r.revision),runId:guid(r.run_id),targetKey:target(r.target_key),sourceHash:hash(r.identity_hash),state:String(r.state),
  native:native?{id:guid(native.id),groupId:guid(native.cutting_group_id),number:native.group_number===null?null:text(native.group_number),posted:native.material_issue_posted as boolean|null}:null,
  dataAsOf:instant(r.data_as_of),snapshot:{need:qty(s.need_pcs),availableFg:qty(s.available_fg_pcs),wip:maybe(s.wip_model_size_pcs),capacity:qty(s.capacity_pcs),productionState:s.production_state===null?null:text(s.production_state)}}
}
export function parseStagedPlanPreview(v:unknown,actor:string,s:PlanSaved):StagedPlanPreview{
 const r=rec(v);flags(r,actor,'cp7.plan-preview-staged.v1')
 if(r.draft_id!==s.id||r.revision!==s.revision||r.plan_id!==s.planId||r.target_key!==s.targetKey||r.identity_hash!==s.sourceHash||r.physical_production_confirmed!==false
  ||r.command!=='erp_save_cutting_group_before_sewing_v2:SAVE_DRAFT'||typeof r.already_applied!=='boolean'||'native_payload'in r)fail()
 hash(r.composition_hash);const body=previewBody(r),l=rec(r.live)
 const verdicts=(Array.isArray(l.verdicts)?l.verdicts:fail()).map(rec).map(x=>({check:x.check as StagedPlanCheck,status:x.status as StagedVerdict['status'],code:x.code===null?null:text(x.code)}))
 if(verdicts.map(x=>x.check).join('|')!==STAGED_PLAN_CHECKS.join('|')||verdicts.some(x=>!['OK','REFUSED','UNKNOWN'].includes(x.status)||(x.status==='REFUSED')!==(x.code!==null)))fail()
 const live:StagedLive={checkedAt:instant(l.checked_at),fgNow:qty(l.fg_now_pcs),fgSnapshot:qty(l.fg_snapshot_pcs),wipNow:maybe(l.wip_now_pcs),wipSnapshot:maybe(l.wip_snapshot_pcs),
  wipStatus:text(l.wip_status),increase:maybe(l.increase_pcs),needNow:maybe(l.need_now_pcs),cutLimitNow:maybe(l.cut_limit_now_pcs),capacityNow:typeof l.capacity_now_pcs==='string'&&/^-?(0|[1-9][0-9]*)(\.[0-9]+)?$/.test(l.capacity_now_pcs)?l.capacity_now_pcs:fail(),
  capacityUsed:qty(l.capacity_used_by_other_plans_pcs),throughAt:l.capacity_through_at===null?null:instant(l.capacity_through_at),policyState:l.policy_state===null?null:text(l.policy_state),verdicts,applyReady:l.apply_ready===true}
 if(typeof l.apply_ready!=='boolean'||live.applyReady!==verdicts.every(x=>x.status==='OK')||l.selected_new_pcs!==body.selected||r.status!==(live.applyReady?'READY_FOR_EXPLICIT_NATIVE_DRAFT':'REVIEW_REQUIRED'))fail()
 const by=Object.fromEntries(verdicts.map(x=>[x.check,x]))
 // The need now: snapshot need less any increase of stock + WIP since then; the cut limit at the same yield.
 if(by.WIP.status==='OK'){
  if(live.wipNow===null||live.wipSnapshot===null||live.increase===null||live.needNow===null||live.cutLimitNow===null)fail()
  const inc=max0(sub(add(dec(live.fgNow),dec(live.wipNow!)),add(dec(live.fgSnapshot),dec(live.wipSnapshot!)))),need=max0(sub(dec(body.needed),inc))
  const y=body.yield,limit=y.basis==='UNKNOWN'?ceil(need):ceil({n:need.n*BigInt(y.denominator!),d:need.d*BigInt(y.numerator!)})
  if(!eq(dec(live.increase!),inc)||!eq(dec(live.needNow!),need)||!eq(dec(live.cutLimitNow!),{n:limit,d:1n}))fail()
  if((by.NEED.status==='REFUSED')!==(need.n===0n||gt(dec(body.selected),{n:limit,d:1n}))||by.NEED.status==='UNKNOWN')fail()
 }else if(by.NEED.status!=='UNKNOWN'||live.needNow!==null)fail()
 // The capacity left: the snapshot's less every other plan outside its load.
 const left=sub(dec(body.capacity),dec(live.capacityUsed)),capacityNow=live.capacityNow.startsWith('-')?{n:-dec(live.capacityNow.slice(1)).n,d:dec(live.capacityNow.slice(1)).d}:dec(live.capacityNow)
 if(!eq(left,capacityNow))fail()
 const expired=live.throughAt===null||Date.parse(live.throughAt)<=Date.parse(live.checkedAt)
 if(by.CAPACITY.code!==(expired?'CP7_PLAN_V2_CAPACITY_EXPIRED':gt(dec(body.selected),capacityNow)?'CP7_PLAN_V2_CAPACITY_USED':null))fail()
 return{...body,dataAsOf:instant(r.data_as_of),live,alreadyApplied:r.already_applied as boolean}
}
// The screen's words for each refused check (the server's code is the authority).
export const stagedVerdictText:Record<StagedPlanCheck,string>={
 PRODUCT:'Produk berubah sejak data diambil (tidak aktif lagi, atau model/ukurannya lain).',
 POLICY:'Status produksi SKU sekarang bukan Aktif.',
 TARGET_PLANS:'Target ini sudah punya rencana lain sesudah data diambil.',
 LINKED_PLANS:'Rencana sebelumnya untuk target ini belum selesai terbukti di produksi.',
 WIP:'Barang dalam proses model dan ukuran ini belum bisa dipastikan.',
 NEED:'Kebutuhan sekarang lebih kecil dari jumlah potong rencana.',
 CAPACITY:'Kapasitas potong yang tersisa tidak cukup, atau kalendernya sudah lewat.',
}
