import { useMemo, useState } from 'react'
import type { DragEvent, ReactNode } from 'react'

type Page = 'dashboard' | 'sales' | 'stock-card' | 'movements' | 'procurement' | 'placeholder'
type NavSection = 'Produksi' | 'Gudang' | 'Penjualan' | 'Keuangan' | 'Master Data'
type Unit = 'lusin' | 'pcs'
type SizeTuple = [string, string, string]
type QtyTuple = [number, number, number]

type SizeRow = { size: string; stock: number; qty: number }
type Movement = {
  id: string
  physicalAt: string
  createdAt: string
  ref: string
  type: string
  note: string
  sku: string
  range: string
  product: string
  location: string
  sizes: SizeTuple
  delta: QtyTuple
  balance: QtyTuple
}

type Sku = {
  sku: string
  range: string
  product: string
  variant: string
  sizes: SizeTuple
  stock: QtyTuple
}

const nav: Record<NavSection, string[]> = {
  Produksi: ['Pesanan Produksi', 'Potongan & Roll', 'Mandor & WIP', 'Laundry', 'QC & Final SKU', 'Barang BS & Rework'],
  Gudang: ['Ringkasan Gudang', 'Pembelian & Penerimaan', 'Bahan & Roll', 'Aksesori', 'Ringkasan Barang Jadi', 'Mutasi Barang Jadi', 'Kartu Stok FG', 'Retur & Penyesuaian'],
  Penjualan: ['Penjualan & Invoice', 'Alokasi Barang Jadi', 'Retur Penjualan', 'Pembayaran Pelanggan', 'Riwayat Pelanggan'],
  Keuangan: ['Ringkasan Keuangan', 'Kas & Bank', 'Hutang Supplier & Vendor', 'Piutang Pelanggan', 'Payroll & Kasbon', 'HPP & Rekalkulasi', 'Jurnal & Transaksi Lain', 'Laporan & Tutup Buku'],
  'Master Data': ['Produk & SKU', 'Pelanggan', 'Supplier & Vendor', 'Mandor', 'Gudang & Lokasi'],
}

const skuCatalog: Sku[] = [
  { sku: '73001', range: '28–30', product: 'Denim Classic', variant: 'Indigo', sizes: ['28', '29', '30'], stock: [96, 84, 108] },
  { sku: '73002', range: '31–33', product: 'Denim Regular', variant: 'Washed Blue', sizes: ['31', '32', '33'], stock: [72, 66, 90] },
  { sku: '73003', range: '34–36', product: 'Denim Relaxed', variant: 'Charcoal', sizes: ['34', '35', '36'], stock: [48, 54, 42] },
]

const initialMovements: Movement[] = [
  { id: 'MV-1053', physicalAt: '27 Agu 2026 · 13:44', createdAt: '13:45', ref: 'INV-260827-019', type: 'Penjualan', note: 'Nusantara Fashion', sku: '73001', range: '28–30', product: 'Denim Classic · Indigo', location: 'Gudang FG Utama', sizes: ['28','29','30'], delta: [-8,-8,-8], balance: [96,84,108] },
  { id: 'MV-1052', physicalAt: '27 Agu 2026 · 12:36', createdAt: '12:39', ref: 'INV-260827-018', type: 'Penjualan', note: 'Toko Berkat Jeans', sku: '73003', range: '34–36', product: 'Denim Relaxed · Charcoal', location: 'Gudang FG Utama', sizes: ['34','35','36'], delta: [-4,-6,-2], balance: [48,54,42] },
  { id: 'MV-1051', physicalAt: '27 Agu 2026 · 10:22', createdAt: '10:24', ref: 'FG-260827-006', type: 'QC → FG', note: 'PO-260812-031 · hasil QC diterima', sku: '73002', range: '31–33', product: 'Denim Regular · Washed Blue', location: 'Gudang FG Utama', sizes: ['31','32','33'], delta: [24,24,24], balance: [72,66,90] },
  { id: 'MV-1050', physicalAt: '27 Agu 2026 · 09:18', createdAt: '09:19', ref: 'RET-260827-002', type: 'Retur Jual', note: 'Sumber Denim · barang baik kembali ke FG', sku: '73001', range: '28–30', product: 'Denim Classic · Indigo', location: 'Gudang FG Utama', sizes: ['28','29','30'], delta: [2,1,1], balance: [104,92,116] },
  { id: 'MV-1049', physicalAt: '26 Agu 2026 · 17:06', createdAt: '17:08', ref: 'INV-260826-027', type: 'Penjualan', note: 'Sumber Denim', sku: '73001', range: '28–30', product: 'Denim Classic · Indigo', location: 'Gudang FG Utama', sizes: ['28','29','30'], delta: [-12,-8,-4], balance: [102,91,115] },
  { id: 'MV-1048', physicalAt: '26 Agu 2026 · 15:42', createdAt: '15:45', ref: 'FG-260826-011', type: 'QC → FG', note: 'PO-260811-029 · final SKU', sku: '73003', range: '34–36', product: 'Denim Relaxed · Charcoal', location: 'Gudang FG Utama', sizes: ['34','35','36'], delta: [12,12,12], balance: [52,60,44] },
  { id: 'MV-1047', physicalAt: '26 Agu 2026 · 14:10', createdAt: '14:16', ref: 'ADJ-260826-004', type: 'Penyesuaian', note: 'Selisih opname disetujui owner', sku: '73002', range: '31–33', product: 'Denim Regular · Washed Blue', location: 'Gudang FG Utama', sizes: ['31','32','33'], delta: [0,-1,0], balance: [48,42,66] },
  { id: 'MV-1046', physicalAt: '26 Agu 2026 · 11:07', createdAt: '11:09', ref: 'INV-260826-021', type: 'Penjualan', note: 'Maju Jaya Garment', sku: '73002', range: '31–33', product: 'Denim Regular · Washed Blue', location: 'Gudang FG Utama', sizes: ['31','32','33'], delta: [-6,-6,-6], balance: [48,43,66] },
]

const money = (value: number) => new Intl.NumberFormat('id-ID', { style: 'currency', currency: 'IDR', maximumFractionDigits: 0 }).format(value)
const total = (values: QtyTuple) => values.reduce((sum, value) => sum + value, 0)

function parseQty(value: string, fallbackUnit: Unit) {
  const normalized = value.toLowerCase().replace(',', '.')
  const dozenMatch = normalized.match(/([0-9]+(?:\.[0-9]+)?)\s*(?:lusin|lsn|dozen)/)
  const pcsMatch = normalized.match(/([0-9]+(?:\.[0-9]+)?)\s*(?:pcs|pc|piece|biji)/)
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
  const glyph: Record<string, string> = {
    dashboard: '◫', Produksi: '⌁', Gudang: '▣', Penjualan: '▤', Keuangan: '▰', 'Master Data': '◉', audit: '⌘', search: '⌕', stock: '◇', check: '✓', menu: '☰', up: '↑', down: '↓', reset: '↺', filter: '⌗', calendar: '◷', arrow: '→', grip: '≡', receipt: '▧',
  }
  return <span className="icon" aria-hidden="true">{glyph[name] ?? '•'}</span>
}

export default function AppV2() {
  const [page, setPage] = useState<Page>('dashboard')
  const [expanded, setExpanded] = useState<NavSection | null>(null)
  const [mobileNav, setMobileNav] = useState(false)
  const [qtyText, setQtyText] = useState('2')
  const [unit, setUnit] = useState<Unit>('lusin')
  const [sizes, setSizes] = useState<SizeRow[]>([
    { size: '28', stock: 96, qty: 8 },
    { size: '29', stock: 84, qty: 8 },
    { size: '30', stock: 108, qty: 8 },
  ])
  const [movements, setMovements] = useState(initialMovements)

  const totalPcs = parseQty(qtyText, unit)
  const composed = sizes.reduce((sum, row) => sum + row.qty, 0)
  const stockEnough = sizes.every((row) => row.qty <= row.stock)
  const compositionOk = composed === totalPcs && totalPcs > 0
  const saleTotal = (totalPcs / 12) * 1080000

  const distribute = () => {
    const base = Math.floor(totalPcs / sizes.length)
    let remainder = totalPcs % sizes.length
    setSizes((rows) => rows.map((row) => ({ ...row, qty: base + (remainder-- > 0 ? 1 : 0) })))
  }

  const title = page === 'dashboard' ? 'Ringkasan bisnis' : page === 'sales' ? 'Input Penjualan' : page === 'stock-card' ? 'Kartu Stok FG' : page === 'movements' ? 'Mutasi Barang Jadi' : page === 'procurement' ? 'Pembelian & Penerimaan' : 'Modul ERP'

  const chooseSubmenu = (label: string) => {
    if (label === 'Penjualan & Invoice') setPage('sales')
    else if (label === 'Kartu Stok FG') setPage('stock-card')
    else if (label === 'Mutasi Barang Jadi') setPage('movements')
    else if (label === 'Pembelian & Penerimaan') setPage('procurement')
    else setPage('placeholder')
    setMobileNav(false)
  }

  return <div className="app-shell">
    <aside className={`sidebar ${mobileNav ? 'sidebar-open' : ''}`}>
      <div className="brand-row"><div className="brand-mark">♧</div><div><strong>ATELIER</strong><span>GARMENT ERP</span></div><button className="nav-close" onClick={() => setMobileNav(false)}>×</button></div>
      <div className="nav-caption">MENU UTAMA</div>
      <button className={`nav-main ${page === 'dashboard' ? 'active' : ''}`} onClick={() => { setPage('dashboard'); setExpanded(null); setMobileNav(false) }}><Icon name="dashboard" /><span>Dashboard</span></button>
      {(Object.keys(nav) as NavSection[]).map((section) => <div className="nav-section" key={section}>
        <button className={`nav-main ${expanded === section ? 'active' : ''}`} onClick={() => setExpanded(expanded === section ? null : section)}><Icon name={section} /><span>{section}</span><span className="chevron">{expanded === section ? '⌄' : '›'}</span></button>
        {expanded === section && <div className="submenu">{nav[section].map((item) => {
          const active = (item === 'Penjualan & Invoice' && page === 'sales') || (item === 'Kartu Stok FG' && page === 'stock-card') || (item === 'Mutasi Barang Jadi' && page === 'movements') || (item === 'Pembelian & Penerimaan' && page === 'procurement')
          return <button key={item} className={active ? 'sub-active' : ''} onClick={() => chooseSubmenu(item)}>• {item}</button>
        })}</div>}
      </div>)}
      <div className="sidebar-spacer" />
      <button className="nav-main"><Icon name="audit" /><span>Pengaturan & Audit</span><span className="chevron">›</span></button>
      <div className="env-card"><div className="env-dot" /><div><strong>ERP Enteng</strong><span>Target dev · UX alpha 2</span></div></div>
    </aside>

    <main className="main-panel">
      <header className="topbar"><button className="mobile-menu" onClick={() => setMobileNav(true)}><Icon name="menu" /></button><div className="top-title"><div className="top-icon"><Icon name="dashboard" /></div><div><strong>{title}</strong><span>{page === 'dashboard' ? 'Satu layar untuk keputusan hari ini' : 'Cepat, jelas, dan aman buat operasional'}</span></div></div><div className="top-actions"><button className="sim-badge"><span /> DATA SIMULASI</button><button className="round-btn"><Icon name="search" /></button><div className="owner"><span>OH</span><div><strong>Owner</strong><small>Administrator</small></div><b>⌄</b></div></div></header>
      <div className="page-wrap">
        {page === 'dashboard' && <Dashboard onOpenSales={() => setPage('sales')} />}
        {page === 'sales' && <SalesPage qtyText={qtyText} setQtyText={setQtyText} unit={unit} setUnit={setUnit} sizes={sizes} setSizes={setSizes} totalPcs={totalPcs} composed={composed} stockEnough={stockEnough} compositionOk={compositionOk} saleTotal={saleTotal} distribute={distribute} openStock={() => setPage('stock-card')} />}
        {page === 'stock-card' && <StockCard />}
        {page === 'movements' && <Movements movements={movements} setMovements={setMovements} />}
        {page === 'procurement' && <Procurement />}
        {page === 'placeholder' && <Placeholder />}
      </div>
    </main>
  </div>
}

function Dashboard({ onOpenSales }: { onOpenSales: () => void }) {
  return <>
    <section className="hero-copy"><div className="eyebrow">DASHBOARD OWNER <span><Icon name="calendar" /> Kamis, 27 Agustus 2026</span></div><h1>Pabrik bergerak.<br className="desktop-only" /> Angka tetap kebaca.</h1><p>Pantau uang, stok, HPP, dan aliran produksi tanpa membuka sepuluh laporan.</p></section>
    <section className="kpi-grid"><Kpi label="Kas & Bank" value="Rp284,6 jt" note="+4,2% dibanding bulan lalu" tone="good" /><Kpi label="Nilai stok FG" value="Rp418,2 jt" note="1.482 pcs siap jual" tone="neutral" /><Kpi label="Piutang berjalan" value="Rp176,8 jt" note="Rp42 jt jatuh tempo ≤ 7 hari" tone="warn" /><Kpi label="HPP bulan ini" value="Rp298,4 jt" note="stabil · 62,1% dari penjualan" tone="good" /></section>
    <section className="dashboard-grid"><div className="panel wide-panel"><div className="panel-head"><div><div className="eyebrow">PULSA KEUANGAN</div><h2>Penjualan, HPP & laba kotor</h2><p>Klik detail untuk menelusuri transaksi pembentuk angkanya.</p></div><button className="soft-btn">30 hari terakhir ⌄</button></div><div className="chart-wrap">{[52,65,58,73,69,84,77,92,88,101,96,112].map((h, i) => <div className="bar-col" key={i}><div className="bar primary" style={{height: `${h}%`}}/><div className="bar secondary" style={{height: `${Math.max(30,h-28)}%`}}/></div>)}</div><div className="chart-legend"><span><i className="legend-a" /> Penjualan Rp480,5 jt</span><span><i className="legend-b" /> HPP Rp298,4 jt</span><strong>Laba kotor Rp182,1 jt</strong></div></div><div className="panel attention-panel"><div className="eyebrow">BUTUH PERHATIAN</div><h2>4 hal hari ini</h2><Attention label="Piutang lewat jatuh tempo" value="Rp18,4 jt" meta="3 pelanggan" tone="danger" /><Attention label="Dasar status stok" value="Belum diatur" meta="belum cukup data" tone="neutral" /><Attention label="WIP tanpa update > 3 hari" value="2 grup" meta="cek mandor" tone="neutral" /><Attention label="QC menunggu keputusan" value="34 pcs" meta="BS / rework" tone="neutral" /></div></section>
    <section className="flow-strip"><div><div className="eyebrow">ALIRAN PABRIK</div><h2>Dari potongan sampai uang masuk</h2></div>{['Potongan 1.920 pcs', 'Mandor 1.406 pcs', 'Laundry 628 pcs', 'QC 412 pcs', 'FG 1.482 pcs'].map((x, i) => <div className="flow-node" key={x}><span>{String(i+1).padStart(2,'0')}</span><strong>{x.split(' ')[0]}</strong><small>{x.split(' ').slice(1).join(' ')}</small></div>)}<button className="primary-btn" onClick={onOpenSales}>Input penjualan <Icon name="arrow" /></button></section>
  </>
}

function Kpi({ label, value, note, tone }: { label: string; value: string; note: string; tone: string }) { return <div className="kpi-card"><div className="kpi-label">{label}</div><div className="kpi-value">{value}</div><div className={`kpi-note ${tone}`}>{tone === 'good' ? '↗' : tone === 'warn' ? '↘' : '•'} {note}</div><div className={`kpi-orb ${tone}`}>◉</div></div> }
function Attention({ label, value, meta, tone }: { label: string; value: string; meta: string; tone: string }) { return <div className="attention-row"><span className={`attention-dot ${tone}`} /><div><strong>{label}</strong><small>{meta}</small></div><b>{value}</b></div> }
function Field({ label, children }: { label: string; children: ReactNode }) { return <label className="field"><span>{label}</span>{children}</label> }

function SalesPage(props: { qtyText: string; setQtyText: (v: string) => void; unit: Unit; setUnit: (v: Unit) => void; sizes: SizeRow[]; setSizes: (v: SizeRow[]) => void; totalPcs: number; composed: number; stockEnough: boolean; compositionOk: boolean; saleTotal: number; distribute: () => void; openStock: () => void }) {
  const { qtyText, setQtyText, unit, setUnit, sizes, setSizes, totalPcs, composed, stockEnough, compositionOk, saleTotal, distribute, openStock } = props
  return <>
    <section className="hero-copy compact"><div className="eyebrow">PENJUALAN · BARANG JADI</div><h1>Input penjualan</h1><p>Masukkan lusin atau pcs, cek komposisi size, lalu review. Stok selalu terlihat di titik keputusan.</p></section>
    <section className="sales-layout"><div className="panel sale-form-panel"><div className="form-grid two"><Field label="Pelanggan"><button className="select-btn">Nusantara Fashion <span>⌄</span></button></Field><Field label="Sumber barang"><button className="select-btn">Gudang FG Utama <span>⌄</span></button></Field></div>
      <div className="product-picker"><div className="eyebrow">PILIH BARANG</div><div className="search-box"><Icon name="search" /> Cari SKU atau range...</div><div className="sku-list">{skuCatalog.map((sku,i)=><div className={`sku-row ${i===0?'selected':''}`} key={sku.sku}><span>{String(i+1).padStart(2,'0')}</span><div><strong>{sku.sku} · {sku.range}</strong><small>{sku.product} · {sku.variant}</small></div></div>)}</div></div>
      <div className="selected-product-head"><div><div className="sku-title"><h2>73001</h2><span>Range 28–30</span></div><p>Denim Classic · Indigo · Atelier</p></div><button className="soft-btn" onClick={openStock}><Icon name="stock" /> Cek kartu stok</button></div>
      <div className="sale-entry-grid"><div className="qty-column"><Field label="Jumlah penjualan"><div className="quantity-input"><input value={qtyText} onChange={(e) => setQtyText(e.target.value)} placeholder="2 atau 1 lusin 6 pcs"/><div className="unit-toggle"><button className={unit === 'lusin' ? 'active' : ''} onClick={() => setUnit('lusin')}>lusin</button><button className={unit === 'pcs' ? 'active' : ''} onClick={() => setUnit('pcs')}>pcs</button></div></div><small className="helper">Boleh ketik bebas: “2 lusin”, “18 pcs”, atau “1 lusin 6 pcs”.</small></Field><div className="conversion"><span>KONVERSI</span><strong>{totalPcs} pcs</strong><small>{totalPcs > 0 ? `${(totalPcs/12).toLocaleString('id-ID',{maximumFractionDigits:2})} lusin ekuivalen` : 'Masukkan jumlah'}</small></div><div className="price-box"><span>HARGA / LUSIN</span><strong>{money(1080000)}</strong></div></div>
        <div className="composition-column"><div className="composition-head"><div><strong>Komposisi size</strong><span>Default rata; bebas diubah selama total cocok.</span></div><button className="mini-btn" onClick={distribute}>Ratakan otomatis</button></div><div className="size-grid">{sizes.map((row, i) => <div className="size-card" key={row.size}><div><strong>Size {row.size}</strong><span>stok {row.stock}</span></div><input type="number" min="0" value={row.qty} onChange={(e) => { const next=[...sizes]; next[i]={...row,qty:Math.max(0,Number(e.target.value)||0)}; setSizes(next)}}/><small>pcs keluar</small></div>)}</div><div className={`validation ${compositionOk && stockEnough ? 'success' : 'error'}`}><Icon name={compositionOk && stockEnough ? 'check' : 'filter'} /> {compositionOk ? (stockEnough ? 'Komposisi pas dan stok setiap size mencukupi.' : 'Komposisi pas, tetapi ada size melebihi stok.') : `Komposisi ${composed} pcs, target ${totalPcs} pcs.`}</div></div></div>
      <div className="sale-footer"><div><span>TOTAL PENJUALAN</span><strong>{money(saleTotal)}</strong><small>Nusantara Fashion · {totalPcs} pcs · komposisi {sizes.map(s=>s.qty).join(' / ')}</small></div><button className="primary-btn" disabled={!compositionOk || !stockEnough}>Review transaksi <Icon name="arrow" /></button></div>
    </div></section>
  </>
}

function StockCard() {
  const [selectedSku, setSelectedSku] = useState('73001')
  const [query, setQuery] = useState('')
  const filteredSkus = skuCatalog.filter((sku) => `${sku.sku} ${sku.range} ${sku.product} ${sku.variant}`.toLowerCase().includes(query.toLowerCase()))
  const selected = skuCatalog.find((sku) => sku.sku === selectedSku) ?? skuCatalog[0]
  const rows = initialMovements.filter((movement) => movement.sku === selected.sku)

  return <>
    <section className="hero-copy compact"><div className="eyebrow">GUDANG · BARANG JADI</div><h1>Kartu stok FG</h1><p>Cari SKU dulu, lalu lihat fakta fisiknya. Urut kronologis dan tidak bisa di-drag.</p></section>
    <div className="panel stock-browser"><div className="stock-browser-head"><div><div className="eyebrow">PILIH SKU</div><h2>Barang jadi</h2></div><label className="live-search"><Icon name="search" /><input value={query} onChange={(e)=>setQuery(e.target.value)} placeholder="Cari SKU, range, model..." /></label></div><div className="stock-sku-grid">{filteredSkus.map((sku) => <button key={sku.sku} className={`stock-sku-card ${selectedSku===sku.sku?'active':''}`} onClick={()=>setSelectedSku(sku.sku)}><div><strong>{sku.sku}</strong><span>{sku.range}</span></div><p>{sku.product} · {sku.variant}</p><div className="stock-mini-sizes">{sku.sizes.map((size,i)=><span key={size}>{size}<b>{sku.stock[i]}</b></span>)}</div><small>Total {total(sku.stock)} pcs</small></button>)}</div></div>
    <div className="panel stock-summary"><div><div className="sku-title"><h2>{selected.sku}</h2><span>Range {selected.range}</span></div><p>{selected.product} · {selected.variant} · Gudang FG Utama</p></div><div className="stock-pills">{selected.sizes.map((size,i)=><span key={size}>{size} <b>{selected.stock[i]}</b></span>)}<span className="total">Total <b>{total(selected.stock)} pcs</b></span></div></div>
    <div className="panel table-panel"><div className="table-toolbar"><div className="search-box compact-search"><Icon name="search" /> Ref / pelanggan pada SKU {selected.sku}</div><button className="soft-btn"><Icon name="calendar" /> 30 hari</button><button className="soft-btn"><Icon name="filter" /> Filter</button></div><div className="responsive-table"><table><thead><tr><th>Waktu fisik</th><th>Ref</th><th>Jenis</th><th>Keterangan</th>{selected.sizes.map(s=><th key={s}>{s}</th>)}<th>Saldo size</th></tr></thead><tbody>{rows.map((m)=><tr key={m.id}><td>{m.physicalAt}</td><td><strong>{m.ref}</strong></td><td><span className="type-pill">{m.type}</span></td><td>{m.note}</td>{m.delta.map((d,i)=><td key={i} className={d<0?'neg':d>0?'pos':''}>{d>0?'+':''}{d}</td>)}<td><strong>{m.balance.join(' / ')}</strong></td></tr>)}</tbody></table></div></div>
  </>
}

function Movements({ movements, setMovements }: { movements: Movement[]; setMovements: (m: Movement[]) => void }) {
  const [query, setQuery] = useState('')
  const [typeFilter, setTypeFilter] = useState('Semua')
  const [draggingId, setDraggingId] = useState<string | null>(null)
  const types = ['Semua', ...Array.from(new Set(initialMovements.map((movement) => movement.type)))]
  const visible = useMemo(() => movements.filter((movement) => {
    const haystack = `${movement.sku} ${movement.range} ${movement.ref} ${movement.type} ${movement.note} ${movement.location}`.toLowerCase()
    return haystack.includes(query.toLowerCase()) && (typeFilter === 'Semua' || movement.type === typeFilter)
  }), [movements, query, typeFilter])

  const reorderById = (fromId: string, toId: string) => {
    if (fromId === toId) return
    const next = [...movements]
    const from = next.findIndex((row) => row.id === fromId)
    const to = next.findIndex((row) => row.id === toId)
    if (from < 0 || to < 0) return
    const [moved] = next.splice(from, 1)
    next.splice(to, 0, moved)
    setMovements(next)
  }

  const moveVisible = (id: string, direction: -1 | 1) => {
    const current = visible.findIndex((row) => row.id === id)
    const target = visible[current + direction]
    if (!target) return
    reorderById(id, target.id)
  }

  const onDrop = (event: DragEvent<HTMLDivElement>, targetId: string) => {
    event.preventDefault()
    if (draggingId) reorderById(draggingId, targetId)
    setDraggingId(null)
  }

  return <>
    <section className="hero-copy compact"><div className="eyebrow">GUDANG · BUKU MUTASI FG</div><h1>Mutasi Barang Jadi</h1><p>Buku kerja global untuk owner: semua SKU satu tempat, stok per-size tetap terbaca, urutan tampilan boleh lu susun tanpa mengubah fakta transaksi.</p></section>
    <div className="mutation-rules"><div><strong>Urutan buku manual</strong><span>Drag di desktop atau pakai ↑ ↓. Nomor buku hanya tampilan.</span></div><div><strong>Fakta tidak berubah</strong><span>Waktu fisik, ref, qty, saldo, dan audit ID tetap asli.</span></div></div>
    <div className="panel mutation-panel">
      <div className="mutation-toolbar"><label className="live-search mutation-search"><Icon name="search" /><input value={query} onChange={(e)=>setQuery(e.target.value)} placeholder="SKU, range, ref, pelanggan..." /></label><select className="toolbar-select" value={typeFilter} onChange={(e)=>setTypeFilter(e.target.value)}>{types.map(type=><option key={type}>{type}</option>)}</select><button className="soft-btn" onClick={()=>{setMovements([...initialMovements]);setDraggingId(null)}}><Icon name="reset" /> Reset kronologis</button></div>
      <div className="book-grid-head"><span></span><span>Urut</span><span>Transaksi</span><span>SKU</span><span>Pergerakan size</span><span>Total</span><span>Saldo</span><span>Aksi</span></div>
      <div className="mutation-list">{visible.map((m,idx) => {
        const globalOrder = movements.findIndex((row)=>row.id===m.id)+1
        const deltaTotal = total(m.delta)
        return <div className={`mutation-row-v2 ${draggingId===m.id?'dragging':''}`} key={m.id} draggable onDragStart={()=>setDraggingId(m.id)} onDragEnd={()=>setDraggingId(null)} onDragOver={(e)=>e.preventDefault()} onDrop={(e)=>onDrop(e,m.id)}>
          <div className="drag-handle" title="Drag untuk atur urutan"><Icon name="grip" /></div>
          <div className="book-order"><b>{String(globalOrder).padStart(2,'0')}</b><small>book</small></div>
          <div className="mutation-main"><div><strong>{m.ref}</strong><span className="type-pill">{m.type}</span></div><p>{m.note}</p><small>Fisik {m.physicalAt} · input {m.createdAt} · {m.id}</small></div>
          <div className="mutation-sku"><strong>{m.sku}</strong><span>{m.range}</span><small>{m.product}</small></div>
          <div className="mutation-delta-v2">{m.delta.map((d,i)=><span key={m.sizes[i]} className={d<0?'neg':d>0?'pos':''}><small>{m.sizes[i]}</small><b>{d>0?'+':''}{d}</b></span>)}</div>
          <div className={`mutation-total ${deltaTotal<0?'neg':deltaTotal>0?'pos':''}`}><strong>{deltaTotal>0?'+':''}{deltaTotal}</strong><small>pcs</small></div>
          <div className="mutation-balance"><strong>{total(m.balance)}</strong><small>{m.balance.join(' / ')}</small></div>
          <div className="reorder"><button onClick={()=>moveVisible(m.id,-1)} disabled={idx===0}><Icon name="up" /></button><button onClick={()=>moveVisible(m.id,1)} disabled={idx===visible.length-1}><Icon name="down" /></button></div>
        </div>
      })}</div>
      {visible.length===0 && <div className="empty-state">Nggak ada mutasi yang cocok dengan filter ini.</div>}
      <div className="mutation-foot"><span>{visible.length} dari {movements.length} transaksi terlihat</span><strong>Lokasi: Gudang FG Utama</strong></div>
    </div>
  </>
}

function Procurement() {
  return <>
    <section className="hero-copy compact"><div className="eyebrow">GUDANG · PROCUREMENT</div><h1>Pembelian & penerimaan</h1><p>Alur singkat dari PO supplier sampai barang benar-benar diterima gudang. Fokus ke apa yang belum datang, selisih, dan dokumen yang perlu tindakan.</p></section>
    <section className="procurement-grid"><div className="panel procurement-list"><div className="panel-head"><div><div className="eyebrow">PO TERBUKA</div><h2>Barang yang ditunggu</h2></div><button className="primary-btn">+ PO pembelian</button></div>{[['PO-260824-014','PT Sinar Textile','Denim 12 oz · 42 roll','ETA hari ini','42/42 roll'],['PO-260825-008','CV Maju Aksesori','Kancing metal + zipper','ETA besok','0/3 item'],['PO-260822-031','PT Warna Jaya','Chemical laundry','Terlambat 2 hari','8/12 drum']].map((row,i)=><div className="proc-row" key={row[0]}><span className={`attention-dot ${i===2?'danger':i===0?'warn':'neutral'}`}/><div><strong>{row[0]}</strong><small>{row[1]} · {row[2]}</small></div><div><b>{row[3]}</b><small>{row[4]}</small></div><button className="soft-btn">Buka</button></div>)}</div>
      <div className="panel receive-card"><div className="eyebrow">PENERIMAAN HARI INI</div><h2>42 roll datang</h2><p>PO-260824-014 · PT Sinar Textile</p><div className="receive-metrics"><span>Surat jalan<b>SJ-88201</b></span><span>Roll fisik<b>42</b></span><span>Selisih<b className="pos">0</b></span></div><div className="validation success"><Icon name="check" /> Jumlah fisik cocok dengan PO. Tinggal timbang/ukur dan posting penerimaan.</div><button className="primary-btn">Lanjut penerimaan <Icon name="arrow" /></button></div></section>
  </>
}

function Placeholder() { return <div className="panel placeholder"><div className="placeholder-icon">◇</div><h2>Fondasinya sudah disiapkan.</h2><p>Modul berikutnya akan mengikuti prinsip yang sama: informasi penting terlihat sebelum user menekan tombol yang mengubah uang atau stok.</p></div> }
