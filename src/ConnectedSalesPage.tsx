import {useCallback,useEffect,useMemo,useRef,useState} from 'react'
import {useAuth} from './auth/AuthProvider'
import {isConnectedRuntime} from './config/runtime'
import {getUatSupabaseClient} from './lib/supabase'
import {normalizeClientError} from './lib/clientError'
import {formatCp6WibDateTime} from './cp6BusinessTime'
import {formatReceiptDecimal as numberText} from './procurementContract'
import {parseSalesRead,salesStatuses,type SalesRead,type SalesStatus} from './salesReadContract'
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
 const [data,setData]=useState<SalesRead|null>(null),[busy,setBusy]=useState(false),[error,setError]=useState(''),[q,setQ]=useState(''),[status,setStatus]=useState('')
 const requested=useRef({q:'',status:'',offset:0,sale_id:null as string|null}),sequence=useRef(0)
 const load=useCallback(async()=>{
  const query={...requested.current},s=++sequence.current;setBusy(true);setData(null);setError('')
  try{const r=await client.rpc('erp_cp7_get_sales_v1',{p_query:{...query,status:query.status||null,limit:25}});if(s!==sequence.current)return;if(r.error)throw r.error
   const d=parseSalesRead(r.data,finance);if(d.page.offset!==query.offset||d.page.limit!==25||(d.detail?.id??null)!==query.sale_id)throw Error('Pilihan invoice berubah. Muat ulang invoice.')
   setData(d)
  }catch(e){if(s===sequence.current)setError(normalizeClientError(e).message)}finally{if(s===sequence.current)setBusy(false)}
 },[client,finance])
 useEffect(()=>{void load();return()=>{++sequence.current}},[load])
 const d=data?.detail,f=d?.financial
 return <section className="cproc csales">
  <header className="panel cproc-heading"><div><div className="eyebrow">PENJUALAN</div><h1>Penjualan & Invoice</h1><p>Periksa invoice, barang yang dipesan, retur, dan sisa pembayaran.</p></div><button disabled={busy} onClick={()=>void load()}>Muat ulang invoice</button></header>
  {error?<p className="panel" role="alert">{error}</p>:null}{busy?<p role="status">Memuat invoice…</p>:null}
  <form className="panel cproc-search" onSubmit={e=>{e.preventDefault();requested.current={q:q.trim(),status,offset:0,sale_id:null};void load()}}>
   <label>Cari nomor invoice atau pelanggan<input aria-label="Cari invoice" value={q} maxLength={120} onChange={e=>setQ(e.target.value)}/></label>
   <label>Status invoice<select value={status} aria-label="Status invoice" onChange={e=>setStatus(e.target.value)}><option value="">Semua status</option>{salesStatuses.map(s=><option key={s} value={s}>{labels[s]}</option>)}</select></label>
   <button disabled={busy}>Cari invoice</button>
  </form>
  <div className="cproc-layout"><section className="panel" aria-label="Daftar invoice"><h2>Daftar invoice</h2>
   {data?.page.rows.length===0?<p>Belum ada invoice sesuai pencarian.</p>:null}
   {data?.page.rows.map(r=><button className="cproc-receipt" key={r.id} aria-pressed={r.id===d?.id} disabled={busy} onClick={()=>{requested.current.sale_id=r.id;void load()}}><span><strong>{r.number}</strong><small>{r.customer_name} · {numberText(r.qty_pcs)} PCS</small><small>{formatCp6WibDateTime(r.physical_at)}</small></span><span><small>{labels[r.status]}</small>{r.financial?<strong>{money(r.financial.net_total)}</strong>:null}</span></button>)}
   {data?<div className="cproc-pagination"><span>Total {data.page.total}</span><button disabled={busy||data.page.offset===0} onClick={()=>{requested.current.offset=Math.max(0,data.page.offset-25);void load()}}>Invoice sebelumnya</button><button disabled={busy||data.page.next_offset===null} onClick={()=>{requested.current.offset=data.page.next_offset??0;void load()}}>Invoice berikutnya</button></div>:null}
  </section><aside className="panel" aria-label="Rincian invoice">{d?<>
   <div className="eyebrow">{labels[d.status]}</div><h2>{d.number}</h2><p>{d.customer_name} · {d.location_name??'Lokasi belum tercatat'}</p><p>{formatCp6WibDateTime(d.physical_at)}{d.due_date?` · jatuh tempo ${d.due_date}`:''}</p>
   <p>{numberText(d.qty_pcs)} PCS dalam invoice · {numberText(d.reserved_qty)} PCS masih dipesan · {numberText(d.returned_qty)} PCS sudah diretur.</p>
   {d.status==='DRAFT'?<p>Draft memesan stok siap jual. Piutang dan penjualan terbentuk saat invoice disahkan.</p>:null}
   {f?<div className="cproc-review" aria-label="Nilai invoice"><p>Bruto <strong>{money(f.gross_total)}</strong></p><p>Retur <strong>{money(f.return_total)}</strong> · bersih <strong>{money(f.net_total)}</strong></p><p>Pembayaran tercatat <strong>{money(f.paid_total)}</strong></p>{f.open_balance!==null?<p>Sisa pembayaran <strong>{money(f.open_balance)}</strong></p>:<p>{f.state==='DRAFT_PREVIEW'?'Nilai draft belum menjadi piutang.':'Dokumen ini sudah dibatalkan.'}</p>}</div>:null}
   {d.notes?<p>{d.notes}</p>:null}
   {d.items.map(i=><article className="cproc-item" key={i.id}><h3>{i.commercial_sku} · {i.size_code}</h3><p>{i.product_name} · {i.brand_name} · {numberText(i.qty_pcs)} PCS</p>{i.financial?<p>{money(i.financial.unit_price)} per PCS · potongan {money(i.financial.discount)} · jumlah <strong>{money(i.financial.line_total)}</strong></p>:null}<small>SKU fisik {i.product_sku}. Kelompok invoice mengikuti tanggal transaksi.</small>{i.notes?<p>{i.notes}</p>:null}</article>)}
  </>:<><h2>Rincian invoice</h2><p>Pilih invoice untuk memeriksa barang dan pembayaran yang tercatat.</p></>}</aside></div>
 </section>
}
