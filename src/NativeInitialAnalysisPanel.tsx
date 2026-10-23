import {useCallback,useEffect,useMemo,useRef,useState} from 'react'
import {useAuth} from './auth/AuthProvider'
import {getUatSupabaseClient} from './lib/supabase'
import {normalizeClientError} from './lib/clientError'
import {formatCp6WibDateTime} from './cp6BusinessTime'
import {stagedProgressText,stagedFailureText} from './nativeStagedJob'
import {initialAnalysisClient,initialReasonLabel,parseInitialAnalysis,type InitialAnalysis,type InitialProduct} from './nativeInitialAnalysis'
import type {NativeDemandQuery} from './nativeDemandHistory'
import './native-initial-analysis.css'

type Props={sourceKey:string;onOpen:(status:InitialAnalysis)=>void;onConfigure:(product:InitialProduct,query:NativeDemandQuery)=>void;
 onOpenMaster?:()=>void;onAuthorityLost?:()=>void}
const rights=['master.product.view','production.wip.view','warehouse.stock.view','sales.invoice.view']
export default function NativeInitialAnalysisPanel(props:Props){
 const {runtime,identity}=useAuth()
 if(runtime.mode!=='DISPOSABLE_TEST'||identity.status!=='AUTHORIZED'||!['OWNER','ADMIN'].includes(identity.profile.role)||!rights.every(p=>identity.permissions.includes(p)))return null
 return <Workspace {...props} key={JSON.stringify([runtime.projectRef,identity.profile.id,identity.profile.authUserId,identity.profile.rowVersion,identity.profile.roleRowVersion,identity.permissions])}/>
}
function Workspace({sourceKey,onOpen,onConfigure,onOpenMaster,onAuthorityLost}:Props){
 const {runtime,identity}=useAuth();if(runtime.mode!=='DISPOSABLE_TEST'||identity.status!=='AUTHORIZED')throw Error('Sesi analisis awal belum siap.')
 const client=useMemo(()=>initialAnalysisClient(getUatSupabaseClient(runtime)),[runtime]),actor=identity.profile.authUserId
 const sequence=useRef(0),binding=useRef(sourceKey),alive=useRef(true),denied=useRef(false)
 binding.current=sourceKey
 const [data,setData]=useState<{binding:string;value:InitialAnalysis}|null>(null),[busy,setBusy]=useState(false),[error,setError]=useState('')
 const read=useCallback(async(force=false)=>{
  if(denied.current&&!force)return
  if(force)denied.current=false
  const n=++sequence.current,bound=binding.current,current=()=>alive.current&&n===sequence.current&&bound===binding.current
  setData(null);setBusy(true);setError('')
  try{
   let reply=await client.rpc('erp_cp7_request_staged_analysis_v1',{p_query:{initial_auto:'STATUS'},p_request:null})
   if(!current())return;if(reply.error)throw reply.error
   let status=parseInitialAnalysis(reply.data,actor)
   if(status.state==='READY'){
    reply=await client.rpc('erp_cp7_request_staged_analysis_v1',{p_query:{initial_auto:'ENSURE'},p_request:null})
    if(!current())return;if(reply.error)throw reply.error
    status=parseInitialAnalysis(reply.data,actor)
    if(status.state==='READY')throw Error('Analisis awal belum mendapat jawaban pasti. Periksa statusnya lagi.')
   }
   if(current())setData({binding:bound,value:status})
  }catch(e){if(current()){
   const failure=normalizeClientError(e);setError(failure.message)
   if(failure.code==='FORBIDDEN'||failure.code==='AUTH_REQUIRED'){denied.current=true;setData(null);onAuthorityLost?.()}
  }}finally{if(current())setBusy(false)}
 },[client,actor,onAuthorityLost])
 useEffect(()=>{alive.current=true;return()=>{alive.current=false;++sequence.current}},[])
 useEffect(()=>{void read();return()=>{++sequence.current}},[read,sourceKey])
 useEffect(()=>{const refresh=()=>{if(document.visibilityState!=='hidden')void read()};addEventListener('focus',refresh);document.addEventListener('visibilitychange',refresh)
  return()=>{removeEventListener('focus',refresh);document.removeEventListener('visibilitychange',refresh)}},[read])
 const value=data?.binding===sourceKey?data.value:null
 useEffect(()=>{
  if(!value||busy||error||!['NOT_READY','BUSY','RUNNING'].includes(value.state))return
  const timer=setTimeout(()=>void read(),value.state==='NOT_READY'?30000:5000)
  return()=>clearTimeout(timer)
 },[value,busy,error,read])
 const open=()=>{if(!value)return;try{onOpen(value)}catch(e){setError(normalizeClientError(e).message)}}
 return <section className="native-initial" aria-label="Analisis awal otomatis"><h3>Analisis awal otomatis</h3>
  <p>Mulai sekali setelah produk dan aturan target minimum siap. Tidak membuat ulang analisis karena halaman dibuka kembali.</p>
  {busy?<p role="status">Memeriksa kesiapan analisis awal…</p>:null}
  {error?<p role="alert">{error}</p>:null}
  {value?<>
   {value.state==='NOT_READY'?<><p>Yang masih perlu dilengkapi:</p><ul>{value.reasons.map(reason=><li key={reason}>{initialReasonLabel[reason]}</li>)}</ul></>:null}
   <p>{value.eligibleTargets} dari {value.activeProducts} produk aktif sudah punya aturan target minimum. Produk lain tetap masuk analisis dengan keterangan data yang kurang.</p>
   <p>Periode {value.jobQuery?.from_date??value.query.from_date} sampai {value.jobQuery?.through_date??value.query.through_date}, hari selesai di WIB.</p>
   {value.job?<p>Sumber hasil diambil {formatCp6WibDateTime(value.job.reference.capturedAt)}.</p>:null}
   {value.reasons.includes('NO_ACTIVE_PRODUCTS')?onOpenMaster?<button type="button" onClick={onOpenMaster}>Lengkapi produk di Data Master</button>:<p>Lengkapi produk aktif melalui menu Data Master.</p>:null}
   {value.reasons.includes('PLANNING_PROFILE_INCOMPLETE')?<><div className="native-initial-products">{value.candidates.filter(p=>!p.profileReady).map(product=><div key={product.productId}>
    <span>{product.sku} · {product.productName}</span><button type="button" onClick={()=>onConfigure(product,value.query)}>Lengkapi target {product.sku}</button></div>)}</div>
    {value.activeProducts>value.candidates.length?<p>Ditampilkan {value.candidates.length} produk. Produk lainnya dapat dibuka dari Data permintaan &amp; stok.</p>:null}</>:null}
   {value.reasons.includes('SOURCE_INCOMPLETE')?<p>Periksa identitas produk dan kelengkapan kejadian stok/penjualan. Sumber yang terpotong belum boleh menjadi analisis awal.</p>:null}
   {value.state==='BUSY'?<p role="status">Menunggu analisis yang sedang berjalan. Permintaan awal belum digandakan.</p>:null}
   {value.job&&value.state==='RUNNING'?<><p role="status">{stagedProgressText(value.job)}</p><p>{value.job.serverRunner?.active?'Server sedang memproses; halaman boleh ditutup.':'Analisis sudah tersimpan. Pekerja server belum terlihat aktif; buka analisis untuk melanjutkan dan memeriksa statusnya.'}</p></>:null}
   {value.state==='DONE'?<p>Analisis awal sudah selesai.</p>:null}
   {value.job?.failure&&value.state==='FAILED'?<p role="alert">{stagedFailureText(value.job.failure)} Permintaan gagal tidak diulang otomatis.</p>:null}
   {value.state==='EXPIRED'?<p>Hasil awal sudah melewati masa simpan. Gunakan analisis baru untuk periode yang dipilih.</p>:null}
   {value.sourceChanged?<p>Sumber atau periode sudah berubah. Hasil awal tetap snapshot lama; gunakan analisis baru untuk keadaan sekarang.</p>:null}
   {value.job&&['RUNNING','DONE'].includes(value.state)?<button type="button" onClick={open}>{value.state==='RUNNING'?'Buka analisis awal yang berjalan':'Buka hasil analisis awal'}</button>:null}
   <p>Diperiksa {formatCp6WibDateTime(value.checkedAt)}. Analisis awal berisi data operasional; kesiapan ini belum memastikan kelayakan produksi.</p>
  </>:null}
  <button type="button" disabled={busy} onClick={()=>void read(true)}>Periksa kesiapan lagi</button>
 </section>
}
