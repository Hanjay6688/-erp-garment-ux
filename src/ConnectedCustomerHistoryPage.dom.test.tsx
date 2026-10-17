// @vitest-environment jsdom
import {act} from 'react'
import {createRoot,type Root} from 'react-dom/client'
import {afterEach,beforeEach,describe,expect,it,vi} from 'vitest'
import ConnectedCustomerHistoryPage,{historyCsv} from './ConnectedCustomerHistoryPage'
import {parseHistoryDetail,parseHistoryList} from './customerHistoryContract'
import {recoveryIdentity} from '../tests/fixtures/productionRecovery'
const mock=vi.hoisted(()=>({auth:null as unknown,rpc:vi.fn()}))
vi.mock('./auth/AuthProvider',()=>({useAuth:()=>mock.auth}))
vi.mock('./lib/supabase',()=>({getUatSupabaseClient:()=>mock}))

const customer='11111111-1111-4111-8111-111111111111',other='11111111-1111-4111-8111-222222222222'
const sale='22222222-2222-4222-8222-222222222222',draft='22222222-2222-4222-8222-333333333333'
const payment='33333333-3333-4333-8333-333333333333',ret='44444444-4444-4444-8444-444444444444'
type Q={q?:string;customer_id?:string;offset:number;limit:number}
const counts={invoices:'2',payments:'1',returns:'1',cancellations:'1'}
const custFinance={basis:'CURRENT_NATIVE_DOCUMENT',active_invoices:'1',invoice_total:'80.00',return_total:'20.00',net_total:'60.00',paid_total:'30.00',open_balance:'30.00'}
function cust(financial:boolean,id=customer,name='Toko Sumber Rejeki'){
 return {id,code:id===customer?'TSR-01':'LAIN-02',name,is_active:true,counts:id===customer?counts:{invoices:'0',payments:'0',returns:'0',cancellations:'0'},
  last_invoice_at:id===customer?'2026-10-17T02:55:00+00:00':null,...(financial?{financial:id===customer?custFinance:{...custFinance,active_invoices:'0',invoice_total:'0.00',return_total:'0.00',net_total:'0.00',paid_total:'0.00',open_balance:'0.00'}}:{})}
}
function events(financial:boolean){
 const e=(kind:string,document:string,id:string,number:string,at:string,status:string,qty:string|null,method:string|null,location:string|null,amount:string,invoice=sale,invoiceNumber='INV-1')=>
  ({id:`${kind}:${id}`,kind,document,document_id:id,number,at,wib_date:at.slice(0,10),invoice_id:invoice,invoice_number:invoiceNumber,status,qty_pcs:qty,method,location_name:location,...(financial?{financial:{amount}}:{})})
 return [
  e('CANCELLATION','INVOICE',draft,'INV-1-D2','2026-10-17T03:10:00+00:00','CANCELLED','2',null,'Gudang FG','40.00',draft,'INV-1-D2'),
  e('RETURN','RETURN',ret,'RET-1','2026-10-17T03:05:00+00:00','POSTED','1',null,null,'20.00'),
  e('PAYMENT','PAYMENT',payment,'PAY-1','2026-10-17T03:00:00+00:00','POSTED',null,'BANK_TRANSFER',null,'30.00'),
  e('INVOICE','INVOICE',draft,'INV-1-D2','2026-10-17T02:55:00+00:00','CANCELLED','2',null,'Gudang FG','40.00',draft,'INV-1-D2'),
  e('INVOICE','INVOICE',sale,'INV-1','2026-10-17T02:50:00+00:00','PARTIAL_PAID','4',null,'Gudang FG','80.00'),
 ]
}
function invoices(financial:boolean,ids:string[]){
 const all=[
  {id:draft,number:'INV-1-D2',status:'CANCELLED',physical_at:'2026-10-17T02:55:00+00:00',due_date:null,qty_pcs:'2',...(financial?{financial:{basis:'CURRENT_NATIVE_DOCUMENT',state:'INACTIVE_DOCUMENT',gross_total:'40.00',return_total:'0.00',net_total:'40.00',paid_total:'0.00',open_balance:null}}:{})},
  {id:sale,number:'INV-1',status:'PARTIAL_PAID',physical_at:'2026-10-17T02:50:00+00:00',due_date:'2026-11-16',qty_pcs:'4',...(financial?{financial:{basis:'CURRENT_NATIVE_DOCUMENT',state:'ACTIVE_RECEIVABLE',gross_total:'80.00',return_total:'20.00',net_total:'60.00',paid_total:'30.00',open_balance:'30.00'}}:{})},
 ]
 return all.filter(i=>ids.includes(i.id))
}
const base=(financial:boolean,exportable:boolean)=>({contract_version:'cp7.customer-history.v1',read_at:'2026-10-17T03:20:00+00:00',financial_captured:financial,can_export:exportable,read_only:true,business_DML:false})
function answer(q:Q,financial:boolean,exportable=financial){
 if(!q.customer_id){
  const rows=[cust(financial),cust(financial,other,'Toko Lain')].filter(c=>!q.q||c.name.toLowerCase().includes(q.q.toLowerCase())).slice(q.offset,q.offset+q.limit)
  return {...base(financial,exportable),mode:'LIST',page:{rows,total:String(rows.length),offset:q.offset,limit:q.limit,next_offset:null}}
 }
 const all=events(financial),rows=all.slice(q.offset,q.offset+q.limit)
 return {...base(financial,exportable),mode:'CUSTOMER',customer:cust(financial),timeline:{rows,total:'5',offset:q.offset,limit:q.limit,next_offset:q.offset+rows.length<5?q.offset+rows.length:null},
  invoices:invoices(financial,[...new Set(rows.map(r=>r.invoice_id))])}
}

let root:Root,container:HTMLDivElement
function identity(permissions:string[]){const auth=structuredClone(recoveryIdentity);auth.identity.permissions=permissions;mock.auth=auth}
beforeEach(()=>{Object.assign(globalThis,{IS_REACT_ACT_ENVIRONMENT:true});mock.rpc.mockReset();identity(['sales.history.view','finance.ar.view','sales.history.export'])
 mock.rpc.mockImplementation((_n:string,{p_query}:{p_query:Q})=>Promise.resolve({data:answer(p_query,true),error:null}))
 container=document.createElement('div');document.body.append(container);root=createRoot(container)})
afterEach(async()=>{await act(async()=>root.unmount());container.remove();vi.restoreAllMocks()})
const flush=async()=>act(async()=>{await new Promise(r=>setTimeout(r,0))})
async function mount(){await act(async()=>root.render(<ConnectedCustomerHistoryPage/>));await flush()}
async function click(e:Element){await act(async()=>(e as HTMLElement).click());await flush()}
const button=(name:string)=>[...container.querySelectorAll('button')].find(e=>e.textContent===name)
async function fill(label:string,value:string){await act(async()=>{const e=container.querySelector<HTMLInputElement>(`input[aria-label="${label}"]`)!;Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value')!.set!.call(e,value);e.dispatchEvent(new Event('input',{bubbles:true}))});await flush()}
const pick=async(id=customer)=>click(container.querySelector(`[data-customer-id="${id}"]`)!)
const timeline=()=>container.querySelector('[aria-label="Riwayat pelanggan terpilih"]')!

describe('Riwayat Pelanggan on real data (R3-03)',()=>{
 it('searches customers, opens one and shows its events newest first with balances',async()=>{
  await mount()
  expect(mock.rpc).toHaveBeenLastCalledWith('erp_cp7_get_customer_history_v1',{p_query:{q:'',offset:0,limit:25}})
  expect(container.querySelector(`[data-customer-id="${customer}"]`)!.textContent).toContain('2 invoice · 1 pembayaran · 1 retur · 1 pembatalan')
  expect(container.querySelector(`[data-customer-id="${customer}"]`)!.textContent).toContain('Sisa tagihanRp30')
  await fill('Cari pelanggan riwayat','sumber');await click(button('Cari pelanggan')!)
  expect(mock.rpc).toHaveBeenLastCalledWith('erp_cp7_get_customer_history_v1',{p_query:{q:'sumber',offset:0,limit:25}})
  expect(container.querySelectorAll('[data-customer-id]')).toHaveLength(1)
  await pick();expect(mock.rpc).toHaveBeenLastCalledWith('erp_cp7_get_customer_history_v1',{p_query:{customer_id:customer,offset:0,limit:25}})
  const items=[...timeline().querySelectorAll('li')]
  expect(items.map(li=>li.getAttribute('data-kind'))).toEqual(['CANCELLATION','RETURN','PAYMENT','INVOICE','INVOICE'])
  expect(items[0].textContent).toContain('Draf invoice INV-1-D2 dibatalkan');expect(items[1].textContent).toContain('Retur RET-1');expect(items[1].textContent).toContain('Rp20')
  expect(items[2].textContent).toContain('Pembayaran PAY-1');expect(items[2].textContent).toContain('Transfer bank');expect(items[2].textContent).toContain('Rp30')
  expect(items[4].textContent).toContain('4 pcs · Gudang FG · Dibayar sebagian');expect(items[4].textContent).toContain('retur Rp20 · dibayar Rp30 · sisa tagihan Rp30')
  expect(items[3].textContent).toContain('nilai Rp40, bukan piutang aktif')
  expect(items[0].querySelector('time')!.textContent).toMatch(/WIB$/)
  const totals=container.querySelector('[aria-label="Ringkasan uang Toko Sumber Rejeki"]')!.textContent
  for(const t of ['Nilai invoice aktifRp80','Retur tercatatRp20','Pembayaran tercatatRp30','Sisa tagihanRp30'])expect(totals).toContain(t)
  expect(new Set(mock.rpc.mock.calls.map(c=>c[0]))).toEqual(new Set(['erp_cp7_get_customer_history_v1']))
 })
 it('shows the events without any amount when the account lacks finance.ar.view',async()=>{
  identity(['sales.history.view']);mock.rpc.mockImplementation((_n:string,{p_query}:{p_query:Q})=>Promise.resolve({data:answer(p_query,false),error:null}))
  await mount();await pick()
  expect(timeline().querySelectorAll('li')).toHaveLength(5);expect(container.textContent).not.toContain('Rp')
  expect(container.textContent).toContain('Nilai uang tidak ditampilkan');expect(button('Unduh riwayat yang tampil (CSV)')).toBeUndefined()
  expect(timeline().textContent).toContain('Invoice INV-1 sekarang: Dibayar sebagian')
 })
 it('refuses an answer that carries amounts the account may not see, or lacks them when it may',async()=>{
  identity(['sales.history.view']);mock.rpc.mockImplementation((_n:string,{p_query}:{p_query:Q})=>Promise.resolve({data:answer(p_query,true),error:null}))
  await mount();expect(container.textContent).toContain('Data riwayat pelanggan belum lengkap');expect(container.textContent).not.toContain('Rp')
  identity(['sales.history.view','finance.ar.view']);mock.rpc.mockImplementation((_n:string,{p_query}:{p_query:Q})=>Promise.resolve({data:answer(p_query,false),error:null}))
  await mount();expect(container.textContent).toContain('Data riwayat pelanggan belum lengkap')
 })
 it('asks for the history permission and calls nothing without it',async()=>{
  identity(['sales.invoice.view','finance.ar.view']);await mount()
  expect(container.textContent).toContain('Hak melihat riwayat pelanggan diperlukan.');expect(mock.rpc).not.toHaveBeenCalled()
 })
 it('pages the timeline newer and older with the server offsets',async()=>{
  // 27 invoices: a first page of 25 events and a second of 2, each with exactly the invoices it names.
  const id=(n:number)=>`55555555-5555-4555-8555-${String(n).padStart(12,'0')}`,at=(n:number)=>new Date(Date.UTC(2026,9,17,3,0)-n*60000).toISOString()
  mock.rpc.mockImplementation((_n:string,{p_query}:{p_query:Q})=>{
   if(!p_query.customer_id)return Promise.resolve({data:answer(p_query,true),error:null})
   const all=Array.from({length:27},(_,n)=>({id:`INVOICE:${id(n)}`,kind:'INVOICE',document:'INVOICE',document_id:id(n),number:`INV-${n}`,at:at(n),wib_date:at(n).slice(0,10),invoice_id:id(n),
    invoice_number:`INV-${n}`,status:'POSTED',qty_pcs:'1',method:null,location_name:'Gudang FG',financial:{amount:'10.00'}}))
   const rows=all.slice(p_query.offset,p_query.offset+p_query.limit)
   const c={...cust(true),counts:{invoices:'27',payments:'0',returns:'0',cancellations:'0'},financial:{...custFinance,active_invoices:'27',invoice_total:'270.00',return_total:'0.00',net_total:'270.00',paid_total:'0.00',open_balance:'270.00'}}
   return Promise.resolve({data:{...base(true,true),mode:'CUSTOMER',customer:c,timeline:{rows,total:'27',offset:p_query.offset,limit:p_query.limit,next_offset:p_query.offset+rows.length<27?p_query.offset+rows.length:null},
    invoices:rows.map(r=>({id:r.document_id,number:r.number,status:'POSTED',physical_at:r.at,due_date:null,qty_pcs:'1',financial:{basis:'CURRENT_NATIVE_DOCUMENT',state:'ACTIVE_RECEIVABLE',gross_total:'10.00',return_total:'0.00',net_total:'10.00',paid_total:'0.00',open_balance:'10.00'}}))},error:null})
  })
  await mount();await pick()
  expect(timeline().querySelectorAll('li')).toHaveLength(25);expect(container.textContent).toContain('Kejadian 1–25 dari 27');expect(button('Kejadian lebih baru')!.disabled).toBe(true)
  await click(button('Kejadian lebih lama')!);expect(mock.rpc).toHaveBeenLastCalledWith('erp_cp7_get_customer_history_v1',{p_query:{customer_id:customer,offset:25,limit:25}})
  expect(timeline().querySelectorAll('li')).toHaveLength(2);expect(container.textContent).toContain('Kejadian 26–27 dari 27');expect(button('Kejadian lebih lama')!.disabled).toBe(true)
  await click(button('Kejadian lebih baru')!);expect(mock.rpc).toHaveBeenLastCalledWith('erp_cp7_get_customer_history_v1',{p_query:{customer_id:customer,offset:0,limit:25}})
  expect(timeline().querySelectorAll('li')).toHaveLength(25)
 })
 it('downloads only the rows on screen, and only with sales.history.export',async()=>{
  const created:Blob[]=[];const createObjectURL=vi.fn((b:Blob)=>{created.push(b);return 'blob:history'});const revokeObjectURL=vi.fn()
  Object.assign(URL,{createObjectURL,revokeObjectURL});const clickSpy=vi.spyOn(HTMLAnchorElement.prototype,'click').mockImplementation(()=>{})
  await mount();await pick();await click(button('Unduh riwayat yang tampil (CSV)')!)
  expect(createObjectURL).toHaveBeenCalledTimes(1);expect(clickSpy).toHaveBeenCalledTimes(1)
  const csv=await new Promise<string>(done=>{const reader=new FileReader();reader.onload=()=>done(String(reader.result));reader.readAsText(created[0])}),lines=csv.trim().split('\r\n')
  expect(lines).toHaveLength(6);expect(lines[0]).toContain('"Nilai (Rp)"');expect(lines[1]).toContain('"INV-1-D2"');expect(lines[3]).toContain('"30.00"');expect(lines[5]).toContain('"30.00"')
  expect(container.textContent).toContain('5 baris yang tampil (kejadian 1–5) sudah diunduh.')
  expect(new Set(mock.rpc.mock.calls.map(c=>c[0]))).toEqual(new Set(['erp_cp7_get_customer_history_v1']))
  identity(['sales.history.view','finance.ar.view']);await mount();await pick();expect(button('Unduh riwayat yang tampil (CSV)')).toBeUndefined()
  identity(['sales.history.view','finance.ar.view','sales.history.export'])
  mock.rpc.mockImplementation((_n:string,{p_query}:{p_query:Q})=>Promise.resolve({data:answer(p_query,true,false),error:null}))
  await mount();await pick();expect(button('Unduh riwayat yang tampil (CSV)')).toBeUndefined()
 })
 it('keeps a spreadsheet formula in a document number as text',()=>{
  const rows=events(true);rows[1]={...rows[1],number:'=HYPERLINK("x")'}
  const csv=historyCsv(rows as never,invoices(true,[sale,draft]) as never,false)
  expect(csv).toContain(`"'=HYPERLINK(""x"")"`);expect(csv).not.toContain('Nilai (Rp)')
 })
 it('says plainly when the server refuses or the history cannot be placed, without numbers',async()=>{
  await mount();mock.rpc.mockResolvedValueOnce({data:null,error:{message:'CP7_CUSTOMER_HISTORY_INCOMPLETE',code:'P0001'}})
  await pick();expect(timeline().textContent).toContain('belum bisa dibaca lengkap');expect(timeline().textContent).not.toContain('Rp')
  mock.rpc.mockResolvedValueOnce({data:null,error:{message:'CP7_CUSTOMER_HISTORY_DENIED',code:'42501'}})
  await click(button('Muat ulang riwayat')!);expect(container.textContent).toContain('Akun ini tidak memiliki hak melihat riwayat pelanggan.')
 })
 it('an answer for the previous account does not replace the current one',async()=>{
  let late:((v:unknown)=>void)|null=null
  mock.rpc.mockImplementationOnce(()=>new Promise(r=>{late=r}))
  await mount();const auth=structuredClone(mock.auth) as typeof recoveryIdentity;auth.identity.profile.id='actor-2';mock.auth=auth
  mock.rpc.mockImplementation((_n:string,{p_query}:{p_query:Q})=>{const a=answer(p_query,true) as {page:{rows:{name:string}[]}};a.page.rows[0].name='Pelanggan akun sekarang';return Promise.resolve({data:a,error:null})})
  await mount();await act(async()=>late!({data:answer({offset:0,limit:25},true),error:null}));await flush()
  expect(container.textContent).toContain('Pelanggan akun sekarang');expect(container.textContent).not.toContain('Toko Sumber Rejeki')
 })
})

describe('customer history contract',()=>{
 const expect0={financial:true,offset:0,limit:25}
 it('accepts the facade answer and rejects unknown keys, broken sums, order and pages',()=>{
  expect(parseHistoryList(answer({offset:0,limit:25},true),expect0).page.rows).toHaveLength(2)
  const d=answer({customer_id:customer,offset:0,limit:25},true)
  expect(parseHistoryDetail(d,{...expect0,customerId:customer}).timeline.rows).toHaveLength(5)
  const bad=[
   (x:Record<string,unknown>)=>({...x,extra:1}),
   (x:Record<string,unknown>)=>({...x,business_DML:true}),
   (x:Record<string,unknown>)=>{const y=structuredClone(x) as {customer:{financial:Record<string,string>}};y.customer.financial.open_balance='31.00';return y},
   (x:Record<string,unknown>)=>{const y=structuredClone(x) as {timeline:{rows:unknown[]}};y.timeline.rows.reverse();return y},
   (x:Record<string,unknown>)=>{const y=structuredClone(x) as {timeline:{total:string}};y.timeline.total='6';return y},
   (x:Record<string,unknown>)=>{const y=structuredClone(x) as {invoices:unknown[]};y.invoices.pop();return y},
   (x:Record<string,unknown>)=>{const y=structuredClone(x) as {timeline:{rows:{wib_date:string}[]}};y.timeline.rows[0].wib_date='2026-10-18';return y},
   (x:Record<string,unknown>)=>{const y=structuredClone(x) as {invoices:{financial:Record<string,string|null>}[]};y.invoices[1].financial.open_balance=null;return y},
   (x:Record<string,unknown>)=>{const y=structuredClone(x) as {timeline:{rows:{status:string}[]}};y.timeline.rows[2].status='PAID';return y},
  ]
  for(const change of bad)expect(()=>parseHistoryDetail(change(d as Record<string,unknown>),{...expect0,customerId:customer})).toThrow('Data riwayat pelanggan belum lengkap')
  expect(()=>parseHistoryDetail(d,{...expect0,customerId:other})).toThrow()
  expect(()=>parseHistoryDetail(answer({customer_id:customer,offset:0,limit:25},false),{...expect0,customerId:customer})).toThrow()
 })
 it('WIB date follows Jakarta time, not the device',()=>{
  const d=answer({customer_id:customer,offset:0,limit:25},true) as {timeline:{rows:{at:string;wib_date:string}[]}}
  d.timeline.rows=d.timeline.rows.map(r=>({...r,at:'2026-10-17T17:30:00+00:00',wib_date:'2026-10-18'}))
  expect(()=>parseHistoryDetail(d,{financial:true,offset:0,limit:25,customerId:customer})).not.toThrow()
 })
})
