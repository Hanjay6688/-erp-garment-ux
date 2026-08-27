import { Fragment, useMemo, useState } from 'react'
import {
  ArrowLeft, ArrowRight, CalendarDays, Check, ChevronDown, ChevronUp, Database,
  Factory, GripVertical, LayoutDashboard, Layers3, ListFilter, Menu, Package,
  ReceiptText, RotateCcw, Scissors, Search, ShieldCheck, SlidersHorizontal,
  UserRound, WalletCards, Warehouse, X,
} from 'lucide-react'
import type { LucideIcon } from 'lucide-react'

type Page = 'dashboard' | 'sales' | 'stock-card' | 'movements' | 'placeholder'
type NavSection = 'Produksi' | 'Gudang' | 'Penjualan' | 'Keuangan' | 'Master Data'

type SizeRow = { size: string; stock: number; qty: number; input: string }

type Movement = {
  id: string
  sku: string
  brand: string
  customer: string | null
  date: string
  ref: string
  type: string
  note: string
  delta: [number, number, number]
  balance: [number, number, number]
}

type Product = {
  code: string
  range: string
  name: string
  color: string
  brand: string
  sizes: [string, string, string]
  stocks: [number, number, number]
  location: string
  grade: string
}

const productCatalog: Product[] = [
  { code: '73001', range: '28–30', name: 'Denim Classic', color: 'Indigo', brand: 'Atelier', sizes: ['28','29','30'], stocks: [96,84,108], location: 'Gudang FG Utama', grade: 'Good' },
  { code: '73002', range: '31–33', name: 'Denim Regular', color: 'Washed Blue', brand: 'Atelier', sizes: ['31','32','33'], stocks: [72,60,48], location: 'Gudang FG Utama', grade: 'Good' },
  { code: '73003', range: '34–36', name: 'Denim Relaxed', color: 'Charcoal', brand: 'Atelier', sizes: ['34','35','36'], stocks: [36,42,54], location: 'Gudang FG Utama', grade: 'Good' },
  { code: '73004', range: '28–30', name: 'Straight Fit', color: 'Deep Black', brand: 'Rivet', sizes: ['28','29','30'], stocks: [60,72,66], location: 'Gudang FG Utama', grade: 'Good' },
  { code: '73005', range: '31–33', name: 'Tapered Core', color: 'Mid Blue', brand: 'Rivet', sizes: ['31','32','33'], stocks: [48,54,42], location: 'Gudang FG Cadangan', grade: 'Good' },
  { code: '73006', range: '34–36', name: 'Workwear Loose', color: 'Stone', brand: 'Rivet', sizes: ['34','35','36'], stocks: [24,30,36], location: 'Gudang FG Cadangan', grade: 'BS' },
  { code: '73007', range: '28–30', name: 'Daily Slim', color: 'Dark Navy', brand: 'Forma', sizes: ['28','29','30'], stocks: [84,78,90], location: 'Gudang FG Utama', grade: 'Good' },
  { code: '73008', range: '31–33', name: 'Daily Regular', color: 'Vintage Blue', brand: 'Forma', sizes: ['31','32','33'], stocks: [42,36,48], location: 'Gudang FG Cadangan', grade: 'BS' },
]

const productBrands = Array.from(new Set(productCatalog.map((product) => product.brand)))
const productRanges = Array.from(new Set(productCatalog.map((product) => product.range)))
const productSizes = Array.from(new Set(productCatalog.flatMap((product) => product.sizes)))
const stockLocations = Array.from(new Set(productCatalog.map((product) => product.location)))
const stockGrades = Array.from(new Set(productCatalog.map((product) => product.grade)))

const nav: Record<NavSection, string[]> = {
  Produksi: ['Pesanan Produksi', 'Potongan & Roll', 'Mandor & WIP', 'Laundry', 'QC & Final SKU', 'Barang BS & Rework'],
  Gudang: ['Ringkasan Gudang', 'Pembelian & Penerimaan', 'Bahan & Roll', 'Aksesori', 'Ringkasan Barang Jadi', 'Mutasi Barang Jadi', 'Kartu Stok FG', 'Retur & Penyesuaian'],
  Penjualan: ['Penjualan & Invoice', 'Alokasi Barang Jadi', 'Retur Penjualan', 'Pembayaran Pelanggan', 'Riwayat Pelanggan'],
  Keuangan: ['Ringkasan Keuangan', 'Kas & Bank', 'Hutang Supplier & Vendor', 'Piutang Pelanggan', 'Payroll & Kasbon', 'HPP & Rekalkulasi', 'Jurnal & Transaksi Lain', 'Laporan & Tutup Buku'],
  'Master Data': ['Produk & SKU', 'Pelanggan', 'Supplier & Vendor', 'Mandor & Pekerja', 'Gudang & Lokasi'],
}

const initialMovements: Movement[] = [
  { id: 'MV-1048', sku: '73001', brand: 'Atelier', customer: 'Nusantara Fashion', date: '27 Agu 2026 · 13:44', ref: 'INV-260827-019', type: 'Penjualan', note: 'Nusantara Fashion', delta: [-8, -8, -8], balance: [96, 84, 108] },
  { id: 'MV-1047', sku: '73001', brand: 'Atelier', customer: null, date: '27 Agu 2026 · 10:22', ref: 'FG-260827-006', type: 'QC → FG', note: 'PO-260812-031', delta: [24, 24, 24], balance: [104, 92, 116] },
  { id: 'MV-1046', sku: '73001', brand: 'Atelier', customer: 'Sumber Denim', date: '26 Agu 2026 · 17:06', ref: 'INV-260826-027', type: 'Penjualan', note: 'Sumber Denim', delta: [-12, -8, -4], balance: [80, 68, 92] },
  { id: 'MV-1045', sku: '73001', brand: 'Atelier', customer: null, date: '26 Agu 2026 · 14:10', ref: 'ADJ-260826-004', type: 'Penyesuaian', note: 'Selisih opname disetujui owner', delta: [0, -1, 0], balance: [92, 76, 96] },
]

const chronologicalMovements = [...initialMovements].reverse()

const money = (value: number) => new Intl.NumberFormat('id-ID', { style: 'currency', currency: 'IDR', maximumFractionDigits: 0 }).format(value)
const dozenPieces = (pcs: number) => `${Math.floor(Math.max(0, pcs) / 12)} lusin · ${Math.max(0, pcs) % 12} potong`

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
    dashboard: LayoutDashboard,
    Produksi: Factory,
    Gudang: Warehouse,
    Penjualan: ReceiptText,
    Keuangan: WalletCards,
    'Master Data': Database,
    audit: ShieldCheck,
    search: Search,
    back: ArrowLeft,
    stock: Layers3,
    check: Check,
    menu: Menu,
    up: ChevronUp,
    down: ChevronDown,
    reset: RotateCcw,
    filter: SlidersHorizontal,
    calendar: CalendarDays,
    user: UserRound,
    arrow: ArrowRight,
    drag: GripVertical,
    close: X,
    chevron: ChevronDown,
    brand: Scissors,
    product: Package,
    list: ListFilter,
  }
  const Glyph = icons[name] ?? Package
  return <Glyph className="icon" strokeWidth={1.8} aria-hidden="true" />
}

function MultiCheckFilter({ label, options, selected, onChange }: {
  label: string
  options: string[]
  selected: string[]
  onChange: (values: string[]) => void
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
        <div className="filter-bulk">
          <label><input type="checkbox" checked={allSelected} onChange={() => onChange(allSelected ? [] : [...options])} /> Pilih semua</label>
          <button onClick={() => onChange([])}>Kosongkan</button>
        </div>
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
    { size: '28', stock: 96, qty: 8, input: '8' },
    { size: '29', stock: 84, qty: 8, input: '8' },
    { size: '30', stock: 108, qty: 8, input: '8' },
  ])
  const [movements, setMovements] = useState(chronologicalMovements)

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

  const title = page === 'dashboard' ? 'Ringkasan bisnis' : page === 'sales' ? 'Input Penjualan' : page === 'stock-card' ? 'Kartu Stok FG' : page === 'movements' ? 'Mutasi Barang Jadi' : 'Modul ERP'

  const chooseSubmenu = (label: string) => {
    if (label === 'Penjualan & Invoice') setPage('sales')
    else if (label === 'Kartu Stok FG') setPage('stock-card')
    else if (label === 'Mutasi Barang Jadi') setPage('movements')
    else setPage('placeholder')
    setMobileNav(false)
  }

  return (
    <div className="app-shell">
      <aside className={`sidebar ${mobileNav ? 'sidebar-open' : ''}`}>
        <div className="brand-row">
          <div className="brand-mark"><Icon name="brand" /></div>
          <div><strong>ATELIER</strong><span>GARMENT ERP</span></div>
          <button className="nav-close" onClick={() => setMobileNav(false)}>×</button>
        </div>

        <div className="nav-caption">MENU UTAMA</div>
        <button className={`nav-main ${page === 'dashboard' ? 'active' : ''}`} onClick={() => { setPage('dashboard'); setExpanded(null); setMobileNav(false) }}>
          <Icon name="dashboard" /><span>Dashboard</span>
        </button>

        {(Object.keys(nav) as NavSection[]).map((section) => (
          <div className="nav-section" key={section}>
            <button className={`nav-main ${expanded === section ? 'active' : ''}`} onClick={() => setExpanded(expanded === section ? null : section)}>
              <Icon name={section} /><span>{section}</span><span className="chevron">{expanded === section ? '⌄' : '›'}</span>
            </button>
            {expanded === section && <div className="submenu">
              {nav[section].map((item) => {
                const active = (item === 'Penjualan & Invoice' && page === 'sales') || (item === 'Kartu Stok FG' && page === 'stock-card') || (item === 'Mutasi Barang Jadi' && page === 'movements')
                return <button key={item} className={active ? 'sub-active' : ''} onClick={() => chooseSubmenu(item)}>• {item}</button>
              })}
            </div>}
          </div>
        ))}

        <div className="sidebar-spacer" />
        <button className="nav-main"><Icon name="audit" /><span>Pengaturan & Audit</span><span className="chevron">›</span></button>
        <div className="env-card"><div className="env-dot" /><div><strong>ERP Enteng</strong><span>Target dev · UX alpha</span></div></div>
      </aside>

      <main className="main-panel">
        <header className="topbar">
          <button className="mobile-menu" onClick={() => setMobileNav(true)}><Icon name="menu" /></button>
          <div className="top-title"><div className="top-icon"><Icon name="dashboard" /></div><div><strong>{title}</strong><span>{page === 'dashboard' ? 'Satu layar untuk keputusan hari ini' : 'Cepat, jelas, dan aman buat operasional'}</span></div></div>
          <div className="top-actions"><button className="sim-badge"><span /> DATA SIMULASI</button><button className="round-btn"><Icon name="search" /></button><div className="owner"><span>OH</span><div><strong>Owner</strong><small>Administrator</small></div><b>⌄</b></div></div>
        </header>

        <div className="page-wrap">
          {page === 'dashboard' && <Dashboard onOpenSales={() => setPage('sales')} />}
          {page === 'sales' && <SalesPage qtyText={qtyText} setQtyText={setQtyText} unit={unit} setUnit={setUnit} sizes={sizes} setSizes={setSizes} totalPcs={totalPcs} composed={composed} stockEnough={stockEnough} compositionOk={compositionOk} saleTotal={saleTotal} distribute={distribute} openStock={() => setPage('stock-card')} />}
          {page === 'stock-card' && <StockCard />}
          {page === 'movements' && <Movements movements={movements} setMovements={setMovements} />}
          {page === 'placeholder' && <Placeholder />}
        </div>
      </main>
    </div>
  )
}

function Dashboard({ onOpenSales }: { onOpenSales: () => void }) {
  return <>
    <section className="hero-copy">
      <div className="eyebrow">DASHBOARD OWNER <span><Icon name="calendar" /> Kamis, 27 Agustus 2026</span></div>
      <h1>Pabrik bergerak.<br className="desktop-only" /> Angka tetap kebaca.</h1>
      <p>Pantau uang, stok, HPP, dan aliran produksi tanpa membuka sepuluh laporan.</p>
    </section>

    <section className="kpi-grid">
      <Kpi label="Kas & Bank" value="Rp284,6 jt" note="+4,2% dibanding bulan lalu" tone="good" />
      <Kpi label="Nilai stok FG" value="Rp418,2 jt" note="1.482 pcs siap jual" tone="neutral" />
      <Kpi label="Piutang berjalan" value="Rp176,8 jt" note="Rp42 jt jatuh tempo ≤ 7 hari" tone="warn" />
      <Kpi label="HPP bulan ini" value="Rp298,4 jt" note="stabil · 62,1% dari penjualan" tone="good" />
    </section>

    <section className="dashboard-grid">
      <div className="panel wide-panel">
        <div className="panel-head"><div><div className="eyebrow">PULSA KEUANGAN</div><h2>Penjualan, HPP & laba kotor</h2><p>Klik detail untuk menelusuri transaksi pembentuk angkanya.</p></div><button className="soft-btn">30 hari terakhir ⌄</button></div>
        <div className="chart-wrap">
          {[52,65,58,73,69,84,77,92,88,101,96,112].map((h, i) => <div className="bar-col" key={i}><div className="bar primary" style={{height: `${h}%`}}/><div className="bar secondary" style={{height: `${Math.max(30,h-28)}%`}}/></div>)}
        </div>
        <div className="chart-legend"><span><i className="legend-a" /> Penjualan Rp480,5 jt</span><span><i className="legend-b" /> HPP Rp298,4 jt</span><strong>Laba kotor Rp182,1 jt</strong></div>
      </div>

      <div className="panel attention-panel">
        <div className="eyebrow">BUTUH PERHATIAN</div><h2>4 hal hari ini</h2>
        <Attention label="Piutang lewat jatuh tempo" value="Rp18,4 jt" meta="3 pelanggan" tone="danger" />
        <Attention label="Stok size menipis" value="7 SKU" meta="di bawah minimum" tone="warn" />
        <Attention label="WIP tanpa update > 3 hari" value="2 grup" meta="cek mandor" tone="neutral" />
        <Attention label="QC menunggu keputusan" value="34 pcs" meta="BS / rework" tone="neutral" />
      </div>
    </section>

    <section className="flow-strip">
      <div><div className="eyebrow">ALIRAN PABRIK</div><h2>Dari potongan sampai uang masuk</h2></div>
      {['Potongan 1.920 pcs', 'Mandor 1.406 pcs', 'Laundry 628 pcs', 'QC 412 pcs', 'FG 1.482 pcs'].map((x, i) => <div className="flow-node" key={x}><span>{String(i+1).padStart(2,'0')}</span><strong>{x.split(' ').slice(0,-2).join(' ') || x.split(' ')[0]}</strong><small>{x.split(' ').slice(-2).join(' ')}</small></div>)}
      <button className="primary-btn" onClick={onOpenSales}>Input penjualan <Icon name="arrow" /></button>
    </section>
  </>
}

function Kpi({ label, value, note, tone }: { label: string; value: string; note: string; tone: string }) {
  return <div className="kpi-card"><div className="kpi-label">{label}</div><div className="kpi-value">{value}</div><div className={`kpi-note ${tone}`}>{tone === 'good' ? '↗' : tone === 'warn' ? '↘' : '•'} {note}</div><div className={`kpi-orb ${tone}`}>◉</div></div>
}

function Attention({ label, value, meta, tone }: { label: string; value: string; meta: string; tone: string }) {
  return <div className="attention-row"><span className={`attention-dot ${tone}`} /><div><strong>{label}</strong><small>{meta}</small></div><b>{value}</b></div>
}

function SalesPage(props: {
  qtyText: string; setQtyText: (v: string) => void; unit: 'lusin' | 'pcs'; setUnit: (v: 'lusin' | 'pcs') => void;
  sizes: SizeRow[]; setSizes: (v: SizeRow[]) => void; totalPcs: number; composed: number; stockEnough: boolean; compositionOk: boolean; saleTotal: number; distribute: () => void; openStock: () => void
}) {
  const { qtyText, setQtyText, unit, setUnit, sizes, setSizes, totalPcs, composed, stockEnough, compositionOk, saleTotal, distribute, openStock } = props
  const [productQuery, setProductQuery] = useState('')
  const [selectedProductCode, setSelectedProductCode] = useState('73001')
  const [selectedBrands, setSelectedBrands] = useState([...productBrands])
  const [selectedRanges, setSelectedRanges] = useState([...productRanges])
  const selectedProduct = productCatalog.find((product) => product.code === selectedProductCode) ?? productCatalog[0]
  const visibleProducts = useMemo(() => productCatalog.filter((product) => {
    const matchesQuery = `${product.code} ${product.range} ${product.name} ${product.color} ${product.brand}`.toLowerCase().includes(productQuery.toLowerCase())
    return matchesQuery && selectedBrands.includes(product.brand) && selectedRanges.includes(product.range)
  }), [productQuery, selectedBrands, selectedRanges])

  const chooseProduct = (product: Product) => {
    setSelectedProductCode(product.code)
    setSizes(product.sizes.map((size, index) => ({ size, stock: product.stocks[index], qty: 0, input: '' })))
  }

  return <>
    <section className="hero-copy compact"><div className="eyebrow">PENJUALAN · BARANG JADI</div><h1>Input penjualan</h1></section>
    <section className="sales-layout">
      <div className="panel sale-form-panel">
        <div className="form-grid two">
          <Field label="Pelanggan"><button className="select-btn">Nusantara Fashion <Icon name="chevron" /></button></Field>
          <Field label="Sumber barang"><button className="select-btn">Gudang FG Utama <Icon name="chevron" /></button></Field>
        </div>
        <div className="product-picker catalog-picker">
          <div className="catalog-toolbar">
            <div><div className="eyebrow">PILIH BARANG</div><small>{visibleProducts.length} dari {productCatalog.length} SKU</small></div>
            <div className="catalog-search"><Icon name="search" /><input value={productQuery} onChange={(event) => setProductQuery(event.target.value)} placeholder="Cari 73001, range, model, warna..." /></div>
            <div className="catalog-filters"><MultiCheckFilter label="Merek" options={productBrands} selected={selectedBrands} onChange={setSelectedBrands} /><MultiCheckFilter label="Range" options={productRanges} selected={selectedRanges} onChange={setSelectedRanges} /></div>
          </div>
          <div className="catalog-results">{visibleProducts.map((product, index) => {
            const total = product.stocks.reduce((sum, qty) => sum + qty, 0)
            const active = product.code === selectedProductCode
            return <button className={`catalog-row ${active ? 'selected' : ''}`} key={product.code} onClick={() => chooseProduct(product)}>
              <span className="catalog-seq">{String(productCatalog.findIndex((item) => item.code === product.code) + 1).padStart(2,'0')}</span>
              <div className="catalog-name"><strong>{product.code}</strong><small>{product.name} · {product.color}</small></div>
              <div className="catalog-meta"><span>{product.brand}</span><span>{product.range}</span></div>
              <div className="catalog-stock"><strong>{total} pcs</strong><small>{dozenPieces(total)}</small></div>
              <span className="catalog-check">{active ? <Icon name="check" /> : <Icon name="arrow" />}</span>
            </button>
          })}{visibleProducts.length === 0 && <div className="catalog-empty"><Icon name="search" /><strong>Barang tidak ditemukan</strong><small>Coba kosongkan sebagian filter atau cari kode lain.</small></div>}</div>
        </div>
        <div className="selected-product-head"><div><div className="sku-title"><h2>{selectedProduct.code}</h2><span>Range {selectedProduct.range}</span></div><p>{selectedProduct.name} · {selectedProduct.color} · {selectedProduct.brand}</p></div><button className="soft-btn" onClick={openStock}><Icon name="stock" /> Cek kartu stok</button></div>
        <div className="sale-entry-grid">
          <div className="qty-column">
            <Field label="Isi cepat total · opsional">
              <div className="quantity-input"><input value={qtyText} onChange={(event) => setQtyText(event.target.value)} placeholder="2 atau 1 lusin 6 potong"/><div className="unit-toggle"><button className={unit === 'lusin' ? 'active' : ''} onClick={() => setUnit('lusin')}>lusin</button><button className={unit === 'pcs' ? 'active' : ''} onClick={() => setUnit('pcs')}>pcs</button></div></div>
              <small className="helper">Gunakan kalau mau isi cepat, lalu bagi rata ke size.</small>
            </Field>
            <div className="conversion"><span>HASIL ISI CEPAT</span><strong>{totalPcs} pcs</strong><small>{dozenPieces(totalPcs)}</small></div>
            <button className="soft-btn quick-distribute" onClick={distribute} disabled={totalPcs <= 0}>Bagi rata ke semua size</button>
            <div className="price-box"><span>HARGA / LUSIN</span><strong>{money(1080000)}</strong></div>
          </div>
          <div className="composition-column">
            <div className="composition-head"><div><strong>Jumlah per size</strong><span>Boleh ketik PCS, lusin, atau campuran.</span></div></div>
            <div className="size-grid">{sizes.map((row, index) => <div className="size-card" key={row.size}>
              <div><strong>Size {row.size}</strong><span>stok {row.stock} pcs</span></div>
              <input inputMode="text" value={row.input} placeholder="8 atau 1 lusin" onChange={(event) => {
                const raw = event.target.value
                const next = [...sizes]
                next[index] = { ...row, input: raw, qty: parseQty(raw, 'pcs') }
                setSizes(next)
              }}/>
              <small className="parsed-qty">{row.qty} pcs · {dozenPieces(row.qty)}</small>
            </div>)}</div>
            <div className="sales-total-strip"><span>TOTAL DARI SIZE</span><strong>{composed} pcs</strong><small>{dozenPieces(composed)}</small></div>
            <div className={`validation ${compositionOk && stockEnough ? 'success' : 'error'}`}><Icon name={compositionOk && stockEnough ? 'check' : 'filter'} /> {!compositionOk ? 'Isi minimal satu size.' : stockEnough ? 'Jumlah otomatis dijumlahkan dan stok mencukupi.' : 'Ada size yang melebihi stok.'}</div>
          </div>
        </div>
        <div className="sale-footer"><div><span>TOTAL PENJUALAN</span><strong>{money(saleTotal)}</strong><small>Nusantara Fashion · {composed} pcs · {dozenPieces(composed)} · size {sizes.map((size)=>size.qty).join(' / ')}</small></div><button className="primary-btn" disabled={!compositionOk || !stockEnough}>Review transaksi <Icon name="arrow" /></button></div>
      </div>
    </section>
  </>
}

function Field({ label, children }: { label: string; children: React.ReactNode }) { return <label className="field"><span>{label}</span>{children}</label> }

function StockCard() {
  const [selectedSku, setSelectedSku] = useState<string | null>(null)
  const [skuQuery, setSkuQuery] = useState('')
  const [expandedId, setExpandedId] = useState<string | null>(null)
  const [selectedBrands, setSelectedBrands] = useState([...productBrands])
  const [selectedSizes, setSelectedSizes] = useState([...productSizes])
  const [selectedLocations, setSelectedLocations] = useState([...stockLocations])
  const [selectedGrades, setSelectedGrades] = useState([...stockGrades])
  const visibleSkus = useMemo(() => productCatalog.filter((product) => {
    const matchesQuery = `${product.code} ${product.range} ${product.name} ${product.color} ${product.brand}`.toLowerCase().includes(skuQuery.toLowerCase())
    const matchesSize = product.sizes.some((size) => selectedSizes.includes(size))
    return matchesQuery && selectedBrands.includes(product.brand) && matchesSize && selectedLocations.includes(product.location) && selectedGrades.includes(product.grade)
  }), [skuQuery, selectedBrands, selectedSizes, selectedLocations, selectedGrades])
  const selected = productCatalog.find((product) => product.code === selectedSku)
  const currentStock = selected?.stocks.reduce((sum, qty) => sum + qty, 0) ?? 0
  const ledgerMovements = selected ? initialMovements.map((movement) => ({
    ...movement,
    sku: selected.code,
    brand: selected.brand,
    balance: selected.stocks.map((stock, index) => stock + movement.balance[index] - initialMovements[0].balance[index]) as [number, number, number],
  })) : []

  if (!selected) return <>
    <section className="hero-copy compact"><div className="eyebrow">GUDANG · BARANG JADI</div><h1>Kartu stok FG</h1></section>
    <div className="panel sku-browser">
      <div className="stock-browser-toolbar">
        <div className="sku-search-field"><Icon name="search" /><input autoFocus value={skuQuery} onChange={(event) => setSkuQuery(event.target.value)} placeholder="Cari kode SKU, range, model, warna..." /></div>
        <div className="stock-filter-row">
          <MultiCheckFilter label="Merek" options={productBrands} selected={selectedBrands} onChange={setSelectedBrands} />
          <MultiCheckFilter label="Size" options={productSizes} selected={selectedSizes} onChange={setSelectedSizes} />
          <MultiCheckFilter label="Lokasi" options={stockLocations} selected={selectedLocations} onChange={setSelectedLocations} />
          <MultiCheckFilter label="Grade" options={stockGrades} selected={selectedGrades} onChange={setSelectedGrades} />
        </div>
      </div>
      <div className="sku-browser-list">{visibleSkus.map((sku) => {
        const total = sku.stocks.reduce((sum, qty) => sum + qty, 0)
        const sequence = productCatalog.findIndex((row) => row.code === sku.code) + 1
        return <button className="sku-browser-row" key={sku.code} onClick={() => { setSelectedSku(sku.code); setExpandedId(null) }}>
          <span className="sku-sequence">{String(sequence).padStart(2, '0')}</span>
          <div className="sku-browser-name"><strong>{sku.code}</strong><small>{sku.name} · {sku.color} · {sku.brand}</small></div>
          <span className="range-chip">{sku.range}</span>
          <div className="sku-size-preview">{sku.sizes.map((size, index) => <span key={size}><small>{size}</small><strong>{sku.stocks[index]}</strong><em>{dozenPieces(sku.stocks[index])}</em></span>)}</div>
          <div className="sku-stock-preview"><strong>{total} pcs</strong><small>{dozenPieces(total)}</small></div>
          <Icon name="arrow" />
        </button>
      })}
        {visibleSkus.length === 0 && <div className="sku-empty">Tidak ada SKU yang cocok dengan pencarian dan filter.</div>}
      </div>
    </div>
  </>

  return <>
    <section className="hero-copy compact"><button className="back-link" onClick={() => { setSelectedSku(null); setExpandedId(null) }}><Icon name="back" /> Semua SKU</button><div className="eyebrow">GUDANG · BARANG JADI</div><h1>Kartu stok FG</h1></section>
    <div className="panel stock-summary">
      <div className="stock-summary-main">
        <div><div className="sku-title"><h2>{selected.code}</h2><span>Range {selected.range}</span></div><p>{selected.name} · {selected.color} · {selected.brand} · {selected.location}</p></div>
        <div className="stock-size-overview">{selected.sizes.map((size, index) => <div key={size}><span>SIZE {size}</span><strong>{selected.stocks[index]} pcs</strong><small>{dozenPieces(selected.stocks[index])}</small></div>)}</div>
      </div>
      <div className="stock-total-hero"><span>TOTAL STOK AKHIR</span><strong>{currentStock} pcs</strong><small>{dozenPieces(currentStock)}</small></div>
    </div>
    <div className="panel table-panel">
      <div className="table-toolbar"><div className="search-box compact-search"><Icon name="search" /> Cari ref / pelanggan...</div><button className="soft-btn"><Icon name="calendar" /> 30 hari</button><button className="soft-btn"><Icon name="filter" /> Filter</button></div>
      <div className="responsive-table stock-ledger"><table>
        <thead><tr><th>Waktu fisik</th><th>Transaksi</th><th className="number-head">Masuk</th><th className="number-head">Keluar</th><th className="number-head">Stok akhir</th><th aria-label="Rincian" /></tr></thead>
        <tbody>{ledgerMovements.map((movement) => {
          const masuk = movement.delta.reduce((sum, qty) => sum + Math.max(0, qty), 0)
          const keluar = movement.delta.reduce((sum, qty) => sum + Math.abs(Math.min(0, qty)), 0)
          const stock = movement.balance.reduce((sum, qty) => sum + qty, 0)
          const open = expandedId === movement.id
          return <Fragment key={movement.id}>
            <tr className={open ? 'stock-row-open' : ''}>
              <td><span className="ledger-date">{movement.date}</span></td>
              <td><div className="ledger-transaction"><div><strong>{movement.ref}</strong><span className="type-pill">{movement.type}</span></div><small>{movement.note}</small></div></td>
              <td className="ledger-number incoming">{masuk > 0 ? `+${masuk}` : '—'}<small>{masuk > 0 ? dozenPieces(masuk) : ''}</small></td>
              <td className="ledger-number outgoing">{keluar > 0 ? `−${keluar}` : '—'}<small>{keluar > 0 ? dozenPieces(keluar) : ''}</small></td>
              <td className="ledger-balance"><strong>{stock} pcs</strong><small>{dozenPieces(stock)}</small></td>
              <td><button className="stock-expand" aria-expanded={open} aria-label={open ? 'Tutup rincian size' : 'Buka rincian size'} onClick={() => setExpandedId(open ? null : movement.id)}>{open ? '−' : '+'}</button></td>
            </tr>
            {open && <tr className="stock-detail-row"><td colSpan={6}><div className="stock-size-details">
              <div className="detail-caption"><span>RINCIAN SIZE</span><small>Komposisi transaksi dan saldo sesudah transaksi</small></div>
              {movement.delta.map((delta, index) => <div className="size-ledger-card" key={index}>
                <span>SIZE {selected.sizes[index]}</span>
                <div><small>{delta >= 0 ? 'Masuk' : 'Keluar'}</small><strong className={delta < 0 ? 'neg' : delta > 0 ? 'pos' : ''}>{delta > 0 ? '+' : delta < 0 ? '−' : ''}{Math.abs(delta)} pcs</strong></div>
                <div><small>Stok akhir</small><strong>{movement.balance[index]} pcs</strong></div>
                <em>{dozenPieces(movement.balance[index])}</em>
              </div>)}
            </div></td></tr>}
          </Fragment>
        })}</tbody>
      </table></div>
    </div>
  </>
}

function Movements({ movements, setMovements }: { movements: Movement[]; setMovements: (m: Movement[]) => void }) {
  const [draggedId, setDraggedId] = useState<string | null>(null)
  const [movementQuery, setMovementQuery] = useState('')
  const customerOptions = ['Nusantara Fashion', 'Sumber Denim', 'Tanpa toko']
  const movementTypes = Array.from(new Set(initialMovements.map((movement) => movement.type)))
  const [selectedCustomers, setSelectedCustomers] = useState([...customerOptions])
  const [selectedTypes, setSelectedTypes] = useState([...movementTypes])
  const moveVisible = (id: string, dir: -1 | 1, visibleIds: string[]) => {
    const visibleIndex = visibleIds.indexOf(id)
    const targetId = visibleIds[visibleIndex + dir]
    if (!targetId) return
    const next = [...movements]
    const from = next.findIndex((movement) => movement.id === id)
    const to = next.findIndex((movement) => movement.id === targetId)
    ;[next[from], next[to]] = [next[to], next[from]]
    setMovements(next)
  }
  const dropOn = (targetId: string) => {
    if (!draggedId || draggedId === targetId) return
    const from = movements.findIndex((movement) => movement.id === draggedId)
    const to = movements.findIndex((movement) => movement.id === targetId)
    if (from < 0 || to < 0) return
    const next = [...movements]
    const [picked] = next.splice(from, 1)
    next.splice(to, 0, picked)
    setMovements(next)
    setDraggedId(null)
  }
  const finalBySku = new Map<string, [number, number, number]>()
  initialMovements.forEach((movement) => { if (!finalBySku.has(movement.sku)) finalBySku.set(movement.sku, [...movement.balance] as [number, number, number]) })
  const totalDeltaBySku = new Map<string, [number, number, number]>()
  movements.forEach((movement) => {
    const total = totalDeltaBySku.get(movement.sku) ?? [0, 0, 0]
    totalDeltaBySku.set(movement.sku, total.map((qty, index) => qty + movement.delta[index]) as [number, number, number])
  })
  const runningBySku = new Map<string, [number, number, number]>()
  finalBySku.forEach((final, sku) => {
    const delta = totalDeltaBySku.get(sku) ?? [0, 0, 0]
    runningBySku.set(sku, final.map((qty, index) => qty - delta[index]) as [number, number, number])
  })
  const bookRows = movements.map((movement) => {
    const before = [...(runningBySku.get(movement.sku) ?? [0, 0, 0])] as [number, number, number]
    const after = before.map((qty, index) => qty + movement.delta[index]) as [number, number, number]
    runningBySku.set(movement.sku, after)
    return { ...movement, before, after }
  })
  const visibleRows = bookRows.filter((movement) => {
    const customer = movement.customer ?? 'Tanpa toko'
    const matchesQuery = `${movement.sku} ${movement.ref} ${movement.note} ${customer}`.toLowerCase().includes(movementQuery.toLowerCase())
    return matchesQuery && selectedCustomers.includes(customer) && selectedTypes.includes(movement.type)
  })
  const visibleIds = visibleRows.map((movement) => movement.id)

  return <>
    <section className="hero-copy compact"><div className="eyebrow">GUDANG · BUKU MUTASI FG</div><h1>Mutasi Barang Jadi</h1></section>
    <div className="panel mutation-panel">
      <div className="table-toolbar mutation-toolbar">
        <div className="catalog-search compact-search"><Icon name="search" /><input value={movementQuery} onChange={(event) => setMovementQuery(event.target.value)} placeholder="Cari SKU, ref, atau toko..." /></div>
        <MultiCheckFilter label="Toko" options={customerOptions} selected={selectedCustomers} onChange={setSelectedCustomers} />
        <MultiCheckFilter label="Jenis" options={movementTypes} selected={selectedTypes} onChange={setSelectedTypes} />
        <button className="soft-btn" onClick={()=>setMovements(chronologicalMovements)}><Icon name="reset" /> Reset urutan</button>
      </div>
      <div className="mutation-list">{visibleRows.map((movement,idx)=>{
        const movementTotal = movement.delta.reduce((sum, qty) => sum + qty, 0)
        const beforeTotal = movement.before.reduce((sum, qty) => sum + qty, 0)
        const afterTotal = movement.after.reduce((sum, qty) => sum + qty, 0)
        return <div className={`mutation-row ${draggedId === movement.id ? 'is-dragging' : ''}`} key={movement.id} draggable onDragStart={()=>setDraggedId(movement.id)} onDragOver={(event)=>event.preventDefault()} onDrop={()=>dropOn(movement.id)} onDragEnd={()=>setDraggedId(null)}>
          <div className="drag-grip" title="Ubah urutan buku"><Icon name="drag" /></div>
          <div className="order-no">{String(idx+1).padStart(2,'0')}</div>
          <div className="mutation-main"><div><strong>{movement.sku}</strong><span className="type-pill">{movement.type}</span></div><p>{movement.ref} · {movement.customer ?? movement.note}</p><small>{movement.date} · {movement.id}</small></div>
          <div className="mutation-delta">{movement.delta.map((delta,index)=><span className="size-book-flow" key={index}>
            <small className="size-book-title">SIZE {['28','29','30'][index]}</small>
            <div className="book-step opening"><label>Saldo awal</label><strong>{movement.before[index]} pcs</strong><small>{dozenPieces(movement.before[index])}</small></div>
            <div className="book-step change"><label>Mutasi</label><strong className={delta<0?'neg':delta>0?'pos':''}>{delta>0?'+':''}{delta} pcs</strong><small>{dozenPieces(Math.abs(delta))}</small></div>
            <div className="book-step closing"><label>Saldo akhir</label><strong>{movement.after[index]} pcs</strong><small>{dozenPieces(movement.after[index])}</small></div>
          </span>)}</div>
          <div className="mutation-total">
            <span className="total-book-title">TOTAL SKU</span>
            <div className="total-book-step"><label>Saldo awal</label><strong>{beforeTotal} pcs</strong><small>{dozenPieces(beforeTotal)}</small></div>
            <div className="total-book-step change"><label>Mutasi</label><strong className={movementTotal<0?'neg':'pos'}>{movementTotal>0?'+':''}{movementTotal} pcs</strong><small>{dozenPieces(Math.abs(movementTotal))}</small></div>
            <div className="total-book-step closing"><label>Saldo akhir</label><strong>{afterTotal} pcs</strong><small>{dozenPieces(afterTotal)}</small></div>
          </div>
          <div className="reorder"><button aria-label="Naikkan urutan" onClick={()=>moveVisible(movement.id,-1,visibleIds)} disabled={idx===0}><Icon name="up" /></button><button aria-label="Turunkan urutan" onClick={()=>moveVisible(movement.id,1,visibleIds)} disabled={idx===visibleRows.length-1}><Icon name="down" /></button></div>
        </div>})}
        {visibleRows.length === 0 && <div className="catalog-empty"><Icon name="filter" /><strong>Tidak ada mutasi</strong><small>Coba ubah pencarian atau pilihan filter.</small></div>}
      </div>
    </div>
  </>
}

function Placeholder() { return <div className="panel placeholder"><div className="placeholder-icon">◇</div><h2>Fondasinya sudah disiapkan.</h2><p>Modul ini berikutnya akan mengikuti flow bisnis yang sama: informasi penting terlihat sebelum user menekan tombol yang mengubah uang atau stok.</p></div> }

export default App
