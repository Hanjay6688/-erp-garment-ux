import {useCallback,useEffect,useRef,useState} from 'react'
import type {getUatSupabaseClient} from './lib/supabase'
import {normalizeClientError} from './lib/clientError'
import {formatCp6WibDateTime} from './cp6BusinessTime'
import {parseRecostQueue,parseRecostOutcome,type RecostQueue,type RecostOutcome} from './recostContract'
import {useProductionMutation,type ProductionMutationHandlers} from './useProductionMutation'
import ProductionRecoveryNotice from './ProductionRecoveryNotice'
export default function RecostQueuePanel({client,canManage,onChanged}:{client:ReturnType<typeof getUatSupabaseClient>;canManage:boolean;onChanged:()=>Promise<boolean>}){
 const [data,setData]=useState<RecostQueue|null>(null),[busy,setBusy]=useState(false),[error,setError]=useState(''),[reason,setReason]=useState(''),[reviewed,setReviewed]=useState(false),[outcome,setOutcome]=useState<RecostOutcome|null>(null)
 const page=useRef(0),mutation=useProductionMutation('HPP_RECOST'),{beginRead,finishRead,isReadCurrent,run,reconcile}=mutation
 const load=useCallback(async()=>{
  const offset=page.current,ticket=beginRead();setData(null);setBusy(true);setError('');setReviewed(false)
  try{const r=await client.rpc('erp_cp7_get_recost_queue_v1',{p_offset:offset});if(!isReadCurrent(ticket)||page.current!==offset)return false;if(r.error)throw r.error;const parsed=parseRecostQueue(r.data,offset);if(!finishRead(ticket))return false;setData(parsed);return true}
  catch(e){if(isReadCurrent(ticket))setError(normalizeClientError(e).message);return false}finally{if(page.current===offset)setBusy(false)}
 },[client,beginRead,finishRead,isReadCurrent])
 useEffect(()=>{void load()},[load])
 const handlers:ProductionMutationHandlers={send:e=>client.rpc('erp_cp7_process_recost_v1',{p_payload:e.payload,p_request:e.id}),validate:(value,e)=>{setOutcome(parseRecostOutcome(value,e.id,e.payload))},retire:()=>{setData(null);setReviewed(false)},reload:async()=>{page.current=0;const current=await load();const hpp=await onChanged();return current&&hpp}}
 const locked=busy||mutation.writerLocked,allowed=canManage&&data&&BigInt(data.counts.eligible)>0n&&reason.trim().length>0&&reason.trim().length<=1000&&reviewed&&!locked
 const labels={PENDING:'Menunggu',RUNNING:'Sedang diproses',FAILED:'Gagal'} as const
 return <section className="panel cproc crecost-control" aria-label="Antrean hitung ulang HPP">
  <h2>Hitung ulang HPP</h2><p>Proses sumber biaya yang berubah menggunakan aturan biaya yang berlaku. Perhitungan dapat memperbarui HPP barang tersisa dan terjual beserta jurnal koreksinya.</p>
  <ProductionRecoveryNotice recovery={mutation} className="" onReconcile={()=>reconcile(handlers)}/>
  <button disabled={busy||mutation.busy} onClick={()=>void load()}>Muat ulang antrean HPP</button>
  {busy?<p role="status">Memeriksa antrean biaya…</p>:null}{error?<p role="alert">{error}</p>:null}
  {outcome?<p role="status">Permintaan terakhir menyelesaikan {outcome.completed} pekerjaan pada {formatCp6WibDateTime(outcome.processed_at)}. Ini hasil permintaan tersebut; periksa antrean terbaru dan kelengkapan biaya sebelum menyatakan HPP final.</p>:null}
  {data?<>
   <p>Menunggu {data.counts.pending} · berjalan {data.counts.running} · gagal {data.counts.failed} · sudah selesai {data.counts.done}.</p>
   <p>Siap dicoba sekarang: {data.counts.eligible}. Gagal mencapai batas percobaan: {data.counts.exhausted}. Daftar ini mencakup seluruh antrean saat ini, terpisah dari tanggal dan SKU pada laporan.</p>
   {data.page.rows.map(row=><article className="cproc-item" key={row.id}><strong>{row.po_number??row.entity_type+' · '+row.entity_id}</strong><p>{labels[row.status]} · percobaan {row.attempt_count} · {row.eligible?'Siap dicoba':'Belum dapat dicoba'}.</p><p>{row.reason}</p><small>Masuk {formatCp6WibDateTime(row.queued_at)}{row.recalc_from?' · biaya sejak '+formatCp6WibDateTime(row.recalc_from):''}{row.next_attempt_at?' · jadwal coba '+formatCp6WibDateTime(row.next_attempt_at):''}</small>{row.error_message?<p>{row.error_message}{row.error_truncated?' … (pesan dipotong)':''}</p>:null}</article>)}
   {data.page.total==='0'?<p>Tidak ada pekerjaan antrean terbuka. Kelengkapan sumber biaya tetap diperiksa pada laporan HPP.</p>:null}
   <p>Total antrean terbuka: {data.page.total}.</p><button disabled={locked||data.page.offset===0} onClick={()=>{page.current=Math.max(0,data.page.offset-25);void load()}}>Antrean sebelumnya</button><button disabled={locked||data.page.next_offset===null} onClick={()=>{page.current=data.page.next_offset??0;void load()}}>Antrean berikutnya</button>
   {canManage?<fieldset disabled={locked}><p>Satu permintaan mencoba maksimal 20 pekerjaan yang siap dan tidak sedang dikunci proses lain. Pekerjaan gagal atau yang belum waktunya dicoba tetap terlihat. Daftar di atas bukan pilihan pekerjaan untuk dipaksa diproses.</p>
    <label>Alasan hitung ulang<textarea aria-label="Alasan hitung ulang" maxLength={1000} value={reason} onChange={e=>{setReason(e.target.value);setReviewed(false)}}/></label>
    <label className="cproc-check"><input type="checkbox" checked={reviewed} onChange={e=>setReviewed(e.target.checked)}/>Saya sudah memeriksa antrean dan dampak perubahan biaya.</label>
    <button className="primary-btn" disabled={!allowed} onClick={()=>{if(allowed)void run('PROCESS_ELIGIBLE',{limit:20,reason:reason.trim()},null,handlers)}}>Proses maksimal 20 pekerjaan</button>
   </fieldset>:<p>Hak mengelola HPP diperlukan untuk memproses antrean.</p>}
  </>:null}
 </section>
}
