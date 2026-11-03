// @vitest-environment jsdom
// Explicit counterexample entry only; not part of the default product test glob.
import {act} from 'react'
import {createRoot,type Root} from 'react-dom/client'
import {beforeEach,afterEach,it,expect,vi} from 'vitest'
import Pocket from '../../src/ConnectedPocketFabricPage'
import Import from '../../src/ConnectedInitialImportPage'
import {recoveryIdentity} from '../../tests/fixtures/productionRecovery'
const auth=vi.hoisted(()=>({current:null as unknown}))
const client=vi.hoisted(()=>({rpc:vi.fn()}))
vi.mock('../../src/auth/AuthProvider',()=>({useAuth:()=>auth.current}))
vi.mock('../../src/lib/supabase',()=>({getUatSupabaseClient:()=>client}))
const id='11111111-1111-4111-8111-111111111111',row='22222222-2222-4222-8222-222222222222'
const revision=(n:number)=>n.toString(16).padStart(64,'0')
const period={id:row,period_start:'2026-09-01',period_end:'2026-09-20',status:'ACTIVE',reason:'Fixture only',quantity:'10',original_amount:'11.25',current_amount:'11.25',per_piece:'1.125000',revision:revision(2)}
const pocket={rolls:[{id,material_id:id,location_id:id,roll_number:'KKT-PRIVATE',material_name:'Kain fixture',unit_code:'YD',location_name:'Gudang fixture',qty:'20.000000',revision:revision(1)}],roll_count:1,materials:[],history:[],periods:[period],period_count:2,period_offset:0,period_next_offset:1}
const preview={period_start:'2026-09-01',period_end:'2026-09-20',amount:'11.25',quantity:'10',per_piece:'1.125000',source_count:1,blocked:false,can_post:true,revision:revision(2)}
const importData=(selected:boolean)=>({recent:[{id,batch_code:'AWAL-PRIVATE',status:'DRAFT'}],batch:!selected?null:{id,code:'AWAL-PRIVATE',status:'DRAFT',cutover_at:'2026-09-20T00:00:00+07:00',revision:revision(1),rows:[{id:row,entity:'MATERIAL',source_row_no:2,payload:{material_sku:'KAIN-PRIVATE',material_name:'Kain fixture',material_type:'FABRIC',unit_code:'YD',accessory_category_code:'',is_active:'true'},validation_status:'VALID',errors:[],applied:false}],cash_advances:[],advance_payrolls:[],prepayments:[],prepayment_cash_accounts:[],production_sources:[]}})
const cutoverCurrent={version:1,cutover_date:'2026-09-01',previous_date:null,reason:'Fixture only',set_at:'2026-09-01T00:00:00+07:00',set_by:'Fixture'}
const cutover={contract_version:'cp7.cutover-workspace.v1',today:'2026-11-03',can_set:false,version:1,current:cutoverCurrent,history:[cutoverCurrent],earliest_operational:null,earliest_import:{date:'2026-09-20',batch_code:'AWAL-PRIVATE'},latest_allowed:'2026-09-20',business_DML:false}
let root:Root,host:HTMLDivElement,denied:number|null
beforeEach(()=>{
 Object.assign(globalThis,{IS_REACT_ACT_ENVIRONMENT:true});localStorage.clear();denied=null;client.rpc.mockReset()
 Object.defineProperty(navigator,'locks',{configurable:true,value:{request:async(_name:string,_options:unknown,fn:(lock:unknown)=>Promise<unknown>)=>fn({})}})
 const identity=structuredClone(recoveryIdentity);identity.identity.permissions.push('warehouse.stock.adjust','finance.hpp.manage');auth.current=identity
 host=document.createElement('div');document.body.append(host);root=createRoot(host)
 client.rpc.mockImplementation(async(name:string,args:Record<string,unknown>)=>{
  if(name==='erp_cp7_get_cutover_v1')return {data:cutover,error:null}
  if(denied!==null)return {data:null,error:{status:denied,code:denied===401?'PGRST301':'42501',message:'Explicit fixture source refusal'}}
  if(name==='erp_get_pocket_fabric_workspace_v1')return {data:structuredClone(pocket),error:null}
  if(name==='erp_preview_pocket_fabric_period_v1')return {data:structuredClone(preview),error:null}
  if(name==='erp_get_initial_import_workspace_v1')return {data:importData(Boolean(args.p_batch_id)),error:null}
  throw Error('UNDECLARED_RPC:'+name)
 })
})
afterEach(async()=>{await act(async()=>root.unmount());host.remove();localStorage.clear();Reflect.deleteProperty(navigator,'locks');vi.restoreAllMocks()})
const flush=async()=>act(async()=>{await new Promise(resolve=>setTimeout(resolve,0))})
async function change(label:string,value:string){
 const input=host.querySelector<HTMLInputElement|HTMLSelectElement>(`[aria-label="${label}"]`);expect(input).not.toBeNull()
 await act(async()=>{Object.getOwnPropertyDescriptor(input instanceof HTMLSelectElement?HTMLSelectElement.prototype:HTMLInputElement.prototype,'value')!.set!.call(input,value);input!.dispatchEvent(new Event('input',{bubbles:true}));input!.dispatchEvent(new Event('change',{bubbles:true}))});await flush()
}
async function click(label:string){const b=[...host.querySelectorAll('button')].find(b=>b.textContent?.trim()===label);expect(b,'visible action '+label).toBeDefined();expect(b!.disabled).toBe(false);await act(async()=>b!.click());await flush()}
function providerUnchanged(){expect((auth.current as typeof recoveryIdentity).identity.status).toBe('AUTHORIZED');expect(client.rpc.mock.calls.filter(([name])=>String(name).startsWith('erp_save_'))).toHaveLength(0)}
for(const status of [401,403])for(const route of ['workspace','period-page','period-preview']){
 it(`pocket ${route} ${status}: hide prior source facts while provider remains AUTHORIZED`,async()=>{
  await act(async()=>root.render(<Pocket/>));await flush()
  expect(host.textContent).toContain('KKT-PRIVATE');expect(host.textContent).toContain('11,25')
  if(route==='period-preview'){await change('Awal periode kain kantong','2026-09-01');await change('Akhir periode kain kantong','2026-09-20')}
  denied=status
  await click(route==='workspace'?'Muat ulang':route==='period-page'?'Muat periode berikutnya':'Lihat pembagian')
  expect(host.textContent).toContain(status===401?'Sesi berakhir':'Akun tidak memiliki izin')
  providerUnchanged()
  console.log(JSON.stringify({fixture:'pocket',route,status,provider:'AUTHORIZED',old_stock_visible:host.textContent?.includes('KKT-PRIVATE'),old_HPP_visible:host.textContent?.includes('11,25'),actual_Auth:0,actual_SQL:0}))
  expect(host.textContent).not.toContain('KKT-PRIVATE')
  expect(host.textContent).not.toContain('11,25')
 })
}
for(const status of [401,403])it(`import workspace ${status}: retire batch facts without relying on provider change`,async()=>{
 await act(async()=>root.render(<Import/>));await flush();await change('Batch impor',id)
 expect(host.querySelector<HTMLInputElement>('[aria-label="Kode bahan, baris 2"]')?.value).toBe('KAIN-PRIVATE')
 denied=status;await click('Muat ulang')
 expect(host.textContent).toContain(status===401?'Sesi berakhir':'Akun tidak memiliki izin');providerUnchanged()
 expect(host.querySelector('[aria-label="Kode bahan, baris 2"]')).toBeNull()
 expect(host.querySelector('[aria-label="Batch impor"]')?.textContent).not.toContain('AWAL-PRIVATE')
})
for(const status of [401,403]){
 it(`extra: late ${status} cannot erase a newer successful pocket read`,async()=>{
  await act(async()=>root.render(<Pocket/>));await flush()
  let release:(value:unknown)=>void=()=>{throw Error('MISSING_DEFERRED_READ')},reads=0
  client.rpc.mockImplementation(async(name:string)=>{
   expect(name).toBe('erp_get_pocket_fabric_workspace_v1');reads++
   if(reads===1)return new Promise(resolve=>{release=resolve})
   const data=structuredClone(pocket);data.rolls[0].roll_number='KKT-FRESH';return {data,error:null}
  })
  await click('Muat ulang');await click('Muat ulang');expect(host.textContent).toContain('KKT-FRESH')
  await act(async()=>release({data:null,error:{status,code:status===401?'PGRST301':'42501'}}));await flush()
  expect(host.textContent).toContain('KKT-FRESH');expect(host.textContent).not.toContain('Sesi berakhir');expect(host.textContent).not.toContain('Akun tidak memiliki izin');providerUnchanged()
 })
 it(`extra: source ${status} also retires an already-open allocation cancellation`,async()=>{
  await act(async()=>root.render(<Pocket/>));await flush();await click('Batalkan alokasi 2026-09-01')
  const confirms=()=>[...host.querySelectorAll('button')].filter(b=>b.textContent?.trim()==='Sahkan pembatalan alokasi')
  expect(confirms()).toHaveLength(1);denied=status;await click('Muat ulang')
  expect(confirms()).toHaveLength(0);expect(host.textContent).not.toContain('KKT-PRIVATE');expect(host.textContent).not.toContain('11,25');providerUnchanged()
 })
}
