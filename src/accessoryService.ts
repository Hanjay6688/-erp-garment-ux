// BC (ACC-04b): the accessory service, return and inspection workspace. The server sends every collection on every read;
// a missing or malformed one is an incomplete read and is refused (the page shows the error, never "nothing here").
import type { Json } from './types/database.preconnect'

export const ACCESSORY_POLICY_KEYS = ['ACC-DEC01', 'ACC-DEC03', 'ACC-DEC04', 'ACC-DEC05', 'ACC-DEC06', 'ACC-DEC07', 'ERP-DEC02'] as const
export type AccessoryPolicyKey = typeof ACCESSORY_POLICY_KEYS[number]
export const ZONE_KINDS = ['MAIN', 'SERVICE_POST', 'INSPECTION', 'DAMAGED'] as const
export type ZoneKind = typeof ZONE_KINDS[number]
export const LOT_SOURCES = ['SERVICE_LEFTOVER', 'NOTE_RETURN', 'OPENING_NOTE_RETURN', 'TEARDOWN', 'LEGACY', 'OPENING_PENDING_VALUE',
  'OPENING_QUARANTINE', 'NOTE_RETURN_CREDITED'] as const
export const SERVICE_ACTIONS = ['FILL_POST', 'RETURN_TO_WAREHOUSE', 'INTERNAL_USE', 'RECEIVE_RETURN', 'INSPECT', 'VALUE_CUSTODY', 'CREDIT_NOTE_RETURN',
  'ALLOCATE_CARRY', 'DISPOSE_STOCK', 'CLOSE_CUSTODY', 'CUSTOMER_GARMENT_IN', 'CUSTOMER_GARMENT_OUT', 'COUNT_POST', 'RESOLVE_VARIANCE', 'ROUND_NOTE'] as const
export type ServiceAction = typeof SERVICE_ACTIONS[number]
export const ACTION_LABEL: Record<ServiceAction, string> = {
  FILL_POST: 'Isi pos servis', RETURN_TO_WAREHOUSE: 'Kembalikan sisa ke gudang', INTERNAL_USE: 'Pemakaian perusahaan', RECEIVE_RETURN: 'Terima kembali',
  INSPECT: 'Periksa barang kembali', VALUE_CUSTODY: 'Nilai titipan', CREDIT_NOTE_RETURN: 'Kredit retur nota mandor', ALLOCATE_CARRY: 'Bawa kredit ke payroll',
  DISPOSE_STOCK: 'Buang barang rusak', CLOSE_CUSTODY: 'Tutup titipan', CUSTOMER_GARMENT_IN: 'Terima titipan pelanggan', CUSTOMER_GARMENT_OUT: 'Kembalikan titipan pelanggan',
  COUNT_POST: 'Hitung stok pos', RESOLVE_VARIANCE: 'Selesaikan selisih hitung', ROUND_NOTE: 'Bulatkan nota mandor' }
export const PURPOSE_LABEL = { FACTORY_USE: 'Pemakaian pabrik', CUSTOMER_SERVICE: 'Servis pelanggan', OWN_FG_REPAIR: 'Perbaikan barang jadi sendiri' } as const
export type Purpose = keyof typeof PURPOSE_LABEL
export const POLICY_LABEL: Record<AccessoryPolicyKey, string> = {
  'ACC-DEC01': 'Garis waktu kembali & periksa', 'ACC-DEC03': 'Nilai titipan belum dinilai', 'ACC-DEC04': 'Akun biaya pemakaian per tujuan',
  'ACC-DEC05': 'Retur nota mandor yang sudah dibayar', 'ACC-DEC06': 'Pembulatan nota ke rupiah', 'ACC-DEC07': 'Batas persetujuan owner & petugas area',
  'ERP-DEC02': 'Kategori gratis mandor Special' }

export type ServicePolicy = { key: AccessoryPolicyKey; status: 'SET' | 'PENDING_POLICY_VALUE'; version: string; value: Record<string, unknown> | null; set_at: string | null }
export type ServiceLocation = { id: string; code: string; name: string; kind: ZoneKind; label: string }
export type ServiceStock = { material_id: string; sku: string; name: string; unit: string; category: string; location_id: string; location: string;
  bucket: string; kind: ZoneKind; qty: string; value: string | null; updated_local: string }
export type ServiceDocument = { id: string; number: string; action: string; status: 'POSTED' | 'REVERSED'; physical_local: string; recorded_local: string;
  responsible: string; reference: string; reason: string; row_version: string; links: number }
export type LotState = { received: string; inspected_usable: string; inspected_damaged: string; usable: string; damaged: string; waiting: string; credited: string; open: string }
export type ServiceLot = { id: string; document: string; source_kind: string; owner_kind: 'COMPANY' | 'MANDOR'; value_status: string; material_id: string;
  sku: string; name: string; location_id: string; received_local: string; note_item_id: string | null; opening_note_line_id: string | null; reference: string; state: LotState }
export type Outstanding = { id: string; source_kind: string; owner_kind: string; material_id: string | null; description: string; holder: string; reference: string;
  expected: string; received: string; label: string }
export type CustomerCustody = { id: string; customer: string; description: string; qty: string; received_local: string; returned: boolean }
export type Variance = { id: string; material_id: string; location_id: string; book: string; counted: string; variance: string; label: string; resolved: boolean }
export type NoteLine = { item_id: string; issue_id: string; number: string; contractor: string; material_id: string; sku: string; name: string; qty: string;
  returned: string; collectible: string; allocated: string; payroll_status: string }
export type OpeningNoteLine = { line_id: string; number: string; contractor: string; material_id: string; sku: string; name: string; qty: string;
  line_amount: string; returned: string; remaining_receivable: string }
export type LotEvent = { id: string; lot_id: string; kind: string; condition: string | null; qty: string; qty_usable: string | null; qty_damaged: string | null;
  inspector: string | null; amount: string | null; unpaid: string | null; carry: string | null; refund: string | null; carry_remaining: string | null }
export type DocumentDetail = { id: string; number: string; action: string; status: 'POSTED' | 'REVERSED'; row_version: string; payload: Record<string, unknown>;
  policy_versions: Record<string, unknown>; reversal_reason: string | null; links: { kind: string; id: string }[]; events: LotEvent[];
  carry_payrolls: { id: string; number: string; status: string; period_end: string }[] }
export type StockCard = { total: number; rows: { movement_id: string; movement_type: string; source_type: string; physical_local: string; recorded_local: string;
  before: string; qty: string; after: string }[] }
export type AccessoryServiceWorkspace = { can_see_value: boolean; is_admin: boolean; page: number; page_size: number; policies: ServicePolicy[];
  locations: ServiceLocation[]; stock_total: number; stock: ServiceStock[]; documents_total: number; documents: ServiceDocument[]; lots: ServiceLot[];
  outstanding: Outstanding[]; customer_custody: CustomerCustody[]; variances: Variance[]; notes: NoteLine[] | null; opening_notes: OpeningNoteLine[] | null;
  customers: { id: string; code: string; name: string }[] | null; document: DocumentDetail | null; card: StockCard | null
  materials: { id: string; sku: string; name: string; unit: string }[]; cash_accounts: Choice[] | null
  accounts: { id: string; code: string; name: string; type: string }[] | null; categories: Choice[] | null; users: Choice[] | null }
export type Choice = { id: string; name: string }

// Any canonical UUID text the database's uuid type produces (seeded ids are not always RFC-4122 v4).
const uuid = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i
function object(value: unknown, label: string): Record<string, unknown> {
  if (!value || typeof value !== 'object' || Array.isArray(value)) throw new Error(`${label} tidak terbaca lengkap.`)
  return value as Record<string, unknown>
}
function list(value: unknown, label: string): Record<string, unknown>[] {
  if (!Array.isArray(value)) throw new Error(`${label} tidak terbaca lengkap.`)
  return value.map(v => object(v, label))
}
function nullableList(value: unknown, label: string): Record<string, unknown>[] | null {
  if (value === null) return null
  return list(value, label)
}
const id = (v: unknown, label: string): string => { if (typeof v !== 'string' || !uuid.test(v)) throw new Error(`${label}: identitas tidak valid.`); return v }
const nullableId = (v: unknown, label: string): string | null => v === null ? null : id(v, label)
const text = (v: unknown, label: string): string => { if (typeof v !== 'string') throw new Error(`${label} tidak valid.`); return v }
const optionalText = (v: unknown, label: string): string => v === null ? '' : text(v, label)
const qty = (v: unknown, label: string): string => { if (typeof v !== 'string' || !/^-?\d{1,18}\.\d{6}$/.test(v)) throw new Error(`${label}: jumlah tidak valid.`); return v }
const money = (v: unknown, label: string): string => { if (typeof v !== 'string' || !/^-?\d{1,18}\.\d{2}$/.test(v)) throw new Error(`${label}: nominal tidak valid.`); return v }
const nullableMoney = (v: unknown, label: string): string | null => v === null ? null : money(v, label)
const amount = (v: unknown, label: string): string | null => {
  if (v === null) return null
  if (typeof v !== 'string' || !/^-?\d{1,18}(\.\d{1,6})?$/.test(v)) throw new Error(`${label}: nominal tidak valid.`)
  return v
}
const count = (v: unknown, label: string): number => { if (typeof v !== 'number' || !Number.isSafeInteger(v) || v < 0) throw new Error(`${label}: jumlah tidak valid.`); return v }
const version = (v: unknown, label: string): string => { if (typeof v !== 'string' || !/^[1-9]\d{0,18}$/.test(v)) throw new Error(`${label}: versi tidak valid.`); return v }
const localMinute = (v: unknown, label: string): string => { if (typeof v !== 'string' || !/^\d{4}-\d{2}-\d{2} \d{2}:\d{2}$/.test(v)) throw new Error(`${label}: waktu tidak valid.`); return v }
const bool = (v: unknown, label: string): boolean => { if (typeof v !== 'boolean') throw new Error(`${label} tidak valid.`); return v }
function oneOf<T extends string>(v: unknown, allowed: readonly T[], label: string): T {
  if (!allowed.includes(v as T)) throw new Error(`${label} tidak dikenal.`)
  return v as T
}
function lotState(v: unknown): LotState {
  const s = object(v, 'Keadaan titipan')
  const keys = ['received', 'inspected_usable', 'inspected_damaged', 'usable', 'damaged', 'waiting', 'credited', 'open'] as const
  return Object.fromEntries(keys.map(k => [k, qty(s[k], 'Keadaan titipan')])) as LotState
}

export function parseAccessoryServiceWorkspace(value: unknown): AccessoryServiceWorkspace {
  const w = object(value, 'Ruang kerja aksesori')
  object(w.filters, 'Filter aksesori')
  const can_see_value = bool(w.can_see_value, 'Hak lihat nilai'), is_admin = bool(w.is_admin, 'Peran')
  const policies = list(w.policies, 'Kebijakan aksesori').map((p): ServicePolicy => {
    const status = oneOf(p.status, ['SET', 'PENDING_POLICY_VALUE'] as const, 'Status kebijakan')
    if (p.value !== null && (typeof p.value !== 'object' || Array.isArray(p.value))) throw new Error('Isi kebijakan tidak valid.')
    if (status === 'PENDING_POLICY_VALUE' && p.value !== null) throw new Error('Kebijakan menunggu tidak boleh berisi nilai.')
    return { key: oneOf(p.key, ACCESSORY_POLICY_KEYS, 'Kunci kebijakan'), status, version: version(p.version, 'Kebijakan'),
      value: p.value as Record<string, unknown> | null, set_at: p.set_at === null ? null : text(p.set_at, 'Waktu kebijakan') }
  })
  if (new Set(policies.map(p => p.key)).size !== ACCESSORY_POLICY_KEYS.length || policies.length !== ACCESSORY_POLICY_KEYS.length) throw new Error('Daftar kebijakan aksesori tidak lengkap.')
  const locations = list(w.locations, 'Lokasi aksesori').map((l): ServiceLocation => ({ id: id(l.id, 'Lokasi'), code: text(l.code, 'Kode lokasi'),
    name: text(l.name, 'Nama lokasi'), kind: oneOf(l.kind, ZONE_KINDS, 'Jenis lokasi'), label: text(l.label, 'Label lokasi') }))
  const stock = list(w.stock, 'Stok aksesori').map((s): ServiceStock => {
    const v = nullableMoney(s.value, 'Nilai stok')
    if ((v === null) === can_see_value) throw new Error('Nilai stok tidak sesuai hak lihat nilai.')
    return { material_id: id(s.material_id, 'Aksesori'), sku: text(s.sku, 'SKU'), name: text(s.name, 'Nama aksesori'), unit: text(s.unit, 'Satuan'),
      category: optionalText(s.category, 'Kategori'), location_id: id(s.location_id, 'Lokasi stok'), location: text(s.location, 'Lokasi stok'),
      bucket: text(s.bucket, 'Keadaan stok'), kind: oneOf(s.kind, ZONE_KINDS, 'Jenis lokasi stok'), qty: qty(s.qty, 'Stok'), value: v,
      updated_local: localMinute(s.updated_local, 'Waktu stok') }
  })
  const documents = list(w.documents, 'Dokumen aksesori').map((d): ServiceDocument => ({ id: id(d.id, 'Dokumen'), number: text(d.number, 'Nomor dokumen'),
    action: text(d.action, 'Jenis dokumen'), status: oneOf(d.status, ['POSTED', 'REVERSED'] as const, 'Status dokumen'),
    physical_local: localMinute(d.physical_local, 'Waktu fisik'), recorded_local: localMinute(d.recorded_local, 'Waktu catat'),
    responsible: optionalText(d.responsible, 'Penanggung jawab'), reference: optionalText(d.reference, 'Referensi'), reason: text(d.reason, 'Alasan'),
    row_version: version(d.row_version, 'Dokumen'), links: count(d.links, 'Tautan dokumen') }))
  const lots = list(w.lots, 'Barang kembali').map((l): ServiceLot => ({ id: id(l.id, 'Titipan'), document: optionalText(l.document, 'Dokumen titipan'),
    source_kind: oneOf(l.source_kind, LOT_SOURCES, 'Asal titipan'), owner_kind: oneOf(l.owner_kind, ['COMPANY', 'MANDOR'] as const, 'Pemilik titipan'),
    value_status: text(l.value_status, 'Status nilai'), material_id: id(l.material_id, 'Aksesori titipan'), sku: text(l.sku, 'SKU'), name: text(l.name, 'Nama'),
    location_id: id(l.location_id, 'Lokasi titipan'), received_local: localMinute(l.received_local, 'Waktu terima'),
    note_item_id: nullableId(l.note_item_id, 'Baris nota'), opening_note_line_id: nullableId(l.opening_note_line_id, 'Baris nota lama'),
    reference: optionalText(l.reference, 'Referensi'), state: lotState(l.state) }))
  const outstanding = list(w.outstanding, 'Belum kembali').map((o): Outstanding => ({ id: id(o.id, 'Belum kembali'), source_kind: text(o.source_kind, 'Asal'),
    owner_kind: text(o.owner_kind, 'Pemilik'), material_id: nullableId(o.material_id, 'Aksesori'), description: optionalText(o.description, 'Keterangan'),
    holder: optionalText(o.holder, 'Pemegang'), reference: optionalText(o.reference, 'Referensi'), expected: qty(o.expected, 'Jumlah'),
    received: qty(o.received, 'Diterima'), label: text(o.label, 'Label') }))
  const customer_custody = list(w.customer_custody, 'Titipan pelanggan').map((c): CustomerCustody => ({ id: id(c.id, 'Titipan pelanggan'),
    customer: text(c.customer, 'Pelanggan'), description: text(c.description, 'Keterangan'), qty: qty(c.qty, 'Jumlah'),
    received_local: localMinute(c.received_local, 'Waktu terima'), returned: bool(c.returned, 'Status kembali') }))
  const variances = list(w.variances, 'Selisih hitung').map((v): Variance => ({ id: id(v.id, 'Selisih'), material_id: id(v.material_id, 'Aksesori'),
    location_id: id(v.location_id, 'Lokasi'), book: qty(v.book, 'Buku'), counted: qty(v.counted, 'Hitung'), variance: qty(v.variance, 'Selisih'),
    label: text(v.label, 'Label'), resolved: bool(v.resolved, 'Status selisih') }))
  const notes = nullableList(w.notes, 'Baris nota mandor')?.map((n): NoteLine => ({ item_id: id(n.item_id, 'Baris nota'), issue_id: id(n.issue_id, 'Nota'),
    number: text(n.number, 'Nomor nota'), contractor: text(n.contractor, 'Mandor'), material_id: id(n.material_id, 'Aksesori'), sku: text(n.sku, 'SKU'),
    name: text(n.name, 'Nama'), qty: qty(n.qty, 'Jumlah'), returned: qty(n.returned, 'Kembali'), collectible: money(n.collectible, 'Sisa ditagih'),
    allocated: amount(n.allocated, 'Dialokasikan') ?? '0', payroll_status: text(n.payroll_status, 'Status payroll') })) ?? null
  const opening_notes = nullableList(w.opening_notes, 'Nota mandor saldo awal')?.map((n): OpeningNoteLine => ({ line_id: id(n.line_id, 'Baris nota lama'),
    number: text(n.number, 'Nomor nota lama'), contractor: text(n.contractor, 'Mandor'), material_id: id(n.material_id, 'Aksesori'), sku: text(n.sku, 'SKU'),
    name: text(n.name, 'Nama'), qty: qty(n.qty, 'Jumlah'), line_amount: money(n.line_amount, 'Nominal baris'), returned: qty(n.returned, 'Kembali'),
    remaining_receivable: money(n.remaining_receivable, 'Sisa piutang') })) ?? null
  const customers = nullableList(w.customers, 'Pelanggan')?.map(c => ({ id: id(c.id, 'Pelanggan'), code: text(c.code, 'Kode pelanggan'), name: text(c.name, 'Nama pelanggan') })) ?? null
  let document: DocumentDetail | null = null
  if (w.document !== null) {
    const d = object(w.document, 'Detail dokumen')
    document = { id: id(d.id, 'Dokumen'), number: text(d.number, 'Nomor dokumen'), action: text(d.action, 'Jenis dokumen'),
      status: oneOf(d.status, ['POSTED', 'REVERSED'] as const, 'Status dokumen'), row_version: version(d.row_version, 'Dokumen'),
      payload: object(d.payload, 'Isi dokumen'), policy_versions: object(d.policy_versions, 'Versi kebijakan'),
      reversal_reason: d.reversal_reason === null ? null : text(d.reversal_reason, 'Alasan batal'),
      links: list(d.links, 'Tautan').map(k => ({ kind: text(k.kind, 'Jenis tautan'), id: id(k.id, 'Tautan') })),
      events: list(d.events, 'Kejadian titipan').map((e): LotEvent => ({ id: id(e.id, 'Kejadian'), lot_id: id(e.lot_id, 'Titipan'), kind: text(e.kind, 'Jenis kejadian'),
        condition: e.condition === null ? null : text(e.condition, 'Kondisi'), qty: qty(e.qty, 'Jumlah'),
        qty_usable: e.qty_usable === null ? null : qty(e.qty_usable, 'Layak'), qty_damaged: e.qty_damaged === null ? null : qty(e.qty_damaged, 'Rusak'),
        inspector: e.inspector === null ? null : text(e.inspector, 'Pemeriksa'), amount: amount(e.amount, 'Nominal'), unpaid: amount(e.unpaid, 'Belum dibayar'),
        carry: amount(e.carry, 'Dibawa'), refund: amount(e.refund, 'Dikembalikan'), carry_remaining: amount(e.carry_remaining, 'Sisa dibawa') })),
      carry_payrolls: list(d.carry_payrolls, 'Payroll draft').map(p => ({ id: id(p.id, 'Payroll'), number: text(p.number, 'Nomor payroll'),
        status: text(p.status, 'Status payroll'), period_end: text(p.period_end, 'Periode payroll') })) }
  }
  let card: StockCard | null = null
  if (w.card !== null) {
    const c = object(w.card, 'Kartu stok')
    card = { total: count(c.total, 'Kartu stok'), rows: list(c.rows, 'Baris kartu stok').map(r => ({ movement_id: id(r.movement_id, 'Gerakan'),
      movement_type: text(r.movement_type, 'Jenis gerakan'), source_type: text(r.source_type, 'Sumber'), physical_local: localMinute(r.physical_local, 'Waktu fisik'),
      recorded_local: localMinute(r.recorded_local, 'Waktu catat'), before: qty(r.before, 'Sebelum'), qty: qty(r.qty, 'Jumlah'), after: qty(r.after, 'Sesudah') })) }
  }
  const choices = (v: unknown, label: string): Choice[] | null => nullableList(v, label)?.map(c => ({ id: id(c.id, label), name: text(c.name, label) })) ?? null
  const materials = list(w.materials, 'Pilihan aksesori').map(m => ({ id: id(m.id, 'Aksesori'), sku: text(m.sku, 'SKU'), name: text(m.name, 'Nama'), unit: text(m.unit, 'Satuan') }))
  const accounts = nullableList(w.accounts, 'Akun')?.map(a => ({ id: id(a.id, 'Akun'), code: text(a.code, 'Kode akun'), name: text(a.name, 'Nama akun'), type: text(a.type, 'Jenis akun') })) ?? null
  if (!is_admin && [w.cash_accounts, w.accounts, w.categories, w.users].some(v => v !== null)) throw new Error('Pilihan pengaturan hanya untuk owner/admin.')
  const stock_total = count(w.stock_total, 'Jumlah stok'), documents_total = count(w.documents_total, 'Jumlah dokumen')
  if (stock_total < stock.length || documents_total < documents.length) throw new Error('Jumlah hasil aksesori tidak valid.')
  return { can_see_value, is_admin, page: count(w.page, 'Halaman'), page_size: count(w.page_size, 'Ukuran halaman'), policies, locations, stock_total, stock,
    documents_total, documents, lots, outstanding, customer_custody, variances, notes, opening_notes, customers, document, card, materials,
    cash_accounts: choices(w.cash_accounts, 'Rekening kas'), accounts, categories: choices(w.categories, 'Kategori aksesori'), users: choices(w.users, 'Pengguna') }
}

/** A service action result: the request, action and posted document it answers (REVERSE answers with the reversed document). */
export function validateServiceResult(value: unknown, action: string, request: string, documentId: string | null) {
  const r = object(value, 'Respons aksesori')
  const status = action === 'REVERSE' ? 'REVERSED' : action === 'SET_POLICY' || action === 'REGISTER_ZONE' ? 'SAVED' : 'POSTED'
  if (r.request_id !== request || r.action !== action || r.status !== status) throw new Error('Respons aksesori tidak cocok; pulihkan transaksi yang sama.')
  if (status === 'SAVED' ? r.document_id !== null : r.document_id !== (action === 'REVERSE' ? documentId : request)) throw new Error('Identitas dokumen aksesori tidak cocok.')
  if (status !== 'SAVED') version(r.row_version, 'Dokumen')
}

// ---------------------------------------------------------------- input helpers (exact text, WIB)
export const wholePcs = (v: string) => /^[1-9]\d{0,11}$/.test(v.trim())
export const moneyText = (v: string) => /^\d{1,12}([.,]\d{1,2})?$/.test(v.trim())
export const normalizeMoney = (v: string) => { const [a, b = ''] = v.trim().replace(',', '.').split('.'); return `${a}.${b.padEnd(2, '0')}` }
export const wibTimestamp = (local: string) => /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(:\d{2})?$/.test(local) ? (local.length === 16 ? local + ':00' : local) + '+07:00' : null
export const displayQty = (raw: string) => raw.replace(/(\.\d*?)0+$/, '$1').replace(/\.$/, '').replace('.', ',')
export const displayRupiah = (raw: string | null) => {
  if (raw === null) return 'Tidak ditampilkan'
  const negative = raw.startsWith('-'), [whole, part = ''] = raw.replace('-', '').split('.')
  return `${negative ? '−' : ''}Rp ${whole.replace(/\B(?=(\d{3})+(?!\d))/g, '.')},${part.padEnd(2, '0').slice(0, 2)}`
}

/** The policy value the owner enters, checked here only for shape; the server checks accounts, users and categories. */
export function policyValue(key: AccessoryPolicyKey, f: Record<string, string>): Record<string, Json> | string {
  const accountOk = (v: string) => /^[0-9a-f-]{36}$/i.test(v.trim())
  switch (key) {
    case 'ACC-DEC01': return { mode: 'BOTH_REAL_TIMELINES' }
    case 'ACC-DEC03':
      if (!accountOk(f.credit_account_id ?? '') || !['MOVING_AVERAGE', 'NONE'].includes(f.unit_value_cap ?? '')) return 'Pilih akun pengakuan nilai dan batas nilai per buah.'
      return { credit_account_id: f.credit_account_id.trim(), unit_value_cap: f.unit_value_cap }
    case 'ACC-DEC04': {
      const out: Record<string, Json> = {}
      for (const k of ['CUSTOMER_SERVICE_account_id', 'OWN_FG_REPAIR_account_id']) if ((f[k] ?? '').trim()) {
        if (!accountOk(f[k])) return 'Akun biaya tidak valid.'
        out[k] = f[k].trim()
      }
      return Object.keys(out).length ? out : 'Isi paling sedikit satu akun biaya.'
    }
    case 'ACC-DEC05': {
      const conditions = (f.credit_conditions ?? '').split(',').map(x => x.trim()).filter(Boolean)
      if (!['CREDIT_UNPAID_ONLY', 'CREDIT_THEN_CARRY', 'CREDIT_THEN_REFUND'].includes(f.mode ?? '') || !conditions.length
        || conditions.some(c => !['USABLE', 'DAMAGED'].includes(c))) return 'Pilih cara kredit dan kondisi barang yang dikredit.'
      return { mode: f.mode, credit_conditions: conditions }
    }
    case 'ACC-DEC06':
      if (!accountOk(f.gain_account_id ?? '') || !accountOk(f.loss_account_id ?? '')) return 'Pilih akun selisih pembulatan naik dan turun.'
      return { mode: 'NOTE_NEAREST_RUPIAH', gain_account_id: f.gain_account_id.trim(), loss_account_id: f.loss_account_id.trim() }
    case 'ACC-DEC07': {
      if (!moneyText(f.owner_approval_above ?? '')) return 'Isi batas nilai persetujuan owner.'
      const out: Record<string, Json> = { owner_approval_above: normalizeMoney(f.owner_approval_above) }
      if ((f.zone_users ?? '').trim()) {
        try { const users = JSON.parse(f.zone_users); if (!users || typeof users !== 'object' || Array.isArray(users)) throw new Error(); out.zone_users = users as Json }
        catch { return 'Petugas area harus berupa daftar {lokasi: [pengguna]}.' }
      }
      return out
    }
    case 'ERP-DEC02': {
      const ids = (f.special_free_category_ids ?? '').split(',').map(x => x.trim()).filter(Boolean)
      if (ids.some(x => !accountOk(x))) return 'Kategori gratis tidak valid.'
      return { special_free_category_ids: ids }
    }
  }
}
