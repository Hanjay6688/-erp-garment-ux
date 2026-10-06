import { parseSalesCashAccountPage, type SalesCashAccount } from './salesCashContract'
import { signedSupplierSourceCents } from './supplierCredit'
import type { SupplierPaymentRead } from './supplierPaymentContract'
import type { Json } from './types/database.preconnect'

const fail = (): never => { throw Error('Data pembayaran supplier baru belum lengkap atau sudah berubah. Muat ulang pembayaran.') }
const uuid = (v: unknown): v is string => typeof v === 'string' && /^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$/i.test(v)
const time = (v: unknown): v is string => typeof v === 'string' && v.includes('T') && Number.isFinite(Date.parse(v))
const text = (v: unknown): v is string => typeof v === 'string' && v.length > 0
function closed(v: unknown, keys: string[]) {
  if (!v || typeof v !== 'object' || Array.isArray(v) || Object.keys(v).sort().join('|') !== [...keys].sort().join('|')) return fail()
  return v as Record<string, unknown>
}
function canonical(v: unknown): unknown {
  if (Array.isArray(v)) return v.map(canonical)
  if (v && typeof v === 'object') return Object.fromEntries(Object.keys(v).sort().map(k => [k, canonical((v as Record<string, unknown>)[k])]))
  return v
}
function cents(v: unknown) {
  if (typeof v !== 'string' || !/^-?(0|[1-9][0-9]{0,17})\.\d{2}$/.test(v)) return fail()
  return signedSupplierSourceCents(v)
}

export type SupplierPaymentCreateRead = {
  contract_version: 'cp7.supplier-payment-create-workspace.v1'; captured_at: string
  purchase: { id: string; number: string; status: 'DRAFT' | 'POSTED' | 'REVERSED'; physical_at: string; supplier_id: string; supplier_name: string }
  Native_AP: SupplierPaymentRead['Native_AP']; eligible: boolean; review_token: string; can_create: boolean
  cash_accounts: { rows: SalesCashAccount[]; total: string; offset: number; limit: number; next_offset: number | null }
}

/** The create workspace must describe the same receipt and the same Native AP as the payment list it is opened from. */
export function parseSupplierPaymentCreateRead(value: unknown, source: SupplierPaymentRead, bankOffset: number): SupplierPaymentCreateRead {
  const r = closed(value, ['contract_version', 'captured_at', 'purchase', 'Native_AP', 'eligible', 'review_token', 'can_create', 'cash_accounts'])
  const h = closed(r.purchase, ['id', 'number', 'status', 'physical_at', 'supplier_id', 'supplier_name'])
  if (r.contract_version !== 'cp7.supplier-payment-create-workspace.v1' || !time(r.captured_at) || h.id !== source.purchase.id
    || h.number !== source.purchase.number || h.status !== source.purchase.status || h.supplier_id !== source.purchase.supplier_id
    || !uuid(h.supplier_id) || !text(h.supplier_name) || !time(h.physical_at) || typeof r.eligible !== 'boolean'
    || typeof r.review_token !== 'string' || !/^[a-f0-9]{32}$/.test(r.review_token) || r.can_create !== source.capabilities.reverse
    || JSON.stringify(canonical(r.Native_AP)) !== JSON.stringify(canonical(source.Native_AP))) fail()
  const ap = source.Native_AP
  if (r.eligible !== (h.status === 'POSTED' && ap !== null && cents(ap.remaining) > 0n)) fail()
  return { ...r, cash_accounts: parseSalesCashAccountPage(r.cash_accounts, bankOffset, 25) } as unknown as SupplierPaymentCreateRead
}

export type SupplierPaymentCreatePayload = { purchase_id: string; review_token: string; amount: string; cash_account_id: string; payment_date: string; note: string }

export function parseSupplierPaymentCreateOutcome(value: unknown, requestId: string, payload: Json) {
  const r = closed(value, ['contract_version', 'kind', 'action', 'request_id', 'request_payload', 'purchase_id', 'payment_id', 'status', 'amount', 'remaining_after'])
  const d = closed(payload, ['purchase_id', 'review_token', 'amount', 'cash_account_id', 'payment_date', 'note'])
  if (r.contract_version !== 'cp7.supplier-payment-create.v1' || r.kind !== 'COMMITTED_OUTCOME' || r.action !== 'CREATE'
    || r.request_id !== requestId || r.purchase_id !== d.purchase_id || ![r.purchase_id, r.payment_id].every(uuid) || r.status !== 'POSTED'
    || r.amount !== d.amount || cents(r.remaining_after) < 0n
    || JSON.stringify(canonical(r.request_payload)) !== JSON.stringify(canonical(d))) fail()
  return r as unknown as { purchase_id: string; payment_id: string; status: 'POSTED'; amount: string; remaining_after: string }
}
