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
import {parseSupplierPaymentCreateRead,type SupplierPaymentCreatePayload,type SupplierPaymentCreateRead}from'./supplierPaymentCreateContract'
import type {SupplierPaymentRead}from'./supplierPaymentContract'
import type {useProductionMutation}from'./useProductionMutation'
import type {useRetainedFormInput}from'./useRetainedFormInput'
type Recovery=ReturnType<typeof useProductionMutation>
type Props={source:SupplierPaymentRead;locked:boolean;inputs:ReturnType<typeof useRetainedFormInput>;currentReadTicket:Recovery['currentReadTicket'];isReadCurrent:Recovery['isReadCurrent'];onInvalid:(message:string)=>void;onSave:(payload:SupplierPaymentCreatePayload)=>void;onClose:()=>void}
const money=(v:string)=>`Rp${formatReceiptDecimal(v)}`
const rupiah=(c:bigint)=>money((c<0n?'-':'')+((c<0n?-c:c)/100n).toString()+'.'+((c<0n?-c:c)%100n).toString().padStart(2,'0'))
export default function SupplierPaymentCreatePanel({source,locked,inputs,currentReadTicket,isReadCurrent,onInvalid,onSave,onClose}:Props){
 const{runtime,identity}=useAuth();if(!isConnectedRuntime(runtime)||identity.status!=='AUTHORIZED')throw Error('Sesi pembayaran supplier belum siap.')
 const client=useMemo(()=>getUatSupabaseClient(runtime),[runtime]);const seq=useRef(0),query=useRef({bank_q:'',bank_offset:0})
 const[data,setData]=useState<SupplierPaymentCreateRead|null>(null),[busy,setBusy]=useState(false),[error,setError]=useState(''),[review,setReview]=useState(false),[search,setSearch]=useState('')
 const key=`supplierPayment.create.${source.purchase.id}.`
 const[amount,setAmount]=useRetainedInput(inputs,key+'amount',''),[at,setAt]=useRetainedInput(inputs,key+'at',''),[bank,setBank]=useRetainedInput<{id:string;name:string}|null>(inputs,key+'bank',null),[note,setNote]=useRetainedInput(inputs,key+'note','')
 const parentKey=JSON.stringify([source.purchase.id,source.purchase.status,source.Native_AP,source.capabilities.reverse])
 const currentParent=useRef(parentKey);currentParent.current=parentKey
 const load=useCallback(async()=>{
  const n=++seq.current,ticket=currentReadTicket(),parent=parentKey;setData(null);setReview(false);setError('')
  if(!ticket){setBusy(false);setError('Muat ulang pembayaran supplier sebelum mencatat pembayaran baru.');return}setBusy(true)
  try{const r=await client.rpc('erp_cp7_get_supplier_payment_create_v1',{p_query:{purchase_id:source.purchase.id,...query.current}})
   if(n!==seq.current||!isReadCurrent(ticket)||currentParent.current!==parent)return
   if(r.error)throw r.error
   const next=parseSupplierPaymentCreateRead(r.data,source,query.current.bank_offset)
   if(!isReadCurrent(ticket)||currentParent.current!==parent)return
   setData(next);if(at==='')setAt(cp6WibDateTimeInput())
  }catch(e){if(n===seq.current&&isReadCurrent(ticket)){const message=normalizeClientError(e).message;setData(null);setReview(false);setError(message);onInvalid(message)}}finally{if(n===seq.current)setBusy(false)}
 },[client,currentReadTicket,isReadCurrent,onInvalid,parentKey,source,at,setAt])
 // The owning payment list is the parent read: a changed AP or receipt reopens this
 // form from a new server read. Typing never triggers an implicit RPC.
 const loadRef=useRef(load);loadRef.current=load
 useEffect(()=>{void loadRef.current();return()=>{++seq.current}},[parentKey])
 const canCreate=['OWNER','ADMIN'].includes(identity.profile.role)&&['warehouse.procurement.view','finance.ap.view','finance.ap.pay'].every(p=>identity.permissions.includes(p))
 const disabled=locked||busy||!data,exact=salesCashAmount(amount),normalized=exact===null?null:exact.split('.')[0]+'.'+(exact.split('.')[1]??'').padEnd(2,'0')
 const remaining=data?.Native_AP?signedSupplierSourceCents(data.Native_AP.remaining):null
 const paid=normalized===null?null:signedSupplierSourceCents(normalized)
 const validAmount=paid!==null&&paid>0n&&remaining!==null&&paid<=remaining
 const physical=cp6WibPhysicalTimeToIso(at),received=data?Date.parse(data.purchase.physical_at):NaN
 const validTime=physical!==null&&Date.parse(physical)<=Date.now()&&Date.parse(physical)>=received
 const valid=!disabled&&canCreate&&data?.can_create&&data.eligible&&validAmount&&validTime&&Boolean(bank)&&note.trim().length>=5&&note.trim().length<=500&&review
 const save=()=>{if(!valid||!data)return;onSave({purchase_id:data.purchase.id,review_token:data.review_token,amount:normalized!,cash_account_id:bank!.id,payment_date:physical!,note:note.trim()})}
 const seek=(offset:number)=>{query.current={...query.current,bank_offset:offset};void loadRef.current()}
 return<section className="cproc-review" aria-label="Catat pembayaran supplier baru">
  <header className="cproc-heading"><h3>Bayar supplier {source.purchase.number}</h3><button disabled={locked} onClick={onClose}>Tutup pembayaran supplier baru</button></header>
  <button disabled={locked||busy} onClick={()=>void loadRef.current()}>Muat ulang pembayaran supplier baru</button>
  {busy?<p role="status">Memuat sisa utang dan rekening…</p>:null}{error?<p role="alert">{error}</p>:null}
  {data?<>
   <p>{data.purchase.supplier_name} · penerimaan {formatCp6WibDateTime(data.purchase.physical_at)} · data diperiksa {formatCp6WibDateTime(data.captured_at)}</p>
   {remaining!==null?<p>Sisa utang sekarang {rupiah(remaining)}{validAmount?` · sesudah bayar ${rupiah(remaining-paid!)}`:''}</p>:<p>Saldo utang penerimaan ini belum tersedia.</p>}
   {!data.eligible?<p>Tidak ada sisa utang yang bisa dibayar pada penerimaan ini.</p>:null}
   {!canCreate||!data.can_create?<p>Pembayaran supplier hanya dapat dicatat Owner/Admin dengan hak bayar utang.</p>:null}
  </>:null}
  {data?.eligible&&data.can_create&&canCreate?<form aria-label="Pembayaran supplier baru" onSubmit={e=>{e.preventDefault();save()}} onChange={()=>setReview(false)}><fieldset className="cproc-fieldset" disabled={disabled}>
   <p>Pembayaran disahkan langsung: kas/bank berkurang dan sisa utang turun pada tanggal bayar. Bila sisa utang berubah sebelum disahkan, pembayaran ditolak dan formulir dimuat ulang. Nomor pembayaran dibuat server.</p>
   <div className="cproc-grid"><label>Nominal dibayar<input aria-label="Nominal pembayaran supplier baru" inputMode="decimal" value={amount} onChange={e=>setAmount(e.target.value)}/></label><label>Waktu pembayaran · WIB<input aria-label="Waktu pembayaran supplier baru WIB" type="datetime-local" value={at} onChange={e=>setAt(e.target.value)}/></label></div>
   {amount&&!validAmount?<p role="alert">Isi nominal positif dengan maksimal dua desimal, paling banyak sisa utang.</p>:null}
   {at&&!validTime?<p role="alert">Waktu pembayaran harus sesudah barang diterima dan tidak di masa depan.</p>:null}
   <label>Cari kas atau rekening<input aria-label="Cari rekening pembayaran supplier baru" maxLength={120} value={search} onChange={e=>setSearch(e.target.value)} onKeyDown={e=>{if(e.key==='Enter'){e.preventDefault();query.current={bank_q:search.trim(),bank_offset:0};void loadRef.current()}}}/></label><button type="button" onClick={()=>{query.current={bank_q:search.trim(),bank_offset:0};void loadRef.current()}}>Cari rekening pembayaran supplier</button>
   <section aria-label="Rekening pembayaran supplier baru">{data.cash_accounts.rows.map(b=><button type="button" key={b.id} aria-pressed={bank?.id===b.id} onClick={()=>{setBank({id:b.id,name:b.name});setReview(false)}}>{b.code} · {b.name}</button>)}{!data.cash_accounts.rows.length?<p>Tidak ada rekening aktif sesuai pencarian.</p>:null}<div className="cproc-pagination"><span>Total {data.cash_accounts.total} rekening</span><button type="button" disabled={!data.cash_accounts.offset} onClick={()=>seek(Math.max(0,data.cash_accounts.offset-25))}>Rekening pembayaran sebelumnya</button><button type="button" disabled={data.cash_accounts.next_offset===null} onClick={()=>seek(data.cash_accounts.next_offset??0)}>Rekening pembayaran berikutnya</button></div></section>
   <p>Rekening terpilih: {bank?.name??'belum dipilih'}</p><label>Keterangan pembayaran<input aria-label="Keterangan pembayaran supplier baru" maxLength={500} value={note} onChange={e=>setNote(e.target.value)}/></label>
   <label><input type="checkbox" aria-label="Pembayaran supplier baru sudah diperiksa" checked={review} onChange={e=>{e.stopPropagation();setReview(e.target.checked)}}/>Nominal, waktu, rekening dan keterangan sudah saya periksa.</label><button disabled={!valid}>Sahkan pembayaran supplier</button>
  </fieldset></form>:null}
 </section>
}
