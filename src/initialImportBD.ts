// BD (ALL-W05): what a posted import holds for laundry work at cutover that is not ordinary WIP. A server with BD sends both
// collections; a server without BD sends neither. One without the other is an incomplete read and is refused. Claims continue
// on the opening WIP row (Saldo fisik produksi awal); an uninvoiced return is billed on the Laundry page, tab Harga & tagihan (invoice line
// with the opening record) and its unknown estimate is set there too.

const uuid = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i
const KEYS = ['laundry_claims', 'laundry_uninvoiced'] as const
function object(value: unknown, label: string): Record<string, unknown> {
  if (!value || typeof value !== 'object' || Array.isArray(value)) throw new Error(`${label} tidak lengkap.`)
  return value as Record<string, unknown>
}
function list(value: unknown, label: string): Record<string, unknown>[] {
  if (!Array.isArray(value)) throw new Error(`${label} tidak terbaca lengkap.`)
  return value.map(v => object(v, label))
}
const id = (v: unknown, label: string) => { if (typeof v !== 'string' || !uuid.test(v)) throw new Error(`${label}: identitas tidak valid.`); return v }
const text = (v: unknown, label: string) => { if (typeof v !== 'string' || !v.trim()) throw new Error(`${label} tidak valid.`); return v }
const optional = (v: unknown, label: string) => v === null ? null : text(v, label)
const count = (v: unknown, label: string) => { if (typeof v !== 'number' || !Number.isSafeInteger(v) || v < 0) throw new Error(`${label}: jumlah tidak valid.`); return v }
const day = (v: unknown, label: string) => { if (typeof v !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(v)) throw new Error(`${label}: tanggal tidak valid.`); return v }
const money = (v: unknown, label: string) => { if (typeof v !== 'string' || !/^-?\d{1,18}\.\d{2}$/.test(v)) throw new Error(`${label}: nominal tidak valid.`); return v }
const version = (v: unknown, label: string) => { if (typeof v !== 'string' || !/^[1-9][0-9]{0,18}$/.test(v)) throw new Error(`${label}: versi tidak valid.`); return v }
const bool = (v: unknown, label: string) => { if (typeof v !== 'boolean') throw new Error(`${label} tidak valid.`); return v }

export type BdOpeningClaim = { claim_id: string; opening_item_id: string; source_key: string; po_number: string; claim_number: string;
  claim_type: 'MISSING' | 'STUCK' | 'DAMAGE'; origin: 'IMPORT' | 'CONTINUATION'; vendor_code: string; qty_claimed: number; recovered: number;
  claim_date: string; dispatch_number: string | null; cancelled: boolean; row_version: string; compensation_amount: string | null }
export type BdOpeningUninvoiced = { id: string; vendor_code: string; document_number: string; receipt_date: string; category: 'GOOD' | 'BS' | 'FAILED_ATTEMPT';
  qty: number; billed: number; estimate_status: 'KNOWN' | 'UNKNOWN'; estimated_amount: string | null; released: string; invoiced: boolean;
  po_number: string | null; dispatch_number: string | null; row_version: string }
export type InitialImportBD = { laundry_claims: BdOpeningClaim[]; laundry_uninvoiced: BdOpeningUninvoiced[] }
export const UNINVOICED_CATEGORY_LABEL = { GOOD: 'Hasil baik', BS: 'BS laundry', FAILED_ATTEMPT: 'Cuci gagal' } as const

export function parseInitialImportBD(batch: Record<string, unknown>): InitialImportBD | null {
  const present = KEYS.filter(key => batch[key] !== undefined)
  if (!present.length) return null
  if (present.length !== KEYS.length) throw new Error('Laundry saldo awal tidak terbaca lengkap.')
  const laundry_claims = list(batch.laundry_claims, 'Klaim laundry saldo awal').map((c): BdOpeningClaim => {
    if (!['MISSING', 'STUCK', 'DAMAGE'].includes(String(c.claim_type)) || (c.origin !== 'IMPORT' && c.origin !== 'CONTINUATION')) throw new Error('Klaim laundry saldo awal tidak valid.')
    const qty_claimed = count(c.qty_claimed, 'Jumlah klaim'), recovered = count(c.recovered, 'Sudah kembali')
    if (!qty_claimed || recovered > qty_claimed) throw new Error('Jumlah klaim laundry tidak cocok.')
    return { claim_id:id(c.claim_id, 'Klaim'), opening_item_id:id(c.opening_item_id, 'WIP laundry'), source_key:text(c.source_key, 'Kode rincian WIP'),
      po_number:text(c.po_number, 'Nomor PO'), claim_number:text(c.claim_number, 'Nomor klaim'), claim_type:c.claim_type as BdOpeningClaim['claim_type'],
      origin:c.origin, vendor_code:text(c.vendor_code, 'Kode laundry'), qty_claimed, recovered, claim_date:day(c.claim_date, 'Tanggal klaim'),
      dispatch_number:optional(c.dispatch_number, 'Nomor kirim lama'), cancelled:bool(c.cancelled, 'Status batal klaim'), row_version:version(c.row_version, 'Klaim'),
      compensation_amount:c.compensation_amount === null ? null : money(c.compensation_amount, 'Kompensasi klaim') }
  })
  const laundry_uninvoiced = list(batch.laundry_uninvoiced, 'Laundry belum ditagih saldo awal').map((u): BdOpeningUninvoiced => {
    if (!['GOOD', 'BS', 'FAILED_ATTEMPT'].includes(String(u.category)) || (u.estimate_status !== 'KNOWN' && u.estimate_status !== 'UNKNOWN')) throw new Error('Laundry belum ditagih tidak valid.')
    const qty = count(u.qty, 'Jumlah belum ditagih'), billed = count(u.billed, 'Sudah ditagih')
    const estimated_amount = u.estimated_amount === null ? null : money(u.estimated_amount, 'Estimasi')
    if (!qty || billed > qty || (u.estimate_status === 'KNOWN') !== (estimated_amount !== null)) throw new Error('Laundry belum ditagih tidak cocok.')
    return { id:id(u.id, 'Laundry belum ditagih'), vendor_code:text(u.vendor_code, 'Kode laundry'), document_number:text(u.document_number, 'Nomor terima lama'),
      receipt_date:day(u.receipt_date, 'Tanggal terima'), category:u.category as BdOpeningUninvoiced['category'], qty, billed, estimate_status:u.estimate_status,
      estimated_amount, released:money(u.released, 'Estimasi dilepas'), invoiced:bool(u.invoiced, 'Status tagih'), po_number:optional(u.po_number, 'Nomor PO'),
      dispatch_number:optional(u.dispatch_number, 'Nomor kirim lama'), row_version:version(u.row_version, 'Laundry belum ditagih') }
  })
  return { laundry_claims, laundry_uninvoiced }
}
