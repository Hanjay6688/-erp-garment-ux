// Plan v2 (a staged snapshot rechecked live when applied): the server refuses
// with 40001 and its numbers in DETAIL. The screen says what changed and asks
// for a review; it never retries on its own and never invents a number.
type Detail = Record<string, unknown>
const n = (v: unknown) => typeof v === 'string' && /^-?(0|[1-9][0-9]*)(\.[0-9]+)?$/.test(v) ? v.replace(/(\.[0-9]*?)0+$/, '$1').replace(/\.$/, '') : null
function detail(raw: unknown): Detail | null {
  if (typeof raw !== 'string') return null
  try { const d = JSON.parse(raw) as unknown; return d !== null && typeof d === 'object' && !Array.isArray(d) ? d as Detail : null } catch { return null }
}
export function planV2Message(message: unknown, details: unknown): string | null {
  if (typeof message !== 'string') return null
  const code = message.trim().toUpperCase(), d = detail(details) ?? {}
  switch (code) {
    case 'CP7_PLAN_V2_NEED_CHANGED': {
      const now = n(d.need_now_pcs), plan = n(d.selected_new_pcs), up = n(d.increase_pcs)
      return now && plan
        ? `Kebutuhan sekarang ${now} pcs, rencana ${plan} pcs${up ? ` (stok barang jadi dan barang dalam proses naik ${up} pcs sejak data diambil)` : ''}. Tinjau ulang rencana.`
        : 'Kebutuhan sudah berubah sejak data diambil. Tinjau ulang rencana.'
    }
    // P20 F01: an earlier-analysis (v1) plan refused for the same reason under the same shared capacity lock.
    case 'CP7_PLAN_CAPACITY_USED':
    case 'CP7_PLAN_V2_CAPACITY_USED': {
      const left = n(d.capacity_now_pcs), used = n(d.capacity_used_by_other_plans_pcs), plan = n(d.selected_new_pcs)
      return left && plan
        ? `Kapasitas potong tersisa ${left} pcs${used ? ` (rencana lain memakai ${used} pcs)` : ''}, rencana ${plan} pcs. Tinjau ulang rencana.`
        : 'Kapasitas potong sudah dipakai rencana lain. Tinjau ulang rencana.'
    }
    case 'CP7_PLAN_V2_CAPACITY_EXPIRED': return 'Kalender kapasitas yang dipakai analisis sudah lewat. Perbarui jadwal, lalu buat analisis baru.'
    case 'CP7_PLAN_V2_PRODUCT_CHANGED': return 'Produk berubah sejak data diambil (tidak aktif lagi, atau model/ukurannya lain). Tinjau ulang rencana.'
    case 'CP7_PLAN_V2_POLICY_CHANGED': return 'Status produksi SKU ini sekarang bukan Aktif. Periksa status produksi sebelum merencanakan.'
    case 'CP7_PLAN_V2_TARGET_PLANNED': return 'Target ini sudah punya rencana lain sesudah data diambil. Buka rencana itu, atau buat analisis baru.'
    case 'CP7_PLAN_V2_WIP_UNKNOWN': return 'Barang dalam proses untuk model dan ukuran ini belum bisa dipastikan, jadi rencana belum bisa disahkan.'
    case 'CP7_PLAN_LINKED_INTENT_CONFLICT': return 'Rencana sebelumnya untuk target ini belum selesai terbukti di produksi. Rencana baru belum bisa dibuat.'
    case 'CP7_PLAN_V2_SNAPSHOT_INDEX_MISSING': return 'Analisis ini dibuat sebelum rencana bisa dibaca per target. Buat analisis bertahap baru.'
    case 'CP7_PLAN_V2_DRAFT_KIND': return 'Rencana ini dibuat dari jenis analisis lain. Buka dari analisis asalnya.'
    default: return null
  }
}
