import {useCallback,useEffect,useId,useRef,useState} from 'react'
import {normalizeClientError} from './lib/clientError'
import {formatCp6WibDateTime} from './cp6BusinessTime'
import {isDefiniteInitialRejection,productionLockManager,productionLockName,readProductionRecovery,hasProductionPending} from './productionRecovery'
import {modelMethods,parseModelPolicyConfig,prepareModelPolicy,readModelPolicy,saveModelPolicy,readModelPolicyRequest,persistModelPolicyRequest,clearModelPolicyRequest,modelPolicyRequestKey,type ModelMethod,type ModelPolicyConfig,type ModelPolicyWorkspace,type PreparedModelPolicy} from './nativeModelPolicy'

type Props={client:unknown;scope:string;actor:string;canManage:boolean;onAccessLost:(message:string)=>void}
const methodNames:Record<ModelMethod,string>={NAIVE:'Nilai terakhir',MOVING_MEAN:'Rata-rata 7 hari',SES:'Pemulusan sederhana (α 0,5)',DAMPED_HOLT:'Tren teredam (α 0,5; β 0,5; φ 0,9)',SEASONAL_NAIVE:'Pola 7 hari',SBA:'Permintaan jarang SBA (α dan β 0,5)',TSB:'Permintaan jarang TSB (α dan β 0,5)'}
const fields=[['training','Minimum hari pelatihan','Hari'],['horizon','Maksimum hari ramalan','Hari'],['folds','Minimum putaran pembanding lengkap','Putaran'],['improvement','Minimum perbaikan kesalahan rata-rata','PCS'],['bias','Batas tambahan bias absolut','PCS'],['tail','Batas tambahan kesalahan seluruh periode','PCS'],['season','Jarak musiman untuk pembandingan','Hari']]as const
type Form=Record<typeof fields[number][0],string>
const empty:Form={training:'',horizon:'',folds:'',improvement:'',bias:'',tail:'',season:''}
function config(form:Form,methods:ModelMethod[]):ModelPolicyConfig{return parseModelPolicyConfig({minimum_training_days:form.training,maximum_horizon_days:form.horizon,allowed_methods:methods,promotion:{minimum_complete_folds:form.folds,minimum_mae_improvement:form.improvement,maximum_bias_worsening:form.bias,maximum_tail_worsening:form.tail,season_lag:form.season}})}
export default function NativeModelPolicyPanel({client,scope,actor,canManage,onAccessLost}:Props){
 const id=useId(),seq=useRef(0),active=useRef(false)
 const[w,setW]=useState<ModelPolicyWorkspace|null>(null),[busy,setBusy]=useState(false),[error,setError]=useState(''),[notice,setNotice]=useState('')
 const[held,setHeld]=useState(()=>readModelPolicyRequest(scope,actor)),[form,setForm]=useState<Form>(empty),[methods,setMethods]=useState<ModelMethod[]>([]),[reason,setReason]=useState(''),[reviewed,setReviewed]=useState(false)
 const report=useCallback((e:unknown)=>{const f=normalizeClientError(e);setError(f.message);if(f.code==='FORBIDDEN'||f.code==='AUTH_REQUIRED'){setW(null);onAccessLost(f.message)}},[onAccessLost])
 const refresh=useCallback(async()=>{if(active.current)return;const n=++seq.current;setW(null);setBusy(true);setError('');setReviewed(false)
  try{const next=await readModelPolicy(client,actor);if(n===seq.current)setW(next)}catch(e){if(n===seq.current)report(e)}finally{if(n===seq.current)setBusy(false)}
 },[client,actor,report])
 useEffect(()=>{void refresh();return()=>{++seq.current}},[refresh])
 useEffect(()=>{const changed=(event:StorageEvent)=>{if(event.key===null||event.key===modelPolicyRequestKey(scope)){++seq.current;setW(null);setBusy(false);setReviewed(false);setHeld(readModelPolicyRequest(scope,actor));setError('Catatan kebijakan berubah di tab lain. Baca ulang versi dan periksa permintaan tersimpan.')}};addEventListener('storage',changed);return()=>removeEventListener('storage',changed)},[scope,actor])
 const send=async(action:'SET'|'SUSPEND'|'RETRY')=>{
  if(busy||active.current||!canManage)return
  const n=++seq.current;active.current=true;setBusy(true);setError('');setNotice('')
  try{const locks=productionLockManager();if(!locks)throw Error('Peramban belum mendukung penguncian penyimpanan. Gunakan peramban yang mendukung sebelum menyimpan kebijakan.')
   await locks.request(productionLockName(scope),{ifAvailable:true},async lock=>{
    if(!lock)throw Error('Ada penyimpanan lain di tab ini atau tab lain. Tunggu selesai lalu periksa lagi.')
    if(n!==seq.current)return
    const other=readProductionRecovery(scope);if(other.corrupted||hasProductionPending(other))throw Error('Pastikan hasil transaksi lain terlebih dahulu sebelum menyimpan kebijakan.')
    const old=readModelPolicyRequest(scope,actor);if(old.error)throw Error(old.error)
    let command:PreparedModelPolicy
    if(action==='RETRY'){if(!old.pending)throw Error('Permintaan kebijakan tersimpan tidak tersedia.');command=old.pending}
    else{if(old.pending||!w)throw Error('Baca versi kebijakan dan periksa permintaan sebelumnya.');command=prepareModelPolicy(w,action,action==='SET'?config(form,methods):null,reason,reviewed,crypto.randomUUID());persistModelPolicyRequest(scope,command)}
    setHeld(readModelPolicyRequest(scope,actor))
    try{const saved=await saveModelPolicy(client,command);if(n!==seq.current)return
     clearModelPolicyRequest(scope,command);setHeld(readModelPolicyRequest(scope,actor));setW(null);setReviewed(false)
     setNotice(`Kebijakan revisi ${saved.revision} ${saved.state==='SUSPENDED'?'dicabut':'tersimpan'}. Riwayat sebelumnya tetap tersimpan. Pemakaian ramalan pada target belum diaktifkan.`)
    }catch(e){if(n!==seq.current)return;if(action!=='RETRY'&&isDefiniteInitialRejection(e)){clearModelPolicyRequest(scope,command);setHeld(readModelPolicyRequest(scope,actor));setW(null);setReviewed(false)}throw e}
    try{const next=await readModelPolicy(client,actor);if(n===seq.current)setW(next)}catch(e){if(n===seq.current)report(e)}
   })
  }catch(e){if(n===seq.current)report(e)}finally{active.current=false;if(n===seq.current){setBusy(false);setHeld(readModelPolicyRequest(scope,actor))}}
 }
 const useStored=()=>{const c=w?.current?.policy.config;if(!c)return;setForm({training:c.minimum_training_days,horizon:c.maximum_horizon_days,folds:c.promotion.minimum_complete_folds,improvement:c.promotion.minimum_mae_improvement,bias:c.promotion.maximum_bias_worsening,tail:c.promotion.maximum_tail_worsening,season:c.promotion.season_lag});setMethods([...c.allowed_methods]);setReviewed(false)}
 const locked=busy||Boolean(held.pending||held.error)||!canManage||!w?.canWrite,current=w?.current?.policy
 let valid=false;try{config(form,methods);valid=true}catch{/* Empty or incomplete entries stay disabled. */}
 return<section className="native-analysis panel" aria-label="Kebijakan penggunaan model">
  <h3>Syarat penggunaan model</h3><p>Tentukan syarat bukti sebelum model boleh dipakai. Kebijakan baru berlaku untuk pengujian berikutnya; hasil lama tidak dianggap sudah memenuhi kebijakan baru. Menyimpan syarat ini belum mengaktifkan ramalan pada target produksi.</p>
  {busy?<p role="status">Memeriksa kebijakan model…</p>:null}{notice?<p role="status">{notice}</p>:null}{error||held.error?<p role="alert">{error||held.error}</p>:null}
  {held.pending?<><p>Hasil permintaan sebelumnya belum dipastikan. Periksa permintaan yang sama sebelum membuat perubahan lain.</p><button disabled={busy||!canManage} onClick={()=>void send('RETRY')}>Periksa hasil kebijakan yang sama</button></>:null}
  <button disabled={busy} onClick={()=>void refresh()}>Baca ulang kebijakan</button>
  {w?<p>{current?`Kebijakan revisi ${current.revision} ${current.state==='SUSPENDED'?'dicabut':'tersimpan'}, dicatat ${formatCp6WibDateTime(current.recorded_at)}. Alasan: ${current.reason}`:'Belum ada kebijakan yang ditinjau. Semua syarat harus diisi secara eksplisit.'}</p>:null}
  {current?<dl><dt>Pelatihan / horizon</dt><dd>{current.config.minimum_training_days} hari / {current.config.maximum_horizon_days} hari</dd><dt>Putaran lengkap / jarak musiman</dt><dd>{current.config.promotion.minimum_complete_folds} putaran / {current.config.promotion.season_lag} hari</dd><dt>Perbaikan minimum / tambahan bias / tambahan kesalahan periode</dt><dd>{current.config.promotion.minimum_mae_improvement} / {current.config.promotion.maximum_bias_worsening} / {current.config.promotion.maximum_tail_worsening} PCS</dd><dt>Model yang diizinkan</dt><dd>{current.config.allowed_methods.map(m=>methodNames[m]).join('; ')||'Tidak ada model pembanding yang diizinkan.'}</dd></dl>:null}
  {!canManage||w&&!w.canWrite?<p>Owner atau admin dengan izin mengelola produk diperlukan untuk mengubah kebijakan.</p>:null}
  <fieldset disabled={locked||!w}><legend>Tinjau kebijakan berikutnya</legend>
   {current?<button onClick={useStored}>Isi dari kebijakan tersimpan</button>:null}
   {fields.map(([key,label,unit])=><label key={key} htmlFor={`${id}-${key}`}>{label} ({unit})<input id={`${id}-${key}`} inputMode={['improvement','bias','tail'].includes(key)?'decimal':'numeric'} value={form[key]} onChange={e=>{setForm({...form,[key]:e.target.value});setReviewed(false)}}/></label>)}
   <p>Gunakan titik untuk pecahan. Perbaikan kesalahan harus lebih besar dari ambang minimum. Seluruh putaran wajib lengkap; periode uji terakhir terpisah dan tidak memilih model. Rata-rata dasar tetap menjadi pembanding.</p>
   <fieldset><legend>Model pembanding yang diizinkan</legend>{modelMethods.map(m=><label key={m}><input type="checkbox" checked={methods.includes(m)} onChange={e=>{setMethods(modelMethods.filter(x=>x===m?e.target.checked:methods.includes(x)));setReviewed(false)}}/>{methodNames[m]}</label>)}<p>Tidak memilih model berarti belum mengizinkan model pembanding apa pun. Parameter tetap ditetapkan sebelum pengujian; pemulusan sederhana memakai nilai awal dari histori dan tren teredam dimulai dari tren nol.</p></fieldset>
   <label htmlFor={id+'-reason'}>Alasan kebijakan atau pencabutan<textarea id={id+'-reason'} value={reason} onChange={e=>{setReason(e.target.value);setReviewed(false)}}/></label>
   <label><input type="checkbox" checked={reviewed} onChange={e=>setReviewed(e.target.checked)}/>Saya telah meninjau syarat bukti, model yang diizinkan, parameter tetap, dan alasan perubahan ini.</label>
   <button disabled={!reviewed||!valid||!reason.trim()} onClick={()=>void send('SET')}>Simpan kebijakan yang ditinjau</button>
   <button disabled={!reviewed||!current||!reason.trim()} onClick={()=>void send('SUSPEND')}>Cabut kebijakan model</button>
  </fieldset>
 </section>
}
