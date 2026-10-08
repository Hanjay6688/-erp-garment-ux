import {reportBodyDigest} from './reportCrypto.mjs'
import type {StagedAnalysis} from '../../src/nativeAnalysisPages'
import type {StagedReportRequest} from '../../src/nativeStagedReports'
// Business Report v2 wire shapes as report-staged.sql returns them, with real
// SHA-256 values (summary, sections, report hash over both). Synthetic; the
// Native, race and HTTP evidence is the P19 report v2 suite.
type Json=Record<string,any>
export const actor='11111111-1111-4111-8111-111111111111'
export const run='22222222-2222-4222-8222-222222222222'
export const series='33333333-3333-4333-8333-333333333333'
export const publication='44444444-4444-4444-8444-444444444444'
export const request='55555555-5555-4555-8555-555555555555'
export const identityHash='e'.repeat(64)
export const dataAsOf='2026-10-08T01:00:00.000000+00:00'
export const query={from_date:'2026-01-01',through_date:'2026-10-07',group_mode:'AS_SOLD'}
export const sha=(s:string)=>reportBodyDigest(s)
const utf8=(s:string)=>new TextEncoder().encode(s).byteLength
export const staged={kind:'STAGED',set:{runId:run,identityHash,reference:{capturedAt:dataAsOf,sourceHash:'a'.repeat(64)}},header:{query}} as unknown as StagedAnalysis
export function payload(extra:Json={}){return{run_id:run,identity_hash:identityHash,kind:'DAILY',series_id:null,expected_revision:null,title:'Briefing pagi',reason:'Ditinjau dari analisis bertahap',finance:'DEFERRED',explicit_review:true,...extra}}
export const req=(extra:Json={},id=request):StagedReportRequest=>({id,payload:payload(extra)} as StagedReportRequest)
const STAGES=['ACTUALS','SECTION','SECTION','FRESHNESS','SUMMARY']
// sections = 2: units 0 ACTUALS, 1-2 SECTION, 3 FRESHNESS, 4 SUMMARY.
export function job(unitsDone:number,state='RUNNING',extra:Json={}){
 return{contract_version:'cp7.report-job.v2',request_id:request,state,stage:state==='RUNNING'?STAGES[unitsDone]:null,units_done:unitsDone,unit_count:5,unit_attempts:0,
  sections_done:Math.max(0,Math.min(unitsDone-1,2)),section_count:2,run_id:run,identity_hash:identityHash,data_as_of:dataAsOf,kind:'DAILY',finance:'DEFERRED',
  series_id:series,revision:'1',last_progress_at:'2026-10-08T02:00:00.000000+00:00',publication_id:state==='DONE'?publication:null,
  failure:state==='FAILED'?{unit:unitsDone,sqlstate:'42501',code:'CP7_REPORT_ACCESS_CHANGED'}:null,production_go:false,...extra}
}
export const sectionBodies=['BAGIAN 1 dari 2 · Target 1–3 dari 5 · Data analisis per 2026-10-08 08:00:00 WIB.\n\nSKU-1 · Produk 1 · size S · Aktif: stok fisik saat analisis 5 PCS; stok fisik aktual per 2026-10-08 09:00:00 WIB 8 PCS',
 'BAGIAN 2 dari 2 · Target 4–5 dari 5 · Data analisis per 2026-10-08 08:00:00 WIB.\n\nSKU-4 · Produk 4 · size S · Ditunda: stok fisik saat analisis 0 PCS']
export const summary='Briefing pagi\n\nBRIEFING HARIAN\n\nData analisis per 2026-10-08 08:00:00 WIB (analisis bertahap, 5 target). Isi analisis adalah keadaan pada waktu itu, bukan angka saat ini.'
export function report(extra:Json={}){
 const sections=[{index:0,target_lo:1,target_hi:3,utf8_bytes:utf8(sectionBodies[0]),sha256:sha(sectionBodies[0])},{index:1,target_lo:4,target_hi:5,utf8_bytes:utf8(sectionBodies[1]),sha256:sha(sectionBodies[1])}]
 const s=extra.summary??summary
 return{contract_version:'cp7.report-publication.v2',actor_scope_id:actor,id:publication,series_id:series,revision:'1',run_id:run,request_id:request,identity_hash:identityHash,
  data_as_of:dataAsOf,kind:'DAILY',period_query:query,title:'Briefing pagi',reason:'Ditinjau dari analisis bertahap',template_version:'native-report-staged-1',finance:'DEFERRED',
  report_date:'2026-10-08',actuals_read_at:'2026-10-08T02:00:00.000000+00:00',financial_source_hash:null,
  freshness:{state:'CHANGES_RECORDED',evaluated_at:'2026-10-08T02:00:01.000000+00:00',changes_total:'3'},targets_total:5,summary:s,summary_sha256:sha(s),sections,
  report_hash:sha([sha(s),...sections.map(x=>x.sha256)].join('\n')),published_at:'2026-10-08T02:00:02.000000+00:00',is_latest:true,access_epoch:'f'.repeat(64),production_go:false,...extra}
}
export function section(i:number,extra:Json={}){const r=report(),e=r.sections[i]
 return{contract_version:'cp7.report-section.v2',publication_id:publication,report_hash:r.report_hash,index:i,section_count:2,target_lo:e.target_lo,target_hi:e.target_hi,
  utf8_bytes:e.utf8_bytes,sha256:e.sha256,body:sectionBodies[i],...extra}}
export function index(){const r=report();return{contract_version:'cp7.report-index.v2',actor_scope_id:actor,rows:[{id:publication,series_id:series,revision:'1',run_id:run,kind:'DAILY',
 title:r.title,period_query:query,data_as_of:dataAsOf,finance:'DEFERRED',published_at:r.published_at,report_hash:r.report_hash}],total:'1',next_before_id:null,page_complete:true,production_go:false}}
