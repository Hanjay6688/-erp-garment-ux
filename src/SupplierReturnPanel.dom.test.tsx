// @vitest-environment jsdom
import {act} from 'react'
import {createRoot,type Root} from 'react-dom/client'
import {afterEach,beforeEach,describe,expect,it,vi} from 'vitest'
import SupplierReturnPanel from './SupplierReturnPanel'
import {parseSupplierReturns,parseSupplierReturnOutcome,parseSupplierReturnSources} from './supplierReturnContract'
import {readProductionRecovery} from './productionRecovery'
import {recoveryIdentity} from '../tests/fixtures/productionRecovery'
import {supplierReturnsFixture,returnPurchaseId as purchase,returnSourceId as source,returnId as ret} from '../tests/fixtures/supplierReturns'
const state=vi.hoisted(()=>({auth:null as unknown}))
const client=vi.hoisted(()=>({rpc:vi.fn()}))
vi.mock('./auth/AuthProvider',()=>({useAuth:()=>state.auth}))
vi.mock('./lib/supabase',()=>({getUatSupabaseClient:()=>client}))
let root:Root,container:HTMLDivElement
beforeEach(()=>{Object.assign(globalThis,{IS_REACT_ACT_ENVIRONMENT:true});localStorage.clear();client.rpc.mockReset();const a=structuredClone(recoveryIdentity);a.identity.permissions.push('warehouse.procurement.view','warehouse.procurement.create','warehouse.procurement.reverse','finance.ap.view');state.auth=a;Object.defineProperty(navigator,'locks',{configurable:true,value:{request:async(_n:string,_o:unknown,fn:(l:unknown)=>Promise<unknown>)=>fn({})}});container=document.createElement('div');document.body.append(container);root=createRoot(container)})
afterEach(async()=>{await act(async()=>root.unmount());container.remove();localStorage.clear();Reflect.deleteProperty(navigator,'locks');vi.restoreAllMocks()})
async function flush(){await act(async()=>{await new Promise(r=>setTimeout(r,0))})}
async function mount(id:string|null=purchase,refresh=async(_id:string)=>true){await act(async()=>root.render(<SupplierReturnPanel purchaseId={id} onReceiptUpdated={refresh}/>));await flush()}
function button(label:string){const b=[...container.querySelectorAll('button')].find(b=>b.textContent===label);if(!b)throw Error('Missing '+label);return b}
async function click(label:string){await act(async()=>button(label).click());await flush()}
async function input(label:string,value:string){const el=container.querySelector<HTMLInputElement>(`[aria-label="${label}"]`)!;await act(async()=>{Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value')!.set!.call(el,value);el.dispatchEvent(new Event('input',{bubbles:true}))});await flush()}
async function select(label:string,value:string){const el=container.querySelector<HTMLSelectElement>(`[aria-label="${label}"]`)!;await act(async()=>{el.value=value;el.dispatchEvent(new Event('change',{bubbles:true}))});await flush()}
async function check(){await act(async()=>container.querySelector<HTMLInputElement>('[aria-label="Retur sudah diperiksa"]')!.click());await flush()}
const writes=()=>client.rpc.mock.calls.filter(([n])=>n==='erp_cp7_save_supplier_return_v1')
function server(finance=true){const s={status:null as 'DRAFT'|'POSTED'|'REVERSED'|null,lose:false,wrong:false,failRead:false,effects:0,hide:false},cache=new Map<string,unknown>();client.rpc.mockImplementation(async(name:string,args:Record<string,unknown>)=>{
 if(name==='erp_cp7_get_procurement_options_v1')return {data:{contract_version:'cp7.procurement-options.v1',kind:'LOCATION',rows:[{id:source,code:'W-1',name:'Gudang A'}],total:'1',offset:0,limit:25,next_offset:null},error:null}
 if(name==='erp_cp7_get_supplier_returns_v1')return s.failRead&&s.status?{data:null,error:{message:'Return read failed'}}:{data:supplierReturnsFixture(s.status,finance,(args.p_location as string)||source),error:null}
 if(name==='erp_cp7_save_supplier_return_v1'){const key=String(args.p_request);if(!cache.has(key)){s.status=args.p_action==='SAVE'?'DRAFT':args.p_action==='POST'?'POSTED':'REVERSED';s.effects++;cache.set(key,{contract_version:'cp7.supplier-return-outcome.v1',kind:'COMMITTED_OUTCOME',action:args.p_action,request_id:key,purchase_id:purchase,return_id:ret,row_version:s.status==='DRAFT'?'9007199254740993':s.status==='POSTED'?'9007199254740994':'9007199254740995',status:s.status})}return s.lose?{data:null,error:{status:503,message:'Lost committed reply'}}:{data:s.wrong?{ok:true}:cache.get(key),error:null}}
 throw Error('Unexpected '+name)
 });return s}
async function draft(){await click('Buat retur supplier');await input('Nomor retur supplier','RET-TEST');await select('Roll retur 1',source);await input('Jumlah retur 1','2,000001');await click('Simpan draft retur')}
async function review(){await click('Tinjau pengiriman retur');expect(button('Sahkan pengiriman retur').disabled).toBe(true);await check()}
describe('supplier return connected boundary',()=>{
 it('saves exact source quantities without a caller credit price, then posts the reviewed native draft',async()=>{const s=server();await mount();await draft();const saved=writes()[0][1];expect(saved.p_expected).toBeNull();expect(saved.p_payload.items[0]).toEqual({purchase_item_id:source,material_id:source,roll_id:source,qty:'2.000001',notes:null});expect(JSON.stringify(saved)).not.toContain('credit_unit_price');expect(container.textContent).toContain('Utang Belum ditetapkan');await review();await click('Sahkan pengiriman retur');expect(writes()[1][1]).toMatchObject({p_action:'POST',p_expected:'9007199254740993',p_payload:{purchase_id:purchase,return_id:ret}});expect(container.textContent).toContain('Retur sudah dikirim');expect(container.textContent).toContain('Utang Rp20');expect(s.effects).toBe(2)})
 it('recovers a committed POST after reload with no receipt selected and restores that source',async()=>{const s=server();const parent=vi.fn(async()=>true);await mount(purchase,parent);await draft();await review();s.lose=true;await click('Sahkan pengiriman retur');const sent=structuredClone(writes()[1][1]);expect(readProductionRecovery('disposable:actor-1').pending.SUPPLIER_RETURN?.id).toBe(sent.p_request);await act(async()=>root.unmount());root=createRoot(container);s.lose=false;await mount(null,parent);await click('Reconcile transaksi');expect(writes()[2][1]).toEqual(sent);expect(s.effects).toBe(2);expect(parent).toHaveBeenLastCalledWith(purchase);expect(readProductionRecovery('disposable:actor-1').pending.SUPPLIER_RETURN).toBeUndefined();expect(container.querySelector('.cproc-return-detail')?.textContent).toContain('Retur sudah dikirim')})
 it('retires the form after COMMIT even when read-back fails and cannot resend a detached submit',async()=>{const s=server();await mount();await click('Buat retur supplier');await input('Nomor retur supplier','RET-TEST');await select('Roll retur 1',source);await input('Jumlah retur 1','2');const old=button('Simpan draft retur');s.failRead=true;await click('Simpan draft retur');expect(container.textContent).toContain('Aksi sudah tersimpan');expect(container.textContent).not.toContain('Simpan draft retur');await act(async()=>old.click());expect(writes()).toHaveLength(1);s.failRead=false;await click('Muat ulang retur');expect(container.textContent).toContain('Draft retur')})
 it('retains malformed success as pending instead of accepting another return identity',async()=>{const s=server();await mount();s.wrong=true;await draft();expect(readProductionRecovery('disposable:actor-1').pending.SUPPLIER_RETURN).toBeTruthy();expect(button('Simpan draft retur').disabled).toBe(true);expect(()=>parseSupplierReturnOutcome({contract_version:'cp7.supplier-return-outcome.v1',kind:'COMMITTED_OUTCOME',action:'POST',request_id:source,purchase_id:purchase,return_id:source,row_version:'1',status:'POSTED'},source,'POST',{purchase_id:purchase,return_id:ret})).toThrow()})
 it('uses the exact posted return revision and renewed review for reversal',async()=>{const s=server();s.status='POSTED';await mount();await act(async()=>container.querySelector<HTMLButtonElement>('.cproc-receipt')!.click());await flush();await click('Tinjau pembatalan retur');await input('Alasan tindakan retur','Barang kembali dari supplier');await check();await input('Alasan tindakan retur','Barang telah diperiksa kembali');expect(button('Batalkan retur supplier').disabled).toBe(true);await check();await click('Batalkan retur supplier');expect(writes()[0][1]).toMatchObject({p_action:'REVERSE',p_expected:'9007199254740994'});expect(container.textContent).toContain('Retur dibatalkan')})
 it('keeps money out of operational data while allowing physical source selection',async()=>{const a=state.auth as typeof recoveryIdentity;a.identity.permissions=a.identity.permissions.filter(p=>p!=='finance.ap.view');server(false);await mount();await draft();expect(container.textContent).not.toContain('Rp');const w=supplierReturnsFixture('DRAFT',false);expect(()=>parseSupplierReturns(w,purchase,false)).not.toThrow();expect(()=>parseSupplierReturns({...w,page:{...w.page,rows:supplierReturnsFixture('DRAFT',true).page.rows}},purchase,false)).toThrow()})
 it('refuses incomplete pages and source lines, and preserves exact timestamp/notes on draft correction',async()=>{const w=supplierReturnsFixture('DRAFT');expect(()=>parseSupplierReturns({...w,source_line_count:'2'},purchase,true)).toThrow();expect(()=>parseSupplierReturns({...w,page:{...w.page,total:'2'}},purchase,true)).toThrow();const s=server();s.status='DRAFT';await mount();await act(async()=>container.querySelector<HTMLButtonElement>('.cproc-receipt')!.click());await flush();await click('Perbaiki draft retur');await input('Alasan retur supplier','Koreksi alasan saja');await click('Simpan draft retur');expect(writes()[0][1]).toMatchObject({p_expected:'9007199254740993',p_payload:{id:ret,physical_at:'2026-09-28T09:00:27.123Z',items:[{notes:'Barang rusak supplier'}]}})})
 it('does not allow another write when the parent source cannot be refreshed',async()=>{server();await mount(purchase,async()=>false);await draft();expect(container.textContent).toContain('Aksi sudah tersimpan');expect(container.textContent).not.toContain('Buat retur supplier');expect(writes()).toHaveLength(1)})
})

const secondPurchase='33333333-3333-4333-8333-333333333333',secondSource='55555555-5555-4555-8555-555555555555',secondLine='66666666-6666-4666-8666-666666666666'
function sourcePage(){return {contract_version:'cp7.return-sources.v1',read_at:'2026-09-30T01:00:00Z',purchase_id:purchase,supplier_id:source,page:{rows:[{id:secondPurchase,number:'SJ-SECOND',physical_at:'2026-09-28T09:00:00Z',row_version:'9007199254740993'}],total:'1',offset:0,limit:25,next_offset:null}}}
function combinedServer(){
 const state={status:null as 'DRAFT'|'POSTED'|'REVERSED'|null,lose:false,invalidSource:false,effects:0},cache=new Map<string,unknown>()
 client.rpc.mockImplementation(async(name:string,args:Record<string,unknown>)=>{
  if(name==='erp_cp7_get_procurement_options_v1')return {data:{contract_version:'cp7.procurement-options.v1',kind:'LOCATION',rows:[{id:source,code:'W-1',name:'Gudang A'}],total:'1',offset:0,limit:25,next_offset:null},error:null}
  if(name==='erp_cp7_get_supplier_return_sources_v1')return {data:sourcePage(),error:null}
  if(name==='erp_cp7_get_supplier_returns_v1'){
   const w=supplierReturnsFixture(state.status),second=args.p_purchase===secondPurchase
   if(second){w.purchase_id=secondPurchase;w.purchase_number='SJ-SECOND';w.source_lines[0]={...w.source_lines[0],id:secondSource,material_id:secondSource,rolls:[{...w.source_lines[0].rolls[0],id:secondSource,number:'ROLL-2'}]}}
   if(state.invalidSource&&second)w.source_line_count='2'
   for(const d of w.page.rows){d.single_receipt=false;d.line_count='2';d.lines.push({...d.lines[0],id:secondLine,purchase_id:secondPurchase,purchase_item_id:secondSource,purchase_number:'SJ-SECOND',material_id:secondSource,roll_id:secondSource,roll_number:'ROLL-2',qty:'3.000000'})}
   return {data:w,error:null}
  }
  if(name==='erp_cp7_save_supplier_return_v1'){
   const key=String(args.p_request)
   if(!cache.has(key)){state.status=args.p_action==='SAVE_DOCUMENT'?'DRAFT':args.p_action==='POST_DOCUMENT'?'POSTED':'REVERSED';state.effects++;cache.set(key,{contract_version:'cp7.supplier-return-outcome.v1',kind:'COMMITTED_OUTCOME',action:args.p_action,request_id:key,purchase_id:purchase,return_id:ret,row_version:state.status==='DRAFT'?'9007199254740993':state.status==='POSTED'?'9007199254740994':'9007199254740995',status:state.status})}
   return state.lose?{data:null,error:{status:503,message:'Lost committed reply'}}:{data:cache.get(key),error:null}
  }
  throw Error('Unexpected '+name)
 });return state
}
async function chooseSecond(){await click('Tambah penerimaan lain');await act(async()=>container.querySelector<HTMLButtonElement>('[aria-label="Pilih penerimaan retur gabungan"] .cproc-receipt')!.click());await flush()}
async function combinedDraft(){await click('Buat retur supplier');await input('Nomor retur supplier','RET-COMBINED');await select('Roll retur 1',source);await input('Jumlah retur 1','2');await chooseSecond();await select('Roll retur 2',secondSource);await input('Jumlah retur 2','3');await click('Simpan draft retur')}
describe('complete supplier return documents',()=>{
 it('selects same-supplier receipts and edits every source without silently dropping a leg',async()=>{
  combinedServer();await mount();await combinedDraft();const saved=writes()[0][1]
  expect(saved).toMatchObject({p_action:'SAVE_DOCUMENT',p_expected:null,p_payload:{items:[{purchase_item_id:source,qty:'2'},{purchase_item_id:secondSource,qty:'3'}]}})
  expect(JSON.stringify(saved)).not.toContain('credit_unit_price');expect(container.textContent).toContain('Retur gabungan')
  await click('Perbaiki draft retur');expect(container.querySelector<HTMLInputElement>('[aria-label="Jumlah retur 2"]')?.value).toBe('3.000000')
  await input('Alasan retur supplier','Semua penerimaan diperiksa');await click('Simpan draft retur')
  expect(writes()[1][1]).toMatchObject({p_action:'SAVE_DOCUMENT',p_expected:'9007199254740993',p_payload:{id:ret,physical_at:'2026-09-28T09:00:27.123Z',items:[{purchase_item_id:source},{purchase_item_id:secondSource}]}})
 })
 it('reconciles a complete committed return and reverses only the reviewed full source set',async()=>{
  const s=combinedServer();await mount();await combinedDraft();await review();s.lose=true;await click('Sahkan pengiriman retur')
  const sent=structuredClone(writes()[1][1]);expect(sent).toMatchObject({p_action:'POST_DOCUMENT',p_expected:'9007199254740993',p_payload:{reviewed_purchase_ids:[purchase,secondPurchase]}})
  await act(async()=>root.unmount());root=createRoot(container);s.lose=false;await mount(null);await click('Reconcile transaksi')
  expect(writes()[2][1]).toEqual(sent);expect(s.effects).toBe(2);expect(readProductionRecovery('disposable:actor-1').pending.SUPPLIER_RETURN).toBeUndefined()
  await click('Tinjau pembatalan retur');await input('Alasan tindakan retur','Seluruh barang kembali');await check();await click('Batalkan retur supplier')
  expect(writes()[3][1]).toMatchObject({p_action:'REVERSE_DOCUMENT',p_expected:'9007199254740994',p_payload:{reviewed_purchase_ids:[purchase,secondPurchase]}})
 })
 it('preserves the entered first leg when another source is incomplete and cannot submit it as loaded',async()=>{
  const s=combinedServer();s.invalidSource=true;await mount();await click('Buat retur supplier');await input('Nomor retur supplier','RET-PRESERVED');await input('Jumlah retur 1','2');await chooseSecond()
  expect(container.textContent).toContain('Data retur supplier belum lengkap');expect(container.querySelector<HTMLInputElement>('[aria-label="Nomor retur supplier"]')?.value).toBe('RET-PRESERVED')
  expect(container.querySelector('[aria-label="Jumlah retur 2"]')).toBeNull();expect(writes()).toHaveLength(0)
 })
 it('refuses incomplete, wrong-supplier and money-bearing source pages',()=>{
  const p=sourcePage();expect(parseSupplierReturnSources(p,purchase,source,0).page.rows).toHaveLength(1)
  for(const v of [{...p,supplier_id:secondSource},{...p,page:{...p.page,total:'2'}},{...p,page:{...p.page,rows:[{...p.page.rows[0],amount:'20'}]}}])expect(()=>parseSupplierReturnSources(v,purchase,source,0)).toThrow()
 })
})
