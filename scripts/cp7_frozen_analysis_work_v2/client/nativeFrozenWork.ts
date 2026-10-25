// Prepared explicit frozen work metadata reader; no UI/default adoption.
import {parseScheduleConfig,STAGED_SCHEDULE_CONTRACT,type ScheduleConfig,type SchedulePayload,type ScheduleWorkspace,type StagedScheduleContext,type WorkPosition} from '../../../src/nativeProductionPlanning'
import type {StagedReference} from '../../../src/nativeAnalysisPages'
import {FROZEN_ANALYSIS_REQUEST,FROZEN_ANALYSIS_REFERENCE} from '../../cp7_frozen_analysis_facade_v2/client/nativeFrozenAnalysis'
export type FrozenWorkContext={requestId:string;reference:StagedReference;runId:string|null;method:'FROZEN_V2'}
export type FrozenScheduleWorkspace=Omit<ScheduleWorkspace,'staged'>&{staged:Omit<StagedScheduleContext,'method'|'inputCoverage'>&{method:'FROZEN_V2';inputCoverage:'PENDING'|'COMPLETE'}}
type SourceState='UNCHANGED'|'ARCHIVED_STALE'
const fail=():never=>{throw Error('Data stok proses atau jadwal dari server berubah atau belum lengkap. Muat ulang sumber.')}
const obj=(v:unknown):Record<string,unknown>=>v&&typeof v==='object'&&!Array.isArray(v)?v as Record<string,unknown>:fail()
const str=(v:unknown)=>typeof v==='string'&&v.length>0&&v.length<=2000?v:fail()
const uuid=(v:unknown)=>typeof v==='string'&&/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/.test(v)?v:fail()
const pcs=(v:unknown)=>typeof v==='string'&&/^(0|[1-9][0-9]{0,33})$/.test(v)?v:fail()
const hash=(v:unknown)=>typeof v==='string'&&/^[0-9a-f]{64}$/.test(v)?v:fail()
const instant=(v:unknown)=>typeof v==='string'&&/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d{1,6})?Z$/.test(v)&&Number.isFinite(Date.parse(v))?v:fail()
const list=(v:unknown,max=1000)=>Array.isArray(v)&&v.length<=max?v:fail()
const state=(v:unknown):SourceState=>v==='UNCHANGED'||v==='ARCHIVED_STALE'?v:fail()
const exact=(v:Record<string,unknown>,keys:string[])=>{if(Object.keys(v).sort().join('|')!==[...keys].sort().join('|'))fail()}
const unique=(keys:string[])=>{if(new Set(keys).size!==keys.length)fail()}
function position(raw:unknown):WorkPosition{
 const p=obj(raw);if(p.ownership!=='COMPANY'&&p.ownership!=='CUSTOMER'||typeof p.eligible_company_wip!=='boolean'||p.ownership==='CUSTOMER'&&p.eligible_company_wip)fail()
 return{key:str(p.key??p.position_key),poolKey:str(p.pool_key),stage:str(p.stage),sizeId:uuid(p.size_id),ownership:p.ownership as WorkPosition['ownership'],eligible:p.eligible_company_wip as boolean,remaining:pcs(p.remaining_pcs)}
}
const referenceUtc=(value:string)=>{
 if(!/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|\+00:00)$/.test(value))fail()
 const utc=value.replace(/\+00:00$/,'Z');instant(utc)
 const [seconds,fraction='']=utc.slice(0,-1).split('.');return seconds+'.'+fraction.padEnd(6,'0')+'Z'
}
export function parseFrozenScheduleWorkspace(raw:unknown,context:FrozenWorkContext):FrozenScheduleWorkspace{
 const{requestId,reference,runId:expectedRun,method}=context
 if(method!=='FROZEN_V2')fail()
 const v=obj(raw);exact(v,['contract_version','source_run','source_request_id','analysis_state','current_source_hash','source_hash','captured_at','staged_review_contract','analysis_source_hash','history_capture_state','production_capture_state','position_requirements','source_state','plan','revision','plan_state','production_go','bounded_request_contract','bounded_reference_contract','history_input_coverage'])
 if(v.contract_version!=='cp7.planning-schedule-staged-bounded.v2'||v.bounded_request_contract!==FROZEN_ANALYSIS_REQUEST||v.bounded_reference_contract!==FROZEN_ANALYSIS_REFERENCE||!['PENDING','COMPLETE'].includes(String(v.history_input_coverage))||v.analysis_state==='DONE'&&v.history_input_coverage!=='COMPLETE'||v.staged_review_contract!==STAGED_SCHEDULE_CONTRACT||v.production_go!==false||uuid(v.source_request_id)!==requestId||hash(v.analysis_source_hash)!==reference.sourceHash||referenceUtc(str(v.captured_at))!==referenceUtc(reference.capturedAt))fail()
 const sourceRun=uuid(v.source_run),sourceHash=hash(v.source_hash),currentHash=hash(v.current_source_hash),capturedAt=instant(v.captured_at),s=state(v.source_state),revision=pcs(v.revision)
 if(expectedRun!==null&&sourceRun!==expectedRun||s==='UNCHANGED'&&sourceHash!==currentHash)fail()
 if(!['RUNNING','DONE','FAILED'].includes(str(v.analysis_state))||!['COMPLETE','INCOMPLETE'].includes(str(v.history_capture_state))||!['COMPLETE','UNKNOWN'].includes(str(v.production_capture_state))||!['UNREVIEWED','SELECTED_ASSUMPTIONS','SOURCE_CHANGED'].includes(str(v.plan_state)))fail()
 let config:ScheduleConfig|null=null
 if(v.plan===null){if(revision!=='0'||v.plan_state!=='UNREVIEWED')fail()}else{const plan=obj(v.plan);uuid(plan.plan_id);uuid(plan.source_run);hash(plan.source_hash);instant(plan.recorded_at);if(plan.revision!==revision||revision==='0'||(plan.source_hash===currentHash)!==(v.plan_state==='SELECTED_ASSUMPTIONS'))fail();config=parseScheduleConfig(plan.config)}
 const requirements=list(v.position_requirements,20000).map(raw=>{const p=obj(raw),r=position(p);if(r.remaining==='0')fail();const route=list(p.remaining_route,5).map(str);unique(route);if(!route.length)fail()
  const targets=list(p.target_candidates,5000).map(raw=>{const t=obj(raw),key=str(t.target_key),parts=key.split(':');if(parts.length!==2||uuid(parts[0])+':'+uuid(parts[1])!==key||parts[1]!==r.sizeId||!r.eligible)fail();return{key,versionId:uuid(t.product_version_id),sku:str(t.sku),name:str(t.product_name)}});unique(targets.map(t=>t.key));return{...r,route,targets}})
 unique(requirements.map(p=>p.key))
 if(v.production_capture_state!=='COMPLETE'&&requirements.length)fail()
 return{sourceRun,sourceHash,currentHash,capturedAt,state:s,revision,planState:v.plan_state as ScheduleWorkspace['planState'],config,requirements,staged:{requestId,analysisHash:reference.sourceHash,analysisState:v.analysis_state as StagedScheduleContext['analysisState'],historyState:v.history_capture_state as StagedScheduleContext['historyState'],productionState:v.production_capture_state as StagedScheduleContext['productionState'],method,inputCoverage:v.history_input_coverage as 'PENDING'|'COMPLETE'}}
}

type Reply={data:unknown;error:unknown}
type FrozenWorkClient={rpc(name:'erp_cp7_get_staged_production_schedule_v1',args:{p_source_request:string}):PromiseLike<Reply>;rpc(name:'erp_cp7_save_staged_production_schedule_v1',args:{p_payload:SchedulePayload;p_request:string}):PromiseLike<Reply>}
export async function readFrozenScheduleWorkspace(client:unknown,context:FrozenWorkContext){
 if(context.method!=='FROZEN_V2')fail();uuid(context.requestId)
 const reply=await(client as FrozenWorkClient).rpc('erp_cp7_get_staged_production_schedule_v1',{p_source_request:context.requestId})
 if(reply.error)throw reply.error
 return parseFrozenScheduleWorkspace(reply.data,context)
}

// The existing public save dispatches by the immutable stored source run.
// A frozen request keeps its own actor/method namespace and requires a v2
// outcome; it is never converted to the old bounded method for recovery.
export type FrozenScheduleRequest={id:string;actor:string;sourceMethod:'FROZEN_V2';sourceRequest:string;reference:StagedReference;payload:SchedulePayload&{staged_review_contract:typeof STAGED_SCHEDULE_CONTRACT}}
const revision=(v:unknown)=>{const n=pcs(v);if(BigInt(n)>=9223372036854775807n)fail();return n}
export function parseFrozenScheduleRequest(raw:unknown,actor:string):FrozenScheduleRequest{
 const r=obj(raw),p=obj(r.payload),ref=obj(r.reference)
 exact(r,['id','actor','sourceMethod','sourceRequest','reference','payload']);exact(ref,['capturedAt','sourceHash'])
 exact(p,['source_run','source_hash','expected_revision','config','reason','staged_review_contract'])
 if(r.sourceMethod!=='FROZEN_V2'||uuid(r.actor)!==uuid(actor)||p.staged_review_contract!==STAGED_SCHEDULE_CONTRACT)fail()
 uuid(r.id);uuid(r.sourceRequest);uuid(p.source_run);hash(p.source_hash);hash(ref.sourceHash);referenceUtc(str(ref.capturedAt));revision(p.expected_revision)
 const reason=str(p.reason);if(reason.trim()!==reason||!reason||Array.from(reason).length>1000)fail()
 parseScheduleConfig(p.config)
 return structuredClone(r)as FrozenScheduleRequest
}
export function prepareFrozenScheduleRequest(w:FrozenScheduleWorkspace,context:FrozenWorkContext,actor:string,config:ScheduleConfig,reason:string,id:string):FrozenScheduleRequest{
 if(context.method!=='FROZEN_V2'||w.staged.method!=='FROZEN_V2'||w.state!=='UNCHANGED'||w.currentHash!==w.sourceHash||w.staged.productionState!=='COMPLETE')fail()
 if(w.staged.requestId!==context.requestId||w.staged.analysisHash!==context.reference.sourceHash||referenceUtc(w.capturedAt)!==referenceUtc(context.reference.capturedAt)||context.runId!==null&&w.sourceRun!==context.runId)fail()
 return parseFrozenScheduleRequest({id,actor,sourceMethod:'FROZEN_V2',sourceRequest:context.requestId,reference:structuredClone(context.reference),payload:{source_run:w.sourceRun,source_hash:w.sourceHash,expected_revision:w.revision,config:parseScheduleConfig(config),reason:reason.trim(),staged_review_contract:STAGED_SCHEDULE_CONTRACT}},actor)
}
export function checkFrozenScheduleOutcome(raw:unknown,request:FrozenScheduleRequest){
 const r=parseFrozenScheduleRequest(request,request.actor),o=obj(raw)
 exact(o,['contract_version','plan_id','revision','source_hash','request_id','quality','staged_review_contract','source_run','production_go','bounded_request_contract','bounded_reference_contract'])
 if(o.contract_version!=='cp7.planning-schedule-staged-bounded-outcome.v2'||o.bounded_request_contract!==FROZEN_ANALYSIS_REQUEST||o.bounded_reference_contract!==FROZEN_ANALYSIS_REFERENCE||o.staged_review_contract!==STAGED_SCHEDULE_CONTRACT||o.request_id!==r.id||o.source_run!==r.payload.source_run||o.source_hash!==r.payload.source_hash||o.quality!=='SELECTED_ASSUMPTIONS'||o.production_go!==false||BigInt(pcs(o.revision))!==BigInt(r.payload.expected_revision)+1n)fail()
 return{planId:uuid(o.plan_id),revision:pcs(o.revision),requestId:r.id,sourceRun:r.payload.source_run,sourceHash:r.payload.source_hash,sourceMethod:'FROZEN_V2' as const}
}
export function frozenScheduleRequestKey(scope:string,actor:string){
 if(typeof scope!=='string'||scope.length<1||scope.length>200)fail()
 return'erp.cp7.schedule-request.v2:'+uuid(actor)+':'+encodeURIComponent(scope)
}
export function readFrozenScheduleRequest(scope:string,actor:string):{pending:FrozenScheduleRequest|null;error:string}{
 try{const raw=localStorage.getItem(frozenScheduleRequestKey(scope,actor));return{pending:raw===null?null:parseFrozenScheduleRequest(JSON.parse(raw),actor),error:''}}
 catch{return{pending:null,error:'Permintaan jadwal tersimpan belum bisa dibaca. Pulihkan catatan sebelum menyimpan lagi.'}}
}
async function exclusive<T>(scope:string,actor:string,action:()=>T|PromiseLike<T>):Promise<T>{
 const key=frozenScheduleRequestKey(scope,actor),locks=globalThis.navigator?.locks
 if(!locks)throw Error('Catatan jadwal belum dapat dikunci. Buka kembali aplikasi pada peramban yang mendukung penguncian.')
 return await locks.request(key,{mode:'exclusive'},async()=>await action())
}
export async function persistFrozenScheduleRequest(scope:string,request:FrozenScheduleRequest){
 const r=parseFrozenScheduleRequest(request,request.actor)
 return await exclusive(scope,r.actor,()=>{
  const held=readFrozenScheduleRequest(scope,r.actor)
  if(held.error||held.pending)throw Error('Pastikan hasil permintaan jadwal tersimpan terlebih dahulu.')
  const key=frozenScheduleRequestKey(scope,r.actor),raw=JSON.stringify(r);localStorage.setItem(key,raw)
  if(localStorage.getItem(key)!==raw)throw Error('Permintaan jadwal belum tersimpan. Penyimpanan belum dikirim.')
 })
}
export async function clearFrozenScheduleRequest(scope:string,request:FrozenScheduleRequest){
 const r=parseFrozenScheduleRequest(request,request.actor)
 return await exclusive(scope,r.actor,()=>{
  const held=readFrozenScheduleRequest(scope,r.actor)
  if(held.error||JSON.stringify(held.pending)!==JSON.stringify(r))throw Error('Catatan permintaan jadwal berubah. Ulangi permintaan yang sama.')
  const key=frozenScheduleRequestKey(scope,r.actor);localStorage.removeItem(key)
  if(localStorage.getItem(key)!==null)throw Error('Catatan jadwal belum dapat diselesaikan.')
 })
}
export async function saveFrozenSchedule(client:unknown,scope:string,actor:string){
 return await exclusive(scope,actor,async()=>{
  const held=readFrozenScheduleRequest(scope,actor)
  if(held.error||!held.pending)throw Error('Permintaan jadwal belum tersimpan. Penyimpanan belum dikirim.')
  const r=held.pending,reply=await(client as FrozenWorkClient).rpc('erp_cp7_save_staged_production_schedule_v1',{p_payload:structuredClone(r.payload),p_request:r.id})
  if(reply.error)throw reply.error
  return checkFrozenScheduleOutcome(reply.data,r)
 })
}
