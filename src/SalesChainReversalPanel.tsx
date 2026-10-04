import {useCallback,useEffect,useMemo,useRef,useState} from 'react'
import {useAuth} from './auth/AuthProvider'
import {isConnectedRuntime} from './config/runtime'
import {getUatSupabaseClient} from './lib/supabase'
import {normalizeClientError} from './lib/clientError'
import {formatCp6WibDateTime} from './cp6BusinessTime'
import {formatReceiptDecimal} from './procurementContract'
import {parseSalesChainWorkspace,salesChainPayload,type SalesChainWorkspace,type SalesChainPayload} from './salesChainContract'
import type {SalesRead} from './salesReadContract'
import type {useProductionMutation} from './useProductionMutation'
import TransactionSourceLink from './TransactionSourceNavigation'

type Recovery=ReturnType<typeof useProductionMutation>
type Props={source:NonNullable<SalesRead['detail']>;locked:boolean;stale:boolean;readFence:Pick<Recovery,'currentReadTicket'|'isReadCurrent'>;onInvalid:(message:string)=>void;onClose:()=>void;onSave:(payload:SalesChainPayload,version:string)=>void}
export default function SalesChainReversalPanel({source,locked,stale,readFence,onInvalid,onClose,onSave}:Props){
 const {runtime,identity}=useAuth();if(!isConnectedRuntime(runtime)||identity.status!=='AUTHORIZED')throw Error('Sesi pembatalan rantai belum siap.')
 const allowed=['OWNER','ADMIN'].includes(identity.profile.role)&&['sales.invoice.view','sales.invoice.reverse','sales.payment.view','sales.payment.reverse','sales.return.view','sales.return.reverse','finance.ar.view','finance.hpp.view'].every(p=>identity.permissions.includes(p))
 const client=useMemo(()=>getUatSupabaseClient(runtime),[runtime]),serial=useRef(0),dataTicket=useRef<ReturnType<Recovery['currentReadTicket']>>(null)
 const {currentReadTicket,isReadCurrent}=readFence,parentKey=JSON.stringify([source.id,source.row_version,source.review_token]),parent=useRef(parentKey);parent.current=parentKey
 const [data,setData]=useState<SalesChainWorkspace|null>(null),[busy,setBusy]=useState(false),[error,setError]=useState(''),[reason,setReason]=useState(''),[reviewed,setReviewed]=useState(false)
 const load=useCallback(async()=>{
  const ticket=currentReadTicket(),capture=parentKey,n=++serial.current;dataTicket.current=null;setData(null);setReviewed(false);setError('');setBusy(false)
  if(!allowed||!ticket||stale)return;setBusy(true)
  try{const r=await client.rpc('erp_cp7_get_sales_chain_v1',{p_sale:source.id});if(n!==serial.current||parent.current!==capture||!isReadCurrent(ticket))return;if(r.error)throw r.error
   const d=parseSalesChainWorkspace(r.data,source);dataTicket.current=ticket;setData(d)
  }catch(e){if(n===serial.current&&parent.current===capture&&isReadCurrent(ticket)){const message=normalizeClientError(e).message;setError(message);setData(null);onInvalid(message)}}finally{if(n===serial.current)setBusy(false)}
 },[client,allowed,currentReadTicket,isReadCurrent,source,parentKey,stale,onInvalid])
 useEffect(()=>{void load();return()=>{++serial.current}},[load])
 const current=!!dataTicket.current&&isReadCurrent(dataTicket.current)&&dataTicket.current===currentReadTicket()
 const disabled=locked||stale||busy||!allowed||!current||!data?.eligible
 const save=()=>{if(disabled||!data||!reviewed||reason.trim().length<5||reason.trim().length>1000)return;onSave(salesChainPayload(data,reason),source.row_version)}
 return <section className="panel cproc-review" aria-label={`Pembatalan atomik rantai ${source.number}`}>
  <header><h2>Batalkan rantai {source.number}</h2><button type="button" disabled={locked||busy||stale||!allowed} onClick={()=>void load()}>Muat ulang rantai</button><button type="button" disabled={locked||busy} onClick={onClose}>Tutup pembatalan rantai</button></header>
  <p>Seluruh pembayaran aktif, seluruh retur aktif, lalu invoice dibatalkan bersama. Riwayat asal tetap tersimpan. Kalau satu langkah ditolak, seluruh pembatalan batal tanpa efek sebagian.</p>
  {busy?<p role="status">Memeriksa semua dokumen terkait…</p>:null}{error?<p role="alert">{error}</p>:null}
  {!allowed?<p role="alert">Izin pembatalan invoice, pembayaran, retur, piutang dan HPP diperlukan.</p>:null}
  {data&&current?<><p>{data.source.payments.length} pembayaran aktif · {data.source.returns.length} retur aktif · 1 invoice. Daftar ini mencakup seluruh dokumen aktif.</p>
   <ol aria-label="Urutan pembatalan lengkap">{data.source.payments.map(p=><li key={p.id}>Pembayaran {p.number} · Rp{formatReceiptDecimal(p.amount)} · {formatCp6WibDateTime(p.physical_at)}</li>)}{data.source.returns.map(r=><li key={r.id}>Retur {r.number} · {r.line_count} baris · {formatCp6WibDateTime(r.physical_at)}</li>)}<li>Invoice {data.source.number}</li></ol>
   {data.source.pending_children.length>0?<div role="alert"><p>Selesaikan dokumen draft berikut pada halaman asal sebelum membatalkan rantai:</p><ul>{data.source.pending_children.map(c=><li key={c.id}>{c.kind==='PAYMENT'?'Pembayaran':'Retur'} {c.number}<TransactionSourceLink sourceType={c.kind==='PAYMENT'?'SALES_PAYMENT':'SALES_RETURN'} sourceId={c.id} disabled={locked||stale||!current} label={`Buka ${c.number}`}/></li>)}</ul></div>:null}
   {!data.eligible&&data.source.pending_children.length===0?<p role="alert">Invoice ini sudah tidak aktif. Muat ulang sumber sebelum melanjutkan.</p>:null}
  </>:!busy?<p>Daftar belum dapat dipastikan. Muat ulang invoice lalu muat ulang rantai sebelum melanjutkan.</p>:null}
  <label>Alasan pembatalan<input aria-label="Alasan pembatalan rantai" value={reason} maxLength={1000} disabled={locked||busy} onChange={e=>{setReason(e.target.value);setReviewed(false)}}/></label>
  <label className="cproc-check"><input type="checkbox" aria-label="Seluruh rantai sudah diperiksa" checked={reviewed} disabled={disabled} onChange={e=>setReviewed(e.target.checked)}/>Semua dokumen dan alasan sudah saya periksa.</label>
  <button type="button" disabled={disabled||!reviewed||reason.trim().length<5} onClick={save}>Batalkan rantai sekaligus</button>
 </section>
}
