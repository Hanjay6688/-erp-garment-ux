import type { Json } from './types/database.preconnect'
import type { ProductionEnvelope } from './productionRecovery'

// D14-14 gap G2: finish a Production Order from the connected HPP screen (UX demo HPP checklist: "Produksi sudah selesai ·
// PO berstatus FINISHED"), and reopen a finished one (owner D15-4). Closed parsers for
// scripts/cp7-src/cutting-correction/finish.sql and po-reopen.sql. How final the HPP is comes from the server's
// display_status only (Astra ASTRA-C17-05), never from the PO status.
export type PoFinishRow = { id: string; number: string; status: string; contractorName: string | null; fgPcs: number }
export type PoFinishList = { query: string; rows: PoFinishRow[]; total: number; offset: number; nextOffset: number | null }
export type PoFinishBlocker = { kind: string; qty: number | null }
export type PoFinishHpp = {
  displayStatus: string; engineCostState: string | null; total: string; qtyBasisPcs: number; perPcs: string | null
  pendingReasons: string[]; latestHppAt: string | null
}
export type PoFinishWorkspace = {
  poId: string; poNumber: string; poStatus: string; stage: string | null; contractorName: string | null
  fgPcs: number; fgLots: number; laundrySentPcs: number; laundryReturnedPcs: number; laundryClaimedPcs: number
  laundryGoodPcs: number; qcAccountedPcs: number; openBsCases: number; recostOpen: number; wipBalance: string
  hpp: PoFinishHpp; finishDate: string; reviewToken: string; eligible: boolean; blockers: PoFinishBlocker[]
}
export type PoFinishOutcome = {
  poId: string; poNumber: string; fgPcs: number; hpp: PoFinishHpp; residualClosed: string; wipAfter: string
  finishedOn: string; recostOpen: number
}
export type PoReopenWorkspace = {
  poId: string; poNumber: string; poStatus: string; stage: string | null; contractorName: string | null; fgPcs: number; fgLots: number
  fgUsedPcs: number; wipBalance: string; returningToWip: string; closeJournals: number; closedThrough: string | null; hpp: PoFinishHpp
  reopenDate: string; reviewToken: string; eligible: boolean; blockers: PoFinishBlocker[]
}
export type PoReopenOutcome = {
  poId: string; poNumber: string; status: string; stage: string | null; reversedJournals: number; returnedToWip: string; wipAfter: string
  hpp: PoFinishHpp; reopenedOn: string
}

const uuid = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/
const amount = /^-?[0-9]{1,18}\.[0-9]{2}$/
function fail(): never { throw new Error('Respons selesai PO tidak cocok dengan PO yang diperiksa.') }
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
function money(value: unknown) { const v = text(value); if (!amount.test(v)) fail(); return v }
function bool(value: unknown) { if (typeof value !== 'boolean') fail(); return value }
function date(value: unknown) { const v = text(value); if (!/^[0-9]{4}-[0-9]{2}-[0-9]{2}$/.test(v)) fail(); return v }

export function parsePoFinishList(value: unknown, query: string, offset: number): PoFinishList {
  const r = record(value)
  keys(r, ['contract_version', 'query', 'rows', 'total', 'offset', 'limit', 'next_offset', 'business_DML'])
  if (r.contract_version !== 'cp7.po-finish-list.v1' || r.business_DML !== false || r.query !== query.trim() || r.offset !== offset
    || r.limit !== 20 || !Array.isArray(r.rows) || r.rows.length > 20) fail()
  const rows = r.rows.map(v => {
    const x = record(v); keys(x, ['id', 'number', 'status', 'contractor_name', 'fg_pcs'])
    return { id: id(x.id), number: text(x.number), status: text(x.status), contractorName: nullableText(x.contractor_name), fgPcs: count(x.fg_pcs) }
  })
  const total = count(r.total), nextOffset = r.next_offset === null ? null : count(r.next_offset)
  if (rows.some(x => x.status === 'CANCELLED') || offset + rows.length > total
    || (nextOffset === null ? offset + rows.length < total : nextOffset !== offset + rows.length || nextOffset >= total)) fail()
  return { query: query.trim(), rows, total, offset, nextOffset }
}

function hpp(value: unknown): PoFinishHpp {
  const h = record(value)
  keys(h, ['display_status', 'engine_cost_state', 'total', 'qty_basis_pcs', 'per_pcs', 'pending_reasons', 'latest_hpp_at'])
  if (!Array.isArray(h.pending_reasons)) fail()
  return {
    displayStatus: text(h.display_status), engineCostState: nullableText(h.engine_cost_state), total: money(h.total),
    qtyBasisPcs: count(h.qty_basis_pcs), perPcs: h.per_pcs === null ? null : money(h.per_pcs),
    pendingReasons: h.pending_reasons.map(text), latestHppAt: nullableText(h.latest_hpp_at),
  }
}

export function parsePoFinishWorkspace(value: unknown, poId: string): PoFinishWorkspace {
  const r = record(value)
  keys(r, ['contract_version', 'po_id', 'po_number', 'po_status', 'stage', 'contractor_name', 'fg_pcs', 'fg_lots', 'laundry_sent_pcs',
    'laundry_returned_pcs', 'laundry_claimed_pcs', 'laundry_good_pcs', 'qc_accounted_pcs', 'open_bs_cases', 'recost_open', 'wip_balance',
    'hpp', 'finish_date', 'review_token', 'eligible', 'blockers', 'business_DML'])
  if (r.contract_version !== 'cp7.po-finish-workspace.v1' || r.business_DML !== false || r.po_id !== poId
    || typeof r.review_token !== 'string' || !/^[a-f0-9]{32}$/.test(r.review_token)) fail()
  const blockers = blockerList(r.blockers), eligible = bool(r.eligible)
  if (eligible !== (blockers.length === 0) || (eligible && (r.po_status === 'FINISHED' || r.po_status === 'CANCELLED'))) fail()
  return {
    poId, poNumber: text(r.po_number), poStatus: text(r.po_status), stage: nullableText(r.stage), contractorName: nullableText(r.contractor_name),
    fgPcs: count(r.fg_pcs), fgLots: count(r.fg_lots), laundrySentPcs: count(r.laundry_sent_pcs), laundryReturnedPcs: count(r.laundry_returned_pcs),
    laundryClaimedPcs: count(r.laundry_claimed_pcs), laundryGoodPcs: count(r.laundry_good_pcs), qcAccountedPcs: count(r.qc_accounted_pcs),
    openBsCases: count(r.open_bs_cases), recostOpen: count(r.recost_open), wipBalance: money(r.wip_balance), hpp: hpp(r.hpp),
    finishDate: date(r.finish_date), reviewToken: r.review_token, eligible, blockers,
  }
}

function blockerList(value: unknown) {
  if (!Array.isArray(value)) fail()
  return value.map(v => { const b = record(v); keys(b, ['kind', 'qty']); return { kind: text(b.kind), qty: b.qty === null ? null : count(b.qty) } })
}

export function parsePoReopenWorkspace(value: unknown, poId: string): PoReopenWorkspace {
  const r = record(value)
  keys(r, ['contract_version', 'po_id', 'po_number', 'po_status', 'stage', 'contractor_name', 'fg_pcs', 'fg_lots', 'fg_used_pcs', 'wip_balance',
    'returning_to_wip', 'close_journals', 'closed_through', 'hpp', 'reopen_date', 'review_token', 'eligible', 'blockers', 'business_DML'])
  if (r.contract_version !== 'cp7.po-reopen-workspace.v1' || r.business_DML !== false || r.po_id !== poId
    || typeof r.review_token !== 'string' || !/^[a-f0-9]{32}$/.test(r.review_token)) fail()
  const blockers = blockerList(r.blockers), eligible = bool(r.eligible)
  if (eligible !== (blockers.length === 0) || (eligible && r.po_status !== 'FINISHED')) fail()
  return {
    poId, poNumber: text(r.po_number), poStatus: text(r.po_status), stage: nullableText(r.stage), contractorName: nullableText(r.contractor_name),
    fgPcs: count(r.fg_pcs), fgLots: count(r.fg_lots), fgUsedPcs: count(r.fg_used_pcs), wipBalance: money(r.wip_balance),
    returningToWip: money(r.returning_to_wip), closeJournals: count(r.close_journals),
    closedThrough: r.closed_through === null ? null : date(r.closed_through), hpp: hpp(r.hpp), reopenDate: date(r.reopen_date),
    reviewToken: r.review_token, eligible, blockers,
  }
}

export function poReopenPayload(w: PoReopenWorkspace, reason: string): Json {
  const why = reason.trim()
  if (!w.eligible || why.length < 5 || why.length > 1000) fail()
  return { action: 'REOPEN', po_id: w.poId, review_token: w.reviewToken, change_reason: why }
}

export function validatePoReopenOutcome(value: unknown, envelope: ProductionEnvelope): PoReopenOutcome {
  const r = record(value), p = record(envelope.payload)
  keys(r, ['contract_version', 'kind', 'action', 'request_id', 'po_id', 'po_number', 'result'])
  if (envelope.action !== 'REOPEN_PO' || p.action !== 'REOPEN' || r.contract_version !== 'cp7.po-reopen-outcome.v1' || r.kind !== 'COMMITTED_OUTCOME'
    || r.action !== 'REOPEN' || r.request_id !== envelope.id || r.po_id !== p.po_id) fail()
  const x = record(r.result)
  keys(x, ['status', 'stage', 'reversed_journals', 'returned_to_wip', 'wip_after', 'hpp', 'reopened_on'])
  if (x.status === 'FINISHED' || x.status === 'CANCELLED') fail()
  return {
    poId: id(r.po_id), poNumber: text(r.po_number), status: text(x.status), stage: nullableText(x.stage), reversedJournals: count(x.reversed_journals),
    returnedToWip: money(x.returned_to_wip), wipAfter: money(x.wip_after), hpp: hpp(x.hpp), reopenedOn: date(x.reopened_on),
  }
}

export function poFinishPayload(w: PoFinishWorkspace, reason: string): Json {
  const why = reason.trim()
  if (!w.eligible || why.length < 5 || why.length > 1000) fail()
  return { action: 'FINISH', po_id: w.poId, review_token: w.reviewToken, change_reason: why }
}

export function validatePoFinishOutcome(value: unknown, envelope: ProductionEnvelope): PoFinishOutcome {
  const r = record(value), p = record(envelope.payload)
  keys(r, ['contract_version', 'kind', 'action', 'request_id', 'po_id', 'po_number', 'result'])
  if (envelope.action !== 'FINISH_PO' || p.action !== 'FINISH' || r.contract_version !== 'cp7.po-finish-outcome.v1' || r.kind !== 'COMMITTED_OUTCOME'
    || r.action !== 'FINISH' || r.request_id !== envelope.id || r.po_id !== p.po_id) fail()
  const x = record(r.result)
  keys(x, ['status', 'fg_pcs', 'hpp', 'residual_closed', 'wip_after', 'finished_on', 'recost_open'])
  if (x.status !== 'FINISHED' || x.wip_after !== '0.00') fail()
  return {
    poId: id(r.po_id), poNumber: text(r.po_number), fgPcs: count(x.fg_pcs), hpp: hpp(x.hpp), residualClosed: money(x.residual_closed),
    wipAfter: money(x.wip_after), finishedOn: date(x.finished_on), recostOpen: count(x.recost_open),
  }
}

const blockerKinds: Record<string, (qty: number | null) => string> = {
  PO_CANCELLED: () => 'PO ini sudah dibatalkan.',
  ALREADY_FINISHED: () => 'PO ini sudah selesai; HPP-nya sudah final.',
  LAUNDRY_OUTSTANDING: qty => `${qty ?? '?'} pcs masih di laundry (belum kembali atau belum diselesaikan klaimnya).`,
  SOURCE_UNACCOUNTED: qty => `${qty ?? '?'} pcs hasil potong belum dijahit dan dikirim ke laundry atau lewat QC langsung.`,
  QC_UNACCOUNTED: qty => `${qty ?? '?'} pcs GOOD dari laundry belum melewati QC.`,
  OPEN_BS: qty => `${qty ?? '?'} kasus BS/rework masih terbuka.`,
  NO_FG_OUTPUT: () => 'Belum ada barang jadi dari PO ini.',
  NOT_FINISHED: () => 'PO ini belum selesai, jadi tidak perlu dibuka ulang.',
  FG_USED: qty => `${qty ?? '?'} pcs barang jadi PO ini sudah terjual, dipesan di draft penjualan, disesuaikan, atau dipindah. Batalkan dulu transaksinya.`,
  PERIOD_CLOSED: () => 'Pembukuan PO ini (atau hari ini) ada di periode yang sudah ditutup. Periode tutup tidak dibuka otomatis.',
}
export function poFinishBlockerText(b: PoFinishBlocker) {
  return blockerKinds[b.kind]?.(b.qty) ?? `Ada catatan lain yang menahan (${b.kind}).`
}
const reasonTexts: Record<string, string> = {
  BELUM_ADA_FG: 'belum ada barang jadi',
  HPP_CURRENT_BELUM_TERBENTUK: 'ada lot barang jadi yang belum punya HPP',
  PRODUKSI_BELUM_FINISHED: 'PO belum diselesaikan',
  'BIAYA_LAUNDRY_MASIH_ESTIMASI/BELUM_FINAL': 'biaya laundry masih perkiraan (tagihan belum final)',
  HPP_ENGINE_MASIH_ESTIMATED: 'HPP masih memakai biaya perkiraan',
  RECOST_BELUM_SELESAI: 'hitung ulang HPP PO ini masih antre atau gagal (proses di "Hitung ulang HPP" di atas)',
  'BS/REWORK_BELUM_SELESAI': 'masih ada kasus BS/rework terbuka',
  'BIAYA_KERJA/BOM_BELUM_DIKONFIRMASI': 'BOM kerja / tarif mandor belum dikunci',
  ADA_KOMPONEN_KERJA_BELUM_PERNAH_DIPOST: 'ada komponen upah yang belum pernah dicatat selesai',
  SNAPSHOT_BIAYA_AKSESORI_BELUM_ADA: 'biaya aksesori lot belum dibekukan',
}
export function poFinishReasonText(code: string) { return reasonTexts[code] ?? code }
const statusTexts: Record<string, string> = {
  BELUM_ADA_HPP: 'Belum ada HPP',
  SEMENTARA: 'Sementara (PO belum selesai)',
  BELUM_LENGKAP: 'Belum lengkap, masih bisa berubah',
  LENGKAP_BERDASARKAN_DATA_SAAT_INI: 'Final, lengkap menurut data saat ini',
}
export function poFinishStatusText(code: string) { return statusTexts[code] ?? code }
