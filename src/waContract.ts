import type { Json } from './types/database.preconnect'
import { formatCp6WibDateTime } from './cp6BusinessTime'
import { isUnansweredFailure, normalizeClientError } from './lib/clientError'

// WA-4 (owner D17-3..D17-6): closed parsers for the public RPCs of scripts/cp7-src/alerts/alerts.sql (alerts_read,
// wa_settings_read, wa_settings_save, wa_key_set, wa_test, wa_resolve, settings_json, defaults, analysis_status). Every
// shape below is the server's own; an unknown key, a missing key or a fact the server never writes is refused with
// "Respons ... tidak cocok". The settings predicates mirror wa_settings_save (best practice D13) except the digest/quiet
// hours rule, which only the server decides (CP7_WA_DIGEST_IN_QUIET_HOURS is shown in plain words). The CallMeBot key is
// never parsed, kept or returned here: no reply carries it.
// SS-1 (owner D17-8, D17-9) adds FG_AT_REORDER_POINT: a finished good at or under its reorder point (cp7_stock_formula);
// SS-2/SS-3 add FABRIC_AT_REORDER_POINT and ACCESSORY_AT_REORDER_POINT (materials.sql, material_alert_row).
export const alertKinds = ['FABRIC_BELOW_MINIMUM', 'FABRIC_AT_REORDER_POINT', 'ACCESSORY_AT_REORDER_POINT', 'FG_AT_REORDER_POINT', 'AR_DUE', 'AP_DUE',
  'PRODUCTION_GAP', 'FABRIC_NEED'] as const
export type AlertKind = typeof alertKinds[number]
/** The order of cp7_alert_native.defaults(). */
export const waKinds = ['MANUAL_REMINDER', 'FABRIC_BELOW_MINIMUM', 'FABRIC_AT_REORDER_POINT', 'ACCESSORY_AT_REORDER_POINT', 'FG_AT_REORDER_POINT', 'AR_DUE', 'AP_DUE',
  'PRODUCTION_GAP', 'FABRIC_NEED'] as const
export type WaKind = typeof waKinds[number]
/** The order of the groups on the Pengingat sistem screen (the order of the WhatsApp message, render() in alerts.sql). */
export const alertKindOrder: readonly AlertKind[] = ['FABRIC_BELOW_MINIMUM', 'FABRIC_AT_REORDER_POINT', 'ACCESSORY_AT_REORDER_POINT', 'FG_AT_REORDER_POINT',
  'FABRIC_NEED', 'PRODUCTION_GAP', 'AP_DUE', 'AR_DUE']
export const waKindLabel: Record<WaKind, string> = {
  MANUAL_REMINDER: 'Pengingat pribadi Bos',
  FABRIC_BELOW_MINIMUM: 'Stok kain di bawah minimum',
  FABRIC_AT_REORDER_POINT: 'Stok kain menipis',
  ACCESSORY_AT_REORDER_POINT: 'Stok aksesori menipis',
  FG_AT_REORDER_POINT: 'Stok barang jadi menipis',
  AR_DUE: 'Piutang pelanggan jatuh tempo',
  AP_DUE: 'Tagihan supplier jatuh tempo',
  PRODUCTION_GAP: 'Kekurangan produksi (dari analisis)',
  FABRIC_NEED: 'Kain perlu dibeli (dari analisis)',
}
export const isAnalysisKind = (kind: AlertKind) => kind === 'PRODUCTION_GAP' || kind === 'FABRIC_NEED'
/** The reorder-point kinds (cp7_stock_formula): no party names, keyed by the item or material. */
export const isReorderKind = (kind: AlertKind) => kind === 'FG_AT_REORDER_POINT' || kind === 'FABRIC_AT_REORDER_POINT' || kind === 'ACCESSORY_AT_REORDER_POINT'
export const outboxStates = ['PENDING', 'HELD_QUIET', 'DISPATCHED', 'ACCEPTED', 'UNKNOWN', 'RESOLVED_BEFORE_SEND', 'DISABLED', 'KIND_OFF'] as const
export type OutboxState = typeof outboxStates[number]
export const dispatchStatuses = ['QUEUED', 'PROVIDER_ACCEPTED', 'PROVIDER_REFUSED', 'TRANSPORT_FAILED', 'UNKNOWN', 'NOTHING_DUE'] as const
export type DispatchStatus = typeof dispatchStatuses[number]
export const dispatchKinds = ['INSTANT', 'DIGEST', 'TEST'] as const
export type DispatchKind = typeof dispatchKinds[number]
export type DispatchOutcome = 'DELIVERED' | 'NOT_DELIVERED'
export type WaDetailMode = 'SUMMARY' | 'DETAILED'
export const waTickJobs = ['COLLECT', 'SEND', 'ANALYSIS'] as const
export type WaTickJob = typeof waTickJobs[number]
/** The key rule of vault_key_write; the key itself never leaves the input that holds it. */
export const waKeyPattern = /^[A-Za-z0-9_-]{4,64}$/
export const waPhonePattern = /^\+[1-9][0-9]{7,14}$/
export const ALERTS_RESOLVED_DAYS = 7
export const WA_DIGEST_SLOTS = 4

export type Tick = { at: string; outcome: string | null }
export type AnalysisRun = {
  runId: string; dataAsOf: string; phase: 'SET' | 'CHECK' | 'DONE' | 'FAILED'; rule: 'PRODUCTION_GAP' | 'FABRIC_NEED'; nextOffset: number
  checked: number; stillOpen: number; closed: number; ruleOff: number; error: string | null; startedAt: string; updatedAt: string; finishedAt: string | null
}
export type AnalysisRequest = {
  requestId: string; state: 'PENDING' | 'REQUESTED' | 'FAILED' | 'SKIPPED_NO_CHANGE'
  query: { fromDate: string | null; throughDate: string | null; groupMode: string | null } | null
  freshness: string; createdAt: string; requestedAt: string | null; error: string | null
}
export type AnalysisStatus = { run: AnalysisRun | null; request: AnalysisRequest | null; tick: Tick | null }
export type AlertSource = { kind: AlertKind; lastTryAt: string | null; lastOkAt: string | null; lastError: string | null; openCount: number | null }
export type AlertWa = { state: OutboxState; round: number; reason: string | null; dispatchId: number | null; dispatchStatus: DispatchStatus | null; settledAt: string | null }
export type FabricDetail = { kind: 'FABRIC_BELOW_MINIMUM'; materialId: string; materialSku: string | null; materialName: string; unitCode: string | null; qty: string; minimumQty: string }
type DueFields = {
  documentId: string | null; number: string | null; amount: string | null; dueDate: string | null
  state: 'OVERDUE' | 'DUE_TODAY'; asOf: string | null; invoiceNumbers: string | null
}
export type DueDetail = ({ kind: 'AR_DUE' } & DueFields) | ({ kind: 'AP_DUE' } & DueFields)
type AnalysisFields = {
  runId: string; dataAsOf: string; checkedAt: string | null; label: string | null; targetKey: string | null
  needSnapshotPcs: string | null; needNowPcs: string | null; increasePcs: string | null; materialId: string | null; materialName: string | null
  value: string | null; unit: string | null; threshold: string | null; reason: string | null
}
export type AnalysisDetail = ({ kind: 'PRODUCTION_GAP' } & AnalysisFields) | ({ kind: 'FABRIC_NEED' } & AnalysisFields)
/** cp7_stock_formula.alert_row: the numbers only, quantities as decimal text. */
export type FgReorderDetail = {
  kind: 'FG_AT_REORDER_POINT'; rootId: string; sizeId: string; sku: string; productName: string; sizeCode: string | null
  freePcs: string; wipPcs: string | null; wipStatus: 'COMPLETE' | 'UNKNOWN' | 'NOT_READ'; positionPcs: string | null; reorderPointPcs: string
  basis: 'MANUAL' | 'FORMULA'; dailyMean: string | null; leadDays: string | null; leadBasis: string | null; bufferMode: string | null
  safetyPcs: string | null; serviceLevel: string | null
}
/** cp7_stock_formula.material_alert_row: a fabric or accessory at or under its reorder point, quantities as decimal text. */
type MaterialReorderFields = {
  materialId: string; materialType: 'FABRIC' | 'ACCESSORY'; sku: string; name: string; unitCode: string | null; freeQty: string; onOrderQty: string
  reorderPointQty: string; basis: 'MANUAL' | 'FORMULA'; dailyMean: string | null; leadDays: string | null; safetyQty: string | null; serviceLevel: string | null
}
export type MaterialReorderDetail = ({ kind: 'FABRIC_AT_REORDER_POINT' } & MaterialReorderFields) | ({ kind: 'ACCESSORY_AT_REORDER_POINT' } & MaterialReorderFields)
export type AlertDetail = FabricDetail | MaterialReorderDetail | FgReorderDetail | DueDetail | AnalysisDetail
export type SystemAlert = {
  id: string; kind: AlertKind; subjectKey: string; episode: number; title: string; detail: AlertDetail; partyNames: string[]
  state: 'OPEN' | 'RESOLVED'; openedAt: string; refreshedAt: string; resolvedAt: string | null; resolution: string | null; wa: AlertWa | null
}
export type SystemAlerts = { readAt: string; configured: boolean; collector: Tick | null; analysis: AnalysisStatus | null; kinds: AlertSource[]; rows: SystemAlert[] }

export type WaSettings = {
  revision: number; enabled: boolean; phone: string | null; detail: WaDetailMode; digestTimes: string[]; kinds: WaKind[]
  repeatMinutes: number; burstAfterPerDay: number; burstMergeMinutes: number; maxItems: number
  quietEnabled: boolean; quietStart: string; quietEnd: string; analysisEveryMinutes: number; analysisStart: string; analysisEnd: string
  savedAt: string | null
}
export type WaDispatch = {
  id: number; kind: DispatchKind; status: DispatchStatus; queuedAt: string; answeredAt: string | null; httpStatus: number | null
  providerText: string | null; body: string | null; digestSlot: string | null; resolvedOutcome: DispatchOutcome | null; resolvedAt: string | null; items: number
}
export type WaWorkspace = {
  readAt: string; settings: WaSettings; defaults: WaSettings; keyPresent: boolean; keySetAt: string | null; transportIsCallmebot: boolean
  quietNow: boolean; analysis: AnalysisStatus; ticks: Partial<Record<WaTickJob, Tick>>; outbox: Partial<Record<OutboxState, number>>; dispatches: WaDispatch[]
}
export type WaDraft = {
  enabled: boolean; phone: string; detail: WaDetailMode; digestTimes: string[]; kinds: WaKind[]
  repeatMinutes: string; burstAfterPerDay: string; burstMergeMinutes: string; maxItems: string
  quietEnabled: boolean; quietStart: string; quietEnd: string; analysisEveryMinutes: string; analysisStart: string; analysisEnd: string
}
export type WaSaveResult = { replay: boolean; settings: WaSettings }
export type WaKeyResult = { replay: boolean; keyPresent: boolean; keySetAt: string }
export type WaTestResult = { replay: boolean; dispatchId: number; status: DispatchStatus }
export type WaResolveResult = { replay: boolean; dispatchId: number; outcome: DispatchOutcome }

export class WaResponseError extends Error {}
function fail(what: string): never { throw new WaResponseError(`Respons sambungan WhatsApp tidak cocok (${what}).`) }
type Obj = Record<string, unknown>
const obj = (v: unknown, what: string): Obj => Boolean(v) && typeof v === 'object' && !Array.isArray(v) ? v as Obj : fail(what)
const arr = (v: unknown, what: string): unknown[] => Array.isArray(v) ? v : fail(what)
const str = (v: unknown, what: string) => typeof v === 'string' ? v : fail(what)
const maybeStr = (v: unknown, what: string) => v === null ? null : str(v, what)
const bool = (v: unknown, what: string) => typeof v === 'boolean' ? v : fail(what)
const instant = (v: unknown, what: string) => typeof v === 'string' && Number.isFinite(Date.parse(v)) ? v : fail(what)
const maybeInstant = (v: unknown, what: string) => v === null ? null : instant(v, what)
const count = (v: unknown, what: string) => typeof v === 'number' && Number.isSafeInteger(v) && v >= 0 ? v : fail(what)
const maybeCount = (v: unknown, what: string) => v === null ? null : count(v, what)
const positive = (v: unknown, what: string) => typeof v === 'number' && Number.isSafeInteger(v) && v >= 1 ? v : fail(what)
const maybePositive = (v: unknown, what: string) => v === null ? null : positive(v, what)
const uuid = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i
const uuidText = (v: unknown, what: string) => typeof v === 'string' && uuid.test(v) ? v : fail(what)
const maybeUuid = (v: unknown, what: string) => v === null ? null : uuidText(v, what)
const decimalText = /^-?\d+(\.\d+)?$/
// Numbers come from the sources as text (numeric::text) or, inside the analysis numbers, as JSON numbers.
const decimal = (v: unknown, what: string) => typeof v === 'number' && Number.isFinite(v) ? String(v)
  : typeof v === 'string' && decimalText.test(v) ? v : fail(what)
const maybeDecimal = (v: unknown, what: string) => v === null ? null : decimal(v, what)
const clock = /^([01][0-9]|2[0-3]):[0-5][0-9]$/
const day = /^\d{4}-\d{2}-\d{2}$/
function oneOf<T extends string>(v: unknown, values: readonly T[], what: string): T {
  return typeof v === 'string' && (values as readonly string[]).includes(v) ? v as T : fail(what)
}
function keys(o: Obj, expected: readonly string[], what: string) {
  const got = Object.keys(o).sort(), want = [...expected].sort()
  if (got.length !== want.length || got.some((k, i) => k !== want[i])) fail(what)
}
// Keys a row must have, and the only other keys it may have.
function keysWithin(o: Obj, required: readonly string[], allowed: readonly string[], what: string) {
  const got = Object.keys(o)
  if (required.some(k => !got.includes(k)) || got.some(k => !allowed.includes(k))) fail(what)
}

function tick(v: unknown, what: string): Tick {
  const o = obj(v, what); keys(o, ['at', 'outcome'], what)
  return { at: instant(o.at, what), outcome: maybeStr(o.outcome, what) }
}
const maybeTick = (v: unknown, what: string) => v === null ? null : tick(v, what)

export function parseAnalysisStatus(v: unknown): AnalysisStatus {
  const o = obj(v, 'analisis'); keys(o, ['run', 'request', 'tick'], 'analisis')
  let run: AnalysisRun | null = null
  if (o.run !== null) {
    const r = obj(o.run, 'analisis')
    keys(r, ['run_id', 'data_as_of', 'phase', 'rule', 'next_offset', 'checked', 'still_open', 'closed', 'rule_off', 'error', 'started_at', 'updated_at', 'finished_at'], 'analisis')
    run = { runId: uuidText(r.run_id, 'analisis'), dataAsOf: instant(r.data_as_of, 'analisis'), phase: oneOf(r.phase, ['SET', 'CHECK', 'DONE', 'FAILED'] as const, 'tahap analisis'),
      rule: oneOf(r.rule, ['PRODUCTION_GAP', 'FABRIC_NEED'] as const, 'analisis'), nextOffset: count(r.next_offset, 'analisis'), checked: count(r.checked, 'analisis'),
      stillOpen: count(r.still_open, 'analisis'), closed: count(r.closed, 'analisis'), ruleOff: count(r.rule_off, 'analisis'), error: maybeStr(r.error, 'analisis'),
      startedAt: instant(r.started_at, 'analisis'), updatedAt: instant(r.updated_at, 'analisis'), finishedAt: maybeInstant(r.finished_at, 'analisis') }
    if ((run.finishedAt !== null) !== (run.phase === 'DONE' || run.phase === 'FAILED') || (run.error !== null) !== (run.phase === 'FAILED')) fail('tahap analisis')
  }
  let request: AnalysisRequest | null = null
  if (o.request !== null) {
    const q = obj(o.request, 'analisis otomatis')
    keys(q, ['request_id', 'state', 'query', 'freshness', 'created_at', 'requested_at', 'error'], 'analisis otomatis')
    let query: AnalysisRequest['query'] = null
    if (q.query !== null) {
      const p = obj(q.query, 'analisis otomatis'); keys(p, ['from_date', 'through_date', 'group_mode'], 'analisis otomatis')
      const date = (x: unknown) => x === null ? null : typeof x === 'string' && day.test(x) ? x : fail('analisis otomatis')
      query = { fromDate: date(p.from_date), throughDate: date(p.through_date), groupMode: maybeStr(p.group_mode, 'analisis otomatis') }
    }
    request = { requestId: uuidText(q.request_id, 'analisis otomatis'), state: oneOf(q.state, ['PENDING', 'REQUESTED', 'FAILED', 'SKIPPED_NO_CHANGE'] as const, 'analisis otomatis'),
      query, freshness: str(q.freshness, 'analisis otomatis'), createdAt: instant(q.created_at, 'analisis otomatis'),
      requestedAt: maybeInstant(q.requested_at, 'analisis otomatis'), error: maybeStr(q.error, 'analisis otomatis') }
    if ((request.state === 'SKIPPED_NO_CHANGE') !== (query === null) || (request.requestedAt !== null) !== (request.state === 'REQUESTED' || request.state === 'FAILED')
      || (request.error !== null) !== (request.state === 'FAILED')) fail('analisis otomatis')
  }
  return { run, request, tick: maybeTick(o.tick, 'analisis') }
}

const analysisDetailKeys = ['run_id', 'data_as_of', 'checked_at', 'label', 'target_key', 'need_snapshot_pcs', 'need_now_pcs', 'increase_pcs', 'material_id',
  'material_name', 'value', 'unit', 'threshold', 'reason'] as const
function detail(kind: AlertKind, v: unknown): AlertDetail {
  const d = obj(v, 'rincian')
  if (kind === 'FABRIC_BELOW_MINIMUM') {
    keys(d, ['material_id', 'material_sku', 'material_name', 'unit_code', 'qty', 'minimum_qty'], 'rincian stok')
    return { kind, materialId: uuidText(d.material_id, 'rincian stok'), materialSku: maybeStr(d.material_sku, 'rincian stok'), materialName: str(d.material_name, 'rincian stok'),
      unitCode: maybeStr(d.unit_code, 'rincian stok'), qty: decimal(d.qty, 'rincian stok'), minimumQty: decimal(d.minimum_qty, 'rincian stok') }
  }
  if (kind === 'FG_AT_REORDER_POINT') return fgReorderDetail(d)
  if (kind === 'FABRIC_AT_REORDER_POINT' || kind === 'ACCESSORY_AT_REORDER_POINT') return materialReorderDetail(kind, d)
  if (kind === 'AR_DUE') {
    keys(d, ['sale_id', 'number', 'open_balance', 'due_date', 'state', 'as_of'], 'rincian piutang')
    return { kind, documentId: maybeStr(d.sale_id, 'rincian piutang'), number: maybeStr(d.number, 'rincian piutang'), amount: maybeDecimal(d.open_balance, 'rincian piutang'),
      dueDate: d.due_date === null ? null : typeof d.due_date === 'string' && day.test(d.due_date) ? d.due_date : fail('rincian piutang'),
      state: oneOf(d.state, ['OVERDUE', 'DUE_TODAY'] as const, 'rincian piutang'), asOf: maybeStr(d.as_of, 'rincian piutang'), invoiceNumbers: null }
  }
  if (kind === 'AP_DUE') {
    keys(d, ['purchase_id', 'purchase_number', 'invoice_numbers', 'remaining', 'due_date', 'state', 'as_of'], 'rincian tagihan')
    return { kind, documentId: maybeStr(d.purchase_id, 'rincian tagihan'), number: maybeStr(d.purchase_number, 'rincian tagihan'), amount: maybeDecimal(d.remaining, 'rincian tagihan'),
      dueDate: d.due_date === null ? null : typeof d.due_date === 'string' && day.test(d.due_date) ? d.due_date : fail('rincian tagihan'),
      state: oneOf(d.state, ['OVERDUE', 'DUE_TODAY'] as const, 'rincian tagihan'), asOf: maybeStr(d.as_of, 'rincian tagihan'),
      invoiceNumbers: maybeStr(d.invoice_numbers, 'rincian tagihan') }
  }
  // analysis_row writes all fourteen keys for both kinds (null where the kind has none); the ones a kind needs must be there.
  const required = kind === 'PRODUCTION_GAP'
    ? ['run_id', 'data_as_of', 'checked_at', 'label', 'target_key', 'need_snapshot_pcs', 'need_now_pcs', 'increase_pcs', 'threshold', 'reason']
    : ['run_id', 'data_as_of', 'checked_at', 'label', 'material_id', 'material_name', 'value', 'unit', 'threshold', 'reason']
  keysWithin(d, required, analysisDetailKeys, 'rincian analisis')
  const at = (k: string) => k in d ? d[k] : null
  return { kind, runId: uuidText(d.run_id, 'rincian analisis'), dataAsOf: instant(d.data_as_of, 'rincian analisis'), checkedAt: maybeInstant(at('checked_at'), 'rincian analisis'),
    label: maybeStr(at('label'), 'rincian analisis'), targetKey: maybeStr(at('target_key'), 'rincian analisis'),
    needSnapshotPcs: maybeDecimal(at('need_snapshot_pcs'), 'rincian analisis'), needNowPcs: maybeDecimal(at('need_now_pcs'), 'rincian analisis'),
    increasePcs: maybeDecimal(at('increase_pcs'), 'rincian analisis'), materialId: maybeUuid(at('material_id'), 'rincian analisis'),
    materialName: maybeStr(at('material_name'), 'rincian analisis'), value: maybeDecimal(at('value'), 'rincian analisis'), unit: maybeStr(at('unit'), 'rincian analisis'),
    threshold: maybeDecimal(at('threshold'), 'rincian analisis'), reason: maybeStr(at('reason'), 'rincian analisis') }
}

// alert_row writes all seventeen keys (null where there is none). Only an item at or under a point is an alert, so its
// basis is MANUAL or FORMULA; the formula's parts (cadangan, tingkat layanan) are written for FORMULA only.
function fgReorderDetail(d: Record<string, unknown>): FgReorderDetail {
  const what = 'rincian barang jadi'
  keys(d, ['root_id', 'size_id', 'sku', 'product_name', 'size_code', 'free_pcs', 'wip_pcs', 'wip_status', 'position_pcs', 'reorder_point_pcs', 'basis', 'daily_mean',
    'lead_days', 'lead_basis', 'buffer_mode', 'safety_pcs', 'service_level'], what)
  const text = (v: unknown) => typeof v === 'string' && decimalText.test(v) ? v : fail(what)
  const maybeText = (v: unknown) => v === null ? null : text(v)
  const r: FgReorderDetail = { kind: 'FG_AT_REORDER_POINT', rootId: uuidText(d.root_id, what), sizeId: uuidText(d.size_id, what), sku: str(d.sku, what),
    productName: str(d.product_name, what), sizeCode: maybeStr(d.size_code, what), freePcs: text(d.free_pcs), wipPcs: maybeText(d.wip_pcs),
    wipStatus: oneOf(d.wip_status, ['COMPLETE', 'UNKNOWN', 'NOT_READ'] as const, what), positionPcs: maybeText(d.position_pcs), reorderPointPcs: text(d.reorder_point_pcs),
    basis: oneOf(d.basis, ['MANUAL', 'FORMULA'] as const, what), dailyMean: maybeText(d.daily_mean), leadDays: maybeText(d.lead_days),
    leadBasis: d.lead_basis === null ? null : oneOf(d.lead_basis, ['MEASURED', 'PROFILE'] as const, what),
    bufferMode: d.buffer_mode === null ? null : oneOf(d.buffer_mode, ['STATISTICAL', 'DAYS'] as const, what), safetyPcs: maybeText(d.safety_pcs),
    serviceLevel: d.service_level === null ? null : oneOf(d.service_level, ['0.90', '0.95', '0.99'] as const, what) }
  const complete = r.wipStatus === 'COMPLETE'
  if (complete !== (r.wipPcs !== null) || complete !== (r.positionPcs !== null)) fail(what)
  if (r.basis === 'MANUAL' ? r.bufferMode !== null || r.safetyPcs !== null || r.serviceLevel !== null
    : r.bufferMode === null || r.safetyPcs === null || (r.serviceLevel !== null) !== (r.bufferMode === 'STATISTICAL')) fail(what)
  return r
}

// material_alert_row writes all thirteen keys. Its material type is the kind's; a fabric is an alert on the formula only (a
// fabric with a minimum stays FABRIC_BELOW_MINIMUM), an accessory on the formula or its manual number. Cadangan and tingkat
// layanan are written for the formula only; nothing is on order for an accessory.
function materialReorderDetail(kind: 'FABRIC_AT_REORDER_POINT' | 'ACCESSORY_AT_REORDER_POINT', d: Record<string, unknown>): MaterialReorderDetail {
  const what = 'rincian bahan'
  keys(d, ['material_id', 'material_type', 'sku', 'name', 'unit_code', 'free_qty', 'on_order_qty', 'reorder_point_qty', 'basis', 'daily_mean', 'lead_days',
    'safety_qty', 'service_level'], what)
  const text = (v: unknown) => typeof v === 'string' && decimalText.test(v) ? v : fail(what)
  const maybeText = (v: unknown) => v === null ? null : text(v)
  const r: MaterialReorderDetail = { kind, materialId: uuidText(d.material_id, what), materialType: oneOf(d.material_type, ['FABRIC', 'ACCESSORY'] as const, what),
    sku: str(d.sku, what), name: str(d.name, what), unitCode: maybeStr(d.unit_code, what), freeQty: text(d.free_qty), onOrderQty: text(d.on_order_qty),
    reorderPointQty: text(d.reorder_point_qty), basis: oneOf(d.basis, ['MANUAL', 'FORMULA'] as const, what), dailyMean: maybeText(d.daily_mean),
    leadDays: maybeText(d.lead_days), safetyQty: maybeText(d.safety_qty),
    serviceLevel: d.service_level === null ? null : oneOf(d.service_level, ['0.90', '0.95', '0.99'] as const, what) }
  const formula = r.basis === 'FORMULA'
  if (r.materialType !== (kind === 'FABRIC_AT_REORDER_POINT' ? 'FABRIC' : 'ACCESSORY') || (r.materialType === 'FABRIC' && !formula)
    || (r.materialType === 'ACCESSORY' && Number(r.onOrderQty) !== 0) || formula !== (r.safetyQty !== null) || formula !== (r.serviceLevel !== null)
    || (formula && (r.leadDays === null || r.dailyMean === null))) fail(what)
  return r
}

function alertWa(v: unknown): AlertWa {
  const w = obj(v, 'status WA'); keys(w, ['state', 'round', 'reason', 'dispatch_id', 'dispatch_status', 'settled_at'], 'status WA')
  const r: AlertWa = { state: oneOf(w.state, outboxStates, 'status WA'), round: count(w.round, 'status WA'), reason: maybeStr(w.reason, 'status WA'),
    dispatchId: maybePositive(w.dispatch_id, 'status WA'), dispatchStatus: w.dispatch_status === null ? null : oneOf(w.dispatch_status, dispatchStatuses, 'status WA'),
    settledAt: maybeInstant(w.settled_at, 'status WA') }
  if ((r.dispatchId === null) !== (r.dispatchStatus === null) || ((r.state === 'DISPATCHED' || r.state === 'UNKNOWN') && r.dispatchId === null)) fail('status WA')
  return r
}

/** erp_cp7_get_alerts_v1. `owner`: the server adds the WhatsApp state of each row only for the owner. */
export function parseSystemAlerts(value: unknown, options: { owner: boolean }): SystemAlerts {
  try { return systemAlerts(value, options) } catch (e) {
    throw e instanceof WaResponseError ? new WaResponseError(e.message.replace('Respons sambungan WhatsApp', 'Respons pengingat sistem')) : e
  }
}
function systemAlerts(value: unknown, options: { owner: boolean }): SystemAlerts {
  const w = obj(value, 'pengingat sistem')
  keys(w, ['contract_version', 'read_at', 'configured', 'collector', 'analysis', 'kinds', 'rows'], 'pengingat sistem')
  if (w.contract_version !== 'cp7.system-alerts.v1') fail('kontrak')
  const kinds = arr(w.kinds, 'jenis').map((x): AlertSource => {
    const k = obj(x, 'jenis'); keys(k, ['kind', 'last_try_at', 'last_ok_at', 'last_error', 'open_count'], 'jenis')
    return { kind: oneOf(k.kind, alertKinds, 'jenis'), lastTryAt: maybeInstant(k.last_try_at, 'jenis'), lastOkAt: maybeInstant(k.last_ok_at, 'jenis'),
      lastError: maybeStr(k.last_error, 'jenis'), openCount: maybeCount(k.open_count, 'jenis') }
  })
  const visible = new Set(kinds.map(k => k.kind))
  if (visible.size !== kinds.length) fail('jenis')
  if (visible.has('PRODUCTION_GAP') !== visible.has('FABRIC_NEED')) fail('jenis')
  const analysis = w.analysis === null ? null : parseAnalysisStatus(w.analysis)
  if ((analysis !== null) !== visible.has('PRODUCTION_GAP')) fail('analisis')
  const rows = arr(w.rows, 'daftar').map((x): SystemAlert => {
    const r = obj(x, 'pengingat')
    keys(r, ['id', 'kind', 'subject_key', 'episode', 'title', 'detail', 'party_names', 'state', 'opened_at', 'refreshed_at', 'resolved_at', 'resolution', 'wa'], 'pengingat')
    const kind = oneOf(r.kind, alertKinds, 'jenis pengingat')
    if (!visible.has(kind)) fail('jenis pengingat')
    const a: SystemAlert = { id: uuidText(r.id, 'id'), kind, subjectKey: str(r.subject_key, 'pengingat'), episode: positive(r.episode, 'pengingat'),
      title: str(r.title, 'judul'), detail: detail(kind, r.detail), partyNames: arr(r.party_names, 'nama pihak').map(n => str(n, 'nama pihak')),
      state: oneOf(r.state, ['OPEN', 'RESOLVED'] as const, 'status'), openedAt: instant(r.opened_at, 'waktu muncul'), refreshedAt: instant(r.refreshed_at, 'waktu diperbarui'),
      resolvedAt: maybeInstant(r.resolved_at, 'waktu beres'), resolution: maybeStr(r.resolution, 'alasan beres'), wa: r.wa === null ? null : alertWa(r.wa) }
    if ((a.state === 'OPEN') !== (a.resolvedAt === null) || (a.state === 'OPEN') !== (a.resolution === null)) fail('status')
    if (!options.owner && a.wa !== null) fail('status WA')
    if ((isAnalysisKind(kind) || isReorderKind(kind)) && a.partyNames.length > 0) fail('nama pihak')
    // A finished-goods alert is keyed by its item (target_key root:size), a material alert by the material.
    if (a.detail.kind === 'FG_AT_REORDER_POINT' && a.subjectKey !== `${a.detail.rootId}:${a.detail.sizeId}`) fail('pengingat')
    if ((a.detail.kind === 'FABRIC_AT_REORDER_POINT' || a.detail.kind === 'ACCESSORY_AT_REORDER_POINT') && a.subjectKey !== a.detail.materialId) fail('pengingat')
    return a
  })
  if (rows.length > 500 || new Set(rows.map(r => r.id)).size !== rows.length
    || new Set(rows.map(r => `${r.kind}\u0000${r.subjectKey}\u0000${r.episode}`)).size !== rows.length
    || new Set(rows.filter(r => r.state === 'OPEN').map(r => `${r.kind}\u0000${r.subjectKey}`)).size !== rows.filter(r => r.state === 'OPEN').length) fail('daftar')
  return { readAt: instant(w.read_at, 'waktu baca'), configured: bool(w.configured, 'pengaturan'), collector: maybeTick(w.collector, 'pengumpul'), analysis, kinds, rows }
}

const settingsKeys = ['revision', 'enabled', 'phone_e164', 'detail', 'digest_times', 'kinds', 'repeat_minutes', 'burst_after_per_day', 'burst_merge_minutes',
  'max_items', 'quiet_enabled', 'quiet_start', 'quiet_end', 'analysis_every_minutes', 'analysis_start', 'analysis_end'] as const
function within(v: unknown, lo: number, hi: number, what: string, orZero = false) {
  const n = count(v, what)
  return (orZero && n === 0) || (n >= lo && n <= hi) ? n : fail(what)
}
function settings(v: unknown, what: string): WaSettings {
  const o = obj(v, what)
  const revision = count(o.revision, what)
  keys(o, revision === 0 ? settingsKeys : [...settingsKeys, 'saved_at'], what)
  const times = arr(o.digest_times, what).map(t => typeof t === 'string' && clock.test(t) ? t : fail(what))
  const kinds = arr(o.kinds, what).map(k => oneOf(k, waKinds, what))
  const s: WaSettings = { revision, enabled: bool(o.enabled, what), phone: maybeStr(o.phone_e164, what), detail: oneOf(o.detail, ['SUMMARY', 'DETAILED'] as const, what),
    digestTimes: times, kinds, repeatMinutes: within(o.repeat_minutes, 60, 10080, what, true), burstAfterPerDay: within(o.burst_after_per_day, 1, 200, what),
    burstMergeMinutes: within(o.burst_merge_minutes, 5, 240, what), maxItems: within(o.max_items, 1, 20, what), quietEnabled: bool(o.quiet_enabled, what),
    quietStart: typeof o.quiet_start === 'string' && clock.test(o.quiet_start) ? o.quiet_start : fail(what),
    quietEnd: typeof o.quiet_end === 'string' && clock.test(o.quiet_end) ? o.quiet_end : fail(what),
    analysisEveryMinutes: within(o.analysis_every_minutes, 15, 1440, what, true),
    analysisStart: typeof o.analysis_start === 'string' && clock.test(o.analysis_start) ? o.analysis_start : fail(what),
    analysisEnd: typeof o.analysis_end === 'string' && clock.test(o.analysis_end) ? o.analysis_end : fail(what),
    savedAt: revision === 0 ? null : instant(o.saved_at, what) }
  if (times.length > WA_DIGEST_SLOTS || new Set(times).size !== times.length || new Set(kinds).size !== kinds.length) fail(what)
  if (s.phone !== null && !waPhonePattern.test(s.phone)) fail(what)
  if ((s.enabled && s.phone === null) || s.quietStart === s.quietEnd || s.analysisStart >= s.analysisEnd) fail(what)
  return s
}

/** erp_cp7_get_wa_settings_v1 (owner only). */
export function parseWaWorkspace(value: unknown): WaWorkspace {
  const w = obj(value, 'sambungan')
  keys(w, ['contract_version', 'read_at', 'settings', 'defaults', 'key_present', 'key_set_at', 'transport_is_callmebot', 'quiet_now', 'analysis', 'ticks',
    'outbox', 'dispatches'], 'sambungan')
  if (w.contract_version !== 'cp7.wa-settings.v1') fail('kontrak')
  const defaults = settings(w.defaults, 'pengaturan bawaan')
  if (defaults.revision !== 0) fail('pengaturan bawaan')
  const t = obj(w.ticks, 'jadwal'), ticks: Partial<Record<WaTickJob, Tick>> = {}
  for (const [job, x] of Object.entries(t)) ticks[oneOf(job, waTickJobs, 'jadwal')] = tick(x, 'jadwal')
  const q = obj(w.outbox, 'antrean'), outbox: Partial<Record<OutboxState, number>> = {}
  for (const [state, n] of Object.entries(q)) outbox[oneOf(state, outboxStates, 'antrean')] = positive(n, 'antrean')
  const dispatches = arr(w.dispatches, 'riwayat').map((x): WaDispatch => {
    const d = obj(x, 'riwayat')
    keys(d, ['id', 'kind', 'status', 'queued_at', 'answered_at', 'http_status', 'provider_text', 'body', 'digest_slot', 'resolved_outcome', 'resolved_at', 'items'], 'riwayat')
    const r: WaDispatch = { id: positive(d.id, 'riwayat'), kind: oneOf(d.kind, dispatchKinds, 'riwayat'), status: oneOf(d.status, dispatchStatuses, 'riwayat'),
      queuedAt: instant(d.queued_at, 'riwayat'), answeredAt: maybeInstant(d.answered_at, 'riwayat'),
      httpStatus: d.http_status === null ? null : typeof d.http_status === 'number' && Number.isSafeInteger(d.http_status) ? d.http_status : fail('riwayat'),
      providerText: maybeStr(d.provider_text, 'riwayat'), body: maybeStr(d.body, 'riwayat'), digestSlot: maybeInstant(d.digest_slot, 'riwayat'),
      resolvedOutcome: d.resolved_outcome === null ? null : oneOf(d.resolved_outcome, ['DELIVERED', 'NOT_DELIVERED'] as const, 'riwayat'),
      resolvedAt: maybeInstant(d.resolved_at, 'riwayat'), items: count(d.items, 'riwayat') }
    if ((r.kind === 'DIGEST') !== (r.digestSlot !== null) || (r.status === 'NOTHING_DUE') !== (r.body === null) || (r.status === 'NOTHING_DUE' && r.kind !== 'DIGEST')
      || (r.resolvedOutcome === null) !== (r.resolvedAt === null) || (r.resolvedOutcome !== null && r.status !== 'UNKNOWN')) fail('riwayat')
    return r
  })
  if (dispatches.length > 30 || dispatches.some((d, i) => i > 0 && d.id >= dispatches[i - 1].id)) fail('riwayat')
  return { readAt: instant(w.read_at, 'waktu baca'), settings: settings(w.settings, 'pengaturan'), defaults, keyPresent: bool(w.key_present, 'kunci'),
    keySetAt: maybeInstant(w.key_set_at, 'kunci'), transportIsCallmebot: bool(w.transport_is_callmebot, 'alamat kirim'), quietNow: bool(w.quiet_now, 'jam tenang'),
    analysis: parseAnalysisStatus(w.analysis), ticks, outbox, dispatches }
}

// ---------------------------------------------------------------- the form --
export function waDraftFromSettings(s: WaSettings): WaDraft {
  const slots = [...s.digestTimes].sort()
  return { enabled: s.enabled, phone: s.phone ?? '', detail: s.detail, digestTimes: Array.from({ length: WA_DIGEST_SLOTS }, (_, i) => slots[i] ?? ''),
    kinds: waKinds.filter(k => s.kinds.includes(k)), repeatMinutes: String(s.repeatMinutes), burstAfterPerDay: String(s.burstAfterPerDay),
    burstMergeMinutes: String(s.burstMergeMinutes), maxItems: String(s.maxItems), quietEnabled: s.quietEnabled, quietStart: s.quietStart, quietEnd: s.quietEnd,
    analysisEveryMinutes: String(s.analysisEveryMinutes), analysisStart: s.analysisStart, analysisEnd: s.analysisEnd }
}
export function sameWaDraft(a: WaDraft, b: WaDraft) {
  const norm = (d: WaDraft) => ({ ...d, phone: d.phone.trim(), digestTimes: d.digestTimes.filter(Boolean).sort(), kinds: waKinds.filter(k => d.kinds.includes(k)) })
  return JSON.stringify(norm(a)) === JSON.stringify(norm(b))
}
const whole = (v: string) => /^\d{1,5}$/.test(v.trim()) ? Number(v.trim()) : null
const inRange = (v: string, lo: number, hi: number, orZero = false) => { const n = whole(v); return n !== null && ((orZero && n === 0) || (n >= lo && n <= hi)) }

/** The ranges and formats of wa_settings_save, in plain words; '' when the draft may be sent. */
export function waDraftProblem(d: WaDraft): string {
  const phone = d.phone.trim()
  if (phone !== '' && !waPhonePattern.test(phone)) return 'Nomor WA ditulis dengan kode negara, tanpa spasi atau tanda hubung: 0812… ditulis +62812….'
  if (d.enabled && phone === '') return 'Isi nomor WA Bos sebelum menyalakan WhatsApp.'
  const times = d.digestTimes.map(t => t.trim()).filter(Boolean)
  if (d.digestTimes.length > WA_DIGEST_SLOTS || times.some(t => !clock.test(t))) return 'Jam ringkasan ditulis jam dan menit, misalnya 08:00.'
  if (new Set(times).size !== times.length) return 'Ada jam ringkasan yang sama. Kosongkan yang dobel.'
  if (d.kinds.some(k => !waKinds.includes(k)) || new Set(d.kinds).size !== d.kinds.length) return 'Pilihan jenis pengingat tidak sah. Muat ulang halaman.'
  if (d.detail !== 'SUMMARY' && d.detail !== 'DETAILED') return 'Pilih isi pesan: Ringkas atau Rinci.'
  if (!inRange(d.repeatMinutes, 60, 10080, true)) return 'Ulangan pesan: isi 0 (tidak diulang) atau 60 sampai 10.080 menit.'
  if (!inRange(d.burstAfterPerDay, 1, 200)) return 'Batas pesan sehari: isi 1 sampai 200.'
  if (!inRange(d.burstMergeMinutes, 5, 240)) return 'Jeda pesan gabungan: isi 5 sampai 240 menit.'
  if (!inRange(d.maxItems, 1, 20)) return 'Baris per jenis dalam satu pesan: isi 1 sampai 20.'
  if (!clock.test(d.quietStart) || !clock.test(d.quietEnd)) return 'Jam tenang ditulis jam dan menit, misalnya 21:00 dan 06:00.'
  if (d.quietStart === d.quietEnd) return 'Jam tenang mulai dan selesai tidak boleh sama.'
  if (!inRange(d.analysisEveryMinutes, 15, 1440, true)) return 'Analisis otomatis: isi 0 (mati) atau 15 sampai 1.440 menit.'
  if (!clock.test(d.analysisStart) || !clock.test(d.analysisEnd)) return 'Jam analisis ditulis jam dan menit, misalnya 07:00 dan 20:00.'
  if (d.analysisStart >= d.analysisEnd) return 'Jam analisis: jam mulai harus lebih awal dari jam selesai, di hari yang sama.'
  return ''
}
/** The server refuses to switch WhatsApp on without a number and a stored key (CP7_WA_ENABLE_NEEDS_PHONE_AND_KEY). */
export function waEnableProblem(d: WaDraft, keyPresent: boolean): string {
  return d.enabled && !keyPresent ? 'Simpan kunci CallMeBot dulu sebelum menyalakan WhatsApp.' : ''
}
/** The exact payload of erp_cp7_save_wa_settings_v1: the settings keys minus revision/saved_at, plus expected_revision. */
export function waSettingsPayload(d: WaDraft, expectedRevision: number): Json {
  if (waDraftProblem(d) || !Number.isSafeInteger(expectedRevision) || expectedRevision < 0) fail('isian')
  return { expected_revision: expectedRevision, enabled: d.enabled, phone_e164: d.phone.trim() === '' ? null : d.phone.trim(), detail: d.detail,
    digest_times: d.digestTimes.map(t => t.trim()).filter(Boolean).sort(), kinds: waKinds.filter(k => d.kinds.includes(k)),
    repeat_minutes: whole(d.repeatMinutes)!, burst_after_per_day: whole(d.burstAfterPerDay)!, burst_merge_minutes: whole(d.burstMergeMinutes)!,
    max_items: whole(d.maxItems)!, quiet_enabled: d.quietEnabled, quiet_start: d.quietStart, quiet_end: d.quietEnd,
    analysis_every_minutes: whole(d.analysisEveryMinutes)!, analysis_start: d.analysisStart, analysis_end: d.analysisEnd }
}

// ----------------------------------------------------------- write answers --
/** erp_cp7_save_wa_settings_v1: a replay answers the settings of the first request, which carried the same payload. */
export function parseWaSaveResult(value: unknown, payload: Json): WaSaveResult {
  const o = obj(value, 'hasil simpan'); keys(o, ['replay', 'settings'], 'hasil simpan')
  const p = obj(payload, 'hasil simpan'), s = settings(o.settings, 'hasil simpan')
  const sorted = (v: unknown) => JSON.stringify([...arr(v, 'hasil simpan')].map(x => String(x)).sort())
  if (s.revision !== Number(p.expected_revision) + 1 || s.enabled !== p.enabled || s.phone !== p.phone_e164 || s.detail !== p.detail
    || sorted(s.digestTimes) !== sorted(p.digest_times) || sorted(s.kinds) !== sorted(p.kinds) || s.repeatMinutes !== p.repeat_minutes
    || s.burstAfterPerDay !== p.burst_after_per_day || s.burstMergeMinutes !== p.burst_merge_minutes || s.maxItems !== p.max_items
    || s.quietEnabled !== p.quiet_enabled || s.quietStart !== p.quiet_start || s.quietEnd !== p.quiet_end
    || s.analysisEveryMinutes !== p.analysis_every_minutes || s.analysisStart !== p.analysis_start || s.analysisEnd !== p.analysis_end) fail('hasil simpan')
  return { replay: bool(o.replay, 'hasil simpan'), settings: s }
}
export function parseWaKeyResult(value: unknown): WaKeyResult {
  const o = obj(value, 'hasil kunci'); keys(o, ['replay', 'key_present', 'key_set_at'], 'hasil kunci')
  const r = { replay: bool(o.replay, 'hasil kunci'), keyPresent: bool(o.key_present, 'hasil kunci'), keySetAt: instant(o.key_set_at, 'hasil kunci') }
  if (!r.replay && !r.keyPresent) fail('hasil kunci')
  return r
}
export function parseWaTestResult(value: unknown): WaTestResult {
  const o = obj(value, 'hasil pesan uji'); keys(o, ['replay', 'dispatch_id', 'status'], 'hasil pesan uji')
  const r = { replay: bool(o.replay, 'hasil pesan uji'), dispatchId: positive(o.dispatch_id, 'hasil pesan uji'), status: oneOf(o.status, dispatchStatuses, 'hasil pesan uji') }
  if ((!r.replay && r.status !== 'QUEUED') || r.status === 'NOTHING_DUE') fail('hasil pesan uji')
  return r
}
export function waResolvePayload(dispatchId: number, outcome: DispatchOutcome): Json {
  if (!Number.isSafeInteger(dispatchId) || dispatchId < 1 || (outcome !== 'DELIVERED' && outcome !== 'NOT_DELIVERED')) fail('pilihan')
  return { dispatch_id: dispatchId, outcome }
}
export function parseWaResolveResult(value: unknown, payload: Json): WaResolveResult {
  const o = obj(value, 'hasil tanda'); keys(o, ['replay', 'dispatch_id', 'resolved_outcome'], 'hasil tanda')
  const p = obj(payload, 'hasil tanda')
  const r = { replay: bool(o.replay, 'hasil tanda'), dispatchId: positive(o.dispatch_id, 'hasil tanda'),
    outcome: oneOf(o.resolved_outcome, ['DELIVERED', 'NOT_DELIVERED'] as const, 'hasil tanda') }
  if (r.dispatchId !== p.dispatch_id || r.outcome !== p.outcome) fail('hasil tanda')
  return r
}

// ------------------------------------------------------------ plain words --
// The refusals of alerts.sql in plain words, with the way out (best practice D18).
const refusals: Record<string, string> = {
  CP7_ALERTS_DENIED: 'Akun ini belum bisa membuka Pengingat sistem. Minta Owner memeriksa akun ini di Pengguna & Hak Akses.',
  CP7_ALERTS_QUERY: 'Pilihan daftar Pengingat sistem tidak sah. Muat ulang halaman.',
  CP7_WA_OWNER_ONLY: 'Sambungan WhatsApp hanya bisa dibuka dan diubah oleh akun Owner yang aktif.',
  CP7_WA_REQUEST_REQUIRED: 'Permintaan tidak lengkap. Muat ulang halaman lalu coba lagi.',
  CP7_WA_REQUEST_REUSED: 'Permintaan ini sudah pernah dipakai dengan isi lain. Tekan "Muat ulang sambungan", periksa isinya, lalu coba lagi.',
  CP7_WA_SETTINGS_INVALID: 'Ada isian pengaturan yang belum sesuai. Periksa nomor WA, jam, dan angka-angka di formulir.',
  CP7_WA_SETTINGS_DUPLICATE: 'Ada jam ringkasan atau jenis pengingat yang tertulis dua kali. Kosongkan yang dobel lalu simpan lagi.',
  CP7_WA_DIGEST_IN_QUIET_HOURS: 'Jam ringkasan jatuh di jam tenang, jadi ringkasan itu tidak akan pernah terkirim. Geser jam ringkasan ke luar jam tenang, atau ubah jam tenangnya, lalu simpan lagi.',
  CP7_WA_SETTINGS_STALE: 'Pengaturan ini baru saja diubah di tab atau perangkat lain. Tekan "Muat ulang sambungan", periksa isinya, lalu simpan lagi.',
  CP7_WA_ENABLE_NEEDS_PHONE_AND_KEY: 'WhatsApp baru bisa dinyalakan sesudah nomor WA Bos diisi dan kunci CallMeBot disimpan.',
  CP7_WA_KEY_FORMAT: 'Kunci tidak sesuai: 4 sampai 64 huruf, angka, tanda minus (-) atau garis bawah (_), tanpa spasi. Salin persis dari balasan CallMeBot.',
  CP7_WA_PHONE_MISSING: 'Isi nomor WA Bos lalu tekan "Simpan pengaturan" dulu, baru kirim pesan uji.',
  CP7_WA_KEY_MISSING: 'Simpan kunci CallMeBot dulu, baru kirim pesan uji.',
  CP7_WA_TEST_LIMIT: 'Pesan uji paling banyak 3 kali dalam satu jam. Tunggu sebentar lalu coba lagi.',
  CP7_WA_RESOLVE_INVALID: 'Pilihan tanda pesan tidak sah. Muat ulang riwayat lalu coba lagi.',
  CP7_WA_RESOLVE_NOT_UNKNOWN: 'Pesan ini sudah tidak berstatus "belum pasti" (mungkin sudah ditandai). Tekan "Muat ulang sambungan".',
}
export function waRefusalCode(error: unknown): string | null {
  const message = error && typeof error === 'object' ? (error as { message?: unknown }).message : null
  if (typeof message !== 'string') return null
  const code = /\bCP7_(?:WA|ALERTS)_[A-Z_]+\b/.exec(message)?.[0]
  return code && code in refusals ? code : null
}
export function waRefusal(message: unknown): string | null {
  const code = waRefusalCode({ message })
  return code ? refusals[code] : null
}
/** A read or write error in plain words: a known refusal first, then the shared client wording. */
export function waErrorText(error: unknown): string {
  const code = waRefusalCode(error)
  return code ? refusals[code] : normalizeClientError(error).message
}
/** The key path never echoes server or network text (it could only ever carry what was sent): codes only. */
export function waKeyErrorText(error: unknown): string {
  const code = waRefusalCode(error)
  if (code) return refusals[code]
  if (error instanceof WaResponseError) return 'Jawaban server untuk kunci tidak cocok. Tekan "Muat ulang sambungan" lalu lihat apakah kunci sudah tersimpan.'
  if (isUnansweredFailure(error)) return 'Jawaban server tidak sampai, jadi belum pasti kunci tersimpan. Tekan "Muat ulang sambungan": kalau tertulis "Kunci tersimpan sejak" dengan jam barusan, kunci sudah tersimpan; kalau belum, ketik kuncinya lagi.'
  const status = error && typeof error === 'object' ? (error as { code?: unknown }).code : null
  if (status === '42501') return refusals.CP7_WA_OWNER_ONLY
  return 'Kunci belum tersimpan. Coba lagi; bila tetap gagal, laporkan ke admin.'
}

export const dispatchKindLabel: Record<DispatchKind, string> = { INSTANT: 'Pesan langsung', DIGEST: 'Ringkasan', TEST: 'Pesan uji' }
export function dispatchStatusLabel(d: Pick<WaDispatch, 'status' | 'httpStatus'>): string {
  switch (d.status) {
    case 'QUEUED': return 'Sedang dikirim'
    case 'PROVIDER_ACCEPTED': return 'Diterima CallMeBot'
    case 'PROVIDER_REFUSED': return d.httpStatus === null ? 'Ditolak CallMeBot' : `Ditolak CallMeBot (HTTP ${d.httpStatus})`
    case 'TRANSPORT_FAILED': return 'Gagal tersambung'
    case 'UNKNOWN': return 'Belum pasti'
    case 'NOTHING_DUE': return 'Ringkasan kosong, tidak dikirim'
  }
}
export const outboxStateLabel: Record<OutboxState, string> = {
  PENDING: 'menunggu dikirim', HELD_QUIET: 'ditahan jam tenang', DISPATCHED: 'sedang dikirim', ACCEPTED: 'terkirim', UNKNOWN: 'belum pasti sampai',
  RESOLVED_BEFORE_SEND: 'beres sebelum dikirim', DISABLED: 'tidak dikirim karena WhatsApp mati', KIND_OFF: 'tidak dikirim karena jenisnya dimatikan',
}
const disabledReason: Record<string, string> = {
  WA_OFF: 'WA: tidak dikirim, WhatsApp mati', PHONE_MISSING: 'WA: tidak dikirim, nomor belum diisi', KEY_MISSING: 'WA: tidak dikirim, kunci belum ada',
  NOT_CONFIGURED: 'WA: tidak dikirim, belum diatur',
}
export function waChip(wa: AlertWa | null): { label: string; tone: 'ok' | 'wait' | 'off' | 'bad' } {
  if (!wa) return { label: 'WA: belum tercatat', tone: 'off' }
  switch (wa.state) {
    case 'ACCEPTED': return { label: wa.round > 0 ? `WA: terkirim (ulangan ke-${wa.round})` : 'WA: terkirim', tone: 'ok' }
    case 'PENDING': return { label: wa.reason ? 'WA: menunggu kirim ulang' : 'WA: menunggu', tone: 'wait' }
    case 'HELD_QUIET': return { label: 'WA: jam tenang', tone: 'wait' }
    case 'DISPATCHED': return { label: 'WA: sedang dikirim', tone: 'wait' }
    case 'UNKNOWN': return { label: 'WA: belum pasti', tone: 'bad' }
    case 'RESOLVED_BEFORE_SEND': return { label: 'WA: beres sebelum dikirim', tone: 'off' }
    case 'KIND_OFF': return { label: 'WA: jenis dimatikan', tone: 'off' }
    case 'DISABLED': return { label: (wa.reason && disabledReason[wa.reason]) || 'WA: tidak dikirim', tone: 'off' }
  }
}
const resolutionText: Record<string, string> = {
  AT_OR_ABOVE_MINIMUM: 'Stok sudah mencapai minimum',
  ZERO_BALANCE: 'Sudah lunas',
  NOT_DUE_YET: 'Belum jatuh tempo lagi',
  MISSING_DUE_DATE: 'Tanggal jatuh tempo tidak ada lagi',
  INACTIVE_DOCUMENT: 'Dokumennya sudah dibatalkan',
  UNKNOWN_BALANCE: 'Sisa tagihan belum bisa dipastikan',
  CREDIT_REVIEW: 'Sedang ditinjau karena ada kredit',
  DRAFT_ONLY: 'Dokumennya masih draf',
  DRAFT_PREVIEW: 'Dokumennya masih draf',
  NOT_IN_SOURCE: 'Tidak muncul lagi di datanya',
  ABOVE_REORDER_POINT: 'Stok sudah di atas titik pesan ulang',
  NO_REORDER_POINT: 'Titik pesan ulangnya tidak ada lagi',
  MANUAL_MINIMUM_IN_FORCE: 'Kain ini sekarang memakai angka minimum (Master Data › Kain & Benchmark)',
  RECHECK_RESOLVED_NOW: 'Dicek ulang: kebutuhannya sudah tertutup',
  RECHECK_BELOW_THRESHOLD_NOW: 'Dicek ulang: sudah di bawah ambang pengingat',
  RECHECK_CHANGED_REVIEW_REQUIRED: 'Dicek ulang: datanya berubah, perlu analisis baru',
  RECHECK_UNKNOWN_NOW: 'Dicek ulang: belum bisa dipastikan',
  RECHECK_UNKNOWN: 'Dicek ulang: belum bisa dipastikan',
  RECHECK_NO_LONGER_DUE: 'Dicek ulang: tidak jatuh tempo lagi',
  RECHECK_NOT_FOUND_NOW: 'Dicek ulang: datanya sudah tidak ada',
  RECHECK_CONDITION_CHANGED: 'Dicek ulang: datanya berubah',
  RULE_UNCONFIGURED: 'Aturan pengingatnya belum diatur',
  RULE_DISABLED: 'Aturan pengingatnya dimatikan',
  NOT_OPEN_IN_LATEST_ANALYSIS: 'Tidak muncul lagi di analisis terbaru',
  ANALYSIS_UNAVAILABLE: 'Analisisnya tidak bisa dipakai lagi',
  ANALYSIS_EXPIRED: 'Analisisnya sudah kedaluwarsa',
}
export function resolutionLabel(resolution: string | null): string {
  if (resolution && resolutionText[resolution]) return resolutionText[resolution]
  if (resolution?.startsWith('RECHECK_')) return 'Dicek ulang: sudah tidak terbuka'
  if (resolution?.startsWith('RULE_')) return 'Aturan pengingatnya tidak meminta pengingat ini lagi'
  return 'Sudah beres menurut data terbaru'
}
const tickText: Record<string, string> = {
  COLLECTED: 'sumber sudah dibaca', NOT_CONFIGURED: 'belum berjalan karena pengaturan WhatsApp belum pernah disimpan',
  OWNER_ACCESS_DENIED: 'berhenti: akun Owner yang menyimpan pengaturan tidak aktif atau bukan Owner lagi', BUSY: 'sedang dikerjakan',
  WA_OFF: 'WhatsApp mati, tidak ada yang dikirim', PHONE_MISSING: 'nomor WA belum diisi', KEY_MISSING: 'kunci belum disimpan',
  HELD_QUIET: 'jam tenang, pesan ditahan', DIGEST: 'ringkasan dikirim', IDLE: 'tidak ada yang perlu dikirim', WAITING: 'menunggu jeda kirim', SENT: 'pesan dikirim',
  CONDITION_SET_STEP: 'menyiapkan analisis untuk dicek', KIND_BUSY: 'menunggu giliran', ANALYSIS_CHECKED: 'analisis selesai dicek ulang',
  ANALYSIS_CHECKING: 'sedang mengecek ulang analisis', ANALYSIS_RUN_FAILED: 'analisis tidak bisa dipakai', ANALYSIS_REQUESTED: 'analisis otomatis diminta',
  ANALYSIS_REQUEST_FAILED: 'analisis otomatis gagal diminta', AUTO_ANALYSIS_OFF: 'analisis otomatis dimatikan', OUTSIDE_ANALYSIS_HOURS: 'di luar jam analisis',
  ANALYSIS_RUNNING: 'analisis Bos sedang berjalan', NO_OWNER_ANALYSIS_YET: 'Bos belum pernah menjalankan analisis', NOT_DUE: 'belum waktunya analisis baru',
  NO_CHANGE_SINCE_ANALYSIS: 'data tidak berubah, analisis dilewati', ANALYSIS_DUE: 'analisis baru akan diminta',
}
export const tickOutcomeLabel = (outcome: string | null) => (outcome && tickText[outcome]) || 'selesai'

// ----------------------------------------------------------- the summaries --
const plain = new Intl.NumberFormat('id-ID', { maximumFractionDigits: 2 })
export const formatWaNumber = (n: number) => plain.format(n)
const num = (v: string | null) => v === null ? '?' : plain.format(Number(v))
const rupiah = (v: string | null) => v === null ? 'Rp?' : `Rp${plain.format(Math.round(Number(v)))}`
const dateOnly = (v: string | null) => v === null ? '-' : new Intl.DateTimeFormat('id-ID', { dateStyle: 'medium', timeZone: 'UTC' }).format(new Date(`${v}T00:00:00Z`))
/** A calendar date (YYYY-MM-DD) as "20 Okt 2026". */
export const formatWaDay = dateOnly
const dueState = { OVERDUE: 'lewat jatuh tempo', DUE_TODAY: 'jatuh tempo hari ini' } as const
function invoiceList(v: string | null) {
  if (!v) return null
  try { const x: unknown = JSON.parse(v); if (Array.isArray(x) && x.every(i => typeof i === 'string')) return x.length ? x.join(', ') : null } catch { /* plain text */ }
  return v
}
/** cp7_alert_native.num: rounded to two decimals (half away from zero, like numeric round), trailing zeros dropped, a decimal
 * comma and no thousands dots; '?' when there is no number. Exact on the decimal text. */
export function alertNumber(v: string | null): string {
  const m = v === null ? null : /^(-?)(\d+)(?:\.(\d+))?$/.exec(v)
  if (!m) return '?'
  const fraction = m[3] ?? '', hundredths = BigInt(m[2] + (fraction + '00').slice(0, 2)) + ((fraction[2] ?? '0') >= '5' ? 1n : 0n)
  const digits = hundredths.toString().padStart(3, '0'), cents = digits.slice(-2).replace(/0+$/, '')
  return `${m[1] && hundredths !== 0n ? '-' : ''}${digits.slice(0, -2)}${cents ? `,${cents}` : ''}`
}
/** The line item_line (alerts.sql) writes for a finished good in the WhatsApp message, cut to 120 characters like left(). */
export function fgReorderLine(d: FgReorderDetail): string {
  const line = `${d.productName}${d.sizeCode !== null ? ` ${d.sizeCode}` : ''}: sisa ${alertNumber(d.freePcs)} pcs, sedang diproduksi `
    + `${d.wipStatus === 'COMPLETE' ? `${alertNumber(d.wipPcs)} pcs` : 'belum diketahui'}, titik pesan ulang ${alertNumber(d.reorderPointPcs)} pcs`
  return Array.from(line).slice(0, 120).join('')
}
/** The line item_line (alerts.sql) writes for a fabric or accessory: the unit after every number (empty when there is none). */
export function materialReorderLine(d: MaterialReorderDetail): string {
  const unit = d.unitCode ?? '', q = (v: string) => `${alertNumber(v)} ${unit}`
  const line = d.kind === 'FABRIC_AT_REORDER_POINT' ? `${d.name}: sisa ${q(d.freeQty)}, dipesan ${q(d.onOrderQty)}, titik pesan ulang ${q(d.reorderPointQty)}`
    : `${d.name}: sisa ${q(d.freeQty)}, titik pesan ulang ${q(d.reorderPointQty)}`
  return Array.from(line).slice(0, 120).join('')
}
/** One line of the numbers of a system reminder, in plain words. */
export function alertSummary(a: SystemAlert): string {
  const d = a.detail
  if (d.kind === 'FG_AT_REORDER_POINT') return fgReorderLine(d)
  if (d.kind === 'FABRIC_AT_REORDER_POINT' || d.kind === 'ACCESSORY_AT_REORDER_POINT') return materialReorderLine(d)
  if (d.kind === 'FABRIC_BELOW_MINIMUM') {
    const unit = d.unitCode ? ` ${d.unitCode}` : ''
    return `Sisa ${num(d.qty)}${unit}, minimum ${num(d.minimumQty)}${unit}${d.materialSku ? ` · SKU ${d.materialSku}` : ''}`
  }
  if (d.kind === 'PRODUCTION_GAP' || d.kind === 'FABRIC_NEED') {
    const unit = d.kind === 'FABRIC_NEED' ? (d.unit ? ` ${d.unit}` : '') : ' pcs'
    const threshold = d.threshold === null ? '' : ` · ambang pengingat ${num(d.threshold)}${unit}`
    if (d.kind === 'PRODUCTION_GAP') {
      const grown = d.increasePcs !== null && Number(d.increasePcs) > 0 ? `, sudah bertambah ${num(d.increasePcs)} pcs` : ''
      const since = d.needSnapshotPcs === null ? '' : ` (di analisis ${num(d.needSnapshotPcs)} pcs${grown})`
      return `${d.label ?? 'Tanpa label'}: kurang ${num(d.needNowPcs ?? d.needSnapshotPcs)} pcs sekarang${since}${threshold}`
    }
    return `${d.materialName ?? 'Kain'} untuk ${d.label ?? 'tanpa label'}: perlu ${num(d.value)}${unit}${threshold}`
  }
  const who = a.partyNames.length ? ` · ${d.kind === 'AR_DUE' ? 'Pelanggan' : 'Supplier'} ${a.partyNames.join(', ')}` : ''
  const invoices = d.kind === 'AP_DUE' ? invoiceList(d.invoiceNumbers) : null
  return `${d.kind === 'AR_DUE' ? 'Nota' : 'Pembelian'} ${d.number ?? '?'} · sisa ${rupiah(d.amount)} · jatuh tempo ${dateOnly(d.dueDate)} (${dueState[d.state]})`
    + `${invoices ? ` · faktur ${invoices}` : ''}${who}`
}
/** "Data analisis per <WIB>, dicek ulang <WIB>" for the analysis kinds; null for the others. */
export function alertAnalysisLine(a: SystemAlert): string | null {
  const d = a.detail
  if (d.kind !== 'PRODUCTION_GAP' && d.kind !== 'FABRIC_NEED') return null
  return `Data analisis per ${formatCp6WibDateTime(d.dataAsOf)}${d.checkedAt ? `, dicek ulang ${formatCp6WibDateTime(d.checkedAt)}` : ', belum dicek ulang'}`
}
