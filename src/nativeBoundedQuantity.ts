import type {BoundedAnalysisRequest} from './nativeBoundedAnalysis'
import {requestBoundedAnalysis} from './nativeBoundedAnalysis'
import {driveStagedJob,type StagedDriveOptions,type StagedJob} from './nativeStagedJob'
import {parseAnalysisPageSet,parseAnalysisHeader,parseAnalysisPage,parseStagedSourceCheck,stagedInstant,type StagedAnalysis,type AnalysisPage,type StagedReference} from './nativeAnalysisPages'

type Reply={data:unknown;error:unknown}
// A owns generated types and the shared RPC registry. Expose exactly the
// existing read/step/page/check facades; no general RPC or table access.
type QuantityClient={
 rpc(name:'erp_cp7_get_staged_analysis_v1'|'erp_cp7_step_staged_analysis_v1',args:{p_request:string}):PromiseLike<Reply>
 rpc(name:'erp_cp7_read_staged_analysis_pages_v1'|'erp_cp7_check_staged_analysis_source_v1',args:{p_run:string}):PromiseLike<Reply>
 rpc(name:'erp_cp7_read_staged_analysis_page_v1',args:{p_run:string;p_index:number;p_access_epoch:string}):PromiseLike<Reply>
}
const data=(reply:Reply)=>{if(reply.error)throw reply.error;return reply.data}
const utcMicrosecond=(value:string)=>{
 const utc=stagedInstant(value).replace(/\+00:00$/,'Z');if(!utc.endsWith('Z'))throw Error('Waktu sumber analisis berubah.')
 const[s,f='']=utc.slice(0,-1).split('.');return s+'.'+f.padEnd(6,'0')+'Z'
}
export function sameBoundedReference(a:StagedReference,b:StagedReference){return a.sourceHash===b.sourceHash&&utcMicrosecond(a.capturedAt)===utcMicrosecond(b.capturedAt)}
export function driveBoundedQuantity(client:unknown,request:BoundedAnalysisRequest,options:Omit<StagedDriveOptions,'rpc'|'request'>){
 const c=client as QuantityClient
 return driveStagedJob({...options,request:{id:request.id,q:request.q},rpc:{
  request:async()=>requestBoundedAnalysis(client,request),
  get:async id=>c.rpc('erp_cp7_get_staged_analysis_v1',{p_request:id}),
  step:async id=>c.rpc('erp_cp7_step_staged_analysis_v1',{p_request:id}),
 }})
}
export async function readBoundedQuantity(client:unknown,request:BoundedAnalysisRequest,job:StagedJob,actor:string):Promise<StagedAnalysis>{
 if(job.requestId!==request.id||job.state!=='DONE'||!job.runId||job.retention?.state==='EXPIRED')throw Error('Hasil perhitungan belum selesai atau sudah kedaluwarsa.')
 const c=client as QuantityClient,set=await parseAnalysisPageSet(data(await c.rpc('erp_cp7_read_staged_analysis_pages_v1',{p_run:job.runId})),job.runId,request.id)
 if(!sameBoundedReference(set.reference,job.reference)||set.targetsTotal!==job.targetsTotal)throw Error('Acuan halaman analisis berubah. Ulangi permintaan tersimpan.')
 const header=await parseAnalysisHeader(set,request.q,actor,{ownerReports:false,preflight:false})
 return{kind:'STAGED',set,header}
}
export async function readBoundedQuantityPage(client:unknown,staged:StagedAnalysis,index:number):Promise<AnalysisPage>{
 if(!Number.isSafeInteger(index)||index<0||index>=staged.set.pageCount)throw Error('Halaman target tidak tersedia.')
 const c=client as QuantityClient
 return parseAnalysisPage(data(await c.rpc('erp_cp7_read_staged_analysis_page_v1',{p_run:staged.set.runId,p_index:index,p_access_epoch:staged.set.accessEpoch})),staged.set,staged.header,index)
}
export async function checkBoundedQuantity(client:unknown,runId:string){
 const c=client as QuantityClient
 return parseStagedSourceCheck(data(await c.rpc('erp_cp7_check_staged_analysis_source_v1',{p_run:runId})),runId)
}
