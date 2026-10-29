import type { Json } from './types/database.preconnect'
import type { ProductionEnvelope } from './productionRecovery'

// R3-04 (Sol KNOWN-R2-POOL-UI, Astra ASTRA-C17-07; owner D16-1): the attendance HPP pool ("Pool HPP absensi") on the connected
// "HPP & Rekalkulasi" page. Closed parsers for scripts/cp7-src/hpp-pool/pool.sql: every object must have exactly the keys the
// server sends; amounts stay exact decimal strings. Which actions a pool offers comes from the server (`actions`), never from
// a rule guessed here.
export type HppPoolStatus = 'DRAFT' | 'ACTIVE' | 'CANCELLED' | 'VOIDED'
export type HppPoolAction = 'ACTIVATE' | 'CANCEL' | 'REPLACE'
export type HppPoolRef = { id: string; poolNumber: string; status: HppPoolStatus }
export type HppPoolPo = { poId: string; poNumber: string | null; sewingQty: number }
export type HppPoolAllocation = HppPoolPo & { amount: string }
export type HppPoolPeriodHold = {
  domain: 'ATTENDANCE_PERIOD_CHOICE'; decisionId: string; sourcePeriodStart: string; sourcePeriodEnd: string
}
export type HppPoolAttendanceChoice = HppPoolPeriodHold & {
  allocationId: string; outputPeriodStart: string; outputPeriodEnd: string; outputPeriodClosed: boolean
}
export type HppPool = {
  id: string; poolNumber: string; status: HppPoolStatus; periodStart: string; periodEnd: string
  numeratorAmount: string; denominatorQty: number; unitCost: string | null; sourceCount: number; poCount: number; allocations: HppPoolAllocation[]
  correctionOf: HppPoolRef | null; replacedBy: HppPoolRef[]
  createdAt: string; createdBy: string | null; reason: string
  activatedAt: string | null; activatedBy: string | null; activationReason: string | null
  cancelledAt: string | null; cancelledBy: string | null; cancellationReason: string | null
  journalNumber: string | null; reversalJournalNumber: string | null
  rowVersion: number; reviewToken: string; periodClosed: boolean; stale: boolean; staleMessage: string | null; actions: HppPoolAction[]
  attendanceChoice: HppPoolAttendanceChoice | null; periodHold: HppPoolPeriodHold | null
}
export type HppPoolPeriod = { periodStart: string; periodEnd: string; payrollCount: number; pool: HppPoolRef | null }
export type HppPoolBlocker = { code: string; message: string }
export type HppPoolPreview = {
  periodStart: string; periodEnd: string; status: 'READY' | 'BLOCKED'; periodClosed: boolean; existingPool: HppPoolRef | null
  cancelledPools: { id: string; poolNumber: string }[]
  numeratorAmount: string | null; denominatorQty: number | null; unitCost: string | null; sourceCount: number | null
  destinationCount: number | null; poCount: number | null; pos: HppPoolPo[]; manifestSha256: string | null; reviewToken: string | null
  blocker: HppPoolBlocker | null; canCreate: boolean
  periodHold: HppPoolPeriodHold | null
}
export type HppPoolWorkspace = {
  capturedAt: string; offset: number; limit: number; total: number; nextOffset: number | null; closedThrough: string | null
  canManage: boolean; pools: HppPool[]; periods: HppPoolPeriod[]; preview: HppPoolPreview | null
}
export type HppPoolQuery = { offset: number; limit: number; periodStart: string | null; periodEnd: string | null }
export type HppPoolOutcome = {
  action: 'CREATE' | 'ACTIVATE' | 'CANCEL'; requestId: string; poolId: string; poolNumber: string; status: HppPoolStatus; rowVersion: number
  periodStart: string; periodEnd: string; correctionOf: string | null; journalId: string | null; reversalJournalId: string | null
}

const uuidPattern = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/
const statuses: readonly string[] = ['DRAFT', 'ACTIVE', 'CANCELLED', 'VOIDED']
const actionNames: readonly string[] = ['ACTIVATE', 'CANCEL', 'REPLACE']
function fail(): never { throw new Error('Respons pool HPP absensi tidak cocok dengan permintaan. Muat ulang daftar pool.') }
function record(value: unknown): Record<string, unknown> {
  if (!value || typeof value !== 'object' || Array.isArray(value)) fail()
  return value as Record<string, unknown>
}
function keys(r: Record<string, unknown>, expected: string[]) {
  if (Object.keys(r).sort().join('|') !== [...expected].sort().join('|')) fail()
}
// reader15 extends affected objects only. Null, unknown fields and simultaneous ownership/ordinary-hold variants fail closed.
function metadataKeys(r: Record<string, unknown>, expected: string[], ownership = false) {
  const extension = ['period_hold', ...(ownership ? ['attendance_choice'] : [])].filter(k => Object.hasOwn(r, k))
  if (extension.length > 1) fail()
  keys(r, [...expected, ...extension])
}
function list(value: unknown, max: number) { if (!Array.isArray(value) || value.length > max) fail(); return value }
function text(value: unknown) { if (typeof value !== 'string' || !value) fail(); return value }
function nullableText(value: unknown) { return value === null ? null : text(value) }
function id(value: unknown) { const v = text(value); if (!uuidPattern.test(v)) fail(); return v }
function nullableId(value: unknown) { return value === null ? null : id(value) }
function count(value: unknown) { if (typeof value !== 'number' || !Number.isSafeInteger(value) || value < 0) fail(); return value }
function nullableCount(value: unknown) { return value === null ? null : count(value) }
function bool(value: unknown) { if (typeof value !== 'boolean') fail(); return value }
function day(value: unknown) {
  const v = text(value)
  if (!/^[0-9]{4}-[0-9]{2}-[0-9]{2}$/.test(v) || new Date(v + 'T00:00:00Z').toISOString().slice(0, 10) !== v) fail()
  return v
}
function nullableDay(value: unknown) { return value === null ? null : day(value) }
function instant(value: unknown) { const v = text(value); if (!Number.isFinite(Date.parse(v))) fail(); return v }
function nullableInstant(value: unknown) { return value === null ? null : instant(value) }
// numeric(20,2) for money, numeric(28,12) for the cost per piece; never a float.
function money(value: unknown) { const v = text(value); if (!/^[0-9]{1,18}\.[0-9]{2}$/.test(v)) fail(); return v }
function unit(value: unknown) { const v = text(value); if (!/^[0-9]{1,16}\.[0-9]{12}$/.test(v)) fail(); return v }
function token(value: unknown) { const v = text(value); if (!/^[a-f0-9]{32}$/.test(v)) fail(); return v }
function status(value: unknown) { const v = text(value); if (!statuses.includes(v)) fail(); return v as HppPoolStatus }
function ref(value: unknown): HppPoolRef {
  const r = record(value); keys(r, ['id', 'pool_number', 'status'])
  return { id: id(r.id), poolNumber: text(r.pool_number), status: status(r.status) }
}
function po(value: unknown): HppPoolPo {
  const r = record(value); keys(r, ['po_id', 'po_number', 'sewing_qty'])
  return { poId: id(r.po_id), poNumber: nullableText(r.po_number), sewingQty: count(r.sewing_qty) }
}

function periodHold(value: unknown, start: string, end: string): HppPoolPeriodHold {
  const r = record(value); keys(r, ['domain', 'decision_id', 'source_period_start', 'source_period_end'])
  if (r.domain !== 'ATTENDANCE_PERIOD_CHOICE' || day(r.source_period_start) !== start || day(r.source_period_end) !== end) fail()
  return { domain: 'ATTENDANCE_PERIOD_CHOICE', decisionId: id(r.decision_id), sourcePeriodStart: start, sourcePeriodEnd: end }
}
function attendanceChoice(value: unknown, start: string, end: string, closedThrough: string | null): HppPoolAttendanceChoice {
  const r = record(value)
  keys(r, ['domain', 'decision_id', 'allocation_id', 'source_period_start', 'source_period_end', 'output_period_start', 'output_period_end', 'output_period_closed'])
  const source = periodHold({ domain: r.domain, decision_id: r.decision_id, source_period_start: r.source_period_start, source_period_end: r.source_period_end }, start, end)
  const outputPeriodStart = day(r.output_period_start), outputPeriodEnd = day(r.output_period_end), outputPeriodClosed = bool(r.output_period_closed)
  if (outputPeriodStart <= end || outputPeriodEnd < outputPeriodStart || outputPeriodClosed !== (closedThrough !== null && outputPeriodEnd <= closedThrough)) fail()
  return { ...source, allocationId: id(r.allocation_id), outputPeriodStart, outputPeriodEnd, outputPeriodClosed }
}

function pool(value: unknown, closedThrough: string | null): HppPool {
  const r = record(value)
  metadataKeys(r, ['id', 'pool_number', 'status', 'period_start', 'period_end', 'numerator_amount', 'denominator_qty', 'unit_cost_per_sewn_pcs',
    'source_count', 'po_count', 'allocations', 'correction_of', 'replaced_by', 'created_at', 'created_by', 'reason', 'activated_at',
    'activated_by', 'activation_reason', 'cancelled_at', 'cancelled_by', 'cancellation_reason', 'journal_number', 'reversal_journal_number',
    'row_version', 'review_token', 'period_closed', 'stale', 'stale_message', 'actions'], true)
  const allocations = list(r.allocations, 20).map(v => {
    const a = record(v); keys(a, ['po_id', 'po_number', 'sewing_qty', 'amount'])
    return { poId: id(a.po_id), poNumber: nullableText(a.po_number), sewingQty: count(a.sewing_qty), amount: money(a.amount) }
  })
  const actions = list(r.actions, 3).map(v => { const a = text(v); if (!actionNames.includes(a)) fail(); return a as HppPoolAction })
  const out: HppPool = {
    id: id(r.id), poolNumber: text(r.pool_number), status: status(r.status), periodStart: day(r.period_start), periodEnd: day(r.period_end),
    numeratorAmount: money(r.numerator_amount), denominatorQty: count(r.denominator_qty),
    unitCost: r.unit_cost_per_sewn_pcs === null ? null : unit(r.unit_cost_per_sewn_pcs), sourceCount: count(r.source_count), poCount: count(r.po_count),
    allocations, correctionOf: r.correction_of === null ? null : ref(r.correction_of), replacedBy: list(r.replaced_by, 5).map(ref),
    createdAt: instant(r.created_at), createdBy: nullableText(r.created_by), reason: text(r.reason),
    activatedAt: nullableInstant(r.activated_at), activatedBy: nullableText(r.activated_by), activationReason: nullableText(r.activation_reason),
    cancelledAt: nullableInstant(r.cancelled_at), cancelledBy: nullableText(r.cancelled_by), cancellationReason: nullableText(r.cancellation_reason),
    journalNumber: nullableText(r.journal_number), reversalJournalNumber: nullableText(r.reversal_journal_number),
    rowVersion: count(r.row_version), reviewToken: token(r.review_token), periodClosed: bool(r.period_closed), stale: bool(r.stale),
    staleMessage: nullableText(r.stale_message), actions,
    attendanceChoice: null, periodHold: null,
  }
  if (Object.hasOwn(r, 'attendance_choice')) out.attendanceChoice = attendanceChoice(r.attendance_choice, out.periodStart, out.periodEnd, closedThrough)
  if (Object.hasOwn(r, 'period_hold')) out.periodHold = periodHold(r.period_hold, out.periodStart, out.periodEnd)
  // The Native lifecycle shape (attendance_hpp_pool_lifecycle_shape_check) and the actions the server may offer for it.
  const allowed: Record<HppPoolStatus, HppPoolAction[]> = { DRAFT: ['ACTIVATE', 'CANCEL'], ACTIVE: ['CANCEL'], CANCELLED: ['REPLACE'], VOIDED: [] }
  if (out.periodEnd < out.periodStart || out.allocations.length > out.poCount || out.stale !== (out.staleMessage !== null)
    || (out.stale && out.status !== 'DRAFT') || actions.some(a => !allowed[out.status].includes(a)) || new Set(actions).size !== actions.length
    || (out.periodClosed && actions.length > 0) || (out.stale && actions.includes('ACTIVATE'))
    || ((out.status === 'DRAFT' || out.status === 'VOIDED') && (out.journalNumber !== null || out.reversalJournalNumber !== null || out.activatedAt !== null))
    || ((out.status === 'DRAFT' || out.status === 'ACTIVE') && (out.reversalJournalNumber !== null || out.cancelledAt !== null))
    || ((out.status === 'CANCELLED' || out.status === 'VOIDED') && out.cancelledAt === null)
    || ((out.status === 'ACTIVE' || out.status === 'CANCELLED') && out.activatedAt === null)
    || (out.attendanceChoice !== null && (actions.length > 0 || !['ACTIVE', 'CANCELLED'].includes(out.status)))
    || (out.periodHold !== null && (actions.length > 0 || !['CANCELLED', 'VOIDED'].includes(out.status)))
    || ((out.attendanceChoice !== null || out.periodHold !== null) && out.periodClosed !== (closedThrough !== null && out.periodEnd <= closedThrough))) fail()
  return out
}

function preview(value: unknown, q: HppPoolQuery, closedThrough: string | null): HppPoolPreview {
  const r = record(value)
  metadataKeys(r, ['period_start', 'period_end', 'status', 'period_closed', 'existing_pool', 'cancelled_pools', 'numerator_amount', 'denominator_qty',
    'unit_cost_per_sewn_pcs', 'source_count', 'destination_count', 'po_count', 'pos', 'manifest_sha256', 'review_token', 'blocker', 'can_create'])
  if (r.period_start !== q.periodStart || r.period_end !== q.periodEnd || (r.status !== 'READY' && r.status !== 'BLOCKED')) fail()
  const ready = r.status === 'READY'
  const cancelledPools = list(r.cancelled_pools, 10).map(v => { const c = record(v); keys(c, ['id', 'pool_number']); return { id: id(c.id), poolNumber: text(c.pool_number) } })
  const out: HppPoolPreview = {
    periodStart: day(r.period_start), periodEnd: day(r.period_end), status: ready ? 'READY' : 'BLOCKED', periodClosed: bool(r.period_closed),
    existingPool: r.existing_pool === null ? null : ref(r.existing_pool), cancelledPools,
    numeratorAmount: r.numerator_amount === null ? null : money(r.numerator_amount), denominatorQty: nullableCount(r.denominator_qty),
    unitCost: r.unit_cost_per_sewn_pcs === null ? null : unit(r.unit_cost_per_sewn_pcs), sourceCount: nullableCount(r.source_count),
    destinationCount: nullableCount(r.destination_count), poCount: nullableCount(r.po_count), pos: list(r.pos, 20).map(po),
    manifestSha256: r.manifest_sha256 === null ? null : text(r.manifest_sha256), reviewToken: r.review_token === null ? null : token(r.review_token),
    blocker: null, canCreate: bool(r.can_create), periodHold: null,
  }
  if (Object.hasOwn(r, 'period_hold')) out.periodHold = periodHold(r.period_hold, out.periodStart, out.periodEnd)
  if (r.blocker !== null) { const b = record(r.blocker); keys(b, ['code', 'message']); out.blocker = { code: text(b.code), message: typeof b.message === 'string' ? b.message : fail() } }
  const figures = [out.numeratorAmount, out.denominatorQty, out.unitCost, out.sourceCount, out.destinationCount, out.poCount, out.manifestSha256, out.reviewToken]
  if (out.existingPool && out.existingPool.status !== 'DRAFT' && out.existingPool.status !== 'ACTIVE') fail()
  // A blocked preview carries no figures at all; a ready one carries all of them.
  if (ready ? figures.some(x => x === null) || out.blocker !== null || !/^[0-9a-f]{64}$/.test(out.manifestSha256 ?? '') || (out.denominatorQty ?? 0) <= 0
    || out.pos.length > (out.poCount ?? 0) || out.canCreate !== (!out.periodClosed && out.existingPool === null)
    : figures.some(x => x !== null) || out.pos.length > 0 || out.blocker === null || out.canCreate) fail()
  if (out.periodHold !== null && (ready || out.blocker?.code !== 'CP7_S03_PERIOD_HELD'
    || out.periodClosed !== (closedThrough !== null && out.periodEnd <= closedThrough))) fail()
  if (out.blocker?.code === 'CP7_S03_PERIOD_HELD' && out.periodHold === null) fail()
  return out
}

export function parseHppPoolWorkspace(value: unknown, q: HppPoolQuery): HppPoolWorkspace {
  const r = record(value)
  keys(r, ['contract_version', 'business_DML', 'captured_at', 'offset', 'limit', 'total', 'next_offset', 'closed_through', 'can_manage', 'pools', 'periods', 'preview'])
  if (r.contract_version !== 'cp7.hpp-pools.v1' || r.business_DML !== false || r.offset !== q.offset || r.limit !== q.limit) fail()
  const closedThrough = nullableDay(r.closed_through)
  const pools = list(r.pools, q.limit).map(v => pool(v, closedThrough)), total = count(r.total), nextOffset = nullableCount(r.next_offset)
  if (q.offset + pools.length > total || (nextOffset === null ? q.offset + pools.length < total : nextOffset !== q.offset + pools.length || nextOffset >= total)
    || new Set(pools.map(p => p.id)).size !== pools.length) fail()
  const periods = list(r.periods, 20).map(v => {
    const p = record(v); keys(p, ['period_start', 'period_end', 'payroll_count', 'pool'])
    return { periodStart: day(p.period_start), periodEnd: day(p.period_end), payrollCount: count(p.payroll_count), pool: p.pool === null ? null : ref(p.pool) }
  })
  const wanted = q.periodStart !== null
  if (wanted !== (r.preview !== null)) fail()
  return {
    capturedAt: instant(r.captured_at), offset: q.offset, limit: q.limit, total, nextOffset, closedThrough,
    canManage: bool(r.can_manage), pools, periods, preview: wanted ? preview(r.preview, q, closedThrough) : null,
  }
}

// What each action sends: exactly the keys pool.sql accepts.
export function hppPoolCreatePayload(p: HppPoolPreview, reason: string, correctionOf: string | null): Json {
  const why = reason.trim()
  if (p.status !== 'READY' || p.periodHold !== null || !p.canCreate || p.reviewToken === null || why.length < 5 || why.length > 1000
    || (correctionOf !== null && !p.cancelledPools.some(c => c.id === correctionOf))) fail()
  return { period_start: p.periodStart, period_end: p.periodEnd, correction_of_pool_id: correctionOf, review_token: p.reviewToken, reason: why }
}
export function hppPoolActionPayload(p: HppPool, action: 'ACTIVATE' | 'CANCEL', reason: string): Json {
  const why = reason.trim()
  if (p.attendanceChoice !== null || p.periodHold !== null || !p.actions.includes(action) || why.length < 5 || why.length > 1000) fail()
  return { pool_id: p.id, review_token: p.reviewToken, reason: why }
}

export function parseHppPoolOutcome(value: unknown, envelope: ProductionEnvelope): HppPoolOutcome {
  const r = record(value), p = record(envelope.payload)
  keys(r, ['contract_version', 'kind', 'action', 'request_id', 'pool_id', 'pool_number', 'status', 'row_version', 'period_start', 'period_end',
    'correction_of_pool_id', 'journal_entry_id', 'reversal_journal_entry_id'])
  if (r.contract_version !== 'cp7.hpp-pool-outcome.v1' || r.kind !== 'COMMITTED_OUTCOME' || r.action !== envelope.action || r.request_id !== envelope.id) fail()
  const out: HppPoolOutcome = {
    action: envelope.action as HppPoolOutcome['action'], requestId: envelope.id, poolId: id(r.pool_id), poolNumber: text(r.pool_number), status: status(r.status),
    rowVersion: count(r.row_version), periodStart: day(r.period_start), periodEnd: day(r.period_end), correctionOf: nullableId(r.correction_of_pool_id),
    journalId: nullableId(r.journal_entry_id), reversalJournalId: nullableId(r.reversal_journal_entry_id),
  }
  if (out.action === 'CREATE') {
    if (out.status !== 'DRAFT' || out.periodStart !== p.period_start || out.periodEnd !== p.period_end || out.correctionOf !== p.correction_of_pool_id
      || out.journalId !== null || out.reversalJournalId !== null) fail()
  } else if (out.action === 'ACTIVATE') {
    if (out.poolId !== p.pool_id || out.status !== 'ACTIVE' || out.journalId === null || out.reversalJournalId !== null) fail()
  } else if (out.action === 'CANCEL') {
    if (out.poolId !== p.pool_id || !(out.status === 'VOIDED' ? out.journalId === null && out.reversalJournalId === null
      : out.status === 'CANCELLED' && out.journalId !== null && out.reversalJournalId !== null)) fail()
  } else fail()
  return out
}

// Plain words for the owner (CLAUDE.md): status, blockers, refusals, dates and amounts in id-ID.
export const hppPoolStatusText: Record<HppPoolStatus, string> = { DRAFT: 'Draf', ACTIVE: 'Aktif', CANCELLED: 'Dibatalkan', VOIDED: 'Dihapus draf' }
const blockerTexts: Record<string, string> = {
  MISSING_POLICY: 'Ada gaji absensi mandor pada periode ini yang belum punya aturan HPP mandor (wajib absensi / Special) untuk seluruh periode. Isi aturannya di Master Data → Mandor, lalu lihat pratinjau lagi.',
  ATTENDANCE_MISMATCH: 'Total absensi pada gaji periode ini tidak sama dengan rincian absensinya. Periksa gaji itu di Payroll & Kasbon dulu.',
  JOURNAL_UNCLEAR: 'Jurnal biaya absensi dari gaji periode ini tidak lengkap atau tidak jelas. Periksa persetujuan gaji itu di Payroll & Kasbon dulu.',
  NO_ATTENDANCE_COST: 'Belum ada biaya absensi mandor biasa untuk periode ini. Pool dibuat dari gaji absensi yang sudah disetujui dengan periode persis sama.',
  NO_SEWING_OUTPUT: 'Ada biaya absensi, tetapi belum ada setoran selesai jahit dari mandor itu pada periode ini, jadi biayanya belum bisa dibagi ke PO.',
  CP7_S03_PERIOD_HELD: 'Periode asal ini sudah memiliki pilihan biaya absensi Owner. Owner membuka Pilihan biaya absensi per periode untuk memeriksa keadaan terbaru; pool biasa tidak dibuat dari periode ini.',
}
export function hppPoolBlockerText(b: HppPoolBlocker) {
  return blockerTexts[b.code] ?? `Server menolak pratinjau periode ini: ${b.message}`
}
const refusalTexts: [string, string][] = [
  ['CP7_S03_PERIOD_CLAIMED', 'Periode asal ini sudah memiliki pilihan biaya absensi Owner. Muat ulang daftar; Owner membuka Pilihan biaya absensi per periode untuk memeriksa pilihan yang berlaku.'],
  ['CP7_S03_OWNING_CARRY_CANCEL_REQUIRED', 'Pool ini dikelola melalui Pilihan biaya absensi per periode. Owner membuka periode asalnya dan memeriksa pembatalan alokasi di sana. Muat ulang daftar pool.'],
  ['CP7_S03_OWNER_REQUIRED', 'Tindakan pilihan biaya absensi memerlukan Owner aktif dengan hak mengelola HPP. Minta Owner membuka Pilihan biaya absensi per periode pada periode asal, lalu muat ulang halaman ini.'],
  ['CP7_S03_HPP_READ_CHANGED', 'Keadaan pool berubah saat dibaca. Muat ulang daftar pool sebelum memeriksa tindakan lagi.'],
  ['CP7_HPP_POOL_PERIOD_CLOSED', 'Pembukuan periode ini sudah ditutup, jadi pool tidak bisa dibuat, diaktifkan, atau dibatalkan. Bila memang perlu dibetulkan, buka kembali periodenya di Keuangan → Laporan & Tutup Buku → tab Tutup Buku, lalu ulangi.'],
  ['CP7_HPP_POOL_REVIEW_CHANGED', 'Data pool atau pratinjau berubah sejak Anda periksa (mungkin di tab lain). Daftar sudah dimuat ulang; periksa lagi sebelum menyimpan.'],
  ['CP7_HPP_POOL_EXISTS', 'Periode ini sudah punya pool draf atau aktif. Aktifkan atau batalkan pool itu dulu.'],
  ['CP7_HPP_POOL_CORRECTION', 'Pool pengganti hanya boleh mengganti pool yang sudah dibatalkan dengan periode yang sama persis.'],
  ['CP7_HPP_POOL_NOT_READY', 'Pratinjau periode ini belum siap, jadi draf pool belum bisa dibuat.'],
  ['CP7_HPP_POOL_SOURCE_CHANGED', 'Data gaji absensi, aturan HPP mandor, atau setoran jahit periode ini berubah sejak draf dibuat. Batalkan draf ini lalu buat draf baru.'],
  ['CP7_HPP_POOL_STATUS', 'Status pool sudah berubah. Muat ulang daftar pool.'],
  ['CP7_HPP_POOL_NOT_FOUND', 'Pool tidak ditemukan. Muat ulang daftar pool.'],
  ['CP7_HPP_POOL_REQUEST_CHANGED', 'Nomor permintaan ini sudah dipakai untuk isian lain. Periksa hasil permintaan sebelumnya sebelum mengirim lagi.'],
  ['CP7_HPP_POOL_FIELDS', 'Isian belum lengkap. Alasan wajib diisi 5 sampai 1000 huruf.'],
  ['CP7_HPP_POOL_ACCESS_CHANGED', 'Hak akses Anda berubah. Muat ulang halaman.'],
  ['CP7_HPP_POOL_DENIED', 'Pool HPP absensi hanya untuk Owner atau Admin; membuat, mengaktifkan, dan membatalkan pool juga perlu hak HPP "Rekalkulasi".'],
]
// Server refusals in plain words; anything else keeps the caller's own normalisation.
export function hppPoolRefusalText(message: unknown): string | null {
  if (typeof message !== 'string') return null
  return refusalTexts.find(([code]) => message.includes(code))?.[1] ?? null
}
const months = ['Jan', 'Feb', 'Mar', 'Apr', 'Mei', 'Jun', 'Jul', 'Agu', 'Sep', 'Okt', 'Nov', 'Des']
export function hppPoolDay(value: string) {
  const [y, m, d] = value.split('-').map(Number)
  return `${d} ${months[m - 1]} ${y}`
}
export function hppPoolPeriodText(start: string, end: string) {
  return start === end ? hppPoolDay(start) : `${hppPoolDay(start)} – ${hppPoolDay(end)}`
}
// Exact Rupiah from a server decimal string: thousands with '.', decimals with ',' (two at least when not whole).
export function hppPoolRupiah(value: string) {
  const [whole, fraction = ''] = value.split('.'), trimmed = fraction.replace(/0+$/, '')
  const grouped = whole.replace(/\B(?=(\d{3})+(?!\d))/g, '.')
  return `Rp${grouped}${trimmed ? ',' + trimmed.padEnd(2, '0') : ''}`
}
export function hppPoolPcs(value: number) { return `${value.toLocaleString('id-ID')} pcs` }
