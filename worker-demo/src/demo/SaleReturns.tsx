import NumberEntry from '../../../src/components/NumberEntry'
import { useState } from 'react'
import { ArrowLeftRight, ArrowRight, Boxes, FileSearch, PackageCheck, ReceiptText, Search, Undo2 } from 'lucide-react'
import { BrowsePane } from '../components/BrowsePane'
import { browseMatchPieces } from '../browseMatch'
import { cashAccounts } from '../financeData'
import { amountText } from './accessoryPricing'
import { ReasonDialog } from './planner/ReasonDialog'
import { readInvoices, type DemoInvoice } from './saleBook'
import { canReturnInvoice, postSaleReturn, returnAllocations, returnQuote, type ReturnDraft } from './saleReturnBook'
import { readSaleReturns, returnDestinations, returnGrades, type ReturnGrade, type SaleReturn } from './saleReturnJournal'
import { lastWarehouseDay } from './warehouseDay'
import './demoCorrection.css'

const defaultDraft=():ReturnDraft=>({at:lastWarehouseDay()+'T10:45',destination:returnDestinations[0],grade:'Good',quantities:{},reason:'',settlement:''})

export function SaleReturns() {
  const [invoices,setInvoices]=useState(readInvoices)
  const [returns,setReturns]=useState(readSaleReturns)
  const [selected,setSelected]=useState(()=>new URLSearchParams(location.search).get('nota')??'INV-JUAL-0241')
  const [query,setQuery]=useState('')
  const posted=invoices.filter(canReturnInvoice)
  const visible=posted.filter(invoice=>browseMatchPieces(query,[invoice.qty,...returnAllocations(invoice,returns).flatMap(row=>[row.sold,row.returned,row.eligible])],
    invoice.number,invoice.customer,invoice.sku))
  const invoice=visible.find(doc=>doc.number===selected)??visible[0]
  return <section className="panel biz-master-detail sale-return-workspace">
    <BrowsePane aria-label="Daftar invoice asal"><header><div><span>INVOICE ASAL</span><strong>{visible.length} ditemukan</strong></div><FileSearch/></header>
      <label className="biz-search"><Search/><input type="search" aria-label="Cari invoice retur" value={query} onChange={event=>setQuery(event.target.value)} placeholder="Cari invoice, toko, SKU, atau pcs…"/></label>
      <div className="biz-browser-list">{visible.map(row=><button key={row.number} type="button" className={row.number===invoice?.number?'active':''}
        aria-pressed={row.number===invoice?.number} onClick={()=>setSelected(row.number)}><i><ReceiptText size={18}/></i>
        <div><strong>{row.qty.toLocaleString('id-ID')} pcs</strong><small>{row.customer}</small><em>{row.number}</em></div><ArrowRight/>
      </button>)}</div>
    </BrowsePane>
    {invoice?<ReturnEditor key={invoice.number} invoice={invoice} returns={returns} onSaved={()=>{setReturns(readSaleReturns());setInvoices(readInvoices())}}/>
      :<main className="biz-empty"><FileSearch/><strong>Invoice tidak ditemukan</strong><small>Cari nomor invoice, toko, SKU, atau jumlah pcs.</small></main>}
  </section>
}

function ReturnEditor({invoice,returns,onSaved}:{invoice:DemoInvoice;returns:SaleReturn[];onSaved:()=>void}) {
  const [draft,setDraft]=useState<ReturnDraft>(defaultDraft)
  const [original,setOriginal]=useState<SaleReturn|null>(null)
  const [review,setReview]=useState(false)
  const [feedback,setFeedback]=useState('')
  const [error,setError]=useState('')
  const history=returns.filter(doc=>doc.invoice===invoice.number).slice().reverse()
  const rows=returnAllocations(invoice,returns,original?.number)
  const quote=returnQuote(invoice,returns,draft,original??undefined)
  const creditReady=quote.excess===0||draft.settlement==='CREDIT'||draft.settlement==='REFUND'&&!!draft.account
  const noSource=rows.every(row=>row.eligible===0)
  const set=(values:Partial<ReturnDraft>)=>{setDraft(current=>({...current,...values}));setError('')}
  function openCorrection(doc:SaleReturn) {
    setOriginal(doc)
    setDraft({at:doc.at,destination:doc.destination,grade:doc.grade,reason:'',quantities:Object.fromEntries(doc.lines.map(line=>[line.key,String(line.qty)])),settlement:doc.settlement,account:doc.account})
    setFeedback('');setError('')
  }
  function save() {
    try {
      const doc=postSaleReturn(invoice.number,draft,original?.number)
      setReview(false);setOriginal(null);setDraft(defaultDraft())
      setFeedback(`${doc.number} tersimpan · ${quote.qty} pcs masuk ${doc.grade}.`)
      onSaved()
    } catch(err) {setError((err as Error).message)}
  }
  const facts=<div className="demo-operation-facts">
    <article><span>Stok masuk</span><strong>{quote.qty.toLocaleString('id-ID')} pcs</strong><small>{draft.destination} · {draft.grade}</small></article>
    <article><span>Potongan piutang nota</span><strong>{amountText(quote.ar)}</strong><small>Sisa piutang {amountText(quote.outstanding-quote.ar)}</small></article>
    <article><span>{draft.settlement==='REFUND'?'Refund kas/bank':'Kredit pelanggan'}</span><strong>{amountText(quote.excess)}</strong><small>{quote.excess>0?draft.account||invoice.customer:'Seluruh nilai terselesaikan di nota'}</small></article>
  </div>
  return <main>
    <header className="biz-detail-head"><div><span>{invoice.number}</span><h2>{invoice.customer}</h2><p>{invoice.day} · {invoice.qty} pcs terjual</p></div>
      <a className="soft-btn" href={'/penjualan/semua-invoice/?nota='+encodeURIComponent(invoice.number)}>Invoice asal <ArrowRight size={16}/></a>
    </header>
    <form className="demo-operation-form sale-return-editor" onSubmit={event=>{event.preventDefault();setError('');setReview(true)}}>
      <div className="demo-operation-heading"><i>{original?<ArrowLeftRight/>:<PackageCheck/>}</i><div><h3>{original?'Koreksi retur '+original.number:'Barang yang diterima kembali'}</h3>
        <p>{original?'Tinjau penggantinya dan simpan alasan koreksi.':'Pilih jumlah per ukuran dari invoice asal.'}</p></div></div>
      <div className="demo-operation-fields">
        <label>Waktu fisik (WIB)<input type="datetime-local" required min={`${invoice.dateKey}T${invoice.time}`} max={lastWarehouseDay()+'T23:59'} value={draft.at} onChange={event=>set({at:event.target.value})}/></label>
        <label>Grade masuk<select value={draft.grade} onChange={event=>{const grade=event.target.value as ReturnGrade;set({grade,destination:grade==='Hold QC'?returnDestinations[2]:returnDestinations[0]})}}>
          {returnGrades.map(grade=><option key={grade}>{grade}</option>)}</select></label>
        <label>Gudang tujuan<select value={draft.destination} onChange={event=>set({destination:event.target.value})}>
          {(draft.grade==='Hold QC'?returnDestinations.slice(2):returnDestinations.slice(0,2)).map(destination=><option key={destination}>{destination}</option>)}</select></label>
      </div>
      <div className="demo-entry-list" aria-label="Alokasi retur per ukuran">{rows.map(row=><article key={row.key}>
        <div><strong>{row.sku} · Ukuran {row.size}</strong><small>Lot {row.lot} · {row.sold} pcs terjual{row.returned>0?' · '+row.returned+' pcs sudah retur':''}</small></div>
        <div><strong>{row.eligible} pcs</strong><small>Masih bisa diretur</small></div>
        <label>Retur (pcs)<NumberEntry aria-label={`Retur ${row.sku} ukuran ${row.size}`} className="demo-qty" inputMode="numeric" disabled={!row.eligible}
          placeholder="0" value={draft.quantities[row.key]??''} onValueChange={rawInput =>set({quantities:{...draft.quantities,[row.key]:rawInput.replace(/\D/g,'').slice(0,9)}})}/></label>
      </article>)}</div>
      {noSource&&<p role="status">Tidak ada alokasi sumber dengan sisa retur yang bisa dicatat dari invoice ini.</p>}
      <label>{original?'Alasan koreksi':'Alasan retur'}<textarea required minLength={4} maxLength={500} value={draft.reason} onChange={event=>set({reason:event.target.value})}/></label>
      {quote.excess>0&&<div className="demo-operation-fields"><label>Penyelesaian selisih<select required value={draft.settlement} onChange={event=>set({settlement:event.target.value as ReturnDraft['settlement'],account:undefined})}>
        <option value="">Pilih penyelesaian</option><option value="CREDIT">Simpan kredit pelanggan</option><option value="REFUND">Refund melalui kas/bank</option></select></label>
        {draft.settlement==='REFUND'&&<label>Rekening refund<select required value={draft.account??''} onChange={event=>set({account:event.target.value})}>
          <option value="">Pilih rekening</option>{cashAccounts.map(account=><option key={account.code}>{account.name}</option>)}</select></label>}</div>}
      {quote.qty>0&&facts}
      {!quote.valid&&<p role="alert">Jumlah retur melebihi sisa alokasi pada salah satu ukuran.</p>}
      {feedback&&<p role="status">{feedback}</p>}
      <footer>{original&&<button type="button" className="soft-btn" onClick={()=>{setOriginal(null);setDraft(defaultDraft())}}>Batal koreksi</button>}
        <button className="primary-btn" disabled={!quote.qty||!quote.valid||!creditReady||draft.reason.trim().length<4}>{original?'Review koreksi':'Review retur'} <ArrowRight size={17}/></button></footer>
    </form>
    {history.length>0&&<section className="sale-return-editor demo-operation-history" aria-label="Riwayat retur">
      <div className="demo-operation-heading"><i><Undo2/></i><div><h3>Riwayat retur</h3><p>{invoice.number}</p></div></div>
      {history.map(doc=><article key={doc.number}><strong>{doc.lines.reduce((sum,line)=>sum+line.qty,0)} pcs · {doc.grade} · {amountText(doc.amount)}</strong>
        <small>{doc.number} · {doc.at.replace('T',' · ')} · {doc.destination}</small>
        <small>{doc.replacedBy?'Dibalik oleh '+doc.replacedBy:doc.replaces?'Pengganti '+doc.replaces:'Terposting'} · {doc.reason}</small>
        {doc.excess>0&&<small>{doc.settlement==='REFUND'?'Refund '+doc.account:'Kredit pelanggan'} · {amountText(doc.excess)}</small>}
        {!doc.replacedBy&&<div className="demo-operation-actions"><button className="soft-btn" type="button" onClick={()=>openCorrection(doc)}>Koreksi retur</button></div>}
      </article>)}
    </section>}
    {review&&<ReasonDialog title={original?'Simpan pembalikan dan pengganti':'Simpan retur penjualan'} closeLabel="Kembali" onClose={()=>setReview(false)} className="demo-operation-dialog">
      <div className="demo-operation-form"><p>{invoice.customer} · {invoice.number}</p>{facts}
        {error&&<p role="alert">{error}</p>}<footer><button className="primary-btn" type="button" onClick={save}><Boxes size={17}/> {original?'Simpan koreksi retur':'Simpan retur'}</button></footer></div>
    </ReasonDialog>}
  </main>
}
