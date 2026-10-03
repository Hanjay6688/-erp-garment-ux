// @vitest-environment jsdom
import {act} from 'react'
import {createRoot,type Root} from 'react-dom/client'
import {afterEach,beforeEach,describe,expect,it,vi} from 'vitest'
import ConnectedSalesPage from './ConnectedSalesPage'
import {parseSalesRead,parseSalesOutcome} from './salesReadContract'
import {parseNoteCorrectionOutcome,parseNoteCorrectionWorkspace} from './noteCorrectionContract'
import {recoveryIdentity} from '../tests/fixtures/productionRecovery'
import {readProductionRecovery} from './productionRecovery'
const state=vi.hoisted(()=>({auth:null as unknown}))
const client=vi.hoisted(()=>({rpc:vi.fn()}))
vi.mock('./auth/AuthProvider',()=>({useAuth:()=>state.auth}))
vi.mock('./lib/supabase',()=>({getUatSupabaseClient:()=>client}))
const id='11111111-1111-4111-8111-111111111111',line='22222222-2222-4222-8222-222222222222'
function data(finance=true,selected=false){
 const financial={basis:'CURRENT_NATIVE_DOCUMENT',state:'ACTIVE_RECEIVABLE',gross_total:'80.00',return_total:'20.00',net_total:'60.00',paid_total:'30.00',open_balance:'30.00'}
 const row={id,number:'INV-1',customer_id:id,customer_name:'Toko satu',location_id:id,location_name:'Gudang FG',physical_at:'2026-09-29T03:00:00Z',due_date:'2026-10-29',status:'PARTIAL_PAID',row_version:'9007199254740993',notes:null,payment_terms:null,line_count:'1',qty_pcs:'4',reserved_qty:'0',returned_qty:'1',...(finance?{financial}: {})}
 return {contract_version:'cp7.sales-workspace.v1',read_at:'2026-09-29T05:00:00Z',financial_captured:finance,read_only:true,page:{rows:[row],total:'1',offset:0,limit:25,next_offset:null},detail:selected?{...row,...(finance?{review_token:'a'.repeat(32)}:{}),items:[{id:line,product_id:id,product_sku:'PHYSICAL',commercial_sku:'HISTORICAL',product_name:'Celana',size_code:'32',brand_name:'Vivo',qty_pcs:'4',notes:null,...(finance?{financial:{unit_price:'20.00',discount:'0.00',line_total:'80.00'}}:{})}]}:null}
}
let root:Root,container:HTMLDivElement
beforeEach(()=>{Object.assign(globalThis,{IS_REACT_ACT_ENVIRONMENT:true});localStorage.clear();Object.defineProperty(navigator,'locks',{configurable:true,value:{request:async(_n:string,_o:unknown,fn:(l:unknown)=>Promise<unknown>)=>fn({})}});client.rpc.mockReset();const a=structuredClone(recoveryIdentity);a.identity.permissions.push('sales.invoice.view','finance.ar.view');state.auth=a;container=document.createElement('div');document.body.append(container);root=createRoot(container)})
afterEach(async()=>{await act(async()=>root.unmount());container.remove();localStorage.clear();Reflect.deleteProperty(navigator,'locks')})
const flush=async()=>act(async()=>{await new Promise(r=>setTimeout(r,0))})
async function mount(){await act(async()=>root.render(<ConnectedSalesPage/>));await flush()}
async function click(button:HTMLElement){await act(async()=>button.click());await flush()}
const reload=()=>[...container.querySelectorAll('button')].find(x=>x.textContent==='Muat ulang invoice')!
describe('P11 invoice source boundary',()=>{
 it('re-reads an opened source invoice and never treats receivables navigation as a business write',async()=>{
  allowCorrection();client.rpc.mockImplementation(async(_name,args)=>({data:data(true,!!args.p_query.sale_id),error:null}))
  await act(async()=>root.render(<ConnectedSalesPage initialSaleId={id}/>));await flush()
  expect(client.rpc.mock.calls[0][1].p_query).toMatchObject({sale_id:id,q:'',status:null,offset:0})
  expect(container.querySelector('[aria-label="Rincian invoice"]')!.textContent).toContain('Rp30');expect(button('Benerin nota')).toBeDefined()
  expect(new Set(client.rpc.mock.calls.map(c=>c[0]))).toEqual(new Set(['erp_cp7_get_sales_v1']))
 })
 it('refuses invalid or mismatched opened invoice identity before showing any old source action',async()=>{
  await act(async()=>root.render(<ConnectedSalesPage initialSaleId="not-an-invoice"/>));await flush();expect(client.rpc).not.toHaveBeenCalled();expect(container.textContent).toContain('Referensi invoice tidak sah')
  client.rpc.mockResolvedValue({data:data(true,true),error:null});await act(async()=>root.render(<ConnectedSalesPage initialSaleId={line}/>));await flush()
  expect(container.textContent).toContain('Pilihan invoice berubah');expect(container.querySelector('[aria-label="Rincian invoice"]')!.textContent).toContain('Pilih invoice');expect(container.querySelector('[aria-label="Rincian invoice"]')!.textContent).not.toContain('Rp30');expect(button('Benerin nota')).toBeUndefined()
 })
 it('keeps sort local and sends browse and filters through the owned current source reader',async()=>{
  client.rpc.mockImplementation(async(_name,args)=>({data:data(true,!!args.p_query.sale_id),error:null}));await mount()
  const order=container.querySelector<HTMLSelectElement>('[aria-label="Urutkan halaman invoice"]')!,before=client.rpc.mock.calls.length
  await act(async()=>{order.value='LABEL_DESC';order.dispatchEvent(new Event('change',{bubbles:true}))});expect(client.rpc.mock.calls).toHaveLength(before)
  await act(async()=>{const input=container.querySelector<HTMLInputElement>('[aria-label="Cari invoice"]')!;Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value')!.set!.call(input,'INV-1');input.dispatchEvent(new Event('input',{bubbles:true}));const s=container.querySelector<HTMLSelectElement>('[aria-label="Status invoice"]')!;s.value='PAID';s.dispatchEvent(new Event('change',{bubbles:true}))})
  await click(button('Cari invoice'));expect(client.rpc.mock.calls.at(-1)![1].p_query).toMatchObject({q:'INV-1',status:'PAID',offset:0,sale_id:null})
  await click(button('Browse semua'));expect(client.rpc.mock.calls.at(-1)![1].p_query).toMatchObject({q:'',status:null,offset:0,sale_id:null});expect(container.querySelector<HTMLInputElement>('[aria-label="Cari invoice"]')!.value).toBe('')
  expect(new Set(client.rpc.mock.calls.map(x=>x[0]))).toEqual(new Set(['erp_cp7_get_sales_v1']))
 })
 it('names active downstream types at the selected invoice and refuses a premature reversal without blocking atomic edit',async()=>{
  allowCorrection();const a=state.auth as typeof recoveryIdentity;a.identity.permissions.push('sales.payment.view','sales.return.view')
  client.rpc.mockImplementation(async(_name,args)=>({data:data(true,!!args.p_query.sale_id),error:null}));await mount();await click(container.querySelector<HTMLButtonElement>('.cproc-receipt')!)
  const notice=container.querySelector('[aria-label="Penghalang pembatalan INV-1"]')!
  expect(notice.textContent).toContain('Pembayaran INV-1 masih aktif');expect(notice.textContent).toContain('Retur INV-1 masih aktif')
  expect(button('Buka pembayaran INV-1')).toBeDefined();expect(button('Buka retur INV-1')).toBeDefined();expect(button('Benerin nota').disabled).toBe(false)
  await act(async()=>container.querySelector<HTMLInputElement>('[aria-label="Pembatalan penjualan sudah diperiksa"]')!.click());expect(button('Batalkan penjualan tercatat').disabled).toBe(true)
  await click(button('Batalkan penjualan tercatat'));expect(client.rpc.mock.calls.some(([n])=>n==='erp_cp7_save_sale_v1')).toBe(false)
 })
 it('keeps exact versions and source price arithmetic',()=>{const d=parseSalesRead(data(true,true),true);expect(d.detail?.row_version).toBe('9007199254740993');expect(d.detail?.financial?.open_balance).toBe('30.00');expect(d.detail?.items[0].commercial_sku).toBe('HISTORICAL')})
 it('rejects wrong balances, hidden finance, missing lines and wrong pages',()=>{
  const values:unknown[]=[];const a=data(true,true);a.detail!.financial!.open_balance='50.00';values.push(a)
  const b=data(true,true);b.detail!.items=[];values.push(b)
  const c=data();c.page.total='2';values.push(c)
  for(const value of values)expect(()=>parseSalesRead(value,true)).toThrow()
  expect(()=>parseSalesRead(data(true,true),false)).toThrow()
  const leak=data(false,true);Object.assign(leak.detail!,{financial:{gross_total:'80.00'}});expect(()=>parseSalesRead(leak,false)).toThrow()
 })
 it('does not label a draft total as posted AR',()=>{const x=data(true,true);for(const r of [x.page.rows[0],x.detail!]){r.status='DRAFT';r.financial!.state='DRAFT_PREVIEW';r.financial!.open_balance=null as unknown as string}expect(parseSalesRead(x,true).detail?.financial?.open_balance).toBeNull()})
 it('renders real fields then clears source and money after failed refresh',async()=>{
  let fail=false;client.rpc.mockImplementation(async(_name,args)=>fail?{data:null,error:{message:'Read unavailable'}}:{data:data(true,!!args.p_query.sale_id),error:null});await mount();await click(container.querySelector<HTMLButtonElement>('.cproc-receipt')!);expect(container.textContent).toContain('HISTORICAL');expect(container.textContent).toContain('Sisa pembayaran Rp30');fail=true;await click(reload());expect(container.textContent).toContain('Read unavailable');expect(container.textContent).not.toContain('Rp');expect(container.textContent).not.toContain('INV-1')
 })
 it('never sends or renders a write and hides finance for operations',async()=>{
  const a=structuredClone(recoveryIdentity);a.identity.permissions.push('sales.invoice.view');state.auth=a;client.rpc.mockImplementation(async(_name,args)=>({data:data(false,!!args.p_query.sale_id),error:null}));await mount();await click(container.querySelector<HTMLButtonElement>('.cproc-receipt')!);expect(container.textContent).toContain('HISTORICAL');expect(container.textContent).not.toContain('Rp');expect(new Set(client.rpc.mock.calls.map(x=>x[0]))).toEqual(new Set(['erp_cp7_get_sales_v1']))
 })
 it('ignores an old pending response after current authority remounts',async()=>{
  let finish!:(r:unknown)=>void;client.rpc.mockImplementationOnce(()=>new Promise(resolve=>{finish=resolve}));await mount();const a=structuredClone(recoveryIdentity);a.identity.permissions.push('sales.invoice.view');state.auth=a;client.rpc.mockResolvedValue({data:data(false),error:null});await act(async()=>root.render(<ConnectedSalesPage/>));await flush();await act(async()=>finish({data:data(true,true),error:null}));await flush();expect(container.textContent).not.toContain('Rp');expect(container.querySelector('[role="alert"]')).toBeNull()
 })
})

function draftData(selected=false,state='DRAFT'){
 const x=data(true,selected)
 for(const r of [x.page.rows[0],...(x.detail?[x.detail]:[])]){r.status=state;r.reserved_qty=state==='DRAFT'?'4':'0';r.returned_qty='0';Object.assign(r.financial!,{state:state==='DRAFT'?'DRAFT_PREVIEW':state==='POSTED'?'ACTIVE_RECEIVABLE':'INACTIVE_DOCUMENT',return_total:'0.00',paid_total:'0.00',net_total:'80.00',open_balance:state==='POSTED'?'80.00':null})}
 return x
}
const button=(label:string)=>[...container.querySelectorAll('button')].find(x=>x.textContent===label)!
function allowCommands(create=false){const a=structuredClone(recoveryIdentity);a.identity.permissions.push('sales.invoice.view','finance.ar.view','sales.invoice.post','sales.invoice.edit_draft');if(create)a.identity.permissions.push('sales.invoice.create');state.auth=a}
describe('P11 reviewed native draft commands',()=>{
 it('requires review and binds POST to exact invoice, bigint revision and token',async()=>{
  allowCommands();let state='DRAFT';client.rpc.mockImplementation(async(name,args)=>{
   if(name==='erp_cp7_get_sales_v1')return {data:draftData(!!args.p_query.sale_id,state),error:null}
   state='POSTED';return {data:{contract_version:'cp7.sales-outcome.v1',kind:'COMMITTED_OUTCOME',action:args.p_action,request_id:args.p_request,sale_id:id,status:state,row_version:'9007199254740994'},error:null}
  });await mount();await click(container.querySelector<HTMLButtonElement>('.cproc-receipt')!);expect(button('Sahkan invoice').disabled).toBe(true)
  await act(async()=>container.querySelector<HTMLInputElement>('[aria-label="Invoice sudah diperiksa"]')!.click());await click(button('Sahkan invoice'))
  const sent=client.rpc.mock.calls.find(([n])=>n==='erp_cp7_save_sale_v1')![1]
  expect(sent.p_expected).toBe('9007199254740993');expect(sent.p_payload).toEqual({sale_id:id,review_token:'a'.repeat(32),change_reason:'Invoice dan barang sudah diperiksa'});expect(container.textContent).toContain('Sisa pembayaran Rp80');expect(button('Sahkan invoice')).toBeUndefined()
 })
 it('retains and reconciles the identical request after a lost commit reply and remount',async()=>{
  allowCommands(true);let lost=false,state='DRAFT';client.rpc.mockImplementation(async(name,args)=>{
   if(name==='erp_cp7_get_sales_v1')return {data:draftData(!!args.p_query.sale_id,state),error:null}
   state='CANCELLED';if(!lost){lost=true;throw Error('Reply lost after commit')}
   return {data:{contract_version:'cp7.sales-outcome.v1',kind:'COMMITTED_OUTCOME',action:args.p_action,request_id:args.p_request,sale_id:id,status:state,row_version:'9007199254740994'},error:null}
  });await mount();await click(container.querySelector<HTMLButtonElement>('.cproc-receipt')!);await act(async()=>container.querySelector<HTMLInputElement>('[aria-label="Invoice sudah diperiksa"]')!.click());await click(button('Batalkan draft invoice'))
  expect(button('Reconcile transaksi')).toBeDefined()
  const pending=structuredClone(readProductionRecovery('disposable:actor-1').pending)
  expect(container.querySelectorAll('.cproc-receipt')).toHaveLength(0)
  await click(reload());expect(container.querySelector('[aria-label="Rincian invoice"]')!.textContent).toContain('Draft dibatalkan');expect(container.querySelectorAll('.cproc-receipt')).toHaveLength(1)
  expect(button('Buat invoice').disabled).toBe(true)
  expect(button('Reconcile transaksi')).toBeDefined();expect(button('Sahkan invoice')).toBeUndefined();expect(button('Batalkan draft invoice')).toBeUndefined()
  expect(client.rpc.mock.calls.filter(([n])=>n==='erp_cp7_save_sale_v1')).toHaveLength(1);expect(readProductionRecovery('disposable:actor-1').pending).toEqual(pending)
  await act(async()=>root.unmount());root=createRoot(container);await mount();await click(button('Reconcile transaksi'))
  const sends=client.rpc.mock.calls.filter(([n])=>n==='erp_cp7_save_sale_v1');expect(sends).toHaveLength(2);expect(sends[1][1]).toEqual(sends[0][1]);expect(button('Reconcile transaksi')).toBeUndefined();expect(container.textContent).toContain('Draft dibatalkan')
 })
 it('rejects a success receipt for a different document or wrong transition',()=>{
  const r={contract_version:'cp7.sales-outcome.v1',kind:'COMMITTED_OUTCOME',action:'POST',request_id:id,sale_id:id,status:'POSTED',row_version:'9007199254740994'}
  expect(parseSalesOutcome(r,id,'POST',id).row_version).toBe('9007199254740994');expect(()=>parseSalesOutcome(r,id,'POST',line)).toThrow();expect(()=>parseSalesOutcome({...r,status:'CANCELLED'},id,'POST',id)).toThrow()
 })
})

const replacement='33333333-3333-4333-8333-333333333333',revisionId='44444444-4444-4444-8444-444444444444'
function allowCorrection(){const a=structuredClone(recoveryIdentity);a.identity.profile.role='OWNER';a.identity.permissions.push('sales.invoice.view','finance.ar.view','finance.hpp.view','sales.invoice.create','sales.invoice.edit_draft','sales.invoice.post','sales.invoice.reverse');state.auth=a}
function correctedData(selected=false){const x=draftData(selected,'POSTED');for(const r of [x.page.rows[0],...(x.detail?[x.detail]:[])]){r.id=replacement;r.number='INV-1 · R1';r.qty_pcs='3';r.row_version='9007199254740994';Object.assign(r.financial!,{gross_total:'60.00',net_total:'60.00',open_balance:'60.00'})}if(x.detail){x.detail.items[0].qty_pcs='3';x.detail.items[0].financial!.line_total='60.00'}return x}
function correctionOutcome(request:string){return {contract_version:'cp7.note-correction-outcome.v1',kind:'COMMITTED_OUTCOME',action:'CORRECT',request_id:request,root_sale_id:id,previous_sale_id:id,sale_id:replacement,revision_id:revisionId,revision:'1',effective_at:'2026-09-29T03:00:00Z'}}
function correctionWorkspace(){return {contract_version:'cp7.note-correction-workspace.v2',read_at:'2026-10-02T10:00:00Z',root_sale_id:id,current_sale_id:replacement,history:[{revision_id:revisionId,revision:'1',previous_sale_id:id,replacement_sale_id:replacement,effective_at:'2026-09-29T03:00:00Z',recorded_at:'2026-10-02T10:00:00Z',reason:'Jumlah sebenarnya tiga PCS',actor_id:id,actor_display_name:'Owner Asli',actor_name_basis:'CURRENT_PROFILE'}],current:correctedData(true),original_note_number:'INV-1',production_go:false}}
async function fillInvoice(label:string,value:string){await act(async()=>{const e=container.querySelector<HTMLInputElement>(`[aria-label="${label}"]`)!;Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value')!.set!.call(e,value);e.dispatchEvent(new Event('input',{bubbles:true}))});await flush()}
describe('owning historical note correction',()=>{
 it('retires current invoice facts and a held correction history after the shared source is invalidated',async()=>{
  allowCorrection();let finish!:(r:unknown)=>void
  client.rpc.mockImplementation((name,args)=>name==='erp_cp7_get_note_correction_v2'?new Promise(resolve=>{finish=resolve}):Promise.resolve({data:draftData(!!args.p_query.sale_id,'POSTED'),error:null}))
  await mount();await click(container.querySelector<HTMLButtonElement>('.cproc-receipt')!);await fillInvoice('Cari invoice','Pencarian milik operator');await click(button('Riwayat pembetulan nota'))
  await act(async()=>window.dispatchEvent(new StorageEvent('storage',{key:null})))
  await act(async()=>finish({data:correctionWorkspace(),error:null}));await flush()
  expect(container.textContent).not.toContain('Owner Asli')
  expect(container.querySelector('[aria-label="Nilai invoice"]')).toBeNull()
  expect(container.querySelectorAll('.cproc-receipt')).toHaveLength(0)
  expect(container.querySelector<HTMLInputElement>('[aria-label="Cari invoice"]')!.value).toBe('Pencarian milik operator')
 })
 it('keeps unsent correction quantities and reason while locking its retired source',async()=>{
  allowCorrection();client.rpc.mockImplementation(async(_name,args)=>({data:draftData(!!args.p_query.sale_id,'POSTED'),error:null}))
  await mount();await click(container.querySelector<HTMLButtonElement>('.cproc-receipt')!);await click(button('Benerin nota'));await fillInvoice('Jumlah invoice 1','3');await fillInvoice('Alasan simpan invoice','Catatan baru milik operator')
  await act(async()=>window.dispatchEvent(new StorageEvent('storage',{key:null})))
  expect(container.querySelector('[aria-label="Nilai invoice"]')).toBeNull()
  expect(container.querySelector<HTMLInputElement>('[aria-label="Jumlah invoice 1"]')!.value).toBe('3')
  expect(container.querySelector<HTMLInputElement>('[aria-label="Alasan simpan invoice"]')!.value).toBe('Catatan baru milik operator')
  expect(button('Simpan pembetulan nota').disabled).toBe(true)
  expect(client.rpc.mock.calls.some(([name])=>name==='erp_cp7_correct_note_v1')).toBe(false)
 })
 it('opens a real form, sends exact source/version and retires it for the replacement',async()=>{
  allowCorrection();let committed=false;client.rpc.mockImplementation(async(name,args)=>{if(name==='erp_cp7_get_sales_v1')return {data:committed?correctedData(!!args.p_query.sale_id):draftData(!!args.p_query.sale_id,'POSTED'),error:null};if(name==='erp_cp7_correct_note_v1'){committed=true;return {data:correctionOutcome(args.p_request),error:null}}throw Error('Unowned RPC')});await mount();await click(container.querySelector<HTMLButtonElement>('.cproc-receipt')!);await click(button('Benerin nota'));expect(container.querySelector<HTMLInputElement>('[aria-label="Waktu draft invoice WIB"]')!.readOnly).toBe(true);await fillInvoice('Jumlah invoice 1','3');await fillInvoice('Alasan simpan invoice','Jumlah sebenarnya tiga PCS');expect(button('Simpan pembetulan nota').disabled).toBe(true);await click(container.querySelector<HTMLInputElement>('[aria-label="Pembetulan nota sudah diperiksa"]')!);await click(button('Simpan pembetulan nota'));const sent=client.rpc.mock.calls.find(([n])=>n==='erp_cp7_correct_note_v1')![1];expect(sent.p_expected).toBe('9007199254740993');expect(sent.p_payload.sale_id).toBe(id);expect(sent.p_payload.sale_date).toBe('2026-09-29T03:00:00Z');expect(sent.p_payload.items[0].qty_pcs).toBe('3');expect(container.querySelector('[aria-label="Benerin nota"]')).toBeNull();expect(container.textContent).toContain('INV-1 · R1');expect(container.textContent).toContain('Sisa pembayaran Rp60');expect(client.rpc.mock.calls.some(([n])=>n==='erp_cp7_save_sale_v1')).toBe(false)
 })
 it('recovers an uncertain correction with the identical UUID and payload after reload',async()=>{
  allowCorrection();let committed=false,lost=false;client.rpc.mockImplementation(async(name,args)=>{if(name==='erp_cp7_get_sales_v1')return {data:committed?correctedData(!!args.p_query.sale_id):draftData(!!args.p_query.sale_id,'POSTED'),error:null};if(name==='erp_cp7_correct_note_v1'){committed=true;if(!lost){lost=true;throw Error('Reply lost after commit')}return {data:correctionOutcome(args.p_request),error:null}}throw Error('Unowned RPC')});await mount();await click(container.querySelector<HTMLButtonElement>('.cproc-receipt')!);await click(button('Benerin nota'));await fillInvoice('Jumlah invoice 1','3');await fillInvoice('Alasan simpan invoice','Jumlah sebenarnya tiga PCS');await click(container.querySelector<HTMLInputElement>('[aria-label="Pembetulan nota sudah diperiksa"]')!);await click(button('Simpan pembetulan nota'));expect(button('Reconcile transaksi')).toBeDefined();await act(async()=>root.unmount());root=createRoot(container);await mount();await click(button('Reconcile transaksi'));const sends=client.rpc.mock.calls.filter(([n])=>n==='erp_cp7_correct_note_v1');expect(sends).toHaveLength(2);expect(sends[1][1]).toEqual(sends[0][1]);expect(button('Reconcile transaksi')).toBeUndefined();expect(container.textContent).toContain('Sisa pembayaran Rp60')
 })
 it('rejects unrelated source, changed effective date and a broken revision chain',()=>{expect(parseNoteCorrectionOutcome(correctionOutcome(id),id,id,'2026-09-29T03:00:00Z').sale_id).toBe(replacement);expect(()=>parseNoteCorrectionOutcome(correctionOutcome(id),line,id,'2026-09-29T03:00:00Z')).toThrow();expect(()=>parseNoteCorrectionOutcome(correctionOutcome(id),id,id,'2026-10-02T03:00:00Z')).toThrow();expect(parseNoteCorrectionWorkspace(correctionWorkspace(),id).current_sale_id).toBe(replacement);const broken=correctionWorkspace();broken.history[0].previous_sale_id=line;expect(()=>parseNoteCorrectionWorkspace(broken,id)).toThrow();expect(()=>parseNoteCorrectionWorkspace(correctionWorkspace(),line)).toThrow()})
 it('shows the immutable correction actor with its current profile name and clears it after current denial',async()=>{
  allowCorrection();client.rpc.mockImplementation(async(name,args)=>({data:name==='erp_cp7_get_note_correction_v2'?correctionWorkspace():draftData(!!args.p_query.sale_id,'POSTED'),error:null}));await mount();await click(container.querySelector<HTMLButtonElement>('.cproc-receipt')!);await click(button('Riwayat pembetulan nota'));expect(container.textContent).toContain('Dibetulkan oleh Owner Asli');expect(container.textContent).toContain('nama profil saat ini')
  client.rpc.mockResolvedValue({data:null,error:{status:403,message:'Hak akses berubah'}});await click(button('Riwayat pembetulan nota'));expect(container.textContent).not.toContain('Owner Asli');expect(container.querySelector('[role="alert"]')).toBeTruthy()
 })
 it('preserves the exact Native microsecond and accepts equivalent timezone rendering',()=>{
  const original='2026-09-29T03:00:00.123456Z'
  expect(parseNoteCorrectionOutcome({...correctionOutcome(id),effective_at:'2026-09-29T10:00:00.123456+07:00'},id,id,original).sale_id).toBe(replacement)
  for(const effective_at of ['2026-09-29T03:00:00.123457Z','2026-09-29T03:00:00.123455Z','2026-09-29T03:00:00.123Z','2026-09-29T03:00:00.1234567Z']){
   expect(()=>parseNoteCorrectionOutcome({...correctionOutcome(id),effective_at},id,id,original)).toThrow()
  }
 })
})
