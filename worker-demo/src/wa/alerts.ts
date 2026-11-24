import { isoDayText as day } from '../lib/contractPatterns'
import {
  arr,
  bool,
  count,
  decimal,
  decimalText,
  fail,
  hash,
  instant,
  keys,
  keysWithin,
  maybeCount,
  maybeDecimal,
  maybeInstant,
  maybePositive,
  maybeStr,
  maybeTick,
  maybeUuid,
  obj,
  oneOf,
  positive,
  str,
  uuidText,
} from './fields'
import type { Obj } from './fields'
import {
  WaResponseError,
  alertKinds,
  dispatchStatuses,
  isAnalysisKind,
  isMaterialReorderDetail,
  isObligationDetail,
  isObligationKind,
  isReorderKind,
  obligationKinds,
  outboxStates,
} from './model'
import type {
  AccessoryNeedDetail,
  AlertDetail,
  AlertKind,
  AlertSource,
  AlertWa,
  AnalysisRequest,
  AnalysisRun,
  AnalysisStatus,
  FgReorderDetail,
  MaterialReorderDetail,
  MaterialReorderFields,
  SystemAlert,
  SystemAlerts,
} from './model'

export function parseAnalysisStatus(v: unknown): AnalysisStatus {
  const o = obj(v, 'analisis'); keys(o, ['run', 'request', 'tick'], 'analisis')
  let run: AnalysisRun | null = null
  if (o.run !== null) {
    const r = obj(o.run, 'analisis')
    keys(r, ['run_id', 'data_as_of', 'phase', 'rule', 'next_offset', 'checked', 'still_open', 'closed', 'rule_off', 'error', 'started_at', 'updated_at', 'finished_at'], 'analisis')
    run = { runId: uuidText(r.run_id, 'analisis'), dataAsOf: instant(r.data_as_of, 'analisis'), phase: oneOf(r.phase, ['SET', 'CHECK', 'DONE', 'FAILED'] as const, 'tahap analisis'),
      rule: oneOf(r.rule, ['PRODUCTION_GAP', 'FABRIC_NEED', 'ACCESSORY_NEED'] as const, 'analisis'), nextOffset: count(r.next_offset, 'analisis'), checked: count(r.checked, 'analisis'),
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

function accessoryNeedDetail(d: Obj): AccessoryNeedDetail {
  if (typeof d.unit !== 'string' || d.unit.trim().length === 0) fail('kebutuhan aksesori')
  const what = 'kebutuhan aksesori'
  keys(d, ['run_id', 'data_as_of', 'checked_at', 'label', 'target_key', 'category_key', 'category_name', 'state', 'verdict', 'gross_state', 'gross_qty',
    'unit', 'installed_state', 'installed_proven', 'unused_allocated_state', 'unused_allocated_proven', 'additional_external_state', 'additional_external',
    'threshold_status', 'reason'], what)
  const targetKey = str(d.target_key, what), parts = targetKey.split(':')
  if (parts.length !== 2) fail(what)
  parts.forEach(p => uuidText(p, what))
  const categoryKey = str(d.category_key, what)
  if (categoryKey !== 'UNKNOWN_BOM') {
    const category = categoryKey.split(':')
    if (category.length !== 2 || category[0] !== 'ACCESSORY_CATEGORY') fail(what)
    uuidText(category[1], what)
  }
  const reason = oneOf(d.reason, ['INSTALLATION_AND_ELIGIBLE_UNUSED_SUPPLY_NOT_PROVEN', 'BOM_NOT_RECORDED', 'BOM_AMBIGUOUS', 'CATEGORY_UNAVAILABLE'] as const, what)
  const grossState = oneOf(d.gross_state, ['KNOWN', 'ASSUMED', 'UNKNOWN'] as const, what)
  const missingBom = reason === 'BOM_NOT_RECORDED' || reason === 'BOM_AMBIGUOUS'
  if (missingBom !== (categoryKey === 'UNKNOWN_BOM') || (missingBom && d.category_name !== null)) fail(what)
  if (grossState === 'UNKNOWN' ? d.gross_qty !== null
    : typeof d.gross_qty !== 'string' || d.gross_qty.length > 128 || !/^(0|[1-9][0-9]*)(\.[0-9]+)?$/.test(d.gross_qty) || !/[1-9]/.test(d.gross_qty)) fail(what)
  if ((reason === 'INSTALLATION_AND_ELIGIBLE_UNUSED_SUPPLY_NOT_PROVEN') !== (grossState !== 'UNKNOWN')) fail(what)
  for (const [state, value] of [['installed_state', 'installed_proven'], ['unused_allocated_state', 'unused_allocated_proven'], ['additional_external_state', 'additional_external']]) {
    if (d[state] !== 'UNKNOWN' || d[value] !== null) fail(what)
  }
  return { kind: 'ACCESSORY_NEED', runId: uuidText(d.run_id, what), dataAsOf: instant(d.data_as_of, what), checkedAt: instant(d.checked_at, what),
    label: str(d.label, what), targetKey, categoryKey, categoryName: maybeStr(d.category_name, what),
    state: oneOf(d.state, ['DATA_REVIEW'] as const, what), verdict: oneOf(d.verdict, ['REVIEW_REQUIRED_NOW'] as const, what),
    grossState, grossQty: d.gross_qty as string | null, unit: str(d.unit, what), installedState: 'UNKNOWN', installedProven: null,
    unusedAllocatedState: 'UNKNOWN', unusedAllocatedProven: null, additionalExternalState: 'UNKNOWN', additionalExternal: null,
    thresholdStatus: oneOf(d.threshold_status, ['NOT_EVALUATED_UNKNOWN'] as const, what), reason }
}

function detail(kind: AlertKind, v: unknown): AlertDetail {
  const d = obj(v, 'rincian')
  if (kind === 'RECOST_PENDING') {
    keys(d,['queue_id','entity_id','entity_type','po_number','status'],'antrean HPP')
    return {kind,queueId:uuidText(d.queue_id,'antrean HPP'),entityId:uuidText(d.entity_id,'sumber HPP'),entityType:str(d.entity_type,'jenis sumber'),
      poNumber:maybeStr(d.po_number,'nomor PO'),status:oneOf(d.status,['PENDING','RUNNING','FAILED'] as const,'status hitung ulang')}
  }
  if (kind === 'ACCESSORY_NEED') return accessoryNeedDetail(d)
  if (kind === 'FABRIC_BELOW_MINIMUM') {
    // D17-10: a fabric on the formula has the material shape (it carries material_type and basis); the others the minimum's.
    if ('material_type' in d || 'basis' in d) return materialReorderDetail(kind, d)
    keys(d, ['material_id', 'material_sku', 'material_name', 'unit_code', 'qty', 'minimum_qty'], 'rincian stok')
    return { kind, materialId: uuidText(d.material_id, 'rincian stok'), materialSku: maybeStr(d.material_sku, 'rincian stok'), materialName: str(d.material_name, 'rincian stok'),
      unitCode: maybeStr(d.unit_code, 'rincian stok'), qty: decimal(d.qty, 'rincian stok'), minimumQty: decimal(d.minimum_qty, 'rincian stok') }
  }
  if (kind === 'FG_AT_REORDER_POINT') return fgReorderDetail(d)
  if (kind === 'ACCESSORY_AT_REORDER_POINT') return materialReorderDetail(kind, d)
  if (isObligationKind(kind)) {
    keys(d, ['domain', 'source_id', 'label', 'remaining_state', 'remaining', 'due_date', 'state', 'reason', 'economic_state', 'as_of', 'source_hash'], 'rincian kewajiban')
    const domain = oneOf(d.domain, obligationKinds, 'jenis kewajiban')
    if (domain !== kind) fail('jenis kewajiban')
    const amountState = oneOf(d.remaining_state, ['KNOWN', 'UNKNOWN'] as const, 'nilai kewajiban')
    const amount = maybeDecimal(d.remaining, 'nilai kewajiban')
    const state = oneOf(d.state, ['ACTIVE', 'DATA_REVIEW'] as const, 'keadaan kewajiban')
    const dueDate = d.due_date === null ? null : typeof d.due_date === 'string' && day.test(d.due_date) ? d.due_date : fail('tanggal kewajiban')
    const economicState = oneOf(d.economic_state, ['OPEN', 'UNKNOWN'] as const, 'keadaan nilai kewajiban')
    if ((amountState === 'KNOWN') !== (amount !== null) || (amountState === 'KNOWN' && typeof d.remaining !== 'string')
      || (state === 'ACTIVE' && (dueDate === null || amountState !== 'KNOWN' || economicState !== 'OPEN'))) fail('nilai kewajiban')
    return { kind: domain, documentId: uuidText(d.source_id, 'dokumen kewajiban'), label: str(d.label, 'label kewajiban'),
      amountState, amount, dueDate, state, reason: str(d.reason, 'sebab kewajiban'), economicState,
      asOf: typeof d.as_of === 'string' && day.test(d.as_of) ? d.as_of : fail('tanggal sumber'), sourceHash: hash(d.source_hash, 'sidik sumber') }
  }
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
  const native = d.contract_version === 'cp7.fg-reorder-detail.v2'
  keys(d, ['root_id', 'size_id', 'sku', 'product_name', 'size_code', 'free_pcs', 'wip_pcs', 'wip_status', 'position_pcs', 'reorder_point_pcs', 'basis', 'daily_mean',
    'lead_days', 'lead_basis', 'buffer_mode', 'safety_pcs', 'service_level', ...(native ? ['contract_version', 'projection'] : [])], what)
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
  if (native) {
    const p = obj(d.projection, what)
    keys(p, ['basis', 'analysis_at', 'candidate_pcs', 'conditional_position_pcs', 'threshold_source', 'candidate_mutes_alert'], what)
    if (p.basis !== 'GLOBAL_PROJECTED_GOOD_ON_TIME' || p.candidate_mutes_alert !== false || r.wipStatus === 'NOT_READ') fail(what)
    const whole = (v: unknown) => typeof v === 'string' && /^(0|[1-9]\d*)$/.test(v) ? v : fail(what)
    const maybeWhole = (v: unknown) => v === null ? null : whole(v)
    const projection: NonNullable<FgReorderDetail['projection']> = {
      analysisAt: maybeInstant(p.analysis_at, what), candidatePcs: maybeWhole(p.candidate_pcs), conditionalPositionPcs: maybeWhole(p.conditional_position_pcs),
      thresholdSource: oneOf(p.threshold_source, ['PLANNING_PROFILE', 'NATIVE_HISTORY_WITH_EXISTING_DEFAULTS', 'PROFILE_UNAVAILABLE'] as const, what),
    }
    whole(r.freePcs); whole(r.reorderPointPcs); maybeWhole(r.wipPcs); maybeWhole(r.positionPcs)
    if (complete !== (projection.analysisAt !== null) || (projection.candidatePcs === null) !== (projection.conditionalPositionPcs === null)
      || (!complete && projection.candidatePcs !== null)
      || (complete && BigInt(r.positionPcs!) !== BigInt(r.freePcs) + BigInt(r.wipPcs!))
      || (projection.candidatePcs !== null && BigInt(projection.conditionalPositionPcs!) !== BigInt(r.positionPcs!) + BigInt(projection.candidatePcs))
      || BigInt(r.reorderPointPcs) === 0n || BigInt(r.positionPcs ?? r.freePcs) > BigInt(r.reorderPointPcs)) fail(what)
    r.projection = projection
  }
  return r
}

// material_alert_row writes all thirteen keys (owner D17-10). A fabric in this shape is on the formula only (FABRIC_BELOW_MINIMUM;
// a fabric with a minimum has the minimum's shape): basis FORMULA with its lama kirim, cadangan and tingkat layanan. An
// accessory is reminded by its minimum only: basis MANUAL (lama kirim optional) or ESTIMATE (with its lama kirim, D17-12), no
// cadangan or tingkat layanan, nothing on order.
function materialReorderDetail(kind: 'FABRIC_BELOW_MINIMUM' | 'ACCESSORY_AT_REORDER_POINT', d: Record<string, unknown>): MaterialReorderDetail {
  const what = 'rincian bahan'
  keys(d, ['material_id', 'material_type', 'sku', 'name', 'unit_code', 'free_qty', 'on_order_qty', 'reorder_point_qty', 'basis', 'daily_mean', 'lead_days',
    'safety_qty', 'service_level'], what)
  const text = (v: unknown) => typeof v === 'string' && decimalText.test(v) ? v : fail(what)
  const maybeText = (v: unknown) => v === null ? null : text(v)
  const fields: MaterialReorderFields = { materialId: uuidText(d.material_id, what), sku: str(d.sku, what), name: str(d.name, what),
    unitCode: maybeStr(d.unit_code, what), freeQty: text(d.free_qty), onOrderQty: text(d.on_order_qty), reorderPointQty: text(d.reorder_point_qty),
    dailyMean: maybeText(d.daily_mean), leadDays: maybeText(d.lead_days), safetyQty: maybeText(d.safety_qty),
    serviceLevel: d.service_level === null ? null : oneOf(d.service_level, ['0.90', '0.95', '0.99'] as const, what) }
  if (kind === 'FABRIC_BELOW_MINIMUM') {
    if (d.material_type !== 'FABRIC' || d.basis !== 'FORMULA' || fields.safetyQty === null || fields.serviceLevel === null || fields.leadDays === null
      || fields.dailyMean === null) fail(what)
    return { kind, materialType: 'FABRIC', basis: 'FORMULA', ...fields }
  }
  const basis = d.basis === 'MANUAL' || d.basis === 'ESTIMATE' ? d.basis : fail(what)
  if (d.material_type !== 'ACCESSORY' || fields.safetyQty !== null || fields.serviceLevel !== null || (basis === 'ESTIMATE' && fields.leadDays === null)
    || Number(fields.onOrderQty) !== 0) fail(what)
  return { kind, materialType: 'ACCESSORY', basis, ...fields }
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
  if (visible.has('ACCESSORY_NEED') && !visible.has('PRODUCTION_GAP')) fail('jenis')
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
    if ((isAnalysisKind(kind) || isReorderKind(kind) || isMaterialReorderDetail(a.detail)) && a.partyNames.length > 0) fail('nama pihak')
    // A finished-goods alert is keyed by its item (target_key root:size), a material alert by the material.
    if (a.detail.kind === 'FG_AT_REORDER_POINT' && a.subjectKey !== `${a.detail.rootId}:${a.detail.sizeId}`) fail('pengingat')
    if (isMaterialReorderDetail(a.detail) && a.subjectKey !== a.detail.materialId) fail('pengingat')
    if (a.detail.kind==='RECOST_PENDING'&&a.subjectKey!==a.detail.queueId)fail('antrean HPP')
    if (isObligationDetail(a.detail) && a.subjectKey !== `${kind === 'OPENING_AR' ? 'AR_DUE' : 'AP_DUE'}:${kind}:${a.detail.documentId}`) fail('pengingat')
    if (a.detail.kind === 'ACCESSORY_NEED' && a.subjectKey !== `ACCESSORY_NEED:${a.detail.targetKey}:${a.detail.categoryKey}`) fail('pengingat')
    return a
  })
  if (rows.length > 500 || new Set(rows.map(r => r.id)).size !== rows.length
    || new Set(rows.map(r => `${r.kind}\u0000${r.subjectKey}\u0000${r.episode}`)).size !== rows.length
    || new Set(rows.filter(r => r.state === 'OPEN').map(r => `${r.kind}\u0000${r.subjectKey}`)).size !== rows.filter(r => r.state === 'OPEN').length) fail('daftar')
  return { readAt: instant(w.read_at, 'waktu baca'), configured: bool(w.configured, 'pengaturan'), collector: maybeTick(w.collector, 'pengumpul'), analysis, kinds, rows }
}
