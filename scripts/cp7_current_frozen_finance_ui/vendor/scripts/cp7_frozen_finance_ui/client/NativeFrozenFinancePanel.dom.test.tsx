// @vitest-environment jsdom
import {act} from 'react'
import {createRoot,type Root} from 'react-dom/client'
import {beforeEach,afterEach,it,expect,vi} from 'vitest'
import NativeFrozenFinancePanel from './NativeFrozenFinancePanel'
import {recoveryIdentity} from '../../../tests/fixtures/productionRecovery'
import {stagedRun} from '../../../tests/fixtures/nativeAnalysisPages'
import {frozenFinanceFixture} from '../../../tests/fixtures/frozenAnalysisFinance'
import {readFrozenAnalysisRequest} from '../../cp7_frozen_analysis_facade_v2/client/nativeFrozenAnalysis'
const state=vi.hoisted(()=>({auth:null as any}))
const client=vi.hoisted(()=>({rpc:vi.fn()}))
vi.mock('../../../src/auth/AuthProvider',()=>({useAuth:()=>state.auth}))
vi.mock('../../../src/lib/supabase',()=>({getUatSupabaseClient:()=>client}))
let root:Root,container:HTMLDivElement,f:Awaited<ReturnType<typeof stagedRun>>,phase:'READY'|'RUNNING'|'ACCESS_REVOKED',denied:boolean
const noop=()=>{},tick=()=>new Promise<void>(r=>setTimeout(r,0)),scope='frozen-quantity:cp6-disposable:actor-1'
async function until(done:()=>boolean){const start=Date.now();while(!done()&&Date.now()-start<3000)await act(async()=>{await tick()});expect(done()).toBe(true)}
async function render(){await act(async()=>{root.render(<NativeFrozenFinancePanel query={f.query} onSourceReadStart={noop} onSourceReadEnd={noop} onClose={noop}/>);await tick()})}
async function click(text:string){const b=[...container.querySelectorAll('button')].find(b=>b.textContent===text);expect(b).toBeTruthy();await act(async()=>{b!.click();await tick()})}
async function startFinance(){await render();await until(()=>container.querySelectorAll('[data-quantity-target]').length===2);await act(async()=>{(container.querySelector('input[type=checkbox]')as HTMLInputElement).click();await tick()});await click('Hitung kebutuhan terbaru');await until(()=>Boolean(container.querySelector('[aria-label="Keuangan analisis dari laporan resmi"]')))}
beforeEach(async()=>{
 Object.assign(globalThis,{IS_REACT_ACT_ENVIRONMENT:true});localStorage.clear();client.rpc.mockReset();phase='READY';denied=false
 const tails=new Map<string,Promise<void>>()
 vi.stubGlobal('navigator',{locks:{request:async(name:string,_opts:unknown,fn:()=>unknown)=>{
  const prior=tails.get(name)??Promise.resolve();let release!:()=>void;const held=new Promise<void>(r=>{release=r});tails.set(name,prior.then(()=>held));await prior;try{return await fn()}finally{release()}
 }}})
 f=await stagedRun({targets:2});const auth=structuredClone(recoveryIdentity)
 Object.assign(auth.runtime,{mode:'DISPOSABLE_TEST',projectRef:'cp6-disposable'});Object.assign(auth.identity.profile,{authUserId:f.actor,rowVersion:1,roleRowVersion:1})
 auth.identity.permissions.push('master.product.view','production.wip.view','warehouse.stock.view','sales.invoice.view','finance.reports.view');state.auth=auth
 container=document.createElement('div');document.body.append(container);root=createRoot(container)
 client.rpc.mockImplementation(async(name,args)=>{
  if(name==='erp_cp7_request_bounded_staged_analysis_v2'){
   if(f.pageSet.request_id!==args.p_request)f=await stagedRun({targets:2,requestId:args.p_request})
   return{data:f.job('DONE',args.p_query.finance_mode==='STAGED'?{finance_capture:frozenFinanceFixture(f,phase)}:{}),error:null}
  }
  if(name==='erp_cp7_get_staged_analysis_v1')return denied?{data:null,error:{code:'42501',message:'CP7_ANALYSIS_ACCESS_CHANGED'}}:{data:f.job('DONE',{finance_capture:frozenFinanceFixture(f,phase)}),error:null}
  if(name==='erp_cp7_read_staged_analysis_pages_v1')return{data:f.pageSet,error:null}
  if(name==='erp_cp7_read_staged_analysis_page_v1')return{data:f.page(args.p_index),error:null}
  throw Error('Unexpected frozen finance RPC:'+name)
 })
})
afterEach(async()=>{await act(async()=>root.unmount());container.remove();localStorage.clear();vi.restoreAllMocks();vi.unstubAllGlobals()})
it('shows completed operational rows while the official report is running, then reads money without reloading pages',async()=>{
 phase='RUNNING';await startFinance();await until(()=>container.textContent!.includes('jumlah langkah total belum diketahui'))
 expect(container.querySelectorAll('[data-quantity-target]')).toHaveLength(2);expect(container.textContent).not.toContain('Rp')
 expect(container.textContent).toContain('Keuangan dan HPP menunggu laporan resmi pada bagian terpisah');expect(container.textContent).not.toContain('Keuangan belum tercakup pada analisis ini.')
 const body=f.pageSet.header.body,stored=readFrozenAnalysisRequest(f.actor,scope).pending;expect(stored?.finance).toBe('STAGED')
 const pages=client.rpc.mock.calls.filter(([name])=>name==='erp_cp7_read_staged_analysis_pages_v1').length
 phase='READY';await click('Muat ulang status keuangan');await until(()=>container.textContent!.includes('Rp123,45'))
 expect(f.pageSet.header.body).toBe(body);expect(client.rpc.mock.calls.filter(([name])=>name==='erp_cp7_read_staged_analysis_pages_v1')).toHaveLength(pages)
 expect(readFrozenAnalysisRequest(f.actor,scope).pending).toEqual(stored)
})
it('reopens the original finance choice and UUID after remount even when the current checkbox defaults off',async()=>{
 await startFinance();await until(()=>container.textContent!.includes('Rp123,45'))
 const stored=readFrozenAnalysisRequest(f.actor,scope).pending,calls=client.rpc.mock.calls.length
 await act(async()=>root.unmount());root=createRoot(container);await render();await until(()=>container.textContent!.includes('Rp123,45'))
 const requests=client.rpc.mock.calls.slice(calls).filter(([name])=>name==='erp_cp7_request_bounded_staged_analysis_v2')
 expect(requests.length).toBeGreaterThan(0);expect(requests.every(([,args])=>args.p_request===stored!.id&&args.p_query.finance_mode==='STAGED')).toBe(true)
 expect((container.querySelector('input[type=checkbox]')as HTMLInputElement).checked).toBe(false);expect(readFrozenAnalysisRequest(f.actor,scope).pending).toEqual(stored)
})
it('retires only protected finance facts when report access is revoked and preserves operational rows',async()=>{
 await startFinance();await until(()=>container.textContent!.includes('Rp123,45'));const stored=readFrozenAnalysisRequest(f.actor,scope).pending
 phase='ACCESS_REVOKED';await click('Muat ulang status keuangan');await until(()=>container.textContent!.includes('Akun saat ini belum boleh membaca angka'))
 expect(container.textContent).not.toContain('Rp');expect(container.textContent).not.toContain('5 dari 5');expect(container.querySelectorAll('[data-quantity-target]')).toHaveLength(2)
 expect(readFrozenAnalysisRequest(f.actor,scope).pending).toEqual(stored)
})
it('retires parent quantities after an operational403 and retains the exact original request',async()=>{
 await startFinance();await until(()=>container.textContent!.includes('Rp123,45'));const stored=readFrozenAnalysisRequest(f.actor,scope).pending
 denied=true;await click('Muat ulang status keuangan');await until(()=>container.querySelectorAll('[data-quantity-target]').length===0)
 expect(container.textContent).not.toContain('Rp');expect(readFrozenAnalysisRequest(f.actor,scope).pending).toEqual(stored)
})
it('keeps the finance choice unavailable outside the Owner/Admin boundary',async()=>{
 state.auth.identity.profile.role='OPERATOR';await render();await until(()=>container.querySelectorAll('[data-quantity-target]').length===2)
 expect(container.querySelector('input[type=checkbox]')).toBeNull();expect(container.querySelector('[aria-label="Keuangan analisis dari laporan resmi"]')).toBeNull()
 expect(client.rpc.mock.calls.filter(([name])=>name==='erp_cp7_request_bounded_staged_analysis_v2').every(([,args])=>args.p_query.finance_mode===undefined)).toBe(true)
})
