import { Fragment, useMemo, useState } from 'react'

type Page = 'dashboard' | 'sales' | 'stock-card' | 'movements' | 'placeholder'
type NavSection = 'Produksi' | 'Gudang' | 'Penjualan' | 'Keuangan' | 'Master Data'

type SizeRow = { size: string; stock: number; qty: number }

type Movement = {
  id: string
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
  { id: 'MV-1048', date: '27 Agu 2026 · 13:44', ref: 'INV-260827-019', type: 'Penjualan', note: 'Nusantara Fashion', delta: [-8, -8, -8], balance: [96, 84, 108] },
  { id: 'MV-1047', date: '27 Agu 2026 · 10:22', ref: 'FG-260827-006', type: 'QC → FG', note: 'PO-260812-031', delta: [24, 24, 24], balance: [104, 92, 116] },
  { id: 'MV-1046', date: '26 Agu 2026 · 17:06', ref: 'INV-260826-027', type: 'Penjualan', note: 'Sumber Denim', delta: [-12, -8, -4], balance: [80, 68, 92] },
  { id: 'MV-1045', date: '26 Agu 2026 · 14:10', ref: 'ADJ-260826-004', type: 'Penyesuaian', note: 'Selisih opname disetujui owner', delta: [0, -1, 0], balance: [92, 76, 96] },
]

const money = (value: number) => new Intl.NumberFormat('id-ID', { style: 'currency', currency: 'IDR', maximumFractionDigits: 0 }).format(value)
const dozenPieces = (pcs: number) => `${Math.floor(Math.max(0, pcs) / 12)} lusin · ${Math.max(0, pcs) % 12} potong`

function parseQty(value: string, fallbackUnit: 'lusin' | 'pcs') {
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
    dashboard: '◫', Produksi: '⌁', Gudang: '▣', Penjualan: '▤', Keuangan: '▰', 'Master Data': '◉', audit: '⌘', search: '⌕', back: '←', stock: '◇', check: '✓', menu: '☰', up: '↑', down: '↓', reset: '↺', filter: '⌗', calendar: '◷', user: '●', arrow: '→', drag: '⋮⋮',
  }
  return <span className="icon" aria-hidden="true">{glyph[name] ?? '•'}</span>
}

function App() {
  const [page, setPage] = useState<Page>('dashboard')
  const [expanded, setExpanded] = useState<NavSection | null>(null)
  const [mobileNav, setMobileNav] = useState(false)
  const [qtyText, setQtyText] = useState('2')
  const [unit, setUnit] = useState<'lusin' | 'pcs'>('lusin')
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
    <section className="hero-copy compact"><div className="eyebrow">PENJUALAN · BARANG JADI</div><h1>Input penjualan</h1><p>Masukkan lusin atau pcs, cek komposisi size, lalu review. Stok selalu terlihat di titik keputusan.</p></section>

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
            <Field label="Jumlah penjualan">
              <div className="quantity-input"><input value={qtyText} onChange={(e) => setQtyText(e.target.value)} placeholder="2 atau 1 lusin 6 pcs"/><div className="unit-toggle"><button className={unit === 'lusin' ? 'active' : ''} onClick={() => setUnit('lusin')}>lusin</button><button className={unit === 'pcs' ? 'active' : ''} onClick={() => setUnit('pcs')}>pcs</button></div></div>
              <small className="helper">Boleh ketik bebas: “2 lusin”, “18 pcs”, atau “1 lusin 6 pcs”.</small>
            </Field>
            <div className="conversion"><span>KONVERSI</span><strong>{totalPcs} pcs</strong><small>{totalPcs > 0 ? `${(totalPcs/12).toLocaleString('id-ID',{maximumFractionDigits:2})} lusin ekuivalen` : 'Masukkan jumlah'}</small></div>
            <div className="price-box"><span>HARGA / LUSIN</span><strong>{money(1080000)}</strong></div>
          </div>

          <div className="composition-column"><div className="composition-head"><div><strong>Komposisi size</strong><span>Default rata; bebas diubah selama total cocok.</span></div><button className="mini-btn" onClick={distribute}>Ratakan otomatis</button></div>
            <div className="size-grid">{sizes.map((row, i) => <div className="size-card" key={row.size}><div><strong>Size {row.size}</strong><span>stok {row.stock}</span></div><input type="number" min="0" value={row.qty} onChange={(e) => { const next=[...sizes]; next[i]={...row,qty:Math.max(0,Number(e.target.value)||0)}; setSizes(next)}}/><small>pcs keluar</small></div>)}</div>
            <div className={`validation ${compositionOk && stockEnough ? 'success' : 'error'}`}><Icon name={compositionOk && stockEnough ? 'check' : 'filter'} /> {compositionOk ? (stockEnough ? 'Komposisi pas dan stok setiap size mencukupi.' : 'Komposisi pas, tetapi ada size melebihi stok.') : `Komposisi ${composed} pcs, target ${totalPcs} pcs.`}</div>
          </div>
        </div>

        <div className="sale-footer"><div><span>TOTAL PENJUALAN</span><strong>{money(saleTotal)}</strong><small>Nusantara Fashion · {totalPcs} pcs · komposisi {sizes.map(s=>s.qty).join(' / ')}</small></div><button className="primary-btn" disabled={!compositionOk || !stockEnough}>Review transaksi <Icon name="arrow" /></button></div>
      </div>
    </section>
  </>
}

function Field({ label, children }: { label: string; children: React.ReactNode }) { return <label className="field"><span>{label}</span>{children}</label> }

function StockCard() {
  const [expandedId, setExpandedId] = useState<string | null>(null)
  const currentStock = initialMovements[0].balance.reduce((sum, qty) => sum + qty, 0)

  return <>
    <section className="hero-copy compact"><div className="eyebrow">GUDANG · BARANG JADI</div><h1>Kartu stok FG</h1><p>Angka utama per transaksi. Tekan rincian untuk melihat komposisi size; urutannya selalu kronologis.</p></section>
    <div className="panel stock-summary">
      <div><div className="sku-title"><h2>73001</h2><span>Range 28–30</span></div><p>Denim Classic · Indigo · Gudang FG Utama</p></div>
      <div className="stock-total-hero"><span>STOK AKHIR</span><strong>{currentStock} pcs</strong><small>{dozenPieces(currentStock)}</small></div>
    </div>
    <div className="panel table-panel">
      <div className="table-toolbar"><div className="search-box compact-search"><Icon name="search" /> Cari ref / pelanggan...</div><button className="soft-btn"><Icon name="calendar" /> 30 hari</button><button className="soft-btn"><Icon name="filter" /> Filter</button></div>
      <div className="responsive-table stock-ledger"><table>
        <thead><tr><th>Waktu fisik</th><th>Transaksi</th><th className="number-head">Masuk</th><th className="number-head">Keluar</th><th className="number-head">Stok akhir</th><th aria-label="Rincian" /></tr></thead>
        <tbody>{initialMovements.map((m) => {
          const masuk = m.delta.reduce((sum, qty) => sum + Math.max(0, qty), 0)
          const keluar = m.delta.reduce((sum, qty) => sum + Math.abs(Math.min(0, qty)), 0)
          const stock = m.balance.reduce((sum, qty) => sum + qty, 0)
          const open = expandedId === m.id
          return <Fragment key={m.id}>
            <tr className={open ? 'stock-row-open' : ''}>
              <td><span className="ledger-date">{m.date}</span></td>
              <td><div className="ledger-transaction"><div><strong>{m.ref}</strong><span className="type-pill">{m.type}</span></div><small>{m.note}</small></div></td>
              <td className="ledger-number incoming">{masuk > 0 ? `+${masuk}` : '—'}<small>{masuk > 0 ? 'pcs' : ''}</small></td>
              <td className="ledger-number outgoing">{keluar > 0 ? `−${keluar}` : '—'}<small>{keluar > 0 ? 'pcs' : ''}</small></td>
              <td className="ledger-balance"><strong>{stock} pcs</strong><small>{dozenPieces(stock)}</small></td>
              <td><button className="stock-expand" aria-expanded={open} aria-label={open ? 'Tutup rincian size' : 'Buka rincian size'} onClick={() => setExpandedId(open ? null : m.id)}>{open ? '−' : '+'}</button></td>
            </tr>
            {open && <tr className="stock-detail-row"><td colSpan={6}><div className="stock-size-details">
              <div className="detail-caption"><span>RINCIAN SIZE</span><small>Komposisi transaksi dan saldo sesudah transaksi</small></div>
              {m.delta.map((delta, i) => <div className="size-ledger-card" key={i}>
                <span>SIZE {['28', '29', '30'][i]}</span>
                <div><small>{delta >= 0 ? 'Masuk' : 'Keluar'}</small><strong className={delta < 0 ? 'neg' : delta > 0 ? 'pos' : ''}>{delta > 0 ? '+' : delta < 0 ? '−' : ''}{Math.abs(delta)} pcs</strong></div>
                <div><small>Stok akhir</small><strong>{m.balance[i]} pcs</strong></div>
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
    const from = movements.findIndex((m) => m.id === draggedId)
    const to = movements.findIndex((m) => m.id === targetId)
    if (from < 0 || to < 0) return
    const next = [...movements]
    const [picked] = next.splice(from, 1)
    next.splice(to, 0, picked)
    setMovements(next)
    setDraggedId(null)
  }
  return <>
    <section className="hero-copy compact"><div className="eyebrow">GUDANG · BUKU MUTASI FG</div><h1>Mutasi Barang Jadi</h1><p>Susun urutan buku tanpa mengubah tanggal, saldo, HPP, atau jurnal. Seret di desktop; gunakan panah di iPad.</p></section>
    <div className="panel mutation-panel">
      <div className="table-toolbar"><div className="search-box compact-search"><Icon name="search" /> SKU, ref, pelanggan...</div><span className="reorder-hint"><Icon name="drag" /> Seret atau pakai panah</span><button className="soft-btn"><Icon name="filter" /> Semua jenis</button><button className="soft-btn" onClick={()=>setMovements(initialMovements)}><Icon name="reset" /> Reset kronologis</button></div>
      <div className="mutation-list">{movements.map((m,idx)=>
        <div className={`mutation-row ${draggedId === m.id ? 'is-dragging' : ''}`} key={m.id} draggable onDragStart={()=>setDraggedId(m.id)} onDragOver={(event)=>event.preventDefault()} onDrop={()=>dropOn(m.id)} onDragEnd={()=>setDraggedId(null)}>
          <div className="drag-grip" title="Seret untuk ubah urutan tampilan"><Icon name="drag" /></div>
          <div className="order-no">{String(idx+1).padStart(2,'0')}</div>
          <div className="mutation-main"><div><strong>{m.ref}</strong><span className="type-pill">{m.type}</span></div><p>{m.note}</p><small>{m.date} · factual ID {m.id}</small></div>
          <div className="mutation-delta">{m.delta.map((d,i)=><span key={i} className={d<0?'neg':d>0?'pos':''}>{['28','29','30'][i]}: {d>0?'+':''}{d}</span>)}</div>
          <div className="reorder"><button aria-label="Naikkan urutan" onClick={()=>move(idx,-1)} disabled={idx===0}><Icon name="up" /></button><button aria-label="Turunkan urutan" onClick={()=>move(idx,1)} disabled={idx===movements.length-1}><Icon name="down" /></button></div>
        </div>)}
      </div>
    </div>
  </>
}

function Placeholder() { return <div className="panel placeholder"><div className="placeholder-icon">◇</div><h2>Fondasinya sudah disiapkan.</h2><p>Modul ini berikutnya akan mengikuti flow bisnis yang sama: informasi penting terlihat sebelum user menekan tombol yang mengubah uang atau stok.</p></div> }

export default App
