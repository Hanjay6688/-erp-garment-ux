import { expect, it } from 'vitest'
import { shopAllocation, shopId, shopMandor, shopPayroll, shopSale, shopWorkspace } from '../tests/fixtures/mandorShop'
import { mandorShopAmount, mandorShopCents, parseMandorShopAllocationOutcome, parseMandorShopBuyerOptions, parseMandorShopBuyerOutcome, parseMandorShopWorkspace } from './mandorShopContract'

it('reads the same chosen week and exact invoice allocation without claiming a draft is paid', () => {
  const w = parseMandorShopWorkspace(shopWorkspace(true), shopPayroll, shopMandor)
  expect(w.period_start).toBe('2026-11-09'); expect(w.net_payable_preview).toBe('1700000.00')
  expect(w.cards[0]).toMatchObject({ paid_amount: '0.00', outstanding: '300000.00', available_to_reserve: '0.00' })
  expect(w.cards[0].allocations[0]).toMatchObject({ payroll_id: shopPayroll, state: 'RESERVED', amount: '300000.00' })
})
it('rejects a different payroll, mandor, or nested invoice identity', () => {
  expect(() => parseMandorShopWorkspace(shopWorkspace(), shopId(8), shopMandor)).toThrow()
  expect(() => parseMandorShopWorkspace(shopWorkspace(), shopPayroll, shopId(8))).toThrow()
  const w = shopWorkspace(true); w.cards[0].allocations[0].allocation.sale_id = shopId(8)
  expect(() => parseMandorShopWorkspace(w, shopPayroll, shopMandor)).toThrow()
})
it('keeps cents beyond the JavaScript safe integer range and rejects numeric JSON money', () => {
  expect(mandorShopAmount(mandorShopCents('9007199254740993,99')!)).toBe('9007199254740993.99')
  const w = shopWorkspace(true), huge = '9007199254740993.99'
  w.cards[0].net_invoice = huge; w.cards[0].outstanding = huge; w.cards[0].allocated_amount = huge
  w.cards[0].allocations[0].allocation.amount = huge
  expect(parseMandorShopWorkspace(w, shopPayroll, shopMandor).cards[0].allocations[0].amount).toBe(huge)
  const bad = structuredClone(w) as unknown as Record<string, unknown>; bad.net_payable_preview = 1700000
  expect(() => parseMandorShopWorkspace(bad, shopPayroll, shopMandor)).toThrow()
})
it('rejects contradictory outstanding, reserved totals and available amounts; legitimate overpayment stays visible', () => {
  for (const field of ['outstanding', 'allocated_amount', 'available_to_reserve'] as const) {
    const w = shopWorkspace(true); w.cards[0][field] = '1.00'
    expect(() => parseMandorShopWorkspace(w, shopPayroll, shopMandor)).toThrow()
  }
  const w = shopWorkspace(); w.cards[0].paid_amount = '350000.00'; w.cards[0].outstanding = '-50000.00'; w.cards[0].available_to_reserve = '-50000.00'
  expect(parseMandorShopWorkspace(w, shopPayroll, shopMandor).cards[0].outstanding).toBe('-50000.00')
})
it('refuses duplicate cards, an invented next cursor, impossible dates and an editable paid payroll', () => {
  const duplicate = shopWorkspace(); duplicate.cards.push(duplicate.cards[0]); expect(() => parseMandorShopWorkspace(duplicate, shopPayroll, shopMandor)).toThrow()
  const cursor = shopWorkspace(); cursor.has_more = true; cursor.next_after = shopId(9); expect(() => parseMandorShopWorkspace(cursor, shopPayroll, shopMandor)).toThrow()
  const day = shopWorkspace(); day.period_start = '2026-02-31'; expect(() => parseMandorShopWorkspace(day, shopPayroll, shopMandor)).toThrow()
  const paid = shopWorkspace(); paid.status = 'PAID'; expect(() => parseMandorShopWorkspace(paid, shopPayroll, shopMandor)).toThrow()
})
it('accepts only canonical exact input amounts without grouping, exponent or extra fractional cents', () => {
  expect(mandorShopCents(' 300000,19 ')).toBe(30000019n); expect(mandorShopAmount(-1n)).toBe('-0.01')
  for (const bad of ['1.000.000', '1e3', '1.001', '-1', '01', '1000000000000000000']) expect(mandorShopCents(bad)).toBeNull()
})
it('binds committed allocation responses to the old request, action, payroll and invoice', () => {
  const request = shopId(20), outcome = { contract_version: 'cp7.mandor-shop-allocation-outcome.v1', kind: 'COMMITTED_OUTCOME',
    action: 'RESERVE', request_id: request, payroll_id: shopPayroll, sale_id: shopSale, allocation_id: shopAllocation,
    net_payable: '1700000.00', invoice_settled_by_this_command: false }
  expect(parseMandorShopAllocationOutcome(outcome, request, 'RESERVE', shopPayroll, shopSale).net_payable).toBe('1700000.00')
  for (const changed of [{ request_id: shopId(21) }, { action: 'RELEASE' }, { sale_id: shopId(22) }, { invoice_settled_by_this_command: true }])
    expect(() => parseMandorShopAllocationOutcome({ ...outcome, ...changed }, request, 'RESERVE', shopPayroll, shopSale)).toThrow()
})
it('keeps same-name buyer UUIDs separate and requires the exact prepared-buyer request', () => {
  const rows = [shopMandor, shopId(10)].map(id => ({ contractor_id: id, code: id, name: 'Epi', customer_id: null, can_select: true, review_token: 'b'.repeat(64) }))
  const value = { contract_version: 'cp7.mandor-shop-buyer-options.v1', buyer_category: 'MANDOR', sales_action: 'CREATE', rows, has_more: false, next_after: null }
  expect(parseMandorShopBuyerOptions(value, 'CREATE').rows.map(x => x.contractor_id)).toEqual([shopMandor, shopId(10)])
  expect(() => parseMandorShopBuyerOptions(value, 'EDIT')).toThrow()
  const outcome = { contract_version: 'cp7.mandor-shop-buyer-outcome.v1', buyer_category: 'MANDOR', request_id: shopId(20), contractor_id: shopMandor, customer_id: shopId(30), name: 'Epi', customer_code: 'MD-EXPLICIT' }
  expect(parseMandorShopBuyerOutcome(outcome, shopId(20), shopMandor).customer_id).toBe(shopId(30))
  expect(() => parseMandorShopBuyerOutcome(outcome, shopId(21), shopMandor)).toThrow()
})
