import {beforeEach,expect,it} from 'vitest'
import {stagedRun} from '../cp7_current_frozen_finance_ui/vendor/tests/fixtures/nativeAnalysisPages'
import {frozenFinanceFixture} from '../cp7_current_frozen_finance_ui/vendor/tests/fixtures/frozenAnalysisFinance'
import {projectCombinedProgress} from './progress'
import type {StagedRequest} from '../cp7_current_frozen_finance_ui/vendor/src/nativeStagedJob'
let f: Awaited<ReturnType<typeof stagedRun>>, request: StagedRequest
const clock = '2026-10-07T10:05:00.654321Z'
beforeEach(async()=>{f=await stagedRun({targets:120,pageSizes:[60,60]});request={id:f.pageSet.request_id,q:f.query,finance:'STAGED'}})
function runningFinance(done=0,total:number|null=null){const v=frozenFinanceFixture(f,'RUNNING');v.capture.units_done=done;v.capture.units_total=total;return v}
function job(state:'DONE'|'RUNNING'='DONE',finance=runningFinance()){return f.job(state,{targets_done_in_stage:state==='DONE'?0:60,finance_capture:finance})}
it('does not call production DONE a completed combined analysis',()=>{
 const p=projectCombinedProgress(job(),request,clock)
 expect(p.operational.state).toBe('COMPLETED');expect(p.state).toBe('RUNNING');expect(p.complete).toBe(false)
 expect(p.finance.total).toBe(null);expect(p.finance.percent).toBe(null);expect(p.overallPercent).toBe(null)
})
it('uses completed units only and never estimates a combined percentage',()=>{
 const raw=job('DONE',runningFinance(2,6)),a=projectCombinedProgress(raw,request,clock),b=projectCombinedProgress(raw,request,'2026-10-08T10:05:00Z')
 expect(a.finance.percent).toBe(33.33);expect(a.finance).toEqual(b.finance);expect(a.state).toBe(b.state)
 expect(b.elapsedSinceCaptureMs).toBeGreaterThan(a.elapsedSinceCaptureMs!);expect(b.overallPercent).toBe(null)
})
it('withholds an operational percentage until the server plan is final',()=>{
 const raw={...job('RUNNING'),plan_final:false},p=projectCombinedProgress(raw,request,clock)
 expect(p.operational.total).toBe(null);expect(p.operational.percent).toBe(null);expect(p.operational.state).toBe('PREPARING')
})
it('completes only when official finance and production both complete',()=>{
 const raw=job('DONE',frozenFinanceFixture(f)),p=projectCombinedProgress(raw,request,clock)
 expect(p.state).toBe('COMPLETED');expect(p.complete).toBe(true);expect(p.finance.percent).toBe(100)
 expect(projectCombinedProgress({...raw,state:'RUNNING',run_id:null,stage:'REPORT'},request,clock).complete).toBe(false)
})
it.each(['BLOCKED','LIMITED'])('keeps completed capture with official %s report incomplete',readiness=>{
 const fin=frozenFinanceFixture(f);fin.capture.readiness=fin.result.readiness=readiness
 for(const m of fin.result.metrics)m.readiness=readiness
 fin.result.dependencies[0].completeness='PARTIAL';fin.result.warnings=['NATIVE_FINANCIAL_READINESS:'+readiness]
 const p=projectCombinedProgress(job('DONE',fin),request,clock)
 expect(p.finance.percent).toBe(100);expect(p.finance.state).toBe('BLOCKED');expect(p.complete).toBe(false)
 expect(p.state).toBe('BLOCKED');expect(p.message).toContain('bukan nol')
})
it('removes finance counts and percentages when current access is revoked',()=>{
 const p=projectCombinedProgress(job('DONE',frozenFinanceFixture(f,'ACCESS_REVOKED')),request,clock)
 expect(p.finance.done).toBe(null);expect(p.finance.percent).toBe(null);expect(p.complete).toBe(false)
 expect(p.state).toBe('ACCESS_REVOKED');expect(p.recovery).toBe('RESTORE_ACCESS')
})
it('preserves an observed finance failure and never attributes it to elapsed time',()=>{
 const fin=runningFinance(2,6);fin.state=fin.capture.state='FAILED';fin.capture.failure_code='CP7_FINANCE_CAPTURE_SOURCE_CHANGED'
 const p=projectCombinedProgress(job('DONE',fin),request,clock)
 expect(p.state).toBe('FAILED');expect(p.finance.failureCode).toBe('CP7_FINANCE_CAPTURE_SOURCE_CHANGED')
 expect(p.complete).toBe(false);expect(p.recovery).toBe('NEW_REQUEST_AFTER_SOURCE_CHECK')
})
it('does not fabricate worker state, queue position, finance heartbeat or terminal duration',()=>{
 const p=projectCombinedProgress(job(),request,clock)
 expect(p.workerState).toBe('NOT_EXPOSED');expect(p.queuePosition).toBe(null)
 expect(p.financeLastProgressAt).toBe(null);expect(p.terminalDurationMs).toBe(null)
})
it('retains same source, UUID and progress across reopen without mutating the server result',()=>{
 const raw=job('DONE',runningFinance(3,6)),before=JSON.stringify(raw),p=projectCombinedProgress(raw,request,clock)
 expect(projectCombinedProgress(JSON.parse(before),{...request},clock)).toEqual(p)
 expect(JSON.stringify(raw)).toBe(before);expect(p.requestId).toBe(request.id);expect(p.recovery).toBe('SAME_REQUEST_STATUS')
})
it('does not give old operational-only results finance completion credit',()=>{
 const {finance:_,...operational}=request,p=projectCombinedProgress(f.job('DONE'),operational,clock)
 expect(p.complete).toBe(true);expect(p.finance.state).toBe('NOT_REQUESTED');expect(p.message).toContain('keuangan tidak termasuk')
})
it('rejects mixed request, source and financial mode before displaying progress',()=>{
 const raw=job();expect(()=>projectCombinedProgress(raw,{...request,id:'00000000-0000-0000-0000-000000000001'},clock)).toThrow()
 const other=structuredClone(raw) as any;other.finance_capture.reference.source_hash='0'.repeat(64)
 expect(()=>projectCombinedProgress(other,request,clock)).toThrow()
 expect(()=>projectCombinedProgress(f.job('DONE'),request,clock)).toThrow()
})
it('reports client clock skew without a negative or fabricated duration',()=>{
 const p=projectCombinedProgress(job(),request,'2020-01-01T00:00:00Z')
 expect(p.elapsedSinceCaptureMs).toBe(null);expect(p.clockBeforeCapture).toBe(true)
 expect(p.finance.percent).toBe(null);expect(p.complete).toBe(false)
})
it('never marks expired results complete',()=>{
 const raw={...job('DONE',frozenFinanceFixture(f)),retention:{days:7,kept_until:'2026-10-14T10:03:00Z',state:'EXPIRED'}}
 const p=projectCombinedProgress(raw,request,clock);expect(p.state).toBe('EXPIRED');expect(p.complete).toBe(false)
})
it('does not let READY finance hide a failed operational job',()=>{
 const raw={...job('RUNNING',frozenFinanceFixture(f)),state:'FAILED',failure:{unit:12,sqlstate:'P0001',code:'CP7_ANALYSIS_STAGE_ERROR'}}
 const p=projectCombinedProgress(raw,request,clock);expect(p.state).toBe('FAILED');expect(p.complete).toBe(false)
 expect(p.operational.failureCode).toBe('CP7_ANALYSIS_STAGE_ERROR');expect(p.finance.state).toBe('COMPLETED')
})
