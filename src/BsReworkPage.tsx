import { useMemo, useState } from 'react'
import type { DragEvent } from 'react'
import {
  ArrowLeft, ArrowRight, Check, CheckCircle2, ChevronRight, CircleMinus, CirclePlus,
  ClipboardCheck, Clock3, FilePlus2, FileText, Filter, GripVertical, History, Link2,
  PackageCheck, Plus, RotateCcw, Search, ShieldCheck, Shirt, UserRound, Waves, Wrench, X,
} from 'lucide-react'
import type { QcFinalResult } from './QcFinalPage'
import './bs-rework.css'

type SourceMode = 'ATTACHED_FG' | 'STANDALONE'
type CaseStatus = 'OPEN' | 'ASSIGNED' | 'IN_REWORK' | 'QC_REWORK' | 'GOOD_RESTORED' | 'BS_FINAL'
type SizeValues = [number, number, number]
type SizeInputs = [string, string, string]

type WorkComponent = {
  id: string
  name: string
  note: string
  rate: number
}

type BsCase = {
  id: string
  source: SourceMode
  sourceNote?: string
  payrollNote?: string
  parentId: string
  batchId: string
  mandor: string
  brand: string
  sku: string
  material: string
  sizes: [string, string, string]
  qtyBySize: SizeValues
  origin: 'QC' | 'LAUNDRY_RETURN' | 'SEWING' | 'OTHER'
  reason: string
  status: CaseStatus
  componentIds: string[]
  createdAt: string
}

type LedgerKind = 'BS_DEDUCTION' | 'REWORK_RELEASE' | 'STUCK_HOLD' | 'STUCK_RELEASE'

type LedgerItem = {
  id: string
  kind: LedgerKind
  label: string
  sign: -1 | 1
  qtyBySize: SizeValues
  rate: number
  amount: number
  originId?: string
  caseId?: string
  sourceLabel: string
  createdAt: string
}

const components: WorkComponent[] = [
  { id: 'jahit', name: 'Jahit utama', note: 'Badan dan sambungan model', rate: 8250 },
  { id: 'obras', name: 'Obras / ceming', note: 'Rapikan sambungan dan kampuh', rate: 2500 },
  { id: 'pinggang', name: 'Ban & pinggang', note: 'Ban, stik, dan penguat', rate: 2600 },
  { id: 'saku', name: 'Saku & ritsleting', note: 'Komponen fungsi depan/belakang', rate: 2300 },
  { id: 'centang', name: 'Centang / bartack', note: 'Pengunci titik rawan', rate: 800 },
  { id: 'kancing', name: 'Kancing', note: 'Pasang dan cek fungsi', rate: 500 },
  { id: 'plastik', name: 'Plastik & packing', note: 'Bungkus hasil akhir', rate: 500 },
  { id: 'hangtag', name: 'Hangtag / label', note: 'Identitas barang jadi', rate: 600 },
  { id: 'lipat', name: 'Lipat akhir', note: 'Lipat sebelum serah', rate: 400 },
]

const statusSteps: Array<{ id: Exclude<CaseStatus, 'BS_FINAL'>; label: string }> = [
  { id: 'OPEN', label: 'Dicatat' },
  { id: 'ASSIGNED', label: 'Ditugaskan' },
  { id: 'IN_REWORK', label: 'Dikerjakan' },
  { id: 'QC_REWORK', label: 'QC ulang' },
  { id: 'GOOD_RESTORED', label: 'Pulih' },
]

const statusLabels: Record<CaseStatus, string> = {
  OPEN: 'Baru dicatat',
  ASSIGNED: 'Sudah ditugaskan',
  IN_REWORK: 'Sedang bikin bagus',
  QC_REWORK: 'Menunggu QC ulang',
  GOOD_RESTORED: 'Bikin bagus selesai',
  BS_FINAL: 'BS final',
}

const sum = (values: SizeValues) => values.reduce((total, value) => total + value, 0)
const money = (value: number) => `Rp${Math.round(value).toLocaleString('id-ID')}`
const asSizeValues = (values: number[]): SizeValues => [values[0] ?? 0, values[1] ?? 0, values[2] ?? 0]
const asSizeInputs = (values: string[]): SizeInputs => [values[0] ?? '', values[1] ?? '', values[2] ?? '']
const cleanQuantity = (raw: string, max = 9999) => {
  const digits = raw.replace(/\D/g, '').replace(/^0+(?=\d)/, '')
  return digits === '' ? '' : String(Math.min(max, Number(digits)))
}
const componentRate = (ids: string[]) => components.filter((component) => ids.includes(component.id)).reduce((total, component) => total + component.rate, 0)
const firstPositiveUnit = (values: SizeValues): SizeValues => {
  const index = values.findIndex((value) => value > 0)
  return index < 0 ? [0, 0, 0] : asSizeValues(values.map((_, row) => row === index ? 1 : 0))
}
const subtractSizes = (source: SizeValues, used: SizeValues): SizeValues => asSizeValues(source.map((value, index) => Math.max(0, value - used[index])))
const addSizes = (left: SizeValues, right: SizeValues): SizeValues => asSizeValues(left.map((value, index) => value + right[index]))

function seedCases(result?: QcFinalResult | null): BsCase[] {
  const sizes: [string, string, string] = result?.sizes ?? ['31', '32', '33']
  const incomingBs: SizeValues = result ? asSizeValues(result.qcBs) : [2, 1, 0]
  const bsQty: SizeValues = sum(incomingBs) > 0 ? incomingBs : [2, 1, 0]
  return [
    {
      id: 'BS-260827-018', source: 'ATTACHED_FG', sourceNote: 'FG-260827-010', payrollNote: 'GJ-260827-010',
      parentId: result?.parentId ?? 'POT-260826-041', batchId: result?.batchId ?? '041-02', mandor: result?.mandor ?? 'Mandor Asep',
      brand: result?.brand ?? 'Widie', sku: result?.finalSku ?? '73001', material: result?.material ?? 'Malibu', sizes,
      qtyBySize: bsQty, origin: 'QC', reason: 'Jahitan bawah perlu dirapikan dan centang ulang.', status: 'QC_REWORK',
      componentIds: ['obras', 'centang', 'lipat'], createdAt: '27 Agu 2026 · 18:42',
    },
    {
      id: 'BS-260828-003', source: 'STANDALONE', sourceNote: 'NOTA-BS-260828-003',
      parentId: 'POT-260825-038', batchId: '038-01', mandor: 'Mandor Ujang', brand: 'Vivo', sku: '73002', material: 'Lucy', sizes: ['31', '32', '33'],
      qtyBySize: [0, 2, 1], origin: 'SEWING', reason: 'Kancing dan ritsleting tidak lolos pemeriksaan.', status: 'OPEN',
      componentIds: ['saku', 'kancing'], createdAt: '28 Agu 2026 · 09:12',
    },
  ]
}

function seedLedger(cases: BsCase[], result?: QcFinalResult | null): LedgerItem[] {
  const primary = cases[0]
  const deductionRate = componentRate(primary.componentIds)
  const firstRestored = firstPositiveUnit(primary.qtyBySize)
  const stuckSource: SizeValues = result ? asSizeValues(result.stuckBySize) : [2, 0, 0]
  const stuckQty: SizeValues = sum(stuckSource) > 0 ? stuckSource : [2, 0, 0]
  const firstSusulan = firstPositiveUnit(stuckQty)
  return [
    { id: 'ADJ-BS-018', kind: 'BS_DEDUCTION', label: 'BS · komponen belum diterima', sign: -1, qtyBySize: primary.qtyBySize, rate: deductionRate, amount: sum(primary.qtyBySize) * deductionRate, caseId: primary.id, sourceLabel: `${primary.id} · ${primary.sourceNote}`, createdAt: '27 Agu · 18:42' },
    { id: 'ADJ-RW-018-01', kind: 'REWORK_RELEASE', label: 'Bikin bagus · pulihkan BS', sign: 1, qtyBySize: firstRestored, rate: deductionRate, amount: sum(firstRestored) * deductionRate, caseId: primary.id, originId: 'ADJ-BS-018', sourceLabel: `Asal ADJ-BS-018 · ${primary.id}`, createdAt: '28 Agu · 09:40' },
    { id: 'HOLD-LDR-1049', kind: 'STUCK_HOLD', label: 'Belum balik dari Laundry', sign: -1, qtyBySize: stuckQty, rate: 3700, amount: sum(stuckQty) * 3700, sourceLabel: `${result?.laundry ?? 'Laundry Intan'} · MV-1049`, createdAt: '27 Agu · 17:30' },
    { id: 'SUS-LDR-1049-01', kind: 'STUCK_RELEASE', label: 'Susulan · fisik sudah balik', sign: 1, qtyBySize: firstSusulan, rate: 3700, amount: sum(firstSusulan) * 3700, originId: 'HOLD-LDR-1049', sourceLabel: 'Asal HOLD-LDR-1049 · sudah diterima Mandor', createdAt: '28 Agu · 10:05' },
  ]
}

function ledgerTone(kind: LedgerKind) {
  if (kind === 'BS_DEDUCTION') return 'minus bs'
  if (kind === 'STUCK_HOLD') return 'minus stuck'
  if (kind === 'REWORK_RELEASE') return 'plus rework'
  return 'plus susulan'
}

export default function BsReworkPage({ initialResult, onBack }: { initialResult?: QcFinalResult | null; onBack: () => void }) {
  const [cases, setCases] = useState<BsCase[]>(() => seedCases(initialResult))
  const [ledger, setLedger] = useState<LedgerItem[]>(() => seedLedger(seedCases(initialResult), initialResult))
  const [selectedId, setSelectedId] = useState('BS-260827-018')
  const [query, setQuery] = useState('')
  const [mandorFilter, setMandorFilter] = useState('Semua mandor')
  const [statusFilter, setStatusFilter] = useState('Semua status')
  const [sourceFilter, setSourceFilter] = useState('Semua sumber')
  const [showForm, setShowForm] = useState(false)
  const [noteItemIds, setNoteItemIds] = useState<string[]>([])
  const [dragOver, setDragOver] = useState(false)
  const [reworkInputs, setReworkInputs] = useState<SizeInputs>(['', '', ''])
  const [susulanInputs, setSusulanInputs] = useState<SizeInputs>(['', '', ''])
  const [notice, setNotice] = useState<string | null>(null)

  const mandors = Array.from(new Set(cases.map((item) => item.mandor)))
  const visibleCases = useMemo(() => cases.filter((item) => {
    const haystack = `${item.id} ${item.parentId} ${item.batchId} ${item.mandor} ${item.brand} ${item.sku} ${item.material} ${item.sourceNote ?? ''}`.toLowerCase()
    return haystack.includes(query.toLowerCase())
      && (mandorFilter === 'Semua mandor' || item.mandor === mandorFilter)
      && (statusFilter === 'Semua status' || item.status === statusFilter)
      && (sourceFilter === 'Semua sumber' || item.source === sourceFilter)
  }), [cases, query, mandorFilter, statusFilter, sourceFilter])
  const selected = visibleCases.find((item) => item.id === selectedId) ?? cases.find((item) => item.id === selectedId) ?? visibleCases[0] ?? cases[0]
  const caseDeduction = selected ? ledger.find((item) => item.kind === 'BS_DEDUCTION' && item.caseId === selected.id) : undefined
  const releasedForCase: SizeValues = selected && caseDeduction
    ? ledger.filter((item) => item.kind === 'REWORK_RELEASE' && item.originId === caseDeduction.id).reduce<SizeValues>((total, item) => addSizes(total, item.qtyBySize), [0, 0, 0])
    : [0, 0, 0]
  const reworkRemaining: SizeValues = selected ? subtractSizes(selected.qtyBySize, releasedForCase) : [0, 0, 0]
  const hold = ledger.find((item) => item.kind === 'STUCK_HOLD')
  const holdReleased: SizeValues = hold
    ? ledger.filter((item) => item.kind === 'STUCK_RELEASE' && item.originId === hold.id).reduce<SizeValues>((total, item) => addSizes(total, item.qtyBySize), [0, 0, 0])
    : [0, 0, 0]
  const holdRemaining: SizeValues = hold ? subtractSizes(hold.qtyBySize, holdReleased) : [0, 0, 0]
  const queueItems = ledger.filter((item) => !noteItemIds.includes(item.id))
  const noteItems = noteItemIds.map((id) => ledger.find((item) => item.id === id)).filter((item): item is LedgerItem => Boolean(item))
  const noteAdjustment = noteItems.reduce((total, item) => total + item.sign * item.amount, 0)
  const allComponentRate = components.reduce((total, component) => total + component.rate, 0)
  const baseQty = initialResult ? sum(asSizeValues(initialResult.expected)) : 132
  const baseValue = baseQty * allComponentRate

  const moveToNote = (id: string) => {
    setNoteItemIds((current) => current.includes(id) ? current : [...current, id])
    setNotice('Baris dipindahkan ke nota. Sumber dan link asal tetap menempel.')
  }
  const removeFromNote = (id: string) => setNoteItemIds((current) => current.filter((itemId) => itemId !== id))
  const handleDrop = (event: DragEvent<HTMLElement>) => {
    event.preventDefault()
    setDragOver(false)
    const id = event.dataTransfer.getData('text/plain')
    if (ledger.some((item) => item.id === id)) moveToNote(id)
  }
  const nextStatus = () => {
    if (!selected) return
    const next: Partial<Record<CaseStatus, CaseStatus>> = { OPEN: 'ASSIGNED', ASSIGNED: 'IN_REWORK', IN_REWORK: 'QC_REWORK' }
    const status = next[selected.status]
    if (!status) return
    setCases((current) => current.map((item) => item.id === selected.id ? { ...item, status } : item))
    setNotice(`${selected.id} sekarang: ${statusLabels[status]}.`)
  }
  const postReworkRelease = () => {
    if (!selected || !caseDeduction) return
    const requested = asSizeValues(reworkInputs.map((value, index) => Math.min(Number(value) || 0, reworkRemaining[index])))
    const qty = sum(requested)
    if (qty <= 0) return
    const item: LedgerItem = {
      id: `ADJ-RW-${selected.id.replace(/\D/g, '')}-${ledger.length + 1}`,
      kind: 'REWORK_RELEASE', label: 'Bikin bagus · pulihkan BS', sign: 1, qtyBySize: requested,
      rate: caseDeduction.rate, amount: qty * caseDeduction.rate, originId: caseDeduction.id, caseId: selected.id,
      sourceLabel: `Asal ${caseDeduction.id} · QC rework lulus`, createdAt: '28 Agu · baru saja',
    }
    const remainingAfter = subtractSizes(reworkRemaining, requested)
    setLedger((current) => [...current, item])
    setCases((current) => current.map((entry) => entry.id === selected.id ? { ...entry, status: sum(remainingAfter) === 0 ? 'GOOD_RESTORED' : 'QC_REWORK' } : entry))
    setReworkInputs(['', '', ''])
    setNotice(`${qty} pcs bikin bagus menjadi +${money(item.amount)} dan terkunci ke ${caseDeduction.id}.`)
  }
  const postSusulan = () => {
    if (!hold) return
    const requested = asSizeValues(susulanInputs.map((value, index) => Math.min(Number(value) || 0, holdRemaining[index])))
    const qty = sum(requested)
    if (qty <= 0) return
    const item: LedgerItem = {
      id: `SUS-${hold.id.replace('HOLD-', '')}-${ledger.length + 1}`,
      kind: 'STUCK_RELEASE', label: 'Susulan · fisik sudah balik', sign: 1, qtyBySize: requested,
      rate: hold.rate, amount: qty * hold.rate, originId: hold.id, sourceLabel: `Asal ${hold.id} · diterima Mandor`, createdAt: '28 Agu · baru saja',
    }
    setLedger((current) => [...current, item])
    setSusulanInputs(['', '', ''])
    setNotice(`${qty} pcs susulan melepas hold +${money(item.amount)}. Barang tetap harus melewati QC.`)
  }
  const markBsFinal = () => {
    if (!selected) return
    setCases((current) => current.map((item) => item.id === selected.id ? { ...item, status: 'BS_FINAL' } : item))
    setNotice(`${selected.id} ditetapkan BS final. Minus asal tetap tercatat.`)
  }

  const openCases = cases.filter((item) => !['GOOD_RESTORED', 'BS_FINAL'].includes(item.status)).length
  const totalBsOutstanding = ledger.filter((item) => item.kind === 'BS_DEDUCTION').reduce((total, deduction) => {
    const released = ledger.filter((item) => item.kind === 'REWORK_RELEASE' && item.originId === deduction.id).reduce((value, item) => value + item.amount, 0)
    return total + Math.max(0, deduction.amount - released)
  }, 0)

  return <>
    <section className="hero-copy compact bsr-hero">
      <div><div className="eyebrow">PRODUKSI · MUTU & PENYELESAIAN</div><h1>Barang BS & Rework</h1><p>BS bisa dicatat kapan saja. Minus, bikin bagus, hold Laundry, dan susulan tetap berdiri sendiri—tetapi selalu saling terhubung.</p></div>
      <div className="bsr-hero-actions"><button type="button" className="soft-btn" onClick={onBack}><ArrowLeft/> Kembali</button><button type="button" className="primary-btn" onClick={() => setShowForm(true)}><FilePlus2/> Catat BS baru</button></div>
    </section>

    <section className="bsr-rule-banner"><ShieldCheck/><div><strong>Dua pasangan yang tidak boleh dicampur</strong><span><b>BS −</b> dipulihkan oleh <b>Bikin bagus +</b>. <b>Belum balik −</b> dilepas oleh <b>Susulan +</b>. Setiap plus wajib menunjuk minus asal dan tidak boleh melebihi sisanya.</span></div></section>

    {notice && <div className="bsr-notice"><CheckCircle2/><span>{notice}</span><button type="button" onClick={() => setNotice(null)} aria-label="Tutup pemberitahuan"><X/></button></div>}

    <section className="bsr-kpis">
      <article className="panel"><span>KASUS AKTIF</span><strong>{openCases}</strong><small>Butuh tindakan Mandor / QC</small></article>
      <article className="panel danger"><span>MINUS BS TERSISA</span><strong>{money(totalBsOutstanding)}</strong><small>Belum dipulihkan bikin bagus</small></article>
      <article className="panel warn"><span>MASIH DI LAUNDRY</span><strong>{sum(holdRemaining)} pcs</strong><small>{hold?.sourceLabel ?? 'Tidak ada hold aktif'}</small></article>
      <article className="panel good"><span>PLUS TERHUBUNG</span><strong>{ledger.filter((item) => item.sign > 0).length}</strong><small>Bikin bagus + susulan berjejak</small></article>
    </section>

    <section className="panel bsr-toolbar">
      <label className="bsr-search"><Search/><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Cari BS, PO, batch, nota, SKU..."/></label>
      <label><Filter/><select value={mandorFilter} onChange={(event) => setMandorFilter(event.target.value)}><option>Semua mandor</option>{mandors.map((mandor) => <option key={mandor}>{mandor}</option>)}</select></label>
      <label><select value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)}><option>Semua status</option>{Object.entries(statusLabels).map(([value, label]) => <option value={value} key={value}>{label}</option>)}</select></label>
      <label><select value={sourceFilter} onChange={(event) => setSourceFilter(event.target.value)}><option>Semua sumber</option><option value="ATTACHED_FG">Nempel nota FG</option><option value="STANDALONE">Nota BS sendiri</option></select></label>
    </section>

    <section className="bsr-master-detail">
      <aside className="panel bsr-case-browser">
        <header><div><span>DAFTAR KASUS</span><strong>{visibleCases.length} kasus</strong></div><ClipboardCheck/></header>
        <div className="bsr-case-list">{visibleCases.map((item, index) => <button type="button" className={selected?.id === item.id ? 'active' : ''} onClick={() => { setSelectedId(item.id); setReworkInputs(['', '', '']) }} key={item.id}>
          <span className="bsr-case-index">{String(index + 1).padStart(2, '0')}</span>
          <span className="bsr-case-copy"><small>{item.brand} · SKU {item.sku}</small><strong>{item.id}</strong><em><UserRound/>{item.mandor}</em><span>{item.parentId} · Batch {item.batchId}</span></span>
          <span className={`bsr-status ${item.status.toLowerCase()}`}>{statusLabels[item.status]}</span><ChevronRight/>
        </button>)}{visibleCases.length === 0 && <div className="bsr-empty"><Search/><strong>Kasus tidak ketemu</strong><small>Ubah filter atau kata pencarian.</small></div>}</div>
      </aside>

      {selected && <div className="bsr-detail-stack">
        <article className="panel bsr-case-detail">
          <header className="bsr-detail-head"><span className="bsr-detail-icon"><Wrench/></span><div><small>{selected.source === 'ATTACHED_FG' ? 'NEMPEL NOTA SERAH FG' : 'NOTA BS SENDIRI'} · {selected.sourceNote}</small><h2>{selected.id} · {selected.brand} SKU {selected.sku}</h2><p>{selected.parentId} · Batch {selected.batchId} · {selected.material}</p></div><div className="bsr-mandor"><UserRound/><span><small>MANDOR</small><strong>{selected.mandor}</strong></span></div><strong className="bsr-case-total">{sum(selected.qtyBySize)} BS</strong></header>

          <div className={`bsr-timeline ${selected.status === 'BS_FINAL' ? 'is-final' : ''}`}>{statusSteps.map((step, index) => {
            const activeIndex = statusSteps.findIndex((item) => item.id === selected.status)
            const done = selected.status === 'BS_FINAL' ? false : index <= activeIndex
            return <div className={done ? 'done' : ''} key={step.id}><span>{done ? <Check/> : index + 1}</span><strong>{step.label}</strong>{index < statusSteps.length - 1 && <i/>}</div>
          })}{selected.status === 'BS_FINAL' && <em><CircleMinus/> BS final</em>}</div>

          <section className="bsr-case-facts">
            <div><span>ASAL TEMUAN</span><strong>{selected.origin === 'QC' ? 'QC finishing' : selected.origin === 'LAUNDRY_RETURN' ? 'Kembali Laundry' : selected.origin === 'SEWING' ? 'WIP & Sewing' : 'Lainnya'}</strong></div>
            <div><span>REFERENSI NOTA</span><strong>{selected.payrollNote ?? 'Belum masuk nota gajian'}</strong></div>
            <div><span>DICATAT</span><strong>{selected.createdAt}</strong></div>
            <div className="wide"><span>ALASAN</span><strong>{selected.reason}</strong></div>
          </section>

          <section className="bsr-size-table">
            <header><span>SIZE</span><span>BS AWAL</span><span>SUDAH BIKIN BAGUS</span><span>SISA MINUS</span></header>
            {selected.sizes.map((size, index) => <div key={size}><strong>{size}</strong><span>{selected.qtyBySize[index]} pcs</span><span className="plus">{releasedForCase[index]} pcs</span><strong className={reworkRemaining[index] > 0 ? 'minus' : 'done'}>{reworkRemaining[index]} pcs</strong></div>)}
          </section>

          <section className="bsr-component-snapshot"><header><div><span>SNAPSHOT KOMPONEN TERDAMPAK</span><strong>{caseDeduction?.id ?? 'Belum ada adjustment'}</strong></div><em><ShieldCheck/> terkunci</em></header><div>{selected.componentIds.map((id) => { const component = components.find((item) => item.id === id); return component ? <article key={id}><span><Wrench/></span><div><strong>{component.name}</strong><small>{component.note}</small></div><b>{money(component.rate)}</b></article> : null })}</div><footer><span>Minus per pcs</span><strong>− {money(caseDeduction?.rate ?? componentRate(selected.componentIds))}</strong></footer></section>

          {selected.status === 'QC_REWORK' && sum(reworkRemaining) > 0 && <section className="bsr-release-card rework"><header><CirclePlus/><div><span>BIKIN BAGUS · PLUS TERHUBUNG</span><h3>Berapa yang lulus QC ulang?</h3><p>Plus tidak boleh lebih besar dari sisa minus <b>{caseDeduction?.id}</b>.</p></div></header><div className="bsr-release-grid" data-keyboard-grid>{selected.sizes.map((size, index) => <label key={size}><span>SIZE {size} · maks {reworkRemaining[index]}</span><input inputMode="numeric" data-grid-row={0} data-grid-col={index} value={reworkInputs[index]} onFocus={(event) => event.currentTarget.select()} onChange={(event) => setReworkInputs((current) => asSizeInputs(current.map((value, row) => row === index ? cleanQuantity(event.target.value, reworkRemaining[index]) : value)))}/></label>)}</div><div className="bsr-release-actions"><button type="button" className="soft-btn danger" onClick={markBsFinal}><CircleMinus/> Tetapkan sisa BS final</button><button type="button" className="primary-btn" disabled={sum(asSizeValues(reworkInputs.map(Number))) <= 0} onClick={postReworkRelease}>Lulus QC & buat plus <ArrowRight/></button></div></section>}

          {['OPEN', 'ASSIGNED', 'IN_REWORK'].includes(selected.status) && <div className="bsr-next-action"><div><Clock3/><span><strong>{statusLabels[selected.status]}</strong><small>Riwayat tidak dihapus saat tahap berganti.</small></span></div><button type="button" className="primary-btn" onClick={nextStatus}>{selected.status === 'OPEN' ? 'Tugaskan rework' : selected.status === 'ASSIGNED' ? 'Mulai bikin bagus' : 'Kirim ke QC ulang'} <ArrowRight/></button></div>}
          {selected.status === 'GOOD_RESTORED' && <div className="bsr-closed good"><CheckCircle2/><div><strong>Seluruh minus sudah dipulihkan</strong><span>Plus rework tetap menunjuk adjustment BS asal.</span></div></div>}
          {selected.status === 'BS_FINAL' && <div className="bsr-closed final"><CircleMinus/><div><strong>Ditetapkan BS final</strong><span>Minus tidak hilang. Koreksi berikutnya wajib melalui reversal berjejak.</span></div></div>}
        </article>

        {hold && <article className="panel bsr-stuck-card"><header><Waves/><div><span>STUCK LAUNDRY · BUKAN BS</span><h2>{hold.id} · {hold.sourceLabel}</h2><p>Mandor yang mengonfirmasi fisik kembali. Sesudah itu Susulan melepas hold, tetapi barang tetap masuk QC.</p></div><strong>{sum(holdRemaining)} pcs di luar</strong></header><div className="bsr-stuck-body"><section className="bsr-stuck-sizes">{(initialResult?.sizes ?? selected.sizes).map((size, index) => <div key={size}><span>Size {size}</span><strong>{holdRemaining[index]} pcs</strong><small>sisa hold</small></div>)}</section><section className="bsr-susulan-entry"><div><span>SUSULAN · PLUS HOLD</span><strong>Pilih qty yang benar-benar diterima</strong></div><div className="bsr-release-grid" data-keyboard-grid>{(initialResult?.sizes ?? selected.sizes).map((size, index) => <label key={size}><span>SIZE {size} · maks {holdRemaining[index]}</span><input inputMode="numeric" data-grid-row={0} data-grid-col={index} value={susulanInputs[index]} onFocus={(event) => event.currentTarget.select()} onChange={(event) => setSusulanInputs((current) => asSizeInputs(current.map((value, row) => row === index ? cleanQuantity(event.target.value, holdRemaining[index]) : value)))}/></label>)}</div><button type="button" className="primary-btn" disabled={sum(asSizeValues(susulanInputs.map(Number))) <= 0} onClick={postSusulan}>Catat fisik balik & buat Susulan + <ArrowRight/></button></section></div></article>}

        <article className="panel bsr-note-composer">
          <header><div><span>AJUKAN GAJIAN · SUSUN NOTA</span><h2>Tarik baris ke nota seperti memindahkan baris kerja</h2><p>Kalau drag kurang nyaman di HP, tombol “Masukkan nota” memberi hasil yang sama.</p></div><FileText/></header>
          <div className="bsr-note-layout">
            <section className="bsr-ledger-queue"><div className="bsr-column-title"><span>SIAP MASUK NOTA</span><strong>{queueItems.length} baris</strong></div>{queueItems.map((item) => <article className={`bsr-ledger-item ${ledgerTone(item.kind)}`} draggable onDragStart={(event) => { event.dataTransfer.setData('text/plain', item.id); event.dataTransfer.effectAllowed = 'move' }} key={item.id}><GripVertical/><div><small>{item.id}</small><strong>{item.label}</strong><span>{item.sourceLabel}</span><em>{sum(item.qtyBySize)} pcs × {money(item.rate)}</em></div><b>{item.sign > 0 ? '+' : '−'} {money(item.amount)}</b><button type="button" onClick={() => moveToNote(item.id)}>Masukkan nota <ArrowRight/></button></article>)}{queueItems.length === 0 && <div className="bsr-queue-empty"><Check/><span>Semua baris sudah di nota.</span></div>}</section>
            <section className={`bsr-payroll-note ${dragOver ? 'drag-over' : ''}`} onDragOver={(event) => { event.preventDefault(); setDragOver(true); event.dataTransfer.dropEffect = 'move' }} onDragLeave={() => setDragOver(false)} onDrop={handleDrop}>
              <header><span>NOTA GAJI</span><strong>GJ-260828-DRAFT</strong><small>Mandor {initialResult?.mandor ?? selected.mandor} · 28 Agu 2026</small></header>
              <div className="bsr-note-base"><span>Upah dasar · snapshot BOM</span><b>{baseQty} pcs × {money(allComponentRate)}</b><strong>{money(baseValue)}</strong></div>
              <div className="bsr-note-lines">{noteItems.map((item) => <article className={ledgerTone(item.kind)} key={item.id}><div><small>{item.id}</small><strong>{item.label}</strong><span>{sum(item.qtyBySize)} pcs × {money(item.rate)} · {item.sourceLabel}</span></div><b>{item.sign > 0 ? '+' : '−'} {money(item.amount)}</b><button type="button" onClick={() => removeFromNote(item.id)} aria-label={`Keluarkan ${item.id} dari nota`}><RotateCcw/></button></article>)}{noteItems.length === 0 && <div className="bsr-drop-empty"><GripVertical/><strong>Drop baris di sini</strong><span>Baris asal akan hilang dari antrean, bukan diduplikasi.</span></div>}</div>
              <footer><span><small>Penyesuaian terpilih</small><b className={noteAdjustment < 0 ? 'negative' : 'positive'}>{noteAdjustment >= 0 ? '+' : '−'} {money(Math.abs(noteAdjustment))}</b></span><div><small>DRAFT DIBAYARKAN</small><strong>{money(baseValue + noteAdjustment)}</strong></div><button type="button" className="primary-btn" disabled={noteItems.length === 0}><PackageCheck/> Simpan draft nota</button></footer>
            </section>
          </div>
        </article>
      </div>}
    </section>

    {showForm && <NewBsDialog result={initialResult} onClose={() => setShowForm(false)} onCreate={(createdCase, deduction) => {
      setCases((current) => [createdCase, ...current])
      setLedger((current) => [deduction, ...current])
      setSelectedId(createdCase.id)
      setShowForm(false)
      setNotice(`${createdCase.id} dibuat dengan minus ${money(deduction.amount)}. Kasus belum masuk nota sampai dipilih.`)
    }}/>} 
  </>
}

function NewBsDialog({ result, onClose, onCreate }: { result?: QcFinalResult | null; onClose: () => void; onCreate: (item: BsCase, deduction: LedgerItem) => void }) {
  const sizes: [string, string, string] = result?.sizes ?? ['31', '32', '33']
  const [source, setSource] = useState<SourceMode>('ATTACHED_FG')
  const [qtyInputs, setQtyInputs] = useState<SizeInputs>(['', '', ''])
  const [selectedComponents, setSelectedComponents] = useState<string[]>(['obras', 'centang', 'lipat'])
  const [reason, setReason] = useState('')
  const [origin, setOrigin] = useState<BsCase['origin']>('QC')
  const quantities = asSizeValues(qtyInputs.map((value) => Number(value) || 0))
  const qty = sum(quantities)
  const rate = componentRate(selectedComponents)
  const create = () => {
    if (qty <= 0 || rate <= 0 || reason.trim() === '') return
    const serial = String(Date.now()).slice(-4)
    const id = `BS-260828-${serial}`
    const item: BsCase = {
      id, source, sourceNote: source === 'ATTACHED_FG' ? 'FG-260827-010' : `NOTA-${id}`,
      parentId: result?.parentId ?? 'POT-260826-041', batchId: result?.batchId ?? '041-02', mandor: result?.mandor ?? 'Mandor Asep',
      brand: result?.brand ?? 'Widie', sku: result?.finalSku ?? '73001', material: result?.material ?? 'Malibu', sizes,
      qtyBySize: quantities, origin, reason: reason.trim(), status: 'OPEN', componentIds: selectedComponents, createdAt: '28 Agu 2026 · baru saja',
    }
    const deduction: LedgerItem = {
      id: `ADJ-${id}`, kind: 'BS_DEDUCTION', label: 'BS · komponen belum diterima', sign: -1, qtyBySize: quantities,
      rate, amount: qty * rate, caseId: id, sourceLabel: `${id} · ${item.sourceNote}`, createdAt: '28 Agu · baru saja',
    }
    onCreate(item, deduction)
  }

  return <div className="bsr-dialog-layer" role="presentation"><section className="bsr-dialog" role="dialog" aria-modal="true" aria-labelledby="new-bs-title">
    <header><div><span>CATAT BARANG BS</span><h2 id="new-bs-title">Bisa nempel nota FG atau berdiri sendiri</h2><p>Identitas PO, batch, Mandor, size, dan snapshot komponen tetap wajib supaya minusnya bisa ditelusuri.</p></div><button type="button" onClick={onClose} aria-label="Tutup"><X/></button></header>
    <div className="bsr-dialog-body">
      <section><div className="bsr-form-title"><b>01</b><span><strong>Pilih sumber nota</strong><small>Menempel tidak menyalin atau memindahkan kasus.</small></span></div><div className="bsr-source-toggle"><button type="button" className={source === 'ATTACHED_FG' ? 'active' : ''} onClick={() => setSource('ATTACHED_FG')}><Link2/><span><strong>Nempel nota Serah FG</strong><small>FG-260827-010 · {result?.mandor ?? 'Mandor Asep'}</small></span></button><button type="button" className={source === 'STANDALONE' ? 'active' : ''} onClick={() => setSource('STANDALONE')}><FileText/><span><strong>Nota BS sendiri</strong><small>Referensi mandiri, boleh ditempel nanti.</small></span></button></div></section>
      <section><div className="bsr-form-title"><b>02</b><span><strong>Identitas & jumlah per size</strong><small>Qty tidak dibagi rata.</small></span></div><div className="bsr-identity-grid"><label><span>POTONGAN INDUK</span><input value={result?.parentId ?? 'POT-260826-041'} readOnly/></label><label><span>CHILD BATCH</span><input value={result?.batchId ?? '041-02'} readOnly/></label><label><span>MANDOR</span><input value={result?.mandor ?? 'Mandor Asep'} readOnly/></label><label><span>ASAL TEMUAN</span><select value={origin} onChange={(event) => setOrigin(event.target.value as BsCase['origin'])}><option value="QC">QC finishing</option><option value="LAUNDRY_RETURN">Kembali Laundry</option><option value="SEWING">WIP & Sewing</option><option value="OTHER">Lainnya</option></select></label></div><div className="bsr-new-size-grid" data-keyboard-grid>{sizes.map((size, index) => <label key={size}><span>SIZE {size}</span><input inputMode="numeric" data-grid-row={0} data-grid-col={index} value={qtyInputs[index]} placeholder="0" onFocus={(event) => event.currentTarget.select()} onChange={(event) => setQtyInputs((current) => asSizeInputs(current.map((value, row) => row === index ? cleanQuantity(event.target.value) : value)))}/></label>)}</div></section>
      <section><div className="bsr-form-title"><b>03</b><span><strong>Komponen yang belum diterima</strong><small>Komponen terpilih menjadi minus; yang sudah selesai tetap dibayar.</small></span></div><div className="bsr-component-picker">{components.map((component) => { const active = selectedComponents.includes(component.id); return <button type="button" className={active ? 'active' : ''} onClick={() => setSelectedComponents((current) => active ? current.filter((id) => id !== component.id) : [...current, component.id])} key={component.id}><span>{active && <Check/>}</span><div><strong>{component.name}</strong><small>{component.note}</small></div><b>{money(component.rate)}</b></button> })}</div></section>
      <section><div className="bsr-form-title"><b>04</b><span><strong>Alasan dan preview minus</strong><small>Bikin bagus nanti hanya boleh memulihkan minus ini.</small></span></div><label className="bsr-reason"><span>CATATAN PEMERIKSAAN</span><textarea value={reason} onChange={(event) => setReason(event.target.value)} placeholder="Contoh: Obras bawah lepas, perlu centang dan lipat ulang..."/></label><div className="bsr-minus-preview"><CircleMinus/><span><small>{qty} pcs × {money(rate)} · {selectedComponents.length} komponen</small><strong>− {money(qty * rate)}</strong></span></div></section>
    </div>
    <footer><p><ShieldCheck/> Setelah disimpan, koreksi dilakukan dengan reversal berjejak—bukan menghapus kasus.</p><div><button type="button" className="soft-btn" onClick={onClose}>Batal</button><button type="button" className="primary-btn" disabled={qty <= 0 || rate <= 0 || reason.trim() === ''} onClick={create}><Plus/> Simpan kasus & minus</button></div></footer>
  </section></div>
}
