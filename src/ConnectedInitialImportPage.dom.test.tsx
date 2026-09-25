// @vitest-environment jsdom
import { act } from 'react'
import { createRoot, type Root } from 'react-dom/client'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import ConnectedInitialImportPage, { parseInitialImportWorkspace } from './ConnectedInitialImportPage'
import { parseInitialProductionSources } from './initialProduction'
import { recoveryIdentity } from '../tests/fixtures/productionRecovery'
import { readProductionRecovery } from './productionRecovery'
const auth = vi.hoisted(() => ({ current: null as unknown }))
const client = vi.hoisted(() => ({ rpc: vi.fn() }))
vi.mock('./auth/AuthProvider', () => ({ useAuth: () => auth.current }))
vi.mock('./lib/supabase', () => ({ getUatSupabaseClient: () => client }))
const id = '11111111-1111-4111-8111-111111111111'
const rowId = '22222222-2222-4222-8222-222222222222'
const rev = (n: number) => n.toString(16).padStart(64, '0')
let root: Root, container: HTMLDivElement
beforeEach(() => {
  Object.assign(globalThis, { IS_REACT_ACT_ENVIRONMENT: true })
  localStorage.clear(); client.rpc.mockReset(); auth.current = structuredClone(recoveryIdentity)
  Object.defineProperty(navigator, 'locks', { configurable:true, value:{request:async (_name: string, _options:unknown, fn:(lock:unknown)=>Promise<unknown>) => fn({})} })
  container = document.createElement('div'); document.body.append(container); root = createRoot(container)
})
afterEach(async () => { await act(async () => root.unmount()); container.remove(); localStorage.clear(); Reflect.deleteProperty(navigator, 'locks'); vi.restoreAllMocks() })
async function flush() { await act(async () => { await new Promise(resolve => setTimeout(resolve,0)) }) }
async function change(input: HTMLInputElement | HTMLSelectElement, value: string) {
  await act(async () => { Object.getOwnPropertyDescriptor(input instanceof HTMLSelectElement ? HTMLSelectElement.prototype : HTMLInputElement.prototype,'value')!.set!.call(input,value); input.dispatchEvent(new Event('input',{bubbles:true}));input.dispatchEvent(new Event('change',{bubbles:true})) });await flush()
}
function button(text: string) { const b=[...container.querySelectorAll('button')].find(b=>b.textContent?.includes(text));if(!b)throw new Error(text+' missing '+container.textContent);return b }
async function click(text:string) { await act(async()=>button(text).click());await flush() }
function server() {
 const state={version:1,status:'DRAFT',rows:[] as { id:string;entity:string;source_row_no:number;payload:Record<string,string>;validation_status:string;errors:string[];applied:boolean }[],cash_advances:[] as Record<string,unknown>[],advance_payrolls:[] as Record<string,unknown>[],prepayments:[] as Record<string,unknown>[],prepayment_cash_accounts:[] as Record<string,unknown>[],production_sources:[] as Record<string,unknown>[],bb:null as Record<string,unknown>|null,lose:false,stale:false,effects:0}
 const cache=new Map<string,unknown>()
 client.rpc.mockImplementation(async(name:string,args:Record<string,unknown>)=>{
  if(name==='erp_get_initial_import_workspace_v1')return {data:{recent:[{id,batch_code:'AWAL',status:state.status}],batch:args.p_batch_id?{id,code:'AWAL',status:state.status,cutover_at:'2026-09-20T00:00:00+07:00',revision:rev(state.version),rows:state.rows,cash_advances:state.cash_advances,advance_payrolls:state.advance_payrolls,prepayments:state.prepayments,prepayment_cash_accounts:state.prepayment_cash_accounts,production_sources:state.production_sources,...(state.bb??{})}:null},error:null}
  const payload=args.p_payload as Record<string,unknown>, key=String(args.p_client_request_id)
  if(!cache.has(key)) {
   if(state.stale){state.version++;return {data:null,error:{code:'P0001',message:'STALE_VERSION'}}}
   if(args.p_action==='SAVE_FILE')state.rows=(payload.rows as {source_row_no:number;payload:Record<string,string>}[]).map(r=>({...r,id:rowId,entity:String(payload.entity),validation_status:'PENDING',errors:[],applied:false}))
   if(args.p_action==='VALIDATE')state.status='READY'
   if(args.p_action==='FINALIZE')state.status='POSTED'
   state.effects++;state.version++
   cache.set(key,{request_id:key,action:args.p_action,batch_id:id,status:state.status,revision:rev(state.version)})
  }
  return state.lose?{data:null,error:{status:503,message:'Lost reply'}}:{data:cache.get(key),error:null}
 })
 return state
}
async function mount() { await act(async()=>root.render(<ConnectedInitialImportPage/>));await flush();await change(container.querySelector('select[aria-label="Batch impor"]')!,id) }
async function csv() {
 await change([...container.querySelectorAll('select')][1],'CUSTOMER')
 const file=new File(['customer_code,customer_name\n001,Toko lama'],'awal.csv',{type:'text/csv'})
 Object.defineProperty(file,'arrayBuffer',{value:async()=>new TextEncoder().encode('customer_code,customer_name\n001,Toko lama').buffer})
 const input=container.querySelector<HTMLInputElement>('input[type="file"]')!
 await act(async()=>{Object.defineProperty(input,'files',{configurable:true,value:[file]});input.dispatchEvent(new Event('change',{bubbles:true}))});await flush()
}
const writes=()=>client.rpc.mock.calls.filter(([name])=>name==='erp_save_initial_import_action_v1')
describe('connected CSV import',()=>{
 it('uploads actual file bytes, edits before saving and finalizes only after server validation',async()=>{
  const s=server();await mount();await csv();expect(writes()).toHaveLength(0)
  await change(container.querySelector('input[aria-label="Nama pelanggan, baris 2"]')!,'Toko terbaru')
  expect(button('Sahkan data awal').disabled).toBe(true)
  await click('Simpan perubahan draft')
  expect(s.rows[0].payload).toEqual({customer_code:'001',customer_name:'Toko terbaru'})
  await click('Periksa seluruh draft');expect(button('Sahkan data awal').disabled).toBe(false)
  await click('Sahkan data awal');expect(container.textContent).toContain('Sudah disahkan')
  expect(container.querySelector('input[type="file"]')).toBeNull();expect(s.effects).toBe(3)
 })
 it('replays the exact saved envelope after a lost response and remount',async()=>{
  const s=server();await mount();await csv();s.lose=true;await click('Simpan perubahan draft')
  const original=structuredClone(writes()[0][1]);expect(readProductionRecovery('disposable:actor-1').pending.INITIAL_IMPORT?.id).toBe(original.p_client_request_id)
  await act(async()=>root.unmount());root=createRoot(container);s.lose=false
  await act(async()=>root.render(<ConnectedInitialImportPage/>));await flush();await click('Reconcile')
  expect(writes()[1][1]).toEqual(original);expect(s.effects).toBe(1);expect(readProductionRecovery('disposable:actor-1').pending.INITIAL_IMPORT).toBeUndefined()
 })
 it('retains edits but refuses to rebase them silently after stale version rejection',async()=>{
  const s=server();await mount();await csv();s.stale=true;await click('Simpan perubahan draft')
  expect(s.effects).toBe(0);expect(container.textContent).toContain('Draft di server sudah berubah')
  expect(button('Simpan perubahan draft').disabled).toBe(true)
 })
 it('denies unauthorized roles without reading data',async()=>{
  server();const a=structuredClone(recoveryIdentity);a.identity.profile.role='CASHIER';auth.current=a
  await act(async()=>root.render(<ConnectedInitialImportPage/>));expect(client.rpc).not.toHaveBeenCalled();expect(container.textContent).toContain('owner dan admin')
 })
 it('fails closed on malformed response while accepting optional null values',()=>{
  const value={recent:[],batch:{id,code:'A',status:'DRAFT',cutover_at:'2026-09-20T00:00:00Z',revision:rev(1),rows:[{id:rowId,entity:'CUSTOMER',source_row_no:2,payload:{customer_code:'A',address:null},validation_status:'PENDING',errors:[],applied:false}],cash_advances:[],advance_payrolls:[],prepayments:[],prepayment_cash_accounts:[],production_sources:[]}}
  expect(parseInitialImportWorkspace(value).batch?.rows[0].payload.address).toBe('')
  expect(()=>parseInitialImportWorkspace({...value,batch:{...value.batch,revision:'wrong'}})).toThrow()
 })
 it('shows exact cash advance amounts and sends an allocation only for a payroll of that contractor',async()=>{
  const s=server();s.status='POSTED'
  s.cash_advances=[advance()]
  s.advance_payrolls=[{id:rowId,contractor_id:id,payroll_number:'PAY-OWN',row_version:'9007199254740993'}, {id,contractor_id:rowId,payroll_number:'PAY-OTHER',row_version:'1'}]
  await mount()
  expect(container.textContent).toContain('Rp 9007199254740993,01')
  expect(container.textContent).not.toContain('PAY-OTHER')
  await change(container.querySelector('select[aria-label="Payroll untuk kasbon"]')!,rowId)
  await change(container.querySelector('input[aria-label="Nominal alokasi kasbon"]')!,'12,75')
  await click('Simpan alokasi kasbon')
  expect(writes()[0][1].p_action).toBe('ALLOCATE_CASH_ADVANCE')
  expect(writes()[0][1].p_payload).toEqual({batch_id:id,expected_revision:rev(1),balance_id:rowId,payroll_id:rowId,expected_payroll_version:'9007199254740993',amount:'12,75'})
 })
 it('recovers a lost cash advance allocation response with the same request and does not issue it twice',async()=>{
  const s=server();s.status='POSTED';s.cash_advances=[advance()]
  s.advance_payrolls=[{id:rowId,contractor_id:id,payroll_number:'PAY-OWN',row_version:'7'}]
  await mount();await change(container.querySelector('select[aria-label="Payroll untuk kasbon"]')!,rowId)
  await change(container.querySelector('input[aria-label="Nominal alokasi kasbon"]')!,'12.75')
  s.lose=true;await click('Simpan alokasi kasbon');const original=structuredClone(writes()[0][1])
  expect(readProductionRecovery('disposable:actor-1').pending.INITIAL_IMPORT?.action).toBe('ALLOCATE_CASH_ADVANCE')
  expect(button('Simpan alokasi kasbon').disabled).toBe(true)
  await act(async()=>root.unmount());root=createRoot(container);s.lose=false
  await act(async()=>root.render(<ConnectedInitialImportPage/>));await flush();await click('Reconcile')
  expect(writes()[1][1]).toEqual(original);expect(s.effects).toBe(1)
 })
 it('releases draft allocations with zero and locks approved or paid allocations',async()=>{
  const s=server();s.status='POSTED';s.cash_advances=[{...advance(),allocations:[
    {payroll_id:rowId,payroll_number:'PAY-DRAFT',status:'CALCULATED',row_version:'8',amount:'12.75'},
    {payroll_id:id,payroll_number:'PAY-PAID',status:'PAID',row_version:'9',amount:'7.25'},
  ]}]
  await mount();expect(container.textContent).not.toContain('Lepas alokasi PAY-PAID');await click('Lepas alokasi PAY-DRAFT')
  expect(writes()[0][1].p_payload).toMatchObject({balance_id:rowId,payroll_id:rowId,expected_payroll_version:'8',amount:'0'})
 })
 it('refuses malformed, rounded numeric, or negative cash advance state',()=>{
  const wrap=(a:unknown)=>({recent:[],batch:{id,code:'A',status:'POSTED',cutover_at:'2026-09-20T00:00:00Z',revision:rev(1),rows:[],cash_advances:[a],advance_payrolls:[],prepayments:[],prepayment_cash_accounts:[],production_sources:[]}})
  expect(parseInitialImportWorkspace(wrap(advance())).batch?.cash_advances[0].original_amount).toBe('9007199254740993.01')
  expect(()=>parseInitialImportWorkspace(wrap({...advance(),available_amount:'-0.01'}))).toThrow('Saldo kasbon')
  expect(()=>parseInitialImportWorkspace(wrap({...advance(),original_amount:9007199254740993.01}))).toThrow('Saldo kasbon')
 })
 it('applies a prepayment with exact money text, selected target and explicit economic date',async()=>{
  const s=server();s.status='POSTED';s.prepayments=[prepay()];await mount()
  expect(container.textContent).toContain('Rp 9007199254740993,01')
  await change(container.querySelector('select[aria-label="Tagihan untuk uang muka"]')!,id)
  await change(container.querySelector('input[aria-label="Nominal uang muka"]')!,'12,75')
  await change(container.querySelector('input[aria-label="Tanggal uang muka"]')!,'2026-09-21')
  expect(button('Pakai untuk tagihan').disabled).toBe(true)
  await change(container.querySelector('input[aria-label="Alasan uang muka"]')!,'Pakai bukti DP')
  await click('Pakai untuk tagihan')
  expect(writes()[0][1].p_action).toBe('PREPAYMENT')
  expect(writes()[0][1].p_payload).toEqual({batch_id:id,expected_revision:rev(1),advance_id:rowId,operation:'APPLY',target_id:id,amount:'12,75',effective_date:'2026-09-21',reason:'Pakai bukti DP'})
 })
 it('reconciles a lost prepayment response using the original request without a second application',async()=>{
  const s=server();s.status='POSTED';s.prepayments=[prepay()];await mount()
  await change(container.querySelector('select[aria-label="Tagihan untuk uang muka"]')!,id)
  await change(container.querySelector('input[aria-label="Nominal uang muka"]')!,'12.75')
  await change(container.querySelector('input[aria-label="Tanggal uang muka"]')!,'2026-09-21')
  await change(container.querySelector('input[aria-label="Alasan uang muka"]')!,'Apply advance')
  s.lose=true;await click('Pakai untuk tagihan');const original=structuredClone(writes()[0][1])
  expect(button('Pakai untuk tagihan').disabled).toBe(true)
  await act(async()=>root.unmount());root=createRoot(container);s.lose=false
  await act(async()=>root.render(<ConnectedInitialImportPage/>));await flush();await click('Reconcile')
  expect(writes()[1][1]).toEqual(original);expect(s.effects).toBe(1)
 })
 it('requires a cash account for refunds and sends linked reversals only with a reason',async()=>{
  const s=server();s.status='POSTED';s.prepayments=[{...prepay(),payments:[{id,number:'USE-1',status:'POSTED',amount:'12.75'},{id:rowId,number:'OLD-1',status:'REVERSED',amount:'1.00'}]}];s.prepayment_cash_accounts=[{id,name:'Bank'}];await mount()
  expect(button('Batalkan pemakaian USE-1').disabled).toBe(true);expect(container.textContent).not.toContain('Batalkan pemakaian OLD-1')
  await change(container.querySelector('select[aria-label="Tindakan uang muka"]')!,'REFUND')
  await change(container.querySelector('input[aria-label="Nominal uang muka"]')!,'10')
  await change(container.querySelector('input[aria-label="Tanggal uang muka"]')!,'2026-09-21')
  await change(container.querySelector('input[aria-label="Alasan uang muka"]')!,'Kelebihan DP')
  expect(button('Catat pengembalian uang').disabled).toBe(true)
  await change(container.querySelector('select[aria-label="Rekening pengembalian uang muka"]')!,id)
  await click('Catat pengembalian uang')
  expect(writes()[0][1].p_payload).toMatchObject({operation:'REFUND',cash_account_id:id,amount:'10'})
  expect(writes()[0][1].p_payload).not.toHaveProperty('target_id')
  await click('Batalkan pemakaian USE-1')
  expect(writes()[1][1].p_payload).toMatchObject({operation:'REVERSE_PAYMENT',payment_id:id,reason:'Kelebihan DP',expected_revision:rev(2)})
 })
 it('fails closed on malformed prepayment amounts, history or cross-party targets',()=>{
  const p=prepay(),wrap=(entry:unknown)=>({recent:[],batch:{id,code:'A',status:'POSTED',cutover_at:'2026-09-20T00:00:00Z',revision:rev(1),rows:[],cash_advances:[],advance_payrolls:[],prepayments:[entry],prepayment_cash_accounts:[],production_sources:[]}})
  expect(parseInitialImportWorkspace(wrap(p)).batch?.prepayments[0].original_amount).toBe('9007199254740993.01')
  expect(()=>parseInitialImportWorkspace(wrap({...p,remaining_amount:'-0.01'}))).toThrow('Saldo uang muka')
  expect(()=>parseInitialImportWorkspace(wrap({...p,original_amount:1.25}))).toThrow('Saldo uang muka')
  expect(()=>parseInitialImportWorkspace(wrap({...p,targets:[{...p.targets[0],party_id:rowId}]}))).toThrow('Tagihan uang muka')
  expect(()=>parseInitialImportWorkspace(wrap({...p,events:[{id,kind:'CORRECTION',delta:1.25,date:'2026-09-21',reason:'Changed',reversed:false}]}))).toThrow('Riwayat uang muka')
 })
})

function advance() { return {balance_id:rowId,contractor_id:id,contractor_name:'Mandor kasbon',document_number:'KAS-001',original_amount:'9007199254740993.01',settled_before_cutover:'32.75',opening_amount:'67.25',settled_amount:'0.00',remaining_amount:'67.25',reserved_amount:'0.00',available_amount:'67.25',allocations:[]} }
function prepay() { return {id:rowId,party_id:id,party_type:'SUPPLIER',party_name:'Supplier',document_number:'DP-001',original_amount:'9007199254740993.01',settled_before_cutover:'32.75',opening_amount:'67.25',applied_amount:'0.00',refunded_amount:'0.00',remaining_amount:'67.25',targets:[{id,number:'BILL-1',party_id:id,party_type:'SUPPLIER',remaining_amount:'100.00',target_date:'2026-09-20'}],payments:[],events:[]} }


describe('opening WIP continuation',()=>{
 it('sends exact remaining quantity and keeps a lost response locked for recovery',async()=>{
  const s=server();s.status='POSTED';s.production_sources=[{opening_item_id:rowId,batch_id:id,source_key:'WIP-001',po_number:'PO-001',balance_type:'WIP',stage:'SEWING',size_code:'M',qty_pcs:8,completed_qty_pcs:3,remaining_qty_pcs:5,contractor_name:'Epi',vendor_name:null,original_amount:'40.00',current_amount:'48.00',outputs:[]}]
  await mount();expect(container.textContent).toContain('Sisa 5 pcs');expect(button('Sahkan hasil WIP awal').disabled).toBe(true)
  for(const [label,value] of [['Hasil WIP baik','6'],['Produk hasil WIP','SKU-M'],['Merek hasil WIP','  BRAND-B  '],['Gudang hasil WIP','FG-01'],['Tanggal hasil WIP','2026-09-21'],['Catatan hasil WIP','Barang sudah diperiksa']])await change(container.querySelector(`input[aria-label="${label}"]`)!,value)
  expect(button('Sahkan hasil WIP awal').disabled).toBe(true)
  await change(container.querySelector('input[aria-label="Hasil WIP baik"]')!,'4');s.lose=true;await click('Sahkan hasil WIP awal')
  const sent=writes()[0][1];expect(sent.p_action).toBe('WIP_OUTPUT');expect(sent.p_payload).toMatchObject({opening_item_id:rowId,expected_remaining:'5',qty_pcs:'4',product_sku:'SKU-M',brand_code:'BRAND-B',location_code:'FG-01',date:'2026-09-21',operation:'COMPLETE'})
  expect(readProductionRecovery('disposable:actor-1').pending.INITIAL_IMPORT?.id).toBe(sent.p_client_request_id)
  expect(button('Sahkan hasil WIP awal').disabled).toBe(true)
  s.lose=false;await click('Reconcile');expect(writes()[1][1]).toEqual(sent);expect(s.effects).toBe(1)
 })
 it.each(['cash_advances','advance_payrolls','prepayments','prepayment_cash_accounts','production_sources'])('refuses a batch whose %s collection is missing instead of reading none',field=>{
  const batch:Record<string,unknown>={id,code:'A',status:'POSTED',cutover_at:'2026-09-20T00:00:00Z',revision:rev(1),rows:[],cash_advances:[],advance_payrolls:[],prepayments:[],prepayment_cash_accounts:[],production_sources:[]}
  expect(parseInitialImportWorkspace({recent:[],batch}).batch?.production_sources).toEqual([])
  Reflect.deleteProperty(batch,field)
  expect(()=>parseInitialImportWorkspace({recent:[],batch})).toThrow('tidak terbaca lengkap')
 })
})
describe('every editable import batch stays selectable (CP6-04)',()=>{
 it('lists 60 batches and finds the oldest draft by search',async()=>{
  const recent=Array.from({length:60},(_,n)=>({id:`00000000-0000-4000-8000-${String(n).padStart(12,'0')}`,batch_code:`AWAL-${String(n).padStart(2,'0')}`,status:'DRAFT'}))
  client.rpc.mockImplementation(async(name:string,args:Record<string,unknown>)=>{
   if(name!=='erp_get_initial_import_workspace_v1')throw new Error('Unexpected RPC '+name)
   const b=recent.find(r=>r.id===args.p_batch_id)
   return {data:{recent,batch:b?{id:b.id,code:b.batch_code,status:'DRAFT',cutover_at:'2026-09-20T00:00:00+07:00',revision:rev(1),rows:[],cash_advances:[],advance_payrolls:[],prepayments:[],prepayment_cash_accounts:[],production_sources:[]}:null},error:null}
  })
  await act(async()=>root.render(<ConnectedInitialImportPage/>));await flush()
  const select=container.querySelector<HTMLSelectElement>('select[aria-label="Batch impor"]')!
  expect(select.options).toHaveLength(61)
  await change(container.querySelector<HTMLInputElement>('input[aria-label="Cari batch impor"]')!,'awal-59')
  expect([...select.options].map(o=>o.textContent)).toEqual(['Buat batch baru','AWAL-59 · DRAFT'])
  await change(select,recent[59].id)
  expect(client.rpc.mock.calls.at(-1)?.[1]).toEqual({p_batch_id:recent[59].id})
  expect(container.textContent).toContain('AWAL-59')
 })

 const bb=()=>({opening_balances:[{balance_id:rowId,balance_type:'SUPPLIER_PAYABLE',source_kind:'BALANCE',source_mode:'DOCUMENT',party_type:'SUPPLIER',party_id:id,party_code:'SUP',party_name:'Supplier Lama',
   document_number:'INV-9',document_date:'2026-08-01',due_date:null,cutover_date:'2026-09-20',original_amount:'100.00',settled_before_cutover:'35.00',opening_amount:'65.00',settled_amount:'0.00',
   reserved_amount:'0.00',remaining_amount:'65.00',available_amount:'65.00',status:'OPEN',settlements:[],payroll_lines:[]}],
  opening_payable_payrolls:[],legacy_documents:[],customer_credits:[],sale_return_rights:[],fg_locations:[],purchase_commitments:[],payroll_entitlements:[],entitlement_payrolls:[],opening_reworks:[]})
 it('BB: pays an opening payable once with its cash account and exact amount; history before cutover stays history',async()=>{
  const s=server();s.status='POSTED';s.bb=bb();s.prepayment_cash_accounts=[{id:rowId,name:'Bank BCA'}]
  await mount();expect(container.textContent).toContain('Pelunasan saldo awal');expect(container.textContent).toContain('Rp 35,00')
  expect(button('Bayar').disabled).toBe(true)
  await change(container.querySelector('select[aria-label="Rekening pelunasan"]')!,rowId)
  for(const [label,value] of [['Nominal saldo awal','20,50'],['Tanggal pelunasan saldo awal','2026-09-22'],['Alasan pelunasan saldo awal','Transfer sebagian']])await change(container.querySelector(`input[aria-label="${label}"]`)!,value)
  await click('Bayar')
  const sent=writes()[0][1];expect(sent.p_action).toBe('OPENING_SETTLEMENT')
  expect(sent.p_payload).toMatchObject({operation:'SETTLE',balance_id:rowId,amount:'20.50',effective_date:'2026-09-22',cash_account_id:rowId,reason:'Transfer sebagian',expected_revision:rev(1)})
 })
 it('BB: cut pieces waiting at cutover are picked up first; no completion is offered before the pickup',async()=>{
  const s=server();s.status='POSTED';s.bb=bb()
  s.production_sources=[{opening_item_id:rowId,batch_id:id,source_key:'WIP-C',po_number:'PO-C',balance_type:'WIP',stage:'CUTTING',size_code:'M',qty_pcs:8,completed_qty_pcs:0,remaining_qty_pcs:8,
   contractor_name:null,vendor_name:null,original_amount:'40.00',current_amount:'40.00',outputs:[],current_stage:'CUTTING',location_code:'MEJA-1',bb:{pickup:null,split_qty_pcs:0,splits:[]}}]
  await mount();expect(container.textContent).toContain('Menunggu pickup di lokasi MEJA-1');expect(()=>button('Sahkan hasil WIP awal')).toThrow()
  for(const [label,value] of [['Mandor pickup','EPI'],['Tanggal pickup','2026-09-21'],['Catatan pickup','Diambil mandor']])await change(container.querySelector(`input[aria-label="${label}"]`)!,value)
  await click('Catat pickup')
  expect(writes()[0][1].p_payload).toMatchObject({operation:'PICKUP',contractor_code:'EPI',date:'2026-09-21',opening_item_id:rowId,expected_remaining:'8'})
 })
 it('BB: a split BS reduces the remaining pieces and can be undone only while untouched',async()=>{
  const s=server();s.status='POSTED';s.bb=bb()
  s.production_sources=[{opening_item_id:rowId,batch_id:id,source_key:'WIP-S',po_number:'PO-S',balance_type:'WIP',stage:'SEWING',size_code:'M',qty_pcs:8,completed_qty_pcs:0,remaining_qty_pcs:6,
   contractor_name:'Epi',vendor_name:null,original_amount:'40.00',current_amount:'40.00',outputs:[],current_stage:'SEWING',location_code:null,
   bb:{pickup:null,split_qty_pcs:2,splits:[{id:rowId,bs_case_id:id,bs_number:'OWBS-1',bs_status:'OPEN',qty_pcs:2,stage_from:'SEWING',date:'2026-09-22',reversed:false,resolved_qty_pcs:0}]}}]
  await mount();expect(container.textContent).toContain('Dipisah BS 2 pcs')
  await change(container.querySelector('input[aria-label="Catatan hasil WIP"]')!,'Salah pisah')
  await click('Batalkan pisah BS 2026-09-22')
  expect(writes()[0][1].p_payload).toMatchObject({operation:'REVERSE_SPLIT',split_id:rowId,expected_remaining:'6'})
 })
 it('BB: continuations are all present or all absent; a partial set is an incomplete read',()=>{
  const batch:Record<string,unknown>={id,code:'A',status:'POSTED',cutover_at:'2026-09-20T00:00:00Z',revision:rev(1),rows:[],cash_advances:[],advance_payrolls:[],prepayments:[],prepayment_cash_accounts:[],production_sources:[]}
  expect(parseInitialImportWorkspace({recent:[],batch}).batch?.bb).toBeNull()
  expect(parseInitialImportWorkspace({recent:[],batch:{...batch,...bb()}}).batch?.bb?.opening_balances[0].remaining_amount).toBe('65.00')
  const partial:Record<string,unknown>={...batch,...bb()};delete partial.opening_reworks
  expect(()=>parseInitialImportWorkspace({recent:[],batch:partial})).toThrow('tidak terbaca lengkap')
  expect(()=>parseInitialImportWorkspace({recent:[],batch:{...batch,...bb(),opening_balances:[{...bb().opening_balances[0],remaining_amount:65}]}})).toThrow()
 })
 it('BB: a WIP whose remaining plus completed plus split pieces is not its quantity is refused',()=>{
  const source={opening_item_id:rowId,batch_id:id,source_key:'W',po_number:'P',balance_type:'WIP',stage:'SEWING',size_code:'M',qty_pcs:8,completed_qty_pcs:0,remaining_qty_pcs:8,
   contractor_name:'Epi',vendor_name:null,outputs:[],current_stage:'SEWING',location_code:null,bb:{pickup:null,split_qty_pcs:2,splits:[{id:rowId,bs_case_id:id,bs_number:'B',bs_status:'OPEN',qty_pcs:2,stage_from:'SEWING',date:'2026-09-22',reversed:false,resolved_qty_pcs:0}]}}
  expect(()=>parseInitialProductionSources([source])).toThrow('tidak cocok')
  expect(parseInitialProductionSources([{...source,remaining_qty_pcs:6}])[0].bb?.split_qty_pcs).toBe(2)
  expect(()=>parseInitialProductionSources([{...source,stage:'CUTTING',current_stage:'SEWING',remaining_qty_pcs:6}])).toThrow()
 })
})