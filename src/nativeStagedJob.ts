import type {NativeDemandQuery} from './nativeDemandHistory'
import {analysisWibClock,analysisWibDate} from './nativeAnalysisTransport'
import {parseStagedReference,stagedInstant,stagedNumber,ANALYSIS_STAGED_TARGETS,type StagedReference} from './nativeAnalysisPages'

// P19 staged job (schema cp7_analysis_stage; P19 plan §10). The job is
// CLIENT-DRIVEN: the page requests it once (a fresh UUID kept per actor and
// query so a reload resumes the same job), then calls step while the server
// says RUNNING, one unit per call under the unchanged 8 s limit. Progress is
// what the server reports from its rows, never a client estimate. A step the
// server skipped because another session holds the job (worker_active) is
// followed by a short wait and a status read instead of another step. The
// loop stops on DONE (then the page set is read) or FAILED (shown with its
// code), and abandons every call when its generation is retired.
export type StagedJobState='RUNNING'|'DONE'|'FAILED'
export type StagedJobFailure={unit:number;sqlstate:string;code:string}
export type StagedJob={requestId:string;state:StagedJobState;stage:string|null;stageIndex:number;stageCount:number;unitsDone:number;unitCount:number;planFinal:boolean
 targetsTotal:number|null;targetsDoneInStage:number;reference:StagedReference;lastProgressAt:string;unitAttempts:number;runId:string|null;failure:StagedJobFailure|null;workerActive:boolean}
export type StagedRequest={id:string;q:NativeDemandQuery}

function fail():never{throw Error('Status analisis bertahap server belum sesuai kontrak CP7.')}
const object=(v:unknown):Record<string,unknown>=>v!==null&&typeof v==='object'&&!Array.isArray(v)?v as Record<string,unknown>:fail()
const uuid=(v:unknown):string=>typeof v==='string'&&/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/.test(v)?v:fail()
const count=(v:unknown,min:number,max:number)=>typeof v==='number'&&Number.isSafeInteger(v)&&v>=min&&v<=max?v:fail()
const REQUIRED=['contract_version','request_id','state','stage','stage_index','stage_count','units_done','unit_count','plan_final','targets_total','targets_done_in_stage','reference','last_progress_at','unit_attempts','apply_enabled','production_go']
// run_id comes only with DONE, failure only with FAILED and worker_active
// only on a skipped step; a field that does not apply is absent or null.
const OPTIONAL=['run_id','failure','worker_active']

export function parseStagedJob(v:unknown,requestId:string):StagedJob{
 const e=object(v),keys=Object.keys(e)
 if(REQUIRED.some(k=>!Object.hasOwn(e,k))||keys.some(k=>!REQUIRED.includes(k)&&!OPTIONAL.includes(k)))fail()
 if(e.contract_version!=='cp7.native-analysis-staged-job.v1'||e.apply_enabled!==false||e.production_go!==false||uuid(e.request_id)!==requestId)fail()
 const state=e.state;if(state!=='RUNNING'&&state!=='DONE'&&state!=='FAILED')fail()
 const unitCount=count(e.unit_count,1,Number.MAX_SAFE_INTEGER),unitsDone=count(e.units_done,0,unitCount),stageCount=count(e.stage_count,1,unitCount),stageIndex=count(e.stage_index,1,stageCount)
 if(typeof e.plan_final!=='boolean')fail()
 const stage=e.stage===null?null:typeof e.stage==='string'&&/^[A-Z][A-Z0-9_]*$/.test(e.stage)?e.stage:fail()
 if(state==='RUNNING'&&stage===null)fail()
 const targetsTotal=e.targets_total===null?null:count(e.targets_total,0,ANALYSIS_STAGED_TARGETS)
 const targetsDoneInStage=count(e.targets_done_in_stage,0,targetsTotal??ANALYSIS_STAGED_TARGETS)
 const reference=parseStagedReference(e.reference),lastProgressAt=stagedInstant(e.last_progress_at),unitAttempts=count(e.unit_attempts,0,Number.MAX_SAFE_INTEGER)
 const runId=state==='DONE'?uuid(e.run_id):e.run_id===undefined||e.run_id===null?null:fail()
 let failure:StagedJobFailure|null=null
 if(state==='FAILED'){
  const f=object(e.failure)
  if(['unit','sqlstate','code'].some(k=>!Object.hasOwn(f,k))||Object.keys(f).some(k=>!['unit','sqlstate','code','message'].includes(k))||typeof f.sqlstate!=='string'||!/^[0-9A-Z]{5}$/.test(f.sqlstate)
   ||typeof f.code!=='string'||!/^CP7_[A-Z0-9_]+$/.test(f.code)||Object.hasOwn(f,'message')&&typeof f.message!=='string')fail()
  failure={unit:count(f.unit,0,unitCount),sqlstate:f.sqlstate,code:f.code}
 }else if(e.failure!==undefined&&e.failure!==null)fail()
 if(state==='DONE'&&(unitsDone!==unitCount||e.plan_final!==true||targetsTotal===null))fail()
 const workerActive=e.worker_active===undefined?false:typeof e.worker_active==='boolean'?e.worker_active:fail()
 return{requestId,state,stage,stageIndex,stageCount,unitsDone,unitCount,planFinal:e.plan_final,targetsTotal,targetsDoneInStage,reference,lastProgressAt,unitAttempts,runId,failure,workerActive}
}

// The staged request is kept apart from the single job's request
// ("erp.cp7.analysis-job.v1:") so a reload resumes the same job UUID; it is
// removed once the job is DONE and its page set loaded, or FAILED and shown.
export const stagedRequestKey=(scope:string)=>scope.endsWith(':completed')?'erp.cp7.analysis-staged-completed.v1:'+scope.slice(0,-10):'erp.cp7.analysis-staged.v1:'+scope
// A small pointer, reverified through get() and the page readers on reopening.
// It is separate from the pending request and never stores analysis bodies.
export const stagedCompletedScope=(scope:string)=>scope+':completed'
const day=(v:unknown)=>typeof v==='string'&&/^\d{4}-\d{2}-\d{2}$/.test(v)&&new Date(v+'T00:00:00Z').toISOString().slice(0,10)===v?v:fail()
const stored=(key:string)=>{try{return localStorage.getItem(key)}catch{return null}}
export function readStagedRequest(scope:string):{pending:StagedRequest|null;error:string}{
 try{
  const raw=localStorage.getItem(stagedRequestKey(scope));if(raw===null)return{pending:null,error:''}
  const v=object(JSON.parse(raw)),q=object(v.q)
  if(Object.keys(v).sort().join('|')!=='id|q'||Object.keys(q).sort().join('|')!=='from_date|group_mode|through_date'||(q.group_mode!=='AS_SOLD'&&q.group_mode!=='RESTATED'))fail()
  const from=day(q.from_date),through=day(q.through_date);if(from>through)fail()
  return{pending:{id:uuid(v.id),q:{from_date:from,through_date:through,group_mode:q.group_mode}},error:''}
 }catch{return{pending:null,error:'Catatan analisis bertahap belum bisa dibaca. Jangan hapus catatan ini; pulihkan penyimpanan sebelum membuat analisis bertahap baru.'}}
}
export function persistStagedRequest(scope:string,r:StagedRequest){
 const before=readStagedRequest(scope);if(before.error||before.pending)throw Error('Selesaikan analisis bertahap yang tersimpan terlebih dahulu.')
 const raw=JSON.stringify({id:r.id,q:r.q});try{localStorage.setItem(stagedRequestKey(scope),raw)}catch{throw Error('Permintaan belum tersimpan. Periksa penyimpanan sebelum mencoba lagi.')}
 if(stored(stagedRequestKey(scope))!==raw||readStagedRequest(scope).pending?.id!==r.id)throw Error('Permintaan belum tersimpan. Periksa penyimpanan sebelum mencoba lagi.')
}
export function persistStagedCompletedRequest(scope:string,r:StagedRequest){
 const target=stagedCompletedScope(scope),key=stagedRequestKey(target)
 if(readStagedRequest(target).error)throw Error('Catatan hasil terakhir belum bisa dibaca. Permintaan aktif tetap disimpan.')
 const raw=JSON.stringify({id:r.id,q:r.q})
 try{localStorage.setItem(key,raw)}catch{throw Error('Hasil terakhir belum tersimpan. Permintaan aktif tetap disimpan.')}
 if(stored(key)!==raw||readStagedRequest(target).pending?.id!==r.id)throw Error('Hasil terakhir belum tersimpan. Permintaan aktif tetap disimpan.')
}
export function clearStagedRequest(scope:string,id:string){
 const held=readStagedRequest(scope);if(held.error||held.pending?.id!==id)throw Error('Catatan analisis bertahap berubah. Periksa analisis bertahap tersimpan.')
 try{localStorage.removeItem(stagedRequestKey(scope))}catch{/* checked below */}
 if(stored(stagedRequestKey(scope))!==null)throw Error('Catatan analisis bertahap belum bisa diselesaikan.')
}

// Refusal codes of the staged job, in the words of the single path's job
// failures where the code is shared; an unknown code is shown as it is.
const failureText:Record<string,string>={
 CP7_ANALYSIS_STAGE_STOPPED:'Unit dihentikan oleh batas waktu server tiga kali berturut-turut. Tidak ada hasil yang disimpan.',
 CP7_ANALYSIS_ACCESS_CHANGED:'Hak akses berubah selama perhitungan. Tidak ada hasil yang disimpan.',
 CP7_ANALYSIS_PAGE_BODY_LIMIT:'Satu target melampaui batas ukuran halaman server dan tidak dipotong. Tidak ada hasil yang disimpan.',
 CP7_ANALYSIS_JOB_ERROR:'Perhitungan gagal di server. Tidak ada hasil yang disimpan.',
 CP7_PLANNING_CAPTURE_INCOMPLETE:'Sumber ERP melampaui batas acuan analisis bertahap dan tidak dipotong. Tidak ada hasil yang disimpan.',
 CP7_NETTING_MATCH_SOURCE_LIMIT:'Sumber pencocokan netting melampaui batas unit server. Tidak ada hasil yang disimpan.',
 CP7_NETTING_WORK_LIMIT:'Beban pencocokan netting melampaui batas unit server. Tidak ada hasil yang disimpan.'}
export const stagedFailureText=(f:StagedJobFailure)=>`Analisis bertahap gagal pada unit ${f.unit} (${f.code}, SQLSTATE ${f.sqlstate}). ${failureText[f.code]??'Server menolak unit ini. Tidak ada hasil yang disimpan.'}`
// "Analisis bertahap: tahap 3 dari 9 (HIST_ROWS) · unit 12 dari 55 · …"
export const stagedProgressText=(j:StagedJob)=>`Analisis bertahap: tahap ${j.stageIndex} dari ${j.stageCount} (${j.stage??'SELESAI'}) · unit ${j.unitsDone} dari ${j.unitCount}`
 +(j.targetsTotal===null?'':` · target ${stagedNumber(j.targetsDoneInStage)} dari ${stagedNumber(j.targetsTotal)} pada tahap ini`)
 +(j.unitAttempts>0?` · percobaan ulang ${j.unitAttempts}`:'')+(j.workerActive?' · sesi lain sedang menjalankan unit':'')
 +` · dimulai jam ${analysisWibClock(j.reference.capturedAt)} WIB (${analysisWibDate(j.reference.capturedAt)}).`
export const stagedPausedText=(j:StagedJob)=>`Analisis bertahap dijeda sejak jam ${analysisWibClock(j.lastProgressAt)} WIB (${analysisWibDate(j.lastProgressAt)}). Lanjutkan untuk meneruskan unit berikutnya; tidak ada hasil yang disimpan sebelum selesai.`
// Refusals of the single path that come from its target count being above
// its bounds (history source 1000 products; netting match/work limits seen
// at 5,000 on CI; grid/scope/allocation bounds): the staged path is offered.
export const STAGED_CAP_REFUSALS=['CP7_PLANNING_CAPTURE_INCOMPLETE','CP7_PLANNING_HISTORY_GRID_LIMIT','CP7_NETTING_MATCH_SOURCE_LIMIT','CP7_NETTING_WORK_LIMIT','CP7_SUPPLY_GLOBAL_SCOPE_LIMIT','CP7_BASELINE_ALLOCATION_LIMIT'] as const
export const stagedCapRefusal=(v:unknown)=>{const e=v!==null&&typeof v==='object'?v as {code?:unknown;message?:unknown}:{};return[e.code,e.message].some(x=>typeof x==='string'&&(STAGED_CAP_REFUSALS as readonly string[]).includes(x))}
export const STAGED_CAP_HINT='Analisis tunggal ditolak karena jumlah target melampaui batasnya. Gunakan "Analisis bertahap (hingga 5.000 target)" untuk kueri yang sama; angka keuangan tidak termasuk.'

export type StagedReply={data:unknown;error:unknown}
export type StagedRpc={request:(r:StagedRequest)=>Promise<StagedReply>;step:(id:string)=>Promise<StagedReply>;get:(id:string)=>Promise<StagedReply>}
export type StagedDriveOptions={rpc:StagedRpc;request:StagedRequest;start:boolean;aborted?:()=>boolean;sleep?:(ms:number)=>Promise<void>;onStatus?:(s:StagedJob)=>void;workerBackoffMs?:number}
export const STAGED_WORKER_BACKOFF_MS=2000
// Returns the final status (DONE or FAILED), or null once aborted; a server
// refusal or a lost reply is thrown with the last known status already
// reported through onStatus, so the caller can show "paused since".
export async function driveStagedJob(o:StagedDriveOptions):Promise<StagedJob|null>{
 const aborted=o.aborted??(()=>false),sleep=o.sleep??(ms=>new Promise<void>(r=>setTimeout(r,ms))),backoff=o.workerBackoffMs??STAGED_WORKER_BACKOFF_MS
 const read=(r:StagedReply)=>{if(r.error)throw r.error;const s=parseStagedJob(r.data,o.request.id);o.onStatus?.(s);return s}
 if(aborted())return null
 const first=await(o.start?o.rpc.request(o.request):o.rpc.get(o.request.id));if(aborted())return null
 let status=read(first)
 while(status.state==='RUNNING'){
  if(aborted())return null
  let reply:StagedReply
  if(status.workerActive){await sleep(backoff);if(aborted())return null;reply=await o.rpc.get(o.request.id)}
  else reply=await o.rpc.step(o.request.id)
  if(aborted())return null
  status=read(reply)
 }
 return status
}
