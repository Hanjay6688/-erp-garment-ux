// @vitest-environment jsdom
import {it,expect,beforeEach,vi} from 'vitest'
import * as f from '../tests/fixtures/nativeStagedReports'
import {parseStagedReportJob,parseStagedReport,parseStagedReportSection,parseStagedReportIndex,driveStagedReport,readStagedReportRequest,persistStagedReportRequest,
 clearStagedReportRequest,stagedReportPayload,stagedReportFreshnessText,stagedReportFailureText,type StagedReportReply} from './nativeStagedReports'

beforeEach(()=>localStorage.clear())
it('reads the job plan exactly: actuals, one section per page, freshness, summary; nothing else',()=>{
 const r=f.req()
 expect([0,1,2,3,4].map(n=>parseStagedReportJob(f.job(n),r).stage)).toEqual(['ACTUALS','SECTION','SECTION','FRESHNESS','SUMMARY'])
 expect(parseStagedReportJob(f.job(5,'DONE'),r).publicationId).toBe(f.publication)
 for(const bad of[f.job(1,'RUNNING',{stage:'ACTUALS'}),f.job(5,'DONE',{publication_id:null}),f.job(2,'RUNNING',{publication_id:f.publication}),f.job(0,'RUNNING',{unit_count:4}),
  f.job(0,'RUNNING',{run_id:f.series}),f.job(0,'RUNNING',{revision:'2'}),f.job(0,'RUNNING',{finance:'INCLUDED'}),f.job(2,'RUNNING',{sections_done:0}),f.job(0,'RUNNING',{extra:1})])
  expect(()=>parseStagedReportJob(bad,r),JSON.stringify(bad).slice(0,300)).toThrow()
 // A revision names its series and the next revision; a closed lookup has no units.
 const rev=f.req({series_id:f.series,expected_revision:'3'})
 expect(parseStagedReportJob(f.job(0,'RUNNING',{revision:'4'}),rev).revision).toBe('4');expect(()=>parseStagedReportJob(f.job(0),rev)).toThrow()
 expect(parseStagedReportJob({...f.job(0,'CLOSED_UNCOMMITTED'),unit_count:0,units_done:0,sections_done:0},r).state).toBe('CLOSED_UNCOMMITTED')
 const failed=parseStagedReportJob(f.job(2,'FAILED'),r);expect(stagedReportFailureText(failed.failure!)).toContain('Hak akses berubah')
})
it('verifies the sealed report: summary hash, the report hash over summary and sections, and ranges covering every target once',async()=>{
 const d=await parseStagedReport(f.report(),f.actor)
 expect([d.dataAsOf,d.sections.length,d.targetsTotal,d.finance,d.isLatest]).toEqual([f.dataAsOf,2,5,'DEFERRED',true])
 expect(stagedReportFreshnessText(d)).toBe('Saat laporan dibuat: ada 3 perubahan tercatat sejak data diambil; isi analisis tetap keadaan saat data diambil.')
 expect(stagedReportFreshnessText(d)).not.toMatch(/terkini/i)
 const tampered=f.report();tampered.summary+=' ';await expect(parseStagedReport(tampered,f.actor)).rejects.toThrow()
 const hash=f.report();hash.report_hash='0'.repeat(64);await expect(parseStagedReport(hash,f.actor)).rejects.toThrow()
 const gap=f.report();gap.sections[1].target_lo=5;await expect(parseStagedReport(gap,f.actor)).rejects.toThrow()
 const short=f.report({targets_total:6});await expect(parseStagedReport(short,f.actor)).rejects.toThrow()
 await expect(parseStagedReport(f.report({actor_scope_id:f.run}),f.actor)).rejects.toThrow()
 await expect(parseStagedReport(f.report({template_version:'native-report-1'}),f.actor)).rejects.toThrow()
 await expect(parseStagedReport(f.report({finance:'INCLUDED'}),f.actor)).rejects.toThrow()
 await expect(parseStagedReport(f.report({finance:'INCLUDED',financial_source_hash:'b'.repeat(64)}),f.actor)).resolves.toMatchObject({finance:'INCLUDED'})
})
it('reads one section only when its body matches the hash and range the report lists',async()=>{
 const d=await parseStagedReport(f.report(),f.actor)
 expect((await parseStagedReportSection(f.section(1),d,1)).body).toBe(f.sectionBodies[1])
 await expect(parseStagedReportSection(f.section(1,{body:f.sectionBodies[1]+'x'}),d,1)).rejects.toThrow()
 await expect(parseStagedReportSection(f.section(0),d,1)).rejects.toThrow()
 await expect(parseStagedReportSection(f.section(1,{report_hash:'0'.repeat(64)}),d,1)).rejects.toThrow()
 expect(parseStagedReportIndex(f.index(),f.actor,25).rows[0].dataAsOf).toBe(f.dataAsOf)
 expect(()=>parseStagedReportIndex({...f.index(),next_before_id:f.publication},f.actor,25)).toThrow()
})
it('drives publish then one step per unit; a skipped step waits and reads the status instead of stepping',async()=>{
 const r=f.req(),seen:string[]=[],replies:StagedReportReply[]=[{data:f.job(1),error:null},{data:{...f.job(1),worker_active:true},error:null},{data:f.job(2),error:null},{data:f.job(3),error:null},{data:f.job(4),error:null},{data:f.job(5,'DONE'),error:null}]
 const rpc={publish:vi.fn(async()=>{seen.push('publish');return{data:f.job(0),error:null}}),lookup:vi.fn(async()=>{seen.push('lookup');return replies.shift()!}),step:vi.fn(async()=>{seen.push('step');return replies.shift()!})}
 const last=await driveStagedReport({rpc,request:r,lookup:false,sleep:async()=>{}})
 expect(last?.state).toBe('DONE');expect(seen).toEqual(['publish','step','step','lookup','step','step','step'])
 // A refusal is thrown; the caller keeps the request.
 const refused={publish:async()=>({data:null,error:{code:'40001',message:'CP7_REPORT_REVISION_CHANGED'}}),lookup:rpc.lookup,step:rpc.step}
 await expect(driveStagedReport({rpc:refused,request:r,lookup:false})).rejects.toMatchObject({message:'CP7_REPORT_REVISION_CHANGED'})
})
it('keeps one pending request per actor scope and never replaces a different one',()=>{
 const r=f.req();persistStagedReportRequest('s',r);expect(readStagedReportRequest('s').pending).toEqual(r)
 expect(()=>persistStagedReportRequest('s',f.req({},f.series))).toThrow();persistStagedReportRequest('s',r)
 expect(()=>clearStagedReportRequest('s',f.req({},f.series))).toThrow();clearStagedReportRequest('s',r);expect(readStagedReportRequest('s').pending).toBeNull()
 localStorage.setItem('erp.cp7.report-request.v2:s','{');expect(readStagedReportRequest('s').error).toBeTruthy()
 for(const bad of[f.payload({finance:'MAYBE'}),f.payload({series_id:f.series}),f.payload({title:' '}),f.payload({identity_hash:'x'}),{...f.payload(),source_hash:'a'.repeat(64)}])
  expect(()=>stagedReportPayload(bad)).toThrow()
})
