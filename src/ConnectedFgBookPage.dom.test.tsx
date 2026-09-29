// @vitest-environment jsdom
import {act} from 'react'
import {createRoot,type Root} from 'react-dom/client'
import {afterEach,beforeEach,describe,expect,it,vi} from 'vitest'
import ConnectedFgBookPage from './ConnectedFgBookPage'
import {parseFgBook,parseFgBookOptions,parseFgBookOutcome} from './fgBookContract'
import {recoveryIdentity} from '../tests/fixtures/productionRecovery'
const state=vi.hoisted(()=>({auth:null as unknown}))
const client=vi.hoisted(()=>({rpc:vi.fn()}))
vi.mock('./auth/AuthProvider',()=>({useAuth:()=>state.auth}))
vi.mock('./lib/supabase',()=>({getUatSupabaseClient:()=>client}))
const id='11111111-1111-4111-8111-111111111111',second='22222222-2222-4222-8222-222222222222',at='2026-09-29T03:00:00Z',token='a'.repeat(32)
const row={id,book_order:'-9007199254740993',physical_at:at,recorded_at:at,product_id:id,brand_id:id,brand_name:'Vivo',commercial_sku:'LUNA',product_name:'Celana',size_code:'M',lot_id:id,lot_number:'LOT-01',location_id:id,location_name:'Gudang FG',quality_grade:'GRADE_A',customer_id:id,customer_name:'Toko A',movement_type:'SALE',source_type:'SALE_ITEM',source_id:id,reversal_of_id:null,notes:null,physical_delta:'-4',reservation_delta:'0',available_delta:'-4',book_physical_before:'0',book_physical_after:'-4',book_available_after:'-4',book_reserved_after:'0',official_physical_after:'11',official_available_after:'11',official_reserved_after:'0'}
const page=(rows:unknown[])=>({rows,total:String(rows.length),offset:0,limit:25,next_offset:null})
function book(){return {contract_version:'cp7.fg-book.v1',read_at:at,knowledge:'CURRENT',book_token:token,can_order:true,quantity_scope:'PHYSICAL_PRODUCT_LOCATION_GRADE',presentation_only:true,page:page([{...row},{...row,id:second}])}}
const options=()=>({contract_version:'cp7.fg-book-options.v1',read_at:at,kind:'BRAND',page:page([{id,label:'Vivo',code:'VIVO'}])})
let root:Root,container:HTMLDivElement
beforeEach(()=>{Object.assign(globalThis,{IS_REACT_ACT_ENVIRONMENT:true});localStorage.clear();client.rpc.mockReset();const a=structuredClone(recoveryIdentity);a.identity.permissions.push('warehouse.movement.view');state.auth=a;Object.defineProperty(navigator,'locks',{configurable:true,value:{request:async(_n:string,_o:unknown,fn:(l:unknown)=>Promise<unknown>)=>fn({})}});container=document.createElement('div');document.body.append(container);root=createRoot(container)})
afterEach(async()=>{await act(async()=>root.unmount());container.remove();localStorage.clear();Reflect.deleteProperty(navigator,'locks');vi.restoreAllMocks()})
async function flush(){await act(async()=>{await new Promise(r=>setTimeout(r,0))})}
async function mount(){await act(async()=>root.render(<ConnectedFgBookPage bookName="Vivo"/>));await flush()}
async function click(label:string){const b=[...container.querySelectorAll('button')].find(x=>x.textContent===label);if(!b)throw Error(label);await act(async()=>b.click());await flush()}
function server(){client.rpc.mockImplementation(async(name:string,args:Record<string,unknown>)=>({error:null,data:name==='erp_cp7_get_fg_book_options_v1'?options():name==='erp_cp7_save_fg_book_v1'?{contract_version:'cp7.fg-book-outcome.v1',kind:'COMMITTED_OUTCOME',action:args.p_action,request_id:args.p_request,source_id:(args.p_payload as typeof row).source_id,book_token:token,presentation_only:true}:book()}))}
describe('global FG book boundary',()=>{
 it('keeps signed book balances/rank and separate official balance; no money field is admitted',()=>{expect(parseFgBook(book()).page.rows[0].book_order).toBe('-9007199254740993');expect(parseFgBook(book()).page.rows[0].book_physical_after).toBe('-4');const bad=book();Object.assign(bad.page.rows[0] as object,{hpp:'10'});expect(()=>parseFgBook(bad)).toThrow();expect(()=>parseFgBook({...book(),page:{...book().page,total:'3'}})).toThrow()})
 it('resolves a real initial brand and binds move to exact source/anchor/token instead of a global row number',async()=>{server();await mount();expect(client.rpc.mock.calls.find(([n])=>n==='erp_cp7_get_fg_book_v1')![1].p_query.brand_ids).toEqual([id]);expect(container.textContent).toContain('−0 lusin 4 pcs');await click('↓ Pindah ke bawah');const write=client.rpc.mock.calls.find(([n])=>n==='erp_cp7_save_fg_book_v1')![1];expect(write.p_payload).toEqual({book_token:token,source_id:id,target_id:second,placement:'AFTER'});expect(typeof write.p_request).toBe('string');expect(container.textContent).not.toContain('Rp')})
 it('requires reset review and clears all cards after a denied reload',async()=>{server();await mount();const reset=[...container.querySelectorAll('button')].find(b=>b.textContent==='Kembalikan seluruh urutan buku')!;expect(reset.disabled).toBe(true);client.rpc.mockResolvedValue({data:null,error:{status:403,message:'Hak berubah'}});await click('Muat ulang buku');expect(container.querySelectorAll('.cfgb-card')).toHaveLength(0);expect(container.textContent).toContain('Akun tidak memiliki izin')})
 it('rejects mismatched options and successful outcomes for another movement or UUID',()=>{expect(()=>parseFgBookOptions(options(),'CUSTOMER')).toThrow();const p={source_id:id},o={contract_version:'cp7.fg-book-outcome.v1',kind:'COMMITTED_OUTCOME',action:'MOVE',request_id:id,source_id:second,book_token:token,presentation_only:true};expect(()=>parseFgBookOutcome(o,id,'MOVE',p)).toThrow();expect(()=>parseFgBookOutcome({...o,source_id:id},second,'MOVE',p)).toThrow()})
})
