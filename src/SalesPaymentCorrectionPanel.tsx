import {useCallback,useEffect,useMemo,useRef,useState} from 'react'
import {useAuth} from './auth/AuthProvider'
import {isConnectedRuntime} from './config/runtime'
import {getUatSupabaseClient} from './lib/supabase'
import {normalizeClientError} from './lib/clientError'
import {cp6WibDateTimeInput,cp6WibPhysicalTimeToIso,formatCp6WibDateTime} from './cp6BusinessTime'
import {formatReceiptDecimal} from './procurementContract'
import {salesCashAmount,salesCashCents,signedSalesCashCents,type SalesPayment} from './salesCashContract'
import {parsePaymentCorrectionWorkspace,type PaymentCorrectionWorkspace} from './salesPaymentCorrectionContract'
import TransactionSourceLink from './TransactionSourceNavigation'
import type {SalesRead} from './salesReadContract'
import type {Json} from './types/database.preconnect'
type Source=NonNullable<SalesRead['detail']>
type Props={source:Source;payment:SalesPayment;edit:boolean;locked:boolean;stale:boolean;onClose:()=>void;onSave:(action:'PAYMENT_CORRECT',document:Json,version:string)=>void}
const money=(v:string)=>`Rp${formatReceiptDecimal(v)}`
export default function SalesPaymentCorrectionPanel({source,payment,edit:initialEdit,locked,stale,onClose,onSave}:Props){
 const {runtime,identity}=useAuth();if(!isConnectedRuntime(runtime)||identity.status!=='AUTHORIZED')throw Error('Sesi koreksi pembayaran belum siap.')
 const client=useMemo(()=>getUatSupabaseClient(runtime),[runtime]),seq=useRef(0),initialized=useRef(false),query=useRef({bank_q:'',bank_offset:0})
 const [data,setData]=useState<PaymentCorrectionWorkspace|null>(null),[busy,setBusy]=useState(false),[error,setError]=useState(''),[edit,setEdit]=useState(initialEdit)
 const [amount,setAmount]=useState(''),[at,setAt]=useState(''),[timeEdited,setTimeEdited]=useState(false),[bank,setBank]=useState<{id:string;name:string|null}|null>(null),[method,setMethod]=useState('BANK_TRANSFER'),[reference,setReference]=useState(''),[notes,setNotes]=useState(''),[reason,setReason]=useState(''),[review,setReview]=useState(false),[search,setSearch]=useState('')
 const prefill=useCallback((d:SalesPayment)=>{setAmount(d.amount);setAt(cp6WibDateTimeInput(d.physical_at));setTimeEdited(false);setBank(d.cash_account_id?{id:d.cash_account_id,name:d.cash_account_name}:null);setMethod(d.method??'BANK_TRANSFER');setReference(d.reference??'');setNotes(d.notes??'');setReason('');setReview(false)},[])
 const [restoredAt,setRestoredAt]=useState<string|null>(null)
 const load=useCallback(async()=>{
  const ticket=++seq.current,p={...query.current};setData(null);setBusy(true);setError('');setReview(false)
  try{const r=await client.rpc('erp_cp7_get_sales_payment_correction_v1',{p_query:{sale_id:source.id,payment_id:payment.id,...p,bank_limit:25}});if(ticket!==seq.current)return;if(r.error)throw r.error
   const parsed=parsePaymentCorrectionWorkspace(r.data,source,payment.id,p.bank_offset);setData(parsed)
   if(!initialized.current){initialized.current=true;prefill(parsed.document)}
  }catch(e){if(ticket===seq.current)setError(normalizeClientError(e).message)}finally{if(ticket===seq.current)setBusy(false)}
 },[client,source,payment.id,prefill])
 useEffect(()=>{void load();return()=>{++seq.current}},[load])
 const canCorrect=['OWNER','ADMIN'].includes(identity.profile.role)&&['sales.invoice.view','finance.ar.view','sales.payment.view','sales.payment.create','sales.payment.post','sales.payment.reverse'].every(p=>identity.permissions.includes(p))
 const disabled=locked||stale||busy||!data,original=data?.document,exact=salesCashAmount(amount)
 const physical=timeEdited?cp6WibPhysicalTimeToIso(at):restoredAt??original?.physical_at??null
 const available=source.financial?.open_balance,maximum=available!==null&&available!==undefined&&original?signedSalesCashCents(available)+salesCashCents(original.amount):null
 const validAmount=exact!==null&&salesCashCents(exact)>0n&&maximum!==null&&salesCashCents(exact)<=maximum
 const changed=original&&(exact!==null&&salesCashCents(exact)!==salesCashCents(original.amount)||physical!==original.physical_at||bank?.id!==original.cash_account_id||method!==original.method||(reference||null)!==original.reference||(notes||null)!==original.notes)
 const valid=!disabled&&canCorrect&&data?.eligible&&Boolean(changed)&&validAmount&&physical&&bank&&['CASH','BANK_TRANSFER'].includes(method)&&reason.trim().length>=5&&review
 const save=()=>{if(!valid||!original||!source.review_token)return
  onSave('PAYMENT_CORRECT',{sale_id:source.id,payment_id:original.id,review_token:source.review_token,change_reason:reason.trim(),replacement:{payment_number:original.number,payment_date:physical!,amount:exact!,cash_account_id:bank!.id,payment_method:method,reference_number:reference||null,notes:notes||null}},source.row_version)
 }
 const restore=()=>{if(disabled||!data?.eligible||!data.previous||!canCorrect)return;prefill(data.previous.document);setRestoredAt(data.previous.document.physical_at);setEdit(true)}
 return <section className="panel" aria-label="Koreksi pembayaran tercatat">
  <div className="cproc-heading"><div><h3>{edit?'Edit pembayaran':'Perubahan pembayaran'} {payment.number}</h3><p>Invoice {source.number}</p></div><button disabled={locked} onClick={onClose}>Tutup perubahan pembayaran</button></div>
  <button disabled={locked||stale||busy} onClick={()=>void load()}>Muat ulang perubahan pembayaran</button>
  {error?<p role="alert">{error}</p>:null}{busy?<p role="status">Memuat sumber dan perubahan pembayaran…</p>:null}{stale?<p role="alert">Invoice berubah. Muat ulang invoice sebelum melanjutkan.</p>:null}
  {data&&!stale?<>
   <p>{data.document.number} · {money(data.document.amount)} · {formatCp6WibDateTime(data.document.physical_at)} · {data.document.cash_account_name??'Rekening tidak tercatat'} · {data.document.status==='REVERSED'?'Dibatalkan':data.document.status==='POSTED'?'Tercatat':'Draft'}</p>
   <p>Data diperiksa {formatCp6WibDateTime(data.captured_at)}. Riwayat pembayaran asal tetap tersimpan.</p>
   {data.previous?<section aria-label="Pembayaran sebelum koreksi"><h4>Sebelum koreksi</h4><p>{data.previous.document.number} · {money(data.previous.document.amount)} · {formatCp6WibDateTime(data.previous.document.physical_at)}</p><p>{data.previous.link.reason}</p><TransactionSourceLink sourceType="SALES_PAYMENT" sourceId={data.previous.document.id} label="Buka pembayaran sebelum koreksi" disabled={disabled}/></section>:null}
   {data.next?<section aria-label="Pembayaran pengganti"><h4>Pengganti</h4><p>{data.next.document.number} · {money(data.next.document.amount)}</p><p>{data.next.link.reason}</p><TransactionSourceLink sourceType="SALES_PAYMENT" sourceId={data.next.document.id} label="Buka pembayaran pengganti" disabled={disabled}/></section>:null}
   {!data.previous&&!data.next?<p>Belum ada koreksi yang mengganti pembayaran ini.</p>:null}
   {!data.eligible?<p>Pembayaran ini belum dapat diedit lewat alur pembayaran biasa. Uang muka, pengalihan antar-invoice, draft dan pembayaran yang sudah dibatalkan mengikuti alurnya masing-masing.</p>:null}
   {data.eligible&&canCorrect&&!edit?<button disabled={disabled} onClick={()=>{setEdit(true);setReview(false)}}>Edit pembayaran tercatat</button>:null}
   {data.eligible&&canCorrect&&data.previous?<button disabled={disabled} onClick={restore}>Pulihkan isi pembayaran sebelum koreksi</button>:null}
  </>:null}
  {edit&&canCorrect&&data?.eligible?<form aria-label="Edit pembayaran pelanggan" onSubmit={e=>{e.preventDefault();save()}} onChange={()=>setReview(false)}><fieldset className="cproc-fieldset" disabled={disabled}>
   <p>Pembayaran lama dibalik dan pengganti dicatat dalam satu tindakan. Jika salah satu langkah ditolak, seluruh koreksi dibatalkan. Pengganti mendapat nomor K dengan jejak ke pembayaran asal.</p>
   <div className="cproc-grid"><label>Nominal diterima<input aria-label="Nominal koreksi pembayaran" inputMode="decimal" value={amount} onChange={e=>setAmount(e.target.value)}/></label><label>Waktu pembayaran · WIB<input aria-label="Waktu koreksi pembayaran WIB" type="datetime-local" value={at} onChange={e=>{setAt(e.target.value);setTimeEdited(true);setRestoredAt(null)}}/></label><label>Metode<select aria-label="Metode koreksi pembayaran" value={method} onChange={e=>setMethod(e.target.value)}><option value="BANK_TRANSFER">Transfer bank</option><option value="CASH">Tunai</option></select></label></div>
   {maximum!==null?<p>Batas nominal pengganti {money((maximum/100n).toString()+'.'+(maximum%100n).toString().padStart(2,'0'))} sesuai pembayaran yang diganti dan sisa invoice.</p>:null}
   {amount&&!validAmount?<p role="alert">Isi nominal positif dengan maksimal dua desimal, sesuai batas pengganti.</p>:null}
   <div className="cproc-search"><label>Cari kas atau rekening<input aria-label="Cari rekening koreksi pembayaran" value={search} maxLength={120} onChange={e=>setSearch(e.target.value)} onKeyDown={e=>{if(e.key==='Enter'){e.preventDefault();query.current={bank_q:search.trim(),bank_offset:0};void load()}}}/></label><button type="button" onClick={()=>{query.current={bank_q:search.trim(),bank_offset:0};void load()}}>Cari rekening koreksi pembayaran</button></div>
   <section aria-label="Rekening koreksi pembayaran">{data.cash_accounts.rows.map(b=><button className="cproc-receipt" type="button" key={b.id} aria-pressed={bank?.id===b.id} onClick={()=>{setBank({id:b.id,name:b.name});setReview(false)}}><span><strong>{b.code} · {b.name}</strong><small>{b.kind}</small></span></button>)}{data.cash_accounts.rows.length===0?<p>Tidak ada rekening aktif sesuai pencarian.</p>:null}<div className="cproc-pagination"><span>Total {data.cash_accounts.total} rekening</span><button type="button" disabled={data.cash_accounts.offset===0} onClick={()=>{query.current.bank_offset=Math.max(0,data.cash_accounts.offset-25);void load()}}>Rekening koreksi sebelumnya</button><button type="button" disabled={data.cash_accounts.next_offset===null} onClick={()=>{query.current.bank_offset=data.cash_accounts.next_offset??0;void load()}}>Rekening koreksi berikutnya</button></div></section>
   <p>Rekening terpilih: {bank?.name??'belum dipilih'}</p><label>Referensi<input aria-label="Referensi koreksi pembayaran" value={reference} maxLength={100} onChange={e=>setReference(e.target.value)}/></label><label>Catatan<input aria-label="Catatan koreksi pembayaran" value={notes} maxLength={2000} onChange={e=>setNotes(e.target.value)}/></label>
   <label>Alasan koreksi<input aria-label="Alasan koreksi pembayaran" value={reason} maxLength={1000} onChange={e=>setReason(e.target.value)}/></label><label className="cproc-check"><input type="checkbox" aria-label="Koreksi pembayaran sudah diperiksa" checked={review} onChange={e=>{e.stopPropagation();setReview(e.target.checked)}}/>Pembayaran asal, isi pengganti dan alasan sudah saya periksa.</label>
   <button className="primary-btn" disabled={!valid}>Simpan koreksi pembayaran</button>
  </fieldset></form>:null}
 </section>
}
