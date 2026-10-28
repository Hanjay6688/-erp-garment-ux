import {useCallback,useEffect,useRef,useState} from 'react'
import {formatCp6WibDateTime} from './cp6BusinessTime'
import {formatReceiptDecimal} from './procurementContract'
import {normalizeClientError} from './lib/clientError'
import {analysisFinanceMetricLabel} from './nativeAnalysis'
import {financeFiguresVisible,type AnalysisFinance} from './nativeAnalysisFinanceSidecar'
import {parseStagedJob,type StagedReply,type StagedRequest} from './nativeStagedJob'
import type {StagedReference} from './nativeAnalysisPages'

const failure=(code:string|null)=>code==='CP7_FINANCE_CAPTURE_SOURCE_CHANGED'?'Buku berubah selama laporan dibaca. Mulai analisis baru agar angkanya memakai satu keadaan data.'
 :code==='CP7_FINANCE_REPORT_TIME_LIMIT'?'Laporan resmi belum selesai dibaca dalam batas waktunya. Angka keuangan belum tersedia.'
 :'Angka laporan resmi belum bisa dipakai. Periksa kelengkapan laporan lalu mulai analisis baru.'
export function AnalysisFinanceSummary({data,allowed,progressOnly=false}:{data:AnalysisFinance;allowed:boolean;progressOnly?:boolean}){
 if(!allowed||data.state==='ACCESS_REVOKED')return<p>Akun saat ini belum boleh membaca angka keuangan analisis. Minta Owner memeriksa hak aksesnya.</p>
 const c=data.capture,r=data.result
 return<>
  {c?<p>Laporan resmi: {c.unitsTotal===null?`${formatReceiptDecimal(String(c.unitsDone))} langkah selesai; jumlah langkah total belum diketahui.`:`${formatReceiptDecimal(String(c.unitsDone))} dari ${formatReceiptDecimal(String(c.unitsTotal))} langkah selesai.`}</p>:null}
  {data.state==='RUNNING'?<p role="status">Angka keuangan sedang disiapkan dari Laporan Keuangan. Hasil operasional tetap bisa dibaca. Laba dan HPP yang belum siap belum ditampilkan.</p>:null}
  {data.state==='FAILED'?<p role="alert">{failure(c?.failureCode??null)}</p>:null}
  {data.state==='READY'&&r?.readiness!=='READY'?<p>Perhitungan laporan selesai, tetapi HPP atau bukunya belum lengkap. Angka laba, biaya dan nilai persediaan masih menunggu; tidak dianggap nol.</p>:null}
  {data.state==='READY'&&r?.readiness==='READY'&&progressOnly?<p>Laporan keuangan sudah siap. Analisis operasional masih diselesaikan.</p>:null}
  {financeFiguresVisible(data,allowed)&&r&&!progressOnly?<>
   <p>Laporan resmi dibaca {formatCp6WibDateTime(r.reportReadAt)}; periode {r.dates.from} sampai {r.dates.to}, posisi buku per {r.dates.asOf}. Jam pembacaan laporan dan data operasional ditampilkan terpisah.</p>
   <p>Angka berasal dari pembaca yang sama dengan Laporan Keuangan.</p>
   <div className="responsive-table"><table><thead><tr><th>Angka laporan resmi</th><th>Nilai</th></tr></thead><tbody>{r.metrics.map(m=><tr key={m.id} data-finance-metric={m.id}><td>{analysisFinanceMetricLabel(m.id)}</td><td>{m.value.state==='KNOWN'?`Rp${formatReceiptDecimal(m.value.value)}`:'Belum diketahui'}</td></tr>)}</tbody></table></div>
  </>:null}
 </>
}
type Props={request:StagedRequest;runId:string;reference:StagedReference;allowed:boolean;get:(id:string)=>Promise<StagedReply>}
// Two minute-schedule opportunities plus the bounded initial stage and read
// margin. This stops this page's observation only; it never fails/cancels a job.
const FINANCE_NO_PROGRESS_MS=150_000
export default function NativeAnalysisFinancePanel({request,runId,reference,allowed,get}:Props){
 const seq=useRef(0),busy=useRef(false),timer=useRef<ReturnType<typeof setTimeout>|null>(null)
 const observed=useRef<{key:string;unitsDone:number;unitsTotal:number|null;reportReadAt:string|null;since:number}|null>(null)
 const[shown,setShown]=useState<{runId:string;data:AnalysisFinance}|null>(null),[loading,setLoading]=useState(false),[error,setError]=useState('')
 const[monitorPaused,setMonitorPaused]=useState(false)
 const clearTimer=()=>{if(timer.current!==null){clearTimeout(timer.current);timer.current=null}}
 const load=useCallback(async():Promise<void>=>{
  if(!allowed||request.finance!=='STAGED'||busy.current)return
  clearTimer();const n=++seq.current;busy.current=true;setShown(null);setError('');setLoading(true)
  try{
   const r=await get(request.id);if(n!==seq.current)return;if(r.error)throw r.error
   const status=parseStagedJob(r.data,request.id,request)
   if(status.state!=='DONE'||status.runId!==runId||status.reference.sourceHash!==reference.sourceHash||Date.parse(status.reference.capturedAt)!==Date.parse(reference.capturedAt)||!status.financeCapture)throw Error('finance binding')
   if(status.retention?.state==='EXPIRED')throw Error('finance expired')
   setShown({runId,data:status.financeCapture})
   if(status.financeCapture.state==='RUNNING'){
    const c=status.financeCapture.capture;if(!c)throw Error('finance capture missing')
    const key=[request.id,runId,reference.sourceHash,reference.capturedAt,c.id].join('|'),now=performance.now(),prior=observed.current
    if(!prior||prior.key!==key||c.unitsDone>prior.unitsDone||prior.unitsTotal===null&&c.unitsTotal!==null||prior.reportReadAt===null&&c.reportReadAt!==null)
     observed.current={key,unitsDone:c.unitsDone,unitsTotal:c.unitsTotal,reportReadAt:c.reportReadAt,since:now}
    const paused=now-observed.current!.since>=FINANCE_NO_PROGRESS_MS
    setMonitorPaused(paused)
    if(!paused)timer.current=setTimeout(()=>{void load()},5000)
   }else{observed.current=null;setMonitorPaused(false)}
  }catch(e){if(n===seq.current){setShown(null);const code=normalizeClientError(e).code;setError(code==='AUTH_REQUIRED'||code==='FORBIDDEN'?'Akun saat ini belum boleh membaca angka keuangan analisis.':e instanceof Error&&e.message==='finance expired'?'Analisis melewati masa simpannya. Mulai analisis baru.':'Status keuangan belum bisa dibaca. Muat ulang status untuk memeriksanya.')}}
  finally{if(n===seq.current){busy.current=false;setLoading(false)}}
 },[allowed,get,reference,request,runId])
 useEffect(()=>{busy.current=false;setShown(null);setError('');setLoading(false);if(!allowed){observed.current=null;setMonitorPaused(false)}void load();return()=>{++seq.current;busy.current=false;clearTimer()}},[load,allowed])
 useEffect(()=>{const focus=()=>{if(document.visibilityState==='visible')void load()};addEventListener('focus',focus);document.addEventListener('visibilitychange',focus);return()=>{removeEventListener('focus',focus);document.removeEventListener('visibilitychange',focus)}},[load])
 const data=shown?.runId===runId&&shown.data.requestId===request.id&&shown.data.reference.sourceHash===reference.sourceHash
  &&Date.parse(shown.data.reference.capturedAt)===Date.parse(reference.capturedAt)
  &&shown.data.query.from_date===request.q.from_date&&shown.data.query.through_date===request.q.through_date&&shown.data.query.group_mode===request.q.group_mode?shown.data:null
 return<section className="native-analysis-finance" aria-label="Keuangan analisis dari laporan resmi"><h3>Angka keuangan dari laporan resmi</h3>
  {!allowed?<p>Akun saat ini belum boleh membaca angka keuangan analisis.</p>:<>
   <p>Data operasional per {formatCp6WibDateTime(reference.capturedAt)}.</p>
   {loading?<p role="status">Membaca kemajuan laporan keuangan…</p>:null}
   {error?<p role="alert">{error}</p>:null}
   {data?<AnalysisFinanceSummary data={data} allowed={allowed}/>:null}
   {data?.state==='RUNNING'&&monitorPaused?<p role="alert">Belum ada kemajuan laporan keuangan yang teramati selama 2 menit 30 detik. Pemantauan otomatis dijeda; jeda ini tidak membatalkan pekerjaan. Muat ulang status keuangan untuk memeriksa pekerjaan yang sama.</p>:null}
   <button type="button" disabled={loading} onClick={()=>{observed.current=null;setMonitorPaused(false);void load()}}>Muat ulang status keuangan</button>
  </>}
 </section>
}
