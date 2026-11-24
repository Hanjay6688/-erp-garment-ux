import {parseSingleTargetDemandHistory,type NativeDemandHistory,type NativeDemandQuery} from './nativeDemandHistory'
import {parseModelQuery,type NativeModelQuery} from './nativeModelEvaluation'
import {parseModelV2Run,type ModelV2Run} from './nativeModelEvaluationV2'

export const scopedHistoryMethod='erp_cp7_capture_model_history_v1' as const
export const scopedModelMethod='erp_cp7_capture_model_evaluation_v3' as const
export type ScopedHistoryQuery=NativeDemandQuery&{target_key:string}
export type ScopedHistoryRequest={requestId:string;actor:string;method:typeof scopedHistoryMethod;query:ScopedHistoryQuery}
export type ScopedModelRequest={requestId:string;actor:string;method:typeof scopedModelMethod;query:NativeModelQuery}
export type ScopedHistoryRun={runId:string;requestId:string;actor:string;query:ScopedHistoryQuery;history:NativeDemandHistory;checkedAt:string;reason:string;immutableSignature:string}
export type ScopedModelRun=ModelV2Run&{runtime:'SCOPED_V3'}
type Obj=Record<string,unknown>
const fail=():never=>{throw Error('Riwayat atau evaluasi produk belum dapat dipastikan. Periksa permintaan yang sama.')}
const object=(x:unknown):Obj=>x&&typeof x==='object'&&!Array.isArray(x)?x as Obj:fail()
const closed=(x:unknown,keys:string[])=>{const o=object(x);if(Object.keys(o).sort().join('|')!==[...keys].sort().join('|'))fail();return o}
const uuid=(x:unknown)=>typeof x==='string'&&/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/.test(x)?x:fail()
const hash=(x:unknown)=>typeof x==='string'&&/^[0-9a-f]{64}$/.test(x)?x:fail()
const day=(x:unknown)=>typeof x==='string'&&/^\d{4}-\d{2}-\d{2}$/.test(x)&&Number.isFinite(Date.parse(x))&&new Date(x).toISOString().slice(0,10)===x?x:fail()
const instant=(x:unknown)=>typeof x==='string'&&/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{6}Z$/.test(x)&&Number.isFinite(Date.parse(x))?x:fail()
const micros=(x:unknown)=>{const s=instant(x);return BigInt(Date.parse(s.slice(0,19)+'Z'))*1000n+BigInt(s.slice(20,26))}
const canonical=(x:unknown):string=>JSON.stringify(x,(_key,v)=>v&&typeof v==='object'&&!Array.isArray(v)?Object.fromEntries(Object.entries(v).sort(([a],[b])=>a.localeCompare(b))):v)
export function parseScopedHistoryQuery(value:unknown):ScopedHistoryQuery{
 const q=closed(value,['target_key','from_date','through_date','group_mode'])
 const target=typeof q.target_key==='string'?q.target_key:fail();const parts=target.split(':');if(parts.length!==2)fail();parts.forEach(uuid)
 const from=day(q.from_date),through=day(q.through_date)
 if(from>through||(Date.parse(through)-Date.parse(from))/86400000>365||!['AS_SOLD','RESTATED'].includes(String(q.group_mode)))fail()
 return{target_key:target,from_date:from,through_date:through,group_mode:q.group_mode as NativeDemandQuery['group_mode']}
}
export function parseScopedHistoryRequest(value:unknown,actor:string):ScopedHistoryRequest{
 const r=closed(value,['requestId','actor','method','query']);if(r.method!==scopedHistoryMethod||uuid(r.actor)!==uuid(actor))fail()
 return{requestId:uuid(r.requestId),actor,method:scopedHistoryMethod,query:parseScopedHistoryQuery(r.query)}
}
export function parseScopedModelRequest(value:unknown,actor:string):ScopedModelRequest{
 const r=closed(value,['requestId','actor','method','query']);if(r.method!==scopedModelMethod||uuid(r.actor)!==uuid(actor))fail()
 return{requestId:uuid(r.requestId),actor,method:scopedModelMethod,query:parseModelQuery(r.query)}
}
export function parseScopedHistoryRun(value:unknown,query:ScopedHistoryQuery,actor:string,prior?:ScopedHistoryRun):ScopedHistoryRun{
 const q=parseScopedHistoryQuery(query),v=closed(value,['contract_version','run_id','request_id','actor_scope_id','captured_at','query','history','source_hash','current_guard','model_caller_integrated','production_go'])
 if(v.contract_version!=='cp7.scoped-history-run.v1'||v.actor_scope_id!==uuid(actor)||canonical(parseScopedHistoryQuery(v.query))!==canonical(q)||v.model_caller_integrated!==false||v.production_go!==false)fail()
 const h=closed(v.history,['contract_version','scope','capture_complete','target_key','raw_capture_status','raw_status_overridden','captured_at','source_hash','history','current_stock','availability_knowledge_basis','training_known_at','model_eligibility','versions','production_go'])
 if(h.target_key!==q.target_key||h.source_hash!==hash(v.source_hash)||h.captured_at!==instant(v.captured_at)||!['COMPLETE','INCOMPLETE'].includes(String(h.raw_capture_status))||h.raw_status_overridden!==false)fail()
 const g=closed(v.current_guard,['source_state','reason','checked_at','live_source_hash','engine_hash'])
 hash(g.engine_hash);const checkedAt=instant(g.checked_at);if(micros(checkedAt)<micros(v.captured_at))fail()
 if(g.source_state==='UNCHANGED'){
  if(g.reason!=='CURRENT_SCOPED_SOURCE_AND_ENGINE'||g.live_source_hash!==v.source_hash)fail()
 }else if(g.source_state==='ARCHIVED_STALE'){
  if(g.reason==='CURRENT_SCOPED_SOURCE_UNAVAILABLE'){if(g.live_source_hash!==null)fail()}
  else if(g.reason==='CURRENT_SCOPED_SOURCE_CHANGED'){if(hash(g.live_source_hash)===v.source_hash)fail()}
  else if(g.reason==='HISTORY_RUNTIME_ENGINE_CHANGED'){if(g.live_source_hash!==v.source_hash)fail()}
  else fail()
 }else fail()
 const history=parseSingleTargetDemandHistory({...h,run_id:v.run_id,request_id:v.request_id,source_state:g.source_state})
 if(history.from!==q.from_date||history.through!==q.through_date||history.basis!==q.group_mode)fail()
 const {current_guard:_guard,...archive}=v,immutableSignature=canonical(archive)
 if(prior&&(prior.actor!==actor||prior.immutableSignature!==immutableSignature||canonical(prior.query)!==canonical(q)))fail()
 return{runId:uuid(v.run_id),requestId:uuid(v.request_id),actor,query:q,history,checkedAt,reason:g.reason as string,immutableSignature}
}
export function parseScopedModelRun(value:unknown,query:NativeModelQuery,actor:string,prior?:ScopedModelRun):ScopedModelRun{
 const v=closed(value,['contract_version','run_id','request_id','actor_scope_id','captured_at','query','assessment','current_guard','history_scope','forecast_applied','production_go'])
 if(v.contract_version!=='cp7.scoped-model-run.v3'||v.history_scope!=='SINGLE_CURRENT_PHYSICAL_ROOT'||prior&&prior.runtime!=='SCOPED_V3')fail()
 // v3 explicitly retains the exact reviewed v2 assessment/guard contract.
 // Check the v3 envelope first; never accept a v2 response at a v3 method.
 const {history_scope:_scope,...sameAssessment}=v
 return{...parseModelV2Run({...sameAssessment,contract_version:'cp7.native-model-run.v2'},query,actor,prior),runtime:'SCOPED_V3'}
}
type Reply={data:unknown;error:unknown}
type Client={rpc(name:typeof scopedHistoryMethod|typeof scopedModelMethod,args:{p_query:ScopedHistoryQuery|NativeModelQuery;p_request:string}):PromiseLike<Reply>;rpc(name:'erp_cp7_read_model_history_v1'|'erp_cp7_read_model_evaluation_v3',args:{p_run:string}):PromiseLike<Reply>}
export async function captureScopedHistory(client:unknown,request:ScopedHistoryRequest){const r=parseScopedHistoryRequest(request,request.actor),reply=await(client as Client).rpc('erp_cp7_capture_model_history_v1',{p_query:structuredClone(r.query),p_request:r.requestId});if(reply.error)throw reply.error;const out=parseScopedHistoryRun(reply.data,r.query,r.actor);if(out.requestId!==r.requestId)fail();return out}
export async function readScopedHistory(client:unknown,prior:ScopedHistoryRun){const reply=await(client as Client).rpc('erp_cp7_read_model_history_v1',{p_run:prior.runId});if(reply.error)throw reply.error;return parseScopedHistoryRun(reply.data,prior.query,prior.actor,prior)}
export async function captureScopedModel(client:unknown,request:ScopedModelRequest){const r=parseScopedModelRequest(request,request.actor),reply=await(client as Client).rpc('erp_cp7_capture_model_evaluation_v3',{p_query:structuredClone(r.query),p_request:r.requestId});if(reply.error)throw reply.error;const out=parseScopedModelRun(reply.data,r.query,r.actor);if(out.requestId!==r.requestId)fail();return out}
export async function readScopedModel(client:unknown,prior:ScopedModelRun){const reply=await(client as Client).rpc('erp_cp7_read_model_evaluation_v3',{p_run:prior.runId});if(reply.error)throw reply.error;return parseScopedModelRun(reply.data,prior.query,prior.actor,prior)}
function recovery<T extends ScopedHistoryRequest|ScopedModelRequest>(prefix:string,parse:(value:unknown,actor:string)=>T){
 const key=(scope:string)=>prefix+scope
 const read=(scope:string,actor:string):{pending:T|null;error:string}=>{try{const raw=localStorage.getItem(key(scope));return{pending:raw===null?null:parse(JSON.parse(raw),actor),error:''}}catch{return{pending:null,error:'Catatan permintaan produk belum dapat dibaca. Pulihkan catatan sebelum membuat permintaan baru.'}}}
 const persist=(scope:string,request:T)=>{const r=parse(request,request.actor),held=read(scope,r.actor);if(held.pending||held.error)throw Error('Pastikan permintaan produk sebelumnya terlebih dahulu.');const raw=JSON.stringify(r);localStorage.setItem(key(scope),raw);if(localStorage.getItem(key(scope))!==raw)throw Error('Permintaan belum tersimpan di perangkat. Data belum dikirim.')}
 const clear=(scope:string,request:T)=>{const held=read(scope,request.actor);if(held.error||canonical(held.pending)!==canonical(request))throw Error('Catatan permintaan berubah. Periksa hasil permintaan yang sama.');localStorage.removeItem(key(scope));if(localStorage.getItem(key(scope))!==null)throw Error('Catatan permintaan belum dapat diselesaikan.')}
 return{key,read,persist,clear}
}
export const scopedHistoryRecovery=recovery('erp.cp7.scoped-history-request.v1:',parseScopedHistoryRequest)
export const scopedModelRecovery=recovery('erp.cp7.scoped-model-request.v3:',parseScopedModelRequest)
