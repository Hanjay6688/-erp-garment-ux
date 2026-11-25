import { BrowsePane } from './components/BrowsePane'
import { WorkspaceFigures } from './components/WorkspaceFigures'
import BrandConversionForm from './demo/BrandConversionForm'
import {dozenPieces,fgQuantity} from './fgQuantity'
import {browseMatchPieces} from './browseMatch'
import { ReasonDialog } from './demo/planner/ReasonDialog'
import { SkuRangePage } from './demo/SkuRangePage'
import { useState, type ReactNode } from 'react'
import {
  AlertTriangle, ArrowRight, Boxes, Check, ClipboardCheck, FileClock,
  FilePlus2, History, MapPin, Layers3, Package, Shirt,
  RotateCcw, Search, ShieldCheck, Warehouse,
} from 'lucide-react'
import { productCatalog } from './productCatalog'
import './inventory-control.css'
import './stock-adjustment.css'

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
  dateKey?: string
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

const areaIcons = { 'Kain & Roll': Layers3, 'Aksesori': Package, 'Barang Jadi': Shirt }

const number = (value: number, digits = 6) => new Intl.NumberFormat('id-ID', { maximumFractionDigits: digits }).format(value)
const parseNumber = (value: string) => {
  const parsed = Number(value.trim().replace(',', '.'))
  return Number.isFinite(parsed) ? parsed : 0
}

const inventoryCases: InventoryCase[] = [
  { id:'ADJ-RM-260828-007', scope:'Kain & Roll', status:'Draft', item:'Lucy · Roll LCY-030', detail:'Sinaran · 96,5 yd tercatat', location:'Rak Kain A-02-02', reason:'Kerusakan hama', source:'Hitung fisik OPN-260828-C', actor:'Nina · Gudang', happenedAt:'28 Agu 2026 · 11:18', systemQty:96.5, physicalQty:89, unit:'yd', note:'Tepi kain berlubang dan tidak dapat dipakai.' },
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
  const tone = status === 'Posted' ? 'good' : status === 'Perlu koreksi sumber' ? 'danger' : status === 'Draft' ? 'neutral' : 'warn'
  return <span className={`ic-status ${tone}`}>{status}</span>
}

function ControlHero({ type }: { type: 'adjustment' | 'brand' }) {
  if (type === 'adjustment') return <section className="hero-copy compact ic-hero">
    <div><div className="eyebrow">GUDANG · KONTROL STOK</div><h1>Stock Adjustment</h1>
      <p>Catat hasil hitung fisik, periksa selisih dengan saldo buku, lalu telusuri dokumen koreksinya.</p></div>
  </section>
  return <section className="hero-copy compact ic-hero">
    <div><div className="eyebrow">GUDANG · INVENTORY CONTROL</div><h1>Ganti Merek</h1><p>Pilih SKU asal dan tujuan. Padanan dari master muncul sebagai saran.</p></div>
    <div className="ic-hero-rule brand"><ShieldCheck/><div><span>STOCK CONVERSION</span><strong>Sumber turun = tujuan naik</strong><small>Jumlah potong dan lokasi tetap sama. Ukuran tujuan bisa dipilih.</small></div></div>
  </section>
}

export function StockAdjustmentPage({navigation}:{navigation?:ReactNode}) {
  const [mode, setMode] = useState<'browse' | 'new'>('browse')
  const [query, setQuery] = useState('')
  const [scopeFilter, setScopeFilter] = useState('Semua')
  const [sourceOpen,setSourceOpen]=useState(false)
  const [editingId,setEditingId]=useState<string|null>(null)
  const [reviewCopies,setReviewCopies]=useState<InventoryCase[]>(()=>JSON.parse(sessionStorage.getItem('erp.owner.count-review.v1')??'[]'))
  const cases=[...reviewCopies,...inventoryCases.filter(d=>!reviewCopies.some(r=>r.id===d.id))]

  const [selectedId, setSelectedId] = useState(inventoryCases[0].id)
  const [scope, setScope] = useState<AdjustmentScope>('Barang Jadi')
  const [itemId, setItemId] = useState('LCY-030')
  const [physicalText, setPhysicalText] = useState('')
  const [physicalDate,setPhysicalDate]=useState('2026-11-24')
  const [reason, setReason] = useState('Kerusakan hama')
  const [reference, setReference] = useState('OPN-260828-C')
  const [note, setNote] = useState('')
  const [notice, setNotice] = useState('')

  const visibleCases = cases.filter((item) => {
    const quantities = [item.physicalQty - item.systemQty, item.systemQty, item.physicalQty]
    return (scopeFilter === 'Semua' || item.scope === scopeFilter)
      && browseMatchPieces(query, item.unit === 'pcs' ? quantities : [], item.id, item.scope, item.item, item.reason, item.source, item.actor,
        ...(item.unit === 'pcs' ? [] : quantities.map(qty=>`${number(Math.abs(qty))} ${item.unit}`)))
  })
  const selectedCase = visibleCases.find(item => item.id === selectedId) ?? visibleCases[0]
  const scopedItems = countItems.filter((item) => item.scope === scope)
  const baseItem = scopedItems.find((item) => item.id === itemId) ?? scopedItems[0]
  const original=cases.find(d=>d.id===editingId)
  const draftItem=original?.item===baseItem.label?{...baseItem,systemQty:original.systemQty}:baseItem
  const physical = parseNumber(physicalText)
  const delta = physical - draftItem.systemQty
  const hasPhysical = /^\d+(?:[.,]\d{1,6})?$/.test(physicalText.trim())&&Number.isFinite(Number(physicalText.replace(',','.')))
  const blockedPositiveFg = hasPhysical && delta > 0 && scope === 'Barang Jadi' && (draftItem.origin === 'PRODUCTION' || draftItem.origin === 'CONVERSION')
  const reasonCopy = adjustmentReasons.find(([label]) => label === reason)?.[1] ?? ''
  function reviewCase(){
    if (!selectedCase) return
    const known=countItems.find(d=>d.scope===selectedCase.scope&&d.label===selectedCase.item)
    if(!known){setSourceOpen(true);return}
    setPhysicalDate(selectedCase.dateKey??'2026-08-28');setScope(known.scope);setItemId(known.id);setEditingId(selectedCase.id);setPhysicalText(String(selectedCase.physicalQty).replace('.',','))
    setReason(selectedCase.reason);setReference(selectedCase.id);setNote(selectedCase.note);setMode('new');setNotice('')
  }
  function saveCountReview(){
    const id=reference.trim()
    const existing=cases.find(c=>c.id===id)
    if(existing&&existing.id!==editingId){setNotice('Nomor penyesuaian sudah dipakai.');return}
    const next:InventoryCase={id,scope,item:draftItem.label,detail:draftItem.detail,location:draftItem.location,status:'Menunggu review',reason,source:original?.source??'Cek fisik '+id,actor:original?.actor??'Owner demo',happenedAt:physicalDate,dateKey:physicalDate,systemQty:draftItem.systemQty,physicalQty:physical,unit:draftItem.unit,note}
    const copies=[next,...reviewCopies.filter(r=>r.id!==next.id)]
    setReviewCopies(copies);sessionStorage.setItem('erp.owner.count-review.v1',JSON.stringify(copies))
    setSelectedId(id);setScopeFilter('Semua');setQuery('');setMode('browse');setEditingId(null)
  }
  const accounting = delta < 0 ? 'Inventory Shrinkage / Other Expense' : delta > 0 ? 'Inventory Gain / Other Income' : 'Tidak ada jurnal'

  const changeScope = (next: AdjustmentScope) => {
    setScope(next)
    setItemId(countItems.find((item) => item.scope === next)?.id ?? '')
    setPhysicalText('')
    setNotice('')
  }

  return <div className="stock-adjust-page">
    <ControlHero type="adjustment"/>
    {navigation}
    <WorkspaceFigures label="Status dokumen cek fisik" figures={[
      {label:'Draf cek fisik',value:cases.filter(c=>c.status==='Draft').length,icon:ClipboardCheck,tone:'blue'},
      {label:'Menunggu review',value:cases.filter(c=>c.status==='Menunggu review').length,icon:FileClock,tone:'amber'},
      {label:'Perlu koreksi sumber',value:cases.filter(c=>c.status==='Perlu koreksi sumber').length,icon:AlertTriangle,tone:'red'},
    ]}/>
    <section className="ic-shell">
      <nav className="ic-mode-tabs" aria-label="Pekerjaan Stock Adjustment">
        <button type="button" className={'ic-mode-option '+(mode==='browse'?'active':'')} aria-pressed={mode==='browse'} onClick={()=>setMode('browse')}><History aria-hidden="true"/><strong>Riwayat adjustment</strong></button>
        <button type="button" className={'ic-mode-option '+(mode==='new'?'active':'')} aria-pressed={mode==='new'} onClick={()=>{setEditingId(null);setPhysicalDate('2026-11-24');setPhysicalText('');setReference('');setNote('');setNotice('');setMode('new')}}><FilePlus2 aria-hidden="true"/><strong>Catat hasil cek fisik</strong></button>
      </nav>
      {mode === 'browse' ? <div className="ic-browse-layout">
        <BrowsePane className="ic-case-browser" id="daftar-cek-fisik" aria-label="Riwayat penyesuaian stok">
          <header className="stock-section-head"><i><History aria-hidden="true"/></i><div><h2>Riwayat cek fisik</h2><small>{visibleCases.length} dokumen</small></div></header>
          <div className="ic-browser-tools"><label><Search aria-hidden="true"/><input type="search" aria-label="Cari riwayat cek fisik" value={query} onChange={event=>setQuery(event.target.value)} placeholder="Cari barang, jumlah, atau dokumen…"/></label>
            <div><select aria-label="Filter area stok" value={scopeFilter} onChange={event=>setScopeFilter(event.target.value)}><option>Semua</option><option>Kain &amp; Roll</option><option>Aksesori</option><option>Barang Jadi</option></select>
              <button type="button" aria-label="Reset filter riwayat" onClick={()=>{setQuery('');setScopeFilter('Semua')}}><RotateCcw aria-hidden="true"/></button></div></div>
          <div className="ic-case-list">{visibleCases.map(item=>{
            const delta = item.physicalQty - item.systemQty
            const Glyph = areaIcons[item.scope]
            return <button type="button" key={item.id} aria-pressed={selectedCase?.id===item.id} className={selectedCase?.id===item.id?'active':''} onClick={()=>{setSelectedId(item.id);if(window.matchMedia('(max-width: 860px)').matches)document.getElementById('detail-cek-fisik')?.scrollIntoView({block:'start'})}}>
              <i className="stock-item-icon"><Glyph aria-hidden="true"/></i>
              <div><strong className={delta<0?'negative':'positive'}>{delta>0?'+':''}{number(delta)} {item.unit}</strong><span>{item.item}</span>
                <small>{item.id} · {item.scope}</small></div>
              <StatusPill status={item.status}/>
            </button>
          })}{!visibleCases.length&&<p className="stock-empty">Tidak ada dokumen yang cocok dengan pencarian ini.</p>}</div>
        </BrowsePane>
        {selectedCase?<main className="ic-case-detail" id="detail-cek-fisik">
          <header className="stock-section-head"><i><ClipboardCheck aria-hidden="true"/></i><div><span>{selectedCase.scope}</span><h2>{selectedCase.item}</h2><p>{selectedCase.id} · {selectedCase.happenedAt}</p></div><StatusPill status={selectedCase.status}/></header>
          <BalanceEquation system={selectedCase.systemQty} physical={selectedCase.physicalQty} unit={selectedCase.unit} finished={selectedCase.scope==='Barang Jadi'}/>
          <div className="ic-detail-facts"><article><MapPin/><span><small>Lokasi &amp; pemeriksa</small><strong>{selectedCase.location}</strong><em>{selectedCase.actor}</em></span></article>
            <article><FileClock/><span><small>Dokumen sumber</small><strong>{selectedCase.source}</strong></span></article>
            <article><Boxes/><span><small>Identitas barang</small><strong>{selectedCase.detail}</strong></span></article></div>
          <section className="ic-reason-card"><span>ALASAN & CATATAN</span><strong>{selectedCase.reason}</strong><p>{selectedCase.note}</p></section>
          {selectedCase.status === 'Perlu koreksi sumber' && <div className="ic-guard danger"><AlertTriangle/><div><strong>Jangan buat stok produksi muncul dari adjustment.</strong><small>Lot ini berasal dari QC/FG receipt. Buka transaksi sumber lalu koreksi penerimaannya supaya WIP, HPP, dan jejak produksi tetap nyambung.</small></div></div>}
          <footer><a className="soft-btn stock-back" href="#daftar-cek-fisik">Kembali ke riwayat</a><button className="soft-btn" onClick={()=>setSourceOpen(true)}><FileClock aria-hidden="true"/> Lihat dokumen sumber</button><button className="primary-btn" onClick={reviewCase} disabled={selectedCase.status === 'Posted' || selectedCase.status === 'Perlu koreksi sumber'}>{selectedCase.status === 'Posted' ? 'Sudah diposting' : selectedCase.status === 'Perlu koreksi sumber' ? 'Posting diblokir' : 'Review kasus'} <ArrowRight/></button></footer>
        </main>:<main className="ic-case-detail stock-empty"><Search aria-hidden="true"/><h2>Belum ada dokumen terpilih</h2><p>Ubah pencarian atau pilih area stok lain.</p></main>}
      </div> : <div className="ic-draft">
        <header className="stock-section-head"><i><ClipboardCheck aria-hidden="true"/></i><div><span>{editingId?'Review dokumen':'Cek fisik baru'}</span><h2>{editingId?'Periksa hasil hitung':'Catat hasil hitung fisik'}</h2><p>Pilih area stok dan isi jumlah yang ditemukan saat dihitung.</p></div></header>
        <div className="ic-field-grid two area-stock"><label><span>Area stok</span><select aria-label="Area stok" disabled={!!editingId} value={scope} onChange={event=>changeScope(event.target.value as AdjustmentScope)}><option>Kain &amp; Roll</option><option>Aksesori</option><option>Barang Jadi</option></select></label></div>
        {scope==='Barang Jadi'?<SkuRangePage mode="adjust"/>:<div className="ic-draft-grid"><section className="ic-form-card"><div className="ic-field-grid two"><label><span>Item / roll</span><select value={draftItem.id} onChange={(event) => { setItemId(event.target.value); setPhysicalText(''); setNotice('') }}>{scopedItems.map((item) => <option key={item.id} value={item.id}>{item.label}</option>)}</select></label></div>
            <div className="ic-selected-item"><Warehouse/><div><span>ITEM TERPILIH</span><strong>{draftItem.label}</strong><small>{draftItem.detail} · {draftItem.location}</small></div></div>
            <div className="ic-count-entry"><label className="locked"><span>SALDO BUKU</span><div><strong>{number(draftItem.systemQty)} </strong><b>{draftItem.unit}</b><ShieldCheck/></div><small>Saldo tercatat saat draf dibuat.</small></label><i>→</i><label><span>HASIL HITUNG FISIK</span><div><input inputMode="decimal" value={physicalText} placeholder="Ketik hasil hitung" onChange={(event) => setPhysicalText(event.target.value.replace(/[^0-9.,]/g, ''))} onFocus={(event) => event.currentTarget.select()}/><b>{draftItem.unit}</b></div><small>Isi jumlah barang yang ditemukan.</small></label></div>
            <BalanceEquation system={draftItem.systemQty} physical={hasPhysical ? physical : null} unit={draftItem.unit}/>
            <div className="ic-reason-select"><span>Alasan selisih</span><div>{adjustmentReasons.map(([label, copy]) => <button key={label} className={reason === label ? 'active' : ''} onClick={() => setReason(label)}><strong>{label}</strong><small>{copy}</small><Check/></button>)}</div><p>{reasonCopy}</p></div>
            <div className="ic-field-grid three"><label><span>TANGGAL KEJADIAN / CEK</span><input aria-label="Tanggal cek fisik" type="date" value={physicalDate} onChange={e=>setPhysicalDate(e.target.value)}/></label><label><span>NOMOR PENYESUAIAN · WAJIB</span><input value={reference} readOnly={!!editingId} onChange={(event) => setReference(event.target.value)} placeholder="Contoh: OPN-260828-C"/></label><label><span>LOKASI</span><input value={draftItem.location} readOnly/></label></div>
            <label className="ic-note-field"><span>ALASAN PENYESUAIAN · WAJIB</span><textarea value={note} onChange={(event) => setNote(event.target.value)} placeholder="Ceritakan apa yang terjadi, siapa yang cek ulang, dan kondisi barang..."/></label>
          </section>
          <aside className="ic-review-card"><span>RINGKASAN KOREKSI</span><h3>{hasPhysical ? delta === 0 ? 'Tidak ada selisih' : `${delta > 0 ? '+' : ''}${number(delta)} ${draftItem.unit}` : 'Isi jumlah fisik'}</h3><p>{draftItem.label}</p><div><article><small>Saldo buku</small><strong>{number(draftItem.systemQty)} {draftItem.unit}</strong></article><article><small>JUMLAH FISIK</small><strong>{hasPhysical ? number(physical) : '—'} {hasPhysical ? draftItem.unit : ''}</strong></article><article className={delta < 0 ? 'danger' : delta > 0 ? 'good' : ''}><small>Selisih stok</small><strong>{hasPhysical ? `${delta > 0 ? '+' : ''}${number(delta)} ${draftItem.unit}` : '—'}</strong></article></div><section><small>Perkiraan jurnal</small><strong>{hasPhysical ? accounting : 'Menunggu angka fisik'}</strong><p>Jurnal baru terbentuk setelah review dan posting.</p></section>
            {blockedPositiveFg ? <div className="ic-guard danger"><AlertTriangle/><div><strong>Adjustment positif diblokir.</strong><small>Koreksi QC/FG receipt sumber lot produksi ini.</small></div></div> : <div className="ic-guard"><ShieldCheck/><div><strong>Saldo belum berubah.</strong><small>Draft ini hanya menyiapkan bukti untuk reviewer.</small></div></div>}
            <button className="primary-btn" disabled={!hasPhysical || !physicalDate || delta === 0 || !note.trim() || !reference.trim() || blockedPositiveFg} onClick={saveCountReview}>Review adjustment <ArrowRight/></button>
            {notice && <em className="ic-notice"><Check/> {notice}</em>}
          </aside>
        </div>}
      </div>}
    </section>
    {sourceOpen&&selectedCase&&<ReasonDialog title={'Sumber · '+selectedCase.id} onClose={()=>setSourceOpen(false)} closeLabel="Kembali"><h3>{selectedCase.source}</h3><p>{selectedCase.item} · {selectedCase.location}</p><p>{selectedCase.actor} · {selectedCase.happenedAt}</p><BalanceEquation system={selectedCase.systemQty} physical={selectedCase.physicalQty} unit={selectedCase.unit} finished={selectedCase.scope==='Barang Jadi'}/><p>{selectedCase.reason} · {selectedCase.note}</p></ReasonDialog>}
    {mode==="browse"&&<SkuRangePage mode="adjust" historyOnly/>}
  </div>
}

function BalanceEquation({system,physical,unit,finished=false}:{system:number;physical:number|null;unit:string;finished?:boolean}) {
  const delta = physical === null ? null : physical - system
  const quantity = (value:number) => number(value)+' '+unit
  return <dl className="stock-balance" aria-label="Perbandingan saldo stok">
    <div><dt>Saldo buku</dt><dd>{quantity(system)}</dd></div>
    <div data-delta={delta===null||delta===0?'zero':delta<0?'negative':'positive'}><dt>Selisih stok</dt>
      <dd>{delta===null?'—':(delta>0?'+':delta<0?'−':'')+quantity(Math.abs(delta))}</dd></div>
    <div><dt>Hasil hitung fisik</dt><dd>{physical===null?'—':quantity(physical)}</dd>
      {finished&&physical!==null&&<small>{dozenPieces(physical)}</small>}</div>
  </dl>
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
  const visibleCases = conversionCases.filter(item => browseMatchPieces(query,[item.qty],item.id,item.source,item.target,item.reason,item.actor) && (statusFilter === 'Semua' || item.status === statusFilter))
  return <>
    <ControlHero type="brand"/>
    <BrandConversionForm/>
    <SkuRangePage mode="convert" historyOnly/>
    <details className="panel wh-archive"><summary>Arsip ganti merek · Agustus 2026</summary>
      <aside className="panel ic-conversion-browser"><header><div><span>BROWSE CONVERSIONS</span><strong>Riwayat ganti merek</strong></div><small>{visibleCases.length} tampil</small></header><div className="ic-browser-tools"><label><Search/><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Cari merek, SKU, ref..."/></label><div><select value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)}><option>Semua</option><option>Draft</option><option>Posted</option><option>Reversed</option></select><button onClick={() => { setQuery(''); setStatusFilter('Semua') }}><RotateCcw/></button></div></div><div className="ic-conversion-case-list">{visibleCases.map((item) => <button key={item.id} className={selectedCase.id === item.id ? 'active' : ''} onClick={() => setSelectedCaseId(item.id)}><span><strong>{item.source}</strong><ArrowRight/><strong>{item.target}</strong></span><small>{item.id} · {item.reason} · {item.happenedAt}</small><em>{item.sizes}</em><b>{fgQuantity(item.qty)}</b><i className={item.status.toLowerCase()}>{item.status}</i></button>)}</div><section className="ic-history-preview"><span>KASUS TERPILIH</span><strong>{selectedCase.id}</strong><p>{selectedCase.source} → {selectedCase.target}</p><small>{fgQuantity(selectedCase.qty)} · {selectedCase.actor}</small></section></aside>
    </details>
  </>
}
