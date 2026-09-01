import { lazy, Suspense, useEffect, useMemo, useRef, useState } from 'react'
import {
  AlertTriangle, ArrowRight, Boxes, Check, ChevronDown, ClipboardCheck,
  FileClock, Filter, History, Layers3, MapPin, Package, PackageCheck,
  RotateCcw, Ruler, Search, ShieldCheck, SlidersHorizontal,
  Sparkles, Tag, Truck, Warehouse, X,
} from 'lucide-react'
import { productCatalog } from './productCatalog'
import { StockHealthExplainability, getStockHealthLabel, type StockLineageLink } from './stock/StockHealthExplainability'
import { calculateStockHealth, createUnconfiguredPrototypeStock, type StockHealthResult } from './stock/stockHealth'
import './warehouse.css'

const StockAdjustmentPage = lazy(() => import('./InventoryControlPages').then((module) => ({ default: module.StockAdjustmentPage })))
const BrandConversionPage = lazy(() => import('./InventoryControlPages').then((module) => ({ default: module.BrandConversionPage })))

export type WarehouseView = 'warehouse-dashboard' | 'materials-rolls' | 'accessories' | 'fg-summary' | 'stock-adjustment' | 'brand-conversion'

type Tone = 'good' | 'warn' | 'danger' | 'neutral'
type MaterialSummary = {
  id: string
  material: string
  supplier: string
  totalReceivedYards: number
  usedYards: number
  supplierReturnedYards: number
  stockOnHandYards: number
  totalRolls: number
  availableRolls: number
  avgCost: number
  location: string
  lastMovement: string
}
type FabricRoll = {
  id: string
  material: string
  supplier: string
  receivedAt: string
  original: number
  remaining: number
  supplierReturned: number
  location: string
  status: 'Available' | 'In Use' | 'Empty'
  costState: 'ACTUAL' | 'ESTIMATED'
  activeCost: number
  source: string
}
type Accessory = {
  id: string
  name: string
  category: string
  supplier: string
  unit: string
  physical: number
  supplierReturned: number
  avgCost: number
  location: string
  lastMovement: string
}
type SupplierReturnTarget = {
  kind: 'fabric' | 'accessory'
  id: string
  label: string
  supplier: string
  unit: string
  maxQty: number
  location: string
}
type SupplierReturnRecord = {
  id: string
  kind: 'fabric' | 'accessory'
  item: string
  supplier: string
  qty: number
  unit: string
  happenedAt: string
  status: 'Posted' | 'Menunggu review'
}
const materials: MaterialSummary[] = [
  { id:'MAT-LCY', material:'Lucy', supplier:'Sinaran', totalReceivedYards:3612.5, usedYards:382.5, supplierReturnedYards:18.5, stockOnHandYards:3211.5, totalRolls:31, availableRolls:22, avgCost:49200, location:'Rak Kain A', lastMovement:'Potongan POT-260828-044 · 10:18' },
  { id:'MAT-1069', material:'1069 Ori', supplier:'Sinaran', totalReceivedYards:3374.5, usedYards:345, supplierReturnedYards:0, stockOnHandYards:3029.5, totalRolls:27, availableRolls:11, avgCost:50750, location:'Rak Kain B', lastMovement:'Material issue POT-260828-041 · 09:42' },
  { id:'MAT-ZDK', material:'Zodiak KW', supplier:'Sumber Cahaya', totalReceivedYards:2112, usedYards:228, supplierReturnedYards:0, stockOnHandYards:1884, totalRolls:18, availableRolls:14, avgCost:47600, location:'Rak Kain C', lastMovement:'Penerimaan SJ-260827-018 · kemarin' },
  { id:'MAT-CRB', material:'Corduroy 8W', supplier:'Mitra Tekstil', totalReceivedYards:794.5, usedYards:126, supplierReturnedYards:18, stockOnHandYards:650.5, totalRolls:7, availableRolls:4, avgCost:68400, location:'Rak Kain D', lastMovement:'Retur supplier RTS-260827-004 · kemarin' },
]

const fabricRolls: FabricRoll[] = [
  { id:'LCY-031', material:'Lucy', supplier:'Sinaran', receivedAt:'27 Agu 2026', original:131.5, remaining:113, supplierReturned:18.5, location:'A-02-03', status:'Available', costState:'ACTUAL', activeCost:49200, source:'SJ-260827-018' },
  { id:'LCY-030', material:'Lucy', supplier:'Sinaran', receivedAt:'27 Agu 2026', original:124, remaining:96.5, supplierReturned:0, location:'A-02-02', status:'Available', costState:'ACTUAL', activeCost:49200, source:'SJ-260827-018' },
  { id:'LCY-029', material:'Lucy', supplier:'Sinaran', receivedAt:'27 Agu 2026', original:91, remaining:18.5, supplierReturned:0, location:'Area Retur', status:'Available', costState:'ACTUAL', activeCost:49200, source:'RT-MD-260828-004' },
  { id:'LCY-028', material:'Lucy', supplier:'Sinaran', receivedAt:'25 Agu 2026', original:140, remaining:140, supplierReturned:0, location:'Staging Potong', status:'Available', costState:'ESTIMATED', activeCost:48500, source:'SJ-260825-012' },
  { id:'1069-027', material:'1069 Ori', supplier:'Sinaran', receivedAt:'24 Agu 2026', original:118, remaining:118, supplierReturned:0, location:'B-01-01', status:'Available', costState:'ACTUAL', activeCost:50750, source:'SJ-260824-009' },
  { id:'1069-026', material:'1069 Ori', supplier:'Sinaran', receivedAt:'24 Agu 2026', original:107.5, remaining:33, supplierReturned:0, location:'B-01-02', status:'Available', costState:'ACTUAL', activeCost:50750, source:'SJ-260824-009' },
  { id:'ZDK-018', material:'Zodiak KW', supplier:'Sumber Cahaya', receivedAt:'27 Agu 2026', original:103, remaining:103, supplierReturned:0, location:'C-02-01', status:'Available', costState:'ESTIMATED', activeCost:47600, source:'SJ-260827-021' },
  { id:'CRB-007', material:'Corduroy 8W', supplier:'Mitra Tekstil', receivedAt:'22 Agu 2026', original:108, remaining:28.5, supplierReturned:18, location:'D-01-02', status:'Available', costState:'ACTUAL', activeCost:68400, source:'SJ-260822-006' },
]

const accessories: Accessory[] = [
  { id:'ACC-KNC-17', name:'Kancing Jeans 17 mm', category:'Kancing', supplier:'Inti Metal', unit:'pcs', physical:12480, supplierReturned:0, avgCost:1850, location:'Aksesori A-01', lastMovement:'Keluar ke Mandor Asep · 10:22' },
  { id:'ACC-RVT-CU', name:'Rivet Copper', category:'Rivet', supplier:'Inti Metal', unit:'pcs', physical:7160, supplierReturned:480, avgCost:940, location:'Aksesori A-02', lastMovement:'Retur supplier RTS-260827-012 · kemarin' },
  { id:'ACC-ZIP-14', name:'Resleting YKK 14 cm', category:'Resleting', supplier:'Sinar Zip', unit:'pcs', physical:4380, supplierReturned:0, avgCost:7100, location:'Aksesori B-01', lastMovement:'Terima PO-BELI-260827-018 · kemarin' },
  { id:'ACC-HTG-WD', name:'Hangtag Widie', category:'Label & tag', supplier:'Cetak Jaya', unit:'pcs', physical:2260, supplierReturned:240, avgCost:620, location:'Aksesori C-02', lastMovement:'Retur supplier RTS-260826-009 · 16:18' },
  { id:'ACC-KRT-32', name:'Karet Pinggang 32 mm', category:'Karet', supplier:'Maju Elastik', unit:'meter', physical:1860, supplierReturned:0, avgCost:3950, location:'Aksesori B-03', lastMovement:'Retur Mandor Asep · kemarin' },
  { id:'ACC-LBL-VV', name:'Label Woven Vivo', category:'Label & tag', supplier:'Cetak Jaya', unit:'pcs', physical:3820, supplierReturned:0, avgCost:780, location:'Aksesori C-01', lastMovement:'Keluar ke Mandor Intan · kemarin' },
]

const fgFixtureTotals = productCatalog.reduce((totals, item) => {
  const quantity = item.stocks.reduce((sum, stock) => sum + stock, 0)
  totals.all += quantity
  if (item.grade === 'Good') totals.good += quantity
  else if (item.grade === 'BS') totals.bs += quantity
  return totals
}, { all:0, good:0, bs:0 })

const supplierReturnRecords: SupplierReturnRecord[] = [
  { id:'RTS-260827-006', kind:'fabric', item:'Lucy · LCY-031', supplier:'Sinaran', qty:18.5, unit:'yd', happenedAt:'27 Agu 2026 · 16:20', status:'Posted' },
  { id:'RTS-260827-004', kind:'fabric', item:'Corduroy 8W · CRB-007', supplier:'Mitra Tekstil', qty:18, unit:'yd', happenedAt:'27 Agu 2026 · 13:12', status:'Posted' },
  { id:'RTS-260827-012', kind:'accessory', item:'Rivet Copper', supplier:'Inti Metal', qty:480, unit:'pcs', happenedAt:'27 Agu 2026 · 11:42', status:'Posted' },
  { id:'RTS-260826-009', kind:'accessory', item:'Hangtag Widie', supplier:'Cetak Jaya', qty:240, unit:'pcs', happenedAt:'26 Agu 2026 · 16:18', status:'Posted' },
]

const prototypeStockHealth = (
  itemKind: 'FABRIC' | 'ACCESSORY' | 'FG',
  physicalStock: number,
  uom: string,
  source: string,
): StockHealthResult => calculateStockHealth({
  ...createUnconfiguredPrototypeStock({
    itemKind,
    physicalStock,
    uom,
    sourceSystem: `SIMULASI — fixture frontend ${source}; belum tersambung ke kalkulasi backend`,
  }),
})

const stockLineage = (kind: 'FABRIC' | 'ACCESSORY' | 'FG', id: string): StockLineageLink[] => {
  if (kind === 'FABRIC') return [
    { label:'Kartu stok kain', source:`Mutasi posted ${id}`, href:null },
    { label:'Alokasi produksi', source:'Rencana potongan yang sudah dikonfirmasi', href:null },
    { label:'PO / penerimaan', source:'Hanya incoming terkonfirmasi', href:null },
  ]
  if (kind === 'ACCESSORY') return [
    { label:'Kartu stok aksesori', source:`Mutasi posted ${id}`, href:null },
    { label:'Issue / sale Mandor', source:'Pengurang fisik; reimbursement BOM tidak dihitung ulang', href:null },
    { label:'PO / penerimaan', source:'Hanya incoming terkonfirmasi', href:null },
    { label:'BOM produksi aktif', source:'Kebutuhan, UOM, dan konversi eksplisit', href:null },
  ]
  return [
    { label:'Kartu stok FG', source:`Mutasi posted ${id}`, href:null },
    { label:'Reserved invoice', source:'Hanya reservation aktif', href:null },
    { label:'Incoming FG accepted', source:'Hanya QC/serah FG yang sah; pre-QC WIP tidak dihitung', href:null },
    { label:'Riwayat penjualan', source:'Demand dihitung hanya pada hari barang tersedia', href:null },
  ]
}

const formatNumber = (value: number, digits = 1) => new Intl.NumberFormat('id-ID', { maximumFractionDigits: digits }).format(value)
const money = (value: number) => new Intl.NumberFormat('id-ID', { style:'currency', currency:'IDR', maximumFractionDigits:0 }).format(value)
const statusTone = (status: string): Tone => status === 'Available' || status === 'Selesai' || status === 'ACTUAL' ? 'good' : status === 'In Use' || status === 'Menunggu review' || status === 'ESTIMATED' ? 'warn' : status === 'Perlu cek' || status === 'Review' || status === 'Selisih ditemukan' ? 'danger' : 'neutral'

function StatusBadge({ children, tone }: { children: string; tone?: Tone }) {
  return <span className={`wh-status ${tone ?? statusTone(children)}`}>{children}</span>
}

function SearchBox({ value, onChange, placeholder }: { value: string; onChange: (value: string) => void; placeholder: string }) {
  return <label className="wh-search"><Search /><input value={value} onChange={(event)=>onChange(event.target.value)} placeholder={placeholder}/></label>
}

function SelectFilter({ label, value, options, onChange }: { label: string; value: string; options: string[]; onChange: (value: string) => void }) {
  const [open,setOpen] = useState(false)
  const rootRef = useRef<HTMLDivElement>(null)
  const choices = ['Semua', ...options.filter((option)=>option!=='Semua')]
  const displayValue = value==='Semua' ? `Semua ${label.toLowerCase()}` : value
  useEffect(()=>{
    if(!open)return
    const closeOnOutside=(event:MouseEvent)=>{if(!rootRef.current?.contains(event.target as Node))setOpen(false)}
    const closeOnEscape=(event:KeyboardEvent)=>{if(event.key==='Escape')setOpen(false)}
    document.addEventListener('mousedown',closeOnOutside)
    document.addEventListener('keydown',closeOnEscape)
    return()=>{document.removeEventListener('mousedown',closeOnOutside);document.removeEventListener('keydown',closeOnEscape)}
  },[open])
  return <div className={`wh-filter ${open?'open':''}`} ref={rootRef}><span>{label}</span><button type="button" aria-haspopup="listbox" aria-expanded={open} onClick={()=>setOpen((current)=>!current)}><strong>{displayValue}</strong><ChevronDown/></button>{open&&<div className="wh-filter-menu" role="listbox" aria-label={`Filter ${label}`}>{choices.map((option)=>{const active=option===value;return <button type="button" role="option" aria-selected={active} className={active?'active':''} key={option} onClick={()=>{onChange(option);setOpen(false)}}><span>{option==='Semua'?`Semua ${label.toLowerCase()}`:option}</span>{active&&<Check/>}</button>})}</div>}</div>
}

function MetricCard({ label, value, note, tone='neutral', icon: Glyph=Boxes }: { label: string; value: string; note: string; tone?: Tone; icon?: typeof Boxes }) {
  return <div className={`panel wh-metric ${tone}`}><span>{label}</span><strong>{value}</strong><small>{note}</small><i><Glyph /></i></div>
}

function EmptyResult({ title, note }: { title: string; note: string }) {
  return <div className="wh-empty"><Filter/><strong>{title}</strong><small>{note}</small></div>
}

function SupplierReturnModal({ kind, target, onClose }: { kind: SupplierReturnTarget['kind']; target: SupplierReturnTarget | null; onClose: () => void }) {
  const [mode,setMode] = useState<'full'|'partial'>(target?.kind === 'fabric' ? 'full' : 'partial')
  const [quantityText,setQuantityText] = useState('')
  const [reference,setReference] = useState('')
  const [note,setNote] = useState('')
  const [notice,setNotice] = useState('')
  const records = supplierReturnRecords.filter((record)=>record.kind===kind)
  const historyTotal = records.reduce((sum,record)=>sum+record.qty,0)
  const typedQty = Number(quantityText.replace(',','.')) || 0
  const qty = target ? mode==='full' ? target.maxQty : typedQty : 0
  const invalidQty = !!target && (qty<=0 || qty>target.maxQty)
  const afterQty = target ? target.maxQty-qty : 0
  return <div className="wh-return-backdrop" role="presentation" onMouseDown={onClose}>
    <section className="wh-return-modal" role="dialog" aria-modal="true" aria-labelledby="supplier-return-title" onMouseDown={(event)=>event.stopPropagation()}>
      <header><div><span>SUPPLIER RETURN</span><h2 id="supplier-return-title">{target ? `Retur ${target.label}` : kind==='fabric' ? 'Riwayat Retur Kain' : 'Riwayat Retur Aksesori'}</h2><p>{target ? `${target.supplier} · ${target.location}` : 'Semua retur keluar ke supplier—bukan sisa produksi yang kembali dari mandor.'}</p></div><button aria-label="Tutup popup retur" onClick={onClose}><X/></button></header>
      <div className="wh-return-summary"><Truck/><div><span>TOTAL RETURNED TO SUPPLIER</span><strong>{formatNumber(historyTotal)} {kind==='fabric'?'yd':'pcs'}</strong><small>{records.length} dokumen posted · lifetime</small></div></div>
      {target&&<div className="wh-return-form">
        <div className="wh-return-identity"><span><small>ITEM / ROLL</small><strong>{target.label}</strong><em>{target.id} · {target.supplier}</em></span><span><small>STOCK ON HAND · FIXTURE</small><strong>{formatNumber(target.maxQty)} {target.unit}</strong><em>Saldo maksimum simulasi · bukan saldo backend</em></span></div>
        {target.kind==='fabric'&&<div className="wh-return-choice"><button className={mode==='full'?'active':''} onClick={()=>{setMode('full');setNotice('')}}><strong>Full sisa roll</strong><small>{formatNumber(target.maxQty)} yd bisa diretur</small><Check/></button><button className={mode==='partial'?'active':''} onClick={()=>{setMode('partial');setNotice('')}}><strong>Retur sebagian</strong><small>Ketik yard yang dikirim</small><Check/></button></div>}
        <div className="wh-return-fields"><label><span>QTY RETUR KE SUPPLIER</span><div><input autoFocus={mode==='partial'} inputMode="decimal" value={mode==='full'?String(target.maxQty).replace('.',','):quantityText} readOnly={mode==='full'} placeholder="0" onFocus={(event)=>event.currentTarget.select()} onChange={(event)=>{setQuantityText(event.target.value.replace(/[^0-9.,]/g,''));setNotice('')}}/><b>{target.unit}</b></div><small>Maksimum {formatNumber(target.maxQty)} {target.unit} sesuai Stock On Hand.</small></label><label><span>TANGGAL RETUR</span><input type="date" defaultValue="2026-08-28"/></label><label><span>REFERENSI / SURAT RETUR</span><input value={reference} onChange={(event)=>setReference(event.target.value)} placeholder="Contoh: RTS-260828-013"/></label></div>
        <label className="wh-return-note"><span>ALASAN & KONDISI BARANG</span><textarea value={note} onChange={(event)=>setNote(event.target.value)} placeholder="Kenapa dikembalikan, kondisi fisik, dan siapa yang menyetujui?"/></label>
        <div className="wh-return-equation"><span><small>STOCK ON HAND</small><strong>{formatNumber(target.maxQty)} {target.unit}</strong></span><i>−</i><span className="out"><small>RETURN TO SUPPLIER</small><strong>{formatNumber(qty)} {target.unit}</strong></span><i>=</i><span><small>STOCK AFTER</small><strong>{formatNumber(Math.max(0,afterQty))} {target.unit}</strong></span></div>
        <div className="wh-return-guard"><ShieldCheck/><div><strong>Retur supplier mengurangi Stock On Hand.</strong><small>Sisa dari mandor yang kembali ke gudang adalah transaksi masuk berbeda dan tidak muncul di form ini.</small></div></div>
        <button className="primary-btn wh-return-review" disabled={invalidQty||!reference.trim()||!note.trim()} onClick={()=>setNotice('Draft retur supplier siap direview. Prototype ini belum mengirim data ke backend.')}>Review retur supplier <ArrowRight/></button>
        {notice&&<em className="wh-return-notice"><Check/> {notice}</em>}
      </div>}
      <section className="wh-return-history"><header><div><span>RETURN HISTORY</span><strong>{kind==='fabric'?'Kain & roll':'Aksesori'} yang sudah dikirim ke supplier</strong></div><small>Terbaru dulu</small></header><div className="wh-return-history-head"><span>Dokumen / tanggal</span><span>Barang</span><span>Supplier</span><span>Qty</span><span>Status</span></div>{records.map((record)=><article key={record.id}><span><strong>{record.id}</strong><small>{record.happenedAt}</small></span><strong>{record.item}</strong><span>{record.supplier}</span><b>− {formatNumber(record.qty)} {record.unit}</b><StatusBadge tone={record.status==='Posted'?'good':'warn'}>{record.status}</StatusBadge></article>)}</section>
    </section>
  </div>
}

export default function WarehousePages({ view, onNavigate }: { view: WarehouseView; onNavigate: (view: WarehouseView) => void }) {
  if (view === 'warehouse-dashboard') return <WarehouseDashboard onNavigate={onNavigate}/>
  if (view === 'materials-rolls') return <MaterialsRollsPage/>
  if (view === 'accessories') return <AccessoriesPage/>
  if (view === 'fg-summary') return <FinishedGoodsSummaryPage/>
  if (view === 'stock-adjustment') return <Suspense fallback={<InventoryControlFallback/>}><StockAdjustmentPage/></Suspense>
  return <Suspense fallback={<InventoryControlFallback/>}><BrandConversionPage/></Suspense>
}

function InventoryControlFallback() {
  return <div className="panel wh-inventory-loading"><span/><strong>Menyiapkan inventory control…</strong><small>Memuat form dan guardrail stok.</small></div>
}

function WarehouseDashboard({ onNavigate }: { onNavigate: (view: WarehouseView) => void }) {
  const movements = [
    { time:'10:22', title:'Aksesori keluar', meta:'Mandor Asep · POT-260826-041', amount:'3.600 pcs', tone:'out' },
    { time:'10:18', title:'Kain ke meja potong', meta:'Lucy · 4 roll · POT-260828-044', amount:'482,5 yd', tone:'out' },
    { time:'09:31', title:'FG masuk', meta:'Widie 73001 · QC-260828-006', amount:'120 pcs', tone:'in' },
    { time:'08:12', title:'Retur mandor', meta:'Lucy · LCY-029', amount:'18,5 yd', tone:'in' },
  ]
  return <>
    <section className="hero-copy compact wh-hero"><div><div className="eyebrow">GUDANG · HARI INI</div><h1>Barang kebaca sebelum dicari.</h1><p>Satu layar untuk melihat bahan, roll, aksesori, barang jadi, dan kasus yang belum beres—dengan jejak Total Received, Used, Returned to Supplier, dan Stock On Hand yang jelas.</p></div><div className="wh-updated"><span><ShieldCheck/> LEDGER READ-ONLY</span><strong>Terakhir sinkron 10:24</strong><small>Prototype frontend · belum posting ke backend</small></div></section>
    <section className="wh-metrics"><MetricCard label="Fabric Stock On Hand" value="8.775,5 yd" note="83 roll aktif · data simulasi" icon={Ruler}/><MetricCard label="Dasar Status Stok" value="Belum diatur" note="Tidak ada minimum palsu" tone="neutral" icon={Package}/><MetricCard label="FG Grade Good · Fixture" value={`${formatNumber(fgFixtureTotals.good,0)} pcs`} note="Belum available stock backend" icon={PackageCheck}/><MetricCard label="Need Review" value="3 kasus" note="Retur, opname, penyesuaian" tone="danger" icon={ClipboardCheck}/></section>
    <section className="wh-dashboard-grid">
      <div className="panel wh-zone-panel"><header><div><span>AREA GUDANG</span><h2>Buka dari pekerjaan fisiknya</h2><p>Angka saat ini masih fixture frontend. Available stock baru boleh tampil setelah saldo posted dan reservation backend benar-benar tersambung.</p></div><Warehouse/></header><div className="wh-zone-grid">
        <button onClick={()=>onNavigate('materials-rolls')}><i className="blue"><Ruler/></i><span><small>KAIN</small><strong>Bahan & Roll</strong><em>83 roll · lifetime movement</em></span><b>8.775,5 yd · fixture</b><ArrowRight/></button>
        <button onClick={()=>onNavigate('accessories')}><i className="violet"><Boxes/></i><span><small>KOMPONEN</small><strong>Aksesori</strong><em>6 item aktif · per unit</em></span><b>31.960 unit · fixture</b><ArrowRight/></button>
        <button onClick={()=>onNavigate('fg-summary')}><i className="green"><PackageCheck/></i><span><small>BARANG JADI</small><strong>Ringkasan FG</strong><em>Per merek, SKU, size, grade</em></span><b>{formatNumber(fgFixtureTotals.good,0)} pcs Good · fixture</b><ArrowRight/></button>
        <button onClick={()=>onNavigate('stock-adjustment')}><i className="amber"><SlidersHorizontal/></i><span><small>PHYSICAL CONTROL</small><strong>Stock Adjustment</strong><em>Hilang, rusak, bencana, surplus</em></span><b>3 open cases</b><ArrowRight/></button>
        <button onClick={()=>onNavigate('brand-conversion')}><i className="violet"><Sparkles/></i><span><small>FG CONVERSION</small><strong>Ganti Merek</strong><em>Source out = target in</em></span><b>36 pcs hari ini</b><ArrowRight/></button>
      </div></div>
      <div className="panel wh-attention"><header><div><span>BUTUH PERHATIAN</span><h2>Jangan kelewat hari ini</h2></div><AlertTriangle/></header><div className="wh-attention-list"><article className="warn"><i/><div><strong>Dasar status stok belum diatur</strong><small>Belum ada histori/backend policy valid—tidak ada rekomendasi pesan palsu</small></div><b>Lengkapi data</b></article><article className="warn"><i/><div><strong>12 pcs selisih opname</strong><small>Kancing Jeans 17 mm · belum posting</small></div><b>Review</b></article><article><i/><div><strong>4 roll masih ESTIMATED</strong><small>Kasbon supplier belum cocok</small></div><b>Cek</b></article></div></div>
    </section>
    <section className="panel wh-movement-panel"><header><div><span>MUTASI TERBARU</span><h2>Gerak barang lintas gudang</h2></div><button className="soft-btn"><History/> Lihat ledger lengkap</button></header><div className="wh-movement-list">{movements.map((item)=><article key={`${item.time}-${item.title}`}><time>{item.time}</time><i className={item.tone}/><div><strong>{item.title}</strong><small>{item.meta}</small></div><b className={item.tone}>{item.tone==='in'?'+':'−'} {item.amount}</b></article>)}</div></section>
  </>
}

function MaterialsRollsPage() {
  const [query,setQuery] = useState('')
  const [supplier,setSupplier] = useState('Semua')
  const [status,setStatus] = useState('Semua')
  const [selectedId,setSelectedId] = useState(materials[0].id)
  const [returnModalOpen,setReturnModalOpen] = useState(false)
  const [returnTarget,setReturnTarget] = useState<SupplierReturnTarget|null>(null)
  const selected = materials.find((item)=>item.id===selectedId) ?? materials[0]
  const selectedHealth = prototypeStockHealth('FABRIC', selected.stockOnHandYards, 'yd', selected.id)
  const visibleMaterials = useMemo(()=>materials.filter((item)=>{
    const health = prototypeStockHealth('FABRIC', item.stockOnHandYards, 'yd', item.id)
    return `${item.material} ${item.supplier} ${item.location}`.toLowerCase().includes(query.toLowerCase()) && (supplier==='Semua'||item.supplier===supplier) && (status==='Semua'||getStockHealthLabel(health)===status)
  }),[query,supplier,status])
  const visibleRolls = fabricRolls.filter((roll)=>roll.material===selected.material)
  const estimatedCount = visibleRolls.filter((roll)=>roll.costState==='ESTIMATED').length
  return <>
    <section className="hero-copy compact wh-hero"><div><div className="eyebrow">GUDANG · RAW MATERIAL</div><h1>Bahan & Roll</h1><p>Pilih bahan dulu, lalu telusuri setiap gulung melalui alur lifetime: Total Received − Used − Returned to Supplier = Stock On Hand.</p></div><div className="wh-rule"><Ruler/><div><span>DATA SIMULASI FRONTEND</span><strong>Belum menjadi saldo backend</strong><small>Saldo, roll, cost, dan status di halaman ini masih fixture untuk verifikasi UX.</small></div></div></section>
    <div className="wh-context-control"><div className="wh-context-copy"><i><History/></i><span><strong>Riwayat retur kain ke supplier</strong><small>Lihat total lifetime dan seluruh dokumen retur—terpisah dari adjustment dan retur mandor.</small></span></div><button className="wh-return-history-button" onClick={()=>{setReturnTarget(null);setReturnModalOpen(true)}}><span><small>SEMUA DOKUMEN</small><strong>Cek retur</strong></span><ArrowRight/></button></div>
    <section className="wh-metrics"><MetricCard label="Total Received" value="9.893,5 yd" note="Fixture · penerimaan lifetime" icon={Layers3}/><MetricCard label="Used" value="1.081,5 yd" note="Fixture · keluar produksi" icon={Tag}/><MetricCard label="Returned to Supplier" value="36,5 yd" note="Fixture · retur supplier" icon={RotateCcw}/><MetricCard label="Stock On Hand" value="8.775,5 yd" note="Fixture · belum backend" icon={Check}/></section>
    <div className="panel wh-workspace material-rolls-workspace">
      <div className="wh-toolbar"><SearchBox value={query} onChange={setQuery} placeholder="Cari bahan, pabrik, atau lokasi..."/><SelectFilter label="Pabrik" value={supplier} options={[...new Set(materials.map((item)=>item.supplier))]} onChange={setSupplier}/><SelectFilter label="Status" value={status} options={[...new Set(materials.map((item)=>getStockHealthLabel(prototypeStockHealth('FABRIC', item.stockOnHandYards, 'yd', item.id))))]} onChange={setStatus}/><button className="wh-reset" onClick={()=>{setQuery('');setSupplier('Semua');setStatus('Semua')}}><RotateCcw/> Reset</button></div>
      <div className="wh-master-detail rolls">
        <aside className="wh-browser"><header><div><span>BROWSE BAHAN</span><strong>{visibleMaterials.length} bahan tampil</strong></div><small>Klik status untuk dasar hitung</small></header><div className="wh-browser-list">{visibleMaterials.map((item)=>{const health=prototypeStockHealth('FABRIC',item.stockOnHandYards,'yd',item.id);return <article key={item.id} className={`wh-stock-browser-row ${selected.id===item.id?'active':''}`}><button type="button" className="wh-stock-select" onClick={()=>setSelectedId(item.id)}><span className="wh-index">{String(materials.indexOf(item)+1).padStart(2,'0')}</span><div><strong>{item.material}</strong><small>{item.supplier} · {item.location}</small><em>{item.availableRolls} dari {item.totalRolls} roll aktif</em></div><b>{formatNumber(item.stockOnHandYards)} yd</b></button><StockHealthExplainability compact itemName={item.material} result={health} lineage={stockLineage('FABRIC',item.id)}/></article>})}{visibleMaterials.length===0&&<EmptyResult title="Bahan tidak ditemukan" note="Ubah pencarian atau reset filter."/>}</div></aside>
        <main className="wh-detail"><header className="wh-detail-head"><div><span>BAHAN TERPILIH</span><h2>{selected.material}</h2><p>{selected.supplier} · {selected.location} · {selected.id}</p></div><div className="wh-detail-total"><span>STOCK ON HAND · FIXTURE</span><strong>{formatNumber(selected.stockOnHandYards)} yd</strong><small>{money(selected.avgCost)} / yd moving average · simulasi</small></div></header>
          <div className="wh-balance-equation lifetime"><span><small>TOTAL RECEIVED</small><strong>{formatNumber(selected.totalReceivedYards)} yd</strong></span><i>−</i><span className="used"><small>USED</small><strong>{formatNumber(selected.usedYards)} yd</strong></span><i>−</i><span className="returned"><small>RETURNED TO SUPPLIER</small><strong>{formatNumber(selected.supplierReturnedYards)} yd</strong></span><i>=</i><span className="available"><small>STOCK ON HAND</small><strong>{formatNumber(selected.stockOnHandYards)} yd</strong></span></div>
          <div className="wh-stock-health-shell"><div><span>STATUS STOK · DATA SIMULASI</span><strong>Tidak ada minimum tetap yang diasumsikan untuk kain.</strong><small>Kebutuhan harus berasal dari rencana potongan/produksi, alokasi, sisa roll, dan incoming terkonfirmasi.</small></div><StockHealthExplainability itemName={selected.material} result={selectedHealth} lineage={stockLineage('FABRIC',selected.id)}/></div>
          {estimatedCount>0&&<div className="wh-inline-note warn"><FileClock/><div><strong>{estimatedCount} roll masih memakai harga benchmark</strong><small>Stok dan HPP boleh berjalan, tetapi histori benchmark tetap terlihat sampai kasbon actual cocok.</small></div></div>}
          <div className="wh-roll-head"><div><span>ROLL AKTIF</span><strong>{visibleRolls.length} gulung untuk {selected.material}</strong></div><small>Urut penerimaan terbaru</small></div>
          <div className="wh-roll-list">{visibleRolls.map((roll)=>{const used=Math.max(0,roll.original-roll.supplierReturned-roll.remaining);const returnable=Math.max(0,roll.remaining);return <article key={roll.id}><header><div className="wh-roll-id"><i><Ruler/></i><div><strong>{roll.id}</strong><small>{roll.source} · {roll.receivedAt}</small></div></div><div><StatusBadge>{roll.status}</StatusBadge><StatusBadge tone={statusTone(roll.costState)}>{roll.costState}</StatusBadge></div></header><div className="wh-roll-numbers lifetime"><span><small>TOTAL RECEIVED</small><strong>{formatNumber(roll.original)} yd</strong></span><span className="used"><small>USED</small><strong>{formatNumber(used)} yd</strong></span><span className="returned"><small>RETURNED TO SUPPLIER</small><strong>{formatNumber(roll.supplierReturned)} yd</strong></span><span className="available"><small>STOCK ON HAND</small><strong>{formatNumber(roll.remaining)} yd</strong></span></div><div className="wh-roll-progress"><span style={{width:`${Math.min(100,(roll.remaining/Math.max(roll.original,1))*100)}%`}}/></div><footer><span><MapPin/> {roll.location}</span><span>{money(roll.activeCost)} / yd aktif</span><div className="wh-roll-actions"><button className="wh-roll-history">Riwayat roll <ArrowRight/></button><button className="return wh-roll-return" disabled={returnable<=0} title={returnable<=0?'Stock On Hand roll sudah nol':'Retur penuh atau sebagian ke supplier'} onClick={()=>{setReturnTarget({kind:'fabric',id:roll.id,label:`${roll.material} · ${roll.id}`,supplier:roll.supplier,unit:'yd',maxQty:returnable,location:roll.location});setReturnModalOpen(true)}}><RotateCcw/><span><strong>{returnable<=0?'Saldo roll habis':'Retur supplier'}</strong><small>{returnable<=0?'Tidak ada saldo untuk diretur':`${formatNumber(returnable)} yd bisa diretur`}</small></span></button></div></footer></article>})}</div>
        </main>
      </div>
    </div>
    {returnModalOpen&&<SupplierReturnModal key={returnTarget?.id??'fabric-history'} kind="fabric" target={returnTarget} onClose={()=>setReturnModalOpen(false)}/>} 
  </>
}

function AccessoriesPage() {
  const [query,setQuery] = useState('')
  const [category,setCategory] = useState('Semua')
  const [status,setStatus] = useState('Semua')
  const [selectedId,setSelectedId] = useState(accessories[0].id)
  const [returnModalOpen,setReturnModalOpen] = useState(false)
  const [returnTarget,setReturnTarget] = useState<SupplierReturnTarget|null>(null)
  const visible = useMemo(()=>accessories.filter((item)=>{
    const health = prototypeStockHealth('ACCESSORY', item.physical, item.unit, item.id)
    return `${item.name} ${item.category} ${item.supplier} ${item.id}`.toLowerCase().includes(query.toLowerCase()) && (category==='Semua'||item.category===category) && (status==='Semua'||getStockHealthLabel(health)===status)
  }),[query,category,status])
  const selected = accessories.find((item)=>item.id===selectedId) ?? accessories[0]
  const available = selected.physical
  const selectedHealth = prototypeStockHealth('ACCESSORY', selected.physical, selected.unit, selected.id)
  const priorBalance = selected.physical + 1200
  const movementRows = [
    { ref:'OUT-260828-018', date:'Hari ini · 10:22', note:'Keluar ke Mandor Asep', delta:-1200, balance:selected.physical },
    selected.supplierReturned>0
      ? { ref:'RTS-260827-012', date:'Kemarin · 16:18', note:`Retur ke ${selected.supplier}`, delta:-selected.supplierReturned, balance:priorBalance }
      : { ref:'MOV-260827-012', date:'Kemarin · 16:18', note:'Pindah lokasi internal', delta:0, balance:priorBalance },
    { ref:'RCV-260827-018', date:'Kemarin · 15:08', note:`Terima dari ${selected.supplier}`, delta:4800, balance:priorBalance+selected.supplierReturned },
  ]
  return <>
    <section className="hero-copy compact wh-hero"><div><div className="eyebrow">GUDANG · KOMPONEN</div><h1>Aksesori</h1><p>Qty langsung per unit. Status stok dipisahkan dari dasar perhitungannya; angka yang belum berasal dari backend ditandai sebagai simulasi.</p></div><div className="wh-rule"><Boxes/><div><span>POLA INPUT</span><strong>Qty langsung, bukan gulungan</strong><small>PCS, meter, set, atau unit master item.</small></div></div></section>
    <div className="wh-context-control"><div className="wh-context-copy"><i><History/></i><span><strong>Riwayat retur aksesori ke supplier</strong><small>Lihat total lifetime dan seluruh dokumen retur—bukan adjustment atau retur sisa mandor.</small></span></div><button className="wh-return-history-button" onClick={()=>{setReturnTarget(null);setReturnModalOpen(true)}}><span><small>SEMUA DOKUMEN</small><strong>Cek retur</strong></span><ArrowRight/></button></div>
    <section className="wh-metrics"><MetricCard label="Stock On Hand" value="31.960 unit" note="Fixture frontend · belum backend" icon={Package}/><MetricCard label="Dasar Perhitungan" value="Belum diatur" note="Tidak ada rekomendasi palsu" tone="neutral" icon={AlertTriangle}/><MetricCard label="Moving Average" value="6 item" note="Valuasi fixture per item" icon={Tag}/><MetricCard label="Returned to Supplier" value="720 pcs" note="2 dokumen fixture" tone="neutral" icon={RotateCcw}/></section>
    <div className="panel wh-workspace">
      <div className="wh-toolbar"><SearchBox value={query} onChange={setQuery} placeholder="Cari aksesori, kode, supplier..."/><SelectFilter label="Kategori" value={category} options={[...new Set(accessories.map((item)=>item.category))]} onChange={setCategory}/><SelectFilter label="Status" value={status} options={[...new Set(accessories.map((item)=>getStockHealthLabel(prototypeStockHealth('ACCESSORY',item.physical,item.unit,item.id))))]} onChange={setStatus}/><button className="wh-reset" onClick={()=>{setQuery('');setCategory('Semua');setStatus('Semua')}}><RotateCcw/> Reset</button></div>
      <div className="wh-master-detail accessory">
        <aside className="wh-browser"><header><div><span>BROWSE AKSESORI</span><strong>{visible.length} item tampil</strong></div><small>Klik status untuk dasar hitung</small></header><div className="wh-browser-list wh-accessory-browser">{visible.map((item)=>{const itemAvailable=item.physical;const health=prototypeStockHealth('ACCESSORY',item.physical,item.unit,item.id);return <article key={item.id} className={selected.id===item.id?'active':''}><button type="button" className="wh-accessory-select" onClick={()=>setSelectedId(item.id)}><span className="wh-index"><Package/></span><div><strong>{item.name}</strong><small>{item.id} · {item.category}</small><em>{item.supplier} · {item.location}</em></div><b>{formatNumber(itemAvailable,0)} {item.unit}</b></button><StockHealthExplainability compact itemName={item.name} result={health} lineage={stockLineage('ACCESSORY',item.id)}/><button className="wh-accessory-return" disabled={itemAvailable<=0} onClick={()=>{setSelectedId(item.id);setReturnTarget({kind:'accessory',id:item.id,label:item.name,supplier:item.supplier,unit:item.unit,maxQty:itemAvailable,location:item.location});setReturnModalOpen(true)}}><RotateCcw/><span><strong>Retur supplier</strong><small>{formatNumber(itemAvailable,0)} {item.unit} maksimal</small></span><ArrowRight/></button></article>})}{visible.length===0&&<EmptyResult title="Aksesori tidak ditemukan" note="Coba kategori lain atau reset filter."/>}</div></aside>
        <main className="wh-detail"><header className="wh-detail-head"><div><span>ITEM TERPILIH</span><h2>{selected.name}</h2><p>{selected.id} · {selected.category} · {selected.supplier}</p></div><div className="wh-detail-total"><span>STOCK ON HAND · FIXTURE</span><strong>{formatNumber(available,0)} {selected.unit}</strong><small>{money(selected.avgCost)} / {selected.unit} moving average · simulasi</small></div></header>
          <div className="wh-accessory-facts"><div><MapPin/><span><small>LOCATION</small><strong>{selected.location}</strong></span></div><div><Boxes/><span><small>STOCK ON HAND</small><strong>{formatNumber(selected.physical,0)} {selected.unit}</strong></span></div><div><Tag/><span><small>VALUATION</small><strong>Moving average · simulasi</strong></span></div><div className="returned"><RotateCcw/><span><small>RETURNED TO SUPPLIER</small><strong>{formatNumber(selected.supplierReturned,0)} {selected.unit}</strong></span></div><div><ShieldCheck/><span><small>DASAR STATUS</small><strong>Batas belum diatur</strong></span></div></div>
          <div className="wh-stock-health-shell"><div><span>STATUS STOK · DATA SIMULASI</span><strong>Reserved, incoming, demand, dan lead time belum tersedia.</strong><small>Klik badge untuk melihat operand null dan jejak data yang nantinya wajib berasal dari backend.</small></div><StockHealthExplainability itemName={selected.name} result={selectedHealth} lineage={stockLineage('ACCESSORY',selected.id)}/></div>
          <section className="wh-mini-ledger"><header><div><span>MUTASI TERAKHIR · SIMULASI</span><strong>{selected.lastMovement}</strong></div><button>Semua riwayat <ArrowRight/></button></header><div className="wh-mini-ledger-head"><span>Waktu / ref</span><span>Keterangan</span><span>Mutasi</span><span>Saldo fisik</span></div>{movementRows.map((row)=><article key={row.ref}><span><strong>{row.ref}</strong><small>{row.date}</small></span><span>{row.note}</span><b className={row.delta<0?'negative':row.delta>0?'positive':''}>{row.delta>0?'+':''}{formatNumber(row.delta,0)} {selected.unit}</b><strong>{formatNumber(row.balance,0)} {selected.unit}</strong></article>)}</section>
        </main>
      </div>
    </div>
    {returnModalOpen&&<SupplierReturnModal key={returnTarget?.id??'accessory-history'} kind="accessory" target={returnTarget} onClose={()=>setReturnModalOpen(false)}/>} 
  </>
}

function FinishedGoodsSummaryPage() {
  const brands = [...new Set(productCatalog.map((item)=>item.brand))]
  const grades = [...new Set(productCatalog.map((item)=>item.grade))]
  const locations = [...new Set(productCatalog.map((item)=>item.location))]
  const [query,setQuery] = useState('')
  const [brand,setBrand] = useState('Semua')
  const [grade,setGrade] = useState('Semua')
  const [location,setLocation] = useState('Semua')
  const [selectedKey,setSelectedKey] = useState(`${productCatalog[0].brand}::${productCatalog[0].code}`)
  const visible = useMemo(()=>productCatalog.filter((item)=>`${item.brand} ${item.code} ${item.name} ${item.color} ${item.range}`.toLowerCase().includes(query.toLowerCase()) && (brand==='Semua'||item.brand===brand) && (grade==='Semua'||item.grade===grade) && (location==='Semua'||item.location===location)),[query,brand,grade,location])
  const selected = productCatalog.find((item)=>`${item.brand}::${item.code}`===selectedKey) ?? productCatalog[0]
  const total = selected.stocks.reduce((sum,qty)=>sum+qty,0)
  const selectedHealth = prototypeStockHealth('FG', total, 'pcs', `${selected.brand}-${selected.code}`)
  const brandTotals = brands.map((name)=>({name,total:productCatalog.filter((item)=>item.brand===name).reduce((sum,item)=>sum+item.stocks.reduce((acc,qty)=>acc+qty,0),0)}))
  return <>
    <section className="hero-copy compact wh-hero"><div><div className="eyebrow">GUDANG · BARANG JADI</div><h1>Ringkasan Barang Jadi</h1><p>Browse merek → SKU → size. Status aman/rendah tidak diasumsikan dari angka fixture; dasar dan formula selalu bisa dibuka.</p></div><div className="wh-rule"><PackageCheck/><div><span>SATU SUMBER SALDO</span><strong>Ledger FG, bukan hitungan manual</strong><small>Grade dan lokasi tetap menjadi dimensi terpisah.</small></div></div></section>
    <section className="wh-metrics"><MetricCard label="Seluruh FG" value={`${formatNumber(fgFixtureTotals.all,0)} pcs`} note="Fixture frontend · semua grade" icon={PackageCheck}/><MetricCard label="Grade Good" value={`${formatNumber(fgFixtureTotals.good,0)} pcs`} note="Fixture · belum available backend" tone="neutral" icon={Check}/><MetricCard label="Grade BS" value={`${formatNumber(fgFixtureTotals.bs,0)} pcs`} note="Fixture · tidak ikut siap jual" tone="neutral" icon={AlertTriangle}/><MetricCard label="Lokasi aktif" value="2 gudang" note="Fixture · Utama & Cadangan" icon={Warehouse}/></section>
    <div className="panel wh-workspace"><div className="wh-toolbar"><SearchBox value={query} onChange={setQuery} placeholder="Cari merek, SKU, model, warna..."/><SelectFilter label="Merek" value={brand} options={brands} onChange={setBrand}/><SelectFilter label="Grade" value={grade} options={grades} onChange={setGrade}/><SelectFilter label="Lokasi" value={location} options={locations} onChange={setLocation}/><button className="wh-reset" onClick={()=>{setQuery('');setBrand('Semua');setGrade('Semua');setLocation('Semua')}}><RotateCcw/> Reset</button></div>
      <div className="wh-brand-strip">{brandTotals.map((item)=><button key={item.name} className={brand===item.name?'active':''} onClick={()=>setBrand(brand===item.name?'Semua':item.name)}><span>{item.name}</span><strong>{item.total} pcs</strong><small>{productCatalog.filter((product)=>product.brand===item.name).length} SKU</small></button>)}</div>
      <div className="wh-master-detail fg"><aside className="wh-browser"><header><div><span>BROWSE SKU</span><strong>{visible.length} SKU tampil</strong></div><small>Pilih untuk breakdown</small></header><div className="wh-browser-list">{visible.map((item)=>{const itemTotal=item.stocks.reduce((sum,qty)=>sum+qty,0);const key=`${item.brand}::${item.code}`;return <button key={key} className={selectedKey===key?'active':''} onClick={()=>setSelectedKey(key)}><span className="wh-index">{item.brand.slice(0,1)}</span><div><strong>{item.brand} · {item.code}</strong><small>{item.name} · {item.color}</small><em>{item.range} · {item.location}</em></div><b>{itemTotal} pcs</b><StatusBadge tone={item.grade==='Good'?'good':'danger'}>{item.grade}</StatusBadge></button>})}{visible.length===0&&<EmptyResult title="SKU tidak ditemukan" note="Ubah merek, grade, lokasi, atau pencarian."/>}</div></aside>
        <main className="wh-detail"><header className="wh-detail-head"><div><span>SKU TERPILIH</span><h2>{selected.brand} · {selected.code}</h2><p>{selected.name} · {selected.color} · Range {selected.range}</p></div><div className="wh-detail-total"><span>SALDO SKU · FIXTURE</span><strong>{total} pcs</strong><small>{selected.location} · Grade {selected.grade} · simulasi</small></div></header>
          <div className="wh-stock-health-shell"><div><span>STATUS SKU · DATA SIMULASI</span><strong>Belum cukup data · batas belum diatur.</strong><small>Pre-QC WIP tidak dihitung sebagai incoming. Hanya serah FG/QC accepted yang terkonfirmasi boleh masuk projected stock.</small></div><StockHealthExplainability itemName={`${selected.brand} ${selected.code}`} result={selectedHealth} lineage={stockLineage('FG',`${selected.brand}-${selected.code}`)}/></div>
          <div className="wh-fg-size-grid">{selected.sizes.map((size,index)=>{const sizeHealth=prototypeStockHealth('FG',selected.stocks[index],'pcs',`${selected.brand}-${selected.code}-${size}`);return <article key={size}><span>SIZE</span><strong>{size}</strong><div><small>SALDO FIXTURE</small><b>{selected.stocks[index]} pcs</b></div><div><small>LUSIN / POTONG</small><b>{Math.floor(selected.stocks[index]/12)} lusin · {selected.stocks[index]%12} potong</b></div><StockHealthExplainability compact itemName={`${selected.brand} ${selected.code} · Size ${size}`} result={sizeHealth} lineage={stockLineage('FG',`${selected.brand}-${selected.code}-${size}`)}/></article>})}</div>
          <section className="wh-fg-location"><header><div><span>POSISI STOK</span><strong>Lokasi dan grade tidak dicampur</strong></div><button>Buka kartu stok <ArrowRight/></button></header><div><article><MapPin/><span><small>LOKASI</small><strong>{selected.location}</strong><em>Bin FG-{selected.brand==='Vivo'?'A':'B'}-{selected.code.slice(-2)}</em></span><b>{total} pcs</b></article><article><ShieldCheck/><span><small>GRADE</small><strong>{selected.grade}</strong><em>{selected.grade==='Good'?'Boleh dialokasikan ke penjualan':'Masuk jalur BS / rework'}</em></span><b>{selected.grade==='Good'?'READY':'HOLD'}</b></article></div></section>
        </main></div>
    </div>
  </>
}
