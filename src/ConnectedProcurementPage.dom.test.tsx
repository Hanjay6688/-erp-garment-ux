// @vitest-environment jsdom
import { act } from 'react'
import { createRoot, type Root } from 'react-dom/client'
import { beforeEach, afterEach, describe, expect, it, vi } from 'vitest'
import ConnectedProcurementPage from './ConnectedProcurementPage'
import { parseProcurementOutcome, parseProcurementUom, parseProcurementWorkspace, receiptDecimal, moneyDecimal } from './procurementContract'
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
  return { contract_version: 'cp7.procurement-workspace.v1', kind: 'LIVE_WORKSPACE', read_at: '2026-09-29T03:00:00Z', capabilities: { create: true, post: true, reverse: finance, view_value: finance }, page: { rows: [row], total: '1', offset: 0, limit: 25, next_offset: null }, detail: null as unknown,
    makeDetail: () => ({ ...row, stock_effect: posted ? 'POSTED_RECEIPT' : 'NOT_POSTED', quantity_basis: 'RECEIPT_DOCUMENT_NOT_CURRENT_ON_HAND', items: [{ id, material_id: id, material_sku: 'K-1', material_name: 'Denim', material_type: 'FABRIC', unit_code: 'YD', qty: '10.000000', purchase_qty_entered: null, purchase_uom_code: null, purchase_uom_factor: null, lot_number: null, notes: null, rolls: [{ id, roll_number: 'ROLL-1', receipt_qty: '10.000000', notes: null }], ...(finance ? { finance: { unit_price: '10.000000', line_total: '100.000000', price_state: 'ESTIMATED', price_source: 'MANUAL_ESTIMATE', invoice_match_state: 'UNMATCHED', benchmark_price_version_id: null, purchase_price_per_uom: null } } : {}) }] }) }
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
  const s={lose:false,failReload:false,posted:false,reversed:false,effects:0,wrong:false,readAt:'2026-09-29T03:00:00Z'};const cache=new Map<string,unknown>()
  client.rpc.mockImplementation(async(name:string,args:Record<string,unknown>)=>{
    if(name==='erp_cp7_get_procurement_v1') {
      if(s.failReload&&s.posted)return {data:null,error:{message:'Read unavailable'}}
      const { makeDetail,...w }=workspace(finance,s.posted); if((args.p_query as Record<string,unknown>).purchase_id)w.detail=makeDetail()
      w.read_at=s.readAt
      if(s.reversed){w.page.rows[0].status='REVERSED';w.page.rows[0].row_version='9007199254740995';if(w.detail)Object.assign(w.detail,{status:'REVERSED',stock_effect:'REVERSED_RECEIPT',row_version:'9007199254740995'})}
      return {data:w,error:null}
    }
    if(name==='erp_cp7_get_procurement_options_v1')return {data:{contract_version:'cp7.procurement-options.v1',kind:args.p_kind,rows:[],total:'0',offset:0,limit:25,next_offset:null},error:null}
    if(name==='erp_cp7_get_supplier_returns_v1')return {data:supplierReturnsFixture(null,finance),error:null}
    if(name==='erp_cp7_get_purchase_invoices_v1')return {data:{...invoiceWorkspaceFixture(false),purchase_status:s.posted?'POSTED':'DRAFT'},error:null}
    if(name!=='erp_cp7_save_procurement_v1')throw Error('Unexpected RPC '+name)
    const key=String(args.p_request)
    if(!cache.has(key)){s.effects++;s.reversed=args.p_action==='REVERSE';s.posted=args.p_action!=='SAVE_DRAFT';cache.set(key,{contract_version:'cp7.procurement-outcome.v1',kind:'COMMITTED_OUTCOME',action:args.p_action,request_id:key,purchase_id:doc,status:s.reversed?'REVERSED':s.posted?'POSTED':'DRAFT',row_version:s.reversed?'9007199254740995':'9007199254740994'})}
    return s.lose?{data:null,error:{status:503,message:'Lost reply'}}:{data:s.wrong?{ok:true}:cache.get(key),error:null}
  });return s
}
describe('connected procurement recovery and financial boundary',()=>{
  function accessoryServer(){
    server();const original=client.rpc.getMockImplementation()!,control={fail:false,wrong:false}
    client.rpc.mockImplementation(async(name:string,args:Record<string,unknown>)=>{
      if(name==='erp_cp7_get_procurement_uom_v1')return control.fail?{data:null,error:{message:'Master tidak tersedia'}}:{data:{contract_version:'cp7.procurement-uom.v1',material_id:control.wrong?doc:id,physical_at:args.p_at,base_unit:'PCS',rows:[{code:'PCS',name:'Piece',factor:'1',dimension:'COUNT'},{code:'LUSIN',name:'Lusin',factor:'12',dimension:'COUNT'},{code:'GROSS',name:'Gross',factor:'144',dimension:'COUNT'}]},error:null}
      const r=await original(name,args)
      if(name==='erp_cp7_get_procurement_v1'&&r.data.detail){const i=r.data.detail.items[0];Object.assign(i,{material_type:'ACCESSORY',unit_code:'PCS',qty:'24.000000',purchase_qty_entered:'2.000000',purchase_uom_code:'LUSIN',purchase_uom_factor:'12.000000',rolls:[]});i.finance.purchase_price_per_uom='120.000000';i.finance.line_total='240.000000'}
      return r
    });return control
  }
  async function fill(label:string,value:string){const input=container.querySelector<HTMLInputElement>(`[aria-label="${label}"]`)!;await act(async()=>{Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value')!.set!.call(input,value);input.dispatchEvent(new Event('input',{bubbles:true}))});await flush()}
  it('edits an accessory receipt using entered quantity and price per purchase unit without client conversion',async()=>{
    accessoryServer();await mount();await click('SJ-TEST');expect(container.querySelector('.cproc-detail')?.textContent).toContain('Rp120 / LUSIN');await click('Perbaiki draft')
    expect(container.querySelector<HTMLInputElement>('[aria-label="Jumlah barang 1"]')!.value).toBe('2.000000');expect(container.querySelector<HTMLInputElement>('[aria-label="Harga barang 1"]')!.value).toBe('120.000000')
    await fill('Alasan pencatatan penerimaan','Periksa jumlah sesuai lusin');await click('Simpan draft penerimaan')
    expect(writes()[0][1].p_payload.lines[0]).toMatchObject({purchase_qty_entered:'2.000000',purchase_uom_code:'LUSIN',purchase_price_per_uom_snapshot:'120.000000',rolls:[]})
    for(const key of ['qty','unit_price','purchase_uom_factor_snapshot'])expect(writes()[0][1].p_payload.lines[0]).not.toHaveProperty(key)
  })
  it('clears quantity and price when switching purchase unit so old values are not reinterpreted',async()=>{
    accessoryServer();await mount();await click('SJ-TEST');await click('Perbaiki draft');await fill('Alasan pencatatan penerimaan','Supplier memakai gross')
    const select=container.querySelector<HTMLSelectElement>('[aria-label="Satuan pembelian 1"]')!;await act(async()=>{select.value='GROSS';select.dispatchEvent(new Event('change',{bubbles:true}))});await flush()
    expect(container.querySelector<HTMLInputElement>('[aria-label="Jumlah barang 1"]')!.value).toBe('');expect(container.querySelector<HTMLInputElement>('[aria-label="Harga barang 1"]')!.value).toBe('');expect(button('Simpan draft penerimaan').disabled).toBe(true)
    await fill('Jumlah barang 1','0,5');await fill('Harga barang 1','1440');await click('Simpan draft penerimaan')
    expect(writes()[0][1].p_payload.lines[0]).toMatchObject({purchase_qty_entered:'0.5',purchase_uom_code:'GROSS',purchase_price_per_uom_snapshot:'1440'})
  })
  it('blocks missing or mismatched unit masters and allows an explicit current read retry',async()=>{
    const c=accessoryServer();c.fail=true;await mount();await click('SJ-TEST');await click('Perbaiki draft');await fill('Alasan pencatatan penerimaan','Periksa master')
    expect(button('Simpan draft penerimaan').disabled).toBe(true);expect(container.textContent).toContain('Master tidak tersedia')
    c.fail=false;c.wrong=true;await click('Muat ulang satuan');expect(button('Simpan draft penerimaan').disabled).toBe(true)
    c.wrong=false;await click('Muat ulang satuan');expect(button('Simpan draft penerimaan').disabled).toBe(false);expect(writes()).toHaveLength(0)
  })
  it('rejects wrong dated unit rows, duplicate codes, or non-unit base factors',()=>{
    const material={id,code:'ACC',name:'Kancing',unit_code:'PCS'},at='2026-09-26T03:00:00Z',row={code:'PCS',name:'Piece',factor:'1',dimension:'COUNT'},w={contract_version:'cp7.procurement-uom.v1',material_id:id,physical_at:at,base_unit:'PCS',rows:[row]}
    expect(()=>parseProcurementUom(w,material,at)).not.toThrow()
    for(const bad of [{...w,physical_at:'2026-09-27T03:00:00Z'},{...w,rows:[row,row]},{...w,rows:[{...row,factor:'12'}]}])expect(()=>parseProcurementUom(bad,material,at)).toThrow()
  })
  async function reviewReverse(){
    await click('Tinjau pembatalan penerimaan')
    const input=container.querySelector<HTMLInputElement>('[aria-label="Alasan pembatalan penerimaan"]')!
    await act(async()=>{Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value')!.set!.call(input,'Penerimaan tercatat ganda');input.dispatchEvent(new Event('input',{bubbles:true}))});await flush()
    expect(button('Batalkan penerimaan').disabled).toBe(true)
    await act(async()=>container.querySelector<HTMLInputElement>('[aria-label="Pembatalan penerimaan sudah diperiksa"]')!.click());await flush()
  }
  for(const lost of [false,true])it(`reverses the reviewed exact revision with ${lost?'persisted recovery after lost reply':'explicit confirmation'}`,async()=>{
    const s=server();s.posted=true;await mount();await click('SJ-TEST');await reviewReverse();s.lose=lost;await click('Batalkan penerimaan')
    const first=structuredClone(writes()[0][1]);expect(first).toMatchObject({p_action:'REVERSE',p_expected:'9007199254740994',p_payload:{purchase_id:doc,change_reason:'Penerimaan tercatat ganda'}})
    if(lost){expect(readProductionRecovery('disposable:actor-1').pending.PROCUREMENT?.id).toBe(first.p_request);await act(async()=>root.unmount());root=createRoot(container);s.lose=false;await mount();await click('Reconcile');expect(writes()[1][1]).toEqual(first)}
    expect(s.effects).toBe(1);expect(container.querySelector('.cproc-detail')?.textContent).toContain('Penerimaan sudah dibatalkan');expect(readProductionRecovery('disposable:actor-1').pending.PROCUREMENT).toBeUndefined()
  })
  it('invalidates a reversal review after a fresh read and retires it before a failed committed reload',async()=>{
    const s=server();s.posted=true;await mount();await click('SJ-TEST');await reviewReverse();s.readAt='2026-09-29T03:00:01Z';await click('Muat ulang')
    expect(container.textContent).toContain('Data penerimaan telah dimuat ulang');expect(container.querySelector('fieldset:disabled')).not.toBeNull();await click('Batalkan penerimaan');expect(writes()).toHaveLength(0)
    await click('Tutup pemeriksaan pembatalan');await reviewReverse();s.failReload=true;await click('Batalkan penerimaan')
    expect(writes()).toHaveLength(1);expect(container.querySelector('[aria-label="Pembatalan penerimaan sudah diperiksa"]')).toBeNull();expect(container.textContent).toContain('Aksi sudah tersimpan')
  })
  it('requires reversal identity and status and rejects unknown action outcomes',()=>{
    const request='44444444-4444-4444-8444-444444444444',p={purchase_id:doc},r={contract_version:'cp7.procurement-outcome.v1',kind:'COMMITTED_OUTCOME',action:'REVERSE',request_id:request,purchase_id:doc,status:'REVERSED',row_version:'9007199254740995'}
    expect(()=>parseProcurementOutcome(r,request,'REVERSE',p)).not.toThrow()
    for(const bad of [{...r,purchase_id:id},{...r,status:'POSTED'},{...r,action:'OTHER',status:'POSTED'}])expect(()=>parseProcurementOutcome(bad,request,String(bad.action),p)).toThrow()
  })
  it('posts the exact reviewed revision then reloads the receipt rather than inventing stock',async()=>{
    server();await mount();await click('SJ-TEST');expect(container.textContent).toContain('Belum menambah stok gudang')
    await click('Sahkan penerimaan ke gudang')
    expect(writes()).toHaveLength(1);expect(writes()[0][1].p_expected).toBe('9007199254740993')
    expect(container.textContent).toContain('Penerimaan sudah tercatat');expect(container.querySelector('[aria-label="Catatan pemeriksaan penerimaan"]')).toBeNull()
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
    // A rupiah value typed with a thousands separator is refused, not read as 16 or 1.5.
    expect(moneyDecimal('16.000')).toBeNull();expect(moneyDecimal('1,500')).toBeNull();expect(moneyDecimal('16000')).toBe('16000');expect(moneyDecimal('16,5')).toBe('16.5');expect(moneyDecimal('16.0000')).toBe('16.0000');expect(moneyDecimal('1234.567')).toBe('1234.567')
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
