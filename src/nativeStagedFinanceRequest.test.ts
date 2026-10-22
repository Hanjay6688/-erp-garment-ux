// @vitest-environment jsdom
import{beforeEach,expect,it}from'vitest'
import{readStagedRequest,persistStagedRequest,persistStagedCompletedRequest,stagedCompletedScope,stagedRequestKey,stagedRequestQuery,parseStagedJob}from'./nativeStagedJob'
import{stagedJobFixture}from'../tests/fixtures/nativeAnalysisPages'
import finance from'../tests/fixtures/analysisFinanceSidecar.json'
import actual from '../tests/fixtures/stagedFinanceRequestActual.json'
const scope='disposable:finance-actor',request={id:finance.request_id,q:finance.query as{from_date:string;through_date:string;group_mode:'AS_SOLD'},finance:'STAGED' as const}
beforeEach(()=>localStorage.clear())
it('reads the exact output of the real patched SQL request/status and retains its complete explicit query',()=>{
 const {finance_mode:mode,...q}=actual.query
 expect(mode).toBe('STAGED')
 const r={id:actual.response.request_id,q:{...q,group_mode:q.group_mode as 'AS_SOLD'},finance:'STAGED' as const}
 const parsed=parseStagedJob(actual.response,r.id,r)
 expect(parsed.state).toBe('RUNNING');expect(parsed.financeCapture?.capture?.unitsTotal).toBeNull()
 expect(parsed.financeCapture?.capture?.id).toBe(actual.response.finance_capture.capture.capture_id)
 persistStagedRequest(scope,r);expect(stagedRequestQuery(readStagedRequest(scope).pending!)).toEqual(actual.query)
})
it('retains the financial selection with the same UUID for pending and completed operational jobs',()=>{
 persistStagedRequest(scope,request);expect(readStagedRequest(scope).pending).toEqual(request)
 persistStagedCompletedRequest(scope,request);expect(readStagedRequest(stagedCompletedScope(scope)).pending).toEqual(request)
 expect(stagedRequestQuery(readStagedRequest(scope).pending!)).toEqual({...request.q,finance_mode:'STAGED'})
})
it('preserves legacy operational-only requests and rejects an unrecognized finance choice',()=>{
 const legacy={id:request.id,q:request.q};persistStagedRequest(scope,legacy)
 expect(readStagedRequest(scope).pending).toEqual(legacy);expect(stagedRequestQuery(legacy)).toEqual(request.q)
 localStorage.setItem(stagedRequestKey(scope),JSON.stringify({...legacy,finance:'INCLUDED_UNPROVEN'}));expect(readStagedRequest(scope).error).not.toBe('')
})
it('requires the bound finance sidecar only when the exact request selected it',()=>{
 const plain=stagedJobFixture(request.id,'DONE',{reference:finance.reference})
 expect(()=>parseStagedJob(plain,request.id,request)).toThrow()
 const linked={...plain,finance_capture:finance}
 expect(parseStagedJob(linked,request.id,request).financeCapture?.requestId).toBe(request.id)
 expect(()=>parseStagedJob(linked,request.id,{id:request.id,q:request.q})).toThrow()
})
