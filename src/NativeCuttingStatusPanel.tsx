import {useCallback,useEffect,useMemo,useRef,useState} from 'react'
import {useAuth} from './auth/AuthProvider'
import {isConnectedRuntime} from './config/runtime'
import {getUatSupabaseClient} from './lib/supabase'
import {normalizeClientError} from './lib/clientError'
import {formatCp6WibDateTime} from './cp6BusinessTime'
import {cuttingCoverageFromPercent,cuttingCoveragePercent,cuttingStatusClient,cuttingStatusLabels,
  cuttingStatusPolicyEvent,cuttingStatusPolicyPrefix,holdCuttingStatusPolicy,pendingCuttingStatusPolicies,
  releaseCuttingStatusPolicy,parseAutomaticCuttingStatus,validateCuttingStatusPolicyIntent,
  validateCuttingStatusPolicyResult,type AutomaticCuttingStatus,type CuttingStatusPolicyIntent} from './nativeCuttingStatus'

type Props={groupId:string|null;sourceKey:string;parentBusy:boolean;onAuthorityLost?:()=>void}
type Form={coverage:string;minimum:string;state:'ACTIVE'|'PAUSED';reason:string;reviewed:boolean}
const empty:Form={coverage:'',minimum:'',state:'ACTIVE',reason:'',reviewed:false}
const rights=['production.cutting.view','master.product.view','production.wip.view','warehouse.stock.view','sales.invoice.view']
const stages:Record<string,string>={DRAFT:'Draf',CUTTING:'Potong',SEWING:'Jahit',LAUNDRY:'Laundry',QC:'Pemeriksaan kualitas',FINISHED:'Selesai',CANCELLED:'Dibatalkan'}

export default function NativeCuttingStatusPanel(props:Props){
  const {runtime,identity}=useAuth()
  if(!isConnectedRuntime(runtime)||identity.status!=='AUTHORIZED'||!['OWNER','ADMIN'].includes(identity.profile.role)||!rights.every(p=>identity.permissions.includes(p)))return null
  const key=JSON.stringify([runtime.projectRef,identity.profile.id,identity.profile.authUserId,identity.profile.role,identity.profile.rowVersion,
    identity.profile.roleRowVersion,identity.permissions])
  return <StatusWorkspace {...props} key={key}/>
}

function StatusWorkspace({groupId,sourceKey,parentBusy,onAuthorityLost}:Props){
  const {runtime,identity}=useAuth()
  if(!isConnectedRuntime(runtime)||identity.status!=='AUTHORIZED')throw Error('Sesi status potong belum siap.')
  const actor=identity.profile.authUserId,scope=runtime.projectRef+':'+actor
  const client=useMemo(()=>cuttingStatusClient(getUatSupabaseClient(runtime)),[runtime])
  const binding=JSON.stringify([groupId,sourceKey,parentBusy]),current=useRef(binding),readSeq=useRef(0),alive=useRef(true),denied=useRef(false)
  current.current=binding
  const [data,setData]=useState<{binding:string;value:AutomaticCuttingStatus}|null>(null)
  const [loading,setLoading]=useState(false),[saving,setSaving]=useState(false),[error,setError]=useState(''),[message,setMessage]=useState('')
  const [pending,setPending]=useState<CuttingStatusPolicyIntent[]>([]),[storageError,setStorageError]=useState(''),[form,setForm]=useState(empty)
  const notifyDenied=useCallback((failure:ReturnType<typeof normalizeClientError>)=>{
    if(['FORBIDDEN','AUTH_REQUIRED'].includes(failure.code)){denied.current=true;++readSeq.current;setData(null);onAuthorityLost?.()}
  },[onAuthorityLost])
  const readPending=useCallback(()=>{
    try{setPending(pendingCuttingStatusPolicies(scope));setStorageError('')}
    catch{setStorageError('Catatan penyimpanan aturan belum dapat dibaca. Penyimpanan baru ditahan agar permintaan lama tetap aman.')}
  },[scope])
  const load=useCallback(async(force=false)=>{
    if(denied.current&&!force)return
    if(force)denied.current=false
    const n=++readSeq.current,bound=current.current
    setData(null);setForm(empty);setError('')
    if(!groupId||parentBusy){setLoading(false);return}
    setLoading(true)
    try{
      const reply=await client.rpc('erp_cp7_get_cutting_status_v1',{p_group:groupId})
      if(!alive.current||n!==readSeq.current||bound!==current.current)return
      if(reply.error)throw reply.error
      const value=parseAutomaticCuttingStatus(reply.data,groupId)
      setData({binding:bound,value})
      setForm({coverage:value.policy?cuttingCoveragePercent(value.policy.coverage):'',minimum:value.policy?.min_groups??'',
        state:value.policy?.state??'ACTIVE',reason:'',reviewed:false})
    }catch(e){if(alive.current&&n===readSeq.current&&bound===current.current){const f=normalizeClientError(e);setError(f.message);notifyDenied(f)}}
    finally{if(alive.current&&n===readSeq.current)setLoading(false)}
  },[client,groupId,parentBusy,notifyDenied])
  useEffect(()=>{alive.current=true;return()=>{alive.current=false;++readSeq.current}},[])
  useEffect(()=>{void load();return()=>{++readSeq.current}},[load,sourceKey])
  useEffect(()=>{
    const refresh=()=>{readPending();setForm(f=>({...f,reviewed:false}));void load()}
    const storage=(event:StorageEvent)=>{if(event.key===null||event.key.startsWith(cuttingStatusPolicyPrefix(scope)))refresh()}
    const local=(event:Event)=>{if((event as CustomEvent).detail===scope)refresh()}
    const visible=()=>{if(document.visibilityState==='visible')refresh()}
    readPending();addEventListener('storage',storage);addEventListener(cuttingStatusPolicyEvent,local)
    addEventListener('focus',refresh);document.addEventListener('visibilitychange',visible)
    return()=>{removeEventListener('storage',storage);removeEventListener(cuttingStatusPolicyEvent,local)
      removeEventListener('focus',refresh);document.removeEventListener('visibilitychange',visible)}
  },[scope,readPending,load])
  const value=data?.binding===binding&&!parentBusy&&!saving&&pending.length===0&&!storageError?data.value:null
  const canManage=identity.profile.role==='OWNER'&&identity.permissions.includes('master.product.manage')
  const locked=saving||parentBusy||pending.length>0||Boolean(storageError)||!value
  const edit=<K extends keyof Form>(key:K,next:Form[K])=>setForm(f=>({...f,[key]:next,reviewed:key==='reviewed'?Boolean(next):false}))

  const send=async(recover?:CuttingStatusPolicyIntent)=>{
    if(saving||parentBusy||!canManage||storageError)return
    const bound=current.current
    setError('');setMessage('')
    let intent:CuttingStatusPolicyIntent
    try{
      if(recover){
        if(!pendingCuttingStatusPolicies(scope).some(p=>p.requestId===recover.requestId&&JSON.stringify(p)===JSON.stringify(recover)))throw Error('Permintaan aturan sudah berubah. Muat ulang.')
        intent=recover
      }else{
        if(!value||!form.reviewed||pendingCuttingStatusPolicies(scope).length)throw Error('Periksa aturan dan sumber terbaru sebelum menyimpan.')
        intent=validateCuttingStatusPolicyIntent({requestId:crypto.randomUUID(),payload:{expected_revision:value.policy?.revision??'0',
          state:form.state,coverage:cuttingCoverageFromPercent(form.coverage),min_groups:form.minimum,
          reason:form.reason,explicit_review:true}})
        holdCuttingStatusPolicy(scope,intent)
      }
    }catch(e){setError(normalizeClientError(e).message);readPending();return}
    setSaving(true);setData(null);setForm(f=>({...f,reviewed:false}))
    try{
      const args={p_payload:intent.payload,p_request:intent.requestId}
      const reply=recover?await client.rpc('erp_cp7_get_cutting_status_policy_request_v1',args)
        :await client.rpc('erp_cp7_save_cutting_status_policy_v1',args)
      if(reply.error)throw reply.error
      const status=validateCuttingStatusPolicyResult(reply.data,intent,actor)
      releaseCuttingStatusPolicy(scope,intent)
      if(alive.current&&bound===current.current)setMessage(status==='COMMITTED'
        ?'Aturan pabrik tersimpan. Status dihitung ulang dari riwayat yang cocok.'
        :'Permintaan tadi belum tersimpan dan sudah ditutup. Periksa aturan terbaru sebelum mencoba lagi.')
    }catch(e){if(alive.current&&bound===current.current){const f=normalizeClientError(e);setError(f.message);notifyDenied(f)}}
    finally{if(alive.current){setSaving(false);readPending();void load()}}
  }
  return <section className="ccut-card wide ccut-status" aria-label="Status hasil potong otomatis">
    <header><span>HASIL POTONG OTOMATIS</span><strong>Status dari riwayat pabrik</strong></header>
    {!groupId?<p>Status muncul otomatis setelah potongan disahkan. Draf belum menjadi hasil potong.</p>:null}
    {parentBusy?<p role="status">Menunggu hasil penyimpanan potongan dipastikan…</p>:loading?<p role="status">Memeriksa hasil potong otomatis…</p>:null}
    {error||storageError?<p role="alert">{error||storageError}</p>:null}
    {message?<p role="status">{message}</p>:null}
    {pending.map(intent=><div key={intent.requestId}><p role="status">Penyimpanan aturan belum dipastikan. Permintaan {intent.requestId.slice(0,8)} tetap disimpan.</p>
      <button type="button" disabled={saving||parentBusy||!canManage||Boolean(storageError)} onClick={()=>void send(intent)}>Periksa aturan tertunda {intent.requestId.slice(0,8)}</button></div>)}
    {value?<>
      <p>{value.group.posted?'Potong sudah disahkan.':'Potongan belum disahkan atau sudah dibatalkan.'} {value.group.pattern_label||'Pola belum lengkap'} · {formatCp6WibDateTime(value.group.physical_at)}.</p>
      <p>Proses produksi: {stages[value.group.production_stage]??'Status proses belum dikenali'}. Penilaian ini khusus hasil potong.</p>
      <ul className="ccut-status-list">{value.materials.map(row=><li key={row.material_id}>
        <strong>{row.sku} · {row.name}</strong>
        <p className={`ccut-status-result ${row.status==='LOW'||row.status==='HIGH'?'review':''}`}>{cuttingStatusLabels[row.status]}</p>
        <p>Total hasil: {row.total_pcs===null?'belum lengkap':row.total_pcs+' pcs'} · kain terpakai: {row.consumed===null?'belum lengkap':row.consumed+' '+row.unit}.</p>
        <p>Ukuran: {row.size_labels.length?row.size_labels.join(', '):'belum lengkap'}.</p>
        {row.lower_pcs!==null&&row.upper_pcs!==null?<p>Rentang untuk jumlah kain ini: {row.lower_pcs}–{row.upper_pcs} pcs.</p>:null}
        <p>{row.history_groups} kelompok potong pembanding dari seluruh pabrik.</p>
      </li>)}</ul>
      {value.materials.length===0?<p>Rincian bahan belum lengkap; belum ada penilaian hasil.</p>:null}
      <p>Perbandingan memakai jenis bahan, pola, revisi, dan ukuran yang sama. Selisih hasil belum menjelaskan penyebabnya.</p>
      <p>Diperiksa {formatCp6WibDateTime(value.checkedAt)}. {value.policy?`Aturan versi ${value.policy.revision}: cakupan riwayat ${cuttingCoveragePercent(value.policy.coverage)}%, minimal ${value.policy.min_groups} kelompok.`:'Aturan cakupan dan minimum riwayat belum ditetapkan owner.'}</p>
      {canManage?<details><summary>Atur rentang hasil potong pabrik</summary>
        <p>Aturan berlaku untuk seluruh pabrik; pembanding setiap bahan, pola dan ukuran tetap terpisah. Tidak ada angka bawaan yang diaktifkan.</p>
        <fieldset disabled={locked}><div className="ccut-fields">
          <label>Cakupan rentang riwayat (%)<input inputMode="decimal" value={form.coverage} onChange={e=>edit('coverage',e.target.value)}/></label>
          <label>Minimum kelompok pembanding<input inputMode="numeric" value={form.minimum} onChange={e=>edit('minimum',e.target.value)}/></label>
          <label>Keadaan aturan<select value={form.state} onChange={e=>edit('state',e.target.value as 'ACTIVE'|'PAUSED')}><option value="ACTIVE">Aktif</option><option value="PAUSED">Jeda</option></select></label>
          <label>Alasan perubahan<input maxLength={1000} value={form.reason} onChange={e=>edit('reason',e.target.value)}/></label>
        </div><label><input type="checkbox" checked={form.reviewed} onChange={e=>edit('reviewed',e.target.checked)}/> Saya sudah memeriksa cakupan dan minimum riwayat ini.</label>
          <button type="button" disabled={locked||!form.reviewed} onClick={()=>void send()}>Simpan aturan hasil potong</button>
        </fieldset>
      </details>:null}
    </>:null}
    {groupId&&!parentBusy&&!loading&&!value&&pending.length===0&&!storageError&&error?<button type="button" onClick={()=>void load(true)}>Coba lagi status potong</button>:null}
  </section>
}
