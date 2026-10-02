import {useEffect, useMemo, useRef, useState} from 'react'
import {useAuth} from './auth/AuthProvider'
import {getUatSupabaseClient} from './lib/supabase'
import {normalizeClientError} from './lib/clientError'
import {formatCp6WibDateTime} from './cp6BusinessTime'
import {cuttingInputChangedEvent, cuttingInputKey, heldCuttingInput, parseCuttingInputWorkspace, type CuttingInputWorkspace} from './nativeCuttingInputs'
import {cuttingLearningKey, heldLearning, holdLearning, releaseLearning, parseLearningReply, parseModelWorkspace, validateLearningIntent, type LearningReply, type ModelWorkspace} from './nativeCuttingLearning'

type Props = {groupId:string|null; sourceKey:string; parentBusy:boolean; onAuthorityLost?:()=>void}
type PolicyForm = {coverage:string; train:string; calibration:string; holdout:string; reviewed:boolean}
const empty:PolicyForm={coverage:'',train:'',calibration:'',holdout:'',reviewed:false}
const required=['production.cutting.view','master.product.view','production.wip.view','warehouse.stock.view','sales.invoice.view']
const reasons:Record<string,string>={
  PROSPECTIVE_SEPARATE_BATCHES_REQUIRED:'Belum cukup kejadian potong baru setelah aturan ini dicatat.',
  CURRENT_HISTORY_RECAPTURE_REQUIRED:'Riwayat potong berubah. Catat hasil nyata yang terbaru dahulu.',
  CURRENT_INPUT_IDENTITY_UNAVAILABLE:'Rencana sudah tidak cocok dengan potongan ini.',
  PLAN_RECORDED_AFTER_PHYSICAL_EVENT:'Rencana dicatat setelah kain dipotong, sehingga belum bisa dipakai untuk penilaian ini.',
  INPUT_RECORDED_AFTER_PHYSICAL_EVENT:'Rencana dicatat setelah waktu potong.',
  NATIVE_UNPOSTED_OR_CANCELLED:'Potongan belum diposting atau sudah dibatalkan.',
  INPUT_IDENTITY_UNAVAILABLE_OR_CHANGED:'Rencana belum tersedia atau identitas potongan berubah.',
  NATIVE_OUTPUT_OR_CONSUMPTION_UNAVAILABLE:'Jumlah kain atau hasil nyata belum lengkap.',
  NATIVE_SLICE_OR_GROUP_REMOVED:'Bagian potongan ini sudah dihapus dari sumber.',
  NATIVE_PHYSICAL_IDENTITY_CHANGED:'Waktu atau identitas kejadian potong berubah.',
  CURRENT_NATIVE_CONSUMPTION_UNAVAILABLE:'Pemakaian kain untuk potongan ini belum lengkap.',
  CONSUMPTION_OUTSIDE_TRAINING_SUPPORT:'Jumlah kain ini berada di luar riwayat yang dipelajari.',
  WIDTH_OUTSIDE_TRAINING_SUPPORT:'Lebar kain ini berada di luar riwayat yang dipelajari.',
  BASELINE_HOLDOUT_COVERAGE_FAILED:'Rentang dasar belum cukup baik saat diperiksa dengan potongan lain.',
  OBSERVATION_CAPTURE_OVERLAPS_LATER_PHYSICAL_FOLD:'Urutan pencatatan hasil belum memungkinkan pemeriksaan dengan kelompok terpisah.',
  CURRENT_PLAN_MUST_FOLLOW_HOLDOUT:'Rencana sekarang harus dibuat setelah kelompok pemeriksaan selesai.',
}
const display=(v:string)=>v.includes('.')?v.replace(/0+$/,'').replace(/\.$/,''):v
const reasonText=(reason:string)=>reasons[reason]??'Data yang tersedia belum mendukung penilaian hasil ini.'
export default function NativeCuttingLearningPanel(props:Props) {
  const {runtime,identity}=useAuth()
  if(runtime.mode!=='DISPOSABLE_TEST'||identity.status!=='AUTHORIZED'||!['OWNER','ADMIN'].includes(identity.profile.role)||!required.every(p=>identity.permissions.includes(p))) return null
  return <Workspace {...props} key={`${runtime.projectRef}:${identity.profile.id}:${identity.profile.rowVersion}:${identity.profile.roleRowVersion}:${identity.permissions.join('|')}`}/>
}
function Workspace({groupId,sourceKey,parentBusy,onAuthorityLost}:Props) {
  const {runtime,identity}=useAuth()
  if(runtime.mode!=='DISPOSABLE_TEST'||identity.status!=='AUTHORIZED') throw Error('Sesi penilaian potong belum siap.')
  const scope=runtime.projectRef+':'+identity.profile.id,actor=identity.profile.authUserId
  const client=useMemo(()=>getUatSupabaseClient(runtime),[runtime]),seq=useRef(0)
  const binding=JSON.stringify([groupId,sourceKey,parentBusy]),current=useRef(binding),previousGroup=useRef(groupId)
  current.current=binding
  const [data,setData]=useState<{binding:string;input:CuttingInputWorkspace;model:ModelWorkspace|null;reply:LearningReply|null}|null>(null)
  const [roll,setRoll]=useState(''),[form,setForm]=useState(empty),[held,setHeld]=useState(()=>heldLearning(scope)),[inputsHeld,setInputsHeld]=useState(()=>heldCuttingInput(scope))
  const [busy,setBusy]=useState(false),[error,setError]=useState(''),[message,setMessage]=useState('')
  useEffect(()=>{
    ++seq.current;setData(null);setBusy(false);setError('');setMessage('')
    if(previousGroup.current!==groupId){setForm(empty);setRoll('')} else setForm(f=>({...f,reviewed:false}))
    previousGroup.current=groupId
    return ()=>{++seq.current}
  },[binding,groupId])
  useEffect(()=>{
    const retire=()=>{++seq.current;setBusy(false);setData(null);setHeld(heldLearning(scope));setInputsHeld(heldCuttingInput(scope));setForm(f=>({...f,reviewed:false}))}
    const storage=(e:StorageEvent)=>{if(e.key===null||[cuttingInputKey(scope),cuttingLearningKey(scope)].includes(e.key)) retire()}
    const input=(e:Event)=>{if((e as CustomEvent).detail===scope) retire()}
    addEventListener('storage',storage);addEventListener(cuttingInputChangedEvent,input)
    return ()=>{removeEventListener('storage',storage);removeEventListener(cuttingInputChangedEvent,input)}
  },[scope])
  const visible=data?.binding===binding&&!busy&&!parentBusy?data:null
  const locked=busy||parentBusy||Boolean(held.pending||held.error||inputsHeld.pending||inputsHeld.error)
  const canWrite=identity.permissions.includes('production.cutting.edit_draft')
  const publish=(input:CuttingInputWorkspace,model:ModelWorkspace|null,reply:LearningReply|null,bound:string)=>{
    if(groupId!==null&&input.requested_group_id!==groupId){setMessage('Permintaan lama selesai. Muat potongan yang sekarang dipilih.');return}
    setData({binding:bound,input,model,reply})
  }
  const load=async(selectedRoll?:string)=>{
    if(parentBusy||held.pending||held.error||inputsHeld.pending||inputsHeld.error) return
    const readGroup=groupId??visible?.input.requested_group_id
    if(!readGroup) return
    const n=++seq.current,bound=current.current
    setData(null);setError('');setMessage('');setBusy(true);setForm(f=>({...f,reviewed:false}))
    try {
      const r=await client.rpc('erp_cp7_get_cutting_input_workspace_v1',{p_group:readGroup})
      if(n!==seq.current||bound!==current.current) return
      if(r.error) throw r.error
      const input=parseCuttingInputWorkspace(r.data,readGroup)
      if(input.actor_scope_id!==actor) throw Error('Sumber penilaian bukan milik sesi ini.')
      const choices=input.anchor?.rolls??[],choice=choices.find(x=>x.roll_id===(selectedRoll??roll))?.roll_id??choices[0]?.roll_id??''
      let model:ModelWorkspace|null=null
      if(choice) {
        const result=await client.rpc('erp_cp7_get_cutting_model_workspace_v1',{p_group:readGroup,p_roll:choice})
        if(n!==seq.current||bound!==current.current) return
        if(result.error) throw result.error
        model=parseModelWorkspace(result.data,readGroup,choice,actor)
        // The model RPC owns the final current input, not the earlier picker read.
        publish(model.input,model,null,bound)
      } else publish(input,null,null,bound)
      setRoll(choice)
    } catch(e) {if(n===seq.current) {const failure=normalizeClientError(e);setError(failure.message);if(['FORBIDDEN','AUTH_REQUIRED'].includes(failure.code)) onAuthorityLost?.()}}
    finally {if(n===seq.current) setBusy(false)}
  }
  const act=async(action:'OBSERVATION'|'POLICY'|'CHECK'|'RECOVER')=>{
    if(parentBusy||inputsHeld.pending||inputsHeld.error) return
    const n=++seq.current,bound=current.current,w=visible
    setData(null);setError('');setMessage('');setBusy(true)
    try {
      const pending=heldLearning(scope)
      if(pending.error) throw Error(pending.error)
      let intent=pending.pending
      if(action==='RECOVER') {if(!intent) throw Error('Catatan permintaan tidak ada.')}
      else {
        if(intent||!canWrite||!w?.input.group) throw Error('Muat sumber potongan dahulu.')
        const input=w.input, common={group_id:input.group!.id,expected_group_version:input.group!.version,expected_input_version:input.record?.version??null}
        if(action==='OBSERVATION') intent=validateLearningIntent({id:crypto.randomUUID(),kind:'OBSERVATION',payload:common})
        else {
          if(!w.model?.feature||!input.record||!input.record_matches_native_identity) throw Error('Catat rencana yang sesuai dengan potongan dahulu.')
          const modelCommon={...common,expected_input_version:input.record.version,roll_id:w.model.rollId}
          if(action==='POLICY') {
            if(!form.reviewed) throw Error('Periksa aturan belajar dahulu.')
            intent=validateLearningIntent({id:crypto.randomUUID(),kind:'MODEL',payload:{action:'POLICY',...modelCommon,expected_policy_id:w.model.policy?.id??null,coverage:form.coverage,train_batches:form.train,calibration_batches:form.calibration,holdout_batches:form.holdout,explicit_review:true}})
          } else {
            if(!w.model.policy) throw Error('Catat aturan belajar dahulu.')
            intent=validateLearningIntent({id:crypto.randomUUID(),kind:'MODEL',payload:{action:'CHECK',...modelCommon,policy_id:w.model.policy.id}})
          }
        }
        holdLearning(scope,intent!)
      }
      setHeld(heldLearning(scope))
      const args={p_payload:intent!.payload,p_request:intent!.id}
      const result=intent!.kind==='OBSERVATION'
        ? action==='RECOVER' ? await client.rpc('erp_cp7_get_cutting_observation_request_v1',args) : await client.rpc('erp_cp7_capture_cutting_observation_v1',args)
        : action==='RECOVER' ? await client.rpc('erp_cp7_get_cutting_model_request_v1',args) : await client.rpc('erp_cp7_capture_cutting_model_v1',args)
      if(n!==seq.current||bound!==current.current) return
      if(result.error) throw result.error
      const reply=parseLearningReply(result.data,intent!,actor)
      releaseLearning(scope,intent!);setHeld(heldLearning(scope));setForm(f=>({...f,reviewed:false}))
      if(!reply.committed) setMessage('Permintaan tadi belum tersimpan dan sudah ditutup. Muat sumber sebelum membuat permintaan baru.')
      else if(intent!.kind==='MODEL'&&intent!.payload.action==='POLICY') setMessage('Aturan belajar tercatat. Penilaian memakai kejadian potong baru sesudah pencatatan ini.')
      else if(!reply.currentOriginal) setMessage('Catatan lama berhasil dipulihkan. Sumber sudah berubah; muat sumber untuk menilai potongan sekarang.')
      else setMessage(intent!.kind==='OBSERVATION'?'Hasil potong tercatat dengan waktu pencatatan yang sebenarnya.':'Penilaian hasil potong tercatat.')
      if(reply.current) {setRoll(reply.current.rollId);publish(reply.current.input,reply.current,reply,bound)}
      else if(w) publish(w.input,w.model,reply,bound)
      else if(intent!.kind==='OBSERVATION'&&reply.committed) {
        const fresh=await client.rpc('erp_cp7_get_cutting_input_workspace_v1',{p_group:intent!.payload.group_id})
        if(n!==seq.current||bound!==current.current) return
        if(fresh.error) throw fresh.error
        const input=parseCuttingInputWorkspace(fresh.data,intent!.payload.group_id)
        if(input.actor_scope_id!==actor) throw Error('Sumber penilaian bukan milik sesi ini.')
        const matches=reply.currentOriginal&&(input.group?.version??null)===intent!.payload.expected_group_version&&(input.record?.version??null)===intent!.payload.expected_input_version
        publish(input,null,{...reply,currentOriginal:matches},bound)
        if(!matches) setMessage('Catatan lama berhasil dipulihkan. Sumber sudah berubah; muat sumber untuk menilai potongan sekarang.')
      }
    } catch(e) {if(n===seq.current){const failure=normalizeClientError(e);setError(failure.message);setHeld(heldLearning(scope));if(['FORBIDDEN','AUTH_REQUIRED'].includes(failure.code)) onAuthorityLost?.()}}
    finally {if(n===seq.current) setBusy(false)}
  }
  const e=visible?.reply?.currentOriginal?visible.reply.assessment:null,o=visible?.reply?.currentOriginal?visible.reply.observation:null
  const plan=visible?.model,edit=(key:keyof Omit<PolicyForm,'reviewed'>,value:string)=>setForm(f=>({...f,[key]:value,reviewed:false}))
  return <section className="ccut-card wide" aria-label="Belajar dari hasil potong">
    <header><span>HASIL POTONG</span><strong>Belajar dari kejadian yang tercatat</strong></header>
    <p>Rencana, waktu potong, dan waktu pencatatan tetap dibedakan. Rentang belajar membantu pemeriksaan operator; stok dan HPP mengikuti transaksi potong.</p>
    <div className="ccut-actions">
      <button type="button" disabled={locked||!groupId&&!visible} onClick={()=>void load()}>Muat penilaian potong</button>
      {held.pending?<button type="button" disabled={busy||parentBusy||Boolean(inputsHeld.pending||inputsHeld.error)} onClick={()=>void act('RECOVER')}>Pulihkan penilaian potong</button>:null}
      {visible?<button type="button" disabled={locked} onClick={()=>void load()}>Periksa sumber penilaian</button>:null}
    </div>
    {busy?<p role="status">Memeriksa hasil potong…</p>:null}
    {error||held.error||inputsHeld.error?<p role="alert">{error||held.error||inputsHeld.error}</p>:null}
    {inputsHeld.pending?<p role="status">Pulihkan rencana potong terlebih dahulu.</p>:null}
    {message?<p role="status">{message}</p>:null}
    {visible?<>
      <label>Roll yang dinilai<select value={roll} disabled={locked} onChange={ev=>{setRoll(ev.target.value);void load(ev.target.value)}}>{visible.input.anchor?.rolls.map(r=><option key={r.roll_id} value={r.roll_id}>{visible.input.roll_labels[r.roll_id]??'Bahan'} · {r.roll_id.slice(0,8)}</option>)}</select></label>
      <button type="button" disabled={locked||!canWrite||!visible.input.group} onClick={()=>void act('OBSERVATION')}>Catat hasil nyata potong</button>
      {o?<div data-cutting-observation><p>Hasil dicatat {formatCp6WibDateTime(o.knownAt)}.</p>{o.records.map(r=><p key={r.id}>{r.valid?`${r.pcs} pcs dari ${r.consumed} ${r.unit}.`:'Bagian ini belum memenuhi syarat riwayat belajar.'}</p>)}{o.exclusions.map((x,i)=><p key={x.id+':'+i}>{reasonText(x.reason)}</p>)}</div>:null}
      {plan?.feature?<p>{plan.feature.context.family.brand} · {plan.feature.context.family.variant} · lebar {plan.feature.width_cm===null?'belum dicatat':plan.feature.width_cm+' cm'}.</p>:<p>Catat rencana bahan terlebih dahulu agar riwayat yang dibandingkan cocok.</p>}
      {plan?.policy?<div data-cutting-policy><p>Aturan dicatat {formatCp6WibDateTime(plan.policy.known_at)}. Target cakupan {plan.policy.coverage}; kelompok belajar {plan.policy.train_batches}, kalibrasi {plan.policy.calibration_batches}, pemeriksaan terpisah {plan.policy.holdout_batches}.</p><p>Cakupan empiris berlaku untuk riwayat tercatat milik akun ini. Jaminan seluruh produksi belum ditetapkan.</p></div>:null}
      <fieldset disabled={locked||!canWrite||!plan?.feature||!visible.input.record_matches_native_identity}>
        <legend>Aturan belajar untuk kejadian baru</legend>
        <p>Aturan baru memakai potongan sesudah aturan dicatat. Tiap kelompok minimal 3 kejadian. Target tinggi memerlukan lebih banyak kejadian kalibrasi.</p>
        <div className="ccut-fields">
          <label>Target cakupan (antara 0 dan 1)<input inputMode="decimal" value={form.coverage} onChange={ev=>edit('coverage',ev.target.value)}/></label>
          <label>Jumlah kejadian belajar<input inputMode="numeric" value={form.train} onChange={ev=>edit('train',ev.target.value)}/></label>
          <label>Jumlah kejadian kalibrasi<input inputMode="numeric" value={form.calibration} onChange={ev=>edit('calibration',ev.target.value)}/></label>
          <label>Jumlah kejadian pemeriksaan terpisah<input inputMode="numeric" value={form.holdout} onChange={ev=>edit('holdout',ev.target.value)}/></label>
        </div>
        <label><input type="checkbox" checked={form.reviewed} onChange={ev=>setForm(f=>({...f,reviewed:ev.target.checked}))}/> Saya sudah memeriksa aturan belajar ini.</label>
        <button type="button" disabled={!form.reviewed} onClick={()=>void act('POLICY')}>Catat aturan belajar potong</button>
      </fieldset>
      <button type="button" disabled={locked||!canWrite||!plan?.policy||!visible.input.record_matches_native_identity} onClick={()=>void act('CHECK')}>Nilai hasil potong</button>
      {e?<div data-cutting-assessment>{e.interval?<>
        <p>Rentang empiris {display(e.interval.lower_pcs)}–{display(e.interval.upper_pcs)} pcs; tengah {display(e.interval.center_pcs)} pcs.</p>
        <p>{e.basis==='WITH_RECORDED_WIDTH'?'Memakai lebar kain yang dicatat.':'Lebar belum menjadi dasar penilaian; variasinya tetap berada dalam rentang.'}</p>
        <p>{e.status==='PREDICTION_ONLY'?'Hasil fisik belum diposting; ini perkiraan dari rencana pemakaian kain.':e.status==='WITHIN_EMPIRICAL_INTERVAL'?'Hasil nyata berada dalam rentang empiris.':'Hasil nyata berada di luar rentang empiris. Periksa kejadian ini; penyebabnya belum diketahui.'}</p>
        <table><thead><tr><th>Kelompok</th><th>Kejadian berbeda</th></tr></thead><tbody>{([['Belajar','train'],['Kalibrasi','calibration'],['Pemeriksaan terpisah','holdout']]as const).map(([label,key])=><tr key={key}><td>{label}</td><td>{new Set(e.folds[key].map(r=>r.batch_key)).size}</td></tr>)}</tbody></table>
      </>:<p>{reasonText(e.reason)}</p>}</div>:null}
    </>:<p>Simpan atau pilih draft potongan, lalu muat sumber penilaian.</p>}
  </section>
}
