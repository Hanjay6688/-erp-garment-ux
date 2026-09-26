// BD (LAU-05b, LAU-DEC01..06, ALL-W05): the laundry price and vendor invoice workspace. The server sends every collection on
// every read; a missing or malformed one is an incomplete read and is refused. Amounts are null for a reader without the
// money permission (hidden, never zero); an unknown price is null with its status UNKNOWN (never zero).
import type { Json } from './types/database.preconnect'

export const LAU_POLICY_KEYS = ['LAU-DEC01', 'LAU-DEC02', 'LAU-DEC03', 'LAU-DEC04', 'LAU-DEC05', 'LAU-DEC06'] as const
export type LauPolicyKey = typeof LAU_POLICY_KEYS[number]
export const LAU_POLICY_LABEL: Record<LauPolicyKey, string> = {
  'LAU-DEC01': 'Satuan harga selain per PCS (borongan, minimum)', 'LAU-DEC02': 'Qty yang boleh ditagih vendor',
  'LAU-DEC03': 'Diskon, tambahan, pajak, pembulatan invoice', 'LAU-DEC04': 'Jual barang yang harga laundrynya belum diketahui',
  'LAU-DEC05': 'Tarif khusus model / ukuran / warna', 'LAU-DEC06': 'Selisih invoice dan koreksi sesudah bayar' }
export const BD_ACTIONS = ['SET_POLICY', 'SAVE_VENDOR_TERMS', 'SAVE_COMPONENT', 'SAVE_COMPONENT_RATE', 'SAVE_PACKAGE', 'SAVE_PACKAGE_RATE',
  'SAVE_PROCESS_RATE', 'SAVE_SCOPED_RATE', 'POST_PRICED_DELIVERY', 'SET_CHARGE_PRICE', 'SAVE_INVOICE_DRAFT', 'CANCEL_INVOICE_DRAFT', 'POST_INVOICE',
  'REVERSE_INVOICE', 'SET_OPENING_ESTIMATE'] as const
export type BdAction = typeof BD_ACTIONS[number]
export const CATEGORY_LABEL = { GOOD: 'Hasil baik', BS: 'BS laundry', FAILED_ATTEMPT: 'Cuci gagal' } as const
export type Category = keyof typeof CATEGORY_LABEL
export const CHARGE_KIND_LABEL = { RATE: 'Tarif proses', SCOPED_RATE: 'Tarif khusus', PACKAGE: 'Paket', COMPONENT: 'Komponen', EXTRA: 'Tambahan',
  BATCH: 'Borongan', MINIMUM_TOPUP: 'Tambahan minimum' } as const
type ChargeKind = keyof typeof CHARGE_KIND_LABEL

export type BdPolicy = { key: LauPolicyKey; status: 'SET' | 'PENDING_POLICY_VALUE'; value: Record<string, unknown> | null; version: string; set_at: string; reason: string }
export type BdVendor = { id: string; code: string; name: string; pricing_mode: 'RATE' | 'PACKAGE' | 'COMPONENTS'; pricing_unit: 'PCS' | 'BATCH';
  minimum_charge: string | null; terms_version: string; bd_priced: boolean }
export type BdComponent = { id: string; vendor_id: string; code: string; name: string; is_active: boolean
  current: { status: 'KNOWN' | 'UNKNOWN'; rate: string | null; from: string } | null }
export type BdPackage = { id: string; vendor_id: string; code: string; name: string; is_active: boolean; component_ids: string[]; current_rate: string | null }
export type BdProcessRate = { id: string; vendor_id: string; wash_process_id: string; rate: string | null; from: string; to: string | null }
export type BdScopedRate = { id: string; vendor_id: string; wash_process_id: string; scope: 'MODEL' | 'MODEL_SIZE' | 'MODEL_SIZE_COLOR'; model_id: string;
  size_id: string | null; color_name: string | null; rate: string | null; from: string }
export type BdCharge = { id: string; line_no: number; kind: ChargeKind; label: string; covered_qty: number; rate_status: 'KNOWN' | 'UNKNOWN';
  unit_rate: string | null; amount: string | null }
export type BdPricedDelivery = { delivery_line_id: string; delivery_id: string; delivery_number: string; status: string; physical_local: string;
  mode: string; unit: string; qty_sent: number; total_known: string | null; total_complete: boolean; charges: BdCharge[] }
export type BdInvoiceLine = { id: string; line_no: number; line_kind: 'BILL' | 'CORRECTION'; receipt_line_id: string | null; opening_uninvoiced_id: string | null;
  category: Category; qty: number; amount: string; net_amount: string | null; released_estimate: string | null; variance: string | null
  product_variance: string | null; completes_source: boolean }
export type BdInvoice = { invoice_id: string; vendor_id: string; vendor_code: string; invoice_number: string; invoice_date: string; due_date: string | null
  status: 'DRAFT' | 'POSTED' | 'REVERSED' | 'CANCELLED'; header_total: string; discount_amount: string; tax_amount: string; rounding_amount: string
  row_version: string; variance_mode: string | null; paid: string; lines: BdInvoiceLine[] }
export type BdBillable = { receipt_line_id: string; receipt_number: string; delivery_number: string; po_number: string; received_local: string
  failed_attempt: boolean; estimate: string; released: string; price_known: boolean; capacity: Record<Category, number>; billed: Record<Category, number> }
export type BdOpening = { id: string; vendor_id: string; vendor_code: string; document_number: string; receipt_date: string; category: Category; qty: number
  billed: number; estimate_status: 'KNOWN' | 'UNKNOWN'; estimated_amount: string | null; released: string | null; invoiced: boolean
  po_number: string | null; dispatch_number: string | null; row_version: string }
export type BdPayableSettlement = { id: string; number: string; date: string; amount: string; method: 'CASH' | 'CLAIM_CREDIT' | 'CREDIT'; reference: string | null
  status: 'POSTED' | 'REVERSED' }
export type BdPayableDocument = { kind: 'VENDOR_INVOICE' | 'OPENING_PAYABLE'; id: string; number: string; date: string; total: string; paid_cash: string
  claim_credit: string; remaining: string; status: string; settlements: BdPayableSettlement[] }
export type BdClaimCredit = { kind: 'DAILY_CLAIM' | 'OPENING_CLAIM'; id: string; number: string; approved_date: string; amount: string; applied: string; available: string }
/** D12: the payment screen of one vendor; the ledger check is AP on the ledger = remaining of the documents - credit not yet used. */
export type BdPayables = { documents: BdPayableDocument[]; credits: BdClaimCredit[]; cash_accounts: { id: string; code: string; name: string }[]
  ledger: { ap_balance: string; documents_remaining: string; credit_available: string; matches: boolean } }
export type LaundryBdWorkspace = { money_visible: boolean; can_manage_master: boolean; can_set_price: boolean; is_owner: boolean
  policies: BdPolicy[]; vendors: BdVendor[]; processes: { id: string; code: string; name: string }[]; components: BdComponent[]; packages: BdPackage[]
  process_rates: BdProcessRate[]; scoped_rates: BdScopedRate[]; priced_deliveries: BdPricedDelivery[]; opening_uninvoiced: BdOpening[]
  invoices: BdInvoice[] | null; billable_receipts: BdBillable[] | null; accounts: { id: string; code: string; name: string; type: 'ASSET' | 'EXPENSE' }[] | null
  payables: BdPayables | null }

const uuid = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i
function object(value: unknown, label: string): Record<string, unknown> {
  if (!value || typeof value !== 'object' || Array.isArray(value)) throw new Error(`${label} tidak terbaca lengkap.`)
  return value as Record<string, unknown>
}
function list(value: unknown, label: string): Record<string, unknown>[] {
  if (!Array.isArray(value)) throw new Error(`${label} tidak terbaca lengkap.`)
  return value.map(v => object(v, label))
}
const nullableList = (value: unknown, label: string) => value === null ? null : list(value, label)
const id = (v: unknown, label: string) => { if (typeof v !== 'string' || !uuid.test(v)) throw new Error(`${label}: identitas tidak valid.`); return v }
const nullableId = (v: unknown, label: string) => v === null ? null : id(v, label)
const text = (v: unknown, label: string) => { if (typeof v !== 'string' || !v.trim()) throw new Error(`${label} tidak valid.`); return v }
const nullableText = (v: unknown, label: string) => v === null ? null : text(v, label)
const bool = (v: unknown, label: string) => { if (typeof v !== 'boolean') throw new Error(`${label} tidak valid.`); return v }
const count = (v: unknown, label: string) => { if (typeof v !== 'number' || !Number.isSafeInteger(v) || v < 0) throw new Error(`${label}: jumlah tidak valid.`); return v }
const money = (v: unknown, label: string) => { if (typeof v !== 'string' || !/^-?\d{1,18}\.\d{2}$/.test(v)) throw new Error(`${label}: nominal tidak valid.`); return v }
const nullableMoney = (v: unknown, label: string) => v === null ? null : money(v, label)
const version = (v: unknown, label: string) => { if (typeof v !== 'string' || !/^\d{1,19}$/.test(v)) throw new Error(`${label}: versi tidak valid.`); return v }
const day = (v: unknown, label: string) => { if (typeof v !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(v)) throw new Error(`${label}: tanggal tidak valid.`); return v }
const local = (v: unknown, label: string) => { if (typeof v !== 'string' || !/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}$/.test(v)) throw new Error(`${label}: waktu tidak valid.`); return v }
const nullableLocal = (v: unknown, label: string) => v === null ? null : local(v, label)
const oneOf = <T extends string>(v: unknown, allowed: readonly T[], label: string): T => {
  if (typeof v !== 'string' || !(allowed as readonly string[]).includes(v)) throw new Error(`${label} tidak dikenal.`)
  return v as T
}
const categories = ['GOOD', 'BS', 'FAILED_ATTEMPT'] as const
const perCategory = (v: unknown, label: string): Record<Category, number> => {
  const o = object(v, label)
  return { GOOD: count(o.GOOD, label), BS: count(o.BS, label), FAILED_ATTEMPT: count(o.FAILED_ATTEMPT, label) }
}
/** A money value the reader may not see must be null; one it may see must be present (a missing amount is an incomplete read). */
const gated = (v: unknown, visible: boolean, label: string) => {
  if (!visible) { if (v !== null && v !== undefined) throw new Error(`${label} tampil tanpa hak melihat nominal.`); return null }
  return nullableMoney(v, label)
}

export function parseLaundryBdWorkspace(value: unknown): LaundryBdWorkspace {
  const r = object(value, 'Harga laundry')
  const money_visible = bool(r.money_visible, 'Hak nominal')
  const policies = list(r.policies, 'Pengaturan laundry').map((p): BdPolicy => {
    const status = oneOf(p.status, ['SET', 'PENDING_POLICY_VALUE'] as const, 'Status pengaturan')
    const policyValue = p.value === null ? null : object(p.value, 'Nilai pengaturan')
    if ((status === 'SET') !== (policyValue !== null)) throw new Error('Nilai pengaturan tidak cocok dengan statusnya.')
    return { key: oneOf(p.key, LAU_POLICY_KEYS, 'Kunci pengaturan'), status, value: policyValue, version: version(p.version, 'Pengaturan'),
      set_at: local(p.set_at, 'Waktu pengaturan'), reason: text(p.reason, 'Alasan pengaturan') }
  })
  if (policies.length !== LAU_POLICY_KEYS.length || new Set(policies.map(p => p.key)).size !== LAU_POLICY_KEYS.length) throw new Error('Pengaturan laundry tidak lengkap.')
  const vendors = list(r.vendors, 'Vendor laundry').map((v): BdVendor => ({ id: id(v.id, 'Vendor'), code: text(v.code, 'Kode vendor'), name: text(v.name, 'Nama vendor'),
    pricing_mode: oneOf(v.pricing_mode, ['RATE', 'PACKAGE', 'COMPONENTS'] as const, 'Cara harga'), pricing_unit: oneOf(v.pricing_unit, ['PCS', 'BATCH'] as const, 'Satuan harga'),
    minimum_charge: gated(v.minimum_charge, money_visible, 'Minimum charge'), terms_version: version(v.terms_version, 'Ketentuan vendor'),
    bd_priced: bool(v.bd_priced, 'Harga BD') }))
  const processes = list(r.processes, 'Proses cuci').map(p => ({ id: id(p.id, 'Proses'), code: text(p.code, 'Kode proses'), name: text(p.name, 'Nama proses') }))
  const components = list(r.components, 'Komponen laundry').map((c): BdComponent => {
    const current = c.current === null ? null : object(c.current, 'Harga komponen')
    const status = current ? oneOf(current.status, ['KNOWN', 'UNKNOWN'] as const, 'Status harga komponen') : null
    const rate = current ? (status === 'UNKNOWN' ? (current.rate === null ? null : (() => { throw new Error('Harga komponen belum diketahui tidak boleh bernilai.') })())
      : gated(current.rate, money_visible, 'Harga komponen')) : null
    if (current && status === 'KNOWN' && money_visible && rate === null) throw new Error('Harga komponen yang diketahui tanpa nominal.')
    return { id: id(c.id, 'Komponen'), vendor_id: id(c.vendor_id, 'Vendor komponen'), code: text(c.code, 'Kode komponen'), name: text(c.name, 'Nama komponen'),
      is_active: bool(c.is_active, 'Status komponen'), current: current && status ? { status, rate, from: local(current.from, 'Berlaku sejak') } : null }
  })
  const packages = list(r.packages, 'Paket laundry').map((p): BdPackage => {
    if (!Array.isArray(p.component_ids)) throw new Error('Isi paket tidak terbaca lengkap.')
    return { id: id(p.id, 'Paket'), vendor_id: id(p.vendor_id, 'Vendor paket'), code: text(p.code, 'Kode paket'), name: text(p.name, 'Nama paket'),
      is_active: bool(p.is_active, 'Status paket'), component_ids: p.component_ids.map(x => id(x, 'Komponen paket')),
      current_rate: money_visible ? nullableMoney(p.current_rate, 'Harga paket') : gated(p.current_rate, false, 'Harga paket') }
  })
  const process_rates = list(r.process_rates, 'Tarif proses').map((x): BdProcessRate => ({ id: id(x.id, 'Tarif'), vendor_id: id(x.vendor_id, 'Vendor tarif'),
    wash_process_id: id(x.wash_process_id, 'Proses tarif'), rate: gated(x.rate, money_visible, 'Tarif proses'), from: local(x.from, 'Berlaku sejak'),
    to: nullableLocal(x.to, 'Berlaku sampai') }))
  const scoped_rates = list(r.scoped_rates, 'Tarif khusus').map((x): BdScopedRate => ({ id: id(x.id, 'Tarif khusus'), vendor_id: id(x.vendor_id, 'Vendor tarif khusus'),
    wash_process_id: id(x.wash_process_id, 'Proses tarif khusus'), scope: oneOf(x.scope, ['MODEL', 'MODEL_SIZE', 'MODEL_SIZE_COLOR'] as const, 'Cakupan tarif'),
    model_id: id(x.model_id, 'Model'), size_id: nullableId(x.size_id, 'Ukuran'), color_name: nullableText(x.color_name, 'Warna'),
    rate: gated(x.rate, money_visible, 'Tarif khusus'), from: local(x.from, 'Berlaku sejak') }))
  const priced_deliveries = list(r.priced_deliveries, 'Kiriman berharga').map((d): BdPricedDelivery => {
    const charges = list(d.charges, 'Rincian harga kiriman').map((c): BdCharge => {
      const rate_status = oneOf(c.rate_status, ['KNOWN', 'UNKNOWN'] as const, 'Status harga')
      const unit_rate = gated(c.unit_rate, money_visible, 'Harga satuan'), amount = gated(c.amount, money_visible, 'Nominal harga')
      if (money_visible && rate_status === 'KNOWN' && amount === null) throw new Error('Harga yang diketahui tanpa nominal.')
      if (rate_status === 'UNKNOWN' && (unit_rate !== null || amount !== null)) throw new Error('Harga belum diketahui tidak boleh bernilai.')
      return { id: id(c.id, 'Baris harga'), line_no: count(c.line_no, 'Nomor baris harga'), kind: oneOf(c.kind, Object.keys(CHARGE_KIND_LABEL) as ChargeKind[], 'Jenis harga'),
        label: text(c.label, 'Keterangan harga'), covered_qty: count(c.covered_qty, 'Qty harga'), rate_status, unit_rate, amount }
    })
    const total_complete = bool(d.total_complete, 'Harga lengkap')
    if (total_complete === charges.some(c => c.rate_status === 'UNKNOWN')) throw new Error('Status harga kiriman tidak cocok dengan rinciannya.')
    return { delivery_line_id: id(d.delivery_line_id, 'Baris kiriman'), delivery_id: id(d.delivery_id, 'Kiriman'), delivery_number: text(d.delivery_number, 'Nomor kirim'),
      status: text(d.status, 'Status kiriman'), physical_local: local(d.physical_local, 'Waktu kirim'), mode: text(d.mode, 'Cara harga'), unit: text(d.unit, 'Satuan'),
      qty_sent: count(d.qty_sent, 'Qty kirim'), total_known: gated(d.total_known, money_visible, 'Total diketahui'), total_complete, charges }
  })
  const opening_uninvoiced = list(r.opening_uninvoiced, 'Laundry saldo awal belum ditagih').map((u): BdOpening => {
    const estimate_status = oneOf(u.estimate_status, ['KNOWN', 'UNKNOWN'] as const, 'Status estimasi')
    const estimated_amount = gated(u.estimated_amount, money_visible, 'Estimasi')
    if (money_visible && (estimate_status === 'KNOWN') !== (estimated_amount !== null)) throw new Error('Estimasi saldo awal tidak cocok dengan statusnya.')
    const qty = count(u.qty, 'Qty belum ditagih'), billed = count(u.billed, 'Qty ditagih')
    if (!qty || billed > qty) throw new Error('Qty laundry saldo awal tidak cocok.')
    return { id: id(u.id, 'Laundry saldo awal'), vendor_id: id(u.vendor_id, 'Vendor'), vendor_code: text(u.vendor_code, 'Kode vendor'),
      document_number: text(u.document_number, 'Nomor terima lama'), receipt_date: day(u.receipt_date, 'Tanggal terima'),
      category: oneOf(u.category, categories, 'Kategori'), qty, billed, estimate_status, estimated_amount, released: gated(u.released, money_visible, 'Estimasi dilepas'),
      invoiced: bool(u.invoiced, 'Status tagih'), po_number: nullableText(u.po_number, 'Nomor PO'), dispatch_number: nullableText(u.dispatch_number, 'Nomor kirim lama'),
      row_version: version(u.row_version, 'Laundry saldo awal') }
  })
  const invoicesRaw = nullableList(r.invoices, 'Invoice laundry'), billableRaw = nullableList(r.billable_receipts, 'Penerimaan yang dapat ditagih')
  const accountsRaw = nullableList(r.accounts, 'Akun')
  if (!money_visible && (invoicesRaw !== null || billableRaw !== null || accountsRaw !== null)) throw new Error('Data nominal tampil tanpa hak melihat nominal.')
  if (money_visible && (invoicesRaw === null || accountsRaw === null)) throw new Error('Invoice laundry tidak terbaca lengkap.')
  const invoices = invoicesRaw?.map((i): BdInvoice => ({ invoice_id: id(i.invoice_id, 'Invoice'), vendor_id: id(i.vendor_id, 'Vendor invoice'),
    vendor_code: text(i.vendor_code, 'Kode vendor'), invoice_number: text(i.invoice_number, 'Nomor invoice'), invoice_date: day(i.invoice_date, 'Tanggal invoice'),
    due_date: i.due_date === null ? null : day(i.due_date, 'Jatuh tempo'), status: oneOf(i.status, ['DRAFT', 'POSTED', 'REVERSED', 'CANCELLED'] as const, 'Status invoice'),
    header_total: money(i.header_total, 'Total invoice'), discount_amount: money(i.discount_amount, 'Diskon'), tax_amount: money(i.tax_amount, 'Pajak'),
    rounding_amount: money(i.rounding_amount, 'Pembulatan'), row_version: version(i.row_version, 'Invoice'), variance_mode: nullableText(i.variance_mode, 'Perlakuan selisih'),
    paid: money(i.paid, 'Sudah dibayar'), lines: list(i.lines, 'Baris invoice').map((l): BdInvoiceLine => {
      const receipt_line_id = nullableId(l.receipt_line_id, 'Baris penerimaan'), opening_uninvoiced_id = nullableId(l.opening_uninvoiced_id, 'Penerimaan saldo awal')
      if ((receipt_line_id === null) === (opening_uninvoiced_id === null)) throw new Error('Sumber baris invoice tidak valid.')
      return { id: id(l.id, 'Baris invoice'), line_no: count(l.line_no, 'Nomor baris'), line_kind: oneOf(l.line_kind, ['BILL', 'CORRECTION'] as const, 'Jenis baris'),
        receipt_line_id, opening_uninvoiced_id, category: oneOf(l.category, categories, 'Kategori'), qty: count(l.qty, 'Qty baris'), amount: money(l.amount, 'Nominal baris'),
        net_amount: nullableMoney(l.net_amount, 'Nominal bersih'), released_estimate: nullableMoney(l.released_estimate, 'Estimasi dilepas'),
        variance: nullableMoney(l.variance, 'Selisih'), product_variance: nullableMoney(l.product_variance, 'Selisih ke biaya produk'),
        completes_source: bool(l.completes_source, 'Melunasi sumber') }
    }) })) ?? null
  const billable_receipts = billableRaw?.map((b): BdBillable => ({ receipt_line_id: id(b.receipt_line_id, 'Baris penerimaan'), receipt_number: text(b.receipt_number, 'Nomor terima'),
    delivery_number: text(b.delivery_number, 'Nomor kirim'), po_number: text(b.po_number, 'Nomor PO'), received_local: local(b.received_local, 'Waktu terima'),
    failed_attempt: bool(b.failed_attempt, 'Cuci gagal'), estimate: money(b.estimate, 'Estimasi'), released: money(b.released, 'Estimasi dilepas'),
    price_known: bool(b.price_known, 'Harga lengkap'), capacity: perCategory(b.capacity, 'Kapasitas tagih'), billed: perCategory(b.billed, 'Sudah ditagih') })) ?? null
  const accounts = accountsRaw?.map(a => ({ id: id(a.id, 'Akun'), code: text(a.code, 'Kode akun'), name: text(a.name, 'Nama akun'),
    type: oneOf(a.type, ['ASSET', 'EXPENSE'] as const, 'Jenis akun') })) ?? null
  const payables = r.payables === null || r.payables === undefined ? null : parsePayables(r.payables)
  if (payables && !money_visible) throw new Error('Pembayaran vendor tampil tanpa hak melihat nominal.')
  return { money_visible, can_manage_master: bool(r.can_manage_master, 'Hak master'), can_set_price: bool(r.can_set_price, 'Hak harga'), is_owner: bool(r.is_owner, 'Owner'),
    policies, vendors, processes, components, packages, process_rates, scoped_rates, priced_deliveries, opening_uninvoiced, invoices, billable_receipts, accounts, payables }
}

function parsePayables(value: unknown): BdPayables {
  const p = object(value, 'Pembayaran vendor'), l = object(p.ledger, 'Cocokkan buku besar')
  return {
    documents: list(p.documents, 'Tagihan vendor').map((d): BdPayableDocument => ({ kind: oneOf(d.kind, ['VENDOR_INVOICE', 'OPENING_PAYABLE'] as const, 'Jenis tagihan'),
      id: id(d.id, 'Tagihan'), number: text(d.number, 'Nomor tagihan'), date: day(d.date, 'Tanggal tagihan'), total: money(d.total, 'Total tagihan'),
      paid_cash: money(d.paid_cash, 'Dibayar kas'), claim_credit: money(d.claim_credit, 'Kredit klaim'), remaining: money(d.remaining, 'Sisa tagihan'),
      status: text(d.status, 'Status tagihan'),
      settlements: list(d.settlements, 'Riwayat pelunasan').map((x): BdPayableSettlement => ({ id: id(x.id, 'Pelunasan'), number: text(x.number, 'Nomor pelunasan'),
        date: day(x.date, 'Tanggal pelunasan'), amount: money(x.amount, 'Nominal pelunasan'), method: oneOf(x.method, ['CASH', 'CLAIM_CREDIT', 'CREDIT'] as const, 'Cara pelunasan'),
        reference: nullableText(x.reference, 'Rujukan pelunasan'), status: oneOf(x.status, ['POSTED', 'REVERSED'] as const, 'Status pelunasan') })) })),
    credits: list(p.credits, 'Kredit klaim').map((c): BdClaimCredit => ({ kind: oneOf(c.kind, ['DAILY_CLAIM', 'OPENING_CLAIM'] as const, 'Jenis klaim'), id: id(c.id, 'Klaim'),
      number: text(c.number, 'Nomor klaim'), approved_date: day(c.approved_date, 'Tanggal disetujui'), amount: money(c.amount, 'Kredit klaim'),
      applied: money(c.applied, 'Kredit terpakai'), available: money(c.available, 'Kredit tersedia') })),
    cash_accounts: list(p.cash_accounts, 'Rekening kas').map(a => ({ id: id(a.id, 'Rekening kas'), code: text(a.code, 'Kode rekening'), name: text(a.name, 'Nama rekening') })),
    ledger: { ap_balance: money(l.ap_balance, 'Saldo utang'), documents_remaining: money(l.documents_remaining, 'Sisa tagihan'),
      credit_available: money(l.credit_available, 'Kredit belum dipakai'), matches: bool(l.matches, 'Cocok buku besar') } }
}

/** The facade echoes the request; a priced delivery answers with the laundry writer's own POST_DELIVERY response. */
export function validateBdResult(value: unknown, action: string, request: string) {
  const r = object(value, 'Respons harga laundry')
  const echoed = action === 'POST_PRICED_DELIVERY' ? r.action === 'POST_DELIVERY' && r.client_request_id === request : r.action === action
  if (r.request_id !== request || !echoed) throw new Error('Respons harga laundry tidak cocok; pulihkan transaksi yang sama.')
}

// ---------------------------------------------------------------- input helpers (exact text)
export const moneyInput = (v: string) => /^\d{1,15}([.,]\d{1,2})?$/.test(v.trim())
export const normalizeMoney = (v: string) => { const [a, b = ''] = v.trim().replace(',', '.').split('.'); return `${a}.${b.padEnd(2, '0')}` }
export const signedMoneyInput = (v: string) => /^-?\d{1,15}([.,]\d{1,2})?$/.test(v.trim())
export const wholePcs = (v: string) => /^[1-9]\d{0,8}$/.test(v.trim())
export const wibTimestamp = (localValue: string) => /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(:\d{2})?$/.test(localValue) ? (localValue.length === 16 ? localValue + ':00' : localValue) + '+07:00' : null
export const rupiah = (raw: string | null) => {
  if (raw === null) return 'Tidak ditampilkan'
  const negative = raw.startsWith('-'), [whole, part = ''] = raw.replace('-', '').split('.')
  return `${negative ? '−' : ''}Rp ${whole.replace(/\B(?=(\d{3})+(?!\d))/g, '.')},${part.padEnd(2, '0').slice(0, 2)}`
}

/** The owner's value for one setting from the form fields, or a message; the server checks it again (accounts included). */
export function policyValue(key: LauPolicyKey, f: Record<string, string>, pick: Record<string, boolean>): Record<string, Json> | string {
  const chosen = (keys: string[]) => keys.filter(k => pick[k])
  switch (key) {
    case 'LAU-DEC01': { const units = chosen(['BATCH', 'MINIMUM']); return units.length ? { units } : 'Pilih BATCH dan/atau MINIMUM.' }
    case 'LAU-DEC02': { const billable = chosen(['GOOD', 'BS', 'FAILED_ATTEMPT']); return billable.length ? { billable } : 'Pilih minimal satu kategori yang ditagih.' }
    case 'LAU-DEC03': {
      if (!f.discount || !f.extra || !f.rounding) return 'Isi diskon, tambahan, dan pembulatan.'
      return { discount: f.discount, extra: f.extra, rounding: f.rounding, ...(f.tax_account_id ? { tax_account_id: f.tax_account_id } : {}) }
    }
    case 'LAU-DEC04': return f.sale ? { sale_with_unknown_laundry: f.sale } : 'Pilih perlakuan penjualan.'
    case 'LAU-DEC05': { const scopes = chosen(['MODEL', 'MODEL_SIZE', 'MODEL_SIZE_COLOR']); return scopes.length && f.fallback ? { scopes, fallback: f.fallback } : 'Pilih cakupan dan cadangan tarif.' }
    case 'LAU-DEC06': {
      if (!f.variance_mode || !f.after_payment) return 'Isi perlakuan selisih dan koreksi sesudah bayar.'
      if (f.variance_mode === 'VARIANCE_ACCOUNT' && !f.variance_account_id) return 'Pilih akun beban selisih.'
      return { variance_mode: f.variance_mode, after_payment: f.after_payment, ...(f.variance_mode === 'VARIANCE_ACCOUNT' ? { variance_account_id: f.variance_account_id } : {}) }
    }
  }
}
