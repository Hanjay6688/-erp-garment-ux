import { describe, expect, it } from 'vitest'
import { SENSITIVE_ACTION_PERMISSION, firstAllowedPageId, hasPermission, isNavLabelAllowed, isPageAllowed } from './accessCatalog'

describe('frontend access ownership', () => {
  const custom = {
    permissions: ['dashboard.view', 'production.wip.view', 'master.pattern.view', 'finance.payroll.approve'],
  }

  it('supports a custom multi-module bundle without checking a role name', () => {
    expect(isPageAllowed(custom, 'sewing-wip')).toBe(true)
    expect(isPageAllowed(custom, 'master-pattern')).toBe(true)
    expect(isNavLabelAllowed(custom, 'WIP & Sewing')).toBe(true)
    expect(isPageAllowed(custom, 'finance-payroll')).toBe(false)
  })

  it('keeps route visibility separate from sensitive action permission', () => {
    expect(hasPermission(custom, SENSITIVE_ACTION_PERMISSION.approvePayroll)).toBe(true)
    expect(hasPermission(custom, SENSITIVE_ACTION_PERMISSION.payPayroll)).toBe(false)
    expect(hasPermission(custom, SENSITIVE_ACTION_PERMISSION.adjustWip)).toBe(false)
  })

  it('fails closed for unknown and unowned routes', () => {
    expect(isPageAllowed(custom, 'missing-route')).toBe(false)
    expect(isNavLabelAllowed(custom, 'Missing label')).toBe(false)
  })

  it('lands a custom role on its first visible workspace instead of a forbidden dashboard', () => {
    const productionOnly = {
      permissions: ['production.wip.view', 'master.pattern.view'],
    }

    expect(firstAllowedPageId(productionOnly)).toBe('sewing-wip')
    expect(firstAllowedPageId(productionOnly, ['dashboard', 'master-pattern', 'sewing-wip'])).toBe('master-pattern')
    expect(firstAllowedPageId({ permissions: ['production.wip.post'] })).toBeNull()
  })
})
