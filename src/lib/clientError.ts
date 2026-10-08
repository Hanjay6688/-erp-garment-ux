import { receiptCorrectionMessage } from './receiptCorrectionMessages'
import { planV2Message } from './planV2Messages'
import { reportV2Message } from './reportV2Messages'

export type ClientErrorCode =
  | 'AUTH_FAILED'
  | 'AUTH_REQUIRED'
  | 'FORBIDDEN'
  | 'PROFILE_API_SCHEMA_UNAVAILABLE'
  | 'NOT_FOUND'
  | 'VERSION_CONFLICT'
  | 'DATA_CONFLICT'
  | 'DUPLICATE_REQUEST'
  | 'RETRYABLE_CONFLICT'
  | 'REJECTED'
  | 'BACKEND_UNAVAILABLE'

export class ClientAppError extends Error {
  readonly code: ClientErrorCode
  readonly retryable: boolean

  constructor(code: ClientErrorCode, message: string, retryable = false) {
    super(message)
    this.name = 'ClientAppError'
    this.code = code
    this.retryable = retryable
  }
}

type ErrorLike = {
  code?: unknown
  status?: unknown
  message?: unknown
  details?: unknown
}

function errorLike(error: unknown): ErrorLike {
  return error !== null && typeof error === 'object' ? error as ErrorLike : {}
}

export function normalizeClientError(error: unknown): ClientAppError {
  if (error instanceof ClientAppError) return error

  const candidate = errorLike(error)
  const code = typeof candidate.code === 'string' ? candidate.code.toUpperCase() : ''
  const status = typeof candidate.status === 'number' ? candidate.status : Number.NaN
  const rawMessage = typeof candidate.message === 'string' ? candidate.message.toLowerCase() : ''

  if (code === 'PGRST106') {
    return new ClientAppError(
      'PROFILE_API_SCHEMA_UNAVAILABLE',
      'Facade self-profile Auth belum tersedia secara aman di Data API UAT.',
    )
  }
  if (status === 401 || code === 'PGRST301') {
    return new ClientAppError('AUTH_REQUIRED', 'Sesi berakhir. Silakan masuk ulang.')
  }
  if (status === 403 || code === '42501') {
    return new ClientAppError('FORBIDDEN', 'Akun tidak memiliki izin untuk operasi ini.')
  }
  if (code === 'PGRST116') {
    return new ClientAppError('NOT_FOUND', 'Data yang diminta tidak ditemukan.')
  }
  if (rawMessage.includes('request_uuid') || rawMessage.includes('idempot')) {
    return new ClientAppError('DUPLICATE_REQUEST', 'Identitas permintaan bertabrakan. Muat ulang status sebelum mengirim ulang.')
  }
  if (code === '23505') {
    return new ClientAppError('DATA_CONFLICT', 'Data bertabrakan dengan catatan yang sudah ada. Muat ulang dan periksa data sebelum menyimpan lagi.')
  }
  const planV2 = planV2Message(candidate.message, candidate.details)
  if (planV2) return new ClientAppError('REJECTED', planV2)
  const reportV2 = reportV2Message(candidate.message)
  if (reportV2) return new ClientAppError('REJECTED', reportV2)
  if (code === '40001' || code === '40P01') {
    return new ClientAppError('RETRYABLE_CONFLICT', 'Terjadi benturan sementara. Muat ulang sebelum mencoba lagi.', true)
  }
  if (rawMessage.includes('row_version') || rawMessage.includes('expected_version')) {
    return new ClientAppError('VERSION_CONFLICT', 'Data berubah di perangkat lain. Muat ulang sebelum menyimpan.')
  }

  const periodMessages: Record<string,string> = {
    cp7_period_review_changed: 'Periode, kesiapan, atau saldo berubah sejak diperiksa. Periksa ulang sebelum melanjutkan.',
    cp7_period_not_closed: 'Belum ada periode tertutup yang dapat dibuka kembali.',
    cp7_period_close_review_date: 'Tanggal penutupan harus sama dengan tanggal yang sudah diperiksa.',
    cp7_period_request_changed: 'Permintaan pemulihan berubah. Periksa status transaksi sebelum membuat tindakan baru.',
  }
  for (const [key,message] of Object.entries(periodMessages)) {
    if (rawMessage.includes(key)) return new ClientAppError('REJECTED',message)
  }

  const notaMessages: Record<string,string> = {
    cp7_nota_source_changed: 'Hak kerja sumber berubah. Muat ulang dan pilih kembali kartu sebelum menyimpan.',
    cp7_nota_payroll_target_changed: 'Payroll tujuan berubah. Muat ulang dan periksa kembali draft nota.',
    cp7_nota_stale_version: 'Draft nota berubah. Muat ulang sebelum menyimpan.',
    cp7_nota_card_in_other_draft: 'Kartu sudah berada di draft nota lain. Buka draft tersebut atau pilih sumber lain.',
    cp7_nota_different_contractor: 'Semua kartu dalam satu nota harus milik mandor yang sama.',
    cp7_nota_after_period: 'Ada pekerjaan yang selesai setelah akhir periode. Periksa kembali periode nota.',
    cp7_nota_locked: 'Nota ini sudah dikunci. Koreksi mengikuti status payroll yang terkait.',
    'payroll period overlaps': 'Periode ini sudah mempunyai payroll aktif. Pilih payroll yang ada untuk menggabungkan nota.',
  }
  for (const [key,message] of Object.entries(notaMessages)) {
    if (rawMessage.includes(key)) return new ClientAppError('REJECTED',message)
  }

  const correctionMessages: Record<string,string> = {
    cp7_note_review_changed: 'Nota, pembayaran, atau retur berubah. Muat ulang lalu periksa nota terbaru.',
    cp7_note_active_posted_only: 'Nota ini sudah dibatalkan atau diganti. Buka nota yang berlaku sebelum membetulkan lagi.',
    cp7_note_source_superseded: 'Nota sudah dibetulkan sebelumnya. Buka nota yang berlaku saat ini.',
    cp7_note_source_identity_changed: 'Nomor, pelanggan, gudang, dan waktu kejadian harus mengikuti nota asal.',
    cp7_note_pending_child_review_required: 'Masih ada draft pembayaran atau retur pada nota ini. Selesaikan atau batalkan draft tersebut terlebih dahulu.',
    cp7_note_return_allocation_changed: 'Barang yang sudah diretur belum cocok dengan jumlah atau SKU pengganti. Periksa barang dan retur asal; pembetulan ini belum disimpan.',
    cp7_note_prepayment_owning_reallocation_required: 'Nota memakai uang muka impor yang perlu dipindahkan melalui alur uang muka. Pembetulan ini belum disimpan.',
    cp7_note_returned_line_price_changed: 'Harga barang yang sudah diretur berubah, sedangkan refund retur dihitung dari harga lama. Betulkan atau batalkan returnya dulu, lalu betulkan harga nota; pembetulan ini belum disimpan.',
    cp7_note_reallocated_payment_review_required: 'Ada pembayaran yang sudah dipindahkan dari nota lain. Betulkan pembayaran itu lewat koreksi pembayaran dulu; pembetulan nota ini belum disimpan.',
    cp7_note_request_changed: 'Permintaan pembetulan berubah. Periksa hasil permintaan sebelumnya sebelum mengirim tindakan baru.',
  }
  for (const [key,message] of Object.entries(correctionMessages)) {
    if (rawMessage.includes(key)) return new ClientAppError('REJECTED',message)
  }

  const returnCorrectionMessages: Record<string,string> = {
    cp7_return_correction_stale_review: 'Retur, stok, gudang, atau biaya berubah sejak diperiksa. Muat ulang invoice dan periksa penggantinya.',
    cp7_return_correction_ineligible: 'Retur ini sudah dibatalkan atau diganti. Buka retur yang berlaku dari riwayat.',
    cp7_return_correction_not_found: 'Retur tidak ditemukan pada invoice ini. Muat ulang dan pilih retur asal yang benar.',
    cp7_return_correction_unchanged: 'Isi retur masih sama. Ubah isian yang perlu dibetulkan sebelum menyimpan.',
    cp7_return_correction_request_changed: 'Isi permintaan pembetulan berubah. Periksa hasil permintaan sebelumnya sebelum membuat tindakan baru.',
    cp7_return_correction_document_too_large: 'Rincian retur belum dapat dimuat lengkap dalam formulir ini. Periksa dokumen asal sebelum melanjutkan.',
    cp7_return_correction_source_unavailable: 'Sumber retur pengganti belum dapat dipastikan. Muat ulang invoice; pembetulan ini belum disimpan.',
    cp7_return_correction_journal_source: 'Jurnal retur belum cocok dengan transaksi asal. Muat ulang dan periksa sumbernya; pembetulan ini belum disimpan.',
    cp7_sales_return_future_date: 'Waktu barang kembali belum boleh berada di masa depan. Periksa tanggal dan waktu dalam WIB.',
  }
  for (const [key,message] of Object.entries(returnCorrectionMessages)) {
    if (rawMessage.includes(key)) return new ClientAppError('REJECTED',message)
  }

  const miscMessages: Record<string,string> = {
    cp7_misc_review_changed: 'Transaksi atau jurnalnya berubah sejak diperiksa. Muat ulang dan periksa nilai terbaru sebelum melanjutkan.',
    cp7_misc_options_changed: 'Kategori atau rekening berubah sejak dipilih. Muat ulang, pilih kembali, lalu periksa penggantinya.',
    cp7_misc_source_unavailable: 'Kategori atau rekening ini belum dapat digunakan. Pilih sumber aktif yang tersedia sebelum menyimpan.',
    cp7_misc_already_corrected: 'Transaksi sudah dikoreksi. Buka dokumen pengganti dari riwayat untuk tindakan berikutnya.',
    cp7_misc_posted_only: 'Koreksi atau pembalikan memerlukan transaksi yang masih tercatat. Muat ulang dan buka dokumen yang berlaku.',
    cp7_misc_draft_only: 'Transaksi ini sudah melewati draft. Gunakan koreksi transaksi tercatat atau pembalikan dari rincian sumbernya.',
    cp7_misc_future_date: 'Waktu kejadian belum boleh berada di masa depan. Periksa waktu transaksi dalam WIB.',
    cp7_misc_physical_date: 'Waktu kejadian tidak valid. Periksa tanggal dan waktu transaksi dalam WIB.',
    cp7_misc_request_changed: 'Isi permintaan berubah. Periksa hasil permintaan sebelumnya sebelum membuat tindakan baru.',
    cp7_misc_correction_number: 'Nomor asli berubah sejak diperiksa. Muat ulang dokumen asal sebelum mengoreksi.',
    cp7_misc_journal_source_changed: 'Jurnal sumber berubah atau belum cocok. Muat ulang dan periksa transaksi asal; koreksi ini belum disimpan.',
  }
  for (const [key,message] of Object.entries(miscMessages)) {
    if (rawMessage.includes(key)) return new ClientAppError('REJECTED',message)
  }

  const receiptMessage = typeof candidate.message === 'string' ? receiptCorrectionMessage(candidate.message) : null
  if (receiptMessage) return new ClientAppError('REJECTED', receiptMessage)

  // W11: only a failure that never got an answer is unreachable; show definite refusals.
  // (a server rule such as CLOSE_ALREADY_CLOSED, or a page parser such as "Model produk bukan UUID valid.") is shown as is.
  const originalMessage = typeof candidate.message === 'string' ? candidate.message.trim() : ''
  if (!isUnansweredFailure(error) && originalMessage) {
    return new ClientAppError('REJECTED', originalMessage)
  }
  return new ClientAppError('BACKEND_UNAVAILABLE', 'Layanan UAT belum dapat dihubungi. Coba lagi setelah status diperiksa.', true)
}

const networkWords = ['failed to fetch', 'fetch failed', 'networkerror', 'network error', 'network request failed', 'network unavailable',
  'load failed', 'timeout', 'timed out', 'aborted', 'econnreset', 'econnrefused']

/**
 * True when the request may not have reached the server or its answer was lost (no server answer to rely on): a thrown
 * TypeError from fetch, an abort, a gateway status (502/503/504), status 0, or a network wording. The outcome of such a
 * write is unknown, so its request identity must be kept for an exact replay (M:1679, M:3819).
 */
export function isUnansweredFailure(error: unknown): boolean {
  if (error instanceof TypeError) return true
  const candidate = errorLike(error)
  if (error instanceof Error && error.name === 'AbortError') return true
  const status = typeof candidate.status === 'number' ? candidate.status : Number.NaN
  if (status === 0 || status === 502 || status === 503 || status === 504) return true
  const code = typeof candidate.code === 'string' ? candidate.code : ''
  const message = typeof candidate.message === 'string' ? candidate.message.toLowerCase() : ''
  if (!message) return true
  return !code && networkWords.some((word) => message.includes(word))
}

export function normalizeAuthError(error: unknown): ClientAppError {
  const candidate = errorLike(error)
  const code = typeof candidate.code === 'string' ? candidate.code.toLowerCase() : ''
  if (code === 'invalid_credentials' || code === 'email_not_confirmed') {
    return new ClientAppError('AUTH_FAILED', 'Email atau kata sandi tidak valid, atau akun belum dikonfirmasi.')
  }
  return normalizeClientError(error)
}
