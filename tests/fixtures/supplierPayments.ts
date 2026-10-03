// Synthetic UI/parser data only. Native qualification creates actual receipts,
// payment drafts and posts/inverses through the unchanged Native commands.
import type { SupplierPayment, SupplierPaymentRead } from '../../src/supplierPaymentContract'
export const supplierPurchaseId = 'a1000000-0000-0000-0000-000000000001'
export const supplierPaymentId = 'b2000000-0000-4000-8000-000000000026'
export const supplierInverseId = 'c3000000-0000-4000-8000-000000000002'
export function supplierPaymentFixture(): SupplierPayment {
  return { id: supplierPaymentId, number: 'PAY-SUP-026', status: 'POSTED', payment_date: '2026-09-26T05:00:00+00:00', amount: '10.00',
    cash_account_id: 'd4000000-0000-4000-8000-000000000001', cash_code: 'BANK', cash_name: 'Bank supplier',
    journal: { id: 'c3000000-0000-4000-8000-000000000001', number: 'JRN-SUP-026', status: 'POSTED',
      economic_date: '2026-09-26', accounting_date: '2026-09-26', posting_at: '2026-09-26T05:00:00Z', period_shifted: false },
    inverse: null, review_token: 'a'.repeat(32) }
}
export function supplierPaymentReadFixture(offset = 25, query = '', selectedPayment: string | null = null): SupplierPaymentRead {
  const actualOffset = selectedPayment ? 25 : offset
  const rows = query || actualOffset === 25 ? [supplierPaymentFixture()] : Array.from({ length: 25 }, (_, index) => {
    const p = supplierPaymentFixture(), suffix = String(index + 1).padStart(12, '0')
    p.id = 'b2000000-0000-4000-8000-' + suffix; p.number = 'PAY-SUP-' + String(index + 1).padStart(3, '0')
    p.journal!.id = 'c3000000-0000-4000-8000-' + suffix; p.journal!.number = 'JRN-SUP-' + String(index + 1).padStart(3, '0')
    return p
  })
  return { contract_version: 'cp7.supplier-payment-read.v1', captured_at: '2026-10-03T05:00:00Z', query, selected_payment_id: selectedPayment,
    purchase: { id: supplierPurchaseId, number: 'SJ-SUP-001', status: 'POSTED', supplier_id: 'e5000000-0000-4000-8000-000000000001', supplier_name: 'Supplier A' },
    Native_AP: { id: supplierPurchaseId, number: 'SJ-SUP-001', date: '2026-09-24', final_ap: '1000.00', paid: '260.00', remaining: '740.00', credit_delta: '0.00', payment_status: 'PARTIAL' },
    capabilities: { reverse: true }, page: { rows, total: query ? '1' : '26', offset: actualOffset, limit: 25, next_offset: query || actualOffset === 25 ? null : 25 } }
}
