// @vitest-environment jsdom
import {act} from 'react'
import {createRoot,type Root} from 'react-dom/client'
import {beforeEach,afterEach,it,expect,vi} from 'vitest'
import NativeDemandHistoryPanel from './NativeDemandHistoryPanel'
import {readStagedRequest} from './nativeStagedJob'
import running from '../tests/fixtures/initialAnalysisRunningActual.json'
import ready from '../tests/fixtures/initialAnalysisReadyActual.json'
import {profileWire} from '../tests/fixtures/nativePlanningProfile'
import {recoveryIdentity} from '../tests/fixtures/productionRecovery'
const state=vi.hoisted(()=>({auth:null as unknown}))
const client=vi.hoisted(()=>({rpc:vi.fn()}))
vi.mock('./auth/AuthProvider',()=>({useAuth:()=>state.auth}));vi.mock('./lib/supabase',()=>({getUatSupabaseClient:()=>client}))
let root:Root,container:HTMLDivElement
beforeEach(()=>{Object.assign(globalThis,{IS_REACT_ACT_ENVIRONMENT:true});localStorage.clear();client.rpc.mockReset();const a=structuredClone(recoveryIdentity)
 Object.assign(a.runtime,{mode:'DISPOSABLE_TEST',projectRef:'cp6-disposable'});Object.assign(a.identity.profile,{id:running.actor,authUserId:running.actor,rowVersion:'1',roleRowVersion:'1'})
 a.identity.permissions.push('master.product.view','master.product.manage','warehouse.stock.view','sales.invoice.view');state.auth=a
 container=document.createElement('div');document.body.append(container);root=createRoot(container)})
afterEach(async()=>{await act(async()=>root.unmount());container.remove();localStorage.clear();vi.restoreAllMocks()})
async function render(){await act(async()=>root.render(<NativeDemandHistoryPanel/>))}
async function click(name:string){const b=[...container.querySelectorAll('button')].find(b=>b.textContent===name);expect(b).toBeTruthy();await act(async()=>b!.click())}
it('opens the actual existing staged driver with the server UUID, without a second analysis request',async()=>{
 client.rpc.mockImplementation(async(name:string,args:{p_query?:{initial_auto?:string};p_request?:string})=>{
  if(name==='erp_cp7_request_staged_analysis_v1'&&args.p_query?.initial_auto)return{data:running,error:null}
  if(name==='erp_cp7_get_staged_analysis_v1')return{data:running.job,error:null}
  if(name==='erp_cp7_step_staged_analysis_v1')return{data:{...running.job,worker_active:true},error:null}
  throw Error('Unexpected RPC '+name)
 })
 await render();await click('Buka analisis awal yang berjalan')
 const held=readStagedRequest('analysis:cp6-disposable:'+running.actor).pending
 expect(held).toEqual({id:running.job.request_id,q:running.job_query,finance:'DEFERRED'})
 expect(client.rpc.mock.calls).toContainEqual(['erp_cp7_get_staged_analysis_v1',{p_request:running.job.request_id}])
 expect(client.rpc.mock.calls.filter(([name])=>name==='erp_cp7_request_staged_analysis_v1')).toHaveLength(1)
 expect(container.textContent).toContain('Analisis bertahap')
 await click('Buka analisis awal yang berjalan')
 expect(client.rpc.mock.calls.filter(([name])=>name==='erp_cp7_get_staged_analysis_v1')).toHaveLength(2)
 expect(client.rpc.mock.calls.filter(([name])=>name==='erp_cp7_request_staged_analysis_v1')).toHaveLength(1)
})
it('opens the existing real planning-profile form for an unready product',async()=>{
 const p=ready.readiness.candidates[0],wire=profileWire(false)
 Object.assign(wire.rows[0],{root_id:p.root_id,product_version_id:p.product_id,size_id:p.size_id,sku:p.sku,product_name:p.product_name})
 const missing={...ready,state:'NOT_READY',readiness:{...ready.readiness,ready:false,eligible_targets:0,reasons:['PLANNING_PROFILE_INCOMPLETE'],candidates:[{...p,profile_ready:false}]}}
 client.rpc.mockImplementation(async(name:string)=>{
  if(name==='erp_cp7_request_staged_analysis_v1')return{data:missing,error:null}
  if(name==='erp_cp7_get_planning_profiles_v1')return{data:wire,error:null}
  throw Error('Unexpected RPC '+name)
 })
 await render();await click('Lengkapi target LOCAL-INITIAL')
 expect(client.rpc.mock.calls).toContainEqual(['erp_cp7_get_planning_profiles_v1',{p_roots:[p.root_id]}])
 expect(container.querySelector('[aria-label="Aturan dan target produksi"]')).toBeTruthy()
 expect(container.querySelector('[aria-label="Waktu proses pilihan (hari kalender)"]')).toBeTruthy()
 expect(container.textContent).toContain('Simpan aturan target')
 expect(client.rpc.mock.calls.some(([,args])=>args.p_query?.initial_auto==='ENSURE')).toBe(false)
})
