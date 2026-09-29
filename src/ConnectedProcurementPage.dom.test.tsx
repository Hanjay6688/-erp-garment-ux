// @vitest-environment jsdom
import { act } from 'react'
import { createRoot, type Root } from 'react-dom/client'
import { beforeEach, afterEach, describe, expect, it, vi } from 'vitest'
import ConnectedProcurementPage from './ConnectedProcurementPage'
import { parseProcurementWorkspace, receiptDecimal } from './procurementContract'
import { recoveryIdentity } from '../tests/fixtures/productionRecovery'
import { readProductionRecovery } from './productionRecovery'
import { invoiceWorkspaceFixture } from '../tests/fixtures/purchaseInvoices'
import { supplierReturnsFixture } from '../tests/fixtures/supplierReturns'
const state = vi.hoisted(() => ({ auth: null as unknown }))
const client = vi.hoisted(() => ({ rpc: vi.fn() }))
vi.mock('./auth/AuthProvider', () => ({ useAuth: () => state.auth }))
vi.mock('./lib/supabase', () => ({ getUatSupabaseClient: () => client }))
const id = '11111111-1111-4111-8111-111111111111', doc = '22222222-2222-4222-8222-222222222222'
function workspace(finance = true, posted = false) {
  const row = { id: doc, purchase_number: 'SJ-TEST', supplier_id: id, supplier_name: 'Supplier A', location_id: id, location_name: 'Gudang kain', physical_at: '2026-09-26T03:00:00+00:00', status: posted ? 'POSTED' : 'DRAFT', row_version: posted ? '9007199254740994' : '9007199254740993', notes: null, line_count: 1,
    ...(finance ? { finance: { supplier_invoice_number: null, due_date: null, payment_status: 'UNPAID', receipt_value: '100.000000', basis: 'RECEIPT_PRICE_NOT_CURRENT_PAYABLE' } } : {}) }
  return { contract_version: 'cp7.procurement-workspace.v1', kind: 'LIVE_WORKSPACE', read_at: '2026-09-29T03:00:00Z', capabilities: { create: true, post: true, view_value: finance }, page: { rows: [row], total: '1', offset: 0, limit: 25, next_offset: null }, detail: null as unknown,
    makeDetail: () => ({ ...row, stock_effect: posted ? 'POSTED_RECEIPT' : 'NOT_POSTED', quantity_basis: 'RECEIPT_DOCUMENT_NOT_CURRENT_ON_HAND', items: [{ id, material_id: id, material_sku: 'K-1', material_name: 'Denim', material_type: 'FABRIC', unit_code: 'YD', qty: '10.000000', purchase_qty_entered: null, purchase_uom_code: null, purchase_uom_factor: null, lot_number: null, notes: null, rolls: [{ id, roll_number: 'ROLL-1', receipt_qty: '10.000000', notes: null }], ...(finance ? { finance: { unit_price: '10.000000', line_total: '100.000000', price_state: 'ESTIMATED', price_source: 'MANUAL_ESTIMATE', invoice_match_state: 'UNMATCHED', benchmark_price_version_id: null } } : {}) }] }) }
}
let root: Root, container: HTMLDivElement
beforeEach(() => {
  Object.assign(globalThis, { IS_REACT_ACT_ENVIRONMENT: true }); localStorage.clear(); client.rpc.mockReset()
  const a = structuredClone(recoveryIdentity); a.identity.permissions.push('warehouse.procurement.view','warehouse.procurement.create','warehouse.procurement.post','finance.ap.view'); state.auth = a
  Object.defineProperty(navigator,'locks',{ configurable:true,value:{ request:async (_n:string,_o:unknown,fn:(l:unknown)=>Promise<unknown>)=>fn({}) } })
  container = document.createElement('div'); document.body.append(container); root = createRoot(container)
})
afterEach(async () => { await act(async () => root.unmount()); container.remove(); localStorage.clear(); Reflect.deleteProperty(navigator,'locks'); vi.restoreAllMocks() })
async function flush() { await act(async () => { await new Promise(r => setTimeout(r,0)) }) }
async function mount() { await act(async () => root.render(<ConnectedProcurementPage/>)); await flush() }
function button(text:string) { const b=[...container.querySelectorAll('button')].find(b=>b.textContent?.includes(text)); if(!b)throw Error('Missing '+text);return b }
async function click(text:string) { await act(async()=>button(text).click());await flush() }
const writes=()=>client.rpc.mock.calls.filter(([name])=>name==='erp_cp7_save_procurement_v1')
function server(finance=true) {
  const s={lose:false,failReload:false,posted:false,effects:0,wrong:false};const cache=new Map<string,unknown>()
  client.rpc.mockImplementation(async(name:string,args:Record<string,unknown>)=>{
    if(name==='erp_cp7_get_procurement_v1') {
      if(s.failReload&&s.posted)return {data:null,error:{message:'Read unavailable'}}
      const { makeDetail,...w }=workspace(finance,s.posted); if((args.p_query as Record<string,unknown>).purchase_id)w.detail=makeDetail()
      return {data:w,error:null}
    }
    if(name==='erp_cp7_get_procurement_options_v1')return {data:{contract_version:'cp7.procurement-options.v1',kind:args.p_kind,rows:[],total:'0',offset:0,limit:25,next_offset:null},error:null}
    if(name==='erp_cp7_get_supplier_returns_v1')return {data:supplierReturnsFixture(null,finance),error:null}
    if(name==='erp_cp7_get_purchase_invoices_v1')return {data:{...invoiceWorkspaceFixture(false),purchase_status:s.posted?'POSTED':'DRAFT'},error:null}
    if(name!=='erp_cp7_save_procurement_v1')throw Error('Unexpected RPC '+name)
    const key=String(args.p_request)
    if(!cache.has(key)){s.effects++;s.posted=args.p_action==='POST';cache.set(key,{contract_version:'cp7.procurement-outcome.v1',kind:'COMMITTED_OUTCOME',action:args.p_action,request_id:key,purchase_id:doc,status:s.posted?'POSTED':'DRAFT',row_version:'9007199254740994'})}
    return s.lose?{data:null,error:{status:503,message:'Lost reply'}}:{data:s.wrong?{ok:true}:cache.get(key),error:null}
  });return s
}
describe('connected procurement recovery and financial boundary',()=>{
  it('posts the exact reviewed revision then reloads the receipt rather than inventing stock',async()=>{
    server();await mount();await click('SJ-TEST');expect(container.textContent).toContain('Belum menambah stok gudang')
    await click('Sahkan penerimaan ke gudang')
    expect(writes()).toHaveLength(1);expect(writes()[0][1].p_expected).toBe('9007199254740993')
    expect(container.textContent).toContain('Penerimaan sudah tercatat');expect(container.querySelector('.cproc-detail .cproc-review')).toBeNull()
    expect(readProductionRecovery('disposable:actor-1').pending.PROCUREMENT).toBeUndefined()
  })
  it('reuses the persisted UUID and exact payload after a lost reply and remount',async()=>{
    const s=server();await mount();await click('SJ-TEST');s.lose=true;await click('Sahkan penerimaan ke gudang')
    const sent=structuredClone(writes()[0][1]);expect(readProductionRecovery('disposable:actor-1').pending.PROCUREMENT?.id).toBe(sent.p_request)
    await act(async()=>root.unmount());root=createRoot(container);s.lose=false;await mount();await click('Reconcile')
    expect(writes()[1][1]).toEqual(sent);expect(s.effects).toBe(1);expect(readProductionRecovery('disposable:actor-1').pending.PROCUREMENT).toBeUndefined()
  })
  it('retires the committed form when reload fails and refuses another post',async()=>{
    const s=server();await mount();await click('SJ-TEST');const old=button('Sahkan penerimaan');s.failReload=true;await click('Sahkan penerimaan')
    expect(container.textContent).toContain('Aksi sudah tersimpan');expect(container.querySelector('.cproc-detail .cproc-review')).toBeNull()
    await act(async()=>old.click());expect(writes()).toHaveLength(1)
    s.failReload=false;await click('Muat ulang');expect(container.textContent).toContain('Penerimaan sudah tercatat')
  })
  it('retains an uncertain outcome when a success body lacks matching identity',async()=>{
    const s=server();await mount();await click('SJ-TEST');s.wrong=true;await click('Sahkan penerimaan')
    expect(readProductionRecovery('disposable:actor-1').pending.PROCUREMENT).toBeTruthy()
    expect(button('Sahkan penerimaan').disabled).toBe(true)
  })
  it('never displays finance for operations and rejects unexpected money in its DTO',async()=>{
    const a=state.auth as typeof recoveryIdentity;a.identity.permissions=a.identity.permissions.filter(k=>k!=='finance.ap.view')
    server(false);await mount();await click('SJ-TEST');expect(container.textContent).not.toContain('Rp100');expect(container.querySelector('.cproc-total')).toBeNull()
    const {makeDetail,...w}=workspace(false);w.detail=makeDetail();expect(()=>parseProcurementWorkspace(w,false)).not.toThrow()
    expect(()=>parseProcurementWorkspace({...w,private_cost:'9'},false)).toThrow()
    ;(w.detail as Record<string,unknown>).finance={receipt_value:'9'};expect(()=>parseProcurementWorkspace(w,false)).toThrow()
  })
  it('reads native PARTIAL invoice pricing without treating the receipt as malformed',()=>{
    const {makeDetail,...w}=workspace(true,true);const d=makeDetail();d.items[0].finance!.price_state='PARTIAL';d.items[0].finance!.invoice_match_state='PARTIAL';w.detail=d
    expect(()=>parseProcurementWorkspace(w,true)).not.toThrow()
  })
  for(const loseReply of [false,true])it(`keeps the receipt and partial invoice together after ${loseReply?'lost reply recovery':'finalization'}`,async()=>{
    const s=server();s.posted=true;const original=client.rpc.getMockImplementation()!
    let invoiced=false,lose=loseReply,effects=0;const cache=new Map<string,unknown>()
    client.rpc.mockImplementation(async(name:string,args:Record<string,unknown>)=>{
      if(name==='erp_cp7_save_purchase_invoice_v1'){
        const key=String(args.p_request)
        if(!cache.has(key)){invoiced=true;effects++;cache.set(key,{contract_version:'cp7.purchase-invoice-outcome.v1',kind:'COMMITTED_OUTCOME',action:'FINALIZE',request_id:key,purchase_id:doc,invoice_id:'33333333-3333-4333-8333-333333333333',version_subject:'RECEIPT',row_version:'9007199254740995',status:'POSTED'})}
        return lose?{data:null,error:{status:503,message:'Lost committed invoice reply'}}:{data:cache.get(key),error:null}
      }
      if(name==='erp_cp7_get_purchase_invoices_v1')return {data:invoiceWorkspaceFixture(invoiced),error:null}
      const r=await original(name,args)
      if(name==='erp_cp7_get_procurement_v1'&&invoiced){
        for(const row of [...r.data.page.rows,...(r.data.detail?[r.data.detail]:[])])row.row_version='9007199254740995'
        if(r.data.detail){r.data.detail.items[0].finance.price_state='PARTIAL';r.data.detail.items[0].finance.invoice_match_state='PARTIAL'}
      }
      return r
    })
    await mount();await click('SJ-TEST');await click('Catat invoice supplier')
    for(const [label,value] of [['Nomor invoice supplier','INV-TEST'],['Jumlah invoice 1','4'],['Harga invoice 1','12.5']]){
      const input=container.querySelector<HTMLInputElement>(`[aria-label="${label}"]`)!
      await act(async()=>{Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value')!.set!.call(input,value);input.dispatchEvent(new Event('input',{bubbles:true}))});await flush()
    }
    await act(async()=>container.querySelector<HTMLInputElement>('[aria-label="Invoice sudah diperiksa"]')!.click());await flush();await click('Sahkan invoice supplier')
    const invoiceWrites=()=>client.rpc.mock.calls.filter(([name])=>name==='erp_cp7_save_purchase_invoice_v1')
    const first=structuredClone(invoiceWrites()[0][1])
    if(loseReply){
      expect(readProductionRecovery('disposable:actor-1').pending.PURCHASE_INVOICE?.id).toBe(first.p_request)
      await act(async()=>root.unmount());root=createRoot(container);lose=false;await mount();await click('Reconcile transaksi')
      expect(invoiceWrites()[1][1]).toEqual(first)
    }
    expect(effects).toBe(1);expect(readProductionRecovery('disposable:actor-1').pending.PURCHASE_INVOICE).toBeUndefined()
    expect(container.querySelector('.cproc-detail')?.textContent).toContain('SJ-TEST')
    expect(container.querySelector('.cproc-detail')?.textContent).toContain('invoice sebagian')
    expect(container.querySelector('.cproc-invoices')?.textContent).toContain('Nilai dokumen Rp50')
    expect(container.querySelector('.cproc-invoices')?.textContent).not.toContain('Pilih penerimaan')
  })
  it('rejects partial pagination and keeps exact decimal input without rounding',()=>{
    const {makeDetail:_,...w}=workspace();expect(()=>parseProcurementWorkspace({...w,page:{...w.page,total:'2'}},true)).toThrow()
    expect(receiptDecimal('1,123456',true)).toBe('1.123456');expect(receiptDecimal('1.1234567',true)).toBeNull();expect(receiptDecimal('0')).toBe('0');expect(receiptDecimal('0',true)).toBeNull()
  })
  it('preserves invoice, line, roll and exact physical-time metadata when editing a draft',async()=>{
    server();const original=client.rpc.getMockImplementation()!
    client.rpc.mockImplementation(async(name:string,args:Record<string,unknown>)=>{
      const r=await original(name,args)
      if(name==='erp_cp7_get_procurement_v1'&&r.data?.detail){const d=r.data.detail;d.physical_at='2026-09-26T03:00:27.123+00:00';d.finance.supplier_invoice_number='INV-KEEP';d.finance.due_date='2026-10-15';d.items[0].lot_number='LOT-KEEP';d.items[0].notes='LINE-KEEP';d.items[0].rolls[0].notes='ROLL-KEEP'}
      return r
    })
    await mount();await click('SJ-TEST');await click('Perbaiki draft')
    const input=container.querySelector<HTMLInputElement>('[aria-label="Alasan pencatatan penerimaan"]')!
    await act(async()=>{Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value')!.set!.call(input,'Koreksi catatan');input.dispatchEvent(new Event('input',{bubbles:true}))});await flush();await click('Simpan draft penerimaan')
    const payload=writes()[0][1].p_payload
    expect(payload).toMatchObject({supplier_invoice_number:'INV-KEEP',due_date:'2026-10-15',physical_at:'2026-09-26T03:00:27.123+00:00',lines:[{lot_number:'LOT-KEEP',notes:'LINE-KEEP',rolls:[{notes:'ROLL-KEEP'}]}]})
  })
})
