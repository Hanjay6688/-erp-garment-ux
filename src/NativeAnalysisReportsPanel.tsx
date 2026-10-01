import {useMemo,useRef,useState,useEffect} from 'react'
import {useAuth} from './auth/AuthProvider'
import {getUatSupabaseClient} from './lib/supabase'
import {normalizeClientError} from './lib/clientError'
import {formatCp6WibDateTime} from './cp6BusinessTime'
import {parseNativeReport,parseReportCommand,parseReportIndex,parseReportComparison,assertSameReport,reportKindLabels,reportKinds,readReportRequest,persistReportRequest,clearReportRequest,reportRequestKey,type NativeReport,type ReportIndex,type ReportComparison,type ReportRequest,type ReportKind} from './nativeAnalysisReports'
import {assertSameAnalysis,analysisMetricLabel,type NativeAnalysis,type AnalysisFinanceAccess} from './nativeAnalysis'
import {productionLockManager,productionLockName,readProductionRecovery,hasProductionPending} from './productionRecovery'
import type {NativeDemandQuery} from './nativeDemandHistory'

type Props={context:NativeAnalysis|null;generation:number;blocked:boolean;access:AnalysisFinanceAccess;onReadStart:()=>number;isReadCurrent:(n:number)=>boolean;onReadEnd:(n:number)=>void;onAnalysis:(a:NativeAnalysis,n:number)=>void;requireClear:()=>void}
type Facts={generation:number;document:NativeReport|null;index:ReportIndex|null;comparison:ReportComparison|null}
type RevisionBase={seriesId:string;revision:string;kind:ReportKind;query:NativeDemandQuery}
const emptyFacts:Facts={generation:-1,document:null,index:null,comparison:null}
export default function NativeAnalysisReportsPanel(props:Props){
 const {runtime,identity}=useAuth();if(runtime.mode!=='DISPOSABLE_TEST'||identity.status!=='AUTHORIZED'||!['master.product.view','production.wip.view','warehouse.stock.view','sales.invoice.view'].every(p=>identity.permissions.includes(p)))return null
 return <Reports {...props} projectRef={runtime.projectRef} profileId={identity.profile.id} actor={identity.profile.authUserId}/>
}
function Reports(props:Props&{projectRef:string;profileId:string;actor:string}){
 const {runtime}=useAuth();if(runtime.mode!=='DISPOSABLE_TEST')throw Error('Sesi laporan ERP belum siap.')
 const client=useMemo(()=>getUatSupabaseClient(runtime),[runtime]),scope=`analysis:${props.projectRef}:${props.profileId}`,productionScope=`${props.projectRef}:${props.profileId}`
 const initial=useRef(readReportRequest(scope)),[recovery,setRecovery]=useState(initial.current),[facts,setFacts]=useState<Facts>(emptyFacts)
 const [title,setTitle]=useState(initial.current.pending?.payload.title??''),[reason,setReason]=useState(initial.current.pending?.payload.reason??''),[kind,setKind]=useState<ReportKind>(initial.current.pending?.payload.kind??'DAILY'),[reviewed,setReviewed]=useState(false),[revisionBase,setRevisionBase]=useState<RevisionBase|null>(null)
 const [beforeId,setBeforeId]=useState(''),[afterId,setAfterId]=useState(''),[busy,setBusy]=useState(false),[error,setError]=useState(''),[message,setMessage]=useState(''),[copyText,setCopyText]=useState('')
 const active=useRef<number|null>(null),mounted=useRef(true),callbacks=useRef(props);callbacks.current=props
 useEffect(()=>{mounted.current=true;return()=>{mounted.current=false;if(active.current!==null)callbacks.current.onReadEnd(active.current)}},[])
 useEffect(()=>{const listener=(e:StorageEvent)=>{if(e.key===null||e.key===reportRequestKey(scope)){setRecovery(readReportRequest(scope));setFacts(emptyFacts);setCopyText('')}};addEventListener('storage',listener);return()=>removeEventListener('storage',listener)},[scope])
 const current=(n:number)=>mounted.current&&props.isReadCurrent(n),visible=facts.generation===props.generation?facts:emptyFacts,blocked=props.blocked||busy||Boolean(recovery.pending||recovery.error)
 const perform=async(operation:(n:number)=>Promise<void>)=>{
  if(active.current!==null)return;const n=props.onReadStart();active.current=n;setBusy(true);setFacts(emptyFacts);setCopyText('');setError('');setMessage('')
  try{await operation(n)}catch(e){if(current(n))setError(normalizeClientError(e).message)}finally{if(mounted.current){setRecovery(readReportRequest(scope));setBusy(false)}if(active.current===n)active.current=null;props.onReadEnd(n)}
 }
 const publishRequest=async(r:ReportRequest,lookup=false)=>perform(async n=>{
  const manager=productionLockManager();if(!manager)throw Error('Penyimpanan laporan memerlukan pengunci tab. Arsip masih dapat dibaca.')
  await manager.request(productionLockName(productionScope),{mode:'exclusive',ifAvailable:true},async lock=>{
   if(!lock)throw Error('Ada transaksi ERP di tab lain. Tunggu selesai, lalu periksa kembali.');if(!current(n))return
   const shared=readProductionRecovery(productionScope);if(shared.corrupted||!lookup&&hasProductionPending(shared))throw Error('Pastikan hasil transaksi ERP yang tertunda sebelum menyimpan laporan baru.')
   persistReportRequest(scope,r);setRecovery(readReportRequest(scope))
   const response=lookup?await client.rpc('erp_cp7_get_report_request_v1',{p_payload:r.payload,p_request:r.id}):await client.rpc('erp_cp7_publish_report_v1',{p_payload:r.payload,p_request:r.id})
   if(!current(n))return;if(response.error)throw response.error
   const parsed=await parseReportCommand(response.data,r,props.actor,props.access);if(!current(n))return
   if(props.context?.runId===parsed.analysis.runId)assertSameAnalysis(props.context,parsed.analysis)
   clearReportRequest(scope,r);setRecovery(readReportRequest(scope));setFacts({...emptyFacts,generation:n,document:parsed.document});setReviewed(false);props.onAnalysis(parsed.analysis,n)
   setMessage(parsed.status==='COMMITTED'?'Laporan tersimpan. Versi sebelumnya tetap utuh.':'Server memastikan permintaan lama belum tersimpan dan sudah ditutup. Periksa sumber sebelum menyimpan permintaan baru.')
  })
 })
 const save=()=>{try{
  props.requireClear();const held=readReportRequest(scope);if(held.error||held.pending)throw Error(held.error??'Pastikan hasil laporan tersimpan terlebih dahulu.')
  const a=props.context;if(!a||a.state!=='UNCHANGED')throw Error('Ambil dan tinjau analisis terbaru sebelum menyimpan laporan.');if(!reviewed||!title.trim()||!reason.trim())throw Error('Isi judul dan alasan, lalu konfirmasi peninjauan laporan.')
  if(revisionBase&&(revisionBase.kind!==kind||(['from_date','through_date','group_mode'] as const).some(field=>revisionBase.query[field]!==a.query[field])))throw Error('Revisi harus memakai jenis dan periode seri yang sama. Pilih laporan baru untuk periode lain.')
  void publishRequest({id:crypto.randomUUID(),query:a.query,payload:{run_id:a.runId,source_hash:a.analysis.snapshot.source_hash,semantic_hash:a.analysis.semantic_hash,kind,series_id:revisionBase?.seriesId??null,expected_revision:revisionBase?.revision??null,title,reason,explicit_review:true}})
 }catch(e){setError(normalizeClientError(e).message)}}
 const retry=(lookup:boolean)=>{try{props.requireClear();const held=readReportRequest(scope);setRecovery(held);if(!held.pending)throw Error(held.error??'Permintaan laporan tersimpan tidak tersedia.');void publishRequest(held.pending,lookup)}catch(e){setError(normalizeClientError(e).message)}}
 const list=(before:string|null=null)=>void perform(async n=>{props.requireClear();const response=await client.rpc('erp_cp7_list_reports_v1',{p_query:{before_id:before,limit:25}});if(!current(n))return;if(response.error)throw response.error;const index=parseReportIndex(response.data,props.actor,25);setFacts({...emptyFacts,generation:n,index})})
 const open=(id:string,copy=false)=>{const original=visible.document;void perform(async n=>{
  props.requireClear();const response=await client.rpc('erp_cp7_read_report_v1',{p_id:id});if(!current(n))return;if(response.error)throw response.error
  const document=await parseNativeReport(response.data,props.actor,props.access);if(!current(n))return;if(document.id!==id)throw Error('Identitas laporan server berubah.');if(original?.id===id)assertSameReport(original,document)
  setFacts({...emptyFacts,generation:n,document});props.onAnalysis(document.analysis,n)
  if(copy){const text=(document.analysis.state==='ARCHIVED_STALE'?'ARSIP LAMA: sumber ERP sudah berubah. Ini isi saat diterbitkan.\n\n':'')+document.body;setCopyText(text);if(new TextEncoder().encode(text).byteLength>1000000){setMessage('Laporan lengkap sudah diperiksa. Pilih teks untuk menyalin manual.');return}try{await navigator.clipboard.writeText(text);if(current(n))setMessage('Isi laporan yang diperiksa disalin.')}catch{if(current(n))setMessage('Salin otomatis gagal. Teks lengkap tersedia untuk disalin manual.')}}
 })}
 const compare=()=>void perform(async n=>{props.requireClear();if(!beforeId||!afterId)throw Error('Pilih dua laporan untuk dibandingkan.');const response=await client.rpc('erp_cp7_compare_reports_v1',{p_before:beforeId,p_after:afterId});if(!current(n))return;if(response.error)throw response.error;const comparison=await parseReportComparison(response.data,props.actor,props.access,beforeId,afterId);if(!current(n))return;setFacts({...emptyFacts,generation:n,comparison});props.onAnalysis(comparison.after.analysis,n)})
 const startRevision=()=>{const d=visible.document;if(!d)return;setRevisionBase({seriesId:d.seriesId,revision:d.revision,kind:d.kind,query:d.query});setKind(d.kind);setReviewed(false);setMessage('Isi judul dan alasan revisi, lalu tinjau analisis terbaru. Isi laporan lama tetap tersimpan.')}
 const options=visible.index?.rows??[]
 return <section className="panel" aria-label="Laporan ERP tersimpan"><h3>Laporan tersimpan, revisi & perbandingan</h3><p>Simpan hasil yang sudah ditinjau. Angka memakai analisis ERP yang sama; laporan tersimpan tidak mengubah stok atau transaksi.</p>
  {busy?<p role="status">Memeriksa laporan dan izin ERP saat ini…</p>:null}{error||recovery.error?<p role="alert">{error||recovery.error}</p>:null}{message?<p role="status">{message}</p>:null}
  {recovery.pending?<div role="status"><p>Hasil penyimpanan laporan belum dipastikan. Permintaan yang sama dipertahankan.</p><button disabled={props.blocked||busy} onClick={()=>retry(true)}>Periksa hasil laporan tersimpan</button><button disabled={props.blocked||busy} onClick={()=>retry(false)}>Ulangi penyimpanan laporan yang sama</button></div>:null}
  <label>Jenis laporan<select aria-label="Jenis laporan tersimpan" value={kind} disabled={busy||Boolean(recovery.pending)} onChange={e=>{setKind(e.target.value as ReportKind);setReviewed(false)}}>{reportKinds.map(k=><option key={k} value={k}>{reportKindLabels[k]}</option>)}</select></label>
  <label>Judul laporan<input aria-label="Judul laporan tersimpan" value={title} maxLength={200} disabled={busy} onChange={e=>{setTitle(e.target.value);setReviewed(false)}}/></label>
  <label>Alasan penerbitan atau revisi<textarea aria-label="Alasan laporan tersimpan" value={reason} maxLength={1000} disabled={busy} onChange={e=>{setReason(e.target.value);setReviewed(false)}}/></label>
  {props.context?<p>Periode sumber {props.context.query.from_date} sampai {props.context.query.through_date} · {props.context.query.group_mode}.</p>:<p>Ambil analisis terbaru atau buka arsip untuk memeriksa sumber laporan.</p>}
  {revisionBase?<p>Revisi seri yang dipilih, setelah versi {revisionBase.revision}. <button disabled={blocked} onClick={()=>{setRevisionBase(null);setReviewed(false)}}>Jadikan laporan baru</button></p>:null}
  <label><input aria-label="Laporan sudah ditinjau" type="checkbox" checked={reviewed} disabled={blocked||!props.context||props.context.state!=='UNCHANGED'} onChange={e=>setReviewed(e.target.checked)}/> Saya sudah meninjau angka, asumsi dan bagian yang belum diketahui.</label>
  <button disabled={blocked||!props.context||props.context.state!=='UNCHANGED'||!reviewed||!title.trim()||!reason.trim()||!productionLockManager()} onClick={save}>{revisionBase?'Simpan revisi laporan':'Simpan laporan yang ditinjau'}</button>
  <button disabled={blocked} onClick={()=>list()}>Muat laporan tersimpan dari server</button>
  {visible.index?<><p>{visible.index.rows.length} pada halaman ini · {visible.index.total} laporan yang dapat diakses.</p>{visible.index.rows.map((r,i)=><button key={r.id} disabled={blocked} aria-label={`Buka laporan tersimpan ${i+1}`} onClick={()=>open(r.id)}>{r.title} · versi {r.revision} · {formatCp6WibDateTime(r.publishedAt)}</button>)}{visible.index.nextBeforeId?<button disabled={blocked} onClick={()=>list(visible.index!.nextBeforeId)}>Halaman laporan berikutnya</button>:null}</>:null}
  <div><label>Laporan sebelum<select aria-label="Laporan sebelum" value={beforeId} disabled={blocked} onChange={e=>setBeforeId(e.target.value)}><option value="">Pilih laporan</option>{beforeId&&!options.some(r=>r.id===beforeId)?<option value={beforeId}>{beforeId}</option>:null}{options.map(r=><option key={r.id} value={r.id}>{r.title} · versi {r.revision}</option>)}</select></label><label>Laporan sesudah<select aria-label="Laporan sesudah" value={afterId} disabled={blocked} onChange={e=>setAfterId(e.target.value)}><option value="">Pilih laporan</option>{afterId&&!options.some(r=>r.id===afterId)?<option value={afterId}>{afterId}</option>:null}{options.map(r=><option key={r.id} value={r.id}>{r.title} · versi {r.revision}</option>)}</select></label><button disabled={blocked||!beforeId||!afterId} onClick={compare}>Bandingkan dua laporan ERP</button></div>
  {visible.document?<article aria-label="Isi laporan tersimpan"><h4>{visible.document.title} · versi {visible.document.revision}</h4><p>{visible.document.isLatest?'Versi terbaru dalam seri ini.':'Versi lama; revisi berikutnya sudah tersedia.'} {visible.document.analysis.state==='ARCHIVED_STALE'?'Arsip lama: sumber ERP sudah berubah.':'Sumber sesuai saat diperiksa.'}</p><p>Alasan: {visible.document.reason}</p><button disabled={blocked||!visible.document.isLatest} onClick={startRevision}>Buat revisi dari laporan ini</button><button disabled={blocked} onClick={()=>open(visible.document!.id,true)}>Periksa & salin laporan tersimpan</button><pre aria-label="Teks laporan tersimpan">{visible.document.body}</pre><details><summary>Identitas dan sumber laporan tersimpan</summary><p>Analisis {visible.document.runId} · template {visible.document.templateVersion} · diterbitkan {formatCp6WibDateTime(visible.document.publishedAt)}.</p><p>Hash isi {visible.document.bodyHash} · sumber {visible.document.sourceHash} · hasil {visible.document.semanticHash}.</p></details></article>:null}
  {visible.comparison?<article aria-label="Perbandingan laporan ERP"><h4>{visible.comparison.before.title} → {visible.comparison.after.title}</h4><p>Periode sebelum: {visible.comparison.before.query.from_date} sampai {visible.comparison.before.query.through_date}. Sesudah: {visible.comparison.after.query.from_date} sampai {visible.comparison.after.query.through_date}.</p><p>Selisih dihitung ERP dari metrik asli dengan versi, cakupan, satuan dan basis pengetahuan yang sama. Nilai yang belum diketahui tetap belum diketahui.</p><div className="responsive-table"><table><thead><tr><th>Metrik / cakupan</th><th>Sebelum</th><th>Sesudah</th><th>Selisih sesudah − sebelum</th></tr></thead><tbody>{visible.comparison.rows.map((r,i)=><tr key={i}><td>{analysisMetricLabel((r.after??r.before)!,r.after?visible.comparison!.after.analysis:visible.comparison!.before.analysis)}</td><td>{r.before&&'value'in r.before.value?r.before.value.value+' '+r.before.value.unit:'Belum diketahui'}</td><td>{r.after&&'value'in r.after.value?r.after.value.value+' '+r.after.value.unit:'Belum diketahui'}</td><td>{r.difference.state==='UNKNOWN'?'Belum diketahui':r.difference.value+' '+r.difference.unit+(r.difference.state==='ASSUMED'?' [asumsi]':'')}</td></tr>)}</tbody></table></div></article>:null}
  {copyText&&facts.generation===props.generation?<label>Salinan lengkap laporan tersimpan<textarea readOnly aria-label="Salinan manual laporan tersimpan" rows={12} value={copyText} onFocus={e=>e.currentTarget.select()}/></label>:null}
 </section>
}
