import type {NativeAnalysis} from './nativeAnalysis'
import type {NativeDemandQuery} from './nativeDemandHistory'

// Only pointers to immutable actor-owned server runs are stored here. No stock,
// forecast, report, prompt, financial value or source facts are cached locally.
export type AnalysisPointer={runId:string;requestId:string;query:NativeDemandQuery;capturedAt:string;sourceHash:string;semanticHash:string}
export const analysisArchiveKey=(scope:string)=>'erp.cp7.analysis-archive.v1:'+scope
const guid=(v:unknown)=>typeof v==='string'&&/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/.test(v)
const hash=(v:unknown)=>typeof v==='string'&&/^[0-9a-f]{64}$/.test(v)
const date=(v:unknown)=>typeof v==='string'&&/^\d{4}-\d{2}-\d{2}$/.test(v)&&Number.isFinite(Date.parse(v+'T00:00:00Z'))&&new Date(v+'T00:00:00Z').toISOString().slice(0,10)===v
function pointer(v:unknown):AnalysisPointer{
 if(v===null||typeof v!=='object'||Array.isArray(v))throw Error('Invalid archive pointer')
 const p=v as Record<string,unknown>,q=p.query as Record<string,unknown>;if(Object.keys(p).sort().join('|')!=='capturedAt|query|requestId|runId|semanticHash|sourceHash'||!guid(p.runId)||!guid(p.requestId)||!hash(p.sourceHash)||!hash(p.semanticHash)||typeof p.capturedAt!=='string'||!/^\d{4}-\d{2}-\d{2}T.*Z$/.test(p.capturedAt)||!Number.isFinite(Date.parse(p.capturedAt))||q===null||typeof q!=='object'||Array.isArray(q)||Object.keys(q).sort().join('|')!=='from_date|group_mode|through_date'||!date(q.from_date)||!date(q.through_date)||(q.from_date as string)>(q.through_date as string)||!['AS_SOLD','RESTATED'].includes(String(q.group_mode)))throw Error('Invalid archive pointer')
 return structuredClone(p)as AnalysisPointer
}
export function readAnalysisArchive(scope:string):{rows:AnalysisPointer[];error:string}{try{const raw=localStorage.getItem(analysisArchiveKey(scope));if(raw===null)return{rows:[],error:''};const p=JSON.parse(raw);if(!Array.isArray(p)||p.length>50)throw Error('Invalid archive index');const rows=p.map(pointer);if(new Set(rows.map(p=>p.runId)).size!==rows.length)throw Error('Duplicate archive');return{rows,error:''}}catch{return{rows:[],error:'Daftar arsip tersimpan belum dapat dibaca. Catatan lama dipertahankan.'}}}
export function rememberAnalysis(scope:string,r:NativeAnalysis){const current=readAnalysisArchive(scope);if(current.error)throw Error(current.error);const p=pointer({runId:r.runId,requestId:r.requestId,query:r.query,capturedAt:r.analysis.snapshot.generated_at,sourceHash:r.analysis.snapshot.source_hash,semanticHash:r.analysis.semantic_hash}),old=current.rows.find(x=>x.runId===p.runId)
 if(old&&JSON.stringify(old)!==JSON.stringify(p))throw Error('Penunjuk arsip lama berubah. Periksa sumber sebelum melanjutkan.')
 const raw=JSON.stringify([p,...current.rows.filter(x=>x.runId!==p.runId)].slice(0,50));localStorage.setItem(analysisArchiveKey(scope),raw);if(localStorage.getItem(analysisArchiveKey(scope))!==raw)throw Error('Daftar arsip belum tersimpan. Ulangi analisis yang sama.')
}
export function checkAnalysisPointer(p:AnalysisPointer,r:NativeAnalysis){if(p.runId!==r.runId||p.requestId!==r.requestId||p.capturedAt!==r.analysis.snapshot.generated_at||p.sourceHash!==r.analysis.snapshot.source_hash||p.semanticHash!==r.analysis.semantic_hash)throw Error('Arsip server tidak sesuai penunjuk aslinya.')}
