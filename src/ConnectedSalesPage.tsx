import {useCallback,useEffect,useMemo,useRef,useState} from 'react'
import {useAuth} from './auth/AuthProvider'
import {isConnectedRuntime} from './config/runtime'
import {getUatSupabaseClient} from './lib/supabase'
import {normalizeClientError} from './lib/clientError'
import {formatCp6WibDateTime} from './cp6BusinessTime'
import {formatReceiptDecimal as numberText} from './procurementContract'
import {parseSalesRead,parseSalesOutcome,salesStatuses,type SalesRead,type SalesStatus} from './salesReadContract'
import {useProductionMutation,type ProductionMutationHandlers} from './useProductionMutation'
import ProductionRecoveryNotice from './ProductionRecoveryNotice'
import SalesDraftPanel from './SalesDraftPanel'
import type {Json} from './types/database.preconnect'
import './procurement-connected.css'
const labels:Record<SalesStatus,string>={DRAFT:'Draft · stok dipesan',POSTED:'Belum lunas',PARTIAL_PAID:'Dibayar sebagian',PAID:'Lunas',CANCELLED:'Draft dibatalkan',REVERSED:'Penjualan dibatalkan'}
const money=(v:string)=>`Rp${numberText(v)}`
export default function ConnectedSalesPage(){
 const {runtime,identity}=useAuth()
 if(!isConnectedRuntime(runtime)||identity.status!=='AUTHORIZED'||!identity.permissions.includes('sales.invoice.view'))return <section className="panel" role="alert">Hak melihat invoice diperlukan.</section>
 return <Workspace key={`${runtime.projectRef}:${identity.profile.id}:${identity.profile.rowVersion}:${identity.profile.roleRowVersion}:${identity.permissions.join('|')}`}/>
}
function Workspace(){
 const {runtime,identity}=useAuth();if(!isConnectedRuntime(runtime)||identity.status!=='AUTHORIZED')throw Error('Sesi penjualan belum siap.')
 const client=useMemo(()=>getUatSupabaseClient(runtime),[runtime]),finance=identity.permissions.includes('finance.ar.view')
 const mutation=useProductionMutation('SALES'),{beginRead,finishRead,isReadCurrent,run,reconcile}=mutation
 const [data,setData]=useState<SalesRead|null>(null),[busy,setBusy]=useState(false),[error,setError]=useState(''),[q,setQ]=useState(''),[status,setStatus]=useState('')
 const [draft,setDraft]=useState<{initial:NonNullable<SalesRead['detail']>|null;key:string}|null>(null)
 const [reviewed,setReviewed]=useState(false),[reason,setReason]=useState('Invoice dan barang sudah diperiksa')
 const requested=useRef({q:'',status:'',offset:0,sale_id:null as string|null}),sequence=useRef(0)
 const load=useCallback(async()=>{
  const query={...requested.current},s=++sequence.current,ticket=beginRead();setBusy(true);setData(null);setError('');setReviewed(false)
  try{const r=await client.rpc('erp_cp7_get_sales_v1',{p_query:{...query,status:query.status||null,limit:25}});if(s!==sequence.current||!isReadCurrent(ticket))return false;if(r.error)throw r.error
   const d=parseSalesRead(r.data,finance);if(d.page.offset!==query.offset||d.page.limit!==25||(d.detail?.id??null)!==query.sale_id)throw Error('Pilihan invoice berubah. Muat ulang invoice.')
   setData(d);return finishRead(ticket)
  }catch(e){if(s===sequence.current&&isReadCurrent(ticket))setError(normalizeClientError(e).message);return false}finally{if(s===sequence.current)setBusy(false)}
 },[client,finance,beginRead,finishRead,isReadCurrent])
 useEffect(()=>{void load();return()=>{++sequence.current}},[load])
 const d=data?.detail,f=d?.financial
 const envelope=(value:Json)=>{const p=value as {document:Json;expected_version:string|null};if(!p||typeof p!=='object'||p.expected_version!==null&&typeof p.expected_version!=='string'||!p.document||typeof p.document!=='object'||Array.isArray(p.document))throw Error('Permintaan invoice belum lengkap.');return p}
 const handlers:ProductionMutationHandlers={
  send:e=>{const p=envelope(e.payload);return client.rpc('erp_cp7_save_sale_v1',{p_action:e.action,p_payload:p.document,p_request:e.id,p_expected:p.expected_version})},
  validate:(v,e)=>{parseSalesOutcome(v,e.id,e.action,(envelope(e.payload).document as {sale_id?:string}).sale_id??null)},
  retire:(v,e)=>{const r=parseSalesOutcome(v,e.id,e.action,(envelope(e.payload).document as {sale_id?:string}).sale_id??null);requested.current.sale_id=r.sale_id;setData(null);setReviewed(false);setDraft(null)},reload:load,
 }
 const canPost=finance&&identity.permissions.includes('sales.invoice.post'),canCancel=finance&&identity.permissions.includes('sales.invoice.edit_draft'),locked=busy||mutation.writerLocked
 const canCreate=finance&&identity.permissions.includes('sales.invoice.create'),canEdit=finance&&identity.permissions.includes('sales.invoice.edit_draft')
 const stale=!!draft?.initial&&(!d||d.id!==draft.initial.id||d.row_version!==draft.initial.row_version||d.review_token!==draft.initial.review_token||d.status!=='DRAFT')
 const write=(action:'POST'|'CANCEL')=>{if(d?.review_token&&!locked&&reviewed&&reason.trim().length>=5)void run(action,{document:{sale_id:d.id,review_token:d.review_token,change_reason:reason.trim()},expected_version:d.row_version},null,handlers)}
 return <section className="cproc csales">
  <header className="panel cproc-heading"><div><div className="eyebrow">PENJUALAN</div><h1>Penjualan & Invoice</h1><p>Periksa invoice, barang yang dipesan, retur, dan sisa pembayaran.</p></div><button disabled={busy||mutation.busy} onClick={()=>void load()}>Muat ulang invoice</button></header>
  {canCreate?<button className="primary-btn" disabled={locked||!!draft} onClick={()=>setDraft({initial:null,key:crypto.randomUUID()})}>Buat invoice</button>:null}
  <ProductionRecoveryNotice recovery={mutation} onReconcile={()=>reconcile(handlers)} className="panel"/>
  {error?<p className="panel" role="alert">{error}</p>:null}{busy?<p role="status">Memuat invoice…</p>:null}
  {draft?<SalesDraftPanel key={draft.key} initial={draft.initial} locked={locked} stale={stale} onClose={()=>setDraft(null)} onSave={(action,document,version)=>{if(!locked&&!stale)void run(action,{document,expected_version:version},null,handlers)}}/>:null}
  <form className="panel cproc-search" onSubmit={e=>{e.preventDefault();requested.current={q:q.trim(),status,offset:0,sale_id:null};void load()}}>
   <label>Cari nomor invoice atau pelanggan<input aria-label="Cari invoice" value={q} maxLength={120} onChange={e=>setQ(e.target.value)}/></label>
   <label>Status invoice<select value={status} aria-label="Status invoice" onChange={e=>setStatus(e.target.value)}><option value="">Semua status</option>{salesStatuses.map(s=><option key={s} value={s}>{labels[s]}</option>)}</select></label>
   <button disabled={busy||mutation.busy}>Cari invoice</button>
  </form>
  <div className="cproc-layout"><section className="panel" aria-label="Daftar invoice"><h2>Daftar invoice</h2>
   {data?.page.rows.length===0?<p>Belum ada invoice sesuai pencarian.</p>:null}
   {data?.page.rows.map(r=><button className="cproc-receipt" key={r.id} aria-pressed={r.id===d?.id} disabled={busy||mutation.busy} onClick={()=>{requested.current.sale_id=r.id;void load()}}><span><strong>{r.number}</strong><small>{r.customer_name} · {numberText(r.qty_pcs)} PCS</small><small>{formatCp6WibDateTime(r.physical_at)}</small></span><span><small>{labels[r.status]}</small>{r.financial?<strong>{money(r.financial.net_total)}</strong>:null}</span></button>)}
   {data?<div className="cproc-pagination"><span>Total {data.page.total}</span><button disabled={busy||mutation.busy||data.page.offset===0} onClick={()=>{requested.current.offset=Math.max(0,data.page.offset-25);void load()}}>Invoice sebelumnya</button><button disabled={busy||mutation.busy||data.page.next_offset===null} onClick={()=>{requested.current.offset=data.page.next_offset??0;void load()}}>Invoice berikutnya</button></div>:null}
  </section><aside className="panel" aria-label="Rincian invoice">{d?<>
   <div className="eyebrow">{labels[d.status]}</div><h2>{d.number}</h2><p>{d.customer_name} · {d.location_name??'Lokasi belum tercatat'}</p><p>{formatCp6WibDateTime(d.physical_at)}{d.due_date?` · jatuh tempo ${d.due_date}`:''}</p>
   <p>{numberText(d.qty_pcs)} PCS dalam invoice · {numberText(d.reserved_qty)} PCS masih dipesan · {numberText(d.returned_qty)} PCS sudah diretur.</p>
   {d.status==='DRAFT'?<p>Draft memesan stok siap jual. Piutang dan penjualan terbentuk saat invoice disahkan.</p>:null}
   {f?<div className="cproc-review" aria-label="Nilai invoice"><p>Bruto <strong>{money(f.gross_total)}</strong></p><p>Retur <strong>{money(f.return_total)}</strong> · bersih <strong>{money(f.net_total)}</strong></p><p>Pembayaran tercatat <strong>{money(f.paid_total)}</strong></p>{f.open_balance!==null?<p>Sisa pembayaran <strong>{money(f.open_balance)}</strong></p>:<p>{f.state==='DRAFT_PREVIEW'?'Nilai draft belum menjadi piutang.':'Dokumen ini sudah dibatalkan.'}</p>}</div>:null}
   {d.notes?<p>{d.notes}</p>:null}
   {d.items.map(i=><article className="cproc-item" key={i.id}><h3>{i.commercial_sku} · {i.size_code}</h3><p>{i.product_name} · {i.brand_name} · {numberText(i.qty_pcs)} PCS</p>{i.financial?<p>{money(i.financial.unit_price)} per PCS · potongan {money(i.financial.discount)} · jumlah <strong>{money(i.financial.line_total)}</strong></p>:null}<small>SKU fisik {i.product_sku}. Kelompok invoice mengikuti tanggal transaksi.</small>{i.notes?<p>{i.notes}</p>:null}</article>)}
   {d.status==='DRAFT'&&canEdit?<button disabled={locked||!!draft} onClick={()=>setDraft({initial:d,key:crypto.randomUUID()})}>Edit draft invoice</button>:null}
   {d.status==='DRAFT'&&(canPost||canCancel)?<div className="cproc-review"><label>Catatan tindakan<input aria-label="Catatan tindakan invoice" maxLength={1000} disabled={locked} value={reason} onChange={e=>{setReason(e.target.value);setReviewed(false)}}/></label><label className="cproc-check"><input type="checkbox" aria-label="Invoice sudah diperiksa" disabled={locked} checked={reviewed} onChange={e=>setReviewed(e.target.checked)}/>Pelanggan, barang, harga, dan tanggal sudah saya periksa.</label><p>Pengesahan mencatat penjualan dan piutang. Pembatalan draft mengembalikan barang yang dipesan ke stok siap jual.</p>{canPost?<button className="primary-btn" disabled={locked||!!draft||!reviewed||reason.trim().length<5} onClick={()=>write('POST')}>Sahkan invoice</button>:null}{canCancel?<button disabled={locked||!!draft||!reviewed||reason.trim().length<5} onClick={()=>write('CANCEL')}>Batalkan draft invoice</button>:null}</div>:null}
  </>:<><h2>Rincian invoice</h2><p>Pilih invoice untuk memeriksa barang dan pembayaran yang tercatat.</p></>}</aside></div>
 </section>
}
