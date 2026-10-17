import {useCallback,useEffect,useMemo,useRef,useState} from 'react'
import {useAuth} from './auth/AuthProvider'
import {hasPermission,PAGE_PERMISSION_BY_ID} from './auth/accessCatalog'
import {isConnectedRuntime} from './config/runtime'
import {getUatSupabaseClient} from './lib/supabase'
import {normalizeClientError} from './lib/clientError'
import {cp6WibDateTimeInput,formatCp6WibDateTime} from './cp6BusinessTime'
import {formatReceiptDecimal} from './procurementContract'
import {parseHistoryDetail,parseHistoryList,type HistoryDetail,type HistoryEvent,type HistoryInvoice,type HistoryList} from './customerHistoryContract'
import {financialRecoveryBlocked,financialRecoveryMessage,useFinancialRecoveryGate} from './useFinancialRecoveryGate'
import RecordTools,{orderRecordPage,type RecordPageOrder} from './RecordTools'
import './procurement-connected.css'
import './customer-history.css'

// R3-03 (owner D16-1): Riwayat Pelanggan on real data, read only, through erp_cp7_get_customer_history_v1.
// Reading needs sales.history.view (the page key of the access catalog); amounts need finance.ar.view and the server's
// own capture of it; the download of the rows on screen needs sales.history.export and the server's can_export.
const VIEW=PAGE_PERMISSION_BY_ID['sales-history'],AMOUNTS='finance.ar.view',EXPORT='sales.history.export'
const LIMIT=25
const invoiceLabel:Record<string,string>={DRAFT:'Draf · belum menjadi piutang',POSTED:'Belum dibayar',PARTIAL_PAID:'Dibayar sebagian',PAID:'Lunas',CANCELLED:'Draf dibatalkan',REVERSED:'Invoice dibatalkan'}
const documentLabel:Record<string,string>={DRAFT:'Draf · belum tercatat',POSTED:'Tercatat',REVERSED:'Dibatalkan'}
const methodLabel:Record<string,string>={CASH:'Tunai',BANK_TRANSFER:'Transfer bank'}
const kindLabel:Record<string,string>={INVOICE:'Invoice',PAYMENT:'Pembayaran',RETURN:'Retur',CANCELLATION:'Pembatalan'}
const rp=(value:string)=>'Rp'+formatReceiptDecimal(value)
const balanceLabel=(value:string)=>value.startsWith('-')?'Kredit pelanggan':'Sisa tagihan'
const statusLabel=(e:HistoryEvent)=>e.document==='INVOICE'?invoiceLabel[e.status]??e.status:documentLabel[e.status]??e.status

export function historyErrorMessage(error:unknown){
 const raw=typeof (error as {message?:unknown})?.message==='string'?String((error as {message:string}).message):''
 if(raw.includes('CP7_CUSTOMER_HISTORY_DENIED'))return 'Akun ini tidak memiliki hak melihat riwayat pelanggan.'
 if(raw.includes('CP7_CUSTOMER_HISTORY_NOT_FOUND'))return 'Pelanggan ini tidak ditemukan. Muat ulang daftar pelanggan.'
 if(raw.includes('CP7_CUSTOMER_HISTORY_INCOMPLETE'))return 'Riwayat pelanggan ini belum bisa dibaca lengkap: waktu pembatalan sebuah dokumen tidak tercatat. Laporkan ke admin; tidak ada angka yang ditampilkan.'
 if(raw.includes('CP7_CUSTOMER_HISTORY_QUERY'))return 'Pencarian tidak bisa dibaca. Periksa kata pencarian (paling banyak 120 huruf) lalu cari lagi.'
 return normalizeClientError(error).message
}

export function eventTitle(e:HistoryEvent){
 if(e.kind==='CANCELLATION')return e.document==='INVOICE'?(e.status==='CANCELLED'?`Draf invoice ${e.number} dibatalkan`:`Invoice ${e.number} dibatalkan`):`${kindLabel[e.document]} ${e.number} dibatalkan`
 if(e.kind==='INVOICE'&&(e.status==='DRAFT'||e.status==='CANCELLED'))return `Draf invoice ${e.number}`
 return `${kindLabel[e.kind]} ${e.number}`
}
function eventLine(e:HistoryEvent){
 if(e.document==='INVOICE')return [`${e.qty_pcs} pcs`,e.location_name,e.kind==='INVOICE'?statusLabel(e):`invoice ${e.invoice_number}`].filter(Boolean).join(' · ')
 if(e.document==='PAYMENT')return [`untuk invoice ${e.invoice_number}`,e.method?methodLabel[e.method]??e.method:null,statusLabel(e)].filter(Boolean).join(' · ')
 return [`${e.qty_pcs} pcs dari invoice ${e.invoice_number}`,statusLabel(e)].join(' · ')
}
function invoiceLine(i:HistoryInvoice,amounts:boolean){
 const head=`Invoice ${i.number} sekarang: ${invoiceLabel[i.status]}`
 if(!amounts||!i.financial)return head
 const f=i.financial
 if(f.state!=='ACTIVE_RECEIVABLE'||f.open_balance===null)return `${head} · nilai ${rp(f.gross_total)}, bukan piutang aktif`
 return `${head} · nilai ${rp(f.gross_total)} · retur ${rp(f.return_total)} · dibayar ${rp(f.paid_total)} · ${balanceLabel(f.open_balance).toLowerCase()} ${rp(f.open_balance)}`
}

// The rows on screen only, for a spreadsheet. Text that a spreadsheet would run as a formula is kept as text.
export function historyCsv(rows:HistoryEvent[],invoices:HistoryInvoice[],amounts:boolean){
 const byId=new Map(invoices.map(i=>[i.id,i]))
 const cell=(value:string|null,textual=true)=>{const v=value??'';const safe=textual&&/^[=+\-@\t\r]/.test(v)?`'${v}`:v;return `"${safe.replace(/"/g,'""')}"`}
 const head=['Waktu (WIB)','Kejadian','Dokumen','Nomor','Invoice','Status dokumen','Status invoice sekarang','Jumlah pcs',...(amounts?['Nilai (Rp)','Sisa invoice (Rp)']:[])]
 const lines=rows.map(e=>{const i=byId.get(e.invoice_id);return [
  cell(cp6WibDateTimeInput(e.at).replace('T',' ')),cell(kindLabel[e.kind]),cell(kindLabel[e.document]),cell(e.number),cell(e.invoice_number),cell(statusLabel(e)),
  cell(i?invoiceLabel[i.status]:''),cell(e.qty_pcs,false),
  ...(amounts?[cell(e.financial?.amount??'',false),cell(i?.financial?.open_balance??'',false)]:[])].join(',')})
 return [head.map(h=>cell(h)).join(','),...lines].join('\r\n')+'\r\n'
}

export default function ConnectedCustomerHistoryPage(){
 const {runtime,identity}=useAuth()
 if(!isConnectedRuntime(runtime)||identity.status!=='AUTHORIZED'||!hasPermission(identity,VIEW))return <section className="panel" role="alert">Hak melihat riwayat pelanggan diperlukan.</section>
 return <Workspace key={`${runtime.projectRef}:${identity.profile.id}:${identity.profile.rowVersion}:${identity.profile.roleRowVersion}:${identity.permissions.join('|')}`}/>
}

type ListQuery={q:string;offset:number}
function Workspace(){
 const {runtime,identity}=useAuth();if(!isConnectedRuntime(runtime)||identity.status!=='AUTHORIZED')throw Error('Sesi riwayat pelanggan belum siap.')
 const client=useMemo(()=>getUatSupabaseClient(runtime),[runtime])
 const amounts=hasPermission(identity,AMOUNTS),exporter=hasPermission(identity,EXPORT)
 const listSeq=useRef(0),detailSeq=useRef(0),listQuery=useRef<ListQuery>({q:'',offset:0}),chosen=useRef<{id:string;offset:number}|null>(null)
 const [q,setQ]=useState(''),[order,setOrder]=useState<RecordPageOrder>('SOURCE')
 const [list,setList]=useState<HistoryList|null>(null),[listBusy,setListBusy]=useState(false),[listError,setListError]=useState('')
 const [detail,setDetail]=useState<HistoryDetail|null>(null),[detailBusy,setDetailBusy]=useState(false),[detailError,setDetailError]=useState(''),[selected,setSelected]=useState<string|null>(null)
 const [exported,setExported]=useState('')
 const retire=useCallback(()=>{++listSeq.current;++detailSeq.current;setList(null);setDetail(null);setListBusy(false);setDetailBusy(false);setListError('');setDetailError('');setExported('')},[])
 const noop=useCallback(()=>{},[])
 const scope=`${runtime.projectRef}:${identity.profile.id}`,gate=useFinancialRecoveryGate(scope,amounts?retire:noop),blocked=amounts&&gate
 const loadList=useCallback(async(query:ListQuery)=>{
  const ticket=++listSeq.current;setList(null);setListBusy(true);setListError('')
  try{
   if(amounts&&financialRecoveryBlocked(scope))return
   const result=await client.rpc('erp_cp7_get_customer_history_v1',{p_query:{q:query.q,offset:query.offset,limit:LIMIT}})
   if(ticket!==listSeq.current||amounts&&financialRecoveryBlocked(scope))return
   if(result.error)throw result.error
   setList(parseHistoryList(result.data,{financial:amounts,offset:query.offset,limit:LIMIT}))
  }catch(e){if(ticket===listSeq.current)setListError(historyErrorMessage(e))}finally{if(ticket===listSeq.current)setListBusy(false)}
 },[amounts,client,scope])
 const loadDetail=useCallback(async(id:string,offset:number)=>{
  const ticket=++detailSeq.current;chosen.current={id,offset};setSelected(id);setDetail(null);setDetailBusy(true);setDetailError('');setExported('')
  try{
   if(amounts&&financialRecoveryBlocked(scope))return
   const result=await client.rpc('erp_cp7_get_customer_history_v1',{p_query:{customer_id:id,offset,limit:LIMIT}})
   if(ticket!==detailSeq.current||amounts&&financialRecoveryBlocked(scope))return
   if(result.error)throw result.error
   setDetail(parseHistoryDetail(result.data,{financial:amounts,offset,limit:LIMIT,customerId:id}))
  }catch(e){if(ticket===detailSeq.current)setDetailError(historyErrorMessage(e))}finally{if(ticket===detailSeq.current)setDetailBusy(false)}
 },[amounts,client,scope])
 useEffect(()=>{void loadList(listQuery.current);return()=>{++listSeq.current;++detailSeq.current}},[loadList])
 const search=(text:string)=>{listQuery.current={q:text,offset:0};void loadList(listQuery.current)}
 const reload=()=>{const text=q.trim();if(text!==listQuery.current.q)listQuery.current={q:text,offset:0};void loadList(listQuery.current);if(chosen.current)void loadDetail(chosen.current.id,chosen.current.offset)}
 const showAmounts=amounts&&detail?.financial_captured===true,listAmounts=amounts&&list?.financial_captured===true
 const canExport=exporter&&detail?.can_export===true&&detail.timeline.rows.length>0
 const download=()=>{
  if(!detail||!canExport)return
  const rows=detail.timeline.rows,from=detail.timeline.offset+1,to=detail.timeline.offset+rows.length
  const url=URL.createObjectURL(new Blob([historyCsv(rows,detail.invoices,showAmounts)],{type:'text/csv;charset=utf-8'}))
  const anchor=document.createElement('a');anchor.href=url;anchor.download=`Riwayat_${detail.customer.code}_${from}-${to}.csv`;anchor.click()
  setTimeout(()=>URL.revokeObjectURL(url),0);setExported(`${rows.length} baris yang tampil (kejadian ${from}–${to}) sudah diunduh.`)
 }
 const invoices=new Map((detail?.invoices??[]).map(i=>[i.id,i]))
 const busy=listBusy||detailBusy
 return <section className="cproc chistory" aria-label="Riwayat pelanggan dari dokumen penjualan">
  <header className="panel cproc-heading"><div><div className="eyebrow">PENJUALAN</div><h1>Riwayat Pelanggan</h1><p>Cari pelanggan, lalu lihat invoice, pembayaran, retur, dan pembatalannya, dari yang terbaru.</p></div><button disabled={busy||blocked} onClick={reload}>Muat ulang riwayat</button></header>
  <RecordTools title="pelanggan" busy={busy||blocked} order={order} onOrder={setOrder} onBrowse={()=>{setQ('');search('')}} submitLabel="Cari pelanggan" onSubmit={e=>{e.preventDefault();search(q.trim())}}
   search={<label>Nama atau kode pelanggan<input aria-label="Cari pelanggan riwayat" maxLength={120} value={q} onChange={e=>setQ(e.target.value)}/></label>}/>
  {!amounts?<p className="panel chistory-note">Nilai uang tidak ditampilkan karena akun ini tidak memiliki hak melihat piutang pelanggan.</p>:null}
  {blocked?<p className="panel" role="alert">{financialRecoveryMessage}</p>:null}
  {!blocked?<div className="cproc-layout chistory-layout">
   <section className="panel" aria-label="Daftar pelanggan riwayat"><h2>Pelanggan</h2>
    {listBusy?<p role="status">Membaca daftar pelanggan…</p>:null}{listError?<p role="alert">{listError}</p>:null}
    {list&&list.page.rows.length===0?<p>Tidak ada pelanggan sesuai pencarian.</p>:null}
    {list?orderRecordPage(list.page.rows,order,c=>c.name).map(c=><article key={c.id}><button className="cproc-receipt" data-customer-id={c.id} aria-pressed={selected===c.id} disabled={busy} onClick={()=>void loadDetail(c.id,0)}>
     <span><strong>{c.name}</strong><small>{c.code}{c.is_active?'':' · nonaktif'}</small><small>{c.counts.invoices} invoice · {c.counts.payments} pembayaran · {c.counts.returns} retur · {c.counts.cancellations} pembatalan</small><small>{c.last_invoice_at?'Invoice terakhir '+formatCp6WibDateTime(c.last_invoice_at):'Belum ada invoice'}</small></span>
     {listAmounts&&c.financial?<span><small>{balanceLabel(c.financial.open_balance)}</small><strong>{rp(c.financial.open_balance)}</strong></span>:null}
    </button></article>):null}
    {list?<div className="cproc-pagination"><span>Total {list.page.total} pelanggan</span><button disabled={busy||list.page.offset===0} onClick={()=>{listQuery.current={...listQuery.current,offset:Math.max(0,list.page.offset-LIMIT)};void loadList(listQuery.current)}}>Pelanggan sebelumnya</button><button disabled={busy||list.page.next_offset===null} onClick={()=>{listQuery.current={...listQuery.current,offset:list.page.next_offset??0};void loadList(listQuery.current)}}>Pelanggan berikutnya</button></div>:null}
   </section>
   <section className="panel chistory-detail" aria-label="Riwayat pelanggan terpilih">
    {selected===null?<><h2>Riwayat pelanggan</h2><p>Pilih pelanggan untuk melihat riwayatnya.</p></>:null}
    {detailBusy?<p role="status">Membaca riwayat pelanggan…</p>:null}{detailError?<p role="alert">{detailError}</p>:null}
    {detail?<>
     <h2>{detail.customer.name}</h2>
     <p>{detail.customer.code}{detail.customer.is_active?'':' · nonaktif'} · {detail.customer.counts.invoices} invoice · {detail.customer.counts.payments} pembayaran · {detail.customer.counts.returns} retur · {detail.customer.counts.cancellations} pembatalan</p>
     {showAmounts&&detail.customer.financial?<div className="chistory-totals" aria-label={`Ringkasan uang ${detail.customer.name}`}>
      {([['invoice_total','Nilai invoice aktif'],['return_total','Retur tercatat'],['paid_total','Pembayaran tercatat']] as const).map(([key,label])=><div className="cproc-total" key={key}><span>{label}</span><strong>{rp(detail.customer.financial![key])}</strong></div>)}
      <div className="cproc-total"><span>{balanceLabel(detail.customer.financial.open_balance)}</span><strong>{rp(detail.customer.financial.open_balance)}</strong></div>
     </div>:null}
     <p className="chistory-note">Kondisi dokumen sekarang, dibaca {formatCp6WibDateTime(detail.read_at)}. {showAmounts?'Sisa tagihan menjumlahkan invoice aktif pelanggan ini; saldo awal dan penyesuaian buku yang tidak berasal dari invoice diperiksa melalui laporan keuangan.':''}</p>
     {canExport?<div className="cproc-actions"><button onClick={download}>Unduh riwayat yang tampil (CSV)</button>{exported?<span role="status">{exported}</span>:null}</div>:null}
     {detail.timeline.rows.length===0?<p>Belum ada transaksi untuk pelanggan ini.</p>:
      <ol className="chistory-timeline" aria-label={`Riwayat ${detail.customer.name}`}>{detail.timeline.rows.map(e=>{const i=invoices.get(e.invoice_id);return <li key={e.id} data-event-id={e.id} data-kind={e.kind}>
       <time dateTime={e.at}>{formatCp6WibDateTime(e.at)}</time>
       <div><strong>{eventTitle(e)}</strong><small>{eventLine(e)}</small>{i&&e.kind!=='INVOICE'||i&&showAmounts?<small>{invoiceLine(i,showAmounts)}</small>:null}</div>
       {showAmounts&&e.financial?<b>{rp(e.financial.amount)}</b>:null}
      </li>})}</ol>}
     <div className="cproc-pagination"><span>Kejadian {detail.timeline.rows.length?`${detail.timeline.offset+1}–${detail.timeline.offset+detail.timeline.rows.length}`:'0'} dari {detail.timeline.total}</span>
      <button disabled={busy||detail.timeline.offset===0} onClick={()=>void loadDetail(detail.customer.id,Math.max(0,detail.timeline.offset-LIMIT))}>Kejadian lebih baru</button>
      <button disabled={busy||detail.timeline.next_offset===null} onClick={()=>void loadDetail(detail.customer.id,detail.timeline.next_offset??0)}>Kejadian lebih lama</button></div>
    </>:null}
   </section>
  </div>:null}
 </section>
}
