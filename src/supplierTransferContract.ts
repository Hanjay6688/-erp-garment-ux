import type { Json } from './types/database.preconnect'
import { signedSupplierSourceCents } from './supplierCredit'

/** OW06: one supplier transfer paid out once and allocated to several receipts. */
export type SupplierTransferJournal = {
  id: string; number: string; status: 'POSTED' | 'REVERSED'; economic_date: string
  accounting_date: string; posting_at: string; period_shifted: boolean
}
export type SupplierTransferReceipt = {
  id: string; number: string; physical_at: string; remaining: string; release_on_correction: string; payable_after_release: string
}
export type SupplierTransferCash = { id: string; code: string; name: string }
export type SupplierTransferRow = { id: string; number: string; status: 'DRAFT' | 'POSTED' | 'REVERSED'; amount: string; payment_date: string }
export type SupplierTransferAllocation = { purchase_id: string; purchase_number: string; payment_id: string; amount: string }
export type SupplierTransferDetail = {
  id: string; number: string; supplier_id: string; status: 'POSTED' | 'REVERSED'; payment_date: string; amount: string
  cash_account_id: string; cash_name: string; note: string; journal: SupplierTransferJournal; inverse: SupplierTransferJournal | null
  allocations: SupplierTransferAllocation[]; previous_id: string | null; replacement_id: string | null
}
type Page<T> = { rows: T[]; total: string; offset: number; limit: 25; next_offset: number | null }
export type SupplierTransferQuery = {
  supplier_id: string; transfer_id: string | null; purchase_q: string; purchase_offset: number
  bank_q: string; bank_offset: number; transfer_offset: number
}
export type SupplierTransferWorkspace = {
  contract_version: 'cp7.supplier-transfer-workspace.v1'; captured_at: string
  supplier: { id: string; name: string }; can_write: boolean; review_token: string; query: SupplierTransferQuery
  receipts: Page<SupplierTransferReceipt>; cash_accounts: Page<SupplierTransferCash>; transfers: Page<SupplierTransferRow>
  selected: SupplierTransferDetail | null
}
export type SupplierTransferAllocationInput = { purchase_id: string; amount: string }
export type SupplierTransferPayload =
  | { action: 'CREATE'; supplier_id: string; review_token: string; reason: string; amount: string; cash_account_id: string; payment_date: string; allocations: SupplierTransferAllocationInput[] }
  | { action: 'CORRECT'; supplier_id: string; transfer_id: string; review_token: string; reason: string; amount: string; cash_account_id: string; payment_date: string; allocations: SupplierTransferAllocationInput[] }
  | { action: 'REVERSE'; supplier_id: string; transfer_id: string; review_token: string; reason: string }
export type SupplierTransferOutcome = {
  action: SupplierTransferPayload['action']; supplier_id: string; transfer_id: string; original_transfer_id: string | null; status: 'POSTED' | 'REVERSED'
}

const fail = (): never => { throw Error('Transfer supplier belum lengkap atau sudah berubah. Muat ulang transfer supplier.') }
const uuid = (v: unknown): v is string => typeof v === 'string' && /^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$/i.test(v)
const text = (v: unknown): v is string => typeof v === 'string' && v.trim().length > 0
const token = (v: unknown): v is string => typeof v === 'string' && /^[a-f0-9]{32}$/.test(v)
const date = (v: unknown): v is string => typeof v === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(v)
  && Number.isFinite(Date.parse(v + 'T00:00:00Z')) && new Date(v + 'T00:00:00Z').toISOString().slice(0, 10) === v
const time = (v: unknown): v is string => typeof v === 'string' && v.includes('T') && Number.isFinite(Date.parse(v))
function closed(v: unknown, keys: string[]) {
  if (!v || typeof v !== 'object' || Array.isArray(v) || Object.keys(v).sort().join('|') !== [...keys].sort().join('|')) return fail()
  return v as Record<string, unknown>
}
/** Exact cents of a server money string; never a float. */
export function transferCents(v: unknown) {
  if (typeof v !== 'string' || !/^-?(0|[1-9][0-9]{0,17})\.\d{2}$/.test(v)) return fail()
  return signedSupplierSourceCents(v)
}
export function centsText(c: bigint) {
  const sign = c < 0n ? '-' : '', a = c < 0n ? -c : c
  return `${sign}${a / 100n}.${(a % 100n).toString().padStart(2, '0')}`
}
function journal(v: unknown): SupplierTransferJournal {
  const r = closed(v, ['id', 'number', 'status', 'economic_date', 'accounting_date', 'posting_at', 'period_shifted'])
  if (!uuid(r.id) || !text(r.number) || !['POSTED', 'REVERSED'].includes(String(r.status)) || !date(r.economic_date)
    || !date(r.accounting_date) || !time(r.posting_at) || typeof r.period_shifted !== 'boolean') fail()
  return r as unknown as SupplierTransferJournal
}
function page<T>(v: unknown, offset: number, row: (x: unknown) => T, id: (x: T) => string): Page<T> {
  const p = closed(v, ['rows', 'total', 'offset', 'limit', 'next_offset'])
  if (!Array.isArray(p.rows) || typeof p.total !== 'string' || !/^(0|[1-9][0-9]{0,18})$/.test(p.total) || p.offset !== offset
    || p.limit !== 25 || p.rows.length > 25) fail()
  const rows = (p.rows as unknown[]).map(row), end = BigInt(offset) + BigInt(rows.length), total = BigInt(p.total as string)
  if (new Set(rows.map(id)).size !== rows.length || rows.length && end > total
    || (end < total ? p.next_offset !== offset + rows.length : p.next_offset !== null)) fail()
  return { rows, total: p.total as string, offset, limit: 25, next_offset: p.next_offset as number | null }
}
function receipt(v: unknown): SupplierTransferReceipt {
  const r = closed(v, ['id', 'number', 'physical_at', 'remaining', 'release_on_correction', 'payable_after_release'])
  if (!uuid(r.id) || !text(r.number) || !time(r.physical_at)) fail()
  const remaining = transferCents(r.remaining), released = transferCents(r.release_on_correction), payable = transferCents(r.payable_after_release)
  if (released < 0n || payable !== remaining + released || payable <= 0n) fail()
  return r as unknown as SupplierTransferReceipt
}
function cash(v: unknown): SupplierTransferCash {
  const r = closed(v, ['id', 'code', 'name'])
  if (!uuid(r.id) || !text(r.code) || !text(r.name)) fail()
  return r as unknown as SupplierTransferCash
}
function transferRow(v: unknown): SupplierTransferRow {
  const r = closed(v, ['id', 'number', 'status', 'amount', 'payment_date'])
  if (!uuid(r.id) || !text(r.number) || !['DRAFT', 'POSTED', 'REVERSED'].includes(String(r.status)) || transferCents(r.amount) <= 0n || !time(r.payment_date)) fail()
  return r as unknown as SupplierTransferRow
}
function detail(v: unknown, supplier: string, transfer: string): SupplierTransferDetail {
  const r = closed(v, ['id', 'number', 'supplier_id', 'status', 'payment_date', 'amount', 'cash_account_id', 'cash_name', 'note', 'journal', 'inverse',
    'allocations', 'previous_id', 'replacement_id'])
  if (r.id !== transfer || r.supplier_id !== supplier || !text(r.number) || !['POSTED', 'REVERSED'].includes(String(r.status)) || !time(r.payment_date)
    || !uuid(r.cash_account_id) || !text(r.cash_name) || !text(r.note) || !Array.isArray(r.allocations) || !r.allocations.length
    || !(r.previous_id === null || uuid(r.previous_id)) || !(r.replacement_id === null || uuid(r.replacement_id))) fail()
  const amount = transferCents(r.amount), j = journal(r.journal), inverse = r.inverse === null ? null : journal(r.inverse)
  if (amount <= 0n || j.status !== r.status || (r.status === 'POSTED') !== (inverse === null) || inverse && (inverse.status !== 'POSTED' || inverse.id === j.id)
    || r.replacement_id !== null && r.status !== 'REVERSED') fail()
  const allocations = (r.allocations as unknown[]).map(x => {
    const a = closed(x, ['purchase_id', 'purchase_number', 'payment_id', 'amount'])
    if (!uuid(a.purchase_id) || !text(a.purchase_number) || !uuid(a.payment_id) || transferCents(a.amount) <= 0n) fail()
    return a as unknown as SupplierTransferAllocation
  })
  if (new Set(allocations.map(a => a.purchase_id)).size !== allocations.length || new Set(allocations.map(a => a.payment_id)).size !== allocations.length
    || allocations.reduce((s, a) => s + transferCents(a.amount), 0n) !== amount) fail()
  return { ...r, journal: j, inverse, allocations } as unknown as SupplierTransferDetail
}

/** The workspace must answer exactly the query that was sent, for the same supplier. */
export function parseSupplierTransferWorkspace(value: unknown, query: SupplierTransferQuery): SupplierTransferWorkspace {
  const r = closed(value, ['contract_version', 'captured_at', 'supplier', 'can_write', 'review_token', 'query', 'receipts', 'cash_accounts', 'transfers', 'selected'])
  const s = closed(r.supplier, ['id', 'name'])
  const q = closed(r.query, ['supplier_id', 'transfer_id', 'purchase_q', 'purchase_offset', 'bank_q', 'bank_offset', 'transfer_offset'])
  if (r.contract_version !== 'cp7.supplier-transfer-workspace.v1' || !time(r.captured_at) || s.id !== query.supplier_id || !text(s.name)
    || typeof r.can_write !== 'boolean' || !token(r.review_token)
    || q.supplier_id !== query.supplier_id || q.transfer_id !== query.transfer_id || q.purchase_q !== query.purchase_q.trim() || q.bank_q !== query.bank_q.trim()
    || q.purchase_offset !== query.purchase_offset || q.bank_offset !== query.bank_offset || q.transfer_offset !== query.transfer_offset) fail()
  const receipts = page(r.receipts, query.purchase_offset, receipt, x => x.id)
  const cash_accounts = page(r.cash_accounts, query.bank_offset, cash, x => x.id)
  const transfers = page(r.transfers, query.transfer_offset, transferRow, x => x.id)
  const selected = query.transfer_id === null ? (r.selected === null ? null : fail()) : detail(r.selected, query.supplier_id, query.transfer_id)
  if (selected && selected.status === 'REVERSED' && receipts.rows.some(x => transferCents(x.release_on_correction) !== 0n)) fail()
  if (selected && selected.status === 'POSTED') {
    // A posted transfer releases exactly its own allocation on each shown receipt.
    for (const x of receipts.rows) {
      const own = selected.allocations.find(a => a.purchase_id === x.id)
      if (transferCents(x.release_on_correction) !== (own ? transferCents(own.amount) : 0n)) fail()
    }
  }
  if (!selected && receipts.rows.some(x => transferCents(x.release_on_correction) !== 0n)) fail()
  return { ...r, query: { ...query, purchase_q: query.purchase_q.trim(), bank_q: query.bank_q.trim() }, receipts, cash_accounts, transfers, selected } as unknown as SupplierTransferWorkspace
}

function canonical(v: unknown): unknown {
  if (Array.isArray(v)) return v.map(canonical)
  if (v && typeof v === 'object') return Object.fromEntries(Object.keys(v).sort().map(k => [k, canonical((v as Record<string, unknown>)[k])]))
  return v
}

/** Payload builder: allocations in cents, total equals their exact sum, one row per receipt. */
export function supplierTransferPayload(base: { action: 'CREATE' | 'CORRECT'; supplier_id: string; transfer_id?: string; review_token: string; reason: string;
  cash_account_id: string; payment_date: string }, allocations: SupplierTransferAllocationInput[]): SupplierTransferPayload | null {
  if (!allocations.length || new Set(allocations.map(a => a.purchase_id)).size !== allocations.length) return null
  let total = 0n
  for (const a of allocations) {
    if (!uuid(a.purchase_id) || !/^(0|[1-9][0-9]{0,17})\.\d{2}$/.test(a.amount)) return null
    const c = signedSupplierSourceCents(a.amount); if (c <= 0n) return null; total += c
  }
  const reason = base.reason.trim()
  if (reason.length < 5 || reason.length > 500 || !uuid(base.cash_account_id) || !time(base.payment_date)) return null
  const common = { supplier_id: base.supplier_id, review_token: base.review_token, reason, amount: centsText(total), cash_account_id: base.cash_account_id,
    payment_date: base.payment_date, allocations: [...allocations].sort((x, y) => x.purchase_id.localeCompare(y.purchase_id)) }
  if (base.action === 'CORRECT') return base.transfer_id && uuid(base.transfer_id) ? { action: 'CORRECT', transfer_id: base.transfer_id, ...common } : null
  return { action: 'CREATE', ...common }
}

export function parseSupplierTransferOutcome(value: unknown, requestId: string, payload: Json): SupplierTransferOutcome {
  const r = closed(value, ['contract_version', 'kind', 'action', 'request_id', 'request_payload', 'supplier_id', 'transfer_id', 'original_transfer_id', 'status'])
  const d = payload as Record<string, unknown>
  if (!d || typeof d !== 'object' || Array.isArray(d)) return fail()
  if (r.contract_version !== 'cp7.supplier-transfer-outcome.v1' || r.kind !== 'COMMITTED_OUTCOME' || r.request_id !== requestId
    || r.action !== d.action || r.supplier_id !== d.supplier_id || !uuid(r.transfer_id)
    || JSON.stringify(canonical(r.request_payload)) !== JSON.stringify(canonical(d))) fail()
  if (d.action === 'CREATE' ? r.original_transfer_id !== null || r.status !== 'POSTED'
    : d.action === 'CORRECT' ? r.original_transfer_id !== d.transfer_id || r.status !== 'POSTED' || r.transfer_id === d.transfer_id
    : d.action === 'REVERSE' ? r.original_transfer_id !== d.transfer_id || r.transfer_id !== d.transfer_id || r.status !== 'REVERSED' : true) fail()
  if (!['CREATE', 'CORRECT', 'REVERSE'].includes(String(d.action))) fail()
  return r as unknown as SupplierTransferOutcome
}
