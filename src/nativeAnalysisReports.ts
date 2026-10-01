import {parseNativeAnalysis,assertSameAnalysis,type NativeAnalysis,type AnalysisFinanceAccess} from './nativeAnalysis'
import type {NativeDemandQuery} from './nativeDemandHistory'
import type {AnalysisResult} from './cp7/contract'
import {financeDate} from './financeReportContract'

export const reportKinds=['DAILY','PERIOD','EXCEPTIONS','ARCHIVE'] as const
export type ReportKind=typeof reportKinds[number]
export const reportKindLabels:Record<ReportKind,string>={DAILY:'Briefing harian',PERIOD:'Review periode',EXCEPTIONS:'Analisis & pengecualian',ARCHIVE:'Arsip laporan'}
export type ReportPayload={run_id:string;source_hash:string;semantic_hash:string;kind:ReportKind;series_id:string|null;expected_revision:string|null;title:string;reason:string;explicit_review:true}
export type ReportRequest={id:string;query:NativeDemandQuery;payload:ReportPayload}
export type NativeReport={id:string;seriesId:string;revision:string;runId:string;requestId:string;kind:ReportKind;query:NativeDemandQuery;title:string;reason:string;templateVersion:string;body:string;bodyHash:string;sourceHash:string;semanticHash:string;publishedAt:string;isLatest:boolean;analysis:NativeAnalysis}
export type ReportCommand={requestId:string;status:'COMMITTED'|'CLOSED_UNCOMMITTED';document:NativeReport|null;analysis:NativeAnalysis}
export type ReportPointer={id:string;seriesId:string;revision:string;runId:string;kind:ReportKind;title:string;query:NativeDemandQuery;publishedAt:string;bodyHash:string}
export type ReportIndex={rows:ReportPointer[];total:string;nextBeforeId:string|null}
type Metric=AnalysisResult['metrics'][number]
export type ReportComparisonRow={metric_id:string;version:string;scope_kind:Metric['scope_kind'];scope_key:string;knowledge_mode:Metric['knowledge_mode'];before:Metric|null;after:Metric|null;difference:{state:'UNKNOWN';unit:string;reason:string}|{state:'KNOWN'|'ASSUMED';unit:string;value:string}}
export type ReportComparison={before:NativeReport;after:NativeReport;rows:ReportComparisonRow[]}
function fail():never{throw Error('Laporan tersimpan belum cocok dengan sumber dan izin ERP.')}
const obj=(v:unknown):Record<string,unknown>=>v!==null&&typeof v==='object'&&!Array.isArray(v)?v as Record<string,unknown>:fail()
const exact=(v:Record<string,unknown>,keys:string[])=>{if(Object.keys(v).length!==keys.length||keys.some(k=>!Object.hasOwn(v,k)))fail()}
const guid=(v:unknown):v is string=>typeof v==='string'&&/^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/.test(v)
const hash=(v:unknown):v is string=>typeof v==='string'&&/^[0-9a-f]{64}$/.test(v)
const revision=(v:unknown):v is string=>typeof v==='string'&&/^[1-9][0-9]{0,18}$/.test(v)&&BigInt(v)<=9223372036854775807n
const stamp=(v:unknown):v is string=>typeof v==='string'&&/^\d{4}-\d{2}-\d{2}T.*(?:Z|[+-]\d{2}:\d{2})$/.test(v)&&financeDate(v.slice(0,10))&&Number.isFinite(Date.parse(v))
const kind=(v:unknown):v is ReportKind=>reportKinds.includes(v as ReportKind)
function query(v:unknown):NativeDemandQuery{const q=obj(v);exact(q,['from_date','through_date','group_mode']);if(!financeDate(q.from_date)||!financeDate(q.through_date)||q.from_date>q.through_date||!['AS_SOLD','RESTATED'].includes(String(q.group_mode)))fail();return structuredClone(q) as NativeDemandQuery}
function payload(v:unknown):ReportPayload{const p=obj(v);exact(p,['run_id','source_hash','semantic_hash','kind','series_id','expected_revision','title','reason','explicit_review']);if(!guid(p.run_id)||!hash(p.source_hash)||!hash(p.semantic_hash)||!kind(p.kind)||p.explicit_review!==true||typeof p.title!=='string'||[...p.title.trim()].length<1||[...p.title].length>200||typeof p.reason!=='string'||[...p.reason.trim()].length<1||[...p.reason].length>1000||(p.series_id===null?p.expected_revision!==null:!guid(p.series_id)||!revision(p.expected_revision)))fail();return structuredClone(p) as ReportPayload}
export async function parseNativeReport(v:unknown,actor:string,access:AnalysisFinanceAccess):Promise<NativeReport>{
 const d=obj(v);exact(d,['contract_version','actor_scope_id','id','series_id','revision','run_id','request_id','kind','period_query','title','reason','template_version','body','body_sha256','source_hash','semantic_hash','published_at','is_latest','source_state','analysis','production_go'])
 if(d.contract_version!=='cp7.report-publication.v1'||d.actor_scope_id!==actor||d.production_go!==false||![d.id,d.series_id,d.run_id,d.request_id].every(guid)||!revision(d.revision)||!kind(d.kind)||typeof d.title!=='string'||!d.title.trim()||[...d.title].length>200||typeof d.reason!=='string'||!d.reason.trim()||[...d.reason].length>1000||d.template_version!=='native-report-1'||typeof d.body!=='string'||!d.body||![d.body_sha256,d.source_hash,d.semantic_hash].every(hash)||!stamp(d.published_at)||typeof d.is_latest!=='boolean')fail()
 const q=query(d.period_query),analysis=parseNativeAnalysis(d.analysis,q,actor,access)
 if(analysis.runId!==d.run_id||analysis.state!==d.source_state||analysis.analysis.snapshot.source_hash!==d.source_hash||analysis.analysis.semantic_hash!==d.semantic_hash)fail()
 const bytes=new TextEncoder().encode(d.body as string);if(bytes.byteLength>8000000)fail()
 const digest=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes)),b=>b.toString(16).padStart(2,'0')).join('');if(digest!==d.body_sha256)fail()
 return {id:d.id,seriesId:d.series_id,revision:d.revision,runId:d.run_id,requestId:d.request_id,kind:d.kind,query:q,title:d.title,reason:d.reason,templateVersion:d.template_version,body:d.body,bodyHash:d.body_sha256,sourceHash:d.source_hash,semanticHash:d.semantic_hash,publishedAt:d.published_at,isLatest:d.is_latest,analysis} as NativeReport
}
export function assertSameReport(before:NativeReport,after:NativeReport){assertSameAnalysis(before.analysis,after.analysis);const frozen=(d:NativeReport)=>({...d,analysis:undefined,isLatest:undefined});if(JSON.stringify(frozen(before))!==JSON.stringify(frozen(after)))fail()}
export async function parseReportCommand(v:unknown,r:ReportRequest,actor:string,access:AnalysisFinanceAccess):Promise<ReportCommand>{
 const c=obj(v);exact(c,['contract_version','request_id','status','document','analysis','production_go']);if(c.contract_version!=='cp7.report-command.v1'||c.production_go!==false||c.request_id!==r.id||!['COMMITTED','CLOSED_UNCOMMITTED'].includes(String(c.status)))fail()
 const a=parseNativeAnalysis(c.analysis,r.query,actor,access),p=payload(r.payload);if(a.runId!==p.run_id||a.analysis.snapshot.source_hash!==p.source_hash||a.analysis.semantic_hash!==p.semantic_hash)fail()
 const document=c.status==='COMMITTED'?await parseNativeReport(c.document,actor,access):null;if(c.status==='CLOSED_UNCOMMITTED'&&c.document!==null)fail()
 if(document){assertSameAnalysis(a,document.analysis);if(document.requestId!==r.id||document.runId!==p.run_id||document.kind!==p.kind||document.title!==p.title.trim()||document.reason!==p.reason.trim()||(p.series_id===null?document.revision!=='1':document.seriesId!==p.series_id||BigInt(document.revision)!==BigInt(p.expected_revision!)+1n))fail()}
 return{requestId:r.id,status:c.status as ReportCommand['status'],document,analysis:a}
}
export function parseReportIndex(v:unknown,actor:string,limit:number):ReportIndex{
 const p=obj(v);exact(p,['contract_version','actor_scope_id','rows','total','next_before_id','page_complete','production_go']);if(p.contract_version!=='cp7.report-index.v1'||p.actor_scope_id!==actor||p.page_complete!==true||p.production_go!==false||!Array.isArray(p.rows)||p.rows.length>limit||!Number.isSafeInteger(limit)||limit<1||limit>50||typeof p.total!=='string'||!/^(0|[1-9][0-9]{0,18})$/.test(p.total)||BigInt(p.total)>9223372036854775807n||BigInt(p.total)<BigInt(p.rows.length)||p.next_before_id!==null&&!guid(p.next_before_id))fail()
 const rows=(p.rows as unknown[]).map(raw=>{const r=obj(raw);exact(r,['id','series_id','revision','run_id','kind','title','period_query','published_at','body_sha256']);if(![r.id,r.series_id,r.run_id].every(guid)||!revision(r.revision)||!kind(r.kind)||typeof r.title!=='string'||!r.title||[...r.title].length>200||!stamp(r.published_at)||!hash(r.body_sha256))fail();return{id:r.id,seriesId:r.series_id,revision:r.revision,runId:r.run_id,kind:r.kind,title:r.title,query:query(r.period_query),publishedAt:r.published_at,bodyHash:r.body_sha256} as ReportPointer})
 if(new Set(rows.map(r=>r.id)).size!==rows.length||p.next_before_id!==null&&(rows.length!==limit||p.next_before_id!==rows.at(-1)?.id))fail()
 return{rows,total:p.total as string,nextBeforeId:p.next_before_id as string|null}
}
const metricKey=(m:Metric)=>JSON.stringify([m.metric_id,m.version,m.scope_kind,m.scope_key,m.knowledge_mode,m.value.unit])
// Verify the comparison receipt with decimal integers; never calculate business facts.
function scaled(v:string):[bigint,number]{if(!/^-?\d+(?:\.\d+)?$/.test(v))fail();const [whole,fraction='']=v.split('.');return[BigInt(whole+fraction),fraction.length]}
function exactDifference(left:string,right:string,result:string){const [a,as]=scaled(left),[b,bs]=scaled(right),[c,cs]=scaled(result),scale=Math.max(as,bs,cs);return b*10n**BigInt(scale-bs)-a*10n**BigInt(scale-as)===c*10n**BigInt(scale-cs)}
export async function parseReportComparison(v:unknown,actor:string,access:AnalysisFinanceAccess,beforeId:string,afterId:string):Promise<ReportComparison>{
 const c=obj(v);exact(c,['contract_version','actor_scope_id','before','after','rows','comparison_basis','production_go']);if(c.contract_version!=='cp7.report-comparison.v1'||c.actor_scope_id!==actor||c.production_go!==false||c.comparison_basis!=='AFTER_MINUS_BEFORE_NATIVE_METRICS_MATCHED_VERSION_SCOPE_UNIT_KNOWLEDGE'||!Array.isArray(c.rows))fail()
 const [before,after]=await Promise.all([parseNativeReport(c.before,actor,access),parseNativeReport(c.after,actor,access)]);if(before.id!==beforeId||after.id!==afterId)fail()
 const left=new Map(before.analysis.analysis.metrics.map(m=>[metricKey(m),m])),right=new Map(after.analysis.analysis.metrics.map(m=>[metricKey(m),m])),expected=new Set([...left.keys(),...right.keys()]),seen=new Set<string>(),sameEngine=before.analysis.analysis.versions.engine===after.analysis.analysis.versions.engine
 const rows=(c.rows as unknown[]).map(raw=>{const r=obj(raw);exact(r,['metric_id','version','scope_kind','scope_key','knowledge_mode','before','after','difference']);const m=(r.after??r.before) as Metric;if(!m)fail();const k=metricKey(m),l=left.get(k)??null,a=right.get(k)??null;if(!expected.has(k)||seen.has(k)||JSON.stringify(l)!==JSON.stringify(r.before)||JSON.stringify(a)!==JSON.stringify(r.after)||['metric_id','version','scope_kind','scope_key','knowledge_mode'].some(key=>r[key]!==m[key as keyof Metric]))fail();seen.add(k)
  const d=obj(r.difference),known=l!==null&&a!==null&&l.value.state!=='UNKNOWN'&&a.value.state!=='UNKNOWN'&&sameEngine
  if(!known){exact(d,['state','unit','reason']);if(d.state!=='UNKNOWN'||d.unit!==m.value.unit||d.reason!==(sameEngine?(l===null||a===null?'METRIC_SCOPE_NOT_COMPARABLE':'ONE_OR_BOTH_VALUES_UNKNOWN'):'ENGINE_VERSIONS_NOT_COMPARABLE'))fail()}
  else{exact(d,['state','unit','value']);if(d.state!==(l.value.state==='ASSUMED'||a.value.state==='ASSUMED'?'ASSUMED':'KNOWN')||d.unit!==m.value.unit||typeof d.value!=='string'||!('value'in l.value)||!('value'in a.value)||!exactDifference(l.value.value,a.value.value,d.value))fail()}
  return structuredClone(r) as ReportComparisonRow
 });if(seen.size!==expected.size)fail();return{before,after,rows}
}
export const reportRequestKey=(scope:string)=>`erp.cp7.report-request.v1:${scope}`
function request(v:unknown):ReportRequest{const r=obj(v);exact(r,['id','query','payload']);if(!guid(r.id))fail();return{id:r.id,query:query(r.query),payload:payload(r.payload)}}
export function readReportRequest(scope:string):{pending:ReportRequest|null;error:string|null}{try{const s=localStorage.getItem(reportRequestKey(scope));return{pending:s===null?null:request(JSON.parse(s)),error:null}}catch{return{pending:null,error:'Permintaan laporan tersimpan belum dapat dibaca. Catatannya dipertahankan.'}}}
export function persistReportRequest(scope:string,r:ReportRequest){request(r);const held=readReportRequest(scope);if(held.error||held.pending&&JSON.stringify(held.pending)!==JSON.stringify(r))throw Error('Pastikan hasil laporan tersimpan terlebih dahulu.');const s=JSON.stringify(r);localStorage.setItem(reportRequestKey(scope),s);if(localStorage.getItem(reportRequestKey(scope))!==s)throw Error('Permintaan laporan belum tersimpan; tidak ada permintaan yang dikirim.')}
export function clearReportRequest(scope:string,r:ReportRequest){const held=readReportRequest(scope);if(held.error||JSON.stringify(held.pending)!==JSON.stringify(r))throw Error('Permintaan laporan tersimpan berubah.');localStorage.removeItem(reportRequestKey(scope));if(localStorage.getItem(reportRequestKey(scope))!==null)throw Error('Permintaan laporan belum dapat diselesaikan.')}
