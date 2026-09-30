import {useCallback,useEffect,useMemo,useRef,useState} from 'react'
import {useAuth} from './auth/AuthProvider'
import {isConnectedRuntime} from './config/runtime'
import {getUatSupabaseClient} from './lib/supabase'
import {normalizeClientError} from './lib/clientError'
import {cp6WibDateTimeInput,formatCp6WibDateTime} from './cp6BusinessTime'
import {formatReceiptDecimal as numberText} from './procurementContract'
import {financeDate,parseFinanceReport,type FinanceReport,type FinanceDates} from './financeReportContract'
import FinancePeriodPanel from './FinancePeriodPanel'
import FinanceAnalysisPanel from './FinanceAnalysisPanel'
import {financialRecoveryBlocked,financialRecoveryMessage,useFinancialRecoveryGate} from './useFinancialRecoveryGate'
import './procurement-connected.css'
const money=(n:string)=>`Rp${numberText(n)}`
const positionLabels={assets:'Aset',cash:'Kas dan bank',customer_ar:'Piutang pelanggan',material_inventory:'Persediaan bahan',wip_inventory:'Barang dalam proses',fg_inventory:'Persediaan barang jadi',liabilities:'Kewajiban',supplier_final_ap:'Utang supplier final',grni_estimated_liability:'Estimasi barang belum ditagih',recorded_equity:'Modal tercatat',current_earnings:'Laba/rugi berjalan',liabilities_plus_equity:'Kewajiban dan modal',balance_difference:'Selisih neraca'} as const
const performanceLabels={sales_revenue_gl:'Penjualan menurut jurnal',cogs_gl:'Harga pokok penjualan',gross_profit:'Laba kotor',other_income:'Penghasilan lain',operating_and_other_expense:'Beban operasi dan lainnya',net_profit:'Laba/rugi bersih',gross_sales_before_discount:'Penjualan sebelum diskon',line_discounts:'Diskon',posted_sales_returns:'Retur penjualan',operational_net_sales:'Penjualan bersih dari transaksi',sales_revenue_bridge_delta:'Selisih transaksi dan jurnal'} as const
const statusLabel={READY:'Lolos pemeriksaan tanggal ini',BLOCKED:'Ada penghalang',RECALC_PENDING:'Menunggu hitung ulang biaya'} as const
export default function ConnectedFinanceReportPage(){
 const {runtime,identity}=useAuth()
 if(!isConnectedRuntime(runtime)||identity.status!=='AUTHORIZED'||!identity.permissions.includes('finance.reports.view'))return <section className="panel" role="alert">Hak melihat laporan keuangan diperlukan.</section>
 if(!['OWNER','ADMIN'].includes(identity.profile.role))return <section className="panel" role="alert">Laporan sumber ini tersedia untuk Owner atau Admin.</section>
 return <Workspace key={`${runtime.projectRef}:${identity.profile.id}:${identity.profile.rowVersion}:${identity.profile.roleRowVersion}:${identity.permissions.join('|')}`}/>
}
function Workspace(){
 const {runtime,identity}=useAuth();if(!isConnectedRuntime(runtime)||identity.status!=='AUTHORIZED')throw Error('Sesi keuangan belum siap.')
 const client=useMemo(()=>getUatSupabaseClient(runtime),[runtime]),canPreflight=identity.permissions.includes('finance.period_close.manage'),today=cp6WibDateTimeInput().slice(0,10)
 const [from,setFrom]=useState(today.slice(0,7)+'-01'),[to,setTo]=useState(today),[asOf,setAsOf]=useState(today),[data,setData]=useState<FinanceReport|null>(null),[busy,setBusy]=useState(false),[error,setError]=useState('')
 const query=useRef<FinanceDates&{filing_id:string|null;offset:number}>({from:today.slice(0,7)+'-01',to:today,as_of:today,filing_id:null,offset:0}),seq=useRef(0)
 const entered=useRef<FinanceDates>({from,to,as_of:asOf});entered.current={from,to,as_of:asOf}
 const retire=useCallback(()=>{++seq.current;setData(null);setBusy(false);setError('')},[])
 const recoveryScope=`${runtime.projectRef}:${identity.profile.id}`,recoveryBlocked=useFinancialRecoveryGate(recoveryScope,retire)
 const load=useCallback(async()=>{
  const ticket=++seq.current,selected={...query.current};setData(null);setError('');setBusy(true)
  try{if(financialRecoveryBlocked(recoveryScope))return false;const r=await client.rpc('erp_cp7_get_finance_report_v1',{p_query:{...selected,limit:25}});if(ticket!==seq.current||financialRecoveryBlocked(recoveryScope))return false;if(r.error)throw r.error;setData(parseFinanceReport(r.data,selected,selected.filing_id,selected.offset,canPreflight));return true}
  catch(e){if(ticket===seq.current)setError(normalizeClientError(e).message);return false}finally{if(ticket===seq.current)setBusy(false)}
 },[client,canPreflight,recoveryScope])
 useEffect(()=>{void load();return()=>{++seq.current}},[load])
 const submit=async()=>{const d={...entered.current};retire();if(![d.from,d.to,d.as_of].every(financeDate)||d.from>d.to||d.to>d.as_of||d.as_of>today){setError('Pilih tanggal mulai ≤ akhir ≤ posisi laporan, sampai hari ini.');return false}query.current={...d,filing_id:null,offset:0};return load()}
 const refresh=()=>{const d=entered.current;return d.from===query.current.from&&d.to===query.current.to&&d.as_of===query.current.as_of?load():submit()}
 const chooseFiling=(f:FinanceReport['filings']['rows'][number])=>{const end=f.closed_through,start=end.slice(0,7)+'-01';setFrom(start);setTo(end);setAsOf(end);query.current={...query.current,from:start,to:end,as_of:end,filing_id:f.id};void load()}
 const d=data?.snapshot,c=d?.data_confidence,filing=data?.filing
 return <section className="cproc cfinance-report">
  <header className="panel cproc-heading"><div><div className="eyebrow">KEUANGAN</div><h1>Laporan & Tutup Buku</h1><p>Periksa angka menurut tanggal pembukuan, kelengkapan biaya, dan arsip penutupan.</p></div><button disabled={busy} onClick={()=>void refresh()}>Muat ulang laporan</button></header>
  <form className="panel cproc-grid" aria-label="Tanggal laporan keuangan" onSubmit={e=>{e.preventDefault();submit()}}>
   <label>Periode dari<input type="date" aria-label="Periode laporan dari" value={from} max={today} onChange={e=>{retire();setFrom(e.target.value)}}/></label><label>Periode sampai<input type="date" aria-label="Periode laporan sampai" value={to} max={today} onChange={e=>{retire();setTo(e.target.value)}}/></label><label>Posisi saldo pada<input type="date" aria-label="Posisi laporan pada" value={asOf} max={today} onChange={e=>{retire();setAsOf(e.target.value)}}/></label><button disabled={busy}>Tampilkan laporan</button>
  </form>
  {error?<p className="panel" role="alert">{error}</p>:null}{busy?<p role="status">Memuat laporan dan pemeriksaan tanggal…</p>:null}
  {recoveryBlocked?<p className="panel" role="alert">{financialRecoveryMessage}</p>:null}
  {canPreflight?<FinancePeriodPanel client={client} onChanged={refresh}/>:null}
  {!recoveryBlocked&&data&&d&&c?<>
   <section className="panel" aria-label="Basis dan kesiapan laporan"><h2>{statusLabel[c.status]}</h2><p>Periode {d.basis.period_from}–{d.basis.period_to}; posisi saldo {d.basis.balance_sheet_as_of}. Dibaca {formatCp6WibDateTime(data.captured_at)}.</p><p>Angka memakai informasi yang sudah tercatat saat laporan dibaca. Ini bukan rekonstruksi informasi yang diketahui pada masa lalu.</p><p>{c.status==='READY'?'Estimasi yang masih tercatat tetap ditampilkan pada informasi di bawah.':'Biaya dan laba di bawah masih berupa nilai tercatat; jangan dianggap final selama penghalangnya belum selesai.'}</p><p>Penghalang kritis/kebijakan: {c.critical_issue_count} · antrean hitung ulang: {c.pending_cost_recalc_count} · peringatan: {c.warning_issue_count}.</p>
    {c.filing?<p>Penutupan terbaru yang mencakup tanggal ini: {c.filing.closed_through}, disimpan {formatCp6WibDateTime(c.filing.filed_at)}. {c.changed_since_filing?'Ada perubahan setelah arsip penutupan; arsip asli tetap.':'Belum ada perubahan yang ditandai mesin sejak arsip tersebut.'}</p>:<p>Belum ada arsip penutupan yang mencakup tanggal ini.</p>}
    {c.blockers.map((b,i)=><article className="cproc-item" key={`${b.code}:${i}`}><strong>{b.reason}</strong><p>{b.code} · {b.impact_date??'Kondisi saat ini'} · {b.scope==='CURRENT_STATE'?'Pemeriksaan keadaan sekarang':b.scope==='WINDOW'?'Kelengkapan rentang tanggal':'Berlaku pada tanggal laporan'}</p></article>)}
    {c.info.map((b,i)=><p key={`${b.code}:${i}`}>{b.reason}</p>)}{c.failed_checks.filter(x=>x.severity==='WARNING').map((x,i)=><p key={`${x.check_name}:${i}`}>Peringatan: {x.details}</p>)}
   </section>
   <div className="cproc-layout"><section className="panel" aria-label="Kinerja keuangan tercatat"><h2>Kinerja menurut jurnal</h2><p>{d.basis.period_from}–{d.basis.period_to}, termasuk pembalikan pada tanggal pembukuannya.</p>{Object.entries(performanceLabels).map(([key,label])=><div className="cproc-total" key={key}><span>{label}</span><strong>{money(d.performance[key as keyof typeof performanceLabels])}</strong></div>)}<p>Margin kotor: {d.performance.gross_margin_pct===null?'Belum dapat dihitung':numberText(d.performance.gross_margin_pct)+'%'} · margin bersih: {d.performance.net_margin_pct===null?'Belum dapat dihitung':numberText(d.performance.net_margin_pct)+'%'}.</p><p>{d.performance.sales_revenue_reconciled?'Transaksi penjualan dan jurnal cocok.':'Transaksi penjualan dan jurnal belum cocok.'}</p></section>
    <section className="panel" aria-label="Posisi keuangan tercatat"><h2>Posisi saldo buku</h2><p>Sampai {d.basis.balance_sheet_as_of}.</p>{Object.entries(positionLabels).map(([key,label])=><div className="cproc-total" key={key}><span>{label}</span><strong>{money(d.financial_position[key as keyof typeof positionLabels])}</strong></div>)}</section>
   </div>
   <FinanceAnalysisPanel client={client} dates={{from:d.basis.period_from,to:d.basis.period_to,as_of:d.basis.balance_sheet_as_of}}/>
   <section className="panel" aria-label="Kondisi supplier saat ini"><h2>Tagihan supplier saat ini</h2><p>Bagian ini memakai kondisi operasional sekarang, walaupun tanggal laporan dipilih ke masa lalu.</p><p>{d.supplier_exposure.open_final_ap_document_count} tagihan final terbuka · lewat jatuh tempo {money(d.supplier_exposure.overdue_final_ap_amount)}.</p><p>{d.supplier_exposure.unfinalized_receipt_count} penerimaan belum final · tertua {d.supplier_exposure.oldest_unfinalized_days} hari.</p></section>
   {data.close_preflight?<section className="panel" aria-label="Pemeriksaan tutup buku"><h2>Pemeriksaan tutup buku {data.close_preflight.through}</h2><p>{statusLabel[data.close_preflight.status]} · {data.close_preflight.date_allowed?'Tanggal dalam batas yang diizinkan.':'Tanggal belum boleh ditutup.'}</p><p>Periode tertutup sampai {data.close_preflight.closed_through??'belum ada'}. Pemeriksaan ini belum menjalankan penutupan.</p></section>:null}
   <section className="panel" aria-label="Arsip penutupan keuangan"><h2>Arsip penutupan</h2><p>Arsip menyimpan saldo GL pada saat penutupan. Laporan kinerja di atas dihitung dari informasi yang tercatat sekarang.</p>{data.filings.rows.length===0?<p>Belum ada arsip penutupan.</p>:null}{data.filings.rows.map(f=><button className="cproc-receipt" aria-pressed={filing?.id===f.id} key={f.id} disabled={busy} onClick={()=>chooseFiling(f)}><span><strong>Sampai {f.closed_through}</strong><small>{formatCp6WibDateTime(f.filed_at)}</small></span><span>{f.reason}</span></button>)}<div className="cproc-pagination"><span>Total {data.filings.total} arsip</span><button disabled={busy||data.filings.offset===0} onClick={()=>{query.current.offset=Math.max(0,data.filings.offset-25);void load()}}>Arsip sebelumnya</button><button disabled={busy||data.filings.next_offset===null} onClick={()=>{query.current.offset=data.filings.next_offset??0;void load()}}>Arsip berikutnya</button></div></section>
   {filing?<section className="panel" aria-label="Saldo asli saat penutupan"><h2>Saldo asli saat penutupan {filing.closed_through}</h2><p>Disimpan {formatCp6WibDateTime(filing.filed_at)} · {filing.reason}. Tanda saldo: debit dikurangi kredit.</p>{Object.entries(filing.gl_balances).map(([account,amount])=><div className="cproc-total" key={account}><span>Akun {account}</span><strong>{money(amount)}</strong></div>)}{Object.keys(filing.gl_balances).length===0?<p>Tidak ada saldo GL dalam arsip ini.</p>:null}</section>:null}
  </>:null}
 </section>
}
