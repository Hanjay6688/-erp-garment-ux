import {stagedRun} from '../cp7_current_frozen_finance_ui/vendor/tests/fixtures/nativeAnalysisPages'
import {frozenFinanceFixture} from '../cp7_current_frozen_finance_ui/vendor/tests/fixtures/frozenAnalysisFinance'
import type {StagedRequest} from './vendor/src/nativeStagedJob'
export async function progressFixture(ready=false){
 const source=await stagedRun({targets:120,pageSizes:[60,60]})
 const request:StagedRequest={id:source.pageSet.request_id,q:source.query,finance:'STAGED'}
 const finance=frozenFinanceFixture(source,ready?'READY':'RUNNING')
 const wire={contract_version:'cp7.frozen-analysis-progress.v1',policy_id:'D17-18-20261026',observed_at:'2026-10-07T10:05:00.654321Z',production_go:false,
  status:{...source.job('DONE'),finance_capture:finance,last_progress_at:'2026-10-07T10:02:00Z'},
  operational:{created_at:'2026-10-07T10:00:00Z',last_activity_at:'2026-10-07T10:02:00Z',finished_at:'2026-10-07T10:02:00Z',worker_observation:'NOT_EXPOSED'},
  finance:{capture_id:finance.capture.capture_id,created_at:'2026-10-07T10:00:01Z',last_activity_at:'2026-10-07T10:04:00Z',finished_at:ready?'2026-10-07T10:04:00Z':null,unit_attempts:0,report_ms:ready?12.34:null,worker_observation:'NO_LOCK_OBSERVED'}}
 const reference={sourceHash:source.pageSet.reference.source_hash,capturedAt:source.pageSet.reference.captured_at}
 return{source,request,wire,reference}
}
