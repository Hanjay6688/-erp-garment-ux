import type {NativeDemandQuery,NativeDemandRequest} from './nativeDemandHistory'

// P19 complete-Original transport. A finished analysis is read as a manifest
// plus immutable segments; each segment body stays within the existing
// 8,000,000-byte UTF8 body bound (2,000,000 characters of at most 4 bytes).
export const ANALYSIS_SEGMENT_CHARACTERS=2000000
export const ANALYSIS_SEGMENT_UTF8_BYTES=8000000
// Engineering bound for one assembled Original: eight times the existing
// single-body bound, about twice the measured 5000-target stand-in Original
// (30,970,077 bytes). A larger document is refused whole; nothing partial is
// shown. It is a transport/memory bound, not a factory policy value.
export const ANALYSIS_DOCUMENT_UTF8_BYTES=64000000

export type AnalysisJobState='WAITING'|'RUNNING'|'DONE'|'FAILED'
export type AnalysisJob={requestId:string;state:AnalysisJobState;requestedAt:string;startedAt:string;finishedAt:string|null;attempts:number;runId:string|null;failure:{sqlstate:string;code:string}|null}
export type AnalysisManifest={runId:string;requestId:string;sourceState:'UNCHANGED'|'ARCHIVED_STALE';accessEpoch:string;document:{utf8Bytes:number;characters:number;sha256:string;segmentCount:number;segmentCharacters:number}}

function fail():never{throw Error('Hasil analisis server belum sesuai sumber dan kontrak CP7.')}
const object=(v:unknown):Record<string,unknown>=>v!==null&&typeof v==='object'&&!Array.isArray(v)?v as Record<string,unknown>:fail()
const uuid=(v:unknown):string=>typeof v==='string'&&/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/.test(v)?v:fail()
const exact=(v:Record<string,unknown>,keys:string[])=>{if(Object.keys(v).length!==keys.length||keys.some(k=>!Object.hasOwn(v,k)))fail()}
const instant=(v:unknown)=>typeof v==='string'&&/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{6}Z$/.test(v)&&Number.isFinite(Date.parse(v))?v:fail()
const hex64=(v:unknown)=>typeof v==='string'&&/^[0-9a-f]{64}$/.test(v)?v:fail()
const count=(v:unknown,min:number,max:number)=>typeof v==='number'&&Number.isSafeInteger(v)&&v>=min&&v<=max?v:fail()
const sameQuery=(v:unknown,q:NativeDemandQuery)=>{const x=object(v);exact(x,['from_date','through_date','group_mode']);if(x.from_date!==q.from_date||x.through_date!==q.through_date||x.group_mode!==q.group_mode)fail()}
const sha256=async(bytes:Uint8Array<ArrayBuffer>)=>Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes)),b=>b.toString(16).padStart(2,'0')).join('')
// Characters as PostgreSQL counts them: Unicode code points, not UTF16 units.
const codePoints=(s:string)=>{let n=s.length;for(let i=0;i<s.length;i++){const c=s.charCodeAt(i);if(c>=0xd800&&c<=0xdbff){const d=s.charCodeAt(i+1);if(!(d>=0xdc00&&d<=0xdfff))fail();n--;i++}else if(c>=0xdc00&&c<=0xdfff)fail()}return n}

export function parseAnalysisJob(v:unknown,requestId:string,q:NativeDemandQuery):AnalysisJob{
 const e=object(v);exact(e,['contract_version','request_id','query','state','requested_at','started_at','finished_at','attempts','run_id','failure','apply_enabled','production_go'])
 if(e.contract_version!=='cp7.native-analysis-job.v1'||e.apply_enabled!==false||e.production_go!==false||uuid(e.request_id)!==requestId)fail()
 sameQuery(e.query,q)
 const state=e.state;if(state!=='WAITING'&&state!=='RUNNING'&&state!=='DONE'&&state!=='FAILED')fail()
 const requestedAt=instant(e.requested_at),startedAt=instant(e.started_at),finishedAt=e.finished_at===null?null:instant(e.finished_at)
 if(startedAt<requestedAt||(finishedAt===null)!==(state==='WAITING'||state==='RUNNING')||(finishedAt!==null&&finishedAt<startedAt))fail()
 const runId=e.run_id===null?null:uuid(e.run_id);if((runId!==null)!==(state==='DONE'))fail()
 let failure:AnalysisJob['failure']=null
 if(state==='FAILED'){const f=object(e.failure);exact(f,['sqlstate','code']);if(typeof f.sqlstate!=='string'||!/^[0-9A-Z]{5}$/.test(f.sqlstate)||typeof f.code!=='string'||!/^CP7_[A-Z0-9_]+$/.test(f.code))fail();failure={sqlstate:f.sqlstate,code:f.code}}
 else if(e.failure!==null)fail()
 return{requestId,state,requestedAt,startedAt,finishedAt,attempts:count(e.attempts,1,Number.MAX_SAFE_INTEGER),runId,failure}
}

// requestId null: an archive read learns it from the run and the caller still
// compares the whole result with its own pointer or previous analysis.
export function parseAnalysisManifest(v:unknown,runId:string,expectedRequestId:string|null):AnalysisManifest{
 const e=object(v);exact(e,['contract_version','run_id','request_id','source_state','access_epoch','document','apply_enabled','production_go'])
 const requestId=uuid(e.request_id)
 if(e.contract_version!=='cp7.native-analysis-manifest.v1'||e.apply_enabled!==false||e.production_go!==false||uuid(e.run_id)!==runId||(expectedRequestId!==null&&requestId!==expectedRequestId))fail()
 if(e.source_state!=='UNCHANGED'&&e.source_state!=='ARCHIVED_STALE')fail()
 const d=object(e.document);exact(d,['utf8_bytes','characters','sha256','segment_count','segment_characters'])
 const utf8Bytes=count(d.utf8_bytes,1,ANALYSIS_DOCUMENT_UTF8_BYTES),characters=count(d.characters,1,utf8Bytes)
 if(d.segment_characters!==ANALYSIS_SEGMENT_CHARACTERS||utf8Bytes>characters*4)fail()
 const segmentCount=count(d.segment_count,1,Math.ceil(ANALYSIS_DOCUMENT_UTF8_BYTES/ANALYSIS_SEGMENT_CHARACTERS));if(segmentCount!==Math.ceil(characters/ANALYSIS_SEGMENT_CHARACTERS))fail()
 return{runId,requestId,sourceState:e.source_state,accessEpoch:hex64(e.access_epoch),document:{utf8Bytes,characters,sha256:hex64(d.sha256),segmentCount,segmentCharacters:ANALYSIS_SEGMENT_CHARACTERS}}
}

export async function parseAnalysisSegment(v:unknown,m:AnalysisManifest,index:number):Promise<string>{
 const e=object(v);exact(e,['contract_version','run_id','index','segment_count','document_sha256','document_utf8_bytes','utf8_bytes','sha256','body'])
 if(e.contract_version!=='cp7.native-analysis-segment.v1'||e.run_id!==m.runId||e.index!==index||e.segment_count!==m.document.segmentCount||e.document_sha256!==m.document.sha256||e.document_utf8_bytes!==m.document.utf8Bytes)fail()
 if(typeof e.body!=='string')fail()
 const last=index===m.document.segmentCount-1,expected=last?m.document.characters-index*ANALYSIS_SEGMENT_CHARACTERS:ANALYSIS_SEGMENT_CHARACTERS
 if(codePoints(e.body)!==expected)fail()
 const bytes=new TextEncoder().encode(e.body);if(bytes.byteLength!==count(e.utf8_bytes,1,ANALYSIS_SEGMENT_UTF8_BYTES)||await sha256(bytes)!==hex64(e.sha256))fail()
 return e.body
}

// Reads every segment in order and returns the complete serve-shaped outcome
// only after the whole document matches the manifest byte count and SHA256.
export async function assembleAnalysisOriginal(m:AnalysisManifest,read:(index:number)=>Promise<unknown>,progress:(done:number,total:number)=>void=()=>{}):Promise<Record<string,unknown>>{
 const parts:string[]=[]
 for(let i=0;i<m.document.segmentCount;i++){parts.push(await parseAnalysisSegment(await read(i),m,i));progress(i+1,m.document.segmentCount)}
 const whole=parts.join(''),bytes=new TextEncoder().encode(whole)
 if(bytes.byteLength!==m.document.utf8Bytes||await sha256(bytes)!==m.document.sha256)fail()
 let parsed:unknown;try{parsed=JSON.parse(whole)}catch{fail()}
 const original=object(parsed);if(Object.hasOwn(original,'source_state')||original.run_id!==m.runId||original.request_id!==m.requestId)fail()
 return{...original,source_state:m.sourceState}
}

// The background request is kept separately from the ordinary capture request
// so a reload can show its server state and continue the same UUID.
export function analysisJobKey(scope:string){return 'erp.cp7.analysis-job.v1:'+scope}
const day=(v:unknown)=>typeof v==='string'&&/^\d{4}-\d{2}-\d{2}$/.test(v)&&new Date(v+'T00:00:00Z').toISOString().slice(0,10)===v?v:fail()
export function readAnalysisJobRequest(scope:string):{pending:NativeDemandRequest|null;error:string}{
 try{
  const raw=localStorage.getItem(analysisJobKey(scope));if(raw===null)return{pending:null,error:''}
  const v=object(JSON.parse(raw)),q=object(v.q)
  if(Object.keys(v).sort().join('|')!=='id|q'||Object.keys(q).sort().join('|')!=='from_date|group_mode|through_date'||(q.group_mode!=='AS_SOLD'&&q.group_mode!=='RESTATED'))fail()
  const from=day(q.from_date),through=day(q.through_date);if(from>through)fail()
  return{pending:{id:uuid(v.id),q:{from_date:from,through_date:through,group_mode:q.group_mode}},error:''}
 }catch{return{pending:null,error:'Catatan perhitungan latar belakang belum bisa dibaca. Jangan hapus catatan ini; pulihkan penyimpanan sebelum membuat perhitungan baru.'}}
}
export function persistAnalysisJobRequest(scope:string,r:NativeDemandRequest){
 const before=readAnalysisJobRequest(scope);if(before.error||before.pending)throw Error('Selesaikan perhitungan latar belakang yang tersimpan terlebih dahulu.')
 const raw=JSON.stringify(r);localStorage.setItem(analysisJobKey(scope),raw)
 if(localStorage.getItem(analysisJobKey(scope))!==raw||readAnalysisJobRequest(scope).pending?.id!==r.id)throw Error('Permintaan belum tersimpan. Periksa penyimpanan sebelum mencoba lagi.')
}
export function clearAnalysisJobRequest(scope:string,id:string){
 const held=readAnalysisJobRequest(scope);if(held.error||held.pending?.id!==id)throw Error('Catatan perhitungan berubah. Periksa perhitungan tersimpan.')
 localStorage.removeItem(analysisJobKey(scope));if(localStorage.getItem(analysisJobKey(scope))!==null)throw Error('Catatan perhitungan belum bisa diselesaikan.')
}
const failureText:Record<string,string>={
 CP7_ANALYSIS_JOB_STOPPED:'Perhitungan dihentikan sebelum selesai oleh batas waktu server atau koneksi yang terputus. Tidak ada hasil yang disimpan.',
 CP7_ANALYSIS_ACCESS_CHANGED:'Hak akses berubah selama perhitungan. Tidak ada hasil yang disimpan.',
 CP7_ANALYSIS_JOB_ERROR:'Perhitungan gagal di server. Tidak ada hasil yang disimpan.'}
export const analysisJobFailureText=(f:{code:string})=>failureText[f.code]??`Perhitungan ditolak server (${f.code}). Tidak ada hasil yang disimpan.`
const wib=(iso:string,o:Intl.DateTimeFormatOptions)=>new Date(iso).toLocaleString('id-ID',{timeZone:'Asia/Jakarta',...o})
export const analysisSinceText=(iso:string)=>`Sedang dihitung sejak jam ${wib(iso,{hour:'2-digit',minute:'2-digit',second:'2-digit',hour12:false})} WIB (${wib(iso,{day:'numeric',month:'short',year:'numeric'})}).`
// Characters above the single-body bound are read through the segment transport.
export const analysisOversized=(v:unknown)=>{try{return new TextEncoder().encode(JSON.stringify((v as {analysis?:unknown}|null)?.analysis??null)).byteLength>ANALYSIS_SEGMENT_UTF8_BYTES}catch{return false}}
