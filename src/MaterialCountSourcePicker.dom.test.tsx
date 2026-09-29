// @vitest-environment jsdom
import { act } from 'react'
import { createRoot, type Root } from 'react-dom/client'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import MaterialCountSourcePicker from './MaterialCountSourcePicker'
import { parseCountOptions, type CountIdentity } from './materialCountContract'
import type { getUatSupabaseClient } from './lib/supabase'
const loc='11111111-1111-4111-8111-111111111111',other='22222222-2222-4222-8222-222222222222',mat='33333333-3333-4333-8333-333333333333'
const choice={material_id:mat,material_sku:'BUTTON-NEW',material_name:'Kancing baru',material_type:'ACCESSORY',unit_code:'PCS',roll_id:null,roll_number:null}
function response(location=loc){return {contract_version:'cp7.material-count-options.v1',selection_basis:'REGISTERED_IDENTITY_NOT_STOCK',read_at:'2026-09-29T10:00:00Z',location_id:location,location_name:location===loc?'Gudang pertama':'Gudang kedua',query:'',page:{rows:[choice],total:'1',offset:0,limit:25,next_offset:null}}}
const expected={location_id:loc,q:'',offset:0,limit:25}
const client={rpc:vi.fn()},onSelect=vi.fn<(x:CountIdentity)=>void>()
let root:Root,container:HTMLDivElement
beforeEach(()=>{Object.assign(globalThis,{IS_REACT_ACT_ENVIRONMENT:true});container=document.createElement('div');document.body.append(container);root=createRoot(container);client.rpc.mockReset();onSelect.mockReset()})
afterEach(async()=>{await act(async()=>root.unmount());container.remove()})
async function flush(){await act(async()=>{await new Promise(r=>setTimeout(r,0))})}
async function mount(location=loc,selected:string[]=[],disabled=false){await act(async()=>root.render(<MaterialCountSourcePicker client={client as unknown as ReturnType<typeof getUatSupabaseClient>} location={{id:location,name:location===loc?'Gudang pertama':'Gudang kedua'}} selected={selected} disabled={disabled} onSelect={onSelect}/>));await flush()}
function button(name:string){const b=[...container.querySelectorAll('button')].find(b=>b.textContent===name);if(!b)throw Error('Missing '+name);return b}
it('accepts identity-only sources and refuses invented quantity, valuation or an unregistered fabric roll',()=>{
 expect(parseCountOptions(response(),expected).page.rows[0]).toEqual(choice)
 for(const extra of [{qty:'0'},{valuation:{unit_cost:'0'}},{material_type:'FABRIC',roll_id:null,roll_number:null}])expect(()=>parseCountOptions({...response(),page:{...response().page,rows:[{...choice,...extra}]}},expected)).toThrow()
})
it('binds sources to warehouse/search and refuses duplicate or incomplete pages',()=>{
 expect(()=>parseCountOptions(response(other),expected)).toThrow()
 expect(()=>parseCountOptions({...response(),query:'other'},expected)).toThrow()
 expect(()=>parseCountOptions({...response(),page:{...response().page,rows:[choice,choice],total:'2'}},expected)).toThrow()
 expect(()=>parseCountOptions({...response(),page:{...response().page,total:'2'}},expected)).toThrow()
})
it('selects the registered position without fabricating stock, price or a movement timestamp and prevents duplicate additions',async()=>{
 client.rpc.mockResolvedValue({data:response(),error:null});await mount();expect(container.textContent).toContain('Saldo diperiksa saat pratinjau.')
 await act(async()=>button('Tambahkan Kancing baru').click());expect(onSelect).toHaveBeenCalledWith({material_id:mat,material_sku:'BUTTON-NEW',material_name:'Kancing baru',unit_code:'PCS',roll_id:null,roll_number:null,location_id:loc,location_name:'Gudang pertama'})
 await mount(loc,[`${mat}:null`]);expect(button('Sudah dipilih').disabled).toBe(true)
})
it('retires a late result for the old warehouse and respects the parent write/recovery lock',async()=>{
 let release!:(v:unknown)=>void;client.rpc.mockImplementation((_n:string,args:{p_query:{location_id:string}})=>args.p_query.location_id===loc?new Promise(r=>{release=r}):Promise.resolve({data:response(other),error:null}))
 await mount();await mount(other);await act(async()=>release({data:response(),error:null}));await flush();await act(async()=>button('Tambahkan Kancing baru').click())
 expect(onSelect.mock.calls[0][0].location_id).toBe(other);await mount(other,[],true);expect(button('Tambahkan Kancing baru').disabled).toBe(true)
})
it('clears selectable identities on a failed refresh and can retry without supplying a stock fallback',async()=>{
 client.rpc.mockResolvedValue({data:response(),error:null});await mount();client.rpc.mockResolvedValue({data:null,error:{message:'Source unavailable'}})
 await act(async()=>button('Cari barang terdaftar').click());await flush();expect(container.querySelectorAll('.cmat-roll')).toHaveLength(0);expect(container.textContent).toContain('Source unavailable');expect(onSelect).not.toHaveBeenCalled()
 client.rpc.mockResolvedValue({data:response(),error:null});await act(async()=>button('Cari barang terdaftar').click());await flush();expect(button('Tambahkan Kancing baru').disabled).toBe(false)
})
