// Frontend contract fixtures, not a claim of Native/Auth/browser execution.
export const shopId = (n: number) => '60000000-0000-4000-8000-' + String(n).padStart(12, '0')
export const shopPayroll = shopId(1), shopMandor = shopId(2), shopSale = shopId(3), shopAllocation = shopId(4)
export function shopWorkspace(reserved = false) {
  return {
    contract_version: 'cp7.mandor-shop-workspace.v1', payroll_id: shopPayroll, contractor_id: shopMandor,
    status: 'CALCULATED', period_start: '2026-11-09', period_end: '2026-11-15',
    net_payable_preview: reserved ? '1700000.00' : '2000000.00', reserved_amount: reserved ? '300000.00' : '0.00',
    can_change: true, has_more: false, next_after: null as string | null,
    cards: [{ sale_id: shopSale, number: 'INV-EPI-01', physical_at: '2026-11-02T02:00:00+00:00',
      net_invoice: '300000.00', paid_amount: '0.00', outstanding: '300000.00',
      allocated_amount: reserved ? '300000.00' : '0.00', available_to_reserve: reserved ? '0.00' : '300000.00',
      review_token: 'a'.repeat(64), allocations: reserved ? [{
        allocation: { allocation_id: shopAllocation, sale_id: shopSale, payroll_id: shopPayroll,
          contractor_id: shopMandor, amount: '300000.00', state: 'RESERVED' },
        payroll_number: 'PAY-EPI-W2', period_start: '2026-11-09', period_end: '2026-11-15', payroll_status: 'CALCULATED',
      }] : [],
    }],
  }
}
