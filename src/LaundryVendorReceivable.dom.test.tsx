// @vitest-environment jsdom
// Real component/recovery hooks with explicit RPC doubles, not actual Auth acceptance.
import { act } from 'react'
import { createRoot, type Root } from 'react-dom/client'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import LaundryBdPanel from './LaundryBdPanel'
import { LAU_POLICY_KEYS } from './laundryBd'
import { readProductionRecovery } from './productionRecovery'
import { recoveryRuntime } from '../tests/fixtures/productionRecovery'
const mock = vi.hoisted(() => ({ auth: null as unknown, rpc: vi.fn() }))
vi.mock('./auth/AuthProvider', () => ({ useAuth: () => mock.auth }))
vi.mock('./lib/supabase', () => ({ getUatSupabaseClient: () => mock }))
const id = (n: number) => `00000000-0000-4000-8000-${String(n).padStart(12, '0')}`
const scope = `${recoveryRuntime.projectRef}:${id(100)}`
const workspace = () => ({ pagination: { as_of: '2026-10-06T00:00:00Z', invoice_next: null, receipt_next: null },
  money_visible: true, can_manage_master: true, can_set_price: true, is_owner: true,
  policies: LAU_POLICY_KEYS.map(key => ({ key, status: 'PENDING_POLICY_VALUE', value: null, version: '1', set_at: '2026-10-06T07:00:00', reason: 'Synthetic policy' })),
  vendors: [{ id: id(1), code: 'V1', name: 'Laundry A', pricing_mode: 'RATE', pricing_unit: 'PCS', minimum_charge: null, terms_version: '1', bd_priced: false }],
  processes: [], components: [], packages: [], process_rates: [], scoped_rates: [], priced_deliveries: [], opening_uninvoiced: [],
  invoices: [], billable_receipts: [], accounts: [], pending_cost: { goods: [], sales: [] },
  vendor_receivable_contract: 'cp7.vendor-receivable.v1', vendor_receivable_accounts: [{ id: id(3), code: 'ARV', name: 'Piutang vendor' }],
  payables: { vendor_receivable_contract: 'cp7.vendor-receivable.v1', documents: [],
    cash_accounts: [{ id: id(4), code: 'BANK', name: 'Bank Utama' }],
    credits: [{ kind: 'INVOICE_CORRECTION', id: id(2), number: 'KOR-1', approved_date: '2026-10-01', amount: '100.00', applied: '0.00', available: '100.00',
      receivable: '100.00', refunded: '0.00', corrects: 'INV-1' }], refunds: [],
    ledger: { ap_balance: '0.00', documents_remaining: '0.00', credit_available: '100.00', receivable_balance: '100.00', receivable_gl: '100.00', matches: true } },
})
let root: Root, box: HTMLDivElement
let data: ReturnType<typeof workspace>
beforeEach(() => {
  Object.assign(globalThis, { IS_REACT_ACT_ENVIRONMENT: true }); localStorage.clear(); mock.rpc.mockReset(); data = workspace()
  mock.auth = { runtime: recoveryRuntime, identity: { status: 'AUTHORIZED',
    profile: { id: id(100), authUserId: id(101), rowVersion: 1, roleRowVersion: 1, role: 'OWNER', roleName: 'Owner', isActive: true },
    permissions: ['production.laundry.view', 'finance.hpp.manage', 'finance.ap.view'] } }
  Object.defineProperty(navigator, 'locks', { configurable: true, value: { request: vi.fn(async (_name, _options, run) => run({ name: _name, mode: 'exclusive' })) } })
  mock.rpc.mockImplementation(async name => { if (name === 'erp_get_laundry_bd_workspace_v1') return { data, error: null }; throw Error('Unexpected ' + name) })
  box = document.createElement('div'); document.body.append(box); root = createRoot(box)
})
afterEach(async () => { await act(async () => root.unmount()); box.remove(); localStorage.clear(); Reflect.deleteProperty(navigator, 'locks'); vi.restoreAllMocks() })
const settle = async () => act(async () => { await new Promise(resolve => setTimeout(resolve, 0)) })
const button = (name: string) => { const matches = [...box.querySelectorAll<HTMLButtonElement>('button')].filter(e => e.textContent?.trim() === name); expect(matches).toHaveLength(1); return matches[0] }
async function click(name: string) { await act(async () => button(name).click()); await settle() }
async function change(label: string, value: string) {
  const e = box.querySelector<HTMLInputElement | HTMLSelectElement>(`[aria-label="${label}"]`)!
  expect(e).not.toBeNull()
  await act(async () => { const proto = e.tagName === 'SELECT' ? HTMLSelectElement.prototype : HTMLInputElement.prototype
    Object.getOwnPropertyDescriptor(proto, 'value')!.set!.call(e, value); e.dispatchEvent(new Event(e.tagName === 'SELECT' ? 'change' : 'input', { bubbles: true })) })
  await settle()
}
async function open() {
  await act(async () => root.render(<LaundryBdPanel laundry={null} onPosted={() => {}}/>)); await settle()
  await change('Vendor harga laundry', id(1)); await click('Pembayaran vendor')
}
it('lost refund response retains source and UUID; reconcile uses that same envelope', async () => {
  let first = true
  mock.rpc.mockImplementation(async (name, args) => {
    if (name === 'erp_get_laundry_bd_workspace_v1') return { data, error: null }
    if (name === 'erp_save_laundry_bd_action_v1') {
      if (first) { first = false; return { data: null, error: { message: 'Failed to fetch' } } }
      return { data: { action: args.p_action, request_id: args.p_client_request_id, refund_id: args.p_client_request_id,
        source_id: args.p_payload.source_id, amount: args.p_payload.amount, remaining: '74.90', journal_id: id(30) }, error: null }
    }
    throw Error('Unexpected ' + name)
  })
  await open(); await change('Piutang vendor dikembalikan', id(2)); await change('Rekening penerima pengembalian vendor', id(4))
  await change('Nominal pengembalian vendor', '25,10'); await change('Alasan pengembalian vendor', 'Uang dari vendor sudah masuk bank')
  expect(button('Catat uang diterima dari vendor').disabled).toBe(false)
  await click('Catat uang diterima dari vendor')
  const writes = () => mock.rpc.mock.calls.filter(([n]) => n === 'erp_save_laundry_bd_action_v1')
  expect(writes()).toHaveLength(1)
  const firstArgs = writes()[0][1]
  expect(firstArgs.p_payload).toMatchObject({ source_id: id(2), amount: '25.10', cash_account_id: id(4) })
  expect(readProductionRecovery(scope).pending.LAUNDRY_BD?.id).toBe(firstArgs.p_client_request_id)
  expect(button('Catat uang diterima dari vendor').disabled).toBe(true)
  await click('Reconcile transaksi')
  expect(writes()).toHaveLength(2); expect(writes()[1][1]).toEqual(firstArgs)
})
it('refund amount cannot exceed displayed source capacity', async () => {
  await open(); await change('Piutang vendor dikembalikan', id(2)); await change('Rekening penerima pengembalian vendor', id(4))
  await change('Alasan pengembalian vendor', 'Uang sudah masuk bank'); await change('Nominal pengembalian vendor', '100.01')
  expect(button('Catat uang diterima dari vendor').disabled).toBe(true)
  expect(mock.rpc.mock.calls.filter(([n]) => n === 'erp_save_laundry_bd_action_v1')).toHaveLength(0)
})
it('older backend has no refund control; incomplete successor fails closed', async () => {
  const old = data as unknown as Record<string, any>
  delete old.vendor_receivable_contract; delete old.vendor_receivable_accounts; delete old.payables.vendor_receivable_contract
  await open()
  expect(box.querySelector('[aria-label="Pengembalian piutang vendor"]')).toBeNull()
})
