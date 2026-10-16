import type { Json } from './types/database.preconnect'
import type { ProductionEnvelope } from './productionRecovery'

// D14-14 gap G1: SELESAI DIJAHIT from the connected WIP & Sewing screen (like the UX demo). Closed parsers for the
// workspace and the committed outcome of scripts/cp7-src/cutting-correction/sewing.sql.
export type SewingBlocker = { kind: string; id: string | null; label: string | null; status: string | null }
export type SewingComponent = { code: string; name: string; rate: number; postedQty: number }
// Before the first record: the rates the Native snapshot would take now (estimate; the record commits them at the sewing time).
export type SewingRate = { code: string; name: string; rate: number }
export type SewingEvent = {
  id: string; number: string; qtyPcs: number; physicalAt: string; rowVersion: number; reason: string
  workCompletionId: string; workStatus: string | null; reversed: boolean; wageAmount: number; inPayroll: boolean
  inActivePool: boolean; cancelBlocker: string | null
}
export type SewingWorkspace = {
  groupId: string; groupVersion: string; number: string; poId: string; poNumber: string; poStatus: string
  contractorId: string | null; contractorName: string | null; pickedUpAt: string | null
  effectivePcs: number; sewnPcs: number; maxQty: number; readyUnsentPcs: number; laundryDraftPcs: number
  ratesCommitted: boolean; components: SewingComponent[]; ratePreview: SewingRate[]; events: SewingEvent[]; canCancel: boolean
  reviewToken: string; eligible: boolean; blockers: SewingBlocker[]
}
export type SewingOutcome = {
  action: 'RECORD' | 'REVERSE'; groupId: string; number: string; qtyPcs: number; wageAmount: number | null
  sewnPcs: number; readyUnsentPcs: number; maxQty: number
}

const uuid = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/
function fail(): never { throw new Error('Respons selesai jahit tidak cocok dengan potongan yang diperiksa.') }
function record(value: unknown): Record<string, unknown> {
  if (!value || typeof value !== 'object' || Array.isArray(value)) fail()
  return value as Record<string, unknown>
}
function keys(r: Record<string, unknown>, expected: string[]) {
  if (Object.keys(r).sort().join('|') !== [...expected].sort().join('|')) fail()
}
function text(value: unknown) { if (typeof value !== 'string' || !value) fail(); return value }
function nullableText(value: unknown) { return value === null || value === undefined ? null : text(value) }
function id(value: unknown) { const v = text(value); if (!uuid.test(v)) fail(); return v }
function count(value: unknown) { if (typeof value !== 'number' || !Number.isSafeInteger(value) || value < 0) fail(); return value }
function money(value: unknown) { if (typeof value !== 'number' || !Number.isFinite(value) || value < 0) fail(); return value }
function bool(value: unknown) { if (typeof value !== 'boolean') fail(); return value }
function instant(value: unknown) { const v = text(value); if (Number.isNaN(new Date(v).getTime())) fail(); return v }

export function parseSewingWorkspace(value: unknown, groupId: string): SewingWorkspace {
  const r = record(value)
  keys(r, ['contract_version', 'group_id', 'group_version', 'number', 'po_id', 'po_number', 'po_status', 'contractor_id', 'contractor_name',
    'picked_up_at', 'effective_pcs', 'sewn_pcs', 'max_qty', 'ready_unsent_pcs', 'laundry_draft_pcs', 'rates_committed', 'components',
    'rate_preview', 'events', 'can_cancel', 'review_token', 'eligible', 'blockers', 'business_DML'])
  if (r.contract_version !== 'cp7.sewing-completion-workspace.v1' || r.business_DML !== false || r.group_id !== groupId
    || typeof r.group_version !== 'string' || !/^[1-9][0-9]{0,18}$/.test(r.group_version)
    || typeof r.review_token !== 'string' || !/^[a-f0-9]{32}$/.test(r.review_token)
    || !Array.isArray(r.components) || !Array.isArray(r.rate_preview) || !Array.isArray(r.events) || !Array.isArray(r.blockers)) fail()
  const components = r.components.map(v => {
    const c = record(v); keys(c, ['code', 'name', 'rate', 'posted_qty'])
    return { code: text(c.code), name: text(c.name), rate: money(c.rate), postedQty: count(c.posted_qty) }
  })
  const ratePreview = r.rate_preview.map(v => {
    const c = record(v); keys(c, ['code', 'name', 'rate'])
    return { code: text(c.code), name: text(c.name), rate: money(c.rate) }
  })
  const events = r.events.map(v => {
    const e = record(v)
    keys(e, ['id', 'number', 'qty_pcs', 'physical_at', 'row_version', 'reason', 'work_completion_id', 'work_status', 'reversed', 'wage_amount',
      'in_payroll', 'in_active_pool', 'cancel_blocker'])
    return {
      id: id(e.id), number: text(e.number), qtyPcs: count(e.qty_pcs), physicalAt: instant(e.physical_at), rowVersion: count(e.row_version),
      reason: text(e.reason), workCompletionId: id(e.work_completion_id), workStatus: nullableText(e.work_status), reversed: bool(e.reversed),
      wageAmount: money(e.wage_amount), inPayroll: bool(e.in_payroll), inActivePool: bool(e.in_active_pool), cancelBlocker: nullableText(e.cancel_blocker),
    }
  })
  const blockers = r.blockers.map(v => {
    const b = record(v)
    return { kind: text(b.kind), id: b.id === undefined || b.id === null ? null : text(b.id), label: nullableText(b.label), status: nullableText(b.status) }
  })
  const eligible = bool(r.eligible), maxQty = count(r.max_qty)
  if (eligible !== (blockers.length === 0) || (eligible && maxQty === 0) || bool(r.rates_committed) !== (components.length > 0)
    || (components.length > 0 && ratePreview.length > 0) || (eligible && components.length === 0 && ratePreview.length === 0)) fail()
  const pickedUpAt = r.picked_up_at === null ? null : instant(r.picked_up_at)
  return {
    groupId, groupVersion: r.group_version, number: text(r.number), poId: id(r.po_id), poNumber: text(r.po_number), poStatus: text(r.po_status),
    contractorId: r.contractor_id === null ? null : id(r.contractor_id), contractorName: nullableText(r.contractor_name), pickedUpAt,
    effectivePcs: count(r.effective_pcs), sewnPcs: count(r.sewn_pcs), maxQty, readyUnsentPcs: count(r.ready_unsent_pcs),
    laundryDraftPcs: count(r.laundry_draft_pcs), ratesCommitted: bool(r.rates_committed), components, ratePreview, events, canCancel: bool(r.can_cancel),
    reviewToken: r.review_token, eligible, blockers,
  }
}

export function sewingRecordPayload(w: SewingWorkspace, qty: string, physicalAtIso: string | null, reason: string): Json {
  const why = reason.trim(), n = Number(qty)
  if (!w.eligible || !/^[1-9][0-9]{0,6}$/.test(qty) || n > w.maxQty || !physicalAtIso || why.length < 5 || why.length > 1000) fail()
  return { action: 'RECORD', group_id: w.groupId, qty_pcs: qty, physical_at: physicalAtIso, review_token: w.reviewToken, change_reason: why }
}

export function sewingCancelPayload(w: SewingWorkspace, event: SewingEvent, reason: string): Json {
  const why = reason.trim()
  if (!w.canCancel || event.cancelBlocker !== null || why.length < 5 || why.length > 1000) fail()
  return { action: 'REVERSE', group_id: w.groupId, event_id: event.id, review_token: w.reviewToken, change_reason: why }
}

export function validateSewingOutcome(value: unknown, envelope: ProductionEnvelope): SewingOutcome {
  const r = record(value), p = record(envelope.payload)
  keys(r, ['contract_version', 'kind', 'action', 'request_id', 'group_id', 'po_id', 'number', 'result'])
  const action = p.action === 'RECORD' ? 'RECORD' : p.action === 'REVERSE' ? 'REVERSE' : fail()
  if (envelope.action !== (action === 'RECORD' ? 'RECORD_SEWING' : 'CANCEL_SEWING') || r.contract_version !== 'cp7.sewing-completion-outcome.v1'
    || r.kind !== 'COMMITTED_OUTCOME' || r.action !== action || r.request_id !== envelope.id || r.group_id !== p.group_id) fail()
  const x = record(r.result)
  if (action === 'RECORD') {
    keys(x, ['work_completion_id', 'sewing_event_id', 'qty_pcs', 'wage_amount', 'components', 'sewn_pcs', 'ready_unsent_pcs', 'max_qty'])
    if (String(x.qty_pcs) !== p.qty_pcs || count(x.components) < 1) fail()
  } else {
    keys(x, ['work_completion_id', 'sewing_event_id', 'qty_pcs', 'status', 'sewn_pcs', 'ready_unsent_pcs', 'max_qty'])
    if (x.status !== 'CANCELLED' || x.sewing_event_id !== p.event_id) fail()
  }
  id(x.work_completion_id); id(x.sewing_event_id)
  return {
    action, groupId: id(r.group_id), number: text(r.number), qtyPcs: count(x.qty_pcs), wageAmount: action === 'RECORD' ? money(x.wage_amount) : null,
    sewnPcs: count(x.sewn_pcs), readyUnsentPcs: count(x.ready_unsent_pcs), maxQty: count(x.max_qty),
  }
}

const blockerKinds: Record<string, string> = {
  NO_POSTED_PICKUP: 'Potongan ini belum dibagi ke mandor (Bagi Potongan belum dicatat).',
  CONTRACTOR_NOT_MANDOR: 'Penerima Bagi Potongan bukan mandor jahit.',
  CONTRACTOR_MISMATCH: 'Mandor di PO berbeda dengan mandor yang menerima potongan ini.',
  PO_STATE: 'Production Order sedang ditahan, sudah selesai, atau dibatalkan.',
  NOTHING_TO_SEW: 'Semua potongan sudah tercatat selesai dijahit.',
  NO_WORK_RATE: 'Tarif kerja (BOM kerja) untuk model PO ini belum ada, jadi upah mandor belum bisa dihitung. Isi komponen kerja model dan tarif mandornya di Master Data → Mandor → Tarif upah mandor.',
  WAVE_SKU_RATES: 'Potongan ini memakai tarif mandor per SKU (wave). Catat selesai jahit per ukuran belum tersedia di layar ini.',
}
export function sewingBlockerText(b: SewingBlocker) {
  return `${blockerKinds[b.kind] ?? `Ada catatan lain yang menahan (${b.kind}).`}${b.status ? ` Status: ${b.status}.` : ''}`
}
const cancelKinds: Record<string, string> = {
  ALREADY_CANCELLED: 'Sudah dibatalkan.',
  WORK_NOT_POSTED: 'Setoran jahitnya tidak dalam status tercatat.',
  IN_PAYROLL: 'Upahnya sudah masuk payroll; batalkan payroll dulu.',
  IN_ATTENDANCE_POOL: 'Sudah dipakai pembagian HPP absensi yang aktif; batalkan pool itu dulu.',
  SENT_OR_DRAFTED_TO_LAUNDRY: 'Sebagian potongan ini sudah dikirim atau didraf ke laundry.',
}
export function sewingCancelText(kind: string) { return cancelKinds[kind] ?? `Tidak bisa dibatalkan (${kind}).` }
