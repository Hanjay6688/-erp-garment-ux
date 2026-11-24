import { formatCp6WibDateTime } from '../cp6BusinessTime'
import { isUnansweredFailure, normalizeClientError } from '../lib/clientError'
import { formatReceiptDecimal } from '../procurementContract'
import { WaResponseError, isMaterialReorderDetail, isObligationDetail } from './model'
import type {
  AlertKind,
  AlertWa,
  DispatchKind,
  FgReorderDetail,
  MaterialReorderDetail,
  OutboxState,
  SystemAlert,
  WaDispatch,
} from './model'

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
  if (wa.state === 'PENDING' || wa.state === 'HELD_QUIET') {
    if (wa.reason === 'KIND_OFF') return { label: 'WA: ditahan, jenis dimatikan', tone: 'off' }
    if (wa.reason && disabledReason[wa.reason]) return { label: disabledReason[wa.reason].replace('tidak dikirim', 'ditahan'), tone: 'off' }
    if (wa.reason === 'REPEAT_OFF') return { label: 'WA: pengulangan dimatikan', tone: 'off' }
    if (wa.reason === 'REPEAT_NOT_DUE') return { label: 'WA: menunggu jadwal pengulangan', tone: 'wait' }
  }
  switch (wa.state) {
    case 'ACCEPTED': return { label: wa.round > 0 ? `WA: terkirim (ulangan ke-${wa.round})` : 'WA: terkirim', tone: 'ok' }
    case 'PENDING': return { label: wa.round > 0 || ['OWNER_NOT_DELIVERED', 'PROVIDER_REFUSED', 'TRANSPORT_FAILED'].includes(wa.reason ?? '') ? 'WA: menunggu kirim ulang' : 'WA: menunggu', tone: 'wait' }
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
  ZERO_NATIVE_REMAINING: 'Sumber membuktikan sudah lunas',
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

// D17-10: the fabric on the formula and the accessory are closed with the reorder codes, said with the words of their screens.
const minimumResolutionText: Partial<Record<AlertKind, Record<string, string>>> = {
  FABRIC_BELOW_MINIMUM: { ABOVE_REORDER_POINT: 'Stok sudah di atas minimum rumus', NO_REORDER_POINT: 'Minimum rumusnya tidak ada lagi' },
  ACCESSORY_AT_REORDER_POINT: { ABOVE_REORDER_POINT: 'Stok sudah di atas batas minimum', NO_REORDER_POINT: 'Batas minimumnya dikosongkan atau diisi 0' },
}

/** Why a system reminder closed, in plain words; `kind` picks the words of its screen when they differ. */
export function resolutionLabel(resolution: string | null, kind?: AlertKind): string {
  const own = resolution && kind ? minimumResolutionText[kind]?.[resolution] : undefined
  if (own) return own
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
const rupiah = (v: string | null) => v === null ? 'Rp?' : `Rp${formatReceiptDecimal(v)}`
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
  if (d.projection) {
    const label = Array.from(`${d.productName}${d.sizeCode !== null ? ` ${d.sizeCode}` : ''}`)
    const suffix = `: bebas ${alertNumber(d.freePcs)} pcs, perkiraan tepat waktu `
      + `${d.wipStatus === 'COMPLETE' ? `${alertNumber(d.wipPcs)} pcs` : 'belum diketahui'}, titik ${alertNumber(d.reorderPointPcs)} pcs`
    return label.length + Array.from(suffix).length <= 256 ? label.join('') + suffix
      : label.slice(0, Math.max(0, 255 - Array.from(suffix).length)).join('') + '…' + suffix
  }
  const line = `${d.productName}${d.sizeCode !== null ? ` ${d.sizeCode}` : ''}: sisa ${alertNumber(d.freePcs)} pcs, sedang diproduksi `
    + `${d.wipStatus === 'COMPLETE' ? `${alertNumber(d.wipPcs)} pcs` : 'belum diketahui'}, titik pesan ulang ${alertNumber(d.reorderPointPcs)} pcs`
  return Array.from(line).slice(0, 120).join('')
}

/** The line item_line (alerts.sql) writes for a fabric on the formula or an accessory (D17-10): the unit after every number
 * (empty when there is none). */
export function materialReorderLine(d: MaterialReorderDetail): string {
  const unit = d.unitCode ?? '', q = (v: string) => `${alertNumber(v)} ${unit}`
  const line = d.materialType === 'FABRIC' ? `${d.name}: sisa ${q(d.freeQty)}, dipesan ${q(d.onOrderQty)}, minimum rumus ${q(d.reorderPointQty)}`
    : `${d.name}: sisa ${q(d.freeQty)}, minimum ${q(d.reorderPointQty)}`
  return Array.from(line).slice(0, 120).join('')
}

/** One line of the numbers of a system reminder, in plain words. */
export function alertSummary(a: SystemAlert): string {
  const d = a.detail
  if (d.kind==='RECOST_PENDING') return `${d.poNumber??d.entityId} · antrean ${d.queueId} · ${d.status==='FAILED'?'perlu diperiksa':d.status==='RUNNING'?'sedang dihitung':'menunggu hitung ulang'}`
  if (d.kind === 'ACCESSORY_NEED') {
    const reasons = { BOM_NOT_RECORDED: 'BOM aksesori belum dicatat', BOM_AMBIGUOUS: 'BOM aksesori tumpang tindih; perlu diperiksa',
      CATEGORY_UNAVAILABLE: 'Kategori aksesori tidak tersedia', INSTALLATION_AND_ELIGIBLE_UNUSED_SUPPLY_NOT_PROVEN: 'Pemasangan dan sisa yang dialokasikan belum terbukti' }
    const gross = d.grossQty === null ? '' : ` · kebutuhan BOM${d.grossState === 'ASSUMED' ? ' (perkiraan)' : ''} ${formatReceiptDecimal(d.grossQty)} ${d.unit}`
    return `${d.label}${d.categoryName ? ` · ${d.categoryName}` : ''}: kebutuhan aksesori perlu diperiksa; jumlah tambahan belum diketahui${gross} · ${reasons[d.reason]}`
  }
  if (isObligationDetail(d)) {
    const reasons: Record<string, string> = {
      MISSING_RECORDED_DUE_DATE: 'Tanggal jatuh tempo belum tercatat',
      UNKNOWN_NATIVE_REMAINING: 'Sisa kewajiban belum dapat dipastikan',
      NATIVE_CREDIT_REVIEW: 'Saldo kredit perlu diperiksa',
      VALUE_PENDING: 'Nilai tagihan final belum tersedia',
      PRICE_KNOWN_AWAITING_INVOICE: 'Tarif layanan sudah diketahui, menunggu invoice',
      ALLOCATION_NOT_SETTLEMENT: 'Alokasi belum membuktikan pembayaran',
      SOURCE_REVIEW: 'Sumber perlu diperiksa',
      INVOICED_LIABILITY_SEE_NATIVE_DOCUMENT: 'Sudah ditagih; nilai utang ada di invoice laundry',
    }
    const money = d.amountState === 'KNOWN' ? `Nilai ${rupiah(d.amount)}` : 'Nilai belum diketahui'
    return d.state === 'DATA_REVIEW' ? `${money} · ${reasons[d.reason] ?? 'Perlu diperiksa di dokumen asal'}`
      : `${money} · jatuh tempo ${dateOnly(d.dueDate)} (${d.reason === 'DUE_TODAY' ? 'hari ini' : 'terlewat'})`
  }
  if (d.kind === 'FG_AT_REORDER_POINT') return fgReorderLine(d)
  if (isMaterialReorderDetail(d)) return materialReorderLine(d)
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
  if (d.kind !== 'PRODUCTION_GAP' && d.kind !== 'FABRIC_NEED' && d.kind !== 'ACCESSORY_NEED') return null
  return `Data analisis per ${formatCp6WibDateTime(d.dataAsOf)}${d.checkedAt ? `, dicek ulang ${formatCp6WibDateTime(d.checkedAt)}` : ', belum dicek ulang'}`
}
