// Parser/DOM stand-ins. These are never Native monetary qualification evidence.
import {reportBodyDigest} from './reportCrypto.mjs'
import {payrollRuleSourceFixture,ruleFixtureActor,ruleFixtureId} from './nativeRuleSource'
import {parseNativeReport} from '../../src/nativeAnalysisReports'
import {parseRuleSource} from '../../src/nativeRuleSource'
import {renderObligationReport,type ObligationReportRequest} from '../../src/nativeObligationReports'
import type {NativeDemandQuery} from '../../src/nativeDemandHistory'
export const appendixActor=ruleFixtureActor,appendixFinance={ownerReports:false,preflight:false},appendixRights={ar:true,ap:true,payroll:true}
export function appendixPreviewFixture(){
 const source=payrollRuleSourceFixture(),e=source.analysis,body='Laporan dasar uji parser. Bukan bukti transaksi Native.'
 const base_report={contract_version:'cp7.report-publication.v1',actor_scope_id:appendixActor,id:ruleFixtureId(91),series_id:ruleFixtureId(92),revision:'1',run_id:e.run_id,request_id:ruleFixtureId(93),kind:'PERIOD',period_query:e.query,title:'Laporan dasar uji',reason:'Kontrak parser',template_version:'native-report-1',body,body_sha256:reportBodyDigest(body),source_hash:e.analysis.snapshot.source_hash,semantic_hash:e.analysis.semantic_hash,published_at:'2026-10-01T09:00:00+00:00',is_latest:true,source_state:e.source_state,analysis:structuredClone(e),production_go:false}
 return{contract_version:'cp7.obligation-report-preview.v1',actor_scope_id:appendixActor,base_report,source,production_go:false}
}
export async function appendixDocumentFixture(r?:ObligationReportRequest){
 const p=appendixPreviewFixture(),base=await parseNativeReport(p.base_report,appendixActor,appendixFinance),source=parseRuleSource(p.source,base.query as NativeDemandQuery,appendixActor,appendixFinance,appendixRights),title=r?.payload.title.trim()??'Lampiran contoh',reason=r?.payload.reason.trim()??'Stand-in, bukan bukti Native',body=renderObligationReport(base,source,title)
 return{contract_version:'cp7.obligation-report.v1',actor_scope_id:appendixActor,id:ruleFixtureId(94),series_id:r?.payload.series_id??ruleFixtureId(95),revision:r?.payload.expected_revision?(BigInt(r.payload.expected_revision)+1n).toString():'1',run_id:base.runId,publication_id:base.id,request_id:r?.id??ruleFixtureId(96),title,reason,published_at:'2026-10-01T10:00:01+00:00',is_latest:true,source_hash:source.hash,source:p.source,base_report:p.base_report,source_state:'UNCHANGED',template_version:'native-obligation-report-1',body,body_sha256:reportBodyDigest(body),production_go:false}
}
