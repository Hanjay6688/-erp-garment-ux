import {useCallback,useEffect,useMemo,useRef,useState} from 'react'
import {useAuth} from './auth/AuthProvider'
import {isConnectedRuntime} from './config/runtime'
import {getUatSupabaseClient} from './lib/supabase'
import {normalizeClientError} from './lib/clientError'
import {cp6WibDateTimeInput,formatCp6WibDateTime} from './cp6BusinessTime'
import {formatReceiptDecimal as numberText} from './procurementContract'
import {financeDate} from './financeReportContract'
import {parseFinanceAnalysis,type AnalysisDates,type FinanceAnalysis} from './financeAnalysisContract'
import {financialRecoveryBlocked,financialRecoveryMessage,useFinancialRecoveryGate} from './useFinancialRecoveryGate'
import './procurement-connected.css'

const money=(value:string)=>'Rp'+numberText(value)
const metrics={opening:'Saldo sebelum periode',debit:'Debit rekening kas/bank',credit:'Kredit rekening kas/bank',net_change:'Perubahan kas bersih',closing:'Saldo akhir periode',source_difference:'Selisih saldo dan jurnal'} as const
function queryFor(from:string,to:string):AnalysisDates{
 const previous=new Date(Date.parse(from+'T00:00:00Z')-86400000).toISOString().slice(0,10)
 return {from,to,as_of:to,compare_from:previous,compare_to:previous}
}

import TransactionSourceLink from './TransactionSourceNavigation'

export default function ConnectedCashLedgerPage(){
 const {runtime,identity}=useAuth()
 if(!isConnectedRuntime(runtime)||identity.status!=='AUTHORIZED'||!identity.permissions.includes('finance.cash.view')||!identity.permissions.includes('finance.reports.view'))return <section className="panel" role="alert">Hak melihat kas dan laporan keuangan diperlukan.</section>
 if(!['OWNER','ADMIN'].includes(identity.profile.role))return <section className="panel" role="alert">Sumber kas ini tersedia untuk Owner atau Admin.</section>
 return <Workspace key={`${runtime.projectRef}:${identity.profile.id}:${identity.profile.rowVersion}:${identity.profile.roleRowVersion}:${identity.permissions.join('|')}`}/>
}

function Workspace(){
 const {runtime,identity}=useAuth();if(!isConnectedRuntime(runtime)||identity.status!=='AUTHORIZED')throw Error('Sesi kas belum siap.')
 const client=useMemo(()=>getUatSupabaseClient(runtime),[runtime]),today=cp6WibDateTimeInput().slice(0,10)
 const [from,setFrom]=useState(today.slice(0,7)+'-01'),[to,setTo]=useState(today),[data,setData]=useState<FinanceAnalysis|null>(null),[busy,setBusy]=useState(false),[error,setError]=useState('')
 const seq=useRef(0),selected=useRef(queryFor(today.slice(0,7)+'-01',today))
 useEffect(()=>()=>{++seq.current},[])
 const retire=useCallback(()=>{++seq.current;setData(null);setBusy(false);setError('')},[])
 const recoveryScope=`${runtime.projectRef}:${identity.profile.id}`,recoveryBlocked=useFinancialRecoveryGate(recoveryScope,retire)
 const load=useCallback(async(query:AnalysisDates,offset=0)=>{
  const ticket=++seq.current;setData(null);setError('');setBusy(true)
  try{
   if(financialRecoveryBlocked(recoveryScope))return
   const response=await client.rpc('erp_cp7_get_finance_analysis_v1',{p_query:{...query,offset,limit:25}})
   if(ticket!==seq.current||financialRecoveryBlocked(recoveryScope))return
   if(response.error)throw response.error
   setData(parseFinanceAnalysis(response.data,query,offset))
  }catch(e){if(ticket===seq.current)setError(normalizeClientError(e).message)}finally{if(ticket===seq.current)setBusy(false)}
 },[client,recoveryScope])
 useEffect(()=>{void load(selected.current)},[load])
 const submit=()=>{
  retire()
  if(!financeDate(from)||!financeDate(to)||from>to||to>today){setError('Pilih periode kas yang sah sampai hari ini.');return}
  const query=queryFor(from,to)
  if(!financeDate(query.compare_from)){setError('Awal periode kas berada di luar tanggal yang didukung.');return}
  selected.current=query;void load(query)
 }
 const cash=data?.cash,page=cash?.entries
 return <main className="cproc ccash" aria-label="Kas dan bank dari jurnal">
  <header><div><span>KEUANGAN · SALDO BUKU</span><h1>Kas & Bank</h1><p>Saldo dan mutasi rekening menurut tanggal pembukuan.</p></div></header>
  <section className="panel">
   <form className="cproc-grid" onSubmit={e=>{e.preventDefault();submit()}}>
    <label>Periode dari<input type="date" aria-label="Periode kas dari" value={from} onChange={e=>{retire();setFrom(e.target.value)}}/></label>
    <label>Periode sampai<input type="date" aria-label="Periode kas sampai" value={to} onChange={e=>{retire();setTo(e.target.value)}}/></label>
    <button disabled={busy}>Tampilkan kas</button>
   </form>
   {busy?<p role="status">Membaca saldo dan sumber jurnal kas…</p>:null}
   {error?<p role="alert">{error}</p>:null}
   {recoveryBlocked?<p role="alert">{financialRecoveryMessage}</p>:null}
   {!recoveryBlocked&&data&&cash&&page?<>
    <p>Periode {data.dates.from}–{data.dates.to}. Informasi yang tercatat sekarang; bukan rekonstruksi pengetahuan masa lalu. Dibaca {formatCp6WibDateTime(data.captured_at)}.</p>
    <section className="cproc-grid" aria-label="Saldo dan perubahan kas">{Object.entries(metrics).map(([key,label])=><div className="cproc-total" key={key}><span>{label}</span><strong>{money(cash[key as keyof typeof metrics])}</strong></div>)}</section>
    <p>{cash.reconciled?'Saldo dan jurnal kas cocok.':'Saldo dan jurnal kas belum cocok. Periksa sumber sebelum memakai hasil.'}</p>
    <p>Rekening tidak aktif yang memiliki riwayat tetap dihitung. Akun buku yang sama dihitung sekali. Transfer antarrekening masuk debit dan kredit, dengan perubahan kas bersih nol. Penerimaan kas tidak otomatis menjadi penjualan.</p>
    <section aria-label="Sumber jurnal kas">
     <h2>Sumber jurnal kas</h2>
     {page.rows.length===0?<p>Tidak ada jurnal kas dalam periode ini.</p>:null}
     {page.rows.map(row=><article className="cproc-item" data-journal-id={row.id} key={row.id}>
      <strong>{row.journal_number}</strong><p>{row.source_type} · pembukuan {row.transaction_date} · kejadian {row.economic_date}</p>
      <p>Debit {money(row.debit)} · kredit {money(row.credit)} · bersih {money(row.net)}.</p>
      <TransactionSourceLink sourceType={row.source_type} sourceId={row.source_id} disabled={busy}/>{row.source_id?<small>Dokumen sumber {row.source_id}</small>:null}
      {row.reversal_of_id?<small>Pembalikan jurnal {row.reversal_of_id}</small>:row.status==='REVERSED'?<small>Jurnal asli sudah dibalik. Catatan asli dan pembalikannya mengikuti tanggal pembukuan masing-masing.</small>:null}
     </article>)}
     <div className="cproc-pagination"><span>Total {page.total} jurnal · halaman mulai {page.offset+1}</span>
      <button disabled={busy||page.offset===0} onClick={()=>void load(selected.current,Math.max(0,page.offset-25))}>Jurnal sebelumnya</button>
      <button disabled={busy||page.next_offset===null} onClick={()=>void load(selected.current,page.next_offset??0)}>Jurnal berikutnya</button>
     </div>
    </section>
   </>:null}
  </section>
 </main>
}
