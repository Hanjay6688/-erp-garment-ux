import {useCallback,useEffect,useRef,useState} from 'react'
import {normalizeClientError} from './lib/clientError'
import {formatCp6WibDateTime} from './cp6BusinessTime'
import {isDefiniteInitialRejection,productionLockManager,productionLockName,readProductionRecovery,hasProductionPending} from './productionRecovery'
import type {AnalogReadContext,AnalogCandidates} from './nativeProductAnalog'
import {readProductAnalogChoice,saveProductAnalogChoice,prepareAnalogConfirmation,prepareAnalogClear,readAnalogChoiceRequest,persistAnalogChoiceRequest,clearAnalogChoiceRequest,analogChoiceRequestKey,type AnalogChoiceWorkspace,type PreparedAnalogChoice} from './nativeProductAnalogChoice'

type Props={client:unknown;context:AnalogReadContext;candidates:AnalogCandidates|null;scope:string;canManage:boolean;onAccessLost:(message:string)=>void}
export default function NativeProductAnalogChoicePanel({client,context,candidates,scope,canManage,onAccessLost}:Props){
 const seq=useRef(0),active=useRef(false)
 const[workspace,setWorkspace]=useState<AnalogChoiceWorkspace|null>(null),[busy,setBusy]=useState(false),[error,setError]=useState(''),[notice,setNotice]=useState('')
 const[held,setHeld]=useState(()=>readAnalogChoiceRequest(scope,context.actor,context.targetKey))
 const[selected,setSelected]=useState(''),[scale,setScale]=useState(''),[reason,setReason]=useState(''),[reviewed,setReviewed]=useState(false)
 const report=useCallback((e:unknown)=>{const f=normalizeClientError(e);setError(f.message);if(f.code==='FORBIDDEN'||f.code==='AUTH_REQUIRED')onAccessLost(f.message)},[onAccessLost])
 const refresh=useCallback(async()=>{
  if(active.current)return
  const n=++seq.current;setBusy(true);setError('');setWorkspace(null)
  try{const w=await readProductAnalogChoice(client,context.actor,context.targetKey);if(n===seq.current)setWorkspace(w)}
  catch(e){if(n===seq.current)report(e)}finally{if(n===seq.current)setBusy(false)}
 },[client,context.actor,context.targetKey,report])
 useEffect(()=>{void refresh();return()=>{++seq.current}},[refresh])
 useEffect(()=>{
  const changed=(event:StorageEvent)=>{if(event.key===null||event.key===analogChoiceRequestKey(scope,context.targetKey)){
   ++seq.current;setWorkspace(null);setBusy(false);setHeld(readAnalogChoiceRequest(scope,context.actor,context.targetKey));setError('Catatan konfirmasi berubah di tab lain. Baca ulang pilihan dan periksa permintaan tersimpan.')
  }}
  addEventListener('storage',changed);return()=>removeEventListener('storage',changed)
 },[scope,context.actor,context.targetKey])
 const send=async(action:'CONFIRM'|'CLEAR'|'RETRY')=>{
  if(active.current||busy||!canManage)return
  const n=++seq.current;active.current=true;setBusy(true);setError('');setNotice('')
  try{
   const locks=productionLockManager();if(!locks)throw Error('Peramban belum mendukung penguncian penyimpanan. Gunakan peramban yang mendukung sebelum mengonfirmasi.')
   await locks.request(productionLockName(scope),{ifAvailable:true},async lock=>{
    if(!lock)throw Error('Ada penyimpanan lain di tab ini atau tab lain. Tunggu selesai lalu periksa lagi.')
    if(n!==seq.current)return
    const other=readProductionRecovery(scope);if(other.corrupted||hasProductionPending(other))throw Error('Pastikan hasil transaksi lain terlebih dahulu sebelum mengonfirmasi pembanding.')
    const old=readAnalogChoiceRequest(scope,context.actor,context.targetKey);if(old.error)throw Error(old.error)
    let command:PreparedAnalogChoice
    if(action==='RETRY'){if(!old.pending)throw Error('Permintaan konfirmasi tersimpan tidak tersedia.');command=old.pending}
    else{
     if(old.pending||!workspace)throw Error('Periksa pilihan tersimpan terlebih dahulu.')
     if(action==='CONFIRM'){if(!candidates)throw Error('Baca kandidat pembanding terlebih dahulu.');command=prepareAnalogConfirmation(context,candidates,workspace,selected,scale,reason,reviewed,crypto.randomUUID())}
     else command=prepareAnalogClear(workspace,reason,reviewed,crypto.randomUUID())
     persistAnalogChoiceRequest(scope,command)
    }
    setHeld(readAnalogChoiceRequest(scope,context.actor,context.targetKey))
    try{
     const saved=await saveProductAnalogChoice(client,command);if(n!==seq.current)return
     clearAnalogChoiceRequest(scope,command);setHeld(readAnalogChoiceRequest(scope,context.actor,context.targetKey));setWorkspace(null);setReviewed(false)
     setNotice(`Bukti ${saved.action==='CLEAR'?'pencabutan':'konfirmasi'} revisi ${saved.revision} tersimpan. Perhitungan target belum memakai pilihan ini.`)
    }catch(e){
     if(n!==seq.current)return
     if(action!=='RETRY'&&isDefiniteInitialRejection(e)){clearAnalogChoiceRequest(scope,command);setHeld(readAnalogChoiceRequest(scope,context.actor,context.targetKey));setWorkspace(null)}
     throw e
    }
    try{const w=await readProductAnalogChoice(client,context.actor,context.targetKey);if(n===seq.current)setWorkspace(w)}catch(e){if(n===seq.current)report(e)}
   })
  }catch(e){if(n===seq.current)report(e)}finally{active.current=false;if(n===seq.current){setBusy(false);setHeld(readAnalogChoiceRequest(scope,context.actor,context.targetKey))}}
 }
 const locked=busy||Boolean(held.pending)||Boolean(held.error)||!canManage,choice=workspace?.choice
 return <section aria-label="Konfirmasi produk pembanding">
  <h5>Pilihan pembanding tersimpan</h5>
  <p>Pilihan ini menyimpan asumsi dan alasan pemeriksaan. Target produksi belum berubah.</p>
  {busy?<p role="status">Memeriksa konfirmasi pembanding…</p>:null}
  {notice?<p role="status">{notice}</p>:null}
  {error||held.error?<p role="alert">{error||held.error}</p>:null}
  {held.pending?<><p>Hasil permintaan tersimpan belum dipastikan. Periksa permintaan yang sama sebelum membuat perubahan lain.</p><button disabled={busy||!canManage} onClick={()=>void send('RETRY')}>Periksa hasil konfirmasi yang sama</button></>:null}
  <button disabled={busy} onClick={()=>void refresh()}>Baca ulang pilihan tersimpan</button>
  {choice?<p>{choice.state==='UNREVIEWED'?'Belum ada pilihan yang dikonfirmasi.':choice.state==='CLEARED'?`Pilihan dicabut pada revisi ${choice.revision}.`:`Pilihan dikonfirmasi pada revisi ${choice.revision}, skala ${choice.evidence!.scale}.`} {choice.recordedAt?`Dicatat ${formatCp6WibDateTime(choice.recordedAt)}.`:''} {choice.reason?`Alasan: ${choice.reason}`:''}</p>:null}
  {!canManage?<p>Izin mengelola produk diperlukan untuk mengubah pilihan.</p>:null}
  <fieldset disabled={locked||!workspace}>
   <legend>Pemeriksaan pilihan</legend>
   <label>Produk pembanding<select value={candidates?.rows.some(r=>r.key===selected)?selected:''} onChange={e=>{setSelected(e.target.value);setReviewed(false)}}><option value="">Pilih setelah memeriksa kandidat</option>{candidates?.rows.map(r=><option key={r.key} value={r.key}>{r.sku} · {r.name}</option>)}</select></label>
   <label>Skala terhadap produk pembanding<input inputMode="decimal" value={scale} onChange={e=>{setScale(e.target.value);setReviewed(false)}}/></label>
   <p>Skala 1 berarti sama, 0.5 berarti setengah. Isi skala sesuai pemeriksaan Anda.</p>
   <label>Alasan kesamaan atau pencabutan<textarea value={reason} onChange={e=>{setReason(e.target.value);setReviewed(false)}}/></label>
   <label><input type="checkbox" checked={reviewed} onChange={e=>setReviewed(e.target.checked)}/>Saya telah memeriksa kesesuaian ukuran, model, kain, pola, dan riwayat penjualan serta alasan perubahan ini.</label>
   <button disabled={!reviewed||!selected||!candidates?.rows.some(r=>r.key===selected)||!scale.trim()||!reason.trim()||workspace?.accessEpoch!==context.accessEpoch} onClick={()=>void send('CONFIRM')}>Simpan pilihan pembanding</button>
   <button disabled={!reviewed||!reason.trim()||!choice||choice.revision==='0'} onClick={()=>void send('CLEAR')}>Cabut pilihan pembanding</button>
  </fieldset>
 </section>
}
