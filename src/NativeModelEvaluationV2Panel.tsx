import {useCallback,useEffect,useRef,useState} from 'react'
import {normalizeClientError} from './lib/clientError'
import {formatReceiptDecimal} from './procurementContract'
import {formatCp6WibDateTime} from './cp6BusinessTime'
import {isDefiniteInitialRejection,productionLockManager,productionLockName,readProductionRecovery,hasProductionPending} from './productionRecovery'
import {readModelRequest,modelRequestKey} from './nativeModelEvaluation'
import {readModelPolicyRequest,modelPolicyRequestKey} from './nativeModelPolicy'
import {modelV2Method,captureModelV2,readModelV2,persistModelV2Request,readModelV2Request,clearModelV2Request,modelV2RequestKey,type ModelV2Request,type ModelV2Run} from './nativeModelEvaluationV2'

type Props={client:unknown;scope:string;actor:string;historyRunId:string;targetKey:string;disabled:boolean;onSourceReadStart:()=>void;onSourceReadEnd:()=>void;onAccessLost:(message:string)=>void;onBlockingChange:(blocked:boolean)=>void}
const names:Record<string,string>={'mean-1':'Rata-rata','naive-1':'Nilai terakhir','moving-mean-7-1':'Rata-rata 7 hari','ses-half-1':'Pemulusan sederhana','holt-damped-1':'Tren teredam','seasonal-7-1':'Pola 7 hari','sba-half-1':'Permintaan jarang · SBA','tsb-half-1':'Permintaan jarang · TSB'}
const reasons:Record<string,string>={EXPLICIT_ACTIVATION_POLICY_REQUIRED:'Belum ada kebijakan penggunaan model yang ditinjau.',ACTIVATION_POLICY_SUSPENDED:'Kebijakan penggunaan model telah dicabut.',NO_EXPLICITLY_ALLOWED_CHALLENGER:'Kebijakan tidak mengizinkan model pembanding.',ACTIVATION_POLICY_CHANGED:'Kebijakan sudah berubah sejak evaluasi ini disimpan.',NATIVE_HISTORY_SOURCE_CHANGED:'Data sumber berubah sejak evaluasi ini disimpan.',MODEL_ENGINE_CHANGED:'Versi perhitungan sudah berubah sejak evaluasi ini disimpan.',MODEL_FORECAST_ORIGIN_NOT_CURRENT:'Tanggal awal ramalan sudah lewat atau belum sesuai hari ini.',CURRENT_CLOCK_PRECEDES_EVALUATION:'Waktu pemeriksaan mendahului waktu evaluasi. Periksa kembali.',REGISTRY_NOT_KNOWN_BEFORE_VALIDATION:'Kebijakan belum tersedia pada waktu pengujian riwayat. Hasil lama tidak membuktikan model memenuhi kebijakan baru.',INSUFFICIENT_CHRONOLOGICAL_HISTORY:'Riwayat belum cukup untuk pembandingan dan periode uji terakhir yang terpisah.',HISTORICAL_NATIVE_KNOWLEDGE_INSUFFICIENT:'Snapshot yang sudah diketahui pada waktu keputusan belum cukup.',BASELINE_RETAINED_BY_PAIRED_PROMOTION_GUARDS:'Model pembanding belum melewati syarat perbaikan kesalahan dan bias.',CURRENT_NATIVE_SOURCE_POLICY_ENGINE_AND_DATED_ADMISSION:'Bukti, kebijakan, dan tanggal ramalan sesuai saat diperiksa.'}
const number=(v:string|null)=>v===null?'Belum diketahui':formatReceiptDecimal(v)
const dated=(start:string,i:number)=>new Date(Date.parse(start)+i*86400000).toISOString().slice(0,10)
export default function NativeModelEvaluationV2Panel({client,scope,actor,historyRunId,targetKey,disabled,onSourceReadStart,onSourceReadEnd,onAccessLost,onBlockingChange}:Props){
 const seq=useRef(0),active=useRef(false)
 const[held,setHeld]=useState(()=>readModelV2Request(scope,actor)),[horizon,setHorizon]=useState(()=>readModelV2Request(scope,actor).pending?.query.horizon_days??''),[data,setData]=useState<ModelV2Run|null>(null),[busy,setBusy]=useState(false),[error,setError]=useState('')
 const retire=useCallback(()=>{++seq.current;setData(null);setBusy(false);const wasActive=active.current;active.current=false;if(!wasActive)onSourceReadStart();onSourceReadEnd()},[onSourceReadStart,onSourceReadEnd])
 const report=(e:unknown)=>{const f=normalizeClientError(e);setData(null);setError(f.message);if(f.code==='FORBIDDEN'||f.code==='AUTH_REQUIRED')onAccessLost(f.message)}
 useEffect(()=>{onBlockingChange(busy||Boolean(held.pending||held.error))},[busy,held,onBlockingChange])
 useEffect(()=>()=>{++seq.current;if(active.current){active.current=false;onSourceReadEnd()}},[onSourceReadEnd])
 useEffect(()=>{++seq.current;setData(null);setError('');if(active.current){active.current=false;setBusy(false);onSourceReadEnd()}},[historyRunId,targetKey,onSourceReadEnd])
 useEffect(()=>{const changed=(e:StorageEvent)=>{if(e.key===null||[modelV2RequestKey(scope),modelRequestKey(scope),modelPolicyRequestKey(scope)].includes(e.key)){retire();setHeld(readModelV2Request(scope,actor));setError('Catatan berubah di tab lain. Periksa permintaan yang tersimpan sebelum melanjutkan.')}};addEventListener('storage',changed);return()=>removeEventListener('storage',changed)},[scope,actor,retire])
 const begin=()=>{const n=++seq.current;active.current=true;setData(null);setError('');setBusy(true);onSourceReadStart();return n}
 const end=(n:number)=>{if(n===seq.current){active.current=false;setBusy(false);setHeld(readModelV2Request(scope,actor));onSourceReadEnd()}}
 const capture=async(retry=false)=>{
  if(disabled||busy||active.current)return
  const n=begin()
  try{const locks=productionLockManager();if(!locks)throw Error('Peramban belum mendukung penguncian permintaan. Gunakan peramban yang mendukung sebelum menyimpan evaluasi.')
   await locks.request(productionLockName(scope),{ifAvailable:true},async lock=>{
    if(!lock)throw Error('Ada penyimpanan lain yang berjalan. Tunggu selesai, lalu periksa lagi.');if(n!==seq.current)return
    const other=readProductionRecovery(scope);if(other.corrupted||hasProductionPending(other))throw Error('Pastikan hasil transaksi lain terlebih dahulu.')
    const policy=readModelPolicyRequest(scope,actor);if(policy.pending||policy.error)throw Error('Pastikan hasil perubahan kebijakan terlebih dahulu.')
    const old=readModelV2Request(scope,actor);if(old.error)throw Error(old.error)
    let request:ModelV2Request
    if(retry){if(!old.pending)throw Error('Permintaan evaluasi tersimpan tidak tersedia.');request=old.pending}
    else{const legacy=readModelRequest(scope);if(old.pending||legacy.pending||legacy.error)throw Error('Pastikan hasil evaluasi sebelumnya terlebih dahulu.');request={requestId:crypto.randomUUID(),actor,method:modelV2Method,query:{history_run_id:historyRunId,target_key:targetKey,horizon_days:horizon}};persistModelV2Request(scope,request)}
    setHeld(readModelV2Request(scope,actor))
    try{const next=await captureModelV2(client,request);if(n!==seq.current)return;clearModelV2Request(scope,request);setHeld(readModelV2Request(scope,actor));setData(next)}
    catch(e){if(n!==seq.current)return;if(!retry&&isDefiniteInitialRejection(e)){clearModelV2Request(scope,request);setHeld(readModelV2Request(scope,actor))}throw e}
   })
  }catch(e){if(n===seq.current)report(e)}finally{end(n)}
 }
 const check=async()=>{if(!data||disabled||busy||active.current)return;const old=data,n=begin();try{const next=await readModelV2(client,old);if(n===seq.current)setData(next)}catch(e){if(n===seq.current)report(e)}finally{end(n)}}
 const blocked=disabled||busy||Boolean(held.pending||held.error)
 return<section className="native-analysis panel" aria-label="Evaluasi sesuai kebijakan">
  <h3>Bandingkan sesuai kebijakan</h3><p>Gunakan syarat yang sudah tersedia ketika snapshot diambil. Setiap evaluasi disimpan sebagai arsip; kelayakannya diperiksa kembali terhadap data, kebijakan, dan tanggal saat ini.</p>
  <form onSubmit={e=>{e.preventDefault();void capture()}}><label>Hari ramalan sesuai kebijakan<input aria-label="Hari ramalan sesuai kebijakan" type="number" min="1" max="90" step="1" required value={horizon} disabled={blocked} onChange={e=>{setData(null);setHorizon(e.target.value)}}/></label><button disabled={blocked||!/^([1-9]|[1-8][0-9]|90)$/.test(horizon)}>Simpan evaluasi sesuai kebijakan</button></form>
  {busy?<p role="status">Memeriksa sumber dan kebijakan evaluasi…</p>:null}{error||held.error?<p role="alert">{error||held.error}</p>:null}
  {held.pending?<div role="status"><p>Hasil evaluasi sebelumnya belum dipastikan. Identitas dan isi permintaan yang sama tetap disimpan.</p><button disabled={disabled||busy} onClick={()=>void capture(true)}>Periksa hasil evaluasi yang sama</button></div>:null}
  {data?<div className="native-model-result"><h4>{data.sku} · {data.name}</h4>
   <p>{data.eligibleNow?'Model memenuhi syarat saat diperiksa.':'Gunakan metode dasar; model pembanding belum layak dipakai saat ini.'} {reasons[data.reason]??'Bukti belum memenuhi seluruh syarat penggunaan model. Periksa riwayat dan kebijakan yang berlaku.'}</p>
   <p>{data.sourceState==='UNCHANGED'?'Sumber sesuai saat diperiksa.':'Arsip: sumber, kebijakan, versi perhitungan, atau tanggal telah berubah.'} Diperiksa {formatCp6WibDateTime(data.checkedAt)}.</p>
   <p>Riwayat {data.from} sampai {data.through}; diketahui {formatCp6WibDateTime(data.knownAt)}. {data.policy?`Kebijakan revisi ${data.policy.policy.revision}, dicatat ${formatCp6WibDateTime(data.registryAt)}.`:'Belum ada kebijakan penggunaan model pada snapshot ini.'}</p>
   <p>Rata-rata dasar pada hari tersedia: {number(data.mean)} PCS/hari. Model terpilih dalam arsip: {names[data.selected]}. {data.admittedAtCapture?'Model memenuhi syarat ketika evaluasi disimpan.':'Model belum memenuhi syarat ketika evaluasi disimpan.'}</p>
   <button disabled={disabled||busy} onClick={()=>void check()}>Periksa kelayakan arsip saat ini</button>
   {data.scores.length?<div className="responsive-table"><table><thead><tr><th>Model</th><th>Putaran lengkap</th><th>Kesalahan rata-rata</th><th>Bias</th><th>Kesalahan periode</th><th>Uji terakhir</th></tr></thead><tbody>{data.scores.map(s=><tr key={s.id}><td>{names[s.id]}</td><td data-label="Putaran lengkap">{s.complete}/{s.requested}</td><td data-label="Kesalahan rata-rata">{number(s.mae)}</td><td data-label="Bias">{number(s.bias)}</td><td data-label="Kesalahan periode">{number(s.tail)}</td><td data-label="Uji terakhir">{number(s.holdoutMae)}</td></tr>)}</tbody></table></div>:<p>Belum ada hasil pembandingan yang lengkap. Nilai yang belum diketahui tidak dianggap nol.</p>}
   {data.forecasts?<><p>Ramalan dalam arsip berikut {data.eligibleNow?'masih memenuhi syarat saat diperiksa':'tidak boleh dipakai sebagai ramalan aktif'}. Periode uji terakhir tidak digunakan untuk memilih model.</p><div className="responsive-table"><table><thead><tr><th>Tanggal</th><th>Ramalan arsip (PCS)</th></tr></thead><tbody>{data.forecasts.map((v,i)=><tr key={i}><td>{dated(data.forecastFrom,i)}</td><td data-label="Ramalan arsip (PCS)">{number(v)}</td></tr>)}</tbody></table></div></>:null}
   <p>Evaluasi ini belum diterapkan pada target produksi.</p>
  </div>:null}
 </section>
}
