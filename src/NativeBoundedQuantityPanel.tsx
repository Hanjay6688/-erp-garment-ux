import {useCallback,useEffect,useMemo,useRef,useState} from 'react'
import {useAuth} from './auth/AuthProvider'
import {getUatSupabaseClient} from './lib/supabase'
import {normalizeClientError} from './lib/clientError'
import {formatCp6WibDateTime} from './cp6BusinessTime'
import {formatFact} from './cp7/workspace'
import {analysisWarningLabel} from './nativeAnalysis'
import type {NativeDemandQuery} from './nativeDemandHistory'
import {BOUNDED_ANALYSIS_REQUEST,boundedAnalysisRequestKey,readBoundedAnalysisRequest,persistBoundedAnalysisRequest,replaceBoundedAnalysisRequest,type BoundedAnalysisRequest} from './nativeBoundedAnalysis'
import {driveBoundedQuantity,readBoundedQuantity,readBoundedQuantityPage,checkBoundedQuantity} from './nativeBoundedQuantity'
import {stagedFailureText,stagedRetentionText,type StagedJob} from './nativeStagedJob'
import {stagedRangeLabel,stagedNumber,type StagedAnalysis,type AnalysisPage,type StagedSourceCheck} from './nativeAnalysisPages'
import NativePlanDraftPanel from './NativePlanDraftPanel'
import type {StagedPlanContext} from './nativePlanDraft'
import NativeProductAnalogPanel from './NativeProductAnalogPanel'
import {analogReadContext,type AnalogReadContext} from './nativeProductAnalog'
import './native-bounded-quantity.css'

type Props={query:NativeDemandQuery;onSourceReadStart:()=>void;onSourceReadEnd:()=>void;onClose:()=>void}
const permissions=['master.product.view','production.wip.view','warehouse.stock.view','sales.invoice.view']
const stateLabel=(s:string)=>s==='ACTIVE'?'Aktif':s==='PAUSED'?'Ditunda':s==='STOPPED'?'Dihentikan':'Perlu diperiksa'
const warningLabel=(s:string)=>s==='RAW_NATIVE_CAPTURE_INCOMPLETE_COMPLETE_SQL_HISTORY_INPUTS'?'Riwayat stok telah dibaca seluruhnya untuk perhitungan ini.':analysisWarningLabel(s)
const sourceRefusal=(e:unknown)=>{if(!e||typeof e!=='object')return false;const v=e as Record<string,unknown>;return v.code==='P0001'&&['CP7_ANALYSIS_STAGED_TARGET_LIMIT','CP7_BOUNDED_ANALYSIS_HISTORY_SCOPE','CP7_BOUNDED_HISTORY_SOURCE_SHAPE','CP7_REORDER_NON_STOCK_SOURCE_INCOMPLETE','CP7_REORDER_STOCK_SNAPSHOT_MISMATCH'].includes(String(v.message))}
export default function NativeBoundedQuantityPanel(props:Props){
 const{runtime,identity}=useAuth()
 if(runtime.mode!=='DISPOSABLE_TEST'||identity.status!=='AUTHORIZED'||!permissions.every(p=>identity.permissions.includes(p)))return null
 return <Workspace {...props} key={`${runtime.projectRef}:${identity.profile.id}:${identity.profile.rowVersion}:${identity.profile.roleRowVersion}:${identity.permissions.join('|')}`}/>
}
function Workspace({query,onSourceReadStart,onSourceReadEnd,onClose}:Props){
 const{runtime,identity}=useAuth();if(runtime.mode!=='DISPOSABLE_TEST'||identity.status!=='AUTHORIZED')throw Error('Sesi perhitungan belum siap.')
 const client=useMemo(()=>getUatSupabaseClient(runtime),[runtime]),scope='quantity:'+runtime.projectRef+':'+identity.profile.id,actor=identity.profile.authUserId
 const seq=useRef(0),active=useRef(false),pageSeq=useRef(0),checkSeq=useRef(0),sleeps=useRef(new Set<{timer:ReturnType<typeof setTimeout>;wake:()=>void}>())
 const[held,setHeld]=useState(()=>readBoundedAnalysisRequest(scope)),[job,setJob]=useState<StagedJob|null>(null),[staged,setStaged]=useState<StagedAnalysis|null>(null),[page,setPage]=useState<AnalysisPage|null>(null)
 const[busy,setBusy]=useState(false),[pageLoading,setPageLoading]=useState(false),[checking,setChecking]=useState(false),[check,setCheck]=useState<StagedSourceCheck|null>(null),[error,setError]=useState(''),[slice,setSlice]=useState(0),[plan,setPlan]=useState<StagedPlanContext|null>(null)
 const[analog,setAnalog]=useState<AnalogReadContext|null>(null),[analogSearch,setAnalogSearch]=useState(''),[analogOffset,setAnalogOffset]=useState(0)
 const[refusedBeforeJob,setRefusedBeforeJob]=useState(false)
 const stop=useCallback(()=>{++seq.current;++pageSeq.current;++checkSeq.current;for(const entry of sleeps.current){clearTimeout(entry.timer);entry.wake()}sleeps.current.clear();if(active.current){active.current=false;onSourceReadEnd()}},[onSourceReadEnd])
 const sleep=useCallback((ms:number)=>new Promise<void>(wake=>{const entry={timer:setTimeout(()=>{sleeps.current.delete(entry);wake()},ms),wake};sleeps.current.add(entry)}),[])
 const retire=useCallback((message:string)=>{setStaged(null);setPage(null);setJob(null);setCheck(null);setAnalog(null);setRefusedBeforeJob(false);setError(message)},[])
 const run=useCallback(async(request:BoundedAnalysisRequest,start:boolean)=>{
  const n=++seq.current;let observed=false;active.current=true;setBusy(true);setError('');setRefusedBeforeJob(false);setStaged(null);setPage(null);setCheck(null);setJob(null);setAnalog(null);setAnalogOffset(0);setSlice(0);++pageSeq.current;++checkSeq.current;onSourceReadStart()
  try{
   const status=await driveBoundedQuantity(client,request,{start,aborted:()=>seq.current!==n,sleep,onStatus:s=>{observed=true;if(seq.current===n)setJob(s)}})
   if(!status||seq.current!==n)return
   if(status.retention?.state==='EXPIRED')throw Error(stagedRetentionText(status.retention))
   if(status.state==='FAILED')throw Error(stagedFailureText(status.failure!))
   const result=await readBoundedQuantity(client,request,status,actor);if(seq.current!==n)return
   const first=result.set.pageCount?await readBoundedQuantityPage(client,result,0):null;if(seq.current!==n)return
   setStaged(result);setPage(first)
  }catch(e){if(seq.current===n){const failure=normalizeClientError(e);setError(failure.message);if(!observed&&sourceRefusal(e))setRefusedBeforeJob(true);if(failure.code==='FORBIDDEN'||failure.code==='AUTH_REQUIRED')retire(failure.message)}}
  finally{if(seq.current===n){active.current=false;setBusy(false);onSourceReadEnd();setHeld(readBoundedAnalysisRequest(scope))}}
 },[actor,client,onSourceReadEnd,onSourceReadStart,retire,scope,sleep])
 useEffect(()=>{
  const saved=readBoundedAnalysisRequest(scope);setHeld(saved)
  if(saved.error){setError(saved.error);return stop}
  if(saved.pending)void run(saved.pending,false)
  else{try{const request:BoundedAnalysisRequest={id:crypto.randomUUID(),q:query,method:BOUNDED_ANALYSIS_REQUEST};persistBoundedAnalysisRequest(scope,request);setHeld(readBoundedAnalysisRequest(scope));void run(request,true)}catch(e){setError(normalizeClientError(e).message)}}
  return stop
  // A new period takes effect only through the explicit new-calculation action.
  // A remount resumes the stored period and method, including after reply loss.
  // eslint-disable-next-line react-hooks/exhaustive-deps
 },[run,scope,stop])
 useEffect(()=>{const listener=(event:StorageEvent)=>{if(event.key===null||event.key===boundedAnalysisRequestKey(scope)){stop();setBusy(false);setPageLoading(false);setChecking(false);retire('Catatan perhitungan berubah di tab lain. Periksa permintaan tersimpan.');setHeld(readBoundedAnalysisRequest(scope))}};addEventListener('storage',listener);return()=>removeEventListener('storage',listener)},[retire,scope,stop])
 const retry=()=>{if(active.current)return;const saved=readBoundedAnalysisRequest(scope);setHeld(saved);if(saved.error||!saved.pending){setError(saved.error||'Permintaan perhitungan tersimpan tidak tersedia.');return}void run(saved.pending,true)}
 const calculateNew=()=>{
  if(active.current||!staged&&!refusedBeforeJob&&job?.state!=='FAILED'&&job?.retention?.state!=='EXPIRED')return
  try{const saved=readBoundedAnalysisRequest(scope);if(saved.error||!saved.pending)throw Error(saved.error||'Catatan perhitungan berubah.');const next:BoundedAnalysisRequest={id:crypto.randomUUID(),q:query,method:BOUNDED_ANALYSIS_REQUEST};replaceBoundedAnalysisRequest(scope,saved.pending,next);setHeld(readBoundedAnalysisRequest(scope));void run(next,true)}catch(e){setError(normalizeClientError(e).message)}
 }
 const loadPage=async(index:number)=>{
  if(!staged||busy||pageLoading||plan||analog)return
  const current=staged,n=++pageSeq.current;setPageLoading(true);setPage(null);setError('');setSlice(0)
  try{const next=await readBoundedQuantityPage(client,current,index);if(n===pageSeq.current)setPage(next)}catch(e){if(n===pageSeq.current){const failure=normalizeClientError(e);setError(failure.message);if(failure.code==='FORBIDDEN'||failure.code==='AUTH_REQUIRED')retire(failure.message)}}finally{if(n===pageSeq.current)setPageLoading(false)}
 }
 const checkSource=async()=>{
  if(!staged||checking||plan||analog)return
  const n=++checkSeq.current,runId=staged.set.runId;setChecking(true);setCheck(null);setError('')
  try{const next=await checkBoundedQuantity(client,runId);if(n===checkSeq.current)setCheck(next)}catch(e){if(n===checkSeq.current){const failure=normalizeClientError(e);setError(failure.message);if(failure.code==='FORBIDDEN'||failure.code==='AUTH_REQUIRED')retire(failure.message)}}finally{if(n===checkSeq.current)setChecking(false)}
 }
 const blocked=busy||pageLoading||checking||plan!==null||analog!==null,canNew=Boolean(staged||refusedBeforeJob||job?.state==='FAILED'||job?.retention?.state==='EXPIRED'),m=staged?.set
 const labels=useMemo(()=>new Map(staged?.header.labels.map(p=>[p.key,`${p.sku} · ${p.name}`])??[]),[staged])
 const analogMatches=useMemo(()=>{
  const term=analogSearch.trim().toLocaleLowerCase('id-ID');if(!term)return[]
  const exact=[],partial=[]
  for(const p of staged?.header.labels??[]){
   const sku=p.sku.toLocaleLowerCase('id-ID')
   if(sku===term)exact.push(p)
   else if(sku.includes(term)||p.name.toLocaleLowerCase('id-ID').includes(term))partial.push(p)
  }
  return[...exact,...partial]
 },[analogSearch,staged])
 const rows=page?.items.recommendations??[],visible=rows.slice(slice,slice+50),pageIndex=page?.index??0
 return <section className="native-production-result native-bounded-quantity" aria-label="Kebutuhan seluruh produk"><header><h3>Kebutuhan seluruh produk</h3><button onClick={()=>{stop();onClose()}}>Tutup perhitungan kebutuhan</button></header>
  <p>Perhitungan memakai jadwal terakhir yang sudah disimpan. Isian jadwal yang belum disimpan belum masuk perhitungan.</p>
  {busy?<p role="status">{job?`Menghitung kebutuhan · ${stagedNumber(job.unitsDone)} dari ${stagedNumber(job.unitCount)} langkah selesai.`:'Mengambil sumber perhitungan…'}</p>:null}
  {job?.retention?<p>{stagedRetentionText(job.retention)}</p>:null}
  {error||held.error?<p role="alert">{error||held.error}</p>:null}
  <div className="native-production-actions"><button disabled={blocked||!held.pending||Boolean(held.error)} onClick={retry}>Buka perhitungan tersimpan</button><button disabled={blocked||!canNew||Boolean(held.error)} onClick={calculateNew}>Hitung kebutuhan terbaru</button></div>
  {staged&&m?<>
   <p>Data per {formatCp6WibDateTime(m.reference.capturedAt)} · {stagedNumber(m.targetsTotal)} target · jadwal versi {staged.header.analysisHeader.scenario.version}.</p>
   <p>Status seluruh target: {stagedNumber(m.totals.recommendations.ACTIVE)} aktif, {stagedNumber(m.totals.recommendations.PAUSED)} ditunda, {stagedNumber(m.totals.recommendations.STOPPED)} dihentikan, {stagedNumber(m.totals.recommendations.OTHER)} status lain. Kebijakan produksi belum diperiksa: {stagedNumber(m.totals.policyUnreviewed)} target.</p>
   <details><summary>Cari produk untuk melihat pembanding</summary><label>Cari SKU atau nama produk yang memerlukan pembanding<input type="search" value={analogSearch} disabled={blocked} onChange={e=>{setAnalogSearch(e.target.value);setAnalogOffset(0)}}/></label>{analogSearch.trim()?<><p>{analogMatches.length} produk ditemukan dalam seluruh hasil perhitungan. Pilihan {analogMatches.length?analogOffset+1:0}–{Math.min(analogOffset+20,analogMatches.length)}. SKU yang sama persis ditampilkan lebih dahulu.</p>{analogMatches.slice(analogOffset,analogOffset+20).map(p=><p key={p.key} data-analog-choice={p.key}>{p.sku} · {p.name} <button disabled={blocked} onClick={()=>setAnalog(analogReadContext(staged,actor,p.key))}>Lihat pembanding {p.sku}</button></p>)}<nav aria-label="Halaman pencarian produk"><button disabled={blocked||analogOffset===0} onClick={()=>setAnalogOffset(n=>Math.max(0,n-20))}>20 produk sebelumnya</button><button disabled={blocked||analogOffset+20>=analogMatches.length} onClick={()=>setAnalogOffset(n=>n+20)}>20 produk berikutnya</button></nav></>:null}</details>
   <button disabled={blocked} onClick={()=>void checkSource()}>Periksa sumber kebutuhan</button>
   {checking?<p role="status">Memeriksa sumber kebutuhan…</p>:null}
   {check?<p className={check.sourceState==='UNCHANGED'?'native-demand-current':'native-demand-stale'}>Pemeriksaan {formatCp6WibDateTime(check.checkedAt)}: {check.sourceState==='UNCHANGED'?'sama dengan data saat itu.':'sumber sudah berubah; hitung kebutuhan terbaru.'}</p>:null}
   <p>Jumlah yang belum dapat dipastikan tetap ditulis belum diketahui. Saran masih memakai asumsi jadwal dan hasil bagus yang dipilih; bahan, uang, dan HPP diperiksa pada sumbernya.</p>
   <details><summary>Rincian pemeriksaan kebutuhan</summary>{[...staged.header.analysisHeader.generation_warnings,...(page?.items.generation_warnings??[])].map((w,i)=><p key={`${i}:${w}`}>{warningLabel(w)}</p>)}</details>
   {m.pageCount?<><nav aria-label="Halaman sumber kebutuhan"><button disabled={blocked||pageIndex===0} onClick={()=>void loadPage(pageIndex-1)}>Sumber sebelumnya</button><span>Halaman {pageIndex+1} dari {m.pageCount}</span><button disabled={blocked||pageIndex>=m.pageCount-1} onClick={()=>void loadPage(pageIndex+1)}>Sumber berikutnya</button></nav>
    {pageLoading?<p role="status">Mengambil halaman target…</p>:page?<><h4>{stagedRangeLabel(page.targetLo,page.targetHi,m.targetsTotal)}</h4>{page.summary.policyUnreviewed?<p>{stagedNumber(page.summary.policyUnreviewed)} target pada halaman ini masih memerlukan pemeriksaan kebijakan produksi dan belum memiliki rekomendasi jumlah.</p>:null}<p>Saran {rows.length?slice+1:0}–{Math.min(slice+50,rows.length)} dari {stagedNumber(rows.length)} baris pada halaman target ini.</p>
    <div className="responsive-table"><table><thead><tr><th>Produk</th><th>Status produksi</th><th>Stok fisik</th><th>Target</th><th>Kurang sebelum pembagian global</th><th>Kurang sesudah pembagian global</th><th>Saran sebelum cek bahan dan kapasitas</th><th>Tambahan kelipatan</th><th>Produksi baru layak</th><th>Pembanding</th>{identity.permissions.includes('production.cutting.view')?<th>Potongan</th>:null}</tr></thead><tbody>{visible.map(r=><tr key={r.target.key} data-quantity-target={r.target.key}><td data-label="Produk">{labels.get(r.target.key)??r.target.key}</td><td data-label="Status produksi">{stateLabel(r.production_state)}</td><td data-label="Stok fisik">{formatFact(r.actual_fg)}</td><td data-label="Target">{formatFact(r.target_qty)}</td><td data-label="Kurang sebelum pembagian global">{formatFact(r.q_base)}</td><td data-label="Kurang sesudah pembagian global">{formatFact(r.q_conditional)}</td><td data-label="Saran sebelum cek bahan dan kapasitas">{formatFact(r.suggested_new)}</td><td data-label="Tambahan kelipatan">{formatFact(r.rounding_extra)}</td><td data-label="Produksi baru layak">{formatFact(r.feasible_new)}</td><td data-label="Pembanding"><button disabled={blocked} onClick={()=>setAnalog(analogReadContext(staged,actor,r.target.key))}>Lihat produk pembanding</button></td>{identity.permissions.includes('production.cutting.view')?<td data-label="Potongan"><button disabled={blocked||check?.sourceState==='ARCHIVED_STALE'} onClick={()=>setPlan({kind:'STAGED',runId:m.runId,targetKey:r.target.key,identityHash:m.identityHash,dataAsOf:m.reference.capturedAt})}>Periksa saran potong</button></td>:null}</tr>)}</tbody></table></div>
    <nav aria-label="Baris saran kebutuhan"><button disabled={blocked||slice===0} onClick={()=>setSlice(s=>Math.max(0,s-50))}>50 saran sebelumnya</button><button disabled={blocked||slice+50>=rows.length} onClick={()=>setSlice(s=>s+50)}>50 saran berikutnya</button></nav></>:null}</>:<p>Tidak ada target produk pada sumber ini.</p>}
  </>:null}
  {analog?<NativeProductAnalogPanel client={client} context={analog} label={labels.get(analog.targetKey)??analog.targetKey} onClose={()=>setAnalog(null)} onAccessLost={retire} choiceReview={{scope:runtime.projectRef+':'+identity.profile.id,canManage:identity.permissions.includes('master.product.manage')}}/>:null}
  {plan?<NativePlanDraftPanel context={plan} requireCurrentSave onSourceReadStart={onSourceReadStart} onSourceReadEnd={onSourceReadEnd} onClose={()=>setPlan(null)}/>:null}
 </section>
}
