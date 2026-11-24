// Indonesian text for the named refusals and blockers of "Benerin penerimaan"
// and "Benerin nama / kode bahan" (schema cp7_receipt_fix). The only caller is
// normalizeClientError in ./clientError, so every page shows one translation;
// 42501 access refusals keep its generic no-permission message.
export const blockerLabels: Record<string, string> = {
  CP7_RECEIPT_FIX_SHARED_INVOICE_RETURN_ACTIVE: 'Invoice supplier ini juga mencakup penerimaan lain yang sudah punya retur ke supplier. Batalkan retur itu dulu.',
  CP7_RECEIPT_FIX_DRAFT_ROLL_USE: 'Roll dari penerimaan ini sudah dipakai di draft potong atau draft transfer. Posting atau batalkan draft itu dulu.',
  CP7_RECEIPT_FIX_PENDING_CHILD_REVIEW_REQUIRED: 'Masih ada draft invoice, retur, pembayaran atau koreksi harga untuk penerimaan ini. Selesaikan atau hapus draft tersebut dulu.',
  CP7_RECEIPT_FIX_RETURN_ACTIVE: 'Ada retur ke supplier yang sudah diposting dari penerimaan ini. Batalkan retur itu dulu.',
  CP7_RECEIPT_FIX_COST_CORRECTION_ACTIVE: 'Ada koreksi harga lama yang aktif. Batalkan koreksi harga itu dulu.',
  CP7_RECEIPT_FIX_SUPPLIER_CREDIT_ACTIVE: 'Kredit supplier dari penerimaan ini sudah dipindah ke tagihan lain. Kembalikan pemindahannya dulu.',
  CP7_RECEIPT_FIX_POCKET_ORIGIN_ACTIVE: 'Bahan dari penerimaan ini sudah dipakai sebagai kain kantong. Batalkan pemakaian kain kantong itu dulu.',
  CP7_RECEIPT_FIX_OPENING_IMPORT_USE_IMPORT_WORKFLOW: 'Penerimaan ini berasal dari impor saldo awal. Betulkan lewat alur impor data awal.',
  CP7_RECEIPT_FIX_ACTIVE_POSTED_ONLY: 'Hanya penerimaan yang sudah diterima (aktif) yang bisa dibenerin.',
}

/** Document kinds named by a blocker (cp7_receipt_fix.blockers). */
export const blockerDocumentLabels: Record<string, string> = {
  SUPPLIER_INVOICE: 'Invoice supplier', SUPPLIER_RETURN: 'Retur supplier', SUPPLIER_PAYMENT: 'Pembayaran supplier', COST_CORRECTION: 'Koreksi harga',
  CUTTING_GROUP: 'Draft potong', MATERIAL_TRANSFER: 'Draft transfer', MATERIAL_PURCHASE: 'Penerimaan', POCKET_USE: 'Pemakaian kain kantong', OPENING_IMPORT: 'Impor saldo awal',
}
const changed = 'berubah sejak diperiksa. Muat ulang lalu periksa lagi.'
const refusalLabels: Record<string, string> = {
  CP7_RECEIPT_FIX_REVIEW_CHANGED: `Penerimaan, pemakaian roll, pembayaran, atau invoice ${changed}`,
  CP7_RECEIPT_FIX_ACTIVE_POSTED_ONLY: 'Penerimaan ini sudah dibetulkan atau dibatalkan. Buka penerimaan yang berlaku.',
  CP7_RECEIPT_FIX_SOURCE_SUPERSEDED: 'Penerimaan ini sudah dibetulkan atau dibatalkan. Buka penerimaan yang berlaku.',
  CP7_RECEIPT_FIX_NOT_FOUND: 'Penerimaan tidak ditemukan.',
  CP7_RECEIPT_FIX_FIELDS: 'Isian pembetulan belum lengkap atau formatnya belum sesuai.',
  CP7_RECEIPT_FIX_REQUEST_CHANGED: 'Permintaan pembetulan berubah. Periksa hasil permintaan sebelumnya sebelum mengirim tindakan baru.',
  CP7_RECEIPT_FIX_ROLL_BELOW_USE: 'Jumlah roll tidak boleh di bawah jumlah yang sudah dipakai atau dipindah dari gudang penerimaan',
  CP7_RECEIPT_FIX_REMOVED_ROLL_USED: 'Roll yang sudah dipakai tidak boleh dihapus dari penerimaan',
  CP7_RECEIPT_FIX_LINE_BELOW_USE: 'Jumlah barang tidak boleh di bawah jumlah yang sudah keluar dari gudang penerimaan',
  CP7_RECEIPT_FIX_ROLL_USE_UNSUPPORTED: 'Roll ini sudah dipakai selain untuk potong. Untuk salah bahan, batalkan pemakaian itu dulu, betulkan penerimaan, lalu catat ulang pemakaiannya',
  CP7_RECEIPT_FIX_ROLL_NUMBER_TAKEN: 'Nomor roll sudah dipakai roll lain dari bahan yang sama (roll baru juga tidak boleh memakai nomor yang sekarang masih dipakai)',
  CP7_RECEIPT_FIX_PURCHASE_NUMBER_TAKEN: 'Nomor surat jalan ini sudah dipakai penerimaan lain',
  CP7_RECEIPT_FIX_DATE_FUTURE: 'Tanggal tidak boleh di masa depan.',
  CP7_RECEIPT_FIX_DATE_AFTER_USE: 'Barang ini sudah dipakai atau dipindah sebelum tanggal datang yang baru. Pilih tanggal datang yang tidak sesudah pemakaian pertamanya',
  CP7_RECEIPT_FIX_LOCATION_USED: 'Barang ini sudah dipakai atau dipindah dari gudang lama, jadi gudangnya tidak bisa diganti. Catat transfer ke gudang yang benar',
  CP7_RECEIPT_FIX_SUPPLIER_SHARED_INVOICE: 'Invoice supplier penerimaan ini juga mencakup penerimaan lain dari supplier lama, jadi suppliernya tidak bisa diganti di sini.',
  CP7_RECEIPT_FIX_SUPPLIER_ADVANCE_PAYMENT: 'Penerimaan ini dibayar dari uang muka saldo awal supplier lama, jadi suppliernya tidak bisa diganti di sini.',
  CP7_RECEIPT_FIX_PURCHASE_NUMBER_LENGTH: 'Nomor surat jalan harus 1–40 huruf.',
  CP7_RECEIPT_FIX_INVOICE_NUMBER_TAKEN: 'Nomor invoice ini sudah dipakai invoice lain dari supplier yang sama',
  CP7_RECEIPT_FIX_ROLL_LINEAGE: `Daftar roll ${changed}`,
  CP7_RECEIPT_FIX_ITEM_LINEAGE: `Daftar barang ${changed}`,
  CP7_RECEIPT_FIX_MATERIAL_KIND_CHANGED: 'Bahan pengganti harus jenis dan satuan yang sama dengan bahan semula.',
  CP7_RECEIPT_FIX_MATERIAL_INACTIVE: 'Bahan pengganti sedang tidak aktif.',
  CP7_RECEIPT_FIX_MATERIAL_NOT_FOUND: 'Bahan tidak ditemukan.',
  CP7_RECEIPT_FIX_FABRIC_ROLLS_REQUIRED: 'Bahan kain dicatat per roll.',
  CP7_RECEIPT_FIX_NON_ROLL_QTY_REQUIRED: 'Bahan selain kain dicatat dengan jumlah, tanpa roll.',
  CP7_RECEIPT_FIX_INVOICE_DECISION_REQUIRED: 'Penerimaan ini sudah punya invoice supplier. Periksa baris invoice yang ikut dibetulkan.',
  CP7_RECEIPT_FIX_INVOICE_EXCEEDS_RECEIPT: 'Jumlah di invoice melebihi jumlah penerimaan yang dibetulkan.',
  CP7_RECEIPT_FIX_INVOICED_LINE_ESTIMATE_REQUIRED: 'Baris yang punya invoice tetap memakai harga perkiraan; harga final ada di invoice.',
  CP7_RECEIPT_FIX_INVOICE_DISCOUNT: 'Diskon invoice tidak boleh melebihi nilai barisnya.',
  CP7_RECEIPT_FIX_INVOICE_SET: `Invoice supplier ${changed}`,
  CP7_RECEIPT_FIX_INVOICE_LINE_SET: `Baris invoice supplier ${changed}`,
  CP7_RECEIPT_FIX_INVOICE_LINE_ORPHAN: 'Setiap baris invoice harus tetap terhubung ke barang penerimaan yang dibetulkan.',
  CP7_RECEIPT_FIX_CREDIT_ALLOCATION_REQUIRED: 'Sudah dibayar lebih dari total yang benar. Pilih nota lain dari supplier yang sama untuk menampung kelebihan bayar',
  CP7_RECEIPT_FIX_CREDIT_ALLOCATION_MISMATCH: 'Jumlah kredit ke nota lain harus sama dengan kelebihan bayar',
  CP7_RECEIPT_FIX_CREDIT_TARGET_INVALID: 'Nota tujuan kredit harus nota lain yang aktif dari supplier yang sama, masing-masing sekali.',
  CP7_RECEIPT_FIX_CREDIT_TARGET_EXCEEDS_REMAINING: 'Kredit melebihi sisa tagihan nota tujuan',
  CP7_RECEIPT_FIX_CREDIT_TARGET_AFTER_ADVANCE_USE: 'Kelebihan bayar ini berasal dari uang muka saldo awal. Pilih nota yang tanggalnya sama atau sebelum tanggal pemakaian uang muka itu',
  CP7_RECEIPT_FIX_CREDIT_CENTS: 'Jumlah kredit paling banyak dua angka di belakang koma.',
  CP7_MATERIAL_NAME_TAKEN: 'Nama ini sudah dipakai bahan lain. Bila itu memang bahan yang sama, jangan digabung lewat ganti nama.',
  CP7_MATERIAL_NAME_UNCHANGED: 'Nama dan kode baru sama dengan yang sekarang.',
  CP7_MATERIAL_NAME_SKU_TAKEN: 'Kode ini sudah dipakai bahan lain. Bila itu memang bahan yang sama, jangan digabung lewat ganti kode.',
  CP7_MATERIAL_NAME_SKU_LENGTH: 'Tulis kode bahan yang benar (1–60 huruf).',
  CP7_MATERIAL_NAME_REVIEW_CHANGED: `Data bahan ${changed}`,
  CP7_MATERIAL_NAME_REASON_REQUIRED: 'Tulis alasan pembetulan (minimal 5 huruf).',
  CP7_MATERIAL_NAME_LENGTH: 'Tulis nama bahan yang benar (1–150 huruf).',
  CP7_MATERIAL_NAME_FIELDS: 'Isian ganti nama belum lengkap atau formatnya belum sesuai.',
  CP7_MATERIAL_NAME_NOT_FOUND: 'Bahan tidak ditemukan.',
  CP7_MATERIAL_NAME_REQUEST_CHANGED: 'Permintaan ganti nama berubah. Periksa hasil permintaan sebelumnya sebelum mengirim tindakan baru.',
}
const detailWords: [RegExp, string][] = [[/\bpaid\b/g, 'dibayar'], [/\bcorrected\b/g, 'dibetulkan'], [/\bused\b/g, 'terpakai'], [/\bcredit\b/g, 'kredit'], [/\ballocated\b/g, 'dialokasikan']]
/** Indonesian message for a cp7_receipt_fix refusal, or null for any other error. */
export function receiptCorrectionMessage(message: string): string | null {
  const m = /^(CP7_(?:RECEIPT_FIX|MATERIAL_NAME)_[A-Z_]+)(?:\s+([\s\S]*))?$/.exec(message.trim())
  if (!m) return null
  const [, code, rest = ''] = m
  if (code === 'CP7_RECEIPT_FIX_DEPENDENCY') {
    const reasons = rest.split(',').map(c => blockerLabels[c.trim()]).filter(Boolean)
    return reasons.length ? reasons.join(' ') : null
  }
  const label = refusalLabels[code]
  if (!label) return null
  const detail = rest.trim() ? ` (${detailWords.reduce((s, [w, t]) => s.replace(w, t), rest.trim())})` : ''
  return label.replace(/\.$/, '') + detail + '.'
}
