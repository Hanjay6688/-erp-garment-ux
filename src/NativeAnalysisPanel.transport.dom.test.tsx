// @vitest-environment jsdom
import {act} from 'react'
import {createRoot,type Root} from 'react-dom/client'
import {beforeEach,afterEach,it,expect,vi} from 'vitest'
import NativeAnalysisPanel from './NativeAnalysisPanel'
import {recoveryIdentity} from '../tests/fixtures/productionRecovery'
import fixture from '../tests/fixtures/nativeAnalysisStandin.json'
import {transport,job} from '../tests/fixtures/nativeAnalysisTransport'
import {readAnalysisJobRequest,persistAnalysisJobRequest} from './nativeAnalysisTransport'
import {readNativeDemandRequest} from './nativeDemandHistory'
import type {NativeDemandQuery} from './nativeDemandHistory'
const state=vi.hoisted(()=>({auth:null as unknown}))
const client=vi.hoisted(()=>({rpc:vi.fn()}))
vi.mock('./auth/AuthProvider',()=>({useAuth:()=>state.auth}));vi.mock('./lib/supabase',()=>({getUatSupabaseClient:()=>client}))
let root:Root,container:HTMLDivElement
const q=fixture.query as NativeDemandQuery,scope='analysis:cp6-disposable:actor-1'
// The complete serve-shaped Original without its live source state.
function original(requestId:string){const{source_state:_s,...rest}={...structuredClone(fixture),request_id:requestId};return rest as Record<string,unknown>}
type Args={p_request?:string;p_run?:string;p_index?:number;p_access?:string;p_query?:unknown}
function server(requestId:()=>string,jobs:(name:string,args:Args)=>unknown){
 return async(name:string,args:Args)=>{
  if(name==='erp_cp7_read_analysis_manifest_v1'){expect(args).toEqual({p_run:fixture.run_id});return{data:(await transport(original(requestId()))).manifest,error:null}}
  if(name==='erp_cp7_read_analysis_segment_v1'){expect(args.p_access).toBe('a'.repeat(64));return{data:(await transport(original(requestId()))).segment(args.p_index!),error:null}}
  return{data:await jobs(name,args),error:null}
 }
}
beforeEach(()=>{Object.assign(globalThis,{IS_REACT_ACT_ENVIRONMENT:true});client.rpc.mockReset();localStorage.clear();const a=structuredClone(recoveryIdentity);Object.assign(a.runtime,{mode:'DISPOSABLE_TEST',projectRef:'cp6-disposable'});Object.assign(a.identity.profile,{authUserId:fixture.analysis.scope.actor_scope_id});a.identity.permissions.push('master.product.view','production.wip.view','warehouse.stock.view','sales.invoice.view');state.auth=a;container=document.createElement('div');document.body.append(container);root=createRoot(container)})
afterEach(async()=>{await act(async()=>root.unmount());container.remove();localStorage.clear();vi.useRealTimers();vi.restoreAllMocks()})
async function render(){await act(async()=>root.render(<NativeAnalysisPanel query={q} onSourceReadStart={vi.fn()} onSourceReadEnd={vi.fn()} onClose={vi.fn()}/>))}
async function click(text:string){const b=[...container.querySelectorAll('button')].find(b=>b.textContent===text)!;expect(b).toBeTruthy();await act(async()=>b.click())}
const names=()=>client.rpc.mock.calls.map(c=>c[0])
// SHA256 digests finish outside React's microtask queue; drain them explicitly.
const macrotask=()=>new Promise<void>(r=>(globalThis as unknown as {setImmediate:(f:()=>void)=>void}).setImmediate(r))
// Waits on the visible outcome, never on a fixed delay; bounded so a missing outcome fails.
async function until(done:()=>boolean){for(let i=0;i<2000&&!done();i++)await act(async()=>{await macrotask()});expect(done()).toBe(true)}
const result=()=>Boolean(container.querySelector('.native-analysis-result')),alerted=()=>Boolean(container.querySelector('[role="alert"]'))
const statusText=()=>[...container.querySelectorAll('[role="status"]')].map(e=>e.textContent).join(' | ')

it('reads an Original above the single-body bound as the verified segments of the same run and UUID',async()=>{
 let id=''
 client.rpc.mockImplementation(server(()=>id,(name,args)=>{
  if(name==='erp_cp7_capture_analysis_v1'){id=args.p_request!;return{...structuredClone(fixture),request_id:id,analysis:{oversized:'x'.repeat(8000001)}}}
  if(name==='erp_cp7_request_analysis_job_v1'){expect(args).toEqual({p_query:q,p_request:id});return job(id,q,'DONE',fixture.run_id)}
  throw Error('unexpected '+name)}))
 await render();await click('Ambil analisis ERP terbaru');await until(result)
 expect(names()).toEqual(['erp_cp7_capture_analysis_v1','erp_cp7_request_analysis_job_v1','erp_cp7_read_analysis_manifest_v1','erp_cp7_read_analysis_segment_v1'])
 expect(container.querySelector('.native-analysis-result')).toBeTruthy();expect(readNativeDemandRequest(scope).pending).toBeNull()
 expect(container.querySelector('[role="alert"]')).toBeNull()
})

it('runs a background calculation once, shows when it started, then displays the complete Original and clears the request',async()=>{
 let id='',finish:(v:unknown)=>void=()=>{}
 client.rpc.mockImplementation(server(()=>id,(name,args)=>{
  if(name==='erp_cp7_request_analysis_job_v1'){id=args.p_request!;expect(readAnalysisJobRequest(scope).pending).toEqual({id,q});return job(id,q,'WAITING')}
  if(name==='erp_cp7_run_analysis_job_v1')return new Promise(r=>{finish=r})
  throw Error('unexpected '+name)}))
 await render();await click('Hitung di latar belakang')
 expect(statusText()).toMatch(/Sedang dihitung sejak jam 19[.:]00[.:]00 WIB/)
 expect([...container.querySelectorAll('button')].find(b=>b.textContent==='Ambil analisis ERP terbaru')!.hasAttribute('disabled')).toBe(true)
 await act(async()=>{finish(job(id,q,'DONE',fixture.run_id))});await until(result)
 expect(names()).toEqual(['erp_cp7_request_analysis_job_v1','erp_cp7_run_analysis_job_v1','erp_cp7_read_analysis_manifest_v1','erp_cp7_read_analysis_segment_v1'])
 expect(container.querySelector('.native-analysis-result')).toBeTruthy();expect(readAnalysisJobRequest(scope).pending).toBeNull()
})

it('keeps the same UUID after a stopped calculation and continues it on request without inventing a result',async()=>{
 let id='',attempt=0
 client.rpc.mockImplementation(server(()=>id,(name,args)=>{
  if(name==='erp_cp7_request_analysis_job_v1'){if(!id)id=args.p_request!;expect(args.p_request).toBe(id);attempt++;return job(id,q,'WAITING',null,{attempts:attempt})}
  if(name==='erp_cp7_run_analysis_job_v1')return attempt===1?job(id,q,'FAILED'):job(id,q,'DONE',fixture.run_id,{attempts:2})
  throw Error('unexpected '+name)}))
 await render();await click('Hitung di latar belakang');await until(alerted)
 expect(container.querySelector('[role="alert"]')!.textContent).toContain('dihentikan sebelum selesai');expect(container.querySelector('.native-analysis-result')).toBeNull()
 expect(readAnalysisJobRequest(scope).pending?.id).toBe(id)
 await click('Lanjutkan perhitungan yang sama');await until(result)
 expect(names().filter(n=>n==='erp_cp7_run_analysis_job_v1')).toHaveLength(2);expect(container.querySelector('.native-analysis-result')).toBeTruthy()
 expect(readAnalysisJobRequest(scope).pending).toBeNull()
})

it('after a reload reads the server state, waits while a worker holds it and then shows the result without starting another run',async()=>{
 vi.useFakeTimers({toFake:['setTimeout']})
 const id='44444444-4444-4444-8444-444444444444';persistAnalysisJobRequest(scope,{id,q});let reads=0
 client.rpc.mockImplementation(server(()=>id,(name,args)=>{
  if(name==='erp_cp7_get_analysis_job_v1'){expect(args).toEqual({p_request:id});return ++reads<3?job(id,q,'RUNNING'):job(id,q,'DONE',fixture.run_id)}
  throw Error('unexpected '+name)}))
 await render()
 expect(statusText()).toMatch(/Sedang dihitung sejak jam 19[.:]00[.:]00 WIB/)
 await act(async()=>{await vi.advanceTimersByTimeAsync(2000)});await act(async()=>{await vi.advanceTimersByTimeAsync(2000)});await until(result)
 expect(names()).toEqual(['erp_cp7_get_analysis_job_v1','erp_cp7_get_analysis_job_v1','erp_cp7_get_analysis_job_v1','erp_cp7_read_analysis_manifest_v1','erp_cp7_read_analysis_segment_v1'])
 expect(container.querySelector('.native-analysis-result')).toBeTruthy();expect(readAnalysisJobRequest(scope).pending).toBeNull()
})

it('after a reload states a calculation that no worker holds and offers only the same UUID',async()=>{
 const id='55555555-5555-4555-8555-555555555555';persistAnalysisJobRequest(scope,{id,q})
 client.rpc.mockImplementation(server(()=>id,(name)=>{if(name==='erp_cp7_get_analysis_job_v1')return job(id,q,'WAITING');throw Error('unexpected '+name)}))
 await render()
 expect(statusText()).toContain('belum berjalan atau terhenti sebelum selesai');expect(names()).toEqual(['erp_cp7_get_analysis_job_v1'])
 expect([...container.querySelectorAll('button')].find(b=>b.textContent==='Hitung di latar belakang')!.hasAttribute('disabled')).toBe(true)
 expect(container.querySelector('.native-analysis-result')).toBeNull()
})

it('states the WIB start clock while an ordinary capture is still computing after three seconds',async()=>{
 vi.useFakeTimers({toFake:['setTimeout','Date']});vi.setSystemTime(new Date('2026-10-06T12:00:00.000Z'))
 let id='',finish:(v:unknown)=>void=()=>{}
 client.rpc.mockImplementation(async(name:string,args:Args)=>{if(name!=='erp_cp7_capture_analysis_v1')throw Error('unexpected '+name);id=args.p_request!;return new Promise(r=>{finish=r})})
 await render();await click('Ambil analisis ERP terbaru')
 expect(statusText()).toContain('Memeriksa sumber ERP');await act(async()=>{await vi.advanceTimersByTimeAsync(3000)})
 expect(statusText()).toMatch(/Sedang dihitung sejak jam 19[.:]00[.:]00 WIB/)
 await act(async()=>{finish({data:{...structuredClone(fixture),request_id:id},error:null})});await until(result)
 expect(container.querySelector('.native-analysis-result')).toBeTruthy();expect(statusText()).not.toContain('Sedang dihitung')
})
