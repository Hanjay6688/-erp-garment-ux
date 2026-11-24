import {useCallback,useEffect,useRef,useState} from 'react'
import {normalizeClientError} from './lib/clientError'
import {formatReceiptDecimal} from './procurementContract'
import {formatCp6WibDateTime} from './cp6BusinessTime'
import {isDefiniteInitialRejection,productionLockManager,productionLockName,readProductionRecovery,hasProductionPending} from './productionRecovery'
import {readModelRequest,modelRequestKey} from './nativeModelEvaluation'
import {readModelV2Request,modelV2RequestKey} from './nativeModelEvaluationV2'
import {readModelPolicyRequest,modelPolicyRequestKey} from './nativeModelPolicy'
import {scopedHistoryMethod,scopedModelMethod,scopedHistoryRecovery,scopedModelRecovery,captureScopedHistory,captureScopedModel,readScopedHistory,readScopedModel,type ScopedHistoryQuery,type ScopedHistoryRun,type ScopedModelRun,type ScopedHistoryRequest,type ScopedModelRequest} from './nativeScopedModel'

type Props={client:unknown;scope:string;actor:string;query:ScopedHistoryQuery|null;disabled:boolean;onSourceReadStart:()=>void;onSourceReadEnd:()=>void;onAccessLost:(message:string)=>void;onBlockingChange:(blocked:boolean)=>void;onClose:()=>void}
const names:Record<string,string>={'mean-1':'Rata-rata','naive-1':'Nilai terakhir','moving-mean-7-1':'Rata-rata 7 hari','ses-half-1':'Pemulusan sederhana','holt-damped-1':'Tren teredam','seasonal-7-1':'Pola 7 hari','sba-half-1':'Permintaan jarang · SBA','tsb-half-1':'Permintaan jarang · TSB'}
const reasons:Record<string,string>={EXPLICIT_ACTIVATION_POLICY_REQUIRED:'Belum ada kebijakan penggunaan model yang ditinjau.',ACTIVATION_POLICY_CHANGED:'Kebijakan sudah berubah sejak evaluasi disimpan.',NATIVE_HISTORY_SOURCE_CHANGED:'Sumber berubah sejak evaluasi disimpan.',MODEL_ENGINE_CHANGED:'Versi perhitungan telah berubah.',MODEL_FORECAST_ORIGIN_NOT_CURRENT:'Tanggal awal ramalan belum sesuai hari ini.',INSUFFICIENT_CHRONOLOGICAL_HISTORY:'Riwayat belum cukup untuk pembandingan dan uji terakhir yang terpisah.',HISTORICAL_NATIVE_KNOWLEDGE_INSUFFICIENT:'Snapshot yang sudah diketahui pada waktu keputusan belum cukup.',REGISTRY_NOT_KNOWN_BEFORE_VALIDATION:'Kebijakan belum tersedia pada waktu pengujian riwayat.',NO_EXPLICITLY_ALLOWED_CHALLENGER:'Kebijakan tidak mengizinkan model pembanding.'}
const number=(v:string|null)=>v===null?'Belum diketahui':formatReceiptDecimal(v)
export default function NativeScopedModelPanel({client,scope,actor,query,disabled,onSourceReadStart,onSourceReadEnd,onAccessLost,onBlockingChange,onClose}:Props){
 const seq=useRef(0),active=useRef(false)
 const [history,setHistory]=useState<ScopedHistoryRun|null>(null),[model,setModel]=useState<ScopedModelRun|null>(null)
 const [heldHistory,setHeldHistory]=useState(()=>scopedHistoryRecovery.read(scope,actor)),[heldModel,setHeldModel]=useState(()=>scopedModelRecovery.read(scope,actor))
 const [horizon,setHorizon]=useState(()=>scopedModelRecovery.read(scope,actor).pending?.query.horizon_days??''),[busy,setBusy]=useState(false),[error,setError]=useState(''),[denied,setDenied]=useState(false)
 const reload=()=>{setHeldHistory(scopedHistoryRecovery.read(scope,actor));setHeldModel(scopedModelRecovery.read(scope,actor))}
 const retire=useCallback(()=>{++seq.current;setHistory(null);setModel(null);setBusy(false);if(active.current){active.current=false;onSourceReadEnd()}},[onSourceReadEnd])
 useEffect(()=>()=>{++seq.current;if(active.current){active.current=false;onSourceReadEnd()}},[onSourceReadEnd])
 const binding=JSON.stringify(query)
 useEffect(()=>{retire();setError('')},[binding,retire])
 useEffect(()=>{onBlockingChange(busy||Boolean(heldHistory.pending||heldHistory.error||heldModel.pending||heldModel.error))},[busy,heldHistory,heldModel,onBlockingChange])
 useEffect(()=>{const changed=(e:StorageEvent)=>{if(e.key===null||[scopedHistoryRecovery.key(scope),scopedModelRecovery.key(scope),modelRequestKey(scope),modelV2RequestKey(scope),modelPolicyRequestKey(scope)].includes(e.key)){retire();setHeldHistory(scopedHistoryRecovery.read(scope,actor));setHeldModel(scopedModelRecovery.read(scope,actor));setError('Catatan berubah di tab lain. Periksa permintaan tersimpan sebelum melanjutkan.')}};addEventListener('storage',changed);return()=>removeEventListener('storage',changed)},[scope,actor,retire])
 const report=(e:unknown)=>{const f=normalizeClientError(e);setHistory(null);setModel(null);setError(f.message);if(f.code==='FORBIDDEN'||f.code==='AUTH_REQUIRED'){setDenied(true);onAccessLost(f.message)}}
 const begin=()=>{const n=++seq.current;active.current=true;setBusy(true);setError('');setModel(null);onSourceReadStart();return n}
 const end=(n:number)=>{if(n===seq.current){active.current=false;setBusy(false);reload();onSourceReadEnd()}}
 const requireOtherRequests=()=>{
  const p=readProductionRecovery(scope),v1=readModelRequest(scope),v2=readModelV2Request(scope,actor),policy=readModelPolicyRequest(scope,actor)
  if(p.corrupted||hasProductionPending(p)||v1.pending||v1.error||v2.pending||v2.error||policy.pending||policy.error)throw Error('Pastikan hasil transaksi, evaluasi, atau kebijakan sebelumnya terlebih dahulu.')
 }
 const save=async(kind:'history'|'model',retry=false)=>{
  if(disabled||busy||active.current||denied)return
  const n=begin()
  try{const locks=productionLockManager();if(!locks)throw Error('Peramban belum mendukung penguncian permintaan. Gunakan peramban yang mendukung sebelum menyimpan.')
   await locks.request(productionLockName(scope),{ifAvailable:true},async lock=>{
    if(!lock)throw Error('Ada penyimpanan lain yang berjalan. Tunggu selesai, lalu periksa lagi.');if(n!==seq.current)return
    requireOtherRequests()
    const h=scopedHistoryRecovery.read(scope,actor),m=scopedModelRecovery.read(scope,actor)
    if(h.error||m.error)throw Error(h.error||m.error)
    if(kind==='history'){
     if(m.pending)throw Error('Pastikan evaluasi yang tersimpan terlebih dahulu.')
     let request:ScopedHistoryRequest
     if(retry){if(!h.pending)throw Error('Permintaan riwayat tersimpan tidak tersedia.');request=h.pending}
     else{if(h.pending||!query)throw Error('Pilih produk dan pastikan permintaan sebelumnya.');request={requestId:crypto.randomUUID(),actor,method:scopedHistoryMethod,query};scopedHistoryRecovery.persist(scope,request)}
     reload();setHistory(null)
     try{const result=await captureScopedHistory(client,request);if(n!==seq.current)return;scopedHistoryRecovery.clear(scope,request);setHistory(result)}
     catch(e){if(n!==seq.current)return;if(!retry&&isDefiniteInitialRejection(e))scopedHistoryRecovery.clear(scope,request);throw e}
    }else{
     if(h.pending)throw Error('Pastikan riwayat produk yang tersimpan terlebih dahulu.')
     let request:ScopedModelRequest
     if(retry){if(!m.pending)throw Error('Permintaan evaluasi tersimpan tidak tersedia.');request=m.pending}
     else{if(m.pending||!history||history.history.state!=='UNCHANGED')throw Error('Ambil riwayat produk yang sesuai sumber saat ini.');request={requestId:crypto.randomUUID(),actor,method:scopedModelMethod,query:{history_run_id:history.runId,target_key:history.query.target_key,horizon_days:horizon}};scopedModelRecovery.persist(scope,request)}
     reload()
     try{const result=await captureScopedModel(client,request);if(n!==seq.current)return;scopedModelRecovery.clear(scope,request);setModel(result)}
     catch(e){if(n!==seq.current)return;if(!retry&&isDefiniteInitialRejection(e))scopedModelRecovery.clear(scope,request);throw e}
    }
   })
  }catch(e){if(n===seq.current)report(e)}finally{end(n)}
 }
 const check=async()=>{
  if(disabled||busy||active.current||denied||!history&&!model)return
  const oldHistory=history,oldModel=model,n=begin();setHistory(null)
  try{if(oldModel){const next=await readScopedModel(client,oldModel);if(n===seq.current)setModel(next)}
   else if(oldHistory){const next=await readScopedHistory(client,oldHistory);if(n===seq.current)setHistory(next)}
  }catch(e){if(n===seq.current)report(e)}finally{end(n)}
 }
 const queryTooLong=query!==null&&(Date.parse(query.through_date)-Date.parse(query.from_date))/86400000>365
 const pending=Boolean(heldHistory.pending||heldHistory.error||heldModel.pending||heldModel.error),blocked=disabled||busy||denied||pending,row=history?.history.rows[0]
 return <section className="native-analysis panel" aria-label="Riwayat dan model per produk">
  <header><h3>Riwayat dan model per produk</h3><button disabled={busy||pending} onClick={onClose}>Tutup riwayat dan model</button></header>
  <p>Simpan riwayat produk yang dipilih, lalu bandingkan model sesuai kebijakan yang sudah tersedia saat riwayat diambil. Hari dengan stok habis atau data belum diketahui tidak dianggap nol.</p>
  {queryTooLong?<p role="alert">Model memakai paling banyak 366 hari. Pilih periode analisis yang lebih pendek sebelum menyimpan riwayat.</p>:null}
  {query?<p>Periode {query.from_date} sampai {query.through_date}. Waktu diketahui mengikuti pencatatan server saat ini.</p>:null}
  <button disabled={blocked||!query||queryTooLong} onClick={()=>void save('history')}>Simpan riwayat produk saat ini</button>
  {busy?<p role="status">Memeriksa sumber produk, izin, dan kebijakan…</p>:null}
  {error||heldHistory.error||heldModel.error?<p role="alert">{error||heldHistory.error||heldModel.error}</p>:null}
  {heldHistory.pending?<div role="status"><p>Hasil penyimpanan riwayat belum dipastikan. Isi dan identitas permintaan tetap disimpan.</p><button disabled={disabled||busy||denied} onClick={()=>void save('history',true)}>Periksa riwayat yang sama</button></div>:null}
  {heldModel.pending?<div role="status"><p>Hasil evaluasi produk belum dipastikan. Periksa permintaan yang sama sebelum membuat evaluasi baru.</p><button disabled={disabled||busy||denied} onClick={()=>void save('model',true)}>Periksa evaluasi produk yang sama</button></div>:null}
  {row&&history?<div><h4>{row.sku} · {row.productName}</h4><p>{history.history.state==='UNCHANGED'?'Sumber sesuai saat diperiksa.':'Arsip: sumber produk telah berubah. Ambil riwayat baru.'} Diketahui {formatCp6WibDateTime(history.history.capturedAt)}; diperiksa {formatCp6WibDateTime(history.checkedAt)}.</p>
   <p>Stok fisik {number(row.physical)} PCS; pesanan terbuka {number(row.reserved)} PCS; tersedia {number(row.available)} PCS. Penjualan tercatat {number(row.gross)} PCS; retur {number(row.returns)} PCS.</p>
   <p>{row.availableDays} hari tersedia, {row.stockoutDays} hari stok habis, {row.unknownDays} hari belum diketahui.</p>
   <form onSubmit={e=>{e.preventDefault();void save('model')}}><label>Hari ramalan produk<input aria-label="Hari ramalan produk" type="number" min="1" max="90" step="1" required value={horizon} disabled={blocked} onChange={e=>{setModel(null);setHorizon(e.target.value)}}/></label><button disabled={blocked||history.history.state!=='UNCHANGED'||!/^([1-9]|[1-8][0-9]|90)$/.test(horizon)}>Simpan evaluasi produk</button></form>
  </div>:null}
  {model?<div><h4>{model.sku} · {model.name}</h4><p>{model.eligibleNow?'Model memenuhi syarat saat diperiksa.':'Gunakan metode dasar; model pembanding belum layak dipakai saat ini.'} {reasons[model.reason]??'Periksa kecukupan riwayat dan kebijakan yang berlaku.'}</p>
   <p>{model.policy?`Kebijakan revisi ${model.policy.policy.revision}, dicatat ${formatCp6WibDateTime(model.registryAt)}.`:'Belum ada kebijakan penggunaan model pada riwayat ini.'} {model.admittedAtCapture?'Model memenuhi syarat ketika evaluasi disimpan.':'Model belum memenuhi syarat ketika evaluasi disimpan.'}</p>
   <p>Rata-rata dasar {number(model.mean)} PCS/hari. Metode dalam arsip: {names[model.selected]}. Riwayat diketahui {formatCp6WibDateTime(model.knownAt)}; evaluasi disimpan {formatCp6WibDateTime(model.capturedAt)}.</p>
   <p>{model.sourceState==='UNCHANGED'?'Sumber sesuai saat diperiksa.':'Arsip: sumber, kebijakan, versi perhitungan, atau tanggal telah berubah.'} Diperiksa {formatCp6WibDateTime(model.checkedAt)}.</p>
   {model.scores.length?<div className="responsive-table"><table><thead><tr><th>Model</th><th>Putaran lengkap</th><th>Kesalahan rata-rata</th><th>Bias</th><th>Kesalahan periode</th><th>Uji terakhir</th></tr></thead><tbody>{model.scores.map(s=><tr key={s.id}><td>{names[s.id]}</td><td data-label="Putaran lengkap">{s.complete}/{s.requested}</td><td data-label="Kesalahan rata-rata">{number(s.mae)}</td><td data-label="Bias">{number(s.bias)}</td><td data-label="Kesalahan periode">{number(s.tail)}</td><td data-label="Uji terakhir">{number(s.holdoutMae)}</td></tr>)}</tbody></table></div>:<p>Belum ada pembandingan lengkap. Nilai yang belum diketahui tidak dianggap nol.</p>}
   {model.forecasts?<><p>Ramalan arsip berikut {model.eligibleNow?'memenuhi syarat saat diperiksa':'tidak boleh dipakai sebagai ramalan aktif'}.</p><div className="responsive-table"><table><thead><tr><th>Tanggal</th><th>Ramalan arsip (PCS)</th></tr></thead><tbody>{model.forecasts.map((v,i)=><tr key={i}><td>{new Date(Date.parse(model.forecastFrom)+i*86400000).toISOString().slice(0,10)}</td><td data-label="Ramalan arsip (PCS)">{number(v)}</td></tr>)}</tbody></table></div></>:null}
   <p>Evaluasi ini belum diterapkan pada target produksi.</p>
  </div>:null}
  {history||model?<button disabled={blocked} onClick={()=>void check()}>Periksa sumber dan kelayakan arsip</button>:null}
 </section>
}
