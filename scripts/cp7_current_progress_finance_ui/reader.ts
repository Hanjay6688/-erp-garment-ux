import {readProgressTelemetry,type ProgressTelemetry} from '../cp7_current_analysis_progress/telemetry'
import {planInstantMicros} from '../cp7_current_frozen_finance_ui/vendor/src/nativePlanInstant'
import type {StagedRequest} from './vendor/src/nativeStagedJob'
import type {StagedReference} from './vendor/src/nativeAnalysisPages'
import {boundedFrozenReply} from './vendor/scripts/cp7_frozen_analysis_facade_v2/client/nativeFrozenWait'

export const PROGRESS_RPC='erp_cp7_get_frozen_analysis_progress_v1'
type Reply={data:unknown;error:unknown}
type Client={rpc(name:typeof PROGRESS_RPC,args:{p_request:string}):PromiseLike<Reply>}
export type Observation={value:ProgressTelemetry|null;error:unknown|null}
export function createProgressReader(client:unknown,request:StagedRequest,reference:StagedReference,current:()=>boolean){
 const bound:StagedRequest={id:request.id,q:{...request.q},...(request.finance?{finance:request.finance}:{})}
 const source={hash:reference.sourceHash,at:planInstantMicros(reference.capturedAt)}
 const listeners=new Set<(state:Observation)=>void>()
 let retired=false,inflight:Promise<ProgressTelemetry>|null=null,observed:bigint|null=null
 let state:Observation={value:null,error:null}
 const active=()=>{if(retired||!current())throw Error('Acuan perhitungan tersimpan berubah. Buka kembali pekerjaan yang sama.')}
 const publish=(next:Observation)=>{state=next;for(const listener of listeners)listener(next)}
 const read=():Promise<ProgressTelemetry>=>{
  try{active()}catch(error){if(!retired)publish({value:null,error});return Promise.reject(error)}
  if(inflight)return inflight
  // Concurrent UI consumers share only an in-flight read. Every later call
  // reaches the current ACL and source checks; no completed-response cache.
  const pending=(async()=>{
   try{
    const reply=await boundedFrozenReply(()=>(client as Client).rpc(PROGRESS_RPC,{p_request:bound.id}))
    active();if(reply.error)throw reply.error
    const value=readProgressTelemetry(reply.data,bound)
    if(value.progress.capturedAt===undefined||value.progress.requestId!==bound.id)throw Error('Acuan kemajuan berubah.')
    const raw=value.originalStatus as {reference?:{source_hash?:unknown;captured_at?:unknown}}
    if(raw.reference?.source_hash!==source.hash||planInstantMicros(raw.reference?.captured_at)!==source.at)throw Error('Sumber kemajuan berbeda dari analisis tersimpan.')
    const stamp=planInstantMicros(value.observedAt)
    if(observed!==null&&stamp<observed)throw Error('Urutan pengamatan server berubah. Periksa kembali status tersimpan.')
    observed=stamp;publish({value,error:null});return value
   }catch(error){if(!retired)publish({value:null,error});throw error}
  })().finally(()=>{if(inflight===pending)inflight=null})
  inflight=pending;return pending
 }
 return{read,subscribe(listener:(value:Observation)=>void){listeners.add(listener);listener(state);return()=>{listeners.delete(listener)}},
  dispose(){retired=true;listeners.clear();state={value:null,error:null}},
  async status(id:string):Promise<Reply>{if(id!==bound.id)throw Error('Identitas laporan berubah.');const value=await read();return{data:value.originalStatus,error:null}}}
}
