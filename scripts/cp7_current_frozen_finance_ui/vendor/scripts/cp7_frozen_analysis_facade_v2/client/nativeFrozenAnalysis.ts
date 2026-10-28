// Prepared v2 transport only. No panel/default route adopts this module yet.
import type {NativeDemandQuery} from '../../../src/nativeDemandHistory'

export const FROZEN_ANALYSIS_REQUEST='cp7.bounded-analysis-request.v2'
export const FROZEN_ANALYSIS_REFERENCE='cp7.bounded-analysis-reference.v2'
export type FrozenAnalysisRequest={id:string;actor:string;q:NativeDemandQuery;method:typeof FROZEN_ANALYSIS_REQUEST;finance?:'STAGED'|'DEFERRED'}
export const frozenAnalysisRequestQuery=(r:FrozenAnalysisRequest)=>r.finance?{...r.q,finance_mode:r.finance}:r.q
type FrozenAnalysisClient={rpc(name:'erp_cp7_request_bounded_staged_analysis_v2',args:{p_query:NativeDemandQuery&{finance_mode?:'STAGED'|'DEFERRED'};p_request:string}):PromiseLike<{data:unknown;error:unknown}>}

const invalid=():never=>{throw Error('Catatan permintaan analisis berubah. Pulihkan catatan asal sebelum mencoba lagi.')}
const object=(v:unknown):Record<string,unknown>=>v!==null&&typeof v==='object'&&!Array.isArray(v)?v as Record<string,unknown>:invalid()
const exact=(v:Record<string,unknown>,keys:string[])=>{if(Object.keys(v).sort().join('|')!==[...keys].sort().join('|'))invalid()}
const uuid=(v:unknown)=>typeof v==='string'&&/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/.test(v)?v:invalid()
function day(v:unknown):string{if(typeof v!=='string'||!/^\d{4}-\d{2}-\d{2}$/.test(v)||!Number.isFinite(Date.parse(v))||new Date(v).toISOString().slice(0,10)!==v)return invalid();return v}
function parse(raw:unknown,actor:string):FrozenAnalysisRequest{
 const v=object(raw),q=object(v.q);exact(v,Object.hasOwn(v,'finance')?['id','actor','q','method','finance']:['id','actor','q','method']);exact(q,['from_date','through_date','group_mode'])
 if(Object.hasOwn(v,'finance')&&v.finance!=='STAGED'&&v.finance!=='DEFERRED')return invalid()
 if(uuid(v.actor)!==uuid(actor)||v.method!==FROZEN_ANALYSIS_REQUEST||q.group_mode!=='AS_SOLD'&&q.group_mode!=='RESTATED')return invalid()
 const from=day(q.from_date),through=day(q.through_date);if(from>through)invalid()
 return{id:uuid(v.id),actor,q:{from_date:from,through_date:through,group_mode:q.group_mode},method:FROZEN_ANALYSIS_REQUEST,...(v.finance?{finance:v.finance as 'STAGED'|'DEFERRED'}:{})}
}
export function frozenAnalysisRequestKey(actor:string,scope:string){
 if(typeof scope!=='string'||scope.length===0||scope.length>200)invalid()
 return'erp.cp7.bounded-analysis-request.v2:'+uuid(actor)+':'+encodeURIComponent(scope)
}
export function readFrozenAnalysisRequest(actor:string,scope:string):{pending:FrozenAnalysisRequest|null;error:string}{
 try{const raw=localStorage.getItem(frozenAnalysisRequestKey(actor,scope));return{pending:raw===null?null:parse(JSON.parse(raw),actor),error:''}}
 catch{return{pending:null,error:'Permintaan analisis tersimpan belum bisa dibaca. Pulihkan catatan sebelum membuat permintaan baru.'}}
}
function persistFrozenAnalysisRequestUnlocked(actor:string,scope:string,request:FrozenAnalysisRequest){
 const held=readFrozenAnalysisRequest(actor,scope);if(held.error||held.pending)throw Error('Pastikan hasil permintaan analisis tersimpan terlebih dahulu.')
 const parsed=parse(request,actor),raw=JSON.stringify(parsed),key=frozenAnalysisRequestKey(actor,scope)
 localStorage.setItem(key,raw)
 if(localStorage.getItem(key)!==raw||JSON.stringify(readFrozenAnalysisRequest(actor,scope).pending)!==raw)throw Error('Permintaan belum tersimpan. Periksa penyimpanan sebelum mencoba lagi.')
}
function clearFrozenAnalysisRequestUnlocked(actor:string,scope:string,expected:FrozenAnalysisRequest){
 const held=readFrozenAnalysisRequest(actor,scope)
 if(held.error||JSON.stringify(held.pending)!==JSON.stringify(parse(expected,actor)))throw Error('Catatan permintaan berubah. Ulangi permintaan tersimpan yang sama.')
 const key=frozenAnalysisRequestKey(actor,scope);localStorage.removeItem(key)
 if(localStorage.getItem(key)!==null)throw Error('Catatan permintaan belum bisa diselesaikan.')
}
function replaceFrozenAnalysisRequestUnlocked(actor:string,scope:string,expected:FrozenAnalysisRequest,next:FrozenAnalysisRequest){
 const held=readFrozenAnalysisRequest(actor,scope),before=parse(expected,actor),after=parse(next,actor)
 if(held.error||JSON.stringify(held.pending)!==JSON.stringify(before))throw Error('Catatan permintaan berubah. Ulangi permintaan tersimpan yang sama.')
 if(after.id===before.id)throw Error('Perhitungan baru harus memakai nomor permintaan baru.')
 const raw=JSON.stringify(after),key=frozenAnalysisRequestKey(actor,scope);localStorage.setItem(key,raw)
 if(localStorage.getItem(key)!==raw)throw Error('Permintaan baru belum tersimpan. Periksa penyimpanan.')
}
// Every storage mutation and send in this namespace uses the same browser
// lock across tabs. An in-flight send holds it until completion/rejection;
// a queued recovery attempt then rereads the durable request under the lock.
async function exclusive<T>(actor:string,scope:string,action:()=>T|PromiseLike<T>):Promise<T>{
 const key=frozenAnalysisRequestKey(actor,scope),locks=globalThis.navigator?.locks
 if(!locks)throw Error('Penyimpanan permintaan belum dapat dikunci. Buka kembali aplikasi pada peramban yang mendukung penguncian.')
 return await locks.request(key,{mode:'exclusive'},async()=>await action())
}
export async function persistFrozenAnalysisRequest(actor:string,scope:string,request:FrozenAnalysisRequest){
 return await exclusive(actor,scope,()=>persistFrozenAnalysisRequestUnlocked(actor,scope,request))
}
export async function clearFrozenAnalysisRequest(actor:string,scope:string,expected:FrozenAnalysisRequest){
 return await exclusive(actor,scope,()=>clearFrozenAnalysisRequestUnlocked(actor,scope,expected))
}
export async function replaceFrozenAnalysisRequest(actor:string,scope:string,expected:FrozenAnalysisRequest,next:FrozenAnalysisRequest){
 return await exclusive(actor,scope,()=>replaceFrozenAnalysisRequestUnlocked(actor,scope,expected,next))
}
// Read the durable request immediately before each attempt. The actor stays
// client metadata; the server derives its own current actor and access.
export async function requestFrozenAnalysis(client:unknown,actor:string,scope:string){
 return await exclusive(actor,scope,async()=>{
 const held=readFrozenAnalysisRequest(actor,scope)
 if(held.error||held.pending===null)throw Error('Permintaan belum tersimpan. Periksa penyimpanan sebelum mencoba lagi.')
 const checked=parse(held.pending,actor)
 return await(client as FrozenAnalysisClient).rpc('erp_cp7_request_bounded_staged_analysis_v2',{p_query:frozenAnalysisRequestQuery(checked),p_request:checked.id})
 })
}
