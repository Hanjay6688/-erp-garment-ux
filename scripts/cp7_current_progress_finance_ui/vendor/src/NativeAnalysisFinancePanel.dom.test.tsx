// @vitest-environment jsdom
import{act}from'react'
import{createRoot,type Root}from'react-dom/client'
import{beforeEach,afterEach,expect,it,vi}from'vitest'
import NativeAnalysisFinancePanel from'./NativeAnalysisFinancePanel'
import{parseStagedReference}from'./nativeAnalysisPages'
import type{NativeDemandQuery}from'./nativeDemandHistory'
import type{StagedRequest}from'./nativeStagedJob'
import{stagedJobFixture}from'../tests/fixtures/nativeAnalysisPages'
import fixture from'../tests/fixtures/analysisFinanceSidecar.json'
let root:Root,container:HTMLDivElement
const run='66666666-6666-4666-8666-666666666666',reference=parseStagedReference(fixture.reference)
const request:StagedRequest={id:fixture.request_id,q:fixture.query as NativeDemandQuery,finance:'STAGED'}
const wire=(f:any=structuredClone(fixture),runId=run)=>({data:stagedJobFixture(f.request_id,'DONE',{run_id:runId,reference:f.reference,finance_capture:f}),error:null})
const flush=async()=>{await Promise.resolve();await new Promise(r=>setTimeout(r,0))}
async function render(get:(id:string)=>Promise<any>,r=request,allowed=true,runId=run){await act(async()=>{root.render(<NativeAnalysisFinancePanel request={r} reference={reference} runId={runId} allowed={allowed} get={get}/>);await flush()})}
async function reload(){await act(async()=>{const b=[...container.querySelectorAll('button')].find(x=>x.textContent==='Muat ulang status keuangan');expect(b).toBeTruthy();b!.click();await flush()})}
beforeEach(()=>{(globalThis as any).IS_REACT_ACT_ENVIRONMENT=true;container=document.createElement('div');document.body.append(container);root=createRoot(container)})
afterEach(async()=>{await act(async()=>root.unmount());container.remove();vi.restoreAllMocks()})
it('shows exact official money and the separate operational/report reading times',async()=>{
 const get=vi.fn(async()=>wire());await render(get)
 expect(container.textContent).toContain('Rp9.007.199.254.740.993,01')
 expect(container.textContent).toContain('Rp123,45');expect(container.textContent).toContain('Laba kotor')
 expect(container.textContent).toContain('Laporan resmi dibaca');expect(container.textContent).toContain('Data operasional per')
 expect(get).toHaveBeenCalledTimes(1)
})
it('never reads or displays figures after the current permission is removed',async()=>{
 const get=vi.fn(async()=>wire());await render(get);await render(get,request,false)
 expect(container.textContent).not.toContain('Rp');expect(container.textContent).not.toContain('5 dari 5')
 expect(container.textContent).toContain('Akun saat ini belum boleh');expect(get).toHaveBeenCalledTimes(1)
})
it('retires previously shown figures when the next status read is refused',async()=>{
 let denied=false;const get=async()=>denied?{data:null,error:{code:'42501',message:'CP7_ANALYSIS_FINANCE_ACCESS_CHANGED'}}:wire()
 await render(get);expect(container.textContent).toContain('Rp123,45');denied=true;await reload()
 expect(container.textContent).not.toContain('Rp123,45');expect(container.querySelector('[role="alert"]')).toBeTruthy()
})
it('keeps an unknown progress total distinct from zero and shows no early money',async()=>{
 const f=structuredClone(fixture)as any;Object.assign(f,{state:'RUNNING',result:null});Object.assign(f.capture,{state:'RUNNING',units_done:0,units_total:null,report_read_at:null,readiness:null})
 await render(async()=>wire(f));expect(container.textContent).toContain('jumlah langkah total belum diketahui')
 expect(container.textContent).not.toContain('0 dari 0');expect(container.textContent).not.toContain('Rp')
})
it('withholds financial conclusions while the official report is incomplete',async()=>{
 const f=structuredClone(fixture)as any;f.capture.readiness=f.result.readiness='BLOCKED';f.result.dependencies[0].completeness='PARTIAL';f.result.warnings=['NATIVE_FINANCIAL_READINESS:BLOCKED']
 for(const m of f.result.metrics){m.readiness='BLOCKED';if(m.metric_id.endsWith(':gross_profit'))m.value={state:'UNKNOWN',unit:'IDR',reason:'SOURCE_INPUT_NOT_PROVEN',refs:m.value.refs}}
 await render(async()=>wire(f));expect(container.textContent).toContain('HPP atau bukunya belum lengkap');expect(container.textContent).not.toContain('Rp')
})
it('rejects a status for another operational result',async()=>{
 await render(async()=>wire(fixture,'77777777-7777-4777-8777-777777777777'))
 expect(container.textContent).not.toContain('Rp');expect(container.textContent).toContain('Status keuangan belum bisa dibaca')
})
it.each(['2026-10-23T00:01:00Z','2026-10-23T00:00:00.000001Z'])('retires figures when operational capture changes to %s even if its source hash stays the same',async capturedAt=>{
 const get=vi.fn(async()=>wire());await render(get);expect(container.textContent).toContain('Rp123,45')
 const next={...reference,capturedAt}
 await act(async()=>{root.render(<NativeAnalysisFinancePanel request={request} reference={next} runId={run} allowed={true} get={get}/>);await flush()})
 expect(container.textContent).not.toContain('Rp');expect(container.textContent).toContain('Status keuangan belum bisa dibaca')
})
it('ignores a late response belonging to a previous selected request',async()=>{
 let release!:(v:any)=>void;const pending=new Promise(resolve=>{release=resolve})
 const other='88888888-8888-4888-8888-888888888888',f=structuredClone(fixture)as any;f.request_id=other
 f.result.source_hash='d'.repeat(64);f.result.dependencies[0].revision=f.result.dependencies[0].source_hash=f.result.source_hash
 for(const m of f.result.metrics)for(const fact of[m.value,...m.operands])for(const ref of fact.refs)ref.id=ref.revision=f.result.source_hash
 const cash=f.result.metrics.find((m:any)=>m.metric_id.endsWith(':cash'));cash.value.value=cash.operands[0].value='5.00'
 const get=async(id:string)=>id===request.id?pending:wire(f)
 await render(get);await render(get,{...request,id:other})
 expect(container.querySelector('[data-finance-metric$=":cash"]')?.textContent).toContain('Rp5')
 await act(async()=>{release(wire());await flush()})
 expect(container.querySelector('[data-finance-metric$=":cash"]')?.textContent).toContain('Rp5');expect(container.textContent).not.toContain('Rp123,45')
})
