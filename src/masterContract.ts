// Owner D15-3: the reader and payload builders of the connected master-data screens (cp7.master-workspace.v1 and
// cp7.work-rate-workspace.v1). The server decides everything (codes in use, blockers, rights); this file only checks
// that an answer has the expected shape and turns the form into the closed payload the server accepts.
import type { Json } from './types/database.preconnect'

export const masterKinds = ['CUSTOMER', 'SUPPLIER', 'LAUNDRY_VENDOR', 'MANDOR', 'LOCATION', 'FABRIC', 'ACCESSORY_CATEGORY', 'ACCESSORY'] as const
export type MasterKind = typeof masterKinds[number]
export type MasterAction = 'CREATE' | 'UPDATE' | 'DEACTIVATE' | 'REACTIVATE' | 'SET_BENCHMARK' | 'SET_MANDOR_PRICE'
export type RateAction = 'SET_RATE' | 'STOP_RATE' | 'SAVE_BOM' | 'CREATE_COMPONENT'
type Obj = Record<string, unknown>
export type Blocker = { kind: string } & Obj
export type AuditEntry = { at: string; table: string; action: string; actor: string | null; reason: string | null; fields: string[] }
export type MasterRow = { id: string; code: string; name: string; active: boolean; extra: Obj }
export type MasterSelected = { entity: Obj; reviewToken: string; usage: Obj; used: boolean; deactivateBlockers: Blocker[]; audit: AuditEntry[] }
export type MasterWorkspace = {
  kind: MasterKind; canWrite: boolean; canPrice: boolean; today: string
  page: { rows: MasterRow[]; total: number; offset: number; limit: number; query: string; status: 'ALL' | 'ACTIVE' | 'INACTIVE' }
  selected: MasterSelected | null; selectedMissing: boolean; options: Obj
}
export type FieldType = 'text' | 'textarea' | 'select' | 'boolean' | 'date' | 'decimal'
export type FieldOption = { value: string; label: string }
export type MasterField = { key: string; label: string; type: FieldType; optional?: boolean; max?: number; lockedAfterCreate?: boolean; help?: string;
  options?: (ws: MasterWorkspace, current: Obj | null) => FieldOption[] }
export type MasterForm = Record<string, string | boolean>

const uuid = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/
const isObj = (v: unknown): v is Obj => v !== null && typeof v === 'object' && !Array.isArray(v)
function fail(what: string): never { throw new Error(`Jawaban server untuk data master tidak sesuai (${what}). Muat ulang halaman.`) }
const str = (v: unknown, what: string) => typeof v === 'string' ? v : fail(what)
const int = (v: unknown, what: string) => typeof v === 'number' && Number.isSafeInteger(v) && v >= 0 ? v : fail(what)
const bool = (v: unknown, what: string) => typeof v === 'boolean' ? v : fail(what)
const arr = (v: unknown, what: string) => Array.isArray(v) ? v : fail(what)

export const kindLabels: Record<MasterKind, { singular: string; plural: string }> = {
  CUSTOMER: { singular: 'pelanggan', plural: 'Pelanggan' }, SUPPLIER: { singular: 'supplier', plural: 'Supplier' },
  LAUNDRY_VENDOR: { singular: 'vendor laundry', plural: 'Vendor laundry' }, MANDOR: { singular: 'mandor', plural: 'Mandor' },
  LOCATION: { singular: 'gudang/lokasi', plural: 'Gudang & lokasi' }, FABRIC: { singular: 'kain', plural: 'Kain' },
  ACCESSORY_CATEGORY: { singular: 'kategori aksesori', plural: 'Kategori aksesori' }, ACCESSORY: { singular: 'varian aksesori', plural: 'Varian aksesori' },
}
export const supplierTypeLabels: Record<string, string> = { MATERIAL: 'Kain / bahan', ACCESSORY: 'Aksesori', OTHER: 'Lainnya' }
export const locationTypeLabels: Record<string, string> = {
  RAW_MATERIAL_WAREHOUSE: 'Gudang bahan', FG_WAREHOUSE: 'Gudang barang jadi', SCRAP_AREA: 'Area barang rusak', OTHER: 'Lainnya',
  CUTTING_WIP: 'WIP potong (sistem)', CONTRACTOR_WIP: 'WIP mandor (sistem)', LAUNDRY_WIP: 'WIP laundry (sistem)', QC_WIP: 'WIP QC (sistem)',
}
const optionList = (ws: MasterWorkspace, key: string) => Array.isArray(ws.options[key]) ? ws.options[key] as Obj[] : []

export const masterFields: Record<MasterKind, MasterField[]> = {
  CUSTOMER: [
    { key: 'code', label: 'Kode', type: 'text', max: 30, help: 'Kode tidak bisa diganti sesudah pelanggan dipakai transaksi.' },
    { key: 'name', label: 'Nama pelanggan', type: 'text', max: 150 },
    { key: 'phone', label: 'Telepon', type: 'text', optional: true, max: 50 },
    { key: 'address', label: 'Alamat', type: 'textarea', optional: true, max: 500 },
  ],
  SUPPLIER: [
    { key: 'code', label: 'Kode', type: 'text', max: 30, help: 'Kode tidak bisa diganti sesudah supplier dipakai transaksi.' },
    { key: 'name', label: 'Nama supplier', type: 'text', max: 150 },
    { key: 'supplier_type', label: 'Jenis supplier', type: 'select', options: () => Object.entries(supplierTypeLabels).map(([value, label]) => ({ value, label })) },
    { key: 'phone', label: 'Telepon', type: 'text', optional: true, max: 50 },
    { key: 'address', label: 'Alamat', type: 'textarea', optional: true, max: 500 },
  ],
  LAUNDRY_VENDOR: [
    { key: 'code', label: 'Kode', type: 'text', max: 30, help: 'Kode tidak bisa diganti sesudah vendor dipakai transaksi. Tarif laundry diatur di layar Laundry.' },
    { key: 'name', label: 'Nama vendor', type: 'text', max: 120 },
    { key: 'phone', label: 'Telepon', type: 'text', optional: true, max: 50 },
    { key: 'notes', label: 'Catatan', type: 'textarea', optional: true, max: 1000 },
  ],
  MANDOR: [
    { key: 'code', label: 'Kode', type: 'text', max: 30, help: 'Kode tidak bisa diganti sesudah mandor dipakai transaksi.' },
    { key: 'name', label: 'Nama mandor', type: 'text', max: 120 },
    { key: 'attendance_required', label: 'Wajib absensi', type: 'boolean' },
    { key: 'is_special', label: 'Mandor Special', type: 'boolean', help: 'Mandor Special memakai komisi dan harga aksesori Special.' },
    { key: 'policy_from', label: 'Absensi/Special berlaku mulai (WIB)', type: 'date', optional: true,
      help: 'Wajib diisi untuk mandor baru dan bila "Wajib absensi" atau "Mandor Special" diubah.' },
    { key: 'notes', label: 'Catatan', type: 'textarea', optional: true, max: 1000 },
  ],
  LOCATION: [
    { key: 'code', label: 'Kode', type: 'text', max: 30, help: 'Kode dan jenis tidak bisa diganti sesudah lokasi punya mutasi stok.' },
    { key: 'name', label: 'Nama lokasi', type: 'text', max: 120 },
    { key: 'location_type', label: 'Jenis lokasi', type: 'select', options: (ws, current) => {
      const allowed = optionList(ws, 'location_types').map(String)
      const now = typeof current?.location_type === 'string' ? current.location_type : null
      return [...allowed, ...(now && !allowed.includes(now) ? [now] : [])].map(value => ({ value, label: locationTypeLabels[value] ?? value }))
    } },
  ],
  FABRIC: [
    { key: 'code', label: 'Kode kain', type: 'text', max: 60, lockedAfterCreate: true },
    { key: 'name', label: 'Nama kain', type: 'text', max: 150, lockedAfterCreate: true },
    { key: 'unit', label: 'Satuan', type: 'select', help: 'Satuan tidak bisa diganti sesudah kain diterima atau dipakai.',
      options: ws => optionList(ws, 'units').map(u => ({ value: String(u), label: String(u) })) },
    { key: 'fabric_category', label: 'Kategori', type: 'text', optional: true, max: 100 },
    { key: 'composition', label: 'Komposisi', type: 'text', optional: true, max: 500 },
    { key: 'construction', label: 'Konstruksi', type: 'text', optional: true, max: 500 },
    { key: 'color_name', label: 'Warna', type: 'text', optional: true, max: 100 },
    { key: 'width_cm', label: 'Lebar (cm)', type: 'decimal', optional: true },
    { key: 'gsm', label: 'Gramasi (gsm)', type: 'decimal', optional: true },
    { key: 'minimum_stock_qty', label: 'Stok minimum', type: 'decimal' },
    { key: 'preferred_supplier_id', label: 'Supplier utama', type: 'select', optional: true,
      options: ws => optionList(ws, 'suppliers').map(s => ({ value: String(s.id), label: `${s.code} · ${s.name}` })) },
    { key: 'notes', label: 'Catatan', type: 'textarea', optional: true, max: 1000 },
  ],
  ACCESSORY_CATEGORY: [
    { key: 'code', label: 'Kode kategori', type: 'text', max: 40, help: 'Kode dan satuan dasar tidak bisa diganti sesudah kategori dipakai.' },
    { key: 'name', label: 'Nama kategori', type: 'text', max: 120 },
    { key: 'base_uom', label: 'Satuan dasar', type: 'select', options: ws => optionList(ws, 'uoms').map(u => ({ value: String(u.code), label: `${u.code} · ${u.name}` })) },
    { key: 'notes', label: 'Catatan', type: 'textarea', optional: true, max: 1000 },
  ],
  ACCESSORY: [
    { key: 'code', label: 'Kode varian', type: 'text', max: 60, lockedAfterCreate: true },
    { key: 'name', label: 'Nama varian', type: 'text', max: 150, lockedAfterCreate: true },
    { key: 'category_id', label: 'Kategori', type: 'select', help: 'Kategori tidak bisa diganti sesudah varian punya mutasi stok.',
      options: ws => optionList(ws, 'categories').map(c => ({ value: String(c.id), label: `${c.code} · ${c.name}` })) },
  ],
}

// The Mandor's HPP policy that covers a WIB date (inclusive ranges, as the Native writer keeps them).
export function policyAt(entity: Obj, day: string) {
  const list = Array.isArray(entity.policies) ? entity.policies as Obj[] : []
  return [...list].reverse().find(p => String(p.effective_from) <= day && (p.effective_to === null || String(p.effective_to) >= day)) ?? null
}

export function emptyForm(kind: MasterKind): MasterForm {
  const form: MasterForm = {}
  for (const f of masterFields[kind]) form[f.key] = f.type === 'boolean' ? (f.key === 'attendance_required') : ''
  if (kind === 'SUPPLIER') form.supplier_type = 'MATERIAL'
  if (kind === 'LOCATION') form.location_type = 'RAW_MATERIAL_WAREHOUSE'
  if (kind === 'FABRIC') form.minimum_stock_qty = '0'
  return form
}

export function formFromEntity(kind: MasterKind, entity: Obj, today: string): MasterForm {
  const form = emptyForm(kind)
  const source: Obj = kind === 'FABRIC' ? { ...entity, ...(isObj(entity.profile) ? entity.profile : {}) } : entity
  for (const f of masterFields[kind]) {
    if (f.key === 'policy_from') { form.policy_from = ''; continue }
    if (f.key === 'is_special') { form.is_special = policyAt(entity, today)?.is_special === true; continue }
    const v = f.key === 'notes' && kind === 'FABRIC' ? (isObj(entity.profile) ? entity.profile.notes : null) : source[f.key]
    form[f.key] = f.type === 'boolean' ? v === true : v === null || v === undefined ? '' : String(v)
  }
  if (kind === 'FABRIC' && typeof form.unit === 'string') form.unit = form.unit.toUpperCase()
  if (kind === 'ACCESSORY_CATEGORY' && typeof form.base_uom === 'string') form.base_uom = form.base_uom.toUpperCase()
  return form
}

const decimal = /^[0-9]{1,12}(\.[0-9]{1,6})?$/
// What the form still needs before the server can be asked (the server repeats every check).
export function formProblems(kind: MasterKind, form: MasterForm, creating: boolean): string[] {
  const out: string[] = []
  for (const f of masterFields[kind]) {
    const v = form[f.key]
    if (f.type === 'boolean') continue
    const s = typeof v === 'string' ? v.trim() : ''
    if (!s) { if (!f.optional) out.push(`${f.label} wajib diisi.`); continue }
    if (f.max && s.length > f.max) out.push(`${f.label} paling panjang ${f.max} huruf.`)
    if (f.key === 'code' && creating && !/^[A-Za-z0-9][A-Za-z0-9._/-]*$/.test(s)) out.push('Kode hanya huruf, angka, titik, garis miring, garis bawah atau tanda minus, tanpa spasi.')
    if (f.type === 'decimal' && (!decimal.test(s) || (['width_cm', 'gsm'].includes(f.key) && Number(s) <= 0))) out.push(`${f.label} harus angka${['width_cm', 'gsm'].includes(f.key) ? ' lebih dari 0' : ''} (pakai titik untuk desimal).`)
    if (f.type === 'date' && !/^\d{4}-\d{2}-\d{2}$/.test(s)) out.push(`${f.label} harus tanggal.`)
  }
  if (kind === 'MANDOR' && creating && !(typeof form.policy_from === 'string' && form.policy_from.trim())) out.push('Tanggal mulai berlaku absensi/Special wajib diisi untuk mandor baru.')
  return out
}

export function fieldsPayload(kind: MasterKind, form: MasterForm): Json {
  const out: Record<string, Json> = {}
  for (const f of masterFields[kind]) {
    const v = form[f.key]
    if (f.type === 'boolean') { out[f.key] = v === true; continue }
    const s = typeof v === 'string' ? v.trim() : ''
    out[f.key] = s === '' && f.optional ? null : s
  }
  return out
}

export function masterPayload(action: MasterAction, reason: string, selected: MasterSelected | null, fields?: Json): Json {
  const base: Record<string, Json> = { action, reason: reason.trim() }
  if (action !== 'CREATE') { base.id = String(selected?.entity.id ?? ''); base.review_token = selected?.reviewToken ?? '' }
  if (fields !== undefined) base.fields = fields
  return base
}

function audit(v: unknown): AuditEntry[] {
  return arr(v, 'audit').map(a => {
    if (!isObj(a)) fail('audit')
    return { at: str(a.at, 'audit.at'), table: str(a.table, 'audit.table'), action: str(a.action, 'audit.action'),
      actor: typeof a.actor === 'string' ? a.actor : null, reason: typeof a.reason === 'string' ? a.reason : null,
      fields: arr(a.fields, 'audit.fields').map(x => str(x, 'audit.fields')) }
  })
}

export function parseMasterWorkspace(value: unknown, kind: MasterKind): MasterWorkspace {
  if (!isObj(value) || value.contract_version !== 'cp7.master-workspace.v1' || value.kind !== kind) fail('kontrak')
  const page = isObj(value.page) ? value.page : fail('page')
  const rows = arr(page.rows, 'rows').map(r => {
    if (!isObj(r) || typeof r.id !== 'string' || !uuid.test(r.id)) fail('rows')
    const { id, code, name, active, ...extra } = r
    return { id: id as string, code: str(code, 'code'), name: str(name, 'name'), active: bool(active, 'active'), extra }
  })
  const status = page.status === 'ACTIVE' || page.status === 'INACTIVE' ? page.status : page.status === 'ALL' ? 'ALL' : fail('status')
  let selected: MasterSelected | null = null
  if (value.selected !== null && value.selected !== undefined) {
    const s = isObj(value.selected) ? value.selected : fail('selected')
    const entity = isObj(s.entity) && typeof s.entity.id === 'string' ? s.entity : fail('entity')
    const token = str(s.review_token, 'token'); if (!/^[a-f0-9]{32}$/.test(token)) fail('token')
    selected = { entity, reviewToken: token, usage: isObj(s.usage) ? s.usage : fail('usage'), used: bool(s.used, 'used'),
      deactivateBlockers: arr(s.deactivate_blockers, 'blockers').map(b => isObj(b) && typeof b.kind === 'string' ? b as Blocker : fail('blocker')),
      audit: audit(s.audit) }
  }
  return { kind, canWrite: bool(value.can_write, 'can_write'), canPrice: bool(value.can_price, 'can_price'), today: str(value.today, 'today'),
    page: { rows, total: int(page.total, 'total'), offset: int(page.offset, 'offset'), limit: int(page.limit, 'limit'), query: str(page.query, 'query'), status },
    selected, selectedMissing: value.selected_missing === true, options: isObj(value.options) ? value.options : fail('options') }
}

export function validateMasterOutcome(value: unknown, kind: MasterKind, action: string, request: string) {
  if (!isObj(value) || value.contract_version !== 'cp7.master-outcome.v1' || value.kind !== 'COMMITTED_OUTCOME' || value.master_kind !== kind
    || value.action !== action || value.request_id !== request || typeof value.id !== 'string' || !uuid.test(value.id) || !isObj(value.entity)) fail('hasil simpan')
  return { id: value.id, entity: value.entity }
}

const n = (b: Blocker, k: string) => String(b[k] ?? '')
export function blockerText(b: Blocker) {
  switch (b.kind) {
    case 'OPEN_SALES_DRAFT': return `Masih ada ${n(b, 'count')} draf penjualan untuk pelanggan ini. Selesaikan atau hapus draf itu dulu.`
    case 'OPEN_PURCHASE_DRAFT': return `Masih ada ${n(b, 'count')} draf pembelian dari supplier ini. Selesaikan atau hapus draf itu dulu.`
    case 'OPEN_LAUNDRY_DELIVERY': return `Masih ada ${n(b, 'count')} kiriman laundry yang belum kembali atau ditutup.`
    case 'OPEN_PRODUCTION_ORDER': return `Mandor ini masih memegang ${n(b, 'count')} PO yang belum selesai.`
    case 'SYSTEM_LOCATION': return `Lokasi sistem (${locationTypeLabels[n(b, 'location_type')] ?? n(b, 'location_type')}) dipakai alur produksi dan tidak dinonaktifkan dari sini.`
    case 'STOCK_AT_LOCATION': return `Lokasi masih berisi stok: bahan ${n(b, 'material_qty')}, barang jadi ${n(b, 'fg_qty')} pcs. Pindahkan atau koreksi stok sampai nol dulu.`
    case 'STOCK_ON_HAND': return `Stok masih ${n(b, 'qty')}. Pakai, pindahkan, atau koreksi stok sampai nol dulu.`
    case 'ACTIVE_VARIANTS': return `Kategori ini masih punya ${n(b, 'count')} varian aktif. Nonaktifkan variannya dulu.`
    default: return 'Belum bisa dinonaktifkan; muat ulang lalu periksa lagi.'
  }
}

export const usageLabels: Record<string, string> = {
  sales: 'Penjualan', sales_draft: 'Draf penjualan', returns: 'Retur', opening: 'Saldo awal', purchases: 'Penerimaan/pembelian',
  purchase_draft: 'Draf pembelian', invoices: 'Invoice', rolls: 'Roll', deliveries: 'Kiriman laundry', deliveries_open: 'Kiriman belum selesai',
  claims: 'Klaim', production_orders: 'PO', production_open: 'PO belum selesai', pickups: 'Bagi Potongan', work: 'Catatan jahit',
  payrolls: 'Payroll', issues: 'Nota ambil aksesori', work_rates: 'Versi tarif upah', material_moves: 'Mutasi bahan', fg_moves: 'Mutasi barang jadi',
  material_qty: 'Stok bahan', fg_qty: 'Stok barang jadi (pcs)', moves: 'Mutasi stok', purchase_lines: 'Baris penerimaan', variants: 'Varian',
  variants_active: 'Varian aktif', prices: 'Versi harga mandor', bom_items: 'Dipakai di BOM aksesori',
}

// ---------------------------------------------------------------- work rates (cp7.work-rate-workspace.v1)
export type RateVersion = { id: string; rate: string; effectiveFrom: string; effectiveTo: string | null; lastUse: string | null; reworkUses: number }
export type RateComponent = { componentId: string; code: string; name: string; defaultRate: string | null; inCurrentBom: boolean;
  versions: RateVersion[]; current: { id: string; rate: string; effectiveFrom: string } | null; reviewToken: string }
export type BomVersion = { id: string; versionNo: number; effectiveFrom: string; effectiveTo: string | null; isActive: boolean; lastUse: string | null;
  items: { componentId: string; code: string; name: string; sequenceNo: number; defaultRate: string }[] }
export type RateWorkspace = {
  canWrite: boolean; canPrice: boolean; today: string
  contractor: { id: string; code: string; name: string; active: boolean; attendanceRequired: boolean; isSpecial: boolean } | null
  models: { rows: { id: string; code: string; name: string; active: boolean; components: number }[]; total: number; offset: number; query: string }
  model: { id: string; code: string; name: string; active: boolean; currentBomId: string | null; bom: BomVersion[]; bomReviewToken: string; components: RateComponent[] } | null
  catalog: { id: string; code: string; name: string; category: string; sequenceDefault: number }[]
}
const optStr = (v: unknown) => typeof v === 'string' ? v : null

export function parseRateWorkspace(value: unknown): RateWorkspace {
  if (!isObj(value) || value.contract_version !== 'cp7.work-rate-workspace.v1') fail('kontrak tarif')
  const models = isObj(value.models) ? value.models : fail('models')
  const c = value.contractor === null ? null : isObj(value.contractor) ? value.contractor : fail('contractor')
  const m = value.model === null ? null : isObj(value.model) ? value.model : fail('model')
  return {
    canWrite: bool(value.can_write, 'can_write'), canPrice: bool(value.can_price, 'can_price'), today: str(value.today, 'today'),
    contractor: c && { id: str(c.id, 'contractor.id'), code: str(c.code, 'contractor.code'), name: str(c.name, 'contractor.name'), active: bool(c.active, 'contractor.active'),
      attendanceRequired: bool(c.attendance_required, 'attendance'), isSpecial: bool(c.is_special, 'special') },
    models: { rows: arr(models.rows, 'models.rows').map(r => isObj(r) ? { id: str(r.id, 'model.id'), code: str(r.code, 'model.code'), name: str(r.name, 'model.name'),
      active: bool(r.active, 'model.active'), components: int(r.components, 'model.components') } : fail('model row')),
      total: int(models.total, 'models.total'), offset: int(models.offset, 'models.offset'), query: str(models.query, 'models.query') },
    model: m && { id: str(m.id, 'model.id'), code: str(m.code, 'model.code'), name: str(m.name, 'model.name'), active: bool(m.active, 'model.active'),
      currentBomId: optStr(m.current_bom_id), bomReviewToken: str(m.bom_review_token, 'bom token'),
      bom: arr(m.bom, 'bom').map(v => isObj(v) ? { id: str(v.id, 'bom.id'), versionNo: int(v.version_no, 'bom.version'), effectiveFrom: str(v.effective_from, 'bom.from'),
        effectiveTo: optStr(v.effective_to), isActive: bool(v.is_active, 'bom.active'), lastUse: optStr(v.last_use),
        items: arr(v.items, 'bom.items').map(i => isObj(i) ? { componentId: str(i.component_id, 'item.component'), code: str(i.code, 'item.code'), name: str(i.name, 'item.name'),
          sequenceNo: int(i.sequence_no, 'item.seq'), defaultRate: str(i.default_rate, 'item.rate') } : fail('bom item')) } : fail('bom version')),
      components: arr(m.components, 'components').map(k => isObj(k) ? { componentId: str(k.component_id, 'component'), code: str(k.code, 'component.code'),
        name: str(k.name, 'component.name'), defaultRate: optStr(k.default_rate), inCurrentBom: bool(k.in_current_bom, 'in bom'), reviewToken: str(k.review_token, 'rate token'),
        current: isObj(k.current) ? { id: str(k.current.id, 'current.id'), rate: str(k.current.rate, 'current.rate'), effectiveFrom: str(k.current.effective_from, 'current.from') } : null,
        versions: arr(k.versions, 'versions').map(v => isObj(v) ? { id: str(v.id, 'version.id'), rate: str(v.rate, 'version.rate'), effectiveFrom: str(v.effective_from, 'version.from'),
          effectiveTo: optStr(v.effective_to), lastUse: optStr(v.last_use), reworkUses: int(v.rework_uses, 'version.rework') } : fail('version')) } : fail('component')) },
    catalog: arr(value.component_catalog, 'catalog').map(k => isObj(k) ? { id: str(k.id, 'catalog.id'), code: str(k.code, 'catalog.code'), name: str(k.name, 'catalog.name'),
      category: str(k.category, 'catalog.category'), sequenceDefault: int(k.sequence_default, 'catalog.seq') } : fail('catalog')),
  }
}

export function validateRateOutcome(value: unknown, action: RateAction, request: string) {
  if (!isObj(value) || value.contract_version !== 'cp7.work-rate-outcome.v1' || value.kind !== 'COMMITTED_OUTCOME' || value.action !== action
    || value.request_id !== request || typeof value.id !== 'string' || !uuid.test(value.id)) fail('hasil simpan tarif')
  return { id: value.id }
}

// "2026-10-01T17:00:00+00:00" (00:00 WIB) -> "2026-10-02": the WIB day a version starts or ends.
export function wibDay(at: string | null) {
  if (!at) return null
  const t = Date.parse(at); if (!Number.isFinite(t)) return at
  return new Date(t + 7 * 3600_000).toISOString().slice(0, 10)
}
// Rupiah from an exact decimal string without going through a float.
export function rupiah(value: string | null) {
  if (value === null) return '—'
  const negative = value.startsWith('-'), [whole, cents = ''] = value.replace('-', '').split('.')
  const trimmed = cents.replace(/0+$/, '')
  return `${negative ? '-' : ''}Rp${whole.replace(/\B(?=(\d{3})+(?!\d))/g, '.')}${trimmed ? ',' + trimmed : ''}`
}
