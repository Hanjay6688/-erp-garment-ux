import {expect, it} from 'vitest'
import {parseMandorShopCustomerBuyer, salesBuyerCurrent} from './mandorShopSalesContract'
import {buyerCustomer, buyerId, classification, storeId} from '../tests/fixtures/mandorShopSales'
it('distinguishes store and explicit Mandor customer UUIDs with the same visible name', () => {
  expect(parseMandorShopCustomerBuyer(classification(), 'EDIT', storeId)).toEqual({category: 'TOKO', mandor: null})
  expect(parseMandorShopCustomerBuyer(classification(buyerCustomer), 'EDIT', buyerCustomer).mandor?.contractor_id).toBe(buyerId)
})
it('rejects wrong customer, wrong action and a Mandor account bound to another customer', () => {
  expect(() => parseMandorShopCustomerBuyer(classification(), 'EDIT', buyerCustomer)).toThrow()
  expect(() => parseMandorShopCustomerBuyer(classification(buyerCustomer, 'CREATE'), 'EDIT', buyerCustomer)).toThrow()
  const wrong = classification(buyerCustomer); wrong.mandor!.customer_id = storeId
  expect(() => parseMandorShopCustomerBuyer(wrong, 'EDIT', buyerCustomer)).toThrow()
})
it('rejects a store label with hidden Mandor data and malformed review tokens', () => {
  expect(() => parseMandorShopCustomerBuyer({...classification(), mandor: classification(buyerCustomer).mandor}, 'EDIT', storeId)).toThrow()
  const wrong = classification(buyerCustomer); wrong.mandor!.review_token = 'b'.repeat(63)
  expect(() => parseMandorShopCustomerBuyer(wrong, 'EDIT', buyerCustomer)).toThrow()
})
it('requires current parent authority and an active explicit Mandor selection before save', () => {
  const ticket = {sequence: 1, scope: 's', signature: 's', session: {}}
  const c = {...parseMandorShopCustomerBuyer(classification(buyerCustomer), 'EDIT', buyerCustomer), ready: true, ticket}
  expect(salesBuyerCurrent(c, {currentReadTicket: () => ticket, isReadCurrent: () => true})).toBe(true)
  expect(salesBuyerCurrent(c, {currentReadTicket: () => ticket, isReadCurrent: () => false})).toBe(false)
  expect(salesBuyerCurrent({...c, mandor: {...c.mandor!, can_select: false}})).toBe(false)
  expect(salesBuyerCurrent({...c, ticket: null}, {currentReadTicket: () => ticket, isReadCurrent: () => true})).toBe(false)
})
