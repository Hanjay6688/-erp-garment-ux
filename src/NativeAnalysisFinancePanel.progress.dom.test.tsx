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
let root:Root,container:HTMLDivElement,clock:number
const run='66666666-6666-4666-8666-666666666666',reference=parseStagedReference(fixture.reference)
const request:StagedRequest={id:fixture.request_id,q:fixture.query as NativeDemandQuery,finance:'STAGED'}
const running=(done=0,total:number|null=null)=>{
 const f=structuredClone(fixture)as any
 Object.assign(f,{state:'RUNNING',result:null})
 Object.assign(f.capture,{state:'RUNNING',units_done:done,units_total:total,report_read_at:null,readiness:null})
 return f
}
const wire=(f:any)=>({data:stagedJobFixture(request.id,'DONE',{run_id:run,reference:f.reference,finance_capture:f}),error:null})
async function render(get:(id:string)=>Promise<any>,allowed=true){
 await act(async()=>{root.render(<NativeAnalysisFinancePanel request={{...request,q:{...request.q}}} reference={{...reference}} runId={run} allowed={allowed} get={get}/>);await vi.advanceTimersByTimeAsync(0)})
}
async function advance(ms:number){
 for(let passed=0;passed<ms;){const step=Math.min(5000,ms-passed);clock+=step;passed+=step;await act(async()=>{await vi.advanceTimersByTimeAsync(step)})}
}
beforeEach(()=>{
 clock=0;vi.useFakeTimers({toFake:['setTimeout','clearTimeout']});vi.spyOn(performance,'now').mockImplementation(()=>clock)
 ;(globalThis as any).IS_REACT_ACT_ENVIRONMENT=true
 container=document.createElement('div');document.body.append(container);root=createRoot(container)
})
afterEach(async()=>{await act(async()=>root.unmount());container.remove();vi.useRealTimers();vi.restoreAllMocks()})
it('bounds an unchanged unknown-total observation and resumes the same UUID safely',async()=>{
 let reply=running();const get=vi.fn(async(_id:string)=>wire(reply));await render(get)
 await advance(145000);expect(container.textContent).not.toContain('Pemantauan otomatis dijeda')
 await advance(5000);expect(container.textContent).toContain('Pemantauan otomatis dijeda')
 expect(container.textContent).toContain('jumlah langkah total belum diketahui')
 expect(container.textContent).not.toContain('0 dari 0');expect(container.textContent).not.toContain('Rp')
 const stopped=get.mock.calls.length;expect(stopped).toBe(31)
 await advance(60000);expect(get).toHaveBeenCalledTimes(stopped)
 reply=structuredClone(fixture)
 await act(async()=>{container.querySelector('button')!.click();await vi.advanceTimersByTimeAsync(0)})
 expect(container.textContent).toContain('Rp123,45');expect(container.textContent).not.toContain('Pemantauan otomatis dijeda')
 expect(get).toHaveBeenCalledTimes(stopped+1)
 expect(get.mock.calls.every(args=>args[0]===request.id)).toBe(true)
 await advance(150000);expect(get).toHaveBeenCalledTimes(stopped+1)
})
it('renews the observation window only when actual financial progress advances',async()=>{
 let reply=running();const get=vi.fn(async(_id:string)=>wire(reply));await render(get)
 await advance(100000);reply=running(1,7);await advance(5000)
 await advance(145000);expect(container.textContent).not.toContain('Pemantauan otomatis dijeda')
 await advance(5000);expect(container.textContent).toContain('Pemantauan otomatis dijeda')
 expect(container.textContent).toContain('1 dari 7 langkah selesai');expect(container.textContent).not.toContain('Rp')
})
it('does not reset the bound on equivalent rerenders or repeated status replies',async()=>{
 const get=vi.fn(async(_id:string)=>wire(running(2,7)));await render(get);await advance(100000)
 await render(id=>get(id));await advance(50000)
 expect(container.textContent).toContain('Pemantauan otomatis dijeda')
 const stopped=get.mock.calls.length;await advance(60000);expect(get).toHaveBeenCalledTimes(stopped)
})
it('removes pending observation and all figures when permission is revoked',async()=>{
 const get=vi.fn(async(_id:string)=>wire(running()));await render(get);await advance(10000)
 const stopped=get.mock.calls.length;await render(get,false);await advance(300000)
 expect(get).toHaveBeenCalledTimes(stopped);expect(container.textContent).toContain('Akun saat ini belum boleh')
 expect(container.textContent).not.toContain('Rp');expect(container.textContent).not.toContain('Pemantauan otomatis dijeda')
})
