import {useCallback,useEffect,useMemo,useRef,useState}from 'react'
import {useAuth}from './auth/AuthProvider'
import {isConnectedRuntime}from './config/runtime'
import {getUatSupabaseClient}from './lib/supabase'
import {normalizeClientError}from './lib/clientError'
import {formatReceiptDecimal}from './procurementContract'
import {cp6WibDateTimeInput}from './cp6BusinessTime'
import {useProductionMutation,type ProductionMutationHandlers}from './useProductionMutation'
import ProductionRecoveryNotice from './ProductionRecoveryNotice'
import {financialRecoveryBlocked,useFinancialRecoveryGate}from './useFinancialRecoveryGate'
import {parseInstallmentRead,parseInstallmentOutcome,validInstallmentAmount,type InstallmentAction,type InstallmentCash,type InstallmentDocument,type InstallmentPayment,type InstallmentRead}from './payrollInstallmentContract'
import type{Json}from './types/database.preconnect'
const money=(v:string)=>`Rp${formatReceiptDecimal(v)}`
const labels={NOT_APPROVED:'Belum disetujui',UNPAID:'Belum dibayar',PARTIAL:'Dibayar sebagian',PAID:'Lunas',REVERSED:'Dibatalkan'}
type Props={parentReady:boolean;payrollId:string|null;readRevision:number;onRetire:()=>void;onReload:()=>Promise<boolean>;onTarget:(id:string)=>void;onSource:(d:InstallmentDocument|null)=>void}
function pendingId(payload:Json|undefined){if(!payload||typeof payload!=='object'||Array.isArray(payload))return null;const d=payload.document;if(!d||typeof d!=='object'||Array.isArray(d))return null;return typeof d.payroll_id==='string'?d.payroll_id:null}
export default function PayrollInstallmentPanel({parentReady,payrollId,readRevision,onRetire,onReload,onTarget,onSource}:Props){
 const{runtime,identity}=useAuth();if(!isConnectedRuntime(runtime)||identity.status!=='AUTHORIZED')throw Error('Sesi payroll belum siap.')
 const client=useMemo(()=>getUatSupabaseClient(runtime),[runtime]),mutation=useProductionMutation('PAYROLL_INSTALLMENT'),{beginRead,finishRead,isReadCurrent,run,reconcile}=mutation
 const[data,setData]=useState<InstallmentRead|null>(null),[busy,setBusy]=useState(false),[error,setError]=useState(''),[action,setAction]=useState<InstallmentAction|null>(null),[chosenPayment,setChosenPayment]=useState<InstallmentPayment|null>(null)
 const[amount,setAmount]=useState(''),[date,setDate]=useState(cp6WibDateTimeInput().slice(0,10)),[reason,setReason]=useState(''),[review,setReview]=useState(false),[bank,setBank]=useState<InstallmentCash|null>(null),[cashQuery,setCashQuery]=useState('')
 const selected=payrollId??pendingId(mutation.pending?.payload),seq=useRef(0),query=useRef({id:selected,payment_offset:0,cash_offset:0,cash_query:''})
 if(query.current.id!==selected)query.current={id:selected,payment_offset:0,cash_offset:0,cash_query:''}
 const retire=useCallback(()=>{++seq.current;setData(null);setBusy(false);setReview(false);setBank(null);onSource(null)},[onSource])
 const blocked=useFinancialRecoveryGate(mutation.scope,retire)
 const pay=identity.permissions.includes('finance.payroll.pay'),reversePayroll=pay&&identity.permissions.includes('finance.payroll.approve')
 const load=useCallback(async()=>{
  retire();setBusy(false);setError('')
  const f={...query.current};if(!f.id||financialRecoveryBlocked(mutation.scope))return false
  const s=++seq.current,ticket=beginRead();setBusy(true)
  try{
   const r=await client.rpc('erp_cp7_get_payroll_installments_v1',{p_query:{payroll_id:f.id,payment_offset:f.payment_offset,cash_offset:f.cash_offset,cash_query:f.cash_query}})
   if(s!==seq.current||!isReadCurrent(ticket)||financialRecoveryBlocked(mutation.scope))return false
   if(r.error)throw r.error
   const next=parseInstallmentRead(r.data,f.id)
   if(next.payments.offset!==f.payment_offset||next.cash_accounts.offset!==f.cash_offset||next.capabilities.pay!==pay||next.capabilities.reverse_payroll!==reversePayroll)throw Error('Pilihan payroll atau hak pembayaran berubah. Muat ulang pembayaran.')
   if(!finishRead(ticket))return false
   setData(next);onSource(next.document);return true
  }catch(e){if(s===seq.current&&isReadCurrent(ticket))setError(normalizeClientError(e).message);return false}finally{if(s===seq.current)setBusy(false)}
 },[client,mutation.scope,pay,reversePayroll,beginRead,finishRead,isReadCurrent,retire,onSource])
 useEffect(()=>{setAction(null);if(parentReady)void load();else{retire();mutation.invalidate()}return()=>{++seq.current}},[load,selected,readRevision,parentReady,retire,mutation.invalidate])
 const visible=parentReady&&!blocked&&data?.document.payroll_id===selected?data:null,h=visible?.document,locked=busy||mutation.writerLocked
 const handlers:ProductionMutationHandlers={send:e=>{const p=e.payload as{document:Json;expected_version:string};return client.rpc('erp_cp7_save_payroll_installment_v1',{p_action:e.action,p_payload:p.document,p_request:e.id,p_expected:p.expected_version})},validate:(v,e)=>{parseInstallmentOutcome(v,e.id,e.action,e.payload)},retire:(v,e)=>{const r=parseInstallmentOutcome(v,e.id,e.action,e.payload);query.current.id=r.payroll_id;query.current.payment_offset=0;setAction(null);retire();onTarget(r.payroll_id);onRetire()},reload:async()=>{if(!await onReload()){retire();mutation.invalidate();return false}return load()}}
 const start=(type:InstallmentAction,payment:InstallmentPayment|null=null)=>{setAction(type);setChosenPayment(payment);setAmount(h?.remaining_amount??'');setDate(cp6WibDateTimeInput().slice(0,10));setReason('');setReview(false);setBank(null)}
 const write=()=>{
  if(!h||!action||locked||!review||reason.trim().length<5)return
  const document:Json={payroll_id:h.payroll_id,review_token:h.review_token,change_reason:reason.trim(),...(action==='PAY'?{amount,payment_date:date,cash_account_id:bank?.id??null,cash_review_token:bank?.review_token??null}:action==='REVERSE_PAYMENT'?{payment_id:chosenPayment?.id??null}:{})},version=h.row_version,chosen=action
  setAction(null);retire();onRetire();void run(chosen,{document,expected_version:version},null,handlers)
 }
 const canPay=Boolean(h&&h.native_status==='APPROVED'&&h.remaining_amount&&validInstallmentAmount(h.remaining_amount,h.remaining_amount)&&pay)
 const canSubmit=Boolean(h&&action&&review&&reason.trim().length>=5&&(action!=='PAY'||bank&&h.remaining_amount&&validInstallmentAmount(amount,h.remaining_amount)&&date&&date<=cp6WibDateTimeInput().slice(0,10)))
 return <section className="panel cpay-detail" aria-label="Pembayaran gaji"><header className="cpay-actions"><h2>Pembayaran gaji</h2><button disabled={busy||mutation.busy||blocked}onClick={()=>{setAction(null);retire();void(async()=>{if(await onReload())await load();else mutation.invalidate()})()}}>Muat ulang pembayaran</button></header>
  <ProductionRecoveryNotice recovery={mutation}className="cpay-action"onReconcile={()=>reconcile(handlers)}noticeText="Pembayaran tersimpan. Catatan terbaru sudah dimuat."messageText={mutation.pending&&!mutation.corruptedEnvelope?'Status pembayaran gaji belum pasti. Periksa pembayaran yang sama sebelum mencatat pembayaran lain.':undefined}reconcileLabel="Periksa status pembayaran gaji"/>
  {error?<p role="alert">{error}</p>:null}{busy?<p role="status">Memuat pembayaran gaji…</p>:null}
  {!selected&&!mutation.pending?<p>Pilih payroll untuk melihat pembayaran dan sisa gajinya.</p>:null}
  {h&&visible?<><p><strong>{h.contractor_name} · {h.payroll_number}</strong> · {labels[h.payment_state]}</p>
   {h.payment_state==='NOT_APPROVED'?<p>Payroll perlu disetujui sebelum gaji dibayar.</p>:<><dl className="cpay-totals"><div><dt>Gaji bersih yang disetujui</dt><dd>{money(h.approved_net)}</dd></div><div><dt>Sudah dibayar</dt><dd>{money(h.paid_amount)}</dd></div>{h.remaining_amount!==null?<div className="cpay-net"><dt>Sisa gaji</dt><dd>{money(h.remaining_amount)}</dd></div>:null}</dl>{h.payment_state==='REVERSED'?<p>Payroll sudah dibatalkan. Catatan pembayaran berikut tetap tersimpan sebagai riwayat.</p>:<p>Gaji yang disetujui tetap. Setiap pembayaran mengurangi sisa gaji di payroll ini.</p>}</>}
   {canPay?<button className="primary-btn"disabled={locked}onClick={()=>start('PAY')}>Bayar gaji</button>:null}
   {h.managed&&reversePayroll&&['APPROVED','PAID'].includes(h.native_status)?<button disabled={locked}onClick={()=>start('REVERSE_PAYROLL')}>Batalkan payroll dan pembayaran</button>:null}
   {action?<section className="cpay-action"aria-label="Periksa pembayaran gaji"><h3>{action==='PAY'?'Bayar sebagian atau seluruh sisa gaji':action==='REVERSE_PAYMENT'?'Balikkan pembayaran ini':'Batalkan payroll dan seluruh pembayaran'}</h3>
    <p>{action==='PAY'?'Catat jumlah uang yang benar-benar dibayar dari akun yang dipilih.':action==='REVERSE_PAYMENT'?`Pembayaran ${chosenPayment?money(chosenPayment.amount):''} akan dibalik. Catatan asli tetap tersimpan dan sisa gaji bertambah kembali.`:'Seluruh pembayaran dan persetujuan biaya dibalik. Payroll menjadi dibatalkan; dokumen sumber tetap tersimpan.'}</p>
    <fieldset disabled={locked}>
     {action==='PAY'?<><label>Jumlah yang dibayar<input aria-label="Jumlah pembayaran gaji"inputMode="decimal"value={amount}onChange={e=>{setAmount(e.target.value);setReview(false)}}/></label><label>Tanggal pembayaran · WIB<input aria-label="Tanggal cicilan gaji"type="date"max={cp6WibDateTimeInput().slice(0,10)}value={date}onChange={e=>{setDate(e.target.value);setReview(false)}}/></label>
      <div className="cpay-cash"><label>Cari akun kas atau bank<input aria-label="Cari akun cicilan gaji"maxLength={120}value={cashQuery}onChange={e=>setCashQuery(e.target.value)}/></label><button onClick={()=>{query.current.cash_query=cashQuery.trim();query.current.cash_offset=0;void load()}}>Cari akun cicilan</button>{visible.cash_accounts.rows.map(c=><button className="cpay-cash-row"key={c.id}aria-pressed={bank?.id===c.id}onClick={()=>{setBank(c);setReview(false)}}>{c.code} · {c.name}{bank?.id===c.id?' · Dipilih':''}</button>)}<Pager label="Akun cicilan"page={visible.cash_accounts}busy={locked}change={offset=>{query.current.cash_offset=offset;void load()}}/>{bank?<p>Akun pembayaran: <strong>{bank.name}</strong></p>:<p>Pilih akun aktif untuk pembayaran.</p>}</div>
     </>:null}
     <label>Alasan tindakan<textarea aria-label="Alasan pembayaran gaji"maxLength={1000}value={reason}onChange={e=>{setReason(e.target.value);setReview(false)}}/></label><label className="cpay-check"><input type="checkbox"aria-label="Pembayaran gaji sudah diperiksa"checked={review}onChange={e=>setReview(e.target.checked)}/>Jumlah, akun, tanggal, dan tindakan ini sudah saya periksa.</label>
     <div className="cpay-actions"><button className="primary-btn"disabled={!canSubmit}onClick={write}>{action==='PAY'?'Catat pembayaran gaji':action==='REVERSE_PAYMENT'?'Balikkan pembayaran sekarang':'Batalkan payroll sekarang'}</button><button onClick={()=>setAction(null)}>Kembali ke pembayaran</button></div>
    </fieldset></section>:null}
   <h3>Riwayat pembayaran</h3>{!h.managed&&h.native_status==='PAID'?<p>Pembayaran penuh sebelumnya tercatat pada payroll ini. Gunakan koreksi payroll lunas untuk membalik seluruh payroll.</p>:null}
   {visible.payments.rows.map(p=><article className="cpay-line"key={p.id}><header><strong>{money(p.amount)}</strong><strong>{p.status==='POSTED'?'Tercatat':'Dibalik'}</strong></header><p>{p.payment_date} · {p.cash_account_code} · {p.cash_account_name}</p><p className="cpay-reference">{p.journal_number} · Tanggal pembukuan {p.accounting_date}{p.period_shifted?' · Beralih ke periode terbuka':''}</p>{p.reversal_journal_id?<p className="cpay-reference">Pembalik {p.reversal_journal_number} · {p.reversal_accounting_date}</p>:null}{pay&&p.status==='POSTED'&&['APPROVED','PAID'].includes(h.native_status)?<button disabled={locked}onClick={()=>start('REVERSE_PAYMENT',p)}>Balikkan pembayaran {p.journal_number}</button>:null}</article>)}{!visible.payments.rows.length&&h.managed?<p>Tidak ada pembayaran pada halaman ini.</p>:null}<Pager label="Pembayaran"page={visible.payments}busy={locked}change={offset=>{query.current.payment_offset=offset;setAction(null);void load()}}/>
  </>:null}
 </section>
}
function Pager({label,page,busy,change}:{label:string;page:{total:string;offset:number;next_offset:number|null};busy:boolean;change:(n:number)=>void}){return <div className="cproc-pagination"><span>Total {page.total}</span><button disabled={busy||!page.offset}onClick={()=>change(Math.max(0,page.offset-25))}>{label} sebelumnya</button><button disabled={busy||page.next_offset===null}onClick={()=>change(page.next_offset??0)}>{label} berikutnya</button></div>}
