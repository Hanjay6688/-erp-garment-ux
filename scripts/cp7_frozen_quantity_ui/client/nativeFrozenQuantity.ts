import {FROZEN_ANALYSIS_REQUEST,frozenAnalysisRequestKey,readFrozenAnalysisRequest,type FrozenAnalysisRequest} from '../../cp7_frozen_analysis_facade_v2/client/nativeFrozenAnalysis'
import {driveStagedJob,parseStagedJob,type StagedDriveOptions,type StagedJob} from '../../../src/nativeStagedJob'
import {parseAnalysisPageSet,parseAnalysisHeader,parseAnalysisPage,parseStagedSourceCheck,type StagedAnalysis} from '../../../src/nativeAnalysisPages'
import {sameBoundedReference} from '../../../src/nativeBoundedQuantity'
import type {StagedPlanContext} from '../../../src/nativePlanDraft'
import {analogReadContext,type AnalogReadContext} from '../../../src/nativeProductAnalog'

export type FrozenQuantitySession={actor:string;scope:string;request:FrozenAnalysisRequest}
type Reply={data:unknown;error:unknown}
type Client={
 rpc(name:'erp_cp7_request_bounded_staged_analysis_v2',args:{p_request:string;p_query:FrozenAnalysisRequest['q']}):PromiseLike<Reply>
 rpc(name:'erp_cp7_get_staged_analysis_v1'|'erp_cp7_step_staged_analysis_v1',args:{p_request:string}):PromiseLike<Reply>
 rpc(name:'erp_cp7_read_staged_analysis_pages_v1'|'erp_cp7_check_staged_analysis_source_v1',args:{p_run:string}):PromiseLike<Reply>
 rpc(name:'erp_cp7_read_staged_analysis_page_v1',args:{p_run:string;p_index:number;p_access:string}):PromiseLike<Reply>
}
const fail=():never=>{throw Error('Acuan permintaan tersimpan berubah. Buka kembali perhitungan tersimpan yang sama.')}
const data=(reply:Reply)=>{if(reply.error)throw reply.error;return reply.data}
const key=(s:FrozenQuantitySession)=>JSON.stringify([s.actor,s.scope,s.request.id,s.request.method,s.request.q.from_date,s.request.q.through_date,s.request.q.group_mode])
function retained(s:FrozenQuantitySession){
 const held=readFrozenAnalysisRequest(s.actor,s.scope),r=s.request,p=held.pending
 if(held.error||!p||r.actor!==s.actor||r.method!==FROZEN_ANALYSIS_REQUEST||key({...s,request:p})!==key(s))return fail()
 return p
}
// Same actor/scope Web Lock as create/replace/recovery. In-flight reads and
// units cannot accidentally follow a competing tab's replacement UUID.
async function locked<T>(s:FrozenQuantitySession,action:(r:FrozenAnalysisRequest)=>Promise<T>):Promise<T>{
 const locks=globalThis.navigator?.locks
 if(!locks)throw Error('Penyimpanan permintaan belum dapat dikunci. Buka kembali aplikasi pada peramban yang mendukung penguncian.')
 return locks.request(frozenAnalysisRequestKey(s.actor,s.scope),{mode:'exclusive'},async()=>{
  const original=key(s),r=retained(s),out=await action(r)
  if(key(s)!==original)fail();retained(s);return out
 })
}
// Always re-enter the explicit v2 idempotent request, including reload. The
// shared get/status response does not attest the stored method by itself.
export function driveFrozenQuantity(client:unknown,s:FrozenQuantitySession,options:Omit<StagedDriveOptions,'rpc'|'request'|'start'>){
 const c=client as Client
 return driveStagedJob({...options,start:true,request:{id:s.request.id,q:s.request.q},rpc:{
  request:async()=>locked(s,async r=>await c.rpc('erp_cp7_request_bounded_staged_analysis_v2',{p_request:r.id,p_query:r.q})),
  get:async()=>locked(s,async r=>await c.rpc('erp_cp7_get_staged_analysis_v1',{p_request:r.id})),
  step:async()=>locked(s,async r=>await c.rpc('erp_cp7_step_staged_analysis_v1',{p_request:r.id})),
 }})
}
const admitted=new WeakMap<StagedAnalysis,string>()
const binding=(s:FrozenQuantitySession,v:StagedAnalysis)=>JSON.stringify([key(s),v.set.requestId,v.set.runId,v.set.identityHash,v.set.accessEpoch,v.set.reference,v.header.query])
function checked(s:FrozenQuantitySession,v:StagedAnalysis){
 retained(s)
 if(v.set.requestId!==s.request.id||admitted.get(v)!==binding(s,v))fail()
}
export async function readFrozenQuantity(client:unknown,s:FrozenQuantitySession,job:StagedJob):Promise<StagedAnalysis>{
 if(job.requestId!==s.request.id||job.state!=='DONE'||!job.runId||job.retention?.state==='EXPIRED')throw Error('Hasil perhitungan belum selesai atau sudah kedaluwarsa.')
 const c=client as Client
 return locked(s,async r=>{
  // A caller cannot relabel an old-method DONE job. The server must accept
  // this exact v2 method/query/UUID again before any page is requested.
  const current=parseStagedJob(data(await c.rpc('erp_cp7_request_bounded_staged_analysis_v2',{p_request:r.id,p_query:r.q})),r.id,{id:r.id,q:r.q})
  if(current.state!=='DONE'||current.retention?.state==='EXPIRED'||current.runId!==job.runId||current.targetsTotal!==job.targetsTotal||!sameBoundedReference(current.reference,job.reference))fail()
  const set=await parseAnalysisPageSet(data(await c.rpc('erp_cp7_read_staged_analysis_pages_v1',{p_run:current.runId!})),current.runId!,r.id)
  if(set.targetsTotal!==current.targetsTotal||!sameBoundedReference(set.reference,current.reference))fail()
  const header=await parseAnalysisHeader(set,r.q,s.actor,{ownerReports:false,preflight:false})
  const out:StagedAnalysis={kind:'STAGED',set,header};admitted.set(out,binding(s,out));return out
 })
}
export async function readFrozenQuantityPage(client:unknown,s:FrozenQuantitySession,v:StagedAnalysis,index:number){
 checked(s,v)
 if(!Number.isSafeInteger(index)||index<0||index>=v.set.pageCount)throw Error('Halaman target tidak tersedia.')
 return locked(s,async()=>{
  checked(s,v)
  const reply=await(client as Client).rpc('erp_cp7_read_staged_analysis_page_v1',{p_run:v.set.runId,p_index:index,p_access:v.set.accessEpoch})
  return parseAnalysisPage(data(reply),v.set,v.header,index)
 })
}
export async function checkFrozenQuantity(client:unknown,s:FrozenQuantitySession,v:StagedAnalysis){
 checked(s,v)
 return locked(s,async()=>{checked(s,v);return parseStagedSourceCheck(data(await(client as Client).rpc('erp_cp7_check_staged_analysis_source_v1',{p_run:v.set.runId})),v.set.runId)})
}
export function frozenQuantityAnalogContext(s:FrozenQuantitySession,v:StagedAnalysis,targetKey:string):AnalogReadContext{
 checked(s,v)
 if(!v.header.labels.some(p=>p.key===targetKey))fail()
 return{...analogReadContext(v,s.actor,targetKey),sourceMethod:'FROZEN_V2'}
}

// Optional prepared cutting host only. Admission belongs to the real v2 read;
// the ordinary dated-plan form receives its exact verified identity and clock.
export function frozenQuantityCuttingContext(s:FrozenQuantitySession,v:StagedAnalysis,targetKey:string):StagedPlanContext{
 checked(s,v)
 if(!v.header.labels.some(p=>p.key===targetKey))fail()
 return{kind:'STAGED',runId:v.set.runId,targetKey,identityHash:v.set.identityHash,dataAsOf:v.set.reference.capturedAt}
}
