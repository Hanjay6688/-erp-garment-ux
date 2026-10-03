import {useTransactionSource} from './TransactionSourceNavigation'
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useAuth } from './auth/AuthProvider'
import { isConnectedRuntime } from './config/runtime'
import { getUatSupabaseClient } from './lib/supabase'
import { normalizeClientError } from './lib/clientError'
import { cp6WibDateTimeInput, cp6WibPhysicalTimeToIso, formatCp6WibDateTime } from './cp6BusinessTime'
import { useProductionMutation, type ProductionMutationHandlers } from './useProductionMutation'
import ProductionRecoveryNotice from './ProductionRecoveryNotice'
import { formatReceiptDecimal as numberText, procurementObject, receiptDecimal } from './procurementContract'
import { hasInvoiceCapacity, parsePurchaseInvoices, parsePurchaseInvoiceOutcome, type PurchaseInvoices, type PurchaseInvoice, parseInvoiceSources, type InvoiceSources, type InvoiceSource } from './purchaseInvoiceContract'
import type { Json } from './types/database.preconnect'
type Props={purchaseId:string|null;receiptRevision?:string|null;onReceiptUpdated:(purchaseId:string)=>Promise<boolean>}
type Form={combined?:{id:string|null;version:string|null;supplier:string;originalAt:string|null};purchaseId:string;version:string;number:string;date:string;at:string;due:string;reason:string;notes:string;reviewed:boolean;lines:{id:string;purchaseId?:string;purchaseNumber?:string;notes?:string|null;name:string;unit:string;selected:boolean;qty:string;price:string;discount:string}[]}
function document(f:Form):Json|null{
 const at=f.combined?.originalAt&&cp6WibDateTimeInput(f.combined.originalAt)===f.at?f.combined.originalAt:cp6WibPhysicalTimeToIso(f.at)
 if(!f.reviewed||!f.number.trim()||!/^\d{4}-\d{2}-\d{2}$/.test(f.date)||!at||!f.reason.trim()||f.due&&!/^\d{4}-\d{2}-\d{2}$/.test(f.due))return null
 const lines:Json[]=[]
 for(const l of f.lines.filter(l=>l.selected)){const qty=receiptDecimal(l.qty,true),price=receiptDecimal(l.price),discount=receiptDecimal(l.discount);if(!qty||price===null||discount===null)return null;lines.push({purchase_item_id:l.id,qty_invoiced:qty,...(f.combined?{unit_price:price,notes:l.notes??null}:{final_unit_price:price}),discount_amount:discount})}
 if(f.combined)return lines.length&&lines.length<=100&&f.lines.some(l=>l.selected&&l.purchaseId===f.purchaseId)?{purchase_id:f.purchaseId,...(f.combined.id?{id:f.combined.id}:{}),supplier_id:f.combined.supplier,invoice_number:f.number.trim(),invoice_date:f.date,received_at:at,due_date:f.due||null,change_reason:f.reason.trim(),notes:f.notes.trim()||null,lines}:null
 return lines.length?{purchase_id:f.purchaseId,supplier_invoice_number:f.number.trim(),invoice_date:f.date,received_at:at,due_date:f.due||null,reason:f.reason.trim(),notes:f.notes.trim()||null,lines}:null
}
export default function PurchaseInvoicePanel(props:Props){
 const {runtime,identity}=useAuth()
 if(!isConnectedRuntime(runtime)||identity.status!=='AUTHORIZED'||!identity.permissions.includes('finance.ap.view')||!identity.permissions.includes('warehouse.procurement.view'))return null
 return <InvoiceWorkspace key={`${runtime.projectRef}:${identity.profile.id}:${identity.profile.rowVersion}:${identity.profile.roleRowVersion}:${identity.permissions.join('|')}`} {...props}/>
}
function InvoiceWorkspace({purchaseId,receiptRevision,onReceiptUpdated}:Props){
 const navigation=useTransactionSource('RECEIPT'),focus=navigation?.document.id===purchaseId&&navigation.document.focus?.kind==='PURCHASE_INVOICE'?navigation.document.focus:null
 const {runtime}=useAuth();if(!isConnectedRuntime(runtime))throw Error('Sesi invoice belum siap.')
 const client=useMemo(()=>getUatSupabaseClient(runtime),[runtime]),mutation=useProductionMutation('PURCHASE_INVOICE')
 const {beginRead,finishRead,isReadCurrent,run,reconcile,invalidate}=mutation
 const [data,setData]=useState<PurchaseInvoices|null>(null),[loading,setLoading]=useState(false),[error,setError]=useState(''),[form,setForm]=useState<Form|null>(null)
 const [sources,setSources]=useState<InvoiceSources|null>(null),[sourceSearch,setSourceSearch]=useState(''),sourceQuery=useRef('')
 const [reviewAction,setReviewAction]=useState('REVERSE')
 const [reverseDoc,setReverseDoc]=useState<PurchaseInvoice|null>(null),[reverseReason,setReverseReason]=useState(''),[confirmed,setConfirmed]=useState(false)
 const requested=useRef({purchase:purchaseId,offset:focus?.page_offset??0}),sequence=useRef(0),pendingRef=useRef(mutation.pending),busyRef=useRef(mutation.busy);pendingRef.current=mutation.pending;busyRef.current=mutation.busy
 const load=useCallback(async()=>{
  const s=++sequence.current,ticket=beginRead(),query={...requested.current};setLoading(true);setError('');setConfirmed(false)
  try{
   if(!query.purchase){setData(null);return false}
   const r=await client.rpc('erp_cp7_get_purchase_invoices_v1',{p_purchase:query.purchase,p_offset:query.offset,p_limit:25})
   if(!isReadCurrent(ticket)||s!==sequence.current)return false
   if(r.error)throw r.error
   const w=parsePurchaseInvoices(r.data,query.purchase);if(w.page.offset!==query.offset)throw Error('Halaman invoice tidak cocok.')
   if(focus&&query.offset===focus.page_offset&&!w.page.rows.some(x=>x.id===focus.id))throw Error('Invoice sumber berubah. Buka ulang sumber dari buku.');setData(w);return finishRead(ticket)
  }catch(e){if(isReadCurrent(ticket)){setData(null);setError(normalizeClientError(e).message)};return false}
  finally{if(s===sequence.current)setLoading(false)}
 },[client,beginRead,finishRead,isReadCurrent,focus])
 useEffect(()=>{
  // During our own mutation the outcome handler owns the complete read-back.
  // An external receipt revision (for example its first POST) reloads here.
  if(busyRef.current)return
  let selected=purchaseId
  if(pendingRef.current){try{const d=procurementObject(procurementObject(pendingRef.current.payload).document);if(typeof d.purchase_id==='string')selected=d.purchase_id}catch{/* Shared recovery refuses corrupted envelopes. */}}
  if(requested.current.purchase!==selected){requested.current={purchase:selected,offset:0};setForm(null);setReverseDoc(null);setConfirmed(false)}
  void load()
 },[purchaseId,receiptRevision,load])
 const handlers:ProductionMutationHandlers={
  send:envelope=>{const p=procurementObject(envelope.payload);return client.rpc('erp_cp7_save_purchase_invoice_v1',{p_action:envelope.action,p_payload:p.document as Json,p_request:envelope.id,p_expected:p.expected_version as string|null})},
  validate:(r,e)=>{parsePurchaseInvoiceOutcome(r,e.id,e.action,procurementObject(e.payload).document as Json)},
  retire:(r,e)=>{const out=parsePurchaseInvoiceOutcome(r,e.id,e.action,procurementObject(e.payload).document as Json);requested.current={purchase:out.purchase_id,offset:0};setForm(null);setReverseDoc(null);setConfirmed(false);setData(null)},
  reload:async()=>{if(!requested.current.purchase||!await onReceiptUpdated(requested.current.purchase)){invalidate();setData(null);return false};return load()},
 }
 const locked=mutation.writerLocked||loading,stale=Boolean(form&&(!data||form.purchaseId!==data.purchase_id||(form.combined?.id?!data.page.rows.some(d=>d.id===form.combined?.id&&d.row_version===form.combined.version&&d.status==='DRAFT'):form.version!==data.purchase_version))),payload=form?document(form):null
 const activeReverse=reverseDoc&&data?.page.rows.find(d=>d.id===reverseDoc.id&&d.row_version===reverseDoc.row_version&&d.status===(reviewAction==='POST_DOCUMENT'||reviewAction==='DELETE_DOCUMENT'?'DRAFT':'POSTED'))
 const available=data?.receipt_lines.filter(hasInvoiceCapacity)??[],conflict=data?.receipt_lines.some(l=>l.remaining_qty.startsWith('-'))
 const write=(action:string,p:Json,version:string|null)=>run(action,{document:p,expected_version:version},null,handlers)
 const newInvoice=(combined=false)=>{if(!data?.supplier_id)return;const at=cp6WibDateTimeInput();setReverseDoc(null);setSources(null);setSourceSearch('');setForm({...(combined?{combined:{id:null,version:null,supplier:data.supplier_id,originalAt:null}}:{}),purchaseId:data.purchase_id,version:data.purchase_version,number:'',date:at.slice(0,10),at,due:'',reason:'Invoice supplier sudah dicocokkan dengan penerimaan',notes:'',reviewed:false,lines:available.map(l=>({id:l.id,purchaseId:data.purchase_id,purchaseNumber:data.purchase_number,name:l.material_name,unit:l.unit_code,selected:true,qty:l.remaining_qty,price:'',discount:'0'}))})}
 const editInvoice=(d:PurchaseInvoice)=>{if(!data?.supplier_id||d.status!=='DRAFT')return;setReverseDoc(null);setSources(null);setSourceSearch('');setForm({combined:{id:d.id,version:d.row_version,supplier:data.supplier_id,originalAt:d.received_at},purchaseId:data.purchase_id,version:data.purchase_version,number:d.number,date:d.invoice_date,at:cp6WibDateTimeInput(d.received_at),due:d.due_date??'',reason:'Koreksi draft invoice supplier',notes:d.notes??'',reviewed:false,lines:d.lines.map(l=>({id:l.purchase_item_id,purchaseId:l.purchase_id,purchaseNumber:l.purchase_number,notes:l.notes,name:l.material_name,unit:l.unit_code,selected:true,qty:l.qty,price:l.unit_price,discount:l.discount}))})}
 const loadSources=async(offset=0)=>{if(!data?.supplier_id||!form?.combined||locked)return;const query=offset?sourceQuery.current:sourceSearch.trim(),ticket=beginRead(),s=++sequence.current;sourceQuery.current=query;setLoading(true);setError('')
  try{const r=await client.rpc('erp_cp7_get_invoice_sources_v1',{p_purchase:data.purchase_id,p_q:query,p_offset:offset,p_limit:10});if(!isReadCurrent(ticket)||s!==sequence.current)return;if(r.error)throw r.error
   const v=parseInvoiceSources(r.data,data.purchase_id,data.supplier_id);if(v.page.offset!==offset)throw Error('Halaman penerimaan invoice tidak cocok.');if(finishRead(ticket))setSources(v)
  }catch(e){if(isReadCurrent(ticket))setError(normalizeClientError(e).message)}finally{if(s===sequence.current)setLoading(false)}
 }
 const addSource=(r:InvoiceSource)=>setForm(f=>{if(!f?.combined)return f;const extra=r.lines.filter(l=>hasInvoiceCapacity(l)&&!f.lines.some(x=>x.id===l.id));if(f.lines.length+extra.length>100)return f;return {...f,reviewed:false,lines:[...f.lines,...extra.map(l=>({id:l.id,purchaseId:r.id,purchaseNumber:r.number,name:l.material_name,unit:l.unit_code,selected:true,qty:l.remaining_qty,price:'',discount:'0'}))]}})
 const review=(d:PurchaseInvoice,action:string)=>{setReverseDoc(d);setReviewAction(action);setReverseReason('');setConfirmed(false)}
 const reviewTitle=reviewAction==='POST_DOCUMENT'?'Sahkan draft invoice':reviewAction==='DELETE_DOCUMENT'?'Hapus draft invoice':'Batalkan invoice'
 const reviewLabel=reviewAction==='POST_DOCUMENT'?'Konfirmasi pengesahan invoice':reviewAction==='DELETE_DOCUMENT'?'Konfirmasi hapus draft invoice':'Konfirmasi pembatalan invoice'
 const updateLine=(id:string,delta:Partial<Form['lines'][number]>)=>setForm(f=>f?{...f,reviewed:false,lines:f.lines.map(l=>l.id===id?{...l,...delta}:l)}:f)
 return <section className="panel cproc-invoices" aria-label="Invoice supplier">
  <div className="cproc-heading"><div><div className="eyebrow">DOKUMEN SUPPLIER</div><h2>Invoice supplier</h2><p>{data?`Penerimaan ${data.purchase_number}`:'Pilih penerimaan untuk mencocokkan invoice supplier.'}</p></div>{requested.current.purchase?<button type="button" disabled={mutation.busy||loading} onClick={()=>void handlers.reload()}>Muat ulang invoice</button>:null}</div>
  {requested.current.purchase||mutation.pending||error?<ProductionRecoveryNotice recovery={{...mutation,notice:mutation.notice?'Invoice supplier sudah diperbarui.':'',...(mutation.pending&&!mutation.corruptedEnvelope?{error:'Hasil pencatatan invoice belum diketahui. Periksa hasil transaksi dengan kiriman yang sama.',blockReason:''}:{})}} onReconcile={()=>reconcile(handlers)} className="cproc-review"/>:null}
  {error?<p role="alert">{error}</p>:null}{loading?<p role="status">Memuat invoice…</p>:null}
  {data?<><p className="cproc-help">Nilai dokumen invoice ditampilkan di sini. Sisa utang mengikuti pembayaran dan kredit supplier yang telah dialokasikan.</p>
   <div className="cproc-grid">{data.receipt_lines.map(l=><article className="cproc-item" key={l.id}><strong>{l.material_name}</strong><p>Diterima {numberText(l.receipt_qty)} {l.unit_code} · sudah ditagih {numberText(l.invoiced_qty)} {l.unit_code}</p><small>{l.invoice_match_state==='DIRECT_FINAL'?'Harga sudah final saat penerimaan':`Belum dicocokkan: ${numberText(l.remaining_qty)} ${l.unit_code}`}</small></article>)}</div>
   {conflict?<p role="alert">Alokasi invoice melebihi penerimaan yang dapat ditagih. Periksa dokumen sumber sebelum menambah invoice.</p>:null}
   {data.purchase_status==='POSTED'&&available.length&&!conflict?<button className="primary-btn" type="button" disabled={locked||!data.capabilities.finalize||Boolean(form)} onClick={()=>newInvoice()}>Catat invoice supplier</button>:null}
   {data.purchase_status==='POSTED'&&available.length&&!conflict?<button type="button" disabled={locked||!data.capabilities.finalize||Boolean(form)} onClick={()=>newInvoice(true)}>Gabungkan penerimaan dalam invoice</button>:null}
   {form?<form className="cproc-editor" onSubmit={e=>{e.preventDefault();if(payload&&!locked&&!stale&&data.capabilities.finalize)void write(form.combined?'SAVE_DOCUMENT':'FINALIZE',payload,form.combined?form.combined.version:form.version)}}>
    <div className="cproc-heading"><h3>{form.combined?.id?'Edit draft invoice':form.combined?'Gabungkan penerimaan':'Invoice baru'} · {data.purchase_number}</h3><button type="button" disabled={locked} onClick={()=>setForm(null)}>Tutup formulir invoice</button></div>
    {stale?<p role="alert">Penerimaan atau alokasinya berubah. Buka formulir baru dengan data terbaru.</p>:null}
    <fieldset disabled={locked||stale}><div className="cproc-grid">
     <label>Nomor invoice supplier<input aria-label="Nomor invoice supplier" required value={form.number} onChange={e=>setForm({...form,number:e.target.value,reviewed:false})}/></label>
     <label>Tanggal pada invoice<input aria-label="Tanggal invoice supplier" type="date" required value={form.date} onChange={e=>setForm({...form,date:e.target.value,reviewed:false})}/></label>
     <label>Invoice diterima · WIB<input aria-label="Waktu invoice diterima WIB" type="datetime-local" required value={form.at} onChange={e=>setForm({...form,at:e.target.value,reviewed:false})}/></label>
     <label>Jatuh tempo<input aria-label="Jatuh tempo invoice supplier" type="date" value={form.due} onChange={e=>setForm({...form,due:e.target.value,reviewed:false})}/></label>
    </div>
    {form.combined?<section className="cproc-review"><h4>Penerimaan dari supplier yang sama</h4><div className="cproc-actions"><label>Cari nomor penerimaan<input aria-label="Cari penerimaan invoice" value={sourceSearch} onChange={e=>setSourceSearch(e.target.value)} maxLength={120}/></label><button type="button" onClick={()=>void loadSources()}>Cari penerimaan invoice</button></div>
     {sources?.page.rows.map(r=><article className="cproc-item" key={r.id}><strong>{r.number}</strong><small>{formatCp6WibDateTime(r.physical_at)} · {r.lines.length} baris</small><button type="button" disabled={!r.lines.some(l=>hasInvoiceCapacity(l)&&!form.lines.some(x=>x.id===l.id))||form.lines.length+r.lines.filter(l=>hasInvoiceCapacity(l)&&!form.lines.some(x=>x.id===l.id)).length>100} onClick={()=>addSource(r)}>Tambahkan {r.number}</button></article>)}
     {sources?<div className="cproc-pagination"><span>Total {sources.page.total} penerimaan</span><button type="button" disabled={!sources.page.offset} onClick={()=>void loadSources(Math.max(0,sources.page.offset-10))}>Penerimaan invoice sebelumnya</button><button type="button" disabled={sources.page.next_offset===null} onClick={()=>void loadSources(sources.page.next_offset??0)}>Penerimaan invoice berikutnya</button></div>:null}<p>Periksa seluruh baris yang dipilih. Harga harus sesuai dokumen supplier; draft belum mengubah utang atau biaya.</p></section>:null}
    {form.lines.map((l,i)=><section className="cproc-line" key={l.id}><label className="cproc-check"><input type="checkbox" aria-label={`Tagih barang ${i+1}`} checked={l.selected} onChange={e=>updateLine(l.id,{selected:e.target.checked})}/>{l.name}{form.combined?` · ${l.purchaseNumber}`:''}</label><div className="cproc-grid">
     <label>Jumlah ditagih ({l.unit})<input aria-label={`Jumlah invoice ${i+1}`} inputMode="decimal" disabled={!l.selected} value={l.qty} onChange={e=>updateLine(l.id,{qty:e.target.value})}/></label>
     <label>Harga per {l.unit}<input aria-label={`Harga invoice ${i+1}`} inputMode="decimal" placeholder="Sesuai invoice" disabled={!l.selected} value={l.price} onChange={e=>updateLine(l.id,{price:e.target.value})}/></label>
     <label>Potongan baris (Rp)<input aria-label={`Potongan invoice ${i+1}`} inputMode="decimal" disabled={!l.selected} value={l.discount} onChange={e=>updateLine(l.id,{discount:e.target.value})}/></label>
    </div></section>)}
    <div className="cproc-grid"><label>Catatan invoice<input aria-label="Catatan invoice supplier" value={form.notes} onChange={e=>setForm({...form,notes:e.target.value,reviewed:false})}/></label><label>Alasan pencatatan<input aria-label="Alasan invoice supplier" required value={form.reason} onChange={e=>setForm({...form,reason:e.target.value,reviewed:false})}/></label></div>
    <p>Jumlah dapat ditagih bertahap. Harga akan memperbarui biaya persediaan dan perhitungan biaya barang yang telah diproses.</p>
    <label className="cproc-check"><input type="checkbox" aria-label="Invoice sudah diperiksa" checked={form.reviewed} onChange={e=>setForm({...form,reviewed:e.target.checked})}/>Nomor, tanggal, jumlah, harga dan potongan sudah sesuai invoice supplier.</label>
    <button className="primary-btn" disabled={locked||stale||!payload||!data.capabilities.finalize}>{form.combined?'Simpan draft invoice':'Sahkan invoice supplier'}</button></fieldset>
   </form>:null}
   <h3>Riwayat invoice</h3>{!data.page.rows.length?<p>Belum ada invoice yang dicocokkan.</p>:null}
   {data.page.rows.map(d=><article className="cproc-line" key={d.id}><div className="cproc-heading"><div><h4>{d.number}</h4><span className={`cproc-status ${d.status.toLowerCase()}`}>{d.status==='POSTED'?'Invoice disahkan':d.status==='REVERSED'?'Invoice dibatalkan':'Draft invoice'}</span></div><strong>Nilai dokumen Rp{numberText(d.document_net_amount)}</strong></div><p>Tanggal invoice {d.invoice_date} · diterima {formatCp6WibDateTime(d.received_at)}{d.due_date?` · jatuh tempo ${d.due_date}`:''}</p>
    {d.lines.map(l=><div className="cproc-item" key={l.id}><strong>{l.material_name}</strong><small>{l.purchase_number} · {numberText(l.qty)} {l.unit_code} × Rp{numberText(l.unit_price)}</small><small>Potongan Rp{numberText(l.discount)} · nilai Rp{numberText(l.net_amount)}</small></div>)}{d.notes?<p>{d.notes}</p>:null}
    {!d.single_receipt?<p>Invoice ini mencakup {new Set(d.lines.map(l=>l.purchase_id)).size} penerimaan. Semua baris ditampilkan untuk diperiksa.</p>:null}
    {d.status==='POSTED'&&data.capabilities.reverse?<button type="button" disabled={locked||Boolean(form)} onClick={()=>review(d,d.single_receipt?'REVERSE':'REVERSE_DOCUMENT')}>Tinjau pembatalan {d.number}</button>:null}
    {d.status==='DRAFT'&&data.capabilities.finalize?<div className="cproc-actions"><button type="button" disabled={locked||Boolean(form)} onClick={()=>editInvoice(d)}>Edit draft {d.number}</button><button type="button" disabled={locked||Boolean(form)} onClick={()=>review(d,'POST_DOCUMENT')}>Tinjau pengesahan {d.number}</button><button type="button" disabled={locked||Boolean(form)} onClick={()=>review(d,'DELETE_DOCUMENT')}>Tinjau hapus draft {d.number}</button></div>:null}
   </article>)}
   {reverseDoc?<section className="cproc-review"><h3>{reviewTitle} {reverseDoc.number}</h3><p>{reviewAction==='POST_DOCUMENT'?'Pengesahan mengakui tagihan dan memperbarui biaya seluruh penerimaan terkait.':reviewAction==='DELETE_DOCUMENT'?'Draft dihapus tanpa mengubah kuantitas, utang atau biaya.':'Pembatalan mengoreksi alokasi invoice, utang dan biaya terkait. Kuantitas barang yang diterima tetap mengikuti penerimaan.'}</p><label>Alasan tindakan<input aria-label="Alasan pembatalan invoice" disabled={locked||Boolean(form)||!activeReverse} value={reverseReason} onChange={e=>{setReverseReason(e.target.value);setConfirmed(false)}}/></label><label className="cproc-check"><input type="checkbox" aria-label={reviewLabel} disabled={locked||Boolean(form)||!activeReverse} checked={confirmed} onChange={e=>setConfirmed(e.target.checked)}/>Saya telah memeriksa seluruh baris invoice ini.</label>{!activeReverse?<p role="alert">Versi invoice berubah. Buka kembali pemeriksaan tindakan.</p>:null}<div className="cproc-actions"><button type="button" disabled={locked||Boolean(form)||!activeReverse||!confirmed||!reverseReason.trim()||!(reviewAction==='REVERSE'||reviewAction==='REVERSE_DOCUMENT'?data.capabilities.reverse:data.capabilities.finalize)} onClick={()=>void write(reviewAction,{purchase_id:data.purchase_id,invoice_id:reverseDoc.id,reason:reverseReason.trim(),...(reviewAction==='REVERSE'?{}:{reviewed_purchase_ids:[...new Set(reverseDoc.lines.map(l=>l.purchase_id))].sort()})},reverseDoc.row_version)}>{reviewTitle} supplier</button><button type="button" disabled={mutation.busy} onClick={()=>setReverseDoc(null)}>Tutup pemeriksaan</button></div></section>:null}
   <div className="cproc-pagination"><span>{data.page.rows.length} dokumen · total {data.page.total}</span><button type="button" disabled={mutation.busy||loading||data.page.offset===0} onClick={()=>{requested.current.offset=Math.max(0,data.page.offset-25);void load()}}>Invoice sebelumnya</button><button type="button" disabled={mutation.busy||loading||data.page.next_offset===null} onClick={()=>{requested.current.offset=data.page.next_offset??0;void load()}}>Invoice berikutnya</button></div>
  </>:null}
 </section>
}
