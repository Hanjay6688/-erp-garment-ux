import type { Json } from './types/database.preconnect'
import type { ProductionEnvelope } from './productionRecovery'

// D14-14 gap G1: SELESAI DIJAHIT from the connected WIP & Sewing screen (like the UX demo). Closed parsers for the
// workspace and the committed outcome of scripts/cp7-src/cutting-correction/sewing.sql.
export type SewingBlocker = { kind: string; id: string | null; label: string | null; status: string | null }
export type SewingComponent = { code: string; name: string; rate: number; postedQty: number }
// Before the first record: the rates the Native snapshot would take now (estimate; the record commits them at the sewing time).
export type SewingRate = { code: string; name: string; rate: number }
// Owner D15-3: rates are dated. Each segment [from, to) holds the rates the Native snapshot takes at a sewing time inside it
// (from the pickup up to now), so the screen shows the rates of the time it sends.
export type SewingRateSegment = { from: string; to: string | null; complete: boolean; rates: SewingRate[] }
// Sol R2-10: a Potongan bound to SKU waves (BF commercial ranges) is recorded per SKU at that SKU's rates. Per SKU: its sizes,
// pieces cut, pieces already paid, what it can still take and, once pinned for the PO, its rates; before that each segment
// [from, to) holds the rates every SKU gets at a sewing time inside it.
export type SewingWaveSku = { skuId: string; sku: string; color: string; sizes: string[]; capacity: number; maxQty: number; postedQty: number; rates: SewingRate[] }
export type SewingWaveSegment = { from: string; to: string | null; complete: boolean; skus: { skuId: string; rates: SewingRate[] }[] }
export type SewingWave = { ratesCommitted: boolean; skus: SewingWaveSku[]; timeline: SewingWaveSegment[] }
export type SewingEvent = {
  id: string; number: string; qtyPcs: number; physicalAt: string; rowVersion: number; reason: string
  workCompletionId: string; workStatus: string | null; reversed: boolean; wageAmount: number; inPayroll: boolean
  inActivePool: boolean; cancelBlocker: string | null; sku: string | null
}
export type SewingWorkspace = {
  groupId: string; groupVersion: string; number: string; poId: string; poNumber: string; poStatus: string
  contractorId: string | null; contractorName: string | null; pickedUpAt: string | null
  effectivePcs: number; sewnPcs: number; maxQty: number; readyUnsentPcs: number; laundryDraftPcs: number
  ratesCommitted: boolean; components: SewingComponent[]; ratePreview: SewingRate[]; rateTimeline: SewingRateSegment[]; events: SewingEvent[]; canCancel: boolean
  reviewToken: string; eligible: boolean; blockers: SewingBlocker[]; wave: SewingWave | null
}
export type SewingOutcome = {
  action: 'RECORD' | 'RECORD_WAVE' | 'REVERSE'; groupId: string; number: string; qtyPcs: number; wageAmount: number | null
  sewnPcs: number; readyUnsentPcs: number; maxQty: number; lines: { sku: string; qtyPcs: number; wageAmount: number }[]
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
function rate(v: unknown): SewingRate { const c = record(v); keys(c, ['code', 'name', 'rate']); return { code: text(c.code), name: text(c.name), rate: money(c.rate) } }
function rates(v: unknown) { if (!Array.isArray(v)) fail(); return v.map(rate) }
function contiguous(segments: { from: string; to: string | null }[]) {
  for (let i = 1; i < segments.length; i++) if (segments[i - 1].to !== segments[i].from) fail()
}

function parseWave(value: unknown): SewingWave {
  const r = record(value); keys(r, ['rates_committed', 'skus', 'timeline'])
  if (!Array.isArray(r.skus) || !Array.isArray(r.timeline) || r.skus.length === 0) fail()
  const skus = r.skus.map(v => {
    const k = record(v); keys(k, ['sku_id', 'sku', 'color', 'sizes', 'capacity', 'max_qty', 'posted_qty', 'rates'])
    if (!Array.isArray(k.sizes) || k.sizes.length === 0) fail()
    const sku = { skuId: id(k.sku_id), sku: text(k.sku), color: text(k.color), sizes: k.sizes.map(text), capacity: count(k.capacity),
      maxQty: count(k.max_qty), postedQty: count(k.posted_qty), rates: rates(k.rates) }
    if (sku.maxQty > sku.capacity || sku.postedQty > sku.capacity) fail()
    return sku
  })
  const ids = skus.map(k => k.skuId).sort()
  if (new Set(ids).size !== ids.length) fail()
  const timeline = r.timeline.map(v => {
    const t = record(v); keys(t, ['from', 'to', 'complete', 'skus'])
    if (!Array.isArray(t.skus)) fail()
    const per = t.skus.map(x => { const y = record(x); keys(y, ['sku_id', 'rates']); return { skuId: id(y.sku_id), rates: rates(y.rates) } })
    const complete = bool(t.complete)
    // Each segment speaks for every SKU of this Potongan; a complete one has rates for each.
    if (per.map(x => x.skuId).sort().join('|') !== ids.join('|') || (complete && per.some(x => x.rates.length === 0))) fail()
    return { from: instant(t.from), to: t.to === null ? null : instant(t.to), complete, skus: per }
  })
  contiguous(timeline)
  const ratesCommitted = bool(r.rates_committed)
  if (ratesCommitted && (timeline.length > 0 || skus.some(k => k.rates.length === 0))) fail()
  return { ratesCommitted, skus, timeline }
}

export function parseSewingWorkspace(value: unknown, groupId: string): SewingWorkspace {
  const r = record(value)
  keys(r, ['contract_version', 'group_id', 'group_version', 'number', 'po_id', 'po_number', 'po_status', 'contractor_id', 'contractor_name',
    'picked_up_at', 'effective_pcs', 'sewn_pcs', 'max_qty', 'ready_unsent_pcs', 'laundry_draft_pcs', 'rates_committed', 'components',
    'rate_preview', 'rate_timeline', 'events', 'can_cancel', 'review_token', 'eligible', 'blockers', 'business_DML', 'wave'])
  if (r.contract_version !== 'cp7.sewing-completion-workspace.v1' || r.business_DML !== false || r.group_id !== groupId
    || typeof r.group_version !== 'string' || !/^[1-9][0-9]{0,18}$/.test(r.group_version)
    || typeof r.review_token !== 'string' || !/^[a-f0-9]{32}$/.test(r.review_token)
    || !Array.isArray(r.components) || !Array.isArray(r.rate_preview) || !Array.isArray(r.rate_timeline) || !Array.isArray(r.events) || !Array.isArray(r.blockers)) fail()
  const components = r.components.map(v => {
    const c = record(v); keys(c, ['code', 'name', 'rate', 'posted_qty'])
    return { code: text(c.code), name: text(c.name), rate: money(c.rate), postedQty: count(c.posted_qty) }
  })
  const ratePreview = r.rate_preview.map(rate)
  const rateTimeline = r.rate_timeline.map(v => {
    const t = record(v); keys(t, ['from', 'to', 'complete', 'rates'])
    const segmentRates = rates(t.rates), complete = bool(t.complete)
    if (complete && segmentRates.length === 0) fail()
    return { from: instant(t.from), to: t.to === null ? null : instant(t.to), complete, rates: segmentRates }
  })
  contiguous(rateTimeline)
  const events = r.events.map(v => {
    const e = record(v)
    keys(e, ['id', 'number', 'qty_pcs', 'physical_at', 'row_version', 'reason', 'work_completion_id', 'work_status', 'reversed', 'wage_amount',
      'in_payroll', 'in_active_pool', 'cancel_blocker', 'sku'])
    return {
      id: id(e.id), number: text(e.number), qtyPcs: count(e.qty_pcs), physicalAt: instant(e.physical_at), rowVersion: count(e.row_version),
      reason: text(e.reason), workCompletionId: id(e.work_completion_id), workStatus: nullableText(e.work_status), reversed: bool(e.reversed),
      wageAmount: money(e.wage_amount), inPayroll: bool(e.in_payroll), inActivePool: bool(e.in_active_pool), cancelBlocker: nullableText(e.cancel_blocker),
      sku: nullableText(e.sku),
    }
  })
  const blockers = r.blockers.map(v => {
    const b = record(v)
    return { kind: text(b.kind), id: b.id === undefined || b.id === null ? null : text(b.id), label: nullableText(b.label), status: nullableText(b.status) }
  })
  const eligible = bool(r.eligible), maxQty = count(r.max_qty), wave = r.wave === null ? null : parseWave(r.wave)
  if (eligible !== (blockers.length === 0) || (eligible && maxQty === 0)) fail()
  if (wave) {
    // The base components are not a wave Potongan's wage: the server sends none, and the totals follow the SKUs.
    if (components.length > 0 || ratePreview.length > 0 || rateTimeline.length > 0 || bool(r.rates_committed) !== wave.ratesCommitted
      || maxQty > wave.skus.reduce((n, k) => n + k.maxQty, 0) || (eligible && !wave.ratesCommitted && !wave.timeline.some(t => t.complete))) fail()
  } else if (bool(r.rates_committed) !== (components.length > 0)
    || (components.length > 0 && (ratePreview.length > 0 || rateTimeline.length > 0))
    || (eligible && components.length === 0 && !rateTimeline.some(t => t.complete))) fail()
  const pickedUpAt = r.picked_up_at === null ? null : instant(r.picked_up_at)
  return {
    groupId, groupVersion: r.group_version, number: text(r.number), poId: id(r.po_id), poNumber: text(r.po_number), poStatus: text(r.po_status),
    contractorId: r.contractor_id === null ? null : id(r.contractor_id), contractorName: nullableText(r.contractor_name), pickedUpAt,
    effectivePcs: count(r.effective_pcs), sewnPcs: count(r.sewn_pcs), maxQty, readyUnsentPcs: count(r.ready_unsent_pcs),
    laundryDraftPcs: count(r.laundry_draft_pcs), ratesCommitted: bool(r.rates_committed), components, ratePreview, rateTimeline, events, canCancel: bool(r.can_cancel),
    reviewToken: r.review_token, eligible, blockers, wave,
  }
}

// The rates the first record will lock for a sewing time: the segment holding it, or null when no complete set applies then.
export function ratesAt(w: SewingWorkspace, iso: string | null): SewingRate[] | null {
  if (iso === null) return null
  const t = new Date(iso).getTime()
  const seg = w.rateTimeline.find(s => new Date(s.from).getTime() <= t && (s.to === null || t < new Date(s.to).getTime()))
  return seg && seg.complete ? seg.rates : null
}

// Sol R2-10: per SKU of a wave Potongan, the rates the first record locks for a sewing time (the SKU's own once pinned).
export function waveRatesAt(w: SewingWorkspace, iso: string | null): Map<string, SewingRate[]> | null {
  if (!w.wave) return null
  if (w.wave.ratesCommitted) return new Map(w.wave.skus.map(k => [k.skuId, k.rates]))
  if (iso === null) return null
  const t = new Date(iso).getTime()
  const seg = w.wave.timeline.find(s => new Date(s.from).getTime() <= t && (s.to === null || t < new Date(s.to).getTime()))
  return seg && seg.complete ? new Map(seg.skus.map(k => [k.skuId, k.rates])) : null
}

// The SKU lines with pieces entered, in the screen's order; null while any entry is not a whole number within its SKU, or the
// total is nothing or more than the Potongan can take.
export function waveLines(w: SewingWorkspace, qty: Record<string, string>): { skuId: string; qty: string }[] | null {
  if (!w.wave) return null
  const lines = w.wave.skus.filter(k => (qty[k.skuId] ?? '') !== '').map(k => ({ skuId: k.skuId, qty: qty[k.skuId], max: k.maxQty }))
  if (lines.length === 0 || lines.some(l => !/^[1-9][0-9]{0,6}$/.test(l.qty) || Number(l.qty) > l.max)
    || lines.reduce((n, l) => n + Number(l.qty), 0) > w.maxQty) return null
  return lines.map(({ skuId, qty: q }) => ({ skuId, qty: q }))
}

export function sewingWavePayload(w: SewingWorkspace, qty: Record<string, string>, physicalAtIso: string | null, reason: string): Json {
  const why = reason.trim(), lines = waveLines(w, qty)
  if (!w.eligible || !w.wave || !lines || !physicalAtIso || why.length < 5 || why.length > 1000) fail()
  return { action: 'RECORD_WAVE', group_id: w.groupId, lines: lines.map(l => ({ sku_id: l.skuId, qty_pcs: l.qty })), physical_at: physicalAtIso,
    review_token: w.reviewToken, change_reason: why }
}

export function sewingRecordPayload(w: SewingWorkspace, qty: string, physicalAtIso: string | null, reason: string): Json {
  const why = reason.trim(), n = Number(qty)
  if (!w.eligible || w.wave || !/^[1-9][0-9]{0,6}$/.test(qty) || n > w.maxQty || !physicalAtIso || why.length < 5 || why.length > 1000) fail()
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
  const action = p.action === 'RECORD' ? 'RECORD' : p.action === 'RECORD_WAVE' ? 'RECORD_WAVE' : p.action === 'REVERSE' ? 'REVERSE' : fail()
  if (envelope.action !== (action === 'REVERSE' ? 'CANCEL_SEWING' : 'RECORD_SEWING') || r.contract_version !== 'cp7.sewing-completion-outcome.v1'
    || r.kind !== 'COMMITTED_OUTCOME' || r.action !== action || r.request_id !== envelope.id || r.group_id !== p.group_id) fail()
  const x = record(r.result)
  let lines: SewingOutcome['lines'] = []
  if (action === 'RECORD_WAVE') {
    keys(x, ['lines', 'qty_pcs', 'wage_amount', 'sewn_pcs', 'ready_unsent_pcs', 'max_qty'])
    const sent = Array.isArray(p.lines) ? p.lines.map(record) : fail()
    if (!Array.isArray(x.lines) || x.lines.length !== sent.length) fail()
    lines = x.lines.map((v, i) => {
      const l = record(v); keys(l, ['sku_id', 'sku', 'work_completion_id', 'sewing_event_id', 'qty_pcs', 'wage_amount', 'components'])
      if (l.sku_id !== sent[i].sku_id || String(l.qty_pcs) !== sent[i].qty_pcs || count(l.components) < 1) fail()
      id(l.work_completion_id); id(l.sewing_event_id)
      return { sku: text(l.sku), qtyPcs: count(l.qty_pcs), wageAmount: money(l.wage_amount) }
    })
    // The totals are the sum of the lines (the wage to the cent).
    if (count(x.qty_pcs) !== lines.reduce((n, l) => n + l.qtyPcs, 0)
      || Math.round(money(x.wage_amount) * 100) !== lines.reduce((n, l) => n + Math.round(l.wageAmount * 100), 0)) fail()
    return { action, groupId: id(r.group_id), number: text(r.number), qtyPcs: count(x.qty_pcs), wageAmount: money(x.wage_amount),
      sewnPcs: count(x.sewn_pcs), readyUnsentPcs: count(x.ready_unsent_pcs), maxQty: count(x.max_qty), lines }
  }
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
    sewnPcs: count(x.sewn_pcs), readyUnsentPcs: count(x.ready_unsent_pcs), maxQty: count(x.max_qty), lines,
  }
}

const blockerKinds: Record<string, string> = {
  NO_POSTED_PICKUP: 'Potongan ini belum dibagi ke mandor (Bagi Potongan belum dicatat).',
  CONTRACTOR_NOT_MANDOR: 'Penerima Bagi Potongan bukan mandor jahit.',
  CONTRACTOR_MISMATCH: 'Mandor di PO berbeda dengan mandor yang menerima potongan ini.',
  PO_STATE: 'Production Order sedang ditahan, sudah selesai, atau dibatalkan.',
  NOTHING_TO_SEW: 'Semua potongan sudah tercatat selesai dijahit.',
  NO_WORK_RATE: 'Tarif kerja (BOM kerja) untuk model PO ini belum ada, jadi upah mandor belum bisa dihitung. Isi komponen kerja model dan tarif mandornya di Master Data → Mandor → Tarif upah mandor.',
  NO_WAVE_RATE: 'Belum ada tarif lengkap untuk setiap SKU wave potongan ini sejak diambil mandor. Periksa komponen kerja model dan tarif mandornya (Master Data → Mandor → Tarif upah mandor) serta versi SKU yang memuat ukurannya.',
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
