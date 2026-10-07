import { useEffect, useMemo, useState } from 'react'
import {
  ArrowLeft, ArrowRight, Check, CheckCircle2, ChevronRight, CircleMinus, CirclePlus,
  ClipboardCheck, Clock3, FilePlus2, Filter, History,
  Inbox, PackageCheck, PackagePlus, ReceiptText, Search, ShieldCheck, Tag,
  UserRound, Waves, Wrench, X,
} from 'lucide-react'
import type { QcFinalResult } from './QcFinalPage'
import type { ReadyFgNotaCard } from './fgNota'
import { productCatalog } from './productCatalog'
import './bs-rework.css'
import { matchesSearch, searchValues } from './lib/search'
import BrowsePicker from './components/BrowsePicker'

export type SizeValues = [number, number, number]
type SizeInputs = [string, string, string]
type BsSource = 'QC_AUTO' | 'LEGACY_IMPORT' | 'HOLD_RESOLUTION'
type BsStatus = 'OPEN' | 'ASSIGNED' | 'IN_REWORK' | 'QC_REWORK' | 'GOOD_RESTORED' | 'BS_FINAL' | 'CONVERTED_SKU'
type StuckStatus = 'OUTSIDE' | 'PARTIAL' | 'RESOLVED'
type LedgerKind = 'BS_DEDUCTION' | 'REWORK_RELEASE' | 'STUCK_HOLD' | 'STUCK_RELEASE' | 'STUCK_TO_BS' | 'BS_TO_NEW_SKU'
export type ResolutionRoute = 'REWORK' | 'REWASH' | 'HOLD' | 'SCRAP'

type WorkComponent = { id: string; name: string; note: string; rate: number }

/** Simulasi lokal: sebagian/seluruh fisik BS dipindah ke SKU baru (mis. grade B). */
export type BsSkuConversion = {
  id: string; newSku: string; newName: string; gradeNote: string; qtyBySize: SizeValues; reason: string; createdAt: string
}

type BsCase = {
  kind: 'BS'; id: string; source: BsSource; sourceNote: string; parentId: string; batchId: string
  originalMandor: string; reworkMandor: string | null; brand: string; sku: string; material: string
  sizes: [string, string, string]; qtyBySize: SizeValues; origin: 'QC' | 'LEGACY' | 'HOLD'; reason: string
  status: BsStatus; componentIds: string[]; createdAt: string; deductionOriginId?: string; fixedDeductionRate?: number
  conversions?: BsSkuConversion[]
}

type StuckCase = {
  kind: 'STUCK'; id: string; parentId: string; batchId: string; mandor: string; laundry: string
  brand: string; sku: string; material: string; sizes: [string, string, string]; qtyBySize: SizeValues
  deliveryRef: string; receiptRef: string; status: StuckStatus; createdAt: string
}

type OperationalCase = BsCase | StuckCase

type LedgerItem = {
  id: string; kind: LedgerKind; label: string; sign: -1 | 0 | 1; qtyBySize: SizeValues; rate: number
  amount: number; payee: string; originId?: string; caseId: string; sourceLabel: string; createdAt: string
  componentIds?: string[]; componentSnapshots?: WorkComponent[]
}

export type BsReworkWorkspace = { cases: OperationalCase[]; ledger: LedgerItem[] }

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
  CONVERTED_SKU: 'Sudah jadi SKU baru',
}
const stuckStatusLabels: Record<StuckStatus, string> = {
  OUTSIDE: 'Masih di Laundry', PARTIAL: 'Balik sebagian', RESOLVED: 'Susulan selesai',
}

const resolutionOptions: Array<{ id: ResolutionRoute; label: string; description: string }> = [
  { id: 'REWORK', label: 'Rework', description: 'Mandor memperbaiki fisik; komponen/aksesori dipilih pada simulasi.' },
  { id: 'REWASH', label: 'Rewash', description: 'Mandor · aksesori terpilih direimburse · fee jasa vendor Laundry Rp0.' },
  { id: 'HOLD', label: 'Hold', description: 'Tahan keputusan kasus; ini bukan Stuck Laundry dan tidak menambah FG.' },
  { id: 'SCRAP', label: 'Scrap', description: 'Preview wajib membawa qty, alasan, actor, tanggal, dan efek persediaan/HPP.' },
]

const sum = (values: SizeValues) => values.reduce((total, value) => total + value, 0)
const money = (value: number) => `Rp${Math.round(value).toLocaleString('id-ID')}`
const asSizeValues = (values: number[]): SizeValues => [values[0] ?? 0, values[1] ?? 0, values[2] ?? 0]
const asSizeInputs = (values: string[]): SizeInputs => [values[0] ?? '', values[1] ?? '', values[2] ?? '']
export const cleanQuantity = (raw: string, max = 9999) => {
  const normalized = raw.trim().replace(',', '.')
  if (normalized === '') return ''
  const value = Number(normalized)
  if (!Number.isFinite(value)) return ''
  return String(Math.min(Math.max(0, Math.floor(max)), Math.max(0, Math.floor(value))))
}
const componentRate = (ids: string[]) => components.filter((component) => ids.includes(component.id)).reduce((total, component) => total + component.rate, 0)
const caseComponents = (item: BsCase): WorkComponent[] => item.origin === 'HOLD'
  ? [{ id: 'hold-value', name: 'Nilai Hold / BS Nota FG', note: 'Reklasifikasi dari Hold; tidak memotong Nota FG lagi', rate: item.fixedDeductionRate ?? 0 }]
  : components.filter((component) => item.componentIds.includes(component.id))
const caseComponentRate = (item: BsCase, ids: string[]) => caseComponents(item).filter((component) => ids.includes(component.id)).reduce((total, component) => total + component.rate, 0)
const firstPositiveUnit = (values: SizeValues): SizeValues => {
  const index = values.findIndex((value) => value > 0)
  return index < 0 ? [0, 0, 0] : asSizeValues(values.map((_, row) => row === index ? 1 : 0))
}
const subtractSizes = (source: SizeValues, used: SizeValues): SizeValues => asSizeValues(source.map((value, index) => Math.max(0, value - used[index])))
const addSizes = (left: SizeValues, right: SizeValues): SizeValues => asSizeValues(left.map((value, index) => value + right[index]))
const caseStatusLabel = (item: OperationalCase) => item.kind === 'BS' ? bsStatusLabels[item.status] : stuckStatusLabels[item.status]
const bsClosedStatuses: BsStatus[] = ['GOOD_RESTORED', 'BS_FINAL', 'CONVERTED_SKU']
const caseIsDone = (item: OperationalCase) => item.kind === 'BS' ? bsClosedStatuses.includes(item.status) : item.status === 'RESOLVED'
const caseSourceValue = (item: OperationalCase) => item.kind === 'STUCK' ? 'LAUNDRY' : item.source
const caseMandors = (item: OperationalCase) => item.kind === 'BS' ? [item.originalMandor, item.reworkMandor ?? ''] : [item.mandor]

/** Identitas SKU dari katalog demo (merek + kode). Null bila kode belum ada di katalog. */
export const bsSkuProduct = (brand: string, sku: string) => productCatalog.find((product) => product.brand === brand && product.code === sku) ?? null
export const bsSkuName = (brand: string, sku: string) => {
  const product = bsSkuProduct(brand, sku)
  return product ? `${product.name} · ${product.color}` : 'Nama produk belum ada di katalog demo'
}
const sizeSummary = (sizes: [string, string, string], qty: SizeValues) => sizes.map((size, index) => qty[index] > 0 ? `${size}: ${qty[index]}` : null).filter(Boolean).join(' · ') || 'Tanpa qty'
export const convertedSizes = (item: BsCase): SizeValues => (item.conversions ?? []).reduce<SizeValues>((total, conversion) => addSizes(total, conversion.qtyBySize), [0, 0, 0])
export const normalizeSkuCode = (raw: string) => raw.trim().toUpperCase().replace(/\s+/g, '-')
export const usedSkuCodes = (cases: OperationalCase[]) => new Set([
  ...productCatalog.map((product) => product.code.toUpperCase()),
  ...cases.flatMap((item) => item.kind === 'BS' ? (item.conversions ?? []).map((conversion) => conversion.newSku.toUpperCase()) : []),
])

export type NewSkuDraft = { code: string; name: string; gradeNote: string; qty: SizeInputs; reason: string }
export type NewSkuErrors = Partial<Record<'code' | 'name' | 'gradeNote' | 'qty' | 'reason', string>>

export function validateNewSkuDraft(draft: NewSkuDraft, available: SizeValues, sizes: [string, string, string], usedCodes: Set<string>): NewSkuErrors {
  const errors: NewSkuErrors = {}
  const code = normalizeSkuCode(draft.code)
  if (!code) errors.code = 'Kode SKU baru wajib diisi.'
  else if (!/^[A-Z0-9][A-Z0-9-]{2,23}$/.test(code)) errors.code = 'Pakai 3–24 huruf/angka/tanda minus, contoh 73001-B.'
  else if (usedCodes.has(code)) errors.code = `Kode ${code} sudah dipakai di katalog demo. Pilih kode lain.`
  if (!draft.name.trim()) errors.name = 'Nama produk SKU baru wajib diisi.'
  if (!draft.gradeNote.trim()) errors.gradeNote = 'Catatan size / grade wajib diisi.'
  const quantities = draft.qty.map((value) => Number(value) || 0)
  const over = quantities.map((qty, index) => qty > available[index] ? `Size ${sizes[index]} maks ${available[index]} pcs` : null).filter(Boolean)
  if (over.length > 0) errors.qty = `Qty melebihi sisa BS: ${over.join(' · ')}.`
  else if (quantities.reduce((total, qty) => total + qty, 0) <= 0) errors.qty = 'Isi minimal 1 pcs yang dipindah ke SKU baru.'
  if (!draft.reason.trim()) errors.reason = 'Alasan wajib diisi supaya jejak audit jelas.'
  return errors
}

export function calculateSusulanResolution(qtySusulan: number[], qtyBsSusulan: number[], outstanding: number[]) {
  const safeOutstanding = asSizeValues(outstanding.map((value) => Math.max(0, Math.floor(Number.isFinite(value) ? value : 0))))
  const total = asSizeValues(qtySusulan.map((value, index) => Math.min(safeOutstanding[index], Math.max(0, Math.floor(Number.isFinite(value) ? value : 0)))))
  const bs = asSizeValues(qtyBsSusulan.map((value, index) => Math.min(total[index], Math.max(0, Math.floor(Number.isFinite(value) ? value : 0)))))
  const good = subtractSizes(total, bs)
  return { total, bs, good, remaining: subtractSizes(safeOutstanding, total) }
}

export function ResolutionRoutePicker({ value, onChange, disabled = false }: {
  value: ResolutionRoute
  onChange: (route: ResolutionRoute) => void
  disabled?: boolean
}) {
  return <fieldset className="bsr-resolution-picker" aria-label="Pilih jalur penyelesaian BS">
    <legend>JALUR PENYELESAIAN · SIMULASI LOKAL</legend>
    <div>{resolutionOptions.map((option) => <button
      type="button"
      key={option.id}
      className={value === option.id ? 'active' : ''}
      data-resolution-route={option.id}
      aria-pressed={value === option.id}
      disabled={disabled}
      onClick={() => onChange(option.id)}
    ><strong>{option.label}</strong><small>{option.description}</small></button>)}</div>
    <p role="note"><ShieldCheck/> SIMULASI FRONTEND · belum menulis transaksi UAT</p>
  </fieldset>
}

function seedCases(result?: QcFinalResult | null): OperationalCase[] {
  const sizes: [string, string, string] = result?.sizes ?? ['31', '32', '33']
  const incomingBs: SizeValues = result ? asSizeValues(result.postedBsBySize) : [2, 1, 0]
  const bsQty: SizeValues = result ? incomingBs : [2, 1, 0]
  const stuckQty: SizeValues = result ? asSizeValues(result.stuckBySize) : [21, 21, 22]
  const resultToken = result ? `${result.parentId.replace(/[^a-z0-9]/gi, '')}-${result.batchId.replace(/[^a-z0-9]/gi, '')}-${result.completionCount}` : null
  const qcCaseId = resultToken ? `BS-${resultToken}` : 'BS-260827-018'
  const stuckId = result
    ? `HOLD-${result.parentId.replace(/[^a-z0-9]/gi, '')}-${result.batchId.replace(/[^a-z0-9]/gi, '')}-${result.laundry.replace(/[^a-z0-9]/gi, '')}`
    : 'HOLD-LDR-1049'
  return [
    {
      kind: 'BS', id: qcCaseId, source: 'QC_AUTO', sourceNote: resultToken ? `QC-${resultToken}` : 'QC-260827-012',
      parentId: result?.parentId ?? 'POT-260826-041', batchId: result?.batchId ?? '041-02',
      originalMandor: result?.mandor ?? 'Mandor Asep', reworkMandor: result ? null : 'Mandor Ujang',
      brand: result?.brand ?? 'Widie', sku: result?.finalSku ?? '73001', material: result?.material ?? 'Malibu', sizes,
      qtyBySize: bsQty, origin: 'QC', reason: 'Jahitan bawah perlu dirapikan dan centang ulang.', status: result ? 'OPEN' : 'QC_REWORK',
      componentIds: ['obras', 'centang', 'lipat'], createdAt: '27 Agu 2026 · 18:42',
    },
    {
      kind: 'STUCK', id: stuckId, parentId: result?.parentId ?? 'POT-260826-041', batchId: result?.batchId ?? '041-02',
      mandor: result?.mandor ?? 'Mandor Asep', laundry: result?.laundry ?? 'Laundry Intan',
      brand: result?.brand ?? 'Widie', sku: result?.finalSku ?? '73001', material: result?.material ?? 'Malibu', sizes,
      qtyBySize: stuckQty, deliveryRef: 'KRM-LDR-260827-006', receiptRef: 'TRM-LDR-260827-011',
      status: sum(stuckQty) > 0 ? 'OUTSIDE' : 'RESOLVED', createdAt: '27 Agu 2026 · 17:30',
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
  const deductionId = qcCase.id === 'BS-260827-018' ? 'ADJ-BS-018' : `ADJ-${qcCase.id}`
  const releaseId = qcCase.id === 'BS-260827-018' ? 'ADJ-RW-018-01' : `ADJ-RW-${qcCase.id.replace(/^BS-/, '')}-01`
  const items: LedgerItem[] = [
    { id: deductionId, kind: 'BS_DEDUCTION', label: 'BS dari QC · komponen belum diterima', sign: -1, qtyBySize: qcCase.qtyBySize, rate: qcRate, amount: sum(qcCase.qtyBySize) * qcRate, payee: qcCase.originalMandor, caseId: qcCase.id, sourceLabel: `${qcCase.id} · ${qcCase.sourceNote}`, createdAt: '27 Agu · 18:42' },
    { id: 'ADJ-BS-LEG-0007', kind: 'BS_DEDUCTION', label: 'BS legacy · komponen belum diterima', sign: -1, qtyBySize: legacyCase.qtyBySize, rate: legacyRate, amount: sum(legacyCase.qtyBySize) * legacyRate, payee: legacyCase.originalMandor, caseId: legacyCase.id, sourceLabel: `${legacyCase.id} · ${legacyCase.sourceNote}`, createdAt: '26 Agu · arsip' },
  ]
  if (qcCase.status === 'QC_REWORK' && sum(firstRestored) > 0) items.splice(1, 0,
    { id: releaseId, kind: 'REWORK_RELEASE', label: 'Bikin bagus · siap Nota FG', sign: 1, qtyBySize: firstRestored, rate: qcRate, amount: sum(firstRestored) * qcRate, payee: qcCase.reworkMandor ?? qcCase.originalMandor, caseId: qcCase.id, originId: deductionId, sourceLabel: `Asal ${deductionId} · QC rework lulus`, createdAt: '28 Agu · 09:40', componentIds: qcCase.componentIds, componentSnapshots: caseComponents(qcCase).map((component) => ({ ...component })) },
  )
  if (sum(stuckCase.qtyBySize) > 0) items.push(
    { id: stuckCase.id, kind: 'STUCK_HOLD', label: 'Belum balik dari Laundry', sign: -1, qtyBySize: stuckCase.qtyBySize, rate: 3700, amount: sum(stuckCase.qtyBySize) * 3700, payee: stuckCase.mandor, caseId: stuckCase.id, sourceLabel: `${stuckCase.laundry} · ${stuckCase.deliveryRef}`, createdAt: '27 Agu · 17:30' },
  )
  return items
}

function createInitialWorkspace(result?: QcFinalResult | null): BsReworkWorkspace {
  const seededCases = seedCases(result)
  const cases = result
    ? seededCases.filter((item) => item.kind === 'BS' ? item.source === 'LEGACY_IMPORT' || sum(item.qtyBySize) > 0 : sum(item.qtyBySize) > 0)
    : seededCases
  const caseIds = new Set(cases.map((item) => item.id))
  return { cases, ledger: seedLedger(seededCases).filter((item) => caseIds.has(item.caseId)) }
}

export default function BsReworkPage({ initialResult, initialWorkspace, onWorkspaceChange, postedFgCardIds = [], onBack, onStuckReturned, onOpenNota, onNotaCardReady }: {
  initialResult?: QcFinalResult | null
  initialWorkspace?: BsReworkWorkspace
  onWorkspaceChange?: (workspace: BsReworkWorkspace) => void
  postedFgCardIds?: string[]
  onBack: () => void
  onStuckReturned?: (returnEvent: { parentId: string; batchId: string; laundry: string; goodBySize: SizeValues; bsBySize: SizeValues }) => void
  onOpenNota?: (card: ReadyFgNotaCard) => void
  onNotaCardReady?: (card: ReadyFgNotaCard) => void
}) {
  const [seededWorkspace] = useState(() => initialWorkspace ?? createInitialWorkspace(initialResult))
  const [cases, setCases] = useState<OperationalCase[]>(seededWorkspace.cases)
  const [ledger, setLedger] = useState<LedgerItem[]>(seededWorkspace.ledger)
  const [selectedId, setSelectedId] = useState(() => cases[0]?.id ?? 'BS-260827-018')
  const [query, setQuery] = useState('')
  const [kindFilter, setKindFilter] = useState('ALL')
  const [mandorFilter, setMandorFilter] = useState('Semua mandor')
  const [statusFilter, setStatusFilter] = useState('ALL')
  const [sourceFilter, setSourceFilter] = useState('ALL')
  const [showLegacyForm, setShowLegacyForm] = useState(false)
  const [reworkInputs, setReworkInputs] = useState<SizeInputs>(['', '', ''])
  const [reworkComponentIds, setReworkComponentIds] = useState<string[]>(['obras', 'centang', 'lipat'])
  const [susulanQtyInputs, setSusulanQtyInputs] = useState<SizeInputs>(['', '', ''])
  const [susulanBsInputs, setSusulanBsInputs] = useState<SizeInputs>(['', '', ''])
  const [resolutionByCase, setResolutionByCase] = useState<Record<string, ResolutionRoute>>({})
  const [newSkuCaseId, setNewSkuCaseId] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)

  useEffect(() => {
    onWorkspaceChange?.({ cases, ledger })
  }, [cases, ledger])

  useEffect(() => {
    if (!initialResult || !initialWorkspace) return
    const incomingCases = seedCases(initialResult).filter((item) => item.kind === 'BS'
      ? item.source !== 'LEGACY_IMPORT' && sum(item.qtyBySize) > 0
      : sum(item.qtyBySize) > 0)
    const missingCases = incomingCases.filter((item) => !cases.some((current) => current.id === item.id))
    if (missingCases.length === 0) return
    const incomingLedger = seedLedger(seedCases(initialResult)).filter((item) => missingCases.some((entry) => entry.id === item.caseId) && item.kind !== 'REWORK_RELEASE')
    setCases((current) => [...missingCases, ...current])
    setLedger((current) => [...incomingLedger.filter((item) => !current.some((entry) => entry.id === item.id)), ...current])
    setSelectedId(missingCases[0].id)
  }, [initialResult, initialWorkspace])

  const mandors = Array.from(new Set(cases.flatMap(caseMandors).filter(Boolean)))
  const visibleCases = useMemo(() => cases.filter((item) => {
    const people = caseMandors(item).join(' ')
    const sourceText = item.kind === 'BS' ? `${item.sourceNote} ${item.source} ${(item.conversions ?? []).map((conversion) => `${conversion.newSku} ${conversion.newName}`).join(' ')}` : `${item.laundry} ${item.deliveryRef} ${item.receiptRef}`
    const haystack = `${item.id} ${item.parentId} ${item.batchId} ${people} ${item.brand} ${item.sku} ${bsSkuName(item.brand, item.sku)} ${item.material} ${sourceText}`.toLowerCase()
    const statusLabel = (bsStatusLabels as Record<string, string>)[item.status] ?? (stuckStatusLabels as Record<string, string>)[item.status]
    return matchesSearch(query, haystack, searchValues(item), statusLabel)
      && (kindFilter === 'ALL' || item.kind === kindFilter)
      && (mandorFilter === 'Semua mandor' || caseMandors(item).includes(mandorFilter))
      && (statusFilter === 'ALL' || (statusFilter === 'ACTIVE' ? !caseIsDone(item) : caseIsDone(item)))
      && (sourceFilter === 'ALL' || caseSourceValue(item) === sourceFilter)
  }), [cases, query, kindFilter, mandorFilter, statusFilter, sourceFilter])
  const selected = visibleCases.find((item) => item.id === selectedId) ?? visibleCases[0]
  const selectedBs = selected?.kind === 'BS' ? selected : null
  const selectedStuck = selected?.kind === 'STUCK' ? selected : null
  const selectedResolution = selectedBs ? resolutionByCase[selectedBs.id] ?? 'REWORK' : 'REWORK'
  const selectedComponents = selectedBs ? caseComponents(selectedBs) : []
  const caseDeduction = selectedBs
    ? selectedBs.deductionOriginId
      ? ledger.find((item) => item.id === selectedBs.deductionOriginId)
      : ledger.find((item) => item.kind === 'BS_DEDUCTION' && item.caseId === selectedBs.id)
    : undefined
  const releasedForCase: SizeValues = selectedBs && caseDeduction
    ? ledger.filter((item) => item.kind === 'REWORK_RELEASE' && item.originId === caseDeduction.id).reduce<SizeValues>((total, item) => addSizes(total, item.qtyBySize), [0, 0, 0])
    : [0, 0, 0]
  const convertedForCase: SizeValues = selectedBs ? convertedSizes(selectedBs) : [0, 0, 0]
  const minusRemaining: SizeValues = selectedBs ? subtractSizes(selectedBs.qtyBySize, releasedForCase) : [0, 0, 0]
  // Fisik BS yang masih bisa dikerjakan ulang atau dijadikan SKU baru.
  const reworkRemaining: SizeValues = subtractSizes(minusRemaining, convertedForCase)
  const caseHistory = selectedBs ? ledger.filter((item) => item.caseId === selectedBs.id) : []
  const newSkuOpen = Boolean(selectedBs && newSkuCaseId === selectedBs.id)
  const selectedHold = selectedStuck ? ledger.find((item) => item.kind === 'STUCK_HOLD' && item.caseId === selectedStuck.id) : undefined
  const holdReleased: SizeValues = selectedHold
    ? ledger.filter((item) => ['STUCK_RELEASE', 'STUCK_TO_BS'].includes(item.kind) && item.originId === selectedHold.id).reduce<SizeValues>((total, item) => addSizes(total, item.qtyBySize), [0, 0, 0])
    : [0, 0, 0]
  const holdRemaining: SizeValues = selectedHold ? subtractSizes(selectedHold.qtyBySize, holdReleased) : [0, 0, 0]
  const susulanResolution = calculateSusulanResolution(susulanQtyInputs.map(Number), susulanBsInputs.map(Number), holdRemaining)
  const requestedHoldGood = susulanResolution.good
  const requestedHoldBs = susulanResolution.bs
  const requestedHoldTotal = susulanResolution.total

  const reworkReadyItems = ledger.filter((item) => item.kind === 'REWORK_RELEASE' || item.kind === 'STUCK_RELEASE')

  const toNotaCard = (item: LedgerItem): ReadyFgNotaCard => {
    const sourceCase = cases.find((entry) => entry.id === item.caseId)
    const sourceComponents = item.componentSnapshots?.map(({ id, name, rate }) => ({ id, name, rate })) ?? (item.kind === 'STUCK_RELEASE'
      ? [{ id: 'hold-value', name: 'Pemulihan nilai Hold', rate: item.rate }]
      : sourceCase?.kind === 'BS'
        ? caseComponents(sourceCase)
          .filter((component) => (item.componentIds ?? []).includes(component.id))
          .map(({ id, name, rate }) => ({ id, name, rate }))
        : [])
    const fallbackSizes: [string, string, string] = ['31', '32', '33']
    return {
      id: item.id,
      kind: item.kind === 'STUCK_RELEASE' ? 'STUCK_RELEASE' : 'REWORK_RELEASE',
      caseId: item.caseId,
      originId: item.originId,
      sourceLabel: item.sourceLabel,
      label: item.label,
      brand: sourceCase?.brand ?? '—',
      sku: sourceCase?.sku ?? '—',
      material: sourceCase?.material ?? '—',
      mandor: item.payee,
      sizes: sourceCase?.sizes ?? fallbackSizes,
      qtyBySize: item.qtyBySize,
      qty: sum(item.qtyBySize),
      components: sourceComponents,
      unitRate: item.rate,
      subtotal: item.amount,
      createdAt: item.createdAt,
    }
  }

  const setSelectedCase = (id: string) => {
    const target=cases.find((item):item is BsCase=>item.kind==='BS'&&item.id===id)
    setSelectedId(id); setReworkInputs(['', '', '']); setSusulanQtyInputs(['', '', '']); setSusulanBsInputs(['', '', '']); setReworkComponentIds(target?.componentIds??[])
    setNewSkuCaseId(null)
  }
  const convertToNewSku = (draft: NewSkuDraft) => {
    if (!selectedBs) return
    const errors = validateNewSkuDraft(draft, reworkRemaining, selectedBs.sizes, usedSkuCodes(cases))
    if (Object.keys(errors).length > 0) return
    const qtyBySize = asSizeValues(draft.qty.map((value) => Number(value) || 0))
    const qty = sum(qtyBySize)
    const code = normalizeSkuCode(draft.code)
    const ordinal = (selectedBs.conversions ?? []).length + 1
    const conversion: BsSkuConversion = {
      id: `SKU-${selectedBs.id.replace(/^BS-/, '').replace(/[^a-z0-9-]/gi, '')}-${String(ordinal).padStart(2, '0')}`,
      newSku: code, newName: draft.name.trim(), gradeNote: draft.gradeNote.trim(), qtyBySize, reason: draft.reason.trim(), createdAt: '28 Agu 2026 · baru saja',
    }
    const remainingAfter = subtractSizes(reworkRemaining, qtyBySize)
    const historyItem: LedgerItem = {
      id: conversion.id, kind: 'BS_TO_NEW_SKU', label: `BS → SKU baru ${code} · ${conversion.newName}`, sign: 0, qtyBySize, rate: 0, amount: 0,
      payee: selectedBs.originalMandor, caseId: selectedBs.id,
      sourceLabel: `Dari ${selectedBs.brand} SKU ${selectedBs.sku} · ${conversion.gradeNote} · ${conversion.reason}`, createdAt: '28 Agu · baru saja',
    }
    setCases((current) => current.map((entry) => entry.kind === 'BS' && entry.id === selectedBs.id ? {
      ...entry,
      conversions: [...(entry.conversions ?? []), conversion],
      status: sum(remainingAfter) === 0 && !['GOOD_RESTORED', 'BS_FINAL'].includes(entry.status) ? 'CONVERTED_SKU' : entry.status,
    } : entry))
    setLedger((current) => [...current, historyItem])
    setReworkInputs(['', '', ''])
    setNewSkuCaseId(null)
    setNotice(`${qty} pcs ${selectedBs.id} (SKU ${selectedBs.sku}) dipindah ke SKU baru ${code} · ${conversion.newName}. Sisa BS fisik ${sum(remainingAfter)} pcs. Simulasi lokal — master Produk & SKU belum berubah.`)
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
    const selectedRate=caseComponentRate(selectedBs, reworkComponentIds)
    if (qty <= 0 || selectedRate <= 0) return
    const releaseOrdinal = ledger.filter((entry) => entry.kind === 'REWORK_RELEASE' && entry.caseId === selectedBs.id).length + 1
    const item: LedgerItem = {
      id: `ADJ-RW-${selectedBs.id.replace(/^BS-/, '').replace(/[^a-z0-9-]/gi, '')}-${String(releaseOrdinal).padStart(2, '0')}`, kind: 'REWORK_RELEASE',
      label: 'Bikin bagus · siap Nota FG', sign: 1, qtyBySize: requested, rate: selectedRate,
      amount: qty * selectedRate, payee: selectedBs.reworkMandor, originId: caseDeduction.id, caseId: selectedBs.id,
      sourceLabel: `Asal ${caseDeduction.id} · QC rework lulus`, createdAt: '28 Agu · baru saja', componentIds: reworkComponentIds,
      componentSnapshots: caseComponents(selectedBs).filter((component) => reworkComponentIds.includes(component.id)).map((component) => ({ ...component })),
    }
    const remainingAfter = subtractSizes(reworkRemaining, requested)
    setLedger((current) => [...current, item])
    setCases((current) => current.map((entry) => entry.kind === 'BS' && entry.id === selectedBs.id ? { ...entry, status: sum(remainingAfter) === 0 ? 'GOOD_RESTORED' : 'QC_REWORK' } : entry))
    setReworkInputs(['', '', ''])
    onNotaCardReady?.(toNotaCard(item))
    setNotice(`${qty} pcs Bikin Bagus menjadi card siap Nota FG untuk ${item.payee}. ${reworkComponentIds.length} komponen bayar sudah disnapshot.`)
  }
  const postHoldResolution = () => {
    if (!selectedStuck || !selectedHold) return
    const goodBySize = requestedHoldGood
    const bsBySize = requestedHoldBs
    const goodQty = sum(goodBySize)
    const bsQty = sum(bsBySize)
    if (goodQty + bsQty <= 0) return
    const serial = String(Date.now()).slice(-6)
    const goodItem: LedgerItem | null = goodQty > 0 ? {
      id: `SUS-${selectedHold.id.replace('HOLD-', '')}-${serial}`, kind: 'STUCK_RELEASE',
      label: 'Susulan Good · plus Hold', sign: 1, qtyBySize: goodBySize, rate: selectedHold.rate,
      amount: goodQty * selectedHold.rate, payee: selectedStuck.mandor, originId: selectedHold.id, caseId: selectedStuck.id,
      sourceLabel: `Asal ${selectedHold.id} · Good diterima ${selectedStuck.mandor}`, createdAt: '29 Agu · baru saja',
      componentSnapshots: [{ id: 'hold-value', name: 'Pemulihan nilai Hold', note: 'Nilai Hold yang benar-benar dilepas', rate: selectedHold.rate }],
    } : null
    const transitionItem: LedgerItem | null = bsQty > 0 ? {
      id: `RCLS-${selectedHold.id.replace('HOLD-', '')}-${serial}`, kind: 'STUCK_TO_BS',
      label: 'Hold → BS · reklasifikasi tanpa potong ulang', sign: 0, qtyBySize: bsBySize, rate: selectedHold.rate,
      amount: bsQty * selectedHold.rate, payee: selectedStuck.mandor, originId: selectedHold.id, caseId: selectedStuck.id,
      sourceLabel: `Asal ${selectedHold.id} · fisik kembali sebagai BS`, createdAt: '29 Agu · baru saja', componentIds: ['hold-value'],
    } : null
    const bsCase: BsCase | null = transitionItem ? {
      kind: 'BS', id: `BS-HOLD-${serial}`, source: 'HOLD_RESOLUTION', sourceNote: selectedStuck.id,
      parentId: selectedStuck.parentId, batchId: selectedStuck.batchId, originalMandor: selectedStuck.mandor,
      reworkMandor: null, brand: selectedStuck.brand, sku: selectedStuck.sku, material: selectedStuck.material,
      sizes: selectedStuck.sizes, qtyBySize: bsBySize, origin: 'HOLD',
      reason: `Susulan ${selectedStuck.laundry} diterima sebagai BS dari Hold. Nilai minus memakai snapshot Hold asal.`,
      status: 'OPEN', componentIds: ['hold-value'], createdAt: '29 Agu 2026 · susulan Laundry',
      deductionOriginId: transitionItem.id, fixedDeductionRate: selectedHold.rate,
    } : null
    const remainingAfter = subtractSizes(holdRemaining, requestedHoldTotal)
    setLedger((current) => [...current, ...[goodItem, transitionItem].filter((item): item is LedgerItem => item !== null)])
    setCases((current) => {
      const updated = current.map((entry) => entry.kind === 'STUCK' && entry.id === selectedStuck.id
        ? { ...entry, status: sum(remainingAfter) === 0 ? 'RESOLVED' as const : 'PARTIAL' as const } : entry)
      return bsCase ? [bsCase, ...updated] : updated
    })
    onStuckReturned?.({parentId:selectedStuck.parentId,batchId:selectedStuck.batchId,laundry:selectedStuck.laundry,goodBySize,bsBySize})
    if (goodItem) onNotaCardReady?.(toNotaCard(goodItem))
    setSusulanQtyInputs(['', '', '']); setSusulanBsInputs(['', '', ''])
    setNotice(`${goodQty} Good melepas Hold +${money(goodItem?.amount ?? 0)}; ${bsQty} BS direklasifikasi tanpa minus kedua dan tanpa QC kedua. Outstanding Laundry ikut turun.`)
  }

  const openCases = cases.filter((item) => !caseIsDone(item)).length
  const totalBsOutstanding = cases.filter((item): item is BsCase => item.kind === 'BS').reduce((total, item) => {
    const deduction = item.deductionOriginId
      ? ledger.find((entry) => entry.id === item.deductionOriginId)
      : ledger.find((entry) => entry.kind === 'BS_DEDUCTION' && entry.caseId === item.id)
    if (!deduction) return total
    const released = ledger.filter((entry) => entry.kind === 'REWORK_RELEASE' && entry.originId === deduction.id).reduce((value, entry) => value + entry.amount, 0)
    return total + Math.max(0, deduction.amount - released)
  }, 0)
  const totalStuck = cases.filter((item): item is StuckCase => item.kind === 'STUCK').reduce((total, item) => {
    const hold = ledger.find((entry) => entry.kind === 'STUCK_HOLD' && entry.caseId === item.id)
    if (!hold) return total
    const released = ledger.filter((entry) => ['STUCK_RELEASE', 'STUCK_TO_BS'].includes(entry.kind) && entry.originId === hold.id).reduce<SizeValues>((sizes, entry) => addSizes(sizes, entry.qtyBySize), [0, 0, 0])
    return total + sum(subtractSizes(hold.qtyBySize, released))
  }, 0)

  return <>
    <section className="hero-copy compact bsr-hero">
      <div><div className="eyebrow">PRODUKSI · MUTU & PENYELESAIAN</div><h1>Kasus BS & Stuck Laundry</h1><p>Preview alur penyelesaian dan formula Susulan. Data, tarif, dan daftar komponen pada halaman ini masih fixture lokal.</p></div>
      <div className="bsr-hero-actions"><button type="button" className="soft-btn" onClick={onBack}><ArrowLeft/> Kembali</button><button type="button" className="primary-btn legacy" onClick={() => setShowLegacyForm(true)}><History/> Impor BS legacy</button></div>
    </section>

    <section className="bsr-rule-banner"><ShieldCheck/><div><strong>SIMULASI FRONTEND · belum menulis transaksi UAT</strong><span>Susulan diselesaikan langsung sebagai <b>Good atau BS</b>, tidak masuk QC kedua. BS hanya mereklasifikasi Hold dan <b>tidak membuat pengurang Nota FG kedua.</b></span></div></section>
    {notice && <div className="bsr-notice"><CheckCircle2/><span>{notice}</span><button type="button" onClick={() => setNotice(null)} aria-label="Tutup pemberitahuan"><X/></button></div>}

    <section className="bsr-kpis">
      <article className="panel"><span>KASUS AKTIF</span><strong>{openCases}</strong><small>BS dan Stuck yang butuh tindakan</small></article>
      <article className="panel danger"><span>MINUS BS TERSISA</span><strong>{money(totalBsOutstanding)}</strong><small>Belum dipulihkan lewat bikin bagus</small></article>
      <article className="panel warn"><span>MASIH DI LAUNDRY</span><strong>{totalStuck} pcs</strong><small>Belum diputus Good atau BS</small></article>
      <article className="panel good"><span>PLUS SIAP NOTA</span><strong>{reworkReadyItems.length}</strong><small>Susulan Good dan Bikin Bagus</small></article>
    </section>

    <section className="panel bsr-toolbar">
      <label className="bsr-search"><Search/><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Cari kasus, PO, batch, Mandor, Laundry, SKU..."/></label>
      <label><Filter/><select value={kindFilter} onChange={(event) => setKindFilter(event.target.value)}><option value="ALL">Semua kasus</option><option value="BS">Barang BS</option><option value="STUCK">Stuck Laundry</option></select></label>
      <div className="bsr-toolbar-picker"><BrowsePicker label="Mandor" hideLabel aria-label="Filter mandor" size="compact" value={mandorFilter} options={[{ id: 'Semua mandor', label: 'Semua mandor', pinned: true }, ...mandors.map((mandor) => ({ id: mandor, label: mandor }))]} onChange={setMandorFilter} searchPlaceholder="Cari mandor…" emptyText="Mandor tidak ditemukan."/></div>
      <label><select value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)}><option value="ALL">Semua status</option><option value="ACTIVE">Butuh tindakan</option><option value="DONE">Selesai</option></select></label>
      <label><select value={sourceFilter} onChange={(event) => setSourceFilter(event.target.value)}><option value="ALL">Semua sumber</option><option value="QC_AUTO">QC otomatis</option><option value="HOLD_RESOLUTION">BS dari Hold</option><option value="LEGACY_IMPORT">BS legacy</option><option value="LAUNDRY">Laundry</option></select></label>
    </section>

    <section className="bsr-master-detail">
      <aside className="panel bsr-case-browser">
        <header><div><span>BROWSE SEMUA KASUS</span><strong>{visibleCases.length} ditemukan</strong></div><ClipboardCheck/></header>
        <div className="bsr-case-list">{visibleCases.map((item, index) => <button type="button" className={selected?.id === item.id ? 'active' : ''} onClick={() => setSelectedCase(item.id)} key={item.id}>
          <span className="bsr-case-index">{String(index + 1).padStart(2, '0')}</span>
          <span className="bsr-case-copy"><small><b className={`bsr-kind ${item.kind.toLowerCase()}`}>{item.kind === 'BS' ? 'BS' : 'STUCK'}</b> {item.brand} · {item.createdAt}</small><strong>{item.id}</strong>
            <span className="bsr-case-sku" data-testid="bs-case-sku"><Tag/><b>SKU {item.sku}</b><i>{bsSkuName(item.brand, item.sku)}</i><i>Size {item.sizes.join('/')} · {sum(item.qtyBySize)} pcs</i></span>
            {item.kind === 'BS' && (item.conversions ?? []).length > 0 && <span className="bsr-case-converted"><PackagePlus/>Jadi SKU {(item.conversions ?? []).map((conversion) => conversion.newSku).join(', ')} · {(item.conversions ?? []).reduce((total, conversion) => total + sum(conversion.qtyBySize), 0)} pcs</span>}
            {item.kind === 'BS' ? <><em><UserRound/>{item.originalMandor}</em><span>{item.source === 'QC_AUTO' ? 'QC otomatis' : item.source === 'HOLD_RESOLUTION' ? 'Reklasifikasi Hold' : 'Legacy'} · {item.parentId} · {item.batchId}</span></> : <><em><Waves/>{item.laundry}</em><span>{item.mandor} · {item.parentId} · {item.batchId}</span></>}
          </span><span className={`bsr-status ${caseIsDone(item) ? 'done' : item.kind.toLowerCase()}`}>{caseStatusLabel(item)}</span><ChevronRight/>
        </button>)}{visibleCases.length === 0 && <div className="bsr-empty"><Search/><strong>Kasus tidak ketemu</strong><small>Ubah filter atau kata pencarian.</small></div>}</div>
      </aside>

      <div className="bsr-detail-stack">
        {selectedBs && <article className="panel bsr-case-detail">
          <header className="bsr-detail-head"><span className="bsr-detail-icon"><Wrench/></span><div><small>{selectedBs.source === 'QC_AUTO' ? 'BS OTOMATIS DARI QC' : selectedBs.source === 'HOLD_RESOLUTION' ? `BS DARI HOLD · ${selectedBs.sourceNote}` : `IMPOR LEGACY · ${selectedBs.sourceNote}`}</small><h2>{selectedBs.id} · {selectedBs.brand} SKU {selectedBs.sku}</h2><p>{selectedBs.parentId} · Batch {selectedBs.batchId} · {selectedBs.material}</p></div><strong className="bsr-case-total">{sum(selectedBs.qtyBySize)} BS</strong></header>
          <section className="bsr-sku-identity" aria-label="Identitas SKU barang BS" data-testid="bs-sku-identity">
            <div className="bsr-sku-code"><Tag/><span><small>SKU BARANG BS</small><strong>{selectedBs.brand} · SKU {selectedBs.sku}</strong><em>{bsSkuName(selectedBs.brand, selectedBs.sku)}</em></span></div>
            <div className="bsr-sku-meta"><span><small>SIZE & QTY BS</small><strong>{sizeSummary(selectedBs.sizes, selectedBs.qtyBySize)}</strong></span><span><small>SISA FISIK BS</small><strong>{sum(reworkRemaining)} pcs</strong></span><span><small>GRADE KATALOG</small><strong>{bsSkuProduct(selectedBs.brand, selectedBs.sku)?.grade ?? '—'}</strong></span></div>
            <div className="bsr-sku-action">
              <button type="button" className="soft-btn bsr-new-sku-trigger" aria-expanded={newSkuOpen} disabled={sum(reworkRemaining) <= 0 || bsClosedStatuses.includes(selectedBs.status)} onClick={() => { setNewSkuCaseId(newSkuOpen ? null : selectedBs.id); setNotice(null) }}><PackagePlus/> Jadikan SKU baru</button>
              <small>{sum(reworkRemaining) > 0 && !bsClosedStatuses.includes(selectedBs.status) ? `${sum(reworkRemaining)} pcs bisa dipindah ke SKU baru` : 'Tidak ada sisa fisik BS'}</small>
            </div>
            {(selectedBs.conversions ?? []).length > 0 && <ul className="bsr-sku-conversions" aria-label="SKU baru dari kasus ini">{(selectedBs.conversions ?? []).map((conversion) => <li key={conversion.id}><PackagePlus/><span><strong>Sudah jadi SKU {conversion.newSku} · {conversion.newName}</strong><small>{sum(conversion.qtyBySize)} pcs ({sizeSummary(selectedBs.sizes, conversion.qtyBySize)}) · {conversion.gradeNote} · {conversion.createdAt}</small></span></li>)}</ul>}
          </section>
          {newSkuOpen && <NewSkuForm key={selectedBs.id} item={selectedBs} available={reworkRemaining} usedCodes={usedSkuCodes(cases)} onCancel={() => setNewSkuCaseId(null)} onConfirm={convertToNewSku}/>}
          <ResolutionRoutePicker value={selectedResolution} disabled={bsClosedStatuses.includes(selectedBs.status)} onChange={(route) => {
            setResolutionByCase((current) => ({ ...current, [selectedBs.id]: route }))
            setReworkInputs(['', '', ''])
            setNotice(null)
          }}/>
          {selectedResolution === 'REWORK' && <>
          <section className="bsr-responsibility-grid">
            <article className="origin"><UserRound/><div><span>MANDOR ASAL · PEMILIK MINUS</span><strong>{selectedBs.originalMandor}</strong><small>Minus BS tetap tercatat ke Mandor ini.</small></div></article>
            <article className="reworker"><Wrench/><div><span aria-hidden="true">MANDOR REWORK · PENERIMA PLUS</span><BrowsePicker label="Mandor rework · penerima plus" hideLabel size="compact" value={selectedBs.reworkMandor ?? ''} options={[{ id: '', label: 'Belum ditugaskan', pinned: true }, ...reworkMandors.map((mandor) => ({ id: mandor, label: mandor }))]} disabled={bsClosedStatuses.includes(selectedBs.status)} onChange={updateReworkMandor} searchPlaceholder="Cari mandor rework…" emptyText="Mandor tidak ditemukan."/><small>Boleh berbeda dari Mandor asal.</small></div></article>
          </section>
          <div className={`bsr-timeline ${selectedBs.status === 'BS_FINAL' || selectedBs.status === 'CONVERTED_SKU' ? 'is-final' : ''}`}>{bsStatusSteps.map((step, index) => {
            const activeIndex = bsStatusSteps.findIndex((item) => item.id === selectedBs.status)
            const done = selectedBs.status === 'BS_FINAL' || selectedBs.status === 'CONVERTED_SKU' ? false : index <= activeIndex
            return <div className={done ? 'done' : ''} key={step.id}><span>{done ? <Check/> : index + 1}</span><strong>{step.label}</strong>{index < bsStatusSteps.length - 1 && <i/>}</div>
          })}{selectedBs.status === 'BS_FINAL' && <em><CircleMinus/> BS final</em>}{selectedBs.status === 'CONVERTED_SKU' && <em className="converted"><PackagePlus/> Jadi SKU baru</em>}</div>
          </>}
          <section className="bsr-case-facts"><div><span>SUMBER KASUS</span><strong>{selectedBs.source === 'QC_AUTO' ? 'Dibuat otomatis saat QC diposting' : selectedBs.source === 'HOLD_RESOLUTION' ? 'Reklasifikasi hasil susulan Laundry' : 'Impor arsip BS legacy'}</strong></div><div><span>REFERENSI</span><strong>{selectedBs.sourceNote}</strong></div><div><span>DICATAT</span><strong>{selectedBs.createdAt}</strong></div><div className="wide"><span>ALASAN</span><strong>{selectedBs.reason}</strong></div></section>
          <section className="bsr-size-table with-sku"><header><span>SIZE</span><span>BS AWAL</span><span>SUDAH DIPULIHKAN</span><span>JADI SKU BARU</span><span>SISA MINUS</span></header>{selectedBs.sizes.map((size, index) => <div key={size}><strong>{size}</strong><span>{selectedBs.qtyBySize[index]} pcs</span><span className="plus">{releasedForCase[index]} pcs</span><span className="converted">{convertedForCase[index]} pcs</span><strong className={minusRemaining[index] > 0 ? 'minus' : 'done'}>{minusRemaining[index]} pcs</strong></div>)}</section>
          {selectedResolution !== 'REWORK' && <section className={`bsr-resolution-preview ${selectedResolution.toLowerCase()}`} aria-live="polite">
            <span>{selectedResolution} · REQUIREMENT PREVIEW</span>
            <h3>{resolutionOptions.find((option) => option.id === selectedResolution)?.label}</h3>
            <p>{resolutionOptions.find((option) => option.id === selectedResolution)?.description}</p>
            {selectedResolution === 'REWASH' && <ul><li>Mandor penyelesaian wajib dipilih.</li><li>Aksesori yang dipakai dipilih untuk reimbursement.</li><li>Fee jasa vendor Laundry tetap Rp0.</li></ul>}
            {selectedResolution === 'HOLD' && <ul><li>Menahan kasus BS, bukan membuat Stuck Laundry.</li><li>Tidak menambah FG, Nota, atau payroll.</li></ul>}
            {selectedResolution === 'SCRAP' && <ul><li>Wajib: qty, alasan, actor, dan tanggal.</li><li>Efek persediaan dan HPP harus terlihat sebelum submit.</li></ul>}
            <small>Belum ada tombol simpan; kontrak backend, RLS, idempotency, dan audit trail belum tersedia.</small>
          </section>}
          {selectedResolution === 'REWORK' && <section className="bsr-component-snapshot"><header><div><span>FIXTURE KOMPONEN · BUKAN BOM AUTHORITATIVE</span><strong>{caseDeduction?.id ?? 'Belum ada minus asal'}</strong></div><em><ShieldCheck/> demo lokal</em></header><div>{selectedComponents.map((component) => <article key={component.id}><span><Wrench/></span><div><strong>{component.name}</strong><small>{component.note}</small></div><b>{money(component.rate)}</b></article>)}</div><footer><span>{selectedBs.origin === 'HOLD' ? 'Nilai Hold yang dibawa' : 'Minus per pcs'}</span><strong>− {money(caseDeduction?.rate ?? caseComponentRate(selectedBs, selectedBs.componentIds))}</strong></footer></section>}
          {selectedResolution === 'REWORK' && selectedBs.status === 'QC_REWORK' && sum(reworkRemaining) > 0 && <section className="bsr-release-card rework" data-keyboard-scope><header><CirclePlus/><div><span>BIKIN BAGUS · SIMULASI KOMPONEN BAYAR</span><h3>Tentukan pekerjaan yang benar-benar diselesaikan</h3><p>Daftar komponen masih fixture UI, bukan BOM authoritative. Pilihan ini hanya mutasi lokal untuk <b>{selectedBs.reworkMandor ?? 'Mandor rework belum dipilih'}</b>.</p></div></header><section className="bsr-rework-component-picker"><div><span>KOMPONEN DIKERJAKAN & DIBAYAR</span><strong>{reworkComponentIds.length} dipilih · {money(caseComponentRate(selectedBs, reworkComponentIds))}/pcs</strong></div><div>{selectedComponents.map((component)=>{const active=reworkComponentIds.includes(component.id);return <button type="button" className={active?'active':''} aria-pressed={active} onClick={()=>setReworkComponentIds((current)=>active?current.filter((item)=>item!==component.id):[...current,component.id])} key={component.id}><span>{active&&<Check/>}</span><div><strong>{component.name}</strong><small>{component.note}</small></div><b>{money(component.rate)}</b></button>})}</div></section><div className="bsr-release-grid" data-keyboard-grid>{selectedBs.sizes.map((size, index) => <label key={size}><span>SIZE {size} · maks {reworkRemaining[index]}</span><input inputMode="numeric" data-grid-row={0} data-grid-col={index} value={reworkInputs[index]} onFocus={(event) => event.currentTarget.select()} onChange={(event) => setReworkInputs((current) => asSizeInputs(current.map((value, row) => row === index ? cleanQuantity(event.target.value, reworkRemaining[index]) : value)))}/></label>)}</div><div className="bsr-release-actions"><button type="button" className="primary-btn" disabled={!selectedBs.reworkMandor || reworkComponentIds.length===0 || sum(asSizeValues(reworkInputs.map(Number))) <= 0} onClick={postReworkRelease}>Lulus QC & buat card simulasi <ArrowRight/></button></div></section>}
          {selectedResolution === 'REWORK' && ['OPEN', 'ASSIGNED', 'IN_REWORK'].includes(selectedBs.status) && <div className="bsr-next-action"><div><Clock3/><span><strong>{bsStatusLabels[selectedBs.status]}</strong><small>Simulasi lokal; riwayat UAT belum ditulis.</small></span></div><button type="button" className="primary-btn" onClick={nextBsStatus}>{selectedBs.status === 'OPEN' ? 'Tugaskan rework' : selectedBs.status === 'ASSIGNED' ? 'Mulai bikin bagus' : 'Kirim ke QC ulang'} <ArrowRight/></button></div>}
          {selectedResolution === 'REWORK' && selectedBs.status === 'GOOD_RESTORED' && <div className="bsr-closed good"><CheckCircle2/><div><strong>Seluruh minus kasus sudah dipulihkan</strong><span>Mandor asal dan Mandor pelaksana tetap terlihat terpisah.</span></div></div>}
          {selectedResolution === 'REWORK' && selectedBs.status === 'BS_FINAL' && <div className="bsr-closed final"><CircleMinus/><div><strong>Riwayat BS final</strong><span>Status lama hanya ditampilkan; halaman ini tidak lagi menyediakan bypass penetapan BS final.</span></div></div>}
          {selectedBs.status === 'CONVERTED_SKU' && <div className="bsr-closed converted"><PackagePlus/><div><strong>Seluruh sisa fisik BS sudah jadi SKU baru</strong><span>Minus Mandor asal tetap tercatat; SKU baru bukan hasil bikin bagus.</span></div></div>}
          {caseHistory.length > 0 && <section className="bsr-case-history" aria-label="Riwayat kasus"><header><History/><span>RIWAYAT KASUS</span></header><ol>{caseHistory.map((entry) => <li key={entry.id} className={entry.kind === 'BS_TO_NEW_SKU' ? 'sku' : entry.sign > 0 ? 'plus' : entry.sign < 0 ? 'minus' : ''}><span><strong>{entry.label}</strong><small>{entry.createdAt} · {entry.id} · {entry.sourceLabel}</small></span><b>{sum(entry.qtyBySize)} pcs{entry.amount > 0 ? ` · ${entry.sign < 0 ? '−' : entry.sign > 0 ? '+' : ''}${money(entry.amount)}` : ''}</b></li>)}</ol></section>}
        </article>}

        {selectedStuck && <article className="panel bsr-stuck-card selected-case"><header><Waves/><div><span>STUCK LAUNDRY · BUKAN BS</span><h2>{selectedStuck.id} · {selectedStuck.laundry}</h2><p>{selectedStuck.parentId} · Batch {selectedStuck.batchId} · {selectedStuck.brand} SKU {selectedStuck.sku} · {bsSkuName(selectedStuck.brand, selectedStuck.sku)}</p></div><strong>{sum(holdRemaining)} pcs di luar</strong></header>
          <section className="bsr-responsibility-grid stuck"><article className="origin"><UserRound/><div><span>MANDOR PENERIMA FISIK</span><strong>{selectedStuck.mandor}</strong><small>Mandor mengonfirmasi susulan benar-benar kembali.</small></div></article><article className="laundry"><Waves/><div><span>LAUNDRY & REFERENSI</span><strong>{selectedStuck.laundry}</strong><small>{selectedStuck.deliveryRef} · {selectedStuck.receiptRef}</small></div></article></section>
          <div className="bsr-stuck-body">
            <section className="bsr-stuck-sizes">{selectedStuck.sizes.map((size, index) => <div key={size}><span>Size {size}</span><strong>{holdRemaining[index]} pcs</strong><small>dari {selectedStuck.qtyBySize[index]} hold</small></div>)}</section>
            <section className="bsr-susulan-entry" data-keyboard-scope>
              <div><span>SUSULAN LANGSUNG · TANPA QC KEDUA</span><strong>Isi qty_susulan dan qty_bs_susulan; Good dihitung otomatis</strong></div>
              <div className="bsr-hold-lanes" data-keyboard-grid>
                <section className="total"><header><Waves/><span><strong>QTY SUSULAN</strong><small>Total fisik yang benar-benar kembali</small></span></header><div className="bsr-release-grid">{selectedStuck.sizes.map((size, index) => <label key={size}><span>qty_susulan · SIZE {size} · maks {holdRemaining[index]}</span><input data-field={`qty_susulan_${size}`} inputMode="numeric" data-grid-row={0} data-grid-col={index} value={susulanQtyInputs[index]} disabled={holdRemaining[index] === 0} onFocus={(event) => event.currentTarget.select()} onChange={(event) => {
                  const totalValue = cleanQuantity(event.target.value, holdRemaining[index])
                  setSusulanQtyInputs((current) => asSizeInputs(current.map((value, row) => row === index ? totalValue : value)))
                  setSusulanBsInputs((current) => asSizeInputs(current.map((value, row) => row === index ? cleanQuantity(value, Number(totalValue) || 0) : value)))
                }}/></label>)}</div></section>
                <section className="bs"><header><CircleMinus/><span><strong>QTY BS SUSULAN</strong><small>Bagian dari qty_susulan; tanpa minus kedua</small></span></header><div className="bsr-release-grid">{selectedStuck.sizes.map((size, index) => <label key={size}><span>qty_bs_susulan · SIZE {size} · maks {requestedHoldTotal[index]}</span><input data-field={`qty_bs_susulan_${size}`} inputMode="numeric" data-grid-row={1} data-grid-col={index} value={susulanBsInputs[index]} disabled={requestedHoldTotal[index] === 0} onFocus={(event) => event.currentTarget.select()} onChange={(event) => setSusulanBsInputs((current) => asSizeInputs(current.map((value, row) => row === index ? cleanQuantity(event.target.value, requestedHoldTotal[index]) : value)))}/></label>)}</div></section>
              </div>
              <div className="bsr-susulan-formula" aria-live="polite"><strong>GOOD = qty_susulan − qty_bs_susulan</strong>{selectedStuck.sizes.map((size, index) => <span key={size}>Size {size}: {requestedHoldTotal[index]} − {requestedHoldBs[index]} = <b>{requestedHoldGood[index]} Good</b></span>)}</div>
              <div className="bsr-hold-preview"><span><small>GOOD TURUNAN</small><strong>{sum(requestedHoldGood)} pcs · +{money(sum(requestedHoldGood) * (selectedHold?.rate ?? 0))}</strong></span><span><small>BS SUSULAN</small><strong>{sum(requestedHoldBs)} pcs · potong ulang Rp0</strong></span><em>Sisa Hold {sum(susulanResolution.remaining)} pcs</em></div>
              <button type="button" className="primary-btn" disabled={sum(requestedHoldTotal) <= 0} onClick={postHoldResolution}>Simpan simulasi susulan <ArrowRight/></button>
            </section>
          </div>
          <div className="bsr-stuck-rule"><ShieldCheck/><span><strong>Satu nilai pengurang, satu kali saja.</strong> Hold dan BS memakai nominal snapshot yang sama. Perubahan Hold → BS hanya memindahkan klasifikasi; bila Bikin Bagus lulus, plus mengacu ke nilai Hold asal.</span></div>
          {selectedStuck.status === 'RESOLVED' && <div className="bsr-closed good"><CheckCircle2/><div><strong>Semua fisik sudah diputus sebagai Good atau BS</strong><span>Kasus selesai langsung tanpa QC kedua; Good menjadi plus dan BS membawa nilai pengurang asal tanpa potong ulang.</span></div></div>}
        </article>}
        {!selected && <article className="panel bsr-no-selection"><Inbox/><strong>Tidak ada kasus pada filter ini</strong><span>Ubah filter untuk membuka detail tindakan.</span></article>}
      </div>
    </section>

    <article className="panel bsr-ready-nota">
      <header><div><span>PLUS DARI SUSULAN & BIKIN BAGUS</span><h2>Card siap disusun pada Nota FG</h2><p>Susulan Good melepas Hold. Hasil Bikin Bagus memulihkan pengurang asal; reklasifikasi Hold → BS sendiri tidak membuat card nominal baru.</p></div><ReceiptText/></header>
      <div className="bsr-ready-grid">{reworkReadyItems.map((item) => {const posted=postedFgCardIds.includes(item.id);return <button type="button" disabled={posted} onClick={() => onOpenNota?.(toNotaCard(item))} aria-label={posted?`${item.id} sudah masuk Nota FG`:`Susun ${item.id} ke Nota FG`} key={item.id}><span className="bsr-ready-icon"><PackageCheck/></span><span className="bsr-ready-copy"><small>{item.id} · {item.sourceLabel}</small><strong>{item.label}</strong>{(() => { const sourceCase = cases.find((entry) => entry.id === item.caseId); return sourceCase ? <i className="bsr-ready-sku">SKU {sourceCase.sku} · {bsSkuName(sourceCase.brand, sourceCase.sku)}</i> : null })()}<em><UserRound/>{item.payee}</em><p>{item.kind === 'STUCK_RELEASE' ? 'Pemulihan nilai Hold' : (item.componentSnapshots??[]).map((component)=>component.name).join(' · ')||(item.componentIds??[]).map((id)=>components.find((component)=>component.id===id)?.name??(id==='hold-value'?'Nilai Hold / BS Nota FG':undefined)).filter(Boolean).join(' · ')}</p></span><span className="bsr-ready-amount"><small>{sum(item.qtyBySize)} pcs × {money(item.rate)}</small><strong>{money(item.amount)}</strong><em>{posted?'SUDAH MASUK NOTA':'SUSUN NOTA FG'} {!posted&&<ArrowRight/>}</em></span></button>})}</div>
      <footer><ShieldCheck/><span><strong>Penyusunan tetap dilakukan di Nota FG</strong><small>Card FG Reguler dan Bikin Bagus dipisahkan jelas. Setelah Nota FG posted, barulah dokumen muncul pada Payroll.</small></span></footer>
    </article>
    {showLegacyForm && <LegacyBsDialog result={initialResult} onClose={() => setShowLegacyForm(false)} onCreate={(createdCase, deduction) => {
      setCases((current) => [createdCase, ...current]); setLedger((current) => [deduction, ...current]); setSelectedId(createdCase.id)
      setKindFilter('ALL'); setSourceFilter('ALL'); setShowLegacyForm(false)
      setNotice(`${createdCase.id} diimpor sebagai BS legacy. BS operasional baru tetap hanya berasal dari QC.`)
    }}/>} 
  </>
}

function NewSkuForm({ item, available, usedCodes, onCancel, onConfirm }: {
  item: BsCase
  available: SizeValues
  usedCodes: Set<string>
  onCancel: () => void
  onConfirm: (draft: NewSkuDraft) => void
}) {
  const [draft, setDraft] = useState<NewSkuDraft>(() => ({
    code: '', name: '', gradeNote: `Grade B · eks-BS ${item.brand} ${item.sku} · size ${item.sizes.join('/')}`,
    qty: asSizeInputs(available.map(String)), reason: '',
  }))
  const [step, setStep] = useState<'FORM' | 'REVIEW'>('FORM')
  const [attempted, setAttempted] = useState(false)
  const errors = validateNewSkuDraft(draft, available, item.sizes, usedCodes)
  const quantities = asSizeValues(draft.qty.map((value) => Number(value) || 0))
  const qty = sum(quantities)
  const code = normalizeSkuCode(draft.code)
  const valid = Object.keys(errors).length === 0
  // Kode duplikat ditampilkan langsung; error lain setelah tombol review ditekan.
  const visibleError = (field: keyof NewSkuErrors) => (attempted || (field === 'code' && draft.code.trim() !== '') || field === 'qty') ? errors[field] : undefined
  const update = (patch: Partial<NewSkuDraft>) => { setDraft((current) => ({ ...current, ...patch })); setStep('FORM') }
  const review = () => { setAttempted(true); if (valid) setStep('REVIEW') }
  const fieldError = (field: keyof NewSkuErrors) => visibleError(field) ? <small className="bsr-field-error" role="alert">{visibleError(field)}</small> : null

  return <section className="bsr-new-sku" data-testid="bs-new-sku-form" data-keyboard-scope aria-labelledby={`new-sku-title-${item.id}`}>
    <header><PackagePlus/><div><span>BS → SKU BARU · SIMULASI LOKAL</span><h3 id={`new-sku-title-${item.id}`}>Jadikan SKU baru dari {item.brand} SKU {item.sku}</h3><p>Seperti Ganti Merek: <b>BS keluar = SKU baru masuk</b>. Barang fisik yang sama diberi identitas SKU baru (mis. grade B); SKU asal tetap punya history sendiri.</p></div><button type="button" className="bsr-icon-btn" onClick={onCancel} aria-label="Tutup form SKU baru"><X/></button></header>
    {step === 'FORM' ? <div className="bsr-new-sku-body">
      <div className="bsr-new-sku-route"><span><small>1 · SUMBER BS</small><strong>{item.brand} · SKU {item.sku}</strong><em>{bsSkuName(item.brand, item.sku)}</em><em>Sisa fisik {sum(available)} pcs · {sizeSummary(item.sizes, available)}</em></span><i><ArrowRight/></i><span className="target"><small>2 · SKU BARU</small><strong>{code || 'Kode belum diisi'}</strong><em>{draft.name.trim() || 'Nama belum diisi'}</em><em>{draft.gradeNote.trim() || 'Catatan grade belum diisi'}</em></span></div>
      <div className="bsr-new-sku-fields">
        <label><span>KODE SKU BARU · WAJIB</span><input aria-label="Kode SKU baru" value={draft.code} placeholder={`Contoh: ${item.sku}-B`} aria-invalid={Boolean(visibleError('code'))} onChange={(event) => update({ code: event.target.value })}/>{fieldError('code')}</label>
        <label><span>NAMA PRODUK BARU · WAJIB</span><input aria-label="Nama produk SKU baru" value={draft.name} placeholder={`Contoh: ${bsSkuProduct(item.brand, item.sku)?.name ?? item.brand} Grade B`} aria-invalid={Boolean(visibleError('name'))} onChange={(event) => update({ name: event.target.value })}/>{fieldError('name')}</label>
        <label className="wide"><span>CATATAN SIZE / GRADE · WAJIB</span><input aria-label="Catatan size atau grade" value={draft.gradeNote} aria-invalid={Boolean(visibleError('gradeNote'))} onChange={(event) => update({ gradeNote: event.target.value })}/>{fieldError('gradeNote')}</label>
      </div>
      <div className="bsr-new-sku-qty"><span>3 · QTY DIPINDAH PER SIZE (DARI SISA BS)</span><div data-keyboard-grid>{item.sizes.map((size, index) => <label key={size} className={quantities[index] > available[index] ? 'invalid' : ''}><small>SIZE {size} · maks {available[index]}</small><input aria-label={`Qty SKU baru size ${size}`} inputMode="numeric" data-grid-row={0} data-grid-col={index} value={draft.qty[index]} placeholder="0" onFocus={(event) => event.currentTarget.select()} onChange={(event) => update({ qty: asSizeInputs(draft.qty.map((value, row) => row === index ? cleanQuantity(event.target.value) : value)) })}/></label>)}</div>{fieldError('qty')}</div>
      <label className="bsr-reason"><span>4 · ALASAN · WAJIB</span><textarea aria-label="Alasan jadi SKU baru" value={draft.reason} placeholder="Contoh: Noda kecil permanen, masih layak jual sebagai grade B." aria-invalid={Boolean(visibleError('reason'))} onChange={(event) => update({ reason: event.target.value })}/>{fieldError('reason')}</label>
      <footer><div className="bsr-new-sku-balance"><span><small>BS KELUAR</small><strong>− {qty} pcs</strong></span><i>=</i><span><small>SKU BARU MASUK</small><strong>+ {qty} pcs</strong></span></div><div><button type="button" className="soft-btn" onClick={onCancel}>Batal</button><button type="button" className="primary-btn" onClick={review}>Review SKU baru <ArrowRight/></button></div></footer>
    </div> : <div className="bsr-new-sku-review" role="group" aria-label="Konfirmasi SKU baru">
      <div className="bsr-new-sku-confirm"><ShieldCheck/><div><span>KONFIRMASI · BELUM TERSIMPAN</span><strong>{qty} pcs {item.brand} SKU {item.sku} jadi SKU baru {code}</strong><small>{draft.name.trim()} · {draft.gradeNote.trim()}</small></div></div>
      <dl><div><dt>Per size</dt><dd>{sizeSummary(item.sizes, quantities)}</dd></div><div><dt>Sisa BS sesudah</dt><dd>{sum(subtractSizes(available, quantities))} pcs</dd></div><div><dt>Alasan</dt><dd>{draft.reason.trim()}</dd></div><div><dt>Kasus asal</dt><dd>{item.id} · {item.parentId} · Batch {item.batchId}</dd></div></dl>
      <ul className="bsr-new-sku-guards"><li><Check/> Minus Mandor asal ({item.originalMandor}) tidak berubah — SKU baru bukan hasil bikin bagus.</li><li><Check/> SKU asal {item.sku} tetap punya history; kasus BS mencatat jejak konversi.</li><li><Check/> Simulasi lokal: master Produk & SKU dan stok UAT belum disentuh.</li></ul>
      <footer><button type="button" className="soft-btn" onClick={() => setStep('FORM')}>Ubah lagi</button><button type="button" className="primary-btn" disabled={!valid} onClick={() => onConfirm(draft)}>Ya, jadikan SKU baru <ArrowRight/></button></footer>
    </div>}
  </section>
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
      <section><div className="bsr-form-title"><b>01</b><span><strong>Jejak arsip lama</strong><small>Referensi dan tanggal tidak boleh kosong.</small></span></div><div className="bsr-identity-grid legacy"><label><span>NO. NOTA / CATATAN LAMA</span><input value={legacyRef} onChange={(event) => setLegacyRef(event.target.value)}/></label><label><span>TANGGAL FISIK</span><input type="date" value={physicalDate} onChange={(event) => setPhysicalDate(event.target.value)}/></label><div className="bsr-identity-picker"><BrowsePicker label="MANDOR ASAL · PEMILIK MINUS" size="compact" value={originalMandor} options={(reworkMandors.includes(originalMandor) ? reworkMandors : [originalMandor, ...reworkMandors]).map((mandor) => ({ id: mandor, label: mandor }))} onChange={setOriginalMandor} searchPlaceholder="Cari mandor asal…" emptyText="Mandor tidak ditemukan."/></div></div></section>
      <section><div className="bsr-form-title"><b>02</b><span><strong>Identitas barang & jumlah per size</strong><small>PO, batch, dan SKU dipakai untuk mengembalikan lineage legacy.</small></span></div><div className="bsr-identity-grid"><label><span>BATCH PRODUKSI</span><input value={parentId} onChange={(event) => setParentId(event.target.value)}/></label><label><span>BATCH DISTRIBUSI</span><input value={batchId} onChange={(event) => setBatchId(event.target.value)}/></label><label><span>MEREK</span><input value={brand} onChange={(event) => setBrand(event.target.value)}/></label><label><span>SKU</span><input value={sku} onChange={(event) => setSku(event.target.value)}/></label></div><div className="bsr-new-size-grid" data-keyboard-grid>{sizes.map((size, index) => <label key={size}><span>SIZE {size}</span><input inputMode="numeric" data-grid-row={0} data-grid-col={index} value={qtyInputs[index]} placeholder="0" onFocus={(event) => event.currentTarget.select()} onChange={(event) => setQtyInputs((current) => asSizeInputs(current.map((value, row) => row === index ? cleanQuantity(event.target.value) : value)))}/></label>)}</div></section>
      <section><div className="bsr-form-title"><b>03</b><span><strong>Komponen yang dahulu belum diterima</strong><small>Snapshot menentukan nilai minus dan batas bikin bagus.</small></span></div><div className="bsr-component-picker">{components.map((component) => { const active = selectedComponents.includes(component.id); return <button type="button" className={active ? 'active' : ''} onClick={() => setSelectedComponents((current) => active ? current.filter((id) => id !== component.id) : [...current, component.id])} key={component.id}><span>{active && <Check/>}</span><div><strong>{component.name}</strong><small>{component.note}</small></div><b>{money(component.rate)}</b></button> })}</div></section>
      <section><div className="bsr-form-title"><b>04</b><span><strong>Alasan & preview minus</strong><small>Rework nanti hanya boleh memulihkan nilai yang berasal dari kasus ini.</small></span></div><label className="bsr-reason"><span>CATATAN ARSIP / KONDISI FISIK</span><textarea value={reason} onChange={(event) => setReason(event.target.value)} placeholder="Contoh: Sisa BS dari nota Agustus, obras bawah lepas..."/></label><div className="bsr-minus-preview"><CircleMinus/><span><small>{qty} pcs × {money(rate)} · {selectedComponents.length} komponen · {originalMandor}</small><strong>− {money(qty * rate)}</strong></span></div></section>
    </div>
    <footer><p><ShieldCheck/> Kasus legacy diberi flag khusus; tidak menyamar sebagai hasil QC baru.</p><div><button type="button" className="soft-btn" onClick={onClose}>Batal</button><button type="button" className="primary-btn" disabled={!validIdentity || qty <= 0 || rate <= 0 || reason.trim() === ''} onClick={create}><FilePlus2/> Impor kasus legacy</button></div></footer>
  </section></div>
}
