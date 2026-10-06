import {useCallback,useEffect,useMemo,useRef,useState} from 'react'
import {useAuth} from './auth/AuthProvider'
import {isConnectedRuntime} from './config/runtime'
import {getUatSupabaseClient} from './lib/supabase'
import {normalizeClientError} from './lib/clientError'
import {cp6WibDateTimeInput,cp6WibPhysicalTimeToIso,formatCp6WibDateTime} from './cp6BusinessTime'
import {formatReceiptDecimal} from './procurementContract'
import {salesCashAmount,salesCashCents} from './salesCashContract'
import {salesQtyInput,type SalesRead} from './salesReadContract'
import {salesReturnTotal,type SalesReturnLocation,type SalesReturnRead} from './salesReturnContract'
import {parseReturnCorrectionWorkspace,returnCorrectionCents,type ReturnCorrectionWorkspace,type ReturnCorrectionAllocation,type ReturnCorrectionDocument} from './salesReturnCorrectionContract'
import {useRetainedInput,type RetainedFormInput} from './useRetainedFormInput'
import type {useProductionMutation} from './useProductionMutation'
import TransactionSourceLink from './TransactionSourceNavigation'
import type {Json} from './types/database.preconnect'
type Recovery=ReturnType<typeof useProductionMutation>
type Source=NonNullable<SalesRead['detail']>
type OwnLine={key:string;allocation_id:string;location_id:string;qty:string;grade:'GRADE_A'|'GRADE_B'|'HOLD';refund:string;notes:string}
type Props={source:Source;returnId:string;number:string;initialEdit:boolean;locked:boolean;stale:boolean;inputs:RetainedFormInput;locations:SalesReturnRead<SalesReturnLocation>|null;readFence:Pick<Recovery,'currentReadTicket'|'isReadCurrent'>;onInvalid:(message:string)=>void;onSave:(action:'RETURN_CORRECT',document:Json,version:string)=>void;onClose:()=>void;onLocationSearch:(q:string)=>void;onLocationPage:(offset:number)=>void}
const money=(v:string)=>`Rp${formatReceiptDecimal(v)}`
export default function SalesReturnCorrectionPanel({source,returnId,number,initialEdit,locked,stale,inputs,locations,readFence,onInvalid,onSave,onClose,onLocationSearch,onLocationPage}:Props){
 const {runtime,identity}=useAuth();if(!isConnectedRuntime(runtime)||identity.status!=='AUTHORIZED')throw Error('Sesi pembetulan retur belum siap.')
 const client=useMemo(()=>getUatSupabaseClient(runtime),[runtime]),seq=useRef(0),query=useRef({q:'',offset:0}),loaded=useRef(false),dataTicket=useRef<ReturnType<Recovery['currentReadTicket']>>(null)
 const {currentReadTicket,isReadCurrent}=readFence,key=`return.${source.id}.${returnId}.`,parentKey=JSON.stringify([source.id,source.row_version,source.review_token,returnId]),parent=useRef(parentKey);parent.current=parentKey
 const [data,setData]=useState<ReturnCorrectionWorkspace|null>(null),[busy,setBusy]=useState(false),[error,setError]=useState(''),[edit,setEdit]=useState(initialEdit),[review,setReview]=useState(false)
 const [lines,setLines]=useRetainedInput<OwnLine[]>(inputs,key+'lines',[]),[at,setAt]=useRetainedInput(inputs,key+'at',''),[timeEdited,setTimeEdited]=useRetainedInput(inputs,key+'timeEdited',false),[restoredAt,setRestoredAt]=useRetainedInput<string|null>(inputs,key+'restoredAt',null),[notes,setNotes]=useRetainedInput(inputs,key+'notes',''),[reason,setReason]=useRetainedInput(inputs,key+'reason','')
 const [search,setSearch]=useState(''),[locationSearch,setLocationSearch]=useState(''),[destination,setDestination]=useState<string|null>(null)
 const facts=useRef({token:'',allocations:new Map<string,ReturnCorrectionAllocation>()})
 const ownInitialized=useRef(Object.hasOwn(inputs,key+'lines'))
 const prefill=useCallback((d:ReturnCorrectionDocument)=>{setLines(d.items.map(i=>({key:crypto.randomUUID(),allocation_id:i.allocation_id,location_id:i.location_id,qty:i.qty_pcs,grade:i.quality_grade,refund:i.refund_amount,notes:i.notes??''})));setAt(cp6WibDateTimeInput(d.physical_at));setTimeEdited(false);setRestoredAt(null);setNotes(d.notes??'');setReason('');setReview(false)},[setLines,setAt,setTimeEdited,setRestoredAt,setNotes,setReason])
 const load=useCallback(async()=>{
  const n=++seq.current,ticket=currentReadTicket(),capture=parentKey,requested={...query.current};dataTicket.current=null;setData(null);setBusy(false);setError('');setReview(false)
  if(!ticket){setError('Muat ulang invoice sebelum membuka pembetulan retur.');return}setBusy(true)
  try{const r=await client.rpc('erp_cp7_get_sales_return_correction_v1',{p_query:{sale_id:source.id,return_id:returnId,...requested,limit:25}})
   if(n!==seq.current||parent.current!==capture||!isReadCurrent(ticket))return;if(r.error)throw r.error
   const next=parseReturnCorrectionWorkspace(r.data,source,returnId,requested.offset)
   if(!isReadCurrent(ticket)||parent.current!==capture)return
   if(facts.current.token!==next.return_review_token)facts.current={token:next.return_review_token,allocations:new Map()}
   for(const a of [...next.current_allocations,...next.allocations.rows])facts.current.allocations.set(a.allocation_id,a)
   dataTicket.current=ticket;setData(next);if(!loaded.current){if(!ownInitialized.current)prefill(next.document);loaded.current=true}
  }catch(e){if(n===seq.current&&isReadCurrent(ticket)&&parent.current===capture){const message=normalizeClientError(e).message;setData(null);setReview(false);setError(message);onInvalid(message)}}finally{if(n===seq.current)setBusy(false)}
 },[client,currentReadTicket,isReadCurrent,onInvalid,parentKey,source,returnId,prefill])
 useEffect(()=>{void load();return()=>{++seq.current}},[load])
 const factsCurrent=dataTicket.current!==null&&isReadCurrent(dataTicket.current)
 const disabled=locked||stale||busy||!data||!locations||!factsCurrent,canCorrect=!!data?.can_correct&&['OWNER','ADMIN'].includes(identity.profile.role)&&['sales.return.create','sales.return.post','sales.return.reverse','finance.hpp.view'].every(p=>identity.permissions.includes(p))
 const original=data?.document,physical=timeEdited?cp6WibPhysicalTimeToIso(at):restoredAt??original?.physical_at??null
 const total=salesReturnTotal(lines.map(l=>l.refund)),originalTotal=original?salesReturnTotal(original.items.map(i=>i.refund_amount)):null
 const maxRefund=data?.financial.open_balance!==null&&data?.financial.open_balance!==undefined&&originalTotal!==null?returnCorrectionCents(data.financial.open_balance)+returnCorrectionCents(originalTotal):null
 const unique=new Set(lines.map(l=>l.allocation_id)).size===lines.length
 const validLines=lines.length>0&&lines.length<=100&&unique&&lines.every(l=>{const a=facts.current.allocations.get(l.allocation_id),q=salesQtyInput(l.qty);return a&&q!==null&&BigInt(q)<=BigInt(a.replacement_capacity)&&salesCashAmount(l.refund)!==null&&l.location_id!==''&&l.notes.length<=2000})
 const replacementLines=lines.map(l=>({allocation_id:l.allocation_id,location_id:l.location_id,qty_pcs:salesQtyInput(l.qty)??l.qty,quality_grade:l.grade,refund_amount:salesCashAmount(l.refund)??l.refund,notes:l.notes||null}))
 const normalized=(v:{allocation_id:string;location_id:string;qty_pcs:string;quality_grade:string;refund_amount:string;notes:string|null}[])=>JSON.stringify([...v].sort((a,b)=>a.allocation_id.localeCompare(b.allocation_id)).map(i=>({...i,refund_amount:salesCashAmount(i.refund_amount)===null?i.refund_amount:salesCashCents(i.refund_amount).toString()})))
 const changed=!!original&&(physical!==original.physical_at||(notes||null)!==original.notes||normalized(replacementLines)!==normalized(original.items.map(i=>({allocation_id:i.allocation_id,location_id:i.location_id,qty_pcs:i.qty_pcs,quality_grade:i.quality_grade,refund_amount:i.refund_amount,notes:i.notes}))))
 const valid=!disabled&&canCorrect&&changed&&validLines&&physical!==null&&total!==null&&maxRefund!==null&&returnCorrectionCents(total)<=maxRefund&&reason.trim().length>=5&&review
 const save=()=>{if(!valid||!data||!source.review_token||!dataTicket.current||!isReadCurrent(dataTicket.current))return;const ticket=currentReadTicket();if(!ticket||!isReadCurrent(ticket))return
  onSave('RETURN_CORRECT',{sale_id:source.id,return_id:returnId,review_token:source.review_token,return_review_token:data.return_review_token,change_reason:reason.trim(),replacement:{physical_at:physical!,notes:notes||null,items:replacementLines}},source.row_version)
 }
 const update=(id:string,change:Partial<OwnLine>)=>{setLines(old=>old.map(l=>l.key===id?{...l,...change}:l));setReview(false)}
 const restore=()=>{if(disabled||!canCorrect||!data?.previous)return;prefill(data.previous.document);setRestoredAt(data.previous.document.physical_at);setEdit(true)}
 return <section className="panel" aria-label="Pembetulan retur tercatat">
  <div className="cproc-heading"><div><h3>{edit?'Edit retur':'Perubahan retur'} {number}</h3><p>Invoice {source.number}</p></div><button disabled={locked} onClick={onClose}>Tutup pembetulan retur</button></div>
  <button disabled={locked||stale||busy} onClick={()=>void load()}>Muat ulang pembetulan retur</button>
  {error?<p role="alert">{error}</p>:null}{busy?<p role="status">Memuat retur dan alokasi asal…</p>:null}{stale?<p role="alert">Invoice berubah. Muat ulang invoice sebelum melanjutkan.</p>:null}
  {data&&!factsCurrent?<p role="alert">Invoice sudah dimuat ulang. Muat ulang pembetulan retur sebelum melanjutkan.</p>:null}
  {data?<><p>{data.document.number} · {formatCp6WibDateTime(data.document.physical_at)} · {money(salesReturnTotal(data.document.items.map(i=>i.refund_amount))!)}</p><p>Retur lama tetap tersimpan. Stok, piutang, dan HPP diperiksa bersama saat pembetulan disimpan.</p>
   {data.previous?<section aria-label="Isi retur sebelum pembetulan"><h4>Sebelum pembetulan</h4><TransactionSourceLink sourceType="SALES_RETURN" sourceId={data.previous.document.id} disabled={disabled} label={`Buka retur sebelum pembetulan ${data.previous.document.number}`}/><p>{formatCp6WibDateTime(data.previous.document.physical_at)} · {money(salesReturnTotal(data.previous.document.items.map(i=>i.refund_amount))!)}</p><p>{data.previous.link.reason}</p>{canCorrect?<button disabled={disabled} onClick={restore}>Pulihkan isi retur sebelum pembetulan</button>:null}</section>:null}
   {data.next?<section aria-label="Retur pengganti"><h4>Retur pengganti</h4><TransactionSourceLink sourceType="SALES_RETURN" sourceId={data.next.document.id} disabled={disabled} label={`Buka retur pengganti ${data.next.document.number}`}/><p>{data.next.link.reason}</p></section>:null}
   {!edit&&canCorrect?<button disabled={disabled} onClick={()=>setEdit(true)}>Edit retur tercatat</button>:null}
  </>:null}
  {edit&&data&&canCorrect?<form aria-label="Edit retur pelanggan" onSubmit={e=>{e.preventDefault();save()}} onChange={()=>setReview(false)}><fieldset disabled={disabled}>
   <label>Waktu barang kembali · WIB<input type="datetime-local" aria-label="Waktu pembetulan retur WIB" value={at} onChange={e=>{setAt(e.target.value);setTimeEdited(true);setRestoredAt(null)}}/></label>
   <label>Catatan retur<textarea aria-label="Catatan pembetulan retur" maxLength={2000} value={notes} onChange={e=>setNotes(e.target.value)}/></label>
   <div className="cproc-search"><label>Cari gudang penerima<input aria-label="Cari gudang pembetulan retur" maxLength={120} value={locationSearch} onChange={e=>setLocationSearch(e.target.value)}/></label><button type="button" onClick={()=>onLocationSearch(locationSearch.trim())}>Cari gudang pembetulan retur</button></div>
   {locations?<section aria-label="Gudang pembetulan retur">{locations.page.rows.map(l=><button type="button" key={l.id} aria-pressed={destination===l.id} onClick={()=>setDestination(l.id)}>{l.name}</button>)}<p>Pilih gudang lalu gunakan tombol pada baris yang ingin dipindah.</p><div className="cproc-pagination"><span>Total {locations.page.total} gudang</span><button type="button" disabled={locations.page.offset===0} onClick={()=>onLocationPage(Math.max(0,locations.page.offset-25))}>Gudang pembetulan sebelumnya</button><button type="button" disabled={locations.page.next_offset===null} onClick={()=>onLocationPage(locations.page.next_offset??0)}>Gudang pembetulan berikutnya</button></div></section>:null}
   {lines.map((l,n)=>{const a=facts.current.allocations.get(l.allocation_id),known=original?.items.find(i=>i.allocation_id===l.allocation_id)??data.previous?.document.items.find(i=>i.allocation_id===l.allocation_id),locationName=locations?.page.rows.find(x=>x.id===l.location_id)?.name??(known?.location_id===l.location_id?known.location_name:null)
    return <article className="cproc-item" key={l.key}><h4>{a?.product_sku??known?.product_sku??'Alokasi belum dimuat'} · lot {a?.lot_number??known?.lot_number??'belum dimuat'}</h4>{a?<p>Maksimum pengganti {formatReceiptDecimal(a.replacement_capacity)} PCS setelah retur lain.</p>:<p role="alert">Cari SKU atau lot untuk memuat alokasi baris ini sebelum menyimpan.</p>}
     <div className="cproc-grid"><label>Jumlah PCS<input aria-label={`Jumlah pembetulan retur ${n+1}`} inputMode="numeric" value={l.qty} onChange={e=>update(l.key,{qty:e.target.value})}/></label><label>Nilai retur<input aria-label={`Nilai pembetulan retur ${n+1}`} inputMode="decimal" value={l.refund} onChange={e=>update(l.key,{refund:e.target.value})}/></label><label>Grade<select aria-label={`Grade pembetulan retur ${n+1}`} value={l.grade} onChange={e=>update(l.key,{grade:e.target.value as OwnLine['grade']})}><option value="GRADE_A">Grade A</option><option value="GRADE_B">Grade B</option><option value="HOLD">Ditahan (Hold)</option></select></label></div>
     <p>Gudang penerima: {locationName??'pilihan gudang belum dimuat'}</p><button type="button" disabled={!destination} onClick={()=>update(l.key,{location_id:destination!})}>Gunakan gudang pilihan untuk baris {n+1}</button><label>Catatan baris<input aria-label={`Catatan baris pembetulan retur ${n+1}`} maxLength={2000} value={l.notes} onChange={e=>update(l.key,{notes:e.target.value})}/></label><button type="button" onClick={()=>{setLines(old=>old.filter(x=>x.key!==l.key));setReview(false)}}>Hapus baris pembetulan {n+1}</button>
    </article>
   })}
   <div className="cproc-search"><label>Cari SKU atau lot asal<input aria-label="Cari alokasi pembetulan retur" maxLength={120} value={search} onChange={e=>setSearch(e.target.value)}/></label><button type="button" onClick={()=>{query.current={q:search.trim(),offset:0};void load()}}>Cari alokasi pembetulan retur</button></div>
   <section aria-label="Alokasi pengganti retur">{data.allocations.rows.map(a=><button type="button" key={a.allocation_id} disabled={lines.length>=100||lines.some(l=>l.allocation_id===a.allocation_id)||!destination} onClick={()=>{setLines(old=>[...old,{key:crypto.randomUUID(),allocation_id:a.allocation_id,location_id:destination!,qty:'',grade:'GRADE_A',refund:'',notes:''}]);setReview(false)}}>Tambah {a.product_sku} · lot {a.lot_number}</button>)}<div className="cproc-pagination"><span>Total {data.allocations.total} alokasi</span><button type="button" disabled={data.allocations.offset===0} onClick={()=>{query.current.offset=Math.max(0,data.allocations.offset-25);void load()}}>Alokasi pembetulan sebelumnya</button><button type="button" disabled={data.allocations.next_offset===null} onClick={()=>{query.current.offset=data.allocations.next_offset??0;void load()}}>Alokasi pembetulan berikutnya</button></div></section>
   <p>Total retur pengganti: {total===null?'periksa nilai baris':money(total)}</p><label>Alasan pembetulan<input aria-label="Alasan pembetulan retur" maxLength={1000} value={reason} onChange={e=>setReason(e.target.value)}/></label><label><input type="checkbox" aria-label="Pembetulan retur sudah diperiksa" checked={review} onChange={e=>{e.stopPropagation();setReview(e.target.checked)}}/>Jumlah, gudang, grade, tanggal, dan nilai retur sudah diperiksa.</label><button className="primary-btn" disabled={!valid}>Simpan pembetulan retur</button>
  </fieldset></form>:null}
 </section>
}
