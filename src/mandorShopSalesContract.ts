import {parseMandorShopBuyerOptions, type MandorShopBuyer} from './mandorShopContract'
import type {useProductionMutation} from './useProductionMutation'

export type BuyerFence = Pick<ReturnType<typeof useProductionMutation>, 'currentReadTicket' | 'isReadCurrent'>
export type SalesBuyerChoice = {
  category: 'TOKO' | 'MANDOR'; mandor: MandorShopBuyer | null; ready: boolean
  ticket: ReturnType<BuyerFence['currentReadTicket']>
}
export function salesBuyerCurrent(choice: SalesBuyerChoice, fence?: BuyerFence) {
  if (!choice.ready || choice.category === 'MANDOR' && !choice.mandor?.can_select) return false
  if (!fence) return true
  if (choice.category === 'MANDOR' && !choice.ticket) return false
  return !choice.ticket || fence.isReadCurrent(choice.ticket)
}
export function parseMandorShopCustomerBuyer(value: unknown, action: 'CREATE' | 'EDIT', customer: string) {
  if (!value || typeof value !== 'object' || Array.isArray(value)) throw Error('Kategori pembeli belum terverifikasi. Baca ulang sumber.')
  const r = value as Record<string, unknown>
  if (r.contract_version !== 'cp7.mandor-shop-customer-buyer.v1' || r.sales_action !== action || r.customer_id !== customer
    || !/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/.test(customer)) {
    throw Error('Kategori pembeli tidak cocok dengan invoice ini. Baca ulang sumber.')
  }
  if (r.buyer_category === 'TOKO' && r.mandor === null) return {category: 'TOKO' as const, mandor: null}
  if (r.buyer_category !== 'MANDOR') throw Error('Kategori pembeli tidak sah.')
  const options = parseMandorShopBuyerOptions({contract_version: 'cp7.mandor-shop-buyer-options.v1',
    buyer_category: 'MANDOR', sales_action: action, rows: [r.mandor], has_more: false, next_after: null}, action)
  if (options.rows[0].customer_id !== customer) throw Error('Identitas mandor tidak cocok dengan pelanggan invoice.')
  return {category: 'MANDOR' as const, mandor: options.rows[0]}
}
