// @vitest-environment jsdom
// Controlled client wire; actual Native/Auth/races are qualified separately.
import {act} from 'react'
import {createRoot,type Root} from 'react-dom/client'
import {afterEach,beforeEach,expect,it,vi} from 'vitest'
import MaterialReorderPanel from './MaterialReorderPanel'
import {readMaterialRequests,materialRequestPrefix} from './materialReorderRequests'
import {materialRow,materialWire,type MaterialWireRow} from '../tests/fixtures/materialReorder'
import {recoveryIdentity} from '../tests/fixtures/productionRecovery'
import type {MaterialPayload,MaterialQuery} from './materialReorderContract'
const auth=vi.hoisted(()=>({current:null as unknown}))
const client=vi.hoisted(()=>({rpc:vi.fn()}))
vi.mock('./auth/AuthProvider',()=>({useAuth:()=>auth.current}))
vi.mock('./lib/supabase',()=>({getUatSupabaseClient:()=>client}))
let root:Root,container:HTMLDivElement
let row:MaterialWireRow,lose:boolean,deny:boolean
const calls:{p_payload:MaterialPayload;p_request:string}[]=[]
const ledger=new Map<string,{payload:MaterialPayload;revision:number}>()
const scope='cp6-disposable:'+recoveryIdentity.identity.profile.id
beforeEach(()=>{
 Object.assign(globalThis,{IS_REACT_ACT_ENVIRONMENT:true});localStorage.clear();client.rpc.mockReset();calls.length=0;ledger.clear();lose=false;deny=false
 const a=structuredClone(recoveryIdentity);Object.assign(a.runtime,{mode:'DISPOSABLE_TEST',projectRef:'cp6-disposable'})
 a.identity.permissions.push('warehouse.material.view','master.fabric.view');auth.current=a
 row={...materialRow(1),legacy_minimum_qty:'500.0000',fabric_rule:null,manual_point:'500',manual_source:'FABRIC_MINIMUM',point:'500',basis:'MANUAL'}
 client.rpc.mockImplementation(async(name:string,args:{p_query?:MaterialQuery;p_payload:MaterialPayload;p_request:string})=>{
  if(deny)return{data:null,error:{code:'42501',message:'CP7_FORMULA_ACCESS_DENIED'}}
  if(name==='erp_cp7_get_material_reorder_v1')return{data:materialWire([row],args.p_query,{contract_version:'cp7.material-reorder.v2'}),error:null}
  if(name!=='erp_cp7_save_material_reorder_v1')throw Error('Unexpected test RPC')
  calls.push(structuredClone(args))
  expect(readMaterialRequests(scope,'FABRIC').pending.some(x=>x.id===args.p_request&&JSON.stringify(x.payload)===JSON.stringify(args.p_payload))).toBe(true)
  const old=ledger.get(args.p_request)
  if(old){expect(args.p_payload).toEqual(old.payload);return{data:{replay:true,material_id:row.material_id,revision:old.revision},error:null}}
  expect(args.p_payload.expected_revision).toBe(row.setting_revision)
  const revision=Number(row.setting_revision)+1
  Object.assign(row,{setting_revision:revision,lead_days:args.p_payload.lead_days===null?null:Number(args.p_payload.lead_days),
   fabric_rule:args.p_payload.fabric_rule??row.fabric_rule,manual_point:args.p_payload.fabric_rule==='FORMULA'?null:'500',
   manual_source:args.p_payload.fabric_rule==='FORMULA'?null:'FABRIC_MINIMUM',point:args.p_payload.fabric_rule==='FORMULA'?'63.34':'500',
   basis:args.p_payload.fabric_rule==='FORMULA'?'FORMULA':'MANUAL'})
  ledger.set(args.p_request,{payload:structuredClone(args.p_payload),revision})
  if(lose){lose=false;return{data:null,error:Error('reply lost')}}
  return{data:{replay:false,material_id:row.material_id,revision,evaluation:{...row}},error:null}
 })
 container=document.createElement('div');document.body.append(container);root=createRoot(container)
})
afterEach(async()=>{await act(async()=>root.unmount());container.remove();vi.restoreAllMocks()})
async function mount(){await act(async()=>root.render(<MaterialReorderPanel materialType="FABRIC"/>))}
async function remount(){await act(async()=>root.unmount());root=createRoot(container);await mount()}
async function click(name:string){const b=[...container.querySelectorAll('button')].find(x=>x.textContent===name||x.getAttribute('aria-label')===name);expect(b).toBeTruthy();await act(async()=>b!.click())}
async function fill(label:string,value:string){
 const e=container.querySelector<HTMLInputElement|HTMLSelectElement>('[aria-label="'+label+'"]');expect(e).toBeTruthy()
 await act(async()=>{Object.getOwnPropertyDescriptor(e instanceof HTMLSelectElement?HTMLSelectElement.prototype:HTMLInputElement.prototype,'value')!.set!.call(e,value);e!.dispatchEvent(new Event(e instanceof HTMLSelectElement?'change':'input',{bubbles:true}))})
}
async function choose(){await click('Atur lama kirim');await fill('Aturan kain yang akan dipakai','FORMULA');await fill('Alasan perubahan bahan','Aturan rumus yang saya periksa')}
it('chooses one rule with a read-only exact reference and recovers its original UUID after remount',async()=>{
 lose=true;await mount()
 expect(container.querySelector('[data-cmr="legacy"]')?.textContent).toContain('500 YD')
 await choose();expect(container.querySelector('[aria-label*="Referensi"]')).toBeNull();await click('Simpan')
 const original=structuredClone(calls[0]);expect(original.p_payload).toMatchObject({fabric_rule:'FORMULA',expected_legacy_minimum_qty:'500.0000',manual_point:null})
 expect(readMaterialRequests(scope,'FABRIC').pending).toHaveLength(1);expect(row.setting_revision).toBe(2)
 await remount();await click('Atur lama kirim');await fill('Aturan kain yang akan dipakai','LEGACY_MINIMUM');await fill('Alasan perubahan bahan','Pilihan lain belum dikirim');await click('Simpan')
 expect(calls).toHaveLength(1);expect(container.textContent).toContain('hasilnya belum jelas')
 await click('Ulangi simpan bahan yang sama: Katun 1')
 expect(calls[1]).toEqual(original);expect(row.setting_revision).toBe(2);expect(readMaterialRequests(scope,'FABRIC').pending).toHaveLength(0)
 expect((container.querySelector('[aria-label="Alasan perubahan bahan"]') as HTMLInputElement).value).toBe('Pilihan lain belum dikirim')
 expect((container.querySelector('[aria-label="Aturan kain yang akan dipakai"]') as HTMLSelectElement).value).toBe('LEGACY_MINIMUM')
 expect(container.querySelector('[data-cmr="basis"]')?.textContent).toBe('Rumus yang dipilih')
})
it('keeps a committed unanswered request through current403 and retires displayed facts until access is restored',async()=>{
 lose=true;await mount();await choose();await click('Simpan');const original=structuredClone(calls[0]);await remount();deny=true
 await click('Ulangi simpan bahan yang sama: Katun 1')
 expect(readMaterialRequests(scope,'FABRIC').pending).toHaveLength(1);expect(container.querySelector('article.cfr-row')).toBeNull()
 expect(container.textContent).not.toContain('Katun 1');expect(container.textContent).toContain('sampai akses akun dipulihkan')
 deny=false;await click('Muat ulang titik pesan ulang kain');await click('Ulangi simpan bahan yang sama: Katun 1')
 expect(calls[1]).toEqual(original);expect(readMaterialRequests(scope,'FABRIC').pending).toHaveLength(0);expect(row.setting_revision).toBe(2)
})
it('preserves corrupt recovery data and refuses a replacement save',async()=>{
 const key=materialRequestPrefix(scope,'FABRIC')+'11111111-1111-4111-8111-111111111111';localStorage.setItem(key,'broken')
 await mount();await choose();await click('Simpan')
 expect(calls).toHaveLength(0);expect(localStorage.getItem(key)).toBe('broken');expect(container.textContent).toContain('Catatan penyimpanan bahan belum bisa dibaca')
})
it('does not send a write when its durable intent cannot be saved first',async()=>{
 await mount();await choose();vi.spyOn(Storage.prototype,'setItem').mockImplementation(()=>{throw new DOMException('full','QuotaExceededError')})
 await click('Simpan');expect(calls).toHaveLength(0);expect(container.textContent).toContain('Data belum dikirim ke server')
})
