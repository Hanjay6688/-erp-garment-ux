/** Decisions recorded in docs/cp6-d11-kebijakan-dan-gbd03.md, 26 Sep 2026.
 * These describe a decision; only the live Native policy says it is applied.
 * No accounts, categories, amounts or vendor agreements are supplied here.
 */
import type { LauPolicyKey } from './laundryBd'
import type { AccessoryPolicyKey } from './accessoryService'

export type Cp6PolicyKey = LauPolicyKey | AccessoryPolicyKey
export type PolicyState = { key: Cp6PolicyKey; status: 'SET' | 'PENDING_POLICY_VALUE'; value: Record<string, unknown> | null }
type Choice = { fields: Record<string, string>; picks: Record<string, boolean> }
const OWNER_CHOICES: Partial<Record<Cp6PolicyKey, Choice>> = {
  'ACC-DEC05': { fields: { mode: 'CREDIT_THEN_CARRY', credit_conditions: 'USABLE' }, picks: {} },
  'ACC-DEC07': { fields: { approval_mode: 'NONE' }, picks: {} },
  'LAU-DEC04': { fields: { sale: 'ALLOW_PENDING' }, picks: {} },
  'LAU-DEC06': { fields: { variance_mode: 'PRODUCT_COST', after_payment: 'CORRECTION_DOCUMENT' }, picks: {} },
}
export const POLICY_EFFECT: Record<Cp6PolicyKey, string> = {
  'ACC-DEC01': 'Tanggal fisik dan tanggal pencatatan tetap terpisah. Transaksi tidak tertahan.',
  'ACC-DEC03': 'Penilaian barang titipan menunggu akun tujuan dan batas nilai. Barang tetap dapat diterima dan diperiksa.',
  'ACC-DEC04': 'Pemakaian untuk servis pelanggan atau perbaikan barang jadi menunggu akun beban. Pemakaian pabrik tetap berjalan.',
  'ACC-DEC05': 'Kredit retur nota menunggu pengaturan. Owner sudah memilih barang layak; sisa kredit dibayar sekali lewat payroll berikutnya.',
  'ACC-DEC06': 'Pembulatan nota menunggu pilihan akun selisih naik dan turun.',
  'ACC-DEC07': 'Owner memilih tanpa persetujuan tambahan sementara. Sebelum diterapkan, biaya bernilai tetap perlu owner/admin.',
  'ERP-DEC02': 'Baris gratis menunggu daftar kategori yang diizinkan owner. Harga yang belum diketahui tidak dianggap gratis.',
  'LAU-DEC01': 'Tarif per PCS tetap berjalan. Borongan dan minimum hanya dipakai setelah owner mengizinkannya.',
  'LAU-DEC02': 'Posting invoice menunggu keputusan hasil baik, BS, atau cuci gagal yang boleh ditagih vendor. Draf dapat disiapkan.',
  'LAU-DEC03': 'Diskon, tambahan, pajak, dan pembulatan invoice menunggu aturan owner bila digunakan.',
  'LAU-DEC04': 'Owner mengizinkan penjualan dengan HPP belum final. Sebelum diterapkan, harga laundry yang belum diketahui menahan penjualan.',
  'LAU-DEC05': 'Tarif khusus sengaja tidak diaktifkan. Tarif vendor, proses, dan paket biasa tetap berjalan.',
  'LAU-DEC06': 'Posting invoice menunggu penerapan keputusan owner: selisih masuk biaya produk dan koreksi sesudah bayar memakai dokumen tertaut. Draf dapat disiapkan.',
}

export function ownerChoice(key: Cp6PolicyKey): Choice | null {
  const choice = OWNER_CHOICES[key]
  return choice ? { fields: { ...choice.fields }, picks: { ...choice.picks } } : null
}

export function policyStatus(policy: PolicyState): string {
  if (policy.status === 'SET') return 'Ditetapkan di aplikasi'
  if (policy.key === 'LAU-DEC05') return 'Sengaja tidak diaktifkan'
  return OWNER_CHOICES[policy.key] ? 'Keputusan owner belum diterapkan' : 'Perlu isian owner'
}

export function invoicePolicyMessage(policies: readonly PolicyState[]): string | null {
  const missing = (['LAU-DEC02', 'LAU-DEC06'] as const).filter(key => !policies.some(p => p.key === key && p.status === 'SET'))
  return missing.length ? `Posting invoice laundry belum siap. Minta owner menerapkan ${missing.join(' dan ')} di Kebijakan owner, lalu muat ulang. Draf invoice dan penerimaan barang tetap bisa berjalan.` : null
}

const LABEL: Record<string, string> = {
  BOTH_REAL_TIMELINES: 'Tanggal fisik dan pencatatan terpisah', MOVING_AVERAGE: 'Harga rata-rata berjalan', NONE: 'Tanpa batas / persetujuan tambahan',
  CREDIT_UNPAID_ONLY: 'Kredit bagian nota yang belum dibayar', CREDIT_THEN_CARRY: 'Kredit nota, sisanya ke payroll berikutnya',
  CREDIT_THEN_REFUND: 'Kredit nota, sisanya dikembalikan tunai', USABLE: 'Layak pakai', DAMAGED: 'Rusak', NOTE_NEAREST_RUPIAH: 'Rupiah terdekat',
  BATCH: 'Borongan per batch', MINIMUM: 'Minimum tagihan', GOOD: 'Hasil baik', BS: 'BS laundry', FAILED_ATTEMPT: 'Cuci gagal',
  ALLOWED: 'Boleh', REFUSED: 'Ditolak', LAST_LINE: 'Baris terakhir', REFUSE: 'Ditolak', ALLOW_PENDING: 'Boleh; HPP belum final',
  MODEL: 'Model', MODEL_SIZE: 'Model dan ukuran', MODEL_SIZE_COLOR: 'Model, ukuran, dan warna', BASE_RATE: 'Tarif proses biasa',
  PRODUCT_COST: 'Biaya produk', VARIANCE_ACCOUNT: 'Akun beban selisih', CORRECTION_DOCUMENT: 'Dokumen koreksi tertaut',
}
const FIELD: Record<string, string> = {
  mode: 'Cara', unit_value_cap: 'Batas nilai', credit_account_id: 'Akun tujuan', CUSTOMER_SERVICE_account_id: 'Akun servis pelanggan',
  OWN_FG_REPAIR_account_id: 'Akun perbaikan barang jadi', credit_conditions: 'Barang yang dikreditkan', gain_account_id: 'Akun pembulatan naik',
  loss_account_id: 'Akun pembulatan turun', approval: 'Persetujuan', owner_approval_above: 'Persetujuan di atas', zone_users: 'Petugas per area',
  special_free_category_ids: 'Kategori gratis', units: 'Satuan', billable: 'Yang boleh ditagih', discount: 'Diskon', extra: 'Tambahan', rounding: 'Pembulatan',
  tax_account_id: 'Akun pajak', sale_with_unknown_laundry: 'Penjualan', scopes: 'Tarif khusus', fallback: 'Jika tarif khusus tidak ada',
  variance_mode: 'Selisih invoice', after_payment: 'Koreksi setelah bayar', variance_account_id: 'Akun beban selisih',
}
export function policyValueText(policy: PolicyState, names: readonly { id: string; name: string }[] = []): string {
  if (policy.value === null) return policy.status === 'SET' ? 'Rincian hanya terlihat owner/admin' : 'Belum diterapkan'
  const describe = (value: unknown): string => {
    if (value === null) return 'Tidak digunakan'
    if (Array.isArray(value)) return value.length ? value.map(describe).join(', ') : 'Tidak ada'
    if (typeof value === 'string') return LABEL[value] ?? names.find(n => n.id === value)?.name ?? (/^[0-9a-f-]{36}$/i.test(value) ? 'Pilihan tersimpan' : value)
    if (typeof value === 'object') return `${Object.keys(value as object).length} area diatur`
    return String(value)
  }
  return Object.entries(policy.value).map(([field, value]) => `${FIELD[field] ?? 'Pengaturan'}: ${describe(value)}`).join(' · ')
}
