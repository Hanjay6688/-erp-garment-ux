import {useCallback,useEffect,useMemo,useRef,useState} from 'react'
import {useAuth} from './auth/AuthProvider'
import {isConnectedRuntime} from './config/runtime'
import {getUatSupabaseClient} from './lib/supabase'
import {normalizeClientError} from './lib/clientError'
import {cp6WibDateTimeInput,formatCp6WibDateTime} from './cp6BusinessTime'
import {formatReceiptDecimal} from './procurementContract'
import {financeDate,parseFinanceReport,type FinanceDates,type FinanceReport} from './financeReportContract'
import type {FinanceView} from './FinancePages'
import {financialRecoveryBlocked,financialRecoveryMessage,useFinancialRecoveryGate} from './useFinancialRecoveryGate'
import './procurement-connected.css'

type Props={onNavigate:(view:FinanceView)=>void}
const money=(amount:string)=>'Rp'+formatReceiptDecimal(amount)
const statusLabel={READY:'Lolos pemeriksaan tanggal ini',BLOCKED:'Ada penghalang',RECALC_PENDING:'Menunggu hitung ulang biaya'} as const
const balanceMetrics=[
 ['cash','Kas dan bank','finance-cash'],
 ['customer_ar','Piutang pelanggan menurut buku','finance-reports'],
 ['supplier_final_ap','Utang supplier final menurut buku','finance-ap'],
 ['grni_estimated_liability','Estimasi barang belum ditagih','finance-reports'],
 ['assets','Total aset','finance-reports'],
 ['liabilities','Total kewajiban','finance-reports'],
] as const
const performanceMetrics=[
 ['sales_revenue_gl','Penjualan menurut jurnal'],
 ['cogs_gl','Harga pokok penjualan'],
 ['gross_profit','Laba kotor'],
 ['operating_and_other_expense','Beban operasi dan lainnya'],
 ['other_income','Penghasilan lain'],
 ['net_profit','Laba/rugi bersih'],
] as const

export default function ConnectedFinanceOverviewPage(props:Props){
 const {runtime,identity}=useAuth()
 if(!isConnectedRuntime(runtime)||identity.status!=='AUTHORIZED'||!identity.permissions.includes('finance.dashboard.view')||!identity.permissions.includes('finance.reports.view'))return <section className="panel" role="alert">Hak melihat ringkasan dan laporan keuangan diperlukan.</section>
 if(!['OWNER','ADMIN'].includes(identity.profile.role))return <section className="panel" role="alert">Ringkasan sumber ini tersedia untuk Owner atau Admin.</section>
 return <Workspace {...props} key={`${runtime.projectRef}:${identity.profile.id}:${identity.profile.rowVersion}:${identity.profile.roleRowVersion}:${identity.permissions.join('|')}`}/>
}

function Workspace({onNavigate}:Props){
 const {runtime,identity}=useAuth()
 if(!isConnectedRuntime(runtime)||identity.status!=='AUTHORIZED')throw Error('Sesi ringkasan keuangan belum siap.')
 const client=useMemo(()=>getUatSupabaseClient(runtime),[runtime]),today=cp6WibDateTimeInput().slice(0,10)
 const canPreflight=identity.permissions.includes('finance.period_close.manage')
 const [from,setFrom]=useState(today.slice(0,7)+'-01'),[to,setTo]=useState(today),[asOf,setAsOf]=useState(today)
 const [data,setData]=useState<FinanceReport|null>(null),[busy,setBusy]=useState(false),[error,setError]=useState('')
 const selected=useRef<FinanceDates>({from:today.slice(0,7)+'-01',to:today,as_of:today}),seq=useRef(0)
 const retire=useCallback(()=>{++seq.current;setData(null);setBusy(false);setError('')},[])
 const recoveryScope=`${runtime.projectRef}:${identity.profile.id}`,recoveryBlocked=useFinancialRecoveryGate(recoveryScope,retire)
 const load=useCallback(async(dates:FinanceDates)=>{
  const ticket=++seq.current;setData(null);setError('');setBusy(true)
  try{
   if(financialRecoveryBlocked(recoveryScope))return
   const result=await client.rpc('erp_cp7_get_finance_report_v1',{p_query:{...dates,filing_id:null,offset:0,limit:25}})
   if(ticket!==seq.current||financialRecoveryBlocked(recoveryScope))return
   if(result.error)throw result.error
   setData(parseFinanceReport(result.data,dates,null,0,canPreflight))
  }catch(e){if(ticket===seq.current)setError(normalizeClientError(e).message)}finally{if(ticket===seq.current)setBusy(false)}
 },[client,canPreflight,recoveryScope])
 useEffect(()=>{void load(selected.current);return()=>{++seq.current}},[load])
 const submit=()=>{
  retire()
  const dates={from,to,as_of:asOf}
  if(![from,to,asOf].every(financeDate)||from>to||to>asOf||asOf>today){setError('Pilih tanggal mulai ≤ akhir ≤ posisi saldo, sampai hari ini.');return}
  selected.current=dates;void load(dates)
 }
 const snapshot=data?.snapshot,confidence=snapshot?.data_confidence
 const navigate=(view:FinanceView)=>onNavigate(view)
 return <main className="cproc cfinance-overview" aria-label="Ringkasan keuangan dari buku">
  <header className="panel cproc-heading"><div><div className="eyebrow">KEUANGAN</div><h1>Ringkasan Keuangan</h1><p>Saldo, kinerja, dan kelengkapan biaya menurut tanggal pembukuan yang dipilih.</p></div><button onClick={()=>navigate('finance-reports')}>Buka laporan</button></header>
  <form className="panel cproc-grid" aria-label="Tanggal ringkasan keuangan" onSubmit={e=>{e.preventDefault();submit()}}>
   <label>Periode dari<input type="date" aria-label="Periode ringkasan dari" max={today} value={from} onChange={e=>{retire();setFrom(e.target.value)}}/></label>
   <label>Periode sampai<input type="date" aria-label="Periode ringkasan sampai" max={today} value={to} onChange={e=>{retire();setTo(e.target.value)}}/></label>
   <label>Posisi saldo pada<input type="date" aria-label="Posisi ringkasan pada" max={today} value={asOf} onChange={e=>{retire();setAsOf(e.target.value)}}/></label>
   <button disabled={busy}>Tampilkan ringkasan</button>
  </form>
  {busy?<p role="status">Membaca saldo dan kesiapan laporan…</p>:null}
  {error?<p className="panel" role="alert">{error}</p>:null}
  {recoveryBlocked?<p className="panel" role="alert">{financialRecoveryMessage}</p>:null}
  {!recoveryBlocked&&data&&snapshot&&confidence?<>
   <section className="panel" aria-label="Basis dan kesiapan ringkasan"><h2>{statusLabel[confidence.status]}</h2>
    <p>Periode {snapshot.basis.period_from}–{snapshot.basis.period_to}; posisi saldo {snapshot.basis.balance_sheet_as_of}. Dibaca {formatCp6WibDateTime(data.captured_at)}.</p>
    <p>Angka memakai informasi yang tercatat sekarang; bukan rekonstruksi pengetahuan masa lalu.</p>
    <p>{confidence.status==='READY'?'Angka lolos pemeriksaan tanggal ini. Estimasi yang tercatat tetap ditampilkan terpisah.':'Angka di bawah masih berupa nilai tercatat. Biaya dan laba belum final selama penghalang belum selesai.'}</p>
    <p>Penghalang kritis/kebijakan: {confidence.critical_issue_count} · antrean hitung ulang: {confidence.pending_cost_recalc_count} · peringatan: {confidence.warning_issue_count}.</p>
    {confidence.blockers.map((b,i)=><article className="cproc-item" key={`${b.code}:${i}`}><strong>{b.reason}</strong><p>{b.code} · {b.impact_date??'Kondisi saat ini'} · {b.scope==='CURRENT_STATE'?'Keadaan sekarang':b.scope==='WINDOW'?'Rentang tanggal':'Tanggal laporan'}</p></article>)}
    {confidence.info.map((b,i)=><p key={`${b.code}:${i}`}>{b.reason}</p>)}
    {confidence.failed_checks.filter(c=>c.severity==='WARNING').map((c,i)=><p key={`${c.check_name}:${i}`}>Peringatan: {c.details}</p>)}
    {confidence.filing?<p>Arsip penutupan terbaru sampai {confidence.filing.closed_through}. {confidence.changed_since_filing?'Ada perubahan sesudah arsip; saldo asli penutupan tetap tersimpan.':'Belum ada perubahan yang ditandai mesin sejak arsip ini.'}</p>:<p>Belum ada arsip penutupan yang mencakup tanggal ini.</p>}
   </section>
   <section className="panel" aria-label="Saldo ringkasan tercatat"><h2>Posisi saldo buku</h2><p>Sampai {snapshot.basis.balance_sheet_as_of}. Saldo piutang dan utang menurut buku; daftar tagihan saat ini ditampilkan terpisah.</p><div className="cproc-grid">
    {balanceMetrics.map(([key,label,view])=><div className="cproc-total" key={key}><span>{label}</span><strong>{money(snapshot.financial_position[key])}</strong><button onClick={()=>navigate(view)}>Periksa {label.toLowerCase()}</button></div>)}
   </div><p>Selisih neraca: {money(snapshot.financial_position.balance_difference)}.</p></section>
   <section className="panel" aria-label="Kinerja ringkasan tercatat"><h2>Kinerja menurut jurnal</h2><p>{snapshot.basis.period_from}–{snapshot.basis.period_to}, termasuk pembalikan pada tanggal pembukuannya.</p><div className="cproc-grid">
    {performanceMetrics.map(([key,label])=><div className="cproc-total" key={key}><span>{label}</span><strong>{money(snapshot.performance[key])}</strong></div>)}
   </div><p>Margin kotor: {snapshot.performance.gross_margin_pct===null?'Belum dapat dihitung':formatReceiptDecimal(snapshot.performance.gross_margin_pct)+'%'} · margin bersih: {snapshot.performance.net_margin_pct===null?'Belum dapat dihitung':formatReceiptDecimal(snapshot.performance.net_margin_pct)+'%'}.</p><p>{snapshot.performance.sales_revenue_reconciled?'Transaksi penjualan dan jurnal cocok.':'Transaksi penjualan dan jurnal belum cocok.'}</p></section>
   <section className="panel" aria-label="Tagihan supplier saat ini pada ringkasan"><h2>Tagihan supplier saat ini</h2><p>Kondisi operasional sekarang, termasuk ketika tanggal saldo dipilih ke masa lalu.</p><p>{snapshot.supplier_exposure.open_final_ap_document_count} tagihan final terbuka · lewat jatuh tempo {money(snapshot.supplier_exposure.overdue_final_ap_amount)}.</p><p>{snapshot.supplier_exposure.unfinalized_receipt_count} penerimaan belum final · tertua {snapshot.supplier_exposure.oldest_unfinalized_days} hari.</p><button onClick={()=>navigate('finance-ap')}>Periksa tagihan supplier</button></section>
  </>:null}
 </main>
}
