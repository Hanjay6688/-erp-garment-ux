import type {NativeAnalysis} from './nativeAnalysis'
import type {NativeDemandQuery} from './nativeDemandHistory'

// Only pointers to immutable actor-owned server runs are stored here. No stock,
// forecast, report, prompt, financial value or source facts are cached locally.
export type AnalysisPointer={runId:string;requestId:string;query:NativeDemandQuery;capturedAt:string;sourceHash:string;semanticHash:string}
export const analysisArchiveKey=(scope:string)=>'erp.cp7.analysis-archive.v1:'+scope
const guid=(v:unknown)=>typeof v==='string'&&/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/.test(v)
const hash=(v:unknown)=>typeof v==='string'&&/^[0-9a-f]{64}$/.test(v)
const date=(v:unknown)=>typeof v==='string'&&/^\d{4}-\d{2}-\d{2}$/.test(v)&&Number.isFinite(Date.parse(v+'T00:00:00Z'))&&new Date(v+'T00:00:00Z').toISOString().slice(0,10)===v
// PostgreSQL retains microseconds. Millisecond Date comparisons would reorder
// two distinct Native captures in the same millisecond by UUID instead of time.
function captureMicros(v:unknown):bigint|null{
 if(typeof v!=='string')return null
 const m=/^(\d{4}-\d{2}-\d{2})T(\d{2}):(\d{2}):(\d{2})(?:\.(\d{1,6}))?Z$/.exec(v)
 if(!m||!date(m[1])||Number(m[2])>23||Number(m[3])>59||Number(m[4])>59)return null
 const seconds=Date.parse(`${m[1]}T${m[2]}:${m[3]}:${m[4]}Z`)
 return Number.isFinite(seconds)?BigInt(seconds)*1000n+BigInt((m[5]??'').padEnd(6,'0')):null
}
function pointer(v:unknown):AnalysisPointer{
 if(v===null||typeof v!=='object'||Array.isArray(v))throw Error('Invalid archive pointer')
 const p=v as Record<string,unknown>,q=p.query as Record<string,unknown>;if(Object.keys(p).sort().join('|')!=='capturedAt|query|requestId|runId|semanticHash|sourceHash'||!guid(p.runId)||!guid(p.requestId)||!hash(p.sourceHash)||!hash(p.semanticHash)||captureMicros(p.capturedAt)===null||q===null||typeof q!=='object'||Array.isArray(q)||Object.keys(q).sort().join('|')!=='from_date|group_mode|through_date'||!date(q.from_date)||!date(q.through_date)||(q.from_date as string)>(q.through_date as string)||!['AS_SOLD','RESTATED'].includes(String(q.group_mode)))throw Error('Invalid archive pointer')
 return structuredClone(p)as AnalysisPointer
}
export function readAnalysisArchive(scope:string):{rows:AnalysisPointer[];error:string}{try{const raw=localStorage.getItem(analysisArchiveKey(scope));if(raw===null)return{rows:[],error:''};const p=JSON.parse(raw);if(!Array.isArray(p)||p.length>50)throw Error('Invalid archive index');const rows=p.map(pointer);if(new Set(rows.map(p=>p.runId)).size!==rows.length)throw Error('Duplicate archive');return{rows,error:''}}catch{return{rows:[],error:'Daftar arsip tersimpan belum dapat dibaca. Catatan lama dipertahankan.'}}}
export function rememberAnalysis(scope:string,r:NativeAnalysis){const current=readAnalysisArchive(scope);if(current.error)throw Error(current.error);const p=pointer({runId:r.runId,requestId:r.requestId,query:r.query,capturedAt:r.analysis.snapshot.generated_at,sourceHash:r.analysis.snapshot.source_hash,semanticHash:r.analysis.semantic_hash}),old=current.rows.find(x=>x.runId===p.runId)
 if(old&&JSON.stringify(old)!==JSON.stringify(p))throw Error('Penunjuk arsip lama berubah. Periksa sumber sebelum melanjutkan.')
 const raw=JSON.stringify([p,...current.rows.filter(x=>x.runId!==p.runId)].slice(0,50));localStorage.setItem(analysisArchiveKey(scope),raw);if(localStorage.getItem(analysisArchiveKey(scope))!==raw)throw Error('Daftar arsip belum tersimpan. Ulangi analisis yang sama.')
}
export function checkAnalysisPointer(p:AnalysisPointer,r:NativeAnalysis){if(p.runId!==r.runId||p.requestId!==r.requestId||p.capturedAt!==r.analysis.snapshot.generated_at||p.sourceHash!==r.analysis.snapshot.source_hash||p.semanticHash!==r.analysis.semantic_hash)throw Error('Arsip server tidak sesuai penunjuk aslinya.')}

export type NativeArchivePage={rows:AnalysisPointer[];totalVisible:string;nextBeforeRun:string|null;readAt:string}
export function parseNativeArchivePage(v:unknown,actor:string,requestedLimit:number):NativeArchivePage{
 const fail=():never=>{throw Error('Daftar arsip server belum sesuai hak akses dan sumbernya.')}
 if(!v||typeof v!=='object'||Array.isArray(v))return fail()
 const p=v as Record<string,unknown>
 if(Object.keys(p).sort().join('|')!=='actor_scope_id|contract_version|next_before_run|page_complete|read_at|rows|total_visible'||p.contract_version!=='cp7.native-analysis-archives.v1'||p.actor_scope_id!==actor||p.page_complete!==true||!Array.isArray(p.rows)||!Number.isInteger(requestedLimit)||requestedLimit<1||requestedLimit>50||p.rows.length>requestedLimit||typeof p.total_visible!=='string'||!/^(0|[1-9][0-9]{0,18})$/.test(p.total_visible)||BigInt(p.total_visible)>9223372036854775807n||BigInt(p.total_visible)<BigInt(p.rows.length)||p.next_before_run!==null&&!guid(p.next_before_run)||typeof p.read_at!=='string'||!/^\d{4}-\d{2}-\d{2}T.*(?:Z|[+-]\d{2}:\d{2})$/.test(p.read_at)||!date(p.read_at.slice(0,10))||!Number.isFinite(Date.parse(p.read_at)))return fail()
 const rows=(p.rows as unknown[]).map(pointer)
 if(new Set(rows.map(r=>r.runId)).size!==rows.length||p.next_before_run!==null&&(rows.length!==requestedLimit||p.next_before_run!==rows.at(-1)?.runId||BigInt(p.total_visible)<=BigInt(requestedLimit)))return fail()
 for(let i=1;i<rows.length;i++){
  const before=rows[i-1],after=rows[i]
  const beforeAt=captureMicros(before.capturedAt)!,afterAt=captureMicros(after.capturedAt)!
  if(beforeAt<afterAt||beforeAt===afterAt&&before.runId<=after.runId)return fail()
 }
 return{rows,totalVisible:p.total_visible,nextBeforeRun:p.next_before_run as string|null,readAt:p.read_at}
}
