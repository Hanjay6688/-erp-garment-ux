import {useEffect,useRef,useState} from 'react'
import type {getUatSupabaseClient} from './lib/supabase'
import {normalizeClientError} from './lib/clientError'
import {formatReceiptDecimal as numberText} from './procurementContract'
import {financeDate,type FinanceDates} from './financeReportContract'
import {parseFinanceAnalysis,type AnalysisDates,type FinanceAnalysis} from './financeAnalysisContract'
const money=(v:string)=>'Rp'+numberText(v)
function prior(dates:FinanceDates){const day=86400000,start=Date.parse(dates.from+'T00:00:00Z'),end=Date.parse(dates.to+'T00:00:00Z');return {from:new Date(start-(end-start+day)).toISOString().slice(0,10),to:new Date(start-day).toISOString().slice(0,10)}}
export default function FinanceAnalysisPanel({client,dates}:{client:ReturnType<typeof getUatSupabaseClient>;dates:FinanceDates}){
 const [open,setOpen]=useState(false),[from,setFrom]=useState(()=>prior(dates).from),[to,setTo]=useState(()=>prior(dates).to),[data,setData]=useState<FinanceAnalysis|null>(null),[busy,setBusy]=useState(false),[error,setError]=useState('')
 const seq=useRef(0),selected=useRef<AnalysisDates|null>(null)
 useEffect(()=>()=>{++seq.current},[])
 const retire=()=>{++seq.current;setData(null);setBusy(false);setError('');selected.current=null}
 async function load(query:AnalysisDates,offset=0){
  const ticket=++seq.current;setData(null);setError('');setBusy(true)
  try{const r=await client.rpc('erp_cp7_get_finance_analysis_v1',{p_query:{...query,offset,limit:25}});if(ticket!==seq.current)return;if(r.error)throw r.error;setData(parseFinanceAnalysis(r.data,query,offset))}
  catch(e){if(ticket===seq.current)setError(normalizeClientError(e).message)}finally{if(ticket===seq.current)setBusy(false)}
 }
 const submit=()=>{if(!financeDate(from)||!financeDate(to)||from>to||to>=dates.from){retire();setError('Pilih rentang pembanding sebelum periode laporan ini.');return}selected.current={...dates,compare_from:from,compare_to:to};void load(selected.current)}
 const comparison=data?.comparison,cash=data?.cash
 const metricLabels={sales_revenue_gl:'Penjualan menurut jurnal',cogs_gl:'Harga pokok penjualan',gross_profit:'Laba kotor',net_profit:'Laba/rugi bersih'} as const
 const status={READY:'Lolos pemeriksaan',BLOCKED:'Ada penghalang',RECALC_PENDING:'Menunggu hitung ulang biaya'} as const
 return <section className="panel cfinance-analysis" aria-label="Perbandingan periode dan arus kas">
  <h2>Perbandingan periode & arus kas</h2><p>Bandingkan periode pembukuan dan periksa perubahan seluruh rekening kas/bank.</p>
  <button onClick={()=>{retire();setOpen(!open)}}>{open?'Tutup perbandingan & arus kas':'Buka perbandingan & arus kas'}</button>
  {open?<>
   <form className="cproc-grid" onSubmit={e=>{e.preventDefault();submit()}}><label>Pembanding dari<input type="date" aria-label="Periode pembanding dari" value={from} onChange={e=>{retire();setFrom(e.target.value)}}/></label><label>Pembanding sampai<input type="date" aria-label="Periode pembanding sampai" value={to} onChange={e=>{retire();setTo(e.target.value)}}/></label><button disabled={busy}>Periksa perbandingan & kas</button></form>
   {busy?<p role="status">Membaca kedua periode dan sumber kas…</p>:null}{error?<p role="alert">{error}</p>:null}
   {data&&comparison&&cash?<>
    <p>Periode {data.dates.from}–{data.dates.to}; pembanding {data.dates.compare_from}–{data.dates.compare_to}. Informasi yang tercatat sekarang; bukan rekonstruksi pengetahuan masa lalu. Perbedaan panjang periode perlu dipertimbangkan.</p>
    <p>Periode ini: {status[comparison.current.data_confidence.status]} · pembanding: {status[comparison.baseline.data_confidence.status]}. Nilai laba dan margin tetap nilai tercatat; biaya yang belum lengkap belum boleh dianggap final.</p>
    <div className="cproc-layout">{(['current','baseline'] as const).map(key=><section key={key} aria-label={key==='current'?'Kinerja periode ini':'Kinerja periode pembanding'}><h3>{key==='current'?'Periode ini':'Periode pembanding'}</h3>{Object.entries(metricLabels).map(([k,label])=><div className="cproc-total" key={k}><span>{label}</span><strong>{money(comparison[key].performance[k as keyof typeof metricLabels])}</strong></div>)}<p>Margin kotor: {comparison[key].performance.gross_margin_pct===null?'N/A':numberText(comparison[key].performance.gross_margin_pct!)+'%'}.</p>{comparison[key].data_confidence.blockers.map((b,i)=><p key={i}>{b.reason}</p>)}</section>)}</div>
    <div className="cproc-total"><span>Pertumbuhan penjualan</span><strong>{comparison.revenue_growth_pct===null?'N/A — penjualan pembanding nol atau minus':numberText(comparison.revenue_growth_pct)+'%'}</strong></div>
    <div className="cproc-total"><span>Perubahan margin kotor</span><strong>{comparison.gross_margin_change_pp===null?'N/A — penjualan nol atau minus':numberText(comparison.gross_margin_change_pp)+' poin persentase'}</strong></div>
    <section aria-label="Arus kas menurut jurnal"><h3>Perubahan kas & bank</h3><p>Sampai awal {data.dates.from}, lalu seluruh pembukuan sampai {data.dates.to}. Rekening tidak aktif yang memiliki catatan tetap dihitung; akun buku yang sama hanya dihitung sekali.</p>
     {Object.entries({opening:'Saldo sebelum periode',debit:'Debit rekening kas/bank',credit:'Kredit rekening kas/bank',net_change:'Perubahan kas bersih',closing:'Saldo akhir periode',source_difference:'Selisih saldo dan jurnal'} as const).map(([key,label])=><div className="cproc-total" key={key}><span>{label}</span><strong>{money(cash[key as 'opening'|'debit'|'credit'|'net_change'|'closing'|'source_difference'])}</strong></div>)}
     <p>{cash.reconciled?'Saldo dan jurnal kas cocok.':'Saldo dan jurnal kas belum cocok. Periksa sumber sebelum memakai hasil.'}</p><p>Transfer antar rekening muncul di debit dan kredit, dengan perubahan kas bersih nol. Penerimaan kas tidak otomatis menjadi penjualan; invoice belum dibayar tidak menambah kas.</p>
     <h3>Sumber jurnal kas</h3>{cash.entries.rows.length===0?<p>Tidak ada jurnal kas dalam periode ini.</p>:null}{cash.entries.rows.map(e=><article className="cproc-item" key={e.id}><strong>{e.journal_number}</strong><p>{e.source_type} · pembukuan {e.transaction_date} · kejadian {e.economic_date}</p><p>Debit {money(e.debit)} · kredit {money(e.credit)} · bersih {money(e.net)}.</p>{e.reversal_of_id?<small>Pembalikan jurnal {e.reversal_of_id}</small>:e.status==='REVERSED'?<small>Jurnal asli sudah memiliki pembalikan; keduanya tetap masuk sesuai tanggal pembukuannya.</small>:null}</article>)}
     <div className="cproc-pagination"><span>Total {cash.entries.total} jurnal</span><button disabled={busy||cash.entries.offset===0} onClick={()=>{if(selected.current)void load(selected.current,Math.max(0,cash.entries.offset-25))}}>Jurnal sebelumnya</button><button disabled={busy||cash.entries.next_offset===null} onClick={()=>{if(selected.current)void load(selected.current,cash.entries.next_offset??0)}}>Jurnal berikutnya</button></div>
    </section>
   </>:null}
  </>:null}
 </section>
}
