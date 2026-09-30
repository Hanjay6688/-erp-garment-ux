import {useCallback,useEffect,useMemo,useRef,useState} from 'react'
import {useAuth} from './auth/AuthProvider'
import {isConnectedRuntime} from './config/runtime'
import {getUatSupabaseClient} from './lib/supabase'
import {normalizeClientError} from './lib/clientError'
import {formatCp6WibDateTime} from './cp6BusinessTime'
import {formatReceiptDecimal} from './procurementContract'
import {parseSalesRead,salesStatuses,type SalesRead,type SalesStatus} from './salesReadContract'
import {financialRecoveryBlocked,financialRecoveryMessage,useFinancialRecoveryGate} from './useFinancialRecoveryGate'
import './procurement-connected.css'

const labels:Record<SalesStatus,string>={DRAFT:'Draft · belum menjadi piutang',POSTED:'Belum lunas',PARTIAL_PAID:'Dibayar sebagian',PAID:'Lunas',CANCELLED:'Draft dibatalkan',REVERSED:'Penjualan dibatalkan'}
const money=(value:string)=>'Rp'+formatReceiptDecimal(value)
type Query={q:string;status:string;offset:number;sale_id:string|null}
export default function ConnectedReceivablesPage(){
 const {runtime,identity}=useAuth()
 if(!isConnectedRuntime(runtime)||identity.status!=='AUTHORIZED'||!identity.permissions.includes('finance.ar.view')||!identity.permissions.includes('sales.invoice.view'))return <section className="panel" role="alert">Hak melihat piutang pelanggan dan invoice diperlukan.</section>
 return <Workspace key={`${runtime.projectRef}:${identity.profile.id}:${identity.profile.rowVersion}:${identity.profile.roleRowVersion}:${identity.permissions.join('|')}`}/>
}

function Workspace(){
 const {runtime,identity}=useAuth();if(!isConnectedRuntime(runtime)||identity.status!=='AUTHORIZED')throw Error('Sesi piutang belum siap.')
 const client=useMemo(()=>getUatSupabaseClient(runtime),[runtime]),seq=useRef(0),selected=useRef<Query>({q:'',status:'',offset:0,sale_id:null})
 const [q,setQ]=useState(''),[status,setStatus]=useState(''),[data,setData]=useState<SalesRead|null>(null),[busy,setBusy]=useState(false),[error,setError]=useState('')
 const retire=useCallback(()=>{++seq.current;setData(null);setBusy(false);setError('')},[])
 const recoveryScope=`${runtime.projectRef}:${identity.profile.id}`,recoveryBlocked=useFinancialRecoveryGate(recoveryScope,retire)
 const load=useCallback(async(query:Query)=>{
  const ticket=++seq.current;setData(null);setBusy(true);setError('')
  try{
   if(financialRecoveryBlocked(recoveryScope))return
   const result=await client.rpc('erp_cp7_get_sales_v1',{p_query:{...query,status:query.status||null,limit:25}})
   if(ticket!==seq.current||financialRecoveryBlocked(recoveryScope))return
   if(result.error)throw result.error
   const read=parseSalesRead(result.data,true)
   if(read.page.offset!==query.offset||read.page.limit!==25||(read.detail?.id??null)!==query.sale_id||query.status&&read.page.rows.some(r=>r.status!==query.status))throw Error('Pilihan sumber piutang berubah. Muat ulang piutang.')
   setData(read)
  }catch(e){if(ticket===seq.current)setError(normalizeClientError(e).message)}finally{if(ticket===seq.current)setBusy(false)}
 },[client,recoveryScope])
 useEffect(()=>{void load(selected.current);return()=>{++seq.current}},[load])
 const submit=()=>{retire();selected.current={q:q.trim(),status,offset:0,sale_id:null};void load(selected.current)}
 const choose=(sale_id:string)=>{selected.current={...selected.current,sale_id};void load(selected.current)}
 const detail=data?.detail
 return <main className="cproc creceivables" aria-label="Piutang pelanggan dari invoice">
  <header className="panel cproc-heading"><div><div className="eyebrow">KEUANGAN</div><h1>Piutang Pelanggan</h1><p>Periksa invoice, retur tercatat, pembayaran, dan sisa tagihan pelanggan.</p></div><button disabled={busy} onClick={()=>{const unchanged=q.trim()===selected.current.q&&status===selected.current.status;if(unchanged)void load(selected.current);else submit()}}>Muat ulang piutang</button></header>
  <form className="panel cproc-search" aria-label="Filter piutang pelanggan" onSubmit={e=>{e.preventDefault();submit()}}>
   <label>Nomor invoice atau pelanggan<input aria-label="Cari sumber piutang" maxLength={120} value={q} onChange={e=>{retire();setQ(e.target.value)}}/></label>
   <label>Status invoice<select aria-label="Status sumber piutang" value={status} onChange={e=>{retire();setStatus(e.target.value)}}><option value="">Semua dokumen</option>{salesStatuses.map(s=><option value={s} key={s}>{labels[s]}</option>)}</select></label><button disabled={busy}>Cari piutang</button>
  </form>
  {busy?<p role="status">Membaca invoice dan sisa pembayaran…</p>:null}{error?<p className="panel" role="alert">{error}</p>:null}
  {recoveryBlocked?<p className="panel" role="alert">{financialRecoveryMessage}</p>:null}
  {!recoveryBlocked&&data?<>
   <section className="panel" aria-label="Basis sumber piutang"><p>Kondisi dokumen sekarang, dibaca {formatCp6WibDateTime(data.read_at)}. Pembayaran dan retur memakai status tercatat saat dibaca; ini bukan saldo historis pada tanggal tertentu.</p><p>Daftar ini berisi sumber invoice. Saldo awal dan penyesuaian buku yang tidak berasal dari invoice diperiksa melalui laporan keuangan. Nilai di setiap invoice tetap milik invoice tersebut, tanpa menutup tagihan pelanggan lain secara otomatis.</p></section>
   <div className="cproc-layout"><section className="panel" aria-label="Daftar sumber piutang"><h2>Invoice pelanggan</h2>
    {data.page.rows.length===0?<p>Tidak ada invoice sesuai pencarian.</p>:null}
    {data.page.rows.map(r=><button className="cproc-receipt" data-sale-id={r.id} key={r.id} aria-pressed={detail?.id===r.id} disabled={busy} onClick={()=>choose(r.id)}><span><strong>{r.number}</strong><small>{r.customer_name} · {labels[r.status]}</small><small>{r.due_date?'Jatuh tempo '+r.due_date:'Jatuh tempo belum tercatat'}</small></span><span>{r.financial?.state==='ACTIVE_RECEIVABLE'&&r.financial.open_balance!==null?<><small>{r.financial.open_balance.startsWith('-')?'Kredit pada invoice':'Sisa tagihan'}</small><strong>{money(r.financial.open_balance)}</strong></>:<small>Belum/tidak menjadi piutang aktif</small>}</span></button>)}
    <div className="cproc-pagination"><span>Total {data.page.total} dokumen</span><button disabled={busy||data.page.offset===0} onClick={()=>{selected.current={...selected.current,offset:Math.max(0,data.page.offset-25)};void load(selected.current)}}>Piutang sebelumnya</button><button disabled={busy||data.page.next_offset===null} onClick={()=>{selected.current={...selected.current,offset:data.page.next_offset??0};void load(selected.current)}}>Piutang berikutnya</button></div>
   </section><aside className="panel" aria-label="Rincian sumber piutang">{detail&&detail.financial?<>
    <h2>{detail.number}</h2><p>{detail.customer_name} · {labels[detail.status]}</p><p>Kejadian {formatCp6WibDateTime(detail.physical_at)} · {detail.due_date?'jatuh tempo '+detail.due_date:'jatuh tempo belum tercatat'}.</p>
    {Object.entries({gross_total:'Nilai invoice',return_total:'Retur tercatat',net_total:'Nilai sesudah retur',paid_total:'Pembayaran tercatat'} as const).map(([key,label])=><div className="cproc-total" key={key}><span>{label}</span><strong>{money(detail.financial![key as 'gross_total'|'return_total'|'net_total'|'paid_total'])}</strong></div>)}
    {detail.financial.state==='ACTIVE_RECEIVABLE'&&detail.financial.open_balance!==null?<div className="cproc-total"><span>{detail.financial.open_balance.startsWith('-')?'Kredit pada invoice':'Sisa tagihan'}</span><strong>{money(detail.financial.open_balance)}</strong></div>:<p>Dokumen ini belum/tidak menjadi piutang aktif. Nilai invoice di atas merupakan informasi dokumen.</p>}
    <h3>Barang pada invoice</h3>{detail.items.map(item=><article className="cproc-item" key={item.id}><strong>{item.commercial_sku}</strong><p>{formatReceiptDecimal(item.qty_pcs)} PCS · {item.product_name} · {item.size_code}</p>{item.financial?<p>Nilai baris {money(item.financial.line_total)} · diskon {money(item.financial.discount)}.</p>:null}</article>)}
   </>:<><h2>Rincian sumber piutang</h2><p>Pilih invoice untuk melihat nilai, retur, pembayaran, dan barang asal.</p></>}</aside></div>
  </>:null}
 </main>
}
