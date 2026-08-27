import { Fragment, useMemo, useState } from 'react'

type Page = 'dashboard' | 'sales' | 'stock-card' | 'movements' | 'placeholder'
type NavSection = 'Produksi' | 'Gudang' | 'Penjualan' | 'Keuangan' | 'Master Data'

type SizeRow = { size: string; stock: number; qty: number; input: string }

type Movement = {
  id: string
  sku: string
  date: string
  ref: string
  type: string
  note: string
  delta: [number, number, number]
  balance: [number, number, number]
}

const nav: Record<NavSection, string[]> = {
  Produksi: ['Pesanan Produksi', 'Potongan & Roll', 'Mandor & WIP', 'Laundry', 'QC & Final SKU', 'Barang BS & Rework'],
  Gudang: ['Ringkasan Gudang', 'Pembelian & Penerimaan', 'Bahan & Roll', 'Aksesori', 'Ringkasan Barang Jadi', 'Mutasi Barang Jadi', 'Kartu Stok FG', 'Retur & Penyesuaian'],
  Penjualan: ['Penjualan & Invoice', 'Alokasi Barang Jadi', 'Retur Penjualan', 'Pembayaran Pelanggan', 'Riwayat Pelanggan'],
  Keuangan: ['Ringkasan Keuangan', 'Kas & Bank', 'Hutang Supplier & Vendor', 'Piutang Pelanggan', 'Payroll & Kasbon', 'HPP & Rekalkulasi', 'Jurnal & Transaksi Lain', 'Laporan & Tutup Buku'],
  'Master Data': ['Produk & SKU', 'Pelanggan', 'Supplier & Vendor', 'Mandor & Pekerja', 'Gudang & Lokasi'],
}

const initialMovements: Movement[] = [
  { id: 'MV-1048', sku: '73001', date: '27 Agu 2026 · 13:44', ref: 'INV-260827-019', type: 'Penjualan', note: 'Nusantara Fashion', delta: [-8, -8, -8], balance: [96, 84, 108] },
  { id: 'MV-1047', sku: '73001', date: '27 Agu 2026 · 10:22', ref: 'FG-260827-006', type: 'QC → FG', note: 'PO-260812-031', delta: [24, 24, 24], balance: [104, 92, 116] },
  { id: 'MV-1046', sku: '73001', date: '26 Agu 2026 · 17:06', ref: 'INV-260826-027', type: 'Penjualan', note: 'Sumber Denim', delta: [-12, -8, -4], balance: [80, 68, 92] },
  { id: 'MV-1045', sku: '73001', date: '26 Agu 2026 · 14:10', ref: 'ADJ-260826-004', type: 'Penyesuaian', note: 'Selisih opname disetujui owner', delta: [0, -1, 0], balance: [92, 76, 96] },
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
  const art: Record<string, React.ReactNode> = {
    dashboard: <><rect x="3" y="3" width="7" height="7" rx="2"/><rect x="14" y="3" width="7" height="7" rx="2"/><rect x="3" y="14" width="7" height="7" rx="2"/><rect x="14" y="14" width="7" height="7" rx="2"/></>,
    Produksi: <><path d="M12 3v3M12 18v3M3 12h3M18 12h3"/><circle cx="12" cy="12" r="4"/><path d="m5.6 5.6 2.1 2.1M16.3 16.3l2.1 2.1M18.4 5.6l-2.1 2.1M7.7 16.3l-2.1 2.1"/></>,
    Gudang: <><path d="m4 8 8-4 8 4v10l-8 3-8-3Z"/><path d="m4 8 8 4 8-4M12 12v9"/></>,
    Penjualan: <><path d="M6 3h12v18l-3-2-3 2-3-2-3 2Z"/><path d="M9 8h6M9 12h6"/></>,
    Keuangan: <><path d="M4 7h15a2 2 0 0 1 2 2v9H4a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h13"/><path d="M16 12h5"/><circle cx="16" cy="12" r=".7" fill="currentColor" stroke="none"/></>,
    'Master Data': <><ellipse cx="12" cy="5" rx="8" ry="3"/><path d="M4 5v7c0 1.7 3.6 3 8 3s8-1.3 8-3V5M4 12v7c0 1.7 3.6 3 8 3s8-1.3 8-3v-7"/></>,
    audit: <><path d="M12 3 5 6v5c0 4.6 2.9 8.1 7 10 4.1-1.9 7-5.4 7-10V6Z"/><path d="m9 12 2 2 4-5"/></>,
    search: <><circle cx="11" cy="11" r="7"/><path d="m16.5 16.5 4 4"/></>,
    back: <><path d="m15 18-6-6 6-6"/><path d="M9 12h11"/></>,
    stock: <><path d="m12 3 9 5-9 5-9-5Z"/><path d="m3 12 9 5 9-5M3 16l9 5 9-5"/></>,
    check: <path d="m5 12 4 4L19 6"/>,
    menu: <><path d="M4 7h16M4 12h16M4 17h16"/></>,
    up: <><path d="m7 14 5-5 5 5"/></>,
    down: <><path d="m7 10 5 5 5-5"/></>,
    reset: <><path d="M4 8V4m0 0h4M4 4l3.2 3.2A8 8 0 1 1 4.6 14"/></>,
    filter: <><path d="M4 6h16M7 12h10M10 18h4"/></>,
    calendar: <><rect x="3" y="5" width="18" height="16" rx="3"/><path d="M8 3v4M16 3v4M3 10h18"/></>,
    user: <><circle cx="12" cy="8" r="4"/><path d="M4 21a8 8 0 0 1 16 0"/></>,
    arrow: <><path d="M5 12h14M14 7l5 5-5 5"/></>,
    drag: <><circle cx="9" cy="6" r="1" fill="currentColor" stroke="none"/><circle cx="15" cy="6" r="1" fill="currentColor" stroke="none"/><circle cx="9" cy="12" r="1" fill="currentColor" stroke="none"/><circle cx="15" cy="12" r="1" fill="currentColor" stroke="none"/><circle cx="9" cy="18" r="1" fill="currentColor" stroke="none"/><circle cx="15" cy="18" r="1" fill="currentColor" stroke="none"/></>,
  }
  return <svg className="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{art[name] ?? <circle cx="12" cy="12" r="2" fill="currentColor" stroke="none"/>}</svg>
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
          <div className="brand-mark">♧</div>
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
  return <>
    <section className="hero-copy compact"><div className="eyebrow">PENJUALAN · BARANG JADI</div><h1>Input penjualan</h1><p>Ketik jumlah bebas di setiap size. Sistem mengubahnya ke PCS lalu langsung menjumlahkan total penjualan.</p></section>
    <section className="sales-layout">
      <div className="panel sale-form-panel">
        <div className="form-grid two">
          <Field label="Pelanggan"><button className="select-btn">Nusantara Fashion <span>⌄</span></button></Field>
          <Field label="Sumber barang"><button className="select-btn">Gudang FG Utama <span>⌄</span></button></Field>
        </div>
        <div className="product-picker">
          <div className="eyebrow">PILIH BARANG</div><div className="search-box"><Icon name="search" /> Cari SKU atau range...</div>
          <div className="sku-list"><div className="sku-row selected"><span>01</span><div><strong>73001 · 28–30</strong><small>Denim Classic · Indigo</small></div></div><div className="sku-row"><span>02</span><div><strong>73002 · 31–33</strong><small>Denim Regular · Washed Blue</small></div></div><div className="sku-row"><span>03</span><div><strong>73003 · 34–36</strong><small>Denim Relaxed · Charcoal</small></div></div></div>
        </div>
        <div className="selected-product-head"><div><div className="sku-title"><h2>73001</h2><span>Range 28–30</span></div><p>Denim Classic · Indigo · Atelier</p></div><button className="soft-btn" onClick={openStock}><Icon name="stock" /> Cek kartu stok</button></div>
        <div className="sale-entry-grid">
          <div className="qty-column">
            <Field label="Isi cepat total · opsional">
              <div className="quantity-input"><input value={qtyText} onChange={(event) => setQtyText(event.target.value)} placeholder="2 atau 1 lusin 6 potong"/><div className="unit-toggle"><button className={unit === 'lusin' ? 'active' : ''} onClick={() => setUnit('lusin')}>lusin</button><button className={unit === 'pcs' ? 'active' : ''} onClick={() => setUnit('pcs')}>pcs</button></div></div>
              <small className="helper">Hanya untuk mengisi cepat. Tekan “Bagi rata”; setelah itu setiap size tetap bebas diubah.</small>
            </Field>
            <div className="conversion"><span>HASIL ISI CEPAT</span><strong>{totalPcs} pcs</strong><small>{dozenPieces(totalPcs)}</small></div>
            <button className="soft-btn quick-distribute" onClick={distribute} disabled={totalPcs <= 0}>Bagi rata ke semua size</button>
            <div className="price-box"><span>HARGA / LUSIN</span><strong>{money(1080000)}</strong></div>
          </div>
          <div className="composition-column">
            <div className="composition-head"><div><strong>Jumlah per size</strong><span>Sumber total penjualan. Boleh ketik PCS, lusin, atau campuran.</span></div></div>
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
            <div className={`validation ${compositionOk && stockEnough ? 'success' : 'error'}`}><Icon name={compositionOk && stockEnough ? 'check' : 'filter'} /> {!compositionOk ? 'Isi minimal satu size.' : stockEnough ? 'Semua size dijumlahkan otomatis dan stok mencukupi.' : 'Ada size yang jumlahnya melebihi stok.'}</div>
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
  const skuRows = [
    { code: '73001', range: '28–30', name: 'Denim Classic · Indigo', sizes: ['28', '29', '30'], stocks: [96, 84, 108] as [number, number, number] },
    { code: '73002', range: '31–33', name: 'Denim Regular · Washed Blue', sizes: ['31', '32', '33'], stocks: [72, 60, 48] as [number, number, number] },
    { code: '73003', range: '34–36', name: 'Denim Relaxed · Charcoal', sizes: ['34', '35', '36'], stocks: [36, 42, 54] as [number, number, number] },
  ]
  const visibleSkus = skuRows.filter((sku) => `${sku.code} ${sku.range} ${sku.name}`.toLowerCase().includes(skuQuery.toLowerCase()))
  const selected = skuRows.find((sku) => sku.code === selectedSku)
  const currentStock = selected?.stocks.reduce((sum, qty) => sum + qty, 0) ?? 0
  const ledgerMovements = selected ? initialMovements.map((movement) => ({
    ...movement,
    balance: selected.stocks.map((stock, index) => stock + movement.balance[index] - initialMovements[0].balance[index]) as [number, number, number],
  })) : []

  if (!selected) return <>
    <section className="hero-copy compact"><div className="eyebrow">GUDANG · BARANG JADI</div><h1>Kartu stok FG</h1><p>Cari SKU, lalu buka kartu kronologisnya. Stok per size, total, dan konversi lusin langsung terlihat.</p></section>
    <div className="panel sku-browser">
      <div className="sku-search-field"><Icon name="search" /><input autoFocus value={skuQuery} onChange={(event) => setSkuQuery(event.target.value)} placeholder="Cari kode SKU, range, atau nama barang..." /></div>
      <div className="sku-browser-head"><span>SKU</span><span>Range</span><span>Stok per size</span><span>Total</span><span /></div>
      <div className="sku-browser-list">{visibleSkus.map((sku) => {
        const total = sku.stocks.reduce((sum, qty) => sum + qty, 0)
        const sequence = skuRows.findIndex((row) => row.code === sku.code) + 1
        return <button className="sku-browser-row" key={sku.code} onClick={() => { setSelectedSku(sku.code); setExpandedId(null) }}>
          <span className="sku-sequence">{String(sequence).padStart(2, '0')}</span>
          <div className="sku-browser-name"><strong>{sku.code}</strong><small>{sku.name}</small></div>
          <span className="range-chip">{sku.range}</span>
          <div className="sku-size-preview">{sku.sizes.map((size, index) => <span key={size}><small>{size}</small><strong>{sku.stocks[index]}</strong><em>{dozenPieces(sku.stocks[index])}</em></span>)}</div>
          <div className="sku-stock-preview"><strong>{total} pcs</strong><small>{dozenPieces(total)}</small></div>
          <Icon name="arrow" />
        </button>
      })}
        {visibleSkus.length === 0 && <div className="sku-empty">SKU tidak ditemukan. Coba kode atau range lain.</div>}
      </div>
    </div>
  </>

  return <>
    <section className="hero-copy compact"><button className="back-link" onClick={() => { setSelectedSku(null); setExpandedId(null) }}><Icon name="back" /> Semua SKU</button><div className="eyebrow">GUDANG · BARANG JADI</div><h1>Kartu stok FG</h1><p>Angka utama per transaksi. Tekan rincian untuk melihat komposisi size; urutannya selalu kronologis.</p></section>
    <div className="panel stock-summary">
      <div className="stock-summary-main">
        <div><div className="sku-title"><h2>{selected.code}</h2><span>Range {selected.range}</span></div><p>{selected.name} · Gudang FG Utama</p></div>
        <div className="stock-size-overview">{selected.sizes.map((size, index) => <div key={size}><span>SIZE {size}</span><strong>{selected.stocks[index]} pcs</strong><small>{dozenPieces(selected.stocks[index])}</small></div>)}</div>
      </div>
      <div className="stock-total-hero"><span>TOTAL STOK AKHIR</span><strong>{currentStock} pcs</strong><small>{dozenPieces(currentStock)}</small></div>
    </div>
    <div className="panel table-panel">
      <div className="table-toolbar"><div className="search-box compact-search"><Icon name="search" /> Cari ref / pelanggan...</div><button className="soft-btn"><Icon name="calendar" /> 30 hari</button><button className="soft-btn"><Icon name="filter" /> Filter</button></div>
      <div className="responsive-table stock-ledger"><table>
        <thead><tr><th>Waktu fisik</th><th>Transaksi</th><th className="number-head">Masuk</th><th className="number-head">Keluar</th><th className="number-head">Stok akhir</th><th aria-label="Rincian" /></tr></thead>
        <tbody>{ledgerMovements.map((m) => {
          const masuk = m.delta.reduce((sum, qty) => sum + Math.max(0, qty), 0)
          const keluar = m.delta.reduce((sum, qty) => sum + Math.abs(Math.min(0, qty)), 0)
          const stock = m.balance.reduce((sum, qty) => sum + qty, 0)
          const open = expandedId === m.id
          return <Fragment key={m.id}>
            <tr className={open ? 'stock-row-open' : ''}>
              <td><span className="ledger-date">{m.date}</span></td>
              <td><div className="ledger-transaction"><div><strong>{m.ref}</strong><span className="type-pill">{m.type}</span></div><small>{m.note}</small></div></td>
              <td className="ledger-number incoming">{masuk > 0 ? `+${masuk}` : '—'}<small>{masuk > 0 ? `${dozenPieces(masuk)}` : ''}</small></td>
              <td className="ledger-number outgoing">{keluar > 0 ? `−${keluar}` : '—'}<small>{keluar > 0 ? `${dozenPieces(keluar)}` : ''}</small></td>
              <td className="ledger-balance"><strong>{stock} pcs</strong><small>{dozenPieces(stock)}</small></td>
              <td><button className="stock-expand" aria-expanded={open} aria-label={open ? 'Tutup rincian size' : 'Buka rincian size'} onClick={() => setExpandedId(open ? null : m.id)}>{open ? '−' : '+'}</button></td>
            </tr>
            {open && <tr className="stock-detail-row"><td colSpan={6}><div className="stock-size-details">
              <div className="detail-caption"><span>RINCIAN SIZE</span><small>Komposisi transaksi dan saldo sesudah transaksi</small></div>
              {m.delta.map((delta, index) => <div className="size-ledger-card" key={index}>
                <span>SIZE {selected.sizes[index]}</span>
                <div><small>{delta >= 0 ? 'Masuk' : 'Keluar'}</small><strong className={delta < 0 ? 'neg' : delta > 0 ? 'pos' : ''}>{delta > 0 ? '+' : delta < 0 ? '−' : ''}{Math.abs(delta)} pcs</strong></div>
                <div><small>Stok akhir</small><strong>{m.balance[index]} pcs</strong></div>
                <em>{dozenPieces(m.balance[index])}</em>
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
  const move = (idx: number, dir: -1 | 1) => { const next=[...movements]; const target=idx+dir; if(target<0||target>=next.length)return; [next[idx],next[target]]=[next[target],next[idx]]; setMovements(next) }
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
  initialMovements.forEach((movement) => {
    if (!finalBySku.has(movement.sku)) finalBySku.set(movement.sku, [...movement.balance] as [number, number, number])
  })
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

  return <>
    <section className="hero-copy compact"><div className="eyebrow">GUDANG · BUKU MUTASI FG</div><h1>Mutasi Barang Jadi</h1><p>Setiap baris menunjukkan saldo sebelum, mutasi, dan saldo sesudah. Menggeser urutan menghitung ulang saldo buku per SKU—bukan saldo resmi, HPP, atau jurnal.</p></section>
    <div className="panel mutation-panel">
      <div className="table-toolbar"><div className="search-box compact-search"><Icon name="search" /> SKU, ref, pelanggan...</div><span className="reorder-hint"><Icon name="drag" /> Seret di desktop · panah di iPad</span><button className="soft-btn"><Icon name="filter" /> Semua jenis</button><button className="soft-btn" onClick={()=>setMovements(chronologicalMovements)}><Icon name="reset" /> Reset kronologis</button></div>
      <div className="mutation-list">{bookRows.map((movement,idx)=>{
        const movementTotal = movement.delta.reduce((sum, qty) => sum + qty, 0)
        const beforeTotal = movement.before.reduce((sum, qty) => sum + qty, 0)
        const afterTotal = movement.after.reduce((sum, qty) => sum + qty, 0)
        return <div className={`mutation-row ${draggedId === movement.id ? 'is-dragging' : ''}`} key={movement.id} draggable onDragStart={()=>setDraggedId(movement.id)} onDragOver={(event)=>event.preventDefault()} onDrop={()=>dropOn(movement.id)} onDragEnd={()=>setDraggedId(null)}>
          <div className="drag-grip" title="Seret untuk ubah urutan tampilan"><Icon name="drag" /></div>
          <div className="order-no">{String(idx+1).padStart(2,'0')}</div>
          <div className="mutation-main"><div><strong>{movement.sku}</strong><span className="type-pill">{movement.type}</span></div><p>{movement.ref} · {movement.note}</p><small>{movement.date} · factual ID {movement.id}</small></div>
          <div className="mutation-delta">{movement.delta.map((delta,index)=><span key={index}><small>SIZE {['28','29','30'][index]}</small><em className="balance-before">{movement.before[index]} pcs</em><strong className={delta<0?'neg':delta>0?'pos':''}>{delta>0?'+':''}{delta} pcs</strong><em className="balance-after">→ {movement.after[index]} pcs</em><i>{dozenPieces(movement.after[index])}</i></span>)}</div>
          <div className="mutation-total"><span>SALDO BUKU TOTAL</span><div className="total-flow"><b>{beforeTotal}</b><em>{movementTotal>0?'+':''}{movementTotal}</em><b>{afterTotal} pcs</b></div><small>{dozenPieces(beforeTotal)} → {dozenPieces(afterTotal)}</small></div>
          <div className="reorder"><button aria-label="Naikkan urutan" onClick={()=>move(idx,-1)} disabled={idx===0}><Icon name="up" /></button><button aria-label="Turunkan urutan" onClick={()=>move(idx,1)} disabled={idx===movements.length-1}><Icon name="down" /></button></div>
        </div>})}
      </div>
    </div>
  </>
}

function Placeholder() { return <div className="panel placeholder"><div className="placeholder-icon">◇</div><h2>Fondasinya sudah disiapkan.</h2><p>Modul ini berikutnya akan mengikuti flow bisnis yang sama: informasi penting terlihat sebelum user menekan tombol yang mengubah uang atau stok.</p></div> }

export default App
