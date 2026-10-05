import{it,expect}from'vitest'
import{analysisFinanceFixture}from'../tests/fixtures/nativeAnalysisFinance'
import{parseNativeAnalysis,analysisReport,analysisPrompt,assertSameAnalysis}from'./nativeAnalysis'
import type{NativeDemandQuery}from'./nativeDemandHistory'
const access={ownerReports:true,preflight:true}
const parse=(e:ReturnType<typeof analysisFinanceFixture>,rights=access)=>parseNativeAnalysis(e,e.query as NativeDemandQuery,e.analysis.scope.actor_scope_id,rights)
it('retains exact huge book values and signed loss from the accepted financial source in all consumers',()=>{
 const r=parse(analysisFinanceFixture()),assets=r.analysis.metrics.find(m=>m.metric_id==='NATIVE_FINANCE:financial_position:assets')!
 expect(assets.value).toMatchObject({state:'KNOWN',value:'9007199254740993.01'})
 expect(r.finance!.report.snapshot.financial_position.current_earnings).toBe('-7.02');expect(analysisReport(r)).toContain('-7,02');expect(JSON.parse(analysisPrompt(r,'periksa').split('<DATA_ERP_JSON>\n\n')[1].split('\n\n</DATA_ERP_JSON>')[0]).financial_source).toEqual(r.finance);expect(r.finance!.report.snapshot.basis.supplier_exposure_basis).toBe('CURRENT_OPERATIONAL_STATE')
})
it('keeps profit and inventory valuation unknown under blocked HPP while retaining recorded cash for examination',()=>{
 const r=parse(analysisFinanceFixture(true)),find=(key:string)=>r.analysis.metrics.find(m=>m.metric_id.endsWith(':'+key))!
 expect(find('net_profit').value.state).toBe('UNKNOWN');expect(find('fg_inventory').value.state).toBe('UNKNOWN');expect(find('cash').value.state).toBe('KNOWN');expect(analysisReport(r)).toContain('Biaya sumber belum diketahui');expect(r.analysis.financial_readiness).toBe('BLOCKED')
})
it('requires current owner-report and preflight capabilities before accepting protected operands',()=>{
 expect(()=>parse(analysisFinanceFixture(),{ownerReports:false,preflight:false})).toThrow()
 expect(()=>parse(analysisFinanceFixture(false,true),{ownerReports:true,preflight:false})).toThrow()
 expect(()=>parse(analysisFinanceFixture(),{ownerReports:true,preflight:false})).not.toThrow()
})
it('rejects changed amounts, forged READY, detached refs and a financial source from a different period',()=>{
 const amount=analysisFinanceFixture();Object.assign(amount.analysis.metrics.find(m=>m.metric_id.endsWith(':assets'))!.value,{value:'1'});expect(()=>parse(amount)).toThrow()
 const ready=analysisFinanceFixture(true);Object.assign(ready.analysis,{financial_readiness:'READY'});expect(()=>parse(ready)).toThrow()
 const refs=analysisFinanceFixture();refs.analysis.metrics.find(m=>m.metric_id.endsWith(':cash'))!.value.refs[0].revision='different';expect(()=>parse(refs)).toThrow()
 const dates=analysisFinanceFixture();dates.financial_source.dates.from='2000-01-01';expect(()=>parse(dates)).toThrow()
})
it('rejects a changed protected original archive even if its displayed metric remains unchanged',()=>{
 const first=parse(analysisFinanceFixture()),next=parse(analysisFinanceFixture());next.finance!.report.snapshot.data_confidence.warning_issue_count='9';expect(()=>assertSameAnalysis(first,next)).toThrow()
})
it('rejects an impossible calendar date instead of normalizing it to another capture day',()=>{
 const e=analysisFinanceFixture();e.analysis.snapshot.effective_as_of='2026-02-30T03:00:00Z';expect(()=>parse(e)).toThrow()
})
