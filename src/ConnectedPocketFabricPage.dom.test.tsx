// @vitest-environment jsdom
import { act } from 'react'
import { createRoot, type Root } from 'react-dom/client'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import ConnectedPocketFabricPage, { parsePocketWorkspace, parsePocketPreview } from './ConnectedPocketFabricPage'
import { recoveryIdentity } from '../tests/fixtures/productionRecovery'
import { readProductionRecovery } from './productionRecovery'
const auth = vi.hoisted(() => ({ current: null as unknown }))
const client = vi.hoisted(() => ({ rpc: vi.fn() }))
vi.mock('./auth/AuthProvider', () => ({ useAuth: () => auth.current }))
vi.mock('./lib/supabase', () => ({ getUatSupabaseClient: () => client }))
const id = '11111111-1111-4111-8111-111111111111', doc = '22222222-2222-4222-8222-222222222222'
const revision = (n: number) => n.toString(16).padStart(64,'0')
const data = () => ({ rolls:[{ id,material_id:id,location_id:id,roll_number:'KKT-001',material_name:'Kain kantong universal',unit_code:'YD',location_name:'Gudang kain',qty:'20.000000',revision:revision(1) }],roll_count:1,materials:[],history:[] as Record<string,unknown>[],periods:[] as Record<string,unknown>[] })
let root: Root, container: HTMLDivElement
beforeEach(() => {
  Object.assign(globalThis,{IS_REACT_ACT_ENVIRONMENT:true});localStorage.clear();client.rpc.mockReset()
  const a=structuredClone(recoveryIdentity);a.identity.permissions.push('warehouse.stock.adjust');auth.current=a
  Object.defineProperty(navigator,'locks',{configurable:true,value:{request:async (_n:string,_o:unknown,fn:(l:unknown)=>Promise<unknown>)=>fn({})}})
  container=document.createElement('div');document.body.append(container);root=createRoot(container)
})
afterEach(async()=>{await act(async()=>root.unmount());container.remove();localStorage.clear();Reflect.deleteProperty(navigator,'locks');vi.restoreAllMocks()})
async function flush(){await act(async()=>{await new Promise(resolve=>setTimeout(resolve,0))})}
async function change(label:string,value:string){
  const input=container.querySelector<HTMLInputElement|HTMLSelectElement>(`[aria-label="${label}"]`)!
  await act(async()=>{Object.getOwnPropertyDescriptor(input instanceof HTMLSelectElement?HTMLSelectElement.prototype:HTMLInputElement.prototype,'value')!.set!.call(input,value);input.dispatchEvent(new Event('input',{bubbles:true}));input.dispatchEvent(new Event('change',{bubbles:true}))});await flush()
}
function button(label:string){const b=[...container.querySelectorAll('button')].find(b=>b.textContent?.includes(label));if(!b)throw new Error(label+' missing');return b}
async function click(label:string){await act(async()=>button(label).click());await flush()}
async function mount(){await act(async()=>root.render(<ConnectedPocketFabricPage/>));await flush()}
const writes=()=>client.rpc.mock.calls.filter(([name])=>name==='erp_save_pocket_fabric_action_v1')
const periodPreview=()=>({period_start:'2026-09-01',period_end:'2026-09-20',amount:'11.25',quantity:'10',per_piece:'1.125000',source_count:1,blocked:false,can_post:true,revision:revision(8)})
function server(){
  const s={data:data(),preview:periodPreview() as unknown,lose:false,effects:0};const cache=new Map<string,unknown>()
  client.rpc.mockImplementation(async(name:string,args:Record<string,unknown>)=>{
    if(name==='erp_get_pocket_fabric_workspace_v1')return {data:structuredClone(s.data),error:null}
    if(name==='erp_preview_pocket_fabric_period_v1')return {data:structuredClone(s.preview),error:null}
    const p=args.p_payload as Record<string,unknown>,key=String(args.p_client_request_id)
    if(!cache.has(key)){s.effects++;cache.set(key,{request_id:key,action:args.p_action,id:['REVERSE','CANCEL_PERIOD'].includes(String(args.p_action))?p.id:doc,status:({REVERSE:'REVERSED',POST:'POSTED',POST_PERIOD:'ACTIVE',CANCEL_PERIOD:'CANCELLED',REGISTER:'REGISTERED'} as Record<string,string>)[String(args.p_action)]})}
    return s.lose?{data:null,error:{status:503,message:'Lost reply'}}:{data:cache.get(key),error:null}
  });return s
}
async function prepare(){await change('Roll kain kantong',`${id}:${id}`);await change('Tanggal pengurangan','2026-09-21')}

describe('pocket fabric warehouse-only expense flow',()=>{
  it('counts remaining stock, accepts zero and posts only after explicit confirmation without production fields',async()=>{
    server();await mount();await prepare();await change('Jumlah kain kantong','0')
    expect(writes()).toHaveLength(0);expect(container.querySelector('[aria-label="Mandor"]')).toBeNull()
    expect(button('Sahkan pengurangan stok').disabled).toBe(false);await click('Sahkan pengurangan stok')
    expect(writes()[0][1].p_payload).toEqual({roll_id:id,location_id:id,expected_revision:revision(1),mode:'REMAINING',quantity:'0',date:'2026-09-21',reason:'Pemakaian bebas kain kantong'})
    expect((container.querySelector('[aria-label="Jumlah kain kantong"]') as HTMLInputElement).value).toBe('')
  })
  it('preserves exact comma input and rejects excess precision and consumption above stock',async()=>{
    server();await mount();await prepare();await change('Cara mencatat','USED');await change('Jumlah kain kantong','20,000001')
    expect(button('Sahkan pengurangan stok').disabled).toBe(true)
    await change('Jumlah kain kantong','1,0000001');expect(button('Sahkan pengurangan stok').disabled).toBe(true)
    await change('Jumlah kain kantong','7,125001');await click('Sahkan pengurangan stok')
    expect(writes()[0][1].p_payload.quantity).toBe('7,125001');expect(writes()[0][1].p_payload.mode).toBe('USED')
  })
  it('recovers a lost result using the identical UUID and payload after remount',async()=>{
    const s=server();await mount();await prepare();await change('Jumlah kain kantong','15');s.lose=true;await click('Sahkan pengurangan stok')
    const original=structuredClone(writes()[0][1]);expect(readProductionRecovery('disposable:actor-1').pending.POCKET_FABRIC?.id).toBe(original.p_client_request_id)
    await act(async()=>root.unmount());root=createRoot(container);s.lose=false;await mount();await click('Reconcile')
    expect(writes()[1][1]).toEqual(original);expect(s.effects).toBe(1);expect(readProductionRecovery('disposable:actor-1').pending.POCKET_FABRIC).toBeUndefined()
  })
  it('keeps the original roll revision when refreshed stock changes instead of silently rebasing a count',async()=>{
    const s=server();await mount();await prepare();await change('Jumlah kain kantong','15');s.data.rolls[0].revision=revision(2);s.data.rolls[0].qty='19.000000'
    await click('Muat ulang');expect(button('Sahkan pengurangan stok').disabled).toBe(true)
    expect(container.textContent).toContain('Stok roll sudah berubah');expect(writes()).toHaveLength(0)
  })
  it('requires a reversal reason and preserves large version strings',async()=>{
    const s=server();s.data.history=[{id:doc,number:'KKT-X',status:'POSTED',row_version:'9007199254740993',date:'2026-09-21',reason:'Keluar bersama',roll_id:id,roll_number:'KKT-001',material_name:'Kantong',unit_code:'YD',issued_quantity:'5.000000',current_cost:'11.25',cost_policy:'PERIOD_EXPENSE'}]
    await mount();await click('Batalkan KKT-001');expect(button('Sahkan pembatalan').disabled).toBe(true)
    await change('Alasan pembatalan','Salah roll');await click('Sahkan pembatalan')
    expect(writes()[0][1].p_payload).toEqual({id:doc,expected_version:'9007199254740993',reason:'Salah roll'})
  })
  it('denies missing stock permission and malformed numeric server data',async()=>{
    server();auth.current=structuredClone(recoveryIdentity);await mount();expect(client.rpc).not.toHaveBeenCalled()
    const w=data();expect(parsePocketWorkspace(w).roll_count).toBe(1)
    expect(()=>parsePocketWorkspace({...w,rolls:[{...w.rolls[0],qty:20}]})).toThrow()
    expect(()=>parsePocketWorkspace({...w,rolls:[{...w.rolls[0],qty:'-1.000000'}]})).toThrow()
  })
})

describe('optional pocket fabric period HPP allocation',()=>{
  beforeEach(()=>{const a=auth.current as typeof recoveryIdentity;a.identity.permissions.push('finance.hpp.manage')})
  const dates=async()=>{await change('Awal periode kain kantong','2026-09-01');await change('Akhir periode kain kantong','2026-09-20')}
  it('previews without a write, then posts the exact reviewed period and source revision',async()=>{
    const s=server();await mount();await dates();await click('Lihat pembagian')
    expect(writes()).toHaveLength(0);expect(s.effects).toBe(0);expect(container.textContent).toContain('10 pcs selesai dijahit');expect(container.textContent).toContain('1,125 per pcs')
    await change('Alasan pembagian kain kantong','Alokasi September');await click('Sahkan pembagian ke HPP')
    expect(writes()[0][1].p_action).toBe('POST_PERIOD')
    expect(writes()[0][1].p_payload).toEqual({period_start:'2026-09-01',period_end:'2026-09-20',expected_revision:revision(8),reason:'Alokasi September'})
    expect(s.effects).toBe(1)
  })
  it('discards a preview after a period edit and refuses a mismatched server period',async()=>{
    server();await mount();await dates();await click('Lihat pembagian');await change('Akhir periode kain kantong','2026-09-21')
    expect(container.textContent).not.toContain('Sahkan pembagian ke HPP');await click('Lihat pembagian')
    expect(container.textContent).toContain('Periode hasil tidak cocok');expect(writes()).toHaveLength(0)
  })
  it('blocks overlap, missing output, blank reason and malformed exact decimal data',async()=>{
    const s=server();s.preview={...periodPreview(),blocked:true,can_post:false};await mount();await dates();await click('Lihat pembagian')
    expect(button('Sahkan pembagian ke HPP').disabled).toBe(true);expect(container.textContent).toContain('bertumpang tindih')
    s.preview={...periodPreview(),quantity:'0',per_piece:'0.000000',can_post:false};await click('Lihat pembagian');expect(button('Sahkan pembagian ke HPP').disabled).toBe(true)
    s.preview=periodPreview();await click('Lihat pembagian');await change('Alasan pembagian kain kantong',' ');expect(button('Sahkan pembagian ke HPP').disabled).toBe(true)
    s.preview={...periodPreview(),amount:11.25};await click('Lihat pembagian');expect(container.textContent).toContain('Pembagian periode tidak valid');expect(writes()).toHaveLength(0)
    expect(()=>parsePocketPreview({...periodPreview(),quantity:10})).toThrow()
    expect(()=>parsePocketPreview({...periodPreview(),blocked:true})).toThrow()
    expect(()=>parsePocketPreview(null)).toThrow()
    expect(parsePocketPreview({...periodPreview(),per_piece:'999999999999999999.000001'}).per_piece).toBe('999999999999999999.000001')
  })
  it('recovers a lost allocation reply with the same UUID after remount',async()=>{
    const s=server();await mount();await dates();await click('Lihat pembagian');s.lose=true;await click('Sahkan pembagian ke HPP')
    const original=structuredClone(writes()[0][1]);expect(original.p_action).toBe('POST_PERIOD')
    expect(readProductionRecovery('disposable:actor-1').pending.POCKET_FABRIC?.id).toBe(original.p_client_request_id)
    await act(async()=>root.unmount());root=createRoot(container);s.lose=false;await mount();await click('Reconcile')
    expect(writes()[1][1]).toEqual(original);expect(s.effects).toBe(1);expect(readProductionRecovery('disposable:actor-1').pending.POCKET_FABRIC).toBeUndefined()
  })
  it('cancels using the displayed allocation revision and a required reason',async()=>{
    const s=server();s.data.periods=[{id:doc,period_start:'2026-09-01',period_end:'2026-09-20',status:'ACTIVE',reason:'Alokasi September',quantity:'9007199254740993',original_amount:'11.25',current_amount:'15.00',per_piece:'0.000000',revision:revision(9)}]
    await mount();await click('Batalkan alokasi');expect(button('Sahkan pembatalan alokasi').disabled).toBe(true)
    await change('Alasan pembatalan alokasi','Perbaiki hasil jahit');await click('Sahkan pembatalan alokasi')
    expect(writes()[0][1].p_action).toBe('CANCEL_PERIOD');expect(writes()[0][1].p_payload).toEqual({id:doc,expected_revision:revision(9),reason:'Perbaiki hasil jahit'})
  })
  it('keeps stock recording available while hiding HPP writes without HPP permission',async()=>{
    server();const a=auth.current as typeof recoveryIdentity;a.identity.permissions=a.identity.permissions.filter(p=>p!=='finance.hpp.manage')
    await mount();expect(container.textContent).toContain('Kurangi stok gudang');expect(container.querySelector('[aria-label="Awal periode kain kantong"]')).toBeNull()
    expect(writes()).toHaveLength(0)
  })
})
