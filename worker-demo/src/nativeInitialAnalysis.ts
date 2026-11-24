import type {NativeDemandQuery,NativeDemandRow} from './nativeDemandHistory'
import type {SupabaseClient} from '@supabase/supabase-js'
import type {Json,PreconnectDatabase} from './types/database.preconnect'
import {stagedInstant} from './nativeAnalysisPages'
import {parseStagedJob,readStagedRequest,persistStagedRequest,type StagedJob,type StagedRequest} from './nativeStagedJob'

export type InitialProduct=Pick<NativeDemandRow,'rootId'|'sizeId'|'sku'|'productName'>&{productId:string;profileReady:boolean}
export type InitialReason='NO_ACTIVE_PRODUCTS'|'PLANNING_PROFILE_INCOMPLETE'|'SOURCE_INCOMPLETE'
export type InitialAnalysis={actor:string;checkedAt:string;state:'NOT_READY'|'READY'|'BUSY'|'RUNNING'|'DONE'|'FAILED'|'EXPIRED';
 ready:boolean;reasons:InitialReason[];productsTotal:number;activeProducts:number;eligibleTargets:number;candidates:InitialProduct[];
 query:NativeDemandQuery;semanticHash:string;jobQuery:NativeDemandQuery|null;jobSemanticHash:string|null;sourceChanged:boolean;job:StagedJob|null}
type InitialDatabase={public:Omit<PreconnectDatabase['public'],'Functions'>&{Functions:
 Omit<PreconnectDatabase['public']['Functions'],'erp_cp7_request_staged_analysis_v1'>&{
  erp_cp7_request_staged_analysis_v1:{Args:{p_query:Json;p_request:string|null};Returns:Json}
 }}}
// The server's additive initial mode deliberately requires a null request
// UUID. A owns folding this nullable signature into the shared client types.
export const initialAnalysisClient=(client:SupabaseClient<PreconnectDatabase>)=>client as unknown as SupabaseClient<InitialDatabase>
function fail():never{throw Error('Status analisis awal server belum sesuai. Muat ulang status.')}
const obj=(v:unknown):Record<string,unknown>=>v!==null&&typeof v==='object'&&!Array.isArray(v)?v as Record<string,unknown>:fail()
const closed=(v:unknown,keys:string[])=>{const o=obj(v);if(keys.some(k=>!Object.hasOwn(o,k))||Object.keys(o).some(k=>!keys.includes(k)))fail();return o}
const uuid=(v:unknown)=>typeof v==='string'&&/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/.test(v)?v:fail()
const hash=(v:unknown)=>typeof v==='string'&&/^[0-9a-f]{64}$/.test(v)?v:fail()
const text=(v:unknown)=>typeof v==='string'&&v.length>0&&v.length<=2000?v:fail()
const count=(v:unknown,max:number)=>typeof v==='number'&&Number.isSafeInteger(v)&&v>=0&&v<=max?v:fail()
const boolean=(v:unknown)=>typeof v==='boolean'?v:fail()
function day(v:unknown):string{
 if(typeof v!=='string'||!/^\d{4}-\d{2}-\d{2}$/.test(v))fail()
 const stamp=Date.parse(v+'T00:00:00Z')
 if(!Number.isFinite(stamp)||new Date(stamp).toISOString().slice(0,10)!==v)fail()
 return v
}
function query(v:unknown):NativeDemandQuery{
 const q=closed(v,['from_date','through_date','group_mode'])
 const from=day(q.from_date),through=day(q.through_date)
 if(from>through||q.group_mode!=='AS_SOLD'||Date.parse(through+'T00:00:00Z')-Date.parse(from+'T00:00:00Z')>3660*86400000)fail()
 return{from_date:from,through_date:through,group_mode:'AS_SOLD'}
}
const reasons:InitialReason[]=['NO_ACTIVE_PRODUCTS','PLANNING_PROFILE_INCOMPLETE','SOURCE_INCOMPLETE']
export const initialReasonLabel:Record<InitialReason,string>={NO_ACTIVE_PRODUCTS:'Belum ada produk aktif.',
 PLANNING_PROFILE_INCOMPLETE:'Belum ada produk aktif dengan aturan target yang lengkap dan sesuai versi produknya.',
 SOURCE_INCOMPLETE:'Sumber data belum lengkap atau identitas produknya perlu diperiksa.'}

export function parseInitialAnalysis(v:unknown,actor:string):InitialAnalysis{
 const o=closed(v,['contract_version','actor','checked_at','automatic_scope','state','readiness','query','semantic_hash',
  'job_query','job_semantic_hash','source_changed','job','apply_enabled','production_go'])
 if(o.contract_version!=='cp7.initial-analysis.v1'||uuid(o.actor)!==actor||o.automatic_scope!=='INITIAL_ONCE'||o.apply_enabled!==false||o.production_go!==false)fail()
 const state=o.state;if(state!=='NOT_READY'&&state!=='READY'&&state!=='BUSY'&&state!=='RUNNING'&&state!=='DONE'&&state!=='FAILED'&&state!=='EXPIRED')fail()
 const r=closed(o.readiness,['ready','reasons','products_total','active_products','eligible_targets','candidates','candidate_limit'])
 const ready=boolean(r.ready),productsTotal=count(r.products_total,5001),activeProducts=count(r.active_products,productsTotal),eligibleTargets=count(r.eligible_targets,activeProducts)
 if(!Array.isArray(r.reasons)||r.reasons.some(x=>!reasons.includes(x as InitialReason))||new Set(r.reasons).size!==r.reasons.length)fail()
 const missing=r.reasons as InitialReason[]
 if(ready!==(missing.length===0)||missing.includes('NO_ACTIVE_PRODUCTS')!==(activeProducts===0)
  ||missing.includes('PLANNING_PROFILE_INCOMPLETE')!==(activeProducts>0&&eligibleTargets===0)||ready&&eligibleTargets===0)fail()
 if(r.candidate_limit!==20||!Array.isArray(r.candidates)||r.candidates.length!==Math.min(20,activeProducts))fail()
 const candidates=r.candidates.map(value=>{const p=closed(value,['root_id','product_id','size_id','sku','product_name','profile_ready'])
  return{rootId:uuid(p.root_id),productId:uuid(p.product_id),sizeId:uuid(p.size_id),sku:text(p.sku),productName:text(p.product_name),profileReady:boolean(p.profile_ready)}})
 if(new Set(candidates.map(p=>p.productId)).size!==candidates.length)fail()
 const q=query(o.query),semanticHash=hash(o.semantic_hash),sourceChanged=boolean(o.source_changed)
 let job:StagedJob|null=null,jobQuery:NativeDemandQuery|null=null,jobSemanticHash:string|null=null
 if(o.job===null){
  if(o.job_query!==null||o.job_semantic_hash!==null||sourceChanged||!['NOT_READY','READY','BUSY'].includes(state))fail()
  if(state==='NOT_READY'&&ready||state!=='NOT_READY'&&!ready)fail()
 }else{
  jobQuery=query(o.job_query);jobSemanticHash=hash(o.job_semantic_hash)
  const id=uuid(obj(o.job).request_id);job=parseStagedJob(o.job,id,{id,q:jobQuery,finance:'DEFERRED'})
  if(sourceChanged!==(jobSemanticHash!==semanticHash)||!['RUNNING','DONE','FAILED','EXPIRED'].includes(state))fail()
  if(state==='EXPIRED'?job.retention?.state!=='EXPIRED':job.state!==state||job.retention?.state==='EXPIRED')fail()
  if(!sourceChanged&&JSON.stringify(q)!==JSON.stringify(jobQuery))fail()
 }
 return{actor,checkedAt:stagedInstant(o.checked_at),state,ready,reasons:missing,productsTotal,activeProducts,eligibleTargets,candidates,
  query:q,semanticHash,jobQuery,jobSemanticHash,sourceChanged,job}
}

export function initialStagedRequest(s:InitialAnalysis):StagedRequest{
 if(!s.job||!s.jobQuery||!['RUNNING','DONE'].includes(s.state))throw Error('Hasil analisis awal belum dapat dibuka. Periksa statusnya.')
 return{id:s.job.requestId,q:s.jobQuery,finance:'DEFERRED'}
}

// Adopts a server-created UUID into the existing driver. Never overwrites a
// different pending request and never manufactures or sends another UUID.
export function adoptInitialStagedRequest(scope:string,s:InitialAnalysis):StagedRequest{
 const request=initialStagedRequest(s),held=readStagedRequest(scope)
 if(held.error)throw Error(held.error)
 if(held.pending){
  if(held.pending.id!==request.id||JSON.stringify(held.pending.q)!==JSON.stringify(request.q)||held.pending.finance==='STAGED'){
   throw Error('Selesaikan analisis bertahap yang tersimpan terlebih dahulu. Analisis awal tetap tersedia di server.')
  }
 }else persistStagedRequest(scope,request)
 return request
}
