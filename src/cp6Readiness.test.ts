import { describe, expect, it } from 'vitest'
import { LAU_POLICY_KEYS, policyValue as laundryValue } from './laundryBd'
import { ACCESSORY_POLICY_KEYS, policyValue as accessoryValue } from './accessoryService'
import { invoicePolicyMessage, ownerChoice, policyStatus, policyValueText, type PolicyState } from './cp6Readiness'

const pending = (key: PolicyState['key']): PolicyState => ({ key, status: 'PENDING_POLICY_VALUE', value: null })
describe('CP6 readiness follows applied Native policies and recorded owner decisions', () => {
  it('keeps eight unanswered settings, four decided but unapplied values and one intentionally disabled policy distinct', () => {
    const policies = [...ACCESSORY_POLICY_KEYS, ...LAU_POLICY_KEYS].map(pending)
    expect(policies.filter(p => policyStatus(p) === 'Perlu isian owner')).toHaveLength(8)
    expect(policies.filter(p => policyStatus(p) === 'Keputusan owner belum diterapkan')).toHaveLength(4)
    expect(policies.filter(p => policyStatus(p) === 'Sengaja tidak diaktifkan').map(p => p.key)).toEqual(['LAU-DEC05'])
    expect(policyStatus({ ...pending('LAU-DEC05'), status: 'SET', value: {} })).toBe('Ditetapkan di aplikasi')
  })
  it('does not mistake an owner decision or an absent policy row for a ready invoice', () => {
    expect(invoicePolicyMessage([])).toContain('LAU-DEC02 dan LAU-DEC06')
    const policies = LAU_POLICY_KEYS.map(pending)
    expect(invoicePolicyMessage(policies)).toContain('Draf invoice dan penerimaan barang tetap bisa berjalan')
    policies[1] = { ...policies[1], status: 'SET', value: { billable: ['GOOD'] } }
    expect(invoicePolicyMessage(policies)).toContain('LAU-DEC06')
    policies[5] = { ...policies[5], status: 'SET', value: { variance_mode: 'PRODUCT_COST' } }
    expect(invoicePolicyMessage(policies)).toBeNull()
  })
  it('translates the four recorded choices through the actual save parsers without supplying accounts or vendor agreements', () => {
    expect(accessoryValue('ACC-DEC05', ownerChoice('ACC-DEC05')!.fields)).toEqual({ mode: 'CREDIT_THEN_CARRY', credit_conditions: ['USABLE'] })
    expect(accessoryValue('ACC-DEC07', ownerChoice('ACC-DEC07')!.fields)).toEqual({ approval: 'NONE' })
    const sale = ownerChoice('LAU-DEC04')!, variance = ownerChoice('LAU-DEC06')!
    expect(laundryValue('LAU-DEC04', sale.fields, sale.picks)).toEqual({ sale_with_unknown_laundry: 'ALLOW_PENDING' })
    expect(laundryValue('LAU-DEC06', variance.fields, variance.picks)).toEqual({ variance_mode: 'PRODUCT_COST', after_payment: 'CORRECTION_DOCUMENT' })
    for (const key of ['ACC-DEC03', 'ACC-DEC04', 'ACC-DEC06', 'ERP-DEC02', 'LAU-DEC01', 'LAU-DEC02', 'LAU-DEC03', 'LAU-DEC05'] as const) expect(ownerChoice(key)).toBeNull()
    sale.fields.sale = 'REFUSE'
    expect(ownerChoice('LAU-DEC04')!.fields.sale).toBe('ALLOW_PENDING')
  })
  it('shows an applied policy hidden from a reader as hidden rather than empty or a guessed decision', () => {
    expect(policyValueText({ ...pending('ACC-DEC07'), status: 'SET' })).toBe('Rincian hanya terlihat owner/admin')
    expect(policyValueText({ ...pending('ACC-DEC05'), status: 'SET', value: { mode: 'CREDIT_THEN_CARRY', credit_conditions: ['USABLE'] } })).toBe('Cara: Kredit nota, sisanya ke payroll berikutnya · Barang yang dikreditkan: Layak pakai')
  })
})
