import {lazy,Suspense,useCallback,useEffect,useMemo,useRef,useState} from 'react'
import {useAuth} from './auth/AuthProvider'
import {isConnectedRuntime} from './config/runtime'
import {getUatSupabaseClient} from './lib/supabase'
import {normalizeClientError} from './lib/clientError'
import {cp6WibDateTimeInput,formatCp6WibDateTime} from './cp6BusinessTime'
import {formatReceiptDecimal} from './procurementContract'
import {financeDate} from './financeReportContract'
import {parseJournalRead,type JournalDates,type JournalRead} from './journalReadContract'
import {hasProductionPending,observeProductionRecovery,readProductionRecovery} from './productionRecovery'
import './procurement-connected.css'
const MiscFinancePanel=lazy(()=>import('./MiscFinancePanel'))
const money=(v:string)=>'Rp'+formatReceiptDecimal(v)
type Query=JournalDates&{offset:number;journal_id:string|null}
import TransactionSourceLink,{useTransactionSource} from './TransactionSourceNavigation'

export default function ConnectedJournalPage(){
 const source=useTransactionSource('MISC_FINANCE')
 const {runtime,identity}=useAuth()
 if(!isConnectedRuntime(runtime)||identity.status!=='AUTHORIZED'||!identity.permissions.includes('finance.journal.view'))return <section className="panel" role="alert">Hak melihat jurnal keuangan diperlukan.</section>
 if(!['OWNER','ADMIN'].includes(identity.profile.role))return <section className="panel" role="alert">Sumber jurnal ini tersedia untuk Owner atau Admin.</section>
 return <Workspace key={`${runtime.projectRef}:${identity.profile.id}:${identity.profile.rowVersion}:${identity.profile.roleRowVersion}:${identity.permissions.join('|')}:${source?.key??''}`} initialMiscId={source?.document.id??null}/>
}
function Workspace({initialMiscId}:{initialMiscId:string|null}){
 const {runtime,identity}=useAuth();if(!isConnectedRuntime(runtime)||identity.status!=='AUTHORIZED')throw Error('Sesi jurnal belum siap.')
 const client=useMemo(()=>getUatSupabaseClient(runtime),[runtime]),today=cp6WibDateTimeInput().slice(0,10)
 const [from,setFrom]=useState(today.slice(0,7)+'-01'),[to,setTo]=useState(today),[q,setQ]=useState(''),[data,setData]=useState<JournalRead|null>(null),[busy,setBusy]=useState(false),[error,setError]=useState('')
 const [miscOpen,setMiscOpen]=useState(Boolean(initialMiscId)),[recoveryBlocked,setRecoveryBlocked]=useState(false)
 const seq=useRef(0),selected=useRef<Query>({from:today.slice(0,7)+'-01',to:today,q:'',offset:0,journal_id:null})
 const entered=useRef({from,to,q});entered.current={from,to,q}
 const recoveryScope=`${runtime.projectRef}:${identity.profile.id}`
 const retire=()=>{++seq.current;setData(null);setBusy(false);setError('')}
 const retireBook=useCallback(()=>{++seq.current;setData(null);setBusy(false);setError('')},[])
 useEffect(()=>{const changed=()=>{const current=readProductionRecovery(recoveryScope),blocked=current.corrupted||hasProductionPending(current);setRecoveryBlocked(blocked);if(blocked)retireBook()};changed();return observeProductionRecovery(recoveryScope,changed)},[recoveryScope,retireBook])
 const load=useCallback(async(query:Query)=>{
  const ticket=++seq.current;setData(null);setBusy(true);setError('')
  try{const recovery=readProductionRecovery(recoveryScope);if(recovery.corrupted||hasProductionPending(recovery)){setRecoveryBlocked(true);return false}const result=await client.rpc('erp_cp7_get_journal_book_v1',{p_query:{...query,limit:25}});if(ticket!==seq.current)return false;if(result.error)throw result.error;setData(parseJournalRead(result.data,query,query.offset,query.journal_id));return true}
  catch(e){if(ticket===seq.current)setError(normalizeClientError(e).message);return false}finally{if(ticket===seq.current)setBusy(false)}
 },[client,recoveryScope])
 useEffect(()=>{void load(selected.current);return()=>{++seq.current}},[load])
 const submit=()=>{retire();if(!financeDate(from)||!financeDate(to)||from>to||to>today){setError('Pilih periode pembukuan yang sah sampai hari ini.');return}selected.current={from,to,q:q.trim(),offset:0,journal_id:null};void load(selected.current)}
 const refresh=()=>{const s=selected.current;if(s.from===from&&s.to===to&&s.q===q.trim())void load(s);else submit()}
 const afterMisc=useCallback(()=>{const f=entered.current,last=selected.current;retireBook();if(!financeDate(f.from)||!financeDate(f.to)||f.from>f.to||f.to>cp6WibDateTimeInput().slice(0,10)){setError('Pilih periode pembukuan yang sah sampai hari ini.');return Promise.resolve(false)}if(last.from!==f.from||last.to!==f.to||last.q!==f.q.trim())selected.current={from:f.from,to:f.to,q:f.q.trim(),offset:0,journal_id:null};return load(selected.current)},[load,retireBook])
 const detail=data?.detail
 return <main className="cproc cjournal" aria-label="Jurnal keuangan dari buku">
  <header className="panel cproc-heading"><div><div className="eyebrow">KEUANGAN</div><h1>Jurnal Keuangan</h1><p>Periksa pembukuan dan akun yang berasal dari transaksi ERP.</p></div><button disabled={busy} onClick={refresh}>Muat ulang jurnal</button></header>
  {identity.permissions.includes('finance.cash.view')?<button aria-expanded={miscOpen} onClick={()=>setMiscOpen(true)}>Buka pendapatan dan biaya lain</button>:null}
  {miscOpen?<Suspense fallback={<p role="status">Membuka transaksi lain…</p>}><MiscFinancePanel initialId={initialMiscId} client={client} onChanged={afterMisc} onRetire={retireBook}/></Suspense>:null}
  {recoveryBlocked?<p role="alert">Transaksi terkait belum dipastikan atau jejak recovery perlu diperiksa. Selesaikan Reconcile transaksi sebelum memuat ulang jurnal.</p>:null}
  <form className="panel cproc-grid" aria-label="Periode dan sumber jurnal" onSubmit={e=>{e.preventDefault();submit()}}>
   <label>Periode dari<input type="date" aria-label="Periode jurnal dari" value={from} max={today} onChange={e=>{retire();setFrom(e.target.value)}}/></label><label>Periode sampai<input type="date" aria-label="Periode jurnal sampai" value={to} max={today} onChange={e=>{retire();setTo(e.target.value)}}/></label><label>Nomor atau sumber<input aria-label="Cari sumber jurnal" maxLength={120} value={q} onChange={e=>{retire();setQ(e.target.value)}}/></label><button disabled={busy}>Tampilkan jurnal</button>
  </form>
  {busy?<p role="status">Membaca jurnal dan rincian akun…</p>:null}{error?<p className="panel" role="alert">{error}</p>:null}
  {data?<>
   <section className="panel" aria-label="Basis dan total jurnal"><p>Periode pembukuan {data.basis.from}–{data.basis.to}; dibaca {formatCp6WibDateTime(data.captured_at)}. Informasi tercatat sekarang; bukan rekonstruksi pengetahuan masa lalu.</p><p>Jurnal asli yang sudah dibalik tetap ditampilkan pada tanggal pembukuannya; jurnal pembalikan mengikuti tanggalnya sendiri. Koreksi dijalankan dari transaksi sumber.</p><div className="cproc-grid"><div className="cproc-total"><span>Debit seluruh hasil</span><strong>{money(data.totals.debit)}</strong></div><div className="cproc-total"><span>Kredit seluruh hasil</span><strong>{money(data.totals.credit)}</strong></div></div><p>Total {data.totals.journal_count} jurnal · {data.totals.line_count} baris akun. {data.totals.unbalanced_journal_count==='0'?'Debit dan kredit pada setiap jurnal cocok.':`${data.totals.unbalanced_journal_count} jurnal belum lengkap atau belum seimbang; periksa sumber.`}</p><p>Kecocokan debit/kredit tidak menetapkan kelengkapan biaya atau kesiapan tutup buku.</p></section>
   <div className="cproc-layout"><section className="panel" aria-label="Daftar jurnal tercatat"><h2>Jurnal transaksi</h2>{data.page.rows.length===0?<p>Tidak ada jurnal sesuai periode dan pencarian.</p>:null}
    {data.page.rows.map(r=><button className="cproc-receipt" data-journal-id={r.id} key={r.id} aria-pressed={detail?.id===r.id} disabled={busy} onClick={()=>{selected.current={...selected.current,journal_id:r.id};void load(selected.current)}}><span><strong>{r.number}</strong><small>{r.source_type} · pembukuan {r.transaction_date}</small><small>{r.reversal_of_id?'Pembalikan bertaut':r.status==='REVERSED'?'Jurnal asli sudah dibalik':'Tercatat'}</small></span><span><small>Debit {money(r.debit)}</small><small>Kredit {money(r.credit)}</small></span></button>)}
    <div className="cproc-pagination"><span>Total {data.page.total} jurnal</span><button disabled={busy||data.page.offset===0} onClick={()=>{selected.current={...selected.current,offset:Math.max(0,data.page.offset-25)};void load(selected.current)}}>Jurnal sebelumnya</button><button disabled={busy||data.page.next_offset===null} onClick={()=>{selected.current={...selected.current,offset:data.page.next_offset??0};void load(selected.current)}}>Jurnal berikutnya</button></div>
   </section><aside className="panel" aria-label="Rincian akun jurnal">{detail?<>
    <h2>{detail.number}</h2><p>{detail.description}</p><p>Kejadian {detail.economic_date} · pembukuan {detail.transaction_date} · dicatat {formatCp6WibDateTime(detail.posting_at)}.</p>{detail.period_shifted?<p>Tanggal pembukuan bergeser dari tanggal kejadian karena kontrol periode.</p>:null}<TransactionSourceLink sourceType={detail.source_type} sourceId={detail.source_id} disabled={busy||recoveryBlocked}/><p>Sumber {detail.source_type}{detail.source_id?' · '+detail.source_id:''}.</p>{detail.reversal_of_id?<p>Pembalikan jurnal {detail.reversal_of_id}.</p>:detail.status==='REVERSED'?<p>Jurnal asli sudah dibalik; catatan asli tetap.</p>:null}
    {detail.lines.map(l=><article className="cproc-item" data-journal-line-id={l.id} key={l.id}><strong>{l.account_code} · {l.account_name}</strong>{l.description?<p>{l.description}</p>:null}<p>Debit {money(l.debit)} · kredit {money(l.credit)}.</p>{l.customer_id?<small>Pelanggan {l.customer_id}</small>:null}{l.vendor_id?<small>Vendor {l.vendor_id}</small>:null}{l.contractor_id?<small>Mandor {l.contractor_id}</small>:null}{l.po_id?<small>PO {l.po_id}</small>:null}{l.product_id?<small>Produk {l.product_id}</small>:null}</article>)}
   </>:<><h2>Rincian akun jurnal</h2><p>Pilih jurnal untuk memeriksa akun dan transaksi asal.</p></>}</aside></div>
  </>:null}
 </main>
}
