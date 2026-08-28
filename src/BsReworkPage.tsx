import { useMemo, useState } from 'react'
import {
  ArrowLeft, ArrowRight, Check, CheckCircle2, ChevronRight, CircleMinus, CirclePlus,
  ClipboardCheck, Clock3, FilePlus2, Filter, History,
  Inbox, PackageCheck, ReceiptText, Search, ShieldCheck,
  UserRound, UsersRound, Waves, Wrench, X,
} from 'lucide-react'
import type { QcFinalResult } from './QcFinalPage'
import './bs-rework.css'

type SizeValues = [number, number, number]
type SizeInputs = [string, string, string]
type BsSource = 'QC_AUTO' | 'LEGACY_IMPORT'
type BsStatus = 'OPEN' | 'ASSIGNED' | 'IN_REWORK' | 'QC_REWORK' | 'GOOD_RESTORED' | 'BS_FINAL'
type StuckStatus = 'OUTSIDE' | 'PARTIAL' | 'BACK_TO_QC'
type LedgerKind = 'BS_DEDUCTION' | 'REWORK_RELEASE' | 'STUCK_HOLD' | 'STUCK_RELEASE'

type WorkComponent = { id: string; name: string; note: string; rate: number }

type BsCase = {
  kind: 'BS'; id: string; source: BsSource; sourceNote: string; parentId: string; batchId: string
  originalMandor: string; reworkMandor: string | null; brand: string; sku: string; material: string
  sizes: [string, string, string]; qtyBySize: SizeValues; origin: 'QC' | 'LEGACY'; reason: string
  status: BsStatus; componentIds: string[]; createdAt: string
}

type StuckCase = {
  kind: 'STUCK'; id: string; parentId: string; batchId: string; mandor: string; laundry: string
  brand: string; sku: string; material: string; sizes: [string, string, string]; qtyBySize: SizeValues
  deliveryRef: string; receiptRef: string; status: StuckStatus; createdAt: string
}

type OperationalCase = BsCase | StuckCase

type LedgerItem = {
  id: string; kind: LedgerKind; label: string; sign: -1 | 1; qtyBySize: SizeValues; rate: number
  amount: number; payee: string; originId?: string; caseId: string; sourceLabel: string; createdAt: string
  componentIds?: string[]
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

const reworkMandors = ['Mandor Asep', 'Mandor Ujang', 'Mandor Dedi', 'Mandor Rian']

const bsStatusSteps: Array<{ id: Exclude<BsStatus, 'BS_FINAL'>; label: string }> = [
  { id: 'OPEN', label: 'Tercatat' }, { id: 'ASSIGNED', label: 'Ditugaskan' },
  { id: 'IN_REWORK', label: 'Dikerjakan' }, { id: 'QC_REWORK', label: 'QC ulang' },
  { id: 'GOOD_RESTORED', label: 'Pulih' },
]

const bsStatusLabels: Record<BsStatus, string> = {
  OPEN: 'Butuh penugasan', ASSIGNED: 'Sudah ditugaskan', IN_REWORK: 'Sedang bikin bagus',
  QC_REWORK: 'Menunggu hasil QC ulang', GOOD_RESTORED: 'Bikin bagus selesai', BS_FINAL: 'BS final',
}
const stuckStatusLabels: Record<StuckStatus, string> = {
  OUTSIDE: 'Masih di Laundry', PARTIAL: 'Balik sebagian', BACK_TO_QC: 'Sudah kembali ke QC',
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
const caseStatusLabel = (item: OperationalCase) => item.kind === 'BS' ? bsStatusLabels[item.status] : stuckStatusLabels[item.status]
const caseIsDone = (item: OperationalCase) => item.kind === 'BS' ? ['GOOD_RESTORED', 'BS_FINAL'].includes(item.status) : item.status === 'BACK_TO_QC'
const caseSourceValue = (item: OperationalCase) => item.kind === 'STUCK' ? 'LAUNDRY' : item.source
const caseMandors = (item: OperationalCase) => item.kind === 'BS' ? [item.originalMandor, item.reworkMandor ?? ''] : [item.mandor]

function seedCases(result?: QcFinalResult | null): OperationalCase[] {
  const sizes: [string, string, string] = result?.sizes ?? ['31', '32', '33']
  const incomingBs: SizeValues = result ? asSizeValues(result.qcBs) : [2, 1, 0]
  const bsQty: SizeValues = sum(incomingBs) > 0 ? incomingBs : [2, 1, 0]
  const stuckQty: SizeValues = result ? asSizeValues(result.stuckBySize) : [21, 21, 22]
  return [
    {
      kind: 'BS', id: 'BS-260827-018', source: 'QC_AUTO', sourceNote: 'QC-260827-012',
      parentId: result?.parentId ?? 'POT-260826-041', batchId: result?.batchId ?? '041-02',
      originalMandor: result?.mandor ?? 'Mandor Asep', reworkMandor: 'Mandor Ujang',
      brand: result?.brand ?? 'Widie', sku: result?.finalSku ?? '73001', material: result?.material ?? 'Malibu', sizes,
      qtyBySize: bsQty, origin: 'QC', reason: 'Jahitan bawah perlu dirapikan dan centang ulang.', status: 'QC_REWORK',
      componentIds: ['obras', 'centang', 'lipat'], createdAt: '27 Agu 2026 · 18:42',
    },
    {
      kind: 'STUCK', id: 'HOLD-LDR-1049', parentId: result?.parentId ?? 'POT-260826-041', batchId: result?.batchId ?? '041-02',
      mandor: result?.mandor ?? 'Mandor Asep', laundry: result?.laundry ?? 'Laundry Intan',
      brand: result?.brand ?? 'Widie', sku: result?.finalSku ?? '73001', material: result?.material ?? 'Malibu', sizes,
      qtyBySize: stuckQty, deliveryRef: 'KRM-LDR-260827-006', receiptRef: 'TRM-LDR-260827-011',
      status: sum(stuckQty) > 0 ? 'PARTIAL' : 'BACK_TO_QC', createdAt: '27 Agu 2026 · 17:30',
    },
    {
      kind: 'BS', id: 'BS-LEG-0007', source: 'LEGACY_IMPORT', sourceNote: 'NOTA-LAMA-08/26-07',
      parentId: 'POT-260825-038', batchId: '038-01', originalMandor: 'Mandor Ujang', reworkMandor: null,
      brand: 'Vivo', sku: '73002', material: 'Lucy', sizes: ['31', '32', '33'], qtyBySize: [0, 2, 1],
      origin: 'LEGACY', reason: 'Sisa BS catatan lama; kancing dan ritsleting belum beres.', status: 'OPEN',
      componentIds: ['saku', 'kancing'], createdAt: '26 Agu 2026 · arsip',
    },
  ]
}

function seedLedger(cases: OperationalCase[]): LedgerItem[] {
  const qcCase = cases.find((item): item is BsCase => item.kind === 'BS' && item.source === 'QC_AUTO')!
  const legacyCase = cases.find((item): item is BsCase => item.kind === 'BS' && item.source === 'LEGACY_IMPORT')!
  const stuckCase = cases.find((item): item is StuckCase => item.kind === 'STUCK')!
  const qcRate = componentRate(qcCase.componentIds)
  const legacyRate = componentRate(legacyCase.componentIds)
  const firstRestored = firstPositiveUnit(qcCase.qtyBySize)
  const firstSusulan = firstPositiveUnit(stuckCase.qtyBySize)
  const items: LedgerItem[] = [
    { id: 'ADJ-BS-018', kind: 'BS_DEDUCTION', label: 'BS dari QC · komponen belum diterima', sign: -1, qtyBySize: qcCase.qtyBySize, rate: qcRate, amount: sum(qcCase.qtyBySize) * qcRate, payee: qcCase.originalMandor, caseId: qcCase.id, sourceLabel: `${qcCase.id} · ${qcCase.sourceNote}`, createdAt: '27 Agu · 18:42' },
    { id: 'ADJ-RW-018-01', kind: 'REWORK_RELEASE', label: 'Bikin bagus · siap Nota FG', sign: 1, qtyBySize: firstRestored, rate: qcRate, amount: sum(firstRestored) * qcRate, payee: qcCase.reworkMandor ?? qcCase.originalMandor, caseId: qcCase.id, originId: 'ADJ-BS-018', sourceLabel: 'Asal ADJ-BS-018 · QC rework lulus', createdAt: '28 Agu · 09:40', componentIds: qcCase.componentIds },
    { id: 'ADJ-BS-LEG-0007', kind: 'BS_DEDUCTION', label: 'BS legacy · komponen belum diterima', sign: -1, qtyBySize: legacyCase.qtyBySize, rate: legacyRate, amount: sum(legacyCase.qtyBySize) * legacyRate, payee: legacyCase.originalMandor, caseId: legacyCase.id, sourceLabel: `${legacyCase.id} · ${legacyCase.sourceNote}`, createdAt: '26 Agu · arsip' },
  ]
  if (sum(stuckCase.qtyBySize) > 0) items.push(
    { id: stuckCase.id, kind: 'STUCK_HOLD', label: 'Belum balik dari Laundry', sign: -1, qtyBySize: stuckCase.qtyBySize, rate: 3700, amount: sum(stuckCase.qtyBySize) * 3700, payee: stuckCase.mandor, caseId: stuckCase.id, sourceLabel: `${stuckCase.laundry} · ${stuckCase.deliveryRef}`, createdAt: '27 Agu · 17:30' },
    { id: 'SUS-LDR-1049-01', kind: 'STUCK_RELEASE', label: 'Susulan · fisik sudah balik', sign: 1, qtyBySize: firstSusulan, rate: 3700, amount: sum(firstSusulan) * 3700, payee: stuckCase.mandor, caseId: stuckCase.id, originId: stuckCase.id, sourceLabel: `Asal ${stuckCase.id} · diterima ${stuckCase.mandor}`, createdAt: '28 Agu · 10:05' },
  )
  return items
}

export default function BsReworkPage({ initialResult, onBack }: { initialResult?: QcFinalResult | null; onBack: () => void }) {
  const [cases, setCases] = useState<OperationalCase[]>(() => seedCases(initialResult))
  const [ledger, setLedger] = useState<LedgerItem[]>(() => seedLedger(seedCases(initialResult)))
  const [selectedId, setSelectedId] = useState('BS-260827-018')
  const [query, setQuery] = useState('')
  const [kindFilter, setKindFilter] = useState('ALL')
  const [mandorFilter, setMandorFilter] = useState('Semua mandor')
  const [statusFilter, setStatusFilter] = useState('ALL')
  const [sourceFilter, setSourceFilter] = useState('ALL')
  const [showLegacyForm, setShowLegacyForm] = useState(false)
  const [reworkInputs, setReworkInputs] = useState<SizeInputs>(['', '', ''])
  const [reworkComponentIds, setReworkComponentIds] = useState<string[]>(['obras', 'centang', 'lipat'])
  const [susulanInputs, setSusulanInputs] = useState<SizeInputs>(['', '', ''])
  const [notice, setNotice] = useState<string | null>(null)

  const mandors = Array.from(new Set(cases.flatMap(caseMandors).filter(Boolean)))
  const visibleCases = useMemo(() => cases.filter((item) => {
    const people = caseMandors(item).join(' ')
    const sourceText = item.kind === 'BS' ? `${item.sourceNote} ${item.source}` : `${item.laundry} ${item.deliveryRef} ${item.receiptRef}`
    const haystack = `${item.id} ${item.parentId} ${item.batchId} ${people} ${item.brand} ${item.sku} ${item.material} ${sourceText}`.toLowerCase()
    return haystack.includes(query.toLowerCase())
      && (kindFilter === 'ALL' || item.kind === kindFilter)
      && (mandorFilter === 'Semua mandor' || caseMandors(item).includes(mandorFilter))
      && (statusFilter === 'ALL' || (statusFilter === 'ACTIVE' ? !caseIsDone(item) : caseIsDone(item)))
      && (sourceFilter === 'ALL' || caseSourceValue(item) === sourceFilter)
  }), [cases, query, kindFilter, mandorFilter, statusFilter, sourceFilter])
  const selected = visibleCases.find((item) => item.id === selectedId) ?? visibleCases[0]
  const selectedBs = selected?.kind === 'BS' ? selected : null
  const selectedStuck = selected?.kind === 'STUCK' ? selected : null
  const caseDeduction = selectedBs ? ledger.find((item) => item.kind === 'BS_DEDUCTION' && item.caseId === selectedBs.id) : undefined
  const releasedForCase: SizeValues = selectedBs && caseDeduction
    ? ledger.filter((item) => item.kind === 'REWORK_RELEASE' && item.originId === caseDeduction.id).reduce<SizeValues>((total, item) => addSizes(total, item.qtyBySize), [0, 0, 0])
    : [0, 0, 0]
  const reworkRemaining: SizeValues = selectedBs ? subtractSizes(selectedBs.qtyBySize, releasedForCase) : [0, 0, 0]
  const selectedHold = selectedStuck ? ledger.find((item) => item.kind === 'STUCK_HOLD' && item.caseId === selectedStuck.id) : undefined
  const holdReleased: SizeValues = selectedHold
    ? ledger.filter((item) => item.kind === 'STUCK_RELEASE' && item.originId === selectedHold.id).reduce<SizeValues>((total, item) => addSizes(total, item.qtyBySize), [0, 0, 0])
    : [0, 0, 0]
  const holdRemaining: SizeValues = selectedHold ? subtractSizes(selectedHold.qtyBySize, holdReleased) : [0, 0, 0]

  const reworkReadyItems = ledger.filter((item) => item.kind === 'REWORK_RELEASE')

  const setSelectedCase = (id: string) => {
    const target=cases.find((item):item is BsCase=>item.kind==='BS'&&item.id===id)
    setSelectedId(id); setReworkInputs(['', '', '']); setSusulanInputs(['', '', '']); setReworkComponentIds(target?.componentIds??[])
  }
  const updateReworkMandor = (mandor: string) => {
    if (!selectedBs) return
    setCases((current) => current.map((item) => item.kind === 'BS' && item.id === selectedBs.id ? { ...item, reworkMandor: mandor || null } : item))
  }
  const nextBsStatus = () => {
    if (!selectedBs) return
    if (selectedBs.status === 'OPEN' && !selectedBs.reworkMandor) { setNotice('Pilih Mandor rework dulu. Mandor asal tidak otomatis menjadi pelaksana.'); return }
    const next: Partial<Record<BsStatus, BsStatus>> = { OPEN: 'ASSIGNED', ASSIGNED: 'IN_REWORK', IN_REWORK: 'QC_REWORK' }
    const status = next[selectedBs.status]
    if (!status) return
    setCases((current) => current.map((item) => item.kind === 'BS' && item.id === selectedBs.id ? { ...item, status } : item))
    setNotice(`${selectedBs.id} sekarang: ${bsStatusLabels[status]}.`)
  }
  const postReworkRelease = () => {
    if (!selectedBs || !caseDeduction || !selectedBs.reworkMandor) { setNotice('Mandor rework wajib dipilih sebelum hasil QC ulang diposting.'); return }
    const requested = asSizeValues(reworkInputs.map((value, index) => Math.min(Number(value) || 0, reworkRemaining[index])))
    const qty = sum(requested)
    const selectedRate=componentRate(reworkComponentIds)
    if (qty <= 0 || selectedRate <= 0) return
    const item: LedgerItem = {
      id: `ADJ-RW-${selectedBs.id.replace(/\D/g, '')}-${ledger.length + 1}`, kind: 'REWORK_RELEASE',
      label: 'Bikin bagus · siap Nota FG', sign: 1, qtyBySize: requested, rate: selectedRate,
      amount: qty * selectedRate, payee: selectedBs.reworkMandor, originId: caseDeduction.id, caseId: selectedBs.id,
      sourceLabel: `Asal ${caseDeduction.id} · QC rework lulus`, createdAt: '28 Agu · baru saja', componentIds: reworkComponentIds,
    }
    const remainingAfter = subtractSizes(reworkRemaining, requested)
    setLedger((current) => [...current, item])
    setCases((current) => current.map((entry) => entry.kind === 'BS' && entry.id === selectedBs.id ? { ...entry, status: sum(remainingAfter) === 0 ? 'GOOD_RESTORED' : 'QC_REWORK' } : entry))
    setReworkInputs(['', '', ''])
    setNotice(`${qty} pcs Bikin Bagus menjadi card siap Nota FG untuk ${item.payee}. ${reworkComponentIds.length} komponen bayar sudah disnapshot.`)
  }
  const postSusulan = () => {
    if (!selectedStuck || !selectedHold) return
    const requested = asSizeValues(susulanInputs.map((value, index) => Math.min(Number(value) || 0, holdRemaining[index])))
    const qty = sum(requested)
    if (qty <= 0) return
    const item: LedgerItem = {
      id: `SUS-${selectedHold.id.replace('HOLD-', '')}-${ledger.length + 1}`, kind: 'STUCK_RELEASE',
      label: 'Susulan · fisik sudah balik', sign: 1, qtyBySize: requested, rate: selectedHold.rate,
      amount: qty * selectedHold.rate, payee: selectedStuck.mandor, originId: selectedHold.id, caseId: selectedStuck.id,
      sourceLabel: `Asal ${selectedHold.id} · diterima ${selectedStuck.mandor}`, createdAt: '28 Agu · baru saja',
    }
    const remainingAfter = subtractSizes(holdRemaining, requested)
    setLedger((current) => [...current, item])
    setCases((current) => current.map((entry) => entry.kind === 'STUCK' && entry.id === selectedStuck.id
      ? { ...entry, status: sum(remainingAfter) === 0 ? 'BACK_TO_QC' : 'PARTIAL' } : entry))
    setSusulanInputs(['', '', ''])
    setNotice(`${qty} pcs susulan melepas hold +${money(item.amount)}. Fisik berikutnya tetap masuk QC.`)
  }
  const markBsFinal = () => {
    if (!selectedBs) return
    setCases((current) => current.map((item) => item.kind === 'BS' && item.id === selectedBs.id ? { ...item, status: 'BS_FINAL' } : item))
    setNotice(`${selectedBs.id} ditetapkan BS final. Minus asal tetap tercatat.`)
  }

  const openCases = cases.filter((item) => !caseIsDone(item)).length
  const totalBsOutstanding = ledger.filter((item) => item.kind === 'BS_DEDUCTION').reduce((total, deduction) => {
    const released = ledger.filter((item) => item.kind === 'REWORK_RELEASE' && item.originId === deduction.id).reduce((value, item) => value + item.amount, 0)
    return total + Math.max(0, deduction.amount - released)
  }, 0)
  const totalStuck = cases.filter((item): item is StuckCase => item.kind === 'STUCK').reduce((total, item) => {
    const hold = ledger.find((entry) => entry.kind === 'STUCK_HOLD' && entry.caseId === item.id)
    if (!hold) return total
    const released = ledger.filter((entry) => entry.kind === 'STUCK_RELEASE' && entry.originId === hold.id).reduce<SizeValues>((sizes, entry) => addSizes(sizes, entry.qtyBySize), [0, 0, 0])
    return total + sum(subtractSizes(hold.qtyBySize, released))
  }, 0)

  return <>
    <section className="hero-copy compact bsr-hero">
      <div><div className="eyebrow">PRODUKSI · MUTU & PENYELESAIAN</div><h1>Kasus BS & Stuck Laundry</h1><p>Browse kasus, selesaikan Bikin Bagus, lalu hasil yang diterima otomatis menjadi card siap disusun pada Nota FG.</p></div>
      <div className="bsr-hero-actions"><button type="button" className="soft-btn" onClick={onBack}><ArrowLeft/> Kembali</button><button type="button" className="primary-btn legacy" onClick={() => setShowLegacyForm(true)}><History/> Impor BS legacy</button></div>
    </section>

    <section className="bsr-rule-banner"><ShieldCheck/><div><strong>BS normal tidak dicatat manual</strong><span><b>QC otomatis membuat kasus BS.</b> Tombol impor hanya untuk arsip BS lama. <b>Stuck Laundry tetap hold</b> sampai fisiknya kembali; baru sesudah itu masuk QC.</span></div></section>
    {notice && <div className="bsr-notice"><CheckCircle2/><span>{notice}</span><button type="button" onClick={() => setNotice(null)} aria-label="Tutup pemberitahuan"><X/></button></div>}

    <section className="bsr-kpis">
      <article className="panel"><span>KASUS AKTIF</span><strong>{openCases}</strong><small>BS dan Stuck yang butuh tindakan</small></article>
      <article className="panel danger"><span>MINUS BS TERSISA</span><strong>{money(totalBsOutstanding)}</strong><small>Belum dipulihkan lewat bikin bagus</small></article>
      <article className="panel warn"><span>MASIH DI LAUNDRY</span><strong>{totalStuck} pcs</strong><small>Belum boleh berubah menjadi BS</small></article>
      <article className="panel good"><span>BIKIN BAGUS SIAP NOTA</span><strong>{reworkReadyItems.length}</strong><small>Menunggu disusun pada Nota FG</small></article>
    </section>

    <section className="panel bsr-toolbar">
      <label className="bsr-search"><Search/><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Cari kasus, PO, batch, Mandor, Laundry, SKU..."/></label>
      <label><Filter/><select value={kindFilter} onChange={(event) => setKindFilter(event.target.value)}><option value="ALL">Semua kasus</option><option value="BS">Barang BS</option><option value="STUCK">Stuck Laundry</option></select></label>
      <label><UsersRound/><select value={mandorFilter} onChange={(event) => setMandorFilter(event.target.value)}><option>Semua mandor</option>{mandors.map((mandor) => <option key={mandor}>{mandor}</option>)}</select></label>
      <label><select value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)}><option value="ALL">Semua status</option><option value="ACTIVE">Butuh tindakan</option><option value="DONE">Selesai</option></select></label>
      <label><select value={sourceFilter} onChange={(event) => setSourceFilter(event.target.value)}><option value="ALL">Semua sumber</option><option value="QC_AUTO">QC otomatis</option><option value="LEGACY_IMPORT">BS legacy</option><option value="LAUNDRY">Laundry</option></select></label>
    </section>

    <section className="bsr-master-detail">
      <aside className="panel bsr-case-browser">
        <header><div><span>BROWSE SEMUA KASUS</span><strong>{visibleCases.length} ditemukan</strong></div><ClipboardCheck/></header>
        <div className="bsr-case-list">{visibleCases.map((item, index) => <button type="button" className={selected?.id === item.id ? 'active' : ''} onClick={() => setSelectedCase(item.id)} key={item.id}>
          <span className="bsr-case-index">{String(index + 1).padStart(2, '0')}</span>
          <span className="bsr-case-copy"><small><b className={`bsr-kind ${item.kind.toLowerCase()}`}>{item.kind === 'BS' ? 'BS' : 'STUCK'}</b> {item.brand} · SKU {item.sku}</small><strong>{item.id}</strong>
            {item.kind === 'BS' ? <><em><UserRound/>{item.originalMandor}</em><span>{item.source === 'QC_AUTO' ? 'QC otomatis' : 'Legacy'} · {item.parentId} · {item.batchId}</span></> : <><em><Waves/>{item.laundry}</em><span>{item.mandor} · {item.parentId} · {item.batchId}</span></>}
          </span><span className={`bsr-status ${caseIsDone(item) ? 'done' : item.kind.toLowerCase()}`}>{caseStatusLabel(item)}</span><ChevronRight/>
        </button>)}{visibleCases.length === 0 && <div className="bsr-empty"><Search/><strong>Kasus tidak ketemu</strong><small>Ubah filter atau kata pencarian.</small></div>}</div>
      </aside>

      <div className="bsr-detail-stack">
        {selectedBs && <article className="panel bsr-case-detail">
          <header className="bsr-detail-head"><span className="bsr-detail-icon"><Wrench/></span><div><small>{selectedBs.source === 'QC_AUTO' ? 'BS OTOMATIS DARI QC' : `IMPOR LEGACY · ${selectedBs.sourceNote}`}</small><h2>{selectedBs.id} · {selectedBs.brand} SKU {selectedBs.sku}</h2><p>{selectedBs.parentId} · Batch {selectedBs.batchId} · {selectedBs.material}</p></div><strong className="bsr-case-total">{sum(selectedBs.qtyBySize)} BS</strong></header>
          <section className="bsr-responsibility-grid">
            <article className="origin"><UserRound/><div><span>MANDOR ASAL · PEMILIK MINUS</span><strong>{selectedBs.originalMandor}</strong><small>Minus BS tetap tercatat ke Mandor ini.</small></div></article>
            <article className="reworker"><Wrench/><div><span>MANDOR REWORK · PENERIMA PLUS</span><select value={selectedBs.reworkMandor ?? ''} disabled={['GOOD_RESTORED', 'BS_FINAL'].includes(selectedBs.status)} onChange={(event) => updateReworkMandor(event.target.value)}><option value="">Belum ditugaskan</option>{reworkMandors.map((mandor) => <option key={mandor}>{mandor}</option>)}</select><small>Boleh berbeda dari Mandor asal.</small></div></article>
          </section>
          <div className={`bsr-timeline ${selectedBs.status === 'BS_FINAL' ? 'is-final' : ''}`}>{bsStatusSteps.map((step, index) => {
            const activeIndex = bsStatusSteps.findIndex((item) => item.id === selectedBs.status)
            const done = selectedBs.status === 'BS_FINAL' ? false : index <= activeIndex
            return <div className={done ? 'done' : ''} key={step.id}><span>{done ? <Check/> : index + 1}</span><strong>{step.label}</strong>{index < bsStatusSteps.length - 1 && <i/>}</div>
          })}{selectedBs.status === 'BS_FINAL' && <em><CircleMinus/> BS final</em>}</div>
          <section className="bsr-case-facts"><div><span>SUMBER KASUS</span><strong>{selectedBs.source === 'QC_AUTO' ? 'Dibuat otomatis saat QC diposting' : 'Impor arsip BS legacy'}</strong></div><div><span>REFERENSI</span><strong>{selectedBs.sourceNote}</strong></div><div><span>DICATAT</span><strong>{selectedBs.createdAt}</strong></div><div className="wide"><span>ALASAN</span><strong>{selectedBs.reason}</strong></div></section>
          <section className="bsr-size-table"><header><span>SIZE</span><span>BS AWAL</span><span>SUDAH DIPULIHKAN</span><span>SISA MINUS</span></header>{selectedBs.sizes.map((size, index) => <div key={size}><strong>{size}</strong><span>{selectedBs.qtyBySize[index]} pcs</span><span className="plus">{releasedForCase[index]} pcs</span><strong className={reworkRemaining[index] > 0 ? 'minus' : 'done'}>{reworkRemaining[index]} pcs</strong></div>)}</section>
          <section className="bsr-component-snapshot"><header><div><span>SNAPSHOT KOMPONEN TERDAMPAK</span><strong>{caseDeduction?.id ?? 'Belum ada minus asal'}</strong></div><em><ShieldCheck/> terkunci</em></header><div>{selectedBs.componentIds.map((id) => { const component = components.find((item) => item.id === id); return component ? <article key={id}><span><Wrench/></span><div><strong>{component.name}</strong><small>{component.note}</small></div><b>{money(component.rate)}</b></article> : null })}</div><footer><span>Minus per pcs</span><strong>− {money(caseDeduction?.rate ?? componentRate(selectedBs.componentIds))}</strong></footer></section>
          {selectedBs.status === 'QC_REWORK' && sum(reworkRemaining) > 0 && <section className="bsr-release-card rework" data-keyboard-scope><header><CirclePlus/><div><span>BIKIN BAGUS · KOMPONEN BAYAR</span><h3>Tentukan pekerjaan yang benar-benar diselesaikan</h3><p>Checkbox hanya berlaku untuk Bikin Bagus. Hasilnya menjadi snapshot tarif card untuk <b>{selectedBs.reworkMandor ?? 'Mandor rework belum dipilih'}</b>.</p></div></header><section className="bsr-rework-component-picker"><div><span>KOMPONEN DIKERJAKAN & DIBAYAR</span><strong>{reworkComponentIds.length} dipilih · {money(componentRate(reworkComponentIds))}/pcs</strong></div><div>{selectedBs.componentIds.map((id)=>{const component=components.find((item)=>item.id===id);if(!component)return null;const active=reworkComponentIds.includes(id);return <button type="button" className={active?'active':''} aria-pressed={active} onClick={()=>setReworkComponentIds((current)=>active?current.filter((item)=>item!==id):[...current,id])} key={id}><span>{active&&<Check/>}</span><div><strong>{component.name}</strong><small>{component.note}</small></div><b>{money(component.rate)}</b></button>})}</div></section><div className="bsr-release-grid" data-keyboard-grid>{selectedBs.sizes.map((size, index) => <label key={size}><span>SIZE {size} · maks {reworkRemaining[index]}</span><input inputMode="numeric" data-grid-row={0} data-grid-col={index} value={reworkInputs[index]} onFocus={(event) => event.currentTarget.select()} onChange={(event) => setReworkInputs((current) => asSizeInputs(current.map((value, row) => row === index ? cleanQuantity(event.target.value, reworkRemaining[index]) : value)))}/></label>)}</div><div className="bsr-release-actions"><button type="button" className="soft-btn danger" onClick={markBsFinal}><CircleMinus/> Tetapkan sisa BS final</button><button type="button" className="primary-btn" disabled={!selectedBs.reworkMandor || reworkComponentIds.length===0 || sum(asSizeValues(reworkInputs.map(Number))) <= 0} onClick={postReworkRelease}>Lulus QC & buat card Nota FG <ArrowRight/></button></div></section>}
          {['OPEN', 'ASSIGNED', 'IN_REWORK'].includes(selectedBs.status) && <div className="bsr-next-action"><div><Clock3/><span><strong>{bsStatusLabels[selectedBs.status]}</strong><small>Riwayat tidak dihapus saat tahap berganti.</small></span></div><button type="button" className="primary-btn" onClick={nextBsStatus}>{selectedBs.status === 'OPEN' ? 'Tugaskan rework' : selectedBs.status === 'ASSIGNED' ? 'Mulai bikin bagus' : 'Kirim ke QC ulang'} <ArrowRight/></button></div>}
          {selectedBs.status === 'GOOD_RESTORED' && <div className="bsr-closed good"><CheckCircle2/><div><strong>Seluruh minus kasus sudah dipulihkan</strong><span>Mandor asal dan Mandor pelaksana tetap terlihat terpisah.</span></div></div>}
          {selectedBs.status === 'BS_FINAL' && <div className="bsr-closed final"><CircleMinus/><div><strong>Ditetapkan BS final</strong><span>Minus tidak hilang. Koreksi berikutnya wajib melalui reversal berjejak.</span></div></div>}
        </article>}

        {selectedStuck && <article className="panel bsr-stuck-card selected-case"><header><Waves/><div><span>STUCK LAUNDRY · BUKAN BS</span><h2>{selectedStuck.id} · {selectedStuck.laundry}</h2><p>{selectedStuck.parentId} · Batch {selectedStuck.batchId} · {selectedStuck.brand} SKU {selectedStuck.sku}</p></div><strong>{sum(holdRemaining)} pcs di luar</strong></header>
          <section className="bsr-responsibility-grid stuck"><article className="origin"><UserRound/><div><span>MANDOR PENERIMA FISIK</span><strong>{selectedStuck.mandor}</strong><small>Mandor mengonfirmasi susulan benar-benar kembali.</small></div></article><article className="laundry"><Waves/><div><span>LAUNDRY & REFERENSI</span><strong>{selectedStuck.laundry}</strong><small>{selectedStuck.deliveryRef} · {selectedStuck.receiptRef}</small></div></article></section>
          <div className="bsr-stuck-body"><section className="bsr-stuck-sizes">{selectedStuck.sizes.map((size, index) => <div key={size}><span>Size {size}</span><strong>{holdRemaining[index]} pcs</strong><small>dari {selectedStuck.qtyBySize[index]} hold</small></div>)}</section><section className="bsr-susulan-entry" data-keyboard-scope><div><span>SUSULAN · PLUS HOLD</span><strong>Pilih qty yang benar-benar diterima</strong></div><div className="bsr-release-grid" data-keyboard-grid>{selectedStuck.sizes.map((size, index) => <label key={size}><span>SIZE {size} · maks {holdRemaining[index]}</span><input inputMode="numeric" data-grid-row={0} data-grid-col={index} value={susulanInputs[index]} disabled={holdRemaining[index] === 0} onFocus={(event) => event.currentTarget.select()} onChange={(event) => setSusulanInputs((current) => asSizeInputs(current.map((value, row) => row === index ? cleanQuantity(event.target.value, holdRemaining[index]) : value)))}/></label>)}</div><button type="button" className="primary-btn" disabled={sum(asSizeValues(susulanInputs.map(Number))) <= 0} onClick={postSusulan}>Catat fisik balik & buat Susulan + <ArrowRight/></button></section></div>
          <div className="bsr-stuck-rule"><ShieldCheck/><span><strong>Kalau susulan ternyata BS:</strong> lepaskan hold saat fisik balik, lalu QC mencatat hasilnya. Kasus BS baru lahir otomatis dari QC—bukan diubah dari Stuck.</span></div>
          {selectedStuck.status === 'BACK_TO_QC' && <div className="bsr-closed good"><CheckCircle2/><div><strong>Semua fisik sudah kembali</strong><span>Kasus tetap tersimpan dan barang menunggu hasil QC.</span></div></div>}
        </article>}
        {!selected && <article className="panel bsr-no-selection"><Inbox/><strong>Tidak ada kasus pada filter ini</strong><span>Ubah filter untuk membuka detail tindakan.</span></article>}
      </div>
    </section>

    <article className="panel bsr-ready-nota">
      <header><div><span>HASIL BIKIN BAGUS · OTOMATIS MASUK ANTREAN</span><h2>Card siap disusun pada Nota FG</h2><p>Browser Kasus tidak lagi menempelkan minus/plus langsung ke Payroll. Hanya hasil Bikin Bagus yang lolos QC ulang menjadi card pekerjaan.</p></div><ReceiptText/></header>
      <div className="bsr-ready-grid">{reworkReadyItems.map((item) => <article key={item.id}><span className="bsr-ready-icon"><PackageCheck/></span><div><small>{item.id} · {item.sourceLabel}</small><strong>{item.label}</strong><em><UserRound/>{item.payee}</em><p>{(item.componentIds??[]).map((id)=>components.find((component)=>component.id===id)?.name).filter(Boolean).join(' · ')}</p></div><span className="bsr-ready-amount"><small>{sum(item.qtyBySize)} pcs × {money(item.rate)}</small><strong>{money(item.amount)}</strong><em>SIAP NOTA FG</em></span></article>)}</div>
      <footer><ShieldCheck/><span><strong>Penyusunan tetap dilakukan di Nota FG</strong><small>Card FG Reguler dan Bikin Bagus dipisahkan jelas. Setelah Nota FG posted, barulah dokumen muncul pada Payroll.</small></span></footer>
    </article>
    {showLegacyForm && <LegacyBsDialog result={initialResult} onClose={() => setShowLegacyForm(false)} onCreate={(createdCase, deduction) => {
      setCases((current) => [createdCase, ...current]); setLedger((current) => [deduction, ...current]); setSelectedId(createdCase.id)
      setKindFilter('ALL'); setSourceFilter('ALL'); setShowLegacyForm(false)
      setNotice(`${createdCase.id} diimpor sebagai BS legacy. BS operasional baru tetap hanya berasal dari QC.`)
    }}/>} 
  </>
}

function LegacyBsDialog({ result, onClose, onCreate }: { result?: QcFinalResult | null; onClose: () => void; onCreate: (item: BsCase, deduction: LedgerItem) => void }) {
  const sizes: [string, string, string] = result?.sizes ?? ['31', '32', '33']
  const [legacyRef, setLegacyRef] = useState('NOTA-LAMA-08/26-')
  const [physicalDate, setPhysicalDate] = useState('2026-08-26')
  const [parentId, setParentId] = useState(result?.parentId ?? 'POT-260826-041')
  const [batchId, setBatchId] = useState(result?.batchId ?? '041-02')
  const [originalMandor, setOriginalMandor] = useState(result?.mandor ?? 'Mandor Asep')
  const [brand, setBrand] = useState(result?.brand ?? 'Widie')
  const [sku, setSku] = useState(result?.finalSku ?? '73001')
  const [qtyInputs, setQtyInputs] = useState<SizeInputs>(['', '', ''])
  const [selectedComponents, setSelectedComponents] = useState<string[]>(['obras', 'centang', 'lipat'])
  const [reason, setReason] = useState('')
  const quantities = asSizeValues(qtyInputs.map((value) => Number(value) || 0))
  const qty = sum(quantities)
  const rate = componentRate(selectedComponents)
  const validIdentity = [legacyRef, physicalDate, parentId, batchId, originalMandor, brand, sku].every((value) => value.trim() !== '')
  const create = () => {
    if (!validIdentity || qty <= 0 || rate <= 0 || reason.trim() === '') return
    const serial = String(Date.now()).slice(-4)
    const id = `BS-LEG-${serial}`
    const item: BsCase = {
      kind: 'BS', id, source: 'LEGACY_IMPORT', sourceNote: legacyRef.trim(), parentId: parentId.trim(), batchId: batchId.trim(),
      originalMandor: originalMandor.trim(), reworkMandor: null, brand: brand.trim(), sku: sku.trim(),
      material: result?.material ?? 'Bahan legacy', sizes, qtyBySize: quantities, origin: 'LEGACY', reason: reason.trim(),
      status: 'OPEN', componentIds: selectedComponents, createdAt: `${physicalDate} · impor legacy`,
    }
    const deduction: LedgerItem = {
      id: `ADJ-${id}`, kind: 'BS_DEDUCTION', label: 'BS legacy · komponen belum diterima', sign: -1, qtyBySize: quantities,
      rate, amount: qty * rate, payee: item.originalMandor, caseId: id, sourceLabel: `${id} · ${item.sourceNote}`, createdAt: `${physicalDate} · impor`,
    }
    onCreate(item, deduction)
  }

  return <div className="bsr-dialog-layer" role="presentation"><section className="bsr-dialog" role="dialog" aria-modal="true" aria-labelledby="legacy-bs-title" data-keyboard-scope>
    <header><div><span>IMPOR BS LEGACY · PENGECUALIAN</span><h2 id="legacy-bs-title">Masukkan kasus lama yang belum lahir dari QC sistem</h2><p>BS hari ini otomatis dari QC. Form ini hanya memindahkan arsip lama dan wajib membawa identitas asal.</p></div><button type="button" onClick={onClose} aria-label="Tutup"><X/></button></header>
    <div className="bsr-dialog-body">
      <section><div className="bsr-legacy-warning"><ShieldCheck/><div><strong>Bukan tombol BS operasional</strong><span>Gunakan hanya untuk saldo/kasus sebelum ERP. Setelah go-live, hasil BS baru datang dari posting QC.</span></div></div></section>
      <section><div className="bsr-form-title"><b>01</b><span><strong>Jejak arsip lama</strong><small>Referensi dan tanggal tidak boleh kosong.</small></span></div><div className="bsr-identity-grid legacy"><label><span>NO. NOTA / CATATAN LAMA</span><input value={legacyRef} onChange={(event) => setLegacyRef(event.target.value)}/></label><label><span>TANGGAL FISIK</span><input type="date" value={physicalDate} onChange={(event) => setPhysicalDate(event.target.value)}/></label><label><span>MANDOR ASAL · PEMILIK MINUS</span><select value={originalMandor} onChange={(event) => setOriginalMandor(event.target.value)}>{reworkMandors.map((mandor) => <option key={mandor}>{mandor}</option>)}</select></label></div></section>
      <section><div className="bsr-form-title"><b>02</b><span><strong>Identitas barang & jumlah per size</strong><small>PO, batch, dan SKU dipakai untuk mengembalikan lineage legacy.</small></span></div><div className="bsr-identity-grid"><label><span>BATCH PRODUKSI</span><input value={parentId} onChange={(event) => setParentId(event.target.value)}/></label><label><span>BATCH DISTRIBUSI</span><input value={batchId} onChange={(event) => setBatchId(event.target.value)}/></label><label><span>MEREK</span><input value={brand} onChange={(event) => setBrand(event.target.value)}/></label><label><span>SKU</span><input value={sku} onChange={(event) => setSku(event.target.value)}/></label></div><div className="bsr-new-size-grid" data-keyboard-grid>{sizes.map((size, index) => <label key={size}><span>SIZE {size}</span><input inputMode="numeric" data-grid-row={0} data-grid-col={index} value={qtyInputs[index]} placeholder="0" onFocus={(event) => event.currentTarget.select()} onChange={(event) => setQtyInputs((current) => asSizeInputs(current.map((value, row) => row === index ? cleanQuantity(event.target.value) : value)))}/></label>)}</div></section>
      <section><div className="bsr-form-title"><b>03</b><span><strong>Komponen yang dahulu belum diterima</strong><small>Snapshot menentukan nilai minus dan batas bikin bagus.</small></span></div><div className="bsr-component-picker">{components.map((component) => { const active = selectedComponents.includes(component.id); return <button type="button" className={active ? 'active' : ''} onClick={() => setSelectedComponents((current) => active ? current.filter((id) => id !== component.id) : [...current, component.id])} key={component.id}><span>{active && <Check/>}</span><div><strong>{component.name}</strong><small>{component.note}</small></div><b>{money(component.rate)}</b></button> })}</div></section>
      <section><div className="bsr-form-title"><b>04</b><span><strong>Alasan & preview minus</strong><small>Rework nanti hanya boleh memulihkan nilai yang berasal dari kasus ini.</small></span></div><label className="bsr-reason"><span>CATATAN ARSIP / KONDISI FISIK</span><textarea value={reason} onChange={(event) => setReason(event.target.value)} placeholder="Contoh: Sisa BS dari nota Agustus, obras bawah lepas..."/></label><div className="bsr-minus-preview"><CircleMinus/><span><small>{qty} pcs × {money(rate)} · {selectedComponents.length} komponen · {originalMandor}</small><strong>− {money(qty * rate)}</strong></span></div></section>
    </div>
    <footer><p><ShieldCheck/> Kasus legacy diberi flag khusus; tidak menyamar sebagai hasil QC baru.</p><div><button type="button" className="soft-btn" onClick={onClose}>Batal</button><button type="button" className="primary-btn" disabled={!validIdentity || qty <= 0 || rate <= 0 || reason.trim() === ''} onClick={create}><FilePlus2/> Impor kasus legacy</button></div></footer>
  </section></div>
}
