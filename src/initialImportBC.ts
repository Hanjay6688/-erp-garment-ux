// BC (ALL-C02/C03): what a posted import holds for accessories that are not ready stock. A server with BC sends both
// collections; a server without BC sends neither. One without the other is an incomplete read and is refused. The
// continuation (return receipt, inspection, credit, valuation) is the accessory service workspace (Gudang · Aksesori).

// Any canonical UUID text the database's uuid type produces (seeded ids are not always RFC-4122 v4).
const uuid = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i
const KEYS = ['accessory_note_lines', 'accessory_custody'] as const
function object(value: unknown, label: string): Record<string, unknown> {
  if (!value || typeof value !== 'object' || Array.isArray(value)) throw new Error(`${label} tidak lengkap.`)
  return value as Record<string, unknown>
}
function list(value: unknown, label: string): Record<string, unknown>[] {
  if (!Array.isArray(value)) throw new Error(`${label} tidak terbaca lengkap.`)
  return value.map(v => object(v, label))
}
const text = (v: unknown, label: string) => { if (typeof v !== 'string') throw new Error(`${label} tidak valid.`); return v }
const optional = (v: unknown, label: string) => v === null || v === undefined ? '' : text(v, label)
const qty = (v: unknown, label: string) => { if (typeof v !== 'string' || !/^\d{1,18}\.\d{6}$/.test(v)) throw new Error(`${label}: jumlah tidak valid.`); return v }
const money = (v: unknown, label: string) => { if (typeof v !== 'string' || !/^-?\d{1,18}\.\d{2}$/.test(v)) throw new Error(`${label}: nominal tidak valid.`); return v }

export type BcNoteLine = { line_id: string; document_number: string; line_number: number; material_sku: string; qty: string; line_amount: string;
  returned: string; remaining_receivable: string }
export type BcCustody = { kind: 'QUARANTINE_VALUED' | 'PENDING_VALUE' | 'UNRETURNED' | 'CUSTOMER_GARMENT'; key: string; material_sku: string; qty: string;
  value_status: string; holder: string; customer_code: string; waiting: string | null; usable: string | null; damaged: string | null }
export type InitialImportBC = { accessory_note_lines: BcNoteLine[]; accessory_custody: BcCustody[] }

export function parseInitialImportBC(batch: Record<string, unknown>): InitialImportBC | null {
  const present = KEYS.filter(key => batch[key] !== undefined)
  if (!present.length) return null
  if (present.length !== KEYS.length) throw new Error('Aksesori saldo awal tidak terbaca lengkap.')
  const accessory_note_lines = list(batch.accessory_note_lines, 'Baris nota aksesori lama').map((n): BcNoteLine => {
    if (typeof n.line_id !== 'string' || !uuid.test(n.line_id) || !Number.isSafeInteger(n.line_number) || Number(n.line_number) < 1) throw new Error('Baris nota aksesori lama tidak valid.')
    return { line_id: n.line_id, document_number: text(n.document_number, 'Nomor nota lama'), line_number: Number(n.line_number),
      material_sku: text(n.material_sku, 'Kode aksesori'), qty: qty(n.qty, 'Jumlah nota'), line_amount: money(n.line_amount, 'Nominal baris'),
      returned: qty(n.returned, 'Sudah kembali'), remaining_receivable: money(n.remaining_receivable, 'Sisa piutang') }
  })
  const accessory_custody = list(batch.accessory_custody, 'Titipan aksesori saldo awal').map((c): BcCustody => {
    const kind = c.kind
    if (kind !== 'QUARANTINE_VALUED' && kind !== 'PENDING_VALUE' && kind !== 'UNRETURNED' && kind !== 'CUSTOMER_GARMENT') throw new Error('Jenis titipan aksesori tidak dikenal.')
    const lot = kind === 'QUARANTINE_VALUED' || kind === 'PENDING_VALUE'
    const state = lot ? object(c.state, 'Keadaan titipan') : null
    if (!lot && c.state !== undefined) throw new Error('Keadaan titipan tidak valid.')
    return { kind, key: text(c.key, 'Kode opname'), material_sku: kind === 'CUSTOMER_GARMENT' ? '' : text(c.material_sku, 'Kode aksesori'), qty: qty(c.qty, 'Jumlah titipan'),
      value_status: text(c.value_status, 'Status nilai'), holder: optional(c.holder, 'Pemegang'), customer_code: optional(c.customer_code, 'Kode pelanggan'),
      waiting: state ? qty(state.waiting, 'Menunggu periksa') : null, usable: state ? qty(state.usable, 'Layak') : null, damaged: state ? qty(state.damaged, 'Rusak') : null }
  })
  return { accessory_note_lines, accessory_custody }
}
