// OW-04b part 3 (retest 23 Oct 2026): when the customer-credit product must refuse a return, a payment, Edit retur or
// Benerin nota, the screen names the reason and the next step, never "belum dapat diperiksa". Three retained refusals
// carry their reason codes in DETAIL (scripts/cp7_credit_followups/followups.sql). The detail is parsed strictly: an
// unreadable detail never becomes a guessed reason; the screen then shows the server code and asks to report it.
export const creditRefusalReasons = ['PRIOR_CREDIT_RETURN', 'CREDIT_APPLIED_TO_INVOICE', 'NOTE_REVISED', 'RETURN_CORRECTED',
  'SOURCE_HISTORY_BLOCKED', 'UNCLASSIFIED'] as const
export type CreditRefusalReason = typeof creditRefusalReasons[number]
export type CreditRefusalKind = 'INITIAL_SOURCE_FAMILY' | 'SOURCE_CORRECTION' | 'REGISTERED_SOURCE_MUTATION'
export type CreditRefusalAction = 'PAYMENT' | 'PAYMENT_REVERSE' | 'RETURN_REVERSE' | 'SALE_REVERSE'
export type CreditRefusal = { kind: CreditRefusalKind; action: CreditRefusalAction | null; reasons: CreditRefusalReason[]; sourceBlockers: string[] }

const CONTRACT = 'cp7.credit-followups.refusal.v1'
const KINDS: Record<string, CreditRefusalKind> = {
  CP7_CREDIT_INITIAL_SOURCE_FAMILY_UNSUPPORTED: 'INITIAL_SOURCE_FAMILY',
  CP7_CREDIT_SOURCE_CORRECTION_ADAPTER_UNIMPLEMENTED: 'SOURCE_CORRECTION',
  CP7_CREDIT_REGISTERED_SOURCE_MUTATION_REQUIRES_BOUND_RECONCILIATION: 'REGISTERED_SOURCE_MUTATION',
}
const ALLOWED: Record<CreditRefusalKind, readonly CreditRefusalReason[]> = {
  INITIAL_SOURCE_FAMILY: ['SOURCE_HISTORY_BLOCKED', 'NOTE_REVISED', 'PRIOR_CREDIT_RETURN', 'CREDIT_APPLIED_TO_INVOICE', 'RETURN_CORRECTED', 'UNCLASSIFIED'],
  SOURCE_CORRECTION: ['NOTE_REVISED', 'RETURN_CORRECTED', 'UNCLASSIFIED'],
  REGISTERED_SOURCE_MUTATION: ['PRIOR_CREDIT_RETURN', 'CREDIT_APPLIED_TO_INVOICE', 'UNCLASSIFIED'],
}
const ACTIONS: readonly CreditRefusalAction[] = ['PAYMENT', 'PAYMENT_REVERSE', 'RETURN_REVERSE', 'SALE_REVERSE']
const SERVER_CODE = /^[A-Z][A-Z0-9_]{2,99}$/

/** Strict: exact keys, contract, kind, action rule, known unique reasons, blocker codes only with SOURCE_HISTORY_BLOCKED. */
export function parseCreditRefusalDetail(details: unknown, kind: CreditRefusalKind): CreditRefusal | null {
  if (typeof details !== 'string') return null
  let d: unknown
  try { d = JSON.parse(details) } catch { return null }
  if (!d || typeof d !== 'object' || Array.isArray(d)) return null
  const r = d as Record<string, unknown>, keys = ['action', 'contract', 'reasons', 'refusal', 'source_blockers']
  if (Object.keys(r).sort().join() !== keys.join() || r.contract !== CONTRACT || r.refusal !== kind) return null
  if (kind === 'REGISTERED_SOURCE_MUTATION' ? !ACTIONS.includes(r.action as CreditRefusalAction) : r.action !== null) return null
  const reasons = r.reasons, blockers = r.source_blockers
  if (!Array.isArray(reasons) || !reasons.length || new Set(reasons).size !== reasons.length
    || !reasons.every(x => ALLOWED[kind].includes(x as CreditRefusalReason))
    || reasons.includes('UNCLASSIFIED') && reasons.length !== 1) return null
  if (!Array.isArray(blockers) || blockers.length > 20 || new Set(blockers).size !== blockers.length
    || !blockers.every(x => typeof x === 'string' && SERVER_CODE.test(x))
    || blockers.length > 0 && !reasons.includes('SOURCE_HISTORY_BLOCKED')) return null
  return { kind, action: r.action as CreditRefusalAction | null, reasons: reasons as CreditRefusalReason[], sourceBlockers: blockers as string[] }
}

const HEADERS: Record<CreditRefusalKind | CreditRefusalAction, string> = {
  INITIAL_SOURCE_FAMILY: 'Retur ini belum bisa dicatat dan diselesaikan (uang kembali atau saldo kredit) pada invoice ini.',
  SOURCE_CORRECTION: 'Transaksi saldo kredit atau pembatalan ini belum bisa diproses pada invoice ini.',
  REGISTERED_SOURCE_MUTATION: 'Perubahan ini belum bisa dilakukan pada invoice ini.',
  PAYMENT: 'Pembayaran baru belum bisa dicatat pada invoice ini.',
  PAYMENT_REVERSE: 'Pembayaran invoice ini belum bisa dibatalkan lewat Benerin nota atau pembatalan berantai.',
  RETURN_REVERSE: 'Retur pada invoice ini belum bisa diubah lewat Edit retur, Benerin nota, atau pembatalan berantai.',
  SALE_REVERSE: 'Nota ini belum bisa dibetulkan (Benerin nota) atau dibatalkan.',
}
const REASONS: Record<CreditRefusalReason, string> = {
  PRIOR_CREDIT_RETURN: 'invoice ini sudah punya retur yang menjadi saldo kredit pelanggan atau uang kembali',
  CREDIT_APPLIED_TO_INVOICE: 'invoice ini pernah dibayar memakai saldo kredit pelanggan',
  NOTE_REVISED: 'invoice ini pernah dibetulkan lewat Benerin nota, atau merupakan nota penggantinya',
  RETURN_CORRECTED: 'ada retur pada invoice ini yang pernah dibetulkan lewat Edit retur',
  SOURCE_HISTORY_BLOCKED: 'riwayat jurnal invoice ini belum lengkap atau tidak cocok dengan dokumennya',
  UNCLASSIFIED: 'riwayat invoice ini belum bisa dicocokkan',
}
const NOT_YET = 'Aplikasi belum bisa menyelesaikan keadaan ini; lanjutan retur dan saldo kredit (butir OW-04b) belum selesai. '
  + 'Membatalkan pemakaian saldo, pembayaran, atau retur sebelumnya tidak membuka jalan ini, karena riwayat kredit tetap disimpan. '
  + 'Catat nomor invoice serta barang dan nilainya, lalu beri tahu admin; jangan mencatatnya lewat menu lain.'
const report = (code: string) => `Muat ulang invoice dan periksa lagi; bila tetap muncul, beri tahu admin dengan kode ${code}.`

function namedRefusal(code: string, kind: CreditRefusalKind, details: unknown): string {
  const parsed = parseCreditRefusalDetail(details, kind)
  if (!parsed) return `${HEADERS[kind]} Alasan rinci dari server tidak dapat dibaca. Langkah berikutnya: ${report(code)}`
  const header = HEADERS[parsed.action ?? kind]
  const why = parsed.reasons.map(x => REASONS[x]).join('; ')
  const steps: string[] = []
  if (parsed.reasons.some(x => x === 'PRIOR_CREDIT_RETURN' || x === 'CREDIT_APPLIED_TO_INVOICE' || x === 'NOTE_REVISED' || x === 'RETURN_CORRECTED')) steps.push(NOT_YET)
  if (parsed.reasons.includes('SOURCE_HISTORY_BLOCKED')) steps.push('Beri tahu admin nomor invoice ini'
    + (parsed.sourceBlockers.length ? ` dan kode pemeriksaan ${parsed.sourceBlockers.join(', ')}` : '')
    + '; jurnal invoice perlu diperiksa dulu sebelum dicatat.')
  if (parsed.reasons.includes('UNCLASSIFIED')) steps.push(report(code))
  return `${header} Alasannya: ${why}. Langkah berikutnya: ${steps.join(' ')}`
}

const SAME_DATA = 'Data HPP atau akun berubah saat diperiksa. Muat ulang invoice, lalu periksa lagi.'
const HPP_BOOK = 'HPP barang ini di buku belum cocok dengan perhitungan HPP, jadi nilai stok retur belum bisa dihitung dengan benar. '
const CREDIT_ACCOUNT = 'Akun saldo kredit yang dipilih tidak memenuhi syarat (akun kewajiban aktif yang saldonya cocok dengan catatan saldo kredit). '
  + 'Pilih akun lain dari daftar akun saldo kredit, lalu periksa lagi.'
// Other refusals the return settlement can meet before its quote or save, each with the user's next step.
const EXACT: Record<string, string | ((code: string) => string)> = {
  CP7_SALES_REVIEW_CHANGED: 'Invoice berubah sejak dibuka. Muat ulang invoice, lalu periksa lagi.',
  AH_RETURN_EXCEEDS_ORIGINAL_ALLOCATION: 'Jumlah retur melebihi sisa barang yang boleh diretur dari penjualan ini. Kurangi jumlah PCS, lalu periksa lagi.',
  CP7_CREDIT_RETURN_QTY_SOURCE_INVALID: 'Jumlah retur melebihi barang terjual yang masih tercatat pada lot ini. Kurangi jumlah PCS dan muat ulang invoice.',
  CP7_CREDIT_REFUND_PRODUCT_VALUE_EXCEEDED: 'Nilai retur melebihi sisa nilai barang ini di invoice. Kurangi nilai pengurang tagihan, lalu periksa lagi.',
  CP7_CREDIT_RETURN_PHYSICAL_DATE_INVALID: 'Waktu barang kembali harus sesudah waktu invoice dan tidak boleh di masa depan. Betulkan waktu retur (WIB), lalu periksa lagi.',
  CP7_CREDIT_REFUND_FUTURE_DATE: 'Waktu pengembalian uang tidak boleh di masa depan. Betulkan waktunya (WIB), lalu periksa lagi.',
  CP7_CREDIT_RETURN_SOURCE_OR_DESTINATION_CHANGED: 'Alokasi penjualan atau gudang penerima berubah, tidak aktif, atau bukan gudang barang jadi. Muat ulang sumber retur dan pilih gudang barang jadi yang aktif.',
  CP7_CREDIT_LIABILITY_ACCOUNT_INELIGIBLE: CREDIT_ACCOUNT,
  CP7_CREDIT_UNTRACKED_LIABILITY_JOURNAL: CREDIT_ACCOUNT,
  CP7_CREDIT_LIABILITY_CUSTOMER_MISSING: CREDIT_ACCOUNT,
  CP7_CREDIT_LIABILITY_RECONCILIATION_FAILED: CREDIT_ACCOUNT,
  CP7_CREDIT_REFUND_CASH_ACCOUNT_INELIGIBLE: 'Rekening pengembalian uang tidak memenuhi syarat. Pilih rekening kas atau bank aktif lain, lalu periksa lagi.',
  CP7_CREDIT_HPP_LOCK_SET_CHANGED: SAME_DATA,
  CP7_CREDIT_HPP_SUPPORT_CHANGED_DURING_READ: SAME_DATA,
  CP7_CREDIT_OPENING_HPP_SOURCE_CHANGED_DURING_READ: SAME_DATA,
  CP7_CREDIT_HPP_ACCOUNT_SOURCE_CHANGED: SAME_DATA,
  CP7_CREDIT_HPP_TARGET_BOOK_NOT_RECONCILED: code => HPP_BOOK + `Beri tahu admin dengan kode ${code} agar HPP barang atau PO ini dicocokkan dulu dengan buku.`,
  CP7_CREDIT_HPP_CANONICAL_TARGET_MISMATCH: code => HPP_BOOK + `Beri tahu admin dengan kode ${code} agar HPP barang atau PO ini dicocokkan dulu dengan buku.`,
  CP7_CREDIT_HPP_VECTOR_NOT_CONSERVED: code => HPP_BOOK + `Beri tahu admin dengan kode ${code} agar HPP barang atau PO ini dicocokkan dulu dengan buku.`,
  CP7_CREDIT_POSITIVE_HPP_ZERO_VECTOR_UNPROVEN: code => HPP_BOOK + `Beri tahu admin dengan kode ${code} agar HPP barang atau PO ini dicocokkan dulu dengan buku.`,
  CP7_CREDIT_NONFINITE_HPP_SOURCE: code => HPP_BOOK + `Beri tahu admin dengan kode ${code} agar HPP barang atau PO ini dicocokkan dulu dengan buku.`,
  CP7_CREDIT_NEGATIVE_HPP_SOURCE: code => HPP_BOOK + `Beri tahu admin dengan kode ${code} agar HPP barang atau PO ini dicocokkan dulu dengan buku.`,
}

/** Plain-language reason and next step for a credit/settlement refusal; null when the code is not a credit refusal. */
export function creditRefusalMessage(message: unknown, details: unknown): string | null {
  if (typeof message !== 'string') return null
  const code = message.trim()
  if (!SERVER_CODE.test(code)) return null
  const kind = KINDS[code]
  if (kind) return namedRefusal(code, kind, details)
  const exact = EXACT[code]
  if (exact) return typeof exact === 'function' ? exact(code) : exact
  if (code.startsWith('CP7_CREDIT_')) return `Permintaan ini ditolak oleh pemeriksaan saldo kredit (kode ${code}). ${report(code)}`
  return null
}

/** A server refusal outside the credit codes: name its code only when it is a bare code, never raw private text. */
export function serverRefusalCode(message: unknown): string | null {
  return typeof message === 'string' && SERVER_CODE.test(message.trim()) ? message.trim() : null
}
