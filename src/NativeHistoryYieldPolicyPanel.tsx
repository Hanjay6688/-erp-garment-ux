import {useCallback,useEffect,useMemo,useRef,useState} from 'react'
import {useAuth} from './auth/AuthProvider'
import {getUatSupabaseClient} from './lib/supabase'
import {normalizeClientError} from './lib/clientError'
import {formatCp6WibDateTime} from './cp6BusinessTime'
import {parseYieldPolicyWorkspace,yieldPolicyPayload,checkYieldPolicyOutcome,readYieldPolicyRequest,persistYieldPolicyRequest,clearYieldPolicyRequest,yieldPolicyRequestKey,type YieldPolicyWorkspace,type YieldPolicyState,type YieldPolicyRequest} from './nativeHistoryYieldPolicy'
type Props={onClose:()=>void}
const permissions=['master.product.view','production.wip.view']
const stateText={PENDING_POLICY_VALUE:'Belum disimpan: rencana memakai perkiraan yang ditinjau atau "belum diketahui".',ACTIVE:'Aktif: rencana memakai yield histori bila datanya cukup.',PAUSED:'Dijeda: histori tidak dipakai; rencana memakai perkiraan yang ditinjau atau "belum diketahui".'}
// PL-5 B: the owner-approved history yield package, saved as a versioned policy by an
// owner or admin with a reason. The form starts from the latest revision, or from the
// approved package when none is saved; the 90% one-sided bound is fixed, not a setting.
export default function NativeHistoryYieldPolicyPanel(props:Props){
 const{runtime,identity}=useAuth();if(runtime.mode!=='DISPOSABLE_TEST'||identity.status!=='AUTHORIZED'||!permissions.every(p=>identity.permissions.includes(p)))return null
 return <Workspace {...props} key={`${runtime.projectRef}:${identity.profile.id}:${identity.profile.rowVersion}:${identity.profile.roleRowVersion}:${identity.permissions.join('|')}`}/>
}
function Workspace({onClose}:Props){
 const{runtime,identity}=useAuth();if(runtime.mode!=='DISPOSABLE_TEST'||identity.status!=='AUTHORIZED')throw Error('Sesi kebijakan yield belum siap.')
 const client=useMemo(()=>getUatSupabaseClient(runtime),[runtime]),sequence=useRef(0),scope=runtime.projectRef+':'+identity.profile.id
 const[recovery,setRecovery]=useState(()=>readYieldPolicyRequest(scope)),[ws,setWs]=useState<YieldPolicyWorkspace|null>(null),[busy,setBusy]=useState(false),[error,setError]=useState(''),[message,setMessage]=useState('')
 const[state,setState]=useState<YieldPolicyState>('ACTIVE'),[windowDays,setWindowDays]=useState(''),[minGroups,setMinGroups]=useState(''),[minCutPcs,setMinCutPcs]=useState(''),[reason,setReason]=useState('')
 const fill=(w:YieldPolicyWorkspace)=>{const v=w.current??{state:'ACTIVE' as const,windowDays:w.decided.windowDays,minGroups:w.decided.minGroups,minCutPcs:w.decided.minCutPcs};setState(v.state);setWindowDays(v.windowDays);setMinGroups(v.minGroups);setMinCutPcs(v.minCutPcs);setReason('')}
 const load=useCallback(async()=>{
  const n=++sequence.current;setBusy(true);setError('')
  try{const r=await client.rpc('erp_cp7_get_history_yield_policy_v1');if(n!==sequence.current)return;if(r.error)throw r.error;const w=parseYieldPolicyWorkspace(r.data);setWs(w);fill(w)}
  catch(e){if(n===sequence.current)setError(normalizeClientError(e).message)}finally{if(n===sequence.current)setBusy(false)}
 },[client])
 useEffect(()=>{void load();return()=>{++sequence.current}},[load])
 useEffect(()=>{const f=(e:StorageEvent)=>{if(e.key===null||e.key===yieldPolicyRequestKey(scope)){++sequence.current;setBusy(false);setRecovery(readYieldPolicyRequest(scope))}};addEventListener('storage',f);return()=>removeEventListener('storage',f)},[scope])
 const save=async(retry=false)=>{
  if(!ws?.manageAllowed)return;const n=++sequence.current;setBusy(true);setError('');setMessage('')
  try{
   const held=readYieldPolicyRequest(scope);if(held.error)throw Error(held.error);if(retry&&!held.pending)throw Error('Permintaan tersimpan tidak tersedia.');if(!retry&&held.pending)throw Error('Periksa permintaan simpan yang sama terlebih dahulu.')
   const request:YieldPolicyRequest=retry?held.pending!:{id:crypto.randomUUID(),payload:yieldPolicyPayload(ws,state,{windowDays,minGroups,minCutPcs},reason)}
   if(!retry)persistYieldPolicyRequest(scope,request);setRecovery(readYieldPolicyRequest(scope))
   const reply=await client.rpc('erp_cp7_save_history_yield_policy_v1',{p_payload:request.payload,p_request:request.id});if(n!==sequence.current)return
   if(reply.error){if(/^[0-9A-Z]{5}$/.test(String((reply.error as {code?:string}).code??''))){clearYieldPolicyRequest(scope,request.id);setRecovery(readYieldPolicyRequest(scope))}throw reply.error}
   const saved=checkYieldPolicyOutcome(reply.data,request);clearYieldPolicyRequest(scope,request.id);setRecovery(readYieldPolicyRequest(scope))
   setMessage(`Kebijakan versi ${saved.revision} tersimpan (${saved.state==='ACTIVE'?'aktif':'dijeda'}).`);setBusy(false);void load()
  }catch(e){if(n===sequence.current){setError(normalizeClientError(e).message);setBusy(false)}}
 }
 const pending=Boolean(recovery.pending||recovery.error)
 return <section className="panel native-yield-policy" aria-label="Kebijakan yield histori"><header><div><div className="eyebrow">PERENCANAAN · YIELD HISTORI</div><h2>Kebijakan yield histori</h2></div><button onClick={()=>{++sequence.current;onClose()}}>Tutup kebijakan yield</button></header>
  <p>Hasil bagus untuk start baru diambil dari grup potong yang sudah selesai dan terbukti habis. Batas bawah satu sisi 90% (dibulatkan ke bawah ke 0,1%), per produk dan ukuran lalu model yang sama. Tidak pernah dari model lain dan tidak pernah dianggap 100%.</p>
  {busy?<p role="status">Memeriksa kebijakan…</p>:null}{error||recovery.error?<p role="alert">{error||recovery.error}</p>:null}{message?<p role="status">{message}</p>:null}
  {ws?<><p data-policy-state={ws.state}>{stateText[ws.state]}</p>
   {ws.current?<p>Versi {ws.current.revision}: {ws.current.windowDays} hari, minimal {ws.current.minGroups} grup selesai dan {ws.current.minCutPcs} PCS potong. Disimpan oleh {ws.current.actorRole==='OWNER'?'pemilik':'admin'} {formatCp6WibDateTime(ws.current.recordedAt)}. Alasan: {ws.current.reason}</p>
    :<p>Paket keputusan owner 8 Okt 2026: {ws.decided.windowDays} hari, minimal {ws.decided.minGroups} grup selesai dan {ws.decided.minCutPcs} PCS potong, batas bawah 90%. Berlaku setelah disimpan.</p>}
   <form onSubmit={e=>{e.preventDefault();void save()}}><fieldset disabled={busy||pending||!ws.manageAllowed}><legend>{ws.current?'Ubah kebijakan (versi baru)':'Simpan kebijakan'}</legend>
    <label>Status<select aria-label="Status kebijakan yield" value={state} onChange={e=>setState(e.target.value as YieldPolicyState)}><option value="ACTIVE">Aktif</option><option value="PAUSED">Jeda</option></select></label>
    <label>Jendela histori (hari)<input aria-label="Jendela histori hari" inputMode="numeric" value={windowDays} onChange={e=>setWindowDays(e.target.value)} required/></label>
    <label>Minimal grup selesai<input aria-label="Minimal grup selesai" inputMode="numeric" value={minGroups} onChange={e=>setMinGroups(e.target.value)} required/></label>
    <label>Minimal PCS potong<input aria-label="Minimal PCS potong" inputMode="numeric" value={minCutPcs} onChange={e=>setMinCutPcs(e.target.value)} required/></label>
    <p>Tingkat keyakinan: 90% satu sisi (tetap).</p>
    <label>Alasan<textarea aria-label="Alasan kebijakan yield" maxLength={1000} value={reason} onChange={e=>setReason(e.target.value)} required/></label>
    <button>Simpan kebijakan yield</button></fieldset></form>
   {!ws.manageAllowed?<p>Hanya pemilik atau admin dengan hak mengubah produk yang dapat menyimpan kebijakan ini.</p>:null}
   {recovery.pending?<div role="status"><p>Hasil simpan belum dipastikan. Ulangi permintaan yang sama sebelum menyimpan lagi.</p><button disabled={busy||!ws.manageAllowed} onClick={()=>void save(true)}>Ulangi simpan kebijakan yang sama</button></div>:null}
   {ws.revisions.length?<details><summary>Riwayat versi ({ws.revisions.length})</summary><ul>{ws.revisions.map(r=><li key={r.id} data-revision={r.revision}>Versi {r.revision} · {r.state==='ACTIVE'?'aktif':'dijeda'} · {r.windowDays} hari, {r.minGroups} grup, {r.minCutPcs} PCS · {r.actorRole==='OWNER'?'pemilik':'admin'} · {formatCp6WibDateTime(r.recordedAt)} · {r.reason}</li>)}</ul></details>:null}
  </>:null}
 </section>
}
