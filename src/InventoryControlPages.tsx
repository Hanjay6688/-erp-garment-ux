import { useMemo, useState } from 'react'
import {
  AlertTriangle, ArrowRight, Boxes, Check, ClipboardCheck, FileClock,
  FilePlus2, History, ImagePlus, MapPin, PackageCheck, Repeat2,
  RotateCcw, Search, ShieldCheck, Sparkles, Warehouse,
} from 'lucide-react'
import { productCatalog } from './productCatalog'
import './inventory-control.css'

type AdjustmentScope = 'Kain & Roll' | 'Aksesori' | 'Barang Jadi'
type AdjustmentStatus = 'Draft' | 'Menunggu review' | 'Posted' | 'Perlu koreksi sumber'
type InventoryCase = {
  id: string
  scope: AdjustmentScope
  status: AdjustmentStatus
  item: string
  detail: string
  location: string
  reason: string
  source: string
  actor: string
  happenedAt: string
  systemQty: number
  physicalQty: number
  unit: string
  note: string
}

type CountItem = {
  id: string
  scope: AdjustmentScope
  label: string
  detail: string
  unit: string
  systemQty: number
  location: string
  origin?: 'PURCHASE' | 'PRODUCTION' | 'CONVERSION'
}

const number = (value: number, digits = 1) => new Intl.NumberFormat('id-ID', { maximumFractionDigits: digits }).format(value)
const rupiah = (value: number) => new Intl.NumberFormat('id-ID', { style: 'currency', currency: 'IDR', maximumFractionDigits: 0 }).format(value)
const parseNumber = (value: string) => {
  const parsed = Number(value.trim().replace(',', '.'))
  return Number.isFinite(parsed) ? parsed : 0
}
const productKey = (brand: string, code: string) => `${brand}::${code}`

const inventoryCases: InventoryCase[] = [
  { id:'ADJ-RM-260828-007', scope:'Kain & Roll', status:'Draft', item:'Lucy · Roll LCY-030', detail:'Sinaran · 96,5 yd tercatat', location:'Rak Kain A-02-02', reason:'Kerusakan hama', source:'Hitung fisik OPN-260828-C', actor:'Nina · Gudang', happenedAt:'28 Agu 2026 · 11:18', systemQty:96.5, physicalQty:89, unit:'yd', note:'Tepi kain berlubang dan tidak dapat dipakai. Foto fisik wajib sebelum review.' },
  { id:'ADJ-ACC-260828-004', scope:'Aksesori', status:'Menunggu review', item:'Kancing Jeans 17 mm', detail:'ACC-KNC-17 · dua kotak terbuka', location:'Aksesori A-01', reason:'Koreksi hitung', source:'Sesi opname OPN-260828-A', actor:'Nina · Gudang', happenedAt:'28 Agu 2026 · 07:44', systemQty:12492, physicalQty:12480, unit:'pcs', note:'Selisih hitung sudah dicek ulang oleh dua orang. Saldo belum berubah sebelum posting.' },
  { id:'ADJ-FG-260828-003', scope:'Barang Jadi', status:'Perlu koreksi sumber', item:'Widie · SKU 73001 · Size 30', detail:'Grade Good · lot produksi', location:'Gudang FG Utama', reason:'Barang ditemukan', source:'Lot PRODUCTION FG-260827-005', actor:'Rina · QC', happenedAt:'28 Agu 2026 · 07:12', systemQty:90, physicalQty:92, unit:'pcs', note:'Surplus pada lot produksi tidak boleh diposting sebagai adjustment positif. Koreksi penerimaan QC/FG sumbernya.' },
]

const countItems: CountItem[] = [
  { id:'LCY-030', scope:'Kain & Roll', label:'Lucy · Roll LCY-030', detail:'Sinaran · Rak A-02-02', unit:'yd', systemQty:96.5, location:'Rak Kain A-02-02', origin:'PURCHASE' },
  { id:'LCY-029', scope:'Kain & Roll', label:'Lucy · Roll LCY-029', detail:'Sinaran · Area Retur', unit:'yd', systemQty:18.5, location:'Area Retur', origin:'PURCHASE' },
  { id:'ACC-KNC-17', scope:'Aksesori', label:'Kancing Jeans 17 mm', detail:'Inti Metal · Aksesori A-01', unit:'pcs', systemQty:12480, location:'Aksesori A-01', origin:'PURCHASE' },
  { id:'ACC-KRT-32', scope:'Aksesori', label:'Karet Pinggang 32 mm', detail:'Maju Elastik · Aksesori B-03', unit:'meter', systemQty:1860, location:'Aksesori B-03', origin:'PURCHASE' },
  ...productCatalog.flatMap((product) => product.sizes.map((size, index) => ({
    id:`${product.brand}-${product.code}-${size}-${product.grade}`,
    scope:'Barang Jadi' as AdjustmentScope,
    label:`${product.brand} · ${product.code} · Size ${size}`,
    detail:`${product.name} · Grade ${product.grade}`,
    unit:'pcs',
    systemQty:product.stocks[index],
    location:product.location,
    origin:'PRODUCTION' as const,
  }))),
]

const adjustmentReasons = [
  ['Hilang / dicuri', 'Barang tidak ditemukan setelah pencarian dan hitung ulang.'],
  ['Kerusakan hama', 'Tikus, serangga, jamur, atau kontaminasi lain.'],
  ['Banjir / bencana', 'Kerusakan karena air, api, atau kejadian luar biasa.'],
  ['Rusak tak terpakai', 'Barang ada secara fisik tetapi tak lagi layak digunakan.'],
  ['Barang ditemukan', 'Surplus fisik yang belum tercatat di sistem.'],
  ['Koreksi hitung', 'Kesalahan hitung setelah verifikasi ulang.'],
] as const

function StatusPill({ status }: { status: AdjustmentStatus }) {
  const tone = status === 'Posted' ? 'good' : status === 'Perlu koreksi sumber' ? 'danger' : 'warn'
  return <span className={`ic-status ${tone}`}>{status}</span>
}

function ControlHero({ type }: { type: 'adjustment' | 'brand' }) {
  return <section className="hero-copy compact ic-hero">
    <div><div className="eyebrow">GUDANG · INVENTORY CONTROL</div><h1>{type === 'adjustment' ? 'Stock Adjustment' : 'Ganti Merek'}</h1><p>{type === 'adjustment' ? 'Catat kondisi fisik yang benar; sistem menghitung selisihnya. Hilang, hama, banjir, rusak, atau barang mendadak ditemukan tetap punya alasan dan jejak.' : 'Pindahkan stok FG dari identitas merek asal ke merek tujuan tanpa mengganti master SKU dan tanpa menghapus sejarah lot.'}</p></div>
    <div className={`ic-hero-rule ${type}`}><ShieldCheck/><div><span>{type === 'adjustment' ? 'GOLDEN RULE' : 'STOCK CONVERSION'}</span><strong>{type === 'adjustment' ? 'Input fisik, bukan ketik plus/minus' : 'Sumber turun = tujuan naik'}</strong><small>{type === 'adjustment' ? 'System Qty terkunci. Delta selalu dihitung otomatis.' : 'Qty, size, grade, dan HPP sumber tetap terjaga.'}</small></div></div>
  </section>
}

export function StockAdjustmentPage() {
  const [mode, setMode] = useState<'browse' | 'new'>('browse')
  const [query, setQuery] = useState('')
  const [scopeFilter, setScopeFilter] = useState('Semua')
  const [selectedId, setSelectedId] = useState(inventoryCases[0].id)
  const [scope, setScope] = useState<AdjustmentScope>('Kain & Roll')
  const [itemId, setItemId] = useState('LCY-030')
  const [physicalText, setPhysicalText] = useState('')
  const [reason, setReason] = useState('Kerusakan hama')
  const [reference, setReference] = useState('OPN-260828-C')
  const [note, setNote] = useState('')
  const [notice, setNotice] = useState('')

  const visibleCases = useMemo(() => inventoryCases.filter((item) => {
    const haystack = `${item.id} ${item.scope} ${item.item} ${item.reason} ${item.source} ${item.actor}`.toLowerCase()
    return haystack.includes(query.toLowerCase()) && (scopeFilter === 'Semua' || item.scope === scopeFilter)
  }), [query, scopeFilter])
  const selectedCase = inventoryCases.find((item) => item.id === selectedId) ?? inventoryCases[0]
  const scopedItems = countItems.filter((item) => item.scope === scope)
  const draftItem = scopedItems.find((item) => item.id === itemId) ?? scopedItems[0]
  const physical = parseNumber(physicalText)
  const delta = physical - draftItem.systemQty
  const hasPhysical = physicalText.trim() !== ''
  const blockedPositiveFg = hasPhysical && delta > 0 && scope === 'Barang Jadi' && (draftItem.origin === 'PRODUCTION' || draftItem.origin === 'CONVERSION')
  const reasonCopy = adjustmentReasons.find(([label]) => label === reason)?.[1] ?? ''
  const accounting = delta < 0 ? 'Inventory Shrinkage / Other Expense' : delta > 0 ? 'Inventory Gain / Other Income' : 'Tidak ada jurnal'

  const changeScope = (next: AdjustmentScope) => {
    setScope(next)
    setItemId(countItems.find((item) => item.scope === next)?.id ?? '')
    setPhysicalText('')
    setNotice('')
  }

  return <>
    <ControlHero type="adjustment"/>
    <section className="ic-metrics">
      <article><ClipboardCheck/><span><small>OPEN CASES</small><strong>3 kasus</strong><em>Belum mengubah saldo</em></span></article>
      <article className="danger"><AlertTriangle/><span><small>NEGATIVE DELTA</small><strong>19,5 unit</strong><em>Perlu alasan & bukti</em></span></article>
      <article className="good"><History/><span><small>POSITIVE DELTA</small><strong>+2 pcs</strong><em>Tetap wajib sumber yang valid</em></span></article>
      <article><ShieldCheck/><span><small>CONTROL</small><strong>Draft → Review → Post</strong><em>Tidak ada edit saldo langsung</em></span></article>
    </section>
    <section className="panel ic-shell">
      <nav className="ic-mode-tabs"><button className={mode === 'browse' ? 'active' : ''} onClick={() => setMode('browse')}><History/> Riwayat adjustment <b>{inventoryCases.length}</b></button><button className={mode === 'new' ? 'active' : ''} onClick={() => setMode('new')}><FilePlus2/> Input hasil cek fisik</button></nav>
      {mode === 'browse' ? <div className="ic-browse-layout">
        <aside className="ic-case-browser">
          <header><div><span>BROWSE ADJUSTMENT</span><strong>Riwayat plus / minus stok</strong></div><small>{visibleCases.length} tampil</small></header>
          <div className="ic-browser-tools"><label><Search/><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Cari item, alasan, atau pemeriksa..."/></label><div><select value={scopeFilter} onChange={(event) => setScopeFilter(event.target.value)}><option>Semua</option><option>Kain & Roll</option><option>Aksesori</option><option>Barang Jadi</option></select><button onClick={() => { setQuery(''); setScopeFilter('Semua') }}><RotateCcw/></button></div></div>
          <div className="ic-case-list">{visibleCases.map((item) => {
            const itemDelta = item.physicalQty - item.systemQty
            return <button key={item.id} className={selectedCase.id === item.id ? 'active' : ''} onClick={() => setSelectedId(item.id)}><span className="ic-case-code">AD</span><div><strong>{item.item}</strong><small>{item.id} · {item.scope}</small><em>{item.reason} · {item.happenedAt}</em></div><b className={itemDelta < 0 ? 'negative' : 'positive'}>{itemDelta > 0 ? '+' : ''}{number(itemDelta)} {item.unit}</b><StatusPill status={item.status}/></button>
          })}</div>
        </aside>
        <main className="ic-case-detail">
          <header><div><span>ADJUSTMENT · {selectedCase.scope.toUpperCase()}</span><h2>{selectedCase.item}</h2><p>{selectedCase.id} · {selectedCase.happenedAt}</p></div><StatusPill status={selectedCase.status}/></header>
          <div className="ic-detail-facts"><article><MapPin/><span><small>LOCATION</small><strong>{selectedCase.location}</strong><em>{selectedCase.actor}</em></span></article><article><FileClock/><span><small>SOURCE</small><strong>{selectedCase.source}</strong><em>{selectedCase.reason}</em></span></article><article><Boxes/><span><small>ITEM DETAIL</small><strong>{selectedCase.detail}</strong><em>Identity locked after review</em></span></article></div>
          <BalanceEquation system={selectedCase.systemQty} physical={selectedCase.physicalQty} unit={selectedCase.unit}/>
          <section className="ic-reason-card"><span>ALASAN & CATATAN</span><strong>{selectedCase.reason}</strong><p>{selectedCase.note}</p></section>
          {selectedCase.status === 'Perlu koreksi sumber' && <div className="ic-guard danger"><AlertTriangle/><div><strong>Jangan buat stok produksi muncul dari adjustment.</strong><small>Lot ini berasal dari QC/FG receipt. Buka transaksi sumber lalu koreksi penerimaannya supaya WIP, HPP, dan jejak produksi tetap nyambung.</small></div></div>}
          <footer><button className="soft-btn">Lihat dokumen sumber</button><button className="primary-btn" disabled={selectedCase.status === 'Posted' || selectedCase.status === 'Perlu koreksi sumber'}>{selectedCase.status === 'Posted' ? 'Sudah diposting' : selectedCase.status === 'Perlu koreksi sumber' ? 'Posting diblokir' : 'Review kasus'} <ArrowRight/></button></footer>
        </main>
      </div> : <div className="ic-draft">
        <header><div><span>NEW STOCK ADJUSTMENT · PHYSICAL COUNT</span><h2>Isi jumlah fisik—plus/minus dihitung sistem</h2><p>Pilih satu item, masukkan jumlah yang benar-benar ada, lalu review selisih terhadap System Qty yang terkunci.</p></div><div className="ic-step-rail"><b className="active">1 · Draft</b><i/><b>2 · Review</b><i/><b>3 · Post</b></div></header>
        <div className="ic-draft-grid">
          <section className="ic-form-card">
            <div className="ic-field-grid two"><label><span>1 · AREA STOK</span><select value={scope} onChange={(event) => changeScope(event.target.value as AdjustmentScope)}><option>Kain & Roll</option><option>Aksesori</option><option>Barang Jadi</option></select></label><label><span>2 · ITEM / ROLL / SKU + SIZE</span><select value={draftItem.id} onChange={(event) => { setItemId(event.target.value); setPhysicalText(''); setNotice('') }}>{scopedItems.map((item) => <option key={item.id} value={item.id}>{item.label}</option>)}</select></label></div>
            <div className="ic-selected-item"><Warehouse/><div><span>ITEM TERPILIH</span><strong>{draftItem.label}</strong><small>{draftItem.detail} · {draftItem.location}</small></div></div>
            <div className="ic-count-entry"><label className="locked"><span>SYSTEM QTY · LOCKED</span><div><strong>{number(draftItem.systemQty)} </strong><b>{draftItem.unit}</b><ShieldCheck/></div><small>Diambil dari stock ledger saat draft dibuat.</small></label><i>→</i><label><span>JUMLAH FISIK SEBENARNYA · INPUT</span><div><input inputMode="decimal" value={physicalText} placeholder="Ketik hasil hitung" onChange={(event) => setPhysicalText(event.target.value.replace(/[^0-9.,]/g, ''))} onFocus={(event) => event.currentTarget.select()}/><b>{draftItem.unit}</b></div><small>Bukan angka plus/minus. Isi hasil hitung total; selisih dibuat otomatis.</small></label></div>
            <BalanceEquation system={draftItem.systemQty} physical={hasPhysical ? physical : draftItem.systemQty} unit={draftItem.unit}/>
            <div className="ic-reason-select"><span>3 · KENAPA BERBEDA?</span><div>{adjustmentReasons.map(([label, copy]) => <button key={label} className={reason === label ? 'active' : ''} onClick={() => setReason(label)}><strong>{label}</strong><small>{copy}</small><Check/></button>)}</div><p>{reasonCopy}</p></div>
            <div className="ic-field-grid three"><label><span>TANGGAL KEJADIAN / CEK</span><input type="date" defaultValue="2026-08-28"/></label><label><span>REFERENSI OPNAME / LAPORAN</span><input value={reference} onChange={(event) => setReference(event.target.value)} placeholder="Contoh: OPN-260828-C"/></label><label><span>LOKASI</span><input value={draftItem.location} readOnly/></label></div>
            <label className="ic-note-field"><span>CATATAN WAJIB</span><textarea value={note} onChange={(event) => setNote(event.target.value)} placeholder="Ceritakan apa yang terjadi, siapa yang cek ulang, dan kondisi barang..."/></label>
            <button className="ic-evidence"><ImagePlus/><span><strong>Tambah foto / bukti</strong><small>Kerusakan, lokasi, hasil hitung, atau laporan kejadian</small></span><b>Browse</b></button>
          </section>
          <aside className="ic-review-card"><span>REVIEW IMPACT</span><h3>{hasPhysical ? delta === 0 ? 'Tidak ada selisih' : `${delta > 0 ? '+' : ''}${number(delta)} ${draftItem.unit}` : 'Isi jumlah fisik'}</h3><p>{draftItem.label}</p><div><article><small>SYSTEM QTY</small><strong>{number(draftItem.systemQty)} {draftItem.unit}</strong></article><article><small>JUMLAH FISIK</small><strong>{hasPhysical ? number(physical) : '—'} {hasPhysical ? draftItem.unit : ''}</strong></article><article className={delta < 0 ? 'danger' : delta > 0 ? 'good' : ''}><small>LEDGER DELTA</small><strong>{hasPhysical ? `${delta > 0 ? '+' : ''}${number(delta)} ${draftItem.unit}` : '—'}</strong></article></div><section><small>ACCOUNTING PREVIEW</small><strong>{hasPhysical ? accounting : 'Menunggu angka fisik'}</strong><p>Jurnal baru terbentuk setelah review dan posting.</p></section>
            {blockedPositiveFg ? <div className="ic-guard danger"><AlertTriangle/><div><strong>Adjustment positif diblokir.</strong><small>Koreksi QC/FG receipt sumber lot produksi ini.</small></div></div> : <div className="ic-guard"><ShieldCheck/><div><strong>Saldo belum berubah.</strong><small>Draft ini hanya menyiapkan bukti untuk reviewer.</small></div></div>}
            <button className="primary-btn" disabled={!hasPhysical || delta === 0 || !note.trim() || !reference.trim() || blockedPositiveFg} onClick={() => setNotice('Draft simulasi siap direview. Belum ada data yang dikirim ke backend.')}>Review adjustment <ArrowRight/></button>
            {notice && <em className="ic-notice"><Check/> {notice}</em>}
          </aside>
        </div>
      </div>}
    </section>
  </>
}

function BalanceEquation({ system, physical, unit }: { system: number; physical: number; unit: string }) {
  const delta = physical - system
  return <div className="ic-balance"><span><small>SYSTEM QTY</small><strong>{number(system)} {unit}</strong></span><i>{delta >= 0 ? '+' : '−'}</i><span className={delta < 0 ? 'negative' : delta > 0 ? 'positive' : ''}><small>DERIVED DELTA</small><strong>{delta > 0 ? '+' : delta < 0 ? '−' : ''}{number(Math.abs(delta))} {unit}</strong></span><i>=</i><span><small>PHYSICAL COUNT</small><strong>{number(physical)} {unit}</strong></span></div>
}

type ConversionCase = {
  id: string
  source: string
  target: string
  qty: number
  sizes: string
  reason: 'REBRAND' | 'RELABEL' | 'REPACK' | 'CORRECTION'
  status: 'Draft' | 'Posted' | 'Reversed'
  happenedAt: string
  actor: string
}

const conversionCases: ConversionCase[] = [
  { id:'BRD-260827-004', source:'Widie · 73001', target:'Vivo · 73001', qty:36, sizes:'28: 12 · 29: 12 · 30: 12', reason:'RELABEL', status:'Posted', happenedAt:'27 Agu 2026 · 15:42', actor:'Nina · Gudang FG' },
  { id:'BRD-260826-002', source:'Vivo · 73002', target:'Widie · 73002', qty:12, sizes:'31: 0 · 32: 6 · 33: 6', reason:'REBRAND', status:'Draft', happenedAt:'26 Agu 2026 · 11:18', actor:'Owner' },
  { id:'BRD-260825-001', source:'Widie · 73001', target:'Vivo · 73001', qty:24, sizes:'28: 8 · 29: 8 · 30: 8', reason:'CORRECTION', status:'Reversed', happenedAt:'25 Agu 2026 · 09:08', actor:'Owner' },
]

export function BrandConversionPage() {
  const pairable = productCatalog.filter((item) => productCatalog.some((candidate) => candidate.code === item.code && candidate.brand !== item.brand))
  const [query, setQuery] = useState('')
  const [statusFilter, setStatusFilter] = useState('Semua')
  const [selectedCaseId, setSelectedCaseId] = useState(conversionCases[0].id)
  const [sourceKey, setSourceKey] = useState(productKey('Widie', '73001'))
  const source = pairable.find((item) => productKey(item.brand, item.code) === sourceKey) ?? pairable[0]
  const targets = productCatalog.filter((item) => item.code === source.code && item.brand !== source.brand)
  const [targetKey, setTargetKey] = useState(productKey('Vivo', '73001'))
  const target = targets.find((item) => productKey(item.brand, item.code) === targetKey) ?? targets[0]
  const [quantities, setQuantities] = useState(['12', '12', '12'])
  const [reason, setReason] = useState<ConversionCase['reason']>('RELABEL')
  const [labelCost, setLabelCost] = useState('350')
  const [note, setNote] = useState('Ganti label merek untuk memenuhi alokasi penjualan tanpa mengubah konstruksi produk.')
  const [notice, setNotice] = useState('')
  const selectedCase = conversionCases.find((item) => item.id === selectedCaseId) ?? conversionCases[0]
  const visibleCases = conversionCases.filter((item) => `${item.id} ${item.source} ${item.target} ${item.reason} ${item.actor}`.toLowerCase().includes(query.toLowerCase()) && (statusFilter === 'Semua' || item.status === statusFilter))
  const qtyValues = quantities.map(parseNumber)
  const totalQty = qtyValues.reduce((sum, qty) => sum + qty, 0)
  const stockEnough = qtyValues.every((qty, index) => qty <= source.stocks[index])
  const compatible = source.code === target.code && source.range === target.range
  const sourceHpp = source.code === '73001' ? 187450 : 193200
  const extraCost = parseNumber(labelCost)
  const targetHpp = sourceHpp + extraCost

  const changeSource = (nextKey: string) => {
    const next = pairable.find((item) => productKey(item.brand, item.code) === nextKey) ?? pairable[0]
    const nextTarget = productCatalog.find((item) => item.code === next.code && item.brand !== next.brand)
    setSourceKey(nextKey)
    setTargetKey(nextTarget ? productKey(nextTarget.brand, nextTarget.code) : '')
    setQuantities(next.sizes.map(() => '0'))
    setNotice('')
  }

  return <>
    <ControlHero type="brand"/>
    <section className="ic-metrics brand"><article><Repeat2/><span><small>CONVERSION TODAY</small><strong>36 pcs</strong><em>1 dokumen posted</em></span></article><article className="good"><PackageCheck/><span><small>RECONCILIATION</small><strong>36 out = 36 in</strong><em>Net inventory tetap nol</em></span></article><article><Sparkles/><span><small>CONVERSION COST</small><strong>{rupiah(12_600)}</strong><em>Label baru masuk HPP</em></span></article><article><ShieldCheck/><span><small>MASTER DATA</small><strong>Tidak diubah</strong><em>History asal tetap utuh</em></span></article></section>
    <div className="ic-conversion-layout">
      <aside className="panel ic-conversion-browser"><header><div><span>BROWSE CONVERSIONS</span><strong>Riwayat ganti merek</strong></div><small>{visibleCases.length} tampil</small></header><div className="ic-browser-tools"><label><Search/><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Cari merek, SKU, ref..."/></label><div><select value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)}><option>Semua</option><option>Draft</option><option>Posted</option><option>Reversed</option></select><button onClick={() => { setQuery(''); setStatusFilter('Semua') }}><RotateCcw/></button></div></div><div className="ic-conversion-case-list">{visibleCases.map((item) => <button key={item.id} className={selectedCase.id === item.id ? 'active' : ''} onClick={() => setSelectedCaseId(item.id)}><span><strong>{item.source}</strong><ArrowRight/><strong>{item.target}</strong></span><small>{item.id} · {item.reason} · {item.happenedAt}</small><em>{item.sizes}</em><b>{item.qty} pcs</b><i className={item.status.toLowerCase()}>{item.status}</i></button>)}</div><section className="ic-history-preview"><span>KASUS TERPILIH</span><strong>{selectedCase.id}</strong><p>{selectedCase.source} → {selectedCase.target}</p><small>{selectedCase.qty} pcs · {selectedCase.actor}</small></section></aside>
      <main className="panel ic-conversion-form"><header><div><span>NEW STOCK CONVERSION</span><h2>Ganti identitas merek, bukan barang fisiknya</h2><p>Produk yang sama dipindahkan antarmerek dengan ukuran dan grade tetap.</p></div><Repeat2/></header>
        <section className="ic-conversion-route"><label><span>1 · SOURCE STOCK</span><select value={sourceKey} onChange={(event) => changeSource(event.target.value)}>{pairable.map((item) => <option key={productKey(item.brand, item.code)} value={productKey(item.brand, item.code)}>{item.brand} · {item.code} · {item.name} · {item.grade}</option>)}</select><small>{source.location} · Range {source.range}</small></label><i><ArrowRight/></i><label><span>2 · TARGET BRAND / SKU</span><select value={productKey(target.brand, target.code)} onChange={(event) => setTargetKey(event.target.value)}>{targets.map((item) => <option key={productKey(item.brand, item.code)} value={productKey(item.brand, item.code)}>{item.brand} · {item.code} · {item.name}</option>)}</select><small>Masuk {target.location} · grade mengikuti sumber: <b>{source.grade}</b></small></label></section>
        <div className="ic-identity-lock"><ShieldCheck/><div><strong>Master SKU tidak diubah</strong><small>{source.brand} · {source.code} tetap punya history sendiri. Dokumen ini membuat stock-out sumber dan stock-in tujuan yang saling menyeimbangkan.</small></div></div>
        <section className="ic-size-transfer"><header><div><span>3 · QTY PER SIZE</span><strong>Tentukan jumlah yang benar-benar diganti labelnya</strong></div><small>Enter / panah untuk pindah sel</small></header><div className="ic-size-head"><span>Size</span><span>Source On Hand</span><span>Transfer Qty</span><span>Source After</span><span>Target +</span></div>{source.sizes.map((size, index) => {
          const qty = qtyValues[index]
          const invalid = qty > source.stocks[index]
          return <article key={size} className={invalid ? 'invalid' : ''}><strong>{size}</strong><span>{source.stocks[index]} pcs</span><label><input inputMode="numeric" value={quantities[index]} placeholder="0" onChange={(event) => setQuantities((current) => current.map((value, rowIndex) => rowIndex === index ? event.target.value.replace(/\D/g, '') : value))} onFocus={(event) => event.currentTarget.select()}/><b>pcs</b></label><span className={invalid ? 'negative' : ''}>{source.stocks[index] - qty} pcs</span><span className="positive">+{qty} pcs</span></article>
        })}<footer><span><small>TOTAL SOURCE OUT</small><strong>− {totalQty} pcs</strong></span><i>=</i><span><small>TOTAL TARGET IN</small><strong>+ {totalQty} pcs</strong></span><b className={stockEnough && totalQty > 0 ? 'good' : 'danger'}>{stockEnough ? totalQty > 0 ? 'BALANCED' : 'ISI QTY' : 'STOK KURANG'}</b></footer></section>
        <section className="ic-conversion-meta"><label><span>4 · ALASAN</span><select value={reason} onChange={(event) => setReason(event.target.value as ConversionCase['reason'])}><option>REBRAND</option><option>RELABEL</option><option>REPACK</option><option>CORRECTION</option></select></label><label><span>BIAYA LABEL / PCS</span><div><b>Rp</b><input inputMode="numeric" value={labelCost} onChange={(event) => setLabelCost(event.target.value.replace(/\D/g, ''))} onFocus={(event) => event.currentTarget.select()}/></div></label><label><span>TANGGAL KONVERSI</span><input type="date" defaultValue="2026-08-28"/></label></section>
        <label className="ic-note-field"><span>CATATAN / REFERENSI PERSETUJUAN</span><textarea value={note} onChange={(event) => setNote(event.target.value)} placeholder="Kenapa merek diganti dan siapa yang menyetujui?"/></label>
        <section className="ic-hpp-preview"><div><span><small>HPP SUMBER / PCS</small><strong>{rupiah(sourceHpp)}</strong></span><i>+</i><span><small>RELABEL / PCS</small><strong>{rupiah(extraCost)}</strong></span><i>=</i><span className="good"><small>HPP TUJUAN / PCS</small><strong>{rupiah(targetHpp)}</strong></span></div><p>Nilai stok sumber ditransfer. Biaya label/repack ditambahkan sebagai conversion cost—bukan dibuang ke nol.</p></section>
        <div className="ic-conversion-guards"><article><Check/><span><strong>Size tetap sama</strong><small>{source.sizes.join(' · ')}</small></span></article><article><Check/><span><strong>Grade tidak naik</strong><small>Target tetap {source.grade}, termasuk jika sumber BS</small></span></article><article><Check/><span><strong>Lot & HPP terlacak</strong><small>Sumber lama tetap bisa diaudit</small></span></article></div>
        {!compatible && <div className="ic-guard danger"><AlertTriangle/><div><strong>Produk tidak kompatibel.</strong><small>Kode dan range sumber harus sama dengan target.</small></div></div>}
        <footer className="ic-conversion-actions"><div><span>NET STOCK</span><strong>0 pcs</strong><small>−{totalQty} sumber + {totalQty} tujuan</small></div><button className="primary-btn" disabled={!compatible || !stockEnough || totalQty === 0 || !note.trim()} onClick={() => setNotice('Draft konversi simulasi siap direview. Backend belum disentuh.')}>Review conversion <ArrowRight/></button></footer>
        {notice && <em className="ic-notice"><Check/> {notice}</em>}
      </main>
    </div>
  </>
}
