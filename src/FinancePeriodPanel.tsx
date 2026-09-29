import { useCallback, useEffect, useRef, useState } from 'react'
import type { getUatSupabaseClient } from './lib/supabase'
import { normalizeClientError } from './lib/clientError'
import { cp6WibDateTimeInput } from './cp6BusinessTime'
import { financeDate } from './financeReportContract'
import { parsePeriodControl, parsePeriodOutcome, type PeriodControl } from './periodControlContract'
import { useProductionMutation, type ProductionMutationHandlers } from './useProductionMutation'
import ProductionRecoveryNotice from './ProductionRecoveryNotice'
import type { Json } from './types/database.preconnect'

export default function FinancePeriodPanel({ client, onChanged }: { client:ReturnType<typeof getUatSupabaseClient>;onChanged:()=>Promise<boolean> }) {
 const today=cp6WibDateTimeInput().slice(0,10)
 const [day,setDay]=useState(today),[data,setData]=useState<PeriodControl|null>(null),[loading,setLoading]=useState(false),[error,setError]=useState('')
 const [action,setAction]=useState<'CLOSE'|'REOPEN'>('CLOSE'),[reopenDay,setReopenDay]=useState(''),[openAll,setOpenAll]=useState(false),[reason,setReason]=useState(''),[reviewed,setReviewed]=useState(false)
 const currentDay=useRef(day);currentDay.current=day
 const mutation=useProductionMutation('FINANCE_PERIOD'),{beginRead,finishRead,isReadCurrent,run,reconcile}=mutation
 const load=useCallback(async()=>{
  const through=currentDay.current,ticket=beginRead();setData(null);setError('');setReviewed(false)
  if(!financeDate(through)||through>today){setLoading(false);setError('Pilih tanggal pemeriksaan yang sah, sampai hari ini.');return false}
  setLoading(true)
  try{
   const r=await client.rpc('erp_cp7_get_period_control_v1',{p_through:through})
   if(!isReadCurrent(ticket)||through!==currentDay.current)return false
   if(r.error)throw r.error
   const next=parsePeriodControl(r.data,through);if(!finishRead(ticket))return false;setData(next);return true
  }catch(e){if(isReadCurrent(ticket))setError(normalizeClientError(e).message);return false}
  finally{if(through===currentDay.current)setLoading(false)}
 },[client,today,beginRead,finishRead,isReadCurrent])
 useEffect(()=>{void load()},[load,day])
 const handlers:ProductionMutationHandlers={
  send:e=>client.rpc('erp_cp7_save_period_control_v1',{p_action:e.action,p_payload:e.payload,p_request:e.id}),
  validate:(v,e)=>{parsePeriodOutcome(v,e.id,e.action,e.payload)},
  retire:()=>{setData(null);setReviewed(false)},
  reload:async()=>{const current=await load();const report=await onChanged();return current&&report},
 }
 const current=data?.through===day?data:null,locked=mutation.writerLocked||loading
 const target=action==='CLOSE'?day:openAll?null:reopenDay
 const allowed=current&&reason.trim()&&reason.trim().length<=1000&&reviewed&&(action==='CLOSE'
  ?current.preflight.status==='READY'&&current.preflight.date_allowed&&day<today&&(!current.control.closed_through||day>current.control.closed_through)
  :current.control.closed_through&&(openAll||financeDate(reopenDay)&&reopenDay<current.control.closed_through&&reopenDay<today))
 const payload:Json|null=allowed?{through:target,review_through:day,review_token:current.review_token,reason:reason.trim()}:null
 return <section className="panel cperiod-control" aria-label="Kelola periode pembukuan">
  <h2>Kelola tutup buku</h2>
  <p>Penutupan menyimpan arsip saldo asli. Membuka kembali periode memberi ruang untuk koreksi; arsip yang sudah tersimpan tetap ada.</p>
  <ProductionRecoveryNotice recovery={mutation} className="" onReconcile={()=>reconcile(handlers)}/>
  {error?<p role="alert">{error}</p>:null}{loading?<p role="status">Memeriksa periode…</p>:null}
  <div className="cproc-grid"><label>Tanggal pemeriksaan tutup buku<input type="date" value={day} max={today} disabled={mutation.writerLocked} onChange={e=>{setData(null);setReviewed(false);setDay(e.target.value)}}/></label><button disabled={loading||mutation.busy} onClick={()=>void load()}>Periksa ulang periode</button></div>
  {current?<>
   <p>Periode tertutup sampai <strong>{current.control.closed_through??'belum ada'}</strong>. Penghalang: {current.preflight.blocker_count}.</p>
   {current.preflight.blockers.map((b,i)=><article className="cproc-item" key={`${b.code}:${i}`}><strong>{b.reason}</strong><small>{b.impact_date??'Kondisi saat ini'}</small></article>)}
   {current.preflight.info.map((b,i)=><p key={`${b.code}:${i}`}>{b.reason}</p>)}
   <fieldset disabled={locked}>
    <label>Tindakan periode<select aria-label="Tindakan periode" value={action} onChange={e=>{setAction(e.target.value as 'CLOSE'|'REOPEN');setReviewed(false)}}><option value="CLOSE">Tutup sampai tanggal pemeriksaan</option><option value="REOPEN">Buka kembali untuk koreksi</option></select></label>
    {action==='REOPEN'?<div className="cproc-grid"><label>Periode tetap tertutup sampai<input type="date" disabled={openAll} value={reopenDay} onChange={e=>{setReopenDay(e.target.value);setReviewed(false)}}/></label><label><input type="checkbox" checked={openAll} onChange={e=>{setOpenAll(e.target.checked);setReviewed(false)}}/>Buka seluruh periode tertutup</label></div>:null}
    <p>{action==='CLOSE'?`Tutup sampai ${day}. Arsip baru akan disimpan setelah pemeriksaan ulang di server.`:openAll?'Seluruh periode akan dibuka kembali. Arsip lama tetap tersimpan.':`Periode setelah ${reopenDay||'tanggal yang dipilih'} akan dibuka kembali; tanggal sebelumnya tetap tertutup.`}</p>
    <label>Alasan perubahan periode<textarea aria-label="Alasan perubahan periode" value={reason} maxLength={1000} onChange={e=>{setReason(e.target.value);setReviewed(false)}}/></label>
    <label className="cmat-check"><input type="checkbox" checked={reviewed} onChange={e=>setReviewed(e.target.checked)}/>Saya sudah memeriksa tanggal, penghalang, dan alasan perubahan periode.</label>
    <button className="primary-btn" disabled={!payload} onClick={()=>{if(payload&&!locked)void run(action,payload,null,handlers)}}>{action==='CLOSE'?'Tutup buku dan simpan arsip':'Buka kembali periode'}</button>
   </fieldset>
  </>:null}
 </section>
}
