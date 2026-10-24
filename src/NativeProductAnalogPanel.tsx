import {useCallback,useEffect,useRef,useState} from 'react'
import {formatCp6WibDateTime} from './cp6BusinessTime'
import {normalizeClientError} from './lib/clientError'
import {readProductAnalogCandidates,type AnalogCandidates,type AnalogReadContext} from './nativeProductAnalog'
import NativeProductAnalogChoicePanel from './NativeProductAnalogChoicePanel'

type Props={client:unknown;context:AnalogReadContext;label:string;onClose:()=>void;onAccessLost:(message:string)=>void;choiceReview?:{scope:string;canManage:boolean}}
const reasonLabel=(v:string)=>v==='SAME_PHYSICAL_SIZE'?'Ukuran fisik sama':v==='SAME_CAPTURED_MODEL'?'Model yang tercatat sama':v==='SAME_CAPTURED_BRAND'?'Merek yang tercatat sama':v
export default function NativeProductAnalogPanel({client,context,label,onClose,onAccessLost,choiceReview}:Props){
 const seq=useRef(0),[result,setResult]=useState<AnalogCandidates|null>(null),[busy,setBusy]=useState(false),[error,setError]=useState('')
 const load=useCallback(async(offset:number,previous?:AnalogCandidates)=>{
  const n=++seq.current;setBusy(true);setError('');setResult(null)
  try{const value=await readProductAnalogCandidates(client,context,offset,previous);if(n===seq.current)setResult(value)}
  catch(e){if(n===seq.current){const failure=normalizeClientError(e);setError(failure.message);if(failure.code==='FORBIDDEN'||failure.code==='AUTH_REQUIRED')onAccessLost(failure.message)}}
  finally{if(n===seq.current)setBusy(false)}
 },[client,context,onAccessLost])
 useEffect(()=>{void load(0);return()=>{++seq.current}},[load])
 return <section className="native-production-result native-product-analog" aria-label="Kandidat produk pembanding">
  <header><h4>Produk pembanding untuk {label}</h4><button onClick={()=>{++seq.current;onClose()}}>Tutup produk pembanding</button></header>
  <p>Data per {formatCp6WibDateTime(context.reference.capturedAt)}. Daftar ini memakai data saat perhitungan dibuat; perubahan data setelah itu belum diperiksa.</p>
  <p>Kandidat belum dipilih dan belum mengubah target produksi. Kemiripan model dan merek berasal dari catatan produk; kecocokan kain, pola, dan pola penjualan masih perlu diperiksa.</p>
  {busy?<p role="status">Membaca kandidat produk pembanding…</p>:null}
  {error?<><p role="alert">{error}</p><button disabled={busy} onClick={()=>void load(0)}>Baca ulang kandidat</button></>:null}
  {result?<>
   {result.state==='PLANNING_CONFIG_REQUIRED'?<p>Atur dan simpan profil perencanaan produk ini terlebih dahulu, termasuk minimal hari data yang tersedia.</p>:<p>{result.total} kandidat memenuhi minimal {result.minimumDays} hari tersedia; {result.suggested} memiliki model atau merek yang tercatat sama.</p>}
   {result.state==='INSUFFICIENT_REVIEWABLE_HISTORY'?<p>Data pembanding belum cukup. Nilai yang belum diketahui tetap belum diketahui.</p>:null}
   {result.state==='MANUAL_CHOICE_REQUIRES_SIMILARITY_REASON'?<p>Belum ada kemiripan model atau merek yang tercatat. Pemilihan nanti memerlukan pemeriksaan dan alasan kesamaan.</p>:null}
   {result.rows.length?<><p>Kandidat {result.offset+1}–{result.offset+result.rows.length} dari {result.total}.</p>
    <div className="responsive-table"><table><thead><tr><th>Produk pembanding</th><th>Alasan kandidat</th><th>Hari tersedia</th><th>Hari stok habis</th><th>Hari belum diketahui</th><th>Rata-rata penjualan saat tersedia (PCS/hari)</th></tr></thead><tbody>{result.rows.map(r=><tr key={r.key} data-analog-target={r.key}><td data-label="Produk pembanding">{r.sku} · {r.name}{r.active?'':' · Tidak aktif'}</td><td data-label="Alasan kandidat">{r.reasons.map(reasonLabel).join('; ')}{r.manualReasonRequired?' · Alasan kesamaan perlu diperiksa':''}</td><td data-label="Hari tersedia">{r.availableDays}</td><td data-label="Hari stok habis">{r.stockoutDays}</td><td data-label="Hari belum diketahui">{r.unknownDays}</td><td data-label="PCS/hari">{r.mean}</td></tr>)}</tbody></table></div>
    <nav aria-label="Halaman produk pembanding"><button disabled={busy||result.offset===0} onClick={()=>void load(Math.max(0,result.offset-50),result)}>50 kandidat sebelumnya</button><button disabled={busy||result.offset+50>=result.total} onClick={()=>void load(result.offset+50,result)}>50 kandidat berikutnya</button></nav></>:null}
  </>:null}
  {choiceReview?<NativeProductAnalogChoicePanel key={choiceReview.scope+':'+context.actor+':'+context.targetKey} client={client} context={context} candidates={result} scope={choiceReview.scope} canManage={choiceReview.canManage} onAccessLost={onAccessLost}/>:null}
 </section>
}
