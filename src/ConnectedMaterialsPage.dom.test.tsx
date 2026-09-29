// @vitest-environment jsdom
import { act } from 'react'
import { createRoot, type Root } from 'react-dom/client'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import ConnectedMaterialsPage from './ConnectedMaterialsPage'
import { parseMaterials, parseMaterialLedger, parseMaterialTransfers } from './materialContract'
import { readProductionRecovery } from './productionRecovery'
import { recoveryIdentity } from '../tests/fixtures/productionRecovery'
const state=vi.hoisted(()=>({auth:null as unknown}))
const client=vi.hoisted(()=>({rpc:vi.fn()}))
vi.mock('./auth/AuthProvider',()=>({useAuth:()=>state.auth}))
vi.mock('./lib/supabase',()=>({getUatSupabaseClient:()=>client}))
const id='11111111-1111-4111-8111-111111111111',doc='22222222-2222-4222-8222-222222222222',to='33333333-3333-4333-8333-333333333333',at='2026-09-29T03:00:00Z'
const caps={transfer:true,reverse_transfer:true},page=(rows:unknown[])=>({rows,total:String(rows.length),offset:0,limit:25,next_offset:null})
function stock(finance=true,posted=false){return {contract_version:'cp7.material-workspace.v1',kind:'LIVE_MATERIAL_LEDGER',read_at:at,quantity_basis:'POSTED_PHYSICAL_LEDGER_CURRENT_KNOWLEDGE',financial_captured:finance,capabilities:caps,totals_by_unit:[{unit_code:'YD',qty:'10.000000',quality:'KNOWN'}],page:page([{material_id:id,material_sku:'DEN-1',material_name:'Denim',material_type:'FABRIC',unit_code:'YD',roll_id:id,roll_number:'ROLL-1',location_id:id,location_name:'Gudang asal',qty:posted?'6.000000':'10.000000',last_movement_at:at,quality:'KNOWN',availability:'ON_HAND',...(finance?{valuation:{state:'KNOWN',unit_cost:'10.000000',value:posted?'60.000000':'100.000000',basis:'CURRENT_MATERIAL_MOVING_AVERAGE'}}:{})}])}}
function transfers(posted=false,detail=false){const row={id:doc,number:'TR-TEST',from_location_id:id,to_location_id:to,from_location_name:'Gudang asal',to_location_name:'Gudang tujuan',physical_at:at,status:posted?'POSTED':'DRAFT',row_version:posted?'9007199254740994':'9007199254740993',notes:null,line_count:'1'};return {contract_version:'cp7.material-transfers.v1',read_at:at,capabilities:caps,page:page([row]),detail:detail?{...row,items:[{id,material_id:id,material_sku:'DEN-1',material_name:'Denim',unit_code:'YD',roll_id:id,roll_number:'ROLL-1',qty:'4.000000',notes:null}]}:null}}
let root:Root,container:HTMLDivElement
beforeEach(()=>{Object.assign(globalThis,{IS_REACT_ACT_ENVIRONMENT:true});localStorage.clear();client.rpc.mockReset();const a=structuredClone(recoveryIdentity);a.identity.permissions.push('warehouse.material.view','warehouse.stock.adjust','finance.hpp.view');state.auth=a;Object.defineProperty(navigator,'locks',{configurable:true,value:{request:async(_n:string,_o:unknown,fn:(l:unknown)=>Promise<unknown>)=>fn({})}});container=document.createElement('div');document.body.append(container);root=createRoot(container)})
afterEach(async()=>{await act(async()=>root.unmount());container.remove();localStorage.clear();Reflect.deleteProperty(navigator,'locks');vi.restoreAllMocks()})
async function flush(){await act(async()=>{await new Promise(r=>setTimeout(r,0))})}
async function mount(){await act(async()=>root.render(<ConnectedMaterialsPage/>));await flush()}
function button(label:string){const x=[...container.querySelectorAll('button')].find(b=>b.textContent===label);if(!x)throw Error('Missing '+label);return x}
async function click(label:string){await act(async()=>button(label).click());await flush()}
const writes=()=>client.rpc.mock.calls.filter(([n])=>n==='erp_cp7_save_materials_v1')
function server(finance=true){const s={posted:false,lose:false,wrong:false,failRead:false,effects:0},cache=new Map<string,unknown>();client.rpc.mockImplementation(async(name:string,args:Record<string,unknown>)=>{
 if(name==='erp_cp7_get_materials_v1')return s.failRead&&s.posted?{data:null,error:{message:'Read unavailable'}}:{data:stock(finance,s.posted),error:null}
 if(name==='erp_cp7_get_material_transfers_v1')return {data:transfers(s.posted,Boolean((args.p_query as Record<string,unknown>).transfer_id)),error:null}
 if(name==='erp_cp7_save_materials_v1'){const key=String(args.p_request);if(!cache.has(key)){s.posted=true;s.effects++;cache.set(key,{contract_version:'cp7.material-outcome.v1',kind:'COMMITTED_OUTCOME',action:args.p_action,request_id:key,transfer_id:doc,status:'POSTED',row_version:'9007199254740994'})}return s.lose?{data:null,error:{status:503,message:'Lost committed reply'}}:{data:s.wrong?{ok:true}:cache.get(key),error:null}}
 throw Error('Unexpected RPC '+name)
});return s}
async function selectTransfer(){await click('Transfer gudang');await act(async()=>{container.querySelector<HTMLButtonElement>('.cproc-receipt')!.click()});await flush()}
describe('material transfer connected boundary',()=>{
 it('opens an accessory ledger with a null roll and offers its ordinary warehouse transfer',async()=>{
  server();const original=client.rpc.getMockImplementation()!
  client.rpc.mockImplementation(async(name:string,args:Record<string,unknown>)=>{
   if(name==='erp_cp7_get_material_ledger_v1')return {data:{contract_version:'cp7.material-ledger.v1',material_id:id,roll_id:null,location_id:id,read_at:at,financial_captured:true,history_basis:'CURRENT_RESTATED_NOT_AS_KNOWN',page:page([])},error:null}
   if(name==='erp_cp7_get_material_locations_v1')return {data:{contract_version:'cp7.material-locations.v1',...page([{id:to,code:'TO',name:'Gudang tujuan'}])},error:null}
   const r=await original(name,args)
   if(name==='erp_cp7_get_materials_v1'){Object.assign(r.data.page.rows[0],{material_type:'ACCESSORY',material_name:'Kancing',unit_code:'PCS',roll_id:null,roll_number:null});r.data.totals_by_unit[0].unit_code='PCS'}
   return r
  });await mount();await click('Mutasi Kancing')
  expect(client.rpc.mock.calls.find(([n])=>n==='erp_cp7_get_material_ledger_v1')?.[1].p_roll).toBeNull()
  expect(container.textContent).not.toContain('Roll belum diketahui');expect(button('Pindahkan Kancing').disabled).toBe(false);await click('Pindahkan Kancing')
  expect(container.querySelector('form')?.textContent).toBeTruthy();expect(container.textContent).toContain('Jumlah (PCS)')
 })
 it('posts the exact reviewed version and reloads stock from the server',async()=>{server();await mount();await selectTransfer();await click('Sahkan perpindahan stok');expect(writes()[0][1].p_expected).toBe('9007199254740993');expect(container.textContent).toContain('Stok sudah dipindahkan');await click('Stok per gudang');expect(container.textContent).toContain('6 YD');expect(readProductionRecovery('disposable:actor-1').pending.MATERIALS).toBeUndefined()})
 it('recovers the same transfer request after lost commit response and remount',async()=>{const s=server();await mount();await selectTransfer();s.lose=true;await click('Sahkan perpindahan stok');const sent=structuredClone(writes()[0][1]);expect(readProductionRecovery('disposable:actor-1').pending.MATERIALS?.id).toBe(sent.p_request);await act(async()=>root.unmount());root=createRoot(container);s.lose=false;await mount();await click('Reconcile transaksi');expect(writes()[1][1]).toEqual(sent);expect(s.effects).toBe(1);expect(container.textContent).toContain('Stok sudah dipindahkan')})
 it('retires stale actions and keeps writers locked when committed reload fails',async()=>{const s=server();await mount();await selectTransfer();const old=button('Sahkan perpindahan stok');s.failRead=true;await click('Sahkan perpindahan stok');expect(container.textContent).toContain('Aksi sudah tersimpan');expect(container.textContent).not.toContain('Sahkan perpindahan stok');await act(async()=>old.click());expect(writes()).toHaveLength(1);s.failRead=false;await click('Muat ulang');expect(container.textContent).toContain('Stok sudah dipindahkan')})
 it('keeps a malformed success uncertain instead of clearing the request',async()=>{const s=server();await mount();await selectTransfer();s.wrong=true;await click('Sahkan perpindahan stok');expect(readProductionRecovery('disposable:actor-1').pending.MATERIALS).toBeTruthy();expect(button('Sahkan perpindahan stok').disabled).toBe(true)})
 it('rejects money in an operational response before rendering',async()=>{const a=state.auth as typeof recoveryIdentity;a.identity.permissions=a.identity.permissions.filter(p=>p!=='finance.hpp.view');server(false);await mount();expect(container.textContent).not.toContain('Rp');expect(()=>parseMaterials(stock(),false)).toThrow();expect(()=>parseMaterials(stock(false),false)).not.toThrow()})
 it('refuses truncated totals/detail and preserves the full server ledger prefix',()=>{const w=stock();expect(()=>parseMaterials({...w,page:{...w.page,total:'2'}},true)).toThrow();const t=transfers(false,true);expect(()=>parseMaterialTransfers({...t,detail:{...t.detail,line_count:'2'}})).toThrow();const l={contract_version:'cp7.material-ledger.v1',material_id:id,roll_id:id,location_id:id,read_at:at,financial_captured:false,history_basis:'CURRENT_RESTATED_NOT_AS_KNOWN',page:{...page([{movement_id:doc,physical_at:at,recorded_at:at,movement_type:'TRANSFER_OUT',qty_signed:'-4.000000',running_qty:'6.000000',source_type:'MATERIAL_TRANSFER',source_id:doc,reversal_of_id:null,note:null}]),total:'2',next_offset:1,limit:1}};expect(parseMaterialLedger(l,false).page.rows[0].running_qty).toBe('6.000000');expect(()=>parseMaterialLedger({...l,history_basis:'AS_KNOWN'},false)).toThrow()})
})
