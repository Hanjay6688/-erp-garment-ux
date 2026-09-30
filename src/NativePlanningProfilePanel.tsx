import {useCallback,useEffect,useMemo,useRef,useState} from 'react'
import {useAuth} from './auth/AuthProvider'
import {getUatSupabaseClient} from './lib/supabase'
import {normalizeClientError} from './lib/clientError'
import {formatReceiptDecimal as numberText} from './procurementContract'
import {formatCp6WibDateTime} from './cp6BusinessTime'
import {readNativeDemandRequest,persistNativeDemandRequest,clearNativeDemandRequest,nativeDemandRequestKey,type NativeDemandRow,type NativeDemandQuery} from './nativeDemandHistory'
import {parsePlanningProfile,planningPayload,checkPlanningOutcome,parseNativeBaseline,readPlanningRequest,persistPlanningRequest,clearPlanningRequest,planningRequestKey,type PlanningProfile,type PlanningRequest,type PlanningConfig,type NativeBaseline} from './nativePlanningProfile'
import './native-planning-profile.css'
type Props={product:NativeDemandRow;query:NativeDemandQuery;onSourceReadStart:()=>void;onSourceReadEnd:()=>void;onClose:()=>void}
const permissions=['master.product.view','production.wip.view','warehouse.stock.view','sales.invoice.view']
export default function NativePlanningProfilePanel(props:Props){
 const{runtime,identity}=useAuth();if(runtime.mode!=='DISPOSABLE_TEST'||identity.status!=='AUTHORIZED'||!permissions.every(p=>identity.permissions.includes(p)))return null
 return <Workspace {...props} key={`${runtime.projectRef}:${identity.profile.id}:${identity.profile.rowVersion}:${identity.profile.roleRowVersion}:${identity.permissions.join('|')}:${props.product.rootId}`}/>
}
function Workspace({product,query,onSourceReadStart,onSourceReadEnd,onClose}:Props){
 const{runtime,identity}=useAuth();if(runtime.mode!=='DISPOSABLE_TEST'||identity.status!=='AUTHORIZED')throw Error('Sesi aturan produksi belum siap.')
 const client=useMemo(()=>getUatSupabaseClient(runtime),[runtime]),sequence=useRef(0),active=useRef(false),formBound=useRef(false),scope=runtime.projectRef+':'+identity.profile.id+':'+product.rootId,baselineScope='baseline:'+scope
 const[recovery,setRecovery]=useState(()=>readPlanningRequest(scope)),[baselineRecovery,setBaselineRecovery]=useState(()=>readNativeDemandRequest(baselineScope))
 const[profile,setProfile]=useState<PlanningProfile|null>(null),[base,setBase]=useState<PlanningProfile|null>(null),[baseline,setBaseline]=useState<NativeBaseline|null>(null)
 const[busy,setBusy]=useState(false),[error,setError]=useState(''),[message,setMessage]=useState(''),[mode,setMode]=useState<PlanningConfig['mean_mode']>('OWN_AVAILABLE_HISTORY'),[daily,setDaily]=useState(''),[minimum,setMinimum]=useState(''),[lead,setLead]=useState(''),[review,setReview]=useState(''),[buffer,setBuffer]=useState(''),[reason,setReason]=useState('')
 const canSave=identity.permissions.includes('master.product.manage')
 const useLatest=useCallback((p:PlanningProfile)=>{setBase(p);const c=p.quality==='SELECTED_ASSUMPTION'?p.config:null;setMode(c?.mean_mode??'OWN_AVAILABLE_HISTORY');setDaily(c?.daily_pcs??'');setMinimum(c?.minimum_available_days??'');setLead(c?.lead_days??'');setReview(c?.review_days??'');setBuffer(c?.buffer_days??'');setReason('')},[])
 const begin=()=>{const n=++sequence.current;active.current=true;setBusy(true);setProfile(null);setBaseline(null);setError('');setMessage('');onSourceReadStart();return n}
 const end=(n:number)=>{if(n===sequence.current){active.current=false;setBusy(false);onSourceReadEnd()}}
 const readProfile=useCallback(async()=>{
  const n=++sequence.current;active.current=true;setBusy(true);setProfile(null);setBaseline(null);setError('');onSourceReadStart()
  try{const r=await client.rpc('erp_cp7_get_planning_profiles_v1',{p_roots:[product.rootId]});if(n!==sequence.current)return;if(r.error)throw r.error;const p=parsePlanningProfile(r.data,product.rootId,product.sizeId);setProfile(p);if(!formBound.current){formBound.current=true;useLatest(p)}}
  catch(e){if(n===sequence.current)setError(normalizeClientError(e).message)}finally{if(n===sequence.current){active.current=false;setBusy(false);onSourceReadEnd()}}
 },[client,product.rootId,product.sizeId,onSourceReadStart,onSourceReadEnd,useLatest])
 useEffect(()=>{void readProfile();return()=>{++sequence.current;if(active.current){active.current=false;onSourceReadEnd()}}},[readProfile,onSourceReadEnd])
 useEffect(()=>{const f=(e:StorageEvent)=>{if(e.key===null||e.key===planningRequestKey(scope)||e.key===nativeDemandRequestKey(baselineScope)){++sequence.current;active.current=false;setBusy(false);setProfile(null);setBaseline(null);setRecovery(readPlanningRequest(scope));setBaselineRecovery(readNativeDemandRequest(baselineScope));onSourceReadStart();onSourceReadEnd()}};addEventListener('storage',f);return()=>removeEventListener('storage',f)},[scope,baselineScope,onSourceReadStart,onSourceReadEnd])
 const save=async(retry=false)=>{
  if(!canSave)return;const n=begin()
  try{
   const held=readPlanningRequest(scope);if(held.error)throw Error(held.error);if(retry&&!held.pending)throw Error('Permintaan tersimpan tidak tersedia.');if(!retry&&held.pending)throw Error('Periksa permintaan simpan yang sama terlebih dahulu.')
   const request:PlanningRequest=retry?held.pending!:{id:crypto.randomUUID(),payload:planningPayload(base!,{mean_mode:mode,daily_pcs:mode==='SELECTED_MANUAL'?daily:null,minimum_available_days:minimum,lead_days:lead===''?null:lead,review_days:review===''?null:review,buffer_days:buffer===''?null:buffer},reason)}
   if(request.payload.root_id!==product.rootId)throw Error('Permintaan tersimpan berasal dari produk lain.');if(!retry)persistPlanningRequest(scope,request);setRecovery(readPlanningRequest(scope))
   const reply=await client.rpc('erp_cp7_save_planning_profile_v1',{p_payload:request.payload,p_request:request.id});if(n!==sequence.current)return;if(reply.error)throw reply.error;checkPlanningOutcome(reply.data,request)
   clearPlanningRequest(scope,request.id);setRecovery(readPlanningRequest(scope));setMessage('Aturan tersimpan. Muat aturan terbaru sebelum menghitung atau menyimpan lagi.')
  }catch(e){if(n===sequence.current)setError(normalizeClientError(e).message)}finally{end(n)}
 }
 const calculate=async(retry=false)=>{
  const n=begin()
  try{
   const held=readNativeDemandRequest(baselineScope);if(held.error)throw Error(held.error);if(retry&&!held.pending)throw Error('Permintaan target tersimpan tidak tersedia.');if(!retry&&held.pending)throw Error('Periksa permintaan target yang sama terlebih dahulu.')
   const request=retry?held.pending!:{id:crypto.randomUUID(),q:query};if(!retry)persistNativeDemandRequest(baselineScope,request);setBaselineRecovery(readNativeDemandRequest(baselineScope))
   const reply=await client.rpc('erp_cp7_capture_baseline_v1',{p_query:request.q,p_request:request.id});if(n!==sequence.current)return;if(reply.error)throw reply.error
   const parsed=parseNativeBaseline(reply.data,request.q);if(parsed.requestId!==request.id||!parsed.rows.some(r=>r.rootId===product.rootId&&r.sizeId===product.sizeId))throw Error('Produk atau permintaan target server berubah.')
   clearNativeDemandRequest(baselineScope,request.id);setBaselineRecovery(readNativeDemandRequest(baselineScope));setBaseline(parsed)
  }catch(e){if(n===sequence.current)setError(normalizeClientError(e).message)}finally{end(n)}
 }
 const check=async()=>{
  if(!baseline)return;const run=baseline.runId,q=baseline.query,n=begin()
  try{const r=await client.rpc('erp_cp7_read_baseline_v1',{p_run:run});if(n!==sequence.current)return;if(r.error)throw r.error;const parsed=parseNativeBaseline(r.data,q);if(parsed.runId!==run)throw Error('Arsip target server berubah.');setBaseline(parsed)}catch(e){if(n===sequence.current)setError(normalizeClientError(e).message)}finally{end(n)}
 }
 const close=()=>{++sequence.current;if(active.current){active.current=false;onSourceReadEnd()}onClose()}
 const stale=Boolean(profile&&base&&(profile.revision!==base.revision||profile.productVersionId!==base.productVersionId)),pending=Boolean(recovery.pending||recovery.error||baselineRecovery.pending||baselineRecovery.error),r=baseline?.rows.find(x=>x.rootId===product.rootId&&x.sizeId===product.sizeId)
 return <section className="native-planning panel" aria-label="Aturan dan target produksi"><header><div><div className="eyebrow">ATURAN PER PRODUK</div><h2>{product.sku}</h2><p>{product.productName}</p></div><button onClick={close}>Tutup aturan target</button></header><p>Isi asumsi yang sudah diperiksa. Waktu proses, jadwal, atau kapasitas yang belum diketahui tetap kosong.</p>
  <button disabled={busy} onClick={()=>void readProfile()}>Muat aturan terbaru</button>{busy?<p role="status">Memeriksa aturan dan sumber ERP…</p>:null}
  {error||recovery.error||baselineRecovery.error?<p role="alert">{error||recovery.error||baselineRecovery.error}</p>:null}{message?<p role="status">{message}</p>:null}
  {profile?<p>Versi aturan {profile.revision} · {profile.quality==='SELECTED_ASSUMPTION'?'Asumsi dipilih dan diperiksa':profile.quality==='PHYSICAL_VERSION_CHANGED'?'Versi produk berubah; aturan perlu diperiksa lagi':'Belum ada aturan yang diperiksa'}</p>:null}
  {stale?<p role="alert">Aturan sumber berubah. Isianmu masih ada. Gunakan aturan terbaru sebelum menyimpan lagi.</p>:null}
  {profile&&(!base||stale||message)?<button disabled={busy||pending} onClick={()=>{useLatest(profile);setMessage('')}}>Gunakan aturan terbaru</button>:null}
  {base?<form onSubmit={e=>{e.preventDefault();void save()}}><fieldset disabled={busy||pending||!canSave}><legend>Asumsi target</legend><label>Dasar permintaan<select aria-label="Dasar permintaan" value={mode} onChange={e=>setMode(e.target.value as PlanningConfig['mean_mode'])}><option value="OWN_AVAILABLE_HISTORY">Riwayat saat stok tersedia</option><option value="SELECTED_MANUAL">Angka pilihan yang diperiksa</option></select></label>{mode==='SELECTED_MANUAL'?<label>Permintaan pilihan (PCS/hari)<input aria-label="Permintaan pilihan PCS per hari" inputMode="decimal" value={daily} onChange={e=>setDaily(e.target.value)} required/></label>:null}<label>Minimal hari riwayat tersedia<input aria-label="Minimal hari riwayat tersedia" inputMode="numeric" value={minimum} onChange={e=>setMinimum(e.target.value)} required/></label>{([['Waktu proses pilihan (hari kalender)',lead,setLead],['Jarak pemeriksaan (hari kalender)',review,setReview],['Cadangan waktu (hari kalender)',buffer,setBuffer]]as const).map(([label,value,set])=><label key={label}>{label}<input aria-label={label} inputMode="decimal" value={value} placeholder="Belum diketahui" onChange={e=>set(e.target.value)}/></label>)}<label className="native-planning-reason">Alasan pemeriksaan<textarea aria-label="Alasan aturan target" value={reason} maxLength={1000} onChange={e=>setReason(e.target.value)} required/></label><button disabled={!profile||stale||Boolean(message)}>Simpan aturan target</button></fieldset></form>:null}
  {!canSave?<p>Hak mengubah aturan produk belum diberikan.</p>:null}
  {recovery.pending?<div role="status"><p>Hasil simpan belum dipastikan. Periksa permintaan yang sama sebelum menyimpan lagi.</p><button disabled={busy||!canSave} onClick={()=>void save(true)}>Ulangi simpan aturan yang sama</button></div>:null}
  {baselineRecovery.pending?<div role="status"><p>Permintaan target belum dipastikan.</p><button disabled={busy} onClick={()=>void calculate(true)}>Ulangi permintaan target yang sama</button></div>:null}
  <button disabled={busy||pending||Boolean(message)} onClick={()=>void calculate()}>Hitung target dari ERP</button>
  {baseline&&r?<article className="native-planning-result"><p className={baseline.state==='UNCHANGED'?'native-demand-current':'native-demand-stale'}>{baseline.state==='UNCHANGED'?'Sumber sesuai saat diperiksa.':'Arsip lama: sumber ERP atau aturan sudah berubah. Hitung target baru.'} Diambil {formatCp6WibDateTime(baseline.capturedAt)}.</p><dl><div><dt>Target stok dari asumsi</dt><dd>{r.target===null?'Belum diketahui':numberText(r.target)+' PCS'}</dd></div><div><dt>Tersedia saat diambil</dt><dd>{numberText(r.available)} PCS</dd></div><div><dt>Permintaan per hari</dt><dd>{r.daily===null?'Belum diketahui':numberText(r.daily)+' PCS'}</dd></div><div><dt>Produksi baru</dt><dd>{r.startNew==='0'?'0 PCS · produksi dihentikan/jeda':'Belum dihitung'}</dd></div></dl><p>{r.meanBasis==='SELECTED_MANUAL_ASSUMPTION'?'Permintaan memakai angka pilihan yang diperiksa.':r.meanBasis==='UNKNOWN'?'Bukti riwayat permintaan belum cukup.':'Permintaan memakai riwayat saat stok tersedia.'} Aturan versi {r.profileRevision}.</p><p>Jumlah yang masih perlu diproduksi belum diketahui. Stok dalam proses, waktu tiba, jadwal dan kapasitas perlu sumber yang lengkap.</p><button disabled={busy} onClick={()=>void check()}>Periksa sumber target</button></article>:null}
 </section>
}
