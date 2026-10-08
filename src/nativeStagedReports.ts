import type {NativeDemandQuery} from './nativeDemandHistory'
import {stagedInstant,ANALYSIS_STAGED_TARGETS,ANALYSIS_PAGE_UTF8_BYTES} from './nativeAnalysisPages'
import {reportKinds,type ReportKind} from './nativeAnalysisReports'
import {financeDate} from './financeReportContract'

// Business Report v2 (snapshot contract v2 §4, owner decision 8 Oct 2026): a
// report of ONE staged run of the actor. The server builds it one unit per
// request under the unchanged statement limit (ACTUALS: finished stock and,
// when chosen, finance; one SECTION per page of the run; FRESHNESS; SUMMARY)
// and seals it once. The analysis part is the run's snapshot, labelled with
// its time and never called current; actual stock, finance and HPP come from
// the ERP sources at the report date. The client verifies every hash it is
// given (summary, each section, the report hash over both) and never edits
// or recomputes a business number.
export type StagedReportFinance='INCLUDED'|'DEFERRED'
export type StagedReportPayload={run_id:string;identity_hash:string;kind:ReportKind;series_id:string|null;expected_revision:string|null;title:string;reason:string;finance:StagedReportFinance;explicit_review:true}
export type StagedReportRequest={id:string;payload:StagedReportPayload}
export type StagedReportStage='ACTUALS'|'SECTION'|'FRESHNESS'|'SUMMARY'
export type StagedReportJob={requestId:string;state:'RUNNING'|'DONE'|'FAILED'|'CLOSED_UNCOMMITTED';stage:StagedReportStage|null;unitsDone:number;unitCount:number;unitAttempts:number
 sectionsDone:number;sectionCount:number;runId:string;identityHash:string;dataAsOf:string;kind:ReportKind;finance:StagedReportFinance;seriesId:string;revision:string
 lastProgressAt:string;publicationId:string|null;failure:{unit:number;sqlstate:string;code:string}|null;workerActive:boolean}
export type StagedReportFreshnessState='STALE_VERIFIED'|'VERIFIED_SAME'|'CHANGES_RECORDED'|'NO_RECORDED_CHANGE'
export type StagedReportSectionEntry={index:number;targetLo:number;targetHi:number;utf8Bytes:number;sha256:string}
export type StagedReport={id:string;seriesId:string;revision:string;runId:string;requestId:string;identityHash:string;dataAsOf:string;kind:ReportKind;query:NativeDemandQuery
 title:string;reason:string;finance:StagedReportFinance;reportDate:string;actualsReadAt:string;financialSourceHash:string|null
 freshness:{state:StagedReportFreshnessState;evaluatedAt:string;changesTotal:string};targetsTotal:number;summary:string;summarySha256:string
 sections:StagedReportSectionEntry[];reportHash:string;publishedAt:string;isLatest:boolean;accessEpoch:string}
export type StagedReportSection={publicationId:string;index:number;targetLo:number;targetHi:number;body:string;sha256:string}
export type StagedReportPointer={id:string;seriesId:string;revision:string;runId:string;kind:ReportKind;title:string;query:NativeDemandQuery;dataAsOf:string;finance:StagedReportFinance;publishedAt:string;reportHash:string}
export type StagedReportIndex={rows:StagedReportPointer[];total:string;nextBeforeId:string|null}

function fail():never{throw Error('Laporan bertahap dari server belum sesuai kontrak CP7.')}
const obj=(v:unknown):Record<string,unknown>=>v!==null&&typeof v==='object'&&!Array.isArray(v)?v as Record<string,unknown>:fail()
const exact=(v:Record<string,unknown>,keys:readonly string[])=>{if(Object.keys(v).length!==keys.length||keys.some(k=>!Object.hasOwn(v,k)))fail()}
const guid=(v:unknown):v is string=>typeof v==='string'&&/^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/.test(v)
const uuid=(v:unknown):string=>guid(v)?v:fail()
const hex=(v:unknown):string=>typeof v==='string'&&/^[0-9a-f]{64}$/.test(v)?v:fail()
const revision=(v:unknown):v is string=>typeof v==='string'&&/^[1-9][0-9]{0,18}$/.test(v)&&BigInt(v)<=9223372036854775807n
const count=(v:unknown,min:number,max:number)=>typeof v==='number'&&Number.isSafeInteger(v)&&v>=min&&v<=max?v:fail()
const kind=(v:unknown):ReportKind=>reportKinds.includes(v as ReportKind)?v as ReportKind:fail()
const finance=(v:unknown):StagedReportFinance=>v==='INCLUDED'||v==='DEFERRED'?v:fail()
const text=(v:unknown,max:number)=>typeof v==='string'&&v.trim().length>0&&[...v].length<=max?v:fail()
const sha256=async(s:string)=>Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(s))),b=>b.toString(16).padStart(2,'0')).join('')
const bytes=(s:string)=>new TextEncoder().encode(s).byteLength
function query(v:unknown):NativeDemandQuery{const q=obj(v);exact(q,['from_date','through_date','group_mode']);if(!financeDate(q.from_date)||!financeDate(q.through_date)||q.from_date>q.through_date||!['AS_SOLD','RESTATED'].includes(String(q.group_mode)))fail();return{from_date:q.from_date,through_date:q.through_date,group_mode:q.group_mode} as NativeDemandQuery}

export function stagedReportPayload(v:unknown):StagedReportPayload{
 const p=obj(v);exact(p,['run_id','identity_hash','kind','series_id','expected_revision','title','reason','finance','explicit_review'])
 if(!guid(p.run_id)||p.explicit_review!==true||(p.series_id===null?p.expected_revision!==null:!guid(p.series_id)||!revision(p.expected_revision)))fail()
 hex(p.identity_hash);kind(p.kind);finance(p.finance);text(p.title,200);text(p.reason,1000)
 return structuredClone(p) as StagedReportPayload
}

const JOB=['contract_version','request_id','state','stage','units_done','unit_count','unit_attempts','sections_done','section_count','run_id','identity_hash','data_as_of',
 'kind','finance','series_id','revision','last_progress_at','publication_id','failure','production_go']
const STAGES=['ACTUALS','SECTION','FRESHNESS','SUMMARY'] as const
// The job status; the unit plan is fixed: 0 ACTUALS, 1..n SECTION, n+1 FRESHNESS, n+2 SUMMARY.
export function parseStagedReportJob(v:unknown,r:StagedReportRequest):StagedReportJob{
 const e=obj(v),keys=Object.keys(e)
 if(JOB.some(k=>!Object.hasOwn(e,k))||keys.some(k=>!JOB.includes(k)&&k!=='worker_active'))fail()
 if(e.contract_version!=='cp7.report-job.v2'||e.production_go!==false||uuid(e.request_id)!==r.id)fail()
 const state=e.state;if(state!=='RUNNING'&&state!=='DONE'&&state!=='FAILED'&&state!=='CLOSED_UNCOMMITTED')fail()
 const sectionCount=count(e.section_count,0,ANALYSIS_STAGED_TARGETS),unitCount=count(e.unit_count,0,ANALYSIS_STAGED_TARGETS+3),unitsDone=count(e.units_done,0,unitCount)
 if(state==='CLOSED_UNCOMMITTED'?unitCount!==0:unitCount!==sectionCount+3)fail()
 const expect=state==='RUNNING'?(unitsDone===0?'ACTUALS':unitsDone<=sectionCount?'SECTION':unitsDone===sectionCount+1?'FRESHNESS':'SUMMARY'):null
 if(e.stage!==expect||state==='RUNNING'&&!STAGES.includes(e.stage as StagedReportStage))fail()
 const sectionsDone=count(e.sections_done,0,sectionCount);if(sectionsDone!==(state==='CLOSED_UNCOMMITTED'?0:Math.max(0,Math.min(unitsDone-1,sectionCount))))fail()
 if((state==='DONE')!==guid(e.publication_id)||state!=='DONE'&&e.publication_id!==null||state==='DONE'&&unitsDone!==unitCount)fail()
 let failure:StagedReportJob['failure']=null
 if(state==='FAILED'){const f=obj(e.failure);exact(f,['unit','sqlstate','code']);if(typeof f.sqlstate!=='string'||!/^[0-9A-Z]{5}$/.test(f.sqlstate)||typeof f.code!=='string'||!/^CP7_[A-Z0-9_]+$/.test(f.code))fail();failure={unit:count(f.unit,0,unitCount),sqlstate:f.sqlstate,code:f.code}}
 else if(e.failure!==null)fail()
 const p=r.payload
 if(uuid(e.run_id)!==p.run_id||hex(e.identity_hash)!==p.identity_hash||kind(e.kind)!==p.kind||finance(e.finance)!==p.finance||!revision(e.revision))fail()
 if(p.series_id===null?e.revision!=='1':e.series_id!==p.series_id||BigInt(e.revision as string)!==BigInt(p.expected_revision!)+1n)fail()
 const workerActive=e.worker_active===undefined?false:typeof e.worker_active==='boolean'?e.worker_active:fail()
 return{requestId:r.id,state,stage:expect as StagedReportStage|null,unitsDone,unitCount,unitAttempts:count(e.unit_attempts,0,Number.MAX_SAFE_INTEGER),sectionsDone,sectionCount,
  runId:p.run_id,identityHash:p.identity_hash,dataAsOf:stagedInstant(e.data_as_of),kind:p.kind,finance:p.finance,seriesId:uuid(e.series_id),revision:e.revision as string,
  lastProgressAt:stagedInstant(e.last_progress_at),publicationId:state==='DONE'?e.publication_id as string:null,failure,workerActive}
}

const DOC=['contract_version','actor_scope_id','id','series_id','revision','run_id','request_id','identity_hash','data_as_of','kind','period_query','title','reason',
 'template_version','finance','report_date','actuals_read_at','financial_source_hash','freshness','targets_total','summary','summary_sha256','sections','report_hash',
 'published_at','is_latest','access_epoch','production_go']
const FRESHNESS=['STALE_VERIFIED','VERIFIED_SAME','CHANGES_RECORDED','NO_RECORDED_CHANGE'] as const
// The publication with its section index: the summary hash, the report hash
// over the summary and section hashes, and the section ranges covering every
// target of the run once.
export async function parseStagedReport(v:unknown,actor:string):Promise<StagedReport>{
 const d=obj(v);exact(d,DOC)
 if(d.contract_version!=='cp7.report-publication.v2'||d.actor_scope_id!==actor||d.production_go!==false||d.template_version!=='native-report-staged-1'||typeof d.is_latest!=='boolean')fail()
 const f=finance(d.finance)
 if(f==='INCLUDED'?typeof d.financial_source_hash!=='string'||!/^[0-9a-f]{64}$/.test(d.financial_source_hash):d.financial_source_hash!==null)fail()
 const fr=obj(d.freshness);exact(fr,['state','evaluated_at','changes_total'])
 if(!FRESHNESS.includes(fr.state as StagedReportFreshnessState)||typeof fr.changes_total!=='string'||!/^(0|[1-9][0-9]{0,18})$/.test(fr.changes_total))fail()
 const targetsTotal=count(d.targets_total,0,ANALYSIS_STAGED_TARGETS)
 if(!Array.isArray(d.sections))fail()
 let next=1
 const sections=(d.sections as unknown[]).map((raw,i)=>{const s=obj(raw);exact(s,['index','target_lo','target_hi','utf8_bytes','sha256'])
  const e={index:count(s.index,i,i),targetLo:count(s.target_lo,next,next),targetHi:count(s.target_hi,next,targetsTotal),utf8Bytes:count(s.utf8_bytes,1,ANALYSIS_PAGE_UTF8_BYTES),sha256:hex(s.sha256)}
  next=e.targetHi+1;return e})
 if(next-1!==targetsTotal)fail()
 if(typeof d.summary!=='string'||!d.summary||bytes(d.summary)>ANALYSIS_PAGE_UTF8_BYTES||await sha256(d.summary)!==hex(d.summary_sha256))fail()
 if(await sha256([d.summary_sha256 as string,...sections.map(s=>s.sha256)].join('\n'))!==hex(d.report_hash))fail()
 if(typeof d.report_date!=='string'||!financeDate(d.report_date)||!revision(d.revision))fail()
 return{id:uuid(d.id),seriesId:uuid(d.series_id),revision:d.revision,runId:uuid(d.run_id),requestId:uuid(d.request_id),identityHash:hex(d.identity_hash),
  dataAsOf:stagedInstant(d.data_as_of),kind:kind(d.kind),query:query(d.period_query),title:text(d.title,200),reason:text(d.reason,1000),finance:f,reportDate:d.report_date,
  actualsReadAt:stagedInstant(d.actuals_read_at),financialSourceHash:d.financial_source_hash as string|null,
  freshness:{state:fr.state as StagedReportFreshnessState,evaluatedAt:stagedInstant(fr.evaluated_at),changesTotal:fr.changes_total},targetsTotal,summary:d.summary,
  summarySha256:d.summary_sha256 as string,sections,reportHash:d.report_hash as string,publishedAt:stagedInstant(d.published_at),isLatest:d.is_latest,accessEpoch:hex(d.access_epoch)}
}
export async function parseStagedReportSection(v:unknown,report:StagedReport,index:number):Promise<StagedReportSection>{
 const e=obj(v);exact(e,['contract_version','publication_id','report_hash','index','section_count','target_lo','target_hi','utf8_bytes','sha256','body'])
 const entry=report.sections[index]??fail()
 if(e.contract_version!=='cp7.report-section.v2'||e.publication_id!==report.id||e.report_hash!==report.reportHash||e.index!==index||e.section_count!==report.sections.length
  ||e.target_lo!==entry.targetLo||e.target_hi!==entry.targetHi||e.utf8_bytes!==entry.utf8Bytes||e.sha256!==entry.sha256||typeof e.body!=='string'
  ||bytes(e.body)!==entry.utf8Bytes||await sha256(e.body)!==entry.sha256)fail()
 return{publicationId:report.id,index,targetLo:entry.targetLo,targetHi:entry.targetHi,body:e.body,sha256:entry.sha256}
}
export function parseStagedReportIndex(v:unknown,actor:string,limit:number):StagedReportIndex{
 const p=obj(v);exact(p,['contract_version','actor_scope_id','rows','total','next_before_id','page_complete','production_go'])
 if(p.contract_version!=='cp7.report-index.v2'||p.actor_scope_id!==actor||p.page_complete!==true||p.production_go!==false||!Array.isArray(p.rows)||p.rows.length>limit
  ||typeof p.total!=='string'||!/^(0|[1-9][0-9]{0,18})$/.test(p.total)||BigInt(p.total)<BigInt(p.rows.length)||p.next_before_id!==null&&!guid(p.next_before_id))fail()
 const rows=(p.rows as unknown[]).map(raw=>{const r=obj(raw);exact(r,['id','series_id','revision','run_id','kind','title','period_query','data_as_of','finance','published_at','report_hash'])
  if(!revision(r.revision))fail()
  return{id:uuid(r.id),seriesId:uuid(r.series_id),revision:r.revision,runId:uuid(r.run_id),kind:kind(r.kind),title:text(r.title,200),query:query(r.period_query),
   dataAsOf:stagedInstant(r.data_as_of),finance:finance(r.finance),publishedAt:stagedInstant(r.published_at),reportHash:hex(r.report_hash)}})
 if(new Set(rows.map(r=>r.id)).size!==rows.length||p.next_before_id!==null&&(rows.length!==limit||p.next_before_id!==rows.at(-1)?.id))fail()
 return{rows,total:p.total,nextBeforeId:p.next_before_id as string|null}
}

// The pending request is kept per actor scope so a reload resumes the same
// job (the server treats the same UUID and payload as the same job); it is
// removed once the job is DONE, FAILED or closed.
export const stagedReportRequestKey=(scope:string)=>`erp.cp7.report-request.v2:${scope}`
function request(v:unknown):StagedReportRequest{const r=obj(v);exact(r,['id','payload']);return{id:uuid(r.id),payload:stagedReportPayload(r.payload)}}
export function readStagedReportRequest(scope:string):{pending:StagedReportRequest|null;error:string|null}{
 try{const s=localStorage.getItem(stagedReportRequestKey(scope));return{pending:s===null?null:request(JSON.parse(s)),error:null}}
 catch{return{pending:null,error:'Permintaan laporan bertahap tersimpan belum dapat dibaca. Catatannya dipertahankan.'}}
}
export function persistStagedReportRequest(scope:string,r:StagedReportRequest){
 request(r);const held=readStagedReportRequest(scope)
 if(held.error||held.pending&&JSON.stringify(held.pending)!==JSON.stringify(r))throw Error('Selesaikan laporan bertahap yang tertunda terlebih dahulu.')
 const s=JSON.stringify(r);try{localStorage.setItem(stagedReportRequestKey(scope),s)}catch{/* checked below */}
 if(localStorage.getItem(stagedReportRequestKey(scope))!==s)throw Error('Permintaan laporan belum tersimpan; tidak ada permintaan yang dikirim.')
}
export function clearStagedReportRequest(scope:string,r:StagedReportRequest){
 const held=readStagedReportRequest(scope);if(held.error||JSON.stringify(held.pending)!==JSON.stringify(r))throw Error('Permintaan laporan bertahap tersimpan berubah.')
 try{localStorage.removeItem(stagedReportRequestKey(scope))}catch{/* checked below */}
 if(localStorage.getItem(stagedReportRequestKey(scope))!==null)throw Error('Permintaan laporan bertahap belum dapat diselesaikan.')
}

export type StagedReportReply={data:unknown;error:unknown}
export type StagedReportRpc={publish:(r:StagedReportRequest)=>PromiseLike<StagedReportReply>;lookup:(r:StagedReportRequest)=>PromiseLike<StagedReportReply>;step:(id:string)=>PromiseLike<StagedReportReply>}
export const STAGED_REPORT_WORKER_BACKOFF_MS=2000
// Publish (or look up), then step while RUNNING; a skipped step (another
// session runs the unit) waits and reads the status again. Returns the final
// status, or null once aborted; a refusal or lost reply is thrown with the
// last status already reported.
export async function driveStagedReport(o:{rpc:StagedReportRpc;request:StagedReportRequest;lookup:boolean;aborted?:()=>boolean;sleep?:(ms:number)=>Promise<void>;onStatus?:(s:StagedReportJob)=>void}):Promise<StagedReportJob|null>{
 const aborted=o.aborted??(()=>false),sleep=o.sleep??(ms=>new Promise<void>(r=>setTimeout(r,ms)))
 const read=(r:StagedReportReply)=>{if(r.error)throw r.error;const s=parseStagedReportJob(r.data,o.request);o.onStatus?.(s);return s}
 if(aborted())return null
 let status=read(await(o.lookup?o.rpc.lookup(o.request):o.rpc.publish(o.request)))
 while(status.state==='RUNNING'){
  if(aborted())return null
  if(status.workerActive){await sleep(STAGED_REPORT_WORKER_BACKOFF_MS);if(aborted())return null;status=read(await o.rpc.lookup(o.request))}
  else status=read(await o.rpc.step(o.request.id))
 }
 return status
}

const stageLabel:Record<StagedReportStage,string>={ACTUALS:'membaca stok dan angka aktual',SECTION:'menyusun bagian rincian',FRESHNESS:'menghitung perubahan sejak data diambil',SUMMARY:'menyusun ringkasan dan menyimpan'}
export const stagedReportProgressText=(j:StagedReportJob)=>`Laporan bertahap: ${j.stage?stageLabel[j.stage]:'selesai'} · langkah ${j.unitsDone} dari ${j.unitCount}`+
 (j.sectionCount?` · bagian ${j.sectionsDone} dari ${j.sectionCount}`:'')+(j.unitAttempts?` · percobaan ulang ${j.unitAttempts}`:'')+(j.workerActive?' · sesi lain sedang menjalankan langkah ini':'')+'.'
const failureText:Record<string,string>={
 CP7_REPORT_ACCESS_CHANGED:'Hak akses berubah selama laporan disusun. Tidak ada laporan yang disimpan.',
 CP7_REPORT_V2_FINANCE_ACCESS:'Akun ini tidak lagi boleh melihat laporan keuangan. Tidak ada laporan yang disimpan.',
 CP7_REPORT_REVISION_CHANGED:'Seri laporan ini sudah direvisi dari permintaan lain. Buka versi terbaru, lalu buat revisi dari sana.',
 CP7_REPORT_SERIES_SCOPE_CHANGED:'Revisi harus memakai jenis dan periode yang sama dengan seri laporannya.',
 CP7_REPORT_V2_STAGE_STOPPED:'Satu langkah dihentikan batas waktu server tiga kali berturut-turut. Tidak ada laporan yang disimpan.',
 CP7_REPORT_V2_SECTION_TOO_LARGE:'Satu bagian laporan melampaui batas ukuran server. Tidak ada laporan yang disimpan.',
 CP7_REPORT_V2_SUMMARY_TOO_LARGE:'Ringkasan laporan melampaui batas ukuran server. Tidak ada laporan yang disimpan.',
 CP7_REPORT_V2_LABEL_AMBIGUOUS:'Satu target punya lebih dari satu nama produk di analisis ini. Tidak ada laporan yang disimpan.'}
export const stagedReportFailureText=(f:NonNullable<StagedReportJob['failure']>)=>`Laporan gagal pada langkah ${f.unit} (${f.code}). ${failureText[f.code]??'Server menolak langkah ini. Tidak ada laporan yang disimpan.'}`
// Freshness at publication, in the words of the snapshot contract: never "current".
export const stagedReportFreshnessText=(r:StagedReport)=>r.freshness.state==='VERIFIED_SAME'?'Saat laporan dibuat: sama dengan data pada cek sumber terakhir.'
 :r.freshness.state==='STALE_VERIFIED'?'Saat laporan dibuat: cek sumber terakhir menemukan data sudah berubah; isi analisis tetap keadaan saat data diambil.'
 :r.freshness.state==='CHANGES_RECORDED'?`Saat laporan dibuat: ada ${r.freshness.changesTotal} perubahan tercatat sejak data diambil; isi analisis tetap keadaan saat data diambil.`
 :'Saat laporan dibuat: belum ada perubahan tercatat sejak data diambil (belum dicek penuh).'
