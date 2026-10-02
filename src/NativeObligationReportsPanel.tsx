import {useEffect,useMemo,useRef,useState} from 'react'
import {useAuth} from './auth/AuthProvider'
import {getUatSupabaseClient} from './lib/supabase'
import {normalizeClientError} from './lib/clientError'
import {formatCp6WibDateTime} from './cp6BusinessTime'
import {productionLockManager,productionLockName,readProductionRecovery,hasProductionPending} from './productionRecovery'
import type {NativeReport} from './nativeAnalysisReports'
import type {NativeAnalysis,AnalysisFinanceAccess} from './nativeAnalysis'
import {parseObligationReportPreview,parseObligationReport,parseObligationReportCommand,parseObligationReportIndex,assertSameObligationReport,renderObligationReport,
 readObligationReportRequest,persistObligationReportRequest,clearObligationReportRequest,obligationReportRequestKey,
 type ObligationReportPreview,type ObligationReport,type ObligationReportRequest,type ObligationReportIndex} from './nativeObligationReports'

type Props={base:NativeReport|null;context:NativeAnalysis|null;generation:number;blocked:boolean;access:AnalysisFinanceAccess;
 onReadStart:()=>number;isReadCurrent:(n:number)=>boolean;onReadEnd:(n:number)=>void;onAnalysis:(a:NativeAnalysis,n:number)=>void;requireClear:()=>void}
type Facts={generation:number;authority:string;preview:ObligationReportPreview|null;document:ObligationReport|null;index:ObligationReportIndex|null;runId:string|null;copy:string}
const empty:Facts={generation:-1,authority:'',preview:null,document:null,index:null,runId:null,copy:''}
export default function NativeObligationReportsPanel(props:Props){
 const {runtime,identity}=useAuth()
 if(runtime.mode!=='DISPOSABLE_TEST'||identity.status!=='AUTHORIZED'||!['master.product.view','production.wip.view','warehouse.stock.view','sales.invoice.view'].every(p=>identity.permissions.includes(p)))return null
 return <Appendix {...props} key={runtime.projectRef+':'+identity.profile.id}/>
}
function Appendix(props:Props){
 const {runtime,identity}=useAuth();if(runtime.mode!=='DISPOSABLE_TEST'||identity.status!=='AUTHORIZED')throw Error('Sesi lampiran belum siap.')
 const client=useMemo(()=>getUatSupabaseClient(runtime),[runtime]),scope=`analysis:${runtime.projectRef}:${identity.profile.id}`,productionScope=`${runtime.projectRef}:${identity.profile.id}`,actor=identity.profile.authUserId
 const rights={ar:identity.permissions.includes('finance.ar.view'),ap:identity.permissions.includes('finance.ap.view'),payroll:identity.permissions.includes('finance.payroll.view'),accessoryPayables:identity.permissions.includes('warehouse.accessory.view')&&identity.permissions.some(p=>p==='finance.hpp.view'||p==='finance.hpp.manage'),laundry:identity.permissions.includes('production.laundry.view')&&identity.permissions.some(p=>p==='finance.hpp.view'||p==='finance.hpp.manage')}
 const authority=JSON.stringify([scope,actor,identity.profile.role,identity.profile.rowVersion,identity.profile.roleRowVersion,identity.permissions,props.access]),latest=useRef(authority);latest.current=authority
 const initial=useRef(readObligationReportRequest(scope)),[recovery,setRecovery]=useState(initial.current)
 const [title,setTitle]=useState(initial.current.pending?.payload.title??''),[reason,setReason]=useState(initial.current.pending?.payload.reason??''),[reviewed,setReviewed]=useState(false)
 const [revision,setRevision]=useState<{seriesId:string;revision:string}|null>(null),[facts,setFacts]=useState<Facts>(empty),[busy,setBusy]=useState(false),[error,setError]=useState(''),[message,setMessage]=useState('')
 const callbacks=useRef(props);callbacks.current=props;const mounted=useRef(true),active=useRef<number|null>(null)
 useEffect(()=>{mounted.current=true;return()=>{mounted.current=false;if(active.current!==null)callbacks.current.onReadEnd(active.current)}},[])
 useEffect(()=>{setFacts(empty);setReviewed(false);setRevision(null)},[authority])
 useEffect(()=>{const listener=(e:StorageEvent)=>{if(e.key===null||e.key===obligationReportRequestKey(scope)){setRecovery(readObligationReportRequest(scope));setFacts(empty);setReviewed(false)}};addEventListener('storage',listener);return()=>removeEventListener('storage',listener)},[scope])
 const current=(n:number,a:string)=>mounted.current&&latest.current===a&&callbacks.current.isReadCurrent(n)
 const visible=facts.generation===props.generation&&facts.authority===authority?facts:empty,blocked=props.blocked||busy||Boolean(recovery.error||recovery.pending)
 const perform=async(operation:(n:number,a:string)=>Promise<void>)=>{
  if(active.current!==null)return;const a=authority,n=props.onReadStart();active.current=n;setBusy(true);setFacts(empty);setReviewed(false);setError('');setMessage('')
  try{props.requireClear();await operation(n,a)}catch(e){if(current(n,a))setError(normalizeClientError(e).message)}finally{if(mounted.current){setRecovery(readObligationReportRequest(scope));setBusy(false)}if(active.current===n)active.current=null;callbacks.current.onReadEnd(n)}
 }
 const load=()=>{const base=props.base;if(!base)return;void perform(async(n,a)=>{
  const response=await client.rpc('erp_cp7_get_obligation_report_preview_v1',{p_publication:base.id});if(!current(n,a))return;if(response.error)throw response.error
  const preview=await parseObligationReportPreview(response.data,actor,props.access,rights);if(!current(n,a))return;if(preview.base.id!==base.id)throw Error('Arsip dasar lampiran berubah.')
  setFacts({...empty,generation:n,authority:a,preview});props.onAnalysis(preview.source.analysis,n)
 })}
 const command=(r:ObligationReportRequest,lookup:boolean)=>void perform(async(n,a)=>{
  const manager=productionLockManager();if(!manager)throw Error('Penyimpanan lampiran memerlukan pengunci tab.')
  await manager.request(productionLockName(productionScope),{mode:'exclusive',ifAvailable:true},async lock=>{
   if(!lock)throw Error('Ada transaksi ERP di tab lain. Tunggu selesai, lalu periksa kembali.');if(!current(n,a))return
   const shared=readProductionRecovery(productionScope);if(shared.corrupted||!lookup&&hasProductionPending(shared))throw Error('Pastikan hasil transaksi ERP yang tertunda terlebih dahulu.')
   persistObligationReportRequest(scope,r);setRecovery(readObligationReportRequest(scope))
   const args={p_payload:r.payload,p_request:r.id}
   const response=lookup?await client.rpc('erp_cp7_get_obligation_report_request_v1',args):await client.rpc('erp_cp7_publish_obligation_report_v1',args);if(!current(n,a))return;if(response.error)throw response.error
   const result=await parseObligationReportCommand(response.data,r,actor,props.access,rights);if(!current(n,a))return
   clearObligationReportRequest(scope,r);setRecovery(readObligationReportRequest(scope));setFacts({...empty,generation:n,authority:a,document:result.document})
   if(result.document)props.onAnalysis(result.document.base.analysis,n)
   setMessage(result.status==='COMMITTED'?'Lampiran tersimpan. Arsip dasar dan lampiran lama tetap utuh.':'Server memastikan permintaan lama belum tersimpan dan sudah ditutup. Periksa sumber sebelum membuat permintaan baru.')
  })
 })
 const save=()=>{try{const p=visible.preview;if(!p||!reviewed||!title.trim()||!reason.trim())throw Error('Periksa lampiran, isi judul dan alasan, lalu konfirmasi peninjauan.');const held=readObligationReportRequest(scope);if(held.pending||held.error)throw Error(held.error??'Pastikan hasil lampiran yang tertunda terlebih dahulu.');command({id:crypto.randomUUID(),payload:{publication_id:p.base.id,run_id:p.base.runId,source_hash:p.source.hash,title,reason,explicit_review:true,series_id:revision?.seriesId??null,expected_revision:revision?.revision??null}},false)}catch(e){setError(normalizeClientError(e).message)}}
 const retry=(lookup:boolean)=>{const held=readObligationReportRequest(scope);if(held.pending)command(held.pending,lookup);else setError(held.error??'Permintaan lampiran tersimpan tidak tersedia.')}
 const open=(id:string,copy=false)=>{const old=visible.document;void perform(async(n,a)=>{
  const response=await client.rpc('erp_cp7_read_obligation_report_v1',{p_id:id});if(!current(n,a))return;if(response.error)throw response.error
  const document=await parseObligationReport(response.data,actor,props.access,rights);if(!current(n,a))return;if(document.id!==id)throw Error('Identitas lampiran berubah.');if(old?.id===id)assertSameObligationReport(old,document)
  const text=copy?(document.state==='ARCHIVED_STALE'?'ARSIP LAMA: berikut isi saat lampiran disimpan.\n\n':'')+document.body:''
  setFacts({...empty,generation:n,authority:a,document,copy:text});props.onAnalysis(document.base.analysis,n)
  if(copy){if(new TextEncoder().encode(text).byteLength>1000000){setMessage('Isi lengkap tersedia untuk disalin manual.');return}try{await navigator.clipboard.writeText(text);if(current(n,a))setMessage('Lampiran yang sudah diperiksa disalin.')}catch{if(current(n,a))setMessage('Salin otomatis gagal. Isi lengkap tersedia untuk disalin manual.')}}
 })}
 const list=(before:string|null=null)=>{const runId=props.context?.runId??visible.runId;if(!runId)return;void perform(async(n,a)=>{
  const response=await client.rpc('erp_cp7_list_obligation_reports_v1',{p_query:{run_id:runId,before_id:before,limit:25}});if(!current(n,a))return;if(response.error)throw response.error
  const index=parseObligationReportIndex(response.data,actor,25);setFacts({...empty,generation:n,authority:a,index,runId})
 })}
 return <section className="panel" aria-label="Lampiran tagihan laporan ERP"><h3>Lampiran tagihan laporan</h3><p>Laporan dasar tetap memakai angka saat diterbitkan. Lampiran mencatat tagihan yang diketahui saat dibaca, dengan nominal dan tanggal dari sumber ERP.</p>
  {busy?<p role="status">Memeriksa sumber dan izin lampiran…</p>:null}{error||recovery.error?<p role="alert">{error||recovery.error}</p>:null}{message?<p role="status">{message}</p>:null}
  {recovery.pending?<div role="status"><p>Hasil penyimpanan lampiran belum dipastikan. Permintaan yang sama dipertahankan.</p><button disabled={props.blocked||busy} onClick={()=>retry(true)}>Periksa hasil lampiran tersimpan</button><button disabled={props.blocked||busy} onClick={()=>retry(false)}>Ulangi penyimpanan lampiran yang sama</button></div>:null}
  <label>Judul lampiran<input aria-label="Judul lampiran tagihan" value={title} maxLength={200} disabled={busy} onChange={e=>{setTitle(e.target.value);setReviewed(false)}}/></label>
  <label>Alasan lampiran<textarea aria-label="Alasan lampiran tagihan" value={reason} maxLength={1000} disabled={busy} onChange={e=>{setReason(e.target.value);setReviewed(false)}}/></label>
  <button disabled={blocked||!props.base||props.base.analysis.state!=='UNCHANGED'} onClick={load}>Periksa tagihan untuk laporan yang dibuka</button>
  {!props.base&&!visible.preview?<p>Simpan atau buka laporan dasar terlebih dahulu.</p>:null}
  {visible.preview?<><p>Tagihan dibaca {formatCp6WibDateTime(visible.preview.source.readAt)}. Periode laporan dasar {visible.preview.base.query.from_date} sampai {visible.preview.base.query.through_date}.</p><pre aria-label="Pratinjau lampiran tagihan">{renderObligationReport(visible.preview.base,visible.preview.source,title.trim()||'Pratinjau lampiran tagihan')}</pre></>:null}
  {revision?<p>Revisi setelah versi {revision.revision}. <button disabled={blocked} onClick={()=>{setRevision(null);setReviewed(false)}}>Jadikan lampiran baru</button></p>:null}
  <label><input type="checkbox" aria-label="Lampiran tagihan sudah ditinjau" checked={reviewed} disabled={blocked||!visible.preview} onChange={e=>setReviewed(e.target.checked)}/> Saya sudah meninjau sumber, tanggal dan tagihan yang belum diketahui.</label>
  <button disabled={blocked||!visible.preview||!reviewed||!title.trim()||!reason.trim()||!productionLockManager()} onClick={save}>{revision?'Simpan revisi lampiran tagihan':'Simpan lampiran tagihan yang ditinjau'}</button>
  <button disabled={blocked||!props.context&&!visible.runId} onClick={()=>list()}>Muat lampiran tagihan tersimpan</button>
  {visible.index?<><p>{visible.index.rows.length} pada halaman ini · {visible.index.total} lampiran yang dapat diakses.</p>{visible.index.rows.map((r,i)=><button key={r.id} disabled={blocked} aria-label={`Buka lampiran tagihan ${i+1}`} onClick={()=>open(r.id)}>{r.title} · versi {r.revision}</button>)}{visible.index.nextBeforeId?<button disabled={blocked} onClick={()=>list(visible.index!.nextBeforeId)}>Halaman lampiran berikutnya</button>:null}</>:null}
  {visible.document?<article aria-label="Isi lampiran tagihan tersimpan"><h4>{visible.document.title} · versi {visible.document.revision}</h4><p>{visible.document.state==='ARCHIVED_STALE'?'Arsip lama: sumber ERP sudah berubah.':'Sumber sesuai saat diperiksa.'} Tagihan dibaca {formatCp6WibDateTime(visible.document.source.readAt)}.</p><p>Alasan: {visible.document.reason}</p><button disabled={blocked||!visible.document.isLatest} onClick={()=>{setRevision({seriesId:visible.document!.seriesId,revision:visible.document!.revision});setReviewed(false)}}>Buat revisi lampiran ini</button><button disabled={blocked} onClick={()=>open(visible.document!.id,true)}>Periksa & salin lampiran tagihan</button><pre aria-label="Teks lampiran tagihan tersimpan">{visible.document.body}</pre></article>:null}
  {visible.copy?<label>Salinan lampiran lengkap<textarea readOnly aria-label="Salinan manual lampiran tagihan" rows={12} value={visible.copy} onFocus={e=>e.currentTarget.select()}/></label>:null}
 </section>
}
