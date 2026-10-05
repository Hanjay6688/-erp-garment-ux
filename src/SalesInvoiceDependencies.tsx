import {useEffect,useRef,useState} from 'react'
import {useAuth} from './auth/AuthProvider'
import {hasPermission} from './auth/accessCatalog'
import {isConnectedRuntime} from './config/runtime'
import {getUatSupabaseClient} from './lib/supabase'
import {normalizeClientError} from './lib/clientError'
import {formatCp6WibDateTime} from './cp6BusinessTime'
import {formatReceiptDecimal as numberText} from './procurementContract'
import {parseSalesCash,type SalesCash} from './salesCashContract'
import {parseSalesReturns,type SalesReturnRead,type SalesReturnRecord} from './salesReturnContract'
import type {SalesRead} from './salesReadContract'
import TransactionSourceLink from './TransactionSourceNavigation'

type Source=NonNullable<SalesRead['detail']>
type Captured={scope:string;payments:SalesCash|null;returns:SalesReturnRead<SalesReturnRecord>|null}
export default function SalesInvoiceDependencies({source,current,locked}:{source:Source;current:boolean;locked:boolean}){
 const {runtime,identity}=useAuth(),access=identity.status==='AUTHORIZED'?identity:null
 const permitted=current&&hasPermission(access,'sales.invoice.view')&&hasPermission(access,'finance.ar.view')
 const canPayments=permitted&&hasPermission(access,'sales.payment.view'),canReturns=permitted&&hasPermission(access,'sales.return.view')
 const scope=JSON.stringify([isConnectedRuntime(runtime)?runtime.projectRef:null,access?.profile.authUserId,access?.profile.id,
  access?.profile.rowVersion,access?.profile.roleRowVersion,access?.permissions,source.id,source.number,source.row_version,source.review_token,permitted])
 const active=useRef(scope),serial=useRef(0);active.current=scope
 const [capture,setCapture]=useState<Captured|null>(null),[busy,setBusy]=useState(false),[error,setError]=useState<{scope:string;message:string}|null>(null)
 useEffect(()=>{++serial.current;setCapture(null);setBusy(false);setError(null);return()=>{++serial.current}},[scope])
 const data=permitted&&capture?.scope===scope?capture:null
 const currentError=permitted&&error?.scope===scope?error.message:''
 const load=async(paymentOffset=0,returnOffset=0)=>{
  if(!permitted||(!canPayments&&!canReturns)||busy||!isConnectedRuntime(runtime)||identity.status!=='AUTHORIZED')return
  const ticket=++serial.current,wanted=scope;setCapture(null);setBusy(true);setError(null)
  try{
   const client=getUatSupabaseClient(runtime)
   const [cash,returned]=await Promise.all([
    canPayments?client.rpc('erp_cp7_get_sales_cash_v1',{p_query:{sale_id:source.id,payment_offset:paymentOffset,payment_limit:25,bank_q:'',bank_offset:0,bank_limit:25}}):Promise.resolve(null),
    canReturns?client.rpc('erp_cp7_get_sales_returns_v1',{p_query:{sale_id:source.id,kind:'RETURNS',offset:returnOffset,q:'',limit:25}}):Promise.resolve(null)
   ])
   if(ticket!==serial.current||active.current!==wanted)return
   if(cash?.error)throw cash.error;if(returned?.error)throw returned.error
   const payments=cash?parseSalesCash(cash.data,source,paymentOffset):null,returns=returned?parseSalesReturns<SalesReturnRecord>(returned.data,'RETURNS',source,returnOffset):null
   setCapture({scope:wanted,payments,returns})
  }catch(failure){if(ticket===serial.current&&active.current===wanted)setError({scope:wanted,message:normalizeClientError(failure).message})}
  finally{if(ticket===serial.current&&active.current===wanted)setBusy(false)}
 }
 const payments=data?.payments?.payments,returns=data?.returns?.page,linksLocked=locked||busy||!permitted
 return <section className="cproc-review" aria-label={`Dokumen penghalang ${source.number}`}>
  <h3>Dokumen terkait pembatalan</h3><p>Periksa pembayaran dahulu, lalu retur, kemudian muat ulang invoice. Setiap pembatalan tetap diperiksa pada transaksi sumbernya.</p>
  <button type="button" disabled={!permitted||busy||(!canPayments&&!canReturns)} onClick={()=>void load()}>{busy?'Memeriksa dokumen terkait…':'Lihat dokumen penghalang'}</button>
  {!canPayments?<p>Izin lihat pembayaran diperlukan untuk membaca rincian pembayaran.</p>:null}{!canReturns?<p>Izin lihat retur diperlukan untuk membaca rincian retur.</p>:null}
  {!data&&!busy&&!currentError?<p>Rincian dokumen belum dimuat. Penghalang invoice tetap berlaku.</p>:null}
  {busy?<p role="status">Rincian sedang dimuat; jumlah dokumen aktif belum dipastikan.</p>:null}{currentError?<p role="alert">{currentError} Rincian belum dapat dipastikan. Muat ulang invoice jika sumber berubah.</p>:null}
  {payments?<section aria-label="Pembayaran penghalang invoice"><h4>Pembayaran tercatat</h4><p>{payments.total} pembayaran dalam riwayat. Yang ditampilkan adalah pembayaran aktif pada halaman yang dimuat.</p>
   {payments.rows.filter(p=>p.status==='POSTED').map(p=><article className="cproc-item" data-invoice-payment-dependency-id={p.id} key={p.id}><strong>{p.number}</strong><p>Rp{numberText(p.amount)} · {formatCp6WibDateTime(p.physical_at)}</p><TransactionSourceLink sourceType="SALES_PAYMENT" sourceId={p.id} disabled={linksLocked} label={`Buka pembayaran ${p.number}`}/></article>)}
   {!payments.rows.some(p=>p.status==='POSTED')?<p>Halaman ini tidak menampilkan pembayaran aktif.</p>:null}
   <div className="cproc-pagination"><button type="button" disabled={busy||payments.offset===0} onClick={()=>void load(Math.max(0,payments.offset-25),returns?.offset??0)}>Penghalang pembayaran sebelumnya</button><button type="button" disabled={busy||payments.next_offset===null} onClick={()=>void load(payments.next_offset??0,returns?.offset??0)}>Penghalang pembayaran berikutnya</button></div>
  </section>:null}
  {returns?<section aria-label="Retur penghalang invoice"><h4>Retur tercatat</h4><p>{returns.total} retur dalam riwayat. Yang ditampilkan adalah retur aktif pada halaman yang dimuat.</p>
   {returns.rows.filter(r=>r.status==='POSTED').map(r=><article className="cproc-item" data-invoice-return-dependency-id={r.id} key={r.id}><strong>{r.number}</strong><p>{numberText(r.line_count)} baris barang · {formatCp6WibDateTime(r.physical_at)}</p><TransactionSourceLink sourceType="SALES_RETURN" sourceId={r.id} disabled={linksLocked} label={`Buka retur ${r.number}`}/></article>)}
   {!returns.rows.some(r=>r.status==='POSTED')?<p>Halaman ini tidak menampilkan retur aktif.</p>:null}
   <div className="cproc-pagination"><button type="button" disabled={busy||returns.offset===0} onClick={()=>void load(payments?.offset??0,Math.max(0,returns.offset-25))}>Penghalang retur sebelumnya</button><button type="button" disabled={busy||returns.next_offset===null} onClick={()=>void load(payments?.offset??0,returns.next_offset??0)}>Penghalang retur berikutnya</button></div>
  </section>:null}
 </section>
}
