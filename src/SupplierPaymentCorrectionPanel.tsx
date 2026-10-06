import {useCallback,useEffect,useMemo,useRef,useState}from'react'
import {useAuth}from'./auth/AuthProvider'
import {isConnectedRuntime}from'./config/runtime'
import {getUatSupabaseClient}from'./lib/supabase'
import {normalizeClientError}from'./lib/clientError'
import {cp6WibDateTimeInput,cp6WibPhysicalTimeToIso,formatCp6WibDateTime}from'./cp6BusinessTime'
import {formatReceiptDecimal}from'./procurementContract'
import {signedSupplierSourceCents}from'./supplierCredit'
import {salesCashAmount}from'./salesCashContract'
import {useRetainedInput}from'./useRetainedFormInput'
import TransactionSourceLink from'./TransactionSourceNavigation'
import {parseSupplierPaymentCorrectionRead,type SupplierPaymentCorrectionRead}from'./supplierPaymentCorrectionContract'
import type {SupplierPayment,SupplierPaymentRead}from'./supplierPaymentContract'
import type {useProductionMutation}from'./useProductionMutation'
import type {useRetainedFormInput}from'./useRetainedFormInput'
import type {Json}from'./types/database.preconnect'
type Recovery=ReturnType<typeof useProductionMutation>
type Props={source:SupplierPaymentRead;payment:SupplierPayment;initialEdit:boolean;locked:boolean;inputs:ReturnType<typeof useRetainedFormInput>;currentReadTicket:Recovery['currentReadTicket'];isReadCurrent:Recovery['isReadCurrent'];onInvalid:(message:string)=>void;onSave:(payload:Json)=>void;onClose:()=>void}
const money=(v:string)=>`Rp${formatReceiptDecimal(v)}`
export default function SupplierPaymentCorrectionPanel({source,payment,initialEdit,locked,inputs,currentReadTicket,isReadCurrent,onInvalid,onSave,onClose}:Props){
 const{runtime,identity}=useAuth();if(!isConnectedRuntime(runtime)||identity.status!=='AUTHORIZED')throw Error('Sesi perubahan pembayaran supplier belum siap.')
 const client=useMemo(()=>getUatSupabaseClient(runtime),[runtime]);const seq=useRef(0),query=useRef({bank_q:'',bank_offset:0})
 const[data,setData]=useState<SupplierPaymentCorrectionRead|null>(null),[busy,setBusy]=useState(false),[error,setError]=useState(''),[edit,setEdit]=useState(initialEdit),[review,setReview]=useState(false)
 const key=`supplierPayment.correction.${source.purchase.id}.${payment.id}.`
 const[amount,setAmount]=useRetainedInput(inputs,key+'amount',''),[at,setAt]=useRetainedInput(inputs,key+'at',''),[bank,setBank]=useRetainedInput<{id:string;name:string}|null>(inputs,key+'bank',null),[reason,setReason]=useRetainedInput(inputs,key+'reason',''),[search,setSearch]=useState('')
 const[timeEdited,setTimeEdited]=useRetainedInput(inputs,key+'timeEdited',false),[restoredAt,setRestoredAt]=useRetainedInput<string|null>(inputs,key+'restoredAt',null),loaded=useRef(false)
 const prefill=useCallback((d:SupplierPayment)=>{setAmount(d.amount);setAt(cp6WibDateTimeInput(d.payment_date));setBank(d.cash_account_id&&d.cash_name?{id:d.cash_account_id,name:d.cash_name}:null);setTimeEdited(false);setRestoredAt(null);setReview(false)},[setAmount,setAt,setBank])
 const parentKey=JSON.stringify([source.purchase.id,payment.id,payment.review_token,source.Native_AP,source.capabilities.reverse])
 const currentParent=useRef(parentKey);currentParent.current=parentKey
 const load=useCallback(async()=>{
  const n=++seq.current,ticket=currentReadTicket(),parent=parentKey;setData(null);setReview(false);setError('')
  if(!ticket){setBusy(false);setError('Muat ulang pembayaran supplier sebelum membuka perubahan.');return}setBusy(true)
  try{const r=await client.rpc('erp_cp7_get_supplier_payment_correction_v1',{p_query:{purchase_id:source.purchase.id,payment_id:payment.id,...query.current}})
   if(n!==seq.current||!isReadCurrent(ticket)||currentParent.current!==parent)return
   if(r.error)throw r.error
   const next=parseSupplierPaymentCorrectionRead(r.data,source,payment,query.current.bank_offset)
   if(!isReadCurrent(ticket)||currentParent.current!==parent)return
   setData(next);if(!loaded.current){if(amount==='')prefill(next.document);loaded.current=true}
  }catch(e){if(n===seq.current&&isReadCurrent(ticket)){const message=normalizeClientError(e).message;setData(null);setReview(false);setError(message);onInvalid(message)}}finally{if(n===seq.current)setBusy(false)}
 },[client,currentReadTicket,isReadCurrent,onInvalid,parentKey,source,payment,prefill,amount])
 // Source identity/token is the owning parent's key. Input edits do not cause
 // implicit RPCs; explicit reload/search gets a new source-bound read.
 const loadRef=useRef(load);loadRef.current=load
 useEffect(()=>{void loadRef.current();return()=>{++seq.current}},[parentKey])
 const canCorrect=['OWNER','ADMIN'].includes(identity.profile.role)&&['warehouse.procurement.view','finance.ap.view','finance.ap.pay'].every(p=>identity.permissions.includes(p))
 const disabled=locked||busy||!data,original=data?.document,exact=salesCashAmount(amount),normalized=exact===null?null:exact.split('.')[0]+'.'+(exact.split('.')[1]??'').padEnd(2,'0')
 const physical=timeEdited?cp6WibPhysicalTimeToIso(at):restoredAt??original?.payment_date??null
 const maximum=source.Native_AP&&original?signedSupplierSourceCents(source.Native_AP.remaining)+signedSupplierSourceCents(original.amount):null
 const validAmount=normalized!==null&&signedSupplierSourceCents(normalized)>0n&&maximum!==null&&signedSupplierSourceCents(normalized)<=maximum
 const changed=original&&(normalized!==null&&signedSupplierSourceCents(normalized)!==signedSupplierSourceCents(original.amount)||physical!==original.payment_date||bank?.id!==original.cash_account_id)
 const validTime=physical!==null&&Date.parse(physical)<=Date.now()
 const valid=!disabled&&canCorrect&&data?.can_correct&&data.eligible&&Boolean(changed)&&validAmount&&validTime&&bank&&reason.trim().length>=5&&review
 const save=()=>{if(!valid||!original)return;onSave({purchase_id:source.purchase.id,payment_id:original.id,review_token:original.review_token,change_reason:reason.trim(),replacement:{amount:normalized!,cash_account_id:bank!.id,payment_date:physical!}})}
 const restore=()=>{if(disabled||!canCorrect||!data?.eligible||!data.previous)return;prefill(data.previous.document);setRestoredAt(data.previous.document.payment_date);setEdit(true)}
 return<section className="cproc-review" aria-label="Koreksi pembayaran supplier tercatat">
  <header className="cproc-heading"><h3>{edit?'Edit pembayaran supplier':'Perubahan pembayaran supplier'} {payment.number}</h3><button disabled={locked} onClick={onClose}>Tutup perubahan pembayaran supplier</button></header>
  <button disabled={locked||busy} onClick={()=>void loadRef.current()}>Muat ulang perubahan pembayaran supplier</button>
  {busy?<p role="status">Memuat sumber perubahan pembayaran supplier…</p>:null}{error?<p role="alert">{error}</p>:null}
  {data?<><p>{data.document.number} · {money(data.document.amount)} · {formatCp6WibDateTime(data.document.payment_date)} · {data.document.cash_name??'Rekening tidak tercatat'}</p><p>Riwayat pembayaran asal tetap disimpan. Data diperiksa {formatCp6WibDateTime(data.captured_at)}.</p>
   {data.previous?<section aria-label="Pembayaran supplier sebelum koreksi"><h4>Sebelum koreksi</h4><p>{data.previous.document.number} · {money(data.previous.document.amount)} · {formatCp6WibDateTime(data.previous.document.payment_date)}</p><p>{data.previous.link.reason}</p><TransactionSourceLink sourceType="SUPPLIER_PAYMENT" sourceId={data.previous.document.id} label="Buka pembayaran supplier sebelum koreksi" disabled={disabled}/></section>:null}
   {data.next?<section aria-label="Pembayaran supplier pengganti"><h4>Pengganti</h4><p>{data.next.document.number} · {money(data.next.document.amount)}</p><p>{data.next.link.reason}</p><TransactionSourceLink sourceType="SUPPLIER_PAYMENT" sourceId={data.next.document.id} label="Buka pembayaran supplier pengganti" disabled={disabled}/></section>:null}
   {!data.previous&&!data.next?<p>Belum ada koreksi yang mengganti pembayaran ini.</p>:null}
   {!data.eligible?<p>Pembayaran ini tidak dapat diedit lewat koreksi pembayaran biasa. Uang muka impor, draft dan pembayaran yang sudah dibatalkan mengikuti alurnya masing-masing.</p>:null}
   {data.eligible&&canCorrect&&!edit?<button disabled={disabled} onClick={()=>{setEdit(true);setReview(false)}}>Edit pembayaran supplier tercatat</button>:null}
   {data.eligible&&canCorrect&&data.previous?<button disabled={disabled} onClick={restore}>Pulihkan isi pembayaran supplier sebelum koreksi</button>:null}
  </>:null}
  {edit&&canCorrect&&data?.eligible?<form aria-label="Edit pembayaran supplier" onSubmit={e=>{e.preventDefault();save()}} onChange={()=>setReview(false)}><fieldset className="cproc-fieldset" disabled={disabled}>
   <p>Pembayaran lama dibalik dan pengganti dicatat dalam satu tindakan. Jika salah satu langkah ditolak, seluruh koreksi dibatalkan. Nomor pengganti dibuat server dengan jejak ke pembayaran asal.</p>
   <div className="cproc-grid"><label>Nominal dibayar<input aria-label="Nominal koreksi pembayaran supplier" inputMode="decimal" value={amount} onChange={e=>setAmount(e.target.value)}/></label><label>Waktu pembayaran · WIB<input aria-label="Waktu koreksi pembayaran supplier WIB" type="datetime-local" value={at} onChange={e=>{setAt(e.target.value);setTimeEdited(true);setRestoredAt(null)}}/></label></div>{physical&&!validTime?<p role="alert">Waktu pembayaran tidak boleh di masa depan.</p>:null}
   {maximum!==null?<p>Batas nominal pengganti {money((maximum<0n?'-':'')+((maximum<0n?-maximum:maximum)/100n).toString()+'.'+((maximum<0n?-maximum:maximum)%100n).toString().padStart(2,'0'))} sesuai pembayaran yang diganti dan sisa utang.</p>:null}
   {amount&&!validAmount?<p role="alert">Isi nominal positif dengan maksimal dua desimal, sesuai batas pengganti.</p>:null}
   <label>Cari kas atau rekening<input aria-label="Cari rekening koreksi supplier" maxLength={120} value={search} onChange={e=>setSearch(e.target.value)} onKeyDown={e=>{if(e.key==='Enter'){e.preventDefault();query.current={bank_q:search.trim(),bank_offset:0};void loadRef.current()}}}/></label><button type="button" onClick={()=>{query.current={bank_q:search.trim(),bank_offset:0};void loadRef.current()}}>Cari rekening koreksi supplier</button>
   <section aria-label="Rekening koreksi supplier">{data.cash_accounts.rows.map(b=><button type="button" key={b.id} aria-pressed={bank?.id===b.id} onClick={()=>{setBank({id:b.id,name:b.name});setReview(false)}}>{b.code} · {b.name}</button>)}{!data.cash_accounts.rows.length?<p>Tidak ada rekening aktif sesuai pencarian.</p>:null}<div className="cproc-pagination"><span>Total {data.cash_accounts.total} rekening</span><button type="button" disabled={!data.cash_accounts.offset} onClick={()=>{query.current.bank_offset=Math.max(0,data.cash_accounts.offset-25);void loadRef.current()}}>Rekening supplier sebelumnya</button><button type="button" disabled={data.cash_accounts.next_offset===null} onClick={()=>{query.current.bank_offset=data.cash_accounts.next_offset??0;void loadRef.current()}}>Rekening supplier berikutnya</button></div></section>
   <p>Rekening terpilih: {bank?.name??'belum dipilih'}</p><label>Alasan koreksi<input aria-label="Alasan koreksi pembayaran supplier" maxLength={1000} value={reason} onChange={e=>setReason(e.target.value)}/></label><label><input type="checkbox" aria-label="Koreksi pembayaran supplier sudah diperiksa" checked={review} onChange={e=>{e.stopPropagation();setReview(e.target.checked)}}/>Pembayaran asal, pengganti dan alasan sudah saya periksa.</label><button disabled={!valid}>Simpan koreksi pembayaran supplier</button>
  </fieldset></form>:null}
 </section>
}
