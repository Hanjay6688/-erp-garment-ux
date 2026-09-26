import type { Json } from './types/database.preconnect'

export type AccessoryChoice = { id: string; sku: string; name: string; unit: string; category: string; stock: string;
  price_version_id: string | null; master_price: string | null; price_unit: string | null; factor: string | null
  /** BC (ERP-DEC02): the owner's Special free list covers this accessory for this mandor at the note time. */
  free?: { category_id: string; policy_version: string } | null }
export type AccessoryLine = { material_id: string; qty: string; mode: 'MASTER' | 'MANUAL' | 'FREE'; manual_price: string }
export type AccessoryDocument = { id: string; number: string; contractor_id: string; location_id: string; po_id: string | null;
  physical_local: string; status: 'DRAFT' | 'POSTED' | 'REVERSED'; row_version: string; notes: string; total: string; payroll_locked: boolean;
  /** BC (ACC-DEC06): the note's posted whole-rupiah rounding line, if any. */
  rounding?: { document_id: string; amount: string; row_version: string } | null
  items: { id: string; material_id: string; sku: string; name: string; unit: string; qty: string; manual_price: string | null;
    price: string; factor: string; price_unit: string; price_version_id: string | null; amount: string; payroll_status: string
    /** BC: a Special free line; what payroll still collects after note return credits and rounding. */
    free?: boolean; collectible?: string }[] }
export type AccessoryWorkspace = { filters: Json; contractor_id: string | null; location_id: string | null; physical_local: string;
  contractors: { id: string; name: string }[]; locations: { id: string; name: string }[]; orders: { id: string; name: string }[];
  materials: AccessoryChoice[]; material_count: number; history_count: number; document: AccessoryDocument | null;
  history: { id: string; number: string; contractor: string; status: string; row_version: string; date: string; total: string }[] }
export const accessoryUuid = (v: unknown): v is string => typeof v === 'string' && /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(v)
const text = (v: unknown): v is string => typeof v === 'string'
const nullableId = (v: unknown) => v === null || accessoryUuid(v)
const decimal = (v: unknown, scale: number): v is string => text(v) && new RegExp(`^\\d{1,18}\\.\\d{${scale}}$`).test(v)
const version = (v: unknown): v is string => text(v) && /^[1-9]\d{0,18}$/.test(v) && BigInt(v) <= 9223372036854775807n
const localDate = (v: unknown): v is string => text(v) && /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}$/.test(v) && Number.isFinite(Date.parse(v + '+07:00'))
function object(value: unknown): Record<string, unknown> {
  if (!value || typeof value !== 'object' || Array.isArray(value)) throw new Error('Data nota aksesori tidak lengkap.')
  return value as Record<string, unknown>
}
function list(value: unknown) {
  if (!Array.isArray(value)) throw new Error('Daftar nota aksesori tidak lengkap.')
  const rows = value.map(object), seen = new Set<string>()
  for (const r of rows) { if (!accessoryUuid(r.id) || seen.has(r.id)) throw new Error('Identitas aksesori tidak valid atau ganda.'); seen.add(r.id) }
  return rows
}
export function parseAccessoryWorkspace(value: unknown): AccessoryWorkspace {
  const w = object(value)
  object(w.filters)
  if (!localDate(w.physical_local) || !nullableId(w.contractor_id) || !nullableId(w.location_id)) throw new Error('Konteks nota tidak valid.')
  for (const name of ['contractors','locations','orders']) for (const r of list(w[name])) if (!text(r.name)) throw new Error('Master nota tidak valid.')
  const materials = list(w.materials), history = list(w.history)
  for (const m of materials) {
    if (![m.sku,m.name,m.category,m.unit].every(text) || String(m.unit).toUpperCase() !== 'PCS' || !decimal(m.stock,6)
      || !nullableId(m.price_version_id)) throw new Error('Stok aksesori tidak valid.')
    if (m.price_version_id === null ? [m.master_price,m.price_unit,m.factor].some(x => x !== null)
      : !decimal(m.master_price,6) || !text(m.price_unit) || !decimal(m.factor,6) || micro(m.factor) <= 0n) throw new Error('Harga master tidak lengkap.')
    if (m.free !== undefined && m.free !== null) {
      const f = object(m.free)
      if (!accessoryUuid(f.category_id) || !version(f.policy_version)) throw new Error('Status gratis Special tidak valid.')
    }
  }
  for (const h of history) if (![h.number,h.contractor].every(text) || !['DRAFT','POSTED','REVERSED'].includes(String(h.status))
    || !version(h.row_version) || !decimal(h.total,2) || !text(h.date) || !/^\d{4}-\d{2}-\d{2}$/.test(h.date)) throw new Error('Riwayat nota tidak valid.')
  for (const [name, length] of [['material_count',materials.length],['history_count',history.length]] as const)
    if (!Number.isSafeInteger(w[name]) || Number(w[name]) < length) throw new Error('Jumlah hasil nota tidak valid.')
  if (w.document !== null) {
    const d = object(w.document)
    if (!accessoryUuid(d.id) || !accessoryUuid(d.contractor_id) || !accessoryUuid(d.location_id) || !nullableId(d.po_id)
      || ![d.number,d.notes].every(text) || !version(d.row_version) || !localDate(d.physical_local) || !decimal(d.total,2)
      || typeof d.payroll_locked !== 'boolean' || !['DRAFT','POSTED','REVERSED'].includes(String(d.status))) throw new Error('Detail nota tidak valid.')
    const ids = new Set<string>(); let amount = 0n
    for (const i of list(d.items)) {
      if (!accessoryUuid(i.material_id) || ids.has(i.material_id) || ![i.sku,i.name,i.unit,i.price_unit,i.payroll_status].every(text)
        || !decimal(i.qty,6) || micro(i.qty) <= 0n || micro(i.qty) % 1000000n !== 0n || !decimal(i.price,6)
        || !decimal(i.factor,6) || micro(i.factor) <= 0n || !decimal(i.amount,6) || !nullableId(i.price_version_id)
        || !(i.manual_price === null || decimal(i.manual_price,2))
        || !(i.free === undefined || typeof i.free === 'boolean') || !(i.collectible === undefined || (text(i.collectible) && /^-?\d{1,18}\.\d{2}$/.test(i.collectible)))) throw new Error('Baris nota tidak valid.')
      ids.add(i.material_id); amount += micro(i.amount)
    }
    if ((amount + 5000n) / 10000n !== micro(String(d.total)) / 10000n) throw new Error('Total nota tidak sesuai rincian.')
    if (d.rounding !== undefined && d.rounding !== null) {
      const r = object(d.rounding)
      if (!accessoryUuid(r.document_id) || !version(r.row_version) || !text(r.amount) || !/^-?\d{1,18}\.\d{2}$/.test(r.amount)) throw new Error('Pembulatan nota tidak valid.')
    }
  }
  return w as AccessoryWorkspace
}
export function micro(raw: string) { const [whole, part = ''] = raw.replace(',', '.').split('.'); return BigInt(whole) * 1000000n + BigInt(part.padEnd(6,'0')) }
export function displayDecimal(raw: string) { return raw.replace(/(\.\d*?)0+$/,'$1').replace(/\.$/,'').replace('.',',') }
export function displayMoney(value: bigint) { const cents = (value + 5000n) / 10000n; return `Rp ${String(cents / 100n).replace(/\B(?=(\d{3})+(?!\d))/g,'.')},${String(cents % 100n).padStart(2,'0')}` }
export function previewAccessoryLine(line: AccessoryLine, material: AccessoryChoice | undefined): { error: string; amount: bigint | null; payload: Record<string, Json> | null } {
  const reject = (error: string) => ({ error, amount:null, payload:null })
  if (!material) return reject('Aksesori tidak aktif atau belum dimuat.')
  if (!/^[1-9]\d{0,11}$/.test(line.qty)) return reject('Isi jumlah PCS utuh positif.')
  const qty = BigInt(line.qty), base = { material_id:line.material_id, qty:line.qty, mode:line.mode }
  if (line.mode === 'FREE') {
    if (!material.free) return reject('Aksesori ini tidak gratis untuk mandor ini pada waktu nota (kebijakan ERP-DEC02).')
    return { error:'', amount:0n, payload:{ ...base, free_policy_version:material.free.policy_version } }
  }
  if (line.mode === 'MANUAL') {
    if (!/^\d{1,12}([.,]\d{1,2})?$/.test(line.manual_price)) return reject('Isi harga per pcs, maksimal dua desimal.')
    return { error:'', amount:qty * micro(line.manual_price), payload:{ ...base, manual_price:line.manual_price.replace(',','.') } }
  }
  if (!material.price_version_id || material.master_price === null || material.factor === null) return reject('Harga master belum tersedia; isi harga eceran per pcs.')
  const factor = micro(material.factor), numerator = qty * 1000000000000n
  if (numerator % factor !== 0n) return reject('Jumlah ini memerlukan harga eceran per pcs; jumlah fisik tetap.')
  return { error:'', amount:(numerator / factor * micro(material.master_price) + 500000n) / 1000000n,
    payload:{ ...base, price_version_id:material.price_version_id, factor:material.factor } }
}
