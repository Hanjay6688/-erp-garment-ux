import { isUnansweredFailure, normalizeClientError } from './lib/clientError'
import {
  FgReorderResponseError, MIN_COUNTED_DAYS, REASON_MAX, formatReorderQty, formatReorderUpTo2, formatReorderWhole, reorderWire as w, servicePercent,
  type ReorderFilter, type ReorderRun, type ReorderSettings, type ServiceLevel,
} from './fgReorderContract'

// SS-2 (fabric) and SS-3 (accessories), owner D17-9: closed parsers for the three public RPCs of scripts/cp7-src/stock-formula/
// materials.sql (material_workspace, material_refresh, save_material). The same rules and words as the finished goods
// (fgReorderContract.ts, shared through reorderWire): an unknown or missing key, a wrong type or a fact the server never
// writes is refused with "Respons titik pesan ulang tidak cocok"; quantities stay decimal text in the material's own unit.
// Owner D17-10 ("aksesoris pake batas minimum manual aja ... rumus ga penting"): an accessory never has the formula. Owner
// D17-12 ("slot untuk diisi aja in app"): the app works its minimum out from the owner's own numbers per accessory (MOQ, lama
// kirim dari Cina, perkiraan pemakaian per bulan, cadangan): ESTIMATE = ceil to 0.01 of usage_month x (lead + buffer) / 30, exact.
// A minimum typed directly wins (MANUAL); neither: NOT_SET (NO_MINIMUM_OR_ESTIMATE). Its measured usage per day is shown next
// to the estimate, never used in the number. Fabric rows are unchanged (the four estimate keys are always null there).
export type MaterialType = 'FABRIC' | 'ACCESSORY'
export type MaterialBasis = 'MANUAL' | 'FORMULA' | 'ESTIMATE' | 'NOT_ENOUGH_DATA' | 'NO_USAGE' | 'NOT_SET'
export type MaterialReason = 'NO_POSTED_USAGE_IN_WINDOW' | 'FEWER_THAN_14_COUNTED_DAYS' | 'NO_LEAD_TIME' | 'NO_MINIMUM_OR_ESTIMATE'
export type MaterialManualSource = 'FABRIC_MINIMUM' | 'ACCESSORY_MANUAL'
/** The list filters of erp_cp7_get_material_reorder_v1: the finished goods' four, ESTIMATE and NOT_SET (accessories). */
export type MaterialFilter = ReorderFilter | 'ESTIMATE' | 'NOT_SET'
/** The filters each screen offers: an accessory has no formula, so no "not enough data"; a fabric has no estimate or "not set". */
export const materialFilters: Record<MaterialType, readonly MaterialFilter[]> = {
  FABRIC: ['ALL', 'AT_OR_BELOW', 'MANUAL', 'NOT_ENOUGH_DATA'], ACCESSORY: ['ALL', 'AT_OR_BELOW', 'MANUAL', 'ESTIMATE', 'NOT_SET'],
}
/** One row of cp7_stock_formula.material_evaluations. */
export type MaterialRow = {
  materialId: string; materialType: MaterialType; sku: string; name: string; unitCode: string | null; freeQty: string; onOrderQty: string; usageQty: string
  countedDays: number; useDays: number; dailyMean: string | null; dailySd: string | null; leadDays: string | null; settingRevision: number | null; z: string
  safetyQty: string | null; formulaPoint: string | null; manualPoint: string | null; manualSource: MaterialManualSource | null; point: string | null
  /** D17-12, accessories only: the owner's MOQ, monthly use and buffer days, and the minimum worked out from them. */
  moq: string | null; usageMonthQty: string | null; bufferDays: string | null; estimatePoint: string | null
  basis: MaterialBasis; reason: MaterialReason | null; state: 'AT_OR_BELOW' | 'ABOVE' | 'NO_POINT'; changedAt: string
}
export type MaterialCounts = {
  items: number; atOrBelow: number; manual: number; formula: number; estimate: number; notEnoughData: number; noUsage: number; notSet: number
}
/** p_query of erp_cp7_get_material_reorder_v1, sent as it is. */
export type MaterialQuery = { material_type: MaterialType; q: string; filter: MaterialFilter; offset: number; limit: number }
export type MaterialWorkspace = {
  materialType: MaterialType; readAt: string; settings: ReorderSettings; run: ReorderRun | null; canManage: boolean; counts: MaterialCounts
  page: { rows: MaterialRow[]; total: string; offset: number; limit: number; nextOffset: number | null }
}
/** lead_days is the lama kirim (of a fabric, or "dari Cina" of an accessory); manual_point the accessory's typed minimum (always
 * null for a fabric); moq, usage_month_qty and buffer_days are sent for an accessory only, always all of them (null when empty). */
export type MaterialPayload = {
  material_id: string; expected_revision: number; lead_days: string | null; manual_point: string | null; reason: string
  moq?: string | null; usage_month_qty?: string | null; buffer_days?: string | null
}
export type MaterialSaveResult = { replay: boolean; materialId: string; revision: number; evaluation: MaterialRow | null }
/** The form of one material: text as typed (a decimal comma is accepted), empty = none. A fabric fills `lead` only; an
 * accessory `lead` (dari Cina), `moq`, `usageMonth`, `buffer` and `manual` (the typed minimum). */
export type MaterialDraft = { lead: string; manual: string; moq: string; usageMonth: string; buffer: string; reason: string }

const fail = (what: string): never => w.fail(what)
const rowKeys = ['material_id', 'material_type', 'sku', 'name', 'unit_code', 'free_qty', 'on_order_qty', 'usage_qty', 'counted_days', 'use_days', 'daily_mean',
  'daily_sd', 'lead_days', 'setting_revision', 'z', 'safety_qty', 'formula_point', 'manual_point', 'manual_source', 'point', 'moq', 'usage_month_qty',
  'buffer_days', 'estimate_point', 'basis', 'reason', 'state', 'changed_at'] as const
const bases = { FABRIC: ['MANUAL', 'FORMULA', 'NOT_ENOUGH_DATA', 'NO_USAGE'], ACCESSORY: ['MANUAL', 'ESTIMATE', 'NOT_SET'] } as const
const reasons = { FABRIC: ['NO_POSTED_USAGE_IN_WINDOW', 'FEWER_THAN_14_COUNTED_DAYS', 'NO_LEAD_TIME'], ACCESSORY: ['NO_MINIMUM_OR_ESTIMATE'] } as const
const canonical = (v: string) => {
  const [i, f = ''] = v.split('.'), frac = f.replace(/0+$/, '')
  return `${i.replace(/^0+(?=\d)/, '')}${frac ? `.${frac}` : ''}`
}
const sameDecimal = (a: string | null, b: string | null) => a === null || b === null ? a === b : canonical(a) === canonical(b)
/** Exact order of two decimal texts (-1, 0, 1), without rounding through floating point. */
function compareDecimal(a: string, b: string): number {
  const places = Math.max((a.split('.')[1] ?? '').length, (b.split('.')[1] ?? '').length)
  const scaled = (v: string) => { const [i, f = ''] = v.replace('-', '').split('.'), n = BigInt(i + f.padEnd(places, '0')); return v.startsWith('-') ? -n : n }
  const x = scaled(a), y = scaled(b)
  return x < y ? -1 : x > y ? 1 : 0
}
// Exact decimal arithmetic on non-negative decimal text (BigInt with a scale), never through floating point.
const fixed = (v: string) => { const [i, f = ''] = v.split('.'); return { n: BigInt(i + f), scale: f.length } }
const pow10 = (k: number) => 10n ** BigInt(k)
/** D17-12: the accessory minimum from the owner's numbers, exactly as the owner's rule says: (usage per month / 30) x (lead
 * days + buffer days), rounded up to 0.01. Decimal text in, decimal text out (no trailing zeros). */
export function accessoryEstimatePoint(usageMonth: string, leadDays: string, bufferDays: string): string {
  const u = fixed(usageMonth), l = fixed(leadDays), b = fixed(bufferDays), scale = Math.max(l.scale, b.scale)
  const days = l.n * pow10(scale - l.scale) + b.n * pow10(scale - b.scale)
  const numerator = u.n * days * 100n, denominator = 30n * pow10(u.scale + scale)
  const cents = (numerator + denominator - 1n) / denominator
  return canonical(`${cents / 100n}.${String(cents % 100n).padStart(2, '0')}`)
}
/** How many days the MOQ lasts at the owner's monthly use (MOQ / (usage / 30)), rounded down; information only. */
export function moqDays(moq: string, usageMonth: string): string {
  const m = fixed(moq), u = fixed(usageMonth), scale = Math.max(m.scale, u.scale)
  return String((m.n * pow10(scale - m.scale) * 30n) / (u.n * pow10(scale - u.scale)))
}
const positive = (v: string) => compareDecimal(v, '0') > 0
function row(v: unknown, type: MaterialType): MaterialRow {
  const what = 'bahan', o = w.obj(v, what); w.keys(o, rowKeys, what)
  const r: MaterialRow = {
    materialId: w.uuidText(o.material_id, what), materialType: w.oneOf(o.material_type, ['FABRIC', 'ACCESSORY'] as const, what), sku: w.str(o.sku, what),
    name: w.str(o.name, what), unitCode: w.maybeStr(o.unit_code, what), freeQty: w.decimal(o.free_qty, what), onOrderQty: w.decimal(o.on_order_qty, what),
    usageQty: w.decimal(o.usage_qty, what), countedDays: w.count(o.counted_days, what), useDays: w.count(o.use_days, what),
    dailyMean: w.maybeDecimal(o.daily_mean, what), dailySd: w.maybeDecimal(o.daily_sd, what), leadDays: w.maybeDecimal(o.lead_days, what),
    settingRevision: w.maybeCount(o.setting_revision, what), z: w.decimal(o.z, what), safetyQty: w.maybeDecimal(o.safety_qty, what),
    formulaPoint: w.maybeDecimal(o.formula_point, what), manualPoint: w.maybeDecimal(o.manual_point, what),
    manualSource: o.manual_source === null ? null : w.oneOf(o.manual_source, ['FABRIC_MINIMUM', 'ACCESSORY_MANUAL'] as const, what),
    point: w.maybeDecimal(o.point, what), moq: w.maybeDecimal(o.moq, what), usageMonthQty: w.maybeDecimal(o.usage_month_qty, what),
    bufferDays: w.maybeDecimal(o.buffer_days, what), estimatePoint: w.maybeDecimal(o.estimate_point, what),
    basis: w.oneOf<MaterialBasis>(o.basis, bases[type], 'dasar angka'),
    reason: o.reason === null ? null : w.oneOf<MaterialReason>(o.reason, reasons[type], what),
    state: w.oneOf(o.state, ['AT_OR_BELOW', 'ABOVE', 'NO_POINT'] as const, 'status'),
    changedAt: w.instant(o.changed_at, what),
  }
  const pointed = r.basis === 'MANUAL' || r.basis === 'FORMULA' || r.basis === 'ESTIMATE'
  // The table checks and compute_materials(): a point exactly for MANUAL, FORMULA and ESTIMATE, the manual number exactly with its
  // source (the fabric's minimum or the accessory's typed minimum), and the point is that number, the formula's or the estimate.
  if ((r.point !== null) !== pointed || (r.manualSource === null) !== (r.manualPoint === null) || (r.manualSource !== null) !== (r.basis === 'MANUAL')
    || (r.basis === 'MANUAL' && r.point !== r.manualPoint) || (r.basis === 'FORMULA' && r.point !== r.formulaPoint)) fail('titik pesan ulang')
  if (pointed ? r.reason !== null : r.basis === 'NO_USAGE' ? r.reason !== 'NO_POSTED_USAGE_IN_WINDOW'
    : r.basis === 'NOT_SET' ? r.reason !== 'NO_MINIMUM_OR_ESTIMATE' : r.reason !== 'FEWER_THAN_14_COUNTED_DAYS' && r.reason !== 'NO_LEAD_TIME') fail('alasan')
  if ((r.basis === 'FORMULA' && (r.leadDays === null || r.safetyQty === null)) || (r.reason === 'NO_LEAD_TIME' && r.leadDays !== null)) fail('lama kirim')
  if ((r.state === 'NO_POINT') !== (r.point === null || Number(r.point) <= 0)) fail('status')
  // A fabric never carries the accessory estimate (D17-12).
  if (type === 'FABRIC' && (r.moq !== null || r.usageMonthQty !== null || r.bufferDays !== null || r.estimatePoint !== null)) fail(what)
  if (type === 'ACCESSORY') {
    // D17-10: no formula. D17-12: the estimate is there exactly when its three numbers are, and it is the owner's rule worked
    // out again here exactly; it is the point when no minimum is typed (a typed minimum wins).
    if (r.safetyQty !== null || r.formulaPoint !== null) fail('batas minimum')
    const inputs = r.usageMonthQty !== null && r.leadDays !== null && r.bufferDays !== null
    if ((r.moq !== null && !positive(r.moq)) || (r.usageMonthQty !== null && !positive(r.usageMonthQty)) || (r.leadDays !== null && !positive(r.leadDays))
      || (r.bufferDays !== null && compareDecimal(r.bufferDays, '0') < 0) || inputs !== (r.estimatePoint !== null)
      || (inputs && !sameDecimal(r.estimatePoint, accessoryEstimatePoint(r.usageMonthQty!, r.leadDays!, r.bufferDays!)))) fail('hitungan')
    if ((r.basis === 'ESTIMATE') !== (r.manualSource === null && r.estimatePoint !== null) || (r.basis === 'ESTIMATE' && !sameDecimal(r.point, r.estimatePoint)))
      fail('titik pesan ulang')
    // At or under its minimum exactly when the stock in the warehouse is not above it (nothing is on order for an accessory).
    if (r.point !== null && Number(r.point) > 0 && (r.state === 'AT_OR_BELOW') !== (compareDecimal(r.freeQty, r.point) <= 0)) fail('status')
  }
  if (r.materialType !== type || (r.manualSource !== null && r.manualSource !== (type === 'FABRIC' ? 'FABRIC_MINIMUM' : 'ACCESSORY_MANUAL'))
    || (type === 'ACCESSORY' && Number(r.onOrderQty) !== 0) || r.useDays > r.countedDays) fail(what)
  return r
}
/** erp_cp7_get_material_reorder_v1 answering `query` (its material type, the page asked for, the filter's rows). */
export function parseMaterialWorkspace(value: unknown, query: MaterialQuery): MaterialWorkspace {
  const x = w.obj(value, 'titik pesan ulang bahan')
  w.keys(x, ['contract_version', 'material_type', 'read_at', 'settings', 'run', 'can_manage', 'counts', 'page'], 'titik pesan ulang bahan')
  if (x.contract_version !== 'cp7.material-reorder.v1') fail('kontrak')
  if (x.material_type !== query.material_type) fail('jenis bahan')
  const c = w.obj(x.counts, 'jumlah'); w.keys(c, ['items', 'at_or_below', 'manual', 'formula', 'estimate', 'not_enough_data', 'no_usage', 'not_set'], 'jumlah')
  const counts: MaterialCounts = { items: w.count(c.items, 'jumlah'), atOrBelow: w.count(c.at_or_below, 'jumlah'), manual: w.count(c.manual, 'jumlah'),
    formula: w.count(c.formula, 'jumlah'), estimate: w.count(c.estimate, 'jumlah'), notEnoughData: w.count(c.not_enough_data, 'jumlah'),
    noUsage: w.count(c.no_usage, 'jumlah'), notSet: w.count(c.not_set, 'jumlah') }
  // Every material has exactly one basis, of its own type's (an accessory is MANUAL, ESTIMATE or NOT_SET; a fabric neither of the last two).
  if (counts.manual + counts.formula + counts.estimate + counts.notEnoughData + counts.noUsage + counts.notSet !== counts.items
    || counts.atOrBelow > counts.manual + counts.formula + counts.estimate
    || (query.material_type === 'FABRIC' ? counts.notSet + counts.estimate !== 0 : counts.formula + counts.notEnoughData + counts.noUsage !== 0)) fail('jumlah')
  const p = w.obj(x.page, 'halaman'); w.keys(p, ['rows', 'total', 'offset', 'limit', 'next_offset'], 'halaman')
  if (!Array.isArray(p.rows)) fail('halaman')
  const total = typeof p.total === 'string' && /^(0|[1-9]\d{0,18})$/.test(p.total) ? p.total : fail('halaman')
  const page = { rows: (p.rows as unknown[]).map(r => row(r, query.material_type)), total, offset: w.count(p.offset, 'halaman'), limit: w.count(p.limit, 'halaman'),
    nextOffset: w.maybeCount(p.next_offset, 'halaman') }
  const end = page.offset + page.rows.length
  // Total and rows come from two statements: only what the server derives from both is checked.
  if (page.offset !== query.offset || page.limit !== query.limit || page.rows.length > page.limit
    || (page.nextOffset !== null) !== (BigInt(end) < BigInt(total)) || (page.nextOffset !== null && page.nextOffset !== end)) fail('halaman')
  if (new Set(page.rows.map(r => r.materialId)).size !== page.rows.length) fail('halaman')
  if (page.rows.some(r => (query.filter === 'AT_OR_BELOW' && r.state !== 'AT_OR_BELOW') || (query.filter === 'MANUAL' && r.basis !== 'MANUAL')
    || (query.filter === 'NOT_ENOUGH_DATA' && r.basis !== 'NOT_ENOUGH_DATA') || (query.filter === 'NOT_SET' && r.basis !== 'NOT_SET')
    || (query.filter === 'ESTIMATE' && r.basis !== 'ESTIMATE'))) fail('saringan')
  return { materialType: query.material_type, readAt: w.instant(x.read_at, 'waktu baca'), settings: w.settings(x.settings, 'pengaturan'),
    run: x.run === null ? null : w.run(x.run), canManage: w.bool(x.can_manage, 'hak ubah'), counts, page }
}

/** erp_cp7_save_material_reorder_v1: a replay answers the first request's revision only (same payload), without the evaluation. */
export function parseMaterialSaveResult(value: unknown, payload: MaterialPayload, type: MaterialType): MaterialSaveResult {
  const what = 'hasil simpan bahan', o = w.obj(value, what), replay = w.bool(o.replay, what)
  w.keys(o, replay ? ['replay', 'material_id', 'revision'] : ['replay', 'material_id', 'revision', 'evaluation'], what)
  const r: MaterialSaveResult = { replay, materialId: w.uuidText(o.material_id, what), revision: w.count(o.revision, what),
    evaluation: replay ? null : row(o.evaluation, type) }
  if (r.materialId !== payload.material_id || r.revision !== payload.expected_revision + 1) fail(what)
  const e = r.evaluation
  if (e && (e.materialId !== r.materialId || e.settingRevision !== r.revision || !sameDecimal(e.leadDays, payload.lead_days)
    || (type === 'ACCESSORY' && (!sameDecimal(e.manualPoint, payload.manual_point) || (e.manualSource !== null) !== (payload.manual_point !== null)
      || !sameDecimal(e.moq, payload.moq ?? null) || !sameDecimal(e.usageMonthQty, payload.usage_month_qty ?? null)
      || !sameDecimal(e.bufferDays, payload.buffer_days ?? null))))) fail(what)
  return r
}

// ---------------------------------------------------------------- the form --
const typed = (v: string) => v.trim().replace(',', '.')
const leadText = /^\d{1,3}(\.\d{1,2})?$/, manualText = /^\d{1,13}(\.\d{1,4})?$/
const validLead = (v: string) => leadText.test(v) && Number(v) > 0 && Number(v) <= 365
const validAmount = (v: string) => manualText.test(v) && positive(v)
const validBuffer = (v: string) => leadText.test(v) && Number(v) <= 365
/** save_material's rule in plain words ('' when it may be sent). A fabric carries its lama kirim only; an accessory its lama
 * kirim dari Cina, MOQ, monthly use, buffer days and typed minimum (D17-12), each of them optional. */
export function materialProblem(type: MaterialType, d: MaterialDraft): string {
  const lead = typed(d.lead), manual = typed(d.manual), moq = typed(d.moq), usage = typed(d.usageMonth), buffer = typed(d.buffer)
  if (type === 'FABRIC' && (moq !== '' || usage !== '' || buffer !== '')) return 'Kain tidak memakai isian hitungan aksesori. Muat ulang halaman.'
  if (lead !== '' && !validLead(lead)) return type === 'FABRIC' ? 'Lama kirim: isi lebih dari 0 sampai 365 hari (boleh 2 angka di belakang koma), atau kosongkan.'
    : 'Lama kirim dari Cina: isi lebih dari 0 sampai 365 hari (boleh 2 angka di belakang koma), atau kosongkan.'
  if (type === 'ACCESSORY') {
    if (moq !== '' && !validAmount(moq)) return 'MOQ: isi lebih dari 0 (boleh 4 angka di belakang koma), atau kosongkan.'
    if (usage !== '' && !validAmount(usage)) return 'Perkiraan pemakaian per bulan: isi lebih dari 0 (boleh 4 angka di belakang koma), atau kosongkan.'
    if (buffer !== '' && !validBuffer(buffer)) return 'Cadangan untuk kiriman telat: isi 0 sampai 365 hari (boleh 2 angka di belakang koma), atau kosongkan.'
    if (manual !== '' && !manualText.test(manual)) return 'Batas minimum: isi 0 atau lebih (boleh 4 angka di belakang koma), atau kosongkan untuk memakai hitungan.'
  }
  const r = d.reason.trim()
  if (r === '' || r.length > REASON_MAX) return type === 'FABRIC' ? 'Tulis alasannya (1 sampai 500 huruf), misalnya "supplier kirim 6 hari sesudah PO".'
    : 'Tulis alasannya (1 sampai 500 huruf), misalnya "pesan minimal 5.000 pcs, kirim dari Cina 20 hari".'
  return ''
}
const shown = (v: string | null) => (v ?? '').replace('.', ',')
export const materialDraftOf = (r: MaterialRow): MaterialDraft => ({ lead: shown(r.leadDays),
  manual: r.manualSource === 'ACCESSORY_MANUAL' ? shown(r.manualPoint) : '', moq: shown(r.moq), usageMonth: shown(r.usageMonthQty), buffer: shown(r.bufferDays),
  reason: '' })
/** The draft differs from what is saved (the reason alone is not a change). */
export function materialChanged(type: MaterialType, r: MaterialRow, d: MaterialDraft): boolean {
  const saved = materialDraftOf(r), differs = (k: keyof MaterialDraft) => !sameDecimal(typed(d[k]) || null, typed(saved[k]) || null)
  return differs('lead') || (type === 'ACCESSORY' && (differs('manual') || differs('moq') || differs('usageMonth') || differs('buffer')))
}
export function materialPayload(r: Pick<MaterialRow, 'materialId' | 'settingRevision'>, type: MaterialType, d: MaterialDraft): MaterialPayload {
  if (materialProblem(type, d)) fail('isian bahan')
  const value = (v: string) => typed(v) === '' ? null : typed(v)
  const base = { material_id: r.materialId, expected_revision: r.settingRevision ?? 0, lead_days: value(d.lead) }
  return type === 'FABRIC' ? { ...base, manual_point: null, reason: d.reason.trim() }
    : { ...base, manual_point: value(d.manual), moq: value(d.moq), usage_month_qty: value(d.usageMonth), buffer_days: value(d.buffer), reason: d.reason.trim() }
}

// ------------------------------------------------------- the accessory hitungan --
/** The owner's numbers of one accessory (decimal text with a dot), null when empty; `undefined` when typed but not valid. */
export type AccessoryNumbers = { moq: string | null | undefined; leadDays: string | null | undefined; usageMonth: string | null | undefined
  bufferDays: string | null | undefined; manual: string | null | undefined }
export const accessoryNumbersOf = (r: MaterialRow): AccessoryNumbers => ({ moq: r.moq, leadDays: r.leadDays, usageMonth: r.usageMonthQty,
  bufferDays: r.bufferDays, manual: r.manualSource === 'ACCESSORY_MANUAL' ? r.manualPoint : null })
/** The draft as numbers, so the screen can show the hitungan while the owner types. */
export function accessoryNumbersOfDraft(d: MaterialDraft): AccessoryNumbers {
  const v = (text: string, ok: (t: string) => boolean) => { const t = typed(text); return t === '' ? null : ok(t) ? t : undefined }
  return { moq: v(d.moq, validAmount), leadDays: v(d.lead, validLead), usageMonth: v(d.usageMonth, validAmount), bufferDays: v(d.buffer, validBuffer),
    manual: v(d.manual, t => manualText.test(t)) }
}
const estimateNames = { usageMonth: 'perkiraan pemakaian per bulan', leadDays: 'lama kirim dari Cina', bufferDays: 'cadangan untuk kiriman telat' } as const
const andList = (words: readonly string[]) => words.length < 2 ? words.join('') : `${words.slice(0, -1).join(', ')} dan ${words[words.length - 1]}`
/** The minimum worked out from the owner's numbers, or what is still missing, in plain words (D17-12). */
export function accessoryEstimateLines(x: AccessoryNumbers, unit: string | null): string[] {
  const q = (v: string) => materialQty(v, unit), keys = ['usageMonth', 'leadDays', 'bufferDays'] as const
  const lines: string[] = []
  if (keys.some(k => x[k] === undefined)) lines.push('Batas minimum hitungan belum bisa dihitung: periksa isian yang belum sesuai.')
  else if (keys.some(k => x[k] === null)) lines.push(`Batas minimum hitungan belum bisa dihitung: ${andList(keys.filter(k => x[k] === null).map(k => estimateNames[k]))} belum diisi.`)
  else {
    const usage = x.usageMonth as string, lead = x.leadDays as string, buffer = x.bufferDays as string
    lines.push(`Batas minimum hitungan: (pemakaian per bulan ÷ 30) × (lama kirim + cadangan) = (${formatReorderQty(usage)} ÷ 30) × (${formatReorderQty(lead)} + `
      + `${formatReorderQty(buffer)}) = ${q(accessoryEstimatePoint(usage, lead, buffer))}.`)
  }
  if (typeof x.manual === 'string') lines.push(`Batas minimum yang diketik (${q(x.manual)}) dipakai, bukan hitungan.`)
  if (typeof x.moq === 'string' && typeof x.usageMonth === 'string')
    lines.push(`MOQ cukup untuk sekitar ${formatReorderQty(moqDays(x.moq, x.usageMonth))} hari (menurut perkiraan pemakaian per bulan).`)
  return lines
}

// ------------------------------------------------------------ plain words --
const shared: Record<string, string> = {
  CP7_FORMULA_ITEM_UNKNOWN: 'Bahan ini sudah tidak aktif, jadi pengaturannya tidak bisa disimpan. Tekan "Muat ulang", lalu periksa bahannya di Master Data.',
  CP7_FORMULA_REQUEST_REUSED: 'Permintaan ini sudah pernah dipakai dengan isi lain. Tekan "Muat ulang", periksa isinya, lalu simpan lagi.',
  CP7_FORMULA_REQUEST_REQUIRED: 'Permintaan tidak lengkap. Muat ulang halaman lalu coba lagi.',
  CP7_FRESH_ACCESS_REQUIRED: 'Server belum bisa memastikan data terbaru untuk permintaan ini. Muat ulang halaman lalu coba lagi.',
}
// The words that differ: a fabric has a lama kirim and a reorder point, an accessory a batas minimum only (D17-10).
const own: Record<MaterialType, Record<string, string>> = {
  FABRIC: {
    CP7_FORMULA_ACCESS_DENIED: 'Akun ini belum boleh membuka atau mengubah titik pesan ulang kain. Melihat butuh hak Bahan & Roll dan Kain & Benchmark; mengubah hanya untuk Owner atau Admin. Minta Owner memeriksa akun ini di Pengguna & Hak Akses.',
    CP7_FORMULA_BUSY: 'Titik pesan ulang sedang dihitung oleh server. Coba lagi sebentar (sekitar satu menit).',
    CP7_FORMULA_MATERIAL_STALE: 'Lama kirim kain ini baru saja diubah di layar atau perangkat lain. Tekan "Muat ulang", periksa isinya, lalu simpan lagi bila masih perlu.',
    CP7_FORMULA_MATERIAL_INVALID: 'Isian belum sesuai: lama kirim lebih dari 0 sampai 365 hari atau kosong, dan alasan 1 sampai 500 huruf. Angka minimum kain diatur di Master Data › Kain & Benchmark.',
    CP7_FORMULA_QUERY: 'Pilihan daftar titik pesan ulang tidak sah. Muat ulang halaman.',
  },
  ACCESSORY: {
    CP7_FORMULA_ACCESS_DENIED: 'Akun ini belum boleh membuka atau mengubah batas minimum aksesori. Melihat butuh hak Aksesori (gudang); mengubah hanya untuk Owner atau Admin. Minta Owner memeriksa akun ini di Pengguna & Hak Akses.',
    CP7_FORMULA_BUSY: 'Server sedang menghitung stok aksesori. Coba lagi sebentar (sekitar satu menit).',
    CP7_FORMULA_MATERIAL_STALE: 'Isian batas minimum aksesori ini baru saja diubah di layar atau perangkat lain. Tekan "Muat ulang", periksa isinya, lalu simpan lagi bila masih perlu.',
    CP7_FORMULA_MATERIAL_INVALID: 'Isian belum sesuai: lama kirim dari Cina lebih dari 0 sampai 365 hari, MOQ dan pemakaian per bulan lebih dari 0, cadangan 0 sampai 365 hari, batas minimum 0 atau lebih (semuanya boleh kosong), dan alasan 1 sampai 500 huruf.',
    CP7_FORMULA_QUERY: 'Pilihan daftar batas minimum tidak sah. Muat ulang halaman.',
  },
}
function refusal(error: unknown, type: MaterialType): string | null {
  const message = error && typeof error === 'object' ? (error as { message?: unknown }).message : null
  const code = typeof message === 'string' ? /\bCP7_(?:FORMULA_[A-Z_]+|FRESH_ACCESS_REQUIRED)\b/.exec(message)?.[0] : undefined
  return !code ? null : own[type][code] ?? shared[code] ?? null
}
/** A read error in plain words. */
export function materialErrorText(error: unknown, type: MaterialType): string {
  return refusal(error, type) ?? normalizeClientError(error).message
}
/** A write error in plain words; an unanswered request may have been saved, so it says so. */
export function materialWriteErrorText(error: unknown, type: MaterialType, write: 'REFRESH' | 'SAVE'): string {
  const known = refusal(error, type)
  if (known) return known
  if (error instanceof FgReorderResponseError) return `${error.message} Tekan "Muat ulang" untuk melihat angka yang berlaku.`
  if (isUnansweredFailure(error)) return write === 'REFRESH'
    ? 'Jawaban server tidak sampai, jadi belum pasti hitungan sudah selesai. Tekan "Muat ulang" untuk melihat jam hitung terakhir.'
    : `Jawaban server tidak sampai, jadi belum pasti ${type === 'FABRIC' ? 'lama kirim kain' : 'isian batas minimum aksesori'} ini tersimpan. Tekan "Simpan" lagi tanpa mengubah isian: permintaan yang sama dikirim ulang, jadi tidak tercatat dua kali. Atau tekan "Muat ulang" untuk melihat yang berlaku.`
  return normalizeClientError(error).message
}

/** The read permissions material_access_now asks for (fabric: Bahan & Roll and Kain & Benchmark; accessory: Aksesori). */
export const materialReorderVisible = (type: MaterialType, permissions: readonly string[]) => type === 'FABRIC'
  ? permissions.includes('warehouse.material.view') && permissions.includes('master.fabric.view') : permissions.includes('warehouse.accessory.view')
/** A quantity with its unit ("56 YD"); the unit is left out when the material has none. */
export const materialQty = (v: string, unit: string | null) => `${formatReorderQty(v)}${unit ? ` ${unit}` : ''}`
export function materialStatus(r: MaterialRow): { label: string; tone: 'warn' | 'ok' | 'off' } {
  return r.state === 'AT_OR_BELOW' ? { label: 'Menipis', tone: 'warn' } : r.state === 'ABOVE' ? { label: 'Aman', tone: 'ok' }
    : { label: r.materialType === 'ACCESSORY' ? 'Tidak diingatkan' : 'Tanpa titik', tone: 'off' }
}
/** Where the point comes from, or why there is none, in plain words (best practice D18: what to fill in). */
export function materialBasisText(r: MaterialRow, windowDays: number): string {
  if (r.basis === 'FORMULA') return 'Rumus'
  if (r.manualSource === 'FABRIC_MINIMUM') return 'Minimum Kain & Benchmark'
  // An accessory (D17-10, D17-12): a typed minimum, the hitungan from the owner's numbers, or none yet.
  if (r.basis === 'NOT_SET') return 'Belum diisi'
  if (r.basis === 'ESTIMATE') return 'Dari isian hitungan'
  if (r.basis === 'MANUAL') return r.point !== null && Number(r.point) === 0 ? 'Diketik manual 0: tidak pernah diingatkan' : 'Diketik manual'
  if (r.basis === 'NO_USAGE') return `Belum ada pemakaian ${formatReorderWhole(windowDays)} hari terakhir`
  return r.reason === 'NO_LEAD_TIME' ? 'Belum cukup data: lama kirim belum diisi'
    : `Belum cukup data: kurang dari ${MIN_COUNTED_DAYS} hari tercatat (baru ${formatReorderWhole(r.countedDays)} hari)`
}
/** The formula of one fabric, one line per step (an accessory has none, D17-10). */
export function materialFormulaLines(r: MaterialRow, windowDays: number, level: ServiceLevel): string[] {
  const q = (v: string) => materialQty(v, r.unitCode)
  const lines = [
    `Rata-rata pakai per hari: ${r.dailyMean === null ? 'belum ada' : q(formatDecimal2(r.dailyMean))}.`,
    `Naik-turun pemakaian per hari: ${r.dailySd === null ? 'belum ada' : q(formatDecimal2(r.dailySd))}.`,
    `Hari terhitung: ${formatReorderWhole(r.countedDays)} dari ${formatReorderWhole(windowDays)} hari (hari ada pemakaian ${formatReorderWhole(r.useDays)}); `
      + `terpakai ${q(r.usageQty)}. Hari tanpa stok dan tanpa pemakaian tidak dihitung.`,
    `Lama kirim: ${r.leadDays === null ? 'belum diisi' : `${formatReorderUpTo2(r.leadDays)} hari (diisi Owner atau Admin)`}.`,
    r.safetyQty === null ? 'Cadangan: belum bisa dihitung.'
      : `Cadangan: ${formatReorderQty(r.z)} × naik-turun × √lama kirim = ${q(formatDecimal2(r.safetyQty))} (tingkat layanan ${servicePercent(level)}%).`,
    r.formulaPoint === null ? 'Hasil rumus: belum ada.'
      : `Hasil rumus: rata-rata × lama kirim + cadangan, dibulatkan ke atas = ${q(r.formulaPoint)}.`,
  ]
  if (r.manualSource === 'FABRIC_MINIMUM') lines.push(`Kain ini memakai angka minimum dari Master Data › Kain & Benchmark (${q(r.manualPoint ?? '0')}), `
    + 'bukan hasil rumus: pengingat "Stok kain di bawah minimum" muncul bila stok di bawah angka itu.')
  return lines
}
// At most two decimals for display only, kept as text (the server keeps the exact numbers).
const formatDecimal2 = (v: string) => String(Math.round(Number(v) * 100) / 100)
