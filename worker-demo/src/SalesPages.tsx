import { browseMatch } from './browseMatch'
import {dozenPieces,fgQuantity} from './fgQuantity'
import {readInvoices,writeInvoices,postInvoice,invoiceLines,sourceLines,saleStock,compareInvoices,type DraftLine,type DemoInvoice} from './demo/saleBook'
import {PeriodFilter,periodFor,periodLabel,matchesPeriod} from './demo/PeriodFilter'
import { useDeferredValue, useMemo, useRef, useState } from 'react'
import {
  AlertTriangle, ArrowRight, Banknote, Boxes, Check, CheckCircle2, ChevronLeft, ChevronRight, Clock3,
  FileSearch, History, PackageCheck, PackageSearch, Plus, ReceiptText,
  Search, ShieldCheck, ShoppingBag, Store, Trash2, Undo2,
  WalletCards, X,
} from 'lucide-react'
import { productCatalog } from './productCatalog'
import type { Product } from './productCatalog'
import { cleanMoneyInput, formatMoneyInput } from './moneyInput'
import { distributeDozensEvenly } from './sales/distributeDozensEvenly'
import { isSellableGoodAtLocation, parseManualPieceQuantity } from './sales/salesEligibility'
import './business-pages.css'

export type SalesView = 'sales-invoice' | 'sales-allocation' | 'sales-returns' | 'sales-payments' | 'sales-history'

type SalesPageProps = { view: SalesView; onNavigate: (view: SalesView) => void }
type Tone = 'good' | 'warn' | 'danger' | 'neutral'

const money = (value: number) => new Intl.NumberFormat('id-ID', {
  style: 'currency', currency: 'IDR', maximumFractionDigits: 0,
}).format(value)
const compactSales = (value:number)=>value>=1_000_000?`Rp${(value/1_000_000).toLocaleString('id-ID',{maximumFractionDigits:1})} jt`:money(value)
const productKey = (product: Pick<Product, 'brand' | 'code'>) => `${product.brand}::${product.code}`
const qtyLabel = dozenPieces
const lineQty = (line: DraftLine) => line.quantities.reduce((sum, qty) => sum + qty, 0)
const lineGross = (line: DraftLine) => (lineQty(line) / 12) * line.priceDozen
const defaultSalesLocation = 'Gudang FG Utama'
const initialSalesProducts = productCatalog.filter((product) => isSellableGoodAtLocation(product, defaultSalesLocation)).slice(0, 2)

function makeLine(product: Product, dozens: number): DraftLine {
  const quantities = distributeDozensEvenly(dozens, product.sizes.length) ?? product.sizes.map(() => 0)
  return {
    key: productKey(product), product,
    quantities,
    priceDozen: product.brand === 'Widie' ? 1_140_000 : 1_080_000,
  }
}

const returnableInvoices = [
  {
    number:'INV-JUAL-0241', customer:'Toko Maju Jaya', date:'27 Agu 2026',
    lines:[
      { key:'73001-28', sku:'Vivo · 73001', size:'28', sold:12, returned:0, price:90_000, lot:'FG-73001-0821' },
      { key:'73001-29', sku:'Vivo · 73001', size:'29', sold:12, returned:2, price:90_000, lot:'FG-73001-0822' },
      { key:'73001-30', sku:'Vivo · 73001', size:'30', sold:12, returned:0, price:90_000, lot:'FG-73001-0820' },
      { key:'73002-31', sku:'Vivo · 73002', size:'31', sold:16, returned:0, price:95_000, lot:'FG-73002-0820' },
    ],
  },
  {
    number:'INV-JUAL-0240', customer:'Nusantara Fashion', date:'26 Agu 2026',
    lines:[
      { key:'73005-31', sku:'Widie · 73005', size:'31', sold:24, returned:0, price:95_000, lot:'FG-73005-0819' },
      { key:'73005-32', sku:'Widie · 73005', size:'32', sold:24, returned:0, price:95_000, lot:'FG-73005-0818' },
      { key:'73005-33', sku:'Widie · 73005', size:'33', sold:24, returned:0, price:95_000, lot:'FG-73005-0817' },
    ],
  },
]

const receivables = [
  { invoice:'INV-JUAL-0241', customer:'Toko Maju Jaya', invoiceDate:'27 Agu 2026', dueDate:'26 Sep 2026', gross:7_830_000, returns:180_000, paid:4_820_000, status:'PARTIAL' },
  { invoice:'INV-JUAL-0239', customer:'Sentra Denim', invoiceDate:'27 Agu 2026', dueDate:'27 Agu 2026', gross:5_730_000, returns:0, paid:0, status:'OVERDUE' },
  { invoice:'INV-JUAL-0237', customer:'Nusantara Fashion', invoiceDate:'22 Agu 2026', dueDate:'21 Sep 2026', gross:12_640_000, returns:860_000, paid:8_000_000, status:'PARTIAL' },
  { invoice:'INV-JUAL-0232', customer:'Toko Maju Jaya', invoiceDate:'14 Agu 2026', dueDate:'14 Agu 2026', gross:4_920_000, returns:0, paid:3_000_000, status:'OVERDUE' },
]

const customerEvents = [
  { date:'28 Agu · 09:18', customer:'Toko Maju Jaya', type:'PAYMENT', number:'PAY-CUST-0188', description:'Pembayaran sebagian INV-JUAL-0241', sku:'—', qty:0, amount:2_000_000 },
  { date:'27 Agu · 14:02', customer:'Toko Maju Jaya', type:'RETURN', number:'RET-JUAL-0045', description:'Retur 73001 size 29', sku:'73001', qty:2, amount:-180_000 },
  { date:'25 Agu · 10:12', customer:'Nusantara Fashion', type:'PAYMENT', number:'PAY-CUST-0186', description:'Pelunasan INV-JUAL-0235', sku:'—', qty:0, amount:9_200_000 },
]

function SalesHero({ eyebrow, title, description, icon: Glyph }: { eyebrow:string; title:string; description:string; icon:typeof ShoppingBag }) {
  return <section className="biz-hero"><div><span>{eyebrow}</span><h1>{title}</h1><p>{description}</p></div><div className="biz-hero-rule"><Glyph/><div><small>SIMULASI UX</small><strong>Belum menulis backend</strong><em>Semua posting tetap menunggu domain RPC.</em></div></div></section>
}

function Pill({ children, tone='neutral' }: { children:string; tone?:Tone }) {
  return <span className={`biz-pill ${tone}`}>{children.replaceAll('_',' ')}</span>
}

function statusTone(status: string): Tone {
  if (['READY','POSTED','PAID'].includes(status)) return 'good'
  if (['SHORT','OVERDUE'].includes(status)) return 'danger'
  if (status==='PARTIAL') return 'warn'
  return 'neutral'
}

function invoiceStatusLabel(status:string){
  if(status==='DRAFT')return 'DRAFT · RESERVED'
  return status
}

const invoicePageSize = 25
const invoiceItemPageSize = 20

function invoiceSkuLabels(invoice: DemoInvoice) {
  const labels = invoice.lines?.length
    ? invoice.lines.map(line => `${line.product.brand} ${line.product.code}`)
    : invoice.sku.split(' · ')
  return [...new Set(labels.map(label => label.trim()).filter(label => label && label !== '—'))]
}

function InvoicePagination({ kind, page, perPage, count, onPage }: {
  kind: 'nota' | 'barang'; page: number; perPage: number; count: number; onPage: (page: number) => void
}) {
  if (count <= perPage) return null
  return <nav className="invoice-pagination" aria-label={'Halaman ' + kind}>
    <button type="button" className="soft-btn" aria-label={kind + ' sebelumnya'} disabled={page === 0} onClick={() => onPage(page - 1)}><ChevronLeft size={16} aria-hidden="true"/>Sebelumnya</button>
    <span aria-live="polite">{page * perPage + 1}–{Math.min((page + 1) * perPage, count)} dari {count} {kind}</span>
    <button type="button" className="soft-btn" aria-label={kind + ' berikutnya'} disabled={(page + 1) * perPage >= count} onClick={() => onPage(page + 1)}>Berikutnya<ChevronRight size={16} aria-hidden="true"/></button>
  </nav>
}

function InvoiceGoods({ invoice, initialQuery }: { invoice: DemoInvoice; initialQuery: string }) {
  const tableRef = useRef<HTMLDivElement>(null)
  const [page, setPage] = useState(0)
  const [query, setQuery] = useState(initialQuery)
  const items = useMemo(() => {
    const rows = invoiceLines(invoice)
    const skus = invoiceSkuLabels(invoice)
    if (!invoice.lines && rows.length === 1 && skus.length > 1) {
      return skus.map(sku => ({ sku, qty: null, amount: null, detail: undefined }))
    }
    const details = invoice.lines ?? (rows.every(row => row.qty > 0 && productCatalog.some(product => product.code === row.sku)) ? sourceLines(invoice) : [])
    return rows.map((row, index) => ({ ...row, detail: details[index] }))
  }, [invoice])
  const visible = query.trim() ? items.filter(item => browseMatch(query, item.sku, item.detail?.product.name, item.detail?.product.color)) : items
  const start = page * invoiceItemPageSize
  const current = visible.slice(start, start + invoiceItemPageSize)
  const visibleDetails = current.flatMap(item => item.detail ? [item.detail] : [])

  function pageTo(next: number) {
    setPage(next)
    tableRef.current?.scrollTo({ top: 0 })
  }

  return <section className="owner-invoice-lines invoice-goods">
    <header><div><h3>Rincian barang</h3><p>{invoice.customer} · {invoice.day} · {invoice.time} WIB</p></div>
      {(items.length > 8 || initialQuery) && <label className="biz-search"><Search aria-hidden="true"/><input type="search" aria-label="Cari SKU di nota" placeholder="Cari SKU di nota…" value={query}
        onChange={event => { setQuery(event.target.value); pageTo(0) }}/></label>}
    </header>
    {current.length > 0 ? <div className="invoice-goods-table" ref={tableRef} tabIndex={0} role="region" aria-label="Daftar SKU pada nota">
      <table><thead><tr><th scope="col">SKU</th><th scope="col">Jumlah</th><th scope="col">Subtotal</th></tr></thead>
        <tbody>{current.map((item, index) => <tr key={item.sku + '-' + (start + index)}>
          <th scope="row"><strong>{item.sku}</strong>{item.detail && <small>{item.detail.product.name}</small>}</th>
          <td>{item.qty === null ? '—' : fgQuantity(item.qty)}</td><td>{item.amount === null ? '—' : money(item.amount)}</td>
        </tr>)}</tbody>
      </table>
    </div> : <p role="status">SKU tidak ditemukan di nota ini.</p>}
    <InvoicePagination kind="barang" page={page} perPage={invoiceItemPageSize} count={visible.length} onPage={pageTo}/>
    {visibleDetails.length > 0 && <details><summary>Detail ukuran, warna dan harga</summary>
      {visibleDetails.map((line, index) => <p key={line.key + '-' + index}><strong>{line.product.brand} {line.product.code} · {line.product.range}</strong> · {line.product.color} · {money(line.priceDozen)}/lusin<br/>
        {line.product.sizes.map((size, i) => size + ' = ' + fgQuantity(line.quantities[i])).join(' · ')}</p>)}
    </details>}
    {invoice.notes && <p>Catatan · {invoice.notes}</p>}
    <p>Bruto {money(invoice.gross)} · Retur {money(invoice.returns)} · Dibayar {money(invoice.paid)} · {invoice.status === 'DRAFT' ? 'Belum dibukukan' : 'Sisa tagihan ' + money(invoice.gross - invoice.returns - invoice.paid)}</p>
  </section>
}

function InvoiceLifecycle({compact=false}:{compact?:boolean}){
  return <section className={`panel biz-invoice-lifecycle ${compact?'compact':''}`} aria-label="Lifecycle invoice"><article className="active"><i>01</i><span><small>DRAFT + AUTO RESERVE</small><strong>Mutasi stok langsung −qty</strong><em>Stok siap jual toko berkurang saat Draft disimpan.</em></span></article><ArrowRight/><article><i>02</i><span><small>DRAFT BERJALAN</small><strong>Boleh tambah, kurang, atau batal</strong><em>Setiap edit hanya mencatat selisih reserve / release.</em></span></article><ArrowRight/><article><i>03</i><span><small>POSTED</small><strong>Kunci invoice tanpa minus kedua</strong><em>Post membentuk AR, revenue, dan COGS; stok tidak bergerak lagi.</em></span></article></section>
}

function ReviewModal({ title, description, onClose, children, action, actionLabel='Simpan simulasi', disabled=false, danger=false }: { title:string; description:string; onClose:()=>void; children:React.ReactNode; action:()=>void; actionLabel?:string; disabled?:boolean; danger?:boolean }) {
  return <div className="biz-modal-backdrop" role="presentation" onMouseDown={onClose}><section className="biz-modal" role="dialog" aria-modal="true" aria-labelledby="sales-review-title" onMouseDown={(event)=>event.stopPropagation()}><header><div><span>REVIEW SEBELUM AKSI</span><h2 id="sales-review-title">{title}</h2><p>{description}</p></div><button aria-label="Tutup" onClick={onClose}><X/></button></header><div className="biz-modal-body">{children}</div><footer><button className="soft-btn" onClick={onClose}>Kembali</button><button className={`primary-btn ${danger?'danger':''}`} disabled={disabled} onClick={action}>{danger?<Trash2/>:<ShieldCheck/>} {actionLabel}</button></footer></section></div>
}

export default function SalesPages({ view, onNavigate }: SalesPageProps) {
  if (view === 'sales-invoice') return <InvoiceWorkspace onNavigate={onNavigate}/>
  if (view === 'sales-allocation') return <AllocationWorkspace onNavigate={onNavigate}/>
  if (view === 'sales-returns') return <ReturnsWorkspace/>
  if (view === 'sales-payments') return <PaymentsWorkspace/>
  return <CustomerHistoryWorkspace/>
}

function InvoiceWorkspace({ onNavigate }: { onNavigate: SalesPageProps['onNavigate'] }) {
  const params=new URLSearchParams(globalThis.location.search)
  const [source]=useState(()=>readInvoices().find(d=>d.number===(params.get('nota')||params.get('koreksi'))))
  const [number,setNumber]=useState(()=>params.get('koreksi')||!source?'INV-SIM-'+crypto.randomUUID().slice(0,8).toUpperCase():source.number)
  const [correction]=useState(()=>params.get('koreksi')||source?.corrects)
  const [memo,setMemo]=useState(source?.notes??'')
  const [changeReason,setChangeReason]=useState('Penyimpanan draft invoice')
  const [customer,setCustomer] = useState(source?.customer??'Nusantara Fashion')
  const [location,setLocation] = useState(source?.location??(source?sourceLines(source)[0]?.product.location:null)??defaultSalesLocation)
  const [terms,setTerms] = useState(source ? source.terms??'' : 'NET 30')
  const [physicalAt,setPhysicalAt] = useState(source?source.dateKey+'T'+source.time:'2026-08-28T10:30')
  const [dueDate,setDueDate] = useState(source ? source.due??'' : '2026-09-27')
  const [query,setQuery] = useState('')
  const [brand,setBrand] = useState('Semua merek')
  const [lines,setLines] = useState<DraftLine[]>(()=>source?sourceLines(source):initialSalesProducts.map((product)=>makeLine(product,3)))
  const [lineDozens,setLineDozens] = useState<Record<string,string>>(()=>Object.fromEntries(lines.map(l=>[l.key,String(lineQty(l)/12)])))
  const [notice,setNotice] = useState('')
  const [reviewOpen,setReviewOpen] = useState(false)
  const [clearOpen,setClearOpen] = useState(false)

  const visibleProducts = useMemo(()=>productCatalog.filter((product)=>{
    const haystack=`${product.brand} ${product.code} ${product.name} ${product.color} ${product.range}`.toLowerCase()
    return isSellableGoodAtLocation(product,location) && haystack.includes(query.toLowerCase()) && (brand==='Semua merek'||product.brand===brand)
  }),[query,brand,location])
  const totalQty=lines.reduce((sum,line)=>sum+lineQty(line),0)
  const gross=lines.reduce((sum,line)=>sum+lineGross(line),0)
  const stockValid=lines.every((line)=>isSellableGoodAtLocation(line.product,location)&&line.quantities.length===line.product.sizes.length&&line.product.stocks.length===line.product.sizes.length&&new Set(line.product.sizes).size===line.product.sizes.length&&line.quantities.every((qty,index)=>Number.isSafeInteger(qty)&&qty>=0&&qty<=saleStock(line.product,readInvoices(),number)[index]))
  const canReview=lines.length>0&&totalQty>0&&stockValid&&customer.trim().length>0&&!!physicalAt&&changeReason.trim().length>=5

  function persistDraft(){
    const book=readInvoices(),current=book.find(d=>d.number===number)
    if(current&&current.status!=='DRAFT'){setReviewOpen(false);setNotice('Invoice sudah dikunci. Muat ulang untuk melihat status.');return}
    if(!canReview||lines.some(l=>l.quantities.some((n,i)=>n>saleStock(l.product,book,number)[i]))){setReviewOpen(false);setNotice('Periksa tanggal, jumlah dan saldo SKU.');return}
    const dateKey=physicalAt.slice(0,10),time=physicalAt.slice(11,16)
    const doc:DemoInvoice={number,customer,dateKey,day:new Intl.DateTimeFormat('id-ID',{day:'numeric',month:'short',year:'numeric',timeZone:'UTC'}).format(new Date(dateKey+'T12:00:00Z')),time,sku:lines.map(l=>l.product.code).join(' · '),qty:totalQty,gross:Math.round(gross),returns:0,paid:0,status:'DRAFT',lines:structuredClone(lines),terms,due:dueDate,notes:memo,changeReason:changeReason.trim(),location,corrects:correction||undefined}
    writeInvoices([doc,...book.filter(d=>d.number!==number)])
    globalThis.history.replaceState(null,'','/penjualan/invoice/?nota='+encodeURIComponent(number))
    const difference=totalQty-(current?.qty??0)
    const impact=difference>0?'Mutasi RESERVE INVOICE −'+difference+' pcs.':difference<0?'Mutasi RELEASE +'+Math.abs(difference)+' pcs.':'Jumlah reserve tetap.'
    setReviewOpen(false);setNotice('Draft tersimpan. '+impact+' '+number)
  }
  function clearDraft(){
    const book=readInvoices(),d=book.find(d=>d.number===number)
    if(d&&d.status!=='DRAFT'){setNotice('Dokumen sudah terkunci.');setClearOpen(false);return}
    if(d)writeInvoices(book.filter(doc=>doc.number!==number))
    setLines([]);setLineDozens({});setClearOpen(false);setNumber('INV-SIM-'+crypto.randomUUID().slice(0,8).toUpperCase())
    globalThis.history.replaceState(null,'','/penjualan/invoice/');setNotice('Draft dibuang. Reserve dilepas.')
  }
  if((params.has('nota')||params.has('koreksi'))&&!source&&!readInvoices().some(d=>d.number===number))return <section className="panel gar-panel"><h1>Invoice tidak ditemukan</h1><a href="/penjualan/semua-invoice/">Kembali ke semua invoice</a></section>
  if(source&&((source.status!=='DRAFT'&&!correction)||(params.has('koreksi')&&(source.paid||source.returns||source.status!=='POSTED'))))return <section className="panel gar-panel"><h1>{source.number}</h1><p>{source.customer} · {source.day} · {source.time} WIB · {source.status}</p><p>{money(source.gross)} · {fgQuantity(source.qty)}</p><a href={'/penjualan/semua-invoice/?nota='+source.number}>Buka rincian dan tindakan dokumen</a></section>
  const addProduct=(product:Product)=>{
    const key=productKey(product)
    if(!isSellableGoodAtLocation(product,location)){setNotice('SKU diblokir: Sales hanya boleh memilih grade GOOD dari lokasi FG yang sedang aktif.');return}
    if(lines.some((line)=>line.key===key)){setNotice(`${product.brand} ${product.code} sudah ada di invoice.`);return}
    const newLine=makeLine(product,1)
    setLines((current)=>[...current,newLine])
    const evenlyApplied=newLine.quantities.reduce((sum,qty)=>sum+qty,0)===12
    setLineDozens((current)=>({...current,[key]:evenlyApplied?'1':''}))
    setNotice(evenlyApplied?`${product.brand} ${product.code}: 1 lusin dibagi merata ke ${product.sizes.length} ukuran.`:`${product.brand} ${product.code}: isi PCS per ukuran; 1 lusin tidak terbagi rata ke ${product.sizes.length} ukuran.`)
  }
  const updateQty=(key:string,index:number,value:string)=>{
    const source=lines.find((line)=>line.key===key)
    if(!source)return
    const parsed=parseManualPieceQuantity(value)
    if(parsed===null){setNotice('Qty size tidak berubah: masukkan bilangan bulat PCS yang aman, tanpa minus, desimal, atau notasi ilmiah.');return}
    const next=[...source.quantities]
    next[index]=parsed
    setLines((current)=>current.map((line)=>line.key===key?{...line,quantities:next}:line))
    setLineDozens((current)=>({...current,[key]:''}))
  }
  const applyDozens=(key:string)=>{
    const rawDozens=(lineDozens[key]??'').trim().replace(',','.')
    if(rawDozens==='')return
    const dozens=Number(rawDozens)
    const source=lines.find((line)=>line.key===key)
    if(!source)return
    const quantities=distributeDozensEvenly(dozens,source.product.sizes.length)
    if(!quantities){
      setNotice(`Helper tidak diterapkan: total potong harus bulat dan habis dibagi rata ke ${source.product.sizes.length} ukuran SKU ini. Qty lama tetap; isi pembagian per ukuran secara eksplisit.`)
      return
    }
    setLines((current)=>current.map((line)=>line.key===key?{...line,quantities}:line))
    setNotice(`Helper ${dozens.toLocaleString('id-ID',{maximumFractionDigits:2})} lusin diterapkan rata ke ${source.product.sizes.length} ukuran SKU ini. Jumlah per ukuran tetap bisa diedit.`)
  }
  const updatePrice=(key:string,value:string)=>setLines((current)=>current.map((line)=>line.key===key?{...line,priceDozen:Math.max(0,Number(value.replace(/\D/g,''))||0)}:line))

  return <>
    <SalesHero eyebrow="PENJUALAN · INVOICE BUILDER" title="Penjualan & Invoice" description="Pilih pelanggan sekali, masukkan banyak SKU, isi size, lalu review stok, allocation FIFO, piutang, dan HPP sebelum posting." icon={ReceiptText}/>
    <div className="owner-payroll-actions"><strong>{number}{correction?' · Koreksi '+correction:''}</strong><a className="gar-button" href={'/penjualan/semua-invoice/'+(readInvoices().some(n=>n.number===number)?'?nota='+number:'')}>Kembali ke Semua Invoice</a></div>
    <InvoiceLifecycle/>
    <section className="biz-meta panel">
      <label><span>PELANGGAN</span><select value={customer} onChange={(event)=>setCustomer(event.target.value)}><option>Nusantara Fashion</option><option>Toko Maju Jaya</option><option>Sentra Denim</option></select></label>
      <label><span>LOKASI FG</span><select value={location} onChange={(event)=>{const nextLocation=event.target.value;setLocation(nextLocation);setNotice(`Lokasi aktif diganti ke ${nextLocation}. Baris dari lokasi lain diblokir sampai dikeluarkan dari draft.`)}}><option>Gudang FG Utama</option><option>Gudang FG Cadangan</option></select></label>
      <label><span>WAKTU FISIK</span><input type="datetime-local" value={physicalAt} onChange={(event)=>setPhysicalAt(event.target.value)}/></label>
      <label><span>TERMIN · OPSIONAL</span><select value={terms} onChange={(event)=>setTerms(event.target.value)}><option value="">Tanpa termin</option><option>NET 30</option><option>COD</option><option>NET 14</option><option>NET 45</option></select></label>
      <label><span>ALASAN PENYIMPANAN · WAJIB</span><input aria-label="Alasan penyimpanan" maxLength={1000} value={changeReason} onChange={e=>setChangeReason(e.target.value)}/></label>
      <label><span>JATUH TEMPO · OPSIONAL</span><input aria-label="Jatuh tempo" type="date" value={dueDate} onChange={(event)=>setDueDate(event.target.value)}/></label>
    </section>

    <section className="biz-sales-builder">
      <aside className="panel biz-catalog">
        <header><div><span>TAMBAH SKU</span><strong>{visibleProducts.length} barang tampil</strong></div><PackageSearch/></header>
        <label className="biz-search"><Search/><input value={query} onChange={(event)=>setQuery(event.target.value)} placeholder="Ketik SKU, merek, model, warna..."/></label>
        <div className="biz-inline-filters browse-only"><select value={brand} onChange={(event)=>setBrand(event.target.value)}><option>Semua merek</option><option>Vivo</option><option>Widie</option></select><span><Plus/> Klik barang untuk tambah</span></div>
        <div className="biz-catalog-list">{visibleProducts.map((product)=>{const added=lines.some((line)=>line.key===productKey(product));const stock=saleStock(product,readInvoices(),number).reduce((sum,qty)=>sum+qty,0);return <button key={productKey(product)} className={added?'added':''} onClick={()=>addProduct(product)}><span>{product.brand.slice(0,1)}</span><div><strong>{product.brand} · {product.code}</strong><small>{product.name} · {product.color}</small><em>{product.range} · {fgQuantity(stock)} · GOOD · {location}</em></div>{added?<Check/>:<Plus/>}</button>})}</div>
      </aside>

      <div className="panel biz-invoice-draft">
        <header><div><span>INVOICE DRAFT</span><strong>{lines.length} SKU · {totalQty} pcs</strong></div><button className="biz-danger-soft" disabled={lines.length===0} onClick={()=>setClearOpen(true)}><Trash2/> Kosongkan</button></header>
        {notice&&<div className="biz-inline-notice"><CheckCircle2/> {notice}</div>}
        <div className="biz-invoice-lines">{lines.map((line,index)=>{
          const qty=lineQty(line)
          const sellable=isSellableGoodAtLocation(line.product,location)
          const stockExceeded=line.quantities.some((value,sizeIndex)=>value>line.product.stocks[sizeIndex])
          const invalid=!sellable||stockExceeded
          return <article key={line.key} className={invalid?'invalid':''}><header><span>{String(index+1).padStart(2,'0')}</span><div><strong>{line.product.brand} · {line.product.code}</strong><small>{line.product.name} · {line.product.color} · {line.product.range} · {line.product.location} · {line.product.grade}</small></div><b>{money(lineGross(line))}</b><button aria-label={`Hapus ${line.product.code}`} onClick={()=>{setLines((current)=>current.filter((item)=>item.key!==line.key));setLineDozens((current)=>{const next={...current};delete next[line.key];return next})}}><X/></button></header><div className="biz-size-entry" data-keyboard-grid>{line.product.sizes.map((size,sizeIndex)=><label key={size} className={line.quantities[sizeIndex]>line.product.stocks[sizeIndex]?'invalid':''}><span>SIZE {size}</span><div><input data-grid-row={index} data-grid-col={sizeIndex} inputMode="numeric" value={line.quantities[sizeIndex]} onFocus={(event)=>event.currentTarget.select()} onChange={(event)=>updateQty(line.key,sizeIndex,event.target.value)}/><b>pcs</b></div><small>stok {fgQuantity(saleStock(line.product,readInvoices(),number)[sizeIndex])}</small></label>)}</div><footer><span className="biz-line-total"><small>QTY BARIS · SUMBER AKHIR</small><strong>{qty} pcs · {qtyLabel(qty)}</strong></span><label className="biz-dozen-helper"><small>ISI CEPAT · LUSIN</small><div><input inputMode="decimal" value={lineDozens[line.key]??''} onFocus={(event)=>event.currentTarget.select()} onChange={(event)=>setLineDozens((current)=>({...current,[line.key]:event.target.value.replace(/[^0-9,.]/g,'')}))}/><b>lusin</b><button type="button" onClick={()=>applyDozens(line.key)}>Terapkan</button></div><em>Helper saja · qty per size tetap bisa diedit</em></label><label className="biz-price-field"><small>HARGA / LUSIN</small><div><b>Rp</b><input inputMode="numeric" value={formatMoneyInput(line.priceDozen)} onFocus={(event)=>event.currentTarget.select()} onChange={(event)=>updatePrice(line.key,event.target.value)}/></div></label>{invalid&&<em className="biz-line-warning"><AlertTriangle/> {!sellable?'Bukan grade GOOD di lokasi FG aktif.':'Ada size melebihi stok.'}</em>}</footer></article>
        })}{lines.length===0&&<div className="biz-empty"><ShoppingBag/><strong>Invoice masih kosong</strong><small>Klik SKU di katalog sebelah kiri.</small></div>}</div>
      </div>

      <aside className="panel biz-review-card">
        <span>RINGKASAN INVOICE</span><h2>{money(gross)}</h2><p>{customer} · {terms}</p>
        <div><article><small>SKU</small><strong>{lines.length}</strong></article><article><small>QTY</small><strong>{totalQty} pcs</strong></article><article><small>LUSIN</small><strong>{qtyLabel(totalQty)}</strong></article></div>
        <section><p><Check/> SKU/size langsung dicek terhadap stok siap jual</p><p><Check/> Simpan Draft langsung membuat mutasi reserve −qty</p><p><Check/> Post mengunci invoice tanpa mengurangi stok kedua kali</p><p><Check/> Batal/kurangi Draft membuat release +qty</p></section>
        {!stockValid&&<div className="biz-guard danger"><AlertTriangle/><span>Ada baris di luar lokasi aktif, bukan grade GOOD, qty tidak aman, atau melebihi stok. Posting harus diblokir.</span></div>}
        <label><span>CATATAN INVOICE</span><textarea maxLength={4000} aria-label="Catatan invoice" value={memo} onChange={e=>setMemo(e.target.value)} placeholder="PO pelanggan, instruksi kirim, atau catatan harga..."/></label>
        <button className="primary-btn" disabled={!canReview} onClick={()=>setReviewOpen(true)}>Review invoice <ArrowRight/></button>
        <button className="soft-btn" onClick={()=>onNavigate('sales-allocation')}>Lihat semua invoice</button>
      </aside>
    </section>

    <section className="panel biz-history-block"><header><div><span>INVOICE TERBARU</span><strong>Draft reserved dan invoice posted</strong></div><History/></header><div className="biz-table"><div className="biz-table-head"><span>Nomor / waktu</span><span>Pelanggan</span><span>SKU / qty</span><span>Nilai</span><span>Status</span></div>{readInvoices().slice().sort(compareInvoices('NEWEST')).slice(0,4).map((item)=><article key={item.number}><span><a href={'/penjualan/semua-invoice/?nota='+item.number}>{item.number}</a><small>{item.day} · {item.time}</small></span><strong>{item.customer}</strong><span>{item.sku}<small>{item.qty} pcs · {qtyLabel(item.qty)}</small></span><b>{money(item.gross)}</b><Pill tone={statusTone(item.status)}>{invoiceStatusLabel(item.status)}</Pill></article>)}</div></section>

    {reviewOpen&&<ReviewModal title="Simpan Draft & kurangi stok siap jual" description="Draft tetap dapat diedit sepanjang hari. Saat disimpan, allocation FIFO dan mutasi reserve dicatat langsung." onClose={()=>setReviewOpen(false)} actionLabel="Simpan Draft + reserve" action={persistDraft}><div className="biz-impact-grid"><article><span>Mutasi stok</span><strong>− {totalQty} pcs</strong><small>{dozenPieces(totalQty)} · RESERVE INVOICE · langsung terlihat</small></article><article><span>Stok siap jual</span><strong>− {totalQty} pcs</strong><small>{dozenPieces(totalQty)} · FIFO per SKU, size, lokasi, dan lot</small></article><article><span>AR / COGS</span><strong>Belum terbentuk</strong><small>Baru dibentuk saat invoice ditutup / Post</small></article></div><div className="biz-guard"><ShieldCheck/><span><strong>Draft mengurangi stok real-time.</strong> Tambah qty membuat reserve tambahan; kurangi atau batal membuat release. Post hanya mengunci dokumen dan finansial tanpa mengurangi stok lagi.</span></div></ReviewModal>}
    {clearOpen&&<ReviewModal danger actionLabel="Kosongkan draft" title="Kosongkan draft invoice?" description="Baris Draft dibuang dan mutasi reserve terkait harus dilepas. Invoice posted tidak pernah dihapus dari sini." onClose={()=>setClearOpen(false)} action={clearDraft}><div className="biz-guard danger"><AlertTriangle/><span>{lines.length} SKU dan {totalQty} pcs akan keluar dari Draft; reserve-nya dikembalikan sebagai mutasi release +qty.</span></div></ReviewModal>}
  </>
}

function AllocationWorkspace({ onNavigate }: { onNavigate: SalesPageProps['onNavigate'] }) {
  const [invoices,setInvoices]=useState(readInvoices)
  const linked = new URLSearchParams(location.search).get('nota')
  const [period,setPeriod]=useState(()=>periodFor('month', invoices.find(invoice => invoice.number === linked)?.dateKey ?? '2026-08-28'))
  const [query,setQuery]=useState('')
  const [customer,setCustomer]=useState('ALL')
  const [status,setStatus]=useState('ALL')
  const [sort,setSort]=useState('NEWEST')
  const [registerPage,setRegisterPage]=useState(0)
  const [selectedInvoice,setSelectedInvoice]=useState<DemoInvoice|null>(()=>invoices.find(i=>i.number===linked)??null)
  const [notice,setNotice]=useState('')
  const customers=[...new Set(invoices.map((invoice)=>invoice.customer))]
  const skuByInvoice = useMemo(() => new Map(invoices.map(invoice => [invoice.number, invoiceSkuLabels(invoice)])), [invoices])
  const registerQuery = useDeferredValue(query.trim())
  const visible = useMemo(() => invoices.filter(invoice => matchesPeriod(invoice.dateKey, period) &&
    (customer === 'ALL' || invoice.customer === customer) && (status === 'ALL' || invoice.status === status) &&
    (!registerQuery || browseMatch(registerQuery, invoice.number, invoice.customer, ...(skuByInvoice.get(invoice.number) ?? []))))
    .sort(compareInvoices(sort)), [invoices, registerQuery, skuByInvoice, customer, status, sort, period])
  const currentPage = Math.min(registerPage, Math.max(0, Math.ceil(visible.length / invoicePageSize) - 1))
  const shown = visible.slice(currentPage * invoicePageSize, (currentPage + 1) * invoicePageSize)
  const selectedSkus = selectedInvoice ? skuByInvoice.get(selectedInvoice.number) ?? [] : []
  const skuQuery = registerQuery && selectedSkus.some(sku => browseMatch(registerQuery, sku)) ? registerQuery : ''
  const counted=visible.filter((invoice)=>['POSTED','PAID'].includes(invoice.status))
  const gross=counted.reduce((sum,invoice)=>sum+invoice.gross,0)
  const returns=counted.reduce((sum,invoice)=>sum+invoice.returns,0)
  const net=gross-returns
  const storeTotals=customers.map((name)=>{const rows=counted.filter((invoice)=>invoice.customer===name);return {name,count:rows.length,qty:rows.reduce((sum,invoice)=>sum+invoice.qty,0),gross:rows.reduce((sum,invoice)=>sum+invoice.gross,0),returns:rows.reduce((sum,invoice)=>sum+invoice.returns,0)}}).filter((item)=>item.count>0).sort((a,b)=>(b.gross-b.returns)-(a.gross-a.returns))
  const maxStore=Math.max(1,...storeTotals.map((item)=>item.gross-item.returns))
  const days=[...new Set(counted.map((invoice)=>invoice.dateKey))].sort((a,b)=>b.localeCompare(a))
  return <>
    <SalesHero eyebrow="PENJUALAN · INVOICE REGISTER" title="Semua Invoice" description="Cari semua nota penjualan, urutkan per toko atau nilai, lalu lihat total setiap nota dan ringkasan sales per toko dari transaksi yang benar-benar posted." icon={ReceiptText}/>
    <InvoiceLifecycle compact/>
    <PeriodFilter label="Periode penjualan dan ranking" value={period} onChange={value => { setPeriod(value); setRegisterPage(0) }}/>
    <section className="biz-metrics"><div className="panel"><span>INVOICE TAMPIL</span><strong>{visible.length}</strong><small>{counted.length} sudah posted / paid</small></div><div className="panel good"><span>PENJUALAN BRUTO</span><strong>{money(gross)}</strong><small>Draft tidak dihitung</small></div><div className="panel danger"><span>RETUR</span><strong>{money(returns)}</strong><small>Dokumen retur posted</small></div><div className="panel good"><span>NET SALES</span><strong>{money(net)}</strong><small>{counted.reduce((sum,invoice)=>sum+invoice.qty,0)} pcs</small></div></section>
    {notice&&<div className="biz-inline-notice biz-register-notice"><CheckCircle2/> {notice}</div>}
    <section className="panel biz-invoice-register">
      <header><div><span>DAFTAR INVOICE</span><strong>{visible.length} nota sesuai filter</strong><small>Pilih nota untuk membuka rincian barang.</small></div>
        <button className="primary-btn" onClick={()=>onNavigate('sales-invoice')}><Plus/> Buat invoice</button></header>
      <div className="biz-history-toolbar compact">
        <label className="biz-search"><Search aria-hidden="true"/><input type="search" aria-label="Cari invoice, toko, atau SKU" value={query} onChange={event=>{setQuery(event.target.value);setRegisterPage(0)}} placeholder="Cari invoice, toko, atau SKU…"/></label>
        <select aria-label="Toko" value={customer} onChange={event=>{setCustomer(event.target.value);setRegisterPage(0)}}><option value="ALL">Semua toko</option>{customers.map(name=><option key={name}>{name}</option>)}</select>
        <select aria-label="Status invoice" value={status} onChange={event=>{setStatus(event.target.value);setRegisterPage(0)}}><option value="ALL">Semua status</option><option value="POSTED">Posted</option><option value="PAID">Paid</option><option value="DRAFT">Draft · reserved</option><option value="REVERSED">Dibalik</option></select>
        <select aria-label="Urutkan invoice" value={sort} onChange={event=>{setSort(event.target.value);setRegisterPage(0)}}><option value="NEWEST">Terbaru dulu</option><option value="OLDEST">Terlama dulu</option><option value="VALUE_ASC">Total terkecil</option><option value="VALUE_DESC">Total terbesar</option><option value="STORE">Urut toko</option></select>
      </div>
      <div className="biz-all-invoice-table">
        <div><span>Waktu / invoice</span><span>Toko</span><span>Barang</span><span>Total nota</span><span>Retur</span><span>Net</span><span>Status</span></div>
        {shown.map(invoice=>{
          const skus = skuByInvoice.get(invoice.number) ?? []
          const matched = registerQuery ? skus.find(sku => browseMatch(registerQuery, sku)) : undefined
          const preview = matched ? [matched, ...skus.filter(sku => sku !== matched).slice(0, 1)] : skus.slice(0, 2)
          return <button type="button" onClick={()=>setSelectedInvoice(invoice)} className={'invoice-register-row' + (!['POSTED','PAID'].includes(invoice.status) ? ' unposted' : '')} key={invoice.number}>
            <span data-label="Invoice"><strong>{invoice.number}</strong><small>{invoice.day} · {invoice.time}</small></span>
            <strong data-label="Toko">{invoice.customer}</strong>
            <span data-label="Barang" className="invoice-goods-cell"><strong className="piece-total">{invoice.qty.toLocaleString('id-ID')} pcs</strong>
              <small>{skus.length} SKU · {qtyLabel(invoice.qty)}</small>
              {preview.length > 0 && <span className="invoice-sku-preview">
                {preview.map(sku => <span className="invoice-sku-chip" key={sku}>{sku}</span>)}
                {skus.length > preview.length && <span className="invoice-sku-more" aria-label={`${skus.length - preview.length} SKU lain`}>+{skus.length - preview.length}</span>}
              </span>}
            </span>
            <b data-label="Total">{money(invoice.gross)}</b>
            <b data-label="Retur" className={invoice.returns>0?'negative':''}>{invoice.returns>0?`− ${money(invoice.returns)}`:'—'}</b>
            <strong data-label="Net">{money(invoice.gross-invoice.returns)}</strong>
            <span data-label="Status"><Pill tone={statusTone(invoice.status)}>{invoiceStatusLabel(invoice.status)}</Pill></span>
          </button>
        })}
      </div>
      {!visible.length && <p className="invoice-register-empty">Tidak ada invoice yang cocok.</p>}
      <InvoicePagination kind="nota" page={currentPage} perPage={invoicePageSize} count={visible.length} onPage={setRegisterPage}/>
      <footer><ShieldCheck/><span><strong>Reserve terjadi saat Draft.</strong><small>Mutasi −qty langsung mengurangi stok siap jual. Post hanya mengunci invoice serta membentuk AR, revenue, dan COGS—tanpa mutasi stok kedua.</small></span></footer>
    </section>
    <section className="biz-store-sales-layout"><article className="panel biz-store-ranking"><header><div><span>SALES PER TOKO</span><strong>Ranking toko · {periodLabel(period)}</strong></div><Store/></header>{storeTotals.map((item,index)=>{const storeNet=item.gross-item.returns;return <div key={item.name}><span>{String(index+1).padStart(2,'0')}</span><div><strong>{item.name}</strong><small>{item.count} invoice · {fgQuantity(item.qty)} · retur {money(item.returns)}</small><i><b style={{width:`${storeNet/maxStore*100}%`}}/></i></div><b>{money(storeNet)}</b></div>})}{storeTotals.length===0&&<div className="biz-empty compact"><FileSearch/><strong>Belum ada sales posted</strong><small>Draft tetap terlihat di register, tetapi tidak masuk total toko.</small></div>}</article><article className="panel biz-sales-timetable"><header><div><span>TIME TABLE</span><strong>Penjualan per tanggal · {periodLabel(period)}</strong></div><Clock3/></header><div className="biz-sales-time-head"><span>Tanggal</span>{customers.map((name)=><span key={name}>{name}</span>)}<span>Total</span></div>{!days.length&&<p>Tidak ada penjualan posted di periode ini.</p>}{days.map((dateKey)=>{const dayRows=counted.filter((invoice)=>invoice.dateKey===dateKey);const label=dayRows[0]?.day??dateKey;return <div className="biz-sales-time-row" key={dateKey}><strong><details><summary>{label}</summary>{dayRows.map(r=><button type="button" className="gar-text" onClick={()=>setSelectedInvoice(r)} key={r.number}>{r.time} · {r.number}</button>)}</details></strong>{customers.map((name)=>{const amount=dayRows.filter((invoice)=>invoice.customer===name).reduce((sum,invoice)=>sum+invoice.gross-invoice.returns,0);return <span key={name}>{amount?compactSales(amount):'—'}</span>})}<b>{compactSales(dayRows.reduce((sum,invoice)=>sum+invoice.gross-invoice.returns,0))}</b></div>})}</article></section>
    {selectedInvoice&&<ReviewModal
      title={selectedInvoice.number}
      description={selectedInvoice.status==='DRAFT'?`${selectedInvoice.customer} · reserve FIFO sudah mengurangi stok siap jual`:`${selectedInvoice.customer} · ${selectedInvoice.day} ${selectedInvoice.time}`}
      onClose={()=>setSelectedInvoice(null)}
      actionLabel={selectedInvoice.status==='DRAFT'?'Post invoice simulasi':'Buat draft koreksi'}
      disabled={selectedInvoice.status!=='DRAFT'&&(selectedInvoice.status!=='POSTED'||!!selectedInvoice.paid||!!selectedInvoice.returns)}
      action={()=>{
        if(selectedInvoice.status==='DRAFT'){
          const invoiceNumber=selectedInvoice.number
          const invoiceQty=selectedInvoice.qty
          try{setInvoices(postInvoice(invoiceNumber))}catch(e){setNotice((e as Error).message);setSelectedInvoice(null);return}
          setNotice(`${invoiceNumber} dipost tanpa minus stok kedua. Reserve ${invoiceQty} pcs tetap menjadi jejak pengeluaran; AR, revenue, dan COGS ikut terbentuk.`)
          setSelectedInvoice(null)
          return
        }
        globalThis.location.assign('/penjualan/invoice/?koreksi='+encodeURIComponent(selectedInvoice.number))
      }}
    >
      <div className="biz-invoice-detail-summary">
        <article><span>STATUS</span><strong><Pill tone={statusTone(selectedInvoice.status)}>{invoiceStatusLabel(selectedInvoice.status)}</Pill></strong><small>{['POSTED','PAID'].includes(selectedInvoice.status)?'Read-only':'Boleh diedit atau dipost'}</small></article>
        <article><span>JUMLAH BARANG</span><strong>{fgQuantity(selectedInvoice.qty)}</strong><small>{selectedSkus.length} SKU</small></article>
        <article><span>NET INVOICE</span><strong>{money(selectedInvoice.gross-selectedInvoice.returns)}</strong><small>Dibayar {money(selectedInvoice.paid)}</small></article>
        <article><span>STOK SIAP JUAL</span><strong>− {fgQuantity(selectedInvoice.qty)}</strong><small>{selectedInvoice.status==='DRAFT'?'Sudah turun sejak Draft':'Tidak dikurangi lagi saat Post'}</small></article>
      </div>
      {selectedInvoice.status==='DRAFT'&&<a className="gar-button primary" href={'/penjualan/invoice/?nota='+selectedInvoice.number}>Edit invoice ini</a>}
      <InvoiceGoods key={selectedInvoice.number} invoice={selectedInvoice} initialQuery={skuQuery}/>
      <div className="biz-invoice-event-log">
        <header><span>DOCUMENT HISTORY</span><strong>Jejak reservation dan stock event</strong></header>
        <article><Clock3/><span><strong>Draft dibuat</strong><small>{selectedInvoice.day} · {selectedInvoice.time} · masih boleh diedit</small></span></article>
        <article><Boxes/><span><strong>Mutasi RESERVE INVOICE</strong><small>Stok siap jual − {fgQuantity(selectedInvoice.qty)} · per SKU, size, lokasi, dan lot FIFO</small></span></article>
        {['POSTED','PAID'].includes(selectedInvoice.status)&&<article><PackageCheck/><span><strong>Post tanpa mutasi stok baru</strong><small>Reserve dikunci sebagai pengeluaran invoice; saldo tidak minus kedua</small></span></article>}
        {['POSTED','PAID'].includes(selectedInvoice.status)&&<article><ShieldCheck/><span><strong>Invoice terkunci</strong><small>AR, revenue, dan COGS terbentuk dalam posting yang sama</small></span></article>}
      </div>
      {selectedInvoice.status==='DRAFT'&&<div className="biz-invoice-correction-actions"><button type="button" className="soft-btn" onClick={()=>{globalThis.location.assign('/penjualan/invoice/?nota='+encodeURIComponent(selectedInvoice.number))}}><ReceiptText/> Buka & edit Draft</button><span><strong>Reserve mengikuti isi Draft real-time.</strong><small>Tambah qty membuat reserve −selisih; kurangi atau batal membuat release +selisih.</small></span></div>}
      {['POSTED','PAID'].includes(selectedInvoice.status)&&<div className="biz-invoice-correction-actions"><button type="button" className="soft-btn" onClick={()=>{setSelectedInvoice(null);onNavigate('sales-returns')}}><Undo2/> Retur fisik</button><span><strong>Edit langsung dinonaktifkan.</strong><small>Koreksi nominal/qty memakai reversal + draft pengganti. Retur fisik memakai dokumen retur.</small></span></div>}
      {selectedInvoice.paid>0&&['POSTED','PAID'].includes(selectedInvoice.status)&&<div className="biz-guard warn"><AlertTriangle/><span><strong>Reversal diblokir karena sudah ada pembayaran {money(selectedInvoice.paid)}.</strong><small>Void/reverse payment terkait lebih dulu atau gunakan retur/koreksi yang tidak merusak settlement.</small></span></div>}
    </ReviewModal>}
  </>
}

function ReturnsWorkspace() {
  const [selectedNumber,setSelectedNumber]=useState(returnableInvoices[0].number)
  const [query,setQuery]=useState('')
  const [quantities,setQuantities]=useState<Record<string,number>>({'73001-29':1})
  const [destination,setDestination]=useState('Gudang FG Utama')
  const [grade,setGrade]=useState('GRADE_A')
  const [reason,setReason]=useState('Ukuran tidak sesuai pesanan toko')
  const [reviewOpen,setReviewOpen]=useState(false)
  const [notice,setNotice]=useState('')
  const visible=returnableInvoices.filter((invoice)=>`${invoice.number} ${invoice.customer}`.toLowerCase().includes(query.toLowerCase()))
  const selected=returnableInvoices.find((invoice)=>invoice.number===selectedNumber)??returnableInvoices[0]
  const returnQty=selected.lines.reduce((sum,line)=>sum+(quantities[line.key]??0),0)
  const refund=selected.lines.reduce((sum,line)=>sum+(quantities[line.key]??0)*line.price,0)
  const valid=selected.lines.every((line)=>(quantities[line.key]??0)<=line.sold-line.returned)
  return <>
    <SalesHero eyebrow="PENJUALAN · KOREKSI TERKENDALI" title="Retur Penjualan" description="Cari invoice asal dan allocation yang benar, lalu preview dampak AR, revenue, stok FG, serta COGS. Retur tidak membuat transaksi lama hilang." icon={Undo2}/>
    <section className="panel biz-master-detail"><aside><header><div><span>INVOICE ASAL</span><strong>{visible.length} ditemukan</strong></div><FileSearch/></header><label className="biz-search"><Search/><input value={query} onChange={(event)=>setQuery(event.target.value)} placeholder="Cari invoice atau pelanggan..."/></label><div className="biz-browser-list">{visible.map((invoice)=><button key={invoice.number} className={invoice.number===selected.number?'active':''} onClick={()=>{setSelectedNumber(invoice.number);setQuantities({});setNotice('')}}><span>IN</span><div><strong>{invoice.number}</strong><small>{invoice.customer}</small><em>{invoice.date} · {invoice.lines.length} baris</em></div><ArrowRight/></button>)}</div></aside><main><header className="biz-detail-head"><div><span>RETUR DARI INVOICE</span><h2>{selected.number}</h2><p>{selected.customer} · {selected.date}</p></div><Pill tone="warn">DRAFT RETURN</Pill></header><div className="biz-return-meta"><label><span>WAKTU FISIK KEMBALI</span><input type="datetime-local" defaultValue="2026-08-28T10:45"/></label><label><span>TUJUAN</span><select value={destination} onChange={(event)=>setDestination(event.target.value)}><option>Gudang FG Utama</option><option>Gudang FG Cadangan</option><option>Area QC Retur</option></select></label><label><span>GRADE MASUK</span><select value={grade} onChange={(event)=>setGrade(event.target.value)}><option value="GRADE_A">Good / Grade A</option><option value="GRADE_B">Grade B</option><option value="HOLD">Hold QC</option></select></label></div><div className="biz-return-lines"><div><span>SKU / size / lot</span><span>Terjual</span><span>Sudah retur</span><span>Retur sekarang</span><span>Sisa eligible</span></div>{selected.lines.map((line)=>{const qty=quantities[line.key]??0;const eligible=line.sold-line.returned;return <article key={line.key} className={qty>eligible?'invalid':''}><strong>{line.sku}<small>Size {line.size} · {line.lot}</small></strong><span>{line.sold} pcs</span><span>{line.returned} pcs</span><label><input inputMode="numeric" value={qty||''} placeholder="0" onChange={(event)=>setQuantities((current)=>({...current,[line.key]:Math.max(0,Number(event.target.value.replace(/\D/g,''))||0)}))}/><b>pcs</b></label><b>{Math.max(0,eligible-qty)} pcs</b></article>})}</div><label className="biz-wide-field"><span>ALASAN RETUR</span><textarea value={reason} onChange={(event)=>setReason(event.target.value)} placeholder="Kenapa barang kembali?"/></label><div className="biz-impact-grid"><article><span>FG masuk kembali</span><strong>+ {returnQty} pcs</strong><small>{destination} · {grade}</small></article><article><span>AR / refund</span><strong>− {money(refund)}</strong><small>Net invoice pelanggan</small></article><article><span>COGS reversal</span><strong>Lot asal</strong><small>HPP versi sale tetap ditelusuri</small></article></div>{!valid&&<div className="biz-guard danger"><AlertTriangle/><span>Qty retur melebihi sisa eligible pada invoice asal.</span></div>}{notice&&<div className="biz-inline-notice"><CheckCircle2/> {notice}</div>}<footer className="biz-detail-actions"><span>Retur tidak menghapus sale; backend membuat dokumen dan jurnal koreksi baru.</span><button className="primary-btn" disabled={returnQty<=0||!valid||!reason.trim()} onClick={()=>setReviewOpen(true)}>Review retur <ArrowRight/></button></footer></main></section>
    {reviewOpen&&<ReviewModal title="Retur siap direview" description="Allocation sale asal, stok masuk, AR, revenue, COGS, dan jurnal harus dikoreksi atomically." onClose={()=>setReviewOpen(false)} action={()=>{setReviewOpen(false);setNotice('Simulasi retur tersimpan di layar. Backend belum berubah.')}}><div className="biz-impact-grid"><article><span>Qty</span><strong>{returnQty} pcs</strong><small>Ke {destination}</small></article><article><span>Nilai retur</span><strong>{money(refund)}</strong><small>Mengurangi AR/revenue</small></article><article><span>HPP</span><strong>Versi sale asal</strong><small>Bukan HPP current baru</small></article></div></ReviewModal>}
  </>
}

function PaymentsWorkspace() {
  const [query,setQuery]=useState('')
  const [customer,setCustomer]=useState('ALL')
  const filtered=receivables.filter((item)=>`${item.invoice} ${item.customer}`.toLowerCase().includes(query.toLowerCase())&&(customer==='ALL'||item.customer===customer))
  const [selectedInvoice,setSelectedInvoice]=useState(receivables[0].invoice)
  const selected=receivables.find((item)=>item.invoice===selectedInvoice)??receivables[0]
  const outstanding=Math.max(0,selected.gross-selected.returns-selected.paid)
  const [amount,setAmount]=useState('2000000')
  const [method,setMethod]=useState('TRANSFER')
  const [account,setAccount]=useState('BCA Operasional')
  const [reference,setReference]=useState('BCA-280826-1842')
  const [reviewOpen,setReviewOpen]=useState(false)
  const [notice,setNotice]=useState('')
  const paid=Math.max(0,Number(amount.replace(/\D/g,''))||0)
  const invalid=paid<=0||paid>outstanding
  return <>
    <SalesHero eyebrow="PENJUALAN · KAS & PIUTANG" title="Pembayaran Pelanggan" description="Pilih invoice terbuka, catat uang yang benar-benar diterima, lalu lihat saldo AR sebelum dan sesudah. Payment tidak pernah disamakan dengan sale." icon={WalletCards}/>
    <section className="biz-metrics"><div className="panel"><span>AR TERBUKA</span><strong>{money(receivables.reduce((sum,item)=>sum+item.gross-item.returns-item.paid,0))}</strong><small>Net retur dan payment</small></div><div className="panel danger"><span>OVERDUE</span><strong>2 invoice</strong><small>Perlu ditagih hari ini</small></div><div className="panel warn"><span>PARTIAL</span><strong>2 invoice</strong><small>Pembayaran sebagian</small></div><div className="panel good"><span>MASUK HARI INI</span><strong>Rp7,7 jt</strong><small>Posted cash receipts</small></div></section>
    <section className="panel biz-master-detail"><aside><header><div><span>PIUTANG TERBUKA</span><strong>{filtered.length} invoice</strong></div><Banknote/></header><label className="biz-search"><Search/><input value={query} onChange={(event)=>setQuery(event.target.value)} placeholder="Cari invoice atau toko..."/></label><select value={customer} onChange={(event)=>setCustomer(event.target.value)}><option value="ALL">Semua pelanggan</option>{[...new Set(receivables.map((item)=>item.customer))].map((name)=><option key={name}>{name}</option>)}</select><div className="biz-browser-list">{filtered.map((item)=>{const open=item.gross-item.returns-item.paid;return <button key={item.invoice} className={item.invoice===selected.invoice?'active':''} onClick={()=>{setSelectedInvoice(item.invoice);setAmount(String(Math.min(2_000_000,open)));setNotice('')}}><span>AR</span><div><strong>{item.invoice}</strong><small>{item.customer}</small><em>Jatuh tempo {item.dueDate}</em></div><b>{money(open)}</b><Pill tone={statusTone(item.status)}>{item.status}</Pill></button>})}</div></aside><main><header className="biz-detail-head"><div><span>CATAT UANG MASUK</span><h2>{selected.invoice}</h2><p>{selected.customer} · invoice {selected.invoiceDate}</p></div><Pill tone={statusTone(selected.status)}>{selected.status}</Pill></header><div className="biz-ar-equation"><span><small>GROSS SALE</small><strong>{money(selected.gross)}</strong></span><i>−</i><span><small>RETUR</small><strong>{money(selected.returns)}</strong></span><i>−</i><span><small>SUDAH DIBAYAR</small><strong>{money(selected.paid)}</strong></span><i>=</i><span><small>OUTSTANDING</small><strong>{money(outstanding)}</strong></span></div><div className="biz-payment-form"><label><span>JUMLAH DITERIMA</span><div><b>Rp</b><input inputMode="numeric" value={formatMoneyInput(amount)} onFocus={(event)=>event.currentTarget.select()} onChange={(event)=>setAmount(cleanMoneyInput(event.target.value))}/></div></label><label><span>METODE</span><select value={method} onChange={(event)=>setMethod(event.target.value)}><option>TRANSFER</option><option>CASH</option><option>GIRO</option></select></label><label><span>AKUN KAS / BANK</span><select value={account} onChange={(event)=>setAccount(event.target.value)}><option>BCA Operasional</option><option>Kas Utama</option><option>Mandiri Payroll</option></select></label><label><span>REFERENSI BANK</span><input value={reference} onChange={(event)=>setReference(event.target.value)} placeholder="Nomor transfer / bukti"/></label></div><div className="biz-impact-grid"><article><span>Kas / bank naik</span><strong>+ {money(paid)}</strong><small>{account}</small></article><article><span>AR turun</span><strong>− {money(paid)}</strong><small>{selected.invoice}</small></article><article><span>Sisa sesudah</span><strong>{money(Math.max(0,outstanding-paid))}</strong><small>{paid===outstanding?'Lunas':'Masih terbuka'}</small></article></div>{invalid&&paid>0&&<div className="biz-guard danger"><AlertTriangle/><span>Pembayaran tidak boleh melebihi outstanding invoice.</span></div>}{notice&&<div className="biz-inline-notice"><CheckCircle2/> {notice}</div>}<footer className="biz-detail-actions"><span>Invoice tetap utuh; payment menjadi transaksi uang terpisah.</span><button className="primary-btn" disabled={invalid||!reference.trim()} onClick={()=>setReviewOpen(true)}>Review payment <ArrowRight/></button></footer></main></section>
    {reviewOpen&&<ReviewModal title="Pembayaran siap direview" description="Kas/bank dan AR akan bergerak bersama saat domain RPC nanti diaktifkan." onClose={()=>setReviewOpen(false)} action={()=>{setReviewOpen(false);setNotice('Simulasi payment tersimpan. Tidak ada uang atau backend yang berubah.')}}><div className="biz-impact-grid"><article><span>Diterima</span><strong>{money(paid)}</strong><small>{method}</small></article><article><span>Akun</span><strong>{account}</strong><small>{reference}</small></article><article><span>Saldo AR</span><strong>{money(Math.max(0,outstanding-paid))}</strong><small>{selected.invoice}</small></article></div></ReviewModal>}
  </>
}

function CustomerHistoryWorkspace() {
  const [customer,setCustomer]=useState('ALL')
  const [type,setType]=useState('ALL')
  const [query,setQuery]=useState('')
  const [period,setPeriod]=useState(()=>periodFor('month','2026-08-28'))
  const [historyOrder,setHistoryOrder]=useState('new')
  const registered=readInvoices().filter(d=>!['DRAFT','REVERSED','CANCELLED'].includes(d.status))
  const events=[
    ...registered.map(d=>({date:d.day+' · '+d.time,dateKey:d.dateKey,time:d.time,customer:d.customer,type:'SALE',number:d.number,description:'Penjualan '+d.sku,sku:d.sku,qty:d.qty,amount:d.gross})),
    ...customerEvents.filter(e=>e.type!=='SALE').map(e=>({...e,dateKey:'2026-08-'+e.date.slice(0,2),time:e.date.slice(-5)}))
  ]
  const visible=events.filter(e=>matchesPeriod(e.dateKey,period)&&[e.customer,e.number,e.description,e.sku].join(' ').toLowerCase().includes(query.toLowerCase())&&(customer==='ALL'||e.customer===customer)&&(type==='ALL'||e.type===type))
    .sort((a,b)=>(historyOrder==='new'?-1:1)*(a.dateKey.localeCompare(b.dateKey)||a.time.localeCompare(b.time)||a.number.localeCompare(b.number)))
  const openAr=registered.filter(d=>matchesPeriod(d.dateKey,period)&&(customer==='ALL'||d.customer===customer)&&[d.customer,d.number,d.sku].join(' ').toLowerCase().includes(query.toLowerCase())).reduce((n,d)=>n+Math.max(0,d.gross-d.returns-d.paid),0)
  const sales=visible.filter((event)=>event.type==='SALE').reduce((sum,event)=>sum+event.amount,0)
  const payments=visible.filter((event)=>event.type==='PAYMENT').reduce((sum,event)=>sum+event.amount,0)
  const returns=Math.abs(visible.filter((event)=>event.type==='RETURN').reduce((sum,event)=>sum+event.amount,0))
  return <>
    <SalesHero eyebrow="PENJUALAN · CUSTOMER 360" title="Riwayat Pelanggan" description="Lihat semua toko atau satu toko: qty, omzet, SKU, warna, invoice, payment, retur, dan outstanding AR dalam satu alur kronologis." icon={Store}/>
    <section className="panel biz-history-toolbar"><label className="biz-search"><Search/><input value={query} onChange={(event)=>setQuery(event.target.value)} placeholder="Cari toko, invoice, SKU, atau aktivitas..."/></label><select value={customer} onChange={(event)=>setCustomer(event.target.value)}><option value="ALL">Semua pelanggan</option>{[...new Set(events.map((event)=>event.customer))].map((name)=><option key={name}>{name}</option>)}</select><select value={type} onChange={(event)=>setType(event.target.value)}><option value="ALL">Semua aktivitas</option><option>SALE</option><option>PAYMENT</option><option>RETURN</option></select></section><PeriodFilter label="Periode aktivitas" value={period} onChange={setPeriod}/>
    <section className="biz-metrics"><div className="panel good"><span>PENJUALAN</span><strong>{money(sales)}</strong><small>{visible.filter((event)=>event.type==='SALE').reduce((sum,event)=>sum+event.qty,0)} pcs</small></div><div className="panel"><span>PEMBAYARAN</span><strong>{money(payments)}</strong><small>Uang benar-benar masuk</small></div><div className="panel danger"><span>RETUR</span><strong>{money(returns)}</strong><small>Mengurangi net sale</small></div><div className="panel warn"><span>OUTSTANDING AR</span><strong>{money(openAr)}</strong><small>Sisa tagihan invoice pada periode dan toko ini</small></div></section>
    <section className="panel biz-timeline"><header><div><span>ACTIVITY TIMELINE</span><select aria-label="Urutan aktivitas" value={historyOrder} onChange={e=>setHistoryOrder(e.target.value)}><option value="new">Terbaru dulu</option><option value="old">Terlama dulu</option></select><strong>{visible.length} kejadian · {periodLabel(period)}</strong></div><History/></header>{visible.map((event)=><article key={event.number}><time>{event.date}</time><i className={event.type.toLowerCase()}>{event.type==='SALE'?<ShoppingBag/>:event.type==='PAYMENT'?<WalletCards/>:<Undo2/>}</i><div><span><Pill tone={event.type==='SALE'?'good':event.type==='PAYMENT'?'neutral':'danger'}>{event.type}</Pill><small>{event.customer}</small></span><strong>{event.description}</strong><em>{event.type==='SALE'?<a className="gar-text" href={'/penjualan/semua-invoice/?nota='+encodeURIComponent(event.number)}>{event.number}</a>:event.number} · SKU {event.sku}{event.qty?' · '+fgQuantity(event.qty):''}</em></div><b className={event.amount<0?'negative':'positive'}>{event.amount<0?'− ':'+ '}{money(Math.abs(event.amount))}</b></article>)}{visible.length===0&&<div className="biz-empty"><FileSearch/><strong>Aktivitas tidak ditemukan</strong><small>Ubah filter atau pencarian.</small></div>}</section>
  </>
}
