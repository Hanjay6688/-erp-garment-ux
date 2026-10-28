import {beforeEach,expect,it} from 'vitest'
import {stagedRun} from '../cp7_current_frozen_finance_ui/vendor/tests/fixtures/nativeAnalysisPages'
import {frozenFinanceFixture} from '../cp7_current_frozen_finance_ui/vendor/tests/fixtures/frozenAnalysisFinance'
import type {StagedRequest} from '../cp7_current_frozen_finance_ui/vendor/src/nativeStagedJob'
import {readProgressTelemetry} from './telemetry'
let f:Awaited<ReturnType<typeof stagedRun>>,request:StagedRequest
beforeEach(async()=>{f=await stagedRun({targets:120,pageSizes:[60,60]});request={id:f.pageSet.request_id,q:f.query,finance:'STAGED'}})
function wire(ready=false){
 const finance=frozenFinanceFixture(f,ready?'READY':'RUNNING'),at='2026-10-07T10:05:00.654321Z'
 return{contract_version:'cp7.frozen-analysis-progress.v1',policy_id:'D17-18-20261026',observed_at:at,production_go:false,
  status:f.job('DONE',{finance_capture:finance,last_progress_at:'2026-10-07T10:02:00Z'}),
  operational:{created_at:'2026-10-07T10:00:00Z',last_activity_at:'2026-10-07T10:02:00Z',finished_at:'2026-10-07T10:02:00Z',worker_observation:'NOT_EXPOSED'},
  finance:{capture_id:finance.capture.capture_id,created_at:'2026-10-07T10:00:01Z',last_activity_at:'2026-10-07T10:04:00Z',finished_at:ready?'2026-10-07T10:04:00Z':null,unit_attempts:0,report_ms:ready?12.34:null,worker_observation:'NO_LOCK_OBSERVED'}}
}
it('uses the server clock and source-bound activity for elapsed times',()=>{
 const r=readProgressTelemetry(wire(),request);expect(r.clock).toBe('SERVER');expect(r.elapsedMs).toBe(300654)
 expect(r.finance?.idleMs).toBe(60654);expect(r.operational.elapsedMs).toBe(120000);expect(r.processingFinished).toBe(false)
 expect(Object.hasOwn(r.progress,'elapsedClock')).toBe(false);expect(Object.hasOwn(r.progress,'elapsedSinceCaptureMs')).toBe(false)
})
it('reports absent worker observation without claiming the runner queued this capture',()=>{
 const w=wire();expect(readProgressTelemetry(w,request).finance?.activity).toBe('NO_WORKER_OBSERVED')
 w.finance.worker_observation='LOCK_HELD';const r=readProgressTelemetry(w,request)
 expect(r.finance?.activity).toBe('WORKER_OBSERVED');expect(r.queuePosition).toBe(null)
})
it('freezes measured terminal duration when reopening much later',()=>{
 const w=wire(true),a=readProgressTelemetry(w,request);w.observed_at='2026-10-08T10:05:00Z';const b=readProgressTelemetry(w,request)
 expect(a.processingFinished).toBe(true);expect(a.elapsedMs).toBe(240000);expect(b.elapsedMs).toBe(a.elapsedMs)
 expect(b.finance?.elapsedMs).toBe(a.finance?.elapsedMs);expect(b.finishedAt).toBe(a.finishedAt)
})
it('keeps completed processing separate from blocked business readiness',()=>{
 const w=wire(true),s=(w.status as any).finance_capture;s.capture.readiness=s.result.readiness='BLOCKED'
 for(const m of s.result.metrics)m.readiness='BLOCKED'
 s.result.dependencies[0].completeness='PARTIAL';s.result.warnings=['NATIVE_FINANCIAL_READINESS:BLOCKED']
 const r=readProgressTelemetry(w,request);expect(r.processingFinished).toBe(true);expect(r.progress.complete).toBe(false)
 expect(r.progress.state).toBe('BLOCKED');expect(r.overallPercent).toBe(null)
})
it('does not infer a failed or stalled job just because time passes',()=>{
 const w=wire();w.observed_at='2026-10-09T10:05:00Z';const r=readProgressTelemetry(w,request)
 expect(r.stallState).toBe('NOT_INFERRED');expect(r.progress.state).toBe('RUNNING');expect(r.progress.finance.percent).toBe(null)
})
it('rejects finance metadata when current access is revoked',()=>{
 const w=wire();w.status=f.job('DONE',{finance_capture:frozenFinanceFixture(f,'ACCESS_REVOKED'),last_progress_at:w.operational.last_activity_at})
 expect(()=>readProgressTelemetry(w,request)).toThrow();const r=readProgressTelemetry({...w,finance:null},request)
 expect(r.finance).toBe(null);expect(r.elapsedMs).toBe(null);expect(r.processingFinished).toBe(false)
})
it.each(['capture_id','created_at','last_activity_at','finished_at'])('rejects mismatched or impossible finance %s',field=>{
 const w=wire();Object.assign(w.finance,{[field]:field==='capture_id'?'00000000-0000-0000-0000-000000000099':field==='created_at'?'2026-10-07T10:06:00Z':field==='finished_at'?'2026-10-07T10:04:00Z':'2026-10-07T10:06:00Z'})
 expect(()=>readProgressTelemetry(w,request)).toThrow()
})
it('binds operational activity to the exact server status microsecond',()=>{
 const w=wire();w.operational.last_activity_at='2026-10-07T10:02:00.000001Z';expect(()=>readProgressTelemetry(w,request)).toThrow()
})
it('rejects missing finish time for a terminal capture',()=>{
 const w=wire(true);w.finance.finished_at=null;expect(()=>readProgressTelemetry(w,request)).toThrow()
})
it('rejects extra fields and foreign request before returning original status',()=>{
 const w=wire();expect(()=>readProgressTelemetry({...w,debug:true},request)).toThrow()
 expect(()=>readProgressTelemetry(w,{...request,id:'00000000-0000-0000-0000-000000000099'})).toThrow()
 const r=readProgressTelemetry(w,request);expect(r.originalStatus).toBe(w.status)
})
