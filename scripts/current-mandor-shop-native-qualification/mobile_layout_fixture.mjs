// Synthetic reads for layout only. All writes and undeclared requests fail.
import { NAV_PERMISSION_BY_LABEL, PAGE_PERMISSION_BY_ID } from '../../src/auth/accessCatalog'
import { recoveryRuntime } from '../../tests/fixtures/productionRecovery'
import { shopMandor, shopPayroll, shopWorkspace } from '../../tests/fixtures/mandorShop'

const fixture = globalThis.__mandorMobileLayoutFixture
const capturedAt = fixture.physical.sale_at
const start = fixture.period_start
const end = fixture.period_end
const token = 'a'.repeat(32)
const zero = '0.00'
const payroll = {
  id: shopPayroll, payroll_number: fixture.payroll_number, contractor_id: shopMandor,
  contractor_name: fixture.contractor_name, attendance_required: false, period_start: start, period_end: end,
  status: 'DRAFT', row_version: '1', review_token: token, notes: null,
  labor_total: zero, attendance_total: zero, reimburse_total: zero, deduction_total: zero,
  manual_adjustment: '2000000.00', net_payable: '2000000.00', payment_cash_account_id: null,
  payment_cash_account_name: null, payment_date: fixture.payment_date, settled_at: null, created_at: capturedAt,
  updated_at: capturedAt, totals_match_items: true, counts: {work: '0', attendance: '0', reimbursements: '0', deductions: '0', notes: '0'},
}
const page = (rows = []) => ({ rows, total: String(rows.length), offset: 0, limit: 25, next_offset: null })
const permissions = [...new Set([...Object.values(NAV_PERMISSION_BY_LABEL), ...Object.values(PAGE_PERMISSION_BY_ID),
  'finance.ar.view', 'finance.payroll.view', 'finance.payroll.approve', 'finance.payroll.pay'])]
const profile = { id: 'layout-owner', authUserId: 'layout-owner', fullName: 'Auditor OWNER', roleId: 'layout-owner',
  role: 'OWNER', roleName: 'Owner', rowVersion: 1, roleRowVersion: 1, isActive: true }
const auth = { runtime: { ...recoveryRuntime, mode: 'DISPOSABLE_TEST', authMode: 'LOCAL_SUPABASE', projectRef: 'cp6-disposable' },
  identity: { status: 'AUTHORIZED', profile, permissions, externalPortals: { mandor: 'NOT CONNECTED', laundry: 'NOT CONNECTED', store: 'NOT CONNECTED' } },
  signingOut: false, signOutError: null }
export const useAuth = () => auth

const requestLog = globalThis.__mandorMobileLayoutRequests = []
const client = {
  async rpc(name, parameters) {
    requestLog.push(name)
    const allow = (data) => ({ error: null, data })
    switch (name) {
      case 'erp_cp7_get_payroll_workspace_v1': {
        const section = parameters.p_section
        if (section !== 'PAYROLLS' && (section !== 'WORK' || parameters.p_query.id !== shopPayroll)) break
        return allow({ contract_version: 'cp7.payroll-workspace.v1', section, read_at: capturedAt,
          capabilities: { approve: true, pay: true }, document: section === 'PAYROLLS' ? null : payroll,
          page: section === 'PAYROLLS' ? page([payroll]) : page() })
      }
      case 'erp_cp7_get_payroll_installments_v1':
        if (parameters.p_query.payroll_id !== shopPayroll) break
        return allow({ contract_version: 'cp7.payroll-installment-read.v1', captured_at: capturedAt,
          document: { payroll_id: shopPayroll, payroll_number: payroll.payroll_number, contractor_id: shopMandor,
            contractor_name: payroll.contractor_name, native_status: payroll.status, payment_state: 'NOT_APPROVED',
            managed: false, approved_net: payroll.net_payable, paid_amount: zero, remaining_amount: null,
            row_version: payroll.row_version, source_review_token: token, review_token: token },
          payments: page(), cash_accounts: page(), capabilities: { pay: true, reverse_payroll: true } })
      case 'erp_cp7_get_mandor_shop_payroll_v1': {
        if (parameters.p_payroll !== shopPayroll || parameters.p_after !== null) break
        const workspace = shopWorkspace()
        workspace.status = payroll.status
        workspace.period_start = start
        workspace.period_end = end
        workspace.cards[0].number = fixture.sale_number
        workspace.cards[0].physical_at = capturedAt
        return allow(workspace)
      }
    }
    throw new Error('MANDOR_LAYOUT_REFUSED_UNDECLARED_RPC:' + name)
  },
}
export const getUatSupabaseClient = () => client
