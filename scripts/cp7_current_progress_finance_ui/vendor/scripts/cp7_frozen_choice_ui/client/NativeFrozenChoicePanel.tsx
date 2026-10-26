import {useCallback,useEffect,useId,useRef,useState} from 'react'
import {normalizeClientError} from '../../../src/lib/clientError'
import {formatCp6WibDateTime} from '../../../src/cp6BusinessTime'
import type {AnalogReadContext,AnalogCandidates} from '../../../src/nativeProductAnalog'
import {readProductAnalogChoice,saveProductAnalogChoice,prepareAnalogConfirmation,prepareAnalogClear,readAnalogChoiceRequest,persistAnalogChoiceRequest,clearAnalogChoiceRequest,analogChoiceRequestKey,type AnalogChoiceWorkspace} from '../../cp7_frozen_analysis_choice_v2/client/nativeFrozenChoice'

type Props={client:unknown;context:AnalogReadContext;candidates:AnalogCandidates|null;scope:string;canManage:boolean;onAccessLost:(message:string)=>void}
// Retire held replies when identity, access, snapshot or displayed page changes.
export default function NativeFrozenChoicePanel(props:Props){
 if(props.context.sourceMethod!=='FROZEN_V2')return null
 const c=props.candidates
 return <Workspace {...props} key={JSON.stringify([props.scope,props.context,props.canManage,c?.sourceMethod,c?.producerHash,c?.sourceHash,c?.historyHash,c?.offset])}/>
}
function Workspace({client,context,candidates,scope,canManage,onAccessLost}:Props){
 const selectId=useId(),seq=useRef(0),active=useRef(false)
 const[workspace,setWorkspace]=useState<AnalogChoiceWorkspace|null>(null),[busy,setBusy]=useState(false),[error,setError]=useState(''),[notice,setNotice]=useState('')
 const[held,setHeld]=useState(()=>readAnalogChoiceRequest(scope,context.actor,context.targetKey))
 const[selected,setSelected]=useState(''),[scale,setScale]=useState(''),[reason,setReason]=useState(''),[reviewed,setReviewed]=useState(false)
 const report=useCallback((e:unknown)=>{
  const f=normalizeClientError(e);setError(f.message)
  if(f.code==='FORBIDDEN'||f.code==='AUTH_REQUIRED'){
   setWorkspace(null);setSelected('');setScale('');setReason('');setReviewed(false);setNotice('');onAccessLost(f.message)
  }
 },[onAccessLost])
 const refresh=useCallback(async()=>{
  if(active.current)return
  const n=++seq.current;active.current=true;setBusy(true);setError('');setWorkspace(null)
  try{const w=await readProductAnalogChoice(client,context.actor,context.targetKey);if(n===seq.current)setWorkspace(w)}
  catch(e){if(n===seq.current)report(e)}finally{if(n===seq.current){active.current=false;setBusy(false)}}
 },[client,context.actor,context.targetKey,report])
 useEffect(()=>{void refresh();return()=>{++seq.current;active.current=false}},[refresh])
 useEffect(()=>{
  const changed=(event:StorageEvent)=>{if(event.key===null||event.key===analogChoiceRequestKey(scope,context.actor,context.targetKey)){
   ++seq.current;active.current=false;setWorkspace(null);setBusy(false);setReviewed(false);setNotice('');setHeld(readAnalogChoiceRequest(scope,context.actor,context.targetKey));setError('Catatan konfirmasi berubah di tab lain. Baca ulang pilihan dan periksa permintaan tersimpan.')
  }}
  addEventListener('storage',changed);return()=>removeEventListener('storage',changed)
 },[scope,context.actor,context.targetKey])
 const send=async(action:'CONFIRM'|'CLEAR'|'RETRY')=>{
  if(active.current||!canManage)return
  const n=++seq.current;active.current=true;setBusy(true);setError('');setNotice('')
  try{
   const old=readAnalogChoiceRequest(scope,context.actor,context.targetKey);if(old.error)throw Error(old.error)
   if(action==='RETRY'&&!old.pending||action!=='RETRY'&&old.pending)throw Error('Periksa permintaan konfirmasi tersimpan yang sama terlebih dahulu.')
   if(action!=='RETRY'&&!workspace)throw Error('Baca ulang pilihan tersimpan terlebih dahulu.')
   if(action==='CONFIRM'&&!candidates)throw Error('Baca kandidat pembanding terlebih dahulu.')
   const command=action==='RETRY'?old.pending!:action==='CLEAR'?prepareAnalogClear(workspace!,reason,reviewed,crypto.randomUUID()):prepareAnalogConfirmation(context,candidates!,workspace!,selected,scale,reason,reviewed,crypto.randomUUID())
   if(action!=='RETRY')await persistAnalogChoiceRequest(scope,command)
   if(n!==seq.current)return
   setHeld(readAnalogChoiceRequest(scope,context.actor,context.targetKey))
   const saved=await saveProductAnalogChoice(client,scope,context.actor,context.targetKey)
   if(n!==seq.current)return
   await clearAnalogChoiceRequest(scope,command)
   if(n!==seq.current)return
   setHeld(readAnalogChoiceRequest(scope,context.actor,context.targetKey));setWorkspace(null);setReviewed(false)
   setNotice(`Bukti ${saved.action==='CLEAR'?'pencabutan':'konfirmasi'} revisi ${saved.revision} tersimpan. Hasil perhitungan lama tetap tersimpan. Buat perhitungan baru untuk memakai konfigurasi terbaru.`)
   const w=await readProductAnalogChoice(client,context.actor,context.targetKey)
   if(n===seq.current)setWorkspace(w)
  }catch(e){if(n===seq.current){setHeld(readAnalogChoiceRequest(scope,context.actor,context.targetKey));report(e)}}
  finally{if(n===seq.current){active.current=false;setBusy(false)}}
 }
 const locked=busy||Boolean(held.pending)||Boolean(held.error)||!canManage,choice=workspace?.choice
 return <section className="native-analog-choice" aria-label="Konfirmasi produk pembanding">
  <h5>Pilihan pembanding tersimpan</h5>
  <p>{'Pilihan ini menyimpan asumsi dan alasan pemeriksaan. Pilihan yang memenuhi syarat dipakai pada perhitungan baru ketika riwayat produk sendiri belum cukup.'}</p>
  {busy?<p role="status">Memeriksa konfirmasi pembanding…</p>:null}
  {notice?<p role="status">{notice}</p>:null}
  {error||held.error?<p role="alert">{error||held.error}</p>:null}
  {held.pending?<><p>Hasil permintaan tersimpan belum dipastikan. Periksa permintaan yang sama sebelum membuat perubahan lain.</p><button disabled={busy||!canManage} onClick={()=>void send('RETRY')}>Periksa hasil konfirmasi yang sama</button></>:null}
  <button disabled={busy} onClick={()=>void refresh()}>Baca ulang pilihan tersimpan</button>
  {choice?<p>{choice.state==='UNREVIEWED'?'Belum ada pilihan yang dikonfirmasi.':choice.state==='CLEARED'?`Pilihan dicabut pada revisi ${choice.revision}.`:`Pembanding ${choice.evidence!.sourceSku} · ${choice.evidence!.sourceName}, revisi ${choice.revision}, skala ${choice.evidence!.scale}.`} {choice.recordedAt?`Dicatat ${formatCp6WibDateTime(choice.recordedAt)}.`:''} {choice.reason?`Alasan: ${choice.reason}`:''}</p>:null}
  {!canManage?<p>Izin mengelola produk diperlukan untuk mengubah pilihan.</p>:null}
  <fieldset disabled={locked||!workspace}>
   <legend>Pemeriksaan pilihan</legend>
   <label htmlFor={selectId}>Produk pembanding</label><select id={selectId} value={candidates?.rows.some(r=>r.key===selected)?selected:''} onChange={e=>{setSelected(e.target.value);setReviewed(false)}}><option value="">Pilih setelah memeriksa kandidat</option>{candidates?.rows.map(r=><option key={r.key} value={r.key}>{r.sku} · {r.name}</option>)}</select>
   <label htmlFor={selectId+'-scale'}>Skala terhadap produk pembanding</label><input id={selectId+'-scale'} inputMode="decimal" value={scale} onChange={e=>{setScale(e.target.value);setReviewed(false)}}/>
   <p>Skala 1 berarti sama, 0.5 berarti setengah. Isi skala sesuai pemeriksaan Anda.</p>
   <label htmlFor={selectId+'-reason'}>Alasan kesamaan atau pencabutan</label><textarea id={selectId+'-reason'} value={reason} onChange={e=>{setReason(e.target.value);setReviewed(false)}}/>
   <label className="native-analog-review"><input type="checkbox" checked={reviewed} onChange={e=>setReviewed(e.target.checked)}/>Saya telah memeriksa kesesuaian ukuran, model, kain, pola, dan riwayat penjualan serta alasan perubahan ini.</label>
   <button disabled={!reviewed||!selected||!candidates?.rows.some(r=>r.key===selected)||!scale.trim()||!reason.trim()||workspace?.accessEpoch!==context.accessEpoch} onClick={()=>void send('CONFIRM')}>Simpan pilihan pembanding</button>
   <button disabled={!reviewed||!reason.trim()||!choice||choice.revision==='0'} onClick={()=>void send('CLEAR')}>Cabut pilihan pembanding</button>
  </fieldset>
 </section>
}
