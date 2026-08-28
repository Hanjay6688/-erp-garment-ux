import { Fragment, lazy, Suspense, useEffect, useMemo, useRef, useState } from 'react'
import type { ClipboardEvent as ReactClipboardEvent, CSSProperties, KeyboardEvent as ReactKeyboardEvent, PointerEvent as ReactPointerEvent, ReactNode } from 'react'
import {
  ArrowLeft, ArrowRight, Boxes, CalendarDays, Check, ChevronDown, ChevronUp,
  CircleDollarSign, Database, Factory, FileText, GripVertical, History,
  LayoutDashboard, Layers3, Link2, ListFilter, Menu, Package, Plus, ReceiptText,
  RotateCcw, Ruler, Scissors, Search, ShieldCheck, SlidersHorizontal, Trash2,
  UserRound, WalletCards, Warehouse, X,
} from 'lucide-react'
import type { LucideIcon } from 'lucide-react'
import HppPage from './HppPage'
import type { SalesView } from './SalesPages'
import type { FinanceView } from './FinancePages'
import QcFinalPage from './QcFinalPage'
import type { QcFinalResult, QcSeed } from './QcFinalPage'
import BsReworkPage from './BsReworkPage'
import WarehousePages from './WarehousePages'
import type { WarehouseView } from './WarehousePages'
import type { WipControlMode, WipControlParent, WipControlResult } from './WipBatchControlLayer'
import type { MaterialMasterView } from './MaterialMasterPages'
import { productCatalog } from './productCatalog'
import type { Product } from './productCatalog'

const SalesPages = lazy(() => import('./SalesPages'))
const FinancePages = lazy(() => import('./FinancePages'))
const WipBatchControlLayer = lazy(() => import('./WipBatchControlLayer'))
const ContractorIssuePage = lazy(() => import('./ContractorIssuePage'))
const MaterialMasterPages = lazy(() => import('./MaterialMasterPages'))

type Page = 'dashboard' | 'stock-card' | 'movements-vivo' | 'movements-widie' | 'procurement' | 'cutting-roll' | 'mandor-wip' | 'contractor-issue' | 'sewing-wip' | 'qc' | 'fg-handoff' | 'bs-rework' | 'laundry' | 'hpp' | SalesView | FinanceView | WarehouseView | MaterialMasterView | 'placeholder'
type NavSection = 'Produksi' | 'Gudang' | 'Penjualan' | 'Keuangan' | 'Master Data'
type QtyTuple = [number, number, number]
type SizeTuple = [string, string, string]
type WipAdjustmentHistoryEntry = {
  id: string
  operation: 'REDISTRIBUTION' | 'PHYSICAL_RECOUNT'
  note: string
  at: string
  before: QtyTuple
  after: QtyTuple
}
type ReceiptMode = 'fabric' | 'accessory'
type LaundryView = 'send' | 'return'
type LaundryPrefill = { batchId: string; vendor: string; view: LaundryView }

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

const productKey = (product: Pick<Product, 'brand' | 'code'>) => `${product.brand}::${product.code}`
const movementProductKey = (movement: Pick<Movement, 'brand' | 'sku'>) => `${movement.brand}::${movement.sku}`

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
  const safeCount = Math.max(1, count)
  const loads = Array(safeCount).fill(0) as number[]
  const matrix: AllocationMatrix = Object.fromEntries(cuttingSizes.map((size) => [size, Array(safeCount).fill('0')]))
  cuttingSizes.map((size, sizeIndex) => ({ size, qty: sizeTotals[sizeIndex] })).sort((a, b) => b.qty - a.qty).forEach((source) => {
    const batchIndex = loads.reduce((lightest, load, index, values) => load < values[lightest] ? index : lightest, 0)
    matrix[source.size][batchIndex] = String(source.qty)
    loads[batchIndex] += source.qty
  })
  return matrix
}

function createRollBatchSizeMatrix(rolls: FabricRoll[], count: number): RollBatchSizeMatrix {
  const wholeRollPlan = createRollAllocationMatrix(rolls, count)
  return Object.fromEntries(rolls.map((roll) => {
    const assignedBatch = (wholeRollPlan[roll.id] ?? []).findIndex((value) => cellQuantity(value) > 0)
    const sourceSizes = rollSizeQuantities(roll.allocation)
    return [roll.id, Array.from({ length: count }, (_, batchIndex) => batchIndex === assignedBatch ? sourceSizes.map(String) : ['0', '0', '0'])]
  }))
}

function createEmptyRollBatchSizeMatrix(rolls: FabricRoll[], count: number): RollBatchSizeMatrix {
  const safeCount = Math.max(1, count)
  return Object.fromEntries(rolls.map((roll) => [roll.id, Array.from({ length: safeCount }, () => ['0', '0', '0'])]))
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
  Produksi: ['Buat Potongan', 'Bagi Potongan', 'WIP & Sewing', 'Laundry', 'QC & Final SKU', 'Barang BS & Rework'],
  Gudang: ['Ringkasan Gudang', 'Pembelian & Penerimaan', 'Bahan & Roll', 'Aksesori', 'Ringkasan Barang Jadi', 'Mutasi Barang Jadi · Vivo', 'Mutasi Barang Jadi · Widie', 'Kartu Stok FG', 'Stock Adjustment', 'Ganti Merek'],
  Penjualan: ['Penjualan & Invoice', 'Semua Invoice', 'Retur Penjualan', 'Pembayaran Pelanggan', 'Riwayat Pelanggan'],
  Keuangan: ['Ringkasan Keuangan', 'Kas & Bank', 'Hutang Supplier & Vendor', 'Piutang Pelanggan', 'Payroll & Kasbon', 'Nota Ambil Aksesori', 'HPP & Rekalkulasi', 'Jurnal & Transaksi Lain', 'Laporan & Tutup Buku'],
  'Master Data': ['Kain & Benchmark', 'Aksesori & Harga Mandor', 'Produk & SKU', 'Pelanggan', 'Supplier & Vendor', 'Mandor & Pekerja', 'Gudang & Lokasi'],
}

const salesPageByLabel: Partial<Record<string, SalesView>> = {
  'Penjualan & Invoice': 'sales-invoice',
  'Semua Invoice': 'sales-allocation',
  'Retur Penjualan': 'sales-returns',
  'Pembayaran Pelanggan': 'sales-payments',
  'Riwayat Pelanggan': 'sales-history',
}
const financePageByLabel: Partial<Record<string, FinanceView>> = {
  'Ringkasan Keuangan': 'finance-overview',
  'Kas & Bank': 'finance-cash',
  'Hutang Supplier & Vendor': 'finance-ap',
  'Piutang Pelanggan': 'finance-ar',
  'Payroll & Kasbon': 'finance-payroll',
  'Jurnal & Transaksi Lain': 'finance-journal',
  'Laporan & Tutup Buku': 'finance-reports',
}
const salesViews: SalesView[] = ['sales-invoice','sales-allocation','sales-returns','sales-payments','sales-history']
const financeViews: FinanceView[] = ['finance-overview','finance-cash','finance-ap','finance-ar','finance-payroll','finance-journal','finance-reports']
const isSalesView = (page: Page): page is SalesView => salesViews.includes(page as SalesView)
const isFinanceView = (page: Page): page is FinanceView => financeViews.includes(page as FinanceView)

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
const cleanDecimalInput = (value: string, decimalPlaces = 2) => {
  const compact = value.replace(/\./g, ',').replace(/[^0-9,]/g, '')
  const [rawInteger = '', ...rawDecimals] = compact.split(',')
  const integer = rawInteger.replace(/^0+(?=\d)/, '')
  if (rawDecimals.length === 0) return integer
  return `${integer || '0'},${rawDecimals.join('').slice(0, decimalPlaces)}`
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

const focusKeyboardControl = (element: HTMLElement) => {
  element.focus()
  if (element instanceof HTMLInputElement && !['date','datetime-local','time'].includes(element.type)) element.select()
}

function handleErgonomicKeyboard(event: ReactKeyboardEvent<HTMLDivElement>) {
  if (event.defaultPrevented || event.nativeEvent.isComposing || event.ctrlKey || event.metaKey || event.altKey) return
  const target = event.target
  if (!(target instanceof HTMLInputElement) || target.disabled || target.readOnly || ['checkbox','radio','file','color'].includes(target.type)) return
  if (target.dataset.cuttingRow !== undefined) return

  const grid = target.closest<HTMLElement>('[data-keyboard-grid]')
  const row = Number(target.dataset.gridRow)
  const col = Number(target.dataset.gridCol)
  const gridKey = ['Enter','ArrowDown','ArrowUp','ArrowLeft','ArrowRight'].includes(event.key)
  if (grid && gridKey && Number.isFinite(row) && Number.isFinite(col)) {
    const cells = Array.from(grid.querySelectorAll<HTMLInputElement>('input[data-grid-row][data-grid-col]:not(:disabled):not([readonly])'))
    const parsed = cells.map((cell) => ({ cell, row: Number(cell.dataset.gridRow), col: Number(cell.dataset.gridCol) }))
    let candidate: HTMLInputElement | undefined
    if (event.key === 'ArrowLeft' || event.key === 'ArrowRight') {
      const direction = event.key === 'ArrowLeft' ? -1 : 1
      candidate = parsed.find((item) => item.row === row && item.col === col + direction)?.cell
    } else {
      const direction = event.key === 'ArrowUp' || (event.key === 'Enter' && event.shiftKey) ? -1 : 1
      const sameColumn = parsed.filter((item) => item.col === col && (direction > 0 ? item.row > row : item.row < row)).sort((a,b) => direction > 0 ? a.row-b.row : b.row-a.row)
      candidate = sameColumn[0]?.cell
    }
    if (candidate) {
      event.preventDefault()
      focusKeyboardControl(candidate)
      return
    }
    if (event.key !== 'Enter') return
  }

  if (event.key !== 'Enter') return
  const scope = target.closest<HTMLElement>('[data-keyboard-scope]')
  if (!scope) return
  const controls = Array.from(scope.querySelectorAll<HTMLElement>('input:not(:disabled):not([readonly]):not([type="checkbox"]):not([type="radio"]), select:not(:disabled)'))
    .filter((control) => control.offsetParent !== null)
  const current = controls.indexOf(target)
  const next = controls[current + (event.shiftKey ? -1 : 1)]
  if (!next) return
  event.preventDefault()
  focusKeyboardControl(next)
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
  const [mandorBatchNotes,setMandorBatchNotes] = useState<string[]>([
    'Warna navy · stik pinggang 2 jalur',
    'Warna maroon · obras rapat',
    'Warna hitam · cek sambungan samping',
  ])
  const [laundryPrefill,setLaundryPrefill] = useState<LaundryPrefill|null>(null)
  const [laundryReadyBatches,setLaundryReadyBatches] = useState<LaundryReadyBatch[]>(laundryReadySeeds)
  const [laundryDeliveries,setLaundryDeliveries] = useState<LaundryDelivery[]>(laundryDeliverySeeds)
  const [laundryDrafts,setLaundryDrafts] = useState<Record<string,string>>({})
  const [wipReverseNotice,setWipReverseNotice] = useState<string|null>(null)
  const [qcSeedId,setQcSeedId] = useState('POT-260826-041::041-02')
  const [qcResult,setQcResult] = useState<QcFinalResult|null>(null)
  const [finalizedQcResults,setFinalizedQcResults] = useState<QcFinalResult[]>([])
  const [bsPrefill,setBsPrefill] = useState<QcFinalResult|null>(null)

  useEffect(()=>{
    window.scrollTo({top:0,left:0,behavior:'auto'})
  },[page])

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
    : page === 'sales-invoice' ? 'Penjualan & Invoice'
    : page === 'sales-allocation' ? 'Semua Invoice'
    : page === 'sales-returns' ? 'Retur Penjualan'
    : page === 'sales-payments' ? 'Pembayaran Pelanggan'
    : page === 'sales-history' ? 'Riwayat Pelanggan'
    : page === 'finance-overview' ? 'Ringkasan Keuangan'
    : page === 'finance-cash' ? 'Kas & Bank'
    : page === 'finance-ap' ? 'Hutang Supplier & Vendor'
    : page === 'finance-ar' ? 'Piutang Pelanggan'
    : page === 'finance-payroll' ? 'Payroll & Kasbon'
    : page === 'finance-journal' ? 'Jurnal & Transaksi Lain'
    : page === 'finance-reports' ? 'Laporan & Tutup Buku'
    : page === 'stock-card' ? 'Kartu Stok FG'
    : page === 'movements-vivo' ? 'Mutasi Barang Jadi · Vivo'
    : page === 'movements-widie' ? 'Mutasi Barang Jadi · Widie'
    : page === 'procurement' ? 'Pembelian & Penerimaan'
    : page === 'cutting-roll' ? 'Buat Potongan'
    : page === 'mandor-wip' ? 'Bagi Potongan'
    : page === 'contractor-issue' ? 'Nota Ambil Aksesori'
    : page === 'sewing-wip' ? 'WIP & Sewing'
    : page === 'qc' ? 'QC & Final SKU'
    : page === 'fg-handoff' ? 'Serah FG & Susun Nota FG'
    : page === 'bs-rework' ? 'Barang BS & Rework'
    : page === 'laundry' ? 'Laundry'
    : page === 'hpp' ? 'HPP & Rekalkulasi'
    : page === 'warehouse-dashboard' ? 'Ringkasan Gudang'
    : page === 'materials-rolls' ? 'Bahan & Roll'
    : page === 'accessories' ? 'Aksesori'
    : page === 'fg-summary' ? 'Ringkasan Barang Jadi'
    : page === 'stock-adjustment' ? 'Stock Adjustment'
    : page === 'brand-conversion' ? 'Ganti Merek'
    : page === 'master-fabric' ? 'Kain & Benchmark'
    : page === 'master-accessory' ? 'Aksesori & Harga Mandor'
    : 'Modul ERP'

  const chooseSubmenu = (label: string) => {
    const salesTarget=salesPageByLabel[label]
    const financeTarget=financePageByLabel[label]
    if (salesTarget) setPage(salesTarget)
    else if (financeTarget) setPage(financeTarget)
    else if (label === 'Kartu Stok FG') setPage('stock-card')
    else if (label === 'Mutasi Barang Jadi · Vivo') setPage('movements-vivo')
    else if (label === 'Mutasi Barang Jadi · Widie') setPage('movements-widie')
    else if (label === 'Pembelian & Penerimaan') setPage('procurement')
    else if (label === 'Ringkasan Gudang') setPage('warehouse-dashboard')
    else if (label === 'Bahan & Roll') setPage('materials-rolls')
    else if (label === 'Aksesori') setPage('accessories')
    else if (label === 'Ringkasan Barang Jadi') setPage('fg-summary')
    else if (label === 'Stock Adjustment') setPage('stock-adjustment')
    else if (label === 'Ganti Merek') setPage('brand-conversion')
    else if (label === 'Buat Potongan') setPage('cutting-roll')
    else if (label === 'Bagi Potongan') setPage('mandor-wip')
    else if (label === 'Nota Ambil Aksesori') setPage('contractor-issue')
    else if (label === 'WIP & Sewing') setPage('sewing-wip')
    else if (label === 'Laundry') { setLaundryPrefill(null); setPage('laundry') }
    else if (label === 'QC & Final SKU') {
      setPage('qc')
    }
    else if (label === 'Barang BS & Rework') { setBsPrefill(null); setPage('bs-rework') }
    else if (label === 'HPP & Rekalkulasi') setPage('hpp')
    else if (label === 'Kain & Benchmark') setPage('master-fabric')
    else if (label === 'Aksesori & Harga Mandor') setPage('master-accessory')
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
          const salesTarget=salesPageByLabel[item]
          const financeTarget=financePageByLabel[item]
          const active = (salesTarget !== undefined && page === salesTarget) || (financeTarget !== undefined && page === financeTarget) || (item === 'Kartu Stok FG' && page === 'stock-card') || (item === 'Mutasi Barang Jadi · Vivo' && page === 'movements-vivo') || (item === 'Mutasi Barang Jadi · Widie' && page === 'movements-widie') || (item === 'Pembelian & Penerimaan' && page === 'procurement') || (item === 'Ringkasan Gudang' && page === 'warehouse-dashboard') || (item === 'Bahan & Roll' && page === 'materials-rolls') || (item === 'Aksesori' && page === 'accessories') || (item === 'Ringkasan Barang Jadi' && page === 'fg-summary') || (item === 'Stock Adjustment' && page === 'stock-adjustment') || (item === 'Ganti Merek' && page === 'brand-conversion') || (item === 'Buat Potongan' && page === 'cutting-roll') || (item === 'Bagi Potongan' && page === 'mandor-wip') || (item === 'Nota Ambil Aksesori' && page === 'contractor-issue') || (item === 'WIP & Sewing' && page === 'sewing-wip') || (item === 'QC & Final SKU' && (page === 'qc' || page === 'fg-handoff')) || (item === 'Barang BS & Rework' && page === 'bs-rework') || (item === 'Laundry' && page === 'laundry') || (item === 'HPP & Rekalkulasi' && page === 'hpp') || (item === 'Kain & Benchmark' && page === 'master-fabric') || (item === 'Aksesori & Harga Mandor' && page === 'master-accessory')
          return <button key={item} className={active ? 'sub-active' : ''} onClick={() => chooseSubmenu(item)}>• {item}</button>
        })}</div>}
      </div>)}
      <div className="sidebar-spacer" />
      <button className="nav-main"><Icon name="audit" /><span>Pengaturan & Audit</span><span className="chevron">›</span></button>
      <div className="env-card"><div className="env-dot" /><div><strong>ERP Enteng</strong><span>Target dev · UX alpha</span></div></div>
    </aside>

    <main className="main-panel">
      <header className="topbar"><button className="mobile-menu" onClick={() => setMobileNav(true)}><Icon name="menu" /></button><div className="top-title"><div className="top-icon"><Icon name="dashboard" /></div><div><strong>{title}</strong><span>{page === 'dashboard' ? 'Satu layar untuk keputusan hari ini' : 'Cepat, jelas, dan aman buat operasional'}</span></div></div><div className="top-actions"><button className="sim-badge"><span /> DATA SIMULASI</button><button className="round-btn"><Icon name="search" /></button><div className="owner"><span>OH</span><div><strong>Owner</strong><small>Administrator</small></div><b>⌄</b></div></div></header>
      <div className="page-wrap" data-keyboard-scope onKeyDown={handleErgonomicKeyboard}>
        {page === 'dashboard' && <Dashboard onOpenSales={() => setPage('sales-invoice')} />}
        {isSalesView(page) && <Suspense fallback={<WorkspaceFallback label="Penjualan"/>}><SalesPages view={page} onNavigate={(next)=>setPage(next)} /></Suspense>}
        {isFinanceView(page) && <Suspense fallback={<WorkspaceFallback label="Keuangan"/>}><FinancePages view={page} onNavigate={(next)=>setPage(next)} onSalesPayment={()=>setPage('sales-payments')} /></Suspense>}
        {page === 'stock-card' && <StockCard />}
        {page === 'movements-vivo' && <Movements bookName="Vivo" bookBrands={vivoBookBrands} setBookBrands={setVivoBookBrands} movements={movements} setMovements={setMovements} />}
        {page === 'movements-widie' && <Movements bookName="Widie" bookBrands={widieBookBrands} setBookBrands={setWidieBookBrands} movements={movements} setMovements={setMovements} />}
        {page === 'procurement' && <ProcurementPage />}
        {(page === 'warehouse-dashboard' || page === 'materials-rolls' || page === 'accessories' || page === 'fg-summary' || page === 'stock-adjustment' || page === 'brand-conversion') && <WarehousePages view={page} onNavigate={(next)=>setPage(next)} />}
        {page === 'cutting-roll' && <CuttingRollPage />}
        {page === 'mandor-wip' && <MandorWipPage batchNotes={mandorBatchNotes} setBatchNotes={setMandorBatchNotes} />}
        {page === 'contractor-issue' && <Suspense fallback={<WorkspaceFallback label="Nota Ambil Aksesori"/>}><ContractorIssuePage/></Suspense>}
        {page === 'sewing-wip' && <SewingWipPage
          batchNotes={mandorBatchNotes}
          deliveries={laundryDeliveries}
          laundryDrafts={laundryDrafts}
          reverseNotice={wipReverseNotice}
          onClearReverseNotice={()=>setWipReverseNotice(null)}
          onClearLaundryDraft={(batchId)=>{
            setLaundryDrafts((current)=>{const next={...current};delete next[batchId];return next})
            setLaundryReadyBatches((current)=>current.filter((batch)=>batch.id!==batchId))
          }}
          onConfirmLaundry={(batchId,vendor,snapshot)=>{
            setLaundryDrafts((current)=>({...current,[batchId]:vendor}))
            setLaundryReadyBatches((current)=>{
              const existing=current.find((batch)=>batch.id===batchId)
              if(existing)return current.map((batch)=>batch.id===batchId?{...batch,vendor,...snapshot}:batch)
              const restored=laundryReadyFromSewingBatch(batchId,vendor,snapshot)
              return restored?[restored,...current]:current
            })
            setLaundryPrefill({batchId,vendor,view:'send'})
            setWipReverseNotice(null)
            setPage('laundry')
          }}
          onOpenLaundry={(batchId,vendor,view)=>{setLaundryPrefill({batchId,vendor,view});setPage('laundry')}}
          onOpenQc={(parentId,batchId)=>{
            const parent=sewingWipSeeds.find((item)=>item.id===parentId)
            const batch=parent?.batches.find((item)=>item.id===batchId)
            if(!parent||!batch)return
            setQcSeedId(`${parentId}::${batchId}`)
            setPage('qc')
          }}
        />}
        {page === 'qc' && <QcFinalPage seeds={buildQcSeeds(laundryDeliveries)} initialSeedId={qcSeedId} finalizedResults={finalizedQcResults} onBack={()=>setPage('sewing-wip')} onFinish={(result)=>{setFinalizedQcResults((current)=>{const key=`${result.parentId}::${result.batchId}`;return current.some((item)=>`${item.parentId}::${item.batchId}`===key)?current.map((item)=>`${item.parentId}::${item.batchId}`===key?result:item):[result,...current]});setQcResult(result)}} onOpenNota={(result)=>{setQcResult(result);setPage('fg-handoff')}} />}
        {page === 'fg-handoff' && qcResult && <FgPayrollHandoffPage result={qcResult} eligibleResults={finalizedQcResults} onBack={()=>{setQcSeedId(`${qcResult.parentId}::${qcResult.batchId}`);setPage('qc')}} onOpenBs={()=>{setBsPrefill(qcResult);setPage('bs-rework')}} />}
        {page === 'bs-rework' && <BsReworkPage initialResult={bsPrefill} onBack={()=>setPage(bsPrefill?'fg-handoff':'sewing-wip')} />}
        {page === 'laundry' && <LaundryPage
          prefill={laundryPrefill}
          readyBatches={laundryReadyBatches}
          setReadyBatches={setLaundryReadyBatches}
          deliveries={laundryDeliveries}
          setDeliveries={setLaundryDeliveries}
          onPosted={(batchIds)=>setLaundryDrafts((current)=>{const next={...current};batchIds.forEach((batchId)=>delete next[batchId]);return next})}
          onReturnToWip={(batchId,vendor,qty)=>{
            setLaundryDrafts((current)=>{const next={...current};delete next[batchId];return next})
            setWipReverseNotice(`Batch ${batchId} · ${qty} pcs kembali dari ${vendor}. Pilih laundry baru.`)
            setPage('sewing-wip')
          }}
          onOpenQc={(parentId,batchId)=>{setQcSeedId(`${parentId}::${batchId}`);setQcResult(null);setPage('qc')}}
        />}
        {page === 'hpp' && <HppPage />}
        {(page === 'master-fabric' || page === 'master-accessory') && <Suspense fallback={<WorkspaceFallback label="Master Material"/>}><MaterialMasterPages view={page}/></Suspense>}
        {page === 'placeholder' && <Placeholder />}
      </div>
    </main>
  </div>
}

function WorkspaceFallback({ label }: { label: string }) {
  return <div className="panel placeholder"><div className="placeholder-icon">◇</div><h2>Menyiapkan {label}…</h2><p>Memuat workspace dan guardrail transaksi.</p></div>
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
          <div className="roll-entry-list" data-keyboard-grid>{rolls.map((roll,index)=><div className="roll-entry-row" key={roll.id}><span className="roll-number">{String(index+1).padStart(2,'0')}</span><div><label htmlFor={`roll-${roll.id}`}>Yard pada gulung</label><div className="yard-input"><input id={`roll-${roll.id}`} data-grid-row={index} data-grid-col={0} inputMode="decimal" value={roll.yards} placeholder="0" onChange={(event)=>updateRoll(roll.id,event.target.value)}/><span>yd</span></div></div><small>{parseDecimal(roll.yards)>0?`${formatQuantity(parseDecimal(roll.yards))} yard siap diterima`:'Belum diisi'}</small><button className="remove-roll" aria-label={`Hapus roll ${index+1}`} onClick={()=>removeRoll(roll.id)} disabled={rolls.length===1}><Icon name="trash"/></button></div>)}</div>
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
  const [rollYardUsage,setRollYardUsage]=useState<Record<string,string>>(()=>Object.fromEntries(fabricRollCatalog.map((roll)=>[roll.id,String(roll.yards).replace('.',',')])))
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
  const rollUsageRows=selectedRolls.map((roll)=>{
    const input=rollYardUsage[roll.id]??''
    const used=parseDecimal(input)
    const valid=input.trim()!==''&&used>0&&used<=roll.yards
    return {roll,input,used,balance:Math.max(0,roll.yards-used),valid,partial:valid&&used<roll.yards}
  })
  const totalSourceYards=selectedRolls.reduce((sum,roll)=>sum+roll.yards,0)
  const totalUsedYards=rollUsageRows.reduce((sum,row)=>sum+(row.valid?row.used:0),0)
  const totalBalanceYards=rollUsageRows.reduce((sum,row)=>sum+(row.valid?row.balance:row.roll.yards),0)
  const yardUsageValid=rollUsageRows.length>0&&rollUsageRows.every((row)=>row.valid)
  const partialRollCount=rollUsageRows.filter((row)=>row.partial).length
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
  const updateRollYardUsage=(rollId:string,value:string)=>setRollYardUsage((current)=>({...current,[rollId]:cleanDecimalInput(value)}))
  const useFullRoll=(roll:FabricRoll)=>setRollYardUsage((current)=>({...current,[roll.id]:String(roll.yards).replace('.',',')}))
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
    <section className="hero-copy compact cutting-hero"><div className="eyebrow">PRODUKSI · CUTTING</div><h1>Buat Potongan</h1><p>Ambil roll, catat hasil potong per roll dan size, lalu simpan sebagai WIP Potongan. Batch mandor belum dibuat di tahap ini.</p></section>
    <section className="cutting-flow-rail panel" aria-label="Alur Buat Potongan">{['Pilih roll','Tentukan yard used','Catat hasil per roll','Simpan ke WIP'].map((label,index)=><div className={index===0?'active':''} key={label}><span>{String(index+1).padStart(2,'0')}</span><strong>{label}</strong>{index<3&&<Icon name="arrow"/>}</div>)}</section>
    <section className="roll-first-layout">
      <div className="panel roll-catalog-panel">
        <div className="cutting-panel-head"><div><span>01 · SUMBER KAIN</span><h2>Pilih roll yang mau dibagi</h2><p>Satu roll tetap satu baris. Urutan dan yard asal tidak digabung.</p></div><span className="selection-pill">{selectedRolls.length} dipilih</span></div>
        <div className="roll-catalog-toolbar"><div className="roll-search"><Icon name="search"/><input value={query} onChange={(event)=>setQuery(event.target.value)} placeholder="Cari roll, pabrik, bahan, atau yard..."/></div><div className="roll-filters"><MultiCheckFilter label="Pabrik" options={fabricRollSuppliers} selected={selectedSuppliers} onChange={setSelectedSuppliers}/><MultiCheckFilter label="Bahan" options={fabricRollMaterials} selected={selectedMaterials} onChange={setSelectedMaterials}/></div></div>
        <div className="roll-list-caption"><span>{visibleRolls.length} roll tersedia</span><button type="button" onClick={toggleVisible}>{allVisibleSelected?'Batalkan hasil tampil':'Pilih semua hasil'}</button></div>
        <div className="cutting-roll-list">{visibleRolls.map((roll)=>{const selected=selectedIdSet.has(roll.id);return <button type="button" aria-pressed={selected} className={`stock-roll-row ${selected?'selected':''}`} key={roll.id} onClick={()=>toggleRoll(roll.id)}><span className="roll-select-box">{selected&&<Icon name="check"/>}</span><span className="stock-roll-seq">{String(roll.sequence).padStart(2,'0')}</span><span className="stock-roll-name"><strong>{roll.material}</strong><small>{roll.supplier} · {roll.id} · masuk {roll.receivedAt}</small></span><span className="stock-roll-yard"><strong>{formatQuantity(roll.yards,2)} yd</strong><small>{selected?'Masuk pembagian':'Siap dipilih'}</small></span></button>})}{visibleRolls.length===0&&<div className="catalog-empty"><Icon name="search"/><strong>Roll tidak ditemukan</strong><small>Periksa pencarian atau pilihan filter pabrik dan bahan.</small></div>}</div>
      </div>
      <aside className="panel cutting-live-summary">
        <div className="eyebrow">BATCH PRODUKSI</div><h2>Kulot Lucy · 31–33</h2><p>Hasil cutting ini belum didistribusikan ke batch Mandor.</p>
        <div className="cutting-summary-main"><div><span>YARD USED</span><strong>{formatQuantity(totalUsedYards,2)} yd</strong><small>{selectedRolls.length} roll · {partialRollCount} split</small></div><div><span>TOTAL POTONGAN</span><strong>{totalPieces} pcs</strong><small>{dozenPieces(totalPieces)}</small></div></div>
        <div className="cutting-summary-sizes">{cuttingSizes.map((size,index)=><div key={size}><span>SIZE {size}</span><strong>{sizeTotals[index]} pcs</strong><small>{dozenPieces(sizeTotals[index])}</small></div>)}</div>
        <div className="po-preview"><Icon name="warehouse"/><div><strong>Tujuan berikutnya: WIP Potongan</strong><span>Setelah disimpan, hasil ini menunggu mandor mengambil. Pembagian batch dilakukan saat pickup.</span></div></div>
        <button type="button" className="primary-btn cutting-next" disabled={selectedRolls.length===0} onClick={()=>document.getElementById('roll-issue-workbench')?.scrollIntoView({behavior:'smooth',block:'start'})}>Atur yard yang dipakai <Icon name="arrow"/></button>
      </aside>
    </section>
    <section className="panel roll-issue-workbench" id="roll-issue-workbench" data-keyboard-scope>
      <div className="cutting-panel-head roll-issue-head"><div><span>02 · YARD USED PER ROLL</span><h2>Pakai seluruh roll atau ambil sebagian</h2><p>Default-nya satu roll dipakai utuh. Kalau hanya dipakai sebagian, masukkan yard aktual; sisanya tetap menjadi Stock On Hand pada nomor roll yang sama.</p></div><span className={yardUsageValid?'issue-ready-pill':'issue-error-pill'}>{yardUsageValid?'Siap dipotong':'Periksa yard'}</span></div>
      <div className="roll-issue-rule"><Icon name="audit"/><div><strong>Golden rule: whole roll first</strong><span>Split hanya saat memang dibutuhkan di lapangan. Identitas roll tidak berubah dan total yard harus tetap rekonsiliasi.</span></div></div>
      <div className="roll-issue-table-head"><span>ROLL SOURCE</span><span>STOCK ON HAND</span><span>USED FOR CUTTING</span><span>REMAINING</span><span>STATUS</span></div>
      <div className="roll-issue-list" data-keyboard-grid>{rollUsageRows.map(({roll,input,used,balance,valid,partial},index)=><article className={`${valid?'':'invalid'} ${partial?'partial':''}`} key={roll.id}>
        <div className="roll-issue-identity"><span>{String(index+1).padStart(2,'0')}</span><div><strong>{roll.id} · {roll.material}</strong><small>{roll.supplier} · masuk {roll.receivedAt}</small></div></div>
        <div className="roll-issue-number"><small>STOCK ON HAND</small><strong>{formatQuantity(roll.yards,2)} yd</strong></div>
        <label className="roll-used-input"><span>USED FOR CUTTING</span><div><input data-grid-row={index} data-grid-col={0} inputMode="decimal" value={input} placeholder="0" aria-invalid={!valid} onFocus={(event)=>event.currentTarget.select()} onChange={(event)=>updateRollYardUsage(roll.id,event.target.value)}/><b>yd</b></div></label>
        <div className="roll-issue-number remaining"><small>REMAINING</small><strong>{valid?formatQuantity(balance,2):'—'} yd</strong></div>
        <div className="roll-issue-state"><em className={!valid?'error':partial?'split':'whole'}>{!valid?'INVALID':partial?'SPLIT':'WHOLE ROLL'}</em><button type="button" disabled={valid&&!partial&&used===roll.yards} onClick={()=>useFullRoll(roll)}>Use full roll</button></div>
      </article>)}{selectedRolls.length===0&&<div className="allocation-empty"><Icon name="ruler"/><strong>Belum ada roll dipilih</strong><small>Pilih roll pada Browse Roll di atas.</small></div>}</div>
      <div className="roll-issue-footer"><div><span>SOURCE SELECTED<strong>{formatQuantity(totalSourceYards,2)} yd</strong></span><i>−</i><span>USED<strong>{formatQuantity(totalUsedYards,2)} yd</strong></span><i>=</i><span className="remaining">REMAINING<strong>{formatQuantity(totalBalanceYards,2)} yd</strong></span></div><button type="button" className="primary-btn" disabled={!yardUsageValid} onClick={()=>document.getElementById('allocation-workbench')?.scrollIntoView({behavior:'smooth',block:'start'})}>Lanjut catat hasil <Icon name="arrow"/></button></div>
    </section>
    <section className="panel allocation-workbench" id="allocation-workbench">
      <div className="cutting-panel-head allocation-head"><div><span>03 · HASIL POTONG PER ROLL</span><h2>Susun slot size sesuai gambar hari ini</h2><p>Satu size boleh punya satu, dua, tiga, atau lebih slot. Label gambar hanya muncul kalau size tersebut berulang.</p></div><span className="draft-pill">Draft</span></div>
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
          <div className="allocation-roll-identity"><span>{String(index+1).padStart(2,'0')}</span><div><strong>Roll {String(roll.sequence).padStart(2,'0')} · {roll.material}</strong><small>{formatQuantity(rollUsageRows[index]?.used??0,2)} yd used · {formatQuantity(rollUsageRows[index]?.balance??roll.yards,2)} yd remaining</small></div></div>
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
        <div><span>04 · SIMPAN HASIL CUTTING</span><h2>Masuk WIP Produksi, belum menjadi Batch Distribusi</h2><p>Jejak roll, yard issued, sisa roll, dan size tetap melekat pada Batch Produksi. Mandor serta Batch Distribusi baru dicatat saat fisik benar-benar diambil.</p></div>
        <div className="cutting-wip-card"><span className="wip-state-dot"/><div><small>STATUS SETELAH DISIMPAN</small><strong>Menunggu mandor mengambil</strong><span>{selectedRolls.length} roll · {formatQuantity(totalUsedYards,2)} yd used · {totalPieces} pcs</span></div></div>
      </section>
      <div className="allocation-footer"><small>Frontend simulasi · belum mengurangi stok roll atau mencatat WIP di backend.</small><div><button type="button" className="soft-btn">Simpan draft cutting</button><button type="button" className="primary-btn" disabled={!yardUsageValid||totalPieces===0}>Simpan Potongan ke WIP <Icon name="arrow"/></button></div></div>
    </section>
  </>
}

function MandorWipPage({ batchNotes, setBatchNotes }: { batchNotes: string[]; setBatchNotes: (updater: (current: string[]) => string[]) => void }) {
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
  const [rollBatchMatrix,setRollBatchMatrix] = useState<RollBatchSizeMatrix>(() => createEmptyRollBatchSizeMatrix(wipRolls, 3))
  const [sizeMatrix,setSizeMatrix] = useState<AllocationMatrix>(() => createSizeAllocationMatrix(wipSizeTotals, 3))
  const [rollAllocationTouched,setRollAllocationTouched] = useState(false)
  const [sizeAllocationTouched,setSizeAllocationTouched] = useState(false)
  const [batchResizeMessage,setBatchResizeMessage] = useState('')
  const [splitEditorRollId,setSplitEditorRollId] = useState<string | null>(null)
  const [allocationMessage,setAllocationMessage] = useState('')
  const [rollDrag,setRollDrag] = useState<{ rollId: string; target: number | null; x: number; y: number } | null>(null)
  const rollDragRef = useRef<{ rollId: string; target: number | null; x: number; y: number } | null>(null)
  const effectiveBatchCount = batchCount
  const targetTotals = balancedBatchTargets(wipTotal, batchCount)
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
  const unassignedRollRows = wipRollRows.filter((row) => (rollBatchMatrix[row.roll.id] ?? []).every((sizes) => sizes.reduce((sum, value) => sum + cellQuantity(value), 0) === 0))
  const resizeBatchCount = (requestedCount: number) => {
    const nextCount = Math.max(1, Math.round(requestedCount || 1))
    if (nextCount === batchCount) {
      setBatchCountInput(String(batchCount))
      setBatchResizeMessage('Jumlah batch tidak berubah; pembagian lu tetap aman.')
      return
    }
    if (nextCount < batchCount) {
      const removedIndexes = Array.from({ length: batchCount - nextCount }, (_, index) => nextCount + index)
      const rollBlocked = rollAllocationTouched && removedIndexes.some((batchIndex) => wipRollRows.some((row) => (rollBatchMatrix[row.roll.id]?.[batchIndex] ?? []).some((value) => cellQuantity(value) > 0)))
      const sizeBlocked = sizeAllocationTouched && removedIndexes.some((batchIndex) => cuttingSizes.some((size) => cellQuantity(sizeMatrix[size]?.[batchIndex]) > 0))
      if (rollBlocked || sizeBlocked) {
        const blockedModes = [rollBlocked ? 'Per Roll' : '', sizeBlocked ? 'Per Size' : ''].filter(Boolean).join(' & ')
        setBatchCountInput(String(batchCount))
        setBatchResizeMessage(`Tidak bisa hapus: batch terakhir masih berisi pembagian ${blockedModes}. Pindahkan atau kosongkan dulu.`)
        return
      }
    }
    setRollBatchMatrix((current) => {
      const currentHasQuantity = wipRolls.some((roll) => (current[roll.id] ?? []).some((sizes) => sizes.some((value) => cellQuantity(value) > 0)))
      if (nextCount === 1 && !currentHasQuantity) return createRollBatchSizeMatrix(wipRolls, 1)
      return Object.fromEntries(wipRolls.map((roll) => {
        const currentBatches = current[roll.id] ?? []
        const resized = Array.from({ length: nextCount }, (_, batchIndex) => currentBatches[batchIndex] ? [...currentBatches[batchIndex]] : ['0', '0', '0'])
        return [roll.id, resized]
      }))
    })
    setSizeMatrix((current) => sizeAllocationTouched
      ? Object.fromEntries(cuttingSizes.map((size) => [size, Array.from({ length: nextCount }, (_, batchIndex) => current[size]?.[batchIndex] ?? '0')]))
      : createSizeAllocationMatrix(wipSizeTotals, nextCount))
    setBatchNotes((current) => Array.from({ length: nextCount }, (_, batchIndex) => current[batchIndex] ?? ''))
    setBatchCountInput(String(nextCount))
    setBatchCount(nextCount)
    setSplitEditorRollId(null)
    setAllocationMessage('')
    setBatchResizeMessage(nextCount > batchCount ? `Batch ${String(nextCount).padStart(2, '0')} ditambahkan; isi lama tetap di tempatnya.` : 'Batch terakhir yang kosong sudah dihapus; isi lain tetap aman.')
  }
  const applyBatchCount = () => resizeBatchCount(Number(batchCountInput))
  const selectAllocationMode = (nextMode: WipAllocationMode) => {
    if (nextMode === allocationMode) return
    setSplitEditorRollId(null)
    setAllocationMessage('')
    setAllocationMode(nextMode)
  }
  const updateSplitAllocation = (rollId: string, batchIndex: number, sizeIndex: number, rawValue: string) => {
    if (/[+-]/.test(rawValue)) {
      setAllocationMessage('Gunakan jumlah absolut. +/− adalah koreksi sumber, bukan pembagian batch.')
      return
    }
    const digits = rawValue.replace(/[^0-9]/g, '')
    const normalized = digits.replace(/^0+(?=\d)/, '')
    setAllocationMessage('')
    setRollAllocationTouched(true)
    setRollBatchMatrix((current) => {
      const rollBatches = (current[rollId] ?? Array.from({ length: batchCount }, () => ['0', '0', '0'])).map((sizes) => [...sizes])
      rollBatches[batchIndex][sizeIndex] = normalized
      return { ...current, [rollId]: rollBatches }
    })
  }
  const updateSizeAllocation = (size: string, batchIndex: number, rawValue: string) => {
    if (/[+-]/.test(rawValue)) {
      setAllocationMessage('Gunakan jumlah absolut. Pindahkan qty antarbatch tanpa mengubah sumber size.')
      return
    }
    const digits = rawValue.replace(/[^0-9]/g, '')
    const normalized = digits.replace(/^0+(?=\d)/, '')
    setAllocationMessage('')
    setSizeAllocationTouched(true)
    setSizeMatrix((current) => ({
      ...current,
      [size]: (current[size] ?? Array(batchCount).fill('0')).map((value, index) => index === batchIndex ? normalized : value),
    }))
  }
  const assignWholeRoll = (rollId: string, targetBatch: number) => {
    const sourceRow = wipRollRows.find((row) => row.roll.id === rollId)
    if (!sourceRow) return
    setRollBatchMatrix((current) => ({
      ...current,
      [rollId]: Array.from({ length: batchCount }, (_, batchIndex) => batchIndex === targetBatch ? sourceRow.sizes.map(String) : ['0', '0', '0']),
    }))
    setRollAllocationTouched(true)
    setAllocationMessage('')
  }
  const unassignRoll = (rollId: string) => {
    setRollBatchMatrix((current) => ({ ...current, [rollId]: Array.from({ length: batchCount }, () => ['0', '0', '0']) }))
    setRollAllocationTouched(true)
    if (splitEditorRollId === rollId) setSplitEditorRollId(null)
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
    setRollAllocationTouched(true)
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
  const pickupReviewAt = pickupAt ? new Intl.DateTimeFormat('id-ID', { day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit', hour12: false }).format(new Date(pickupAt)) : 'Belum diisi'

  return <>
    <section className="hero-copy compact cutting-hero"><div className="eyebrow">PRODUKSI · PICKUP MANDOR</div><h1>Bagi Potongan</h1><p>Pilih Potongan yang sudah selesai cutting. Setelah mandor mengambil, baru bentuk batch kerja dan beri arahan jahitan atau warna untuk setiap batch.</p></section>
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
          <div className="batch-builder-copy"><span>03 · BENTUK BATCH SETELAH PICKUP</span><h2>Mau dibuat menjadi berapa batch?</h2><p>{allocationMode==='roll'?'Satu batch juga boleh. Setelah diterapkan, tarik roll yang belum ditempatkan ke batch tujuan.':'Jumlah batch bebas. Sistem hanya menyusun awal berdasarkan size; setelah itu angkanya tetap bisa lu atur sendiri.'}</p></div>
          <div className="batch-count-control"><label><span>JUMLAH BATCH · MINIMAL 1</span><div><input type="text" pattern="[0-9]*" inputMode="numeric" value={batchCountInput} onFocus={(event)=>event.currentTarget.select()} onChange={(event)=>setBatchCountInput(event.target.value.replace(/[^0-9]/g,'').replace(/^0+(?=\d)/,''))}/><b>batch</b></div></label><div className="batch-count-buttons"><button type="button" aria-label="Hapus batch terakhir" disabled={batchCount<=1} onClick={()=>resizeBatchCount(batchCount-1)}>−</button><button type="button" aria-label="Tambah satu batch" onClick={()=>resizeBatchCount(batchCount+1)}>+</button><button type="button" className="soft-btn" onClick={applyBatchCount}>Terapkan</button></div>{batchResizeMessage&&<small className={batchResizeMessage.startsWith('Tidak bisa')?'warn':'success'}>{batchResizeMessage}</small>}</div>
        </section>

        <div className="wip-allocation-mode" role="group" aria-label="Dasar pembagian batch">
          <button type="button" className={allocationMode==='roll'?'active':''} aria-pressed={allocationMode==='roll'} onClick={()=>selectAllocationMode('roll')}><Icon name="boxes"/><div><span>UTAMA</span><strong>Drag per roll</strong><small>Bagi per roll; kalau bisa jangan dipisah.</small></div></button>
          <button type="button" className={allocationMode==='size'?'active':''} aria-pressed={allocationMode==='size'} onClick={()=>selectAllocationMode('size')}><Icon name="ruler"/><div><span>AWAL PER SIZE</span><strong>Kelompokkan dari size</strong><small>Jumlah batch dan isi akhirnya tetap bebas.</small></div></button>
        </div>

        <div className="wip-reconcile-strip">
          <div><span>SUMBER POTONGAN · TERKUNCI</span><strong>{wipTotal} pcs</strong><small>{cuttingSizes.map((size,index)=>`${size}: ${wipSizeTotals[index]}`).join(' · ')}</small></div>
          <div className={assignedTotal===wipTotal?'success':'warn'}><span>SUDAH DIBAGI</span><strong>{assignedTotal} pcs</strong><small>{effectiveBatchCount} batch · angka absolut</small></div>
          <div className={remainingTotal===0&&sourcesExact?'success':'warn'}><span>SISA / SELISIH</span><strong>{remainingTotal===0&&sourcesExact?'0 pcs · Pas':remainingTotal>0?`${remainingTotal} pcs tersisa`:`${Math.abs(remainingTotal)} pcs berlebih`}</strong><small>{sourcesExact?'Semua sumber cocok':'Ada roll atau size yang tidak cocok'}</small></div>
        </div>

        {allocationMode==='roll'?<div className="golden-roll-rule"><Icon name="boxes"/><div><span>GOLDEN RULE</span><strong>Bagi per roll kalau bisa jangan dipisah</strong><small>{wholeRolls.length} roll utuh · {splitRolls.length} roll terpecah · {unassignedRollRows.length} belum ditempatkan.</small></div><div><button type="button" onClick={tidyWholeRolls}>Susun otomatis tanpa pecah</button></div></div>:<div className="golden-roll-rule size-mode"><Icon name="ruler"/><div><span>PEMBAGIAN AWAL PER SIZE</span><strong>Size utuh dikelompokkan dulu, lalu bebas lu pecah atau gabung</strong><small>Contoh 2 batch: Size 31 sendiri, Size 32+33 bersama. Total setiap size tetap harus sama dengan sumber.</small></div></div>}

        {allocationMode==='roll'&&<section className={`wip-roll-tray ${unassignedRollRows.length===0?'all-assigned':''}`}><div className="wip-roll-tray-head"><div><span>ROLL BELUM DITEMPATKAN</span><strong>{unassignedRollRows.length===0?'Semua roll sudah masuk batch':'Tarik roll ke kartu batch di bawah'}</strong><small>{unassignedRollRows.length===0?'Kalau mau pindah, tarik dari kartu batch atau keluarkan kembali.':'Setelah di-drop, roll hilang dari area ini supaya urutannya tetap bersih.'}</small></div><span>{unassignedRollRows.length} roll tersisa</span></div>{unassignedRollRows.length>0?<div className="wip-roll-token-grid">{unassignedRollRows.map((row)=><article className="wip-roll-token" key={row.roll.id}><button type="button" className="wip-roll-drag-handle" aria-label={`Tarik Roll ${row.roll.sequence} ke batch`} title="Tahan lalu tarik ke kartu batch" onPointerDown={(event)=>beginRollDrag(event,row.roll.id)} onPointerMove={moveRollDrag} onPointerUp={finishRollDrag} onPointerCancel={cancelRollDrag}><Icon name="drag"/></button><div><span>ROLL {String(row.roll.sequence).padStart(2,'0')} · {row.roll.id}</span><strong>{row.quantity} pcs</strong><small>{cuttingSizes.map((size,index)=>`${size}: ${row.sizes[index]}`).join(' · ')}</small></div><em>Belum masuk</em><button type="button" className="wip-roll-split-btn" onClick={()=>{setSplitEditorRollId(row.roll.id);setAllocationMessage('')}}>Atur pecahan</button><small className="wip-roll-assigned">Sumber utuh</small></article>)}</div>:<div className="wip-roll-tray-empty"><Icon name="check"/><span>Area sumber bersih</span></div>}</section>}

        {allocationMode==='size'&&<div className="split-source-locks size-allocation-source-locks">{cuttingSizes.map((size,sizeIndex)=>{const check=sourceChecks[sizeIndex];const remaining=(check?.total??0)-(check?.assigned??0);return <div className={remaining===0?'success':'warn'} key={size}><span>SIZE {size} · SUMBER</span><strong>{check?.total??wipSizeTotals[sizeIndex]} pcs</strong><small>Terbagi {check?.assigned??0} · Sisa {remaining}</small></div>})}</div>}

        {allocationMode==='roll'&&splitEditorRow&&<section className={`roll-split-editor ${splitEditorExact?'exact':'warn'}`} role="dialog" aria-label={`Atur pecahan Roll ${splitEditorRow.roll.sequence}`}><div className="roll-split-editor-head"><div><span>PENGECUALIAN · ROLL {String(splitEditorRow.roll.sequence).padStart(2,'0')}</span><h3>Pecah {splitEditorRow.roll.id} per size</h3><p>Isi jumlah absolut untuk setiap batch. Angka sumber Potongan di bawah ini tidak bisa diubah.</p></div><button type="button" aria-label="Tutup editor pecahan" onClick={()=>{setSplitEditorRollId(null);setAllocationMessage('')}}><Icon name="close"/></button></div><div className="split-source-locks">{cuttingSizes.map((size,sizeIndex)=>{const check=splitEditorChecks[sizeIndex];return <div className={check?.remaining===0?'success':'warn'} key={size}><span>SIZE {size} · SUMBER</span><strong>{check?.source??0} pcs</strong><small>Terbagi {check?.assigned??0} · Sisa {check?.remaining??0}</small></div>})}</div><div className="split-batch-grid" data-keyboard-grid>{Array.from({length:batchCount},(_,batchIndex)=>{const batchValues=rollBatchMatrix[splitEditorRow.roll.id]?.[batchIndex]??['0','0','0'];return <article key={batchIndex}><span>BATCH {String(batchIndex+1).padStart(2,'0')}</span>{cuttingSizes.map((size,sizeIndex)=><label key={size}><small>Size {size}</small><div><input type="text" pattern="[0-9]*" inputMode="numeric" data-grid-row={sizeIndex} data-grid-col={batchIndex} aria-label={`Roll ${splitEditorRow.roll.sequence}, batch ${batchIndex+1}, size ${size}`} value={batchValues[sizeIndex]??'0'} onFocus={(event)=>event.currentTarget.select()} onClick={(event)=>event.currentTarget.select()} onChange={(event)=>updateSplitAllocation(splitEditorRow.roll.id,batchIndex,sizeIndex,event.target.value)}/><b>pcs</b></div></label>)}<strong>{batchValues.reduce((sum,value)=>sum+cellQuantity(value),0)} pcs</strong></article>})}</div><div className="roll-split-editor-foot"><span className={allocationMessage?'error':splitEditorExact?'success':'warn'}>{allocationMessage|| (splitEditorExact?'Pas dengan sumber Potongan.':'Belum pas—cek Sumber, Terbagi, dan Sisa per size.')}</span><button type="button" className="soft-btn" onClick={()=>setSplitEditorRollId(null)}>Selesai</button></div></section>}

        <div className="wip-batch-grid" data-keyboard-grid>
          {Array.from({length:effectiveBatchCount},(_,batchIndex)=>{const assignedRows=allocationMode==='roll'?wipRollRows.filter((row)=>(rollBatchMatrix[row.roll.id]?.[batchIndex]??[]).reduce((sum,value)=>sum+cellQuantity(value),0)>0):[];return <article data-wip-drop-batch={allocationMode==='roll'?batchIndex:undefined} className={`wip-batch-card ${rollDrag?.target===batchIndex?'drop-target':''} ${allocationMode==='size'?'size-batch-card':''}`} key={batchIndex}>
            <div className="wip-batch-card-head"><div><span>BATCH {String(batchIndex+1).padStart(2,'0')}</span><strong>{batchTotals[batchIndex]} pcs</strong></div><label className="batch-mandor-note"><span>CATATAN JAHITAN / WARNA</span><input type="text" value={batchNotes[batchIndex]??''} placeholder="Contoh: navy · obras rapat..." aria-label={`Catatan jahitan atau warna Batch ${batchIndex+1}`} onChange={(event)=>setBatchNotes((current)=>Array.from({length:effectiveBatchCount},(_,noteIndex)=>noteIndex===batchIndex?event.target.value:current[noteIndex]??''))}/></label><small>Saran {targetTotals[batchIndex]}</small></div>
            <div className="wip-batch-size-mix">{cuttingSizes.map((size,sizeIndex)=><span className={batchSizeMix[batchIndex][sizeIndex]>0?'active':''} key={size}><small>SIZE {size}</small><strong>{batchSizeMix[batchIndex][sizeIndex]}</strong></span>)}</div>
            <div className="wip-batch-source-list">
            {allocationMode==='roll'?(assignedRows.length>0?assignedRows.map((row)=>{const sizes=rollBatchMatrix[row.roll.id]?.[batchIndex]??['0','0','0'];const allocated=sizes.reduce((sum,value)=>sum+cellQuantity(value),0);const usedIn=(rollBatchMatrix[row.roll.id]??[]).filter((batchSizes)=>batchSizes.reduce((sum,value)=>sum+cellQuantity(value),0)>0).length;const sourceExact=row.sizes.every((source,sizeIndex)=>(rollBatchMatrix[row.roll.id]??[]).reduce((sum,batchSizes)=>sum+cellQuantity(batchSizes[sizeIndex]),0)===source);const draggable=usedIn===1&&sourceExact;return <div className="wip-batch-source locked-source movable-source" key={row.roll.id}><button type="button" disabled={!draggable} className="batch-roll-drag-handle" aria-label={`Pindahkan Roll ${row.roll.sequence} ke batch lain`} title={draggable?'Tarik ke batch lain':'Roll pecah dipindahkan lewat Atur'} onPointerDown={(event)=>draggable&&beginRollDrag(event,row.roll.id)} onPointerMove={moveRollDrag} onPointerUp={finishRollDrag} onPointerCancel={cancelRollDrag}><Icon name="drag"/></button><div className="batch-roll-body"><header><div><span>ROLL {String(row.roll.sequence).padStart(2,'0')}</span><strong>{row.roll.id}</strong></div><b>{allocated} pcs</b></header><div className="batch-roll-size-pills">{cuttingSizes.map((size,sizeIndex)=><span className={cellQuantity(sizes[sizeIndex])>0?'active':''} key={size}><small>{size}</small><strong>{cellQuantity(sizes[sizeIndex])}</strong></span>)}</div><small className="batch-roll-lineage">Sumber {row.quantity} pcs · {usedIn>1?`tersebar di ${usedIn} Batch Distribusi`:'masuk utuh ke Batch Distribusi ini'}</small></div><em className={usedIn>1?'pecah':'utuh'}>{usedIn>1?'Pecah':'Utuh'}</em><div className="batch-source-actions"><button type="button" onClick={()=>{setSplitEditorRollId(row.roll.id);setAllocationMessage('')}}>Atur pembagian</button><button type="button" onClick={()=>unassignRoll(row.roll.id)}>Keluarkan roll</button></div></div>}):<div className="wip-batch-empty"><Icon name="drag"/><strong>Tarik roll ke sini</strong><small>Roll masuk utuh secara default</small></div>):cuttingSizes.map((size,sizeIndex)=>{const allocated=sizeMatrix[size]?.[batchIndex]??'0';const check=sourceChecks[sizeIndex];return <label className={`wip-batch-source editable-size-source ${cellQuantity(allocated)===0?'empty':''}`} key={size}><div><strong>Size {size}</strong><small>Sumber {check?.total??wipSizeTotals[sizeIndex]} · terbagi {check?.assigned??0}</small></div><div className="wip-free-input"><input type="text" pattern="[0-9]*" inputMode="numeric" data-grid-row={sizeIndex} data-grid-col={batchIndex} aria-label={`Batch ${batchIndex+1}, Size ${size}`} value={allocated} onFocus={(event)=>event.currentTarget.select()} onClick={(event)=>event.currentTarget.select()} onChange={(event)=>updateSizeAllocation(size,batchIndex,event.target.value)}/><span>pcs</span></div></label>})}
            </div>
            <div className="wip-batch-route"><span>JAHIT</span><Icon name="arrow"/><span>LAUNDRY</span><small>Kode batch tetap sama</small></div>
          </article>})}
        </div>

        {rollDrag&&<div className="roll-drag-ghost" style={{left:rollDrag.x,top:rollDrag.y}}><Icon name="drag"/><span>{rollDrag.rollId}</span><small>{rollDrag.target===null?'Arahkan ke batch':`Lepas di Batch ${String(rollDrag.target+1).padStart(2,'0')}`}</small></div>}
        <div className="wip-source-audit"><Icon name={sourcesExact?'check':'history'}/><div><strong>{sourcesExact?'Pembagian cocok dengan seluruh sumber':'Masih ada sumber roll atau size yang tidak cocok'}</strong><span>{sourceChecks.filter((source)=>source.assigned!==source.total).map((source)=>`${source.key}: ${source.assigned}/${source.total}`).join(' · ')||`${wipRollRows.length} roll · Size 31/32/33 seluruhnya rekonsiliasi`}</span></div></div>
        <section className={`pickup-final-review ${isReady?'ready':'blocked'}`} aria-label="Review akhir pickup"><div className="pickup-review-head"><Icon name={isReady?'check':'history'}/><div><span>04 · REVIEW SEBELUM POSTING</span><strong>{isReady?'Siap dicatat sebagai pickup mandor':'Belum siap diposting'}</strong><small>{isReady?'Sesudah konfirmasi, PO masuk tahap SEWING.':'Rapikan pembagian sampai sumber, size, dan total seluruh batch pas.'}</small></div></div><div className="pickup-review-facts"><div><span>MANDOR</span><strong>{mandor||'Belum dipilih'}</strong></div><div><span>WAKTU AMBIL</span><strong>{pickupReviewAt}</strong></div><div><span>PEMBAGIAN</span><strong>{allocationMode==='roll'?'Per roll':'Awal per size'}</strong></div><div><span>TOTAL</span><strong>{effectiveBatchCount} batch · {assignedTotal} pcs</strong></div></div><div className="pickup-review-batches">{batchTotals.map((total,batchIndex)=><div className={total>0?'filled':'empty'} key={batchIndex}><span>BATCH {String(batchIndex+1).padStart(2,'0')}</span><strong>{total} pcs</strong><small>{batchNotes[batchIndex]||'Belum ada catatan mandor'}</small><em>{cuttingSizes.map((size,sizeIndex)=>`${size}: ${batchSizeMix[batchIndex][sizeIndex]}`).join(' · ')}</em></div>)}</div><div className="pickup-review-next"><Icon name="arrow"/><span><strong>Setelah posting: SEWING</strong> · Laundry baru boleh dicatat ketika batch benar-benar dikirim keluar.</span></div></section>
        <div className="allocation-footer"><small>{isReady?'Ringkasan final di atas sudah cocok. Backend belum disentuh selama prototype.':'Tombol posting terbuka setelah seluruh sumber dan total batch cocok.'}</small><div><button type="button" className="soft-btn">Simpan draft pickup</button><button type="button" className="primary-btn" disabled={!isReady}>Review & catat pickup <Icon name="arrow"/></button></div></div>
      </div>
    </section>
  </>
}

type SewingBatchSeed = {
  id: string
  number: number
  qty: number
  sizes: QtyTuple
  completed: number
  note: string
}

type SewingParentSeed = {
  id: string
  sequence: number
  brand: string
  model: string
  material: string
  mandor: string
  pickupAt: string
  sizes: SizeTuple
  batches: SewingBatchSeed[]
}

const sewingWipSeeds: SewingParentSeed[] = [
  { id:'POT-260827-042',sequence:42,brand:'Widie',model:'Kulot Lucy',material:'Lucy',mandor:'Mandor Afat',pickupAt:'27 Agu 2026 · 10:30',sizes:['31','32','33'],batches:[
    {id:'042-01',number:1,qty:229,sizes:[229,0,0],completed:188,note:'Warna navy · stik pinggang 2 jalur'},
    {id:'042-02',number:2,qty:225,sizes:[0,225,0],completed:225,note:'Warna maroon · obras rapat'},
    {id:'042-03',number:3,qty:222,sizes:[0,0,222],completed:0,note:'Warna hitam · cek sambungan samping'},
  ]},
  { id:'POT-260826-041',sequence:41,brand:'Widie',model:'Malibu Regular',material:'Malibu',mandor:'Mandor Asep',pickupAt:'26 Agu 2026 · 14:15',sizes:['28','29','30'],batches:[
    {id:'041-01',number:1,qty:244,sizes:[82,81,81],completed:244,note:'Biru muda · benang senada · obras rapat'},
    {id:'041-02',number:2,qty:244,sizes:[81,81,82],completed:244,note:'Biru tua · cek kantong kanan kiri'},
  ]},
  { id:'POT-260825-039',sequence:39,brand:'Vivo',model:'Zodiak Jumbo',material:'Zodiak KW',mandor:'Mandor Dedi',pickupAt:'25 Agu 2026 · 09:40',sizes:['34','35','36'],batches:[
    {id:'039-01',number:1,qty:114,sizes:[38,38,38],completed:114,note:'Stone · stik bawah 2 jalur'},
    {id:'039-02',number:2,qty:114,sizes:[38,38,38],completed:114,note:'Charcoal · sambungan samping dobel'},
    {id:'039-03',number:3,qty:114,sizes:[38,38,38],completed:0,note:'Black · gunakan benang hitam pekat'},
  ]},
]

const laundryVendorNames = ['Laundry Berkah', 'Laundry Intan', 'Cemerlang Wash']

function SewingWipPage({
  batchNotes, deliveries, laundryDrafts, reverseNotice, onClearReverseNotice,
  onClearLaundryDraft, onConfirmLaundry, onOpenLaundry, onOpenQc,
}: {
  batchNotes: string[]
  deliveries: LaundryDelivery[]
  laundryDrafts: Record<string,string>
  reverseNotice: string|null
  onClearReverseNotice: () => void
  onClearLaundryDraft: (batchId:string) => void
  onConfirmLaundry: (batchId:string,vendor:string,snapshot?:{qty:number;sizes:QtyTuple}) => void
  onOpenLaundry: (batchId:string,vendor:string,view:LaundryView) => void
  onOpenQc: (parentId:string,batchId:string) => void
}) {
  const [batchOverrides,setBatchOverrides] = useState<Record<string,QtyTuple>>({})
  const [reversedBatchIds,setReversedBatchIds] = useState<string[]>([])
  const [controlTarget,setControlTarget] = useState<{parentId:string;batchId:string;mode:WipControlMode}|null>(null)
  const [controlNotice,setControlNotice] = useState<{title:string;message:string}|null>(null)
  const [adjustmentHistory,setAdjustmentHistory] = useState<Record<string,WipAdjustmentHistoryEntry[]>>({})
  const parentGroups = useMemo(() => sewingWipSeeds.map((parent) => ({
    ...parent,
    batches:parent.batches
      .filter((batch)=>!reversedBatchIds.includes(batch.id))
      .map((batch)=>{
        const sizes=batchOverrides[batch.id]??batch.sizes
        const noteIndex=parent.batches.findIndex((source)=>source.id===batch.id)
        return {...batch,sizes,qty:sizes.reduce((sum,qty)=>sum+qty,0),note:parent.id==='POT-260827-042'?(batchNotes[noteIndex]||batch.note):batch.note}
      }),
  })), [batchNotes,batchOverrides,reversedBatchIds])
  const mandorOptions = Array.from(new Set(parentGroups.map((parent) => parent.mandor)))
  const [selectedMandors,setSelectedMandors] = useState([...mandorOptions])
  const [query,setQuery] = useState('')
  const [completedInputs,setCompletedInputs] = useState<Record<string,string>>(() => Object.fromEntries(sewingWipSeeds.flatMap((parent) => parent.batches.map((batch) => [batch.id,String(batch.completed)]))))
  const [hideCompleted,setHideCompleted] = useState(true)
  const [pendingLaundry,setPendingLaundry] = useState<{batchId:string;vendor:string;qty:number}|null>(null)
  const parentIsReturned=(parent:SewingParentSeed)=>parent.batches.every((batch)=>summarizeLaundryBatch(deliveries,batch.id).returned>=batch.qty)
  const completedParentCount=parentGroups.filter(parentIsReturned).length
  const visibleGroups = parentGroups
    .filter((parent) => selectedMandors.includes(parent.mandor))
    .filter((parent) => `${parent.id} ${parent.model} ${parent.material} ${parent.mandor} ${parent.batches.map((batch) => `${batch.number} ${batch.note}`).join(' ')}`.toLowerCase().includes(query.toLowerCase()))
    .filter((parent)=>!hideCompleted||!parentIsReturned(parent))
    .sort((a,b) => b.sequence-a.sequence)
  const visibleBatches = visibleGroups.flatMap((parent) => parent.batches)
  const visibleQty = visibleBatches.reduce((sum,batch) => sum+batch.qty,0)
  const visibleCompleted = visibleBatches.reduce((sum,batch) => sum+Math.min(batch.qty,cellQuantity(completedInputs[batch.id])),0)
  const readyLaundryCount = visibleBatches.filter((batch) => {
    const summary=summarizeLaundryBatch(deliveries,batch.id)
    return cellQuantity(completedInputs[batch.id])===batch.qty&&summary.outside===0&&summary.returned<batch.qty
  }).length
  const updateCompleted = (batch: SewingBatchSeed, rawValue: string) => {
    const digits = rawValue.replace(/[^0-9]/g,'').replace(/^0+(?=\d)/,'')
    const nextValue = digits===''?'':String(Math.min(batch.qty,cellQuantity(digits)))
    setCompletedInputs((current)=>({...current,[batch.id]:nextValue}))
    if(cellQuantity(nextValue)<batch.qty&&laundryDrafts[batch.id])onClearLaundryDraft(batch.id)
  }
  const controlParent=controlTarget?parentGroups.find((parent)=>parent.id===controlTarget.parentId):undefined
  const controlPayload:WipControlParent|null=controlParent?{
    id:controlParent.id,model:controlParent.model,material:controlParent.material,mandor:controlParent.mandor,sizeLabels:controlParent.sizes,
    batches:controlParent.batches.map((batch)=>{
      const completed=Math.min(batch.qty,cellQuantity(completedInputs[batch.id]))
      const summary=summarizeLaundryBatch(deliveries,batch.id)
      const draft=laundryDrafts[batch.id]
      const lockLabel=summary.returned>0?'Sudah kembali':summary.outside>0?'Di Laundry':draft?'Draft Laundry':completed>0?`${completed} pcs dijahit`:'Pre-sewing'
      return {...batch,completed,locked:completed>0||summary.returned>0||summary.outside>0||Boolean(draft),lockLabel}
    }),
  }:null
  const applyWipControl=(result:WipControlResult)=>{
    if(!controlParent)return
    if(result.kind==='ADJUST'){
      const before=controlParent.batches.reduce((sum,batch)=>sum+batch.qty,0)
      const after=Object.values(result.sizesByBatch).reduce((sum,sizes)=>sum+sizes.reduce((lineTotal,qty)=>lineTotal+qty,0),0)
      const changedBatches=controlParent.batches.filter((batch)=>{
        const next=result.sizesByBatch[batch.id]
        return next&&batch.sizes.some((qty,index)=>qty!==next[index])
      })
      setBatchOverrides((current)=>({...current,...result.sizesByBatch}))
      setAdjustmentHistory((current)=>{
        const next={...current}
        changedBatches.forEach((batch,index)=>{
          const entry:WipAdjustmentHistoryEntry={
            id:`${result.operation}-${Date.now()}-${index}`,
            operation:result.operation,
            note:result.note,
            at:'28 Agu 2026 · baru saja',
            before:[...batch.sizes] as QtyTuple,
            after:[...result.sizesByBatch[batch.id]] as QtyTuple,
          }
          next[batch.id]=[entry,...(next[batch.id]??[])]
        })
        return next
      })
      setCompletedInputs((current)=>Object.fromEntries(Object.entries(current).map(([batchId,value])=>{
        const sizes=result.sizesByBatch[batchId]
        return [batchId,sizes?String(Math.min(cellQuantity(value),sizes.reduce((sum,qty)=>sum+qty,0))):value]
      })))
      setControlNotice({
        title:result.operation==='REDISTRIBUTION'?'Distribusi batch diperbarui':'Hasil fisik diperbarui',
        message:result.operation==='REDISTRIBUTION'
          ? `Batch Produksi ${controlParent.id} tetap ${after} pcs; redistribusi tersimpan sebagai simulasi berjejak.`
          : `Batch Produksi ${controlParent.id} berubah dari ${before} menjadi ${after} pcs (${after-before>=0?'+':''}${after-before}). Batas transaksi downstream tetap dijaga server.`,
      })
    }else{
      setReversedBatchIds((current)=>current.includes(result.batchId)?current:[...current,result.batchId])
      setControlNotice({title:`Distribusi ${result.batchId} dibatalkan`,message:`Kuantitas kembali ke Batch Produksi ${controlParent.id}. Dokumen hasil potong tidak dihapus.`})
    }
    setControlTarget(null)
  }

  return <>
    <section className="hero-copy compact sewing-hero"><div className="eyebrow">PRODUKSI · SETELAH PICKUP</div><h1>WIP & Sewing</h1><p>Seluruh pekerjaan jahit dikelompokkan berdasarkan Batch Produksi. Mandor menyelesaikan setiap Batch Distribusi, lalu tujuan laundry dapat dipilih ketika kuantitas jahitan sudah penuh.</p></section>
    {reverseNotice&&<div className="sewing-reverse-notice"><Icon name="reset"/><div><strong>Kembali ke WIP</strong><span>{reverseNotice}</span></div><button type="button" aria-label="Tutup pemberitahuan" onClick={onClearReverseNotice}><Icon name="close"/></button></div>}
    {controlNotice&&<div className="wip-control-notice"><ShieldCheck/><div><strong>{controlNotice.title}</strong><span>{controlNotice.message} Backend belum berubah selama mode simulasi.</span></div><button type="button" aria-label="Tutup pemberitahuan" onClick={()=>setControlNotice(null)}><X/></button></div>}
    <section className="sewing-kpi-grid"><div className="panel"><span>BATCH PRODUKSI</span><strong>{visibleGroups.length}</strong><small>Urut dari produksi terbaru</small></div><div className="panel"><span>BATCH DISTRIBUSI</span><strong>{visibleBatches.length}</strong><small>{visibleQty} pcs sedang dikelola</small></div><div className="panel"><span>SELESAI DIJAHIT</span><strong>{visibleCompleted} pcs</strong><small>{visibleQty-visibleCompleted} pcs belum selesai</small></div><div className="panel ready"><span>SIAP PILIH LAUNDRY</span><strong>{readyLaundryCount} batch</strong><small>Tujuan laundry sudah dapat dipilih</small></div></section>
    <section className="panel sewing-workspace">
      <div className="sewing-toolbar"><div><span>SEMUA JAHITAN</span><strong>Batch Produksi → Batch Distribusi</strong><small>{visibleGroups.length} Batch Produksi · {visibleBatches.length} distribusi tampil</small></div><label className="sewing-search"><Icon name="search"/><input value={query} onChange={(event)=>setQuery(event.target.value)} placeholder="Cari Batch Produksi, model, bahan, atau catatan..."/></label><MultiCheckFilter label="Mandor" options={mandorOptions} selected={selectedMandors} onChange={setSelectedMandors}/><button type="button" className={`sewing-hide-toggle ${hideCompleted?'active':''}`} onClick={()=>setHideCompleted((current)=>!current)}><Icon name={hideCompleted?'check':'history'}/><span>{hideCompleted?'Selesai disembunyikan':'Sembunyikan selesai'}</span><b>{completedParentCount}</b></button></div>
      <div className="sewing-parent-list" data-keyboard-grid>{visibleGroups.map((parent,parentIndex)=>{
        const parentCompleted=parent.batches.reduce((sum,batch)=>sum+Math.min(batch.qty,cellQuantity(completedInputs[batch.id])),0)
        const parentQty=parent.batches.reduce((sum,batch)=>sum+batch.qty,0)
        const parentProgress=Math.round((parentCompleted/Math.max(1,parentQty))*100)
        const parentDeliveries=deliveries.filter((delivery)=>delivery.parentId===parent.id)
        const parentOutside=parentDeliveries.reduce((sum,delivery)=>sum+laundryOutstanding(delivery),0)
        const parentReturned=parentDeliveries.reduce((sum,delivery)=>sum+delivery.good+delivery.bs,0)
        const parentVendors=Array.from(new Set(parentDeliveries.filter((delivery)=>laundryOutstanding(delivery)>0).map((delivery)=>delivery.vendor)))
        return <article className="sewing-parent-card" key={parent.id}>
          <header className="sewing-parent-head"><span className="sewing-parent-order">{String(parentIndex+1).padStart(2,'0')}</span><div><small>{parent.brand} · BATCH PRODUKSI</small><h2>{parent.id} · {parent.model}</h2><p>{parent.material} · pickup {parent.pickupAt}</p></div><span className="sewing-mandor-pill"><Icon name="user"/><span><small>MANDOR</small><strong>{parent.mandor}</strong></span></span><div className="sewing-parent-total"><strong>{parentCompleted}/{parentQty} pcs</strong><small>{parentVendors.length>0?`${parentVendors.join(' & ')} · ${parentOutside} di luar · ${parentReturned} kembali`:`${parent.batches.length} Batch Distribusi · ${parentProgress}%`}</small></div></header>
          <div className="sewing-parent-progress"><span style={{width:`${parentProgress}%`}}/></div>
          <div className="sewing-child-grid">{parent.batches.map((batch,batchIndex)=>{
            const completed=Math.min(batch.qty,cellQuantity(completedInputs[batch.id]))
            const progress=Math.round((completed/Math.max(1,batch.qty))*100)
            const isReady=completed===batch.qty
            const summary=summarizeLaundryBatch(deliveries,batch.id)
            const draftLaundry=laundryDrafts[batch.id]
            const inLaundry=summary.outside>0
            const returnedToQc=summary.returned>0
            const availableLaundryQty=Math.max(0,batch.qty-summary.returned-summary.outside)
            const locked=inLaundry||returnedToQc
            const preSewing=completed===0&&!locked&&!draftLaundry
            const batchHistory=adjustmentHistory[batch.id]??[]
            const status=returnedToQc?(summary.outside>0?'Kembali sebagian · siap QC':'Kembali · siap QC'):inLaundry?'Di laundry':draftLaundry?'Draft laundry':isReady?'Siap laundry':completed>0?'Sedang dijahit':'Menunggu jahit · Pre-sewing'
            return <section className={`sewing-batch-card ${isReady&&!locked?'ready':''} ${draftLaundry?'laundry-draft':''} ${inLaundry?'laundry-in-transit':''} ${returnedToQc?'laundry-returned':''} ${reverseNotice?.includes(batch.id)?'reverse-focus':''}`} key={batch.id}>
              <div className="sewing-batch-head"><div><span>BATCH DISTRIBUSI {String(batch.number).padStart(2,'0')}</span><strong>{batch.qty} pcs</strong></div><em>{status}</em></div>
              <div className="sewing-batch-sizes">{parent.sizes.map((size,sizeIndex)=><span className={batch.sizes[sizeIndex]>0?'active':''} key={size}><small>SIZE {size}</small><strong>{batch.sizes[sizeIndex]}</strong></span>)}</div>
              <div className="sewing-batch-note"><Icon name="document"/><div><span>ARAHAN MANDOR</span><strong>{batch.note}</strong></div></div>
              <div className={`wip-child-controls ${preSewing?'editable':''}`}>{preSewing?<><span><ShieldCheck/> Belum ada bukti jahit; distribusi masih aman dikoreksi.</span><button type="button" onClick={()=>setControlTarget({parentId:parent.id,batchId:batch.id,mode:'adjust'})}><SlidersHorizontal/> Koreksi</button><button type="button" className="reverse" onClick={()=>setControlTarget({parentId:parent.id,batchId:batch.id,mode:'reverse'})}><RotateCcw/> Batalkan</button></>:<span><ShieldCheck/> Kontrol distribusi terkunci oleh {returnedToQc?'hasil return':inLaundry?'Laundry':draftLaundry?'draft Laundry':`${completed} pcs selesai dijahit`}.</span>}</div>
              {batchHistory.length>0&&<details className="wip-adjust-history"><summary><Icon name="history"/><span><strong>Riwayat koreksi batch</strong><small>{batchHistory[0].operation==='REDISTRIBUTION'?'Redistribusi terakhir':'Koreksi fisik terakhir'} · {batchHistory[0].at}</small></span><b>{batchHistory.length}</b></summary><div>{batchHistory.map((entry)=><article key={entry.id}><header><strong>{entry.operation==='REDISTRIBUTION'?'Redistribusi Batch':'Koreksi hasil fisik'}</strong><span>{entry.at}</span></header><div>{parent.sizes.map((size,sizeIndex)=><span key={size}><small>SIZE {size}</small><strong>{entry.before[sizeIndex]} → {entry.after[sizeIndex]}</strong></span>)}</div><p>{entry.note}</p></article>)}</div></details>}
              <label className={`sewing-completed-input ${locked?'disabled':''}`}><span>SELESAI DIJAHIT</span><div><input disabled={locked} type="text" pattern="[0-9]*" inputMode="numeric" data-grid-row={parentIndex*100+batchIndex} data-grid-col={0} value={completedInputs[batch.id]??''} onFocus={(event)=>event.currentTarget.select()} onClick={(event)=>event.currentTarget.select()} onChange={(event)=>updateCompleted(batch,event.target.value)}/><b>/ {batch.qty} pcs</b></div></label>
              <div className="sewing-batch-progress"><span style={{width:`${progress}%`}}/></div>
              {returnedToQc?<div className="sewing-laundry-gate returned"><div><span>{summary.outside>0?'KEMBALI SEBAGIAN · SIAP QC':'SUDAH KEMBALI · SIAP QC'}</span><small>{summary.returned} pcs kembali · {summary.outside} pcs otomatis Stuck Laundry saat review.</small></div><div className="laundry-name-grid">{[...new Set([...summary.activeVendors,...summary.returnedVendors])].map((name)=><button type="button" className="active jump" onClick={()=>onOpenLaundry(batch.id,name,'return')} key={name}><Icon name="arrow"/>{name}</button>)}</div><p><Icon name="check"/><span>{summary.good} Good · {summary.bs} BS tercatat. Riwayat laundry tetap terlihat.</span></p><button type="button" className="wip-review-finishing" onClick={()=>onOpenQc(parent.id,batch.id)}>Review finishing <Icon name="arrow"/></button></div>
              :inLaundry?<div className="sewing-laundry-gate open tracking"><div><span>SEDANG DI LAUNDRY</span><small>{summary.outside} pcs masih di luar · belum ada fisik yang kembali</small></div><div className="laundry-name-grid">{summary.activeVendors.map((name)=><button type="button" className="active jump" onClick={()=>onOpenLaundry(batch.id,name,'return')} key={name}><Icon name="arrow"/>{name}</button>)}</div><p><Icon name="history"/><span>Tekan nama laundry untuk buka surat kirim aktif.</span></p></div>
              :<div className={`sewing-laundry-gate ${isReady?'open':'locked'} ${draftLaundry?'draft':''}`}><div><span>{isReady?(draftLaundry?'DRAFT TUJUAN LAUNDRY':'PILIH NAMA LAUNDRY'):'LAUNDRY TERKUNCI'}</span><small>{isReady?(draftLaundry?'Belum mengubah stok. Tekan nama aktif untuk kembali ke review.':summary.returned>0?`${availableLaundryQty} pcs sisa siap dipilihkan laundry baru.`:'Tekan nama tujuan, lalu konfirmasi pindah halaman.'):`Selesaikan ${batch.qty-completed} pcs lagi.`}</small></div>{isReady&&availableLaundryQty>0&&<div className="laundry-name-grid">{laundryVendorNames.map((name)=><button type="button" className={draftLaundry===name?'active':''} aria-pressed={draftLaundry===name} onClick={()=>draftLaundry===name?onOpenLaundry(batch.id,name,'send'):setPendingLaundry({batchId:batch.id,vendor:name,qty:availableLaundryQty})} key={name}>{draftLaundry===name&&<Icon name="check"/>}{name}</button>)}</div>}{draftLaundry&&<p><Icon name="arrow"/><span><strong>{draftLaundry}</strong> · draft surat kirim siap dilanjutkan.</span></p>}</div>}
            </section>
          })}</div>
        </article>
      })}{visibleGroups.length===0&&<div className="sewing-empty"><Icon name={completedParentCount>0?'check':'search'}/><strong>{completedParentCount>0&&hideCompleted?'Semua hasil yang cocok sudah selesai':'Tidak ada jahitan yang cocok'}</strong><small>{completedParentCount>0&&hideCompleted?'Tekan “Selesai disembunyikan” untuk membuka riwayat.':'Cek pilihan mandor atau kata pencarian.'}</small></div>}</div>
    </section>
    {controlTarget&&controlPayload&&<Suspense fallback={null}><WipBatchControlLayer key={`${controlTarget.parentId}-${controlTarget.batchId}-${controlTarget.mode}`} mode={controlTarget.mode} parent={controlPayload} targetBatchId={controlTarget.batchId} onClose={()=>setControlTarget(null)} onApply={applyWipControl}/></Suspense>}
    {pendingLaundry&&<div className="wip-confirm-layer" role="presentation"><section className="wip-confirm-dialog" role="alertdialog" aria-modal="true" aria-labelledby="confirm-laundry-title"><div className="wip-confirm-icon"><Icon name="boxes"/></div><div><span>PINDAH KE HALAMAN LAUNDRY</span><h2 id="confirm-laundry-title">Siapkan ke {pendingLaundry.vendor}?</h2><p>Batch {pendingLaundry.batchId} · {pendingLaundry.qty} pcs. Ini baru membuat draft tujuan; stok belum berpindah sampai lu menekan <strong>Catat dikirim</strong> di halaman Laundry.</p></div><div className="wip-confirm-actions"><button type="button" className="soft-btn" onClick={()=>setPendingLaundry(null)}>Batal</button><button type="button" className="primary-btn" onClick={()=>{const source=parentGroups.flatMap((parent)=>parent.batches).find((batch)=>batch.id===pendingLaundry.batchId);onConfirmLaundry(pendingLaundry.batchId,pendingLaundry.vendor,source?{qty:source.qty,sizes:source.sizes}:undefined);setPendingLaundry(null)}}>Buka Laundry <Icon name="arrow"/></button></div></section></div>}
  </>
}


const laborBomComponents = [
  {id:'jahit-utama',name:'Jahit utama',rate:8250,required:true,note:'Badan, sambungan utama, dan bentuk model'},
  {id:'finishing-detail',name:'Ceming / finishing detail',rate:2500,required:true,note:'Detail sambungan sesuai snapshot model'},
  {id:'pinggang',name:'Ban & pinggang',rate:2600,required:true,note:'Ban, stik pinggang, dan penguat'},
  {id:'saku',name:'Saku & ritsleting',rate:2300,required:true,note:'Komponen fungsi depan/belakang'},
  {id:'centang',name:'Centang / bartack',rate:800,required:false,note:'Penguat titik dan pemeriksaan detail'},
  {id:'kancing',name:'Kancing',rate:500,required:false,note:'Pasang kancing sesuai model'},
  {id:'plastik',name:'Plastik & packing',rate:500,required:false,note:'Plastik per barang jadi'},
  {id:'hangtag',name:'Hangtag / label',rate:600,required:false,note:'Label dan hangtag final'},
  {id:'lipat',name:'Lipat akhir',rate:400,required:false,note:'Lipat dan susun serah gudang'},
]
function FgPayrollHandoffPage({result,eligibleResults,onBack,onOpenBs}:{result:QcFinalResult;eligibleResults:QcFinalResult[];onBack:()=>void;onOpenBs:()=>void}) {
  const currentId=`qc-${result.parentId}-${result.batchId}`
  const [regularIds,setRegularIds]=useState<string[]>([])
  const [repairIds,setRepairIds]=useState<string[]>([])
  const [noteReviewed,setNoteReviewed]=useState(false)
  const [note,setNote]=useState('Nilai FG reguler memakai Total Pulang × harga lengkap, lalu dikurangi BS × komponen yang ditandai untuk Bikin Bagus.')
  const [noteStatus,setNoteStatus]=useState<'DRAFT'|'POSTED'>('DRAFT')
  const expectedTotal=result.expected.reduce((sum,value)=>sum+value,0)
  const goodTotal=result.qcGood.reduce((sum,value)=>sum+value,0)
  const outstanding=result.stuckBySize.reduce((sum,value)=>sum+value,0)
  const bsTotal=result.qcBs.reduce((sum,value)=>sum+value,0)
  const rewashTotal=result.rewash.reduce((sum,value)=>sum+value,0)
  const returnedTotal=goodTotal+bsTotal+rewashTotal
  const standardRate=laborBomComponents.reduce((sum,component)=>sum+component.rate,0)
  const selectedBsComponents=laborBomComponents.filter((component)=>['finishing-detail','kancing','lipat'].includes(component.id))
  const bsDeductionRate=selectedBsComponents.reduce((sum,component)=>sum+component.rate,0)
  const cardsFromQc=eligibleResults.filter((item)=>item.mandor===result.mandor).map((item)=>{
    const good=item.qcGood.reduce((sum,value)=>sum+value,0)
    const bs=item.qcBs.reduce((sum,value)=>sum+value,0)
    const rewash=item.rewash.reduce((sum,value)=>sum+value,0)
    const hold=item.stuckBySize.reduce((sum,value)=>sum+value,0)
    const returned=good+bs+rewash
    const components=bs>0?selectedBsComponents:[]
    const deductionRate=components.reduce((sum,component)=>sum+component.rate,0)
    const gross=returned*standardRate
    const deduction=bs*deductionRate
    return {id:`qc-${item.parentId}-${item.batchId}`,source:`${item.parentId} · Batch ${item.batchId}`,sku:`${item.brand} · ${item.finalSku}`,returned,good,bs,rewash,hold,sewingRate:14_050,commissionRate:1_800,bomRate:Math.max(0,standardRate-15_850),bsComponents:components,gross,deduction,subtotal:gross-deduction,current:`${item.parentId}::${item.batchId}`===`${result.parentId}::${result.batchId}`}
  })
  const demoComponents=laborBomComponents.filter((component)=>['finishing-detail','kancing'].includes(component.id))
  const demoRate=17_800
  const demoGross=74*demoRate
  const demoDeduction=2*demoComponents.reduce((sum,component)=>sum+component.rate,0)
  const regularCards=cardsFromQc.some((card)=>card.id===currentId)?cardsFromQc:[{id:currentId,source:`${result.parentId} · Batch ${result.batchId}`,sku:`${result.brand} · ${result.finalSku}`,returned:returnedTotal,good:goodTotal,bs:bsTotal,rewash:rewashTotal,hold:outstanding,sewingRate:14_050,commissionRate:1_800,bomRate:Math.max(0,standardRate-15_850),bsComponents:bsTotal>0?selectedBsComponents:[],gross:returnedTotal*standardRate,deduction:bsTotal*bsDeductionRate,subtotal:returnedTotal*standardRate-bsTotal*bsDeductionRate,current:true},...cardsFromQc]
  if(!regularCards.some((card)=>card.id==='eligible-previous'))regularCards.push({id:'eligible-previous',source:'POT-260827-042 · Batch 042-01',sku:'Widie · 73005',returned:74,good:72,bs:2,rewash:0,hold:2,sewingRate:13_400,commissionRate:1_650,bomRate:2_750,bsComponents:demoComponents,gross:demoGross,deduction:demoDeduction,subtotal:demoGross-demoDeduction,current:false})
  const repairCards=[
    {id:'repair-ready',source:'BS-260827-018 · QC ulang lulus',sku:'Vivo · 73003',qty:5,components:[{name:'Ceming / finishing detail',rate:2_500},{name:'Kancing',rate:500},{name:'Lipat akhir',rate:400}],unitRate:3_400,subtotal:17_000},
  ]
  const selectedRegular=regularCards.filter((card)=>regularIds.includes(card.id))
  const selectedRepair=repairCards.filter((card)=>repairIds.includes(card.id))
  const regularSubtotal=selectedRegular.reduce((sum,card)=>sum+card.subtotal,0)
  const repairSubtotal=selectedRepair.reduce((sum,card)=>sum+card.subtotal,0)
  const noteTotal=regularSubtotal+repairSubtotal
  const editable=noteStatus==='DRAFT'
  const toggleRegular=(id:string)=>{setRegularIds((current)=>current.includes(id)?current.filter((item)=>item!==id):[...current,id]);setNoteReviewed(false)}
  const toggleRepair=(id:string)=>{setRepairIds((current)=>current.includes(id)?current.filter((item)=>item!==id):[...current,id]);setNoteReviewed(false)}

  return <>
    <section className="hero-copy compact fg-handoff-hero"><div><div className="eyebrow">PRODUKSI · ANTREAN CARD FINISHING</div><h1>Susun Nota FG</h1><p>QC yang sudah final tinggal sebagai card siap disusun. Gabungkan beberapa Batch Distribusi atau SKU milik Mandor yang sama, lalu post satu Nota FG ke Payroll.</p></div><button type="button" className="soft-btn handoff-back" onClick={onBack}><Icon name="back"/> Tinggalkan antrean & kembali ke QC</button></section>
    <div className="handoff-flow-strip"><span className="done"><b>1</b>QC terkunci</span><i/><span className="done"><b>2</b>Card siap</span><i/><span className="active"><b>3</b>Susun Nota FG</span><i/><span><b>4</b>Payroll</span></div>
    <div className="handoff-queue-banner"><Icon name="check"/><div><strong>FIN-{result.batchId} aman di antrean</strong><span>Kembali ke QC tidak membatalkan finalisasi dan tidak membuat card kedua. Card baru masuk draft setelah tombol Tambah ditekan.</span></div><em>{regularCards.length} card {result.mandor}</em></div>
    {noteStatus==='POSTED'&&<div className="handoff-success"><Icon name="check"/><div><strong>Nota FG sudah posted dan masuk antrean Payroll</strong><span>NFG-260828-NEW · {money(noteTotal)} · belum dibayar dan belum mengubah kas.</span></div></div>}
    <section className="handoff-layout">
      <div className="panel handoff-workbench">
        <header className="handoff-source-head"><span>01</span><div><small>QC FINAL · {result.parentId} · BATCH DISTRIBUSI {result.batchId}</small><h2>{result.brand} · SKU {result.finalSku}</h2><p>{result.finalProductName} · {result.finalColor} · Range {result.finalRange} · bahan {result.material}</p><div className="handoff-mandor-hero"><Icon name="user"/><span><small>MANDOR PENERIMA NOTA</small><strong>{result.mandor}</strong></span></div></div><strong>{returnedTotal} pulang · {goodTotal} Good</strong></header>
        <div className="handoff-section-title"><div><span>02</span><div><strong>Rekonsiliasi fisik dari QC</strong><small>Good menentukan FG. Total Pulang menjadi dasar pekerjaan; Stuck belum ikut karena barangnya belum kembali.</small></div></div><em className="ok">QC read-only</em></div>
        <div className="handoff-size-breakdown" role="table" aria-label="Rekonsiliasi serah FG per size">
          <div className="handoff-size-breakdown-head" role="row"><span>SIZE</span><span>POTONGAN</span><span>BAGUS → FG</span><span>BS</span><span>CUCI ULANG</span><span>STUCK LAUNDRY</span></div>
          {result.sizes.map((size,index)=><div className={`handoff-size-breakdown-row ${result.stuckBySize[index]>0?'has-outstanding':''}`} role="row" key={size}><strong data-label="SIZE">{size}</strong><span data-label="POTONGAN">{result.expected[index]} pcs</span><strong className="good" data-label="BAGUS → FG">{result.qcGood[index]} pcs</strong><span className="bs" data-label="BS">{result.qcBs[index]} pcs</span><span className="rewash" data-label="CUCI ULANG">{result.rewash[index]} pcs</span><span className="stuck" data-label="STUCK LAUNDRY">{result.stuckBySize[index]} pcs</span></div>)}
          <div className="handoff-size-breakdown-total" role="row"><strong>TOTAL</strong><span>{expectedTotal} pcs</span><strong>{goodTotal} pcs</strong><span>{bsTotal} pcs</span><span>{rewashTotal} pcs</span><span>{outstanding} pcs</span></div>
        </div>
        <div className="handoff-equation"><span><small>GOOD → FG</small><strong>{goodTotal} pcs</strong></span><b>+</b><span><small>BS</small><strong>{bsTotal} pcs</strong></span><b>+</b><span><small>CUCI ULANG</small><strong>{rewashTotal} pcs</strong></span><b>=</b><span className="total"><small>TOTAL PULANG</small><strong>{returnedTotal} pcs</strong></span><b>+</b><span className="outside"><small>STUCK</small><strong>{outstanding} pcs</strong></span></div>
        <section className="nota-work-group regular"><header><div><span>03 · ANTREAN FG REGULER</span><h2>Card finishing belum masuk Nota FG</h2><p>Browse card Mandor yang sama. Nilai memakai Total Pulang × harga lengkap, lalu dikurangi BS × komponen Bikin Bagus.</p></div><em>{selectedRegular.length} di draft · {regularCards.length-selectedRegular.length} siap</em></header><div>{regularCards.map((card)=>{const added=regularIds.includes(card.id);const rate=card.sewingRate+card.commissionRate+card.bomRate;const status=noteStatus==='POSTED'&&added?'SUDAH MASUK NOTA':added?'SEDANG DI DRAFT':'SIAP DISUSUN';return <article className={`nota-work-card regular ${added?'added':''}`} key={card.id}><header><div><small>{card.source}</small><strong>{card.sku}</strong></div><span>{status}</span></header><div className="nota-work-facts"><span><small>TOTAL PULANG</small><strong>{card.returned} pcs</strong></span><span className="good"><small>GOOD → FG</small><strong>{card.good} pcs</strong></span><span className="bs"><small>BS</small><strong>{card.bs} pcs</strong></span><span className="rewash"><small>CUCI ULANG</small><strong>{card.rewash} pcs</strong></span><span className="hold"><small>STUCK</small><strong>{card.hold} pcs</strong></span></div><div className="nota-bs-components"><span>KOMPONEN BS DITANDAI BIKIN BAGUS</span><div>{card.bsComponents.length>0?card.bsComponents.map((component)=><em key={component.id}><Icon name="check"/>{component.name}<b>{money(component.rate)}</b></em>):<small>Tidak ada pengurang BS</small>}</div></div><div className="nota-value-formula"><span><small>TOTAL PULANG × HARGA</small><strong>{card.returned} × {money(rate)}</strong><em>{money(card.gross)}</em></span><b>−</b><span className="deduction"><small>BS × KOMPONEN DICENTANG</small><strong>{card.bs} × {money(card.bsComponents.reduce((sum,component)=>sum+component.rate,0))}</strong><em>{money(card.deduction)}</em></span><b>=</b><span className="result"><small>NILAI FG REGULER</small><strong>{money(card.subtotal)}</strong><em>Good bukan pengali upah</em></span></div><footer><small>Good hanya menentukan stok FG. Pengurang BS terlihat dan akan menjadi batas maksimum pembayaran Bikin Bagus.</small><button type="button" disabled={!editable} onClick={()=>toggleRegular(card.id)}>{added?'Keluarkan dari Draft':'Tambah ke Nota FG'}</button></footer></article>})}</div></section>
        <section className="nota-work-group repair"><header><div><span>04 · ANTREAN BIKIN BAGUS</span><h2>Pekerjaan rework yang sudah diterima</h2><p>Card tetap terpisah. Pembayaran hanya komponen yang dicentang dan tidak boleh melampaui pengurang BS asal.</p></div><button type="button" className="soft-btn" onClick={onOpenBs}>Buka Browser Kasus <Icon name="arrow"/></button></header><div>{repairCards.map((card)=>{const added=repairIds.includes(card.id);const status=noteStatus==='POSTED'&&added?'SUDAH MASUK NOTA':added?'SEDANG DI DRAFT':'SIAP DISUSUN';return <article className={`nota-work-card repair ${added?'added':''}`} key={card.id}><header><div><small>{card.source}</small><strong>{card.sku}</strong></div><span>{status}</span></header><div className="nota-repair-components">{card.components.map((component)=><span key={component.name}><Icon name="check"/><small>{component.name}</small><strong>{money(component.rate)}</strong></span>)}</div><div className="nota-work-rate repair"><span>Qty diterima <b>{card.qty} pcs</b></span><span>Tarif komponen <b>{money(card.unitRate)}</b></span><strong>{card.qty} × {money(card.unitRate)} = {money(card.subtotal)}</strong></div><footer><small>Snapshot komponen terkunci dari Bikin Bagus.</small><button type="button" disabled={!editable} onClick={()=>toggleRepair(card.id)}>{added?'Keluarkan dari Draft':'Tambah ke Nota FG'}</button></footer></article>})}</div></section>
        <label className="handoff-note nota-note"><span>CATATAN NOTA FG</span><textarea disabled={!editable} value={note} onChange={(event)=>{setNote(event.target.value);setNoteReviewed(false)}} /></label>
      </div>
      <aside className="panel handoff-payroll-ticket">
        <div className="handoff-ticket-title"><span>NOTA FG · NFG-260828-NEW</span><h2>{result.mandor}</h2><p>{selectedRegular.length} FG Reguler · {selectedRepair.length} Bikin Bagus</p><small>28 Agu 2026 · {noteStatus==='POSTED'?'posted, belum dibayar':'draft dapat disusun'}</small></div>
        <div className="nota-ticket-groups"><article className="regular"><span><small>FG REGULER</small><strong>{selectedRegular.length} card</strong></span><b>{money(regularSubtotal)}</b></article><article className="repair"><span><small>BIKIN BAGUS</small><strong>{selectedRepair.length} card</strong></span><b>{money(repairSubtotal)}</b></article></div>
        <div className="handoff-net"><span>TOTAL NOTA FG</span><strong>{money(noteTotal)}</strong><small>Total ini masuk Payroll setelah posted. Belum ada pembayaran atau pergerakan kas.</small></div>
        <div className="handoff-output"><span>DOKUMEN INI MEMBAWA</span><p><Icon name="check"/><b>{selectedRegular.reduce((sum,card)=>sum+card.returned,0)} pcs</b> Total Pulang sebagai dasar</p><p><Icon name="history"/><b>{money(selectedRegular.reduce((sum,card)=>sum+card.deduction,0))}</b> pengurang BS tercatat</p><p><Icon name="audit"/><b>{selectedRepair.reduce((sum,card)=>sum+card.qty,0)} pcs</b> Bikin Bagus eligible</p></div>
        <label className="handoff-final-check"><input type="checkbox" disabled={!editable} checked={noteReviewed} onChange={(event)=>setNoteReviewed(event.target.checked)}/><span><strong>Susunan Nota FG sudah gue review</strong><small>Semua card milik {result.mandor}; formula dan pengurang BS terlihat jelas.</small></span></label>
        <button type="button" className="primary-btn handoff-submit" disabled={!editable||selectedRegular.length===0||noteTotal<=0||!noteReviewed} onClick={()=>setNoteStatus('POSTED')}>{noteStatus==='POSTED'?'Nota FG sudah posted':'Post Nota FG ke Payroll'} <Icon name={noteStatus==='POSTED'?'check':'arrow'}/></button>
        <p className="handoff-audit-note">Card yang tidak dipilih tetap aman di antrean. Posted hanya memindahkan susunan ini ke Payroll; backend dan kas belum berubah.</p>
      </aside>
    </section>
  </>
}

type LaundryReadyBatch = {
  id:string; parentId:string; sequence:number; brand:string; model:string; material:string; mandor:string;
  pickupAt:string; sewingDoneAt:string; vendor:string; process:string; qty:number; sizes:QtyTuple; sizeLabels:SizeTuple; note:string
}

type LaundryDelivery = {
  id:string; parentId:string; sequence:number; batchId:string; brand:string; model:string; material:string; mandor:string;
  vendor:string; process:string; sentAt:string; qty:number; sizes:QtyTuple; sizeLabels:SizeTuple;
  good:number; bs:number; goodSizes:QtyTuple; bsSizes:QtyTuple; reversed:number; reversedSizes:QtyTuple; reverseNote?:string
}

const laundryProcesses = ['Stone Wash','Bio Wash','Enzyme Wash']
const laundryRates:Record<string,number> = {'Stone Wash':6500,'Bio Wash':5500,'Enzyme Wash':6000}

const laundryReadySeeds:LaundryReadyBatch[] = [
  {id:'042-02',parentId:'POT-260827-042',sequence:42,brand:'Widie',model:'Kulot Lucy',material:'Lucy',mandor:'Mandor Afat',pickupAt:'27 Agu 2026 · 10:30',sewingDoneAt:'27 Agu 2026 · 15:20',vendor:'Laundry Berkah',process:'Stone Wash',qty:225,sizes:[0,225,0],sizeLabels:['31','32','33'],note:'Maroon · obras rapat'},
  {id:'041-01',parentId:'POT-260826-041',sequence:41,brand:'Widie',model:'Malibu Regular',material:'Malibu',mandor:'Mandor Asep',pickupAt:'26 Agu 2026 · 14:15',sewingDoneAt:'26 Agu 2026 · 18:10',vendor:'Laundry Intan',process:'Bio Wash',qty:244,sizes:[82,81,81],sizeLabels:['28','29','30'],note:'Biru muda · benang senada · obras rapat'},
  {id:'039-01',parentId:'POT-260825-039',sequence:39,brand:'Vivo',model:'Zodiak Jumbo',material:'Zodiak KW',mandor:'Mandor Dedi',pickupAt:'25 Agu 2026 · 09:40',sewingDoneAt:'25 Agu 2026 · 17:45',vendor:'Cemerlang Wash',process:'Enzyme Wash',qty:114,sizes:[38,38,38],sizeLabels:['34','35','36'],note:'Stone · stik bawah 2 jalur'},
]

const laundryDeliverySeeds:LaundryDelivery[] = [
  {id:'LDR-260827-011',parentId:'POT-260826-041',sequence:41,batchId:'041-02',brand:'Widie',model:'Malibu Regular',material:'Malibu',mandor:'Mandor Asep',vendor:'Laundry Intan',process:'Bio Wash',sentAt:'27 Agu 2026 · 08:30',qty:244,sizes:[81,81,82],sizeLabels:['28','29','30'],good:174,bs:6,goodSizes:[58,58,58],bsSizes:[2,2,2],reversed:0,reversedSizes:[0,0,0]},
  {id:'LDR-260826-010',parentId:'POT-260825-039',sequence:39,batchId:'039-02',brand:'Vivo',model:'Zodiak Jumbo',material:'Zodiak KW',mandor:'Mandor Dedi',vendor:'Cemerlang Wash',process:'Enzyme Wash',sentAt:'26 Agu 2026 · 13:10',qty:114,sizes:[38,38,38],sizeLabels:['34','35','36'],good:112,bs:2,goodSizes:[37,37,38],bsSizes:[0,1,1],reversed:0,reversedSizes:[0,0,0]},
  {id:'LDR-260825-009',parentId:'POT-260824-038',sequence:38,batchId:'038-01',brand:'Vivo',model:'Vivo Regular',material:'Denim 12 Oz',mandor:'Mandor Afat',vendor:'Laundry Berkah',process:'Stone Wash',sentAt:'25 Agu 2026 · 11:00',qty:180,sizes:[60,60,60],sizeLabels:['31','32','33'],good:176,bs:4,goodSizes:[59,59,58],bsSizes:[1,1,2],reversed:0,reversedSizes:[0,0,0]},
]

const laundryDigits = (value:string,max:number) => {
  const digits=value.replace(/\D/g,'').replace(/^0+(?=\d)/,'')
  return digits===''?'':String(Math.min(max,Number(digits)))
}

const laundryOutstanding = (delivery:LaundryDelivery) => Math.max(0,delivery.qty-delivery.good-delivery.bs-delivery.reversed)
const laundryReturnedSizes = (delivery:LaundryDelivery):QtyTuple => delivery.goodSizes.map((qty,index)=>qty+delivery.bsSizes[index]) as QtyTuple
const laundryOutstandingSizes = (delivery:LaundryDelivery):QtyTuple => delivery.sizes.map((qty,index)=>Math.max(0,qty-delivery.goodSizes[index]-delivery.bsSizes[index]-delivery.reversedSizes[index])) as QtyTuple

const summarizeLaundryBatch = (deliveries:LaundryDelivery[],batchId:string) => {
  const rows=deliveries.filter((delivery)=>delivery.batchId===batchId)
  const good=rows.reduce((sum,delivery)=>sum+delivery.good,0)
  const bs=rows.reduce((sum,delivery)=>sum+delivery.bs,0)
  const returned=good+bs
  const outside=rows.reduce((sum,delivery)=>sum+laundryOutstanding(delivery),0)
  const reversed=rows.reduce((sum,delivery)=>sum+delivery.reversed,0)
  const goodSizes=([0,1,2].map((index)=>rows.reduce((sum,delivery)=>sum+delivery.goodSizes[index],0)) as QtyTuple)
  const bsSizes=([0,1,2].map((index)=>rows.reduce((sum,delivery)=>sum+delivery.bsSizes[index],0)) as QtyTuple)
  const outsideSizes=([0,1,2].map((index)=>rows.reduce((sum,delivery)=>sum+laundryOutstandingSizes(delivery)[index],0)) as QtyTuple)
  const activeVendors=Array.from(new Set(rows.filter((delivery)=>laundryOutstanding(delivery)>0).map((delivery)=>delivery.vendor)))
  const returnedVendors=Array.from(new Set(rows.filter((delivery)=>delivery.good+delivery.bs>0).map((delivery)=>delivery.vendor)))
  return {good,bs,returned,outside,reversed,goodSizes,bsSizes,outsideSizes,activeVendors,returnedVendors}
}

function makeQcSeed(parent:SewingParentSeed,batch:SewingBatchSeed,summary:ReturnType<typeof summarizeLaundryBatch>):QcSeed {
  const qcSourceSizes=([0,1,2].map((index)=>summary.goodSizes[index]+summary.bsSizes[index]+summary.outsideSizes[index]) as QtyTuple)
  return {
    parentId:parent.id,batchId:batch.id,brand:parent.brand,model:parent.model,material:parent.material,mandor:parent.mandor,
    laundry:[...new Set([...summary.activeVendors,...summary.returnedVendors])].join(' & '),
    sizes:parent.sizes,expected:qcSourceSizes,returnedGoodBySize:summary.goodSizes,returnedBsBySize:summary.bsSizes,stuckBySize:summary.outsideSizes,
  }
}

function buildQcSeeds(deliveries:LaundryDelivery[]):QcSeed[] {
  const batchIds=Array.from(new Set(deliveries.filter((delivery)=>delivery.good+delivery.bs>0).map((delivery)=>delivery.batchId)))
  return batchIds.map((batchId)=>{
    const rows=deliveries.filter((delivery)=>delivery.batchId===batchId)
    const first=rows[0]
    const parent=sewingWipSeeds.find((item)=>item.id===first.parentId)
    const batch=parent?.batches.find((item)=>item.id===batchId)
    if(parent&&batch)return makeQcSeed(parent,batch,summarizeLaundryBatch(deliveries,batchId))
    const goodSizes=([0,1,2].map((index)=>rows.reduce((sum,row)=>sum+row.goodSizes[index],0)) as QtyTuple)
    const bsSizes=([0,1,2].map((index)=>rows.reduce((sum,row)=>sum+row.bsSizes[index],0)) as QtyTuple)
    const stuckBySize=([0,1,2].map((index)=>rows.reduce((sum,row)=>sum+laundryOutstandingSizes(row)[index],0)) as QtyTuple)
    const expected=([0,1,2].map((index)=>goodSizes[index]+bsSizes[index]+stuckBySize[index]) as QtyTuple)
    return {parentId:first.parentId,batchId,brand:first.brand,model:first.model,material:first.material,mandor:first.mandor,laundry:Array.from(new Set(rows.map((row)=>row.vendor))).join(' & '),sizes:first.sizeLabels,expected,returnedGoodBySize:goodSizes,returnedBsBySize:bsSizes,stuckBySize}
  }).sort((a,b)=>b.parentId.localeCompare(a.parentId))
}

const vendorProcess = (vendor:string) => vendor==='Laundry Intan'?'Bio Wash':vendor==='Cemerlang Wash'?'Enzyme Wash':'Stone Wash'

function laundryReadyFromSewingBatch(batchId:string,vendor:string,snapshot?:{qty:number;sizes:QtyTuple}):LaundryReadyBatch|null {
  const parent=sewingWipSeeds.find((item)=>item.batches.some((batch)=>batch.id===batchId))
  const batch=parent?.batches.find((item)=>item.id===batchId)
  if(!parent||!batch)return null
  return {id:batch.id,parentId:parent.id,sequence:parent.sequence,brand:parent.brand,model:parent.model,material:parent.material,mandor:parent.mandor,pickupAt:parent.pickupAt,sewingDoneAt:'27 Agu 2026 · siap kirim',vendor,process:vendorProcess(vendor),qty:snapshot?.qty??batch.qty,sizes:snapshot?.sizes??batch.sizes,sizeLabels:parent.sizes,note:batch.note}
}

const proportionalLaundrySizes = (sizes:QtyTuple,total:number,qty:number):QtyTuple => {
  const raw=sizes.map((size)=>total>0?(size/total)*qty:0)
  const values=raw.map(Math.floor)
  let remainder=qty-values.reduce((sum,value)=>sum+value,0)
  raw.map((value,index)=>({index,fraction:value-values[index]})).sort((a,b)=>b.fraction-a.fraction).forEach(({index})=>{if(remainder>0){values[index]+=1;remainder-=1}})
  return values as QtyTuple
}

const laundryReadyFromDelivery = (delivery:LaundryDelivery,qty:number):LaundryReadyBatch => {
  const source=laundryReadyFromSewingBatch(delivery.batchId,'Belum dipilih')
  const outstandingSizes=laundryOutstandingSizes(delivery)
  return source?{...source,qty,sizes:outstandingSizes,vendor:'Belum dipilih',process:delivery.process}:{
    id:delivery.batchId,parentId:delivery.parentId,sequence:delivery.sequence,brand:delivery.brand,model:delivery.model,material:delivery.material,mandor:delivery.mandor,pickupAt:delivery.sentAt,sewingDoneAt:delivery.sentAt,vendor:'Belum dipilih',process:delivery.process,qty,sizes:outstandingSizes,sizeLabels:delivery.sizeLabels,note:'Dikembalikan dari laundry · pilih tujuan baru',
  }
}

const laundryDeliveryStatus = (delivery:LaundryDelivery) => {
  const received=delivery.good+delivery.bs
  const outstanding=laundryOutstanding(delivery)
  if(delivery.reversed>0&&outstanding===0)return received>0?'Sisa kembali WIP':'Kembali ke WIP'
  return received===0?'Di laundry':outstanding>0?'Kembali sebagian':'Selesai'
}

function LaundryPage({prefill,readyBatches,setReadyBatches,deliveries,setDeliveries,onPosted,onReturnToWip,onOpenQc}:{
  prefill:LaundryPrefill|null
  readyBatches:LaundryReadyBatch[]
  setReadyBatches:(value:LaundryReadyBatch[]|((current:LaundryReadyBatch[])=>LaundryReadyBatch[]))=>void
  deliveries:LaundryDelivery[]
  setDeliveries:(value:LaundryDelivery[]|((current:LaundryDelivery[])=>LaundryDelivery[]))=>void
  onPosted:(batchIds:string[])=>void
  onReturnToWip:(batchId:string,vendor:string,qty:number)=>void
  onOpenQc:(parentId:string,batchId:string)=>void
}) {
  const initialBatch=readyBatches.find((batch)=>batch.id===prefill?.batchId)??readyBatches[0]
  const [activeTab,setActiveTab]=useState<LaundryView>(prefill?.view??'send')
  const [vendorFilter,setVendorFilter]=useState(prefill?.vendor??'Semua laundry')
  const [query,setQuery]=useState('')
  const [selectedIds,setSelectedIds]=useState<string[]>(initialBatch?[initialBatch.id]:[])
  const [sendSizeInputs,setSendSizeInputs]=useState<Record<string,[string,string,string]>>(()=>Object.fromEntries(readyBatches.map((batch)=>[batch.id,batch.sizes.map(String) as [string,string,string]])))
  const [selectedProcess,setSelectedProcess]=useState(initialBatch?.process??'Stone Wash')
  const [sentAt,setSentAt]=useState('2026-08-27T16:00')
  const [sendNote,setSendNote]=useState('')
  const [notice,setNotice]=useState('')
  const [returnInputs,setReturnInputs]=useState<Record<string,{good:[string,string,string];bs:[string,string,string]}>>({})
  const [returnTimes,setReturnTimes]=useState<Record<string,string>>({})
  const [pendingReverse,setPendingReverse]=useState<LaundryDelivery|null>(null)
  const vendorOptions=['Semua laundry',...laundryVendorNames]

  const visibleReady=readyBatches.filter((batch)=>batch.vendor!=='Belum dipilih').filter((batch)=>vendorFilter==='Semua laundry'||batch.vendor===vendorFilter).filter((batch)=>`${batch.parentId} ${batch.id} ${batch.model} ${batch.material} ${batch.mandor} ${batch.vendor} ${batch.note}`.toLowerCase().includes(query.toLowerCase())).sort((a,b)=>b.sequence-a.sequence)
  const groupedReady=Array.from(visibleReady.reduce((groups,batch)=>groups.set(batch.parentId,[...(groups.get(batch.parentId)??[]),batch]),new Map<string,LaundryReadyBatch[]>()).entries())
  const selectedBatches=readyBatches.filter((batch)=>selectedIds.includes(batch.id))
  const selectedParent=selectedBatches[0]?.parentId??''
  const selectedVendor=selectedBatches[0]?.vendor??''
  const selectedTotal=selectedBatches.reduce((sum,batch)=>sum+(sendSizeInputs[batch.id]??batch.sizes.map(String)).reduce((subtotal,value)=>subtotal+cellQuantity(value),0),0)
  const estimatedCost=selectedTotal*(laundryRates[selectedProcess]??0)
  const visibleDeliveries=deliveries.filter((delivery)=>vendorFilter==='Semua laundry'||delivery.vendor===vendorFilter).filter((delivery)=>`${delivery.id} ${delivery.parentId} ${delivery.batchId} ${delivery.model} ${delivery.material} ${delivery.mandor} ${delivery.vendor}`.toLowerCase().includes(query.toLowerCase())).sort((a,b)=>b.sequence-a.sequence)
  const outsideQty=deliveries.reduce((sum,delivery)=>sum+laundryOutstanding(delivery),0)
  const partialCount=deliveries.filter((delivery)=>laundryDeliveryStatus(delivery)==='Kembali sebagian').length
  const totalBs=deliveries.reduce((sum,delivery)=>sum+delivery.bs,0)

  const toggleBatch=(batch:LaundryReadyBatch)=>{
    setNotice('')
    setSelectedIds((current)=>{
      if(current.includes(batch.id))return current.filter((id)=>id!==batch.id)
      const currentBatch=readyBatches.find((item)=>current.includes(item.id))
      if(currentBatch&&(currentBatch.parentId!==batch.parentId||currentBatch.vendor!==batch.vendor)){setSelectedProcess(batch.process);return[batch.id]}
      setSelectedProcess(batch.process)
      return[...current,batch.id]
    })
  }

  const postDelivery=()=>{
    const posted=selectedBatches.map((batch)=>{
      const sizes=(sendSizeInputs[batch.id]??batch.sizes.map(String)).map((value,index)=>Math.min(batch.sizes[index],cellQuantity(value))) as QtyTuple
      return{batch,sizes,qty:sizes.reduce((sum,value)=>sum+value,0)}
    }).filter((row)=>row.qty>0)
    if(posted.length===0)return
    const startNo=deliveries.length+12
    const [physicalDate,physicalTime]=sentAt.split('T')
    const physicalSentAt=physicalDate==='2026-08-27'?`27 Agu 2026 · ${physicalTime}`:`${physicalDate} · ${physicalTime}`
    setDeliveries((current)=>[
      ...posted.map(({batch,qty,sizes},index)=>({id:`LDR-260827-${String(startNo+index).padStart(3,'0')}`,parentId:batch.parentId,sequence:batch.sequence,batchId:batch.id,brand:batch.brand,model:batch.model,material:batch.material,mandor:batch.mandor,vendor:batch.vendor,process:selectedProcess,sentAt:physicalSentAt,qty,sizes,sizeLabels:batch.sizeLabels,good:0,bs:0,goodSizes:[0,0,0] as QtyTuple,bsSizes:[0,0,0] as QtyTuple,reversed:0,reversedSizes:[0,0,0] as QtyTuple})),
      ...current,
    ])
    const sentById=new Map(posted.map((row)=>[row.batch.id,row.sizes]))
    setReadyBatches((current)=>current.flatMap((batch)=>{const sent=sentById.get(batch.id)??[0,0,0];const sizes=batch.sizes.map((value,index)=>Math.max(0,value-sent[index])) as QtyTuple;const remaining=sizes.reduce((sum,value)=>sum+value,0);return remaining<=0?[]:[{...batch,qty:remaining,sizes}]}))
    setSendSizeInputs((current)=>{const next={...current};posted.forEach(({batch,sizes})=>{const remaining=batch.sizes.map((value,index)=>Math.max(0,value-sizes[index])) as QtyTuple;if(remaining.some((value)=>value>0))next[batch.id]=remaining.map(String) as [string,string,string];else delete next[batch.id]});return next})
    onPosted(posted.map(({batch})=>batch.id))
    setSelectedIds([])
    setNotice(`${posted.reduce((sum,row)=>sum+row.qty,0)} pcs dicatat keluar ke ${selectedVendor}.`)
    setActiveTab('return')
  }

  const emptyReturnDraft=()=>({good:['','',''] as [string,string,string],bs:['','',''] as [string,string,string]})
  const updateReturn=(delivery:LaundryDelivery,sizeIndex:number,field:'good'|'bs',raw:string)=>{
    const outstanding=laundryOutstandingSizes(delivery)[sizeIndex]
    setReturnInputs((current)=>{
      const row=current[delivery.id]??emptyReturnDraft()
      const other=cellQuantity(row[field==='good'?'bs':'good'][sizeIndex])
      const nextField=[...row[field]] as [string,string,string]
      nextField[sizeIndex]=laundryDigits(raw,Math.max(0,outstanding-other))
      return{...current,[delivery.id]:{...row,[field]:nextField}}
    })
  }

  const postReturn=(delivery:LaundryDelivery)=>{
    const values=returnInputs[delivery.id]??emptyReturnDraft()
    const goodSizes=values.good.map(cellQuantity) as QtyTuple
    const bsSizes=values.bs.map(cellQuantity) as QtyTuple
    const good=goodSizes.reduce((sum,value)=>sum+value,0);const bs=bsSizes.reduce((sum,value)=>sum+value,0)
    if(good+bs<=0)return
    setDeliveries((current)=>current.map((item)=>item.id===delivery.id?{...item,good:item.good+good,bs:item.bs+bs,goodSizes:item.goodSizes.map((value,index)=>value+goodSizes[index]) as QtyTuple,bsSizes:item.bsSizes.map((value,index)=>value+bsSizes[index]) as QtyTuple}:item))
    setReturnInputs((current)=>({...current,[delivery.id]:emptyReturnDraft()}))
    setNotice(`${good} Good + ${bs} BS diterima dari ${delivery.vendor}.`)
  }

  const confirmReverse=()=>{
    if(!pendingReverse)return
    const outstanding=laundryOutstanding(pendingReverse)
    if(outstanding<=0){setPendingReverse(null);return}
    const reverseSizes=laundryOutstandingSizes(pendingReverse)
    setDeliveries((current)=>current.map((delivery)=>delivery.id===pendingReverse.id?{...delivery,reversed:delivery.reversed+outstanding,reversedSizes:delivery.reversedSizes.map((value,index)=>value+reverseSizes[index]) as QtyTuple,reverseNote:'Pindah laundry di detik akhir'}:delivery))
    const restored=laundryReadyFromDelivery(pendingReverse,outstanding)
    setReadyBatches((current)=>{
      const existing=current.find((batch)=>batch.id===pendingReverse.batchId)
      return existing?current.map((batch)=>{
        if(batch.id!==pendingReverse.batchId)return batch
        const nextQty=batch.qty+outstanding
        const source=laundryReadyFromSewingBatch(batch.id,'Belum dipilih')
        return {...batch,qty:nextQty,sizes:source?proportionalLaundrySizes(source.sizes,source.qty,nextQty):batch.sizes,vendor:'Belum dipilih'}
      }):[restored,...current]
    })
    const existingReady=readyBatches.find((batch)=>batch.id===pendingReverse.batchId)
    const restoredSizes=(existingReady?existingReady.sizes.map((value,index)=>value+reverseSizes[index]):reverseSizes) as QtyTuple
    setSendSizeInputs((current)=>({...current,[pendingReverse.batchId]:restoredSizes.map(String) as [string,string,string]}))
    const batchId=pendingReverse.batchId
    const vendor=pendingReverse.vendor
    setPendingReverse(null)
    onReturnToWip(batchId,vendor,outstanding)
  }

  return <>
    <section className="hero-copy compact laundry-hero"><div className="eyebrow">PRODUKSI · SETELAH SEWING</div><h1>Laundry</h1><p>Kirim Batch Distribusi yang jahitannya sudah penuh, lalu catat Good dan BS ketika kembali. Urutannya tetap mengikuti Batch Produksi.</p></section>
    <section className="laundry-kpi-grid">
      <div className="panel"><span>SIAP DIKIRIM</span><strong>{readyBatches.reduce((sum,batch)=>sum+batch.qty,0)} pcs</strong><small>{readyBatches.length} batch jahit</small></div>
      <div className="panel"><span>SEDANG DI LUAR</span><strong>{outsideQty} pcs</strong><small>{deliveries.filter((item)=>laundryOutstanding(item)>0).length} surat kirim aktif</small></div>
      <div className="panel"><span>KEMBALI SEBAGIAN</span><strong>{partialCount} kiriman</strong><small>tetap terbuka sampai habis</small></div>
      <div className="panel alert"><span>LAUNDRY BS</span><strong>{totalBs} pcs</strong><small>langsung masuk kasus BS</small></div>
    </section>
    {notice&&<div className="laundry-notice"><Icon name="check"/><strong>{notice}</strong></div>}
    <section className="panel laundry-workspace">
      <div className="laundry-toolbar">
        <div className="laundry-tabs"><button className={activeTab==='send'?'active':''} onClick={()=>{setActiveTab('send');setNotice('')}}><Icon name="arrow"/> Kirim ke laundry</button><button className={activeTab==='return'?'active':''} onClick={()=>{setActiveTab('return');setNotice('')}}><Icon name="boxes"/> Terima kembali</button></div>
        <label className="laundry-search"><Icon name="search"/><input value={query} onChange={(event)=>setQuery(event.target.value)} placeholder="Cari Potongan, batch, bahan..."/></label>
        <div className="laundry-vendors">{vendorOptions.map((vendor)=><button type="button" className={vendorFilter===vendor?'active':''} onClick={()=>setVendorFilter(vendor)} key={vendor}>{vendor}</button>)}</div>
      </div>

      {activeTab==='send'?<div className="laundry-send-layout">
        <div className="laundry-ready-pane">
          <div className="laundry-section-head"><div><span>SIAP BERANGKAT</span><h2>Pilih batch selesai jahit</h2><p>Satu surat kirim hanya berisi satu Batch Produksi dan satu laundry.</p></div><b>{visibleReady.length} batch</b></div>
          <div className="laundry-parent-list" data-keyboard-grid>{groupedReady.map(([parentId,batches],groupIndex)=>{const first=batches[0];return <article className="laundry-parent-card" key={parentId}>
            <header><span>{String(groupIndex+1).padStart(2,'0')}</span><div><small>{first.brand} · BATCH PRODUKSI</small><h3>{parentId} · {first.model}</h3><p className="laundry-mandor-line"><Icon name="user"/><span><small>MANDOR</small><strong>{first.mandor}</strong></span><em>{first.material}</em></p></div><div><strong>{batches.reduce((sum,batch)=>sum+batch.qty,0)} pcs</strong><small>{first.vendor}</small></div></header>
            <div className="laundry-batch-rows">{batches.map((batch,batchIndex)=>{const selected=selectedIds.includes(batch.id);const foreign=selectedBatches.length>0&&(selectedParent!==batch.parentId||selectedVendor!==batch.vendor);return <div className={`laundry-batch-row ${selected?'selected':''}`} key={batch.id}>
              <button type="button" className="laundry-batch-select" onClick={()=>toggleBatch(batch)}><span className="laundry-check">{selected&&<Icon name="check"/>}</span><div><span>BATCH {batch.id}</span><strong>{batch.note}</strong><small>Selesai {batch.sewingDoneAt}</small></div><b>{batch.qty} pcs</b></button>
              <div className="laundry-size-pills">{batch.sizeLabels.map((size,index)=>batch.sizes[index]>0&&<span key={size}>Size <b>{size}</b> · {batch.sizes[index]}</span>)}</div>
              {selected&&<div className="laundry-send-by-size"><span>QTY DIKIRIM PER SIZE</span><div>{batch.sizeLabels.map((size,sizeIndex)=><label key={size}><small>SIZE {size}</small><input inputMode="numeric" data-grid-row={groupIndex*100+batchIndex} data-grid-col={sizeIndex} value={(sendSizeInputs[batch.id]??batch.sizes.map(String))[sizeIndex]} onFocus={(event)=>event.currentTarget.select()} onChange={(event)=>setSendSizeInputs((current)=>{const row=[...(current[batch.id]??batch.sizes.map(String))] as [string,string,string];row[sizeIndex]=laundryDigits(event.target.value,batch.sizes[sizeIndex]);return{...current,[batch.id]:row}})}/><em>/ {batch.sizes[sizeIndex]}</em></label>)}</div></div>}
              {foreign&&!selected&&<small className="laundry-switch-note">Memilih ini akan pindah ke surat kirim Potongan tersebut.</small>}
            </div>})}</div>
          </article>})}{groupedReady.length===0&&<div className="laundry-empty"><Icon name="search"/><strong>Batch tidak ditemukan</strong><small>Coba ganti laundry atau kata pencarian.</small></div>}</div>
        </div>
        <aside className="laundry-ticket"><div className="laundry-section-head"><div><span>SURAT KIRIM</span><h2>Review sebelum keluar</h2></div></div>
          {selectedBatches.length>0?<div className="laundry-ticket-content">
            <div className="laundry-destination"><span>TUJUAN TERPILIH</span><strong>{selectedVendor}</strong><small>{selectedParent} · {selectedBatches[0].material}</small></div>
            <label><span>PROSES LAUNDRY</span><select value={selectedProcess} onChange={(event)=>setSelectedProcess(event.target.value)}>{laundryProcesses.map((process)=><option value={process} key={process}>{process}</option>)}</select></label>
            <label><span>WAKTU FISIK DIKIRIM</span><input type="datetime-local" value={sentAt} onChange={(event)=>setSentAt(event.target.value)}/></label>
            <label><span>CATATAN · OPSIONAL</span><input value={sendNote} onChange={(event)=>setSendNote(event.target.value)} placeholder="Contoh: pisahkan warna maroon"/></label>
            <div className="laundry-cost-review"><p><span>Batch terpilih</span><b>{selectedBatches.length} batch</b></p><p><span>Qty dikirim</span><b>{selectedTotal} pcs</b></p><p><span>Tarif estimasi</span><b>{money(laundryRates[selectedProcess]??0)} / pcs</b></p><div><span>ESTIMASI BIAYA</span><strong>{money(estimatedCost)}</strong></div></div>
            <p className="laundry-estimate-note">Tarif disimpan sebagai snapshot estimasi. Stok baru berpindah dari Sewing ke Laundry saat pengiriman diposting.</p>
            <div className="laundry-ticket-actions"><button type="button" className="soft-btn" onClick={()=>setNotice('Draft surat kirim tersimpan di layar ini.')}>Simpan draft</button><button type="button" className="primary-btn" disabled={selectedTotal<=0} onClick={postDelivery}>Catat dikirim <Icon name="arrow"/></button></div>
          </div>:<div className="laundry-empty ticket"><Icon name="boxes"/><strong>Belum ada batch dipilih</strong><small>Tekan batch di kiri. Surat kirim otomatis mengikuti Batch Produksi dan laundry tujuan.</small></div>}
        </aside>
      </div>:<div className="laundry-return-pane">
        <div className="laundry-section-head"><div><span>BARANG KEMBALI</span><h2>Good + BS dari laundry</h2><p>Boleh kembali sebagian. Good lanjut ke QC; BS otomatis menjadi kasus terbuka.</p></div><b>{visibleDeliveries.length} surat kirim</b></div>
        <div className="laundry-return-list">{visibleDeliveries.map((delivery,index)=>{
          const received=delivery.good+delivery.bs
          const outstanding=laundryOutstanding(delivery)
          const outstandingSizes=laundryOutstandingSizes(delivery)
          const returnedSizes=laundryReturnedSizes(delivery)
          const progress=Math.round((received+delivery.reversed)/Math.max(1,delivery.qty)*100)
          const status=laundryDeliveryStatus(delivery)
          const values=returnInputs[delivery.id]??emptyReturnDraft()
          const inputGood=values.good.map(cellQuantity) as QtyTuple
          const inputBs=values.bs.map(cellQuantity) as QtyTuple
          const inputTotal=inputGood.reduce((sum,value)=>sum+value,0)+inputBs.reduce((sum,value)=>sum+value,0)
          const reversedStatus=status==='Kembali ke WIP'||status==='Sisa kembali WIP'
          return <article className={`laundry-return-card ${reversedStatus?'reversed':''}`} key={delivery.id}>
          <header><span>{String(index+1).padStart(2,'0')}</span><div><small>{delivery.brand} · {delivery.id}</small><h3>{delivery.parentId} · Batch {delivery.batchId}</h3><p>{delivery.model} · {delivery.material}</p></div><em className={status==='Selesai'?'done':status==='Kembali sebagian'?'partial':reversedStatus?'reversed':''}>{status}</em><div><strong>{delivery.vendor}</strong><small>{delivery.process}</small></div></header>
          <div className="laundry-return-body"><div className="laundry-return-facts"><div className="laundry-mandor-hero"><Icon name="user"/><span><small>MANDOR PENANGGUNG JAWAB</small><strong>{delivery.mandor}</strong></span></div><div className="laundry-counts"><span><small>DIKIRIM</small><strong>{delivery.qty} pcs</strong></span><span><small>SUDAH KEMBALI</small><strong>{received} pcs</strong></span><span><small>MASIH DI LUAR</small><strong>{outstanding} pcs</strong></span></div><div className="laundry-progress"><span style={{width:`${progress}%`}}/></div><p><Icon name="calendar"/> Dikirim {delivery.sentAt}</p>{received>0&&<><small>Akumulasi: <b className="good">{delivery.good} Good</b> · <b className="bs">{delivery.bs} BS</b></small><button type="button" className="laundry-open-qc" onClick={()=>onOpenQc(delivery.parentId,delivery.batchId)}><Icon name="audit"/><span><strong>Buka QC & Final SKU</strong><small>{received} pcs sudah bisa diperiksa sekarang</small></span><Icon name="arrow"/></button></>}{delivery.reversed>0&&<small className="reversed-note"><b>{delivery.reversed} pcs kembali ke WIP</b> · {delivery.reverseNote}</small>}{outstanding>0&&<button type="button" className="laundry-reverse-btn" onClick={()=>setPendingReverse(delivery)}><Icon name="reset"/><span><strong>Kembalikan ke WIP</strong><small>{outstanding} pcs bisa pilih laundry lain</small></span></button>}</div>
            {outstanding>0?<div className="laundry-return-entry size-mode" data-keyboard-grid><div className="laundry-return-entry-head"><span>TERIMA PER SIZE</span><small>Good ke QC dan Stuck dihitung persis per ukuran.</small></div><div className="laundry-return-size-head"><span>Size</span><span>Dikirim</span><span>Kembali</span><span>Good → QC</span><span>BS</span><span>Stuck sesudah</span></div><div className="laundry-return-size-rows">{delivery.sizeLabels.map((size,sizeIndex)=><div className="laundry-return-size-row" key={size}><strong>{size}</strong><span>{delivery.sizes[sizeIndex]}</span><span>{returnedSizes[sizeIndex]}</span><label><input inputMode="numeric" data-grid-row={sizeIndex} data-grid-col={0} value={values.good[sizeIndex]} onFocus={(event)=>event.currentTarget.select()} onChange={(event)=>updateReturn(delivery,sizeIndex,'good',event.target.value)} placeholder="0"/></label><label className="bs"><input inputMode="numeric" data-grid-row={sizeIndex} data-grid-col={1} value={values.bs[sizeIndex]} onFocus={(event)=>event.currentTarget.select()} onChange={(event)=>updateReturn(delivery,sizeIndex,'bs',event.target.value)} placeholder="0"/></label><strong className="stuck">{Math.max(0,outstandingSizes[sizeIndex]-inputGood[sizeIndex]-inputBs[sizeIndex])}</strong></div>)}</div><label className="return-time"><span>WAKTU FISIK KEMBALI</span><input type="datetime-local" value={returnTimes[delivery.id]??'2026-08-27T17:30'} onChange={(event)=>setReturnTimes((current)=>({...current,[delivery.id]:event.target.value}))}/></label><div className="laundry-return-action"><span>Total input <b>{inputTotal} pcs</b> · sisa <b>{Math.max(0,outstanding-inputTotal)} pcs</b></span><button type="button" className="primary-btn" disabled={inputTotal<=0} onClick={()=>postReturn(delivery)}>Catat kembali <Icon name="arrow"/></button></div></div>:<div className="laundry-return-done"><Icon name={delivery.reversed>0?'reset':'check'}/><strong>{delivery.reversed>0?'Qty aktif sudah kembali ke WIP':'Pengiriman selesai'}</strong><small>{delivery.reversed>0?`${delivery.reversed} pcs siap dipilihkan laundry baru · histori lama tetap ada`:`${delivery.good} Good sudah bisa dibuka di QC · ${delivery.bs} BS tercatat`}</small></div>}
          </div>
        </article>})}</div>
      </div>}
    </section>
    {pendingReverse&&<div className="wip-confirm-layer" role="presentation"><section className="wip-confirm-dialog laundry-reverse-dialog" role="alertdialog" aria-modal="true" aria-labelledby="reverse-laundry-title"><div className="wip-confirm-icon reverse"><Icon name="reset"/></div><div><span>REVERSE PENGIRIMAN</span><h2 id="reverse-laundry-title">Kembalikan ke WIP?</h2><p><strong>{laundryOutstanding(pendingReverse)} pcs</strong> yang masih di {pendingReverse.vendor} akan muncul lagi di WIP dan bisa langsung dipilihkan laundry lain. {pendingReverse.good+pendingReverse.bs>0&&`${pendingReverse.good+pendingReverse.bs} pcs yang sudah kembali tetap tercatat.`}</p><small>Jejak surat kirim lama tidak dihapus; statusnya berubah menjadi Kembali ke WIP.</small></div><div className="wip-confirm-actions"><button type="button" className="soft-btn" onClick={()=>setPendingReverse(null)}>Jangan</button><button type="button" className="primary-btn reverse" onClick={confirmReverse}>Ya, kembali ke WIP <Icon name="arrow"/></button></div></section></div>}
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
      <div className="composition-column"><div className="composition-head"><div><strong>Jumlah per size</strong><span>Boleh ketik PCS, lusin, atau campuran.</span></div></div><div className="size-grid" data-keyboard-grid>{sizes.map((row,index)=><div className="size-card" key={row.size}><div><strong>Size {row.size}</strong><span>stok {row.stock} pcs</span></div><input inputMode="text" data-grid-row={index} data-grid-col={0} value={row.input} placeholder="8 atau 1 lusin" onChange={(e)=>{ const raw=e.target.value; const next=[...sizes]; next[index]={...row,input:raw,qty:parseQty(raw,'pcs')}; setSizes(next) }}/><small className="parsed-qty">{row.qty} pcs · {dozenPieces(row.qty)}</small></div>)}</div><div className="sales-total-strip"><span>TOTAL DARI SIZE</span><strong>{composed} pcs</strong><small>{dozenPieces(composed)}</small></div><div className={`validation ${compositionOk&&stockEnough?'success':'error'}`}><Icon name={compositionOk&&stockEnough?'check':'filter'} /> {!compositionOk?'Isi minimal satu size.':stockEnough?'Jumlah otomatis dijumlahkan dan stok mencukupi.':'Ada size yang melebihi stok.'}</div></div></div>
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
      <div className="mutation-list">{visibleRows.map((movement,idx)=>{ const product=productCatalog.find((item)=>productKey(item)===movementProductKey(movement)); const sizes=product?.sizes??['28','29','30']; const movementTotal=movement.delta.reduce((s,q)=>s+q,0); const beforeTotal=movement.before.reduce((s,q)=>s+q,0); const afterTotal=movement.after.reduce((s,q)=>s+q,0); return <div className={`mutation-row mutation-collapsible ${draggedId===movement.id?'is-dragging':''}`} key={movement.id} draggable onDragStart={()=>setDraggedId(movement.id)} onDragOver={(e)=>e.preventDefault()} onDrop={()=>dropOn(movement.id)} onDragEnd={()=>setDraggedId(null)}><div className="drag-grip" title="Ubah urutan buku"><Icon name="drag" /></div><div className="order-no">{String(idx+1).padStart(2,'0')}</div><div className="mutation-main"><div className="mutation-brand-row"><strong className="mutation-brand">{movement.brand}</strong><span className="type-pill">{movement.type}</span></div><div className="mutation-sku-row"><b>SKU {movement.sku}</b><span>{product ? `${product.name} · ${product.color}` : 'Deskripsi barang'}</span></div><p>{movement.ref} · {movement.customer??movement.note}</p><small>{movement.date} · {movement.id}</small></div><div className="mutation-delta">{movement.delta.map((delta,index)=><span className="size-book-flow" key={index}><small className="size-book-title">SIZE {sizes[index]}</small><div className="book-step opening"><label>Saldo awal</label><strong>{movement.before[index]} pcs</strong><small>{dozenPieces(movement.before[index])}</small></div><div className="book-step change"><label>Mutasi</label><strong className={delta<0?'neg':delta>0?'pos':''}>{delta>0?'+':''}{delta} pcs</strong><small>{dozenPieces(Math.abs(delta))}</small></div><div className="book-step closing"><label>Saldo akhir</label><strong>{movement.after[index]} pcs</strong><small>{dozenPieces(movement.after[index])}</small></div></span>)}</div><div className="mutation-total"><span className="total-book-title">TOTAL {movement.brand} · {movement.sku}</span><div className="total-book-step"><label>Saldo awal</label><strong>{beforeTotal} pcs</strong><small>{dozenPieces(beforeTotal)}</small></div><div className="total-book-step change"><label>Mutasi</label><strong className={movementTotal<0?'neg':'pos'}>{movementTotal>0?'+':''}{movementTotal} pcs</strong><small>{dozenPieces(Math.abs(movementTotal))}</small></div><div className="total-book-step closing"><label>Saldo akhir</label><strong>{afterTotal} pcs</strong><small>{dozenPieces(afterTotal)}</small></div></div><div className="reorder"><button aria-label="Naikkan urutan" onClick={()=>moveVisible(movement.id,-1,visibleIds)} disabled={idx===0}><Icon name="up" /></button><button aria-label="Turunkan urutan" onClick={()=>moveVisible(movement.id,1,visibleIds)} disabled={idx===visibleRows.length-1}><Icon name="down" /></button></div></div>})}{visibleRows.length===0&&<div className="catalog-empty"><Icon name="filter" /><strong>Tidak ada mutasi di buku {bookName}</strong><small>Cek merek yang dipilih atau ubah filter.</small></div>}</div>
    </div>
  </>
}

function Placeholder() { return <div className="panel placeholder"><div className="placeholder-icon">◇</div><h2>Fondasinya sudah disiapkan.</h2><p>Modul ini berikutnya akan mengikuti flow bisnis yang sama: informasi penting terlihat sebelum user menekan tombol yang mengubah uang atau stok.</p></div> }

export default App
