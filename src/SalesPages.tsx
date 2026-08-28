import { useMemo, useState } from 'react'
import {
  AlertTriangle, ArrowRight, Banknote, Boxes, Check, CheckCircle2, Clock3,
  FileSearch, History, PackageCheck, PackageSearch, Plus, ReceiptText,
  RotateCcw, Search, ShieldCheck, ShoppingBag, Store, Trash2, Undo2,
  WalletCards, X,
} from 'lucide-react'
import { productCatalog } from './productCatalog'
import type { Product } from './productCatalog'
import './business-pages.css'

export type SalesView = 'sales-invoice' | 'sales-allocation' | 'sales-returns' | 'sales-payments' | 'sales-history'

type SalesPageProps = { view: SalesView; onNavigate: (view: SalesView) => void }
type DraftLine = { key: string; product: Product; quantities: [number, number, number]; priceDozen: number }
type Tone = 'good' | 'warn' | 'danger' | 'neutral'

const money = (value: number) => new Intl.NumberFormat('id-ID', {
  style: 'currency', currency: 'IDR', maximumFractionDigits: 0,
}).format(value)
const number = (value: number) => new Intl.NumberFormat('id-ID', { maximumFractionDigits: 0 }).format(value)
const productKey = (product: Pick<Product, 'brand' | 'code'>) => `${product.brand}::${product.code}`
const qtyLabel = (qty: number) => `${Math.floor(Math.max(0, qty) / 12)} lusin · ${Math.max(0, qty) % 12} potong`
const lineQty = (line: DraftLine) => line.quantities.reduce((sum, qty) => sum + qty, 0)
const lineGross = (line: DraftLine) => (lineQty(line) / 12) * line.priceDozen

function makeLine(product: Product, dozens: number): DraftLine {
  const total = Math.max(0, Math.round(dozens * 12))
  const base = Math.floor(total / 3)
  const remainder = total % 3
  return {
    key: productKey(product), product,
    quantities: [base + (remainder > 0 ? 1 : 0), base + (remainder > 1 ? 1 : 0), base],
    priceDozen: product.brand === 'Widie' ? 1_140_000 : 1_080_000,
  }
}

const invoiceHistory = [
  { number:'INV-JUAL-0245', customer:'Nusantara Fashion', date:'28 Agu 2026 · 10:30', sku:'73001 · 73005', qty:72, gross:6_660_000, status:'DRAFT' },
  { number:'INV-JUAL-0244', customer:'Toko Maju Jaya', date:'28 Agu 2026 · 09:15', sku:'73003', qty:64, gross:5_760_000, status:'WAITING_ALLOCATION' },
  { number:'INV-JUAL-0241', customer:'Toko Maju Jaya', date:'27 Agu 2026 · 16:24', sku:'73001 · 73002', qty:84, gross:7_830_000, status:'POSTED' },
  { number:'INV-JUAL-0240', customer:'Nusantara Fashion', date:'27 Agu 2026 · 15:18', sku:'73001 · 73005', qty:144, gross:13_320_000, status:'POSTED' },
]

const allocationOrders = [
  {
    number:'INV-JUAL-0245', customer:'Nusantara Fashion', at:'28 Agu 2026 · 10:30', status:'READY',
    lines:[
      { sku:'Vivo · 73001', size:'28', requested:12, onHand:96, lot:'FG-73001-0821', fifo:12 },
      { sku:'Vivo · 73001', size:'29', requested:12, onHand:84, lot:'FG-73001-0822', fifo:12 },
      { sku:'Vivo · 73001', size:'30', requested:12, onHand:108, lot:'FG-73001-0820', fifo:12 },
      { sku:'Widie · 73005', size:'31', requested:12, onHand:48, lot:'FG-73005-0819', fifo:12 },
      { sku:'Widie · 73005', size:'32', requested:12, onHand:54, lot:'FG-73005-0818', fifo:12 },
      { sku:'Widie · 73005', size:'33', requested:12, onHand:42, lot:'FG-73005-0817', fifo:12 },
    ],
  },
  {
    number:'INV-JUAL-0244', customer:'Toko Maju Jaya', at:'28 Agu 2026 · 09:15', status:'SHORT',
    lines:[
      { sku:'Vivo · 73003', size:'34', requested:12, onHand:36, lot:'FG-73003-0824', fifo:12 },
      { sku:'Vivo · 73003', size:'35', requested:12, onHand:42, lot:'FG-73003-0823', fifo:12 },
      { sku:'Vivo · 73003', size:'36', requested:40, onHand:32, lot:'FG-73003-0822', fifo:32 },
    ],
  },
  {
    number:'DRAFT-0091', customer:'Sentra Denim', at:'28 Agu 2026 · 08:40', status:'DRAFT',
    lines:[
      { sku:'Widie · 73006', size:'34', requested:4, onHand:24, lot:'Belum dipilih', fifo:0 },
      { sku:'Widie · 73006', size:'35', requested:4, onHand:30, lot:'Belum dipilih', fifo:0 },
      { sku:'Widie · 73006', size:'36', requested:4, onHand:36, lot:'Belum dipilih', fifo:0 },
    ],
  },
]

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
  { date:'27 Agu · 15:18', customer:'Nusantara Fashion', type:'SALE', number:'INV-JUAL-0240', description:'73001, 73005 · Indigo dan Mid Blue', sku:'73001 · 73005', qty:144, amount:13_320_000 },
  { date:'27 Agu · 14:02', customer:'Toko Maju Jaya', type:'RETURN', number:'RET-JUAL-0045', description:'Retur 73001 size 29', sku:'73001', qty:2, amount:-180_000 },
  { date:'27 Agu · 11:06', customer:'Sentra Denim', type:'SALE', number:'INV-JUAL-0239', description:'73003, 73006 · Charcoal dan Stone', sku:'73003 · 73006', qty:60, amount:5_730_000 },
  { date:'26 Agu · 16:24', customer:'Toko Maju Jaya', type:'SALE', number:'INV-JUAL-0241', description:'73001, 73002 · empat size aktif', sku:'73001 · 73002', qty:84, amount:7_830_000 },
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
  if (['PARTIAL','WAITING_ALLOCATION'].includes(status)) return 'warn'
  return 'neutral'
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
  const [customer,setCustomer] = useState('Nusantara Fashion')
  const [location,setLocation] = useState('Gudang FG Utama')
  const [terms,setTerms] = useState('NET 30')
  const [physicalAt,setPhysicalAt] = useState('2026-08-28T10:30')
  const [dueDate,setDueDate] = useState('2026-09-27')
  const [query,setQuery] = useState('')
  const [brand,setBrand] = useState('Semua merek')
  const [defaultDozens,setDefaultDozens] = useState('1')
  const [lines,setLines] = useState<DraftLine[]>([makeLine(productCatalog[0],3),makeLine(productCatalog[6],3)])
  const [notice,setNotice] = useState('')
  const [reviewOpen,setReviewOpen] = useState(false)
  const [clearOpen,setClearOpen] = useState(false)

  const visibleProducts = useMemo(()=>productCatalog.filter((product)=>{
    const haystack=`${product.brand} ${product.code} ${product.name} ${product.color} ${product.range}`.toLowerCase()
    return haystack.includes(query.toLowerCase()) && (brand==='Semua merek'||product.brand===brand)
  }),[query,brand])
  const totalQty=lines.reduce((sum,line)=>sum+lineQty(line),0)
  const gross=lines.reduce((sum,line)=>sum+lineGross(line),0)
  const stockValid=lines.every((line)=>line.quantities.every((qty,index)=>qty<=line.product.stocks[index]))
  const canReview=lines.length>0&&totalQty>0&&stockValid&&customer.trim().length>0

  const addProduct=(product:Product)=>{
    const key=productKey(product)
    if(lines.some((line)=>line.key===key)){setNotice(`${product.brand} ${product.code} sudah ada di invoice.`);return}
    const dozens=Math.max(0,Number(defaultDozens.replace(',','.'))||0)
    setLines((current)=>[...current,makeLine(product,dozens)])
    setNotice(`${product.brand} ${product.code} masuk ke invoice.`)
  }
  const updateQty=(key:string,index:number,value:string)=>setLines((current)=>current.map((line)=>{
    if(line.key!==key)return line
    const next=[...line.quantities] as [number,number,number]
    next[index]=Math.max(0,Math.round(Number(value.replace(/\D/g,''))||0))
    return {...line,quantities:next}
  }))
  const updatePrice=(key:string,value:string)=>setLines((current)=>current.map((line)=>line.key===key?{...line,priceDozen:Math.max(0,Number(value.replace(/\D/g,''))||0)}:line))

  return <>
    <SalesHero eyebrow="PENJUALAN · INVOICE BUILDER" title="Penjualan & Invoice" description="Pilih pelanggan sekali, masukkan banyak SKU, isi size, lalu review stok, allocation FIFO, piutang, dan HPP sebelum posting." icon={ReceiptText}/>
    <section className="biz-meta panel">
      <label><span>PELANGGAN</span><select value={customer} onChange={(event)=>setCustomer(event.target.value)}><option>Nusantara Fashion</option><option>Toko Maju Jaya</option><option>Sentra Denim</option></select></label>
      <label><span>LOKASI FG</span><select value={location} onChange={(event)=>setLocation(event.target.value)}><option>Gudang FG Utama</option><option>Gudang FG Cadangan</option></select></label>
      <label><span>WAKTU FISIK</span><input type="datetime-local" value={physicalAt} onChange={(event)=>setPhysicalAt(event.target.value)}/></label>
      <label><span>TERMIN</span><select value={terms} onChange={(event)=>setTerms(event.target.value)}><option>NET 30</option><option>COD</option><option>NET 14</option><option>NET 45</option></select></label>
      <label><span>JATUH TEMPO</span><input type="date" value={dueDate} onChange={(event)=>setDueDate(event.target.value)}/></label>
    </section>

    <section className="biz-sales-builder">
      <aside className="panel biz-catalog">
        <header><div><span>TAMBAH SKU</span><strong>{visibleProducts.length} barang tampil</strong></div><PackageSearch/></header>
        <label className="biz-search"><Search/><input value={query} onChange={(event)=>setQuery(event.target.value)} placeholder="Ketik SKU, merek, model, warna..."/></label>
        <div className="biz-inline-filters"><select value={brand} onChange={(event)=>setBrand(event.target.value)}><option>Semua merek</option><option>Vivo</option><option>Widie</option></select><label><span>DEFAULT</span><input inputMode="decimal" value={defaultDozens} onChange={(event)=>setDefaultDozens(event.target.value.replace(/[^0-9,.]/g,''))}/><b>lusin</b></label></div>
        <div className="biz-catalog-list">{visibleProducts.map((product)=>{const added=lines.some((line)=>line.key===productKey(product));const stock=product.stocks.reduce((sum,qty)=>sum+qty,0);return <button key={productKey(product)} className={added?'added':''} onClick={()=>addProduct(product)}><span>{product.brand.slice(0,1)}</span><div><strong>{product.brand} · {product.code}</strong><small>{product.name} · {product.color}</small><em>{product.range} · {stock} pcs</em></div>{added?<Check/>:<Plus/>}</button>})}</div>
      </aside>

      <div className="panel biz-invoice-draft">
        <header><div><span>INVOICE DRAFT</span><strong>{lines.length} SKU · {totalQty} pcs</strong></div><button className="biz-danger-soft" disabled={lines.length===0} onClick={()=>setClearOpen(true)}><Trash2/> Kosongkan</button></header>
        {notice&&<div className="biz-inline-notice"><CheckCircle2/> {notice}</div>}
        <div className="biz-invoice-lines">{lines.map((line,index)=>{const qty=lineQty(line);const invalid=line.quantities.some((value,sizeIndex)=>value>line.product.stocks[sizeIndex]);return <article key={line.key} className={invalid?'invalid':''}><header><span>{String(index+1).padStart(2,'0')}</span><div><strong>{line.product.brand} · {line.product.code}</strong><small>{line.product.name} · {line.product.color} · {line.product.range}</small></div><b>{money(lineGross(line))}</b><button aria-label={`Hapus ${line.product.code}`} onClick={()=>setLines((current)=>current.filter((item)=>item.key!==line.key))}><X/></button></header><div className="biz-size-entry" data-keyboard-grid>{line.product.sizes.map((size,sizeIndex)=><label key={size} className={line.quantities[sizeIndex]>line.product.stocks[sizeIndex]?'invalid':''}><span>SIZE {size}</span><div><input data-grid-row={index} data-grid-col={sizeIndex} inputMode="numeric" value={line.quantities[sizeIndex]} onFocus={(event)=>event.currentTarget.select()} onChange={(event)=>updateQty(line.key,sizeIndex,event.target.value)}/><b>pcs</b></div><small>stok {line.product.stocks[sizeIndex]} pcs</small></label>)}</div><footer><span><small>QTY BARIS</small><strong>{qty} pcs · {qtyLabel(qty)}</strong></span><label><small>HARGA / LUSIN</small><div><b>Rp</b><input inputMode="numeric" value={line.priceDozen} onFocus={(event)=>event.currentTarget.select()} onChange={(event)=>updatePrice(line.key,event.target.value)}/></div></label>{invalid&&<em><AlertTriangle/> Ada size melebihi stok.</em>}</footer></article>})}{lines.length===0&&<div className="biz-empty"><ShoppingBag/><strong>Invoice masih kosong</strong><small>Klik SKU di katalog sebelah kiri.</small></div>}</div>
      </div>

      <aside className="panel biz-review-card">
        <span>RINGKASAN INVOICE</span><h2>{money(gross)}</h2><p>{customer} · {terms}</p>
        <div><article><small>SKU</small><strong>{lines.length}</strong></article><article><small>QTY</small><strong>{totalQty} pcs</strong></article><article><small>LUSIN</small><strong>{(totalQty/12).toLocaleString('id-ID',{maximumFractionDigits:2})}</strong></article></div>
        <section><p><Check/> Stok dicek per merek · SKU · size</p><p><Check/> FIFO lot dipilih backend saat posting</p><p><Check/> HPP lot menjadi COGS snapshot</p><p><Check/> Invoice membentuk AR, bukan kas</p></section>
        {!stockValid&&<div className="biz-guard danger"><AlertTriangle/><span>Ada qty melebihi stok. Posting harus diblokir.</span></div>}
        <label><span>CATATAN INVOICE</span><textarea placeholder="PO pelanggan, instruksi kirim, atau catatan harga..."/></label>
        <button className="primary-btn" disabled={!canReview} onClick={()=>setReviewOpen(true)}>Review invoice <ArrowRight/></button>
        <button className="soft-btn" onClick={()=>onNavigate('sales-allocation')}>Buka antrean alokasi</button>
      </aside>
    </section>

    <section className="panel biz-history-block"><header><div><span>INVOICE TERBARU</span><strong>Draft, menunggu alokasi, dan posted</strong></div><History/></header><div className="biz-table"><div className="biz-table-head"><span>Nomor / waktu</span><span>Pelanggan</span><span>SKU / qty</span><span>Nilai</span><span>Status</span></div>{invoiceHistory.map((item)=><article key={item.number}><span><strong>{item.number}</strong><small>{item.date}</small></span><strong>{item.customer}</strong><span>{item.sku}<small>{item.qty} pcs · {qtyLabel(item.qty)}</small></span><b>{money(item.gross)}</b><Pill tone={statusTone(item.status)}>{item.status}</Pill></article>)}</div></section>

    {reviewOpen&&<ReviewModal title="Invoice siap direview" description="Ini preview lokal. Backend belum berubah dan nomor final belum dibuat." onClose={()=>setReviewOpen(false)} action={()=>{setReviewOpen(false);setNotice('Draft invoice tersimpan di layar. Belum ada data backend yang berubah.')}}><div className="biz-impact-grid"><article><span>FG keluar</span><strong>− {totalQty} pcs</strong><small>Per size dan lot FIFO</small></article><article><span>Piutang naik</span><strong>+ {money(gross)}</strong><small>Kas tetap tidak berubah</small></article><article><span>COGS</span><strong>Dari HPP lot</strong><small>Bukan harga rata-rata SKU</small></article></div><div className="biz-guard"><ShieldCheck/><span>Posting final nanti wajib atomic: allocation, stock ledger, invoice, AR, COGS, dan jurnal berhasil bersama atau semuanya batal.</span></div></ReviewModal>}
    {clearOpen&&<ReviewModal danger actionLabel="Kosongkan draft" title="Kosongkan draft invoice?" description="Hanya baris draft di layar yang dibuang. Invoice posted tidak pernah dihapus dari sini." onClose={()=>setClearOpen(false)} action={()=>{setLines([]);setClearOpen(false);setNotice('Draft invoice dikosongkan.')}}><div className="biz-guard danger"><AlertTriangle/><span>{lines.length} SKU dan {totalQty} pcs akan dikeluarkan dari draft lokal.</span></div></ReviewModal>}
  </>
}

function AllocationWorkspace({ onNavigate }: { onNavigate: SalesPageProps['onNavigate'] }) {
  const [query,setQuery]=useState('')
  const [status,setStatus]=useState('ALL')
  const [selectedNumber,setSelectedNumber]=useState(allocationOrders[0].number)
  const [showFifo,setShowFifo]=useState(true)
  const visible=allocationOrders.filter((order)=>`${order.number} ${order.customer}`.toLowerCase().includes(query.toLowerCase())&&(status==='ALL'||order.status===status))
  const selected=allocationOrders.find((order)=>order.number===selectedNumber)??allocationOrders[0]
  const requested=selected.lines.reduce((sum,line)=>sum+line.requested,0)
  const allocated=selected.lines.reduce((sum,line)=>sum+Math.min(line.requested,line.onHand),0)
  return <>
    <SalesHero eyebrow="PENJUALAN · BARANG JADI" title="Alokasi Barang Jadi" description="Preview kebutuhan per size dan lot FIFO sebelum invoice dipost. Operator menangani exception stok; urutan lot tetap dipilih server." icon={PackageSearch}/>
    <section className="biz-metrics"><div className="panel"><span>ANTREAN</span><strong>{allocationOrders.length}</strong><small>Invoice dan draft</small></div><div className="panel good"><span>READY</span><strong>1</strong><small>Stok cukup</small></div><div className="panel danger"><span>SHORT</span><strong>1</strong><small>Butuh koreksi qty</small></div><div className="panel"><span>QTY TERPILIH</span><strong>{allocated}/{requested}</strong><small>pcs teralokasi</small></div></section>
    <section className="panel biz-master-detail"><aside><header><div><span>BROWSE ORDER</span><strong>{visible.length} tampil</strong></div><Boxes/></header><label className="biz-search"><Search/><input value={query} onChange={(event)=>setQuery(event.target.value)} placeholder="Cari invoice atau pelanggan..."/></label><select value={status} onChange={(event)=>setStatus(event.target.value)}><option value="ALL">Semua status</option><option>READY</option><option>SHORT</option><option>DRAFT</option></select><div className="biz-browser-list">{visible.map((order)=><button key={order.number} className={order.number===selected.number?'active':''} onClick={()=>setSelectedNumber(order.number)}><span>{order.status==='READY'?'OK':order.status==='SHORT'?'!':'D'}</span><div><strong>{order.number}</strong><small>{order.customer}</small><em>{order.at}</em></div><Pill tone={statusTone(order.status)}>{order.status}</Pill></button>)}</div></aside><main><header className="biz-detail-head"><div><span>ORDER TERPILIH</span><h2>{selected.number}</h2><p>{selected.customer} · {selected.at}</p></div><Pill tone={statusTone(selected.status)}>{selected.status}</Pill></header><div className="biz-toggle"><div><strong>Perlihatkan lot FIFO</strong><small>Lot hanya preview; server menentukan urutan final.</small></div><button className={showFifo?'active':''} onClick={()=>setShowFifo((value)=>!value)}>{showFifo?'ON':'OFF'}</button></div><div className="biz-allocation-table"><div><span>SKU / size</span><span>Diminta</span><span>On hand</span><span>{showFifo?'Lot FIFO':'Status'}</span><span>Teralokasi</span></div>{selected.lines.map((line)=><article key={`${line.sku}-${line.size}`} className={line.requested>line.onHand?'invalid':''}><strong>{line.sku}<small>Size {line.size}</small></strong><span>{line.requested} pcs</span><span>{line.onHand} pcs</span><span>{showFifo?line.lot:line.requested<=line.onHand?'Cukup':'Kurang'}</span><b>{Math.min(line.requested,line.onHand)} pcs</b></article>)}</div>{selected.status==='SHORT'&&<div className="biz-guard danger"><AlertTriangle/><span>Qty size 36 kurang 8 pcs. Ubah invoice, pilih pengiriman parsial, atau tunggu FG baru—jangan paksa stok negatif.</span></div>}<footer className="biz-detail-actions"><button className="soft-btn" onClick={()=>onNavigate('sales-invoice')}>Buka invoice</button><button className="primary-btn" disabled={selected.status!=='READY'}>Review posting <ArrowRight/></button></footer></main></section>
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
    <section className="panel biz-master-detail"><aside><header><div><span>PIUTANG TERBUKA</span><strong>{filtered.length} invoice</strong></div><Banknote/></header><label className="biz-search"><Search/><input value={query} onChange={(event)=>setQuery(event.target.value)} placeholder="Cari invoice atau toko..."/></label><select value={customer} onChange={(event)=>setCustomer(event.target.value)}><option value="ALL">Semua pelanggan</option>{[...new Set(receivables.map((item)=>item.customer))].map((name)=><option key={name}>{name}</option>)}</select><div className="biz-browser-list">{filtered.map((item)=>{const open=item.gross-item.returns-item.paid;return <button key={item.invoice} className={item.invoice===selected.invoice?'active':''} onClick={()=>{setSelectedInvoice(item.invoice);setAmount(String(Math.min(2_000_000,open)));setNotice('')}}><span>AR</span><div><strong>{item.invoice}</strong><small>{item.customer}</small><em>Jatuh tempo {item.dueDate}</em></div><b>{money(open)}</b><Pill tone={statusTone(item.status)}>{item.status}</Pill></button>})}</div></aside><main><header className="biz-detail-head"><div><span>CATAT UANG MASUK</span><h2>{selected.invoice}</h2><p>{selected.customer} · invoice {selected.invoiceDate}</p></div><Pill tone={statusTone(selected.status)}>{selected.status}</Pill></header><div className="biz-ar-equation"><span><small>GROSS SALE</small><strong>{money(selected.gross)}</strong></span><i>−</i><span><small>RETUR</small><strong>{money(selected.returns)}</strong></span><i>−</i><span><small>SUDAH DIBAYAR</small><strong>{money(selected.paid)}</strong></span><i>=</i><span><small>OUTSTANDING</small><strong>{money(outstanding)}</strong></span></div><div className="biz-payment-form"><label><span>JUMLAH DITERIMA</span><div><b>Rp</b><input inputMode="numeric" value={amount} onFocus={(event)=>event.currentTarget.select()} onChange={(event)=>setAmount(event.target.value.replace(/\D/g,''))}/></div></label><label><span>METODE</span><select value={method} onChange={(event)=>setMethod(event.target.value)}><option>TRANSFER</option><option>CASH</option><option>GIRO</option></select></label><label><span>AKUN KAS / BANK</span><select value={account} onChange={(event)=>setAccount(event.target.value)}><option>BCA Operasional</option><option>Kas Utama</option><option>Mandiri Payroll</option></select></label><label><span>REFERENSI BANK</span><input value={reference} onChange={(event)=>setReference(event.target.value)} placeholder="Nomor transfer / bukti"/></label></div><div className="biz-impact-grid"><article><span>Kas / bank naik</span><strong>+ {money(paid)}</strong><small>{account}</small></article><article><span>AR turun</span><strong>− {money(paid)}</strong><small>{selected.invoice}</small></article><article><span>Sisa sesudah</span><strong>{money(Math.max(0,outstanding-paid))}</strong><small>{paid===outstanding?'Lunas':'Masih terbuka'}</small></article></div>{invalid&&paid>0&&<div className="biz-guard danger"><AlertTriangle/><span>Pembayaran tidak boleh melebihi outstanding invoice.</span></div>}{notice&&<div className="biz-inline-notice"><CheckCircle2/> {notice}</div>}<footer className="biz-detail-actions"><span>Invoice tetap utuh; payment menjadi transaksi uang terpisah.</span><button className="primary-btn" disabled={invalid||!reference.trim()} onClick={()=>setReviewOpen(true)}>Review payment <ArrowRight/></button></footer></main></section>
    {reviewOpen&&<ReviewModal title="Pembayaran siap direview" description="Kas/bank dan AR akan bergerak bersama saat domain RPC nanti diaktifkan." onClose={()=>setReviewOpen(false)} action={()=>{setReviewOpen(false);setNotice('Simulasi payment tersimpan. Tidak ada uang atau backend yang berubah.')}}><div className="biz-impact-grid"><article><span>Diterima</span><strong>{money(paid)}</strong><small>{method}</small></article><article><span>Akun</span><strong>{account}</strong><small>{reference}</small></article><article><span>Saldo AR</span><strong>{money(Math.max(0,outstanding-paid))}</strong><small>{selected.invoice}</small></article></div></ReviewModal>}
  </>
}

function CustomerHistoryWorkspace() {
  const [customer,setCustomer]=useState('ALL')
  const [type,setType]=useState('ALL')
  const [query,setQuery]=useState('')
  const [period,setPeriod]=useState('30D')
  const visible=customerEvents.filter((event)=>`${event.customer} ${event.number} ${event.description} ${event.sku}`.toLowerCase().includes(query.toLowerCase())&&(customer==='ALL'||event.customer===customer)&&(type==='ALL'||event.type===type))
  const sales=visible.filter((event)=>event.type==='SALE').reduce((sum,event)=>sum+event.amount,0)
  const payments=visible.filter((event)=>event.type==='PAYMENT').reduce((sum,event)=>sum+event.amount,0)
  const returns=Math.abs(visible.filter((event)=>event.type==='RETURN').reduce((sum,event)=>sum+event.amount,0))
  return <>
    <SalesHero eyebrow="PENJUALAN · CUSTOMER 360" title="Riwayat Pelanggan" description="Lihat semua toko atau satu toko: qty, omzet, SKU, warna, invoice, payment, retur, dan outstanding AR dalam satu alur kronologis." icon={Store}/>
    <section className="panel biz-history-toolbar"><label className="biz-search"><Search/><input value={query} onChange={(event)=>setQuery(event.target.value)} placeholder="Cari toko, invoice, SKU, atau aktivitas..."/></label><select value={customer} onChange={(event)=>setCustomer(event.target.value)}><option value="ALL">Semua pelanggan</option>{[...new Set(customerEvents.map((event)=>event.customer))].map((name)=><option key={name}>{name}</option>)}</select><select value={type} onChange={(event)=>setType(event.target.value)}><option value="ALL">Semua aktivitas</option><option>SALE</option><option>PAYMENT</option><option>RETURN</option></select><div className="biz-period-tabs">{['7D','30D','90D'].map((item)=><button key={item} className={period===item?'active':''} onClick={()=>setPeriod(item)}>{item}</button>)}</div></section>
    <section className="biz-metrics"><div className="panel good"><span>PENJUALAN</span><strong>{money(sales)}</strong><small>{visible.filter((event)=>event.type==='SALE').reduce((sum,event)=>sum+event.qty,0)} pcs</small></div><div className="panel"><span>PEMBAYARAN</span><strong>{money(payments)}</strong><small>Uang benar-benar masuk</small></div><div className="panel danger"><span>RETUR</span><strong>{money(returns)}</strong><small>Mengurangi net sale</small></div><div className="panel warn"><span>OUTSTANDING AR</span><strong>Rp12,4 jt</strong><small>Sesuai filter pelanggan</small></div></section>
    <section className="panel biz-timeline"><header><div><span>ACTIVITY TIMELINE</span><strong>{visible.length} kejadian · {period}</strong></div><History/></header>{visible.map((event)=><article key={event.number}><time>{event.date}</time><i className={event.type.toLowerCase()}>{event.type==='SALE'?<ShoppingBag/>:event.type==='PAYMENT'?<WalletCards/>:<Undo2/>}</i><div><span><Pill tone={event.type==='SALE'?'good':event.type==='PAYMENT'?'neutral':'danger'}>{event.type}</Pill><small>{event.customer}</small></span><strong>{event.description}</strong><em>{event.number} · SKU {event.sku}{event.qty?` · ${event.qty} pcs`:''}</em></div><b className={event.amount<0?'negative':'positive'}>{event.amount<0?'− ':'+ '}{money(Math.abs(event.amount))}</b></article>)}{visible.length===0&&<div className="biz-empty"><FileSearch/><strong>Aktivitas tidak ditemukan</strong><small>Ubah filter atau pencarian.</small></div>}</section>
  </>
}
