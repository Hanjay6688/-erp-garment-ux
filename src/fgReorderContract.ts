import { isUnansweredFailure, normalizeClientError } from './lib/clientError'
import { formatReceiptDecimal } from './procurementContract'

// SS-1 (owner D17-8, D17-9): closed parsers for the four public RPCs of scripts/cp7-src/stock-formula/formula.sql
// (cp7_stock_formula.workspace, refresh, save_manual, save_settings). Every shape is the server's own: an unknown key, a
// missing key, a wrong type or a fact the server never writes (a point without its basis, a manual basis whose point is not
// the manual number, "in production" COMPLETE without its number) is refused with "Respons titik pesan ulang tidak cocok".
// Quantities arrive as JSON numbers (to_jsonb of numeric) and are kept as decimal text, so nothing is rounded on the way.
// The form checks mirror save_manual and save_settings (best practice D13); the server still decides.
export const reorderFilters = ['ALL', 'AT_OR_BELOW', 'MANUAL', 'NOT_ENOUGH_DATA'] as const
export type ReorderFilter = typeof reorderFilters[number]
export const serviceLevels = ['0.90', '0.95', '0.99'] as const
export type ServiceLevel = typeof serviceLevels[number]
export const REORDER_PAGE = 25
export const REORDER_QUERY_MAX = 120
export const MANUAL_POINT_MAX = 10_000_000
export const REASON_MAX = 500
export const WINDOW_MIN = 14
export const WINDOW_MAX = 365
export const MIN_COUNTED_DAYS = 14

export type ReorderBasis = 'MANUAL' | 'FORMULA' | 'NOT_ENOUGH_DATA' | 'NO_SALES'
export type ReorderReason = 'NO_POSTED_SALES_IN_WINDOW' | 'FEWER_THAN_14_COUNTED_DAYS' | 'NO_LEAD_TIME'
export type WipStatus = 'COMPLETE' | 'UNKNOWN' | 'NOT_READ'
export type ReorderState = 'AT_OR_BELOW' | 'ABOVE' | 'NO_POINT'
export type ReorderSettings = { revision: number; serviceLevel: ServiceLevel; windowDays: number; reason: string | null; savedAt: string | null }
export type ReorderRun = {
  computedAt: string; windowFrom: string; windowThrough: string; settingsRevision: number; serviceLevel: ServiceLevel; windowDays: number
  items: number; atOrBelow: number; wipRead: number; materials: number; materialsAtOrBelow: number; millis: number
}
export type ReorderCounts = { items: number; atOrBelow: number; manual: number; formula: number; notEnoughData: number; noSales: number }
/** One row of cp7_stock_formula.evaluations (plus wip_read_at on the list). Decimal quantities are text. */
export type ReorderRow = {
  targetKey: string; rootId: string; sizeId: string; modelId: string | null; productId: string; sku: string; productName: string; sizeCode: string | null
  freePcs: string; salesPcs: string; countedDays: number; saleDays: number; dailyMean: string | null; dailySd: string | null
  leadDays: string | null; leadBasis: 'MEASURED' | 'PROFILE' | null; leadLots: number | null; leadGroups: number | null
  bufferMode: 'STATISTICAL' | 'DAYS'; bufferDays: string | null; z: string; safetyPcs: string | null
  formulaPoint: number | null; manualPoint: number | null; manualRevision: number | null; point: number | null
  basis: ReorderBasis; reason: ReorderReason | null; wipPcs: string | null; wipStatus: WipStatus; wipReason: string | null
  state: ReorderState; changedAt: string; wipReadAt: string | null
}
export type ReorderQuery = { q: string; filter: ReorderFilter; offset: number; limit: number }
export type ReorderPage = { rows: ReorderRow[]; total: string; offset: number; limit: number; nextOffset: number | null }
export type ReorderWorkspace = { readAt: string; settings: ReorderSettings; run: ReorderRun | null; canManage: boolean; counts: ReorderCounts; page: ReorderPage }
export type ReorderRefresh = { computedAt: string; items: number; atOrBelow: number; wipRead: number; materials: number; materialsAtOrBelow: number }
export type ManualPayload = { root_id: string; expected_revision: number; reorder_point_pcs: number | null; reason: string }
export type SettingsPayload = { expected_revision: number; service_level: ServiceLevel; window_days: number; reason: string }
export type ManualResult = { replay: boolean; rootId: string; revision: number; reorderPointPcs: number | null; evaluation: ReorderRow | null }
export type SettingsResult = { replay: boolean; settings: ReorderSettings }
export type SettingsDraft = { serviceLevel: ServiceLevel; windowDays: string; reason: string }

export class FgReorderResponseError extends Error {}
function fail(what: string): never { throw new FgReorderResponseError(`Respons titik pesan ulang tidak cocok (${what}).`) }
type Obj = Record<string, unknown>
const obj = (v: unknown, what: string): Obj => Boolean(v) && typeof v === 'object' && !Array.isArray(v) ? v as Obj : fail(what)
const str = (v: unknown, what: string) => typeof v === 'string' ? v : fail(what)
const maybeStr = (v: unknown, what: string) => v === null ? null : str(v, what)
const bool = (v: unknown, what: string) => typeof v === 'boolean' ? v : fail(what)
const instant = (v: unknown, what: string) => typeof v === 'string' && Number.isFinite(Date.parse(v)) ? v : fail(what)
const maybeInstant = (v: unknown, what: string) => v === null ? null : instant(v, what)
const count = (v: unknown, what: string) => typeof v === 'number' && Number.isSafeInteger(v) && v >= 0 ? v : fail(what)
const maybeCount = (v: unknown, what: string) => v === null ? null : count(v, what)
const uuid = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i
const uuidText = (v: unknown, what: string) => typeof v === 'string' && uuid.test(v) ? v : fail(what)
const maybeUuid = (v: unknown, what: string) => v === null ? null : uuidText(v, what)
// A JSON number written by to_jsonb(numeric), kept as its plain decimal text (an exponent form is refused, never guessed).
const decimalText = /^-?\d+(\.\d+)?$/
const decimal = (v: unknown, what: string) => typeof v === 'number' && Number.isFinite(v) && decimalText.test(String(v)) ? String(v) : fail(what)
const maybeDecimal = (v: unknown, what: string) => v === null ? null : decimal(v, what)
const dayText = /^(\d{4})-(\d{2})-(\d{2})$/
function day(v: unknown, what: string) {
  const m = typeof v === 'string' ? dayText.exec(v) : null
  if (!m) return fail(what)
  const t = Date.UTC(Number(m[1]), Number(m[2]) - 1, Number(m[3]))
  return new Date(t).toISOString().slice(0, 10) === v ? { text: v as string, t } : fail(what)
}
function oneOf<T extends string>(v: unknown, values: readonly T[], what: string): T {
  return typeof v === 'string' && (values as readonly string[]).includes(v) ? v as T : fail(what)
}
function keys(o: Obj, expected: readonly string[], what: string) {
  const got = Object.keys(o).sort(), want = [...expected].sort()
  if (got.length !== want.length || got.some((k, i) => k !== want[i])) fail(what)
}

function settings(v: unknown, what: string): ReorderSettings {
  const o = obj(v, what); keys(o, ['revision', 'service_level', 'window_days', 'reason', 'saved_at'], what)
  const s: ReorderSettings = { revision: count(o.revision, what), serviceLevel: oneOf(o.service_level, serviceLevels, what), windowDays: count(o.window_days, what),
    reason: maybeStr(o.reason, what), savedAt: maybeInstant(o.saved_at, what) }
  // None saved: revision 0 with no reason and no time (current_settings' defaults); a saved revision has both.
  if (s.windowDays < WINDOW_MIN || s.windowDays > WINDOW_MAX || (s.revision === 0) !== (s.savedAt === null) || (s.revision === 0) !== (s.reason === null)) fail(what)
  return s
}
// runs.service_level is numeric: to_jsonb writes 0.90 as the JSON number 0.9.
const levelOfNumber = (v: unknown, what: string): ServiceLevel => v === 0.9 ? '0.90' : v === 0.95 ? '0.95' : v === 0.99 ? '0.99' : fail(what)
function run(v: unknown): ReorderRun {
  const what = 'hitungan terakhir', o = obj(v, what)
  // The same run also evaluates fabric and accessories (materials, materials_at_or_below); their screens come later.
  keys(o, ['computed_at', 'window_from', 'window_through', 'settings_revision', 'service_level', 'window_days', 'items', 'at_or_below', 'wip_read', 'materials',
    'materials_at_or_below', 'millis'], what)
  const from = day(o.window_from, what), through = day(o.window_through, what)
  const r: ReorderRun = { computedAt: instant(o.computed_at, what), windowFrom: from.text, windowThrough: through.text, settingsRevision: count(o.settings_revision, what),
    serviceLevel: levelOfNumber(o.service_level, what), windowDays: count(o.window_days, what), items: count(o.items, what), atOrBelow: count(o.at_or_below, what),
    wipRead: count(o.wip_read, what), materials: count(o.materials, what), materialsAtOrBelow: count(o.materials_at_or_below, what), millis: count(o.millis, what) }
  // compute(): window_from = today - window_days, window_through = today - 1 (complete WIB days).
  if (r.windowDays < WINDOW_MIN || r.windowDays > WINDOW_MAX || (through.t - from.t) / 86_400_000 !== r.windowDays - 1 || r.atOrBelow > r.items
    || r.materialsAtOrBelow > r.materials) fail(what)
  return r
}

const rowKeys = ['target_key', 'root_id', 'size_id', 'model_id', 'product_id', 'sku', 'product_name', 'size_code', 'free_pcs', 'sales_pcs', 'counted_days',
  'sale_days', 'daily_mean', 'daily_sd', 'lead_days', 'lead_basis', 'lead_lots', 'lead_groups', 'buffer_mode', 'buffer_days', 'z', 'safety_pcs', 'formula_point',
  'manual_point', 'manual_revision', 'point', 'basis', 'reason', 'wip_pcs', 'wip_status', 'wip_reason', 'state', 'changed_at'] as const
const reasons = ['NO_POSTED_SALES_IN_WINDOW', 'FEWER_THAN_14_COUNTED_DAYS', 'NO_LEAD_TIME'] as const
function row(v: unknown, list: boolean): ReorderRow {
  const what = 'barang', o = obj(v, what)
  keys(o, list ? [...rowKeys, 'wip_read_at'] : rowKeys, what)
  const r: ReorderRow = {
    targetKey: str(o.target_key, what), rootId: uuidText(o.root_id, what), sizeId: uuidText(o.size_id, what), modelId: maybeUuid(o.model_id, what),
    productId: uuidText(o.product_id, what), sku: str(o.sku, what), productName: str(o.product_name, what), sizeCode: maybeStr(o.size_code, what),
    freePcs: decimal(o.free_pcs, what), salesPcs: decimal(o.sales_pcs, what), countedDays: count(o.counted_days, what), saleDays: count(o.sale_days, what),
    dailyMean: maybeDecimal(o.daily_mean, what), dailySd: maybeDecimal(o.daily_sd, what), leadDays: maybeDecimal(o.lead_days, what),
    leadBasis: o.lead_basis === null ? null : oneOf(o.lead_basis, ['MEASURED', 'PROFILE'] as const, what), leadLots: maybeCount(o.lead_lots, what),
    leadGroups: maybeCount(o.lead_groups, what), bufferMode: oneOf(o.buffer_mode, ['STATISTICAL', 'DAYS'] as const, what), bufferDays: maybeDecimal(o.buffer_days, what),
    z: decimal(o.z, what), safetyPcs: maybeDecimal(o.safety_pcs, what), formulaPoint: maybeCount(o.formula_point, what), manualPoint: maybeCount(o.manual_point, what),
    manualRevision: maybeCount(o.manual_revision, what), point: maybeCount(o.point, what),
    basis: oneOf(o.basis, ['MANUAL', 'FORMULA', 'NOT_ENOUGH_DATA', 'NO_SALES'] as const, 'dasar angka'), reason: o.reason === null ? null : oneOf(o.reason, reasons, what),
    wipPcs: maybeDecimal(o.wip_pcs, what), wipStatus: oneOf(o.wip_status, ['COMPLETE', 'UNKNOWN', 'NOT_READ'] as const, 'sedang diproduksi'),
    wipReason: maybeStr(o.wip_reason, what), state: oneOf(o.state, ['AT_OR_BELOW', 'ABOVE', 'NO_POINT'] as const, 'status'), changedAt: instant(o.changed_at, what),
    wipReadAt: list ? maybeInstant(o.wip_read_at, what) : null,
  }
  const pointed = r.basis === 'MANUAL' || r.basis === 'FORMULA'
  // The evaluations table: point is there exactly for MANUAL and FORMULA, and is the manual number or the formula's.
  if ((r.point !== null) !== pointed || (r.basis === 'MANUAL' && r.point !== r.manualPoint) || (r.basis === 'FORMULA' && r.point !== r.formulaPoint)
    || (r.manualPoint !== null) !== (r.basis === 'MANUAL') || (r.manualPoint !== null && r.manualRevision === null)) fail('titik pesan ulang')
  // compute(): the reason says why there is no formula basis, and only then.
  if (pointed ? r.reason !== null : r.basis === 'NO_SALES' ? r.reason !== 'NO_POSTED_SALES_IN_WINDOW'
    : r.reason !== 'FEWER_THAN_14_COUNTED_DAYS' && r.reason !== 'NO_LEAD_TIME') fail('alasan')
  // In production: a number exactly when COMPLETE; any other status says why.
  if ((r.wipStatus === 'COMPLETE') !== (r.wipPcs !== null) || (r.wipStatus === 'COMPLETE') !== (r.wipReason === null)) fail('sedang diproduksi')
  if ((r.state === 'NO_POINT') !== (r.point === null || r.point <= 0)) fail('status')
  if (r.targetKey !== `${r.rootId}:${r.sizeId}` || r.saleDays > r.countedDays || (r.leadDays === null) !== (r.leadBasis === null)
    || (r.bufferMode === 'DAYS') !== (r.bufferDays !== null)) fail(what)
  return r
}

/** erp_cp7_get_fg_reorder_v1 answering `query` (the page must be the one asked for, its rows the filter's). */
export function parseFgReorderWorkspace(value: unknown, query: ReorderQuery): ReorderWorkspace {
  const w = obj(value, 'titik pesan ulang')
  keys(w, ['contract_version', 'read_at', 'settings', 'run', 'can_manage', 'counts', 'page'], 'titik pesan ulang')
  if (w.contract_version !== 'cp7.fg-reorder.v1') fail('kontrak')
  const c = obj(w.counts, 'jumlah'); keys(c, ['items', 'at_or_below', 'manual', 'formula', 'not_enough_data', 'no_sales'], 'jumlah')
  const counts: ReorderCounts = { items: count(c.items, 'jumlah'), atOrBelow: count(c.at_or_below, 'jumlah'), manual: count(c.manual, 'jumlah'),
    formula: count(c.formula, 'jumlah'), notEnoughData: count(c.not_enough_data, 'jumlah'), noSales: count(c.no_sales, 'jumlah') }
  // One statement counts them all: every item has exactly one basis, and an item at or under its point has a point.
  if (counts.manual + counts.formula + counts.notEnoughData + counts.noSales !== counts.items || counts.atOrBelow > counts.manual + counts.formula) fail('jumlah')
  const p = obj(w.page, 'halaman'); keys(p, ['rows', 'total', 'offset', 'limit', 'next_offset'], 'halaman')
  if (!Array.isArray(p.rows)) fail('halaman')
  const total = typeof p.total === 'string' && /^(0|[1-9]\d{0,18})$/.test(p.total) ? p.total : fail('halaman')
  const page: ReorderPage = { rows: p.rows.map(x => row(x, true)), total, offset: count(p.offset, 'halaman'), limit: count(p.limit, 'halaman'),
    nextOffset: maybeCount(p.next_offset, 'halaman') }
  const end = page.offset + page.rows.length
  // The total and the rows are read by two statements, so only what the server derives from both is checked here.
  if (page.offset !== query.offset || page.limit !== query.limit || page.rows.length > page.limit
    || (page.nextOffset !== null) !== (BigInt(end) < BigInt(total)) || (page.nextOffset !== null && page.nextOffset !== end)) fail('halaman')
  if (new Set(page.rows.map(r => r.targetKey)).size !== page.rows.length) fail('halaman')
  if (page.rows.some(r => (query.filter === 'AT_OR_BELOW' && r.state !== 'AT_OR_BELOW') || (query.filter === 'MANUAL' && r.basis !== 'MANUAL')
    || (query.filter === 'NOT_ENOUGH_DATA' && r.basis !== 'NOT_ENOUGH_DATA'))) fail('saringan')
  return { readAt: instant(w.read_at, 'waktu baca'), settings: settings(w.settings, 'pengaturan'), run: w.run === null ? null : run(w.run),
    canManage: bool(w.can_manage, 'hak ubah'), counts, page }
}

/** erp_cp7_refresh_fg_reorder_v1: what compute() answers (finished goods, then fabric and accessories of the same run). */
export function parseFgReorderRefresh(value: unknown): ReorderRefresh {
  const what = 'hasil hitung', o = obj(value, what)
  keys(o, ['computed_at', 'items', 'at_or_below', 'wip_read', 'materials', 'materials_at_or_below'], what)
  const r = { computedAt: instant(o.computed_at, what), items: count(o.items, what), atOrBelow: count(o.at_or_below, what), wipRead: count(o.wip_read, what),
    materials: count(o.materials, what), materialsAtOrBelow: count(o.materials_at_or_below, what) }
  if (r.atOrBelow > r.items || r.materialsAtOrBelow > r.materials) fail(what)
  return r
}

/** erp_cp7_save_fg_reorder_manual_v1: a replay answers the first request's row (same payload), without the evaluation. */
export function parseFgReorderManualResult(value: unknown, payload: ManualPayload): ManualResult {
  const what = 'hasil angka manual', o = obj(value, what), replay = bool(o.replay, what)
  keys(o, replay ? ['replay', 'root_id', 'revision', 'reorder_point_pcs'] : ['replay', 'root_id', 'revision', 'reorder_point_pcs', 'evaluation'], what)
  const r: ManualResult = { replay, rootId: uuidText(o.root_id, what), revision: count(o.revision, what), reorderPointPcs: maybeCount(o.reorder_point_pcs, what),
    evaluation: replay ? null : row(o.evaluation, false) }
  if (r.rootId !== payload.root_id || r.revision !== payload.expected_revision + 1 || r.reorderPointPcs !== payload.reorder_point_pcs) fail(what)
  if (r.evaluation && (r.evaluation.rootId !== r.rootId || r.evaluation.manualRevision !== r.revision || r.evaluation.manualPoint !== r.reorderPointPcs)) fail(what)
  return r
}

/** erp_cp7_save_stock_formula_settings_v1: a replay answers the settings in force now, which may be newer. */
export function parseFgReorderSettingsResult(value: unknown, payload: SettingsPayload): SettingsResult {
  const what = 'hasil pengaturan', o = obj(value, what); keys(o, ['replay', 'settings'], what)
  const r: SettingsResult = { replay: bool(o.replay, what), settings: settings(o.settings, what) }
  const s = r.settings, saved = payload.expected_revision + 1
  if (r.replay ? s.revision < saved : s.revision !== saved || s.serviceLevel !== payload.service_level || s.windowDays !== payload.window_days
    || s.reason !== payload.reason) fail(what)
  return r
}

// ---------------------------------------------------------------- the forms --
const wholeText = /^\d{1,8}$/
/** save_manual's rule in plain words ('' when it may be sent): a whole number 0..10.000.000 (none to clear) and a reason. */
export function manualProblem(qty: string | null, reason: string): string {
  if (qty !== null && (!wholeText.test(qty.trim()) || Number(qty.trim()) > MANUAL_POINT_MAX)) return 'Isi titik pesan ulang dengan angka bulat 0 sampai 10.000.000 pcs (0 = peringatan barang ini dimatikan).'
  const r = reason.trim()
  if (r === '' || r.length > REASON_MAX) return 'Tulis alasannya (1 sampai 500 huruf), misalnya "pesanan besar toko A bulan depan".'
  return ''
}
export function manualPayload(row: Pick<ReorderRow, 'rootId' | 'manualRevision'>, qty: string | null, reason: string): ManualPayload {
  if (manualProblem(qty, reason)) fail('isian angka manual')
  return { root_id: row.rootId, expected_revision: row.manualRevision ?? 0, reorder_point_pcs: qty === null ? null : Number(qty.trim()), reason: reason.trim() }
}
export const settingsDraftOf = (s: ReorderSettings): SettingsDraft => ({ serviceLevel: s.serviceLevel, windowDays: String(s.windowDays), reason: '' })
/** The draft differs from the settings in force (the reason alone is not a change). */
export const settingsChanged = (d: SettingsDraft, s: Pick<SettingsDraft, 'serviceLevel' | 'windowDays'>) =>
  d.serviceLevel !== s.serviceLevel || d.windowDays.trim() !== s.windowDays.trim()
export function settingsProblem(d: SettingsDraft): string {
  if (!serviceLevels.includes(d.serviceLevel)) return 'Pilih tingkat layanan 90, 95 atau 99%.'
  const w = d.windowDays.trim()
  if (!/^\d{1,3}$/.test(w) || Number(w) < WINDOW_MIN || Number(w) > WINDOW_MAX) return 'Jumlah hari penjualan: isi 14 sampai 365 hari.'
  const r = d.reason.trim()
  if (r === '' || r.length > REASON_MAX) return 'Tulis alasan perubahan (1 sampai 500 huruf).'
  return ''
}
export function settingsPayload(d: SettingsDraft, expectedRevision: number): SettingsPayload {
  if (settingsProblem(d) || !Number.isSafeInteger(expectedRevision) || expectedRevision < 0) fail('isian pengaturan')
  return { expected_revision: expectedRevision, service_level: d.serviceLevel, window_days: Number(d.windowDays.trim()), reason: d.reason.trim() }
}

// ------------------------------------------------------------ plain words --
// The refusals of formula.sql in plain words, with the way out (best practice D18).
const refusals: Record<string, string> = {
  CP7_FORMULA_ACCESS_DENIED: 'Akun ini belum boleh membuka atau mengubah titik pesan ulang. Melihat butuh hak Ringkasan Barang Jadi; mengubah hanya untuk Owner atau Admin. Minta Owner memeriksa akun ini di Pengguna & Hak Akses.',
  CP7_FORMULA_BUSY: 'Server sedang menghitung titik pesan ulang (hitungan otomatis tiap menit, atau tombol "Hitung sekarang" dari layar lain). Coba lagi sekitar satu menit lagi.',
  CP7_FORMULA_MANUAL_STALE: 'Angka manual barang ini baru saja diubah di layar atau perangkat lain. Tekan "Muat ulang", periksa angkanya, lalu simpan lagi bila masih perlu.',
  CP7_FORMULA_SETTINGS_STALE: 'Pengaturan rumus baru saja diubah di layar atau perangkat lain. Tekan "Muat ulang", periksa isinya, lalu simpan lagi bila masih perlu.',
  CP7_FORMULA_MANUAL_INVALID: 'Isian angka manual belum sesuai: angka bulat 0 sampai 10.000.000 pcs dan alasan 1 sampai 500 huruf.',
  CP7_FORMULA_SETTINGS_INVALID: 'Isian pengaturan rumus belum sesuai: tingkat layanan 90, 95 atau 99%, jumlah hari 14 sampai 365, dan alasan 1 sampai 500 huruf.',
  CP7_FORMULA_ITEM_UNKNOWN: 'Barang ini sudah tidak aktif atau sedang berganti versi, jadi angka manualnya tidak bisa disimpan. Tekan "Muat ulang", lalu periksa barangnya di Data Master.',
  CP7_FORMULA_REQUEST_REUSED: 'Permintaan ini sudah pernah dipakai dengan isi lain. Tekan "Muat ulang", periksa angkanya, lalu simpan lagi.',
  CP7_FORMULA_REQUEST_REQUIRED: 'Permintaan tidak lengkap. Muat ulang halaman lalu coba lagi.',
  CP7_FORMULA_QUERY: 'Pilihan daftar titik pesan ulang tidak sah. Muat ulang halaman.',
  CP7_FRESH_ACCESS_REQUIRED: 'Server belum bisa memastikan data terbaru untuk permintaan ini. Muat ulang halaman lalu coba lagi.',
}
export function fgReorderRefusalCode(error: unknown): string | null {
  const message = error && typeof error === 'object' ? (error as { message?: unknown }).message : null
  if (typeof message !== 'string') return null
  const code = /\bCP7_(?:FORMULA_[A-Z_]+|FRESH_ACCESS_REQUIRED)\b/.exec(message)?.[0]
  return code && code in refusals ? code : null
}
/** A read error in plain words: a known refusal first, then the shared client wording. */
export function fgReorderErrorText(error: unknown): string {
  const code = fgReorderRefusalCode(error)
  return code ? refusals[code] : normalizeClientError(error).message
}
export type ReorderWrite = 'REFRESH' | 'MANUAL' | 'SETTINGS'
const lost: Record<ReorderWrite, string> = {
  REFRESH: 'Jawaban server tidak sampai, jadi belum pasti hitungan sudah selesai. Tekan "Muat ulang" untuk melihat jam hitung terakhir.',
  MANUAL: 'Jawaban server tidak sampai, jadi belum pasti angka manual tersimpan. Tekan tombol yang sama lagi tanpa mengubah isian: permintaan yang sama dikirim ulang, jadi tidak tercatat dua kali. Atau tekan "Muat ulang" untuk melihat angka yang berlaku.',
  SETTINGS: 'Jawaban server tidak sampai, jadi belum pasti pengaturan rumus tersimpan. Tekan "Simpan pengaturan rumus" lagi tanpa mengubah isian: permintaan yang sama dikirim ulang, jadi tidak tercatat dua kali. Atau tekan "Muat ulang" untuk melihat pengaturan yang berlaku.',
}
/** A write error in plain words. An unanswered request may have been saved: say so, never "gagal". */
export function fgReorderWriteErrorText(error: unknown, write: ReorderWrite): string {
  const code = fgReorderRefusalCode(error)
  if (code) return refusals[code]
  if (error instanceof FgReorderResponseError) return `${error.message} Tekan "Muat ulang" untuk melihat angka yang berlaku.`
  if (isUnansweredFailure(error)) return lost[write]
  return normalizeClientError(error).message
}

const plain = new Intl.NumberFormat('id-ID', { maximumFractionDigits: 2 })
const two = new Intl.NumberFormat('id-ID', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
/** Exact decimal text as Indonesian digits ("1234.5" -> "1.234,5"). */
export const formatReorderQty = (v: string) => formatReceiptDecimal(v)
export const formatReorderWhole = (n: number) => formatReceiptDecimal(String(n))
/** At most two decimals, for the formula's inputs (a display rounding only; the server keeps the exact numbers). */
export const formatReorderUpTo2 = (v: string) => plain.format(Number(v))
export const formatReorderTwo = (v: string) => two.format(Number(v))
export const servicePercent = (level: ServiceLevel) => level === '0.90' ? '90' : level === '0.95' ? '95' : '99'

export type ReorderChip = { label: string; tone: 'warn' | 'ok' | 'off' }
/** The status of one item; the window is the number of days the last calculation read. */
export function reorderChip(r: ReorderRow, windowDays: number): ReorderChip {
  if (r.state === 'AT_OR_BELOW') return { label: 'Perlu produksi', tone: 'warn' }
  if (r.state === 'ABOVE') return { label: 'Aman', tone: 'ok' }
  if (r.basis === 'NOT_ENOUGH_DATA') return { label: 'Belum cukup data', tone: 'off' }
  if (r.basis === 'NO_SALES') return { label: `Belum ada penjualan ${windowDays} hari terakhir`, tone: 'off' }
  if (r.basis === 'MANUAL' && r.point === 0) return { label: 'Peringatan dimatikan (angka manual 0)', tone: 'off' }
  return { label: 'Belum ada titik pesan ulang', tone: 'off' }
}
/** Why the formula has no number yet, with what to fill in (best practice D18); null when it has one. */
export function reorderReasonText(r: ReorderRow): string | null {
  if (r.reason === 'FEWER_THAN_14_COUNTED_DAYS') return `Belum cukup data: baru ${r.countedDays} hari tercatat, perlu ${MIN_COUNTED_DAYS}.`
  if (r.reason === 'NO_LEAD_TIME') return 'Belum cukup data: lama produksi belum ada, karena belum ada 3 kali produksi model ini. Isi lama produksi di profil perencanaan '
    + '(tombol "Data permintaan & stok" di atas, lalu "Atur target", kolom "Waktu proses pilihan") atau isi angka manual.'
  return null
}
export function reorderSourceText(r: ReorderRow): string | null {
  if (r.basis === 'MANUAL') return `Asal angka: angka manual (rumus: ${r.formulaPoint === null ? 'belum ada' : formatReorderWhole(r.formulaPoint)})`
  return r.basis === 'FORMULA' ? 'Asal angka: rumus' : null
}
export function reorderWipText(r: ReorderRow): string {
  return r.wipStatus === 'COMPLETE' ? `${formatReorderQty(r.wipPcs ?? '0')} pcs` : r.wipStatus === 'NOT_READ' ? 'belum dibaca' : 'belum bisa dihitung'
}
const wipReasons: Record<string, string> = {
  PRODUCT_WITHOUT_MODEL: 'barang ini belum terhubung ke model',
  MODEL_WIP_GROUP_LIMIT: 'potongan model ini yang masih berjalan lebih dari 200',
}
/** Why "in production" is not a number, and what is compared instead; null when it is. */
export function reorderWipNote(r: ReorderRow): string | null {
  if (r.wipStatus === 'COMPLETE') return null
  const why = r.wipStatus === 'NOT_READ' ? 'server belum sempat membacanya' : (r.wipReason && wipReasons[r.wipReason]) || 'data produksinya belum lengkap'
  return `Sedang diproduksi ${r.wipStatus === 'NOT_READ' ? 'belum dibaca' : 'belum bisa dihitung'}: ${why}. Selama itu, yang dibandingkan dengan titik pesan ulang hanya stok bebas.`
}
/** The formula of one item, one line per step, in plain words. */
export function reorderFormulaLines(r: ReorderRow, windowDays: number, level: ServiceLevel): string[] {
  const lead = r.leadDays === null ? 'Lama produksi: belum ada.'
    : `Lama produksi: ${formatReorderUpTo2(r.leadDays)} hari (${r.leadBasis === 'MEASURED'
      ? `diukur dari ${formatReorderWhole(r.leadLots ?? 0)} lot dari ${formatReorderWhole(r.leadGroups ?? 0)} potongan` : 'dari profil perencanaan'}).`
  const safety = r.safetyPcs === null ? 'Cadangan: belum bisa dihitung.'
    : r.bufferMode === 'DAYS' ? `Cadangan: rata-rata × ${formatReorderUpTo2(r.bufferDays ?? '0')} hari = ${formatReorderUpTo2(r.safetyPcs)} pcs (cadangan hari dari profil perencanaan).`
    : `Cadangan: ${formatReorderQty(r.z)} × naik-turun × √lama produksi = ${formatReorderUpTo2(r.safetyPcs)} pcs (tingkat layanan ${servicePercent(level)}%).`
  return [
    `Rata-rata jual per hari: ${r.dailyMean === null ? 'belum ada' : `${formatReorderTwo(r.dailyMean)} pcs`}.`,
    `Naik-turun penjualan per hari: ${r.dailySd === null ? 'belum ada' : `${formatReorderTwo(r.dailySd)} pcs`}.`,
    `Hari terhitung: ${formatReorderWhole(r.countedDays)} dari ${formatReorderWhole(windowDays)} hari (hari jual ${formatReorderWhole(r.saleDays)}); terjual ${formatReorderQty(r.salesPcs)} pcs.`,
    lead, safety,
    r.formulaPoint === null ? 'Hasil rumus: belum ada.'
      : `Hasil rumus: rata-rata × lama produksi + cadangan, dibulatkan ke atas = ${formatReorderWhole(r.formulaPoint)} pcs.`,
  ]
}
