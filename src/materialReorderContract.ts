import { isUnansweredFailure, normalizeClientError } from './lib/clientError'
import {
  FgReorderResponseError, MIN_COUNTED_DAYS, REASON_MAX, formatReorderQty, formatReorderUpTo2, formatReorderWhole, reorderWire as w, servicePercent,
  type ReorderFilter, type ReorderRun, type ReorderSettings, type ServiceLevel,
} from './fgReorderContract'

// SS-2 (fabric) and SS-3 (accessories), owner D17-9: closed parsers for the three public RPCs of scripts/cp7-src/stock-formula/
// materials.sql (material_workspace, material_refresh, save_material). The same rules and words as the finished goods
// (fgReorderContract.ts, shared through reorderWire): an unknown or missing key, a wrong type or a fact the server never
// writes is refused with "Respons titik pesan ulang tidak cocok"; quantities stay decimal text in the material's own unit.
// Owner D17-10 ("aksesoris pake batas minimum manual aja ... rumus ga penting"): an accessory never has a formula. Its row is
// MANUAL (the minimum entered by Owner/Admin) or NOT_SET (none, NO_MANUAL_MINIMUM), without lama kirim, cadangan or formula
// number; its usage per day is still shown, to help choose the minimum. Fabric rows are unchanged.
export type MaterialType = 'FABRIC' | 'ACCESSORY'
export type MaterialBasis = 'MANUAL' | 'FORMULA' | 'NOT_ENOUGH_DATA' | 'NO_USAGE' | 'NOT_SET'
export type MaterialReason = 'NO_POSTED_USAGE_IN_WINDOW' | 'FEWER_THAN_14_COUNTED_DAYS' | 'NO_LEAD_TIME' | 'NO_MANUAL_MINIMUM'
export type MaterialManualSource = 'FABRIC_MINIMUM' | 'ACCESSORY_MANUAL'
/** The list filters of erp_cp7_get_material_reorder_v1: the finished goods' four and NOT_SET (an accessory without a minimum). */
export type MaterialFilter = ReorderFilter | 'NOT_SET'
/** The filters each screen offers: an accessory has no formula, so no "not enough data"; a fabric has no "not set". */
export const materialFilters: Record<MaterialType, readonly MaterialFilter[]> = {
  FABRIC: ['ALL', 'AT_OR_BELOW', 'MANUAL', 'NOT_ENOUGH_DATA'], ACCESSORY: ['ALL', 'AT_OR_BELOW', 'MANUAL', 'NOT_SET'],
}
/** One row of cp7_stock_formula.material_evaluations. */
export type MaterialRow = {
  materialId: string; materialType: MaterialType; sku: string; name: string; unitCode: string | null; freeQty: string; onOrderQty: string; usageQty: string
  countedDays: number; useDays: number; dailyMean: string | null; dailySd: string | null; leadDays: string | null; settingRevision: number | null; z: string
  safetyQty: string | null; formulaPoint: string | null; manualPoint: string | null; manualSource: MaterialManualSource | null; point: string | null
  basis: MaterialBasis; reason: MaterialReason | null; state: 'AT_OR_BELOW' | 'ABOVE' | 'NO_POINT'; changedAt: string
}
export type MaterialCounts = { items: number; atOrBelow: number; manual: number; formula: number; notEnoughData: number; noUsage: number; notSet: number }
/** p_query of erp_cp7_get_material_reorder_v1, sent as it is. */
export type MaterialQuery = { material_type: MaterialType; q: string; filter: MaterialFilter; offset: number; limit: number }
export type MaterialWorkspace = {
  materialType: MaterialType; readAt: string; settings: ReorderSettings; run: ReorderRun | null; canManage: boolean; counts: MaterialCounts
  page: { rows: MaterialRow[]; total: string; offset: number; limit: number; nextOffset: number | null }
}
/** lead_days is the fabric's lama kirim (always null for an accessory); manual_point the accessory's batas minimum (always null for a fabric). */
export type MaterialPayload = { material_id: string; expected_revision: number; lead_days: string | null; manual_point: string | null; reason: string }
export type MaterialSaveResult = { replay: boolean; materialId: string; revision: number; evaluation: MaterialRow | null }
/** The form of one material: text as typed (a decimal comma is accepted), empty = none. A fabric fills `lead` only, an
 * accessory `manual` (its batas minimum) only. */
export type MaterialDraft = { lead: string; manual: string; reason: string }

const fail = (what: string): never => w.fail(what)
const rowKeys = ['material_id', 'material_type', 'sku', 'name', 'unit_code', 'free_qty', 'on_order_qty', 'usage_qty', 'counted_days', 'use_days', 'daily_mean',
  'daily_sd', 'lead_days', 'setting_revision', 'z', 'safety_qty', 'formula_point', 'manual_point', 'manual_source', 'point', 'basis', 'reason', 'state',
  'changed_at'] as const
const bases = { FABRIC: ['MANUAL', 'FORMULA', 'NOT_ENOUGH_DATA', 'NO_USAGE'], ACCESSORY: ['MANUAL', 'NOT_SET'] } as const
const reasons = { FABRIC: ['NO_POSTED_USAGE_IN_WINDOW', 'FEWER_THAN_14_COUNTED_DAYS', 'NO_LEAD_TIME'], ACCESSORY: ['NO_MANUAL_MINIMUM'] } as const
/** Exact order of two decimal texts (-1, 0, 1), without rounding through floating point. */
function compareDecimal(a: string, b: string): number {
  const places = Math.max((a.split('.')[1] ?? '').length, (b.split('.')[1] ?? '').length)
  const scaled = (v: string) => { const [i, f = ''] = v.replace('-', '').split('.'), n = BigInt(i + f.padEnd(places, '0')); return v.startsWith('-') ? -n : n }
  const x = scaled(a), y = scaled(b)
  return x < y ? -1 : x > y ? 1 : 0
}
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
    point: w.maybeDecimal(o.point, what), basis: w.oneOf<MaterialBasis>(o.basis, bases[type], 'dasar angka'),
    reason: o.reason === null ? null : w.oneOf<MaterialReason>(o.reason, reasons[type], what),
    state: w.oneOf(o.state, ['AT_OR_BELOW', 'ABOVE', 'NO_POINT'] as const, 'status'),
    changedAt: w.instant(o.changed_at, what),
  }
  const pointed = r.basis === 'MANUAL' || r.basis === 'FORMULA'
  // The table checks and compute_materials(): a point exactly for MANUAL and FORMULA, the manual number exactly with its source
  // (the fabric's minimum or the accessory's own number), and the point is that number or the formula's.
  if ((r.point !== null) !== pointed || (r.manualSource === null) !== (r.manualPoint === null) || (r.manualSource !== null) !== (r.basis === 'MANUAL')
    || (r.basis === 'MANUAL' && r.point !== r.manualPoint) || (r.basis === 'FORMULA' && r.point !== r.formulaPoint)) fail('titik pesan ulang')
  if (pointed ? r.reason !== null : r.basis === 'NO_USAGE' ? r.reason !== 'NO_POSTED_USAGE_IN_WINDOW' : r.basis === 'NOT_SET' ? r.reason !== 'NO_MANUAL_MINIMUM'
    : r.reason !== 'FEWER_THAN_14_COUNTED_DAYS' && r.reason !== 'NO_LEAD_TIME') fail('alasan')
  if ((r.basis === 'FORMULA' && (r.leadDays === null || r.safetyQty === null)) || (r.reason === 'NO_LEAD_TIME' && r.leadDays !== null)) fail('lama kirim')
  if ((r.state === 'NO_POINT') !== (r.point === null || Number(r.point) <= 0)) fail('status')
  // D17-10: an accessory has no lama kirim and no formula, and it is at or under its minimum exactly when the stock in the
  // warehouse is not above it (nothing is on order for an accessory).
  if (type === 'ACCESSORY' && (r.leadDays !== null || r.safetyQty !== null || r.formulaPoint !== null)) fail('batas minimum')
  if (type === 'ACCESSORY' && r.point !== null && Number(r.point) > 0 && (r.state === 'AT_OR_BELOW') !== (compareDecimal(r.freeQty, r.point) <= 0)) fail('status')
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
  const c = w.obj(x.counts, 'jumlah'); w.keys(c, ['items', 'at_or_below', 'manual', 'formula', 'not_enough_data', 'no_usage', 'not_set'], 'jumlah')
  const counts: MaterialCounts = { items: w.count(c.items, 'jumlah'), atOrBelow: w.count(c.at_or_below, 'jumlah'), manual: w.count(c.manual, 'jumlah'),
    formula: w.count(c.formula, 'jumlah'), notEnoughData: w.count(c.not_enough_data, 'jumlah'), noUsage: w.count(c.no_usage, 'jumlah'),
    notSet: w.count(c.not_set, 'jumlah') }
  // Every material has exactly one basis, of its own type's (D17-10: an accessory is MANUAL or NOT_SET, a fabric never NOT_SET).
  if (counts.manual + counts.formula + counts.notEnoughData + counts.noUsage + counts.notSet !== counts.items || counts.atOrBelow > counts.manual + counts.formula
    || (query.material_type === 'FABRIC' ? counts.notSet !== 0 : counts.formula + counts.notEnoughData + counts.noUsage !== 0)) fail('jumlah')
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
    || (query.filter === 'NOT_ENOUGH_DATA' && r.basis !== 'NOT_ENOUGH_DATA') || (query.filter === 'NOT_SET' && r.basis !== 'NOT_SET'))) fail('saringan')
  return { materialType: query.material_type, readAt: w.instant(x.read_at, 'waktu baca'), settings: w.settings(x.settings, 'pengaturan'),
    run: x.run === null ? null : w.run(x.run), canManage: w.bool(x.can_manage, 'hak ubah'), counts, page }
}

const canonical = (v: string) => {
  const [i, f = ''] = v.split('.'), frac = f.replace(/0+$/, '')
  return `${i.replace(/^0+(?=\d)/, '')}${frac ? `.${frac}` : ''}`
}
const sameDecimal = (a: string | null, b: string | null) => a === null || b === null ? a === b : canonical(a) === canonical(b)
/** erp_cp7_save_material_reorder_v1: a replay answers the first request's revision only (same payload), without the evaluation. */
export function parseMaterialSaveResult(value: unknown, payload: MaterialPayload, type: MaterialType): MaterialSaveResult {
  const what = 'hasil simpan bahan', o = w.obj(value, what), replay = w.bool(o.replay, what)
  w.keys(o, replay ? ['replay', 'material_id', 'revision'] : ['replay', 'material_id', 'revision', 'evaluation'], what)
  const r: MaterialSaveResult = { replay, materialId: w.uuidText(o.material_id, what), revision: w.count(o.revision, what),
    evaluation: replay ? null : row(o.evaluation, type) }
  if (r.materialId !== payload.material_id || r.revision !== payload.expected_revision + 1) fail(what)
  const e = r.evaluation
  if (e && (e.materialId !== r.materialId || e.settingRevision !== r.revision || !sameDecimal(e.leadDays, payload.lead_days)
    || (type === 'ACCESSORY' && (!sameDecimal(e.manualPoint, payload.manual_point) || (e.manualSource !== null) !== (payload.manual_point !== null))))) fail(what)
  return r
}

// ---------------------------------------------------------------- the form --
const typed = (v: string) => v.trim().replace(',', '.')
const leadText = /^\d{1,3}(\.\d{1,2})?$/, manualText = /^\d{1,13}(\.\d{1,4})?$/
/** save_material's rule in plain words ('' when it may be sent). A fabric carries a lama kirim only, an accessory its batas
 * minimum only (D17-10: the server refuses a lama kirim for an accessory). */
export function materialProblem(type: MaterialType, d: MaterialDraft): string {
  const lead = typed(d.lead), manual = typed(d.manual)
  if (type === 'ACCESSORY' && lead !== '') return 'Aksesori tidak memakai lama kirim. Muat ulang halaman lalu isi batas minimumnya saja.'
  if (lead !== '' && (!leadText.test(lead) || Number(lead) <= 0 || Number(lead) > 365))
    return 'Lama kirim: isi lebih dari 0 sampai 365 hari (boleh 2 angka di belakang koma), atau kosongkan.'
  if (type === 'ACCESSORY' && manual !== '' && !manualText.test(manual))
    return 'Batas minimum: isi 0 atau lebih (boleh 4 angka di belakang koma), atau kosongkan.'
  const r = d.reason.trim()
  if (r === '' || r.length > REASON_MAX) return type === 'FABRIC' ? 'Tulis alasannya (1 sampai 500 huruf), misalnya "supplier kirim 6 hari sesudah PO".'
    : 'Tulis alasannya (1 sampai 500 huruf), misalnya "pesan minimal 1.000 pcs, kirim dari Cina 30 hari".'
  return ''
}
export const materialDraftOf = (r: MaterialRow): MaterialDraft => ({ lead: (r.leadDays ?? '').replace('.', ','),
  manual: r.manualSource === 'ACCESSORY_MANUAL' ? (r.manualPoint ?? '').replace('.', ',') : '', reason: '' })
/** The draft differs from what is saved (the reason alone is not a change). */
export function materialChanged(type: MaterialType, r: MaterialRow, d: MaterialDraft): boolean {
  const lead = typed(d.lead), manual = typed(d.manual), saved = materialDraftOf(r)
  return !sameDecimal(lead || null, typed(saved.lead) || null) || (type === 'ACCESSORY' && !sameDecimal(manual || null, typed(saved.manual) || null))
}
export function materialPayload(r: Pick<MaterialRow, 'materialId' | 'settingRevision'>, type: MaterialType, d: MaterialDraft): MaterialPayload {
  if (materialProblem(type, d)) fail('isian bahan')
  const lead = typed(d.lead), manual = typed(d.manual)
  return { material_id: r.materialId, expected_revision: r.settingRevision ?? 0, lead_days: type === 'FABRIC' && lead !== '' ? lead : null,
    manual_point: type === 'ACCESSORY' && manual !== '' ? manual : null, reason: d.reason.trim() }
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
    CP7_FORMULA_MATERIAL_STALE: 'Batas minimum aksesori ini baru saja diubah di layar atau perangkat lain. Tekan "Muat ulang", periksa isinya, lalu simpan lagi bila masih perlu.',
    CP7_FORMULA_MATERIAL_INVALID: 'Isian belum sesuai: batas minimum 0 atau lebih, atau kosong, dan alasan 1 sampai 500 huruf. Aksesori tidak memakai lama kirim.',
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
    : `Jawaban server tidak sampai, jadi belum pasti ${type === 'FABRIC' ? 'lama kirim kain' : 'batas minimum aksesori'} ini tersimpan. Tekan "Simpan" lagi tanpa mengubah isian: permintaan yang sama dikirim ulang, jadi tidak tercatat dua kali. Atau tekan "Muat ulang" untuk melihat yang berlaku.`
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
  // An accessory (D17-10): its own minimum, or none yet.
  if (r.basis === 'NOT_SET') return 'Belum diisi'
  if (r.basis === 'MANUAL') return r.point !== null && Number(r.point) === 0 ? 'Manual 0: tidak pernah diingatkan' : 'Manual'
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
