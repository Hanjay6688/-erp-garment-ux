import type {SalesRead} from '../../src/salesReadContract'
import {recoveryIdentity} from './productionRecovery'

export const saleId = '30000000-0000-4000-8000-000000000001'
export const storeId = '30000000-0000-4000-8000-000000000002'
export const buyerId = '30000000-0000-4000-8000-000000000003'
export const buyerCustomer = '30000000-0000-4000-8000-000000000004'
export const otherBuyer = '30000000-0000-4000-8000-000000000005'
export const productId = '30000000-0000-4000-8000-000000000006'
export function salesShopAuth() {
  const a = structuredClone(recoveryIdentity)
  a.identity.permissions = ['sales.invoice.view', 'sales.invoice.create', 'sales.invoice.edit_draft', 'finance.ar.view']
  return a
}
export function buyerRow(action: 'CREATE' | 'EDIT' = 'EDIT', other = false) {
  return {contractor_id: other ? otherBuyer : buyerId, code: other ? 'M2' : 'M1', name: 'Epi',
    customer_id: other ? null : buyerCustomer, can_select: true, review_token: (action === 'EDIT' ? 'b' : 'c').repeat(64)}
}
export const buyerOptions = (action: 'CREATE' | 'EDIT' = 'EDIT') => ({
  contract_version: 'cp7.mandor-shop-buyer-options.v1', buyer_category: 'MANDOR', sales_action: action,
  rows: [buyerRow(action), buyerRow(action, true)], has_more: false, next_after: null,
})
export const classification = (customer = storeId, action: 'CREATE' | 'EDIT' = 'EDIT') => ({
  contract_version: 'cp7.mandor-shop-customer-buyer.v1', sales_action: action, customer_id: customer,
  buyer_category: customer === buyerCustomer ? 'MANDOR' : 'TOKO', mandor: customer === buyerCustomer ? buyerRow(action) : null,
})
export function shopDraft(customer = storeId, version = '5'): NonNullable<SalesRead['detail']> {
  return {id: saleId, number: 'INV-EPI-FORM', customer_id: customer, customer_name: customer === buyerCustomer ? 'Epi' : 'Toko Epi',
    location_id: storeId, location_name: 'Gudang FG', physical_at: '2026-11-01T02:00:00.123456Z', due_date: null,
    status: 'DRAFT', row_version: version, notes: 'Catatan awal', payment_terms: 'Kredit', line_count: '1', qty_pcs: '1',
    reserved_qty: '1', returned_qty: '0', financial: {basis: 'CURRENT_NATIVE_DOCUMENT', state: 'DRAFT_PREVIEW',
      gross_total: '300000.00', return_total: '0.00', net_total: '300000.00', paid_total: '0.00', open_balance: null},
    review_token: 'a'.repeat(32), items: [{id: productId, product_id: productId, product_sku: 'FG-01', commercial_sku: 'FG-01',
      product_name: 'Celana', size_code: '32', brand_name: 'Vivo', qty_pcs: '1', notes: 'Catatan barang',
      financial: {unit_price: '300000.00', discount: '0.00', line_total: '300000.00'}}]}
}
export function salesShopRead(selected: boolean, customer = storeId, version = '5'): SalesRead {
  const detail = shopDraft(customer, version), {items: _items, review_token: _review, ...row} = detail
  return {contract_version: 'cp7.sales-workspace.v1', read_at: '2026-11-02T01:00:00Z', financial_captured: true,
    read_only: true, page: {rows: [row], total: '1', offset: 0, limit: 25, next_offset: null}, detail: selected ? detail : null}
}
