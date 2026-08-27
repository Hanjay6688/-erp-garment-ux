import { Fragment, useMemo, useRef, useState } from 'react'
import type { ClipboardEvent as ReactClipboardEvent, CSSProperties, KeyboardEvent as ReactKeyboardEvent, PointerEvent as ReactPointerEvent, ReactNode } from 'react'
import {
  ArrowLeft, ArrowRight, Boxes, CalendarDays, Check, ChevronDown, ChevronUp,
  CircleDollarSign, Database, Factory, FileText, GripVertical, History,
  LayoutDashboard, Layers3, Link2, ListFilter, Menu, Package, Plus, ReceiptText,
  RotateCcw, Ruler, Scissors, Search, ShieldCheck, SlidersHorizontal, Trash2,
  UserRound, WalletCards, Warehouse, X,
} from 'lucide-react'
import type { LucideIcon } from 'lucide-react'

type Page = 'dashboard' | 'sales' | 'stock-card' | 'movements-vivo' | 'movements-widie' | 'procurement' | 'cutting-roll' | 'mandor-wip' | 'placeholder'
type NavSection = 'Produksi' | 'Gudang' | 'Penjualan' | 'Keuangan' | 'Master Data'
type QtyTuple = [number, number, number]
type SizeTuple = [string, string, string]
type ReceiptMode = 'fabric' | 'accessory'

type SizeRow = { size: string; stock: number; qty: number; input: string }
type RollDraft = { id: number; yards: string }
type SlotAllocation = [number, number, number, number, number, number]
type CuttingSizeSlot = { key: string; size: string }
type WipAllocationMode = 'roll' | 'size'
type AllocationMatrix = Record<string, string[]>
type RollBatchSizeMatrix = Record<string, string[][]>
type FabricRoll = {
  id: string
  sequence: number
  supplier: string
  material: string
  yards: number
  receivedAt: string
  allocation: SlotAllocation
}

type Movement = {
  id: string
  sku: string
  brand: string
  customer: string | null
  date: string
  ref: string
  type: string
  note: string
  delta: QtyTuple
  balance: QtyTuple
}

type Product = {
  code: string
  range: string
  name: string
  color: string
  brand: string
  sizes: SizeTuple
  stocks: QtyTuple
  location: string
  grade: string
}

const productKey = (product: Pick<Product, 'brand' | 'code'>) => `${product.brand}::${product.code}`
const movementProductKey = (movement: Pick<Movement, 'brand' | 'sku'>) => `${movement.brand}::${movement.sku}`

const productCatalog: Product[] = [
  { code: '73001', range: '28–30', name: 'Vivo Classic', color: 'Indigo', brand: 'Vivo', sizes: ['28','29','30'], stocks: [96,84,108], location: 'Gudang FG Utama', grade: 'Good' },
  { code: '73002', range: '31–33', name: 'Vivo Regular', color: 'Washed Blue', brand: 'Vivo', sizes: ['31','32','33'], stocks: [72,60,48], location: 'Gudang FG Utama', grade: 'Good' },
  { code: '73003', range: '34–36', name: 'Vivo Relaxed', color: 'Charcoal', brand: 'Vivo', sizes: ['34','35','36'], stocks: [36,42,54], location: 'Gudang FG Utama', grade: 'Good' },
  { code: '73004', range: '28–30', name: 'Vivo Straight', color: 'Deep Black', brand: 'Vivo', sizes: ['28','29','30'], stocks: [60,72,66], location: 'Gudang FG Utama', grade: 'Good' },
  { code: '73001', range: '28–30', name: 'Widie Daily', color: 'Dark Navy', brand: 'Widie', sizes: ['28','29','30'], stocks: [84,78,90], location: 'Gudang FG Utama', grade: 'Good' },
  { code: '73002', range: '31–33', name: 'Widie Regular', color: 'Vintage Blue', brand: 'Widie', sizes: ['31','32','33'], stocks: [42,36,48], location: 'Gudang FG Cadangan', grade: 'BS' },
  { code: '73005', range: '31–33', name: 'Widie Tapered', color: 'Mid Blue', brand: 'Widie', sizes: ['31','32','33'], stocks: [48,54,42], location: 'Gudang FG Cadangan', grade: 'Good' },
  { code: '73006', range: '34–36', name: 'Widie Workwear', color: 'Stone', brand: 'Widie', sizes: ['34','35','36'], stocks: [24,30,36], location: 'Gudang FG Cadangan', grade: 'BS' },
]

const initialCuttingSizeSlots: CuttingSizeSlot[] = [
  { key: '31-1', size: '31' }, { key: '31-2', size: '31' },
  { key: '32-1', size: '32' }, { key: '32-2', size: '32' },
  { key: '33-1', size: '33' }, { key: '33-2', size: '33' },
]
const cuttingSizes: SizeTuple = ['31','32','33']

const drawingLabel = (drawingNo: number) => {
  let value = Math.max(1, drawingNo)
  let label = ''
  while (value > 0) {
    value -= 1
    label = String.fromCharCode(65 + (value % 26)) + label
    value = Math.floor(value / 26)
  }
  return label
}

const rollSizeQuantities = (allocation: SlotAllocation): QtyTuple => [
  allocation[0] + allocation[1], allocation[2] + allocation[3], allocation[4] + allocation[5],
]
const cellQuantity = (value: string | undefined) => Math.max(0, Math.round(Number(value) || 0))
const balancedBatchTargets = (total: number, count: number) => {
  const base = Math.floor(total / count)
  const remainder = total % count
  return Array.from({ length: count }, (_, index) => base + (index < remainder ? 1 : 0))
}

function createRollAllocationMatrix(rolls: FabricRoll[], count: number): AllocationMatrix {
  const sources = rolls.map((roll) => ({ id: roll.id, qty: rollSizeQuantities(roll.allocation).reduce((sum, qty) => sum + qty, 0) }))
  const loads = Array(count).fill(0) as number[]
  const matrix: AllocationMatrix = Object.fromEntries(sources.map((source) => [source.id, Array(count).fill('0')]))

  ;[...sources].sort((a, b) => b.qty - a.qty).forEach((source) => {
    const batchIndex = loads.reduce((lightest, load, index, values) => load < values[lightest] ? index : lightest, 0)
    matrix[source.id][batchIndex] = String(source.qty)
    loads[batchIndex] += source.qty
  })
  return matrix
}

function createSizeAllocationMatrix(sizeTotals: QtyTuple, count: number): AllocationMatrix {
  return Object.fromEntries(cuttingSizes.map((size, sizeIndex) => [size, Array.from({ length: count }, (_, batchIndex) => String(batchIndex === sizeIndex ? sizeTotals[sizeIndex] : 0))]))
}

function createRollBatchSizeMatrix(rolls: FabricRoll[], count: number): RollBatchSizeMatrix {
  const wholeRollPlan = createRollAllocationMatrix(rolls, count)
  return Object.fromEntries(rolls.map((roll) => {
    const assignedBatch = (wholeRollPlan[roll.id] ?? []).findIndex((value) => cellQuantity(value) > 0)
    const sourceSizes = rollSizeQuantities(roll.allocation)
    return [roll.id, Array.from({ length: count }, (_, batchIndex) => batchIndex === assignedBatch ? sourceSizes.map(String) : ['0', '0', '0'])]
  }))
}

const fabricRollCatalog: FabricRoll[] = [
  { id:'LCY-001',sequence:1,supplier:'Sinaran',material:'Lucy',yards:101.5,receivedAt:'25 Agu 2026',allocation:[13,13,12,11,10,10] },
  { id:'LCY-002',sequence:2,supplier:'Sinaran',material:'Lucy',yards:108.5,receivedAt:'25 Agu 2026',allocation:[13,13,12,12,12,12] },
  { id:'LCY-003',sequence:3,supplier:'Sinaran',material:'Lucy',yards:104,receivedAt:'25 Agu 2026',allocation:[11,11,12,12,12,12] },
  { id:'LCY-004',sequence:4,supplier:'Sinaran',material:'Lucy',yards:109.5,receivedAt:'25 Agu 2026',allocation:[13,13,12,12,12,12] },
  { id:'LCY-005',sequence:5,supplier:'Sinaran',material:'Lucy',yards:140,receivedAt:'25 Agu 2026',allocation:[15,15,16,16,16,16] },
  { id:'LCY-006',sequence:6,supplier:'Sinaran',material:'Lucy',yards:121.5,receivedAt:'25 Agu 2026',allocation:[15,15,13,13,13,13] },
  { id:'LCY-007',sequence:7,supplier:'Sinaran',material:'Lucy',yards:131.5,receivedAt:'25 Agu 2026',allocation:[14,14,15,15,15,15] },
  { id:'LCY-008',sequence:8,supplier:'Sinaran',material:'Lucy',yards:96.5,receivedAt:'25 Agu 2026',allocation:[10,10,11,11,11,11] },
  { id:'LCY-009',sequence:9,supplier:'Sinaran',material:'Lucy',yards:90,receivedAt:'25 Agu 2026',allocation:[11,10,10,10,10,10] },
  { id:'LCY-010',sequence:10,supplier:'Sinaran',material:'Lucy',yards:119,receivedAt:'26 Agu 2026',allocation:[0,0,0,0,0,0] },
  { id:'ZDK-011',sequence:11,supplier:'Sumber Cahaya',material:'Zodiak KW',yards:103,receivedAt:'25 Agu 2026',allocation:[0,0,0,0,0,0] },
  { id:'ZDK-012',sequence:12,supplier:'Sumber Cahaya',material:'Zodiak KW',yards:98,receivedAt:'25 Agu 2026',allocation:[0,0,0,0,0,0] },
]
const fabricRollSuppliers=Array.from(new Set(fabricRollCatalog.map((roll)=>roll.supplier)))
const fabricRollMaterials=Array.from(new Set(fabricRollCatalog.map((roll)=>roll.material)))

const productBrands = Array.from(new Set(productCatalog.map((product) => product.brand)))
const productRanges = Array.from(new Set(productCatalog.map((product) => product.range)))
const productSizes = Array.from(new Set(productCatalog.flatMap((product) => product.sizes)))
const stockLocations = Array.from(new Set(productCatalog.map((product) => product.location)))
const stockGrades = Array.from(new Set(productCatalog.map((product) => product.grade)))

const nav: Record<NavSection, string[]> = {
  Produksi: ['Pesanan Produksi', 'Bagi Potongan', 'Mandor & WIP', 'Laundry', 'QC & Final SKU', 'Barang BS & Rework'],
  Gudang: ['Ringkasan Gudang', 'Pembelian & Penerimaan', 'Bahan & Roll', 'Aksesori', 'Ringkasan Barang Jadi', 'Mutasi Barang Jadi · Vivo', 'Mutasi Barang Jadi · Widie', 'Kartu Stok FG', 'Retur & Penyesuaian'],
  Penjualan: ['Penjualan & Invoice', 'Alokasi Barang Jadi', 'Retur Penjualan', 'Pembayaran Pelanggan', 'Riwayat Pelanggan'],
  Keuangan: ['Ringkasan Keuangan', 'Kas & Bank', 'Hutang Supplier & Vendor', 'Piutang Pelanggan', 'Payroll & Kasbon', 'HPP & Rekalkulasi', 'Jurnal & Transaksi Lain', 'Laporan & Tutup Buku'],
  'Master Data': ['Produk & SKU', 'Pelanggan', 'Supplier & Vendor', 'Mandor & Pekerja', 'Gudang & Lokasi'],
}

const initialMovements: Movement[] = [
  { id: 'MV-1052', sku: '73001', brand: 'Vivo', customer: 'Nusantara Fashion', date: '27 Agu 2026 · 13:44', ref: 'INV-260827-019', type: 'Penjualan', note: 'Nusantara Fashion', delta: [-8,-8,-8], balance: [96,84,108] },
  { id: 'MV-1051', sku: '73001', brand: 'Widie', customer: 'Maju Jaya', date: '27 Agu 2026 · 12:30', ref: 'INV-260827-018', type: 'Penjualan', note: 'Maju Jaya', delta: [-6,-6,-6], balance: [84,78,90] },
  { id: 'MV-1050', sku: '73002', brand: 'Vivo', customer: null, date: '27 Agu 2026 · 10:22', ref: 'FG-260827-006', type: 'QC → FG', note: 'PO-260812-031', delta: [24,24,24], balance: [72,60,48] },
  { id: 'MV-1049', sku: '73002', brand: 'Widie', customer: null, date: '27 Agu 2026 · 09:55', ref: 'FG-260827-005', type: 'QC → FG', note: 'PO-260812-028', delta: [12,12,12], balance: [42,36,48] },
  { id: 'MV-1048', sku: '73001', brand: 'Vivo', customer: 'Sumber Denim', date: '26 Agu 2026 · 17:06', ref: 'INV-260826-027', type: 'Penjualan', note: 'Sumber Denim', delta: [-12,-8,-4], balance: [104,92,116] },
  { id: 'MV-1047', sku: '73001', brand: 'Widie', customer: null, date: '26 Agu 2026 · 15:40', ref: 'ADJ-260826-006', type: 'Penyesuaian', note: 'Selisih opname disetujui owner', delta: [0,-1,0], balance: [90,84,96] },
  { id: 'MV-1046', sku: '73002', brand: 'Vivo', customer: 'Nusantara Fashion', date: '26 Agu 2026 · 14:25', ref: 'INV-260826-023', type: 'Penjualan', note: 'Nusantara Fashion', delta: [-6,-6,-6], balance: [48,36,24] },
  { id: 'MV-1045', sku: '73002', brand: 'Widie', customer: 'Sumber Denim', date: '26 Agu 2026 · 11:18', ref: 'INV-260826-020', type: 'Penjualan', note: 'Sumber Denim', delta: [-4,-4,-4], balance: [30,24,36] },
]

const chronologicalMovements = [...initialMovements].reverse()
const money = (value: number) => new Intl.NumberFormat('id-ID', { style: 'currency', currency: 'IDR', maximumFractionDigits: 0 }).format(value)
const dozenPieces = (pcs: number) => `${Math.floor(Math.max(0, pcs) / 12)} lusin · ${Math.max(0, pcs) % 12} potong`
const parseDecimal = (value: string) => {
  const parsed = Number(value.trim().replace(/\s/g, '').replace(',', '.'))
  return Number.isFinite(parsed) ? Math.max(0, parsed) : 0
}
const formatQuantity = (value: number, digits = 1) => new Intl.NumberFormat('id-ID', { maximumFractionDigits: digits }).format(value)

function parseQty(value: string, fallbackUnit: 'lusin' | 'pcs') {
  const normalized = value.toLowerCase().replace(',', '.')
  const dozenMatch = normalized.match(/([0-9]+(?:\.[0-9]+)?)\s*(?:lusin|lsn|dozen)/)
  const pcsMatch = normalized.match(/([0-9]+(?:\.[0-9]+)?)\s*(?:pcs|pc|piece|biji|potong|ptg)/)
  if (dozenMatch || pcsMatch) {
    const dozen = dozenMatch ? Number(dozenMatch[1]) * 12 : 0
    const pcs = pcsMatch ? Number(pcsMatch[1]) : 0
    return Math.max(0, Math.round(dozen + pcs))
  }
  const plain = Number(normalized.replace(/[^0-9.]/g, ''))
  if (Number.isNaN(plain)) return 0
  return Math.max(0, Math.round(fallbackUnit === 'lusin' ? plain * 12 : plain))
}

function Icon({ name }: { name: string }) {
  const icons: Record<string, LucideIcon> = {
    dashboard: LayoutDashboard, Produksi: Factory, Gudang: Warehouse, Penjualan: ReceiptText,
    Keuangan: WalletCards, 'Master Data': Database, audit: ShieldCheck, search: Search,
    back: ArrowLeft, stock: Layers3, check: Check, menu: Menu, up: ChevronUp, down: ChevronDown,
    reset: RotateCcw, filter: SlidersHorizontal, calendar: CalendarDays, user: UserRound,
    arrow: ArrowRight, drag: GripVertical, close: X, chevron: ChevronDown, brand: Scissors,
    product: Package, list: ListFilter, boxes: Boxes, cost: CircleDollarSign,
    document: FileText, history: History, link: Link2, plus: Plus, ruler: Ruler,
    trash: Trash2,
  }
  const Glyph = icons[name] ?? Package
  return <Glyph className="icon" strokeWidth={1.8} aria-hidden="true" />
}

function MultiCheckFilter({ label, options, selected, onChange }: {
  label: string; options: string[]; selected: string[]; onChange: (values: string[]) => void
}) {
  const [open, setOpen] = useState(false)
  const [query, setQuery] = useState('')
  const allSelected = selected.length === options.length
  const shownOptions = options.filter((option) => option.toLowerCase().includes(query.toLowerCase()))
  const toggle = (option: string) => onChange(selected.includes(option) ? selected.filter((value) => value !== option) : [...selected, option])

  return <div className={`multi-filter ${open ? 'is-open' : ''}`}>
    <button className="filter-trigger" aria-expanded={open} onClick={() => setOpen(!open)}>
      <Icon name="filter" /><span>{label}</span><b>{allSelected ? 'Semua' : selected.length}</b><Icon name="chevron" />
    </button>
    {open && <>
      <button className="filter-page-shield" aria-label={`Tutup filter ${label}`} onClick={() => setOpen(false)} />
      <div className="filter-sheet" role="dialog" aria-label={`Filter ${label}`}>
        <div className="filter-sheet-handle" />
        <div className="filter-sheet-head"><div><small>FILTER</small><strong>{label}</strong></div><button aria-label="Tutup" onClick={() => setOpen(false)}><Icon name="close" /></button></div>
        <div className="filter-option-search"><Icon name="search" /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder={`Cari ${label.toLowerCase()}...`} /></div>
        <div className="filter-bulk"><label><input type="checkbox" checked={allSelected} onChange={() => onChange(allSelected ? [] : [...options])} /> Pilih semua</label><button onClick={() => onChange([])}>Kosongkan</button></div>
        <div className="filter-options">{shownOptions.map((option) => <label key={option}><input type="checkbox" checked={selected.includes(option)} onChange={() => toggle(option)} /><span>{option}</span></label>)}</div>
        <button className="filter-apply" onClick={() => setOpen(false)}>Terapkan · {selected.length} dipilih</button>
      </div>
    </>}
  </div>
}

function App() {
  const [page, setPage] = useState<Page>('dashboard')
  const [expanded, setExpanded] = useState<NavSection | null>(null)
  const [mobileNav, setMobileNav] = useState(false)
  const [qtyText, setQtyText] = useState('2')
  const [unit, setUnit] = useState<'lusin' | 'pcs'>('lusin')
  const [sizes, setSizes] = useState<SizeRow[]>([
    { size: '28', stock: 96, qty: 8, input: '8' }, { size: '29', stock: 84, qty: 8, input: '8' }, { size: '30', stock: 108, qty: 8, input: '8' },
  ])
  const [movements, setMovements] = useState(chronologicalMovements)
  const [vivoBookBrands, setVivoBookBrands] = useState<string[]>(['Vivo'])
  const [widieBookBrands, setWidieBookBrands] = useState<string[]>(['Widie'])

  const totalPcs = parseQty(qtyText, unit)
  const composed = sizes.reduce((sum, row) => sum + row.qty, 0)
  const stockEnough = sizes.every((row) => row.qty <= row.stock)
  const compositionOk = composed > 0
  const saleTotal = (composed / 12) * 1080000

  const distribute = () => {
    const base = Math.floor(totalPcs / sizes.length)
    let remainder = totalPcs % sizes.length
    setSizes((rows) => rows.map((row) => {
      const qty = base + (remainder-- > 0 ? 1 : 0)
      return { ...row, qty, input: String(qty) }
    }))
  }

  const title = page === 'dashboard' ? 'Ringkasan bisnis'
    : page === 'sales' ? 'Input Penjualan'
    : page === 'stock-card' ? 'Kartu Stok FG'
    : page === 'movements-vivo' ? 'Mutasi Barang Jadi · Vivo'
    : page === 'movements-widie' ? 'Mutasi Barang Jadi · Widie'
    : page === 'procurement' ? 'Pembelian & Penerimaan'
    : page === 'cutting-roll' ? 'Bagi Potongan'
    : page === 'mandor-wip' ? 'Mandor & WIP'
    : 'Modul ERP'

  const chooseSubmenu = (label: string) => {
    if (label === 'Penjualan & Invoice') setPage('sales')
    else if (label === 'Kartu Stok FG') setPage('stock-card')
    else if (label === 'Mutasi Barang Jadi · Vivo') setPage('movements-vivo')
    else if (label === 'Mutasi Barang Jadi · Widie') setPage('movements-widie')
    else if (label === 'Pembelian & Penerimaan') setPage('procurement')
    else if (label === 'Bagi Potongan') setPage('cutting-roll')
    else if (label === 'Mandor & WIP') setPage('mandor-wip')
    else setPage('placeholder')
    setMobileNav(false)
  }

  return <div className="app-shell">
    <aside className={`sidebar ${mobileNav ? 'sidebar-open' : ''}`}>
      <div className="brand-row"><div className="brand-mark"><Icon name="brand" /></div><div><strong>ATELIER</strong><span>GARMENT ERP</span></div><button className="nav-close" onClick={() => setMobileNav(false)}>×</button></div>
      <div className="nav-caption">MENU UTAMA</div>
      <button className={`nav-main ${page === 'dashboard' ? 'active' : ''}`} onClick={() => { setPage('dashboard'); setExpanded(null); setMobileNav(false) }}><Icon name="dashboard" /><span>Dashboard</span></button>
      {(Object.keys(nav) as NavSection[]).map((section) => <div className="nav-section" key={section}>
        <button className={`nav-main ${expanded === section ? 'active' : ''}`} onClick={() => setExpanded(expanded === section ? null : section)}><Icon name={section} /><span>{section}</span><span className="chevron">{expanded === section ? '⌄' : '›'}</span></button>
        {expanded === section && <div className="submenu">{nav[section].map((item) => {
          const active = (item === 'Penjualan & Invoice' && page === 'sales') || (item === 'Kartu Stok FG' && page === 'stock-card') || (item === 'Mutasi Barang Jadi · Vivo' && page === 'movements-vivo') || (item === 'Mutasi Barang Jadi · Widie' && page === 'movements-widie') || (item === 'Pembelian & Penerimaan' && page === 'procurement') || (item === 'Bagi Potongan' && page === 'cutting-roll') || (item === 'Mandor & WIP' && page === 'mandor-wip')
          return <button key={item} className={active ? 'sub-active' : ''} onClick={() => chooseSubmenu(item)}>• {item}</button>
        })}</div>}
      </div>)}
      <div className="sidebar-spacer" />
      <button className="nav-main"><Icon name="audit" /><span>Pengaturan & Audit</span><span className="chevron">›</span></button>
      <div className="env-card"><div className="env-dot" /><div><strong>ERP Enteng</strong><span>Target dev · UX alpha</span></div></div>
    </aside>

    <main className="main-panel">
      <header className="topbar"><button className="mobile-menu" onClick={() => setMobileNav(true)}><Icon name="menu" /></button><div className="top-title"><div className="top-icon"><Icon name="dashboard" /></div><div><strong>{title}</strong><span>{page === 'dashboard' ? 'Satu layar untuk keputusan hari ini' : 'Cepat, jelas, dan aman buat operasional'}</span></div></div><div className="top-actions"><button className="sim-badge"><span /> DATA SIMULASI</button><button className="round-btn"><Icon name="search" /></button><div className="owner"><span>OH</span><div><strong>Owner</strong><small>Administrator</small></div><b>⌄</b></div></div></header>
      <div className="page-wrap">
        {page === 'dashboard' && <Dashboard onOpenSales={() => setPage('sales')} />}
        {page === 'sales' && <SalesPage qtyText={qtyText} setQtyText={setQtyText} unit={unit} setUnit={setUnit} sizes={sizes} setSizes={setSizes} totalPcs={totalPcs} composed={composed} stockEnough={stockEnough} compositionOk={compositionOk} saleTotal={saleTotal} distribute={distribute} openStock={() => setPage('stock-card')} />}
        {page === 'stock-card' && <StockCard />}
        {page === 'movements-vivo' && <Movements bookName="Vivo" bookBrands={vivoBookBrands} setBookBrands={setVivoBookBrands} movements={movements} setMovements={setMovements} />}
        {page === 'movements-widie' && <Movements bookName="Widie" bookBrands={widieBookBrands} setBookBrands={setWidieBookBrands} movements={movements} setMovements={setMovements} />}
        {page === 'procurement' && <ProcurementPage />}
        {page === 'cutting-roll' && <CuttingRollPage />}
        {page === 'mandor-wip' && <MandorWipPage />}
        {page === 'placeholder' && <Placeholder />}
      </div>
    </main>
  </div>
}

function Dashboard({ onOpenSales }: { onOpenSales: () => void }) {
  return <>
    <section className="hero-copy"><div className="eyebrow">DASHBOARD OWNER <span><Icon name="calendar" /> Kamis, 27 Agustus 2026</span></div><h1>Pabrik bergerak.<br className="desktop-only" /> Angka tetap kebaca.</h1><p>Pantau uang, stok, HPP, dan aliran produksi tanpa membuka sepuluh laporan.</p></section>
    <section className="kpi-grid"><Kpi label="Kas & Bank" value="Rp284,6 jt" note="+4,2% dibanding bulan lalu" tone="good" /><Kpi label="Nilai stok FG" value="Rp418,2 jt" note="1.482 pcs siap jual" tone="neutral" /><Kpi label="Piutang berjalan" value="Rp176,8 jt" note="Rp42 jt jatuh tempo ≤ 7 hari" tone="warn" /><Kpi label="HPP bulan ini" value="Rp298,4 jt" note="stabil · 62,1% dari penjualan" tone="good" /></section>
    <section className="dashboard-grid"><div className="panel wide-panel"><div className="panel-head"><div><div className="eyebrow">PULSA KEUANGAN</div><h2>Penjualan, HPP & laba kotor</h2><p>Klik detail untuk menelusuri transaksi pembentuk angkanya.</p></div><button className="soft-btn">30 hari terakhir ⌄</button></div><div className="chart-wrap">{[52,65,58,73,69,84,77,92,88,101,96,112].map((h,i)=><div className="bar-col" key={i}><div className="bar primary" style={{height:`${h}%`}}/><div className="bar secondary" style={{height:`${Math.max(30,h-28)}%`}}/></div>)}</div><div className="chart-legend"><span><i className="legend-a" /> Penjualan Rp480,5 jt</span><span><i className="legend-b" /> HPP Rp298,4 jt</span><strong>Laba kotor Rp182,1 jt</strong></div></div><div className="panel attention-panel"><div className="eyebrow">BUTUH PERHATIAN</div><h2>4 hal hari ini</h2><Attention label="Piutang lewat jatuh tempo" value="Rp18,4 jt" meta="3 pelanggan" tone="danger" /><Attention label="Stok size menipis" value="7 SKU" meta="di bawah minimum" tone="warn" /><Attention label="WIP tanpa update > 3 hari" value="2 grup" meta="cek mandor" tone="neutral" /><Attention label="QC menunggu keputusan" value="34 pcs" meta="BS / rework" tone="neutral" /></div></section>
    <section className="flow-strip"><div><div className="eyebrow">ALIRAN PABRIK</div><h2>Dari potongan sampai uang masuk</h2></div>{['Potongan 1.920 pcs','Mandor 1.406 pcs','Laundry 628 pcs','QC 412 pcs','FG 1.482 pcs'].map((x,i)=><div className="flow-node" key={x}><span>{String(i+1).padStart(2,'0')}</span><strong>{x.split(' ').slice(0,-2).join(' ') || x.split(' ')[0]}</strong><small>{x.split(' ').slice(-2).join(' ')}</small></div>)}<button className="primary-btn" onClick={onOpenSales}>Input penjualan <Icon name="arrow" /></button></section>
  </>
}

function Kpi({ label, value, note, tone }: { label: string; value: string; note: string; tone: string }) { return <div className="kpi-card"><div className="kpi-label">{label}</div><div className="kpi-value">{value}</div><div className={`kpi-note ${tone}`}>{tone === 'good' ? '↗' : tone === 'warn' ? '↘' : '•'} {note}</div><div className={`kpi-orb ${tone}`}>◉</div></div> }
function Attention({ label, value, meta, tone }: { label: string; value: string; meta: string; tone: string }) { return <div className="attention-row"><span className={`attention-dot ${tone}`} /><div><strong>{label}</strong><small>{meta}</small></div><b>{value}</b></div> }

function ProcurementPage() {
  const [mode,setMode] = useState<ReceiptMode>('fabric')
  const [rolls,setRolls] = useState<RollDraft[]>([{id:1,yards:'131,5'},{id:2,yards:'91'},{id:3,yards:'124'},{id:4,yards:''}])
  const [benchmarkPrice,setBenchmarkPrice] = useState('48500')
  const [accessoryQty,setAccessoryQty] = useState('1200')
  const [accessoryPrice,setAccessoryPrice] = useState('850')
  const [historyOpen,setHistoryOpen] = useState(false)
  const [rollDetailOpen,setRollDetailOpen] = useState(false)
  const activeRolls=rolls.filter((roll)=>parseDecimal(roll.yards)>0)
  const totalYards=activeRolls.reduce((sum,roll)=>sum+parseDecimal(roll.yards),0)
  const benchmark=parseDecimal(benchmarkPrice)
  const accessoryTotal=parseDecimal(accessoryQty)*parseDecimal(accessoryPrice)
  const updateRoll=(id:number,value:string)=>setRolls((rows)=>rows.map((roll)=>roll.id===id?{...roll,yards:value}:roll))
  const addRoll=()=>setRolls((rows)=>[...rows,{id:Math.max(0,...rows.map((roll)=>roll.id))+1,yards:''}])
  const removeRoll=(id:number)=>setRolls((rows)=>rows.length>1?rows.filter((roll)=>roll.id!==id):rows)

  return <>
    <section className="hero-copy compact procurement-hero"><div className="eyebrow">GUDANG · PENERIMAAN BARANG</div><h1>Pembelian & penerimaan</h1><p>Catat surat jalan saat barang datang. Kain masuk per gulung, aksesori masuk sebagai jumlah langsung.</p></section>
    <div className="procurement-mode-bar panel" role="tablist" aria-label="Jenis penerimaan">
      <div className="mode-tabs"><button role="tab" aria-selected={mode==='fabric'} className={mode==='fabric'?'active':''} onClick={()=>setMode('fabric')}><Icon name="ruler"/><span><strong>Kain</strong><small>Roll + yard</small></span></button><button role="tab" aria-selected={mode==='accessory'} className={mode==='accessory'?'active':''} onClick={()=>setMode('accessory')}><Icon name="boxes"/><span><strong>Aksesori</strong><small>Qty langsung</small></span></button></div>
      <div className="receiving-rule"><Icon name="document"/><span><strong>Dasar penerimaan: surat jalan</strong><small>Kasbon boleh menyusul tanpa menahan stok masuk.</small></span></div>
    </div>
    <section className="procurement-layout">
      <div className="panel receipt-editor">
        <div className="proc-panel-head"><div><div className="eyebrow">PENERIMAAN BARU</div><h2>{mode==='fabric'?'Kain per gulung':'Aksesori per jumlah'}</h2></div><span className="draft-pill">Draft</span></div>
        <div className="receipt-meta-grid" key={mode}>
          <Field label="Pabrik / supplier"><input className="erp-input" defaultValue={mode==='fabric'?'Sinaran':'Mitra Aksesori'}/></Field>
          <Field label={mode==='fabric'?'Nama bahan':'Nama aksesori'}><input className="erp-input" defaultValue={mode==='fabric'?'1069 Ori':'Kancing Metal 17 mm'}/></Field>
          <Field label="Nomor surat jalan"><input className="erp-input" defaultValue={mode==='fabric'?'SJ-SNR-0827-19':'SJ-MA-0827-08'}/></Field>
          <Field label="Tanggal barang datang"><input className="erp-input" type="date" defaultValue="2026-08-27"/></Field>
        </div>
        {mode==='fabric'?<>
          <div className="roll-entry-head"><div><span>RINCIAN GULUNG</span><strong>Satu baris untuk satu roll</strong></div><button className="soft-btn add-roll" onClick={addRoll}><Icon name="plus"/> Tambah roll</button></div>
          <div className="roll-entry-list">{rolls.map((roll,index)=><div className="roll-entry-row" key={roll.id}><span className="roll-number">{String(index+1).padStart(2,'0')}</span><div><label htmlFor={`roll-${roll.id}`}>Yard pada gulung</label><div className="yard-input"><input id={`roll-${roll.id}`} inputMode="decimal" value={roll.yards} placeholder="0" onChange={(event)=>updateRoll(roll.id,event.target.value)}/><span>yd</span></div></div><small>{parseDecimal(roll.yards)>0?`${formatQuantity(parseDecimal(roll.yards))} yard siap diterima`:'Belum diisi'}</small><button className="remove-roll" aria-label={`Hapus roll ${index+1}`} onClick={()=>removeRoll(roll.id)} disabled={rolls.length===1}><Icon name="trash"/></button></div>)}</div>
          <div className="benchmark-entry"><div><Icon name="cost"/><span><strong>Harga benchmark / yard</strong><small>Dipakai sementara sampai kasbon aktual datang.</small></span></div><div className="money-input"><span>Rp</span><input inputMode="numeric" value={benchmarkPrice} onChange={(event)=>setBenchmarkPrice(event.target.value)}/></div></div>
          <div className="receipt-total-strip"><div><span>TOTAL GULUNG</span><strong>{activeRolls.length}</strong><small>roll terisi</small></div><div><span>TOTAL PANJANG</span><strong>{formatQuantity(totalYards)} yd</strong><small>jumlah semua roll</small></div><div className="receipt-grand-total"><span>NILAI BENCHMARK</span><strong>{money(totalYards*benchmark)}</strong><small>{formatQuantity(totalYards)} yd × {money(benchmark)}</small></div></div>
        </>:<>
          <div className="accessory-entry-grid"><Field label="Jumlah diterima"><div className="qty-unit-input"><input inputMode="numeric" value={accessoryQty} onChange={(event)=>setAccessoryQty(event.target.value)}/><span>pcs</span></div></Field><Field label="Harga benchmark / pcs"><div className="money-input"><span>Rp</span><input inputMode="numeric" value={accessoryPrice} onChange={(event)=>setAccessoryPrice(event.target.value)}/></div></Field></div>
          <div className="accessory-total-card"><div><Icon name="boxes"/><span><small>JUMLAH MASUK</small><strong>{formatQuantity(parseDecimal(accessoryQty),0)} pcs</strong></span></div><div><small>NILAI BENCHMARK</small><strong>{money(accessoryTotal)}</strong></div></div>
        </>}
        <div className="receipt-actions"><button className="soft-btn">Simpan draft</button><button className="primary-btn">Review penerimaan <Icon name="arrow"/></button></div>
      </div>
      <aside className="procurement-side">{mode==='fabric'?<>
        <div className="panel current-receipt-card">
          <div className="current-receipt-head"><div><span>HARGA AKTIF</span><h2>Sinaran · 1069 Ori</h2><small>SJ-SNR-0821-07 · masuk 21 Agu 2026</small></div><span className="actual-pill"><Icon name="check"/> Aktual</span></div>
          <div className="receipt-quantity-hero"><div><span>27 gulung</span><strong>3.029,5 yd</strong></div><Icon name="ruler"/></div>
          <div className="active-price"><span>Harga kasbon terbaru</span><strong>{money(49200)}<small>/ yard</small></strong><em>Nilai aktif {money(3029.5*49200)}</em></div>
          <button className="history-toggle" aria-expanded={historyOpen} onClick={()=>setHistoryOpen(!historyOpen)}><span><Icon name="history"/> Riwayat harga</span><span>{historyOpen?'Tutup':'Lihat'} <Icon name={historyOpen?'up':'down'}/></span></button>
          {historyOpen&&<div className="price-history"><div><span className="timeline-dot current"/><div><strong>Rp49.200 / yd</strong><small>Kasbon aktual · 26 Agu 2026</small></div><b>Aktif</b></div><div><span className="timeline-dot"/><div><strong>Rp48.500 / yd</strong><small>Benchmark saat barang datang · 21 Agu 2026</small></div><b>Awal</b></div><div className="price-delta"><span>Selisih nilai</span><strong>+{money(3029.5*(49200-48500))}</strong></div></div>}
          <button className="roll-preview-toggle" aria-expanded={rollDetailOpen} onClick={()=>setRollDetailOpen(!rollDetailOpen)}><span>Rincian 27 roll</span><Icon name={rollDetailOpen?'up':'down'}/></button>
          {rollDetailOpen&&<div className="roll-preview-grid">{[131.5,91,124,115.5,109,127.25].map((yard,index)=><span key={`${yard}-${index}`}><small>ROLL {String(index+1).padStart(2,'0')}</small><strong>{formatQuantity(yard,2)} yd</strong></span>)}<span className="more-rolls"><strong>+21</strong><small>roll lainnya</small></span></div>}
        </div>
        <div className="panel pending-cost-card"><div><span className="estimated-dot"/><div><strong>Malibu · Denim 14 oz</strong><small>18 gulung · 1.984 yd</small></div><span>Menunggu kasbon</span></div><div><small>Harga benchmark aktif sementara</small><strong>{money(47800)} / yd</strong><em>{money(1984*47800)}</em></div></div>
      </>:<>
        <div className="panel current-receipt-card accessory-current"><div className="current-receipt-head"><div><span>PENERIMAAN TERAKHIR</span><h2>Kancing Metal 17 mm</h2><small>Mitra Aksesori · SJ-MA-0827-08</small></div><span className="actual-pill"><Icon name="check"/> Diterima</span></div><div className="accessory-quantity-hero"><span>Jumlah masuk</span><strong>1.200 pcs</strong><small>Tidak perlu dibuat roll atau yard.</small></div><div className="active-price"><span>Harga aktif</span><strong>{money(850)}<small>/ pcs</small></strong><em>Total {money(1200*850)}</em></div></div>
        <div className="panel procurement-note"><Icon name="link"/><div><strong>Tetap satu alur gudang</strong><p>Kain dan aksesori masuk dari surat jalan yang sama, tetapi cara hitung fisiknya tetap sesuai bentuk barang.</p></div></div>
      </>}</aside>
    </section>
  </>
}

function CuttingRollPage() {
  const [query,setQuery]=useState('')
  const [selectedSuppliers,setSelectedSuppliers]=useState([...fabricRollSuppliers])
  const [selectedMaterials,setSelectedMaterials]=useState([...fabricRollMaterials])
  const [selectedRollIds,setSelectedRollIds]=useState(()=>fabricRollCatalog.slice(0,9).map((roll)=>roll.id))
  const [sizeSlots,setSizeSlots]=useState<CuttingSizeSlot[]>(()=>initialCuttingSizeSlots.map((slot)=>({...slot})))
  const nextSlotKeyRef=useRef(initialCuttingSizeSlots.length+1)
  const [allocations,setAllocations]=useState<Record<string,number[]>>(()=>Object.fromEntries(fabricRollCatalog.map((roll)=>[roll.id,[...roll.allocation]])))
  const [fillRange,setFillRange]=useState<{source:number;target:number}|null>(null)
  const fillRangeRef=useRef<{source:number;target:number}|null>(null)
  const fillDraggedRef=useRef(false)
  const [columnFillRange,setColumnFillRange]=useState<{source:number;target:number}|null>(null)
  const columnFillRangeRef=useRef<{source:number;target:number}|null>(null)
  const columnFillDraggedRef=useRef(false)
  const selectedIdSet=useMemo(()=>new Set(selectedRollIds),[selectedRollIds])
  const visibleRolls=useMemo(()=>fabricRollCatalog.filter((roll)=>{
    const matchesQuery=`${roll.id} roll ${roll.sequence} ${roll.supplier} ${roll.material} ${roll.yards}`.toLowerCase().includes(query.toLowerCase())
    return matchesQuery&&selectedSuppliers.includes(roll.supplier)&&selectedMaterials.includes(roll.material)
  }),[query,selectedSuppliers,selectedMaterials])
  const selectedRolls=fabricRollCatalog.filter((roll)=>selectedIdSet.has(roll.id))
  const totalYards=selectedRolls.reduce((sum,roll)=>sum+roll.yards,0)
  const displayedSizeSlots=useMemo(()=>sizeSlots.map((slot,slotIndex)=>{
    const sameSizeCount=sizeSlots.filter((candidate)=>candidate.size===slot.size).length
    const drawingNo=sizeSlots.slice(0,slotIndex+1).filter((candidate)=>candidate.size===slot.size).length
    return {...slot,drawingNo,image:sameSizeCount>1?drawingLabel(drawingNo):''}
  }),[sizeSlots])
  const slotTotals=sizeSlots.map((_,slotIndex)=>selectedRolls.reduce((sum,roll)=>sum+(allocations[roll.id]?.[slotIndex]??0),0))
  const sizeTotals=cuttingSizes.map((size)=>sizeSlots.reduce((sum,slot,slotIndex)=>sum+(slot.size===size?slotTotals[slotIndex]:0),0)) as QtyTuple
  const totalPieces=slotTotals.reduce((sum,qty)=>sum+qty,0)
  const slotGridStyle={'--cutting-slot-count':displayedSizeSlots.length} as CSSProperties
  const allVisibleSelected=visibleRolls.length>0&&visibleRolls.every((roll)=>selectedIdSet.has(roll.id))
  const toggleRoll=(id:string)=>setSelectedRollIds((current)=>current.includes(id)?current.filter((rollId)=>rollId!==id):fabricRollCatalog.filter((roll)=>current.includes(roll.id)||roll.id===id).map((roll)=>roll.id))
  const toggleVisible=()=>setSelectedRollIds((current)=>{
    const next=new Set(current)
    visibleRolls.forEach((roll)=>allVisibleSelected?next.delete(roll.id):next.add(roll.id))
    return fabricRollCatalog.filter((roll)=>next.has(roll.id)).map((roll)=>roll.id)
  })
  const addSizeSlot=(size:string)=>{
    let insertIndex=sizeSlots.length
    sizeSlots.forEach((slot,index)=>{if(slot.size===size)insertIndex=index+1})
    const nextSlot={key:`${size}-${nextSlotKeyRef.current++}`,size}
    setSizeSlots((current)=>[...current.slice(0,insertIndex),nextSlot,...current.slice(insertIndex)])
    setAllocations((current)=>Object.fromEntries(Object.entries(current).map(([rollId,row])=>[rollId,[...row.slice(0,insertIndex),0,...row.slice(insertIndex)]])))
    setColumnFillRange(null)
    columnFillRangeRef.current=null
  }
  const removeSizeSlot=(size:string)=>{
    const matchingIndexes=sizeSlots.map((slot,index)=>slot.size===size?index:-1).filter((index)=>index>=0)
    if(matchingIndexes.length<=1)return
    const removeIndex=matchingIndexes[matchingIndexes.length-1]
    const mergeIndex=matchingIndexes[matchingIndexes.length-2]
    setSizeSlots((current)=>current.filter((_,index)=>index!==removeIndex))
    setAllocations((current)=>Object.fromEntries(Object.entries(current).map(([rollId,row])=>{
      const next=[...row]
      next[mergeIndex]=(next[mergeIndex]??0)+(next[removeIndex]??0)
      next.splice(removeIndex,1)
      return [rollId,next]
    })))
    setColumnFillRange(null)
    columnFillRangeRef.current=null
  }
  const updateAllocation=(roll:FabricRoll,slotIndex:number,value:string)=>setAllocations((current)=>{
    const next=[...(current[roll.id]??sizeSlots.map((_,index)=>roll.allocation[index]??0))]
    const normalized=value.replace(/[^0-9]/g,'').replace(/^0+(?=\d)/,'')
    next[slotIndex]=normalized===''?0:Math.max(0,Math.round(Number(normalized)||0))
    return {...current,[roll.id]:next}
  })
  const focusAllocationCell=(rollIndex:number,slotIndex:number)=>{
    const input=document.querySelector<HTMLInputElement>(`[data-cutting-row="${rollIndex}"][data-cutting-slot="${slotIndex}"]`)
    if(!input)return
    input.focus()
    input.select()
  }
  const handleAllocationKey=(event:ReactKeyboardEvent<HTMLInputElement>,rollIndex:number,slotIndex:number)=>{
    if(event.ctrlKey||event.metaKey||event.altKey)return
    let nextRoll=rollIndex
    let nextSlot=slotIndex
    if(event.key==='Enter')nextRoll+=event.shiftKey?-1:1
    else if(event.key==='ArrowDown')nextRoll+=1
    else if(event.key==='ArrowUp')nextRoll-=1
    else if(event.key==='ArrowRight')nextSlot+=1
    else if(event.key==='ArrowLeft')nextSlot-=1
    else return
    if(nextRoll<0||nextRoll>=selectedRolls.length||nextSlot<0||nextSlot>=sizeSlots.length)return
    event.preventDefault()
    focusAllocationCell(nextRoll,nextSlot)
  }
  const pasteAllocationGrid=(event:ReactClipboardEvent<HTMLInputElement>,startRoll:number,startSlot:number)=>{
    const clipboard=event.clipboardData.getData('text').replace(/\r/g,'').replace(/\n+$/,'')
    if(!clipboard)return
    event.preventDefault()
    const pastedRows=clipboard.split('\n').map((line)=>line.split('\t'))
    setAllocations((current)=>{
      const next={...current}
      pastedRows.forEach((cells,rowOffset)=>{
        const roll=selectedRolls[startRoll+rowOffset]
        if(!roll)return
        const row=[...(next[roll.id]??sizeSlots.map((_,index)=>roll.allocation[index]??0))]
        cells.forEach((cell,columnOffset)=>{
          const slotIndex=startSlot+columnOffset
          if(slotIndex>=sizeSlots.length)return
          const normalized=cell.trim().replace(/[^0-9]/g,'').replace(/^0+(?=\d)/,'')
          row[slotIndex]=normalized===''?0:Math.max(0,Math.round(Number(normalized)||0))
        })
        next[roll.id]=row
      })
      return next
    })
  }
  const fillRowsFromSource=(sourceIndex:number,targetIndex:number)=>{
    if(targetIndex===sourceIndex)return
    setAllocations((current)=>{
      const sourceRoll=selectedRolls[sourceIndex]
      if(!sourceRoll)return current
      const sourceValues=[...(current[sourceRoll.id]??sizeSlots.map((_,index)=>sourceRoll.allocation[index]??0))]
      const next={...current}
      const start=Math.min(sourceIndex,targetIndex)
      const end=Math.max(sourceIndex,targetIndex)
      for(let rowIndex=start;rowIndex<=end;rowIndex+=1){
        if(rowIndex===sourceIndex)continue
        const targetRoll=selectedRolls[rowIndex]
        if(targetRoll)next[targetRoll.id]=[...sourceValues]
      }
      return next
    })
  }
  const beginRowFill=(event:ReactPointerEvent<HTMLButtonElement>,sourceIndex:number)=>{
    event.preventDefault()
    event.currentTarget.setPointerCapture(event.pointerId)
    fillDraggedRef.current=false
    const range={source:sourceIndex,target:sourceIndex}
    fillRangeRef.current=range
    setFillRange(range)
  }
  const moveRowFill=(event:ReactPointerEvent<HTMLButtonElement>)=>{
    const range=fillRangeRef.current
    if(!range)return
    const rowElement=document.elementFromPoint(event.clientX,event.clientY)?.closest<HTMLElement>('[data-allocation-row-index]')
    const hoveredIndex=Number(rowElement?.dataset.allocationRowIndex)
    if(!Number.isFinite(hoveredIndex))return
    const target=Math.max(0,Math.min(selectedRolls.length-1,hoveredIndex))
    if(target===range.target)return
    const nextRange={source:range.source,target}
    fillRangeRef.current=nextRange
    setFillRange(nextRange)
  }
  const finishRowFill=(event:ReactPointerEvent<HTMLButtonElement>)=>{
    const range=fillRangeRef.current
    if(range&&range.target!==range.source){
      fillRowsFromSource(range.source,range.target)
      fillDraggedRef.current=true
    }
    fillRangeRef.current=null
    setFillRange(null)
    if(event.currentTarget.hasPointerCapture(event.pointerId))event.currentTarget.releasePointerCapture(event.pointerId)
  }
  const cancelRowFill=(event:ReactPointerEvent<HTMLButtonElement>)=>{
    fillRangeRef.current=null
    setFillRange(null)
    if(event.currentTarget.hasPointerCapture(event.pointerId))event.currentTarget.releasePointerCapture(event.pointerId)
  }
  const clickRowFill=(sourceIndex:number)=>{
    if(fillDraggedRef.current){fillDraggedRef.current=false;return}
    const targetIndex=sourceIndex<selectedRolls.length-1?sourceIndex+1:sourceIndex-1
    fillRowsFromSource(sourceIndex,targetIndex)
  }
  const fillColumnsFromSource=(sourceSlot:number,targetSlot:number)=>{
    if(targetSlot===sourceSlot)return
    setAllocations((current)=>{
      const next={...current}
      const start=Math.min(sourceSlot,targetSlot)
      const end=Math.max(sourceSlot,targetSlot)
      selectedRolls.forEach((roll)=>{
        const row=[...(current[roll.id]??sizeSlots.map((_,index)=>roll.allocation[index]??0))]
        const sourceValue=row[sourceSlot]
        for(let slotIndex=start;slotIndex<=end;slotIndex+=1){
          if(slotIndex!==sourceSlot)row[slotIndex]=sourceValue
        }
        next[roll.id]=row
      })
      return next
    })
  }
  const beginColumnFill=(event:ReactPointerEvent<HTMLButtonElement>,sourceSlot:number)=>{
    event.preventDefault()
    event.currentTarget.setPointerCapture(event.pointerId)
    columnFillDraggedRef.current=false
    const range={source:sourceSlot,target:sourceSlot}
    columnFillRangeRef.current=range
    setColumnFillRange(range)
  }
  const moveColumnFill=(event:ReactPointerEvent<HTMLButtonElement>)=>{
    const range=columnFillRangeRef.current
    if(!range)return
    const slotElement=document.elementFromPoint(event.clientX,event.clientY)?.closest<HTMLElement>('[data-column-fill-slot]')
    const hoveredSlot=Number(slotElement?.dataset.columnFillSlot)
    if(!Number.isFinite(hoveredSlot))return
    const target=Math.max(0,Math.min(sizeSlots.length-1,hoveredSlot))
    if(target===range.target)return
    const nextRange={source:range.source,target}
    columnFillRangeRef.current=nextRange
    setColumnFillRange(nextRange)
  }
  const finishColumnFill=(event:ReactPointerEvent<HTMLButtonElement>)=>{
    const range=columnFillRangeRef.current
    if(range&&range.target!==range.source){
      fillColumnsFromSource(range.source,range.target)
      columnFillDraggedRef.current=true
    }
    columnFillRangeRef.current=null
    setColumnFillRange(null)
    if(event.currentTarget.hasPointerCapture(event.pointerId))event.currentTarget.releasePointerCapture(event.pointerId)
  }
  const cancelColumnFill=(event:ReactPointerEvent<HTMLButtonElement>)=>{
    columnFillRangeRef.current=null
    setColumnFillRange(null)
    if(event.currentTarget.hasPointerCapture(event.pointerId))event.currentTarget.releasePointerCapture(event.pointerId)
  }
  const clickColumnFill=(sourceSlot:number)=>{
    if(columnFillDraggedRef.current){columnFillDraggedRef.current=false;return}
    const targetSlot=sourceSlot<sizeSlots.length-1?sourceSlot+1:sourceSlot-1
    fillColumnsFromSource(sourceSlot,targetSlot)
  }
  return <>
    <section className="hero-copy compact cutting-hero"><div className="eyebrow">PRODUKSI · CUTTING</div><h1>Bagi Potongan</h1><p>Ambil roll, catat hasil potong per roll dan size, lalu simpan sebagai WIP Potongan. Batch mandor belum dibuat di tahap ini.</p></section>
    <section className="cutting-flow-rail cutting-flow-three panel" aria-label="Alur Bagi Potongan">{['Pilih roll','Catat hasil per roll','Simpan ke WIP'].map((label,index)=><div className={index===0?'active':''} key={label}><span>{String(index+1).padStart(2,'0')}</span><strong>{label}</strong>{index<2&&<Icon name="arrow"/>}</div>)}</section>
    <section className="roll-first-layout">
      <div className="panel roll-catalog-panel">
        <div className="cutting-panel-head"><div><span>01 · SUMBER KAIN</span><h2>Pilih roll yang mau dibagi</h2><p>Satu roll tetap satu baris. Urutan dan yard asal tidak digabung.</p></div><span className="selection-pill">{selectedRolls.length} dipilih</span></div>
        <div className="roll-catalog-toolbar"><div className="roll-search"><Icon name="search"/><input value={query} onChange={(event)=>setQuery(event.target.value)} placeholder="Cari roll, pabrik, bahan, atau yard..."/></div><div className="roll-filters"><MultiCheckFilter label="Pabrik" options={fabricRollSuppliers} selected={selectedSuppliers} onChange={setSelectedSuppliers}/><MultiCheckFilter label="Bahan" options={fabricRollMaterials} selected={selectedMaterials} onChange={setSelectedMaterials}/></div></div>
        <div className="roll-list-caption"><span>{visibleRolls.length} roll tersedia</span><button type="button" onClick={toggleVisible}>{allVisibleSelected?'Batalkan hasil tampil':'Pilih semua hasil'}</button></div>
        <div className="cutting-roll-list">{visibleRolls.map((roll)=>{const selected=selectedIdSet.has(roll.id);return <button type="button" aria-pressed={selected} className={`stock-roll-row ${selected?'selected':''}`} key={roll.id} onClick={()=>toggleRoll(roll.id)}><span className="roll-select-box">{selected&&<Icon name="check"/>}</span><span className="stock-roll-seq">{String(roll.sequence).padStart(2,'0')}</span><span className="stock-roll-name"><strong>{roll.material}</strong><small>{roll.supplier} · {roll.id} · masuk {roll.receivedAt}</small></span><span className="stock-roll-yard"><strong>{formatQuantity(roll.yards,2)} yd</strong><small>{selected?'Masuk pembagian':'Siap dipilih'}</small></span></button>})}{visibleRolls.length===0&&<div className="catalog-empty"><Icon name="search"/><strong>Roll tidak ditemukan</strong><small>Periksa pencarian atau pilihan filter pabrik dan bahan.</small></div>}</div>
      </div>
      <aside className="panel cutting-live-summary">
        <div className="eyebrow">POTONGAN INDUK</div><h2>Kulot Lucy · 31–33</h2><p>Hasil cutting ini belum dibagi ke batch mandor.</p>
        <div className="cutting-summary-main"><div><span>ROLL DIPILIH</span><strong>{selectedRolls.length}</strong><small>{formatQuantity(totalYards,2)} yard</small></div><div><span>TOTAL POTONGAN</span><strong>{totalPieces} pcs</strong><small>{dozenPieces(totalPieces)}</small></div></div>
        <div className="cutting-summary-sizes">{cuttingSizes.map((size,index)=><div key={size}><span>SIZE {size}</span><strong>{sizeTotals[index]} pcs</strong><small>{dozenPieces(sizeTotals[index])}</small></div>)}</div>
        <div className="po-preview"><Icon name="warehouse"/><div><strong>Tujuan berikutnya: WIP Potongan</strong><span>Setelah disimpan, hasil ini menunggu mandor mengambil. Pembagian batch dilakukan saat pickup.</span></div></div>
        <button type="button" className="primary-btn cutting-next" disabled={selectedRolls.length===0} onClick={()=>document.getElementById('allocation-workbench')?.scrollIntoView({behavior:'smooth',block:'start'})}>Lanjut bagi ukuran <Icon name="arrow"/></button>
      </aside>
    </section>
    <section className="panel allocation-workbench" id="allocation-workbench">
      <div className="cutting-panel-head allocation-head"><div><span>02 · HASIL POTONG PER ROLL</span><h2>Susun slot size sesuai gambar hari ini</h2><p>Satu size boleh punya satu, dua, tiga, atau lebih slot. Label gambar hanya muncul kalau size tersebut berulang.</p></div><span className="draft-pill">Draft</span></div>
      <div className="cutting-meta-grid"><Field label="Merek"><select className="erp-input" defaultValue="Vivo"><option>Vivo</option><option>Widie</option></select></Field><Field label="Model"><input className="erp-input" defaultValue="Kulot Lucy"/></Field><Field label="Tipe pola"><input className="erp-input" defaultValue="Cutbray Jumbo Lucy"/></Field><Field label="Range ukuran"><select className="erp-input" defaultValue="31–33"><option>28–30</option><option>31–33</option><option>34–36</option></select></Field><Field label="Tanggal potong"><input className="erp-input" type="date" defaultValue="2026-08-27"/></Field><div className="future-po-field"><span>KODE POTONGAN</span><strong>POT otomatis</strong><small>saat hasil masuk WIP</small></div></div>
      <div className="size-slot-builder"><div className="size-slot-builder-copy"><span>SUSUN KOLOM SIZE</span><strong>Tambah atau kurangi gambar per size</strong><small>Tombol minus menggabungkan isi kolom terakhir ke kolom sebelumnya—total size tetap aman.</small></div><div className="size-slot-controls">{cuttingSizes.map((size)=>{const count=sizeSlots.filter((slot)=>slot.size===size).length;return <div className="size-slot-control" key={size}><div><span>SIZE {size}</span><strong>{count===1?'1 kolom':`${count} kolom`}</strong><small>{count===1?'Tanpa label gambar':`Gambar A–${drawingLabel(count)}`}</small></div><div><button type="button" disabled={count<=1} aria-label={`Kurangi slot Size ${size}`} title="Gabungkan kolom terakhir ke kolom sebelumnya" onClick={()=>removeSizeSlot(size)}>−</button><b>{count}</b><button type="button" aria-label={`Tambah slot Size ${size}`} title="Tambah kolom gambar baru" onClick={()=>addSizeSlot(size)}>+</button></div></div>})}</div></div>
      <div className="cutting-grid-shortcuts"><span><kbd>Enter</kbd> turun</span><span><kbd>Tab</kbd> ke kanan</span><span><kbd>↑ ↓ ← →</kbd> pindah sel</span><span><Icon name="drag"/> Tarik baris ke atas / bawah</span><span>Tarik kolom ke kiri / kanan</span><span>Paste blok Excel didukung</span></div>
      <div className="column-fill-toolbar"><div><span>FILL SATU KOLOM</span><small>Klik untuk satu kolom · tarik kiri/kanan untuk beberapa</small></div><div className="column-fill-grid" style={slotGridStyle}>{displayedSizeSlots.map((slot,slotIndex)=>{const isSource=columnFillRange?.source===slotIndex;const isPreview=Boolean(columnFillRange&&slotIndex!==columnFillRange.source&&slotIndex>=Math.min(columnFillRange.source,columnFillRange.target)&&slotIndex<=Math.max(columnFillRange.source,columnFillRange.target));const drawingCopy=slot.image?` gambar ${slot.image}`:'';return <button type="button" tabIndex={-1} data-column-fill-slot={slotIndex} className={`${isSource?'fill-source':''} ${isPreview?'fill-preview':''}`} key={slot.key} aria-label={`Salin seluruh kolom size ${slot.size}${drawingCopy}`} title="Klik: salin ke kolom sebelah · tarik: isi beberapa kolom" onPointerDown={(event)=>beginColumnFill(event,slotIndex)} onPointerMove={moveColumnFill} onPointerUp={finishColumnFill} onPointerCancel={cancelColumnFill} onClick={()=>clickColumnFill(slotIndex)}><span>{slot.size}{slot.image&&<small>{slot.image}</small>}</span><Icon name="drag"/></button>})}</div><span>{displayedSizeSlots.length} kolom aktif</span></div>
      <div className="slot-legend"><div><span>SLOT UKURAN</span><small>Jumlah gambar mengikuti susunan di atas</small></div>{displayedSizeSlots.map((slot)=><span key={slot.key}><strong>{slot.size}</strong>{slot.image&&<small>Gbr {slot.image}</small>}</span>)}<b>TOTAL</b></div>
      <div className="allocation-roll-list">{selectedRolls.map((roll,index)=>{
        const row=allocations[roll.id]??sizeSlots.map((_,slotIndex)=>roll.allocation[slotIndex]??0)
        const rowTotal=row.reduce((sum,qty)=>sum+qty,0)
        const isFillSource=fillRange?.source===index
        const isFillPreview=Boolean(fillRange&&index!==fillRange.source&&index>=Math.min(fillRange.source,fillRange.target)&&index<=Math.max(fillRange.source,fillRange.target))
        return <article data-allocation-row-index={index} className={`allocation-roll-row ${isFillSource?'fill-source':''} ${isFillPreview?'fill-preview':''}`} key={roll.id}>
          <div className="allocation-roll-identity"><span>{String(index+1).padStart(2,'0')}</span><div><strong>Roll {String(roll.sequence).padStart(2,'0')} · {roll.material}</strong><small>{roll.supplier} · {formatQuantity(roll.yards,2)} yd</small></div></div>
          <div className="allocation-slot-grid" style={slotGridStyle}>{displayedSizeSlots.map((slot,slotIndex)=>{
            const isColumnSource=columnFillRange?.source===slotIndex
            const isColumnPreview=Boolean(columnFillRange&&slotIndex!==columnFillRange.source&&slotIndex>=Math.min(columnFillRange.source,columnFillRange.target)&&slotIndex<=Math.max(columnFillRange.source,columnFillRange.target))
            const drawingCopy=slot.image?`, gambar ${slot.image}`:''
            return <label className={`${isColumnSource?'column-fill-source':''} ${isColumnPreview?'column-fill-preview':''}`} key={slot.key}><span>{slot.size}{slot.image&&<small>{slot.image}</small>}</span><input data-cutting-row={index} data-cutting-slot={slotIndex} aria-label={`Roll ${roll.sequence}, size ${slot.size}${drawingCopy}`} inputMode="numeric" type="text" pattern="[0-9]*" value={row[slotIndex]??0} onFocus={(event)=>{if((row[slotIndex]??0)===0){const input=event.currentTarget;requestAnimationFrame(()=>input.select())}}} onClick={(event)=>{if((row[slotIndex]??0)===0)event.currentTarget.select()}} onKeyDown={(event)=>handleAllocationKey(event,index,slotIndex)} onPaste={(event)=>pasteAllocationGrid(event,index,slotIndex)} onChange={(event)=>updateAllocation(roll,slotIndex,event.target.value)}/></label>
          })}</div>
          <div className="allocation-row-total"><span>TOTAL ROLL</span><strong>{rowTotal} pcs</strong><small>{dozenPieces(rowTotal)}</small></div>
          <button type="button" tabIndex={-1} className="row-fill-handle" aria-label={`Salin isi Roll ${roll.sequence} ke baris atas atau bawah`} title="Klik: salin ke baris terdekat · tarik: isi ke atas atau bawah" onPointerDown={(event)=>beginRowFill(event,index)} onPointerMove={moveRowFill} onPointerUp={finishRowFill} onPointerCancel={cancelRowFill} onClick={()=>clickRowFill(index)}><Icon name="drag"/><span/></button>
        </article>
      })}{selectedRolls.length===0&&<div className="allocation-empty"><Icon name="ruler"/><strong>Belum ada roll dipilih</strong><small>Pilih minimal satu roll di bagian atas untuk mulai membagi ukuran.</small></div>}</div>
      <div className="cutting-totals-row"><div><span>JUMLAH SIZE 31</span><strong>{sizeTotals[0]} pcs</strong></div><div><span>JUMLAH SIZE 32</span><strong>{sizeTotals[1]} pcs</strong></div><div><span>JUMLAH SIZE 33</span><strong>{sizeTotals[2]} pcs</strong></div><div><span>TOTAL BATCH</span><strong>{totalPieces} pcs</strong><small>{dozenPieces(totalPieces)}</small></div></div>
      <section className="cutting-wip-destination" aria-label="Tujuan hasil cutting">
        <div><span>03 · SIMPAN HASIL CUTTING</span><h2>Masuk WIP Potongan, belum menjadi batch jahit</h2><p>Semua jejak roll dan size tetap melekat pada Potongan induk. Mandor, batch jahit, dan alur laundry baru dicatat saat fisik barang benar-benar diambil.</p></div>
        <div className="cutting-wip-card"><span className="wip-state-dot"/><div><small>STATUS SETELAH DISIMPAN</small><strong>Menunggu mandor mengambil</strong><span>{selectedRolls.length} roll · {totalPieces} pcs · belum dialokasikan ke batch</span></div></div>
      </section>
      <div className="allocation-footer"><small>Frontend simulasi · belum mengurangi stok roll atau mencatat WIP di backend.</small><div><button type="button" className="soft-btn">Simpan draft cutting</button><button type="button" className="primary-btn" disabled={selectedRolls.length===0||totalPieces===0}>Simpan Potongan ke WIP <Icon name="arrow"/></button></div></div>
    </section>
  </>
}

function MandorWipPage() {
  const wipRolls = fabricRollCatalog.slice(0, 9)
  const wipRollRows = wipRolls.map((roll) => {
    const sizes = rollSizeQuantities(roll.allocation)
    return { roll, sizes, quantity: sizes.reduce((sum, qty) => sum + qty, 0) }
  })
  const wipSizeTotals = wipRollRows.reduce<QtyTuple>((totals, row) => totals.map((qty, index) => qty + row.sizes[index]) as QtyTuple, [0, 0, 0])
  const wipTotal = wipSizeTotals.reduce((sum, qty) => sum + qty, 0)
  const [mandor,setMandor] = useState('Mandor Afat')
  const [pickupAt,setPickupAt] = useState('2026-08-27T10:30')
  const [batchCountInput,setBatchCountInput] = useState('3')
  const [batchCount,setBatchCount] = useState(3)
  const [allocationMode,setAllocationMode] = useState<WipAllocationMode>('roll')
  const [rollBatchMatrix,setRollBatchMatrix] = useState<RollBatchSizeMatrix>(() => createRollBatchSizeMatrix(wipRolls, 3))
  const [splitEditorRollId,setSplitEditorRollId] = useState<string | null>(null)
  const [allocationMessage,setAllocationMessage] = useState('')
  const [rollDrag,setRollDrag] = useState<{ rollId: string; target: number | null; x: number; y: number } | null>(null)
  const rollDragRef = useRef<{ rollId: string; target: number | null; x: number; y: number } | null>(null)
  const rollBatchCountRef = useRef(3)
  const effectiveBatchCount = allocationMode === 'size' ? cuttingSizes.length : batchCount
  const targetTotals = allocationMode === 'size' ? [...wipSizeTotals] : balancedBatchTargets(wipTotal, batchCount)
  const sizeMatrix = createSizeAllocationMatrix(wipSizeTotals, cuttingSizes.length)
  const sourceChecks = allocationMode === 'roll'
    ? wipRollRows.flatMap((row) => row.sizes.map((total, sizeIndex) => ({
      key: `${row.roll.id} · Size ${cuttingSizes[sizeIndex]}`,
      total,
      assigned: (rollBatchMatrix[row.roll.id] ?? []).reduce((sum, batchSizes) => sum + cellQuantity(batchSizes[sizeIndex]), 0),
    })))
    : cuttingSizes.map((size, sizeIndex) => ({
      key: `Size ${size}`,
      total: wipSizeTotals[sizeIndex],
      assigned: (sizeMatrix[size] ?? []).reduce((sum, value) => sum + cellQuantity(value), 0),
    }))
  const sourcesExact = sourceChecks.every((source) => source.assigned === source.total)
  const batchSizeMix = Array.from({ length: effectiveBatchCount }, (_, batchIndex) => cuttingSizes.map((size, sizeIndex) => {
    if (allocationMode === 'size') return cellQuantity(sizeMatrix[size]?.[batchIndex])
    return wipRollRows.reduce((sum, row) => sum + cellQuantity(rollBatchMatrix[row.roll.id]?.[batchIndex]?.[sizeIndex]), 0)
  }) as QtyTuple)
  const batchTotals = batchSizeMix.map((sizes) => sizes.reduce((sum, qty) => sum + qty, 0))
  const assignedTotal = batchTotals.reduce((sum, qty) => sum + qty, 0)
  const remainingTotal = wipTotal - assignedTotal
  const splitRolls = wipRollRows.filter((row) => (rollBatchMatrix[row.roll.id] ?? []).filter((sizes) => sizes.reduce((sum, value) => sum + cellQuantity(value), 0) > 0).length > 1)
  const wholeRolls = wipRollRows.filter((row) => {
    const batches = rollBatchMatrix[row.roll.id] ?? []
    const usedBatches = batches.filter((sizes) => sizes.reduce((sum, value) => sum + cellQuantity(value), 0) > 0)
    return usedBatches.length === 1 && row.sizes.every((source, sizeIndex) => cellQuantity(usedBatches[0][sizeIndex]) === source)
  })
  const applyBatchCount = () => {
    const nextCount = Math.min(6, Math.max(2, Math.round(Number(batchCountInput) || 2)))
    setBatchCountInput(String(nextCount))
    setBatchCount(nextCount)
    rollBatchCountRef.current = nextCount
    setRollBatchMatrix(createRollBatchSizeMatrix(wipRolls, nextCount))
    setSplitEditorRollId(null)
  }
  const selectAllocationMode = (nextMode: WipAllocationMode) => {
    if (nextMode === allocationMode) return
    setSplitEditorRollId(null)
    setAllocationMessage('')
    if (nextMode === 'size') {
      rollBatchCountRef.current = batchCount
      setAllocationMode('size')
      setBatchCount(cuttingSizes.length)
      setBatchCountInput(String(cuttingSizes.length))
      return
    }
    const restoredCount = rollBatchCountRef.current
    setAllocationMode('roll')
    setBatchCount(restoredCount)
    setBatchCountInput(String(restoredCount))
  }
  const updateSplitAllocation = (rollId: string, batchIndex: number, sizeIndex: number, rawValue: string) => {
    if (/[+-]/.test(rawValue)) {
      setAllocationMessage('Gunakan jumlah absolut. +/− adalah koreksi sumber, bukan pembagian batch.')
      return
    }
    const digits = rawValue.replace(/[^0-9]/g, '')
    const normalized = digits.replace(/^0+(?=\d)/, '')
    setAllocationMessage('')
    setRollBatchMatrix((current) => {
      const rollBatches = (current[rollId] ?? Array.from({ length: batchCount }, () => ['0', '0', '0'])).map((sizes) => [...sizes])
      rollBatches[batchIndex][sizeIndex] = normalized
      return { ...current, [rollId]: rollBatches }
    })
  }
  const assignWholeRoll = (rollId: string, targetBatch: number) => {
    const sourceRow = wipRollRows.find((row) => row.roll.id === rollId)
    if (!sourceRow) return
    setRollBatchMatrix((current) => ({
      ...current,
      [rollId]: Array.from({ length: batchCount }, (_, batchIndex) => batchIndex === targetBatch ? sourceRow.sizes.map(String) : ['0', '0', '0']),
    }))
    setAllocationMessage('')
  }
  const beginRollDrag = (event: ReactPointerEvent<HTMLButtonElement>, rollId: string) => {
    event.preventDefault()
    event.currentTarget.setPointerCapture(event.pointerId)
    const next = { rollId, target: null, x: event.clientX, y: event.clientY }
    rollDragRef.current = next
    setRollDrag(next)
  }
  const moveRollDrag = (event: ReactPointerEvent<HTMLButtonElement>) => {
    const current = rollDragRef.current
    if (!current) return
    const targetElement = document.elementFromPoint(event.clientX, event.clientY)?.closest<HTMLElement>('[data-wip-drop-batch]')
    const parsedTarget = Number(targetElement?.dataset.wipDropBatch)
    const target = Number.isFinite(parsedTarget) && parsedTarget >= 0 && parsedTarget < batchCount ? parsedTarget : null
    const next = { ...current, target, x: event.clientX, y: event.clientY }
    rollDragRef.current = next
    setRollDrag(next)
  }
  const finishRollDrag = (event: ReactPointerEvent<HTMLButtonElement>) => {
    const current = rollDragRef.current
    if (current?.target !== null && current?.target !== undefined) assignWholeRoll(current.rollId, current.target)
    rollDragRef.current = null
    setRollDrag(null)
    if (event.currentTarget.hasPointerCapture(event.pointerId)) event.currentTarget.releasePointerCapture(event.pointerId)
  }
  const cancelRollDrag = (event: ReactPointerEvent<HTMLButtonElement>) => {
    rollDragRef.current = null
    setRollDrag(null)
    if (event.currentTarget.hasPointerCapture(event.pointerId)) event.currentTarget.releasePointerCapture(event.pointerId)
  }
  const tidyWholeRolls = () => {
    setRollBatchMatrix(createRollBatchSizeMatrix(wipRolls, batchCount))
    setSplitEditorRollId(null)
    setAllocationMessage('')
  }
  const splitEditorRow = wipRollRows.find((row) => row.roll.id === splitEditorRollId)
  const splitEditorChecks = splitEditorRow?.sizes.map((source, sizeIndex) => {
    const assigned = (rollBatchMatrix[splitEditorRow.roll.id] ?? []).reduce((sum, sizes) => sum + cellQuantity(sizes[sizeIndex]), 0)
    return { source, assigned, remaining: source - assigned }
  }) ?? []
  const splitEditorExact = splitEditorChecks.every((check) => check.remaining === 0)
  const isReady = sourcesExact && assignedTotal === wipTotal && mandor.length > 0 && pickupAt.length > 0

  return <>
    <section className="hero-copy compact cutting-hero"><div className="eyebrow">PRODUKSI · MANDOR</div><h1>Ambil WIP & Bentuk Batch</h1><p>Pilih Potongan yang sudah selesai cutting. Setelah mandor mengambil, baru bentuk batch kerja yang sama untuk alur jahit sampai laundry.</p></section>
    <section className="wip-flow-rail panel" aria-label="Alur pickup dan pembentukan batch">{['Pilih WIP Potongan','Catat mandor mengambil','Tentukan jumlah batch','Drag roll / batch per size'].map((label,index)=><div className={index===0?'active':''} key={label}><span>{String(index+1).padStart(2,'0')}</span><strong>{label}</strong>{index<3&&<Icon name="arrow"/>}</div>)}</section>
    <section className="wip-pickup-layout">
      <aside className="panel wip-queue-panel">
        <div className="wip-queue-head"><div><span>01 · WIP POTONGAN</span><h2>Menunggu diambil</h2><p>Belum punya batch jahit atau laundry.</p></div><span className="selection-pill">3 antrean</span></div>
        <label className="wip-search"><Icon name="search"/><input placeholder="Cari kode, bahan, atau model..."/></label>
        <div className="wip-queue-list">
          <button type="button" className="wip-queue-card selected"><span className="wip-queue-status">SIAP DIAMBIL</span><strong>POT-260827-042</strong><small>Kulot Lucy · Sinaran</small><div><span><b>{wipTotal} pcs</b> · 9 roll</span><em>Size 31–33</em></div></button>
          <button type="button" className="wip-queue-card"><span className="wip-queue-status">SIAP DIAMBIL</span><strong>POT-260827-041</strong><small>Malibu · Sinaran</small><div><span><b>488 pcs</b> · 7 roll</span><em>Size 28–30</em></div></button>
          <button type="button" className="wip-queue-card"><span className="wip-queue-status">MENUNGGU REVIEW</span><strong>POT-260827-039</strong><small>Zodiak KW · Sumber Cahaya</small><div><span><b>342 pcs</b> · 5 roll</span><em>Size 34–36</em></div></button>
        </div>
      </aside>

      <div className="panel wip-batch-workspace">
        <div className="wip-selected-head"><div><span>WIP TERPILIH</span><h2>POT-260827-042 · Kulot Lucy</h2><p>{wipTotal} pcs dari 9 roll · selesai potong 27 Agu 2026</p></div><span className="wip-waiting-pill"><span/> Belum diambil</span></div>
        <div className="pickup-meta-grid">
          <Field label="Diambil oleh / mandor"><select className="erp-input" value={mandor} onChange={(event)=>setMandor(event.target.value)}><option>Mandor Afat</option><option>Mandor Asep</option><option>Mandor Dedi</option></select></Field>
          <Field label="Tanggal & waktu ambil"><input className="erp-input" type="datetime-local" value={pickupAt} onChange={(event)=>setPickupAt(event.target.value)}/></Field>
          <div className="pickup-flow-note"><Icon name="link"/><div><span>BATCH YANG SAMA</span><strong>Jahit → Laundry</strong><small>Vendor laundry dipilih saat barang benar-benar dikirim.</small></div></div>
        </div>

        <section className="batch-builder-setup">
          <div className="batch-builder-copy"><span>03 · BENTUK BATCH SETELAH PICKUP</span><h2>{allocationMode==='roll'?'Mau dibagi menjadi berapa batch?':'Satu size langsung menjadi satu batch'}</h2><p>{allocationMode==='roll'?'Pilih jumlah batch, lalu tarik roll utuh ke batch tujuan. Pecah roll hanya saat memang diperlukan.':'Sistem membuat Batch Size 31, Size 32, dan Size 33 langsung dari sumber Potongan yang terkunci.'}</p></div>
          {allocationMode==='roll'?<div className="batch-count-control"><label><span>JUMLAH BATCH</span><div><input type="text" pattern="[0-9]*" inputMode="numeric" value={batchCountInput} onFocus={(event)=>event.currentTarget.select()} onChange={(event)=>setBatchCountInput(event.target.value.replace(/[^0-9]/g,'').replace(/^0+(?=\d)/,''))}/><b>batch</b></div></label><button type="button" className="soft-btn" onClick={applyBatchCount}>Buat ulang</button></div>:<div className="size-batch-count-lock"><span>OTOMATIS</span><strong>3 batch</strong><small>Size 31 · Size 32 · Size 33</small></div>}
        </section>

        <div className="wip-allocation-mode" role="group" aria-label="Dasar pembagian batch">
          <button type="button" className={allocationMode==='roll'?'active':''} aria-pressed={allocationMode==='roll'} onClick={()=>selectAllocationMode('roll')}><Icon name="boxes"/><div><span>UTAMA</span><strong>Drag per roll</strong><small>Bagi per roll; kalau bisa jangan dipisah.</small></div></button>
          <button type="button" className={allocationMode==='size'?'active':''} aria-pressed={allocationMode==='size'} onClick={()=>selectAllocationMode('size')}><Icon name="ruler"/><div><span>PER SIZE</span><strong>Langsung batch per size</strong><small>Tiga size sumber menjadi tiga batch terkunci.</small></div></button>
        </div>

        <div className="wip-reconcile-strip">
          <div><span>SUMBER POTONGAN · TERKUNCI</span><strong>{wipTotal} pcs</strong><small>{cuttingSizes.map((size,index)=>`${size}: ${wipSizeTotals[index]}`).join(' · ')}</small></div>
          <div className={assignedTotal===wipTotal?'success':'warn'}><span>SUDAH DIBAGI</span><strong>{assignedTotal} pcs</strong><small>{effectiveBatchCount} batch · angka absolut</small></div>
          <div className={remainingTotal===0&&sourcesExact?'success':'warn'}><span>SISA / SELISIH</span><strong>{remainingTotal===0&&sourcesExact?'0 pcs · Pas':remainingTotal>0?`${remainingTotal} pcs tersisa`:`${Math.abs(remainingTotal)} pcs berlebih`}</strong><small>{sourcesExact?'Semua sumber cocok':'Ada roll atau size yang tidak cocok'}</small></div>
        </div>

        {allocationMode==='roll'?<div className="golden-roll-rule"><Icon name="boxes"/><div><span>GOLDEN RULE</span><strong>Bagi per roll kalau bisa jangan dipisah</strong><small>{wholeRolls.length} roll utuh · {splitRolls.length} roll terpecah. Jumlah roll pecah bukan batas; pecah hanya bila kebutuhan batch memang meminta.</small></div><div><button type="button" onClick={tidyWholeRolls}>Susun roll utuh</button></div></div>:<div className="golden-roll-rule size-mode"><Icon name="ruler"/><div><span>MODE PER SIZE</span><strong>Size 31, 32, dan 33 langsung menjadi batch sendiri</strong><small>Jumlah sumber dikunci; pembagian batch tidak boleh mengubah komposisi Potongan.</small></div></div>}

        {allocationMode==='roll'&&<section className="wip-roll-tray"><div className="wip-roll-tray-head"><div><span>ROLL SUMBER · DRAG & DROP</span><strong>Tarik roll utuh ke kartu batch</strong><small>Butuh pengecualian? Buka “Atur pecahan” dan isi per size.</small></div><span>{wipRollRows.length} roll · {wipTotal} pcs</span></div><div className="wip-roll-token-grid">{wipRollRows.map((row)=>{
          const batches=rollBatchMatrix[row.roll.id]??[]
          const usedBatchIndexes=batches.map((sizes,index)=>({index,quantity:sizes.reduce((sum,value)=>sum+cellQuantity(value),0)})).filter((batch)=>batch.quantity>0)
          const assigned=usedBatchIndexes.reduce((sum,batch)=>sum+batch.quantity,0)
          const exact=row.sizes.every((source,sizeIndex)=>batches.reduce((sum,sizes)=>sum+cellQuantity(sizes[sizeIndex]),0)===source)
          const status=!exact?'Belum pas':usedBatchIndexes.length===1?`Batch ${String(usedBatchIndexes[0].index+1).padStart(2,'0')}`:`Pecah ${usedBatchIndexes.length} batch`
          return <article className={`wip-roll-token ${!exact?'warn':usedBatchIndexes.length>1?'split':'whole'}`} key={row.roll.id}><button type="button" className="wip-roll-drag-handle" aria-label={`Tarik Roll ${row.roll.sequence} ke batch`} title="Tahan lalu tarik ke kartu batch" onPointerDown={(event)=>beginRollDrag(event,row.roll.id)} onPointerMove={moveRollDrag} onPointerUp={finishRollDrag} onPointerCancel={cancelRollDrag}><Icon name="drag"/></button><div><span>ROLL {String(row.roll.sequence).padStart(2,'0')} · {row.roll.id}</span><strong>{row.quantity} pcs</strong><small>{cuttingSizes.map((size,index)=>`${size}: ${row.sizes[index]}`).join(' · ')}</small></div><em>{status}</em><button type="button" className="wip-roll-split-btn" onClick={()=>{setSplitEditorRollId(row.roll.id);setAllocationMessage('')}}>Atur pecahan</button><small className="wip-roll-assigned">{assigned}/{row.quantity}</small></article>
        })}</div></section>}

        {allocationMode==='roll'&&splitEditorRow&&<section className={`roll-split-editor ${splitEditorExact?'exact':'warn'}`} role="dialog" aria-label={`Atur pecahan Roll ${splitEditorRow.roll.sequence}`}><div className="roll-split-editor-head"><div><span>PENGECUALIAN · ROLL {String(splitEditorRow.roll.sequence).padStart(2,'0')}</span><h3>Pecah {splitEditorRow.roll.id} per size</h3><p>Isi jumlah absolut untuk setiap batch. Angka sumber Potongan di bawah ini tidak bisa diubah.</p></div><button type="button" aria-label="Tutup editor pecahan" onClick={()=>{setSplitEditorRollId(null);setAllocationMessage('')}}><Icon name="close"/></button></div><div className="split-source-locks">{cuttingSizes.map((size,sizeIndex)=>{const check=splitEditorChecks[sizeIndex];return <div className={check?.remaining===0?'success':'warn'} key={size}><span>SIZE {size} · SUMBER</span><strong>{check?.source??0} pcs</strong><small>Terbagi {check?.assigned??0} · Sisa {check?.remaining??0}</small></div>})}</div><div className="split-batch-grid">{Array.from({length:batchCount},(_,batchIndex)=>{const batchValues=rollBatchMatrix[splitEditorRow.roll.id]?.[batchIndex]??['0','0','0'];return <article key={batchIndex}><span>BATCH {String(batchIndex+1).padStart(2,'0')}</span>{cuttingSizes.map((size,sizeIndex)=><label key={size}><small>Size {size}</small><div><input type="text" pattern="[0-9]*" inputMode="numeric" aria-label={`Roll ${splitEditorRow.roll.sequence}, batch ${batchIndex+1}, size ${size}`} value={batchValues[sizeIndex]??'0'} onFocus={(event)=>event.currentTarget.select()} onClick={(event)=>event.currentTarget.select()} onChange={(event)=>updateSplitAllocation(splitEditorRow.roll.id,batchIndex,sizeIndex,event.target.value)}/><b>pcs</b></div></label>)}<strong>{batchValues.reduce((sum,value)=>sum+cellQuantity(value),0)} pcs</strong></article>})}</div><div className="roll-split-editor-foot"><span className={allocationMessage?'error':splitEditorExact?'success':'warn'}>{allocationMessage|| (splitEditorExact?'Pas dengan sumber Potongan.':'Belum pas—cek Sumber, Terbagi, dan Sisa per size.')}</span><button type="button" className="soft-btn" onClick={()=>setSplitEditorRollId(null)}>Selesai</button></div></section>}

        <div className="wip-batch-grid">
          {Array.from({length:effectiveBatchCount},(_,batchIndex)=>{const assignedRows=allocationMode==='roll'?wipRollRows.filter((row)=>(rollBatchMatrix[row.roll.id]?.[batchIndex]??[]).reduce((sum,value)=>sum+cellQuantity(value),0)>0):[];return <article data-wip-drop-batch={allocationMode==='roll'?batchIndex:undefined} className={`wip-batch-card ${rollDrag?.target===batchIndex?'drop-target':''} ${allocationMode==='size'?'size-batch-card':''}`} key={batchIndex}>
            <div className="wip-batch-card-head"><div><span>{allocationMode==='size'?`BATCH SIZE ${cuttingSizes[batchIndex]}`:`BATCH ${String(batchIndex+1).padStart(2,'0')}`}</span><strong>{batchTotals[batchIndex]} pcs</strong></div><small>{allocationMode==='size'?'Sumber terkunci':`Saran ${targetTotals[batchIndex]}`}</small></div>
            <div className="wip-batch-size-mix">{cuttingSizes.map((size,sizeIndex)=><span className={allocationMode==='size'&&sizeIndex===batchIndex?'active':''} key={size}><small>SIZE {size}</small><strong>{batchSizeMix[batchIndex][sizeIndex]}</strong></span>)}</div>
            <div className="wip-batch-source-list">
              {allocationMode==='roll'?(assignedRows.length>0?assignedRows.map((row)=>{const sizes=rollBatchMatrix[row.roll.id]?.[batchIndex]??['0','0','0'];const allocated=sizes.reduce((sum,value)=>sum+cellQuantity(value),0);const usedIn=(rollBatchMatrix[row.roll.id]??[]).filter((batchSizes)=>batchSizes.reduce((sum,value)=>sum+cellQuantity(value),0)>0).length;return <div className="wip-batch-source locked-source" key={row.roll.id}><div><strong>Roll {String(row.roll.sequence).padStart(2,'0')} · {allocated} pcs</strong><small>{cuttingSizes.map((size,sizeIndex)=>`${size}: ${cellQuantity(sizes[sizeIndex])}`).join(' · ')}</small></div><em className={usedIn>1?'pecah':'utuh'}>{usedIn>1?'Pecah':'Utuh'}</em><button type="button" onClick={()=>{setSplitEditorRollId(row.roll.id);setAllocationMessage('')}}>Atur</button></div>}):<div className="wip-batch-empty"><Icon name="drag"/><strong>Tarik roll ke sini</strong><small>Roll masuk utuh secara default</small></div>):<div className="wip-batch-source locked-size-source"><div><strong>Size {cuttingSizes[batchIndex]}</strong><small>Jumlah Potongan asli · tidak bisa diedit</small></div><b>{wipSizeTotals[batchIndex]} pcs</b><em>Pas</em></div>}
            </div>
            <div className="wip-batch-route"><span>JAHIT</span><Icon name="arrow"/><span>LAUNDRY</span><small>Kode batch tetap sama</small></div>
          </article>})}
        </div>

        {rollDrag&&<div className="roll-drag-ghost" style={{left:rollDrag.x,top:rollDrag.y}}><Icon name="drag"/><span>{rollDrag.rollId}</span><small>{rollDrag.target===null?'Arahkan ke batch':`Lepas di Batch ${String(rollDrag.target+1).padStart(2,'0')}`}</small></div>}
        <div className="wip-source-audit"><Icon name={sourcesExact?'check':'history'}/><div><strong>{sourcesExact?'Pembagian cocok dengan seluruh sumber':'Masih ada sumber roll atau size yang tidak cocok'}</strong><span>{sourceChecks.filter((source)=>source.assigned!==source.total).map((source)=>`${source.key}: ${source.assigned}/${source.total}`).join(' · ')||`${wipRollRows.length} roll · Size 31/32/33 seluruhnya rekonsiliasi`}</span></div></div>
        <div className="wip-correction-boundary"><Icon name="audit"/><div><strong>Ini pembagian batch, bukan Koreksi Potongan</strong><span>Jumlah sumber Size 31/32/33 dikunci. “Size 32 −5, Size 31 +5” tidak diterima di sini; bila hasil cutting memang salah, gunakan Koreksi Potongan berjejak.</span></div></div>
        <div className="allocation-footer"><small>Frontend simulasi · pickup dan batch belum diposting ke backend.</small><div><button type="button" className="soft-btn">Simpan draft pickup</button><button type="button" className="primary-btn" disabled={!isReady}>Catat pickup & buat {effectiveBatchCount} batch <Icon name="arrow"/></button></div></div>
      </div>
    </section>
  </>
}

function SalesPage(props: {
  qtyText: string; setQtyText: (v: string) => void; unit: 'lusin' | 'pcs'; setUnit: (v: 'lusin' | 'pcs') => void;
  sizes: SizeRow[]; setSizes: (v: SizeRow[]) => void; totalPcs: number; composed: number; stockEnough: boolean; compositionOk: boolean; saleTotal: number; distribute: () => void; openStock: () => void
}) {
  const { qtyText, setQtyText, unit, setUnit, sizes, setSizes, totalPcs, composed, stockEnough, compositionOk, saleTotal, distribute, openStock } = props
  const [productQuery, setProductQuery] = useState('')
  const [selectedProductKey, setSelectedProductKey] = useState(productKey(productCatalog[0]))
  const [selectedBrands, setSelectedBrands] = useState([...productBrands])
  const [selectedRanges, setSelectedRanges] = useState([...productRanges])
  const selectedProduct = productCatalog.find((product) => productKey(product) === selectedProductKey) ?? productCatalog[0]
  const visibleProducts = useMemo(() => productCatalog.filter((product) => {
    const matchesQuery = `${product.brand} ${product.code} ${product.range} ${product.name} ${product.color}`.toLowerCase().includes(productQuery.toLowerCase())
    return matchesQuery && selectedBrands.includes(product.brand) && selectedRanges.includes(product.range)
  }), [productQuery, selectedBrands, selectedRanges])
  const chooseProduct = (product: Product) => { setSelectedProductKey(productKey(product)); setSizes(product.sizes.map((size,index)=>({size,stock:product.stocks[index],qty:0,input:''}))) }

  return <>
    <section className="hero-copy compact"><div className="eyebrow">PENJUALAN · BARANG JADI</div><h1>Input penjualan</h1></section>
    <section className="sales-layout"><div className="panel sale-form-panel">
      <div className="form-grid two"><Field label="Pelanggan"><button className="select-btn">Nusantara Fashion <Icon name="chevron" /></button></Field><Field label="Sumber barang"><button className="select-btn">Gudang FG Utama <Icon name="chevron" /></button></Field></div>
      <div className="product-picker catalog-picker"><div className="catalog-toolbar"><div><div className="eyebrow">PILIH BARANG</div><small>{visibleProducts.length} dari {productCatalog.length} SKU</small></div><div className="catalog-search"><Icon name="search" /><input value={productQuery} onChange={(e)=>setProductQuery(e.target.value)} placeholder="Cari merek, SKU, range, model, warna..." /></div><div className="catalog-filters"><MultiCheckFilter label="Merek" options={productBrands} selected={selectedBrands} onChange={setSelectedBrands} /><MultiCheckFilter label="Range" options={productRanges} selected={selectedRanges} onChange={setSelectedRanges} /></div></div>
      <div className="catalog-results">{visibleProducts.map((product)=>{ const total=product.stocks.reduce((s,q)=>s+q,0); const active=productKey(product)===selectedProductKey; return <button className={`catalog-row ${active?'selected':''}`} key={productKey(product)} onClick={()=>chooseProduct(product)}><span className="catalog-seq">{String(productCatalog.findIndex((item)=>productKey(item)===productKey(product))+1).padStart(2,'0')}</span><div className="catalog-name"><small className="catalog-brand-first">{product.brand}</small><strong>{product.code}</strong><small>{product.name} · {product.color}</small></div><div className="catalog-meta"><span>{product.brand}</span><span>{product.range}</span></div><div className="catalog-stock"><strong>{total} pcs</strong><small>{dozenPieces(total)}</small></div><span className="catalog-check">{active?<Icon name="check"/>:<Icon name="arrow"/>}</span></button>})}</div></div>
      <div className="selected-product-head"><div><div className="sku-title"><span className="brand-chip strong">{selectedProduct.brand}</span><h2>{selectedProduct.code}</h2><span>Range {selectedProduct.range}</span></div><p>{selectedProduct.name} · {selectedProduct.color}</p></div><button className="soft-btn" onClick={openStock}><Icon name="stock" /> Cek kartu stok</button></div>
      <div className="sale-entry-grid"><div className="qty-column"><Field label="Isi cepat total · opsional"><div className="quantity-input"><input value={qtyText} onChange={(e)=>setQtyText(e.target.value)} placeholder="2 atau 1 lusin 6 potong"/><div className="unit-toggle"><button className={unit==='lusin'?'active':''} onClick={()=>setUnit('lusin')}>lusin</button><button className={unit==='pcs'?'active':''} onClick={()=>setUnit('pcs')}>pcs</button></div></div><small className="helper">Gunakan kalau mau isi cepat, lalu bagi rata ke size.</small></Field><div className="conversion"><span>HASIL ISI CEPAT</span><strong>{totalPcs} pcs</strong><small>{dozenPieces(totalPcs)}</small></div><button className="soft-btn quick-distribute" onClick={distribute} disabled={totalPcs<=0}>Bagi rata ke semua size</button><div className="price-box"><span>HARGA / LUSIN</span><strong>{money(1080000)}</strong></div></div>
      <div className="composition-column"><div className="composition-head"><div><strong>Jumlah per size</strong><span>Boleh ketik PCS, lusin, atau campuran.</span></div></div><div className="size-grid">{sizes.map((row,index)=><div className="size-card" key={row.size}><div><strong>Size {row.size}</strong><span>stok {row.stock} pcs</span></div><input inputMode="text" value={row.input} placeholder="8 atau 1 lusin" onChange={(e)=>{ const raw=e.target.value; const next=[...sizes]; next[index]={...row,input:raw,qty:parseQty(raw,'pcs')}; setSizes(next) }}/><small className="parsed-qty">{row.qty} pcs · {dozenPieces(row.qty)}</small></div>)}</div><div className="sales-total-strip"><span>TOTAL DARI SIZE</span><strong>{composed} pcs</strong><small>{dozenPieces(composed)}</small></div><div className={`validation ${compositionOk&&stockEnough?'success':'error'}`}><Icon name={compositionOk&&stockEnough?'check':'filter'} /> {!compositionOk?'Isi minimal satu size.':stockEnough?'Jumlah otomatis dijumlahkan dan stok mencukupi.':'Ada size yang melebihi stok.'}</div></div></div>
      <div className="sale-footer"><div><span>TOTAL PENJUALAN</span><strong>{money(saleTotal)}</strong><small>Nusantara Fashion · {selectedProduct.brand} {selectedProduct.code} · {composed} pcs · {dozenPieces(composed)}</small></div><button className="primary-btn" disabled={!compositionOk||!stockEnough}>Review transaksi <Icon name="arrow" /></button></div>
    </div></section>
  </>
}

function Field({ label, children }: { label: string; children: ReactNode }) { return <label className="field"><span>{label}</span>{children}</label> }

function StockCard() {
  const [selectedKey, setSelectedKey] = useState<string | null>(null)
  const [skuQuery, setSkuQuery] = useState('')
  const [expandedId, setExpandedId] = useState<string | null>(null)
  const [selectedBrands, setSelectedBrands] = useState([...productBrands])
  const [selectedSizes, setSelectedSizes] = useState([...productSizes])
  const [selectedLocations, setSelectedLocations] = useState([...stockLocations])
  const [selectedGrades, setSelectedGrades] = useState([...stockGrades])
  const visibleSkus = useMemo(() => productCatalog.filter((product) => {
    const matchesQuery = `${product.brand} ${product.code} ${product.range} ${product.name} ${product.color}`.toLowerCase().includes(skuQuery.toLowerCase())
    const matchesSize = product.sizes.some((size) => selectedSizes.includes(size))
    return matchesQuery && selectedBrands.includes(product.brand) && matchesSize && selectedLocations.includes(product.location) && selectedGrades.includes(product.grade)
  }), [skuQuery, selectedBrands, selectedSizes, selectedLocations, selectedGrades])
  const selected = productCatalog.find((product) => productKey(product) === selectedKey)
  const currentStock = selected?.stocks.reduce((sum,qty)=>sum+qty,0) ?? 0
  const productMovements = selected ? initialMovements.filter((movement)=>movementProductKey(movement)===productKey(selected)) : []
  const ledgerMovements = selected ? productMovements.map((movement)=>({ ...movement, balance: movement.balance })) : []

  if (!selected) return <><section className="hero-copy compact"><div className="eyebrow">GUDANG · BARANG JADI</div><h1>Kartu stok FG</h1></section><div className="panel sku-browser"><div className="stock-browser-toolbar"><div className="sku-search-field"><Icon name="search" /><input autoFocus value={skuQuery} onChange={(e)=>setSkuQuery(e.target.value)} placeholder="Cari merek dulu, lalu SKU / model / warna..." /></div><div className="stock-filter-row"><MultiCheckFilter label="Merek" options={productBrands} selected={selectedBrands} onChange={setSelectedBrands}/><MultiCheckFilter label="Size" options={productSizes} selected={selectedSizes} onChange={setSelectedSizes}/><MultiCheckFilter label="Lokasi" options={stockLocations} selected={selectedLocations} onChange={setSelectedLocations}/><MultiCheckFilter label="Grade" options={stockGrades} selected={selectedGrades} onChange={setSelectedGrades}/></div></div><div className="sku-browser-list">{visibleSkus.map((sku)=>{ const total=sku.stocks.reduce((s,q)=>s+q,0); const sequence=productCatalog.findIndex((row)=>productKey(row)===productKey(sku))+1; return <button className="sku-browser-row" key={productKey(sku)} onClick={()=>{setSelectedKey(productKey(sku));setExpandedId(null)}}><span className="sku-sequence">{String(sequence).padStart(2,'0')}</span><div className="sku-browser-name"><span className="brand-chip strong">{sku.brand}</span><strong>{sku.code}</strong><small>{sku.name} · {sku.color}</small></div><span className="range-chip">{sku.range}</span><div className="sku-size-preview">{sku.sizes.map((size,index)=><span key={size}><small>{size}</small><strong>{sku.stocks[index]}</strong><em>{dozenPieces(sku.stocks[index])}</em></span>)}</div><div className="sku-stock-preview"><strong>{total} pcs</strong><small>{dozenPieces(total)}</small></div><Icon name="arrow" /></button>})}</div></div></>

  return <><section className="hero-copy compact"><button className="back-link" onClick={()=>{setSelectedKey(null);setExpandedId(null)}}><Icon name="back" /> Semua SKU</button><div className="eyebrow">GUDANG · BARANG JADI</div><h1>Kartu stok FG</h1></section><div className="panel stock-summary"><div className="stock-summary-main"><div><div className="sku-title"><span className="brand-chip strong">{selected.brand}</span><h2>{selected.code}</h2><span>Range {selected.range}</span></div><p>{selected.name} · {selected.color} · {selected.location}</p></div><div className="stock-size-overview">{selected.sizes.map((size,index)=><div key={size}><span>SIZE {size}</span><strong>{selected.stocks[index]} pcs</strong><small>{dozenPieces(selected.stocks[index])}</small></div>)}</div></div><div className="stock-total-hero"><span>TOTAL STOK AKHIR</span><strong>{currentStock} pcs</strong><small>{dozenPieces(currentStock)}</small></div></div><div className="panel table-panel"><div className="table-toolbar"><div className="search-box compact-search"><Icon name="search" /> Cari ref / pelanggan...</div><button className="soft-btn"><Icon name="calendar" /> 30 hari</button><button className="soft-btn"><Icon name="filter" /> Filter</button></div><div className="responsive-table stock-ledger"><table><thead><tr><th>Waktu fisik</th><th>Transaksi</th><th className="number-head">Masuk</th><th className="number-head">Keluar</th><th className="number-head">Stok akhir</th><th aria-label="Rincian" /></tr></thead><tbody>{ledgerMovements.map((movement)=>{ const masuk=movement.delta.reduce((s,q)=>s+Math.max(0,q),0); const keluar=movement.delta.reduce((s,q)=>s+Math.abs(Math.min(0,q)),0); const stock=movement.balance.reduce((s,q)=>s+q,0); const open=expandedId===movement.id; return <Fragment key={movement.id}><tr className={open?'stock-row-open':''}><td><span className="ledger-date">{movement.date}</span></td><td><div className="ledger-transaction"><div><strong>{movement.ref}</strong><span className="type-pill">{movement.type}</span></div><small>{movement.note}</small></div></td><td className="ledger-number incoming">{masuk>0?`+${masuk}`:'—'}<small>{masuk>0?dozenPieces(masuk):''}</small></td><td className="ledger-number outgoing">{keluar>0?`−${keluar}`:'—'}<small>{keluar>0?dozenPieces(keluar):''}</small></td><td className="ledger-balance"><strong>{stock} pcs</strong><small>{dozenPieces(stock)}</small></td><td><button className="stock-expand" onClick={()=>setExpandedId(open?null:movement.id)}>{open?'−':'+'}</button></td></tr>{open&&<tr className="stock-detail-row"><td colSpan={6}><div className="stock-size-details"><div className="detail-caption"><span>RINCIAN SIZE</span><small>Komposisi transaksi dan saldo sesudah transaksi</small></div>{movement.delta.map((delta,index)=><div className="size-ledger-card" key={index}><span>SIZE {selected.sizes[index]}</span><div><small>{delta>=0?'Masuk':'Keluar'}</small><strong className={delta<0?'neg':delta>0?'pos':''}>{delta>0?'+':delta<0?'−':''}{Math.abs(delta)} pcs</strong></div><div><small>Stok akhir</small><strong>{movement.balance[index]} pcs</strong></div><em>{dozenPieces(movement.balance[index])}</em></div>)}</div></td></tr>}</Fragment>})}</tbody></table></div></div></>
}

function Movements({ bookName, bookBrands, setBookBrands, movements, setMovements }: {
  bookName: string; bookBrands: string[]; setBookBrands: (brands: string[]) => void; movements: Movement[]; setMovements: (m: Movement[]) => void
}) {
  const [draggedId, setDraggedId] = useState<string | null>(null)
  const [movementQuery, setMovementQuery] = useState('')
  const customerOptions = ['Nusantara Fashion','Sumber Denim','Maju Jaya','Tanpa toko']
  const movementTypes = Array.from(new Set(initialMovements.map((movement)=>movement.type)))
  const [selectedCustomers,setSelectedCustomers] = useState([...customerOptions])
  const [selectedTypes,setSelectedTypes] = useState([...movementTypes])

  const moveVisible = (id:string,dir:-1|1,visibleIds:string[]) => { const visibleIndex=visibleIds.indexOf(id); const targetId=visibleIds[visibleIndex+dir]; if(!targetId)return; const next=[...movements]; const from=next.findIndex((m)=>m.id===id); const to=next.findIndex((m)=>m.id===targetId); [next[from],next[to]]=[next[to],next[from]]; setMovements(next) }
  const dropOn = (targetId:string) => { if(!draggedId||draggedId===targetId)return; const from=movements.findIndex((m)=>m.id===draggedId); const to=movements.findIndex((m)=>m.id===targetId); if(from<0||to<0)return; const next=[...movements]; const [picked]=next.splice(from,1); next.splice(to,0,picked); setMovements(next); setDraggedId(null) }

  const finalByProduct = new Map<string, QtyTuple>()
  initialMovements.forEach((movement)=>{ const key=movementProductKey(movement); if(!finalByProduct.has(key)) finalByProduct.set(key,[...movement.balance] as QtyTuple) })
  const totalDeltaByProduct = new Map<string, QtyTuple>()
  movements.forEach((movement)=>{ const key=movementProductKey(movement); const current=totalDeltaByProduct.get(key)??[0,0,0]; totalDeltaByProduct.set(key,current.map((qty,index)=>qty+movement.delta[index]) as QtyTuple) })
  const runningByProduct = new Map<string, QtyTuple>()
  finalByProduct.forEach((final,key)=>{ const delta=totalDeltaByProduct.get(key)??[0,0,0]; runningByProduct.set(key,final.map((qty,index)=>qty-delta[index]) as QtyTuple) })
  const bookRows = movements.map((movement)=>{ const key=movementProductKey(movement); const before=[...(runningByProduct.get(key)??[0,0,0])] as QtyTuple; const after=before.map((qty,index)=>qty+movement.delta[index]) as QtyTuple; runningByProduct.set(key,after); return {...movement,before,after} })
  const visibleRows = bookRows.filter((movement)=>{ const customer=movement.customer??'Tanpa toko'; const product=productCatalog.find((item)=>productKey(item)===movementProductKey(movement)); const matchesQuery=`${movement.brand} ${movement.sku} ${product?.name??''} ${product?.color??''} ${movement.ref} ${movement.note} ${customer}`.toLowerCase().includes(movementQuery.toLowerCase()); return bookBrands.includes(movement.brand)&&matchesQuery&&selectedCustomers.includes(customer)&&selectedTypes.includes(movement.type) })
  const visibleIds=visibleRows.map((movement)=>movement.id)

  return <>
    <section className="hero-copy compact brand-book-hero"><div><div className="eyebrow">GUDANG · BUKU MUTASI FG</div><h1>Buku {bookName}</h1><p>Halaman ini mengikuti buku fisik. Merek yang masuk ke buku bisa diatur tanpa mengubah fakta transaksi.</p></div><div className="book-brand-control"><span>MEREK DALAM BUKU</span><MultiCheckFilter label="Atur merek" options={productBrands} selected={bookBrands} onChange={setBookBrands}/></div></section>
    <div className="panel mutation-panel"><div className="table-toolbar mutation-toolbar"><div className="catalog-search compact-search"><Icon name="search" /><input value={movementQuery} onChange={(e)=>setMovementQuery(e.target.value)} placeholder="Cari merek, SKU, deskripsi, ref, toko..." /></div><MultiCheckFilter label="Toko" options={customerOptions} selected={selectedCustomers} onChange={setSelectedCustomers}/><MultiCheckFilter label="Jenis" options={movementTypes} selected={selectedTypes} onChange={setSelectedTypes}/><button className="soft-btn" onClick={()=>setMovements(chronologicalMovements)}><Icon name="reset" /> Reset urutan</button></div>
      <div className="mutation-list">{visibleRows.map((movement,idx)=>{ const product=productCatalog.find((item)=>productKey(item)===movementProductKey(movement)); const sizes=product?.sizes??['28','29','30']; const movementTotal=movement.delta.reduce((s,q)=>s+q,0); const beforeTotal=movement.before.reduce((s,q)=>s+q,0); const afterTotal=movement.after.reduce((s,q)=>s+q,0); return <div className={`mutation-row ${draggedId===movement.id?'is-dragging':''}`} key={movement.id} draggable onDragStart={()=>setDraggedId(movement.id)} onDragOver={(e)=>e.preventDefault()} onDrop={()=>dropOn(movement.id)} onDragEnd={()=>setDraggedId(null)}><div className="drag-grip" title="Ubah urutan buku"><Icon name="drag" /></div><div className="order-no">{String(idx+1).padStart(2,'0')}</div><div className="mutation-main"><div className="mutation-brand-row"><strong className="mutation-brand">{movement.brand}</strong><span className="type-pill">{movement.type}</span></div><div className="mutation-sku-row"><b>SKU {movement.sku}</b><span>{product ? `${product.name} · ${product.color}` : 'Deskripsi barang'}</span></div><p>{movement.ref} · {movement.customer??movement.note}</p><small>{movement.date} · {movement.id}</small></div><div className="mutation-delta">{movement.delta.map((delta,index)=><span className="size-book-flow" key={index}><small className="size-book-title">SIZE {sizes[index]}</small><div className="book-step opening"><label>Saldo awal</label><strong>{movement.before[index]} pcs</strong><small>{dozenPieces(movement.before[index])}</small></div><div className="book-step change"><label>Mutasi</label><strong className={delta<0?'neg':delta>0?'pos':''}>{delta>0?'+':''}{delta} pcs</strong><small>{dozenPieces(Math.abs(delta))}</small></div><div className="book-step closing"><label>Saldo akhir</label><strong>{movement.after[index]} pcs</strong><small>{dozenPieces(movement.after[index])}</small></div></span>)}</div><div className="mutation-total"><span className="total-book-title">TOTAL {movement.brand} · {movement.sku}</span><div className="total-book-step"><label>Saldo awal</label><strong>{beforeTotal} pcs</strong><small>{dozenPieces(beforeTotal)}</small></div><div className="total-book-step change"><label>Mutasi</label><strong className={movementTotal<0?'neg':'pos'}>{movementTotal>0?'+':''}{movementTotal} pcs</strong><small>{dozenPieces(Math.abs(movementTotal))}</small></div><div className="total-book-step closing"><label>Saldo akhir</label><strong>{afterTotal} pcs</strong><small>{dozenPieces(afterTotal)}</small></div></div><div className="reorder"><button aria-label="Naikkan urutan" onClick={()=>moveVisible(movement.id,-1,visibleIds)} disabled={idx===0}><Icon name="up" /></button><button aria-label="Turunkan urutan" onClick={()=>moveVisible(movement.id,1,visibleIds)} disabled={idx===visibleRows.length-1}><Icon name="down" /></button></div></div>})}{visibleRows.length===0&&<div className="catalog-empty"><Icon name="filter" /><strong>Tidak ada mutasi di buku {bookName}</strong><small>Cek merek yang dipilih atau ubah filter.</small></div>}</div>
    </div>
  </>
}

function Placeholder() { return <div className="panel placeholder"><div className="placeholder-icon">◇</div><h2>Fondasinya sudah disiapkan.</h2><p>Modul ini berikutnya akan mengikuti flow bisnis yang sama: informasi penting terlihat sebelum user menekan tombol yang mengubah uang atau stok.</p></div> }

export default App
