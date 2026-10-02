// @vitest-environment jsdom
import {beforeEach,afterEach,it,expect,vi} from 'vitest'
import {reportCrypto,reportBodyDigest} from '../tests/fixtures/reportCrypto.mjs'
import {appendixPreviewFixture,appendixDocumentFixture,appendixActor,appendixFinance,appendixRights} from '../tests/fixtures/nativeObligationReports'
import {ruleFixtureId} from '../tests/fixtures/nativeRuleSource'
import {parseObligationReportPreview,parseObligationReport,parseObligationReportCommand,assertSameObligationReport,persistObligationReportRequest,readObligationReportRequest,clearObligationReportRequest,obligationReportRequestKey,type ObligationReportRequest} from './nativeObligationReports'
beforeEach(()=>{vi.stubGlobal('crypto',reportCrypto);localStorage.clear()})
afterEach(()=>{vi.unstubAllGlobals();localStorage.clear()})
it('copies exact amounts and absent dates, with a separate current-knowledge date from the base period',async()=>{
 const p=await parseObligationReportPreview(appendixPreviewFixture(),appendixActor,appendixFinance,appendixRights),d=await parseObligationReport(await appendixDocumentFixture(),appendixActor,appendixFinance,appendixRights)
 expect(d.body).toContain('9007199254740993.01 IDR');expect(d.body).toContain('jatuh tempo tercatat Belum diketahui');expect(d.body).toContain('Dibaca 2026-10-01 17:00:00 WIB');expect(d.body).toContain('Jangan menjumlahkan baris ini sebagai total utang');expect(d.base.query).toEqual(p.base.query)
})
it('rejects a newly digested forged amount, a false due date, altered Native money and a foreign Original',async()=>{
 const raw=await appendixDocumentFixture(),forged=structuredClone(raw);forged.body=forged.body.replace('9007199254740993.01','9007199254740993.02');forged.body_sha256=reportBodyDigest(forged.body)
 await expect(parseObligationReport(forged,appendixActor,appendixFinance,appendixRights)).rejects.toThrow()
 const due=structuredClone(raw);Object.assign(due.source.rows.at(-1)!.financial_source!,{recorded_due_date:'2026-10-01'});await expect(parseObligationReport(due,appendixActor,appendixFinance,appendixRights)).rejects.toThrow()
 const money=structuredClone(raw);Object.assign(Reflect.get(money.source.rows.at(-1)!.financial_source!,'remaining'),{value:'0'});await expect(parseObligationReport(money,appendixActor,appendixFinance,appendixRights)).rejects.toThrow()
 await expect(parseObligationReport({...raw,publication_id:ruleFixtureId(97)},appendixActor,appendixFinance,appendixRights)).rejects.toThrow()
})
it('keeps the complete old body when source changes, without relabeling current facts as history',async()=>{
 const raw=await appendixDocumentFixture(),one=await parseObligationReport(raw,appendixActor,appendixFinance,appendixRights),old=structuredClone(raw);old.source_state='ARCHIVED_STALE';old.base_report.source_state='ARCHIVED_STALE';old.base_report.analysis.source_state='ARCHIVED_STALE';old.is_latest=false
 const reopened=await parseObligationReport(old,appendixActor,appendixFinance,appendixRights);assertSameObligationReport(one,reopened);expect(reopened.body).toBe(one.body);expect(reopened.source.readAt).toBe(one.source.readAt)
 await expect(parseObligationReport({...old,source_state:'UNCHANGED'},appendixActor,appendixFinance,appendixRights)).rejects.toThrow()
})
it('denies narrower rights before returning saved salary facts but permits a later broader scope without rewriting the old snapshot',async()=>{
 const raw=await appendixDocumentFixture();await expect(parseObligationReport(raw,appendixActor,appendixFinance,{...appendixRights,payroll:false})).rejects.toThrow()
 expect((await parseObligationReport(raw,appendixActor,appendixFinance,{...appendixRights,laundry:true,accessoryPayables:true})).body).toBe(raw.body)
})
it('persists only one reviewed UUID and operator payload, retaining corrupt or unresolved intent',async()=>{
 const p=appendixPreviewFixture(),r:ObligationReportRequest={id:ruleFixtureId(98),payload:{publication_id:p.base_report.id,run_id:p.base_report.run_id,source_hash:p.source.source_hash,title:'Judul operator',reason:'Alasan operator',explicit_review:true,series_id:null,expected_revision:null}}
 persistObligationReportRequest('s',r);expect(readObligationReportRequest('s').pending).toEqual(r);expect(()=>persistObligationReportRequest('s',{...r,id:ruleFixtureId(99)})).toThrow();expect(()=>persistObligationReportRequest('s',{...r,source:p.source} as ObligationReportRequest)).toThrow()
 const raw=await appendixDocumentFixture(r),reply={contract_version:'cp7.obligation-report-command.v1',request_id:r.id,status:'COMMITTED',document:raw,production_go:false};expect((await parseObligationReportCommand(reply,r,appendixActor,appendixFinance,appendixRights)).document?.title).toBe('Judul operator')
 const closed={...reply,status:'CLOSED_UNCOMMITTED',document:null};expect((await parseObligationReportCommand(closed,r,appendixActor,appendixFinance,appendixRights)).document).toBeNull();await expect(parseObligationReportCommand({...closed,document:raw},r,appendixActor,appendixFinance,appendixRights)).rejects.toThrow()
 clearObligationReportRequest('s',r);localStorage.setItem(obligationReportRequestKey('s'),'{broken');expect(readObligationReportRequest('s').error).toBeTruthy();expect(()=>persistObligationReportRequest('s',r)).toThrow();expect(localStorage.getItem(obligationReportRequestKey('s'))).toBe('{broken')
})
