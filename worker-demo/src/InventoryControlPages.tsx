import { SkuRangePage } from './demo/SkuRangePage'
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
  const [scope, setScope] = useState<AdjustmentScope>('Barang Jadi')
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
      <nav className="ic-mode-tabs"><button className={`ic-mode-option ${mode === 'browse' ? 'active' : ''}`} onClick={() => setMode('browse')}><i><History/></i><span><strong>Riwayat adjustment</strong><small>Lihat seluruh koreksi + / −</small></span><b>{inventoryCases.length}</b></button><button className={`ic-mode-option create ${mode === 'new' ? 'active' : ''}`} onClick={() => setMode('new')}><i><FilePlus2/></i><span><strong>Catat hasil cek fisik</strong><small>Isi saldo nyata · sistem hitung + / −</small></span><ArrowRight/></button></nav>
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
        <header><div><span>CATAT HASIL CEK FISIK · STOCK ADJUSTMENT</span><h2>Masukkan saldo nyata, bukan angka koreksi</h2><p>Pilih barang yang dihitung, isi jumlah fisik sebenarnya, lalu sistem otomatis membuat selisih plus atau minus terhadap ledger.</p></div><div className="ic-step-rail"><b className="active">1 · Hitung</b><i/><b>2 · Review</b><i/><b>3 · Post</b></div></header>
        <div className="ic-field-grid two area-stock"><label><span>Area stok</span><select aria-label="Area stok" value={scope} onChange={event=>changeScope(event.target.value as AdjustmentScope)}><option>Kain &amp; Roll</option><option>Aksesori</option><option>Barang Jadi</option></select></label></div>
        {scope==='Barang Jadi'?<SkuRangePage mode="adjust"/>:<div className="ic-draft-grid"><section className="ic-form-card"><div className="ic-field-grid two"><label><span>Item / roll</span><select value={draftItem.id} onChange={(event) => { setItemId(event.target.value); setPhysicalText(''); setNotice('') }}>{scopedItems.map((item) => <option key={item.id} value={item.id}>{item.label}</option>)}</select></label></div>
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
        </div>}
      </div>}
    </section>
    {mode==="browse"&&<SkuRangePage mode="adjust" historyOnly/>}
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
  const [query,setQuery]=useState('')
  const [statusFilter,setStatusFilter]=useState('Semua')
  const [selectedCaseId,setSelectedCaseId]=useState(conversionCases[0].id)
  const selectedCase = conversionCases.find((item) => item.id === selectedCaseId) ?? conversionCases[0]
  const visibleCases = conversionCases.filter((item) => `${item.id} ${item.source} ${item.target} ${item.reason} ${item.actor}`.toLowerCase().includes(query.toLowerCase()) && (statusFilter === 'Semua' || item.status === statusFilter))
  return <>
    <ControlHero type="brand"/>
    <section className="ic-metrics brand"><article><Repeat2/><span><small>CONVERSION TODAY</small><strong>36 pcs</strong><em>1 dokumen posted</em></span></article><article className="good"><PackageCheck/><span><small>RECONCILIATION</small><strong>36 out = 36 in</strong><em>Net inventory tetap nol</em></span></article><article><Sparkles/><span><small>CONVERSION COST</small><strong>{rupiah(12_600)}</strong><em>Label baru masuk HPP</em></span></article><article><ShieldCheck/><span><small>MASTER DATA</small><strong>Tidak diubah</strong><em>History asal tetap utuh</em></span></article></section>
    <div className="ic-conversion-layout">
      <aside className="panel ic-conversion-browser"><header><div><span>BROWSE CONVERSIONS</span><strong>Riwayat ganti merek</strong></div><small>{visibleCases.length} tampil</small></header><div className="ic-browser-tools"><label><Search/><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Cari merek, SKU, ref..."/></label><div><select value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)}><option>Semua</option><option>Draft</option><option>Posted</option><option>Reversed</option></select><button onClick={() => { setQuery(''); setStatusFilter('Semua') }}><RotateCcw/></button></div></div><div className="ic-conversion-case-list">{visibleCases.map((item) => <button key={item.id} className={selectedCase.id === item.id ? 'active' : ''} onClick={() => setSelectedCaseId(item.id)}><span><strong>{item.source}</strong><ArrowRight/><strong>{item.target}</strong></span><small>{item.id} · {item.reason} · {item.happenedAt}</small><em>{item.sizes}</em><b>{item.qty} pcs</b><i className={item.status.toLowerCase()}>{item.status}</i></button>)}</div><SkuRangePage mode="convert" historyOnly/><section className="ic-history-preview"><span>KASUS TERPILIH</span><strong>{selectedCase.id}</strong><p>{selectedCase.source} → {selectedCase.target}</p><small>{selectedCase.qty} pcs · {selectedCase.actor}</small></section></aside>
      <main className="panel ic-conversion-form"><header><div><span>BARANG JADI</span><h2>Pindah stok antarmerek</h2></div><Repeat2/></header><SkuRangePage mode="convert"/></main>
    </div>
  </>
}
