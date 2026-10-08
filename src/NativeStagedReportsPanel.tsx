import {useEffect,useMemo,useRef,useState} from 'react'
import {useAuth} from './auth/AuthProvider'
import {getUatSupabaseClient} from './lib/supabase'
import {normalizeClientError} from './lib/clientError'
import {formatCp6WibDateTime} from './cp6BusinessTime'
import {reportKindLabels,reportKinds,type ReportKind} from './nativeAnalysisReports'
import type {AnalysisFinanceAccess} from './nativeAnalysis'
import type {StagedAnalysis} from './nativeAnalysisPages'
import {driveStagedReport,parseStagedReport,parseStagedReportSection,parseStagedReportIndex,readStagedReportRequest,persistStagedReportRequest,clearStagedReportRequest,
 stagedReportRequestKey,stagedReportProgressText,stagedReportFailureText,stagedReportFreshnessText,type StagedReport,type StagedReportIndex,type StagedReportJob,
 type StagedReportRequest,type StagedReportSection,type StagedReportRpc} from './nativeStagedReports'

// Business Report v2 of the staged run on screen (snapshot contract v2 §4).
// The report is built by the server step by step and sealed once; this panel
// keeps the request so a reload resumes it, shows the real progress, then the
// sealed summary and one section at a time. The analysis is always the
// snapshot "data per <time>"; actual stock, finance and HPP are the ones the
// server read for the report date.
type Props={staged:StagedAnalysis;blocked:boolean;financeAccess:AnalysisFinanceAccess}
type Base={seriesId:string;revision:string;kind:ReportKind}
export default function NativeStagedReportsPanel(props:Props){
 const{runtime,identity}=useAuth();if(runtime.mode!=='DISPOSABLE_TEST'||identity.status!=='AUTHORIZED')return null
 return<Reports {...props} key={`${runtime.projectRef}:${identity.profile.id}`} scope={`analysis:${runtime.projectRef}:${identity.profile.id}`} actor={identity.profile.authUserId}/>
}
function Reports({staged,blocked:outer,financeAccess,scope,actor}:Props&{scope:string;actor:string}){
 const{runtime}=useAuth();if(runtime.mode!=='DISPOSABLE_TEST')throw Error('Sesi laporan ERP belum siap.')
 const client=useMemo(()=>getUatSupabaseClient(runtime),[runtime]),run=staged.set,seq=useRef(0),mounted=useRef(true)
 const[recovery,setRecovery]=useState(()=>readStagedReportRequest(scope)),[job,setJob]=useState<StagedReportJob|null>(null)
 const[kind,setKind]=useState<ReportKind>(recovery.pending?.payload.kind??'DAILY'),[title,setTitle]=useState(recovery.pending?.payload.title??''),[reason,setReason]=useState(recovery.pending?.payload.reason??'')
 const[withFinance,setWithFinance]=useState(false),[reviewed,setReviewed]=useState(false),[base,setBase]=useState<Base|null>(null)
 const[report,setReport]=useState<StagedReport|null>(null),[section,setSection]=useState<StagedReportSection|null>(null),[sectionIndex,setSectionIndex]=useState(0),[index,setIndex]=useState<StagedReportIndex|null>(null)
 const[busy,setBusy]=useState(false),[error,setError]=useState(''),[message,setMessage]=useState('')
 useEffect(()=>{mounted.current=true;return()=>{mounted.current=false;++seq.current}},[])
 useEffect(()=>{const listener=(e:StorageEvent)=>{if(e.key===null||e.key===stagedReportRequestKey(scope))setRecovery(readStagedReportRequest(scope))};addEventListener('storage',listener);return()=>removeEventListener('storage',listener)},[scope])
 const blocked=outer||busy
 const rpc:StagedReportRpc={publish:r=>client.rpc('erp_cp7_publish_report_v2',{p_payload:r.payload,p_request:r.id}),lookup:r=>client.rpc('erp_cp7_get_report_request_v2',{p_payload:r.payload,p_request:r.id}),
  step:id=>client.rpc('erp_cp7_step_report_v2',{p_request:id})}
 const perform=async(op:(n:number)=>Promise<void>)=>{const n=++seq.current;setBusy(true);setError('');setMessage('');try{await op(n)}catch(e){if(n===seq.current&&mounted.current)setError(normalizeClientError(e).message)}finally{if(n===seq.current&&mounted.current){setBusy(false);setRecovery(readStagedReportRequest(scope))}}}
 const open=async(id:string,n:number)=>{const r=await client.rpc('erp_cp7_read_report_v2',{p_id:id});if(n!==seq.current)return;if(r.error)throw r.error;const d=await parseStagedReport(r.data,actor);if(n!==seq.current)return;if(d.id!==id)throw Error('Identitas laporan server berubah.');setReport(d);setSection(null);setSectionIndex(0)}
 const drive=(r:StagedReportRequest,lookup:boolean)=>perform(async n=>{
  setReport(null);setSection(null)
  const last=await driveStagedReport({rpc,request:r,lookup,aborted:()=>n!==seq.current||!mounted.current,onStatus:s=>{if(n===seq.current)setJob(s)}})
  if(!last||n!==seq.current)return
  clearStagedReportRequest(scope,r);setRecovery(readStagedReportRequest(scope))
  if(last.state==='DONE'){setReviewed(false);setBase(null);await open(last.publicationId!,n);if(n===seq.current)setMessage('Laporan tersimpan. Isinya tidak berubah lagi; revisi menjadi versi baru.')}
  else if(last.state==='FAILED')setError(stagedReportFailureText(last.failure!))
  else setMessage('Server memastikan permintaan lama belum tersimpan dan sudah ditutup. Buat permintaan laporan baru bila masih diperlukan.')
 })
 const publish=()=>{try{
  const held=readStagedReportRequest(scope);if(held.error||held.pending)throw Error(held.error??'Selesaikan laporan bertahap yang tertunda terlebih dahulu.')
  if(!reviewed||!title.trim()||!reason.trim())throw Error('Isi judul dan alasan, lalu konfirmasi peninjauan laporan.')
  if(base&&base.kind!==kind)throw Error('Revisi harus memakai jenis laporan yang sama dengan serinya.')
  const r:StagedReportRequest={id:crypto.randomUUID(),payload:{run_id:run.runId,identity_hash:run.identityHash,kind,series_id:base?.seriesId??null,expected_revision:base?.revision??null,
   title,reason,finance:withFinance&&financeAccess.ownerReports?'INCLUDED':'DEFERRED',explicit_review:true}}
  persistStagedReportRequest(scope,r);setRecovery(readStagedReportRequest(scope));void drive(r,false)
 }catch(e){setError(normalizeClientError(e).message)}}
 const resume=(lookup:boolean)=>{const held=readStagedReportRequest(scope);setRecovery(held);if(!held.pending){setError(held.error??'Permintaan laporan tersimpan tidak tersedia.');return}void drive(held.pending,lookup)}
 const list=(before:string|null=null)=>void perform(async n=>{const r=await client.rpc('erp_cp7_list_reports_v2',{p_query:{before_id:before,limit:25}});if(n!==seq.current)return;if(r.error)throw r.error;setIndex(parseStagedReportIndex(r.data,actor,25))})
 const readSection=()=>{const d=report;if(!d)return;const i=sectionIndex;void perform(async n=>{const r=await client.rpc('erp_cp7_read_report_section_v2',{p_id:d.id,p_index:i,p_access:d.accessEpoch});if(n!==seq.current)return;if(r.error)throw r.error;const s=await parseStagedReportSection(r.data,d,i);if(n===seq.current)setSection(s)})}
 const revise=()=>{if(!report)return;setBase({seriesId:report.seriesId,revision:report.revision,kind:report.kind});setKind(report.kind);setReviewed(false);setMessage('Isi judul dan alasan revisi. Revisi memakai analisis bertahap yang sedang dibuka; isi laporan lama tetap tersimpan.')}
 const pending=recovery.pending,mine=pending&&pending.payload.run_id===run.runId
 return<section className="panel" role="region" aria-label="Laporan analisis bertahap" data-report-state={job?.state??''}>
  <h3>Laporan dari analisis bertahap</h3>
  <p>Laporan memakai data analisis per {formatCp6WibDateTime(run.reference.capturedAt)}: angka analisis adalah keadaan pada waktu itu, bukan angka saat ini. Stok barang jadi aktual dibaca saat laporan dibuat, dan keuangan serta HPP hanya diambil dari laporan keuangan ERP untuk tanggal laporan.</p>
  {busy&&job?<p role="status">{stagedReportProgressText(job)}</p>:busy?<p role="status">Memeriksa laporan dan izin ERP…</p>:null}
  {error||recovery.error?<p role="alert">{error||recovery.error}</p>:null}{message?<p role="status">{message}</p>:null}
  {pending?<div role="status"><p>{mine?'Ada laporan dari analisis ini yang belum selesai disusun. Permintaan yang sama dipertahankan.':'Ada laporan dari analisis bertahap lain yang belum selesai. Selesaikan dulu dari sini.'}</p>
   <button disabled={blocked} onClick={()=>resume(false)}>Lanjutkan laporan yang tertunda</button><button disabled={blocked} onClick={()=>resume(true)}>Periksa hasil laporan yang tertunda</button></div>:null}
  <label>Jenis laporan<select aria-label="Jenis laporan bertahap" value={kind} disabled={blocked||Boolean(pending)||Boolean(base)} onChange={e=>{setKind(e.target.value as ReportKind);setReviewed(false)}}>{reportKinds.map(k=><option key={k} value={k}>{reportKindLabels[k]}</option>)}</select></label>
  <label>Judul laporan<input aria-label="Judul laporan bertahap" value={title} maxLength={200} disabled={blocked} onChange={e=>{setTitle(e.target.value);setReviewed(false)}}/></label>
  <label>Alasan penerbitan atau revisi<textarea aria-label="Alasan laporan bertahap" value={reason} maxLength={1000} disabled={blocked} onChange={e=>{setReason(e.target.value);setReviewed(false)}}/></label>
  {financeAccess.ownerReports?<label><input type="checkbox" aria-label="Sertakan keuangan dan HPP pada laporan bertahap" checked={withFinance} disabled={blocked} onChange={e=>{setWithFinance(e.target.checked);setReviewed(false)}}/> Sertakan keuangan dan HPP dari laporan keuangan ERP untuk tanggal laporan (menunggu buku besar)</label>:<p>Keuangan dan HPP tidak dimasukkan; akun ini tidak membuka laporan keuangan.</p>}
  {base?<p>Revisi seri yang dipilih, setelah versi {base.revision}. <button disabled={blocked} onClick={()=>{setBase(null);setReviewed(false)}}>Jadikan laporan baru</button></p>:null}
  <label><input aria-label="Laporan bertahap sudah ditinjau" type="checkbox" checked={reviewed} disabled={blocked||Boolean(pending)} onChange={e=>setReviewed(e.target.checked)}/> Saya sudah meninjau analisis, asumsi dan bagian yang belum diketahui.</label>
  <button disabled={blocked||Boolean(pending)||Boolean(recovery.error)||!reviewed||!title.trim()||!reason.trim()} onClick={publish}>{base?'Simpan revisi laporan bertahap':'Buat laporan dari analisis ini'}</button>
  <button disabled={blocked} onClick={()=>list()}>Muat laporan bertahap tersimpan</button>
  {index?<><p>{index.rows.length} pada halaman ini · {index.total} laporan bertahap yang dapat diakses.</p>{index.rows.map((r,i)=><button key={r.id} disabled={blocked} aria-label={`Buka laporan bertahap ${i+1}`} onClick={()=>void perform(n=>open(r.id,n))}>{r.title} · versi {r.revision} · data per {formatCp6WibDateTime(r.dataAsOf)}</button>)}{index.nextBeforeId?<button disabled={blocked} onClick={()=>list(index.nextBeforeId)}>Halaman laporan bertahap berikutnya</button>:null}</>:null}
  {report?<article aria-label="Isi laporan bertahap" data-report-id={report.id} data-freshness-state={report.freshness.state}>
   <h4>{report.title} · versi {report.revision}</h4>
   <p>{report.isLatest?'Versi terbaru dalam seri ini.':'Versi lama; revisi berikutnya sudah tersedia.'} Data analisis per {formatCp6WibDateTime(report.dataAsOf)}. {stagedReportFreshnessText(report)}</p>
   <p>Stok barang jadi aktual dibaca {formatCp6WibDateTime(report.actualsReadAt)} · tanggal laporan {report.reportDate}. {report.finance==='INCLUDED'?'Keuangan dan HPP dari laporan keuangan ERP untuk tanggal itu.':'Keuangan dan HPP tidak dimasukkan.'}</p>
   <p>Alasan: {report.reason}</p>
   <button disabled={blocked||!report.isLatest||staged.header.query.from_date!==report.query.from_date||staged.header.query.through_date!==report.query.through_date||staged.header.query.group_mode!==report.query.group_mode} onClick={revise}>Buat revisi dari laporan ini</button>
   <pre aria-label="Ringkasan laporan bertahap">{report.summary}</pre>
   {report.sections.length?<div><label>Pilih bagian laporan<select aria-label="Pilih bagian laporan bertahap" value={sectionIndex} disabled={blocked} onChange={e=>{setSectionIndex(Number(e.target.value));setSection(null)}}>{report.sections.map(s=><option key={s.index} value={s.index}>Bagian {s.index+1}: target {s.targetLo}–{s.targetHi} dari {report.targetsTotal}</option>)}</select></label>
    <button disabled={blocked} onClick={readSection}>Buka bagian laporan</button></div>:<p>Analisis ini tidak memuat rincian per target.</p>}
   {section?<pre aria-label="Bagian laporan bertahap" data-section-index={section.index}>{section.body}</pre>:null}
   <details><summary>Identitas laporan</summary><p>Analisis {report.runId} · identitas {report.identityHash}</p><p>Hash laporan {report.reportHash} · diterbitkan {formatCp6WibDateTime(report.publishedAt)}.</p></details>
  </article>:null}
 </section>
}
