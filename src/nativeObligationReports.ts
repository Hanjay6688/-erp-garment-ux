import {parseNativeReport,assertSameReport,type NativeReport} from './nativeAnalysisReports'
import {assertSameAnalysis,type AnalysisFinanceAccess} from './nativeAnalysis'
import {parseRuleSource,type RuleSource,type RuleRights} from './nativeRuleSource'
import {financeDate} from './financeReportContract'

export type ObligationReportPayload={publication_id:string;run_id:string;source_hash:string;title:string;reason:string;explicit_review:true;series_id:string|null;expected_revision:string|null}
export type ObligationReportRequest={id:string;payload:ObligationReportPayload}
export type ObligationReportPreview={base:NativeReport;source:RuleSource}
export type ObligationReport={id:string;seriesId:string;revision:string;requestId:string;title:string;reason:string;publishedAt:string;isLatest:boolean;state:'UNCHANGED'|'ARCHIVED_STALE';body:string;bodyHash:string;base:NativeReport;source:RuleSource}
export type ObligationReportIndex={rows:{id:string;seriesId:string;revision:string;runId:string;publicationId:string;title:string;publishedAt:string;bodyHash:string}[];total:string;nextBeforeId:string|null}
const fail=():never=>{throw Error('Lampiran tagihan belum cocok dengan arsip, sumber dan hak akses ERP.')}
const object=(v:unknown,keys:string[])=>{if(!v||typeof v!=='object'||Array.isArray(v)||Object.keys(v).sort().join('|')!==[...keys].sort().join('|'))return fail();return v as Record<string,unknown>}
const guid=(v:unknown):v is string=>typeof v==='string'&&/^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/.test(v)
const hash=(v:unknown):v is string=>typeof v==='string'&&/^[0-9a-f]{64}$/.test(v)
const uint=(v:unknown):v is string=>typeof v==='string'&&/^(0|[1-9][0-9]{0,18})$/.test(v)&&BigInt(v)<=9223372036854775807n
const revision=(v:unknown):v is string=>uint(v)&&v!=='0'
const stamp=(v:unknown):v is string=>typeof v==='string'&&financeDate(v.slice(0,10))&&/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|[+-]\d{2}:\d{2})$/.test(v)&&Number.isFinite(Date.parse(v))
const canonical=(v:unknown):string=>JSON.stringify(v===null||typeof v!=='object'?v:Array.isArray(v)?v.map(x=>JSON.parse(canonical(x))):Object.fromEntries(Object.entries(v).sort(([a],[b])=>a<b?-1:a>b?1:0).map(([k,x])=>[k,JSON.parse(canonical(x))])))
const labels:Record<string,string>={SALES_AR:'Piutang penjualan',MATERIAL_AP:'Utang bahan',OPENING_AR:'Piutang saldo awal',OPENING_AP:'Utang saldo awal',PAYROLL_AP:'Utang gaji',ACCESSORY_AP:'Kredit retur aksesori',LAUNDRY_AP:'Utang nota laundry',LAUNDRY_RECEIPT:'Penerimaan laundry belum final',LAUNDRY_OPENING_UNINVOICED:'Laundry saldo awal belum ditagih'}
export function renderObligationReport(base:NativeReport,source:RuleSource,title:string):string{
 const at=new Date(Date.parse(source.readAt)+7*60*60*1000).toISOString().slice(0,19).replace('T',' ')
 const lines=[title,'LAPORAN DAN LAMPIRAN TAGIHAN ERP',base.body,'TAGIHAN YANG DIKETAHUI SAAT LAMPIRAN DIBUAT',
  `Dibaca ${at} WIB. Ini keadaan sumber saat dibaca, bukan rekonstruksi tagihan pada periode laporan lama.`,
  'Angka berikut disalin per dokumen dari ERP. Saldo awal, alokasi gaji, kredit retur, penerimaan dan nota dapat saling terkait. Jangan menjumlahkan baris ini sebagai total utang. Estimasi dan penerimaan belum ditagih tidak menjadi utang final.',
  'CAKUPAN IZIN DAN SUMBER',...Object.keys(source.coverage).sort().map(k=>`${k}: ${source.coverage[k]}.`)]
 for(const r of [...source.rows].filter(r=>r.financial_source!==null).sort((a,b)=>a.key<b.key?-1:a.key>b.key?1:0)){
  const f=r.financial_source!,remaining='value'in f.remaining?f.remaining.value+' IDR':`Belum diketahui (${f.remaining.reason})`
  lines.push(`${labels[r.domain]??r.domain} · ${r.label}: sisa ${remaining}; jatuh tempo tercatat ${f.recorded_due_date??'Belum diketahui'}; keadaan ekonomi ${r.economic_state}; pemeriksaan ${r.reason}; sumber ${r.key}.`,
   `Revisi sumber ${f.revision_basis}; hash dokumen ${f.document_sha256}. Referensi lengkap dipertahankan bersama sumber lampiran.`)
 }
 lines.push(`Arsip dasar ${base.id}; hash isi ${base.bodyHash}; sumber lampiran ${source.hash}; template native-obligation-report-1. Tidak memposting transaksi.`)
 return lines.join('\n\n')
}
function capturedRights(v:unknown,current:RuleRights):RuleRights{
 if(!v||typeof v!=='object'||Array.isArray(v))fail()
 const coverage=(v as Record<string,unknown>).coverage;if(!coverage||typeof coverage!=='object'||Array.isArray(coverage))fail()
 const c=coverage as Record<string,unknown>,captured={ar:c.sales_ar!=='EXCLUDED_BY_CURRENT_RIGHTS',ap:c.material_ap!=='EXCLUDED_BY_CURRENT_RIGHTS',payroll:c.payroll_ap!=='EXCLUDED_BY_CURRENT_RIGHTS',accessoryPayables:c.accessory_ap!=='EXCLUDED_BY_CURRENT_RIGHTS',laundry:c.laundry_ap!=='EXCLUDED_BY_CURRENT_RIGHTS'}
 for(const k of ['ar','ap','payroll','accessoryPayables','laundry'] as const)if(captured[k]&&current[k]!==true)fail()
 return captured
}
export async function parseObligationReportPreview(v:unknown,actor:string,finance:AnalysisFinanceAccess,rights:RuleRights):Promise<ObligationReportPreview>{
 const p=object(v,['contract_version','actor_scope_id','base_report','source','production_go'])
 if(p.contract_version!=='cp7.obligation-report-preview.v1'||p.actor_scope_id!==actor||p.production_go!==false)fail()
 const base=await parseNativeReport(p.base_report,actor,finance),source=parseRuleSource(p.source,base.query,actor,finance,rights)
 assertSameAnalysis(base.analysis,source.analysis);if(base.analysis.state!=='UNCHANGED'||source.analysis.state!=='UNCHANGED')fail()
 return{base,source}
}
export async function parseObligationReport(v:unknown,actor:string,finance:AnalysisFinanceAccess,rights:RuleRights):Promise<ObligationReport>{
 const d=object(v,['contract_version','actor_scope_id','id','series_id','revision','run_id','publication_id','request_id','title','reason','published_at','is_latest','source_hash','source','base_report','source_state','template_version','body','body_sha256','production_go'])
 if(d.contract_version!=='cp7.obligation-report.v1'||d.actor_scope_id!==actor||d.production_go!==false||![d.id,d.series_id,d.run_id,d.publication_id,d.request_id].every(guid)||!revision(d.revision)||typeof d.title!=='string'||!d.title.trim()||[...d.title].length>200||typeof d.reason!=='string'||!d.reason.trim()||[...d.reason].length>1000||!stamp(d.published_at)||typeof d.is_latest!=='boolean'||!['UNCHANGED','ARCHIVED_STALE'].includes(String(d.source_state))||d.template_version!=='native-obligation-report-1'||typeof d.body!=='string'||!hash(d.body_sha256)||!hash(d.source_hash))fail()
 const base=await parseNativeReport(d.base_report,actor,finance),source=parseRuleSource(d.source,base.query,actor,finance,capturedRights(d.source,rights))
 assertSameAnalysis(base.analysis,source.analysis)
 if(base.id!==d.publication_id||base.runId!==d.run_id||source.hash!==d.source_hash||Date.parse(source.readAt)>Date.parse(d.published_at as string)||base.analysis.state==='ARCHIVED_STALE'&&d.source_state!=='ARCHIVED_STALE')fail()
 const body=renderObligationReport(base,source,d.title as string),bytes=new TextEncoder().encode(body)
 if(body!==d.body||bytes.byteLength>8000000)fail()
 const digest=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes)),b=>b.toString(16).padStart(2,'0')).join('');if(digest!==d.body_sha256)fail()
 return{id:d.id,seriesId:d.series_id,revision:d.revision,requestId:d.request_id,title:d.title,reason:d.reason,publishedAt:d.published_at,isLatest:d.is_latest,state:d.source_state,body,bodyHash:d.body_sha256,base,source} as ObligationReport
}
export function assertSameObligationReport(a:ObligationReport,b:ObligationReport){
 assertSameReport(a.base,b.base)
 const frozen=(d:ObligationReport)=>{const {state,isLatest,base,source,...fields}=d;void state;void isLatest;void base;const {analysis,...snapshot}=source;void analysis;return{...fields,source:snapshot}}
 if(canonical(frozen(a))!==canonical(frozen(b)))fail()
}
function payload(v:unknown):ObligationReportPayload{
 const p=object(v,['publication_id','run_id','source_hash','title','reason','explicit_review','series_id','expected_revision'])
 if(!guid(p.publication_id)||!guid(p.run_id)||!hash(p.source_hash)||typeof p.title!=='string'||!p.title.trim()||[...p.title].length>200||typeof p.reason!=='string'||!p.reason.trim()||[...p.reason].length>1000||p.explicit_review!==true||(p.series_id===null?p.expected_revision!==null:!guid(p.series_id)||!revision(p.expected_revision)||BigInt(p.expected_revision)>=9223372036854775807n))fail()
 return structuredClone(p) as ObligationReportPayload
}
export async function parseObligationReportCommand(v:unknown,r:ObligationReportRequest,actor:string,finance:AnalysisFinanceAccess,rights:RuleRights){
 const c=object(v,['contract_version','request_id','status','document','production_go']),p=payload(r.payload)
 if(c.contract_version!=='cp7.obligation-report-command.v1'||c.request_id!==r.id||c.production_go!==false||!['COMMITTED','CLOSED_UNCOMMITTED'].includes(String(c.status)))fail()
 const document=c.status==='COMMITTED'?await parseObligationReport(c.document,actor,finance,rights):null
 if(c.status==='CLOSED_UNCOMMITTED'&&c.document!==null)fail()
 if(document&&(document.requestId!==r.id||document.base.id!==p.publication_id||document.base.runId!==p.run_id||document.source.hash!==p.source_hash||document.title!==p.title.trim()||document.reason!==p.reason.trim()||(p.series_id===null?document.revision!=='1':document.seriesId!==p.series_id||BigInt(document.revision)!==BigInt(p.expected_revision!)+1n)))fail()
 return{status:c.status as 'COMMITTED'|'CLOSED_UNCOMMITTED',document}
}
export function parseObligationReportIndex(v:unknown,actor:string,limit:number):ObligationReportIndex{
 const p=object(v,['contract_version','actor_scope_id','rows','total','next_before_id','page_complete','production_go'])
 if(p.contract_version!=='cp7.obligation-report-index.v1'||p.actor_scope_id!==actor||p.page_complete!==true||p.production_go!==false||!Array.isArray(p.rows)||!Number.isSafeInteger(limit)||limit<1||limit>50||p.rows.length>limit||!uint(p.total)||BigInt(p.total)<BigInt(p.rows.length)||p.next_before_id!==null&&!guid(p.next_before_id))fail()
 const rows=(p.rows as unknown[]).map(raw=>{const r=object(raw,['id','series_id','revision','run_id','publication_id','title','published_at','body_sha256']);if(![r.id,r.series_id,r.run_id,r.publication_id].every(guid)||!revision(r.revision)||typeof r.title!=='string'||!r.title||[...r.title].length>200||!stamp(r.published_at)||!hash(r.body_sha256))fail();return{id:r.id,seriesId:r.series_id,revision:r.revision,runId:r.run_id,publicationId:r.publication_id,title:r.title,publishedAt:r.published_at,bodyHash:r.body_sha256} as ObligationReportIndex['rows'][number]})
 if(new Set(rows.map(r=>r.id)).size!==rows.length||p.next_before_id!==null&&(rows.length!==limit||rows.at(-1)?.id!==p.next_before_id))fail()
 return{rows,total:p.total as string,nextBeforeId:p.next_before_id as string|null}
}
export const obligationReportRequestKey=(scope:string)=>'erp.cp7.obligation-report-request.v1:'+scope
function request(v:unknown):ObligationReportRequest{const r=object(v,['id','payload']);if(!guid(r.id))fail();return{id:r.id as string,payload:payload(r.payload)}}
export function readObligationReportRequest(scope:string):{pending:ObligationReportRequest|null;error:string|null}{try{const s=localStorage.getItem(obligationReportRequestKey(scope));return{pending:s===null?null:request(JSON.parse(s)),error:null}}catch{return{pending:null,error:'Permintaan lampiran belum dapat dibaca. Catatan lama dipertahankan.'}}}
export function persistObligationReportRequest(scope:string,r:ObligationReportRequest){request(r);const held=readObligationReportRequest(scope);if(held.error||held.pending&&canonical(held.pending)!==canonical(r))throw Error('Pastikan hasil lampiran yang tertunda terlebih dahulu.');const s=JSON.stringify(r);localStorage.setItem(obligationReportRequestKey(scope),s);if(localStorage.getItem(obligationReportRequestKey(scope))!==s)throw Error('Permintaan lampiran belum tersimpan; tidak ada permintaan yang dikirim.')}
export function clearObligationReportRequest(scope:string,r:ObligationReportRequest){const held=readObligationReportRequest(scope);if(held.error||canonical(held.pending)!==canonical(r))throw Error('Permintaan lampiran tersimpan berubah.');localStorage.removeItem(obligationReportRequestKey(scope));if(localStorage.getItem(obligationReportRequestKey(scope))!==null)throw Error('Permintaan lampiran belum dapat diselesaikan.')}
