import{expect,it}from'vitest'
import fixture from'../tests/fixtures/analysisFinanceSidecar.json'
import{parseAnalysisFinance,financeFiguresVisible}from'./nativeAnalysisFinanceSidecar'
import{parseStagedReference}from'./nativeAnalysisPages'
const context={requestId:fixture.request_id,reference:parseStagedReference(fixture.reference),query:fixture.query as {from_date:string;through_date:string;group_mode:'AS_SOLD'}}
const copy=()=>structuredClone(fixture)as any
it('reads the actual SQL consumer output and preserves official IDR decimals beyond safe integers',()=>{
 const r=parseAnalysisFinance(fixture,context)
 expect(r.result?.metrics.find(m=>m.id==='NATIVE_FINANCE:performance:sales_revenue_gl')?.value).toEqual({state:'KNOWN',value:'9007199254740993.01'})
 expect(r.capture).toMatchObject({unitsDone:5,unitsTotal:5,readiness:'READY'})
 expect(financeFiguresVisible(r,true)).toBe(true);expect(financeFiguresVisible(r,false)).toBe(false)
})
it.each(['request','job','query','reference','date','source-ref','version','operand','duplicate','unknown-ready','number-money','premature-result','wrong-total','ready-failure','smuggled'])('refuses a mismatched financial response: %s',kind=>{
 const x=copy(),other='99999999-9999-4999-8999-999999999999'
 if(kind==='request')x.request_id=other
 if(kind==='job')x.capture.owner_id=other
 if(kind==='query')x.query.from_date='2026-09-24'
 if(kind==='reference')x.reference.source_hash='f'.repeat(64)
 if(kind==='date')x.result.dates.as_of='2026-10-22'
 if(kind==='source-ref')x.result.metrics[0].value.refs[0].id='f'.repeat(64)
 if(kind==='version')x.result.metrics[0].version='different'
 if(kind==='operand')x.result.metrics[0].operands[0].value='2.00'
 if(kind==='duplicate')x.result.metrics.push(structuredClone(x.result.metrics[0]))
 if(kind==='unknown-ready')x.result.metrics[0].value={state:'UNKNOWN',unit:'IDR',reason:'SOURCE_INPUT_NOT_PROVEN',refs:x.result.metrics[0].value.refs}
 if(kind==='number-money')x.result.metrics[0].value.value=123
 if(kind==='premature-result')x.state=x.capture.state='RUNNING'
 if(kind==='wrong-total')x.capture.units_total=6
 if(kind==='ready-failure')x.capture.failure_code='CP7_FINANCE_CAPTURE_SOURCE_CHANGED'
 if(kind==='smuggled')x.extra='unexpected'
 expect(()=>parseAnalysisFinance(x,context)).toThrow()
})
it('keeps unstarted totals unknown, failed results absent, and revoked financial facts entirely absent',()=>{
 const running=copy();Object.assign(running,{state:'RUNNING',result:null});Object.assign(running.capture,{state:'RUNNING',units_done:0,units_total:null,report_read_at:null,readiness:null})
 expect(parseAnalysisFinance(running,context).capture?.unitsTotal).toBeNull()
 const failed=copy();Object.assign(failed,{state:'FAILED',result:null});Object.assign(failed.capture,{state:'FAILED',failure_code:'CP7_FINANCE_CAPTURE_SOURCE_CHANGED'})
 expect(financeFiguresVisible(parseAnalysisFinance(failed,context),true)).toBe(false)
 const revoked={...copy(),state:'ACCESS_REVOKED',capture:null,result:null}
 expect(parseAnalysisFinance(revoked,context)).toMatchObject({state:'ACCESS_REVOKED',capture:null,result:null})
 expect(()=>parseAnalysisFinance({...revoked,capture:fixture.capture},context)).toThrow()
})
it.each(['reference','report'])('refuses a different %s instant within the same millisecond',kind=>{
 const x=copy()
 if(kind==='reference')x.reference.captured_at='2026-10-23T00:00:00.000001Z'
 else x.result.report_read_at='2026-10-23T00:03:00.000001Z'
 expect(()=>parseAnalysisFinance(x,context)).toThrow()
})
it('accepts equivalent offsets and preserves all six fractional digits',()=>{
 const x=copy();x.reference.captured_at='2026-10-23T07:00:00.123456+07:00'
 x.capture.report_read_at='2026-10-23T00:03:00.654321Z';x.result.report_read_at='2026-10-23T07:03:00.654321+07:00'
 const exactContext={...context,reference:{...context.reference,capturedAt:'2026-10-23T00:00:00.123456Z'}}
 const r=parseAnalysisFinance(x,exactContext)
 expect(r.reference.capturedAt).toBe(x.reference.captured_at)
 expect(r.result?.reportReadAt).toBe(x.result.report_read_at)
})
it.each(['2026-02-30T00:00:00Z','2026-10-23T24:00:00Z','2026-10-23T00:03:00.0000001Z','2026-10-23T00:03:00+24:00'])('refuses invalid financial clocks: %s',at=>{
 const x=copy();x.capture.report_read_at=x.result.report_read_at=at
 expect(()=>parseAnalysisFinance(x,context)).toThrow()
})
