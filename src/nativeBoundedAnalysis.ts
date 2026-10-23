import type {NativeDemandQuery} from './nativeDemandHistory'

export const BOUNDED_ANALYSIS_REQUEST='cp7.bounded-analysis-request.v1'
export const BOUNDED_ANALYSIS_REFERENCE='cp7.bounded-analysis-reference.v1'
export type BoundedAnalysisRequest={id:string;q:NativeDemandQuery;method:typeof BOUNDED_ANALYSIS_REQUEST}
export type StagedSourceMethod='NATIVE'|'BOUNDED'

const invalid=():never=>{throw Error('Catatan permintaan analisis berubah. Pulihkan catatan asal sebelum mencoba lagi.')}
const object=(v:unknown):Record<string,unknown>=>v!==null&&typeof v==='object'&&!Array.isArray(v)?v as Record<string,unknown>:invalid()
const exact=(v:Record<string,unknown>,keys:string[])=>{if(Object.keys(v).sort().join('|')!==keys.sort().join('|'))invalid()}
function day(v:unknown):string{if(typeof v!=='string'||!/^\d{4}-\d{2}-\d{2}$/.test(v)||!Number.isFinite(Date.parse(v))||new Date(v).toISOString().slice(0,10)!==v)return invalid();return v}
function parse(raw:unknown):BoundedAnalysisRequest{
 const v=object(raw),q=object(v.q);exact(v,['id','q','method']);exact(q,['from_date','through_date','group_mode'])
 if(typeof v.id!=='string'||! /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/.test(v.id)||v.method!==BOUNDED_ANALYSIS_REQUEST||q.group_mode!=='AS_SOLD'&&q.group_mode!=='RESTATED')return invalid()
 const from=day(q.from_date),through=day(q.through_date);if(from>through)invalid()
 return{id:v.id,q:{from_date:from,through_date:through,group_mode:q.group_mode},method:BOUNDED_ANALYSIS_REQUEST}
}
export const boundedAnalysisRequestKey=(scope:string)=>'erp.cp7.bounded-analysis-request.v1:'+scope
export function readBoundedAnalysisRequest(scope:string):{pending:BoundedAnalysisRequest|null;error:string}{
 try{const raw=localStorage.getItem(boundedAnalysisRequestKey(scope));return{pending:raw===null?null:parse(JSON.parse(raw)),error:''}}
 catch{return{pending:null,error:'Permintaan analisis tersimpan belum bisa dibaca. Pulihkan catatan sebelum membuat permintaan baru.'}}
}
export function persistBoundedAnalysisRequest(scope:string,request:BoundedAnalysisRequest){
 const held=readBoundedAnalysisRequest(scope);if(held.error||held.pending)throw Error('Pastikan hasil permintaan analisis tersimpan terlebih dahulu.')
 const parsed=parse(request),raw=JSON.stringify(parsed);localStorage.setItem(boundedAnalysisRequestKey(scope),raw)
 if(localStorage.getItem(boundedAnalysisRequestKey(scope))!==raw||JSON.stringify(readBoundedAnalysisRequest(scope).pending)!==raw)throw Error('Permintaan belum tersimpan. Periksa penyimpanan sebelum mencoba lagi.')
}
export function clearBoundedAnalysisRequest(scope:string,expected:BoundedAnalysisRequest){
 const held=readBoundedAnalysisRequest(scope);if(held.error||JSON.stringify(held.pending)!==JSON.stringify(parse(expected)))throw Error('Catatan permintaan berubah. Ulangi permintaan tersimpan yang sama.')
 localStorage.removeItem(boundedAnalysisRequestKey(scope));if(localStorage.getItem(boundedAnalysisRequestKey(scope))!==null)throw Error('Catatan permintaan belum bisa diselesaikan.')
}
// A deliberately new calculation replaces the verified finished pointer in
// one storage write. A failed write leaves the old request recoverable.
export function replaceBoundedAnalysisRequest(scope:string,expected:BoundedAnalysisRequest,next:BoundedAnalysisRequest){
 const held=readBoundedAnalysisRequest(scope);if(held.error||JSON.stringify(held.pending)!==JSON.stringify(parse(expected)))throw Error('Catatan permintaan berubah. Ulangi permintaan tersimpan yang sama.')
 if(next.id===expected.id)throw Error('Perhitungan baru harus memakai nomor permintaan baru.')
 const raw=JSON.stringify(parse(next));localStorage.setItem(boundedAnalysisRequestKey(scope),raw)
 if(localStorage.getItem(boundedAnalysisRequestKey(scope))!==raw)throw Error('Permintaan baru belum tersimpan. Periksa penyimpanan.')
}
// Only this reviewed new facade is exposed; A owns generated types/registry.
type BoundedAnalysisClient={rpc(name:'erp_cp7_request_bounded_staged_analysis_v1',args:{p_query:NativeDemandQuery;p_request:string}):PromiseLike<{data:unknown;error:unknown}>}
export async function requestBoundedAnalysis(client:unknown,request:BoundedAnalysisRequest){
 const checked=parse(request)
 return await(client as BoundedAnalysisClient).rpc('erp_cp7_request_bounded_staged_analysis_v1',{p_query:checked.q,p_request:checked.id})
}
