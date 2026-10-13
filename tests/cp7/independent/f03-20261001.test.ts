import { describe, expect, it } from 'vitest'
import { salesLineTotal, salesMoneyInput, salesQtyInput } from '../../../src/salesReadContract'
import { salesCashAmount, salesCashCents } from '../../../src/salesCashContract'
import { salesReturnTotal } from '../../../src/salesReturnContract'
import { installmentCents, validInstallmentAmount } from '../../../src/payrollInstallmentContract'
import { formatReceiptDecimal, receiptDecimal } from '../../../src/procurementContract'
import { financeDate } from '../../../src/financeReportContract'

// Auditor-owned operands; this qualifies local contract arithmetic only.
// It does not claim SQL execution, real Auth, or browser integration.
describe('F03 independent numeric boundaries, 2026-10-01', () => {
  it('agrees with the independent seven-piece worksheet', () => {
    expect(salesLineTotal('7', '37,13', '0,06')).toBe('259.85')
    expect(salesCashCents('123.45') + salesCashCents('136.40')).toBe(25985n)
    expect(salesReturnTotal(['37.11', '37.11'])).toBe('74.22')
  })
  it('keeps cents beyond JavaScript safe integer', () => {
    expect(salesLineTotal('7', '9007199254740.99', '0.06')).toBe('63050394783186.87')
    expect(formatReceiptDecimal('9007199254740993.01')).toBe('9.007.199.254.740.993,01')
    expect(installmentCents('9007199254740993.01')).toBe(900719925474099301n)
  })
  it('does not round an oversized installment into the remaining balance', () => {
    expect(validInstallmentAmount('9007199254740993.02', '9007199254740993.01')).toBe(false)
    expect(validInstallmentAmount('9007199254740993.01', '9007199254740993.01')).toBe(true)
  })
  it('preserves a one-cent final installment', () => {
    expect(installmentCents('333.33') * 2n + installmentCents('333.34')).toBe(100000n)
    expect(validInstallmentAmount('0.01', '0.01')).toBe(true)
    expect(validInstallmentAmount('0.02', '0.01')).toBe(false)
  })
  it('does not permit a discount above the whole line', () => {
    expect(salesLineTotal('7', '37.13', '259.92')).toBe(null)
    expect(salesLineTotal('7', '37.13', '259.91')).toBe('0.00')
  })
  for (const bad of ['NaN', 'Infinity', '-Infinity', '1e3', '1.001', '1,000.00', '1.000,00', '-1', '']) {
    it(`refuses ambiguous or unsupported cash input ${JSON.stringify(bad)}`, () => {
      expect(salesMoneyInput(bad)).toBe(null)
      expect(salesCashAmount(bad)).toBe(null)
      expect(validInstallmentAmount(bad, '1000')).toBe(false)
    })
  }
  for (const bad of ['0', '-1', '1.5', '1e3', 'NaN', '01']) {
    it(`refuses non-PCS invoice quantity ${JSON.stringify(bad)}`, () => expect(salesQtyInput(bad)).toBe(null))
  }
  it('keeps all six receipt decimals and refuses a seventh', () => {
    expect(receiptDecimal('1,234567', true)).toBe('1.234567')
    expect(receiptDecimal('1.2345678', true)).toBe(null)
    expect(formatReceiptDecimal('-0.010000')).toBe('-0,01')
  })
  for (const bad of ['2026-02-29', '2026-04-31', '2026-13-01', '2026-1-01']) {
    it(`rejects nonexistent report date ${bad}`, () => expect(financeDate(bad)).toBe(false))
  }
  it('accepts the actual leap day', () => expect(financeDate('2028-02-29')).toBe(true))
})
